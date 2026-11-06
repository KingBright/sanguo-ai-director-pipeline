#!/usr/bin/env python3
"""Render an audio-conditioned performance with the installed MiniMax H3 pipeline.

Uses existing local models only. A manifest supplies shots with id, audio,
keyframe, prompt, before, after and seed. No speech synthesis or speed fitting.
Real GPU availability and artistic quality must be checked with a pilot first.
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import time
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame_budget(samples, rate, before, after):
    if samples <= 0 or rate <= 0 or not all(math.isfinite(x) and x >= 0 for x in (before, after)):
        raise ValueError('Invalid audio length or pauses')
    needed = (samples + round(before*rate) + round(after*rate)) * 24 / rate
    # Backend alignment, never a target length imposed on the actor.
    return max(22, math.ceil((needed-5)/17)*17+5)


def guidance_scale(value=1.):
    value = float(value)
    if not math.isfinite(value) or value < 1:
        raise ValueError('cfg_scale must be finite and at least1')
    return value


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest', type=Path)
    p.add_argument('--model-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--ffmpeg', default='ffmpeg')
    p.add_argument('--shot', action='append', help='Render only selected shot ids')
    a = p.parse_args()
    manifest = json.loads(a.manifest.read_text(encoding='utf-8'))
    shots = [s for s in manifest['shots'] if not a.shot or s['id'] in a.shot]
    if not shots or len({s['id'] for s in shots}) != len(shots):
        raise ValueError('Empty selection or duplicate shot ids')
    if a.shot and set(a.shot) != {s['id'] for s in shots}:
        raise ValueError('Unknown shot selection')
    width, height = manifest.get('width', 896), manifest.get('height', 512)
    if width % 64 or height % 64:
        raise ValueError('H3 width and height must be multiples of64')
    scheduled = set()
    for shot in shots:
        shot['cfg_scale'] = guidance_scale(shot.get('cfg_scale', 1.))
        if Path(shot['id']).name != shot['id'] or shot['id'] in ('.', '..'):
            raise ValueError('Shot id must be a simple filename')
        if (a.output/shot['id']).exists():
            raise FileExistsError(f"Retakes need a new output directory: {shot['id']}")
        if not (a.manifest.parent/shot['audio']).is_file():
            raise FileNotFoundError(shot['audio'])
        if 'keyframe_from' in shot:
            previous = shot['keyframe_from']
            if previous not in scheduled:
                raise ValueError('keyframe_from must name an earlier selected shot')
        elif not (a.manifest.parent/shot['keyframe']).is_file():
            raise FileNotFoundError(shot['keyframe'])
        scheduled.add(shot['id'])
    os.environ.setdefault('TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL','1')
    os.environ['DIFFSYNTH_SKIP_DOWNLOAD']='True'
    import torch
    import numpy as np
    import soundfile as sf
    from PIL import Image
    from diffsynth.pipelines.minimax_h3_audio_video import MiniMaxH3Pipeline
    from diffsynth.core import ModelConfig
    from diffsynth.utils.data import save_video
    names=['diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors',
           'text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors',
           'vae/minimax_h3_video_vae_fp16.safetensors','vae/minimax_h3_audio_vae_fp32.safetensors']
    for name in names+['processor','loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors']:
        if not (a.model_root/name).exists():
            raise FileNotFoundError(a.model_root/name)
    pipe = MiniMaxH3Pipeline.from_pretrained(torch_dtype=torch.bfloat16,device='cuda',
        model_configs=[ModelConfig(path=str(a.model_root/n)) for n in names],
        processor_config=ModelConfig(path=str(a.model_root/'processor')),redirect_common_files=False)
    pipe.load_lora(pipe.dit,str(a.model_root/'loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors'),alpha=1.)
    for shot in shots:
        start=time.time();out=a.output/shot['id'];out.mkdir(parents=True)
        source_audio=(a.manifest.parent/shot['audio']).resolve()
        source_image=((a.output/shot['keyframe_from']/'last_frame.png') if 'keyframe_from' in shot
                      else (a.manifest.parent/shot['keyframe'])).resolve()
        audio,rate=sf.read(source_audio,dtype='float32',always_2d=True)
        if audio.shape[1] not in (1,2) or not np.isfinite(audio).all() or (np.max(np.abs(audio)) < .005 and shot.get('dialogue', True)):
            raise ValueError('Need finite audible mono or stereo performance')
        before,after=shot.get('before',.3),shot.get('after',.7)
        frames=frame_budget(len(audio),rate,before,after)
        if audio.shape[1]==1:audio=np.repeat(audio,2,axis=1)
        audio=np.pad(audio,((round(before*rate),0),(0,0)))
        audio=np.pad(audio,((0,math.ceil(frames/24*rate)-len(audio)),(0,0)))
        sf.write(out/'condition.wav',audio,rate,subtype='FLOAT')
        record={**shot,'audio_sha256':digest(source_audio),'keyframe_sha256':digest(source_image),
                'frames':frames,'fps':24,'audio_mode':'audio_conditioned_generation','speed':1,
                'negative_guidance_active':shot['cfg_scale'] != 1.,
                'status':'rendering','started_at':time.time(),'acceptance':'not_reviewed'}
        receipt=out/'generation.json';receipt.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f"RENDER {shot['id']} {frames} frames cfg={shot['cfg_scale']} negative_guidance={record['negative_guidance_active']}",flush=True)
        result=pipe(prompt=shot['prompt'],negative_prompt=shot.get('negative_prompt','extra limbs, subtitles, distorted face, disappearing objects'),
            height=height,width=width,num_frames=frames,num_inference_steps=4,cfg_scale=shot['cfg_scale'],flow_shift=12.,audio_flow_shift=3.,
            keyframes=[Image.open(source_image).convert('RGB')],keyframe_indices=[0],keyframe_strengths=[1.],
            retake_audio=torch.from_numpy(audio.T.copy()),retake_audio_sample_rate=rate,seconds_regions_to_retake=[],seed=shot.get('seed',401))
        pictures=result[0]
        if len(pictures)!=frames:raise RuntimeError('Unexpected generated frame count')
        # Model output is sRGB RGB; transform explicitly before encoding YUV.
        color='format=gbrp,colorspace=ispace=gbr:iprimaries=bt709:itrc=iec61966-2-1:irange=pc:all=bt709:range=tv:format=yuv420p'
        save_video(pictures,str(out/'picture.mp4'),fps=24,quality=9,ffmpeg_params=[
            '-vf',color,'-colorspace','bt709','-color_trc','bt709','-color_primaries','bt709','-color_range','tv'])
        pictures[-1].save(out/'last_frame.png')
        subprocess.run([a.ffmpeg,'-v','error','-i',str(out/'picture.mp4'),'-i',str(out/'condition.wav'),
            '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(out/'native.mp4')],check=True)
        record.update(status='generated',elapsed=time.time()-start,output_sha256=digest(out/'native.mp4'),color_conversion=color)
        receipt.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f"GENERATED {shot['id']} elapsed={record['elapsed']:.1f}s",flush=True)
        del result,pictures
        torch.cuda.empty_cache()


if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    main()

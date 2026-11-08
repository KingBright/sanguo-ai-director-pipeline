"""Build a silent STATIC storyboard reel; not acting, lip sync or a finished film."""
import json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
SHOTS=[
 (5,'进门：先交代母子三人和店内方位。','门铃、脚步；此处没有对白。'),
 (5,'母亲看零钱，再决定买半份。','母亲：“师傅，要半份。”'),
 (4,'付款成立，老板开始正常服务。','老板：“好，半份十块。”'),
 (5,'同一整饼切成两半；A上白盘，B留在柜台。','切饼声、盘子声；完整动作需要后续试拍。'),
 (5,'母亲端A到餐桌，两个孩子这时才坐下。','母亲：“来，坐这儿。”'),
 (4,'男孩先看见母亲没动，再邀请她。','男孩：“妈妈，你也吃。”'),
 (6,'母亲看分量、迟疑、让盘，再笑着推辞。','母亲：“你们先吃。妈妈回家再吃。”'),
 (4,'老板停下抹布；看母亲，再看剩半与钟。','留出听见、理解和决定的反应。'),
 (4,'老板把B从柜台端到餐桌；木板变空。','用走动和盘子方向接下一镜。'),
 (12,'母亲：“这……我们只买了半份。”','老板：“快打烊了，这半个也卖不掉。帮我吃了吧。”'),
 (6,'母亲：“谢谢您。”','男孩：“妈妈，这块给你。” 这次她接受。'),
 (5,'母亲真正吃下一口，孩子也放松地吃起来。','在第一口与放松反应处收束；图中剩余量仅为示意。'),
]

def main():
 out=ROOT/'animatic-build'
 out.mkdir(exist_ok=True)
 header=out/'header.txt'
 header.write_text('《剩下的半份》  静态分镜预演 · 无对白音轨 · 非成片',encoding='utf8')
 paths=[]
 for i,(duration,line1,line2) in enumerate(SHOTS):
  path=out/f'{i+1:02}.mp4';paths.append(path)
  text=out/f'{i+1:02}.txt';text.write_text(f'{i+1:02}  {line1}\n{line2}',encoding='utf8')
  x=[4,486,970,1452][i%4];y=[4,276,548][i//4]
  overlay=out/f'{i+1:02}-labels.png'
  canvas=Image.new('RGBA',(1280,720),(0,0,0,0));draw=ImageDraw.Draw(canvas)
  draw.text((28,8),header.read_text(),font=ImageFont.truetype(FONT,20),fill='#cbd5e1')
  draw.multiline_text((28,628),text.read_text(),font=ImageFont.truetype(FONT,23),fill='white',spacing=12)
  canvas.save(overlay)
  vf=(f'[0:v]crop=474:264:{x}:{y},scale=1024:576:flags=lanczos,'
      'pad=1280:720:128:36:color=0x161a20,setsar=1[art];[art][1:v]overlay=0:0,format=yuv420p[out]')
  subprocess.run(['ffmpeg','-v','error','-y','-loop','1','-i',str(ROOT/'storyboard-draft-v2.png'),
                  '-loop','1','-i',str(overlay),'-filter_complex',vf,'-map','[out]',
                  '-t',str(duration),'-r','24','-an','-c:v','libx264','-crf','20',
                  '-preset','veryfast','-pix_fmt','yuv420p',str(path)],check=True)

 listing=out/'concat.txt';listing.write_text('\n'.join("file '"+p.name+"'" for p in paths))
 subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),
                 '-c','copy','-movflags','+faststart',str(ROOT/'story-reel-draft.mp4')],check=True)
 (ROOT/'animatic.json').write_text(json.dumps({'status':'static_storyboard_preview_only','audio':'none',
    'duration_seconds':sum(x[0] for x in SHOTS),'timing':'provisional, not based on acted dialogue',
    'not_verified':['acting','pronunciation','lip sync','actual object transfer'],
    'shots':[{'id':i+1,'seconds':x[0],'purpose':x[1],'dialogue_or_note':x[2]} for i,x in enumerate(SHOTS)]},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'preview':str(ROOT/'story-reel-draft.mp4'),'seconds':sum(x[0] for x in SHOTS),'audio':'none'}))

if __name__=='__main__':main()

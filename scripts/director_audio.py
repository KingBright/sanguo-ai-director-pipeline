#!/usr/bin/env python3
"""Generate standalone dialogue or instrumental BGM for AetherDirector."""

import argparse
import base64
import binascii
import io
import json
import os
import re
import sys
import tempfile
import wave
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

API_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
TTS_MODEL = "gemini-3.8-flash-tts"
MUSIC_MODEL = "lyria-3.5"
CLIP_MODEL = "lyria-3-clip-preview"
QWEN_MODEL = "Qwen3-TTS-12Hz-1.7B-VoiceDesign"
RESPONSE_LIMIT = 64 * 1024 * 1024


class AudioError(Exception):
    """Generation failed before a playable output could be published."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def gemini_audio(request_body, timeout):
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise AudioError("Set GEMINI_API_KEY (or GOOGLE_API_KEY) for the Gemini Developer API.")

    request = Request(
        API_URL,
        method="POST",
        data=json.dumps({**request_body, "store": False}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Api-Revision": "2026-05-20",
            "x-goog-api-key": key,
        },
    )
    try:
        with build_opener(NoRedirects()).open(request, timeout=timeout) as response:
            data = response.read(RESPONSE_LIMIT + 1)
    except HTTPError as exc:
        status = ""
        try:
            detail = json.loads(exc.read(8192))["error"]["status"]
            if re.fullmatch(r"[A-Z_]{1,64}", detail):
                status = f" ({detail})"
        except (KeyError, TypeError, ValueError):
            pass
        raise AudioError(f"Gemini API returned HTTP {exc.code}{status}.") from None
    except (URLError, TimeoutError):
        raise AudioError("Could not complete the Gemini API request. Check network and timeout.") from None

    if len(data) > RESPONSE_LIMIT:
        raise AudioError("Gemini API response exceeded 64 MiB.")
    return decode_interaction(json.loads(data))


def decode_interaction(result):
    if result.get("status") != "completed":
        raise AudioError("Gemini API did not complete the audio interaction.")
    audio = [
        part
        for step in result.get("steps", [])
        if step.get("type") == "model_output"
        for part in step.get("content", [])
        if part.get("type") == "audio" and part.get("data")
    ]
    if len(audio) != 1:
        raise AudioError("Gemini API did not return exactly one audio track.")
    try:
        return base64.b64decode(audio[0]["data"], validate=True), audio[0]["mime_type"]
    except (binascii.Error, KeyError, TypeError):
        raise AudioError("Gemini API returned invalid audio data.") from None


def speech_wav(audio, mime_type):
    media_type, _, params = mime_type.lower().partition(";")
    if media_type in {"audio/l16", "audio/pcm"}:
        rate = re.search(r"(?:^|;)\s*rate=(\d+)", params)
        sample_rate = int(rate.group(1)) if rate else 24000
        if not audio or len(audio) % 2 or not 8000 <= sample_rate <= 96000:
            raise AudioError("Gemini API returned invalid 16-bit PCM speech.")
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as output:
            output.setparams((1, 2, sample_rate, 0, "NONE", "not compressed"))
            output.writeframes(audio)
        audio = buffer.getvalue()
    elif media_type not in {"audio/wav", "audio/wave", "audio/x-wav"}:
        raise AudioError("The speech response did not contain PCM or WAV audio.")

    with wave.open(io.BytesIO(audio), "rb") as source:
        frames = source.readframes(source.getnframes())
        if not frames or len(frames) != source.getnframes() * source.getsampwidth() * source.getnchannels():
            raise AudioError("Speech WAV is empty or truncated.")
        return audio, round(source.getnframes() / source.getframerate(), 3)


def qwen_speech(text, voice, style, model_dir, language):
    if not (model_dir / "config.json").is_file():
        raise AudioError(f"Qwen VoiceDesign model directory is missing config.json: {model_dir}")
    try:
        import soundfile
        import torch
        from qwen_tts import Qwen3TTSModel
    except ImportError:
        raise AudioError("Run the command with the Python environment that has qwen-tts, torch and soundfile.") from None

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda:0" else torch.float32
    model = Qwen3TTSModel.from_pretrained(str(model_dir), device_map=device, dtype=dtype)
    instruction = "\n".join(filter(None, (voice or "清晰自然的叙述音色", style)))
    samples, sample_rate = model.generate_voice_design(text=text, language=language, instruct=instruction)
    buffer = io.BytesIO()
    soundfile.write(buffer, samples[0], sample_rate, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


def generate_speech(args):
    text = read_input(args.text, args.text_file)
    if args.provider == "qwen":
        model = QWEN_MODEL
        data = qwen_speech(text, args.voice, args.style, args.model_dir.expanduser(), args.language or "Auto")
        mime_type = "audio/wav"
    else:
        if args.model_dir:
            raise AudioError("--model-dir requires --provider qwen.")
        model = TTS_MODEL
        if args.language:
            raise AudioError("Use --style to specify accent or delivery with Gemini.")
        transcript = {"type": "text", "text": text}
        if args.style:
            transcript["annotations"] = [{"type": "speech_metadata", "style": args.style}]
        data, mime_type = gemini_audio(
            {
                "model": model,
                "input": [{"type": "user_input", "content": [transcript]}],
                "response_format": {"type": "audio"},
                "generation_config": {
                    "speech_config": [{"voice": args.voice or "Kore"}],
                },
            },
            args.timeout,
        )
    audio, duration = speech_wav(data, mime_type)
    return audio, {"provider": args.provider, "model": model, "duration_seconds": duration}


def generate_music(args):
    prompt = read_input(args.prompt, args.prompt_file)
    model = CLIP_MODEL if args.clip else MUSIC_MODEL
    audio, mime_type = gemini_audio(
        {
            "model": model,
            "input": f"{prompt}\nInstrumental background music only. No lyrics, vocals, or spoken words.",
        },
        args.timeout,
    )
    if mime_type.lower().split(";", 1)[0] not in {"audio/mpeg", "audio/mp3"} or not is_mp3(audio):
        raise AudioError("Lyria did not return an MP3 audio track.")
    return audio, {"provider": "gemini", "model": model}


def is_mp3(audio):
    if audio.startswith(b"ID3") and len(audio) > 10 and all(value < 128 for value in audio[6:10]):
        tag_size = 0
        for value in audio[6:10]:
            tag_size = tag_size * 128 + value
        footer = 10 if audio[3] == 4 and audio[5] & 0x10 else 0
        audio = audio[10 + tag_size + footer:]
    return (
        len(audio) >= 128
        and audio[0] == 0xFF
        and audio[1] & 0xE0 == 0xE0
        and audio[1] & 0x06 == 0x02
    )


def read_input(text, file):
    value = file.read_text(encoding="utf-8-sig") if file else text
    if not value.strip():
        raise AudioError("Provide nonempty text or a UTF-8 text file.")
    return value


def publish_audio(output, audio):
    output.parent.mkdir(parents=True, exist_ok=True)
    # Write completely on the destination volume before making the result visible.
    # A hard link publishes without overwriting a concurrent writer's result.
    with tempfile.TemporaryDirectory(prefix=".director-audio-", dir=output.parent) as tmp:
        staged = Path(tmp) / output.name
        staged.write_bytes(audio)
        os.link(staged, output)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    speech = commands.add_parser("speech", help="Generate a standalone voice-over WAV.")
    music = commands.add_parser("music", help="Generate instrumental BGM with the Gemini API.")
    for command, name in [(speech, "text"), (music, "prompt")]:
        group = command.add_mutually_exclusive_group(required=True)
        group.add_argument(f"--{name}")
        group.add_argument(f"--{name}-file", type=Path)
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--timeout", type=int, default=300, help="Gemini API timeout in seconds.")

    speech.add_argument("--provider", choices=["gemini", "qwen"], default="gemini")
    speech.add_argument("--voice", help="Gemini voice name or Qwen timbre description.")
    speech.add_argument("--style", help="Natural-language delivery, emotion and pacing.")
    speech.add_argument("--model-dir", type=Path, help="Installed Qwen VoiceDesign model directory.")
    speech.add_argument("--language", help="Qwen language, for example Chinese (default: Auto).")
    music.add_argument("--clip", action="store_true", help="Use Lyria 3 Clip for an approximately 30s preview.")
    args = parser.parse_args(argv)
    output = Path(os.path.abspath(args.output.expanduser()))

    try:
        suffix = ".wav" if args.command == "speech" else ".mp3"
        if output.suffix.lower() != suffix:
            raise AudioError(f"Output must have the {suffix} extension.")
        if os.path.lexists(output):
            raise AudioError(f"Output already exists: {output}")
        if args.timeout <= 0:
            raise AudioError("--timeout must be positive.")
        if args.command == "speech" and args.provider == "qwen" and not args.model_dir:
            args.model_dir = Path.home() / "minimax" / QWEN_MODEL
        audio, details = generate_speech(args) if args.command == "speech" else generate_music(args)
        publish_audio(output, audio)
    except (AudioError, OSError, RuntimeError, ValueError, TypeError, AttributeError, wave.Error, EOFError) as exc:
        print(f"director-audio: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({**details, "output": str(output), "bytes": len(audio)}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

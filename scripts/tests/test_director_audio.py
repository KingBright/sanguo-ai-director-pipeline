import base64
import contextlib
import io
import json
import os
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from scripts import director_audio as audio


PCM = b"\x22\x03\x00\x00" * 1200
MP3 = b"\xff\xfb\x90\x64" + b"\x00" * 413


def interaction(data, mime_type):
    return {
        "status": "completed",
        "steps": [
            {
                "type": "model_output",
                "content": [
                    {
                        "type": "audio",
                        "data": base64.b64encode(data).decode("ascii"),
                        "mime_type": mime_type,
                    },
                ],
            }
        ],
    }


class DirectorAudioTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def run_cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
            result = audio.main(list(args))
        return result, out.getvalue(), err.getvalue()

    def test_speech_preserves_transcript_and_passes_voice_and_style_separately(self):
        original = "放轻脚步。\n桥那头还有人。"
        output = self.root / "dialogue.wav"
        with patch.object(audio, "gemini_audio", return_value=(PCM, "audio/l16;rate=24000")) as provider:
            code, result, _ = self.run_cli(
                "speech", "--text", original, "--voice", "Kore", "--style", "紧张、轻声", "--output", str(output)
            )
        self.assertEqual(code, 0)
        body, _ = provider.call_args.args
        self.assertEqual(body["model"], "gemini-3.8-flash-tts")
        self.assertEqual(body["generation_config"]["speech_config"], [{"voice": "Kore"}])
        transcript = body["input"][0]["content"][0]
        self.assertEqual(transcript["text"], original)
        self.assertEqual(transcript["annotations"], [{"type": "speech_metadata", "style": "紧张、轻声"}])
        with wave.open(str(output), "rb") as generated:
            self.assertEqual(generated.getframerate(), 24000)
            self.assertEqual(generated.readframes(generated.getnframes()), PCM)
        self.assertEqual(json.loads(result)["duration_seconds"], 0.1)

    def test_lyria_preserves_mp3_and_requests_instrumental(self):
        output = self.root / "score.mp3"
        prompt = self.root / "prompt.txt"
        prompt.write_text("轻柔的钢琴", encoding="utf-8-sig")
        with patch.object(audio, "gemini_audio", return_value=(MP3, "audio/mpeg")) as provider:
            code, result, _ = self.run_cli("music", "--prompt-file", str(prompt), "--output", str(output))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(result)["model"], "lyria-3.5")
        self.assertEqual(output.read_bytes(), MP3)
        body, _ = provider.call_args.args
        self.assertIn("轻柔的钢琴", body["input"])
        self.assertIn("No lyrics, vocals, or spoken words.", body["input"])

    def test_refuses_missing_auth_or_invalid_media_without_an_output(self):
        output = self.root / "score.mp3"
        argv = ("music", "--prompt", "piano", "--output", str(output))
        with patch.dict(os.environ, {}, clear=True):
            code, _, error = self.run_cli(*argv)
        self.assertEqual(code, 1)
        self.assertIn("GEMINI_API_KEY", error)
        self.assertFalse(output.exists())
        with patch.object(audio, "gemini_audio", return_value=(b"not MP3", "audio/mpeg")):
            code, _, error = self.run_cli(*argv)
        self.assertEqual(code, 1)
        self.assertIn("did not return an MP3", error)
        self.assertFalse(output.exists())

    def test_preexisting_output_is_left_intact_without_calling_model(self):
        output = self.root / "existing.wav"
        output.write_bytes(b"original")
        with patch.object(audio, "gemini_audio") as provider:
            code, _, error = self.run_cli("speech", "--text", "test", "--output", str(output))
        self.assertEqual(code, 1)
        self.assertIn("already exists", error)
        self.assertEqual(output.read_bytes(), b"original")
        provider.assert_not_called()

    def test_decodes_only_completed_audio_interactions(self):
        result = interaction(MP3, "audio/mpeg")
        self.assertEqual(audio.decode_interaction(result), (MP3, "audio/mpeg"))
        result["status"] = "failed"
        with self.assertRaises(audio.AudioError):
            audio.decode_interaction(result)


if __name__ == "__main__":
    unittest.main()

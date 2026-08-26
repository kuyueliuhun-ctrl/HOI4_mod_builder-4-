"""电台语音广播（Piper TTS）适配测试。"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


class TtsRadioTest(unittest.TestCase):
    def test_not_installed_guide(self):
        from tts_radio import synthesize_ogg
        with patch("tts_radio.shutil.which", return_value=None), \
                patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PIPER_BIN", None)
            r = synthesize_ogg("测试广播", "/tmp/x.ogg")
            self.assertFalse(r["ok"])
            self.assertIn("未安装", r["reason"])
            self.assertIn("PIPER_BIN", r["guide"])

    def test_empty_text(self):
        from tts_radio import synthesize_ogg
        with patch("tts_radio.shutil.which", return_value="piper"):
            r = synthesize_ogg("   ", "/tmp/x.ogg")
            self.assertFalse(r["ok"])

    def test_synthesize_with_piper(self):
        from tts_radio import synthesize_ogg
        with patch("tts_radio.shutil.which", return_value="piper"), \
                patch("tts_radio.subprocess.run") as mrun, \
                patch("tts_radio.os.path.isfile", return_value=True), \
                patch("tts_radio.transcode_ogg",
                      return_value={"method": "copy"}):
            r = synthesize_ogg("Hello", "/tmp/x.ogg")
            self.assertTrue(r["ok"])
            self.assertEqual(r["ogg"], "/tmp/x.ogg")
            self.assertEqual(r["method"], "piper+copy")
            self.assertEqual(mrun.call_count, 1)
            args = mrun.call_args[0][0]
            self.assertIn("piper", args)
            self.assertIn("--output_file", args)

    def test_piper_available_env(self):
        from tts_radio import piper_available
        with patch("tts_radio.shutil.which", return_value=None):
            os.environ["PIPER_BIN"] = "/usr/bin/fake-piper"
            try:
                self.assertTrue(piper_available())
            finally:
                os.environ.pop("PIPER_BIN", None)


if __name__ == "__main__":
    unittest.main()
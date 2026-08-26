"""电台/广播 S 档后端测试（radio_station.py）。"""

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


def _mkdtemp(prefix):
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


class RadioStationTest(unittest.TestCase):
    def test_build_music_station_text(self):
        from radio_station import build_music_station_text
        t = build_music_station_text("base", ["a", "b"])
        self.assertIn('music_station = "base"', t)
        self.assertIn('song = "a"', t)
        self.assertIn('song = "b"', t)

    def test_write_music_station(self):
        from radio_station import write_music_station
        mod = _mkdtemp("radio_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        r = write_music_station(mod, "my_radio", ["song1", "song2"])
        self.assertEqual(r["path"], "music/my_radio.txt")
        fp = os.path.join(mod, "music", "my_radio.txt")
        self.assertTrue(os.path.isfile(fp))
        with open(fp, encoding="utf-8") as f:
            content = f.read()
        self.assertIn('song = "song1"', content)
        self.assertIn('song = "song2"', content)

    def test_transcode_copy_fallback(self):
        from radio_station import transcode_ogg
        mod = _mkdtemp("radio_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        with patch("radio_station.shutil.which", return_value=None):
            src = os.path.join(mod, "src.ogg")
            with open(src, "wb") as f:
                f.write(b"OggSfake")
            dst = os.path.join(mod, "music", "x.ogg")
            r = transcode_ogg(src, dst)
            self.assertEqual(r["method"], "copy")
            with open(dst, "rb") as f:
                self.assertEqual(f.read(), b"OggSfake")
            # 非 .ogg 且无 ffmpeg → ValueError
            src2 = os.path.join(mod, "src.wav")
            with open(src2, "wb") as f:
                f.write(b"WAVE")
            with self.assertRaises(ValueError):
                transcode_ogg(src2, dst)

    def test_add_ogg_track(self):
        from radio_station import add_ogg_track
        mod = _mkdtemp("radio_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        with patch("radio_station.shutil.which", return_value=None):
            src = os.path.join(mod, "song1.ogg")
            with open(src, "wb") as f:
                f.write(b"OggS")
            r = add_ogg_track(mod, "radio1", "song1", src)
            self.assertEqual(r["method"], "copy")
            fp = os.path.join(mod, "music", "radio1.txt")
            with open(fp, encoding="utf-8") as f:
                station = f.read()
            self.assertIn('song = "song1"', station)
            # 追加第二首：station 头不重复
            src2 = os.path.join(mod, "song2.ogg")
            with open(src2, "wb") as f:
                f.write(b"OggS")
            add_ogg_track(mod, "radio1", "song2", src2)
            with open(fp, encoding="utf-8") as f:
                station = f.read()
            self.assertEqual(station.count("music_station ="), 1)
            self.assertIn('song = "song2"', station)


if __name__ == "__main__":
    unittest.main()

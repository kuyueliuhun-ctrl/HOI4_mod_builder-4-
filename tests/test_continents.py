"""大洲划分（P1 方案 A）测试。"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


def _mkdtemp(prefix):
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


class _FakeStateData:
    def __init__(self, states, mod_path="", hoi4_path=""):
        self.states = states
        self.mod_path = mod_path
        self.hoi4_path = hoi4_path


class ContinentsTest(unittest.TestCase):
    def _make_env(self):
        mod = _mkdtemp("cont_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "map")
        os.makedirs(d, exist_ok=True)
        # id;R;G;B;type;coastal;terrain;continent
        lines = [
            "1;255;0;0;land;true;hills;1",     # 欧洲
            "2;0;255;0;land;false;plains;1",   # 欧洲
            "3;0;0;255;land;false;plains;6",   # 亚洲
            "4;0;0;0;sea;false;ocean;0",       # 水域
        ]
        with open(os.path.join(d, "definition.csv"), "w",
                  encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        states = {1: {"provinces": [1, 2, 3, 4]}}
        return mod, states

    def test_load_province_continents(self):
        from continents import load_province_continents
        mod, _ = self._make_env()
        pc = load_province_continents(mod, "")
        self.assertEqual(pc[1], 1)
        self.assertEqual(pc[2], 1)
        self.assertEqual(pc[3], 6)
        self.assertEqual(pc[4], 0)

    def test_load_state_continents_majority(self):
        from continents import load_state_continents
        mod, states = self._make_env()
        sd = _FakeStateData(states, mod_path=mod)
        sc = load_state_continents(sd)
        self.assertEqual(sc[1], "europe")   # 2 欧 vs 1 亚，水域过滤
        self.assertIsNone(sc.get(99))

    def test_state_continent_overlay(self):
        from continents import load_state_continents, state_continent_overlay
        mod, states = self._make_env()
        sd = _FakeStateData(states, mod_path=mod)
        sc = load_state_continents(sd)
        ov = state_continent_overlay(sd, sc)
        self.assertEqual(ov[1], 1)
        self.assertEqual(ov[2], 1)
        self.assertEqual(ov[3], 1, "州多数表决为欧洲，故省3随州归欧洲")
        self.assertEqual(ov[4], 1, "水域省随州归欧洲（叠加层用州色）")

    def test_province_meta_column_fix(self):
        """_province_meta 列错位修复：type=第4列、coastal=第5列。"""
        from api_core_ext.states import StatesMixin
        mod, _ = self._make_env()
        obj = StatesMixin()
        obj.mod_path = mod
        obj.game_path = ""
        r = obj._province_meta(1)
        self.assertEqual(r["type"], "land")
        self.assertTrue(r["coastal"])
        r3 = obj._province_meta(3)
        self.assertEqual(r3["type"], "land")
        self.assertFalse(r3["coastal"])


if __name__ == "__main__":
    unittest.main()

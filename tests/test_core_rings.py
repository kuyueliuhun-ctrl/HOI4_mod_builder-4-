"""核心圈层（P1 方案 B）测试：add_core_of 解析 / 州邻接 / BFS 分层 / 叠加。"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


def _mkdtemp(prefix):
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


class StateCoresParseTest(unittest.TestCase):
    def test_add_core_of_parsed(self):
        from state_loader import StateData
        mod = _mkdtemp("core_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "history", "states")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "1.txt"), "w", encoding="utf-8") as f:
            f.write("state = {\n\tid = 1\n\tname = \"STATE_1\"\n"
                    "\thistory = {\n\t\towner = GER\n"
                    "\t\tadd_core_of = GER\n\t\tadd_core_of = FRA\n\t}\n"
                    "\tprovinces = { 100 }\n}\n")
        sd = StateData(mod, "")
        info = sd.states[1]
        self.assertEqual(sorted(info["cores"]), ["FRA", "GER"])
        self.assertEqual(sd.cores_by_tag["GER"], {1})
        self.assertEqual(sd.cores_by_tag["FRA"], {1})


class _FakeMapData:
    def __init__(self, id_map, province_table):
        self.id_map = id_map
        self.province_table = province_table


class _FakeStateData:
    def __init__(self, states, p2s, cores_by_tag=None):
        self.states = states
        self.province_to_state = p2s
        self.cores_by_tag = cores_by_tag or {}


class CoreRingsTest(unittest.TestCase):
    def _env(self):
        # 1-2 与 2-3 陆地相邻；4 为海
        id_map = np.array([
            [1, 1, 2],
            [1, 2, 2],
            [3, 3, 4],
        ], dtype=np.int32)
        ptab = {1: {"type": "land"}, 2: {"type": "land"},
                3: {"type": "land"}, 4: {"type": "sea"}}
        p2s = {1: 10, 2: 20, 3: 30, 4: 40}
        states = {10: {"provinces": [1]}, 20: {"provinces": [2]},
                  30: {"provinces": [3]}, 40: {"provinces": [4]}}
        md = _FakeMapData(id_map, ptab)
        sd = _FakeStateData(states, p2s,
                            cores_by_tag={"GER": {10}})
        return md, sd

    def test_build_state_adjacency(self):
        from core_rings import build_state_adjacency
        md, sd = self._env()
        adj = build_state_adjacency(md, sd)
        self.assertEqual(adj[10], {20, 30})  # 1-2 水平、1-3 垂直
        self.assertEqual(adj[20], {10, 30})
        self.assertEqual(adj[30], {10, 20})
        self.assertNotIn(40, adj, "海省不参与邻接")

    def test_compute_core_rings(self):
        from core_rings import build_state_adjacency, compute_core_rings
        md, sd = self._env()
        adj = build_state_adjacency(md, sd)
        rings = compute_core_rings("GER", sd.cores_by_tag, adj, max_ring=6)
        self.assertEqual(rings.get(10), 0)
        self.assertEqual(rings.get(20), 1)
        self.assertEqual(rings.get(30), 1)
        # 无核心国 → {}
        self.assertEqual(compute_core_rings("NOPE", sd.cores_by_tag, adj), {})

    def test_core_ring_overlay(self):
        from core_rings import build_state_adjacency, compute_core_rings, \
            core_ring_overlay
        md, sd = self._env()
        adj = build_state_adjacency(md, sd)
        rings = compute_core_rings("GER", sd.cores_by_tag, adj)
        ov = core_ring_overlay(sd, rings)
        self.assertEqual(ov[1], 0)
        self.assertEqual(ov[2], 1)
        self.assertEqual(ov[3], 1)


if __name__ == "__main__":
    unittest.main()

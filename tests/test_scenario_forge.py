"""Scenario Forge 移植后端测试：build_snapshot 溯源台账 + high_risk_ids 高危清单。"""

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


class BuildSnapshotTest(unittest.TestCase):
    def _make_mod(self):
        mod = _mkdtemp("snap_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "common", "national_focus")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "ger.txt"), "w", encoding="utf-8") as f:
            f.write("focus_tree = {\n\tfocus = { id = a }\n}\n")
        return mod

    def test_build_and_diff(self):
        from build_snapshot import build_snapshot, diff_snapshots
        mod = self._make_mod()
        snap1 = build_snapshot(mod, "")
        self.assertGreater(snap1["count"], 0)
        rel = "common/national_focus/ger.txt"
        self.assertIn(rel, snap1["files"])
        self.assertEqual(snap1["files"][rel]["source"], "new")
        # 修改文件 → changed
        with open(os.path.join(mod, *rel.split("/")), "w",
                  encoding="utf-8") as f:
            f.write("focus_tree = {\n\tfocus = { id = b }\n}\n")
        snap2 = build_snapshot(mod, "")
        d = diff_snapshots(snap1, snap2)
        self.assertIn(rel, d["changed"])
        self.assertEqual(d["unchanged"], snap1["count"] - 1)

    def test_source_override(self):
        from build_snapshot import build_snapshot
        mod = self._make_mod()
        game = _mkdtemp("snap_game_")
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        d = os.path.join(game, "common", "national_focus")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "ger.txt"), "w", encoding="utf-8") as f:
            f.write("x")
        snap = build_snapshot(mod, game)
        self.assertEqual(
            snap["files"]["common/national_focus/ger.txt"]["source"],
            "override")

    def test_save_load(self):
        from build_snapshot import build_snapshot, save_snapshot, load_snapshot
        mod = self._make_mod()
        snap = build_snapshot(mod, "")
        p = os.path.join(_mkdtemp("snap_out_"), "snap.json")
        save_snapshot(snap, p)
        loaded = load_snapshot(p)
        self.assertEqual(loaded["count"], snap["count"])
        self.assertEqual(loaded["files"], snap["files"])


class HighRiskIdsTest(unittest.TestCase):
    def _make(self):
        mod = _mkdtemp("hr_mod_")
        game = _mkdtemp("hr_game_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        for root in (mod, game):
            d = os.path.join(root, "common", "national_focus")
            os.makedirs(d, exist_ok=True)
        # mod：与 vanilla 撞 id + 保留字 id + 正常 id
        with open(os.path.join(mod, "common", "national_focus", "x.txt"),
                  "w", encoding="utf-8") as f:
            f.write("focus_tree = {\n"
                    "\tfocus = { id = collision_id }\n"
                    "\tfocus = { id = root }\n"
                    "\tfocus = { id = normal_id }\n"
                    "}\n")
        with open(os.path.join(game, "common", "national_focus", "x.txt"),
                  "w", encoding="utf-8") as f:
            f.write("focus_tree = {\n\tfocus = { id = collision_id }\n}\n")
        return mod, game

    def test_high_risk_ids(self):
        from high_risk_ids import high_risk_ids
        mod, game = self._make()
        risks = high_risk_ids(mod, game)
        reasons = {r["reason"] for r in risks}
        self.assertTrue(any("覆盖风险" in r for r in reasons))
        self.assertTrue(any("保留字" in r for r in reasons))
        by_id = {r["id"]: r for r in risks}
        self.assertIn("collision_id", by_id)
        self.assertIn("root", by_id)
        self.assertNotIn("normal_id", by_id)

    def test_export_health_includes_high_risk(self):
        from export_health import run_export_health_check
        mod, game = self._make()
        report = run_export_health_check(mod, game)
        high = [i for i in report.issues
                if i.category == "high_risk" and i.severity == "warning"]
        ids = {i.message.split("：", 1)[1].split(" — ")[0] for i in high}
        self.assertIn("collision_id", ids)
        self.assertIn("root", ids)


if __name__ == "__main__":
    unittest.main()

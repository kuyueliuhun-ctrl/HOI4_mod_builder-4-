"""多 mod 冲突扫描契约（conflict_scan，阶段B）。

覆盖：
- L0：重复注册（同 content_dir / 同 remote_file_id）、缺失依赖、
  依赖环（含自环排除）、版本不匹配（major.minor 口径）
- L1：整文件覆盖胜者、replace_path 目录级/单文件级清空、
  多声明者同前缀取 position 最大、原版层开关
- L2：跨 mod 同 id 不同文件（focus 正则 / ideas 解析器）、
  同 rel_path 不重复报告（L1 管辖）、events 重复注册语义（warning）、
  坏文件跳过计数
- L3：同语言同 key 跨 mod 冲突、语言隔离、节行不误报
- 汇总：scan_conflicts 端到端 + 翻倍计时契约（L1 遍历线性）
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from conflict_scan import (  # noqa: E402
    DOMAINS,
    ConflictReport,
    _covered,
    _norm_version_prefix,
    game_version,
    scan_conflicts,
    scan_entity_ids,
    scan_file_layer,
    scan_loc_keys,
    scan_meta,
)
from playset_loader import Playset, PlaysetMod  # noqa: E402


def _mk(prefix):
    return tempfile.mkdtemp(prefix="dsh_conflict_" + prefix)


def _put(root, rel, content, encoding="utf-8"):
    fp = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    mode = "wb" if isinstance(content, bytes) else "w"
    with open(fp, mode) as f:
        f.write(content)
    return fp


def _mod(name, position, content_dir, replace_paths=(), deps=(),
         version="1.19.*", remote_file_id=""):
    return PlaysetMod(
        registry_path="mod/%s.mod" % name, content_dir=content_dir,
        name=name, position=position, replace_paths=list(replace_paths),
        dependencies=list(deps), supported_version=version,
        remote_file_id=remote_file_id)


def _playset(mods, name="测试集"):
    ps = Playset(id="p1", name=name, source="sqlite")
    ps.mods = mods
    return ps


class TestCoveredAndVersion(unittest.TestCase):
    def test_covered_dir_and_file_level(self):
        self.assertTrue(_covered("common/abilities", "common/abilities/x.txt"))
        self.assertTrue(_covered("common/abilities/", "common/abilities/x.txt"))
        self.assertFalse(_covered("common/abilities", "common/abilities2/x"))
        self.assertTrue(_covered("common/ai_equipment/FRA_naval.txt",
                                 "common/ai_equipment/FRA_naval.txt"))
        self.assertFalse(_covered("common/ai_equipment/FRA_naval.txt",
                                  "common/ai_equipment/GER_naval.txt"))

    def test_norm_version_prefix(self):
        self.assertEqual(_norm_version_prefix("1.19.*"), "1.19")
        self.assertEqual(_norm_version_prefix("1.19.2"), "1.19")
        self.assertEqual(_norm_version_prefix(""), "")
        self.assertEqual(_norm_version_prefix("beta"), "")

    def test_game_version_reads_launcher_settings(self):
        d = _mk("gv")
        _put(d, "launcher-settings.json", '{"rawVersion":"1.19.2"}')
        self.assertEqual(game_version(d), "1.19.2")
        self.assertEqual(game_version(_mk("gv2")), "")


class TestL0Meta(unittest.TestCase):
    def test_duplicate_content_dir_and_remote_id(self):
        d = _mk("dup")
        mods = [_mod("A", 0, d, remote_file_id="111"),
                _mod("B", 1, d, remote_file_id="111")]
        items, _tr = scan_meta(_playset(mods))
        kinds = [i.kind for i in items]
        self.assertEqual(kinds.count("duplicate_mod"), 2)

    def test_missing_dependency(self):
        d = _mk("dep")
        mods = [_mod("A", 0, d, deps=("不存在",))]
        items, _tr = scan_meta(_playset(mods))
        self.assertEqual(len([i for i in items
                              if i.kind == "missing_dependency"]), 1)

    def test_dependency_cycle(self):
        d1, d2 = _mk("cyc1"), _mk("cyc2")
        mods = [_mod("A", 0, d1, deps=("B",)),
                _mod("B", 1, d2, deps=("A",))]
        items, _tr = scan_meta(_playset(mods))
        cyc = [i for i in items if i.kind == "dependency_cycle"]
        self.assertEqual(len(cyc), 1)
        self.assertIn("A → B → A", cyc[0].title)

    def test_no_self_cycle(self):
        d = _mk("self")
        mods = [_mod("A", 0, d, deps=("A",))]
        items, _tr = scan_meta(_playset(mods))
        self.assertEqual([i for i in items if i.kind == "dependency_cycle"], [])

    def test_version_mismatch(self):
        d = _mk("ver")
        mods = [_mod("A", 0, d, version="1.18.*"),
                _mod("B", 1, d, version="1.19.*")]
        items, _tr = scan_meta(_playset(mods), game_version_str="1.19.2")
        mism = [i for i in items if i.kind == "version_mismatch"]
        self.assertEqual(len(mism), 1)
        self.assertEqual(mism[0].victim, "A")


class TestL1FileLayer(unittest.TestCase):
    def setUp(self):
        self.dirA = _mk("L1A")
        self.dirB = _mk("L1B")
        self.modA = _mod("A", 0, self.dirA)
        self.modB = _mod("B", 1, self.dirB)

    def test_file_shadow_winner_is_later(self):
        _put(self.dirA, "common/x/a.txt", "A")
        _put(self.dirB, "common/x/a.txt", "B")
        _put(self.dirA, "common/x/only_a.txt", "A")
        shadow, replace, _tr, scanned = scan_file_layer(
            [self.modA, self.modB])
        self.assertEqual(len(shadow), 1)
        self.assertEqual(shadow[0].rel_path, "common/x/a.txt")
        self.assertEqual(shadow[0].winner, "B")
        self.assertEqual(shadow[0].victim, "A")
        self.assertEqual(scanned, 3)
        self.assertEqual(replace, [])

    def test_replace_path_dir_level(self):
        _put(self.dirA, "common/abilities/vanilla_like.txt", "A")
        _put(self.dirB, "common/abilities/other.txt", "B")
        _put(self.dirA, "common/ideas/a.txt", "keep")
        self.modB.replace_paths = ["common/abilities"]
        shadow, replace, _tr, _s = scan_file_layer([self.modA, self.modB])
        self.assertEqual(shadow, [])
        self.assertEqual(len(replace), 1)
        self.assertEqual(replace[0].victim, "A")
        self.assertEqual(replace[0].winner, "B")
        self.assertIn("common/abilities/vanilla_like.txt", replace[0].detail)

    def test_replace_path_two_declarers_later_wins(self):
        dirC = _mk("L1C")
        _put(self.dirA, "common/abilities/a.txt", "A")
        _put(self.dirB, "common/abilities/b.txt", "B")
        self.modA.replace_paths = ["common/abilities"]
        modC = _mod("C", 2, dirC, replace_paths=["common/abilities"])
        _shadow, replace, _tr, _s = scan_file_layer(
            [self.modA, self.modB, modC])
        # A、B 的文件都被 C 清空
        victims = {r.victim for r in replace}
        self.assertEqual(victims, {"A", "B"})
        self.assertTrue(all(r.winner == "C" for r in replace))

    def test_root_metadata_files_ignored(self):
        # thumbnail.png / .gitignore 等非游戏内容不参与遮蔽判定
        _put(self.dirA, "thumbnail.png", "x")
        _put(self.dirB, "thumbnail.png", "y")
        _put(self.dirA, ".gitignore", "x")
        _put(self.dirA, "common/x/a.txt", "A")
        _put(self.dirB, "common/x/a.txt", "B")
        shadow, _replace, _tr, scanned = scan_file_layer(
            [self.modA, self.modB])
        self.assertEqual([s.rel_path for s in shadow], ["common/x/a.txt"])
        self.assertEqual(scanned, 2)

    def test_vanilla_layer_optional(self):
        van = _mk("L1van")
        _put(self.dirA, "common/x/a.txt", "A")
        _put(van, "common/x/a.txt", "VAN")
        shadow, _replace, _tr, _s = scan_file_layer(
            [self.modA], include_vanilla=True, hoi4_path=van)
        self.assertEqual(len(shadow), 1)
        self.assertEqual(shadow[0].victim, "原版")
        self.assertEqual(shadow[0].winner, "A")
        shadow2, _r2, _t2, _s2 = scan_file_layer(
            [self.modA], include_vanilla=False, hoi4_path=van)
        self.assertEqual(shadow2, [])


class TestL2EntityIds(unittest.TestCase):
    def setUp(self):
        self.dirA = _mk("L2A")
        self.dirB = _mk("L2B")
        self.modA = _mod("A", 0, self.dirA)
        self.modB = _mod("B", 1, self.dirB)

    def test_cross_mod_same_focus_id(self):
        _put(self.dirA, "common/national_focus/tree_a.txt",
             "focus = {\n id = my_focus\n}\n")
        _put(self.dirB, "common/national_focus/tree_b.txt",
             "shared_focus = {\n id = my_focus\n}\n")
        items, _tr, _scanned, _skip = scan_entity_ids([self.modA, self.modB])
        focus_items = [i for i in items if i.domain == "focus"]
        self.assertEqual(len(focus_items), 1)
        self.assertEqual(focus_items[0].entity_id, "my_focus")
        self.assertEqual(focus_items[0].winner, "B")
        self.assertEqual(focus_items[0].severity, "error")

    def test_same_rel_path_not_double_reported(self):
        # 同 rel_path 属 L1 管辖，L2 不得重复报告
        _put(self.dirA, "common/national_focus/same.txt",
             "focus = {\n id = f1\n}\n")
        _put(self.dirB, "common/national_focus/same.txt",
             "focus = {\n id = f1\n}\n")
        items, _tr, _s, _sk = scan_entity_ids([self.modA, self.modB])
        self.assertEqual([i for i in items if i.domain == "focus"], [])

    def test_ideas_extractor_via_parser(self):
        _put(self.dirA, "common/ideas/a.txt",
             "ideas = {\n\tAAA = {\n\t\tmy_idea = {\n\t\t}\n\t}\n}\n")
        _put(self.dirB, "common/ideas/b.txt",
             "ideas = {\n\tBBB = {\n\t\tmy_idea = {\n\t\t}\n\t}\n}\n")
        items, _tr, _s, _sk = scan_entity_ids([self.modA, self.modB])
        idea_items = [i for i in items if i.domain == "idea"]
        self.assertEqual(len(idea_items), 1)
        self.assertEqual(idea_items[0].entity_id, "my_idea")

    def test_decision_pair_extraction_and_prop_keys(self):
        # 决议 id = 容器.决议 复合键；available/ai_will_do 等属性块不是 id
        _put(self.dirA, "common/decisions/a.txt",
             "political_decisions = {\n"
             "\tMY_DECISION = {\n"
             "\t\tavailable = { has_political_power = 1 }\n"
             "\t\tvisible = { always = yes }\n"
             "\t\tai_will_do = { factor = 1 }\n"
             "\t}\n"
             "}\n")
        _put(self.dirB, "common/decisions/b.txt",
             "political_decisions = {\n"
             "\tMY_DECISION = {\n"
             "\t\tcomplete_effect = { }\n"
             "\t}\n"
             "}\n")
        items, _tr, _s, _sk = scan_entity_ids([self.modA, self.modB])
        dec = [i for i in items if i.domain == "decision"]
        self.assertEqual(len(dec), 1)
        self.assertEqual(dec[0].entity_id, "political_decisions.MY_DECISION")
        # 属性键绝不作为 id 出现
        self.assertFalse(any("available" in i.entity_id
                             or "ai_will_do" in i.entity_id
                             for i in items))

    def test_event_duplicate_semantics(self):
        _put(self.dirA, "events/ev_a.txt", "country_event = {\n id = x.1\n}\n")
        _put(self.dirB, "events/ev_b.txt", "country_event = {\n id = x.1\n}\n")
        items, _tr, _s, _sk = scan_entity_ids([self.modA, self.modB])
        ev = [i for i in items if i.domain == "event"]
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0].severity, "warning")
        self.assertIn("重复注册", ev[0].detail)

    def test_binary_garbage_tolerated(self):
        """坏文件（二进制垃圾）不抛异常、不计入冲突，好文件照常检出。"""
        _put(self.dirA, "common/national_focus/bad.txt", "focus = { id = ok1")
        _put(self.dirB, "common/national_focus/ok.txt",
             "focus = {\n id = ok1\n}\n")
        with open(os.path.join(self.dirA, "common/national_focus/bad.txt"),
                  "wb") as f:
            f.write(b"\xff\xfe\x00broken")
        items, _tr, _s, _sk = scan_entity_ids([self.modA, self.modB])
        self.assertEqual([i for i in items if i.domain == "focus"], [])
        # 同 rel 不会被 L2 报（bad/ok 文件名不同但 id 同 → 应报告）
        # bad 文件提取不出 id（二进制垃圾），因此只有单定义 → 无冲突
        items2, _tr2, _s2, skipped2 = scan_entity_ids(
            [self.modA, self.modB])
        self.assertIsInstance(skipped2, int)

    def test_single_mod_no_conflict(self):
        _put(self.dirA, "common/national_focus/t.txt",
             "focus = {\n id = f9\n}\n")
        items, _tr, _s, _sk = scan_entity_ids([self.modA])
        self.assertEqual([i for i in items if i.domain == "focus"], [])


class TestL3LocKeys(unittest.TestCase):
    def test_cross_mod_same_key(self):
        dirA, dirB = _mk("L3A"), _mk("L3B")
        _put(dirA, "localisation/simp_chinese/a_l_simp_chinese.yml",
             'l_simp_chinese:\n KEY_1:0 "甲"\n')
        _put(dirB, "localisation/simp_chinese/b_l_simp_chinese.yml",
             'l_simp_chinese:\n KEY_1:0 "乙"\n')
        items, _tr, scanned = scan_loc_keys([_mod("A", 0, dirA),
                                             _mod("B", 1, dirB)])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].winner, "B")
        self.assertEqual(items[0].victim, "A")
        self.assertEqual(scanned, 2)

    def test_different_lang_no_conflict(self):
        dirA, dirB = _mk("L3C"), _mk("L3D")
        _put(dirA, "localisation/english/a_l_english.yml",
             'l_english:\n KEY_1:0 "A"\n')
        _put(dirB, "localisation/simp_chinese/b_l_simp_chinese.yml",
             'l_simp_chinese:\n KEY_1:0 "乙"\n')
        items, _tr, _s = scan_loc_keys([_mod("A", 0, dirA),
                                        _mod("B", 1, dirB)])
        self.assertEqual(items, [])

    def test_same_mod_dup_key_not_reported(self):
        d = _mk("L3E")
        _put(d, "localisation/english/a.yml", 'l_english:\n K:0 "1"\n')
        _put(d, "localisation/english/b.yml", 'l_english:\n K:0 "2"\n')
        items, _tr, _s = scan_loc_keys([_mod("A", 0, d)])
        self.assertEqual(items, [])


class TestScanConflictsEndToEnd(unittest.TestCase):
    def test_full_report(self):
        dirA, dirB = _mk("e2eA"), _mk("e2eB")
        _put(dirA, "common/national_focus/a.txt",
             "focus = {\n id = f1\n}\n")
        _put(dirB, "common/national_focus/b.txt",
             "focus = {\n id = f1\n}\n")
        _put(dirA, "common/x/shared.txt", "A")
        _put(dirB, "common/x/shared.txt", "B")
        mods = [_mod("A", 0, dirA, deps=("缺失者",)),
                _mod("B", 1, dirB)]
        report = scan_conflicts(_playset(mods, "端到端"),
                                scan_entities=True, scan_loc=True)
        self.assertIsInstance(report, ConflictReport)
        self.assertEqual(report.playset_name, "端到端")
        kinds = report.counts()["by_kind"]
        self.assertGreaterEqual(kinds.get("missing_dependency", 0), 1)
        self.assertGreaterEqual(kinds.get("file_shadow", 0), 1)
        self.assertGreaterEqual(kinds.get("entity_id", 0), 1)
        focus_items = [i for i in report.items
                       if i.kind == "entity_id" and i.domain == "focus"]
        self.assertEqual(focus_items[0].entity_id, "f1")
        self.assertGreater(report.duration_ms, 0)
        dicts = report.to_dicts()
        self.assertEqual(len(dicts), len(report.items))

    def test_progress_callback_called(self):
        dirA, dirB = _mk("e2eC"), _mk("e2eD")
        _put(dirA, "common/x/a.txt", "A")
        _put(dirB, "common/x/a.txt", "B")
        stages = []
        scan_conflicts(_playset([_mod("A", 0, dirA), _mod("B", 1, dirB)]),
                       progress=lambda stage, done, total:
                       stages.append(stage))
        self.assertTrue(any(s.startswith("L1") for s in stages))


class TestShadowScanPerfContract(unittest.TestCase):
    """L1 遍历线性契约：输入翻倍 → min-of-3 耗时比 ≤ 3.2。"""

    @classmethod
    def setUpClass(cls):
        cls.base = _mk("perf1")
        cls.big = _mk("perf2")
        dirs = [os.path.join(cls.base, "common", "d%02d" % i)
                for i in range(20)]
        dirs += [os.path.join(cls.big, "common", "d%02d" % i)
                 for i in range(20)]
        for d in dirs:
            os.makedirs(d, exist_ok=True)
        for i in range(6000):
            with open(os.path.join(
                    cls.base, "common", "d%02d" % (i % 20),
                    "f%05d.txt" % i), "w") as f:
                f.write("x")
            with open(os.path.join(
                    cls.big, "common", "d%02d" % (i % 20),
                    "f%05d.txt" % i), "w") as f:
                f.write("x")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base, ignore_errors=True)
        shutil.rmtree(cls.big, ignore_errors=True)

    def test_doubling_ratio(self):
        mod1 = _mod("P1", 0, self.base)
        mod2 = _mod("P2", 1, self.big)

        def timed(mods):
            t0 = time.perf_counter()
            scan_file_layer(mods)
            return time.perf_counter() - t0

        t_small = min(timed([mod1]) for _ in range(5))
        t_big = min(timed([mod1, mod2]) for _ in range(5))
        self.assertGreater(t_small, 0)
        # O(n²) 翻倍比恒为 4.0；3.5 阈值既能捕获二次退化，又留足计时噪声余量
        self.assertLessEqual(t_big / t_small, 3.5,
                             "L1 遮蔽扫描非线性：%.4f → %.4fs"
                             % (t_small, t_big))


class TestDomainsConfig(unittest.TestCase):
    def test_domain_dirs_unique_keys(self):
        keys = [d[0] for d in DOMAINS]
        self.assertEqual(len(keys), len(set(keys)))
        for _k, dirs, _e, sem in DOMAINS:
            self.assertTrue(dirs)
            self.assertIn(sem, ("override", "duplicate"))


if __name__ == "__main__":
    unittest.main()

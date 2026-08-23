"""契约测试：原子写 / 写入契约 / 导出前健康检查 / 写入纪律扫描

运行：
    python -m unittest discover -s tests -v
    （或 python tools/verify_contracts.py 一键运行全部契约）
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
SRC = os.path.join(PROJECT_ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def _mkdtemp(prefix):
    """工作区内临时目录（沙箱不允许写系统 %TEMP%）。

    契约测试统一在这里建临时目录，测试结束时由 addCleanup 清理。
    """
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


class HealthCheckTest(unittest.TestCase):
    """export_health 导出前健康检查契约。"""

    def setUp(self):
        self.tmp = _mkdtemp("dsh_health_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _write(self, rel, content, mode="w"):
        fp = os.path.join(self.tmp, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, mode, encoding="utf-8", newline="") as f:
            f.write(content)
        return fp

    def _check(self):
        from export_health import run_export_health_check
        return run_export_health_check(self.tmp)

    def _sev(self, report, severity, category=None):
        return [i for i in report.issues
                if i.severity == severity
                and (category is None or i.category == category)]

    def test_clean_mod_no_errors(self):
        self._write("descriptor.mod", 'name = "Test"\npath = "test"\n')
        os.makedirs(os.path.join(self.tmp, "test"), exist_ok=True)
        self._write("common/national_focus/test.txt",
                    "focus_tree = {\n\tcountry = {\n\t\tfocus = {\n\t\t\tid = A_1\n\t\t}\n\t}\n}\n")
        report = self._check()
        self.assertEqual(report.counts["error"], 0,
                         "干净 mod 不应有 error：%s" % [i.message for i in report.issues])

    def test_missing_descriptor_is_error(self):
        report = self._check()
        self.assertTrue(self._sev(report, "error", "descriptor"))

    def test_unbalanced_braces_is_error(self):
        self._write("descriptor.mod", 'name = "T"\n')
        self._write("common/national_focus/bad.txt",
                    "focus_tree = {\n\tcountry = {\n\t\tfocus = {\n\t\t\tid = A\n")
        report = self._check()
        self.assertTrue(self._sev(report, "error", "syntax"))

    def test_bom_warning(self):
        self._write("descriptor.mod", 'name = "T"\n')
        with open(os.path.join(self.tmp, "bom.txt"), "wb") as f:
            f.write(b"\xef\xbb\xbfcontent")
        report = self._check()
        self.assertTrue(self._sev(report, "warning", "encoding"))

    def test_gfx_texture_missing_is_error(self):
        self._write("descriptor.mod", 'name = "T"\n')
        self._write("interface/test.gfx",
                    'spriteTypes = {\n\tspriteType = {\n\t\tname = "GFX_test"\n'
                    '\t\ttexturefile = "gfx/interface/missing.png"\n\t}\n}\n')
        report = self._check()
        self.assertTrue(self._sev(report, "error", "reference"))

    def test_gfx_texture_present_passes(self):
        self._write("descriptor.mod", 'name = "T"\n')
        self._write("gfx/interface/ok.png", "not-really-png")
        self._write("interface/test.gfx",
                    'spriteTypes = {\n\tspriteType = {\n\t\tname = "GFX_test"\n'
                    '\t\ttexturefile = "gfx/interface/ok.png"\n\t}\n}\n')
        report = self._check()
        self.assertEqual(self._sev(report, "error", "reference"), [])

    def test_duplicate_focus_id_is_error(self):
        self._write("descriptor.mod", 'name = "T"\n')
        self._write("common/national_focus/dup.txt",
                    "focus_tree = {\n\tcountry = {\n\t\tfocus = {\n\t\t\tid = DUP_A\n\t\t}\n"
                    "\t\tfocus = {\n\t\t\tid = DUP_A\n\t\t}\n\t}\n}\n")
        report = self._check()
        self.assertTrue(self._sev(report, "error", "duplicate"))

    def test_duplicate_tech_id_is_error(self):
        self._write("descriptor.mod", 'name = "T"\n')
        self._write("common/technologies/dup.txt",
                    "technologies = {\n\ttech1 = {\n\t}\n\ttech1 = {\n\t}\n}\n")
        report = self._check()
        self.assertTrue(self._sev(report, "error", "duplicate"))


class WriteDisciplineScannerTest(unittest.TestCase):
    """tools/check_write_discipline.py 静态扫描契约。"""

    def setUp(self):
        self.tmp = _mkdtemp("dsh_discipline_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _write(self, rel, content):
        fp = os.path.join(self.tmp, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)

    def test_detects_direct_text_write(self):
        self._write("bad_mod.py",
                    "import os\n"
                    "def save(path, text):\n"
                    "    with open(path, 'w', encoding='utf-8') as f:\n"
                    "        f.write(text)\n")
        sys.path.insert(0, os.path.join(PROJECT_ROOT, "tools"))
        try:
            from check_write_discipline import scan_root
            violations, _reg, _bin, _checked = scan_root(self.tmp)
        finally:
            sys.path.remove(os.path.join(PROJECT_ROOT, "tools"))
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0][1], 3)  # open 调用所在行

    def test_binary_copy_is_not_violation(self):
        self._write("ok_mod.py",
                    "import shutil\n"
                    "shutil.copyfile('a.png', 'b.png')\n")
        sys.path.insert(0, os.path.join(PROJECT_ROOT, "tools"))
        try:
            from check_write_discipline import scan_root
            violations, _reg, binaries, _checked = scan_root(self.tmp)
        finally:
            sys.path.remove(os.path.join(PROJECT_ROOT, "tools"))
        self.assertEqual(violations, [])
        self.assertEqual(len(binaries), 1)


class OverlayRulesTest(unittest.TestCase):
    """overlay_rules 规则分层 + delta 增量报告契约。"""

    def _setup(self):
        mod = _mkdtemp("dsh_ovl_mod_")
        game = _mkdtemp("dsh_ovl_game_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        for base in (mod, game):
            os.makedirs(os.path.join(base, "common", "decisions"),
                        exist_ok=True)
        return mod, game

    def test_classify_kinds(self):
        from overlay_rules import classify_override
        mod, game = self._setup()
        # identical（字节一致）
        for base in (mod, game):
            with open(os.path.join(base, "common", "decisions", "a.txt"),
                      "w", encoding="utf-8") as f:
                f.write("x = 1\n")
        e1 = classify_override("common/decisions/a.txt",
                               os.path.join(mod, "common", "decisions",
                                            "a.txt"),
                               os.path.join(game, "common", "decisions",
                                            "a.txt"))
        self.assertEqual(e1["kind"], "identical")
        self.assertEqual(e1["quality"], "direct_copy")
        # override（内容不同 + 行级增量）
        with open(os.path.join(mod, "common", "decisions", "a.txt"),
                  "w", encoding="utf-8") as f:
            f.write("x = 1\ny = 2\n")
        e2 = classify_override("common/decisions/a.txt",
                               os.path.join(mod, "common", "decisions",
                                            "a.txt"),
                               os.path.join(game, "common", "decisions",
                                            "a.txt"))
        self.assertEqual(e2["kind"], "override")
        self.assertEqual(e2["delta"]["added"], 1)
        # new（游戏无对应文件）
        new_abs = os.path.join(mod, "common", "decisions", "new.txt")
        with open(new_abs, "w", encoding="utf-8") as f:
            f.write("n = 1\n")
        e3 = classify_override("common/decisions/new.txt", new_abs, None)
        self.assertEqual(e3["kind"], "new")

    def test_quality_grading(self):
        from overlay_rules import _quality_of
        self.assertEqual(_quality_of("identical", 10, "a", "a"),
                         "direct_copy")
        self.assertEqual(_quality_of("new", 10, None, "x"), "manual_reviewed")
        # 高度相似 → approx（9 行相同 + 1 行新增 → ratio 0.947）
        game9 = "".join("line%d = %d\n" % (i, i) for i in range(9))
        mod10 = game9 + "extra = 1\n"
        self.assertEqual(_quality_of("override", 100, game9, mod10),
                         "approx")
        # 大体积低相似 → blocker
        big_new = "x = 1\n" * 20000
        self.assertEqual(_quality_of("override", 200 * 1024,
                                     "a = 1\n" * 100, big_new), "blocker")

    def test_build_report_and_write(self):
        from overlay_rules import (build_override_report,
                                   write_override_report)
        mod, game = self._setup()
        with open(os.path.join(game, "common", "decisions", "g.txt"),
                  "w", encoding="utf-8") as f:
            f.write("g = 1\n")
        with open(os.path.join(mod, "common", "decisions", "g.txt"),
                  "w", encoding="utf-8") as f:
            f.write("g = 2\nm = 3\n")
        os.makedirs(os.path.join(mod, "events"), exist_ok=True)
        with open(os.path.join(mod, "events", "e.txt"), "w",
                  encoding="utf-8") as f:
            f.write("e = {}\n")
        r = build_override_report(mod, game)
        rels = [e["rel"] for e in r["files"]]
        self.assertIn("common/decisions/g.txt", rels)
        self.assertIn("events/e.txt", rels)
        self.assertEqual(r["stats"]["new"], 1)
        self.assertEqual(r["stats"]["override"], 1)
        # 顶层非内容文件不纳入
        with open(os.path.join(mod, "notes.txt"), "w", encoding="utf-8") as f:
            f.write("n")
        r2 = build_override_report(mod, game)
        self.assertFalse(any(e["rel"] == "notes.txt" for e in r2["files"]))
        # 导出 JSON（原子写）
        out = os.path.join(mod, "report.json")
        write_override_report(mod, game, out)
        self.assertTrue(os.path.isfile(out))
        import json
        with open(out, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["stats"]["total"], 2)

    def test_rules_resolve_priority(self):
        from overlay_rules import OverlayRules
        rules = OverlayRules.load()
        layer, quality = rules.resolve("common/decisions/a.txt")
        self.assertEqual(layer.source, "mod")
        self.assertEqual(quality, "manual_reviewed")
        # 排除模式（*.bak）→ 回落只读层
        layer2, _q2 = rules.resolve("common/decisions/a.bak")
        self.assertEqual(layer2.source, "vanilla")


class IconManifestTest(unittest.TestCase):
    """icon_manifest 图标库清单契约。"""

    def _setup_gfx(self):
        from PIL import Image
        import numpy as np
        mod = _mkdtemp("dsh_im_mod_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        g = os.path.join(mod, "gfx", "interface")
        os.makedirs(g)
        with open(os.path.join(g, "icons.gfx"), "w", encoding="utf-8") as f:
            f.write('spriteType = { name = "GFX_ok" texturefile = '
                    '"gfx/interface/t.dds" }\n')
            f.write('spriteType = { name = "GFX_missing" texturefile = '
                    '"gfx/interface/nope.dds" }\n')
            f.write('spriteType = { name = "GFX_notexture" }\n')
        Image.fromarray(np.zeros((16, 16, 4), np.uint8)).save(
            os.path.join(g, "t.dds"))
        return mod

    def test_build_and_query(self):
        from icon_manifest import build_icon_manifest, IconManifest
        mod = self._setup_gfx()
        m = build_icon_manifest(mod, "")
        self.assertEqual(m["stats"]["total"], 2)
        im = IconManifest(m["entries"])
        e = im.get("GFX_ok")
        self.assertIsNotNone(e)
        self.assertEqual(e["missing"], False)
        self.assertEqual(e["size"], [16, 16])
        self.assertEqual(e["source"], "mod")
        self.assertTrue(im.get("GFX_missing")["missing"])
        self.assertIsNone(im.get("GFX_notexture"))
        self.assertEqual(len(im.search("GFX_")), 2)

    def test_vanilla_fallback_source(self):
        from PIL import Image
        import numpy as np
        from icon_manifest import build_icon_manifest
        mod = _mkdtemp("dsh_im_mod2_")
        game = _mkdtemp("dsh_im_game_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        os.makedirs(os.path.join(game, "gfx", "interface"))
        with open(os.path.join(game, "gfx", "interface", "v.gfx"),
                  "w", encoding="utf-8") as f:
            f.write('spriteType = { name = "GFX_van" texturefile = '
                    '"gfx/interface/v.dds" }\n')
        Image.fromarray(np.zeros((8, 8, 4), np.uint8)).save(
            os.path.join(game, "gfx", "interface", "v.dds"))
        m = build_icon_manifest(mod, game)
        e = next(x for x in m["entries"] if x["name"] == "GFX_van")
        self.assertEqual(e["source"], "vanilla")
        self.assertEqual(m["stats"]["sources"], {"vanilla": 1})

    def test_write_manifest(self):
        from icon_manifest import write_icon_manifest
        mod = self._setup_gfx()
        out = os.path.join(mod, "icon_manifest.json")
        write_icon_manifest(mod, "", out)
        self.assertTrue(os.path.isfile(out))
        import json
        with open(out, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["stats"]["total"], 2)
        self.assertEqual(len(data["entries"]), 2)


class UnitCounterLibraryTest(unittest.TestCase):
    """unit_counter_library 标牌库提取/加载契约。"""

    def _setup_game(self):
        from PIL import Image
        import numpy as np
        game = _mkdtemp("dsh_ucl_game_")
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        d1 = os.path.join(game, "gfx", "interface", "counters",
                          "divisions_small")
        d2 = os.path.join(game, "gfx", "interface", "counters",
                          "air_small")
        os.makedirs(d1)
        os.makedirs(d2)
        Image.fromarray(np.zeros((32, 32, 4), np.uint8)).save(
            os.path.join(d1, "onmap_infantry.dds"))
        Image.fromarray(np.zeros((24, 24, 4), np.uint8)).save(
            os.path.join(d2, "onmap_fighter.dds"))
        return game

    def test_import_and_load(self):
        from unit_counter_library import (import_unit_counter_library,
                                          UnitCounterLibrary)
        game = self._setup_game()
        out = _mkdtemp("dsh_ucl_out_")
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        r = import_unit_counter_library(game, out)
        self.assertEqual(r["total"], 2)
        self.assertEqual(r["skipped"], 0)
        self.assertEqual(sorted(r["categories"]),
                         ["air_small", "divisions_small"])
        lib = UnitCounterLibrary(out)
        self.assertTrue(lib.is_ready)
        self.assertEqual(sorted(lib.names),
                         ["onmap_fighter", "onmap_infantry"])
        e = lib.get("onmap_infantry")
        self.assertEqual(e["category"], "divisions_small")
        self.assertEqual(e["size"], [32, 32])
        self.assertTrue(os.path.isfile(lib.abs_path(e)))
        # 类别过滤
        self.assertEqual([x["name"] for x in lib.entries_in("air_small")],
                         ["onmap_fighter"])

    def test_empty_library_ready_false(self):
        from unit_counter_library import UnitCounterLibrary
        out = _mkdtemp("dsh_ucl_empty_")
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        lib = UnitCounterLibrary(out)
        self.assertFalse(lib.is_ready)
        self.assertEqual(lib.names, [])


class IconBatchTest(unittest.TestCase):
    """图标 GFX 批量注册。"""

    def setUp(self):
        self.tmp = _mkdtemp("icon_batch_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        os.makedirs(os.path.join(self.mod, "common", "national_focus"))
        os.makedirs(os.path.join(self.mod, "gfx", "interface", "goals"))
        os.makedirs(os.path.join(self.mod, "interface"))

    def _write_focus(self, icon_field):
        body = ("focus_tree = {\n id = TG_pj\n country = { factor = 0 }\n"
                " focus = { id = TG_a ICONFIELD\n}\n")
        body = body.replace("ICONFIELD", "icon = " + icon_field)
        with open(os.path.join(self.mod, "common", "national_focus", "f.txt"),
                  "w", encoding="utf-8") as f:
            f.write(body)

    def test_register_missing_registers_and_skips(self):
        from icon_batch import register_missing_gfx
        # 有贴图的图标应注册
        open(os.path.join(self.mod, "gfx", "interface", "goals", "GFX_goal_in.svg"), "w").close()
        open(os.path.join(self.mod, "gfx", "interface", "goals", "GFX_goal_have.dds"), "w").close()
        self._write_focus("GFX_goal_have")
        r = register_missing_gfx(self.mod, "common/national_focus/f.txt", "focus")
        self.assertEqual(r["registered"], 1)
        gfx = os.path.join(self.mod, "interface", "goals_mod.gfx")
        self.assertTrue(os.path.isfile(gfx))
        content = open(gfx, "r", encoding="utf-8").read()
        self.assertIn('name = "GFX_goal_have"', content)
        # 再次调用：已是已注册 → 不再写
        r2 = register_missing_gfx(self.mod, "common/national_focus/f.txt", "focus")
        self.assertEqual(r2["registered"], 0)

    def test_skip_when_no_texture(self):
        from icon_batch import register_missing_gfx
        self._write_focus("GFX_goal_missing")
        r = register_missing_gfx(self.mod, "common/national_focus/f.txt", "focus")
        self.assertEqual(r["registered"], 0)
        self.assertEqual(r["skipped_no_texture"], 1)


class ApiCoreToolTest(unittest.TestCase):
    """接口：第一批工具的 ApiCore 端点。"""

    def setUp(self):
        self.tmp = _mkdtemp("api_tools_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        os.makedirs(os.path.join(self.mod, "common", "national_focus"))
        os.makedirs(os.path.join(self.mod, "gfx", "interface", "goals"))
        os.makedirs(os.path.join(self.mod, "history", "states"))
        os.makedirs(os.path.join(self.mod, "localisation", "simp_chinese"))
        self.focus = os.path.join(self.mod, "common", "national_focus", "f.txt")
        with open(self.focus, "w", encoding="utf-8") as f:
            f.write("focus_tree = {\n id = TG_pj\n focus = { id = TG_a }\n}\n")
        with open(os.path.join(self.mod, "history", "states", "01.txt"),
                  "w", encoding="utf-8") as f:
            f.write("state = {\n\tid = 1\n\tvictory_points = { 10 2 }\n}\n")
        from api_server import ApiCore
        self.core = ApiCore(mod_path=self.mod, game_path="")
        # 建一个格式化用的临时文件（相对 mod）
        self.target_rel = "common/national_focus/ugly.txt"
        with open(os.path.join(self.mod, self.target_rel), "w", encoding="utf-8") as f:
            f.write("x = {\ny = 1\n}\n")

    def test_format_pdx(self):
        r = self.core.format_pdx({"path": self.target_rel})
        self.assertTrue(r["ok"])
        content = open(os.path.join(self.mod, self.target_rel), "r", encoding="utf-8").read()
        self.assertIn("\ty = 1", content)

    def test_vp_loc_dry_run(self):
        r = self.core.vp_loc_dry_run()
        self.assertTrue(r["ok"])
        self.assertGreaterEqual(r["count"], 1)
        self.assertIn("VICTORY_POINTS_10", r["text"])

    def test_register_icon_batch_and_error_log(self):
        # 图标：放一张贴图并引用它
        open(os.path.join(self.mod, "gfx", "interface", "goals", "GFX_g.dds"), "w").close()
        with open(self.focus, "w", encoding="utf-8") as f:
            f.write("focus_tree = {\n id = TG_pj\n"
                    " focus = { id = TG_a icon = GFX_g }\n}\n")
        r = self.core.register_icon_batch({"path": "common/national_focus/f.txt", "type": "focus"})
        self.assertEqual(r["registered"], 1)
        # 错误日志
        log = os.path.join(self.mod, "error.log")
        with open(log, "w", encoding="utf-8") as f:
            f.write("missing localisation for key X\n")
        r2 = self.core.analyze_error_log({"absolute_path": log})
        self.assertTrue(r2["ok"])
        self.assertIn("localisation", r2["subsystems"])


class McpRegistrationTest(unittest.TestCase):
    """MCP 补充计划：159 工具注册完整性。"""

    def setUp(self):
        self.tmp = _mkdtemp("mcp_reg_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        os.makedirs(self.mod)
        from api_server import ApiCore
        from mcp_tools import build_tools
        self.core = ApiCore(mod_path=self.mod, game_path="")
        self.tools = build_tools(self.core)

    def test_tool_count_and_unique(self):
        self.assertGreaterEqual(len(self.tools), 159)
        names = [t["name"] for t in self.tools]
        self.assertEqual(len(names), len(set(names)), "工具名必须全局唯一")

    def test_schema_valid(self):
        for t in self.tools:
            schema = t["inputSchema"]
            self.assertEqual(schema.get("type"), "object")
            self.assertIsInstance(schema.get("properties"), dict)
            self.assertTrue(callable(t["_handler"]), t["name"])

    def test_handlers_callable_with_missing_args_not_crash_unexpected(self):
        # 抽检：查询类工具空参不应抛非 ValueError（多数会因缺 mod/参数抛 ValueError 也接受）
        query_tools = [t for t in self.tools if "list_" in t["name"] or
                       t["name"] in ("get_status", "list_types", "validate_mod",
                                     "list_templates")]
        for t in query_tools[:20]:
            try:
                t["_handler"]({})
            except (ValueError, ImportError):
                pass
            except Exception as e:
                self.fail("%s 空参调用抛出非 ValueError: %s" % (t["name"], e))


class McpDomainSmokeTest(unittest.TestCase):
    """MCP 新增域核心冒烟（纯数据层，不依赖 PyQt）。"""

    def setUp(self):
        self.tmp = _mkdtemp("mcp_domain_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        os.makedirs(os.path.join(self.mod, "history", "states"))
        with open(os.path.join(self.mod, "history", "states", "1.txt"),
                  "w", encoding="utf-8") as f:
            f.write("state = {\n\tid = 1\n\tname = \"STATE_1\"\n"
                    "\tprovinces = { 10 11 }\n"
                    "\thistory = { owner = GER buildings = { infrastructure = 2 } }\n}\n")
        os.makedirs(os.path.join(self.mod, "common", "ai_strategy_plans"))
        with open(os.path.join(self.mod, "common", "ai_strategy_plans", "a.txt"),
                  "w", encoding="utf-8") as f:
            f.write("PLAN_A = {\n\tname = \"A\"\n}\n")
        os.makedirs(os.path.join(self.mod, "common", "bop"))
        with open(os.path.join(self.mod, "common", "bop", "ITA.txt"),
                  "w", encoding="utf-8") as f:
            f.write("ITA_bop = {\n\tinitial_value = 50\n"
                    "\tleft_side = fascism\n\tright_side = democracy\n"
                    "\tdecision_category = ITA_cat\n}\n")
        os.makedirs(os.path.join(self.mod, "history", "countries"))
        with open(os.path.join(self.mod, "history", "countries", "JAP.txt"),
                  "w", encoding="utf-8") as f:
            f.write("JAP = {\n}\n")
        from api_server import ApiCore
        self.core = ApiCore(mod_path=self.mod, game_path="")

    def test_states_roundtrip(self):
        r = self.core.list_states({})
        self.assertEqual(r["count"], 1)
        self.assertEqual(self.core.get_state({"state_id": 1})["state"]["owner"], "GER")
        self.core.set_state_owner({"state_id": 1, "tag": "FRA"})
        self.assertEqual(self.core.get_state({"state_id": 1})["state"]["owner"], "FRA")

    def test_ai_roundtrip(self):
        r = self.core.ai_plan_create({"id": "PLAN_B", "name": "B"})
        self.assertTrue(r["ok"])
        self.assertIn("PLAN_B", [x["id"] for x in self.core.ai_plan_list({})["items"]])
        r2 = self.core.ai_plan_rename({"id": "PLAN_B", "new": "PLAN_C"})
        self.assertTrue(r2["ok"])
        self.core.ai_plan_delete({"id": "PLAN_C"})
        ids = [x["id"] for x in self.core.ai_plan_list({})["items"]]
        self.assertNotIn("PLAN_C", ids)

    def test_bop_roundtrip(self):
        r = self.core.set_bop_initial_value({"bop_id": "ITA", "value": 80})
        self.assertTrue(r["ok"])
        self.assertEqual(self.core.get_bop({"bop_id": "ITA"})["bop"]["initial_value"], 80.0)

    def test_design_roundtrip(self):
        r = self.core.create_ship_design({
            "country": "JAP", "name": "Test", "hull": "ship_hull_light_1",
            "upgrades": {"engine": "e1"}})
        self.assertTrue(r["ok"])
        self.assertEqual(self.core.list_ship_designs({})["count"], 1)
        self.assertTrue(self.core.delete_ship_design(
            {"country": "JAP", "name": "Test"})["ok"])
        self.assertEqual(self.core.list_ship_designs({})["count"], 0)

    def test_generator_dry_run_no_write(self):
        before = set()
        for root, _dirs, files in os.walk(self.mod):
            for fn in files:
                before.add(os.path.relpath(os.path.join(root, fn), self.mod))
        r = self.core.generate_ideas({"ideas": [{"id": "x"}], "dry_run": True})
        self.assertTrue(r["dry_run"])
        after = set()
        for root, _dirs, files in os.walk(self.mod):
            for fn in files:
                after.add(os.path.relpath(os.path.join(root, fn), self.mod))
        self.assertEqual(before, after)

    def test_region_roundtrip(self):
        r = self.core.create_region({
            "kind": "strategic_region", "province_ids": [10, 11]})
        self.assertTrue(r["ok"])
        files = self.core.list_regions({"kind": "strategic_region"})["files"]
        self.assertEqual(files[0]["regions"][0]["provinces"], [10, 11])
        self.assertTrue(self.core.remove_region(
            {"kind": "strategic_region", "region_id": r["region_id"]})["ok"])

    def test_oob_copy_and_roundtrip(self):
        game = os.path.join(self.tmp, "game")
        os.makedirs(os.path.join(game, "history", "units"))
        with open(os.path.join(game, "history", "units", "army.txt"),
                  "w", encoding="utf-8") as f:
            f.write("division_template = {\n"
                    "\tname = \"Inf\"\n"
                    "\tregiments = { infantry = { x = 0 y = 0 } }\n"
                    "}\n")
        from api_server import ApiCore
        core = ApiCore(mod_path=self.mod, game_path=game)
        files = core.list_oob_files({})["files"]
        self.assertTrue(any(f["path"] == "history/units/army.txt" for f in files))
        r = core.list_division_templates({"path": "history/units/army.txt"})
        self.assertEqual(r["count"], 1)
        self.assertTrue(core.create_division_template(
            {"path": "history/units/army.txt", "name": "New",
             "units": [{"type": "infantry", "x": 0, "y": 1}]})["ok"])
        self.assertEqual(core.list_division_templates(
            {"path": "history/units/army.txt"})["count"], 2)
        self.assertTrue(core.delete_division_template(
            {"path": "history/units/army.txt", "name": "New"})["ok"])



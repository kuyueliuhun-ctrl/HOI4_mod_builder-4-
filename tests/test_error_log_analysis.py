# -*- coding: utf-8 -*-
"""6.94 崩溃分析内容补全：位置提取/落位/建议/去重 + 崩溃报告 + UI/MCP。

样例行全部取自真实 error.log（本机 2026-09-06 会话），覆盖引擎实际的
四种「文件:行号」形态与高频错误类型。
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
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


# ---- 真实 error.log 样例（逐字摘录） ----

SAMPLE_PAREN = ("[06:06:17][no_game_date][nationalfocus.cpp:642]: Missing icon "
                "shine for focus: GXC_the_japanese_visit "
                "(common/national_focus/TSR_lingguang_incident_joint_branch.txt:1 )")
SAMPLE_INLINE = ("[06:44:11][1940.07.26.20][state_effect_implementation.cpp:2054]: "
                 "common/national_focus/france.txt:3516: add_compliance "
                 "阿尔及利亚沙漠 does not have resistance")
SAMPLE_INFILE = ('[06:06:05][no_game_date][persistent.cpp:67]: Error: '
                 '"Unexpected token: thumbnail, near line: 6" in file: '
                 '"mod/ugc_3671805192.mod" near line: 6')
SAMPLE_FILELINE = ("[06:06:06][no_game_date][assetfactory_audio.cpp:467]: Could not "
                   "load sound file 'sound/menu/sfx_ui_sd_module_turrent_01.wav' "
                   "in  file: sound/sound.asset line: 730")
SAMPLE_ENGINE = ("[06:06:05][no_game_date][dlc.cpp:142]: incorrect checksum for DLC")
SAMPLE_GFX = ("[06:07:55][1936.01.01.12][equipment_group.cpp:70]: GFX key "
              "GFX_military_industrial_organization_convoy is missing "
              "(cannot represent 运输船)")
SAMPLE_SCOPE = ("[06:44:31][1940.07.28.19][eventtarget.cpp:336]: tried to use "
                "character BRA_candido_mariano as scope, but could not find this "
                "character in country FRA. Check that recruit_character was done "
                "before this.")
SAMPLE_ENTITY = ("[06:06:14][no_game_date][pdx_entity.cpp:2172]: Duplicate of "
                 "HOL_infantry_rider_entity added to entity system")


class LocationExtractTest(unittest.TestCase):
    """四种「文件:行号」形态的解析（真实样例）。"""

    def test_paren_suffix_shape(self):
        from error_log import extract_location
        loc = extract_location(SAMPLE_PAREN)
        self.assertEqual(loc["rel_path"],
                         "common/national_focus/TSR_lingguang_incident_joint_branch.txt")
        self.assertEqual(loc["line"], 1)

    def test_inline_prefix_shape(self):
        from error_log import extract_location
        loc = extract_location(SAMPLE_INLINE)
        self.assertEqual(loc["rel_path"], "common/national_focus/france.txt")
        self.assertEqual(loc["line"], 3516)

    def test_in_file_near_line_shape(self):
        from error_log import extract_location
        loc = extract_location(SAMPLE_INFILE)
        self.assertEqual(loc["rel_path"], "mod/ugc_3671805192.mod")
        self.assertEqual(loc["line"], 6)

    def test_file_line_shape(self):
        from error_log import extract_location
        loc = extract_location(SAMPLE_FILELINE)
        self.assertEqual(loc["rel_path"], "sound/sound.asset")
        self.assertEqual(loc["line"], 730)

    def test_engine_internal_not_extracted(self):
        from error_log import extract_location
        self.assertIsNone(extract_location(SAMPLE_ENGINE))
        self.assertIsNone(extract_location(
            "[xx][yy][equipment_group.cpp:70]: GFX key GFX_a is missing"))


class LocationResolveTest(unittest.TestCase):
    """相对路径 → 绝对落位（mod/游戏/用户mod目录/未找到）。"""

    def _layout(self):
        mod = _mkdtemp("errlog_mod_")
        game = _mkdtemp("errlog_game_")
        user = _mkdtemp("errlog_user_")
        os.makedirs(os.path.join(mod, "common", "national_focus"))
        os.makedirs(os.path.join(game, "sound"))
        os.makedirs(os.path.join(user, "mod"))
        with open(os.path.join(mod, "common", "national_focus", "a.txt"),
                  "w", encoding="utf-8") as f:
            f.write("focus = {\n}\n")
        with open(os.path.join(game, "sound", "sound.asset"),
                  "w", encoding="utf-8") as f:
            f.write("soundfiles = {\n}\n")
        with open(os.path.join(user, "mod", "ugc_3671805192.mod"),
                  "w", encoding="utf-8") as f:
            f.write('version="1"\n')
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        self.addCleanup(shutil.rmtree, user, ignore_errors=True)
        return mod, game, user

    def test_mod_hit(self):
        from error_log import resolve_location
        mod, game, user = self._layout()
        r = resolve_location({"rel_path": "common/national_focus/a.txt",
                              "line": 2},
                             mod_path=mod, hoi4_path=game, user_dir=user)
        self.assertEqual(r["source"], "mod")
        self.assertEqual(os.path.normpath(r["abs_path"]),
                         os.path.normpath(os.path.join(
                             mod, "common", "national_focus", "a.txt")))

    def test_game_hit_when_not_in_mod(self):
        from error_log import resolve_location
        mod, game, user = self._layout()
        r = resolve_location({"rel_path": "sound/sound.asset", "line": 730},
                             mod_path=mod, hoi4_path=game, user_dir=user)
        self.assertEqual(r["source"], "游戏")
        self.assertTrue(r["abs_path"].endswith(
            os.path.normpath("sound/sound.asset")))

    def test_ugc_descriptor_under_user_dir(self):
        from error_log import resolve_location
        mod, game, user = self._layout()
        r = resolve_location({"rel_path": "mod/ugc_3671805192.mod", "line": 1},
                             mod_path=mod, hoi4_path=game, user_dir=user)
        self.assertEqual(r["source"], "用户mod目录")
        self.assertEqual(os.path.basename(r["abs_path"]), "ugc_3671805192.mod")

    def test_not_found_keeps_rel(self):
        from error_log import resolve_location
        r = resolve_location({"rel_path": "common/other/missing.txt",
                              "line": 3}, mod_path="", hoi4_path="",
                             user_dir="")
        self.assertEqual(r["abs_path"], "")
        self.assertEqual(r["source"], "未找到")
        self.assertEqual(r["rel_path"], "common/other/missing.txt")


class TokenHintTest(unittest.TestCase):
    """实体 token + 中文修复建议。"""

    def test_gfx_key_missing(self):
        from error_log import extract_token
        token, hint = extract_token(SAMPLE_GFX)
        self.assertEqual(token, "GFX_military_industrial_organization_convoy")
        self.assertIn("SpriteType", hint)

    def test_focus_shine(self):
        from error_log import extract_token
        token, hint = extract_token(SAMPLE_PAREN)
        self.assertEqual(token, "GXC_the_japanese_visit")
        self.assertIn("shine", hint)

    def test_duplicate_entity(self):
        from error_log import extract_token
        token, _hint = extract_token(SAMPLE_ENTITY)
        self.assertEqual(token, "HOL_infantry_rider_entity")

    def test_character_scope(self):
        from error_log import extract_token
        token, hint = extract_token(SAMPLE_SCOPE)
        self.assertEqual(token, "BRA_candido_mariano")
        self.assertIn("recruit_character", hint)

    def test_resistance_token(self):
        from error_log import extract_token
        token, hint = extract_token(SAMPLE_INLINE)
        self.assertEqual(token, "阿尔及利亚沙漠")
        self.assertIn("add_compliance", hint)

    def test_supported_version_and_parse_token(self):
        from error_log import extract_token
        sample_meta = ("[06:06:05][no_game_date][dlc.cpp:218]: Invalid "
                       "supported_version in  file: mod/ugc_2243912940.mod "
                       "line: 10")
        _token, hint = extract_token(sample_meta)
        self.assertIn("supported_version", hint)
        token, hint = extract_token(SAMPLE_INFILE)
        self.assertEqual(token, "thumbnail")
        self.assertIn("解析失败", hint)


class AnalyzeDedupeTest(unittest.TestCase):
    """前缀剥离 / 去重计数 / 按文件汇总。"""

    def test_prefix_stripped_and_categorized(self):
        from error_log import analyze
        res = analyze(SAMPLE_PAREN)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["category"], "图标/实体缺失")
        self.assertNotIn("[06:06:17]", res[0]["message"])
        self.assertEqual(res[0]["rel_path"],
                         "common/national_focus/TSR_lingguang_incident_joint_branch.txt")

    def test_dedupe_merges_same_message(self):
        from error_log import analyze
        # 前缀（时间戳/引擎来源）不同的重复行，剥离后消息相同 → 合并
        text = "\n".join([
            SAMPLE_GFX, SAMPLE_GFX,
            SAMPLE_GFX.replace("equipment_group.cpp:70", "equipment_group.cpp:71"),
            SAMPLE_PAREN,
        ])
        res = analyze(text, dedupe=True)
        self.assertEqual(len(res), 2)
        by_msg = {r["message"]: r for r in res}
        self.assertEqual(
            by_msg[SAMPLE_GFX.split("]: ", 1)[1]]["count"], 3)
        self.assertEqual(
            by_msg[SAMPLE_GFX.split("]: ", 1)[1]]["lineno"], 1)

    def test_engine_noise_excluded(self):
        from error_log import analyze
        # 「incorrect checksum for DLC」与 mod 内容无关，不产生结果
        self.assertEqual(analyze(SAMPLE_ENGINE), [])

    def test_summarize_by_file(self):
        from error_log import analyze, summarize_by_file
        res = analyze("\n".join([SAMPLE_PAREN, SAMPLE_INLINE, SAMPLE_GFX,
                                 SAMPLE_ENTITY]))
        files = summarize_by_file(res)
        self.assertEqual(files["common/national_focus/TSR_lingguang_incident_joint_branch.txt"], 1)
        self.assertEqual(files["common/national_focus/france.txt"], 1)
        # GFX 键缺失/entity 重复无文件位置 → 记入未标注
        self.assertEqual(files["(引擎内部/未标注)"], 2)

    def test_analyze_file_resolves_locations(self):
        from error_log import analyze_file
        mod, game, user = LocationResolveTest._layout(self)
        log = os.path.join(_mkdtemp("errlog_log_"), "error.log")
        sample = ("[06:06:17][no_game_date][nationalfocus.cpp:642]: Missing icon "
                  "shine for focus: TST_focus (common/national_focus/a.txt:2 )")
        with open(log, "w", encoding="utf-8") as f:
            f.write(sample + "\n")
        res = analyze_file(log, mod_path=mod, hoi4_path=game,
                           user_dir=user, dedupe=True)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["source"], "mod")
        self.assertTrue(res[0]["abs_path"].endswith("a.txt"))
        self.assertEqual(res[0]["line"], 2)


class CrashReportTest(unittest.TestCase):
    """编辑器自身崩溃报告：落盘 + 含 文件:行号 traceback。"""

    def test_write_crash_report(self):
        import crash_report
        try:
            _ = 1 // 0  # noqa: B018 —— 制造真实 traceback
        except ZeroDivisionError:
            handle = sys.exc_info()
            path = crash_report.write_crash_report(*handle)
        self.assertTrue(path, "崩溃报告应成功落盘")
        self.assertTrue(path.startswith(crash_report.crash_report_dir()))
        self.assertTrue(os.path.basename(path).startswith("crash_"))
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.addCleanup(os.remove, path)
        self.assertIn("ZeroDivisionError", content)
        self.assertIn("test_error_log_analysis.py", content)
        self.assertIn("line", content)  # traceback 自带 文件:行号
        self.assertIn("Python:", content)


class ErrorLogReportDialogTest(unittest.TestCase):
    """结果表 UI：位置/来源列、双击打开、右键复制位置。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_dialog_shows_resolved_locations(self):
        mod, game, user = LocationResolveTest._layout(self)
        log = os.path.join(_mkdtemp("errlog_ui_"), "error.log")
        sample = ("[06:06:17][no_game_date][nationalfocus.cpp:642]: Missing icon "
                  "shine for focus: TST_focus (common/national_focus/a.txt:2 )")
        with open(log, "w", encoding="utf-8") as f:
            f.write(sample + "\n" + SAMPLE_ENGINE + "\n" + SAMPLE_GFX + "\n")
        from standalone_tool_dialogs import show_error_log_report
        # exec 会阻塞：monkeypatch QDialog.exec 为立即返回
        from PyQt6.QtWidgets import QDialog
        orig_exec = QDialog.exec
        QDialog.exec = lambda self: 0
        try:
            results = show_error_log_report(None, log, mod_path=mod,
                                            hoi4_path=game, user_dir=user)
        finally:
            QDialog.exec = orig_exec
        self.assertEqual(len(results), 2)
        # 首行：解析到 mod 内真实文件
        self.assertEqual(results[0]["source"], "mod")
        self.assertEqual(results[0]["rel_path"], "common/national_focus/a.txt")
        self.assertTrue(results[0]["abs_path"].endswith("a.txt"))
        # GFX 行无文件位置 → 无落位字段（UI 显示 引擎内部/未标注）
        gfx = [r for r in results if "GFX key" in r["message"]]
        self.assertEqual(gfx[0].get("source", ""), "")
        self.assertEqual(gfx[0].get("abs_path", ""), "")
        self.assertEqual(gfx[0]["token"],
                         "GFX_military_industrial_organization_convoy")

    def test_open_location_noop_without_abs_path(self):
        from standalone_tool_dialogs import _open_error_location
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem
        from PyQt6.QtCore import Qt
        table = QTableWidget()
        _open_error_location(table)  # 空表 → 直接返回
        table.setRowCount(1)
        table.setColumnCount(5)
        it = QTableWidgetItem("x")
        it.setData(Qt.ItemDataRole.UserRole, {"abs_path": ""})
        table.setItem(0, 0, it)
        table.setCurrentCell(0, 0)
        _open_error_location(table)  # abs_path 为空 → 直接返回


class McpAnalyzeErrorLogTest(unittest.TestCase):
    """MCP analyze_error_log：位置落位/建议/按文件汇总对外暴露。"""

    def test_core_analyze_returns_locations(self):
        mod = _mkdtemp("errlog_mcp_")
        os.makedirs(os.path.join(mod, "common", "national_focus"))
        with open(os.path.join(mod, "common", "national_focus", "m.txt"),
                  "w", encoding="utf-8") as f:
            f.write("focus = {\n}\n")
        log = os.path.join(mod, "error.log")
        sample = ("[06:06:17][no_game_date][nationalfocus.cpp:642]: Missing icon "
                  "shine for focus: TST_focus (common/national_focus/m.txt:1 )")
        with open(log, "w", encoding="utf-8") as f:
            f.write(sample + "\n" + SAMPLE_ENGINE + "\n")
        from api_server import ApiCore
        core = ApiCore(mod_path=mod, game_path="")
        r = core.analyze_error_log({"absolute_path": log})
        self.assertTrue(r["ok"])
        self.assertEqual(r["count"], 1)  # 引擎噪音行被排除
        self.assertEqual(r["unique_count"], 1)
        self.assertIn("files", r)
        paren = [i for i in r["items"] if i["rel_path"] == "common/national_focus/m.txt"]
        self.assertEqual(len(paren), 1)
        self.assertEqual(paren[0]["line"], 1)
        self.assertEqual(paren[0]["source"], "mod")
        self.assertTrue(paren[0]["abs_path"].endswith("m.txt"))
        self.assertEqual(paren[0]["token"], "TST_focus")
        self.assertTrue(paren[0]["hint"])
        # 引擎噪音行不在 items 中
        self.assertFalse(any("incorrect checksum" in i["message"]
                             for i in r["items"]))
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

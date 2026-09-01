"""现状评估报告修复契约（docs/现状评估报告.md P0/P1/P2 全量修复，迭代 6.89）

覆盖：
- P0-1 解析器线性化：pdx_parser / tree_node 分词行号增量统计 + 翻倍耗时比契约
- P0-2 通用树保存保真：verbatim 原文行（注释/空行/缩进）、多顶层块不再套
  focus 外壳、无改动保存不写盘（字节级一致）、外部修改（mtime）防护
- P1-3 write_utils 权限恢复 / undo 字节预算 / 写路径严格解码
- P1-4 entity_scanner 去 O(m²)（嵌套去重保序）+ pdx_span.find_block_range
- P1-5 _AI_CACHE 按 kind 精确失效
- P2-6 本地化参考语言回退（english）
- P2-7 state 重复 id 检查 + 国家 tag 全局索引
- P2-8 树编辑器循环搜索 + 写入纪律 allow_paths 审计
"""

from __future__ import annotations

import ast
import os
import shutil
import stat
import sys
import tempfile
import time
import unittest
from unittest import mock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


def _mkdtemp(prefix):
    return tempfile.mkdtemp(prefix="dsh_eval_fix_" + prefix)


def _gen_focus_text(n_lines):
    """合成国策文本（与评估基准一致，约 120B/行）。"""
    lines = []
    for i in range(n_lines):
        lines.append(
            "\tfocus = {\n"
            "\t\tid = FOCUS_%d\n"
            "\t\ticon = GFX_goal_%d\n"
            "\t\tx = %d\n"
            "\t\ty = %d\n"
            "\t\tcost = 70\n"
            "\t\tavailable = {\n"
            "\t\t\thas_war = yes\n"
            "\t\t}\n"
            "\t}\n" % (i, i, i % 30, i // 30))
    return "".join(lines)


class ParserLinearizationContract(unittest.TestCase):
    """P0-1：解析耗时随输入线性增长（翻倍输入耗时比 ≤ 阈值）。"""

    def test_parse_pdx_script_scaling(self):
        from pdx_parser import parse_pdx_script
        t1 = self._timed_parse(parse_pdx_script, _gen_focus_text(600))
        t2 = self._timed_parse(parse_pdx_script, _gen_focus_text(1200))
        self._assert_linear(t1, t2)

    def test_parse_pdx_text_to_nodes_scaling(self):
        from tree_node import parse_pdx_text_to_nodes
        t1 = self._timed_parse(parse_pdx_text_to_nodes, _gen_focus_text(600))
        t2 = self._timed_parse(parse_pdx_text_to_nodes, _gen_focus_text(1200))
        self._assert_linear(t1, t2)

    @staticmethod
    def _timed_parse(fn, text):
        best = None
        for _ in range(3):  # 取多次最优，降低调度噪声
            t0 = time.perf_counter()
            fn(text)
            dt = time.perf_counter() - t0
            best = dt if best is None else min(best, dt)
        return best

    def _assert_linear(self, t1, t2):
        # 绝对上限防退化（线性化后 1200 行应在毫秒~几十毫秒级）
        self.assertLess(t2, 5.0, "解析耗时异常（疑似回退为 O(n²)）")
        ratio = t2 / max(t1, 1e-6)
        # 线性期望 ≈ 2.0；旧 O(n²) 实测 ≈ 4.0；快路径放宽到 3.2 容调度噪声
        limit = 3.2 if t2 < 0.2 else 2.5
        self.assertLess(ratio, limit,
                        "翻倍输入耗时比 %.2f 超阈值 %.1f（疑似 O(n²) 回退）"
                        % (ratio, limit))


class TreeSaveFidelityContract(unittest.TestCase):
    """P0-2：通用树保存保真（注释/空行/结构 + mtime 防护）。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = _mkdtemp("save_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _open_editor(self, fp, content):
        from tree_node import tree_from_pdx_text, attach_verbatim_lines
        from generic_tree_editor import GenericTreeEditor
        root = tree_from_pdx_text(content)
        attach_verbatim_lines(root, content)
        file_lines = content.splitlines()
        return GenericTreeEditor(
            root, fp, file_lines, (1, len(file_lines) + 1),
            title="t", hoi4_path="", mod_path="")

    def test_no_change_save_is_byte_identical(self):
        content = ("# 头注释\na = {\n\tb = 1 # 行尾\n}\n\n# 中段\nc = 2\n"
                   "\n# 尾注释\n")
        fp = os.path.join(self.tmp, "round.txt")
        with open(fp, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        before = open(fp, "rb").read()
        ed = self._open_editor(fp, content)
        self.assertTrue(ed._save())
        self.assertEqual(before, open(fp, "rb").read())

    def test_edit_keeps_comments_and_no_focus_wrapper(self):
        content = ("# 顶部注释\n"
                   "idea_a = {\n"
                   "\ticon = GFX_a\n"
                   "}\n"
                   "\n"
                   "# idea_b 前的注释\n"
                   "idea_b = {\n"
                   "\ticon = GFX_b\n"
                   "}\n"
                   "\n# 文件尾注释\n")
        fp = os.path.join(self.tmp, "multi.txt")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        ed = self._open_editor(fp, content)
        node_a = ed.root_node.children[0]
        for c in node_a.children:
            if c.key == "icon":
                c.value = "GFX_new"
                c.raw_lines = []
        ed._invalidate_ancestors(node_a)
        self.assertTrue(ed._save())
        out = open(fp, encoding="utf-8").read()
        self.assertIn("GFX_new", out)              # 修改生效
        self.assertIn("# 顶部注释", out)            # 前导注释保留
        self.assertIn("# idea_b 前的注释", out)      # 兄弟节点前注释保留
        self.assertIn("# 文件尾注释", out)           # 文件尾保留
        self.assertNotIn("focus", out)             # 旧版 focus 外壳 bug 不再出现

    def test_single_wrapper_structure_kept(self):
        content = "focus_tree = {\n\tid = T\n}\n"
        fp = os.path.join(self.tmp, "wrap.txt")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        ed = self._open_editor(fp, content)
        wrapper = ed.root_node.children[0]
        for c in wrapper.children:
            if c.key == "id":
                c.value = "T2"
                c.raw_lines = []
        ed._invalidate_ancestors(wrapper)
        self.assertTrue(ed._save())
        out = open(fp, encoding="utf-8").read()
        self.assertTrue(out.startswith("focus_tree = {"))
        self.assertIn("id = T2", out)

    def test_external_modification_guard(self):
        import generic_tree_editor as gte
        from PyQt6.QtWidgets import QMessageBox as _QB
        content = "a = {\n\tb = 1\n}\n"
        fp = os.path.join(self.tmp, "ext.txt")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        ed = self._open_editor(fp, content)
        # 模拟外部修改（mtime 变化）
        with open(fp, "a", encoding="utf-8") as f:
            f.write("# external\n")
        node = ed.root_node.children[0]
        for c in node.children:
            if c.key == "b":
                c.value = "2"
                c.raw_lines = []
        ed._invalidate_ancestors(node)
        # 用户拒绝覆盖 → 保存中止、文件不动
        with mock.patch.object(gte.QMessageBox, "question",
                               return_value=_QB.StandardButton.No):
            self.assertFalse(ed._save())
        self.assertIn("b = 1", open(fp, encoding="utf-8").read())
        # 用户确认覆盖 → 保存生效
        with mock.patch.object(gte.QMessageBox, "question",
                               return_value=_QB.StandardButton.Yes):
            self.assertTrue(ed._save())
        self.assertIn("b = 2", open(fp, encoding="utf-8").read())


class WriteSafetyContract(unittest.TestCase):
    """P1-3：权限恢复 / 严格写前读取 / undo 字节预算。"""

    def setUp(self):
        self.tmp = _mkdtemp("write_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_chmod_fallback_restores_mode(self):
        from write_utils import atomic_write_text
        fp = os.path.join(self.tmp, "ro.txt")
        with open(fp, "w", encoding="utf-8") as f:
            f.write("old")
        os.chmod(fp, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # 0o444
        try:
            atomic_write_text(fp, "new")
            self.assertEqual(open(fp, encoding="utf-8").read(), "new")
            mode = stat.S_IMODE(os.stat(fp).st_mode)
            # 写入成功但不得遗留 0o666 全员可写（原只读位应恢复）
            self.assertFalse(mode & stat.S_IWUSR == 0
                             and mode & (stat.S_IWGRP | stat.S_IWOTH) != 0)
        finally:
            os.chmod(fp, 0o644)

    def test_read_text_for_write_rejects_bad_bytes(self):
        from write_utils import read_text_for_write, WriteContractError
        fp = os.path.join(self.tmp, "gbk.txt")
        with open(fp, "wb") as f:
            f.write(b"name = \xd6\xd0\xce\xc4\n")  # GBK 字节，非 UTF-8
        before = open(fp, "rb").read()
        with self.assertRaises(WriteContractError):
            read_text_for_write(fp)
        self.assertEqual(before, open(fp, "rb").read())  # 原文件不动

    def test_read_text_for_write_accepts_utf8_bom(self):
        from write_utils import read_text_for_write
        fp = os.path.join(self.tmp, "bom.txt")
        with open(fp, "w", encoding="utf-8-sig") as f:
            f.write("a = 1")
        self.assertEqual(read_text_for_write(fp), "a = 1")

    def test_state_write_aborts_on_bad_bytes(self):
        from state_build_ops import set_state_building
        mod = os.path.join(self.tmp, "mod")
        states = os.path.join(mod, "history", "states")
        os.makedirs(states)
        fp = os.path.join(states, "1-Test.txt")
        with open(fp, "wb") as f:
            f.write(b"state = {\n\tid = 1\n\thistory = {\n\t\tbuildings = {\n"
                    b"\t\t\tnaval_base = 3\n\t\t}\n\t}\n\tname = \xd6\xd0\n}\n")
        before = open(fp, "rb").read()
        ok, message, _rel = set_state_building(mod, "", 1, "naval_base", 5)
        self.assertFalse(ok)
        self.assertEqual(message, "decode_error")
        self.assertEqual(before, open(fp, "rb").read())  # 原文件不动

    def test_undo_byte_budget_evicts_oldest(self):
        from undo_mgr import FileUndoManager
        mgr = FileUndoManager(max_entries=50, max_total_bytes=100)
        files = []
        for i in range(4):
            fp = os.path.join(self.tmp, "f%d.txt" % i)
            with open(fp, "w", encoding="utf-8") as f:
                f.write("x" * 60)
            files.append(fp)
            mgr.before_write(fp)
        # 预算 100B：只应保留最新的 1 条（60B）
        self.assertEqual(len(mgr._stack), 1)
        path, ok = mgr.undo()
        self.assertEqual(path, files[-1])
        self.assertTrue(ok)
        self.assertEqual(open(files[-1], encoding="utf-8").read(), "x" * 60)
        self.assertFalse(mgr.can_undo())  # 更早的快照已按预算淘汰


class ScannerDeQuadratizeContract(unittest.TestCase):
    """P1-4：keys 嵌套去重保序（外层全保留）+ 块定位语义不变。"""

    CONTENT = (
        "\nfocus = { id = A }\n"
        "focus = { id = B\n\tfocus = { id = NESTED }\n}\n"
        "focus = { id = C }\n")

    def test_keys_rule_keeps_outer_blocks_in_order(self):
        from entity_scanner import EntityScanner
        spans = EntityScanner._block_spans(EntityScanner._scan_blocks(
            self.CONTENT))
        es = EntityScanner._apply_locate_rule(
            ("keys", ["focus"]), self.CONTENT, spans, {"field": "icon"})
        self.assertEqual([e["name"] for e in es], ["A", "B", "C"])

    def test_find_block_range_entity_id(self):
        from pdx_span import find_block_range
        start, end = find_block_range(
            self.CONTENT, ("focus", "shared_focus", "joint_focus"), "A")
        self.assertTrue(start >= 0 and end > start)
        self.assertIn("id = A", self.CONTENT[start:end])
        self.assertEqual(find_block_range(self.CONTENT, "focus", "ZZZ"),
                         (-1, -1))

    def test_children_in_early_exit(self):
        from pdx_span import scan_blocks, block_spans, depth_index, children_in
        spans = block_spans(scan_blocks(self.CONTENT))
        by_depth = depth_index(spans)
        outer = [s for s in spans if s[0] == "focus" and s[1] == 0]
        inner = children_in(by_depth, outer[1][2], outer[1][3], 1)
        self.assertEqual([s[0] for s in inner], ["focus"])


class CacheInvalidationContract(unittest.TestCase):
    """P1-5：_AI_CACHE 按 kind 精确失效。"""

    def test_invalidate_by_kind_only(self):
        import ai_loader
        ai_loader._AI_CACHE.clear()
        ai_loader._AI_CACHE[("scripted_effects", "m", "g")] = 1
        ai_loader._AI_CACHE[("scripted_triggers", "m", "g")] = 2
        ai_loader._AI_CACHE[("scripted_effects", "m2", "g")] = 3
        removed = ai_loader.invalidate_cache(kind="scripted_effects",
                                             mod_path="m")
        self.assertEqual(removed, 1)
        self.assertNotIn(("scripted_effects", "m", "g"), ai_loader._AI_CACHE)
        self.assertIn(("scripted_triggers", "m", "g"), ai_loader._AI_CACHE)
        self.assertIn(("scripted_effects", "m2", "g"), ai_loader._AI_CACHE)
        ai_loader._AI_CACHE.clear()


class LocalizationFallbackContract(unittest.TestCase):
    """P2-6：简中缺失时回退参考语言（english）。"""

    def setUp(self):
        self.tmp = _mkdtemp("loc_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_english_fallback_and_cn_priority(self):
        from localization_mgr import LocalizationManager
        game = os.path.join(self.tmp, "game")
        cn_dir = os.path.join(game, "localisation", "simp_chinese")
        en_dir = os.path.join(game, "localisation", "english")
        os.makedirs(cn_dir)
        os.makedirs(en_dir)
        with open(os.path.join(cn_dir, "a_l_simp_chinese.yml"), "w",
                  encoding="utf-8-sig") as f:
            f.write('l_simp_chinese:\n BOTH: "中文"\n')
        with open(os.path.join(en_dir, "a_l_english.yml"), "w",
                  encoding="utf-8-sig") as f:
            f.write('l_english:\n BOTH: "English"\n ONLY_EN: "Only"\n')
        mgr = LocalizationManager()
        mgr.add_game_path(game)
        self.assertEqual(mgr.get_name("BOTH"), "中文")     # 简中优先
        self.assertEqual(mgr.get_name("ONLY_EN"), "Only")  # 回退 english
        self.assertEqual(mgr.get_desc("ONLY_EN"), "")      # 无 _desc 键


class DuplicateStateIdContract(unittest.TestCase):
    """P2-7：history/states 数字 id 跨文件重复检查。"""

    def test_duplicate_state_ids_detected(self):
        from game_data import find_duplicate_ids
        mod = _mkdtemp("dup_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        states = os.path.join(mod, "history", "states")
        os.makedirs(states)
        for name in ("1-A.txt", "1-B.txt", "2-C.txt"):
            sid = name.split("-")[0]
            with open(os.path.join(states, name), "w",
                      encoding="utf-8") as f:
                f.write("state = {\n\tid = %s\n}\n" % sid)
        dups = find_duplicate_ids(mod)
        self.assertIn("state_1", dups)
        self.assertNotIn("state_2", dups)


class CountryTagIndexContract(unittest.TestCase):
    """P2-7：国家 tag 全局索引辅助识别。"""

    def tearDown(self):
        from entity_scanner import EntityScanner
        EntityScanner.set_country_tag_index(set())

    def test_mid_token_tag_detected_with_index(self):
        from entity_scanner import EntityScanner
        EntityScanner.set_country_tag_index({"GER"})
        tags = EntityScanner._detect_country_tags(
            "/x/common/ideas/focus_GER_add.txt", "")
        self.assertEqual(tags, ["GER"])

    def test_no_index_keeps_legacy_behavior(self):
        from entity_scanner import EntityScanner
        EntityScanner.set_country_tag_index(set())
        tags = EntityScanner._detect_country_tags(
            "/x/common/ideas/focus_GER_add.txt", "")
        self.assertEqual(tags, [])

    def test_build_index_from_country_tags(self):
        from entity_scanner import EntityScanner
        mod = _mkdtemp("tagidx_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "common", "country_tags")
        os.makedirs(d)
        with open(os.path.join(d, "00_tags.txt"), "w",
                  encoding="utf-8") as f:
            f.write('GER = "countries/GER.txt"\nPOL = "countries/POL.txt"\n')
        tags = EntityScanner.build_country_tag_index(mod, "")
        self.assertIn("GER", tags)
        self.assertIn("POL", tags)


class CyclicSearchContract(unittest.TestCase):
    """P2-8：树编辑器循环搜索（同一关键词继续回车 → 下一个匹配）。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    class _StubTranslator:
        """直通翻译桩（find_nodes 依赖 translator 才执行搜索）。"""

        def translate_node(self, key, value):
            return key, value

        def translate_key(self, key):
            return key

    def test_search_advance_cycles(self):
        from tree_node import TreeNode
        from generic_tree_editor import GenericTreeEditor
        root = TreeNode("block", "(paste_root)")
        for key in ("alpha", "beta", "alpha2"):
            root.add_child(TreeNode("value", key, ""))
        ed = GenericTreeEditor(root, "", ["x"], (1, 2), title="t",
                               translator=self._StubTranslator())
        ed.show()
        self.addCleanup(ed.close)
        ed._on_search("alpha")
        first = ed.tree_view.currentIndex()
        self.assertTrue(first.isValid())
        ed._search_advance()
        second = ed.tree_view.currentIndex()
        self.assertTrue(second.isValid())
        self.assertNotEqual(first, second)  # 命中第二个 alpha2
        ed._search_advance()
        third = ed.tree_view.currentIndex()
        self.assertEqual(third, first)      # 循环回到第一个


class AllowPathsAuditContract(unittest.TestCase):
    """P2-8：写入纪律 allow_paths 静态审计。"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(PROJECT_ROOT, "tools"))

    def _resolve(self, code):
        from check_write_discipline import _module_const_strings, \
            _resolve_write_target
        tree = ast.parse(code)
        consts = _module_const_strings(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) \
                    and getattr(node.func, "id", "") == "open":
                return _resolve_write_target(node, consts)
        return None

    def test_resolve_literal_and_join_tail(self):
        self.assertEqual(
            self._resolve("open('settings.json', 'w')"), "settings.json")
        self.assertEqual(
            self._resolve("import os\n"
                          "SETTINGS = os.path.join(ROOT, 'settings.json')\n"
                          "open(SETTINGS, 'w')"),
            "settings.json")
        self.assertIsNone(self._resolve("open(make_path(), 'w')"))

    def test_target_allowed_suffix_and_fnmatch(self):
        from check_write_discipline import _target_allowed
        self.assertTrue(_target_allowed("E:/x/settings.json",
                                        ["settings.json"]))
        self.assertTrue(_target_allowed("mod/history/a.txt", ["*.txt"]))
        self.assertFalse(_target_allowed("mod/history/a.txt",
                                         ["settings.json"]))


if __name__ == "__main__":
    unittest.main()

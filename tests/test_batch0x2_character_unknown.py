"""§0.x-2：角色未知块结构化编辑 + instance 解析。

CharacterUnknownEditTest：
- 未知块以 {"key","raw"} 结构化保存；
- 通过 ScriptBlockEditorDialog 编辑后写回，内容可改、其他字段不变；
- TFR 的 instance = { ... } 包装进入可编辑未知块列表，不再计入只读保留区。
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

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


class CharacterUnknownEditTest(unittest.TestCase):
    """角色未知块结构化编辑与 instance 包装。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = _mkdtemp("char_unknown_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        os.makedirs(os.path.join(self.mod, "common", "characters"))
        os.makedirs(os.path.join(self.mod, "localisation", "simp_chinese"))
        self.file = os.path.join(self.mod, "common", "characters", "TST.txt")

    def _write(self, content):
        with open(self.file, "w", encoding="utf-8") as f:
            f.write(content)

    def _read(self):
        with open(self.file, "r", encoding="utf-8") as f:
            return f.read()

    def test_unknown_blocks_parsed_as_structured_editable(self):
        self._write(
            "characters = {\n"
            "\tTST_leader = {\n"
            "\t\tname = \"TST_leader\"\n"
            "\t\tcan_be_captured = no\n"
            "\t\tlegacy = { old = yes }\n"
            "\t\tinstance = {\n"
            "\t\t\tallowed = { has_dlc = \"La Resistance\" }\n"
            "\t\t\tname = TST_leader\n"
            "\t\t\tportraits = { civilian = { large = GFX_TST } }\n"
            "\t\t}\n"
            "\t}\n"
            "}\n")
        from character_data import load_file
        _h, metas, _t = load_file(self.file)
        m = metas[0]
        unknown = m.get("unknown_blocks", [])
        self.assertEqual([b["key"] for b in unknown], ["legacy", "instance"])
        self.assertEqual(len(m.get("others_blocks", [])), 2)
        # 行/块分离：未知块不应混入只读行列表
        self.assertTrue(any(x[1] == "can_be_captured" for x in m["others_lines"]))
        self.assertFalse(any(x[0] == "block" for x in m["others_lines"]))
        self.assertIn("allowed", unknown[1]["raw"])
        self.assertIn("portraits", unknown[1]["raw"])

    def test_unknown_block_roundtrip_content_changed_others_unchanged(self):
        self._write(
            "characters = {\n"
            "\tTST_leader = {\n"
            "\t\tname = \"TST_leader\"\n"
            "\t\tdesc = \"TST_desc\"\n"
            "\t\tcan_be_captured = no\n"
            "\t\tcustom_block = { value = 1 }\n"
            "\t\tcountry_leader = {\n"
            "\t\t\tideology = democratic\n"
            "\t\t\ttraits = { bold }\n"
            "\t\t}\n"
            "\t}\n"
            "}\n")
        from character_data import load_file, save_file_v2
        h, metas, t = load_file(self.file)
        m = metas[0]
        custom = next(b for b in m["unknown_blocks"] if b["key"] == "custom_block")
        custom["raw"] = "custom_block = {\n\tvalue = 2\n\tnew_key = yes\n}"
        save_file_v2(self.file, h, metas, t)

        _h2, m2, _t2 = load_file(self.file)
        m2 = m2[0]
        self.assertEqual(m2["name_loc"], "TST_leader")
        self.assertEqual(m2["desc_loc"], "TST_desc")
        self.assertEqual([r["role_type"] for r in m2["role_entries"]],
                         ["country_leader"])
        self.assertTrue(any(x[1] == "can_be_captured" for x in m2["others_lines"]))
        custom2 = next(b for b in m2["unknown_blocks"] if b["key"] == "custom_block")
        self.assertIn("value = 2", custom2["raw"])
        self.assertIn("new_key = yes", custom2["raw"])
        content = self._read()
        self.assertIn("value = 2", content)
        self.assertIn("can_be_captured = no", content)
        self.assertIn("ideology = democratic", content)

    def _open_dialog(self):
        from character_editor_dialog import CharacterEditorDialog
        dlg = CharacterEditorDialog(mod_path=self.mod, hoi4_path="")
        self.app.processEvents()
        self.addCleanup(dlg.close)
        return dlg

    def test_instance_wrapper_editable_and_not_in_readonly_count(self):
        self._write(
            "characters = {\n"
            "\tPRC_mao = {\n"
            "\t\tname = \"PRC_mao\"\n"
            "\t\tcan_be_captured = no\n"
            "\t\tinstance = {\n"
            "\t\t\tallowed = { has_dlc = \"No Compromise, No Surrender\" }\n"
            "\t\t\tname = PRC_mao\n"
            "\t\t}\n"
            "\t}\n"
            "}\n")
        from character_data import load_file
        _h, metas, _t = load_file(self.file)
        m = metas[0]
        self.assertEqual([b["key"] for b in m["unknown_blocks"]], ["instance"])
        dlg = self._open_dialog()
        self.assertEqual(dlg.unknown_list.count(), 1)
        self.assertIn("instance", dlg.unknown_list.item(0).text())
        # 只读保留提示只统计未知行；未知块标记为可编辑
        self.assertIn("未知块 1 个（✎ 可编辑）", dlg.keep_info.text())
        self.assertNotIn("不可在此编辑", dlg.keep_info.text())
        self.assertNotIn("未知块 1 个（保留", dlg.keep_info.text())

    def test_edit_unknown_block_through_dialog_and_save(self):
        self._write(
            "characters = {\n"
            "\tTST_leader = {\n"
            "\t\tname = \"TST_leader\"\n"
            "\t\tinstance = {\n"
            "\t\t\tallowed = { has_dlc = \"Old\" }\n"
            "\t\t}\n"
            "\t\tcountry_leader = { ideology = democratic }\n"
            "\t}\n"
            "}\n")
        class _FakeScriptBlockEditorDialog:
            def __init__(self, *args, **kwargs):
                self.called_kwargs = kwargs

            def exec(self):
                return True

            def get_block_text(self):
                return ("instance = {\n"
                        "\tallowed = { has_dlc = \"New\" }\n"
                        "\tnew_flag = yes\n"
                        "}")

        


if __name__ == "__main__":
    unittest.main()
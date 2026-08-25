"""Mod 描述（.mod）专用编辑器测试：数据层 + 对话框 offscreen 冒烟。"""

from __future__ import annotations

import os
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


SAMPLE = """replace_path="common/technologies"
tags={
	"Military"
	"Gameplay"
}
name="The Fire Rises"
version="1.0.8.3"
supported_version="1.19.*"
remote_file_id="3350890356"
"""


class ModDescriptorLoaderTest(unittest.TestCase):
    def test_parse_known_fields(self):
        from mod_descriptor_loader import extract_fields, parse_mod_entries

        fields = extract_fields(parse_mod_entries(SAMPLE))
        self.assertEqual(fields["name"], "The Fire Rises")
        self.assertEqual(fields["version"], "1.0.8.3")
        self.assertEqual(fields["supported_version"], "1.19.*")
        self.assertEqual(fields["remote_file_id"], "3350890356")
        self.assertEqual(fields["replace_path"], ["common/technologies"])
        self.assertEqual(fields["tags"], ["Military", "Gameplay"])

    def test_round_trip_preserves_all_known(self):
        from mod_descriptor_loader import (
            build_entries, extract_fields, format_mod_entries, parse_mod_entries,
        )

        fields = extract_fields(parse_mod_entries(SAMPLE))
        text = format_mod_entries(build_entries(fields))
        again = extract_fields(parse_mod_entries(text))
        self.assertEqual(again["name"], fields["name"])
        self.assertEqual(again["replace_path"], fields["replace_path"])
        self.assertEqual(again["tags"], fields["tags"])
        self.assertEqual(again["dependencies"], fields["dependencies"])

    def test_unknown_and_repeated_entries_preserved(self):
        from mod_descriptor_loader import (
            build_entries, extract_fields, format_mod_entries, parse_mod_entries,
        )

        text = ('custom_flag="x"\n'
                'replace_path="common/events"\n'
                'replace_path="history/states"\n'
                'name="A"\n'
                'picture = "thumb.png"\n')
        fields = extract_fields(parse_mod_entries(text))
        self.assertEqual(fields["replace_path"], [
            "common/events", "history/states"])
        self.assertEqual(fields["picture"], "thumb.png")
        self.assertEqual(len(fields["other"]), 1)  # custom_flag 进 other
        out = format_mod_entries(build_entries(fields))
        self.assertIn("custom_flag = x", out)
        self.assertEqual(out.count("replace_path"), 2)

    def test_dependencies_block_and_scalar(self):
        from mod_descriptor_loader import extract_fields, parse_mod_entries

        text = 'dependencies = { "123456" "789012" }\nname="B"\n'
        fields = extract_fields(parse_mod_entries(text))
        self.assertEqual(fields["dependencies"], ["123456", "789012"])

    def test_split_list_text(self):
        from mod_descriptor_loader import split_list_text

        self.assertEqual(split_list_text(" a\nb,\n\n c "), ["a", "b", "c"])


class ModDescriptorEditorSmokeTest(unittest.TestCase):
    def test_dialog_opens_and_saves(self):
        try:
            from mod_descriptor_editor_dialog import ModDescriptorEditorDialog
        except Exception as e:  # noqa: BLE001
            self.skipTest("PyQt6 不可用: %s" % e)
        import os
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])
        tmp = _mkdtemp("mod_desc_")
        fp = os.path.join(tmp, "descriptor.mod")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(SAMPLE)

        dlg = ModDescriptorEditorDialog(file_path=fp, mod_path=tmp)
        self.assertEqual(dlg._scalar_edits["name"].text(), "The Fire Rises")
        dlg._replace_path_edit.setPlainText("common/technologies\nhistory/states")

        import mod_descriptor_editor_dialog as mod_editor
        orig_info = mod_editor.QMessageBox.information
        mod_editor.QMessageBox.information = staticmethod(lambda *a, **k: None)
        try:
            dlg._on_save()
        finally:
            mod_editor.QMessageBox.information = orig_info

        with open(fp, encoding="utf-8") as f:
            content = f.read()
        # 保存后两个 replace_path 条目都在
        self.assertIn("common/technologies", content)
        self.assertIn("history/states", content)
        self.assertEqual(content.count("replace_path"), 2)
        dlg.close()


if __name__ == "__main__":
    unittest.main()
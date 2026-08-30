"""政治类型专用编辑器测试（P2 ②）：意识形态 + 民族精神 ideas。"""

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


IDEOLOGY_SAMPLE = """ideologies = {
\tdemocratic = {
\t\ttypes = {
\t\t\tconservatism = {
\t\t\t}
\t\t}
\t\tcolor = { 0 0 255 }
\t\tdynamic_faction_names = {
\t\t\t"FACTION_NAME_DEMOCRATIC_1"
\t\t}
\t\trules = {
\t\t\tcan_declare_war_on_same_ideology = no
\t\t}
\t\twar_impact_on_world_tension = 0.25
\t}
}
"""

IDEAS_SAMPLE = """ideas = {
\tcountry = {
\t\tmy_spirit = {
\t\t\tpicture = my_spirit
\t\t\tallowed = { always = yes }
\t\t}
\t}
}
"""


class PoliticalEditorDataTest(unittest.TestCase):
    def test_replace_child_block(self):
        from political_editor_data import replace_child_block

        bt = "democratic = {\n\tcolor = { 0 0 255 }\n}"
        out = replace_child_block(bt, "color", " 1 2 3")
        self.assertIn("color = { 1 2 3}", out)
        out2 = replace_child_block(out, "types", "\tconservatism = {}")
        self.assertIn("types = {", out2)
        self.assertIn("conservatism = {}", out2)

    def test_set_scalar_field(self):
        from political_editor_data import set_scalar_field

        bt = "x = {\n\tcost = 1\n}"
        out = set_scalar_field(bt, "cost", "2")
        self.assertIn("cost = 2", out)
        out2 = set_scalar_field(out, "removal_cost", "-1")
        self.assertIn("removal_cost = -1", out2)

    def test_list_helpers(self):
        from political_editor_data import (
            join_list_block, list_items_from_block,
        )

        items = list_items_from_block(
            'dynamic_faction_names = {\n\t"A"\n\t"B C"\n}')
        self.assertEqual(items, ["A", "B C"])
        self.assertIn('"B C"', join_list_block(["A", "B C"]))

    def test_replace_nested_block_text_depth2(self):
        from political_editor_data import replace_nested_block_text

        out = replace_nested_block_text(
            IDEAS_SAMPLE, "my_spirit",
            "my_spirit = {\n\tpicture = new_pic\n}",
            wrapper_key="ideas", depth=2)
        self.assertIn("picture = new_pic", out)
        self.assertIn("my_spirit = {", out)

    def test_insert_into_category(self):
        from political_editor_data import insert_into_category

        out = insert_into_category(
            IDEAS_SAMPLE, "ideas", "country",
            "other = {\n\tcost = 0\n}", depth=2)
        self.assertIn("other = {", out)
        # other 插在 my_spirit 之后、分类块（文件最后一个 }）之前
        self.assertGreater(out.index("other = {"),
                           out.index("my_spirit = {"))
        self.assertLess(out.index("other = {"), out.rfind("}"))


class IdeologiesEditorSmokeTest(unittest.TestCase):
    def test_open_edit_save(self):
        try:
            from PyQt6.QtWidgets import QApplication
        except Exception as e:  # noqa: BLE001
            self.skipTest("PyQt6 不可用: %s" % e)

        tmp = _mkdtemp("pol_ideo_")
        d = os.path.join(tmp, "common", "ideologies")
        os.makedirs(d)
        fp = os.path.join(d, "00_test.txt")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(IDEOLOGY_SAMPLE)

        app = QApplication.instance() or QApplication([])
        import ideologies_editor_dialog as ideo_mod
        from ideologies_editor_dialog import IdeologiesEditorDialog

        dlg = IdeologiesEditorDialog(mod_path=tmp)
        self.assertIn("democratic", dlg.entities)
        dlg.sidebar.set_current("democratic")
        dlg._on_current_changed("democratic")
        self.assertEqual(dlg.color_edit.text().strip(), "0 0 255")
        dlg.color_edit.setText("1 2 3")

        orig_info = ideo_mod.QMessageBox.information
        ideo_mod.QMessageBox.information = staticmethod(lambda *a, **k: None)
        try:
            dlg._on_save()
        finally:
            ideo_mod.QMessageBox.information = orig_info

        with open(fp, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("color = { 1 2 3}", content)
        dlg.close()


class IdeasEditorSmokeTest(unittest.TestCase):
    def test_open_edit_save(self):
        try:
            from PyQt6.QtWidgets import QApplication
        except Exception as e:  # noqa: BLE001
            self.skipTest("PyQt6 不可用: %s" % e)

        tmp = _mkdtemp("pol_ideas_")
        d = os.path.join(tmp, "common", "ideas")
        os.makedirs(d)
        fp = os.path.join(d, "00_test.txt")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(IDEAS_SAMPLE)

        app = QApplication.instance() or QApplication([])
        import ideas_editor_dialog as ideas_mod
        from ideas_editor_dialog import IdeasEditorDialog

        dlg = IdeasEditorDialog(mod_path=tmp)
        self.assertIn("my_spirit", dlg.entities)
        self.assertEqual(dlg.entities["my_spirit"]["parent_id"], "country")
        dlg.category_combo.setCurrentText("country")
        dlg.sidebar.set_current("my_spirit")
        dlg._on_current_changed("my_spirit")
        dlg.editor.load_text("\tpicture = other_pic\n\tallowed = { always = yes }")

        orig_info = ideas_mod.QMessageBox.information
        ideas_mod.QMessageBox.information = staticmethod(lambda *a, **k: None)
        try:
            dlg._on_save()
        finally:
            ideas_mod.QMessageBox.information = orig_info

        with open(fp, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("picture = other_pic", content)
        dlg.close()


if __name__ == "__main__":
    unittest.main()
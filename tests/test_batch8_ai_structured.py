"""批次 8：raw 兜底降级 —— 结构化默认视图 / 顾问 traits 选择器 / AI 计划 desc。

使用 unittest，全部 GUI 冒烟在 Qt offscreen 下运行。
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

from PyQt6.QtCore import Qt

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


def _make_mod_with_plan():
    """创建含一个 AI 战略计划的临时 mod 目录。"""
    mod = _mkdtemp("dsh_batch8_plan_")
    target = os.path.join(mod, "common", "ai_strategy_plans")
    os.makedirs(target, exist_ok=True)
    with open(os.path.join(target, "GER.txt"), "w", encoding="utf-8") as f:
        f.write(
            "GER_historical = {\n"
            "\tname = \"German historical plan\"\n"
            "\tallowed = { original_tag = GER }\n"
            "\tai_national_focuses = { A B C }\n"
            "}\n"
        )
    return mod


class ScriptBlockStructuredTest(unittest.TestCase):
    """ScriptBlockEditorDialog 默认结构化视图 + raw 在高级菜单。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_default_view_is_kv_table_plus_subblock_list(self):
        from ai_ui_common import ScriptBlockEditorDialog
        dlg = ScriptBlockEditorDialog(
            "allowed = {\n"
            "\talways = yes\n"
            "\tnorway = { tag = NOR }\n"
            "\tdate > 1936.1.1\n"
            "}\n",
            block_key="allowed")

        # 键值表只显示非块标量子节点；比较操作语句键为空、值保留原文
        self.assertEqual(dlg.kv_table.table.rowCount(), 2)
        keys = [dlg.kv_table.table.item(r, 0).text()
                for r in range(dlg.kv_table.table.rowCount())]
        values = [dlg.kv_table.table.item(r, 1).text()
                  for r in range(dlg.kv_table.table.rowCount())]
        self.assertIn("always", keys)
        self.assertIn("date > 1936.1.1", values)

        # 子块列表只显示块子节点，双击进入结构
        self.assertEqual(dlg.list.count(), 1)
        self.assertIn("norway = { ... }", dlg.list.item(0).text())
        node = dlg.list.item(0).data(Qt.ItemDataRole.UserRole)
        self.assertEqual(node.key if node is not None else None, "norway")
        dlg.close()

    def test_raw_kept_in_advanced_menu(self):
        from ai_ui_common import ScriptBlockEditorDialog
        dlg = ScriptBlockEditorDialog(
            "allowed = { always = yes }", block_key="allowed")
        self.assertIsNotNone(dlg.advanced_btn.menu())
        actions = dlg.advanced_btn.menu().actions()
        self.assertGreaterEqual(len(actions), 1)
        # raw 是「高级 ▾」菜单的末项，且未被删除
        self.assertEqual(actions[-1].text(), "📝 原始 PDX（兜底）")
        self.assertEqual(dlg.get_block_text().strip(),
                         "allowed = {\n\talways = yes\n}")
        dlg.close()

    def test_table_edits_commit_to_block_text(self):
        from ai_ui_common import ScriptBlockEditorDialog
        dlg = ScriptBlockEditorDialog(
            "allowed = { always = yes }", block_key="allowed")
        dlg.kv_table.table.item(0, 1).setText("no")
        dlg.kv_table.add_row("x", "1")
        text = dlg.get_block_text()
        self.assertIn("always = no", text)
        self.assertIn("x = 1", text)
        dlg.close()


class AdvisorTraitsTest(unittest.TestCase):
    """顾问 traits 多选弹窗回写格式与字段化构建。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_picker_selected_preserves_saved_order(self):
        from advisor_assign_dialog import TraitsPickerDialog
        dlg = TraitsPickerDialog(
            ["trait_a", "trait_b", "trait_c"],
            selected=["trait_c", "trait_a"],
            parent=None)
        # 不 exec()（避免模态阻塞），show 后检查预选与回写列表
        dlg.show()
        self.app.processEvents()
        selected = dlg.selected()
        self.assertEqual(sorted(selected), ["trait_a", "trait_c"])
        # 修改选择后仍返回列表格式（每行一个 trait，保存时 join）
        dlg.list.item(1).setSelected(True)
        dlg.list.item(2).setSelected(False)
        self.assertEqual(dlg.selected(), ["trait_a", "trait_b"])
        dlg.close()

    def test_build_assign_block_roundtrip_idea_slot_name_desc_traits(self):
        from advisor_assign_dialog import build_assign_block
        out = build_assign_block(
            "GEN_NAME",
            ["GER"],
            {
                "slot": "political_advisor",
                "idea_token": "GEN_IDEA",
                "name": "GEN_NAME",
                "desc": "GEN_DESC",
                "traits": "trait_a\ntrait_b",
                "available": "always = yes",
            })
        self.assertIn("name = GEN_NAME", out)
        self.assertIn("idea_token = GEN_IDEA", out)
        self.assertIn("desc = GEN_DESC", out)
        self.assertIn("slot = political_advisor", out)
        self.assertIn("trait_a", out)
        self.assertIn("trait_b", out)
        # traits 保持块内逐项写回格式
        self.assertIn("traits = {", out)

    def test_slot_choices_are_fixed_enum(self):
        from advisor_assign_dialog import SLOT_CHOICES
        self.assertEqual(SLOT_CHOICES, [
            "political_advisor", "theorist", "army_chief", "navy_chief",
            "air_chief", "high_command",
        ])


class AiPlanDescTest(unittest.TestCase):
    """AI 战略计划 desc 本地化双行编辑。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_desc_dual_line_fields_and_save(self):
        from ai_loader import _AI_CACHE, load_ai_plans
        from ai_plan_editor_dialog import AiPlanEditorDialog
        from localisation_editor_data import default_mod_loc_file
        from PyQt6.QtWidgets import QMessageBox

        mod = _make_mod_with_plan()
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        _AI_CACHE.clear()
        plans = load_ai_plans(mod, "")
        dlg = AiPlanEditorDialog(plans, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertIsNotNone(dlg.desc_key_edit)
        self.assertIsNotNone(dlg.desc_cn_edit)

        dlg.desc_key_edit.setText("GER_AI_DESC")
        dlg.desc_cn_edit.setText("德国 AI 历史方案说明")
        old_info = QMessageBox.information
        QMessageBox.information = lambda *args, **kwargs: None
        try:
            dlg._save()
        finally:
            QMessageBox.information = old_info
        dlg.close()

        plan_file = os.path.join(mod, "common", "ai_strategy_plans", "GER.txt")
        with open(plan_file, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        self.assertIn("desc = GER_AI_DESC", content)

        loc_fp = default_mod_loc_file(mod)
        self.assertTrue(os.path.exists(loc_fp))
        with open(loc_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            loc = f.read()
        self.assertIn('GER_AI_DESC: "德国 AI 历史方案说明"', loc)


if __name__ == "__main__":
    unittest.main()
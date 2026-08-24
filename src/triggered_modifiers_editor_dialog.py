"""触发修正专用编辑器（B2/B3，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_triggered_modifiers
from simple_block_editor import make_simple_block_dialog

TriggeredModifiersEditorDialog = make_simple_block_dialog(
    load_triggered_modifiers, "触发修正", "触发修正编辑器")


def open_triggered_modifiers_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示触发修正编辑器（非模态）。"""
    dlg = TriggeredModifiersEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

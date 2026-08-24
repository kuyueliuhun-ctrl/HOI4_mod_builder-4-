"""修正类型专用编辑器（B3/P36，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_modifiers
from simple_block_editor import make_simple_block_dialog

ModifiersEditorDialog = make_simple_block_dialog(
    load_modifiers, "修正类型", "修正类型编辑器")


def open_modifiers_editor(file_path="", mod_path="", hoi4_path="",
                          entity_id=None, parent=None):
    """入口：加载并显示修正类型编辑器（非模态）。"""
    dlg = ModifiersEditorDialog(mod_path, hoi4_path,
                                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg
"""持续国策专用编辑器（B3，通用 NestedBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_continuous_focus
from nested_block_editor import make_nested_block_dialog

ContinuousFocusEditorDialog = make_nested_block_dialog(
    load_continuous_focus, "持续国策", "持续国策编辑器", id_field="id")


def open_continuous_focus_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示持续国策编辑器（非模态）。"""
    dlg = ContinuousFocusEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

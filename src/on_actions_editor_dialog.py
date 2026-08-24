"""on_actions专用编辑器（B3，通用 NestedBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_on_actions
from nested_block_editor import make_nested_block_dialog

OnActionsEditorDialog = make_nested_block_dialog(
    load_on_actions, "on_actions 事件", "on_actions编辑器")


def open_on_actions_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示on_actions编辑器（非模态）。"""
    dlg = OnActionsEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

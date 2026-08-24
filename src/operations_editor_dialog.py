"""间谍行动专用编辑器（B2/B3，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_operations
from simple_block_editor import make_simple_block_dialog

OperationsEditorDialog = make_simple_block_dialog(
    load_operations, "间谍行动", "间谍行动编辑器")


def open_operations_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示间谍行动编辑器（非模态）。"""
    dlg = OperationsEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

"""决议专用编辑器（B3，通用 NestedBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_decisions
from nested_block_editor import make_nested_block_dialog

DecisionsEditorDialog = make_nested_block_dialog(
    load_decisions, "决议", "决议编辑器")


def open_decisions_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示决议编辑器（非模态）。"""
    dlg = DecisionsEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

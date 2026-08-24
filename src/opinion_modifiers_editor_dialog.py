"""观点修正专用编辑器（B3/P33，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_opinion_modifiers
from simple_block_editor import make_simple_block_dialog

OpinionModifiersEditorDialog = make_simple_block_dialog(
    load_opinion_modifiers, "观点修正", "观点修正编辑器")


def open_opinion_modifiers_editor(file_path="", mod_path="", hoi4_path="",
                                  entity_id=None, parent=None):
    """入口：加载并显示观点修正编辑器（非模态）。"""
    dlg = OpinionModifiersEditorDialog(mod_path, hoi4_path,
                                       parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg
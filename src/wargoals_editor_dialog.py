"""战争目标专用编辑器（B3/P33，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_wargoals
from simple_block_editor import make_simple_block_dialog

WargoalsEditorDialog = make_simple_block_dialog(
    load_wargoals, "战争目标", "战争目标编辑器")


def open_wargoals_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示战争目标编辑器（非模态）。"""
    dlg = WargoalsEditorDialog(mod_path, hoi4_path,
                               parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg
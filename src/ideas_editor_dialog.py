"""理念专用编辑器（B3，通用 NestedBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_ideas
from nested_block_editor import make_nested_block_dialog

IdeasEditorDialog = make_nested_block_dialog(
    load_ideas, "理念", "理念编辑器", depth=2)


def open_ideas_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示理念编辑器（非模态）。"""
    dlg = IdeasEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

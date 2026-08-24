"""理念槽位专用编辑器（B3，通用 NestedBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_idea_tags
from nested_block_editor import make_nested_block_dialog

IdeaTagsEditorDialog = make_nested_block_dialog(
    load_idea_tags, "理念槽位", "理念槽位编辑器")


def open_idea_tags_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示理念槽位编辑器（非模态）。"""
    dlg = IdeaTagsEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

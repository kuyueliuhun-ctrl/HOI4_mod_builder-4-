"""科技标签编辑器专用编辑器（B2/B3，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_technology_tags
from simple_block_editor import make_simple_block_dialog

TechnologyTagsEditorDialog = make_simple_block_dialog(
    load_technology_tags, "科技标签", "科技标签编辑器")


def open_technology_tags_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示科技标签编辑器（非模态）。"""
    dlg = TechnologyTagsEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

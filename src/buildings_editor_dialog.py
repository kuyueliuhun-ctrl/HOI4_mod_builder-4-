"""建筑专用编辑器（B3，通用 NestedBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_buildings
from nested_block_editor import make_nested_block_dialog

BuildingsEditorDialog = make_nested_block_dialog(
    load_buildings, "建筑", "建筑编辑器")


def open_buildings_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示建筑编辑器（非模态）。"""
    dlg = BuildingsEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

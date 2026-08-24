"""地形专用编辑器（B3，通用 NestedBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_terrain
from nested_block_editor import make_nested_block_dialog

TerrainEditorDialog = make_nested_block_dialog(
    load_terrain, "地形", "地形编辑器")


def open_terrain_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示地形编辑器（非模态）。"""
    dlg = TerrainEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

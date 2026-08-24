"""战略要地专用编辑器（B3/P34，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_strategic_locations
from simple_block_editor import make_simple_block_dialog

StrategicLocationsEditorDialog = make_simple_block_dialog(
    load_strategic_locations, "战略要地", "战略要地编辑器")


def open_strategic_locations_editor(file_path="", mod_path="", hoi4_path="",
                                    entity_id=None, parent=None):
    """入口：加载并显示战略要地编辑器（非模态）。"""
    dlg = StrategicLocationsEditorDialog(mod_path, hoi4_path,
                                         parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg
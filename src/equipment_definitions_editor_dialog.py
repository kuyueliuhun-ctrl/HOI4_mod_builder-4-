"""装备定义专用编辑器（B2/B3）。"""

from __future__ import annotations

from ai_loader import load_equipment_definitions
from nested_block_editor import make_nested_block_dialog

EquipmentDefinitionsEditorDialog = make_nested_block_dialog(
    load_equipment_definitions, "装备定义", "装备定义编辑器")


def open_equipment_definitions_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示装备定义编辑器（非模态）。"""
    dlg = EquipmentDefinitionsEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

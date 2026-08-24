"""将领特质专用编辑器（B3，通用 NestedBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_unit_leader_traits
from nested_block_editor import make_nested_block_dialog

UnitLeaderTraitsEditorDialog = make_nested_block_dialog(
    load_unit_leader_traits, "将领特质", "将领特质编辑器")


def open_unit_leader_traits_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示将领特质编辑器（非模态）。"""
    dlg = UnitLeaderTraitsEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

"""战术专用编辑器（B2/B3，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_combat_tactics
from simple_block_editor import make_simple_block_dialog

CombatTacticsEditorDialog = make_simple_block_dialog(
    load_combat_tactics, "战术", "战术编辑器")


def open_combat_tactics_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示战术编辑器（非模态）。"""
    dlg = CombatTacticsEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

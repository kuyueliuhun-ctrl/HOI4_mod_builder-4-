"""特种能力编辑器专用编辑器（B2/B3，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_abilities
from simple_block_editor import make_simple_block_dialog

AbilitiesEditorDialog = make_simple_block_dialog(
    load_abilities, "特种能力", "特种能力编辑器")


def open_abilities_editor(file_path="", mod_path="", hoi4_path="",
            entity_id=None, parent=None):
    """入口：加载并显示特种能力编辑器（非模态）。"""
    dlg = AbilitiesEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

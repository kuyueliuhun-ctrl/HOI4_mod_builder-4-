"""派系专用编辑器（B2/B3）。"""

from __future__ import annotations

from ai_loader import load_factions
from simple_block_editor import make_simple_block_dialog

FactionsEditorDialog = make_simple_block_dialog(
    load_factions, "派系", "派系编辑器")


def open_factions_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示派系编辑器（非模态）。"""
    dlg = FactionsEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

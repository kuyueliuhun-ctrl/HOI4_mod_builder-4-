"""占领法编辑器专用编辑器（B2/B3，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_occupation_laws
from simple_block_editor import make_simple_block_dialog

OccupationLawsEditorDialog = make_simple_block_dialog(
    load_occupation_laws, "占领法", "占领法编辑器")


def open_occupation_laws_editor(file_path="", mod_path="", hoi4_path="",
            entity_id=None, parent=None):
    """入口：加载并显示占领法编辑器（非模态）。"""
    dlg = OccupationLawsEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

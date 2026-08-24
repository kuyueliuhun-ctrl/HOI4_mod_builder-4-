"""抵抗活动编辑器专用编辑器（B2/B3，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_resistance_activity
from simple_block_editor import make_simple_block_dialog

ResistanceActivityEditorDialog = make_simple_block_dialog(
    load_resistance_activity, "抵抗活动", "抵抗活动编辑器")


def open_resistance_activity_editor(file_path="", mod_path="", hoi4_path="",
            entity_id=None, parent=None):
    """入口：加载并显示抵抗活动编辑器（非模态）。"""
    dlg = ResistanceActivityEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

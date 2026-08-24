"""抵抗合规编辑器专用编辑器（B2/B3，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_resistance_compliance
from simple_block_editor import make_simple_block_dialog

ResistanceComplianceEditorDialog = make_simple_block_dialog(
    load_resistance_compliance, "抵抗合规", "抵抗合规编辑器")


def open_resistance_compliance_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示抵抗合规编辑器（非模态）。"""
    dlg = ResistanceComplianceEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

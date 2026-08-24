"""自治状态专用编辑器（B3/P33，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_autonomous_states
from simple_block_editor import make_simple_block_dialog

AutonomousStatesEditorDialog = make_simple_block_dialog(
    load_autonomous_states, "自治状态", "自治状态编辑器")


def open_autonomous_states_editor(file_path="", mod_path="", hoi4_path="",
                                  entity_id=None, parent=None):
    """入口：加载并显示自治状态编辑器（非模态）。"""
    dlg = AutonomousStatesEditorDialog(mod_path, hoi4_path,
                                       parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg
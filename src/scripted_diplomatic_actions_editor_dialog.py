"""脚本化外交行动编辑器专用编辑器（B2/B3，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_scripted_diplomatic_actions
from simple_block_editor import make_simple_block_dialog

ScriptedDiplomaticActionsEditorDialog = make_simple_block_dialog(
    load_scripted_diplomatic_actions, "脚本化外交行动", "脚本化外交行动编辑器")


def open_scripted_diplomatic_actions_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示脚本化外交行动编辑器（非模态）。"""
    dlg = ScriptedDiplomaticActionsEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

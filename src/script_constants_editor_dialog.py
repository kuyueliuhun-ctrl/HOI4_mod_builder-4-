"""脚本常量专用编辑器（B3/P36，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_script_constants
from simple_block_editor import make_simple_block_dialog

ScriptConstantsEditorDialog = make_simple_block_dialog(
    load_script_constants, "脚本常量", "脚本常量编辑器")


def open_script_constants_editor(file_path="", mod_path="", hoi4_path="",
                                 entity_id=None, parent=None):
    """入口：加载并显示脚本常量编辑器（非模态）。"""
    dlg = ScriptConstantsEditorDialog(mod_path, hoi4_path,
                                      parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg
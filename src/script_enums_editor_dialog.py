"""枚举结构体编辑器专用编辑器（B2-P17，共享 RawBlockEditor）。"""

from __future__ import annotations

from ai_loader import load_script_enums
from raw_block_editor import make_raw_block_dialog

ScriptEnumsEditorDialog = make_raw_block_dialog(
    load_script_enums, "枚举结构体", "枚举结构体编辑器")


def open_script_enums_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示枚举结构体编辑器（非模态）。"""
    dlg = ScriptEnumsEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

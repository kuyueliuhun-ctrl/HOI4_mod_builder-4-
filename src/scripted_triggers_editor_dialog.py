"""条件结构体编辑器专用编辑器（B2-P17，共享 RawBlockEditor）。"""

from __future__ import annotations

from ai_loader import load_scripted_triggers
from raw_block_editor import make_raw_block_dialog

ScriptedTriggersEditorDialog = make_raw_block_dialog(
    load_scripted_triggers, "条件结构体", "条件结构体编辑器")


def open_scripted_triggers_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示条件结构体编辑器（非模态）。"""
    dlg = ScriptedTriggersEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

"""效果结构体编辑器专用编辑器（B2-P17，共享 RawBlockEditor）。"""

from __future__ import annotations

from ai_loader import load_scripted_effects
from raw_block_editor import make_raw_block_dialog

ScriptedEffectsEditorDialog = make_raw_block_dialog(
    load_scripted_effects, "效果结构体", "效果结构体编辑器")


def open_scripted_effects_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示效果结构体编辑器（非模态）。"""
    dlg = ScriptedEffectsEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

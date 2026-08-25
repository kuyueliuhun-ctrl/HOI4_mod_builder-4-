"""游戏定义专用编辑器（B2/B3，RawBlockEditor 原始块）。"""

from __future__ import annotations

from ai_loader import load_defines
from raw_block_editor import make_raw_block_dialog

DefinesEditorDialog = make_raw_block_dialog(
    load_defines, "游戏定义", "游戏定义编辑器")


def open_defines_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示游戏定义编辑器（非模态）。"""
    dlg = DefinesEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

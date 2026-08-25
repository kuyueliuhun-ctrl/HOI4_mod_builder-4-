"""命名列表专用编辑器（B2/B3，RawBlockEditor 原始块）。"""

from __future__ import annotations

from ai_loader import load_names
from raw_block_editor import make_raw_block_dialog

NamesEditorDialog = make_raw_block_dialog(
    load_names, "命名列表", "命名列表编辑器")


def open_names_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示命名列表编辑器（非模态）。"""
    dlg = NamesEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

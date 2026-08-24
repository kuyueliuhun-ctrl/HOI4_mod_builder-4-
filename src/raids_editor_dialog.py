"""突袭编辑器专用编辑器（B2/B3，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_raids
from simple_block_editor import make_simple_block_dialog

RaidsEditorDialog = make_simple_block_dialog(
    load_raids, "突袭", "突袭编辑器")


def open_raids_editor(file_path="", mod_path="", hoi4_path="",
            entity_id=None, parent=None):
    """入口：加载并显示突袭编辑器（非模态）。"""
    dlg = RaidsEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

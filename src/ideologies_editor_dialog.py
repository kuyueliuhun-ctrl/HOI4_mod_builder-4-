"""意识形态编辑器专用编辑器（B2/B3，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_ideologies
from simple_block_editor import make_simple_block_dialog

IdeologiesEditorDialog = make_simple_block_dialog(
    load_ideologies, "意识形态", "意识形态编辑器")


def open_ideologies_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示意识形态编辑器（非模态）。"""
    dlg = IdeologiesEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

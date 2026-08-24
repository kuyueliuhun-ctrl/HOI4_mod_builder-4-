"""科技共享专用编辑器（B3/P38，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_technology_sharing
from simple_block_editor import make_simple_block_dialog

TechnologySharingEditorDialog = make_simple_block_dialog(
    load_technology_sharing, "科技共享", "科技共享编辑器")


def open_technology_sharing_editor(file_path="", mod_path="", hoi4_path="",
                                   entity_id=None, parent=None):
    """入口：加载并显示科技共享编辑器（非模态）。"""
    dlg = TechnologySharingEditorDialog(mod_path, hoi4_path,
                                        parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg
"""事件修正专用编辑器（B2/B3，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_event_modifiers
from simple_block_editor import make_simple_block_dialog

EventModifiersEditorDialog = make_simple_block_dialog(
    load_event_modifiers, "事件修正", "事件修正编辑器")


def open_event_modifiers_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示事件修正编辑器（非模态）。"""
    dlg = EventModifiersEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

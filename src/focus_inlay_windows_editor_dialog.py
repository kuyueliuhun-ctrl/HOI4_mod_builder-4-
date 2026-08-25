"""国策内嵌窗口专用编辑器（B2/B3）。"""

from __future__ import annotations

from ai_loader import load_focus_inlay_windows
from simple_block_editor import make_simple_block_dialog

FocusInlayWindowsEditorDialog = make_simple_block_dialog(
    load_focus_inlay_windows, "国策内嵌窗口", "国策内嵌窗口编辑器")


def open_focus_inlay_windows_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示国策内嵌窗口编辑器（非模态）。"""
    dlg = FocusInlayWindowsEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

"""剧本专用编辑器（B3/P37，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_bookmarks
from simple_block_editor import make_simple_block_dialog

BookmarksEditorDialog = make_simple_block_dialog(
    load_bookmarks, "剧本", "剧本编辑器")


def open_bookmarks_editor(file_path="", mod_path="", hoi4_path="",
                          entity_id=None, parent=None):
    """入口：加载并显示剧本编辑器（非模态）。"""
    dlg = BookmarksEditorDialog(mod_path, hoi4_path,
                                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg
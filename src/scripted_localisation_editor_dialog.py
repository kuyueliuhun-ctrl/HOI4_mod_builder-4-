"""脚本化本地化专用编辑器（B3/P36，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_scripted_localisation
from simple_block_editor import make_simple_block_dialog

ScriptedLocalisationEditorDialog = make_simple_block_dialog(
    load_scripted_localisation, "脚本化本地化", "脚本化本地化编辑器")


def open_scripted_localisation_editor(file_path="", mod_path="", hoi4_path="",
                                      entity_id=None, parent=None):
    """入口：加载并显示脚本化本地化编辑器（非模态）。"""
    dlg = ScriptedLocalisationEditorDialog(mod_path, hoi4_path,
                                           parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg
"""难度设置专用编辑器（B3/P33，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_difficulty_settings
from simple_block_editor import make_simple_block_dialog

DifficultySettingsEditorDialog = make_simple_block_dialog(
    load_difficulty_settings, "难度设置", "难度设置编辑器")


def open_difficulty_settings_editor(file_path="", mod_path="", hoi4_path="",
                                   entity_id=None, parent=None):
    """入口：加载并显示难度设置编辑器（非模态）。"""
    dlg = DifficultySettingsEditorDialog(mod_path, hoi4_path,
                                         parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg
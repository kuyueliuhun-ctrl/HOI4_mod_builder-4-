"""游戏规则专用编辑器（B3/P33，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_game_rules
from simple_block_editor import make_simple_block_dialog

GameRulesEditorDialog = make_simple_block_dialog(
    load_game_rules, "游戏规则", "游戏规则编辑器")


def open_game_rules_editor(file_path="", mod_path="", hoi4_path="",
                           entity_id=None, parent=None):
    """入口：加载并显示游戏规则编辑器（非模态）。"""
    dlg = GameRulesEditorDialog(mod_path, hoi4_path,
                                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg
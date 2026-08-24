"""国家领袖编辑器专用编辑器（B2/B3，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_country_leader
from simple_block_editor import make_simple_block_dialog

CountryLeaderEditorDialog = make_simple_block_dialog(
    load_country_leader, "国家领袖", "国家领袖编辑器")


def open_country_leader_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示国家领袖编辑器（非模态）。"""
    dlg = CountryLeaderEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

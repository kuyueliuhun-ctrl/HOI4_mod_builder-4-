"""国家别名专用编辑器（B3/P38，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_country_tag_aliases
from simple_block_editor import make_simple_block_dialog

CountryTagAliasesEditorDialog = make_simple_block_dialog(
    load_country_tag_aliases, "国家别名", "国家别名编辑器")


def open_country_tag_aliases_editor(file_path="", mod_path="", hoi4_path="",
                                    entity_id=None, parent=None):
    """入口：加载并显示国家别名编辑器（非模态）。"""
    dlg = CountryTagAliasesEditorDialog(mod_path, hoi4_path,
                                        parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg
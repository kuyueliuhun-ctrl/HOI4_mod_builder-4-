"""科学家特质专用编辑器（B2/B3，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_scientist_traits
from simple_block_editor import make_simple_block_dialog

ScientistTraitsEditorDialog = make_simple_block_dialog(
    load_scientist_traits, "科学家特质", "科学家特质编辑器")


def open_scientist_traits_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示科学家特质编辑器（非模态）。"""
    dlg = ScientistTraitsEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

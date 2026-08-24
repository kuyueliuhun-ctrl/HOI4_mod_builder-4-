"""行动令牌编辑器专用编辑器（B2/B3，通用 SimpleBlockEditorDialog 落地）。"""

from __future__ import annotations

from ai_loader import load_operation_tokens
from simple_block_editor import make_simple_block_dialog

OperationTokensEditorDialog = make_simple_block_dialog(
    load_operation_tokens, "行动令牌", "行动令牌编辑器")


def open_operation_tokens_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示行动令牌编辑器（非模态）。"""
    dlg = OperationTokensEditorDialog(mod_path, hoi4_path,
                parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg

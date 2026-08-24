"""通用嵌套实体编辑器（B3 复杂类型：wrapper → 实体块）。

复用 SimpleBlockEditorDialog 的侧栏+表单+CRUD 骨架，仅覆写块级操作：
保存字段 / 新建 / 复制 / 改名 / 删除都定位到 wrapper 内的实体块，
支持 id_field（块内标量字段作实体 id）与嵌套深度。
"""

from __future__ import annotations

from nested_block_crud import (
    delete_nested_block,
    duplicate_nested_block,
    insert_nested_block,
    rename_nested_block,
    replace_nested_block_fields,
)
from simple_block_editor import SimpleBlockEditorDialog


class NestedBlockEditorDialog(SimpleBlockEditorDialog):
    """wrapper → 实体块的通用嵌套编辑器。"""

    def __init__(self, loader, list_title, window_title, mod_path="",
                 hoi4_path="", parent=None, initial_id=None,
                 id_field=None, depth=1):
        self.id_field = id_field
        self.depth = depth
        super().__init__(loader, list_title, window_title, mod_path,
                         hoi4_path, parent, initial_id)

    def _parent_id_for(self, entity_id=None):
        eid = entity_id or self.tab.sidebar.current_id() or None
        if eid and eid in self.entities:
            pid = self.entities[eid].get("parent_id")
            if pid:
                return pid
        for ent in self.entities.values():
            pid = ent.get("parent_id")
            if pid:
                return pid
        return None

    # ---------- 块级操作覆写 ----------

    def _block_op_replace(self, content, ent_id, fields):
        parent = self._parent_id_for(ent_id)
        return replace_nested_block_fields(
            content, ent_id, fields, parent_id=parent,
            id_field=self.id_field, depth=self.depth)

    def _block_op_insert(self, content, new_id, after_id=None):
        parent = self._parent_id_for(after_id)
        if self.id_field:
            body = "\t%s = %s\n" % (self.id_field, new_id)
        else:
            body = ""
        block_text = "%s = {\n%s\t}\n" % (new_id, body)
        return insert_nested_block(
            content, new_id, block_text, parent_id=parent,
            id_field=self.id_field, depth=self.depth, after_id=after_id)

    def _block_op_duplicate(self, content, cur_id, new_id):
        parent = self._parent_id_for(cur_id)
        return duplicate_nested_block(
            content, cur_id, new_id, parent_id=parent,
            id_field=self.id_field, depth=self.depth)

    def _block_op_rename(self, content, cur_id, new_id):
        parent = self._parent_id_for(cur_id)
        return rename_nested_block(
            content, cur_id, new_id, parent_id=parent,
            id_field=self.id_field, depth=self.depth)

    def _block_op_delete(self, content, cur_id):
        parent = self._parent_id_for(cur_id)
        return delete_nested_block(
            content, cur_id, parent_id=parent,
            id_field=self.id_field, depth=self.depth)


def make_nested_block_dialog(loader, list_title, window_title,
                             id_field=None, depth=1):
    """返回可被路由使用的嵌套编辑器对话框类。"""

    class _Dialog(NestedBlockEditorDialog):
        def __init__(self, mod_path="", hoi4_path="", parent=None,
                     initial_id=None):
            super().__init__(loader, list_title, window_title,
                             mod_path, hoi4_path, parent, initial_id,
                             id_field=id_field, depth=depth)

    return _Dialog

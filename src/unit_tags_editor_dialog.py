"""部队标签专用编辑器（B3/P38，simple_entity_tab 动态字段）。

common/unit_tags/*.txt 每个顶层块 = 一个部队标签（标量字段），
以动态 text 表单展示；保存走 replace_top_block_fields 写回。
"""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QMessageBox, QVBoxLayout

from ai_loader import load_unit_tags, replace_top_block_fields
from simple_entity_tab import SimpleEntityTab
from state_build_ops import ensure_file_in_mod
from write_utils import atomic_write_text

SKIP_KEYS = {"id", "raw", "file", "rel"}


class UnitTagsEditorDialog(QDialog):
    """部队标签编辑器。"""

    def __init__(self, tags, mod_path="", hoi4_path="", parent=None,
                 initial_id=None):
        super().__init__(parent)
        self.tags = tags
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.setWindowTitle("部队标签编辑器")
        self.resize(1080, 680)

        all_keys = []
        for ent in tags.values():
            for k in ent:
                if k not in SKIP_KEYS and k not in all_keys:
                    all_keys.append(k)
        fields = [{"key": k, "label": k, "type": "text"} for k in all_keys]

        entities = []
        for uid, ent in tags.items():
            e = {"id": uid, "name": uid}
            for k in all_keys:
                e[k] = ent.get(k, "")
            e["rel"] = ent.get("rel", "")
            entities.append(e)

        root = QVBoxLayout(self)
        self.tab = SimpleEntityTab(entities, fields, self.mod_path,
                                   self.hoi4_path, parent=self,
                                   list_title="部队标签")
        self.tab.saved.connect(self._on_save)
        root.addWidget(self.tab)
        if initial_id:
            self.tab.sidebar.set_current(initial_id)

    def _on_save(self):
        if self.tab._current is None:
            return
        ent = self.tab._current
        rel = ent.get("rel", "")
        if not rel:
            return
        mod_fp, copied = ensure_file_in_mod(self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位部队标签文件")
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        values = self.tab.values()
        fields = {k: v for k, v in values.items() if v != ""}
        content = replace_top_block_fields(content, ent["id"], fields)
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        for k, v in fields.items():
            ent[k] = v
        msg = "已保存部队标签 %s" % ent["id"]
        if copied:
            msg += "\n原版文件已自动复制到 mod"
        QMessageBox.information(self, "已保存", msg)


def open_unit_tags_editor(file_path="", mod_path="", hoi4_path="",
                          entity_id=None, parent=None):
    """入口：加载并显示部队标签编辑器（非模态）。"""
    tags = load_unit_tags(mod_path, hoi4_path)
    dlg = UnitTagsEditorDialog(tags, mod_path, hoi4_path,
                               parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg
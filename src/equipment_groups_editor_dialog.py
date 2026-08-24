"""装备组专用编辑器（B3/P38，simple_entity_tab 动态字段）。

common/equipment_groups/*.txt 每个顶层块 = 一个装备组（标量字段），
以动态 text 表单展示；保存走 replace_top_block_fields 写回。
"""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QMessageBox, QVBoxLayout

from ai_loader import load_equipment_groups2, replace_top_block_fields
from simple_entity_tab import SimpleEntityTab
from state_build_ops import ensure_file_in_mod
from write_utils import atomic_write_text

SKIP_KEYS = {"id", "raw", "file", "rel"}


class EquipmentGroupsEditorDialog(QDialog):
    """装备组编辑器。"""

    def __init__(self, groups, mod_path="", hoi4_path="", parent=None,
                 initial_id=None):
        super().__init__(parent)
        self.groups = groups
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.setWindowTitle("装备组编辑器")
        self.resize(1080, 680)

        all_keys = []
        for ent in groups.values():
            for k in ent:
                if k not in SKIP_KEYS and k not in all_keys:
                    all_keys.append(k)
        fields = [{"key": k, "label": k, "type": "text"} for k in all_keys]

        entities = []
        for gid, ent in groups.items():
            e = {"id": gid, "name": gid}
            for k in all_keys:
                e[k] = ent.get(k, "")
            e["rel"] = ent.get("rel", "")
            entities.append(e)

        root = QVBoxLayout(self)
        self.tab = SimpleEntityTab(entities, fields, self.mod_path,
                                   self.hoi4_path, parent=self,
                                   list_title="装备组")
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
            QMessageBox.warning(self, "保存失败", "无法定位装备组文件")
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
        msg = "已保存装备组 %s" % ent["id"]
        if copied:
            msg += "\n原版文件已自动复制到 mod"
        QMessageBox.information(self, "已保存", msg)


def open_equipment_groups_editor(file_path="", mod_path="", hoi4_path="",
                                 entity_id=None, parent=None):
    """入口：加载并显示装备组编辑器（非模态）。"""
    groups = load_equipment_groups2(mod_path, hoi4_path)
    dlg = EquipmentGroupsEditorDialog(groups, mod_path, hoi4_path,
                                      parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg
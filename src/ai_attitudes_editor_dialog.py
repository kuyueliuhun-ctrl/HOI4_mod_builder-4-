"""AI 态度专用编辑器（B1 P16，simple_entity_tab 落地）。

common/ai_attitudes/*.txt 中每个顶层块 = 一个国家/条件的态度：
一堆布尔 flag（yes/no）。用 SimpleEntityTab 的 select 字段编辑，
保存走 replace_top_block_fields 写回文件（原版自动复制到 mod）。
"""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QMessageBox

from ai_loader import load_ai_attitudes, replace_top_block_fields
from simple_entity_tab import SimpleEntityTab
from state_build_ops import ensure_file_in_mod
from write_utils import atomic_write_text

# AI 态度常用布尔 flag（yes/no；未知字段仍可走树形编辑器兜底）
ATTITUDE_FLAGS = (
    "use_military_force", "send_volunteers", "lend_lease", "join_faction",
    "declare_war", "guarantee", "improve_relations", "send_attaché",
    "trade", "share_technology", "military_access",
)


class AiAttitudesEditorDialog(QDialog):
    """AI 态度编辑器。"""

    def __init__(self, attitudes, mod_path="", hoi4_path="", parent=None,
                 initial_id=None):
        super().__init__(parent)
        self.attitudes = attitudes
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.setWindowTitle("AI 态度编辑器")
        self.resize(1080, 680)

        fields = []
        for flag in ATTITUDE_FLAGS:
            fields.append({
                "key": flag,
                "label": flag,
                "type": "select",
                "options": ["yes", "no", ""],
            })
        entities = []
        for aid, att in attitudes.items():
            ent = {"id": aid, "name": aid}
            for flag in ATTITUDE_FLAGS:
                ent[flag] = att.get(flag, "")
            entities.append(ent)

        from PyQt6.QtWidgets import QVBoxLayout
        root = QVBoxLayout(self)
        self.tab = SimpleEntityTab(entities, fields, self.mod_path,
                                   self.hoi4_path, parent=self,
                                   list_title="态度")
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
            QMessageBox.warning(self, "保存失败", "无法定位 AI 态度文件")
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        values = self.tab.values()
        fields = {k: v for k, v in values.items() if k in ATTITUDE_FLAGS}
        content = replace_top_block_fields(content, ent["id"], fields)
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        for k, v in fields.items():
            ent[k] = v
        msg = "已保存 AI 态度 %s" % ent["id"]
        if copied:
            msg += "\n原版文件已自动复制到 mod"
        QMessageBox.information(self, "已保存", msg)


def open_ai_attitudes_editor(file_path="", mod_path="", hoi4_path="",
                             entity_id=None, parent=None):
    """入口：加载并显示 AI 态度编辑器（非模态）。"""
    attitudes = load_ai_attitudes(mod_path, hoi4_path)
    dlg = AiAttitudesEditorDialog(attitudes, mod_path, hoi4_path,
                                  parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg
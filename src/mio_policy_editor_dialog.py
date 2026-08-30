"""MIO 方针（Policy）编辑器（UI/信号槽层）。

按游戏内方针弹窗：方针列表 + 图标选择 + 条件/加成原始块编辑，
支持新增/复制/改名/删除。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from ai_ui_common import EntityListSidebar
from mio_loader import (
    delete_policy,
    duplicate_policy,
    insert_policy,
    load_mio_policies,
    policy_to_pdx,
    rename_policy,
    replace_policy_block,
)
from mio_ui_theme import BannerWidget
from state_build_ops import ensure_file_in_mod
from write_utils import atomic_write_text


class MioPolicyEditorDialog(QDialog):
    """MIO 方针编辑器（主题与编辑器全局主题一致）。"""

    def __init__(self, mod_path="", hoi4_path="", parent=None,
                 initial_id=None):
        super().__init__(parent)
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.setWindowTitle("MIO 方针编辑器")
        self.resize(980, 700)

        self.policies = {}
        self._current_id = None
        self._gfx_map = self._make_gfx_map()

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.sidebar = EntityListSidebar("MIO 方针", self)
        self.sidebar.set_paths(self.mod_path, self.hoi4_path)
        self.sidebar.currentChanged.connect(self._on_policy_changed)
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        self.banner = BannerWidget(self.mod_path, self.hoi4_path)
        self.title_label = self.banner.title_label
        right.addWidget(self.banner)

        icon_row = QHBoxLayout()
        self.icon_edit = QLineEdit()
        self.icon_edit.setPlaceholderText("icon（GFX_...）")
        icon_row.addWidget(QLabel("图标"))
        icon_row.addWidget(self.icon_edit, 1)
        self.icon_btn = QPushButton("🖼 选图标")
        self.icon_btn.clicked.connect(self._pick_icon)
        icon_row.addWidget(self.icon_btn)
        right.addLayout(icon_row)

        self.allowed_edit = QPlainTextEdit()
        self.allowed_edit.setPlaceholderText("allowed 原始块（含外层）")
        right.addWidget(QLabel("allowed"))
        right.addWidget(self.allowed_edit, 1)
        self.available_edit = QPlainTextEdit()
        self.available_edit.setPlaceholderText("available 原始块（含外层）")
        right.addWidget(QLabel("available"))
        right.addWidget(self.available_edit, 1)
        self.equip_edit = QPlainTextEdit()
        self.equip_edit.setPlaceholderText("equipment_bonus 原始块（含外层）")
        right.addWidget(QLabel("equipment_bonus"))
        right.addWidget(self.equip_edit, 1)
        self.prod_edit = QPlainTextEdit()
        self.prod_edit.setPlaceholderText("production_bonus 原始块（含外层）")
        right.addWidget(QLabel("production_bonus"))
        right.addWidget(self.prod_edit, 1)
        self.org_edit = QPlainTextEdit()
        self.org_edit.setPlaceholderText("organization_modifier 原始块（含外层）")
        right.addWidget(QLabel("organization_modifier"))
        right.addWidget(self.org_edit, 1)

        btns = QHBoxLayout()
        for label, fn in (("💾 保存", self._on_save),
                          ("＋新增", self._on_add),
                          ("⧉复制", self._on_dup),
                          ("✎改名", self._on_rename),
                          ("🗑删除", self._on_delete)):
            b = QPushButton(label)
            b.clicked.connect(fn)
            btns.addWidget(b)
        btns.addStretch(1)
        right.addLayout(btns)
        root.addLayout(right, 1)

        self._reload(initial_id)

    # ---------- 依赖 ----------

    def _make_gfx_map(self):
        gfx = {}
        try:
            from gui_translator import get_translator, scan_gfx_folder
            gfx = dict(get_translator().gfx_map)
            if self.mod_path:
                scan_gfx_folder(self.mod_path, gfx)
        except Exception:
            pass
        return gfx

    # ---------- 数据流 ----------

    def _reload(self, select_id=None):
        self.policies = load_mio_policies(self.mod_path, self.hoi4_path)
        labels = [(pid, p.get("name", pid)) for pid, p in self.policies.items()]
        self.sidebar.set_entities(labels)
        if select_id:
            self.sidebar.set_current(select_id)
        elif self.sidebar.list.count():
            self.sidebar.set_current(
                self.sidebar.list.item(0).data(Qt.ItemDataRole.UserRole))

    def _on_policy_changed(self, policy_id):
        self._current_id = policy_id
        self.title_label.setText(policy_id or "—")
        p = self.policies.get(policy_id)
        if not p:
            self._clear_form()
            return
        self.icon_edit.setText(p.get("icon", ""))
        self.allowed_edit.setPlainText(p.get("allowed", ""))
        self.available_edit.setPlainText(p.get("available", ""))
        self.equip_edit.setPlainText(p.get("equipment_bonus", ""))
        self.prod_edit.setPlainText(p.get("production_bonus", ""))
        self.org_edit.setPlainText(p.get("organization_modifier", ""))

    def _clear_form(self):
        self.icon_edit.setText("")
        for w in (self.allowed_edit, self.available_edit, self.equip_edit,
                  self.prod_edit, self.org_edit):
            w.setPlainText("")

    def _form_block(self, policy_id):
        return policy_to_pdx(
            policy_id,
            self.icon_edit.text().strip(),
            self.allowed_edit.toPlainText(),
            self.available_edit.toPlainText(),
            self.equip_edit.toPlainText(),
            self.prod_edit.toPlainText(),
            self.org_edit.toPlainText(),
        )

    # ---------- 写文件 ----------

    def _write_rel(self, rel, transform):
        if not rel:
            return False
        mod_fp, _copied = ensure_file_in_mod(self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位文件")
            return False
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        new_content = transform(content)
        try:
            atomic_write_text(mod_fp, new_content)
        except Exception as e:
            QMessageBox.warning(self, "写入失败", "写入失败：%s" % e)
            return False
        return True

    # ---------- 操作 ----------

    def _on_save(self):
        p = self.policies.get(self._current_id)
        if not p:
            return
        new_block = self._form_block(p["id"])
        def transform(content):
            return replace_policy_block(content, p["id"], new_block)
        if self._write_rel(p.get("rel", ""), transform):
            self._reload(p["id"])
            QMessageBox.information(self, "已保存", "已保存方针 %s" % p["id"])

    def _on_add(self):
        policy_id, ok = QInputDialog.getText(self, "新增方针", "新方针 id：")
        if not ok or not policy_id.strip():
            return
        policy_id = policy_id.strip()
        if policy_id in self.policies:
            QMessageBox.warning(self, "新增失败", "方针 id 已存在：%s" % policy_id)
            return
        after = self._current_id or None
        def transform(content):
            return insert_policy(content, policy_id, after_id=after)
        if self._write_rel(self._current_rel(), transform):
            self._reload(policy_id)

    def _on_dup(self):
        if not self._current_id:
            return
        new_id, ok = QInputDialog.getText(
            self, "复制方针", "新方针 id：", text=self._current_id + "_copy")
        if not ok or not new_id.strip():
            return
        new_id = new_id.strip()
        if new_id in self.policies:
            QMessageBox.warning(self, "复制失败", "方针 id 已存在：%s" % new_id)
            return
        def transform(content):
            return duplicate_policy(content, self._current_id, new_id)
        if self._write_rel(self._current_rel(), transform):
            self._reload(new_id)

    def _on_rename(self):
        if not self._current_id:
            return
        new_id, ok = QInputDialog.getText(
            self, "重命名方针", "新方针 id：", text=self._current_id)
        if not ok or not new_id.strip() or new_id.strip() == self._current_id:
            return
        new_id = new_id.strip()
        def transform(content):
            return rename_policy(content, self._current_id, new_id)
        if self._write_rel(self._current_rel(), transform):
            self._reload(new_id)

    def _on_delete(self):
        if not self._current_id:
            return
        ret = QMessageBox.question(
            self, "删除方针", "确定删除 %s ？" % self._current_id,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        def transform(content):
            return delete_policy(content, self._current_id)
        if self._write_rel(self._current_rel(), transform):
            self._reload()

    def _current_rel(self):
        p = self.policies.get(self._current_id)
        if p and p.get("rel"):
            return p["rel"]
        for p in self.policies.values():
            if p.get("rel"):
                return p["rel"]
        return ""

    # ---------- 图标 ----------

    def _pick_icon(self):
        from icon_picker_dialog import IconPickerDialog
        dlg = IconPickerDialog(
            self._gfx_map, parent=self, prefix="GFX_mio_policy_",
            current_icon=self.icon_edit.text().strip())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = dlg.get_selected_icon()
            if name:
                self.icon_edit.setText(name)


def open_mio_policy_editor(file_path="", mod_path="", hoi4_path="",
                           entity_id=None, parent=None):
    """入口：加载并显示 MIO 方针编辑器（非模态）。"""
    dlg = MioPolicyEditorDialog(mod_path, hoi4_path, parent=parent,
                                initial_id=entity_id)
    dlg.show()
    return dlg

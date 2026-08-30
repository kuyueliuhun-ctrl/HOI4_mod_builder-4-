"""AI 师模板专用编辑器（完全专用 UI，不依赖树形编辑器页面）

- 左侧固定侧边栏：角色模板列表 + CRUD
- 中间：目标模板列表 + CRUD
- 右侧：目标详情（replace 字段 / target_template 用 DivisionEditor /
  高级脚本块 enable / can_upgrade_in_field / upgrade_prio）
- 保存：原版自动复制到 mod + 原子写
"""

from __future__ import annotations

import os
import tempfile

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMenu, QMessageBox, QPushButton, QToolButton,
    QVBoxLayout,
)

from ai_loader import (
    _AI_CACHE,
    delete_ai_template_role,
    delete_ai_template_target,
    duplicate_ai_template_role,
    duplicate_ai_template_target,
    insert_ai_template_role,
    insert_ai_template_target,
    load_ai_templates,
    rename_ai_template_role,
    rename_ai_template_target,
    replace_ai_template_target_field,
    replace_ai_template_target_template,
    replace_or_upsert_nested_child,
    replace_top_block_field,
    upsert_top_block_child,
)
from ai_ui_common import EntityListSidebar, ScriptBlockEditorDialog, file_tooltip
from division_editor import DivisionEditor
from oob_loader import OobFile, load_sub_units
from state_build_ops import ensure_file_in_mod
from write_utils import atomic_write_text

TARGET_ADVANCED = ("enable", "can_upgrade_in_field", "upgrade_prio")


def _target_template_to_division_text(target_template):
    """把 `target_template = { ... }` 转为可被 OobFile 解析的 division_template。"""
    text = (target_template or "").strip()
    if not text:
        text = "target_template = { }"
    if text.startswith("target_template"):
        text = "division_template" + text[len("target_template"):]
    idx = text.find("{")
    if idx >= 0:
        text = text[:idx + 1] + ' name = "ai_target"' + text[idx + 1:]
    return text


def _division_template_to_target_text(tpl):
    """把 DivisionTemplate 转回 `target_template = { ... }` 文本。"""
    lines = ["target_template = {"]
    if tpl.support:
        lines.append("\tsupport = {")
        for typ, x, y in tpl.support:
            lines.append("\t\t%s = { x = %s y = %s }" % (typ, x, y))
        lines.append("\t}")
    if tpl.regiments:
        lines.append("\tregiments = {")
        for typ, x, y in tpl.regiments:
            lines.append("\t\t%s = { x = %s y = %s }" % (typ, x, y))
        lines.append("\t}")
    lines.append("}")
    return "\n".join(lines)


def find_upgrade_cycle(role, start_target):
    """沿 replace_with 链检测成环，返回环路径；无环返回 []。"""
    if not role:
        return []
    by_id = {t.get("id", ""): t for t in role.get("targets", [])}
    seen = []
    cur = start_target
    while cur and cur in by_id:
        if cur in seen:
            idx = seen.index(cur)
            return seen[idx:] + [cur]
        seen.append(cur)
        cur = (by_id[cur].get("replace_with") or "").strip()
    return []


class AiDivisionTemplateEditor(DivisionEditor):
    """在 DivisionEditor 基础上拦截保存，写回 AI target_template。"""

    def __init__(self, oob_file, sub_units, mod_path, hoi4_path,
                 on_save, parent=None):
        self._ai_on_save = on_save
        super().__init__(oob_file, sub_units=sub_units, mod_path=mod_path,
                         hoi4_path=hoi4_path, parent=parent)

    def _save(self):
        if self.current is None:
            return
        try:
            target_text = _division_template_to_target_text(self.current)
            self._ai_on_save(target_text)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return
        QMessageBox.information(self, "已保存", "AI 目标编制已写回")
        self.accept()


class AiTemplateEditorDialog(QDialog):
    """AI 师模板专用编辑器。"""

    def __init__(self, roles, mod_path="", hoi4_path="", parent=None,
                 initial_role_id=None):
        super().__init__(parent)
        self.roles = roles
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self._current_role = None
        self._current_target = None
        self._target_advanced = {}
        self.setWindowTitle("AI 师模板编辑器")
        self.resize(1240, 740)
        self.setMinimumSize(1120, 660)
        self._build_ui()
        self._populate_roles(initial_role_id)

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # 左：角色侧边栏
        self.sidebar = EntityListSidebar("角色模板", self)
        self.sidebar.set_paths(self.mod_path, self.hoi4_path)
        self.sidebar.currentChanged.connect(self._on_role_changed)
        self.sidebar.createRequested.connect(self._create_role)
        self.sidebar.duplicateRequested.connect(self._duplicate_role)
        self.sidebar.renameRequested.connect(self._rename_role)
        self.sidebar.deleteRequested.connect(self._delete_role)
        root.addWidget(self.sidebar)
        self.role_list = self.sidebar.list

        # 中：目标模板
        middle = QVBoxLayout()
        middle.addWidget(QLabel("目标模板"))
        self.target_list = QListWidget()
        self.target_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.target_list.currentItemChanged.connect(self._on_target_changed)
        middle.addWidget(self.target_list, 1)
        tbtns = QHBoxLayout()
        add_t = QPushButton("＋")
        dup_t = QPushButton("⧉")
        ren_t = QPushButton("✎")
        del_t = QPushButton("🗑")
        add_t.setToolTip("新建目标模板")
        dup_t.setToolTip("复制目标模板")
        ren_t.setToolTip("重命名目标模板")
        del_t.setToolTip("删除目标模板")
        add_t.clicked.connect(self._create_target)
        dup_t.clicked.connect(self._duplicate_target)
        ren_t.clicked.connect(self._rename_target)
        del_t.clicked.connect(self._delete_target)
        for b in (add_t, dup_t, ren_t, del_t):
            tbtns.addWidget(b)
        tbtns.addStretch(1)
        middle.addLayout(tbtns)
        root.addLayout(middle, 2)

        # 右：目标详情
        right = QVBoxLayout()
        self.role_label = QLabel("—")
        self.role_label.setStyleSheet("font-weight:bold; font-size:14px;")
        right.addWidget(self.role_label)
        self.target_label = QLabel("—")
        right.addWidget(self.target_label)

        form = QHBoxLayout()
        form.addWidget(QLabel("replace_with"))
        self.replace_with_edit = QLineEdit()
        form.addWidget(self.replace_with_edit, 1)
        form.addWidget(QLabel("replace_at_match"))
        self.replace_at_match_edit = QLineEdit()
        self.replace_at_match_edit.setMaximumWidth(100)
        form.addWidget(self.replace_at_match_edit)
        right.addLayout(form)

        form2 = QHBoxLayout()
        form2.addWidget(QLabel("target_min_match"))
        self.target_min_match_edit = QLineEdit()
        form2.addWidget(self.target_min_match_edit, 1)
        tpl_btn = QPushButton("✏ 编辑目标编制（DivisionEditor）")
        tpl_btn.clicked.connect(self._edit_target_template)
        form2.addWidget(tpl_btn)
        right.addLayout(form2)

        self.cycle_label = QLabel("")
        self.cycle_label.setWordWrap(True)
        self.cycle_label.setStyleSheet("color:#b7791f; font-weight:bold;")
        right.addWidget(self.cycle_label)

        adv_label = QLabel("高级脚本块（enable / can_upgrade_in_field / upgrade_prio）")
        adv_label.setStyleSheet("font-weight:bold; color:#1f4f7e;")
        right.addWidget(adv_label)
        self.adv_buttons = {}
        for field in TARGET_ADVANCED:
            row = QHBoxLayout()
            row.addWidget(QLabel(field))
            btn = QPushButton("未编辑")
            btn.clicked.connect(
                lambda checked=False, f=field: self._edit_advanced(f))
            row.addWidget(btn, 1)
            self.adv_buttons[field] = btn
            right.addLayout(row)

        footer = QHBoxLayout()
        advanced_btn = QToolButton()
        advanced_btn.setText("高级 ▾")
        advanced_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        raw_menu = QMenu(advanced_btn)
        raw_act = raw_menu.addAction("高级：原始 PDX（兜底）")
        raw_act.triggered.connect(self._edit_raw)
        advanced_btn.setMenu(raw_menu)
        footer.addWidget(advanced_btn)
        footer.addStretch(1)
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save)
        footer.addWidget(save_btn)
        right.addLayout(footer)
        root.addLayout(right, 3)

    # ---------- 填充 ----------
    def _populate_roles(self, initial_role_id=None):
        items = [(rid, rid, file_tooltip(self.roles.get(rid), getattr(self, "mod_path", ""), getattr(self, "hoi4_path", ""))
                  or rid) for rid in sorted(self.roles)]
        self.sidebar.set_entities(items)
        if initial_role_id:
            self.sidebar.set_current(initial_role_id)
        elif self.sidebar.current_id() is None and self.sidebar.list.count():
            self.sidebar.set_current(self.sidebar.list.item(0).data(
                Qt.ItemDataRole.UserRole))

    def _on_role_changed(self, role_id):
        if role_id is None:
            self._current_role = None
            self.role_label.setText("—")
            self.target_list.clear()
            return
        role = self.roles.get(role_id)
        if not role:
            return
        self._current_role = role
        self.role_label.setText("%s  （%s）" % (role_id, role.get("file", "")))
        self.target_list.blockSignals(True)
        self.target_list.clear()
        for t in role.get("targets", []):
            item = QListWidgetItem(t.get("id", ""))
            item.setData(Qt.ItemDataRole.UserRole, t.get("id", ""))
            self.target_list.addItem(item)
        self.target_list.blockSignals(False)
        if self.target_list.count() > 0:
            self.target_list.setCurrentRow(0)
            self._on_target_changed(self.target_list.currentItem())
        else:
            self._current_target = None

    def _on_target_changed(self, item):
        if item is None or self._current_role is None:
            self._current_target = None
            self.target_label.setText("—")
            return
        tid = item.data(Qt.ItemDataRole.UserRole)
        self._current_target = tid
        target = self._find_target(tid)
        if not target:
            self.target_label.setText(tid)
            return
        self.target_label.setText("目标：%s" % tid)
        self.replace_with_edit.setText(target.get("replace_with", ""))
        self.replace_at_match_edit.setText(target.get("replace_at_match", ""))
        self.target_min_match_edit.setText(target.get("target_min_match", ""))
        self._target_advanced = {
            f: target.get(f, "") or "" for f in TARGET_ADVANCED}
        self._update_advanced_summaries()
        cycle = find_upgrade_cycle(self._current_role, tid)
        if cycle:
            self.cycle_label.setText(
                "⚠ 升级链成环：%s" % " → ".join(cycle))
        else:
            self.cycle_label.setText("")

    def _find_target(self, tid):
        if not self._current_role:
            return None
        for t in self._current_role.get("targets", []):
            if t.get("id") == tid:
                return t
        return None

    # ---------- 目标 CRUD ----------
    def _reload_roles(self, keep_role=None, keep_target=None):
        _AI_CACHE.pop(("ai_templates", self.mod_path or "",
                       self.hoi4_path or ""), None)
        self.roles = load_ai_templates(self.mod_path, self.hoi4_path)
        if self._current_role:
            norm = os.path.normpath(
                self._current_role.get("file", "")).replace("\\", "/")
            self.roles = {rid: r for rid, r in self.roles.items()
                          if os.path.normpath(r.get("file", "")).replace("\\", "/") == norm}
        self._populate_roles(keep_role)
        if keep_role and keep_target:
            self.sidebar.set_current(keep_role)
            self._select_target(keep_target)

    def _select_target(self, tid):
        for i in range(self.target_list.count()):
            if self.target_list.item(i).data(Qt.ItemDataRole.UserRole) == tid:
                self.target_list.setCurrentRow(i)
                return True
        return False

    def _write_current_file(self, content):
        role = self._current_role
        if not role:
            return None, False
        rel = role.get("rel", "")
        if not rel:
            return None, False
        mod_fp, copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            return None, False
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return None, False
        return mod_fp, copied

    def _create_target(self):
        if not self._current_role:
            return
        role = self._current_role
        new_id, ok = QInputDialog.getText(self, "新建目标模板", "目标 ID：")
        if not ok or not new_id.strip():
            return
        if any(t.get("id") == new_id.strip() for t in role.get("targets", [])):
            QMessageBox.warning(self, "错误", "目标已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, role.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = insert_ai_template_target(content, role["id"], new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload_roles(role["id"], new_id.strip())

    def _duplicate_target(self):
        if not self._current_target:
            return
        old_id = self._current_target
        new_id, ok = QInputDialog.getText(
            self, "复制目标模板", "新目标 ID：", text=old_id + "_copy")
        if not ok or not new_id.strip():
            return
        if any(t.get("id") == new_id.strip()
               for t in self._current_role.get("targets", [])):
            QMessageBox.warning(self, "错误", "目标已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_role.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = duplicate_ai_template_target(
            content, self._current_role["id"], old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload_roles(self._current_role["id"], new_id.strip())

    def _rename_target(self):
        if not self._current_target:
            return
        old_id = self._current_target
        new_id, ok = QInputDialog.getText(
            self, "重命名目标模板", "新目标 ID：", text=old_id)
        if not ok or not new_id.strip() or new_id.strip() == old_id:
            return
        if any(t.get("id") == new_id.strip()
               for t in self._current_role.get("targets", [])):
            QMessageBox.warning(self, "错误", "目标已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_role.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = rename_ai_template_target(
            content, self._current_role["id"], old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload_roles(self._current_role["id"], new_id.strip())

    def _delete_target(self):
        if not self._current_target:
            return
        reply = QMessageBox.question(
            self, "确认", "确定要删除目标模板 '%s' 吗？" % self._current_target)
        if reply != QMessageBox.StandardButton.Yes:
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_role.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = delete_ai_template_target(
            content, self._current_role["id"], self._current_target)
        atomic_write_text(mod_fp, content)
        self._reload_roles(self._current_role["id"])

    # ---------- 角色 CRUD ----------
    def _create_role(self):
        if not self._current_role:
            return
        new_id, ok = QInputDialog.getText(self, "新建角色模板", "角色 ID：")
        if not ok or not new_id.strip():
            return
        if new_id.strip() in self.roles:
            QMessageBox.warning(self, "错误", "角色已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_role.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = insert_ai_template_role(content, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload_roles(new_id.strip())

    def _duplicate_role(self):
        if not self._current_role:
            return
        old_id = self._current_role["id"]
        new_id, ok = QInputDialog.getText(
            self, "复制角色模板", "新角色 ID：", text=old_id + "_copy")
        if not ok or not new_id.strip():
            return
        if new_id.strip() in self.roles:
            QMessageBox.warning(self, "错误", "角色已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_role.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = duplicate_ai_template_role(
            content, old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload_roles(new_id.strip())

    def _rename_role(self):
        if not self._current_role:
            return
        old_id = self._current_role["id"]
        new_id, ok = QInputDialog.getText(
            self, "重命名角色模板", "新角色 ID：", text=old_id)
        if not ok or not new_id.strip() or new_id.strip() == old_id:
            return
        if new_id.strip() in self.roles:
            QMessageBox.warning(self, "错误", "角色已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_role.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = rename_ai_template_role(content, old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload_roles(new_id.strip())

    def _delete_role(self):
        if not self._current_role:
            return
        reply = QMessageBox.question(
            self, "确认", "确定要删除角色模板 '%s' 吗？" % self._current_role["id"])
        if reply != QMessageBox.StandardButton.Yes:
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_role.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = delete_ai_template_role(content, self._current_role["id"])
        atomic_write_text(mod_fp, content)
        self._reload_roles()

    # ---------- 高级块 / 原始 ----------
    def _update_advanced_summaries(self):
        for field in TARGET_ADVANCED:
            text = (self._target_advanced.get(field) or "").strip()
            self.adv_buttons[field].setText(
                "空" if not text else "已编辑（%d 行）" % len(text.splitlines()))

    def _edit_advanced(self, field):
        from gui_translator import get_translator
        from focus_view import CUSTOM_STATEMENT_PATH
        dlg = ScriptBlockEditorDialog(
            block_text=self._target_advanced.get(field, ""),
            block_key=field,
            translator=get_translator(),
            custom_statement_path=CUSTOM_STATEMENT_PATH,
            parent=self,
            title="编辑 %s" % field,
        )
        if dlg.exec():
            self._target_advanced[field] = dlg.get_block_text()
            self._update_advanced_summaries()

    def _edit_raw(self):
        target = self._find_target(self._current_target) if self._current_target else None
        if not target:
            return
        from gui_translator import get_translator
        from focus_view import CUSTOM_STATEMENT_PATH
        dlg = ScriptBlockEditorDialog(
            block_text=target.get("raw", ""),
            block_key=self._current_target,
            translator=get_translator(),
            custom_statement_path=CUSTOM_STATEMENT_PATH,
            parent=self,
            title="AI 师模板目标 - %s" % self._current_target,
        )
        if dlg.exec():
            target["raw"] = dlg.get_block_text()

    def _edit_target_template(self):
        target = self._find_target(self._current_target) if self._current_target else None
        if not target:
            return
        target_text = target.get("target_template", "")
        tmp_dir = tempfile.mkdtemp(prefix="dsh_ai_tpl_")
        tmp_path = os.path.join(tmp_dir, "ai_target.txt")
        try:
            atomic_write_text(tmp_path, _target_template_to_division_text(target_text))
            oob = OobFile(tmp_path)
        except Exception as e:
            QMessageBox.warning(self, "无法打开", "转换 AI 目标编制失败：%s" % e)
            return
        sub_units = load_sub_units(self.mod_path, self.hoi4_path)
        role_id = self._current_role["id"]
        target_id = self._current_target

        def on_save(new_target_text):
            self._write_target(role_id, target_id, new_target_text)

        editor = AiDivisionTemplateEditor(
            oob, sub_units, self.mod_path, self.hoi4_path,
            on_save, parent=self)
        editor.exec()
        try:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

    def _write_target(self, role_id, target_id, new_target_text):
        role = self._current_role
        if not role:
            return
        rel = role.get("rel", "")
        if not rel:
            return
        mod_fp, copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = replace_ai_template_target_template(
            content, role_id, target_id, new_target_text)
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        target = self._find_target(target_id)
        if target:
            target["target_template"] = new_target_text

    # ---------- 保存 ----------
    def _save(self):
        role = self._current_role
        if not role or not self._current_target:
            return
        target_id = self._current_target
        target = self._find_target(target_id)
        if not target:
            return
        rel = role.get("rel", "")
        if not rel:
            return
        mod_fp, copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位 AI 师模板文件")
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = replace_ai_template_target_field(
            content, role["id"], target_id, "replace_with",
            self.replace_with_edit.text().strip())
        content = replace_ai_template_target_field(
            content, role["id"], target_id, "replace_at_match",
            self.replace_at_match_edit.text().strip())
        content = replace_ai_template_target_field(
            content, role["id"], target_id, "target_min_match",
            self.target_min_match_edit.text().strip())
        for field in TARGET_ADVANCED:
            text = (self._target_advanced.get(field) or "").strip()
            if text:
                content = replace_or_upsert_nested_child(
                    content, role["id"], target_id, field, text)
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        target["replace_with"] = self.replace_with_edit.text().strip()
        target["replace_at_match"] = self.replace_at_match_edit.text().strip()
        target["target_min_match"] = self.target_min_match_edit.text().strip()
        for field in TARGET_ADVANCED:
            if field in self._target_advanced:
                target[field] = self._target_advanced.get(field, "")
        msg = "已保存 AI 师模板 %s / %s" % (role["id"], target_id)
        if copied:
            msg += "\n原版文件已自动复制到 mod"
        QMessageBox.information(self, "已保存", msg)


def open_ai_template_editor(file_path, mod_path="", hoi4_path="",
                            entity_id=None, parent=None):
    """按文件/实体打开 AI 师模板编辑器。"""
    roles = load_ai_templates(mod_path, hoi4_path)
    norm = os.path.normpath(file_path).replace("\\", "/")
    file_roles = {}
    for rid, role in roles.items():
        if os.path.normpath(role.get("file", "")).replace("\\", "/") == norm:
            file_roles[rid] = role
    if not file_roles:
        return False
    dlg = AiTemplateEditorDialog(
        file_roles, mod_path, hoi4_path, parent,
        initial_role_id=entity_id if entity_id in file_roles else None)
    dlg.exec()
    return True

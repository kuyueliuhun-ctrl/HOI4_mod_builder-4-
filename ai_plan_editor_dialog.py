"""AI 战略计划编辑器

- 左侧：战略计划列表
- 右侧：名称/描述/国策顺序
- 「🎯 编辑国策顺序」：打开国策绘图点选器，按顺序确认 `ai_national_focuses`
- 「✏ 编辑定义」：打开通用树形编辑器（条件块等完整编辑）
- 保存：原版自动复制到 mod + 原子写
"""

from __future__ import annotations

import os
import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from ai_loader import (
    load_ai_plans, replace_ai_plan_focus_order, replace_ai_plan_field,
)
from write_utils import atomic_write_text
from state_build_ops import ensure_file_in_mod


def _plan_country(plan):
    """从 plan 的 allowed/enable 文本中猜测国家 tag（original_tag 优先）。"""
    blob = "%s %s" % (plan.get("allowed", "") or "",
                      plan.get("enable", "") or "")
    m = re.search(r"\boriginal_tag\s*=\s*([A-Z0-9]{2,4})", blob)
    if m:
        return m.group(1)
    base = os.path.basename(plan.get("file", "") or "")
    m = re.match(r"([A-Z0-9]{2,4})[_\-\s]", base)
    if m:
        return m.group(1)
    return ""


class AiPlanEditorDialog(QDialog):
    """AI 战略计划专用编辑器。"""

    def __init__(self, plans, mod_path="", hoi4_path="", parent=None,
                 initial_plan_id=None):
        super().__init__(parent)
        self.plans = plans
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self._current_plan = None
        self._ordered = []
        self._focus_picker = None
        self.setWindowTitle("AI 战略计划编辑器")
        self.resize(980, 640)
        self._build_ui()
        self._populate_plans(initial_plan_id)

    # ---------- UI ----------
    def _build_ui(self):
        root = QHBoxLayout(self)
        # 左：计划列表
        left = QVBoxLayout()
        left.addWidget(QLabel("战略计划"))
        self.plan_list = QListWidget()
        self.plan_list.currentItemChanged.connect(self._on_plan_changed)
        left.addWidget(self.plan_list, 1)
        root.addLayout(left, 1)

        # 右：详情
        right = QVBoxLayout()
        self.id_label = QLabel("—")
        self.id_label.setStyleSheet("font-weight:bold; font-size:15px;")
        right.addWidget(self.id_label)

        form = QVBoxLayout()
        form.addWidget(QLabel("名称"))
        self.name_edit = QLineEdit()
        form.addWidget(self.name_edit)
        form.addWidget(QLabel("描述"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setFixedHeight(80)
        form.addWidget(self.desc_edit)
        right.addLayout(form)

        order_box = QVBoxLayout()
        self.order_label = QLabel("国策顺序：—")
        self.order_label.setWordWrap(True)
        order_box.addWidget(self.order_label)
        order_btns = QHBoxLayout()
        edit_order_btn = QPushButton("🎯 编辑国策顺序")
        edit_order_btn.clicked.connect(self._edit_order)
        order_btns.addWidget(edit_order_btn)
        tree_btn = QPushButton("✏ 编辑定义（树编辑器）")
        tree_btn.clicked.connect(self._edit_tree)
        order_btns.addWidget(tree_btn)
        order_box.addLayout(order_btns)
        right.addLayout(order_box)
        right.addStretch(1)

        footer = QHBoxLayout()
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save)
        footer.addStretch(1)
        footer.addWidget(save_btn)
        right.addLayout(footer)
        root.addLayout(right, 2)

    def _populate_plans(self, initial_plan_id=None):
        self.plan_list.blockSignals(True)
        self.plan_list.clear()
        for pid in sorted(self.plans):
            plan = self.plans[pid]
            label = pid
            if plan.get("name"):
                label += "  (%s)" % plan["name"]
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, pid)
            self.plan_list.addItem(item)
        self.plan_list.blockSignals(False)
        if self.plan_list.count() > 0:
            target = 0
            if initial_plan_id:
                for i in range(self.plan_list.count()):
                    if self.plan_list.item(i).data(Qt.ItemDataRole.UserRole) == initial_plan_id:
                        target = i
                        break
            self.plan_list.setCurrentRow(target)
            self._on_plan_changed(self.plan_list.currentItem())

    def _on_plan_changed(self, item):
        if item is None:
            return
        pid = item.data(Qt.ItemDataRole.UserRole)
        plan = self.plans.get(pid)
        if not plan:
            return
        self._current_plan = plan
        self._ordered = list(plan.get("ai_national_focuses", []))
        self.id_label.setText("%s  （%s）" % (pid, plan.get("file", "")))
        self.name_edit.setText(plan.get("name", ""))
        self.desc_edit.setPlainText(plan.get("desc", ""))
        self._update_order_label()

    def _update_order_label(self):
        if self._ordered:
            self.order_label.setText("国策顺序：%s" % " → ".join(self._ordered))
        else:
            self.order_label.setText("国策顺序：—")

    # ---------- 编辑 ----------
    def _edit_order(self):
        if not self._current_plan:
            return
        from focus_order_picker import FocusOrderPicker
        country = _plan_country(self._current_plan)
        picker = FocusOrderPicker(
            ordered=self._ordered,
            country=country,
            mod_path=self.mod_path,
            hoi4_path=self.hoi4_path,
            parent=self,
        )
        if country:
            picker._load_country(country)
        if picker.exec():
            self._ordered = picker.ordered_ids()
            self._update_order_label()

    def _edit_tree(self):
        if not self._current_plan:
            return
        fp = self._current_plan.get("file", "")
        if not fp:
            return
        mod_fp, copied = self._ensure_writable(fp)
        if not mod_fp:
            QMessageBox.warning(self, "无法编辑", "请先打开 mod 目录")
            return
        self._open_tree_for_file(mod_fp, self._current_plan["id"])

    def _ensure_writable(self, fp):
        if self.mod_path and os.path.normcase(fp).startswith(
                os.path.normcase(os.path.normpath(self.mod_path))):
            return fp, False
        if not self.mod_path or not self.hoi4_path:
            return None, False
        try:
            rel = os.path.relpath(fp, self.hoi4_path).replace("\\", "/")
            if not rel.startswith(".."):
                return ensure_file_in_mod(self.mod_path, self.hoi4_path, rel)
        except Exception:
            pass
        return None, False

    def _open_tree_for_file(self, fp, entity_id):
        from tree_node import tree_from_pdx_text
        from generic_tree_editor import GenericTreeEditor
        from gui_translator import get_translator
        from focus_view import CUSTOM_STATEMENT_PATH
        try:
            with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "无法编辑", "读取文件失败：%s" % e)
            return
        file_lines = content.splitlines()
        root = tree_from_pdx_text(content)
        editor = GenericTreeEditor(
            root_node=root,
            file_path=fp,
            file_lines=file_lines,
            block_range=(1, len(file_lines) + 1),
            translator=get_translator(),
            custom_statement_path=CUSTOM_STATEMENT_PATH,
            loc_manager=None,
            parent=self,
            title="AI 战略计划 - %s" % entity_id,
            hoi4_path=self.hoi4_path,
            mod_path=self.mod_path,
        )
        editor.show()
        try:
            model = getattr(editor, "model", None)
            if model is not None:
                results = model.find_nodes(entity_id)
                if results:
                    editor.tree_view.setCurrentIndex(results[0])
                    editor.tree_view.scrollTo(results[0])
        except Exception:
            pass

    # ---------- 保存 ----------
    def _save(self):
        if not self._current_plan:
            return
        plan = self._current_plan
        rel = plan.get("rel", "")
        if not rel:
            return
        mod_fp, copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位 AI 战略计划文件")
            return
        try:
            with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "读取文件失败：%s" % e)
            return
        pid = plan["id"]
        content = replace_ai_plan_field(content, pid, "name", self.name_edit.text().strip())
        content = replace_ai_plan_field(content, pid, "desc", self.desc_edit.toPlainText().strip())
        content = replace_ai_plan_focus_order(content, pid, self._ordered)
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        plan["name"] = self.name_edit.text().strip()
        plan["desc"] = self.desc_edit.toPlainText().strip()
        plan["ai_national_focuses"] = list(self._ordered)
        msg = "已保存 AI 战略计划 %s" % pid
        if copied:
            msg += "\n原版文件已自动复制到 mod"
        QMessageBox.information(self, "已保存", msg)


def open_ai_plan_editor(file_path, mod_path="", hoi4_path="",
                        entity_id=None, parent=None):
    """按文件/实体打开 AI 战略计划编辑器。"""
    plans = load_ai_plans(mod_path, hoi4_path)
    norm = os.path.normpath(file_path).replace("\\", "/")
    file_plans = {}
    for pid, plan in plans.items():
        if os.path.normpath(plan.get("file", "")).replace("\\", "/") == norm:
            file_plans[pid] = plan
    if not file_plans:
        return False
    dlg = AiPlanEditorDialog(
        file_plans, mod_path, hoi4_path, parent,
        initial_plan_id=entity_id if entity_id in file_plans else None)
    dlg.exec()
    return True

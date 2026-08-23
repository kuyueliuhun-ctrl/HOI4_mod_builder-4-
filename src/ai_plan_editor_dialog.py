"""AI 战略计划专用编辑器（完全专用 UI，不依赖树形编辑器页面）

- 左侧固定侧边栏：计划列表 + 搜索 + CRUD
- 主内容页签：基本信息 / 国策顺序 / 高级脚本块
- 保存：原版自动复制到 mod + 原子写
"""

from __future__ import annotations

import os
import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMenu,
    QMessageBox, QPushButton, QTabWidget, QTextEdit, QToolButton,
    QVBoxLayout, QWidget,
)

from ai_loader import (
    _AI_CACHE,
    delete_ai_plan,
    duplicate_ai_plan,
    insert_ai_plan,
    load_ai_plans,
    rename_ai_plan,
    replace_ai_plan_field,
    replace_ai_plan_focus_order,
    upsert_top_block_child,
)
from ai_ui_common import EntityListSidebar, ScriptBlockEditorDialog
from ui_widgets import OrderRowList
from state_build_ops import ensure_file_in_mod
from write_utils import atomic_write_text
from localisation_editor_data import (
    default_mod_loc_file, load_effective_dict, upsert_loc_entry,
)

ADVANCED_FIELDS = ("allowed", "enable", "abort", "focus_factors",
                   "research", "ideas", "weight")


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
        self._advanced_blocks = {}
        self._focus_picker = None
        self.setWindowTitle("AI 战略计划编辑器")
        self.resize(1180, 720)
        self.setMinimumSize(1060, 640)
        self._build_ui()
        self._populate_plans(initial_plan_id)

    # ---------- UI ----------
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.sidebar = EntityListSidebar("战略计划", self)
        self.sidebar.set_paths(self.mod_path, self.hoi4_path)
        self.sidebar.currentChanged.connect(self._on_plan_changed)
        self.sidebar.createRequested.connect(self._create_plan)
        self.sidebar.duplicateRequested.connect(self._duplicate_plan)
        self.sidebar.renameRequested.connect(self._rename_plan)
        self.sidebar.deleteRequested.connect(self._delete_plan)
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        self.id_label = QLabel("—")
        self.id_label.setStyleSheet("font-weight:bold; font-size:15px;")
        right.addWidget(self.id_label)

        self.tabs = QTabWidget()

        # 基本信息
        info_tab = QWidget()
        info = QVBoxLayout(info_tab)
        info.addWidget(QLabel("名称"))
        self.name_edit = QLineEdit()
        info.addWidget(self.name_edit)
        info.addWidget(QLabel("描述键"))
        self.desc_key_edit = QLineEdit()
        self.desc_key_edit.setPlaceholderText("desc 本地化键（如 AI_DESC）")
        self.desc_edit = self.desc_key_edit  # 兼容旧测试/旧调用
        info.addWidget(self.desc_key_edit)
        info.addWidget(QLabel("描述中文"))
        self.desc_cn_edit = QLineEdit()
        self.desc_cn_edit.setPlaceholderText("中文翻译（保存时写入本地化）")
        info.addWidget(self.desc_cn_edit)
        info.addStretch(1)
        self.tabs.addTab(info_tab, "基本信息")

        # 国策顺序
        order_tab = QWidget()
        order = QVBoxLayout(order_tab)
        self.order_label = QLabel("国策顺序：—")
        self.order_label.setWordWrap(True)
        order.addWidget(self.order_label)
        self.order_list = OrderRowList()
        self.order_list.setMaximumHeight(200)
        order.addWidget(self.order_list)
        order.addWidget(QLabel("国策顺序可增删/上下移，或用下方点选器"))
        order_btns = QHBoxLayout()
        add_order_btn = QPushButton("➕ 添加")
        del_order_btn = QPushButton("🗑 删除")
        up_order_btn = QPushButton("⬆")
        down_order_btn = QPushButton("⬇")
        add_order_btn.clicked.connect(self._add_order_item)
        del_order_btn.clicked.connect(self._delete_order_item)
        up_order_btn.clicked.connect(lambda: self._move_order_item(-1))
        down_order_btn.clicked.connect(lambda: self._move_order_item(1))
        for b in (add_order_btn, del_order_btn, up_order_btn, down_order_btn):
            order_btns.addWidget(b)
        order_btns.addStretch(1)
        order.addLayout(order_btns)
        btn_row = QHBoxLayout()
        pick_btn = QPushButton("🎯 编辑国策顺序（点选器）")
        pick_btn.clicked.connect(self._edit_order)
        btn_row.addWidget(pick_btn)
        btn_row.addStretch(1)
        order.addLayout(btn_row)
        order.addStretch(1)
        self.tabs.addTab(order_tab, "国策顺序")

        # 高级脚本
        adv_tab = QWidget()
        adv = QVBoxLayout(adv_tab)
        adv.addWidget(QLabel("高级脚本块（可在下方逐一编辑）"))
        self.adv_buttons = {}
        for field in ADVANCED_FIELDS:
            row = QHBoxLayout()
            row.addWidget(QLabel(field))
            btn = QPushButton("未编辑")
            btn.clicked.connect(
                lambda checked=False, f=field: self._edit_advanced(f))
            row.addWidget(btn, 1)
            self.adv_buttons[field] = btn
            adv.addLayout(row)
        adv.addStretch(1)
        self.tabs.addTab(adv_tab, "高级脚本")
        right.addWidget(self.tabs, 1)

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
        root.addLayout(right, 1)

    def _populate_plans(self, initial_plan_id=None):
        items = []
        for pid in sorted(self.plans):
            plan = self.plans[pid]
            label = pid
            if plan.get("name"):
                label += "  (%s)" % plan["name"]
            items.append((pid, label))
        self.sidebar.set_entities(items)
        if initial_plan_id:
            self.sidebar.set_current(initial_plan_id)
        elif self.sidebar.current_id() is None and self.sidebar.list.count():
            self.sidebar.set_current(self.sidebar.list.item(0).data(
                Qt.ItemDataRole.UserRole))

    def _on_plan_changed(self, plan_id):
        if plan_id is None:
            self._current_plan = None
            self.id_label.setText("—")
            return
        plan = self.plans.get(plan_id)
        if not plan:
            return
        self._current_plan = plan
        self._ordered = list(plan.get("ai_national_focuses", []))
        self._advanced_blocks = {
            f: plan.get(f, "") or "" for f in ADVANCED_FIELDS}
        self.id_label.setText("%s  （%s）" % (plan_id, plan.get("file", "")))
        self.name_edit.setText(plan.get("name", ""))
        desc_key = plan.get("desc", "") or ""
        self.desc_key_edit.setText(desc_key)
        try:
            loc = load_effective_dict(self.mod_path, self.hoi4_path,
                                      "simp_chinese")
            self.desc_cn_edit.setText(loc.get(desc_key, ""))
        except Exception:
            self.desc_cn_edit.setText("")
        self.order_list.set_order(self._ordered)
        self._update_order_label()
        self._update_advanced_summaries()

    def _update_order_label(self):
        if self._ordered:
            self.order_label.setText("国策顺序：%s" % " → ".join(self._ordered))
        else:
            self.order_label.setText("国策顺序：—")

    def _update_advanced_summaries(self):
        for field in ADVANCED_FIELDS:
            text = (self._advanced_blocks.get(field) or "").strip()
            self.adv_buttons[field].setText(
                "空" if not text else "已编辑（%d 行）" % len(text.splitlines()))

    # ---------- 编辑 ----------

    def _add_order_item(self):
        text, ok = QInputDialog.getText(self, "添加国策", "focus id:")
        if ok and text.strip():
            self._ordered.append(text.strip())
            self.order_list.set_order(self._ordered)
            self._update_order_label()

    def _delete_order_item(self):
        row = self.order_list.currentRow()
        if row < 0 or row >= len(self._ordered):
            return
        del self._ordered[row]
        self.order_list.set_order(self._ordered)
        self._update_order_label()

    def _move_order_item(self, delta):
        row = self.order_list.currentRow()
        new = row + delta
        if row < 0 or new < 0 or new >= len(self._ordered):
            return
        self._ordered[row], self._ordered[new] = (
            self._ordered[new], self._ordered[row])
        self.order_list.set_order(self._ordered)
        self.order_list.setCurrentRow(new)
        self._update_order_label()

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
            self.order_list.set_order(self._ordered)
            self._update_order_label()

    def _edit_advanced(self, field):
        from gui_translator import get_translator
        from focus_view import CUSTOM_STATEMENT_PATH
        dlg = ScriptBlockEditorDialog(
            block_text=self._advanced_blocks.get(field, ""),
            block_key=field,
            translator=get_translator(),
            custom_statement_path=CUSTOM_STATEMENT_PATH,
            parent=self,
            title="编辑 %s" % field,
        )
        if dlg.exec():
            self._advanced_blocks[field] = dlg.get_block_text()
            self._update_advanced_summaries()

    def _edit_raw(self):
        if not self._current_plan:
            return
        from gui_translator import get_translator
        from focus_view import CUSTOM_STATEMENT_PATH
        dlg = ScriptBlockEditorDialog(
            block_text=self._current_plan.get("raw", ""),
            block_key=self._current_plan["id"],
            translator=get_translator(),
            custom_statement_path=CUSTOM_STATEMENT_PATH,
            parent=self,
            title="AI 战略计划 - %s" % self._current_plan["id"],
        )
        if dlg.exec():
            self._current_plan["raw"] = dlg.get_block_text()

    # ---------- CRUD ----------
    def _reload_plans(self, keep_id=None):
        _AI_CACHE.pop(("ai_plans", self.mod_path or "",
                       self.hoi4_path or ""), None)
        self.plans = load_ai_plans(self.mod_path, self.hoi4_path)
        if self._current_plan:
            norm = os.path.normpath(
                self._current_plan.get("file", "")).replace("\\", "/")
            self.plans = {pid: p for pid, p in self.plans.items()
                          if os.path.normpath(p.get("file", "")).replace("\\", "/") == norm}
        self._populate_plans(keep_id)

    def _current_rel(self):
        if not self._current_plan:
            return ""
        return self._current_plan.get("rel", "")

    def _create_plan(self):
        if not self._current_plan:
            return
        new_id, ok = QInputDialog.getText(self, "新建计划", "计划 ID：")
        if not ok or not new_id.strip():
            return
        if new_id.strip() in self.plans:
            QMessageBox.warning(self, "错误", "计划已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_rel())
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = insert_ai_plan(content, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload_plans(new_id.strip())

    def _duplicate_plan(self):
        if not self._current_plan:
            return
        old_id = self._current_plan["id"]
        new_id, ok = QInputDialog.getText(
            self, "复制计划", "新计划 ID：", text=old_id + "_copy")
        if not ok or not new_id.strip():
            return
        if new_id.strip() in self.plans:
            QMessageBox.warning(self, "错误", "计划已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_rel())
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = duplicate_ai_plan(content, old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload_plans(new_id.strip())

    def _rename_plan(self):
        if not self._current_plan:
            return
        old_id = self._current_plan["id"]
        new_id, ok = QInputDialog.getText(
            self, "重命名计划", "新计划 ID：", text=old_id)
        if not ok or not new_id.strip() or new_id.strip() == old_id:
            return
        if new_id.strip() in self.plans:
            QMessageBox.warning(self, "错误", "计划已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_rel())
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = rename_ai_plan(content, old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload_plans(new_id.strip())

    def _delete_plan(self):
        if not self._current_plan:
            return
        reply = QMessageBox.question(
            self, "确认", "确定要删除计划 '%s' 吗？" % self._current_plan["id"])
        if reply != QMessageBox.StandardButton.Yes:
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_rel())
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = delete_ai_plan(content, self._current_plan["id"])
        atomic_write_text(mod_fp, content)
        self._reload_plans()

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
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        pid = plan["id"]
        content = replace_ai_plan_field(
            content, pid, "name", self.name_edit.text().strip())
        desc_key = self.desc_key_edit.text().strip()
        desc_cn = self.desc_cn_edit.text().strip()
        desc_content = replace_ai_plan_field(content, pid, "desc", desc_key)
        if desc_key and desc_content == content:
            # 原计划没有 desc 字段时，兜底插入（replace_ai_plan_field 只替换不新增）
            desc_content = upsert_top_block_child(
                content, pid, "desc", "desc = %s" % desc_key)
        content = desc_content
        if desc_key and desc_cn:
            loc_fp = default_mod_loc_file(self.mod_path)
            if loc_fp:
                upsert_loc_entry(loc_fp, desc_key, desc_cn)
        # 国策顺序：若 _ordered 与文件原序一致（未用点选器改），则从文本域读取；
        # 若已被点选器/外部直接改过，优先使用 _ordered。
        plan_order = list(plan.get("ai_national_focuses", []))
        if self._ordered == plan_order:
            self._ordered = self.order_list.order()
            self._update_order_label()
        content = replace_ai_plan_focus_order(content, pid, self._ordered)
        for field in ADVANCED_FIELDS:
            text = (self._advanced_blocks.get(field) or "").strip()
            if text:
                content = upsert_top_block_child(content, pid, field, text)
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        plan["name"] = self.name_edit.text().strip()
        plan["desc"] = desc_key
        plan["ai_national_focuses"] = list(self._ordered)
        for field in ADVANCED_FIELDS:
            plan[field] = self._advanced_blocks.get(field, "")
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

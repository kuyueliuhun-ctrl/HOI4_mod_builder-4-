# -*- coding: utf-8 -*-
"""事件（Event）专用编辑器 UI。

批次 4 完整版：
- 左侧 EntityListSidebar + 类型过滤 + CRUD
- 表单：id/type/namespace/title/desc 本地化双行、picture 96x64 预览、
  major/is_triggered_only/fire_only_once/hidden、MTTH 天数 + modifier
  结构化块、option 列表卡、immediate/after 结构化块、其他字段表
- 保存：事件块内容级变换 + 原子写（原版自动落 mod）+ 本地化写回
"""

from __future__ import annotations

import os
import re

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QScrollArea, QSpinBox, QSplitter, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QInputDialog, QHeaderView,
)

from ai_ui_common import EntityListSidebar, ScriptBlockEditorDialog
from content_types import ICON_RULES
from event_data import (
    apply_event_edits, apply_file_other_fields, delete_event,
    duplicate_event, insert_event, load_event_entities, parse_file_other_fields,
    rename_event, _replace_child_in_seg, _replace_scalar_in_seg,
)
from localisation_editor_data import (
    default_mod_loc_file, find_mod_file_for_key, load_loc_file,
    load_effective_dict, upsert_loc_entry,
)
from oob_loader import _block_ranges
from state_build_ops import ensure_file_in_mod
from write_utils import atomic_write_text

_EVENT_TYPE_KEYS = (
    "country_event", "news_event", "state_event",
    "operative_leader_event", "dynamic_event", "unit_leader_event",
)


# ---------------------------------------------------------------------------
# 小型复用控件
# ---------------------------------------------------------------------------

class LocEdit(QWidget):
    """本地化双行编辑：键 + 中文内容。"""

    def __init__(self, key="", cn="", key_placeholder="本地化键",
                 cn_placeholder="中文内容（保存写入 mod 本地化）", parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(2)
        self.key_edit = QLineEdit(key)
        self.key_edit.setPlaceholderText(key_placeholder)
        self.cn_edit = QLineEdit(cn)
        self.cn_edit.setPlaceholderText(cn_placeholder)
        root.addWidget(self.key_edit)
        root.addWidget(self.cn_edit)

    def set_key(self, key):
        self.key_edit.setText(key or "")

    def set_cn(self, value):
        self.cn_edit.setText(value or "")

    def key(self):
        return self.key_edit.text().strip()

    def cn(self):
        return self.cn_edit.text().strip()


class StructuredBlockCard(QFrame):
    """「key = { ... }」结构化块行：键名 + 概要 + 编辑按钮。"""

    def __init__(self, block_key, block_text="", parent=None, title="结构化编辑"):
        super().__init__(parent)
        self.block_key = block_key
        self.block_text = block_text or ""
        self.setStyleSheet(
            "QFrame{background:#f5f7fa;border:1px solid #d8e0ea;"
            "border-radius:8px;}")
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 6, 10, 6)
        row.setSpacing(8)
        self.key_label = QLabel(block_key)
        self.key_label.setStyleSheet(
            "font-family:Consolas,monospace;color:#1f6feb;font-weight:bold;")
        row.addWidget(self.key_label)
        self.summary_label = QLabel(self._summary())
        self.summary_label.setStyleSheet("color:#5d6b7a;font-size:11px;")
        self.summary_label.setWordWrap(True)
        row.addWidget(self.summary_label, 1)
        self.edit_btn = QPushButton("结构化编辑")
        self.edit_btn.clicked.connect(self._open_editor)
        row.addWidget(self.edit_btn)

    def _summary(self):
        text = (self.block_text or "").strip()
        if not text:
            return "（空）"
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if len(lines) <= 3:
            return " · ".join(lines)
        return " · ".join(lines[:3]) + " …"

    def set_block_text(self, text):
        self.block_text = text or ""
        self.summary_label.setText(self._summary())

    def _open_editor(self):
        dlg = ScriptBlockEditorDialog(
            self.block_text, block_key=self.block_key, parent=self,
            title="编辑 %s" % self.block_key)
        dlg.accepted.connect(lambda: self.set_block_text(dlg.get_block_text()))
        dlg.show()


class OtherFieldsTable(QWidget):
    """其他字段表：两列键值，文件内其余键统一编辑（读写无损）。"""

    def __init__(self, rows=(), parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)
        note = QLabel("文件中存在而表单未覆盖的键在此统一编辑（读写完整保留）")
        note.setStyleSheet("color:#5d6b7a;font-size:11px;")
        note.setWordWrap(True)
        root.addWidget(note)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["键", "值"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        btns = QHBoxLayout()
        add_btn = QPushButton("＋ 添加键")
        del_btn = QPushButton("－ 删除选中")
        add_btn.clicked.connect(lambda: self.add_row("", ""))
        del_btn.clicked.connect(self._remove_selected)
        btns.addWidget(add_btn)
        btns.addWidget(del_btn)
        btns.addStretch(1)
        root.addLayout(btns)
        self.set_rows(rows)

    def set_rows(self, rows):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for k, v in rows or []:
            self.add_row(k, v)
        self.table.blockSignals(False)

    def add_row(self, key, value):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(str(key)))
        self.table.setItem(r, 1, QTableWidgetItem(str(value)))

    def _remove_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()},
                      reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def rows(self):
        out = []
        for r in range(self.table.rowCount()):
            k = self.table.item(r, 0)
            v = self.table.item(r, 1)
            out.append((k.text().strip() if k else "",
                        v.text().strip() if v else ""))
        return out


class OptionCard(QFrame):
    """事件选项卡片：名称本地化双行 + trigger/ai_chance/效果结构化块 + 排序。"""

    def __init__(self, index, option, parent=None, on_move_up=None,
                 on_move_down=None, on_duplicate=None, on_delete=None):
        super().__init__(parent)
        self.option = option or {}
        self.index = index
        self.raw = self.option.get("raw") or (
            "option = {\n\tname = %s\n}" % self.option.get("name", ""))
        self.trigger_text = self.option.get("trigger") or ""
        self.ai_text = self.option.get("ai_chance") or ""
        self.effects_text = self.raw
        self.on_move_up = on_move_up
        self.on_move_down = on_move_down
        self.on_duplicate = on_duplicate
        self.on_delete = on_delete

        self.setObjectName("OptionCard")
        self.setStyleSheet(
            "QFrame#OptionCard{background:#ffffff;border:1px solid #d8e0ea;"
            "border-radius:12px;}")
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 10)
        root.setSpacing(6)

        head = QHBoxLayout()
        title = QLabel("选项 %d" % index)
        title.setStyleSheet("font-weight:bold;color:#1f6feb;")
        head.addWidget(title)
        head.addStretch(1)
        self.up_btn = QPushButton("↑")
        self.down_btn = QPushButton("↓")
        self.copy_btn = QPushButton("⧉ 复制")
        self.del_btn = QPushButton("🗑 删除")
        for b in (self.up_btn, self.down_btn, self.copy_btn, self.del_btn):
            b.setFixedHeight(24)
            head.addWidget(b)
        self.up_btn.clicked.connect(lambda: self.on_move_up(self) if self.on_move_up else None)
        self.down_btn.clicked.connect(lambda: self.on_move_down(self) if self.on_move_down else None)
        self.copy_btn.clicked.connect(lambda: self.on_duplicate(self) if self.on_duplicate else None)
        self.del_btn.clicked.connect(lambda: self.on_delete(self) if self.on_delete else None)
        root.addLayout(head)

        self.name_loc = LocEdit(self.option.get("name", ""),
                                self.option.get("name_cn", ""),
                                "选项名称键（可留空 = 默认名）")
        root.addWidget(self.name_loc)
        root.addWidget(self._make_block_card("trigger", self.trigger_text))
        root.addWidget(self._make_block_card("ai_chance", self.ai_text))
        root.addWidget(self._make_block_card("（效果体）", self.raw))

    def _make_block_card(self, key, text):
        card = StructuredBlockCard(key, text, parent=self)
        card.edit_btn.clicked.disconnect()
        if key == "trigger":
            card.edit_btn.clicked.connect(lambda: self._edit_trigger(card))
        elif key == "ai_chance":
            card.edit_btn.clicked.connect(lambda: self._edit_ai(card))
        else:
            card.edit_btn.clicked.connect(lambda: self._edit_effects(card))
        return card

    def _replace_child_in_raw(self, key, new_text):
        changed = _replace_child_in_seg(self.raw, key, new_text)
        if changed is not None:
            self.raw = changed
        else:
            close = self.raw.rfind("}")
            self.raw = (self.raw[:close] + "\n\t" + new_text.strip()
                        + "\n" + self.raw[close:])

    def _edit_trigger(self, card):
        dlg = ScriptBlockEditorDialog(
            self.trigger_text or "trigger = {\n}", block_key="trigger",
            parent=self, title="编辑 trigger")
        dlg.accepted.connect(lambda: self._apply_trigger(dlg, card))
        dlg.show()

    def _apply_trigger(self, dlg, card):
        self.trigger_text = dlg.get_block_text()
        self._replace_child_in_raw("trigger", self.trigger_text)
        card.set_block_text(self.trigger_text)

    def _edit_ai(self, card):
        dlg = ScriptBlockEditorDialog(
            self.ai_text or "ai_chance = {\n\tfactor = 1\n}",
            block_key="ai_chance", parent=self, title="编辑 ai_chance")
        dlg.accepted.connect(lambda: self._apply_ai(dlg, card))
        dlg.show()

    def _apply_ai(self, dlg, card):
        self.ai_text = dlg.get_block_text()
        self._replace_child_in_raw("ai_chance", self.ai_text)
        card.set_block_text(self.ai_text)

    def _edit_effects(self, card):
        dlg = ScriptBlockEditorDialog(
            self.raw, block_key="option", parent=self,
            title="编辑选项效果体")
        dlg.accepted.connect(lambda: self._apply_effects(dlg, card))
        dlg.show()

    def _apply_effects(self, dlg, card):
        self.raw = dlg.get_block_text()
        self.effects_text = self.raw
        card.set_block_text(self.raw)

    def final_raw(self):
        raw = self.raw
        name = self.name_loc.key()
        if name:
            raw = _replace_scalar_in_seg(raw, "name", name, quoted=False)
        return raw


# ---------------------------------------------------------------------------
# 事件编辑器对话框
# ---------------------------------------------------------------------------

class EventEditorDialog(QDialog):
    """事件专用编辑器（非模态）。"""

    saved = pyqtSignal()

    def __init__(self, mod_path="", hoi4_path="", file_path="", parent=None):
        super().__init__(parent)
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.file_path = file_path or ""
        self.events = []
        self._event_map = {}
        self.current_event = None
        self._loc_cache = {}
        self._gfx_cache = None

        self.setWindowTitle("事件编辑器")
        self.resize(1240, 840)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        split = QSplitter(Qt.Orientation.Horizontal)
        left = self._build_left()
        right = self._build_right()
        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        outer.addWidget(split, 1)

        bottom = QHBoxLayout()
        self.batch_loc_btn = QPushButton("🌐 批量补写缺失本地化…")
        self.batch_loc_btn.clicked.connect(self._batch_fill_loc)
        bottom.addWidget(self.batch_loc_btn)
        bottom.addStretch(1)
        reset_btn = QPushButton("⟲ 重置")
        reset_btn.clicked.connect(self._reload)
        save_btn = QPushButton("💾 保存（原子写 · 可撤销）")
        save_btn.setStyleSheet("font-weight:bold;")
        save_btn.clicked.connect(self._save)
        bottom.addWidget(reset_btn)
        bottom.addWidget(save_btn)
        outer.addLayout(bottom)

        self._reload()

    # ---------- UI 构造 ----------

    def _build_left(self):
        wrap = QWidget()
        root = QVBoxLayout(wrap)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)
        frow = QHBoxLayout()
        frow.addWidget(QLabel("过滤"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部类型", "country_event", "news_event",
                                    "unit_leader_event", "隐藏事件"])
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        frow.addWidget(self.filter_combo, 1)
        root.addLayout(frow)
        self.sidebar = EntityListSidebar(
            "事件（events/）", parent=self, enable_crud=True,
            mod_path=self.mod_path, hoi4_path=self.hoi4_path)
        self.sidebar.currentChanged.connect(self._on_select)
        self.sidebar.createRequested.connect(self._create_event)
        self.sidebar.duplicateRequested.connect(self._duplicate_event)
        self.sidebar.renameRequested.connect(self._rename_event)
        self.sidebar.deleteRequested.connect(self._delete_event)
        root.addWidget(self.sidebar, 1)
        return wrap

    def _build_right(self):
        wrap = QWidget()
        root = QVBoxLayout(wrap)
        root.setContentsMargins(6, 0, 0, 0)
        root.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        form = QVBoxLayout(body)
        form.setContentsMargins(0, 0, 6, 0)
        form.setSpacing(8)

        # 基本信息
        basic = QFrame()
        basic.setObjectName("Card")
        basic.setStyleSheet(
            "QFrame#Card{background:#ffffff;border:1px solid #d8e0ea;"
            "border-radius:12px;}")
        bl = QVBoxLayout(basic)
        bl.setContentsMargins(12, 10, 12, 12)
        bl.addWidget(self._card_title("基本信息"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(_EVENT_TYPE_KEYS)
        self.id_edit = QLineEdit()
        self.namespace_edit = QLineEdit()
        self.title_loc = LocEdit("", "", "标题本地化键（如 events.x.t）")
        self.desc_loc = LocEdit("", "", "描述本地化键（如 events.x.d）")
        self.title_edit = self.title_loc.key_edit
        self.desc_edit = self.desc_loc.key_edit
        bl.addLayout(self._form_row("事件类型", self.type_combo))
        bl.addLayout(self._form_row("事件 id", self.id_edit))
        bl.addLayout(self._form_row("命名空间", self.namespace_edit))
        bl.addWidget(QLabel("标题 title（本地化双行）"))
        bl.addWidget(self.title_loc)
        bl.addWidget(QLabel("描述 desc（本地化双行）"))
        bl.addWidget(self.desc_loc)
        bl.addLayout(self._build_picture_row())
        form.addWidget(basic)

        # 触发与时机
        trig = QFrame()
        trig.setObjectName("Card")
        trig.setStyleSheet(basic.styleSheet())
        tl = QVBoxLayout(trig)
        tl.setContentsMargins(12, 10, 12, 12)
        tl.addWidget(self._card_title("触发与时机"))
        checks = QHBoxLayout()
        self.major_check = QCheckBox("major 重大事件")
        self.triggered_check = QCheckBox("is_triggered_only 仅脚本触发")
        self.fire_once_check = QCheckBox("fire_only_once 仅触发一次")
        self.hidden_check = QCheckBox("hidden 隐藏事件")
        for cb in (self.major_check, self.triggered_check,
                   self.fire_once_check, self.hidden_check):
            checks.addWidget(cb)
        checks.addStretch(1)
        tl.addLayout(checks)
        self.mtth_spin = QSpinBox()
        self.mtth_spin.setRange(0, 999999)
        self.mtth_spin.setValue(30)
        tl.addLayout(self._form_row("MTTH 天数", self.mtth_spin, "天"))
        self.mtth_modifier_card = StructuredBlockCard(
            "mean_time_to_happen.modifier", "", parent=self)
        tl.addWidget(self.mtth_modifier_card)
        self.options_count_label = QLabel("—")
        self.options_label = self.options_count_label
        self.file_label = QLabel("")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("color:#5d6b7a;")
        form.addWidget(trig)

        # 选项
        opts = QFrame()
        opts.setObjectName("Card")
        opts.setStyleSheet(basic.styleSheet())
        ol = QVBoxLayout(opts)
        ol.setContentsMargins(12, 10, 12, 12)
        ol.addWidget(self._card_title("选项（option）"))
        note = QLabel("选项可增删/排序；名称走本地化；trigger / ai_chance / 效果体均为结构化编辑")
        note.setStyleSheet("color:#5d6b7a;font-size:11px;")
        note.setWordWrap(True)
        ol.addWidget(note)
        self.option_cards_layout = QVBoxLayout()
        ol.addLayout(self.option_cards_layout)
        add_opt_btn = QPushButton("＋ 新增选项")
        add_opt_btn.clicked.connect(self._add_option)
        ol.addWidget(add_opt_btn)
        form.addWidget(opts)

        # 事件脚本块
        blocks = QFrame()
        blocks.setObjectName("Card")
        blocks.setStyleSheet(basic.styleSheet())
        bkl = QVBoxLayout(blocks)
        bkl.setContentsMargins(12, 10, 12, 12)
        bkl.addWidget(self._card_title("事件脚本块"))
        self.immediate_card = StructuredBlockCard("immediate", "", parent=self)
        self.after_card = StructuredBlockCard("after", "", parent=self)
        bkl.addWidget(self.immediate_card)
        bkl.addWidget(self.after_card)
        form.addWidget(blocks)

        # 其他字段
        other = QFrame()
        other.setObjectName("Card")
        other.setStyleSheet(basic.styleSheet())
        okl = QVBoxLayout(other)
        okl.setContentsMargins(12, 10, 12, 12)
        okl.addWidget(self._card_title("其他字段（树编辑器兜底）"))
        self.other_fields_table = OtherFieldsTable()
        okl.addWidget(self.other_fields_table)
        form.addWidget(other)

        # 文件级其他字段（顶层常量 / add_namespace / 非事件键）
        file_other = QFrame()
        file_other.setObjectName("Card")
        file_other.setStyleSheet(basic.styleSheet())
        fokl = QVBoxLayout(file_other)
        fokl.setContentsMargins(12, 10, 12, 12)
        fokl.addWidget(self._card_title("文件级其他字段（顶层常量/非事件键）"))
        self.file_other_fields_table = OtherFieldsTable()
        fokl.addWidget(self.file_other_fields_table)
        form.addWidget(file_other)

        form.addStretch(1)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)
        return wrap

    def _build_picture_row(self):
        row = QHBoxLayout()
        row.setSpacing(8)
        self.picture_preview = QLabel("🖼")
        self.picture_preview.setFixedSize(96, 64)
        self.picture_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.picture_preview.setStyleSheet(
            "background:#eef2f6;border:1px solid #d8e0ea;border-radius:6px;")
        row.addWidget(self.picture_preview)
        col = QVBoxLayout()
        self.picture_edit = QLineEdit()
        col.addWidget(self.picture_edit)
        btns = QHBoxLayout()
        up = QPushButton("⬆ 上传图片")
        up.clicked.connect(self._upload_picture)
        sel = QPushButton("🔍 从图标库选择")
        sel.clicked.connect(self._pick_picture)
        btns.addWidget(up)
        btns.addWidget(sel)
        btns.addStretch(1)
        col.addLayout(btns)
        row.addLayout(col, 1)
        return row

    @staticmethod
    def _card_title(text):
        lab = QLabel(text)
        lab.setStyleSheet("color:#1f4f7e;font-weight:bold;font-size:13px;")
        return lab

    @staticmethod
    def _form_row(label, widget, unit=""):
        row = QHBoxLayout()
        row.setSpacing(8)
        lab = QLabel(label)
        lab.setMinimumWidth(88)
        lab.setStyleSheet("color:#5d6b7a;")
        row.addWidget(lab)
        row.addWidget(widget, 1)
        if unit:
            u = QLabel(unit)
            u.setStyleSheet("color:#8a97a5;")
            row.addWidget(u)
        return row

    # ---------- 数据加载 ----------

    def _visible_events(self):
        events = self.events
        if self.file_path:
            norm = self.file_path.replace("\\", "/")
            events = [e for e in events
                      if (e.get("file") or "").replace("\\", "/") == norm]
        filt = self.filter_combo.currentIndex()
        if filt == 1:
            events = [e for e in events if e["type"] == "country_event"]
        elif filt == 2:
            events = [e for e in events if e["type"] == "news_event"]
        elif filt == 3:
            events = [e for e in events if e["type"] == "unit_leader_event"]
        elif filt == 4:
            events = [e for e in events if e.get("hidden")]
        return events

    def _reload(self):
        self.events = load_event_entities(self.mod_path, self.hoi4_path)
        self._event_map = {e["id"]: e for e in self.events}
        self._apply_filter()

    def _apply_filter(self):
        events = self._visible_events()
        self.sidebar.set_entities([
            (e["id"], "%s · %s [%s]" % (e["id"], self._event_cn(e), e["type"]))
            for e in events
        ])

    def _event_cn(self, e):
        key = e.get("title") or ""
        if not key:
            return ""
        return self._loc_get(key) or key

    def _loc_get(self, key):
        if not self.mod_path:
            return ""
        if key in self._loc_cache:
            return self._loc_cache[key]
        found = find_mod_file_for_key(self.mod_path, key)
        value = ""
        if found:
            value = load_loc_file(found, "simp_chinese").get(key, "")
        if not value and self.hoi4_path:
            try:
                effective = load_effective_dict(self.mod_path, self.hoi4_path,
                                                "simp_chinese")
                value = effective.get(key, "")
            except Exception:
                pass
        self._loc_cache[key] = value
        return value

    # ---------- 选中加载 ----------

    def _on_select(self, event_id):
        self.current_event = self._event_map.get(event_id or "")
        if self.current_event is None:
            return
        e = self.current_event
        self.type_combo.setCurrentText(e["type"])
        self.id_edit.setText(e["id"])
        self.namespace_edit.setText(e.get("namespace", ""))
        self.title_loc.set_key(e.get("title", ""))
        self.title_loc.set_cn(self._loc_get(e.get("title", "")))
        self.desc_loc.set_key(e.get("desc", ""))
        self.desc_loc.set_cn(self._loc_get(e.get("desc", "")))
        self.picture_edit.setText(e.get("picture", ""))
        self.major_check.setChecked(e.get("major", False))
        self.triggered_check.setChecked(e.get("is_triggered_only", False))
        self.fire_once_check.setChecked(e.get("fire_only_once", False))
        self.hidden_check.setChecked(e.get("hidden", False))
        mtth = e.get("mean_time_to_happen") or {}
        try:
            self.mtth_spin.setValue(int(mtth.get("days") or 0))
        except Exception:
            self.mtth_spin.setValue(0)
        self.mtth_modifier_card.set_block_text(mtth.get("modifier", ""))
        self.immediate_card.set_block_text(e.get("immediate", ""))
        self.after_card.set_block_text(e.get("after", ""))
        self.other_fields_table.set_rows(e.get("other_fields", []))
        file_rows = []
        if e.get("file"):
            file_content = self._read_file(e["file"])
            file_rows = parse_file_other_fields(file_content)
        self.file_other_fields_table.set_rows(file_rows)

        # 清空并重建 option 卡片
        while self.option_cards_layout.count():
            item = self.option_cards_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for i, opt in enumerate(e.get("options", []), start=1):
            self._append_option_card(i, opt)
        self.options_count_label.setText(str(len(e.get("options", []))))
        self.file_label.setText(e.get("file", ""))
        self._refresh_picture()

    def _append_option_card(self, index, option=None):
        card = OptionCard(
            index, option or {"name": "", "name_cn": ""}, parent=self,
            on_move_up=self._move_option, on_move_down=self._move_option,
            on_duplicate=self._duplicate_option, on_delete=self._delete_option)
        if option and option.get("name"):
            card.name_loc.set_cn(self._loc_get(option.get("name", "")))
        self.option_cards_layout.addWidget(card)
        return card

    def _option_cards(self):
        out = []
        for i in range(self.option_cards_layout.count()):
            item = self.option_cards_layout.itemAt(i)
            w = item.widget()
            if isinstance(w, OptionCard):
                out.append(w)
        return out

    def _refresh_options_label(self):
        self.options_count_label.setText(str(len(self._option_cards())))

    # ---------- 图片 ----------

    def _gfx_map_data(self):
        if self._gfx_cache is None:
            from gui_translator import get_translator, scan_gfx_folder
            try:
                self._gfx_cache = dict(get_translator().gfx_map)
            except Exception:
                self._gfx_cache = {}
            if self.mod_path:
                try:
                    scan_gfx_folder(self.mod_path, self._gfx_cache)
                except Exception:
                    pass
        return self._gfx_cache

    def _refresh_picture(self):
        from icon_resolver import resolve_pixmap
        value = self.picture_edit.text().strip()
        pm = resolve_pixmap(
            value, dirs=ICON_RULES["event"]["dirs"],
            gfx_map=self._gfx_map_data(), mod_path=self.mod_path,
            hoi4_path=self.hoi4_path)
        if pm is not None and not pm.isNull():
            pm = pm.scaledToHeight(64, Qt.TransformationMode.SmoothTransformation)
            self.picture_preview.setPixmap(pm)
        else:
            self.picture_preview.setText("🖼")

    def _upload_picture(self):
        if not self.mod_path:
            QMessageBox.warning(self, "提示", "请先打开 mod 目录")
            return
        if self.current_event is None:
            QMessageBox.information(self, "提示", "请先选择事件")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "选择事件图片", "",
            "图片 (*.png *.jpg *.jpeg *.bmp *.dds *.tga *.webp)")
        if not path:
            return
        from icon_ops import upload_icon
        base = re.sub(r'[^A-Za-z0-9_.\-]', '_', self.current_event["id"])
        config = ICON_RULES["event"]["upload"]
        value = upload_icon(self.mod_path, path, base, config)
        self.picture_edit.setText(value)
        self._refresh_picture()

    def _pick_picture(self):
        from icon_picker_dialog import IconPickerDialog
        dlg = IconPickerDialog(
            self._gfx_map_data(), parent=self,
            prefix=ICON_RULES["event"].get("picker_prefix", ""),
            current_icon=self.picture_edit.text().strip())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = dlg.get_selected_icon()
            if name:
                self.picture_edit.setText(name)
                self._refresh_picture()

    # ---------- option 增删排序 ----------

    def _reindex_options(self):
        for i, card in enumerate(self._option_cards(), start=1):
            # 更新标题文本
            for j in range(card.layout().count()):
                item = card.layout().itemAt(j)
                if isinstance(item, QHBoxLayout):
                    pass
            card.index = i

    def _move_option(self, card):
        cards = self._option_cards()
        idx = cards.index(card)
        direction = 1 if self.sender() is card.down_btn else -1
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(cards):
            return
        cards[idx], cards[new_idx] = cards[new_idx], cards[idx]
        self._rebuild_option_cards()

    def _duplicate_option(self, card):
        cards = self._option_cards()
        idx = cards.index(card)
        new_raw = card.raw
        new_name = card.name_loc.key() + "_copy"
        new_raw = _replace_scalar_in_seg(new_raw, "name", new_name,
                                         quoted=False)
        new_card = self._append_option_card(
            idx + 2,
            {"raw": new_raw, "name": new_name, "name_cn": card.name_loc.cn(),
             "trigger": card.trigger_text, "ai_chance": card.ai_text})
        self._rebuild_option_cards()
        self._refresh_options_label()
        return new_card

    def _delete_option(self, card):
        cards = self._option_cards()
        if len(cards) <= 1:
            QMessageBox.information(self, "提示", "至少保留一个选项")
            return
        card.deleteLater()
        self._rebuild_option_cards()

    def _rebuild_option_cards(self):
        old = self._option_cards()
        data = []
        for i, card in enumerate(old, start=1):
            data.append((card.raw,
                         card.name_loc.key(),
                         card.trigger_text,
                         card.ai_text,
                         card.name_loc.cn()))
        while self.option_cards_layout.count():
            item = self.option_cards_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for i, (raw, name_key, trigger, ai, cn) in enumerate(data, start=1):
            card = OptionCard(
                i, {"raw": raw, "name": name_key, "name_cn": cn,
                    "trigger": trigger, "ai_chance": ai},
                parent=self, on_move_up=self._move_option,
                on_move_down=self._move_option,
                on_duplicate=self._duplicate_option,
                on_delete=self._delete_option)
            self.option_cards_layout.addWidget(card)
        self._refresh_options_label()

    def _add_option(self):
        card = OptionCard(
            len(self._option_cards()) + 1,
            {"raw": "option = {\n\tname = %s\n}" % (
                "%s.a" % (self.id_edit.text() or "event")),
             "name": "%s.a" % (self.id_edit.text() or "event")},
            parent=self, on_move_up=self._move_option,
            on_move_down=self._move_option,
            on_duplicate=self._duplicate_option,
            on_delete=self._delete_option)
        self.option_cards_layout.addWidget(card)
        self._refresh_options_label()

    # ---------- CRUD ----------

    def _current_file_path(self):
        if self.current_event:
            return self.current_event.get("file")
        if self.events:
            return self.events[0].get("file")
        if self.mod_path:
            return os.path.join(self.mod_path, "events", "events_new.txt")
        return ""

    def _read_file(self, file_path):
        if file_path and os.path.isfile(file_path):
            with open(file_path, "r", encoding="utf-8-sig",
                      errors="ignore") as f:
                return f.read()
        return ""

    def _write_file(self, file_path, content):
        if not file_path:
            return
        if self.mod_path and os.path.normcase(file_path).startswith(
                os.path.normcase(self.mod_path)):
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            atomic_write_text(file_path, content)
            return
        # 原版文件自动落 mod
        rel = self._rel_path(file_path)
        if rel:
            dst, _copied = ensure_file_in_mod(self.mod_path, self.hoi4_path,
                                              rel)
            if dst:
                atomic_write_text(dst, content)
                return
        QMessageBox.warning(self, "保存失败", "无法确定 mod 内写入路径")

    def _rel_path(self, file_path):
        norm = file_path.replace("\\", "/")
        for base in (self.mod_path, self.hoi4_path):
            base_norm = (base or "").replace("\\", "/").rstrip("/")
            if base_norm and norm.startswith(base_norm + "/"):
                return norm[len(base_norm) + 1:]
        return norm

    def _create_event(self):
        eid, ok = QInputDialog.getText(self, "新建事件", "事件 id:")
        eid = (eid or "").strip()
        if not ok or not eid:
            return
        fp = self._current_file_path() or os.path.join(
            self.mod_path or "", "events", "events_new.txt")
        content = self._read_file(fp)
        content = insert_event(content, eid, self.type_combo.currentText(), "")
        self._write_file(fp, content)
        self._reload()
        self.sidebar.set_current(eid)

    def _duplicate_event(self):
        if self.current_event is None:
            QMessageBox.information(self, "提示", "请先选择事件")
            return
        new_id, ok = QInputDialog.getText(
            self, "复制事件", "新事件 id:", text=self.current_event["id"] + "_copy")
        new_id = (new_id or "").strip()
        if not ok or not new_id:
            return
        fp = self.current_event["file"]
        content = self._read_file(fp)
        content = duplicate_event(content, self.current_event["id"], new_id)
        self._write_file(fp, content)
        self._reload()
        self.sidebar.set_current(new_id)

    def _rename_event(self):
        if self.current_event is None:
            QMessageBox.information(self, "提示", "请先选择事件")
            return
        new_id, ok = QInputDialog.getText(
            self, "重命名事件", "新事件 id:", text=self.current_event["id"])
        new_id = (new_id or "").strip()
        if not ok or not new_id:
            return
        fp = self.current_event["file"]
        content = self._read_file(fp)
        content = rename_event(content, self.current_event["id"], new_id)
        self._write_file(fp, content)
        self._reload()
        self.sidebar.set_current(new_id)

    def _delete_event(self):
        if self.current_event is None:
            QMessageBox.information(self, "提示", "请先选择事件")
            return
        reply = QMessageBox.question(
            self, "确认删除", "确定删除事件 %s 吗？" % self.current_event["id"])
        if reply != QMessageBox.StandardButton.Yes:
            return
        fp = self.current_event["file"]
        content = self._read_file(fp)
        content = delete_event(content, self.current_event["id"])
        self._write_file(fp, content)
        self._reload()

    # ---------- 保存与本地化 ----------

    def _loc_file_for(self, key):
        if not key:
            return ""
        found = find_mod_file_for_key(self.mod_path, key)
        if found:
            return found
        return default_mod_loc_file(self.mod_path, "simp_chinese")

    def _save(self):
        if self.current_event is None:
            QMessageBox.information(self, "保存", "没有选中事件。")
            return
        e = self.current_event
        fields = {
            "id": (self.id_edit.text().strip(), False),
            "title": (self.title_loc.key(), False),
            "desc": (self.desc_loc.key(), False),
            "picture": (self.picture_edit.text().strip(), False),
            "major": ("yes" if self.major_check.isChecked() else "no", False),
            "is_triggered_only": (
                "yes" if self.triggered_check.isChecked() else "no", False),
            "fire_only_once": (
                "yes" if self.fire_once_check.isChecked() else "no", False),
            "hidden": ("yes" if self.hidden_check.isChecked() else "no", False),
        }
        blocks = {}
        mtth_days = self.mtth_spin.value()
        if mtth_days > 0 or (e.get("mean_time_to_happen") or {}).get("raw"):
            blocks["mean_time_to_happen.days"] = str(mtth_days)
        if self.mtth_modifier_card.block_text.strip():
            blocks["mean_time_to_happen.modifier"] = \
                self.mtth_modifier_card.block_text
        if self.immediate_card.block_text.strip():
            blocks["immediate"] = self.immediate_card.block_text
        if self.after_card.block_text.strip():
            blocks["after"] = self.after_card.block_text
        options = [c.final_raw() for c in self._option_cards()]
        other_fields = [r for r in self.other_fields_table.rows() if r[0]]
        file_other_fields = [r for r in self.file_other_fields_table.rows() if r[0]]

        fp = e["file"]
        content = self._read_file(fp)
        new_content = apply_event_edits(
            content, e["id"], fields=fields, blocks=blocks, options=options,
            other_fields=other_fields)
        new_content = apply_file_other_fields(new_content, file_other_fields)
        try:
            self._write_file(fp, new_content)
        except Exception as ex:
            QMessageBox.critical(self, "保存失败", str(ex))
            return

        # 本地化写回
        loc_written = 0
        for loc, cn in (
                (self.title_loc.key(), self.title_loc.cn()),
                (self.desc_loc.key(), self.desc_loc.cn())):
            if loc and cn:
                target = self._loc_file_for(loc)
                if target and upsert_loc_entry(target, loc, cn):
                    loc_written += 1
        for card in self._option_cards():
            loc = card.name_loc.key()
            cn = card.name_loc.cn()
            if loc and cn:
                target = self._loc_file_for(loc)
                if target and upsert_loc_entry(target, loc, cn):
                    loc_written += 1

        QMessageBox.information(
            self, "已保存", "已保存到:\n%s\n本地化词条更新：%d"
            % (fp, loc_written))
        self.saved.emit()
        self._reload()

    def _batch_fill_loc(self):
        if not self.mod_path:
            QMessageBox.warning(self, "提示", "请先打开 mod 目录")
            return
        english = {}
        if self.hoi4_path:
            try:
                english = load_effective_dict(self.mod_path, self.hoi4_path,
                                              "english")
            except Exception:
                english = {}
        target = default_mod_loc_file(self.mod_path, "simp_chinese")
        existing = {}
        if os.path.isfile(target):
            existing = load_loc_file(target, "simp_chinese")
        keys = []
        for e in self._visible_events():
            for k in (e.get("title"), e.get("desc")):
                if k:
                    keys.append(k)
            for opt in e.get("options", []):
                name = opt.get("name")
                if name:
                    keys.append(name)
        written = 0
        for k in keys:
            if k in existing:
                continue
            val = english.get(k) or k
            if upsert_loc_entry(target, k, val, "simp_chinese"):
                written += 1
        QMessageBox.information(
            self, "批量本地化", "已补写 %d 个缺失词条到:\n%s" % (written, target))
        self._loc_cache.clear()


def open_event_editor(mod_path="", hoi4_path="", file_path="",
                      entity_id="", parent=None):
    """打开事件编辑器；file_path 限定来源文件，entity_id 定位事件。"""
    dlg = EventEditorDialog(mod_path=mod_path, hoi4_path=hoi4_path,
                            file_path=file_path, parent=parent)
    dlg.show()
    if entity_id:
        dlg.sidebar.set_current(entity_id)
    return dlg
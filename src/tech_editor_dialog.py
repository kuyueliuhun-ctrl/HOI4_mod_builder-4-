# -*- coding: utf-8 -*-
"""科技（Technology）专用编辑器 UI。

批次 4 完整版：
- 左边 QTreeWidget 目录树（folder → 科技，中文名+年份，搜索过滤）
- 表单：本地化双行、图标 183x84、start_year/research_cost、
  categories 徽章、folder + position、path 表、enable_equipments、
  allow / ai_will_do / category_* 加成块、其他字段表
- 保存：科技块内容级变换 + 原子写（原版自动落 mod）+ 本地化写回
"""

from __future__ import annotations

import os
import re

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QHeaderView,
    QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QScrollArea, QSpinBox, QSplitter,
    QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from ai_ui_common import EntityListSidebar
from content_types import ICON_RULES
from event_editor_dialog import LocEdit, OtherFieldsTable, StructuredBlockCard
from localisation_editor_data import (
    default_mod_loc_file, find_mod_file_for_key, load_loc_file,
    load_effective_dict, upsert_loc_entry,
)
from state_build_ops import ensure_file_in_mod
from tech_data import (
    apply_tech_edits, delete_tech, duplicate_tech, insert_tech,
    load_tech_entities, rename_tech,
)
from write_utils import atomic_write_text


class TechEditorDialog(QDialog):
    """科技专用编辑器（非模态）。"""

    saved = pyqtSignal()

    def __init__(self, mod_path="", hoi4_path="", file_path="", parent=None):
        super().__init__(parent)
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.file_path = file_path or ""
        self.techs = {}
        self.current_tech_id = ""
        self._loc_cache = {}
        self._gfx_cache = None

        # 兼容旧测试：保留 hidden EntityListSidebar
        self.sidebar = EntityListSidebar(
            "科技", parent=self, enable_crud=False,
            mod_path=self.mod_path, hoi4_path=self.hoi4_path)
        self.sidebar.setVisible(False)

        self.setWindowTitle("科技编辑器")
        self.resize(1240, 840)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self._build_left())
        split.addWidget(self._build_right())
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        outer.addWidget(split, 1)

        bottom = QHBoxLayout()
        self.canvas_btn = QPushButton("🌳 在科技树画布中定位 ›")
        self.canvas_btn.clicked.connect(self._locate_in_canvas)
        bottom.addWidget(self.canvas_btn)
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
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索科技（中文名/id）...")
        self.search_edit.textChanged.connect(self._apply_filter)
        root.addWidget(self.search_edit)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("科技树目录（folder → 科技）")
        self.tree.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)
        root.addWidget(self.tree, 1)
        add_btn = QPushButton("＋ 新建科技…")
        add_btn.clicked.connect(self._create_tech)
        root.addWidget(add_btn)
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

        basic = self._card("基本信息")
        bl = basic.layout()
        self.id_edit = QLineEdit()
        self.name_loc = LocEdit("", "", "科技名本地化键（如 infantry_weapons）")
        self.desc_loc = LocEdit("", "", "描述本地化键（如 infantry_weapons_desc）")
        self.start_year_edit = QLineEdit()
        self.cost_edit = QLineEdit()
        bl.addLayout(self._form_row("科技 id", self.id_edit))
        bl.addWidget(QLabel("科技名（本地化双行）"))
        bl.addWidget(self.name_loc)
        bl.addWidget(QLabel("描述（本地化双行）"))
        bl.addWidget(self.desc_loc)
        bl.addLayout(self._form_row("起始年份 start_year", self.start_year_edit))
        bl.addLayout(self._form_row("研究花费 research_cost", self.cost_edit))
        form.addWidget(basic)

        icon_card = self._card("科技图标")
        il = icon_card.layout()
        il.addLayout(self._build_icon_row())
        form.addWidget(icon_card)

        cat_card = self._card("分类与目录")
        cl = cat_card.layout()
        self.categories_list = QListWidget()
        self.categories_list.setMaximumHeight(80)
        cl.addWidget(self.categories_list)
        cbtns = QHBoxLayout()
        add_cat = QPushButton("＋ 添加分类")
        add_cat.clicked.connect(self._add_category)
        del_cat = QPushButton("－ 移除选中")
        del_cat.clicked.connect(self._remove_selected_category)
        cbtns.addWidget(add_cat)
        cbtns.addWidget(del_cat)
        cbtns.addStretch(1)
        cl.addLayout(cbtns)
        self.folder_combo = QComboBox()
        self.folder_combo.setEditable(True)
        cl.addLayout(self._form_row("folder 目录", self.folder_combo))
        pos = QHBoxLayout()
        self.pos_x_spin = QSpinBox()
        self.pos_y_spin = QSpinBox()
        self.pos_x_spin.setRange(-9999, 9999)
        self.pos_y_spin.setRange(-9999, 9999)
        pos.addWidget(QLabel("x"))
        pos.addWidget(self.pos_x_spin)
        pos.addWidget(QLabel("y"))
        pos.addWidget(self.pos_y_spin)
        pos.addStretch(1)
        cl.addLayout(pos)
        form.addWidget(cat_card)

        path_card = self._card("前置与后续（path）")
        pl = path_card.layout()
        self.path_table = QTableWidget(0, 2)
        self.path_table.setHorizontalHeaderLabels(
            ["leads_to_tech（前置→后续）", "research_cost_coeff"])
        self.path_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.path_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self.path_table.verticalHeader().setVisible(False)
        pl.addWidget(self.path_table)
        pbtns = QHBoxLayout()
        add_path = QPushButton("＋ 添加连线")
        add_path.clicked.connect(lambda: self._add_path_row())
        del_path = QPushButton("－ 删除选中")
        del_path.clicked.connect(self._delete_selected_rows)
        pbtns.addWidget(add_path)
        pbtns.addWidget(del_path)
        pbtns.addStretch(1)
        pl.addLayout(pbtns)
        form.addWidget(path_card)

        eq_card = self._card("解锁装备（enable_equipments）")
        el = eq_card.layout()
        self.enable_list = QListWidget()
        self.enable_list.setMaximumHeight(90)
        el.addWidget(self.enable_list)
        ebtns = QHBoxLayout()
        add_eq = QPushButton("＋ 添加装备")
        add_eq.clicked.connect(self._add_enable_equipment)
        del_eq = QPushButton("－ 移除选中")
        del_eq.clicked.connect(self._remove_selected_enable)
        ebtns.addWidget(add_eq)
        ebtns.addWidget(del_eq)
        ebtns.addStretch(1)
        el.addLayout(ebtns)
        form.addWidget(eq_card)

        block_card = self._card("允许与加成块（allow / category_*）")
        blk = block_card.layout()
        self.allow_card = StructuredBlockCard("allow", "", parent=self)
        self.ai_card = StructuredBlockCard("ai_will_do", "", parent=self)
        blk.addWidget(self.allow_card)
        blk.addWidget(self.ai_card)
        bonus_note = QLabel("装备加成块（category_*，修正名自动中文化 + 百分比格式化）")
        bonus_note.setStyleSheet("color:#5d6b7a;font-size:11px;")
        blk.addWidget(bonus_note)
        self.category_cards_layout = QVBoxLayout()
        blk.addLayout(self.category_cards_layout)
        add_bonus = QPushButton("＋ 添加加成块")
        add_bonus.clicked.connect(self._add_category_bonus)
        blk.addWidget(add_bonus)
        form.addWidget(block_card)

        other_card = self._card("其他字段（树编辑器兜底）")
        ol = other_card.layout()
        self.other_fields_table = OtherFieldsTable()
        ol.addWidget(self.other_fields_table)
        form.addWidget(other_card)

        self.file_label = QLabel("")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("color:#5d6b7a;")
        form.addWidget(self.file_label)
        form.addStretch(1)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)
        return wrap

    def _build_icon_row(self):
        row = QHBoxLayout()
        row.setSpacing(10)
        self.icon_preview = QLabel("🔬")
        self.icon_preview.setFixedSize(183, 84)
        self.icon_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_preview.setStyleSheet(
            "background:#101820;color:#d8e0ea;border:1px solid #4a5568;"
            "border-radius:8px;font-size:36px;")
        row.addWidget(self.icon_preview)
        col = QVBoxLayout()
        up = QPushButton("⬆ 上传图标")
        up.clicked.connect(self._upload_icon)
        lib = QPushButton("🔍 从图标库选择")
        lib.clicked.connect(self._pick_icon)
        note = QLabel("展示尺寸 183×84（countrytechtreeview.gui item 盒）")
        note.setStyleSheet("color:#5d6b7a;font-size:11px;")
        col.addWidget(up)
        col.addWidget(lib)
        col.addWidget(note)
        col.addStretch(1)
        row.addLayout(col, 1)
        return row

    @staticmethod
    def _card(title):
        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet(
            "QFrame#Card{background:#ffffff;border:1px solid #d8e0ea;"
            "border-radius:12px;}")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 12)
        t = QLabel(title)
        t.setStyleSheet("color:#1f4f7e;font-weight:bold;font-size:13px;")
        lay.addWidget(t)
        return card

    @staticmethod
    def _form_row(label, widget, unit=""):
        row = QHBoxLayout()
        row.setSpacing(8)
        lab = QLabel(label)
        lab.setMinimumWidth(120)
        lab.setStyleSheet("color:#5d6b7a;")
        row.addWidget(lab)
        row.addWidget(widget, 1)
        if unit:
            u = QLabel(unit)
            u.setStyleSheet("color:#8a97a5;")
            row.addWidget(u)
        return row

    # ---------- 数据加载 ----------

    def _visible_techs(self):
        techs = self.techs
        if self.file_path:
            norm = self.file_path.replace("\\", "/")
            techs = {tid: t for tid, t in techs.items()
                     if (t.get("file") or "").replace("\\", "/") == norm}
        return techs

    def _reload(self):
        self.techs = load_tech_entities(self.mod_path, self.hoi4_path)
        # 兼容隐藏 sidebar 数据
        labels = []
        for tid, t in self.techs.items():
            folder = t.get("folder") or "未分组"
            labels.append((tid, "%s [%s]" % (tid, folder)))
        self.sidebar.set_entities(labels)
        self._apply_filter()

    def _apply_filter(self):
        keyword = self.search_edit.text().strip().lower()
        techs = self._visible_techs()
        folders = {}
        for tid, t in techs.items():
            label = self._tech_label(tid, t)
            if keyword and not self._tech_matches(tid, t, keyword):
                continue
            folder = t.get("folder") or "未分组"
            folders.setdefault(folder, []).append((tid, label))
        self.tree.blockSignals(True)
        self.tree.clear()
        for folder in sorted(folders):
            fitem = QTreeWidgetItem(self.tree, [folder])
            fitem.setFlags(fitem.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            fitem.setExpanded(True)
            for tid, label in sorted(folders[folder],
                                      key=lambda x: x[1].lower()):
                item = QTreeWidgetItem(fitem, [label])
                item.setData(0, Qt.ItemDataRole.UserRole, tid)
                item.setToolTip(0, tid + "\n点击后在右侧编辑该科技")
        self.tree.blockSignals(False)
        # 重建 folder 下拉候选
        current = self.folder_combo.currentText()
        self.folder_combo.blockSignals(True)
        self.folder_combo.clear()
        self.folder_combo.addItem("")
        for folder in sorted(folders):
            self.folder_combo.addItem(folder)
        if current:
            self.folder_combo.setCurrentText(current)
        self.folder_combo.blockSignals(False)
        if self.current_tech_id and self._find_tree_item(self.current_tech_id) is not None:
            self.tree.setCurrentItem(self._find_tree_item(self.current_tech_id))
        else:
            first = self._first_tech_item()
            if first is not None:
                tid = first.data(0, Qt.ItemDataRole.UserRole)
                self.tree.setCurrentItem(first)
                self._load_tech(tid)

    def _first_tech_item(self):
        for i in range(self.tree.topLevelItemCount()):
            folder_item = self.tree.topLevelItem(i)
            for j in range(folder_item.childCount()):
                return folder_item.child(j)
        return None

    def _find_tree_item(self, tech_id):
        for i in range(self.tree.topLevelItemCount()):
            folder_item = self.tree.topLevelItem(i)
            for j in range(folder_item.childCount()):
                item = folder_item.child(j)
                if item.data(0, Qt.ItemDataRole.UserRole) == tech_id:
                    return item
        return None

    def _tech_matches(self, tid, t, keyword):
        return (keyword in tid.lower()
                or keyword in self._loc_get(tid).lower()
                or keyword in (t.get("folder") or "").lower())

    def _tech_label(self, tid, t):
        year = t.get("start_year") or ""
        cn = self._loc_get(tid) or tid
        if year:
            return "%s · %s" % (cn, year)
        return cn

    def _loc_get(self, key):
        if not key or not self.mod_path:
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

    def _on_tree_item_clicked(self, item, _column):
        tech_id = item.data(0, Qt.ItemDataRole.UserRole)
        if tech_id:
            self._load_tech(tech_id)

    def _load_tech(self, tech_id):
        self.current_tech_id = tech_id or ""
        t = self.techs.get(tech_id or "")
        if t is None:
            return
        self.id_edit.setText(tech_id)
        self.name_loc.set_key(tech_id)
        self.name_loc.set_cn(self._loc_get(tech_id))
        self.desc_loc.set_key(tech_id + "_desc")
        self.desc_loc.set_cn(self._loc_get(tech_id + "_desc"))
        self.start_year_edit.setText(t.get("start_year", ""))
        self.cost_edit.setText(t.get("research_cost", ""))
        self.folder_combo.setCurrentText(t.get("folder", ""))
        try:
            self.pos_x_spin.setValue(int(t.get("position_x") or 0))
        except Exception:
            self.pos_x_spin.setValue(0)
        try:
            self.pos_y_spin.setValue(int(t.get("position_y") or 0))
        except Exception:
            self.pos_y_spin.setValue(0)
        self.categories_list.clear()
        for c in t.get("categories", []):
            self.categories_list.addItem(QListWidgetItem(c))
        self.path_table.setRowCount(0)
        for r in t.get("path", []):
            self._add_path_row(r.get("leads_to_tech", ""),
                               r.get("research_cost_coeff", ""))
        self.enable_list.clear()
        for e in t.get("enable_equipments", []):
            self.enable_list.addItem(QListWidgetItem(e))
        self.allow_card.set_block_text(t.get("allow", ""))
        self.ai_card.set_block_text(t.get("ai_will_do", ""))
        # 重建 category 卡片
        while self.category_cards_layout.count():
            item = self.category_cards_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for key, raw in t.get("category_blocks", []):
            self._append_category_card(key, raw)
        self.other_fields_table.set_rows(t.get("other_fields", []))
        self.file_label.setText(t.get("file", ""))
        self._refresh_icon()

    def _append_category_card(self, key, raw):
        card = StructuredBlockCard(key, raw, parent=self)
        row = QHBoxLayout()
        row.addWidget(card, 1)
        del_btn = QPushButton("🗑")
        del_btn.setFixedSize(30, 28)
        del_btn.clicked.connect(
            lambda: self._remove_category_card(card))
        row.addWidget(del_btn)
        self.category_cards_layout.addLayout(row)

    def _remove_category_card(self, card):
        for i in range(self.category_cards_layout.count()):
            item = self.category_cards_layout.itemAt(i)
            if item.layout() is not None:
                lay = item.layout()
                for j in range(lay.count()):
                    w = lay.itemAt(j).widget()
                    if w is card:
                        while lay.count():
                            w2 = lay.takeAt(0).widget()
                            if w2 is not None:
                                w2.deleteLater()
                        self.category_cards_layout.removeItem(item)
                        return

    # ---------- 图标 ----------

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

    def _refresh_icon(self):
        from icon_resolver import resolve_pixmap
        tid = self.current_tech_id or ""
        pm = resolve_pixmap(
            tid, dirs=ICON_RULES["tech"]["dirs"], gfx_map=self._gfx_map_data(),
            mod_path=self.mod_path, hoi4_path=self.hoi4_path)
        # 科技按 GFX_<id>_medium 查找；裸 id 也交给 resolve_pixmap 变体链
        if pm is not None and not pm.isNull():
            pm = pm.scaled(183, 84, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            self.icon_preview.setPixmap(pm)
        else:
            self.icon_preview.setText("🔬")

    def _upload_icon(self):
        if not self.mod_path:
            QMessageBox.warning(self, "提示", "请先打开 mod 目录")
            return
        if not self.current_tech_id:
            QMessageBox.information(self, "提示", "请先选择科技")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "选择科技图标", "",
            "图片 (*.png *.jpg *.jpeg *.bmp *.dds *.tga *.webp)")
        if not path:
            return
        from tech_icon_ops import upload_tech_icon
        info = upload_tech_icon(self.mod_path, self.current_tech_id, path)
        self._gfx_cache = None
        self._refresh_icon()
        QMessageBox.information(
            self, "上传成功",
            "科技图标已上传\nsprite: %s\n图片: %s"
            % (info.get("sprite_name", ""), info.get("texture_rel", "")))

    def _pick_icon(self):
        if not self.current_tech_id:
            QMessageBox.information(self, "提示", "请先选择科技")
            return
        from icon_picker_dialog import IconPickerDialog
        dlg = IconPickerDialog(
            self._gfx_map_data(), parent=self, prefix="GFX_",
            current_icon="GFX_%s_medium" % self.current_tech_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_icon()

    # ---------- 列表操作 ----------

    def _add_category(self):
        candidates = []
        if self.mod_path:
            tags_dir = os.path.join(self.mod_path, "common", "technology_tags")
            if os.path.isdir(tags_dir):
                for n in sorted(os.listdir(tags_dir)):
                    if n.lower().endswith(".txt"):
                        candidates.append(os.path.splitext(n)[0])
        item, ok = QInputDialog.getItem(
            self, "添加分类", "科技分类（候选来自 technology_tags）：",
            candidates or ["infantry_tech", "armor", "artillery"], 0, True)
        item = (item or "").strip()
        if ok and item:
            self.categories_list.addItem(QListWidgetItem(item))

    def _remove_selected_category(self):
        for item in self.categories_list.selectedItems():
            self.categories_list.takeItem(self.categories_list.row(item))

    def _add_path_row(self, leads="", coeff=""):
        r = self.path_table.rowCount()
        self.path_table.insertRow(r)
        self.path_table.setItem(r, 0, QTableWidgetItem(str(leads)))
        self.path_table.setItem(r, 1, QTableWidgetItem(str(coeff)))

    def _delete_selected_rows(self):
        rows = sorted({i.row() for i in self.path_table.selectedIndexes()},
                      reverse=True)
        for r in rows:
            self.path_table.removeRow(r)

    def _add_enable_equipment(self):
        item, ok = QInputDialog.getText(self, "添加装备", "装备 id：")
        item = (item or "").strip()
        if ok and item:
            self.enable_list.addItem(QListWidgetItem(item))

    def _remove_selected_enable(self):
        for item in self.enable_list.selectedItems():
            self.enable_list.takeItem(self.enable_list.row(item))

    def _add_category_bonus(self):
        key, ok = QInputDialog.getText(
            self, "添加加成块", "块键（如 category_infantry_equipment）：",
            text="category_")
        key = (key or "").strip()
        if not ok or not key:
            return
        self._append_category_card(key, "%s = {\n}" % key)

    # ---------- CRUD ----------

    def _current_file_path(self):
        if self.current_tech_id:
            t = self.techs.get(self.current_tech_id)
            if t:
                return t.get("file")
        if self.techs:
            return next(iter(self.techs.values())).get("file")
        if self.mod_path:
            return os.path.join(self.mod_path, "common", "technologies",
                                "technologies_new.txt")
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

    def _create_tech(self):
        tid, ok = QInputDialog.getText(self, "新建科技", "科技 id:")
        tid = (tid or "").strip()
        if not ok or not tid:
            return
        fp = self._current_file_path() or os.path.join(
            self.mod_path or "", "common", "technologies",
            "technologies_new.txt")
        content = self._read_file(fp)
        folder = self.folder_combo.currentText().strip() or ""
        content = insert_tech(content, tid, folder=folder)
        self._write_file(fp, content)
        self._reload()
        self._load_tech(tid)

    # ---------- 保存 ----------

    def _loc_file_for(self, key):
        if not key:
            return ""
        found = find_mod_file_for_key(self.mod_path, key)
        if found:
            return found
        return default_mod_loc_file(self.mod_path, "simp_chinese")

    def _path_rows(self):
        rows = []
        for r in range(self.path_table.rowCount()):
            leads = self.path_table.item(r, 0)
            coeff = self.path_table.item(r, 1)
            rows.append({
                "leads_to_tech": leads.text().strip() if leads else "",
                "research_cost_coeff": coeff.text().strip() if coeff else "",
            })
        return [r for r in rows if r["leads_to_tech"]]

    def _category_blocks(self):
        out = {}
        for i in range(self.category_cards_layout.count()):
            item = self.category_cards_layout.itemAt(i)
            lay = item.layout()
            if lay is None or lay.count() == 0:
                continue
            w = lay.itemAt(0).widget()
            if isinstance(w, StructuredBlockCard) and w.block_text.strip():
                out[w.block_key] = w.block_text
        return out

    def _save(self):
        if not self.current_tech_id:
            QMessageBox.information(self, "保存", "没有选中科技。")
            return
        t = self.techs[self.current_tech_id]
        fields = {
            "start_year": self.start_year_edit.text().strip(),
            "research_cost": self.cost_edit.text().strip(),
        }
        blocks = {}
        if self.allow_card.block_text.strip():
            blocks["allow"] = self.allow_card.block_text
        if self.ai_card.block_text.strip():
            blocks["ai_will_do"] = self.ai_card.block_text
        blocks.update(self._category_blocks())

        categories = [self.categories_list.item(i).text().strip()
                      for i in range(self.categories_list.count())]
        enable = [self.enable_list.item(i).text().strip()
                  for i in range(self.enable_list.count())]
        other_fields = [r for r in self.other_fields_table.rows() if r[0]]

        fp = t["file"]
        content = self._read_file(fp)
        folder_name = self.folder_combo.currentText().strip()
        folder_position = None
        if folder_name or t.get("folder") or t.get("folder_position"):
            folder_position = {
                "name": folder_name,
                "x": self.pos_x_spin.value(),
                "y": self.pos_y_spin.value()
            }
        new_content = apply_tech_edits(
            content, self.current_tech_id,
            fields=fields,
            blocks=blocks,
            categories=categories,
            enable_equipments=enable,
            paths=self._path_rows(),
            folder_position=folder_position,
            other_fields=other_fields)
        try:
            self._write_file(fp, new_content)
        except Exception as ex:
            QMessageBox.critical(self, "保存失败", str(ex))
            return

        loc_written = 0
        if self.name_loc.key() and self.name_loc.cn():
            target = self._loc_file_for(self.name_loc.key())
            if target and upsert_loc_entry(target, self.name_loc.key(),
                                           self.name_loc.cn()):
                loc_written += 1
        desc_key = self.desc_loc.key() or (self.current_tech_id + "_desc")
        if desc_key and self.desc_loc.cn():
            target = self._loc_file_for(desc_key)
            if target and upsert_loc_entry(target, desc_key,
                                           self.desc_loc.cn()):
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
        for tid, t in self._visible_techs().items():
            keys.append(tid)
            if t.get("special_project_specialization"):
                keys.append(t.get("special_project_specialization"))
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

    def _locate_in_canvas(self):
        fp = self.current_tech_id and self.techs.get(self.current_tech_id, {}).get("file")
        if not fp:
            QMessageBox.information(self, "提示", "请先选择科技")
            return
        win = self.window()
        if win is not None and hasattr(win, "custom_view") \
                and hasattr(win.custom_view, "show_tech_tree_file"):
            win.custom_view.show_tech_tree_file(fp)
        elif win is not None and hasattr(win, "_on_workbench_tech_file"):
            win._on_workbench_tech_file(fp)


def open_tech_editor(mod_path="", hoi4_path="", file_path="",
                     tech_id="", parent=None):
    """打开科技编辑器；file_path 限定来源文件，tech_id 定位科技。"""
    dlg = TechEditorDialog(mod_path=mod_path, hoi4_path=hoi4_path,
                           file_path=file_path, parent=parent)
    dlg.show()
    if tech_id:
        dlg._load_tech(tech_id)
    return dlg
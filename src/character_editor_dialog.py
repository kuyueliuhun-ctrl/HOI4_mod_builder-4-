"""角色（Character）专用编辑器（单页三栏，方案 B）

批 A 修复：roles 结构化为可编辑条目（类型/字段/traits/desc）、肖像槽位表化、
角色 desc 词条编辑；未知行无损保留，未知块（含 instance = { ... }）经
ScriptBlockEditorDialog 结构化编辑后写回。
保存走 save_file_v2（结构化原子写）+ 本地化 upsert（名称/角色描述/职责描述）。
"""

from __future__ import annotations

import os
import re

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from character_data import (
    ROLE_FIELDS, ROLE_TYPES, load_file, save_file_v2,
    role_get_field, role_set_field, role_summary,
)
from localisation_editor_data import (
    default_mod_loc_file, find_mod_file_for_key, load_effective_dict,
    upsert_loc_entry,
)


def _char_file_list(mod_path, hoi4_path):
    files = []
    for base in (mod_path, hoi4_path):
        if not base:
            continue
        d = os.path.join(base, "common", "characters")
        if os.path.isdir(d):
            for n in sorted(os.listdir(d)):
                if n.lower().endswith(".txt"):
                    files.append(os.path.join(d, n))
    return files


def _block_key(raw):
    """从未知块原始文本提取块键（兼容字符串形式的未知块）。"""
    m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{", raw or "")
    return m.group(1) if m else "block"


def _unknown_blocks_of(meta):
    """兼容新版 structured list 与旧版 raw string 列表。"""
    ub = meta.get("unknown_blocks")
    if ub:
        return ub
    ob = meta.get("others_blocks") or []
    if ob:
        return ob
    return ub or []


class CharacterEditorDialog(QDialog):
    """角色专用编辑器（非模态，单页三栏：左列表 / 中基本信息+肖像 / 右职责）。"""

    def __init__(self, mod_path="", hoi4_path="", parent=None):
        super().__init__(parent)
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self._files = []
        self._current_file = ""
        self._header = ""
        self._tail = ""
        self._metas = []
        self._desc_keys = {}   # char_id -> 角色描述本地化键
        self._loc = {}

        self.setWindowTitle("角色（Character）编辑器")
        self.resize(1320, 760)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._build_ui()
        self._load_files()
        if self.file_combo.count():
            self._switch_file(0)

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("文件:"))
        self.file_combo = QComboBox()
        self.file_combo.setMinimumWidth(460)
        self.file_combo.currentIndexChanged.connect(self._on_file_changed)
        top.addWidget(self.file_combo, 1)
        add_btn = QPushButton("＋ 新建角色")
        add_btn.clicked.connect(self._add_char)
        dup_btn = QPushButton("⧉ 复制")
        dup_btn.clicked.connect(self._dup_char)
        del_btn = QPushButton("🗑 删除")
        del_btn.clicked.connect(self._delete_char)
        refresh_btn = QPushButton("⟳ 刷新")
        refresh_btn.clicked.connect(self._reload)
        for b in (add_btn, dup_btn, del_btn, refresh_btn):
            top.addWidget(b)
        root.addLayout(top)

        split = QSplitter(Qt.Orientation.Horizontal)

        # ── 左：角色列表 ──
        left = QWidget()
        llay = QVBoxLayout(left)
        llay.addWidget(QLabel("角色"))
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_select)
        llay.addWidget(self.list, 1)
        split.addWidget(left)

        # ── 中：基本信息 + 肖像 ──
        mid = QWidget()
        mlay = QVBoxLayout(mid)
        info_form = QFormLayout()
        self.id_label = QLabel("—")
        info_form.addRow("ID:", self.id_label)
        self.name_loc_edit = QLineEdit()
        self.name_loc_edit.setPlaceholderText("显示名本地化键（name = \"...\"）")
        info_form.addRow("名称键:", self.name_loc_edit)
        self.cn_edit = QLineEdit()
        self.cn_edit.setPlaceholderText("该名称键的中文翻译（保存时写入本地化）")
        info_form.addRow("中文名:", self.cn_edit)
        self.desc_key_edit = QLineEdit()
        self.desc_key_edit.setPlaceholderText("角色描述本地化键（默认 <ID>_desc）")
        info_form.addRow("描述键:", self.desc_key_edit)
        self.desc_cn_edit = QLineEdit()
        self.desc_cn_edit.setPlaceholderText("角色描述中文（保存时写入本地化）")
        info_form.addRow("描述中文:", self.desc_cn_edit)
        mlay.addLayout(info_form)

        mlay.addWidget(QLabel("肖像槽位（类型 / 尺寸 / 贴图）"))
        self.portraits_table = QTableWidget(0, 4)
        self.portraits_table.setHorizontalHeaderLabels(
            ["类型 scope", "尺寸 size", "贴图 texture", "预览"])
        self.portraits_table.horizontalHeader().setStretchLastSection(True)
        mlay.addWidget(self.portraits_table, 1)
        pbar = QHBoxLayout()
        p_add = QPushButton("＋ 添加肖像")
        p_add.clicked.connect(self._add_portrait)
        p_del = QPushButton("🗑 删除选中")
        p_del.clicked.connect(self._del_portrait)
        p_upload = QPushButton("⬆ 上传肖像")
        p_upload.clicked.connect(self._upload_portrait)
        pbar.addWidget(p_add)
        pbar.addWidget(p_del)
        pbar.addWidget(p_upload)
        pbar.addStretch()
        mlay.addLayout(pbar)

        mlay.addWidget(QLabel("未知块（✎ 可编辑）"))
        self.unknown_list = QListWidget()
        self.unknown_list.setMaximumHeight(110)
        mlay.addWidget(self.unknown_list)
        ubar = QHBoxLayout()
        edit_unknown_btn = QPushButton("✎ 编辑未知块")
        edit_unknown_btn.clicked.connect(self._edit_unknown_block)
        ubar.addWidget(edit_unknown_btn)
        ubar.addStretch()
        mlay.addLayout(ubar)

        self.keep_info = QLabel("")
        self.keep_info.setWordWrap(True)
        mlay.addWidget(self.keep_info)
        split.addWidget(mid)

        # ── 右：角色职责 ──
        right = QWidget()
        rlay = QVBoxLayout(right)
        rhead = QHBoxLayout()
        rhead.addWidget(QLabel("角色职责 roles"))
        r_add = QPushButton("＋ 添加职责")
        r_add.clicked.connect(self._add_role)
        r_del = QPushButton("🗑 删除选中")
        r_del.clicked.connect(self._del_role)
        rhead.addWidget(r_add)
        rhead.addWidget(r_del)
        rlay.addLayout(rhead)
        self.role_list = QListWidget()
        self.role_list.currentItemChanged.connect(self._on_role_select)
        rlay.addWidget(self.role_list, 1)

        self.role_form = QFormLayout()
        self.role_type_combo = QComboBox()
        self.role_type_combo.addItems(list(ROLE_TYPES))
        self.role_type_combo.currentTextChanged.connect(self._on_role_type_changed)
        self.role_form.addRow("类型:", self.role_type_combo)
        self.role_fields = {}      # field -> QLineEdit
        self.role_field_grid = QGridLayout()
        self._rebuild_field_form("country_leader")
        self.role_form.addRow(self._role_field_widget())
        self.role_traits_edit = QLineEdit()
        self.role_traits_edit.setPlaceholderText("trait1 trait2 ...（空格分隔）")
        self.role_traits_edit.textChanged.connect(self._on_traits_changed)
        self.role_form.addRow("特质 traits:", self.role_traits_edit)
        self.role_desc_key_edit = QLineEdit()
        self.role_desc_key_edit.setPlaceholderText("职责描述本地化键（desc = ...）")
        self.role_desc_key_edit.textChanged.connect(self._on_field_changed)
        self.role_form.addRow("desc 键:", self.role_desc_key_edit)
        self.role_desc_cn_edit = QLineEdit()
        self.role_desc_cn_edit.setPlaceholderText("职责描述中文（保存时写入本地化）")
        self.role_form.addRow("desc 中文:", self.role_desc_cn_edit)
        rlay.addLayout(self.role_form)
        split.addWidget(right)

        split.setSizes([240, 620, 460])
        root.addWidget(split, 1)

        bottom = QHBoxLayout()
        bottom.addStretch()
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save)
        bottom.addWidget(save_btn)
        root.addLayout(bottom)

    def _role_field_widget(self):
        w = QWidget()
        w.setLayout(self.role_field_grid)
        return w

    def _rebuild_field_form(self, role_type):
        """按职责类型重建字段表单（保留已有输入值）。"""
        while self.role_field_grid.count():
            it = self.role_field_grid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self.role_fields = {}
        fields = ROLE_FIELDS.get(role_type, [])
        for i, f in enumerate(fields):
            label = QLabel(f + ":")
            edit = QLineEdit()
            edit.setPlaceholderText(f)
            edit.setProperty("char_field", f)
            edit.textChanged.connect(self._on_field_changed)
            self.role_field_grid.addWidget(label, i, 0)
            self.role_field_grid.addWidget(edit, i, 1)
            self.role_fields[f] = edit

    # ---------------- 生命周期 ----------------
    def _load_files(self):
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        self._files = _char_file_list(self.mod_path, self.hoi4_path)
        for fp in self._files:
            rel = os.path.relpath(fp, self.mod_path or os.path.dirname(fp))
            src = "mod" if os.path.normcase(fp).startswith(os.path.normcase(self.mod_path or "")) else "游戏"
            self.file_combo.addItem("{:5s} {}".format(src, rel), fp)
        self.file_combo.blockSignals(False)

    def _on_file_changed(self, idx):
        self._switch_file(idx)

    def _switch_file(self, idx):
        if 0 <= idx < len(self._files):
            self._current_file = self._files[idx]
            self._reload()

    def _reload(self):
        if not self._current_file or not os.path.isfile(self._current_file):
            return
        try:
            self._header, self._metas, self._tail = load_file(self._current_file)
        except Exception as e:
            QMessageBox.warning(self, "读取失败", str(e))
            return
        self._loc = load_effective_dict(self.mod_path, self.hoi4_path, "simp_chinese")
        self._desc_keys = {}
        self.list.blockSignals(True)
        self.list.clear()
        for m in self._metas:
            item = QListWidgetItem(m["id"])
            item.setData(Qt.ItemDataRole.UserRole, m["id"])
            self.list.addItem(item)
        self.list.blockSignals(False)
        if self.list.count():
            self.list.setCurrentRow(0)
            self._load_meta()

    def _current_meta(self):
        item = self.list.currentItem()
        if item is None:
            return None
        cid = item.data(Qt.ItemDataRole.UserRole)
        for m in self._metas:
            if m["id"] == cid:
                return m
        return None

    def _load_meta(self):
        m = self._current_meta()
        if m is None:
            return
        self.id_label.setText(m["id"])
        # 基本信息
        self.name_loc_edit.blockSignals(True)
        self.cn_edit.blockSignals(True)
        self.desc_key_edit.blockSignals(True)
        self.desc_cn_edit.blockSignals(True)
        self.name_loc_edit.setText(m["name_loc"])
        self.cn_edit.setText(self._loc.get(m["name_loc"], ""))
        dkey = m.get("desc_loc") or self._desc_keys.get(m["id"]) or (m["id"] + "_desc")
        self._desc_keys[m["id"]] = dkey
        self.desc_key_edit.setText(dkey)
        self.desc_cn_edit.setText(self._loc.get(dkey, ""))
        self.name_loc_edit.blockSignals(False)
        self.cn_edit.blockSignals(False)
        self.desc_key_edit.blockSignals(False)
        self.desc_cn_edit.blockSignals(False)

        # 肖像表
        self._fill_portraits(m.get("portraits_slots") or [])

        # 职责
        self._fill_roles(m.get("role_entries") or [])

        # 未知块列表 + 保留提示
        unknown_blocks = _unknown_blocks_of(m)
        self._fill_unknown_blocks(unknown_blocks)
        n_unk_lines = len(m.get("others_lines", []))
        n_unk_blocks = len(unknown_blocks)
        self.keep_info.setText(
            "顶层未知行 {} 个（保留，保存原样） · 未知块 {} 个（✎ 可编辑）".format(
                n_unk_lines, n_unk_blocks))

    def _make_preview_item(self, texture):
        item = QTableWidgetItem("")
        try:
            from icon_resolver import resolve_pixmap
            pm = resolve_pixmap(
                texture, dirs=["gfx/Leaders", "gfx/interface/portraits"],
                mod_path=self.mod_path, hoi4_path=self.hoi4_path)
            if pm is not None and not pm.isNull():
                item.setIcon(QIcon(pm))
                item.setText("预览")
        except Exception:
            pass
        return item

    def _upload_portrait(self):
        row = self.portraits_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "上传肖像", "请先选中要上传的肖像行。")
            return
        scope = self.portraits_table.item(row, 0)
        size = self.portraits_table.item(row, 1)
        if scope is None or size is None:
            return
        from PyQt6.QtWidgets import QFileDialog
        path, _f = QFileDialog.getOpenFileName(
            self, "选择肖像图片", "", "图片 (*.png *.jpg *.jpeg *.dds *.tga)")
        if not path:
            return
        from icon_ops import upload_icon
        from content_types import ICON_RULES
        m = self._current_meta()
        cid = m["id"] if m else "char"
        base = "%s_%s_%s" % (cid, scope.text().strip(), size.text().strip())
        try:
            value = upload_icon(
                self.mod_path, path, base,
                ICON_RULES["character"]["upload"])
        except Exception as e:
            QMessageBox.critical(self, "上传失败", str(e))
            return
        self.portraits_table.setItem(row, 2, QTableWidgetItem(value))
        self.portraits_table.setItem(row, 3, self._make_preview_item(value))
        self._portraits_changed = True

    def _fill_portraits(self, slots):
        self.portraits_table.blockSignals(True)
        self.portraits_table.setRowCount(0)
        for s in slots:
            r = self.portraits_table.rowCount()
            self.portraits_table.insertRow(r)
            self.portraits_table.setItem(r, 0, QTableWidgetItem(s.get("scope", "")))
            self.portraits_table.setItem(r, 1, QTableWidgetItem(s.get("size", "")))
            self.portraits_table.setItem(r, 2, QTableWidgetItem(s.get("texture", "")))
            self.portraits_table.setItem(
                r, 3, self._make_preview_item(s.get("texture", "")))
        self.portraits_table.blockSignals(False)

    def _portrait_slots_from_table(self):
        slots = []
        for r in range(self.portraits_table.rowCount()):
            scope = self.portraits_table.item(r, 0)
            size = self.portraits_table.item(r, 1)
            tex = self.portraits_table.item(r, 2)
            scope_t = scope.text().strip() if scope else ""
            size_t = size.text().strip() if size else ""
            tex_t = tex.text().strip() if tex else ""
            if scope_t and size_t and tex_t:
                slots.append({"scope": scope_t, "size": size_t, "texture": tex_t})
        return slots

    def _add_portrait(self):
        r = self.portraits_table.rowCount()
        self.portraits_table.insertRow(r)
        self.portraits_table.setItem(r, 0, QTableWidgetItem("civilian"))
        self.portraits_table.setItem(r, 1, QTableWidgetItem("large"))
        self.portraits_table.setItem(r, 2, QTableWidgetItem("GFX_"))
        self.portraits_table.setItem(r, 3, self._make_preview_item(""))
        self.portraits_table.setCurrentCell(r, 2)

    def _del_portrait(self):
        rows = sorted({i.row() for i in self.portraits_table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.portraits_table.removeRow(r)

    # ---------------- 未知块 ----------------
    def _fill_unknown_blocks(self, entries):
        self.unknown_list.blockSignals(True)
        self.unknown_list.clear()
        for e in entries:
            if isinstance(e, dict):
                key = e.get("key", "block")
                raw = e.get("raw", "")
            else:
                key = _block_key(e)
                raw = e
            lines = raw.strip().splitlines()
            detail = "（{} 行）".format(len(lines)) if lines else ""
            item = QListWidgetItem("{} = {{ ... }} {}".format(key, detail))
            item.setData(Qt.ItemDataRole.UserRole, id(e))
            item.setToolTip((raw or "").strip()[:500])
            self.unknown_list.addItem(item)
        self.unknown_list.blockSignals(False)
        if self.unknown_list.count():
            self.unknown_list.setCurrentRow(0)

    def _current_unknown_entry(self):
        item = self.unknown_list.currentItem()
        if item is None:
            return None
        uid = item.data(Qt.ItemDataRole.UserRole)
        m = self._current_meta()
        if m is None:
            return None
        for e in _unknown_blocks_of(m):
            if id(e) == uid:
                return e
        return None

    def _edit_unknown_block(self):
        m = self._current_meta()
        if m is None:
            QMessageBox.information(self, "提示", "请先选择角色")
            return
        entry = self._current_unknown_entry()
        if entry is None:
            QMessageBox.information(self, "提示", "请先选择要编辑的未知块")
            return
        from ai_ui_common import ScriptBlockEditorDialog
        if isinstance(entry, dict):
            key = entry.get("key", "block")
            raw = entry.get("raw", "")
            dlg = ScriptBlockEditorDialog(
                block_text=raw,
                block_key=key,
                parent=self,
                title="编辑未知块：{}".format(key),
            )
            if dlg.exec():
                entry["raw"] = dlg.get_block_text()
        else:
            key = _block_key(entry)
            raw = entry
            dlg = ScriptBlockEditorDialog(
                block_text=raw,
                block_key=key,
                parent=self,
                title="编辑未知块：{}".format(key),
            )
            if dlg.exec():
                blocks = _unknown_blocks_of(m)
                idx = blocks.index(entry)
                blocks[idx] = dlg.get_block_text()
        blocks = _unknown_blocks_of(m)
        self._fill_unknown_blocks(blocks)

    def _fill_roles(self, entries):
        self.role_list.blockSignals(True)
        self.role_list.clear()
        for e in entries:
            item = QListWidgetItem(role_summary(e))
            item.setData(Qt.ItemDataRole.UserRole, id(e))
            self.role_list.addItem(item)
        self.role_list.blockSignals(False)
        if self.role_list.count():
            self.role_list.setCurrentRow(0)
            self._load_role_form()

    def _current_role(self):
        item = self.role_list.currentItem()
        if item is None:
            return None
        uid = item.data(Qt.ItemDataRole.UserRole)
        for e in self._metas[self._current_meta_index()].get("role_entries", []):
            if id(e) == uid:
                return e
        return None

    def _current_meta_index(self):
        m = self._current_meta()
        if m is None:
            return -1
        try:
            return self._metas.index(m)
        except ValueError:
            return -1

    def _on_select(self, current, _prev):
        self._load_meta()

    def _role_summary_key(self, e):
        return role_summary(e)

    def _refresh_role_item(self):
        e = self._current_role()
        item = self.role_list.currentItem()
        if e is not None and item is not None:
            item.setText(role_summary(e))

    # ---------------- 职责表单 ----------------
    def _load_role_form(self, entry=None):
        e = entry if entry is not None else self._current_role()
        self.role_type_combo.blockSignals(True)
        if e is not None and e["role_type"] in ROLE_TYPES:
            self.role_type_combo.setCurrentText(e["role_type"])
        self.role_type_combo.blockSignals(False)
        self._rebuild_field_form(e["role_type"] if e else "country_leader")
        self.role_traits_edit.blockSignals(True)
        self.role_desc_key_edit.blockSignals(True)
        self.role_desc_cn_edit.blockSignals(True)
        if e is not None:
            for f, edit in self.role_fields.items():
                edit.setText(role_get_field(e, f))
            self.role_traits_edit.setText(" ".join(e.get("traits", [])))
            dkey = role_get_field(e, "desc")
            self.role_desc_key_edit.setText(dkey)
            self.role_desc_cn_edit.setText(self._loc.get(dkey, "") if dkey else "")
        else:
            for edit in self.role_fields.values():
                edit.setText("")
            self.role_traits_edit.setText("")
            self.role_desc_key_edit.setText("")
            self.role_desc_cn_edit.setText("")
        self.role_traits_edit.blockSignals(False)
        self.role_desc_key_edit.blockSignals(False)
        self.role_desc_cn_edit.blockSignals(False)

    def _on_role_select(self, current, _prev):
        self._load_role_form()

    def _on_role_type_changed(self, text):
        e = self._current_role()
        if e is None or not text:
            return
        if text in ROLE_TYPES:
            e["role_type"] = text
            self._rebuild_field_form(text)
            self._load_role_form(e)
            self._refresh_role_item()

    def _on_field_changed(self, _text):
        e = self._current_role()
        if e is None:
            return
        sender = self.sender()
        f = sender.property("char_field") if sender is not None else None
        if f is not None and f in self.role_fields:
            role_set_field(e, f, self.role_fields[f].text().strip(), quoted=False)
            self._refresh_role_item()
        elif sender is self.role_desc_key_edit:
            role_set_field(e, "desc", self.role_desc_key_edit.text().strip(), quoted=False)
            self._refresh_role_item()

    def _on_traits_changed(self, text):
        e = self._current_role()
        if e is None:
            return
        toks = [t for t in text.replace(",", " ").split() if t]
        e["traits"] = toks
        self._refresh_role_item()

    def _add_role(self):
        m = self._current_meta()
        if m is None:
            QMessageBox.information(self, "提示", "请先选择角色")
            return
        from character_data import parse_role_entry
        entry = parse_role_entry("country_leader = {\n}")
        m.setdefault("role_entries", []).append(entry)
        self._fill_roles(m["role_entries"])
        self.role_list.setCurrentRow(self.role_list.count() - 1)

    def _del_role(self):
        m = self._current_meta()
        e = self._current_role()
        if m is None or e is None:
            return
        if QMessageBox.question(self, "确认", "删除职责 {}？".format(e["role_type"])) != QMessageBox.StandardButton.Yes:
            return
        m["role_entries"] = [x for x in m["role_entries"] if x is not e]
        self._fill_roles(m["role_entries"])

    # ---------------- 新建/复制/删除角色 ----------------
    def _add_char(self):
        from PyQt6.QtWidgets import QInputDialog
        cid, ok = QInputDialog.getText(self, "新建角色", "角色 ID（建议带国家前缀）")
        if not ok or not cid.strip():
            return
        self._metas.append({"id": cid.strip(), "name_loc": cid.strip(),
                            "portraits_slots": [], "role_entries": [],
                            "others_lines": [], "others_blocks": [],
                            "unknown_blocks": [],
                            "portraits_inner": "", "roles": [], "others": [], "raw": ""})
        self._reload()

    def _dup_char(self):
        m = self._current_meta()
        if not m:
            QMessageBox.information(self, "提示", "请先选择角色")
            return
        from PyQt6.QtWidgets import QInputDialog
        new_id, ok = QInputDialog.getText(self, "复制角色", "新 ID", text=m["id"] + "_copy")
        if not ok or not new_id.strip():
            return
        import copy
        meta = copy.deepcopy(m)
        meta["id"] = new_id.strip()
        self._metas.append(meta)
        self._reload()

    def _delete_char(self):
        m = self._current_meta()
        if not m:
            QMessageBox.information(self, "提示", "请先选择角色")
            return
        if QMessageBox.question(self, "确认", "删除角色 {}？".format(m["id"])) != QMessageBox.StandardButton.Yes:
            return
        self._metas = [x for x in self._metas if x["id"] != m["id"]]
        self._reload()

    # ---------------- 保存 ----------------
    def _apply_current_edits(self):
        m = self._current_meta()
        if m is None:
            return
        # 基本信息
        m["name_loc"] = self.name_loc_edit.text().strip() or m["id"]
        # 肖像表 → slots
        m["portraits_slots"] = self._portrait_slots_from_table()
        # 职责表单已实时写回 role_entries；traits/desc 由 _on_*_changed 同步

    def _save(self):
        self._apply_current_edits()
        if not self._metas:
            QMessageBox.information(self, "提示", "没有角色可保存")
            return
        # 本地化：名称 / 角色描述 / 各职责 desc
        for m in self._metas:
            nkey = m["name_loc"]
            cn = self.cn_edit.text().strip() if m is self._current_meta() else \
                self._loc.get(nkey, "")
            if nkey and cn:
                target = find_mod_file_for_key(self.mod_path, nkey, "simp_chinese") \
                    or default_mod_loc_file(self.mod_path, "simp_chinese")
                upsert_loc_entry(target, nkey, cn, "simp_chinese")
            dkey = self._desc_keys.get(m["id"])
            dcn = self.desc_cn_edit.text().strip() if m is self._current_meta() else \
                self._loc.get(dkey or "", "")
            if dkey and dcn:
                target = find_mod_file_for_key(self.mod_path, dkey, "simp_chinese") \
                    or default_mod_loc_file(self.mod_path, "simp_chinese")
                upsert_loc_entry(target, dkey, dcn, "simp_chinese")
            for e in m.get("role_entries", []):
                rkey = role_get_field(e, "desc")
                rcn = self.role_desc_cn_edit.text().strip() if (
                    m is self._current_meta() and e is self._current_role()) else \
                    (self._loc.get(rkey, "") if rkey else "")
                if rkey and rcn:
                    target = find_mod_file_for_key(self.mod_path, rkey, "simp_chinese") \
                        or default_mod_loc_file(self.mod_path, "simp_chinese")
                    upsert_loc_entry(target, rkey, rcn, "simp_chinese")
        try:
            n = save_file_v2(self._current_file, self._header, self._metas, self._tail)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", str(e))
            return
        QMessageBox.information(self, "已保存",
                                "已保存 {} 个角色 → {}".format(n, os.path.basename(self._current_file)))
        self._reload()


def open_character_editor(mod_path="", hoi4_path="", file_path="",
                          entity_id="", parent=None):
    dlg = CharacterEditorDialog(mod_path=mod_path, hoi4_path=hoi4_path,
                                parent=parent)
    dlg.show()
    if file_path:
        norm = os.path.normpath(file_path)
        for i in range(dlg.file_combo.count()):
            if os.path.normpath(dlg.file_combo.itemData(i)) == norm:
                dlg.file_combo.setCurrentIndex(i)
                break
    if entity_id:
        for i in range(dlg.list.count()):
            if dlg.list.item(i).data(Qt.ItemDataRole.UserRole) == entity_id:
                dlg.list.setCurrentRow(i)
                break
    return dlg
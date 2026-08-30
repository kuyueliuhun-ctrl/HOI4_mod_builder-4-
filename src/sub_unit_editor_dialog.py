# -*- coding: utf-8 -*-
"""兵种（sub_unit）编辑器对话框。

补齐批次 7 规格：
  - id / 名称双行（本地化）/ 描述双行
  - group 下拉 / parent / sprite
  - need 键值表
  - terrain 键值表（三列展开 movement / attack / defence，避免手输逗号）
  - 22 属性字段表
  - OtherFieldsTable（未覆盖标量字段，读写完整保留）
  - 保存走 oob_loader.save_sub_unit（块级写回 + 原子写）
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QComboBox,
)

from ai_ui_common import EntityListSidebar, KeyValueTableEditor, file_tooltip
from localization_mgr import get_localization_manager
from oob_loader import (
    TERRAIN_KEYS, _STAT_FIELDS, load_sub_units, save_sub_unit,
)


# 下拉可选项：group 大类常见值 + 已扫描到的大类；parent 用已有兵种 id
_GROUP_CHOICES = ("infantry", "mobile", "armor", "support",
                  "combat_support", "mobile_combat_support",
                  "armor_combat_support")


class LocEdit(QWidget):
    """本地化双行编辑：键 + 中文内容。"""

    def __init__(self, key="", cn="", key_placeholder="本地化键", parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(2)
        self.key_edit = QLineEdit(key)
        self.key_edit.setPlaceholderText(key_placeholder)
        self.key_edit.setReadOnly(True)
        self.cn_edit = QLineEdit(cn)
        self.cn_edit.setPlaceholderText("中文内容（保存时写入 mod 本地化 yml）")
        root.addWidget(self.key_edit)
        root.addWidget(self.cn_edit)


class OtherFieldsTable(QWidget):
    """未知标量字段表（表单未覆盖的键值统一在此编辑）。"""

    def __init__(self, rows=(), parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)
        tip = QLabel("文件中存在而表单未覆盖的标量键在此统一编辑（读写完整保留）")
        tip.setStyleSheet("color:#5d6b7a; font-size:11px;")
        tip.setWordWrap(True)
        root.addWidget(tip)
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
        add_btn.clicked.connect(lambda: self.add_row("", ""))
        del_btn = QPushButton("－ 删除选中")
        del_btn.clicked.connect(self._remove_selected)
        btns.addWidget(add_btn)
        btns.addWidget(del_btn)
        btns.addStretch(1)
        root.addLayout(btns)
        for k, v in rows:
            self.add_row(k, v)

    def add_row(self, k, v):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(str(k)))
        self.table.setItem(r, 1, QTableWidgetItem(str(v)))

    def _remove_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()},
                      reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def data(self):
        out = {}
        for r in range(self.table.rowCount()):
            k_item = self.table.item(r, 0)
            v_item = self.table.item(r, 1)
            k = k_item.text().strip() if k_item else ""
            v = v_item.text().strip() if v_item else ""
            if k:
                out[k] = v
        return out


class TerrainTable(QWidget):
    """地形三列展开表（movement / attack / defence）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)
        tip = QLabel("地形修正三列展开（movement / attack / defence），避免手输逗号")
        tip.setStyleSheet("color:#5d6b7a; font-size:11px;")
        tip.setWordWrap(True)
        root.addWidget(tip)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["地形", "移动", "攻击", "防御"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        for c in (1, 2, 3):
            self.table.horizontalHeader().setSectionResizeMode(
                c, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        btns = QHBoxLayout()
        add_btn = QPushButton("＋ 添加地形")
        add_btn.clicked.connect(lambda: self.add_row("", "", "", ""))
        del_btn = QPushButton("－ 删除选中")
        del_btn.clicked.connect(self._remove_selected)
        btns.addWidget(add_btn)
        btns.addWidget(del_btn)
        btns.addStretch(1)
        root.addLayout(btns)

    def add_row(self, terrain="", movement="", attack="", defence=""):
        r = self.table.rowCount()
        self.table.insertRow(r)
        for c, v in enumerate((terrain, movement, attack, defence)):
            self.table.setItem(r, c, QTableWidgetItem(str(v) if v is not None else ""))

    def set_terrain(self, terrain_full):
        self.table.setRowCount(0)
        keys = list(TERRAIN_KEYS)
        for k in terrain_full:
            if k not in keys:
                keys.append(k)
        for k in keys:
            item = terrain_full.get(k) or {}
            self.add_row(k,
                         item.get("movement") if item.get("movement") is not None else "",
                         item.get("attack") if item.get("attack") is not None else "",
                         item.get("defence") if item.get("defence") is not None else "")

    def _remove_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()},
                      reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def data(self):
        out = {}
        for r in range(self.table.rowCount()):
            k_item = self.table.item(r, 0)
            if k_item is None:
                continue
            k = k_item.text().strip()
            if not k:
                continue
            row = {}
            for c, key in ((1, "movement"), (2, "attack"), (3, "defence")):
                it = self.table.item(r, c)
                val = it.text().strip() if it else ""
                row[key] = val if val else None
            out[k] = row
        return out


class SubUnitEditorDialog(QDialog):
    """兵种专用编辑器（非模态）。"""

    def __init__(self, mod_path="", hoi4_path="", parent=None):
        super().__init__(parent)
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.units = {}
        self.current_id = ""

        self.setWindowTitle("兵种编辑器")
        self.resize(1180, 820)
        root = QHBoxLayout(self)

        self.sidebar = EntityListSidebar(
            "兵种", parent=self, enable_crud=False,
            mod_path=self.mod_path, hoi4_path=self.hoi4_path)
        self.sidebar.currentChanged.connect(self._on_select)
        root.addWidget(self.sidebar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setSpacing(8)
        self._build_basic_form(body_layout)
        self._build_need_form(body_layout)
        self._build_terrain_form(body_layout)
        self._build_stats_form(body_layout)
        self._build_other_form(body_layout)
        body_layout.addStretch(1)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        # 底部按钮
        btn_row = QHBoxLayout()
        save_btn = QPushButton("💾 保存（原子写 · 可撤销）")
        save_btn.setStyleSheet("font-weight:bold;")
        save_btn.clicked.connect(self._save)
        reset_btn = QPushButton("⟲ 重置")
        reset_btn.clicked.connect(self._reload)
        btn_row.addStretch(1)
        btn_row.addWidget(reset_btn)
        btn_row.addWidget(save_btn)
        body_layout.addLayout(btn_row)

        self._ensure_loc()
        self._reload()

    # ---------- UI ----------

    def _ensure_loc(self):
        try:
            get_localization_manager().reload(
                self.hoi4_path, self.mod_path)
        except Exception:
            pass

    def _build_basic_form(self, host):
        box = QWidget()
        box.setStyleSheet("background:#f6f8fa;border-radius:8px;")
        root = QVBoxLayout(box)
        root.setContentsMargins(10, 8, 10, 8)
        form = QFormLayout()
        self.id_edit = QLineEdit()
        self.id_edit.setReadOnly(True)
        form.addRow("兵种 id:", self.id_edit)
        self.name_edit = LocEdit()
        form.addRow("名称:", self.name_edit)
        self.desc_edit = LocEdit()
        form.addRow("描述:", self.desc_edit)
        self.group_combo = QComboBox()
        self.group_combo.setEditable(True)
        for g in _GROUP_CHOICES:
            self.group_combo.addItem(g)
        form.addRow("group（编制栏位组）:", self.group_combo)
        self.parent_combo = QComboBox()
        self.parent_combo.setEditable(True)
        self.parent_combo.addItem("")
        form.addRow("parent（变种）:", self.parent_combo)
        self.sprite_edit = QLineEdit()
        form.addRow("sprite（地图兵牌 GFX）:", self.sprite_edit)
        root.addLayout(form)
        host.addWidget(box)

    def _build_need_form(self, host):
        self.need_table = KeyValueTableEditor("装备键", "数量")
        host.addWidget(self.need_table)

    def _build_terrain_form(self, host):
        self.terrain_table = TerrainTable()
        host.addWidget(self.terrain_table)

    def _build_stats_form(self, host):
        self.stats_table = QTableWidget(len(_STAT_FIELDS), 2)
        self.stats_table.setHorizontalHeaderLabels(["属性字段", "值"])
        self.stats_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.stats_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self.stats_table.verticalHeader().setVisible(False)
        for i, key in enumerate(_STAT_FIELDS):
            self.stats_table.setItem(i, 0, QTableWidgetItem(key))
            self.stats_table.setItem(i, 1, QTableWidgetItem(""))
        host.addWidget(self.stats_table)

    def _build_other_form(self, host):
        self.other_table = OtherFieldsTable()
        host.addWidget(self.other_table)

    # ---------- 数据 ----------

    def _reload(self):
        self.units = load_sub_units(self.mod_path, self.hoi4_path)
        loc = get_localization_manager()
        labels = []
        for uid in sorted(self.units):
            cn = loc.get_name(uid) or ""
            labels.append((uid, cn if cn and cn != uid else uid,
                           file_tooltip(self.units.get(uid), getattr(self, "mod_path", ""), getattr(self, "hoi4_path", ""))
                           or uid))
        self.sidebar.set_entities(labels, keep_selection=True)

    def _on_select(self, unit_id):
        self.current_id = unit_id or ""
        u = self.units.get(unit_id)
        if u is None:
            return
        loc = get_localization_manager()
        self.id_edit.setText(unit_id)
        self.name_edit.key_edit.setText(unit_id)
        self.name_edit.cn_edit.setText(loc.get_name(unit_id) or "")
        self.desc_edit.key_edit.setText(unit_id + "_desc")
        self.desc_edit.cn_edit.setText(loc.get_name(unit_id + "_desc") or "")

        # group
        group = u.get("group") or ""
        if self.group_combo.findText(group) < 0:
            self.group_combo.addItem(group)
        self.group_combo.setCurrentText(group)

        # parent
        parent = u.get("parent") or ""
        # 重建 parent 候选（已有兵种 id + 当前 parent）
        self.parent_combo.blockSignals(True)
        self.parent_combo.clear()
        self.parent_combo.addItem("")
        for pid in sorted(self.units):
            if pid != unit_id:
                self.parent_combo.addItem(pid)
        if parent and self.parent_combo.findText(parent) < 0:
            self.parent_combo.addItem(parent)
        self.parent_combo.setCurrentText(parent)
        self.parent_combo.blockSignals(False)

        self.sprite_edit.setText(u.get("sprite") or "")
        self.need_table.set_data(u.get("need") or {})
        self.terrain_table.set_terrain(u.get("terrain_full") or {})
        for i, key in enumerate(_STAT_FIELDS):
            val = u.get(key)
            self.stats_table.setItem(i, 1, QTableWidgetItem(
                "" if val is None else ("%g" % val)))
        self.other_table.table.setRowCount(0)
        for k, v in sorted((u.get("others") or {}).items()):
            self.other_table.add_row(k, v)

    # ---------- 选择 ----------

    def select_unit(self, unit_id):
        """外部入口：切换到指定兵种（若存在）。"""
        if unit_id and unit_id in self.units:
            self.sidebar.set_current(unit_id)

    # ---------- 保存 ----------

    def _collect_stats(self):
        out = {}
        for r in range(self.stats_table.rowCount()):
            k_item = self.stats_table.item(r, 0)
            v_item = self.stats_table.item(r, 1)
            if k_item is None:
                continue
            k = k_item.text().strip()
            v = v_item.text().strip() if v_item else ""
            if k and v:
                out[k] = v
        return out

    def _save_loc(self, unit_id):
        if not self.mod_path:
            return
        try:
            from localisation_editor_data import (
                default_mod_loc_file, upsert_loc_entry)
            fp = default_mod_loc_file(self.mod_path)
            name_cn = self.name_edit.cn_edit.text().strip()
            desc_cn = self.desc_edit.cn_edit.text().strip()
            if name_cn:
                upsert_loc_entry(fp, unit_id, name_cn)
            if desc_cn:
                upsert_loc_entry(fp, unit_id + "_desc", desc_cn)
        except Exception:
            # 本地化写失败不阻断兵种块保存
            pass

    def _save(self):
        if not self.current_id:
            return
        unit_id = self.current_id
        fields = {
            "group": self.group_combo.currentText().strip(),
            "parent": self.parent_combo.currentText().strip(),
            "sprite": self.sprite_edit.text().strip(),
        }
        need = {}
        for k, v in self.need_table.data().items():
            try:
                need[k] = int(float(v))
            except (TypeError, ValueError):
                if v:
                    need[k] = v
        terrain = self.terrain_table.data()
        stats = self._collect_stats()
        others = self.other_table.data()
        try:
            fp = save_sub_unit(
                self.mod_path, self.hoi4_path, unit_id,
                fields=fields, need=need, terrain=terrain,
                stats=stats, others=others)
            self._save_loc(unit_id)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return
        if fp is None:
            QMessageBox.critical(self, "保存失败", "未定位到兵种定义。")
            return
        QMessageBox.information(self, "已保存", "已保存到:\n%s" % fp)
        self._reload()


def open_sub_unit_editor(mod_path="", hoi4_path="", parent=None):
    dlg = SubUnitEditorDialog(mod_path=mod_path, hoi4_path=hoi4_path,
                              parent=parent)
    dlg.show()
    return dlg
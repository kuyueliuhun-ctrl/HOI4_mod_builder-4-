"""AI 装备编辑器（调用现有设计器）

- 左侧：AI 装备设计组列表（GER_fighter / GER_tank 等）
- 中间：目标设计变体列表
- 「✏ 编辑设计」：根据 category 调用飞机/坦克/舰艇设计器
- 保存：把设计器修改后的 target_variant 写回 AI 装备文件
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QVBoxLayout,
)

from ai_loader import (
    load_ai_equipment, parse_ai_target_variant,
    replace_ai_equipment_target_variant,
)
from write_utils import atomic_write_text
from state_build_ops import ensure_file_in_mod


class _AiPlaneDesignDialog:
    """占位，实际在 open 时动态生成子类。"""


def _make_plane_subclass():
    from plane_design_dialog import PlaneDesignDialog
    class AiPlaneDesignDialog(PlaneDesignDialog):
        def __init__(self, variant, mod_path, hoi4_path, on_save, parent=None):
            super().__init__(mod_path=mod_path, hoi4_path=hoi4_path,
                             parent=parent)
            self._ai_on_save = on_save
            self._ai_name = variant.get("name", "AI_Design")
            self.variants = {"ZZZ": {
                self._ai_name: {
                    "type": variant.get("type", ""),
                    "modules": dict(variant.get("modules") or {}),
                }}}
            self._initial_country_tag = "ZZZ"
            self._refresh_countries()

        def _save(self):
            if self.current_variant is None:
                return
            self._ai_on_save(self.current_name,
                             self.current_variant.get("modules") or {})
            QMessageBox.information(self, "已保存", "AI 飞机设计已写回")
            self.accept()
    return AiPlaneDesignDialog


def _make_tank_subclass():
    from tank_design_dialog import TankDesignDialog
    class AiTankDesignDialog(TankDesignDialog):
        def __init__(self, variant, mod_path, hoi4_path, on_save, parent=None):
            super().__init__(mod_path=mod_path, hoi4_path=hoi4_path,
                             parent=parent)
            self._ai_on_save = on_save
            self._ai_name = variant.get("name", "AI_Design")
            self.variants = {"ZZZ": {
                self._ai_name: {
                    "type": variant.get("type", ""),
                    "modules": dict(variant.get("modules") or {}),
                }}}
            self._initial_country_tag = "ZZZ"
            self._refresh_countries()

        def _save(self):
            if self.current_variant is None:
                return
            self._ai_on_save(self.current_name,
                             self.current_variant.get("modules") or {})
            QMessageBox.information(self, "已保存", "AI 坦克设计已写回")
            self.accept()
    return AiTankDesignDialog


def _make_ship_subclass():
    from ship_design_dialog import ShipDesignDialog
    class AiShipDesignDialog(ShipDesignDialog):
        def __init__(self, variant, mod_path, hoi4_path, on_save, parent=None):
            super().__init__(mod_path=mod_path, hoi4_path=hoi4_path,
                             parent=parent)
            self._ai_on_save = on_save
            self._ai_name = variant.get("name", "AI_Design")
            self.variants = {"ZZZ": {
                self._ai_name: {
                    "type": variant.get("type", ""),
                    "modules": dict(variant.get("modules") or {}),
                }}}
            self._initial_country_tag = "ZZZ"
            self._refresh_countries()

        def _save(self):
            if self.current_variant is None:
                return
            self._ai_on_save(self.current_name,
                             self.current_variant.get("modules") or {})
            QMessageBox.information(self, "已保存", "AI 海军装备设计已写回")
            self.accept()
    return AiShipDesignDialog


class AiEquipmentEditorDialog(QDialog):
    """AI 装备选择器。"""

    def __init__(self, groups, mod_path="", hoi4_path="", parent=None,
                 initial_group_id=None):
        super().__init__(parent)
        self.groups = groups
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self._current_group = None
        self._current_variant = None
        self.setWindowTitle("AI 装备编辑器")
        self.resize(900, 560)
        self._build_ui()
        self._populate_groups(initial_group_id)

    def _build_ui(self):
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(QLabel("设计组"))
        self.group_list = QListWidget()
        self.group_list.currentItemChanged.connect(self._on_group_changed)
        left.addWidget(self.group_list, 1)
        root.addLayout(left, 1)

        mid = QVBoxLayout()
        mid.addWidget(QLabel("设计变体"))
        self.variant_list = QListWidget()
        self.variant_list.currentItemChanged.connect(self._on_variant_changed)
        mid.addWidget(self.variant_list, 1)
        root.addLayout(mid, 1)

        right = QVBoxLayout()
        self.info_label = QLabel("—")
        self.info_label.setWordWrap(True)
        right.addWidget(self.info_label)
        edit_btn = QPushButton("✏ 编辑设计（调用现有设计器）")
        edit_btn.clicked.connect(self._edit_variant)
        right.addWidget(edit_btn)
        tree_btn = QPushButton("✏ 编辑定义（树编辑器）")
        tree_btn.clicked.connect(self._edit_tree)
        right.addWidget(tree_btn)
        right.addStretch(1)
        root.addLayout(right, 2)

    def _populate_groups(self, initial_group_id=None):
        self.group_list.blockSignals(True)
        self.group_list.clear()
        for gid in sorted(self.groups):
            item = QListWidgetItem(gid)
            item.setData(Qt.ItemDataRole.UserRole, gid)
            self.group_list.addItem(item)
        self.group_list.blockSignals(False)
        if self.group_list.count() > 0:
            target = 0
            if initial_group_id:
                for i in range(self.group_list.count()):
                    if self.group_list.item(i).data(Qt.ItemDataRole.UserRole) == initial_group_id:
                        target = i
                        break
            self.group_list.setCurrentRow(target)
            self._on_group_changed(self.group_list.currentItem())

    def _on_group_changed(self, item):
        if item is None:
            return
        gid = item.data(Qt.ItemDataRole.UserRole)
        group = self.groups.get(gid)
        if not group:
            return
        self._current_group = group
        self.variant_list.blockSignals(True)
        self.variant_list.clear()
        for v in group.get("variants", []):
            it = QListWidgetItem(v.get("id", ""))
            it.setData(Qt.ItemDataRole.UserRole, v.get("id", ""))
            self.variant_list.addItem(it)
        self.variant_list.blockSignals(False)
        if self.variant_list.count() > 0:
            self.variant_list.setCurrentRow(0)
            self._on_variant_changed(self.variant_list.currentItem())

    def _on_variant_changed(self, item):
        if item is None or self._current_group is None:
            return
        vid = item.data(Qt.ItemDataRole.UserRole)
        self._current_variant = None
        for v in self._current_group.get("variants", []):
            if v.get("id") == vid:
                self._current_variant = v
                parsed = parse_ai_target_variant(v.get("target_variant", ""))
                self.info_label.setText(
                    "变体：%s\n类型：%s\n模块数：%d" % (
                        vid, parsed.get("type", "—"),
                        len(parsed.get("modules", {}))))
                return

    def _edit_variant(self):
        if not self._current_group or not self._current_variant:
            return
        group = self._current_group
        variant = self._current_variant
        parsed = parse_ai_target_variant(variant.get("target_variant", ""))
        category = group.get("category", "").lower()
        name = variant.get("id", "AI_Design")
        ai_variant = {
            "name": name,
            "type": parsed.get("type", ""),
            "modules": parsed.get("modules", {}),
        }

        def on_save(new_name, modules):
            self._write_variant(group, variant, new_name, modules)

        if category == "air":
            dlg_cls = _make_plane_subclass()
        elif category == "tank":
            dlg_cls = _make_tank_subclass()
        elif category == "naval" or category == "navy" or category == "ship":
            dlg_cls = _make_ship_subclass()
        else:
            QMessageBox.warning(self, "无法编辑", "未知装备类别：%s" % category)
            return
        dlg = dlg_cls(ai_variant, self.mod_path, self.hoi4_path,
                      on_save, parent=self)
        dlg.exec()

    def _write_variant(self, group, variant, new_name, modules):
        rel = group.get("rel", "")
        if not rel:
            return
        mod_fp, copied = ensure_file_in_mod(self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位 AI 装备文件")
            return
        try:
            with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "读取文件失败：%s" % e)
            return
        parsed = parse_ai_target_variant(variant.get("target_variant", ""))
        content = replace_ai_equipment_target_variant(
            content, group["id"], variant["id"],
            parsed.get("type", ""), modules)
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        # 更新内存
        from ai_loader import _AI_CACHE
        _AI_CACHE.pop(("ai_equipment", self.mod_path or "", self.hoi4_path or ""), None)
        variant["target_variant"] = (
            "target_variant = {\n\ttype = %s\n\tmodules = {\n%s\n\t}\n}" % (
                parsed.get("type", ""),
                "\n".join("\t\t%s = %s" % (k, v) for k, v in modules.items())))

    def _edit_tree(self):
        if not self._current_group:
            return
        fp = self._current_group.get("file", "")
        if not fp:
            return
        mod_fp, copied = self._ensure_writable(fp)
        if not mod_fp:
            QMessageBox.warning(self, "无法编辑", "请先打开 mod 目录")
            return
        from tree_node import tree_from_pdx_text
        from generic_tree_editor import GenericTreeEditor
        from gui_translator import get_translator
        from focus_view import CUSTOM_STATEMENT_PATH
        try:
            with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "无法编辑", "读取文件失败：%s" % e)
            return
        root = tree_from_pdx_text(content)
        editor = GenericTreeEditor(
            root_node=root,
            file_path=mod_fp,
            file_lines=content.splitlines(),
            block_range=(1, len(content.splitlines()) + 1),
            translator=get_translator(),
            custom_statement_path=CUSTOM_STATEMENT_PATH,
            loc_manager=None,
            parent=self,
            title="AI 装备 - %s" % self._current_group["id"],
            hoi4_path=self.hoi4_path,
            mod_path=self.mod_path,
        )
        editor.show()
        try:
            model = getattr(editor, "model", None)
            if model is not None:
                results = model.find_nodes(self._current_group["id"])
                if results:
                    editor.tree_view.setCurrentIndex(results[0])
                    editor.tree_view.scrollTo(results[0])
        except Exception:
            pass

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


def open_ai_equipment_editor(file_path, mod_path="", hoi4_path="",
                             entity_id=None, parent=None):
    """按文件/实体打开 AI 装备编辑器。"""
    groups = load_ai_equipment(mod_path, hoi4_path)
    norm = os.path.normpath(file_path).replace("\\", "/")
    file_groups = {}
    for gid, g in groups.items():
        if os.path.normpath(g.get("file", "")).replace("\\", "/") == norm:
            file_groups[gid] = g
    if not file_groups:
        return False
    dlg = AiEquipmentEditorDialog(
        file_groups, mod_path, hoi4_path, parent,
        initial_group_id=entity_id if entity_id in file_groups else None)
    dlg.exec()
    return True

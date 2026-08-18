"""AI 装备专用编辑器（完全专用 UI，不依赖树形编辑器页面）

- 左侧固定侧边栏：设计组列表 + CRUD
- 中间：设计变体列表 + CRUD
- 右侧：变体详情（category / priority / history / target_variant 用设计器 /
  allowed_modules / 高级块）
- 保存：原版自动复制到 mod + 原子写
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout,
)

from ai_loader import (
    _AI_CACHE,
    delete_ai_equipment_group,
    delete_ai_equipment_variant,
    duplicate_ai_equipment_group,
    duplicate_ai_equipment_variant,
    insert_ai_equipment_group,
    insert_ai_equipment_variant,
    load_ai_equipment,
    parse_ai_target_variant,
    rename_ai_equipment_group,
    rename_ai_equipment_variant,
    replace_ai_equipment_allowed_modules,
    replace_ai_equipment_target_variant,
    replace_ai_equipment_variant_field,
    replace_or_upsert_nested_child,
    replace_top_block_field,
    upsert_top_block_child,
)
from ai_ui_common import EntityListSidebar, ScriptBlockEditorDialog
from state_build_ops import ensure_file_in_mod
from write_utils import atomic_write_text

VARIANT_ADVANCED = ("priority",)


class _AiPlaneDesignDialog:

    def _make(self):
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


class _AiTankDesignDialog:

    def _make(self):
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


class _AiShipDesignDialog:

    def _make(self):
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
                QMessageBox.information(self, "已保存", "AI 舰艇设计已写回")
                self.accept()
        return AiShipDesignDialog


class AiEquipmentEditorDialog(QDialog):
    """AI 装备专用编辑器。"""

    def __init__(self, groups, mod_path="", hoi4_path="", parent=None,
                 initial_group_id=None):
        super().__init__(parent)
        self.groups = groups
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self._current_group = None
        self._current_variant = None
        self._variant_advanced = {}
        self.setWindowTitle("AI 装备编辑器")
        self.resize(1240, 740)
        self.setMinimumSize(1120, 660)
        self._build_ui()
        self._populate_groups(initial_group_id)

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # 左：设计组
        self.sidebar = EntityListSidebar("设计组", self)
        self.sidebar.currentChanged.connect(self._on_group_changed)
        self.sidebar.createRequested.connect(self._create_group)
        self.sidebar.duplicateRequested.connect(self._duplicate_group)
        self.sidebar.renameRequested.connect(self._rename_group)
        self.sidebar.deleteRequested.connect(self._delete_group)
        root.addWidget(self.sidebar)
        self.group_list = self.sidebar.list

        # 中：变体
        middle = QVBoxLayout()
        middle.addWidget(QLabel("设计变体"))
        self.variant_list = QListWidget()
        self.variant_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.variant_list.currentItemChanged.connect(self._on_variant_changed)
        middle.addWidget(self.variant_list, 1)
        vbtns = QHBoxLayout()
        add_v = QPushButton("＋")
        dup_v = QPushButton("⧉")
        ren_v = QPushButton("✎")
        del_v = QPushButton("🗑")
        add_v.setToolTip("新建变体")
        dup_v.setToolTip("复制变体")
        ren_v.setToolTip("重命名变体")
        del_v.setToolTip("删除变体")
        add_v.clicked.connect(self._create_variant)
        dup_v.clicked.connect(self._duplicate_variant)
        ren_v.clicked.connect(self._rename_variant)
        del_v.clicked.connect(self._delete_variant)
        for b in (add_v, dup_v, ren_v, del_v):
            vbtns.addWidget(b)
        vbtns.addStretch(1)
        middle.addLayout(vbtns)
        root.addLayout(middle, 2)

        # 右：详情
        right = QVBoxLayout()
        self.group_label = QLabel("—")
        self.group_label.setStyleSheet("font-weight:bold; font-size:14px;")
        right.addWidget(self.group_label)
        self.variant_label = QLabel("—")
        right.addWidget(self.variant_label)

        gform = QHBoxLayout()
        gform.addWidget(QLabel("category"))
        self.category_edit = QLineEdit()
        self.category_edit.setMaximumWidth(120)
        gform.addWidget(self.category_edit)
        gform.addWidget(QLabel("history"))
        self.history_edit = QLineEdit()
        gform.addWidget(self.history_edit, 1)
        right.addLayout(gform)

        design_btn = QPushButton("✏ 编辑设计（调用现有设计器）")
        design_btn.clicked.connect(self._edit_variant)
        right.addWidget(design_btn)

        right.addWidget(QLabel("allowed_modules"))
        self.modules_list = QListWidget()
        self.modules_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right.addWidget(self.modules_list, 1)
        mbtns = QHBoxLayout()
        add_m = QPushButton("＋ 添加模块")
        del_m = QPushButton("🗑 删除模块")
        add_m.clicked.connect(self._add_module)
        del_m.clicked.connect(self._del_module)
        mbtns.addWidget(add_m)
        mbtns.addWidget(del_m)
        mbtns.addStretch(1)
        right.addLayout(mbtns)

        adv_label = QLabel("高级脚本块（priority 等）")
        adv_label.setStyleSheet("font-weight:bold; color:#1f4f7e;")
        right.addWidget(adv_label)
        self.adv_buttons = {}
        for field in VARIANT_ADVANCED:
            row = QHBoxLayout()
            row.addWidget(QLabel(field))
            btn = QPushButton("未编辑")
            btn.clicked.connect(
                lambda checked=False, f=field: self._edit_advanced(f))
            row.addWidget(btn, 1)
            self.adv_buttons[field] = btn
            right.addLayout(row)

        footer = QHBoxLayout()
        raw_btn = QPushButton("📝 原始变体块")
        raw_btn.clicked.connect(self._edit_raw_variant)
        footer.addWidget(raw_btn)
        footer.addStretch(1)
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save)
        footer.addWidget(save_btn)
        right.addLayout(footer)
        root.addLayout(right, 3)

    # ---------- 填充 ----------
    def _populate_groups(self, initial_group_id=None):
        items = [(gid, gid) for gid in sorted(self.groups)]
        self.sidebar.set_entities(items)
        if initial_group_id:
            self.sidebar.set_current(initial_group_id)
        elif self.sidebar.current_id() is None and self.sidebar.list.count():
            self.sidebar.set_current(self.sidebar.list.item(0).data(
                Qt.ItemDataRole.UserRole))

    def _on_group_changed(self, group_id):
        if group_id is None:
            self._current_group = None
            self.group_label.setText("—")
            self.variant_list.clear()
            return
        group = self.groups.get(group_id)
        if not group:
            return
        self._current_group = group
        self.group_label.setText("%s  （%s）" % (group_id, group.get("file", "")))
        self.category_edit.setText(group.get("category", ""))
        self.variant_list.blockSignals(True)
        self.variant_list.clear()
        for v in group.get("variants", []):
            item = QListWidgetItem(v.get("id", ""))
            item.setData(Qt.ItemDataRole.UserRole, v.get("id", ""))
            self.variant_list.addItem(item)
        self.variant_list.blockSignals(False)
        if self.variant_list.count() > 0:
            self.variant_list.setCurrentRow(0)
            self._on_variant_changed(self.variant_list.currentItem())
        else:
            self._current_variant = None

    def _on_variant_changed(self, item):
        if item is None or self._current_group is None:
            self._current_variant = None
            self.variant_label.setText("—")
            return
        vid = item.data(Qt.ItemDataRole.UserRole)
        self._current_variant = vid
        variant = self._find_variant(vid)
        if not variant:
            self.variant_label.setText(vid)
            return
        parsed = parse_ai_target_variant(variant.get("target_variant", ""))
        self.variant_label.setText(
            "变体：%s　类型：%s　模块数：%d" % (
                vid, parsed.get("type", "—"), len(parsed.get("modules", {}))))
        self.history_edit.setText(variant.get("history", ""))
        self.modules_list.blockSignals(True)
        self.modules_list.clear()
        for m in (variant.get("allowed_modules") or "").splitlines():
            m = m.strip()
            if m and not m.startswith("{"):
                self.modules_list.addItem(m)
        self.modules_list.blockSignals(False)
        self._variant_advanced = {
            f: variant.get(f, "") or "" for f in VARIANT_ADVANCED}
        self._update_advanced_summaries()

    def _find_variant(self, vid):
        if not self._current_group:
            return None
        for v in self._current_group.get("variants", []):
            if v.get("id") == vid:
                return v
        return None

    # ---------- 变体 CRUD ----------
    def _reload_groups(self, keep_group=None, keep_variant=None):
        _AI_CACHE.pop(("ai_equipment", self.mod_path or "",
                       self.hoi4_path or ""), None)
        self.groups = load_ai_equipment(self.mod_path, self.hoi4_path)
        if self._current_group:
            norm = os.path.normpath(
                self._current_group.get("file", "")).replace("\\", "/")
            self.groups = {gid: g for gid, g in self.groups.items()
                           if os.path.normpath(g.get("file", "")).replace("\\", "/") == norm}
        self._populate_groups(keep_group)
        if keep_group and keep_variant:
            self.sidebar.set_current(keep_group)
            self._select_variant(keep_variant)

    def _select_variant(self, vid):
        for i in range(self.variant_list.count()):
            if self.variant_list.item(i).data(Qt.ItemDataRole.UserRole) == vid:
                self.variant_list.setCurrentRow(i)
                return True
        return False

    def _create_variant(self):
        if not self._current_group:
            return
        new_id, ok = QInputDialog.getText(self, "新建变体", "变体 ID：")
        if not ok or not new_id.strip():
            return
        if any(v.get("id") == new_id.strip()
               for v in self._current_group.get("variants", [])):
            QMessageBox.warning(self, "错误", "变体已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_group.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = insert_ai_equipment_variant(
            content, self._current_group["id"], new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload_groups(self._current_group["id"], new_id.strip())

    def _duplicate_variant(self):
        if not self._current_variant:
            return
        old_id = self._current_variant
        new_id, ok = QInputDialog.getText(
            self, "复制变体", "新变体 ID：", text=old_id + "_copy")
        if not ok or not new_id.strip():
            return
        if any(v.get("id") == new_id.strip()
               for v in self._current_group.get("variants", [])):
            QMessageBox.warning(self, "错误", "变体已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_group.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = duplicate_ai_equipment_variant(
            content, self._current_group["id"], old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload_groups(self._current_group["id"], new_id.strip())

    def _rename_variant(self):
        if not self._current_variant:
            return
        old_id = self._current_variant
        new_id, ok = QInputDialog.getText(
            self, "重命名变体", "新变体 ID：", text=old_id)
        if not ok or not new_id.strip() or new_id.strip() == old_id:
            return
        if any(v.get("id") == new_id.strip()
               for v in self._current_group.get("variants", [])):
            QMessageBox.warning(self, "错误", "变体已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_group.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = rename_ai_equipment_variant(
            content, self._current_group["id"], old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload_groups(self._current_group["id"], new_id.strip())

    def _delete_variant(self):
        if not self._current_variant:
            return
        reply = QMessageBox.question(
            self, "确认", "确定要删除变体 '%s' 吗？" % self._current_variant)
        if reply != QMessageBox.StandardButton.Yes:
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_group.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = delete_ai_equipment_variant(
            content, self._current_group["id"], self._current_variant)
        atomic_write_text(mod_fp, content)
        self._reload_groups(self._current_group["id"])

    # ---------- 组 CRUD ----------
    def _create_group(self):
        if not self._current_group:
            return
        new_id, ok = QInputDialog.getText(self, "新建设计组", "设计组 ID：")
        if not ok or not new_id.strip():
            return
        if new_id.strip() in self.groups:
            QMessageBox.warning(self, "错误", "设计组已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_group.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = insert_ai_equipment_group(content, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload_groups(new_id.strip())

    def _duplicate_group(self):
        if not self._current_group:
            return
        old_id = self._current_group["id"]
        new_id, ok = QInputDialog.getText(
            self, "复制设计组", "新设计组 ID：", text=old_id + "_copy")
        if not ok or not new_id.strip():
            return
        if new_id.strip() in self.groups:
            QMessageBox.warning(self, "错误", "设计组已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_group.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = duplicate_ai_equipment_group(
            content, old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload_groups(new_id.strip())

    def _rename_group(self):
        if not self._current_group:
            return
        old_id = self._current_group["id"]
        new_id, ok = QInputDialog.getText(
            self, "重命名设计组", "新设计组 ID：", text=old_id)
        if not ok or not new_id.strip() or new_id.strip() == old_id:
            return
        if new_id.strip() in self.groups:
            QMessageBox.warning(self, "错误", "设计组已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_group.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = rename_ai_equipment_group(content, old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload_groups(new_id.strip())

    def _delete_group(self):
        if not self._current_group:
            return
        reply = QMessageBox.question(
            self, "确认", "确定要删除设计组 '%s' 吗？" % self._current_group["id"])
        if reply != QMessageBox.StandardButton.Yes:
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current_group.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = delete_ai_equipment_group(content, self._current_group["id"])
        atomic_write_text(mod_fp, content)
        self._reload_groups()

    # ---------- 详情编辑 ----------
    def _modules(self):
        return [self.modules_list.item(i).text().strip()
                for i in range(self.modules_list.count())
                if self.modules_list.item(i).text().strip()]

    def _add_module(self):
        text, ok = QInputDialog.getText(self, "添加模块", "模块名：")
        if ok and text.strip():
            self.modules_list.addItem(text.strip())

    def _del_module(self):
        rows = sorted({i.row() for i in self.modules_list.selectedIndexes()}, reverse=True)
        for r in rows:
            self.modules_list.takeItem(r)

    def _update_advanced_summaries(self):
        for field in VARIANT_ADVANCED:
            text = (self._variant_advanced.get(field) or "").strip()
            self.adv_buttons[field].setText(
                "空" if not text else "已编辑（%d 行）" % len(text.splitlines()))

    def _edit_advanced(self, field):
        from gui_translator import get_translator
        from focus_view import CUSTOM_STATEMENT_PATH
        dlg = ScriptBlockEditorDialog(
            block_text=self._variant_advanced.get(field, ""),
            block_key=field,
            translator=get_translator(),
            custom_statement_path=CUSTOM_STATEMENT_PATH,
            parent=self,
            title="编辑 %s" % field,
        )
        if dlg.exec():
            self._variant_advanced[field] = dlg.get_block_text()
            self._update_advanced_summaries()

    def _edit_raw_variant(self):
        variant = self._find_variant(self._current_variant) if self._current_variant else None
        if not variant:
            return
        from gui_translator import get_translator
        from focus_view import CUSTOM_STATEMENT_PATH
        dlg = ScriptBlockEditorDialog(
            block_text=variant.get("raw", ""),
            block_key=self._current_variant,
            translator=get_translator(),
            custom_statement_path=CUSTOM_STATEMENT_PATH,
            parent=self,
            title="AI 装备变体 - %s" % self._current_variant,
        )
        if dlg.exec():
            variant["raw"] = dlg.get_block_text()

    def _edit_variant(self):
        if not self._current_group or not self._current_variant:
            return
        group = self._current_group
        variant = self._find_variant(self._current_variant)
        if not variant:
            return
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
            dlg_cls = _AiPlaneDesignDialog()._make()
        elif category == "tank":
            dlg_cls = _AiTankDesignDialog()._make()
        elif category in ("naval", "navy", "ship"):
            dlg_cls = _AiShipDesignDialog()._make()
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
        mod_fp, copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        parsed = parse_ai_target_variant(variant.get("target_variant", ""))
        content = replace_ai_equipment_target_variant(
            content, group["id"], variant["id"],
            parsed.get("type", ""), modules)
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        variant["target_variant"] = (
            "target_variant = {\n\ttype = %s\n\tmodules = {\n%s\n\t}\n}" % (
                parsed.get("type", ""),
                "\n".join("\t\t%s = %s" % (k, v) for k, v in modules.items())))

    # ---------- 保存 ----------
    def _save(self):
        group = self._current_group
        if not group or not self._current_variant:
            return
        variant = self._find_variant(self._current_variant)
        if not variant:
            return
        rel = group.get("rel", "")
        if not rel:
            return
        mod_fp, copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位 AI 装备文件")
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = replace_top_block_field(
            content, group["id"], "category", self.category_edit.text().strip())
        content = replace_ai_equipment_variant_field(
            content, group["id"], variant["id"], "history",
            self.history_edit.text().strip())
        content = replace_ai_equipment_allowed_modules(
            content, group["id"], variant["id"], self._modules())
        for field in VARIANT_ADVANCED:
            text = (self._variant_advanced.get(field) or "").strip()
            if text:
                content = replace_or_upsert_nested_child(
                    content, group["id"], variant["id"], field, text)
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        group["category"] = self.category_edit.text().strip()
        variant["history"] = self.history_edit.text().strip()
        variant["allowed_modules"] = "\n".join(self._modules())
        for field in VARIANT_ADVANCED:
            if field in self._variant_advanced:
                variant[field] = self._variant_advanced.get(field, "")
        msg = "已保存 AI 装备 %s / %s" % (group["id"], variant["id"])
        if copied:
            msg += "\n原版文件已自动复制到 mod"
        QMessageBox.information(self, "已保存", msg)


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

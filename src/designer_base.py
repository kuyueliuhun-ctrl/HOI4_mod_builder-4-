"""三设计器公共基类（F4）。

将 ship/plane/tank 三个高度重复的设计器对话框的共享方法抽到
`VariantDesignerBase`，子类只提供：
- 数据层 Provider（load hosts/modules/variants、stats、apply/insert/rename 等）
- UI 差异（_build_ui / _rebuild_editor / _update_stats / _load_data）
- 少量类属性（KIND / TITLE / SLOT_COLS / 中文名函数 / 槽位表等）

四层归属：本文件属 UI 层；槽位解析等算法仍在 designer_slots.py / *_design.py。
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
)

PANEL_WIDTH = 330

_STAT_LABEL_STYLE = "color:#5d6b7a; font-size:12px;"
_STAT_VALUE_STYLE = "color:#1f4f7e; font-weight:bold; font-size:12px;"
_STAT_GROUP_STYLE = (
    "QGroupBox { border: 1px solid rgba(22,35,51,0.18); border-radius: 8px;"
    " margin-top: 10px; font-weight: bold; }"
    "QGroupBox::title { subcontrol-origin: margin; left: 10px;"
    " padding: 0 4px; color:#425062; }")


def _fmt(v, nd=1):
    """数值格式化：None → "—"；整数去 .0；否则保留 nd 位。"""
    if v is None:
        return "—"
    f = float(v)
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return ("%." + str(nd) + "f") % f


def _fmt_pct(v, nd=1):
    if v is None:
        return "—"
    p = v * 100.0
    if abs(p - round(p)) < 1e-9:
        return "%d%%" % int(round(p))
    return ("%." + str(nd) + "f%%") % p


class VariantDesignerBase(QDialog):
    """设计器公共基类：顶部工具栏/数据加载/刷新/保存/模板/同款同步等。"""

    saved = pyqtSignal()

    # ---- 子类必须提供的类属性 ----
    KIND = ""                     # "ship" / "plane" / "tank"
    TITLE = ""                    # 窗口标题与顶栏标题
    HOST_LABEL = "未选择设计"      # 左侧 host 标签默认文本
    SLOT_COLS = 6
    HOSTS_LOADER = None
    MODULES_LOADER = None
    VARIANTS_LOADER = None
    STATS_FN = None
    TYPE_CN = None
    NAME_CN = None
    APPLY_MODULES = None
    APPLY_UPGRADES = None
    APPLY_ADVANCED = None
    INSERT_FN = None
    REMOVE_FN = None
    RENAME_FN = None
    PARSE_VARIANTS_FN = None
    VARIANTS_CACHE = None
    MODULE_PICKER_CLS = None
    SLOT_LABELS = {}
    CATEGORY_LABELS = {}

    def __init__(self, mod_path="", hoi4_path="", country_tag="", parent=None):
        super().__init__(parent)
        self.mod_path = mod_path
        self.hoi4_path = hoi4_path
        self._initial_country_tag = (country_tag or "").upper()
        self.hosts = {}
        self.modules = {}
        self.variants = {}
        self.current_tag = ""
        self.current_name = ""
        self.current_variant = None
        self._stat_labels = {}
        self._slot_buttons = {}
        self._empty_hint = None

        self.setWindowTitle(self.TITLE)
        self.resize(1280, 780)
        self._build_ui()
        self._load_data()
        self._refresh_countries()

    # ---------- 子类差异点（默认占位，子类覆盖） ----------

    def _build_ui(self):
        raise NotImplementedError

    def _load_data(self):
        raise NotImplementedError

    def _rebuild_editor(self):
        raise NotImplementedError

    def _update_stats(self):
        raise NotImplementedError

    # ---------- 统计面板 ----------

    def _build_stat_group(self, host_layout, title, fields):
        box = QGroupBox(title)
        box.setStyleSheet(_STAT_GROUP_STYLE)
        grid = QGridLayout(box)
        grid.setContentsMargins(10, 12, 10, 8)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)
        for row, (key, label) in enumerate(fields):
            lbl = QLabel(label)
            lbl.setStyleSheet(_STAT_LABEL_STYLE)
            val = QLabel("—")
            val.setStyleSheet(_STAT_VALUE_STYLE)
            val.setAlignment(Qt.AlignmentFlag.AlignRight
                             | Qt.AlignmentFlag.AlignVCenter)
            val.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(lbl, row, 0)
            grid.addWidget(val, row, 1)
            self._stat_labels[key] = val
        host_layout.addWidget(box)

    # ---------- 数据加载 ----------

    def _country_file(self, tag):
        """tag → history/countries 文件路径（mod 优先）。"""
        for base in (self.mod_path, self.hoi4_path):
            if not base:
                continue
            d = os.path.join(base, "history", "countries")
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                first = fn.split()[0].strip()
                if first.lower().endswith(".txt"):
                    first = first[:-4]
                if first == tag and fn.lower().endswith(".txt"):
                    return os.path.join(d, fn)
        return ""

    def _save_path(self, tag):
        """保存目标：mod 内路径（原版自动复制到 mod）。

        Returns:
            (mod_abs_path, copied)：copied=True 表示本次从游戏复制到 mod；
            找不到文件返回 (None, False)。
        """
        from state_build_ops import ensure_file_in_mod
        for base in (self.mod_path, self.hoi4_path):
            if not base:
                continue
            d = os.path.join(base, "history", "countries")
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                first = fn.split()[0].strip()
                if first.lower().endswith(".txt"):
                    first = first[:-4]
                if first == tag and fn.lower().endswith(".txt"):
                    rel = os.path.join("history", "countries", fn)
                    return ensure_file_in_mod(self.mod_path, self.hoi4_path,
                                              rel)
        return None, False

    # ---------- 刷新 ----------

    def _refresh_countries(self):
        self.country_combo.blockSignals(True)
        self.country_combo.clear()
        for tag in sorted(self.variants):
            n = len(self.variants[tag])
            self.country_combo.addItem(f"{tag} ({n} 个设计)", tag)
        self.country_combo.blockSignals(False)
        if self.country_combo.count() > 0:
            idx = 0
            if self._initial_country_tag:
                fi = self.country_combo.findData(self._initial_country_tag)
                if fi >= 0:
                    idx = fi
            self.country_combo.setCurrentIndex(idx)
            self._on_country_changed(idx)

    def _on_country_changed(self, index):
        tag = self.country_combo.itemData(index)
        self.current_tag = tag or ""
        self._refresh_designs()

    def _refresh_designs(self):
        self.design_combo.blockSignals(True)
        self.design_combo.clear()
        variants = self.variants.get(self.current_tag) or {}
        for name, v in variants.items():
            cn = type(self).TYPE_CN(v.get("type", ""))
            disp = type(self).NAME_CN(name)
            self.design_combo.addItem(f"{disp}  [{cn}]", name)
        self.design_combo.blockSignals(False)
        if self.design_combo.count() > 0:
            self.design_combo.setCurrentIndex(0)
            self._on_design_changed(0)
        else:
            self.current_name = ""
            self.current_variant = None
            self._clear_editor()

    def _on_design_changed(self, index):
        name = self.design_combo.itemData(index)
        variants = self.variants.get(self.current_tag) or {}
        self.current_name = name or ""
        self.current_variant = variants.get(self.current_name)
        self._rebuild_editor()

    # ---------- 高级字段 ----------

    def _advanced_values(self):
        """收集高级字段表单值；空/默认值保持缺省语义。"""
        design_team = self.design_team_combo.currentText().strip()
        if design_team and not design_team.startswith("mio:"):
            design_team = "mio:" + design_team
        parent_version = self.parent_version_edit.text().strip()
        if parent_version == "":
            parent_version = 0
        return {
            "design_team": design_team,
            "parent_version": parent_version,
            "obsolete": self.obsolete_check.isChecked(),
            "icon": self.icon_edit.text().strip(),
        }

    def _load_advanced_fields(self):
        """把当前变体高级字段回填表单，并收集同国家已有设计团队作为下拉候选。"""
        if self.current_variant is None:
            self.design_team_combo.setCurrentText("")
            self.parent_version_edit.setText("")
            self.obsolete_check.setChecked(False)
            self.icon_edit.setText("")
            return
        v = self.current_variant
        tag_variants = self.variants.get(self.current_tag) or {}
        teams = sorted({(d.get("design_team") or "") for d in tag_variants.values()
                        if d.get("design_team")})
        self.design_team_combo.blockSignals(True)
        self.design_team_combo.clear()
        for team in teams:
            self.design_team_combo.addItem(team)
        self.design_team_combo.setCurrentText(v.get("design_team") or "")
        self.design_team_combo.blockSignals(False)
        pv = v.get("parent_version")
        self.parent_version_edit.setText("" if pv in (None, 0) else str(pv))
        self.obsolete_check.setChecked(bool(v.get("obsolete")))
        self.icon_edit.setText(v.get("icon") or "")

    # ---------- 编辑区通用 ----------

    def _clear_editor(self):
        self.host_label.setText("（该国家暂无设计）")
        if hasattr(self, "same_name_label"):
            self.same_name_label.setText("")
        while self.slot_grid.count():
            item = self.slot_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        for key in self._stat_labels:
            self._stat_labels[key].setText("—")
        if hasattr(self, "dominance_label"):
            self.dominance_label.setText("—")
        self.cost_label.setText("生产花费: —")
        self._load_advanced_fields()

    def _update_save_validation(self):
        if self.current_variant is None:
            return
        v = self.current_variant
        host = self.hosts.get(v.get("type", "")) or {}
        slots = host.get("module_slots") or {}
        modules = v.get("modules") or {}
        missing = sum(
            1 for s, info in slots.items()
            if info.get("required")
            and (not modules.get(s) or modules.get(s) == "empty"))
        if missing:
            self.save_validation_label.setText(
                "⛔ 必装槽未填 %d 个 —— 填满后方可保存" % missing)
            self.save_validation_label.setStyleSheet(
                "color:#b7791f; font-weight:bold;")
            self.save_btn.setEnabled(False)
        else:
            self.save_validation_label.setText("✅ 必装槽已填满，可保存")
            self.save_validation_label.setStyleSheet(
                "color:#2f7d57; font-weight:bold;")
            self.save_btn.setEnabled(True)

    def _module_brief(self, mod):
        """模块效果摘要（add/multiply 前几项）。"""
        parts = []
        for k, v in list((mod.get("add_stats") or {}).items())[:4]:
            parts.append(f"{k} {_fmt(v, 1)}")
        for k, v in list((mod.get("multiply_stats") or {}).items())[:3]:
            parts.append(f"{k} ×{_fmt(1 + v, 3)}")
        return "效果: " + " · ".join(parts) if parts else "（无修正）"

    def _refresh_upgrade_card(self):
        rows = []
        if self.current_variant is not None:
            v = self.current_variant
            host = self.hosts.get(v.get("type", "")) or {}
            keys = host.get("upgrades_decl") or []
            from designer_slots import load_upgrade_definitions
            defs = load_upgrade_definitions(self.hoi4_path, self.mod_path)
            cur_u = v.get("upgrades") or {}
            for key in keys:
                info = defs.get(key) or {}
                cur = int(cur_u.get(key, 0) or 0)
                mx = info.get("max_level") or 5
                cn = type(self).NAME_CN(key)
                reqs = info.get("level_requirements") or {}
                remark = ""
                if reqs:
                    remark = "科技解锁: " + "、".join(
                        "Lv%d" % lv for lv in sorted(reqs))
                rows.append((cn, key, cur, mx, remark))
        if hasattr(self, "upgrade_card"):
            self.upgrade_card.set_rows(rows)

    # ---------- 模块选择 ----------

    def _open_module_picker(self, slot_key):
        if self.current_variant is None:
            return
        host = self.hosts.get(self.current_variant.get("type", "")) or {}
        slot_info = (host.get("module_slots") or {}).get(slot_key) or {}
        allowed = slot_info.get("allowed") or []
        current = (self.current_variant.get("modules") or {}).get(slot_key)
        dlg = self.MODULE_PICKER_CLS(
            self.modules, allowed,
            self.SLOT_LABELS.get(slot_key, slot_key),
            current_module=current, parent=self)
        if not dlg.exec():
            return
        upgrades = self.current_variant.setdefault("modules", {})
        if dlg.remove_requested:
            upgrades.pop(slot_key, None)
        elif dlg.picked:
            upgrades[slot_key] = dlg.picked
        self._rebuild_editor()

    # ---------- 模板管理 ----------

    def _add_design(self):
        if not self.current_tag:
            return
        from PyQt6.QtWidgets import QInputDialog
        host_keys = [k for k in self.hosts
                     if not self.hosts[k].get("is_archetype")]
        if not host_keys:
            QMessageBox.warning(self, "无法新建", "未找到可用" + self.KIND + "。")
            return
        items = []
        for k in sorted(host_keys, key=lambda x: (self.hosts[x].get("year") or 0, x)):
            cn = type(self).TYPE_CN(k)
            yr = self.hosts[k].get("year")
            items.append("%s  %s  [%s]" % (cn, yr if yr else "", k))
        choice, ok = QInputDialog.getItem(
            self, "选择" + self.KIND, self.KIND + "（中文名 + 年份 + 键）:",
            items, 0, False)
        if not ok:
            return
        host_key = choice.rsplit("[", 1)[-1].rstrip("]")
        if host_key not in self.hosts:
            return
        name = "New " + self.KIND.title() + " Design"
        self.variants.setdefault(self.current_tag, {})[name] = {
            "type": host_key, "modules": {}}
        self._refresh_designs()
        idx = self.design_combo.findData(name)
        if idx >= 0:
            self.design_combo.setCurrentIndex(idx)

    def _copy_design(self):
        if self.current_variant is None:
            return
        new_name = self.current_name + " Copy"
        self.variants.setdefault(self.current_tag, {})[new_name] = {
            "type": self.current_variant.get("type", ""),
            "modules": dict(self.current_variant.get("modules") or {}),
            "design_team": self.current_variant.get("design_team", ""),
            "parent_version": self.current_variant.get("parent_version", 0),
            "obsolete": self.current_variant.get("obsolete", False),
            "icon": self.current_variant.get("icon", ""),
        }
        self._refresh_designs()
        idx = self.design_combo.findData(new_name)
        if idx >= 0:
            self.design_combo.setCurrentIndex(idx)

    def _delete_design(self):
        if self.current_variant is None:
            return
        ret = QMessageBox.question(
            self, "删除设计",
            f"删除设计「{self.current_name}」？（写入保存后才生效）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        self.variants.get(self.current_tag, {}).pop(self.current_name, None)
        self.current_variant = None
        self._refresh_designs()

    def _serialize_template(self, name):
        """当前设计 → create_equipment_variant PDX 文本（modules 块）。"""
        if self.current_variant is None:
            return None
        typ = self.current_variant.get("type", "")
        modules = self.current_variant.get("modules") or {}
        lines = ["create_equipment_variant = {",
                 f'\tname = "{name}"',
                 f"\ttype = {typ}"]
        adv = self._advanced_values()
        if adv["design_team"]:
            lines.append("\tdesign_team = " + adv["design_team"])
        if adv["parent_version"] not in (None, "", 0) and str(adv["parent_version"]) != "0":
            lines.append("\tparent_version = " + str(adv["parent_version"]))
        if adv["obsolete"]:
            lines.append("\tobsolete = yes")
        if adv["icon"]:
            lines.append('\ticon = "' + adv["icon"] + '"')
        lines.append("\tmodules = {")
        for slot, mod in modules.items():
            lines.append(f"\t\t{slot} = {mod}")
        lines.append("\t}")
        lines.append("}")
        return "\n".join(lines)

    def _save_as_template(self):
        if self.current_variant is None:
            QMessageBox.information(self, "提示", "没有可保存的设计。")
            return
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "存为模板", "模板名:", text=self.current_name)
        if not ok or not name.strip():
            return
        content = self._serialize_template(name.strip())
        if not content:
            return
        from design_template import save_design_template
        path = save_design_template(self.KIND, name.strip(), content)
        if path:
            QMessageBox.information(self, "已保存模板",
                                    f"模板已保存到:\n{path}")
        else:
            QMessageBox.critical(self, "保存失败", "模板保存失败。")

    def _new_from_template(self):
        if not self.current_tag:
            return
        from PyQt6.QtWidgets import QInputDialog
        from design_template import list_design_templates, load_design_template
        tpls = list_design_templates(self.KIND)
        if not tpls:
            QMessageBox.information(self, "模板", "暂无" + self.KIND + "设计模板。")
            return
        names = [t["name"] for t in tpls]
        name, ok = QInputDialog.getItem(self, "从模板新建", "选择模板:",
                                        names, 0, False)
        if not ok:
            return
        content = load_design_template(self.KIND, name)
        if not content:
            return
        parsed = type(self).PARSE_VARIANTS_FN(content, None, "modules")
        if not parsed:
            QMessageBox.warning(self, "模板无效",
                                "模板内容不是有效的" + self.KIND + "设计。")
            return
        tpl_name, tpl_data = next(iter(parsed.items()))
        variants = self.variants.setdefault(self.current_tag, {})
        new_name = tpl_name
        while new_name in variants:
            new_name = tpl_name + " Copy"
            tpl_name = new_name
        variants[new_name] = {
            "type": tpl_data.get("type", ""),
            "modules": tpl_data.get("modules", {}),
            "design_team": tpl_data.get("design_team", ""),
            "parent_version": tpl_data.get("parent_version", 0),
            "obsolete": tpl_data.get("obsolete", False),
            "icon": tpl_data.get("icon", ""),
        }
        self._refresh_designs()
        idx = self.design_combo.findData(new_name)
        if idx >= 0:
            self.design_combo.setCurrentIndex(idx)

    # ---------- 同款跨国家（按名字匹配） ----------

    def _same_name_tags(self):
        """当前设计名在哪些国家存在（含当前国家）。"""
        if not self.current_name:
            return []
        tags = []
        for tag, ds in self.variants.items():
            if self.current_name in ds:
                tags.append(tag)
        return tags

    def _update_same_name_label(self):
        if not hasattr(self, "same_name_label"):
            return
        tags = self._same_name_tags()
        if len(tags) > 1:
            self.same_name_label.setText(
                f"同款 {len(tags)} 国: " + "、".join(sorted(tags)[:8])
                + ("…" if len(tags) > 8 else ""))
        else:
            self.same_name_label.setText("")

    def _sync_to_all_same_name(self):
        """把当前设计配置写回所有使用同名设计的国家（原子写）。"""
        if self.current_variant is None:
            return
        tags = [t for t in self._same_name_tags() if t != self.current_tag]
        if not tags:
            QMessageBox.information(self, "同步",
                                    "当前设计没有其他国家的同款。")
            return
        ret = QMessageBox.question(
            self, "同步到所有同款",
            f"将当前配置写入 {len(tags)} 个国家的同名设计？\n"
            + "、".join(sorted(tags)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        modules = dict(self.current_variant.get("modules") or {})
        typ = self.current_variant.get("type", "")
        name = self.current_name
        ok = 0
        failed = []
        for tag in tags:
            try:
                path, _copied = self._save_path(tag)
                if not path:
                    failed.append(tag)
                    continue
                with open(path, "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    content = f.read()
                if name in content:
                    new_content = type(self).APPLY_MODULES(
                        content, name, modules, typ)
                else:
                    new_content = type(self).INSERT_FN(content, tag, name, typ,
                                                 modules)
                if new_content is not None and type(self).APPLY_UPGRADES is not None:
                    new_content = type(self).APPLY_UPGRADES(
                        new_content, name,
                        self.upgrade_card.values(), typ)
                if new_content is not None:
                    new_content = type(self).APPLY_ADVANCED(
                        new_content, name,
                        self._advanced_values(), typ)
                if new_content is None:
                    failed.append(tag)
                    continue
                from write_utils import atomic_write_text
                atomic_write_text(path, new_content)
                adv = self._advanced_values()
                self.variants.setdefault(tag, {})[name] = {
                    "type": typ, "modules": modules,
                    "design_team": adv["design_team"],
                    "parent_version": adv["parent_version"],
                    "obsolete": adv["obsolete"],
                    "icon": adv["icon"],
                }
                ok += 1
            except Exception as e:
                failed.append(f"{tag}({e})")
        msg = f"已同步 {ok} 个国家。"
        if failed:
            msg += "\n失败: " + "、".join(failed)
        QMessageBox.information(self, "同步完成", msg)
        self._update_same_name_label()

    # ---------- 保存 / 重置 ----------

    def _save(self):
        if self.current_variant is None:
            QMessageBox.information(self, "提示", "没有可保存的设计。")
            return
        tag = self.current_tag
        path, copied = self._save_path(tag)
        if not path:
            QMessageBox.critical(self, "保存失败", f"找不到国家 {tag} 的文件。")
            return
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return
        new_name = self.name_edit.text().strip() or self.current_name
        old_name = self.current_name
        modules = self.current_variant.get("modules") or {}
        new_content = None
        if old_name in content:
            new_content = type(self).APPLY_MODULES(
                content, old_name, modules,
                self.current_variant.get("type", ""))
            if new_content is not None and new_name != old_name:
                new_content = type(self).RENAME_FN(
                    new_content, old_name, new_name,
                    self.current_variant.get("type", ""))
        else:
            new_content = type(self).INSERT_FN(
                content, tag, new_name,
                self.current_variant.get("type", ""), modules)
        if new_content is not None and type(self).APPLY_UPGRADES is not None:
            new_content = type(self).APPLY_UPGRADES(
                new_content, new_name,
                self.upgrade_card.values(),
                self.current_variant.get("type", ""))
        if new_content is not None:
            new_content = type(self).APPLY_ADVANCED(
                new_content, new_name,
                self._advanced_values(),
                self.current_variant.get("type", ""))
        if new_content is None:
            QMessageBox.critical(self, "保存失败",
                                 "未能定位到设计块，文件可能已被外部修改。")
            return
        try:
            from write_utils import atomic_write_text
            atomic_write_text(path, new_content)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return
        variants = self.variants.setdefault(tag, {})
        if old_name != new_name:
            variants.pop(old_name, None)
        adv = self._advanced_values()
        variants[new_name] = {
            "type": self.current_variant.get("type", ""),
            "modules": modules,
            "design_team": adv["design_team"],
            "parent_version": adv["parent_version"],
            "obsolete": adv["obsolete"],
            "icon": adv["icon"],
        }
        self.current_name = new_name
        self._refresh_designs()
        idx = self.design_combo.findData(new_name)
        if idx >= 0:
            self.design_combo.setCurrentIndex(idx)
        QMessageBox.information(self, "已保存",
                                f"已保存到:\n{path}"
                                + ("\n\n（该国家文件原本只在游戏目录，已自动复制到 mod）"
                                   if copied else ""))
        self.saved.emit()

    def _reset(self):
        if not self.current_tag:
            return
        if self.VARIANTS_CACHE is not None:
            self.VARIANTS_CACHE.pop(
                (self.mod_path or "", self.hoi4_path or ""), None)
        self._load_data()
        self._refresh_countries()
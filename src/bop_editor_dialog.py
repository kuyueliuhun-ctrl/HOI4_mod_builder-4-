# -*- coding: utf-8 -*-
"""力量平衡（Balance of Power）专用工作台

批次 6：完整行内编辑表单（程序基本亮色风格，废弃深色 QSS）。

功能：
  - 平衡与区间：滑块 + 初始值；每区间卡 min/max SpinBox + modifier 键值表；
    区间增删。
  - 势力与修正：左右势力卡（图标 / 本地化键 / 中文名 / 关联区间勾选）。
  - 决议（动作）：动作列表 + 新建决议（模板：通用/限时/切换类）+ 选中项编辑
    （名称本地化双行 / 花费 / BOP 增量 / 效果结构化块）+ 删除。
  - 保存：BOP 文件与决策文件分别 ensure_file_in_mod + 原子写；本地化沿用
    upsert_loc_entry 链。

兼容旧入口/旧契约测试：保留滑块/状态标签/左右势力/决策分类编辑控件和
「动作 / 势力与修正」两个页签；「平衡与区间」作为顶部页签区展示。
"""

from __future__ import annotations

import os
import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFrame, QGridLayout,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QScrollArea, QSlider,
    QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

from ai_loader import _find_block_bounds
from ai_ui_common import KeyValueTableEditor, ScriptBlockEditorDialog
from bop_loader import (
    _parse_decision_action, _state_label, find_active_range, load_bop_actions,
)
from oob_loader import _block_ranges
from theme import COLORS as C
from bop_editor_pages import (
    BopEditorPagesMixin,
    _action_icon,
    _card,
    _fmt_modifier_value,
    _loc_text,
    _make_scroll,
    _strip_icon_token,
)

try:
    from quick_loc_menu import install_context_menu
except Exception:  # 测试/无菜单环境兼容
    def install_context_menu(*args, **kwargs):
        return None


_ICON_TOKEN_RE = re.compile(r"^\s*£[^\s]*\s*")
_VAR_REF_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)\$")
_CARD_QSS = """
QFrame#BopCard {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 12px;
}}
QLabel#BopCardTitle {{
    color: {heading};
    font-weight: bold;
    font-size: 14px;
}}
QLabel#BopSecondary {{
    color: {secondary};
}}
""".format(surface=C["bg_surface"], border=C["border_strong"],
           heading=C["text_heading"], secondary=C["text_secondary"])


class BopEditorDialog(BopEditorPagesMixin, QDialog):
    """力量平衡（Balance of Power）专用编辑器。"""

    def __init__(self, bop, mod_path="", hoi4_path="", parent=None):
        super().__init__(parent)
        self.bop = bop
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.setWindowTitle("Balance of Power - %s" % bop.get("tag", ""))
        self.setModal(True)
        self.resize(1040, 820)

        self._loc = self._load_loc_manager()
        self.actions = load_bop_actions(
            self.mod_path, self.hoi4_path,
            bop.get("decision_category", ""), self._loc)
        self._orig_actions = {a["key"]: dict(a) for a in self.actions}
        self._orig_range_ids = {item["rng"].get("id", "")
                                for item in self._flat_ranges()}
        self._action_blocks = {}
        self._dirty = False
        self._loading_action_list = False
        self._loading_detail = False
        self._delta_edited = False
        self._detail_loaded = False

        self._build_ui()
        self._refresh_slider_text()
        self._rebuild_range_cards()
        self._rebuild_side_cards()
        self._populate_action_list()
        self._loading_action_list = True
        try:
            if self.action_list.count() > 0:
                self.action_list.setCurrentRow(0)
                self._load_action_detail(self._current_action())
                self._detail_loaded = True
            else:
                self._load_action_detail(None)
        finally:
            self._loading_action_list = False

    # ------------------------------------------------------------ 本地化
    def _load_loc_manager(self):
        from localization_mgr import get_localization_manager
        try:
            loc = get_localization_manager()
        except Exception:
            return None
        try:
            if self.hoi4_path:
                loc.add_game_path(self.hoi4_path)
            if self.mod_path:
                loc.add_mod_path(self.mod_path)
        except Exception:
            pass
        return loc

    def _modifier_name(self, key):
        """修饰键中文名：MODIFIER_<KEY> / raw key / 英语 yml，逐级回退。"""
        if self._loc is not None:
            for cand in ("MODIFIER_" + key.upper(), key):
                try:
                    raw = self._loc.get_name(cand)
                    if raw:
                        return _strip_icon_token(raw)
                except Exception:
                    pass
        for base in (self.mod_path, self.hoi4_path):
            if not base:
                continue
            fp = os.path.join(base, "localisation", "english",
                              "modifiers_l_english.yml")
            if not os.path.isfile(fp):
                continue
            try:
                with open(fp, "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    for line in f:
                        m = re.match(
                            r'\s*(?:MODIFIER_%s|%s)\s*:\s*"(.*)"\s*$'
                            % (re.escape(key.upper()), re.escape(key)),
                            line)
                        if m:
                            return m.group(1)
            except Exception:
                pass
        return key

    # ------------------------------------------------------------ 数据视图
    def _flat_ranges(self):
        """返回 [{rng, side_id}]，含顶层与 side 内嵌区间。"""
        out = []
        for rng in self.bop.get("ranges", []):
            out.append({"rng": rng, "side_id": None})
        for side in self.bop.get("sides", []):
            for rng in side.get("ranges", []):
                out.append({"rng": rng, "side_id": side.get("id", "")})
        return out

    def _flat_range_keys(self):
        keys = set()
        for item in self._flat_ranges():
            keys.add((item["side_id"] or "", item["rng"].get("id", "")))
        return keys

    def _current_range_by_id(self, range_id):
        for item in self._flat_ranges():
            if item["rng"].get("id") == range_id:
                return item
        return None

    # ------------------------------------------------------------ UI 构建
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        header = self._build_header()
        root.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Vertical)
        top_widget = self._build_balance_page()
        splitter.addWidget(_make_scroll(top_widget))
        splitter.setStretchFactor(0, 1)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_sides_tab(), "势力与修正")
        self.tabs.addTab(self._build_actions_tab(), "决议（动作）")
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter, 1)

        footer = QHBoxLayout()
        edit_btn = QPushButton("✏ 编辑定义")
        edit_btn.setToolTip("打开 BOP 文件树编辑器（可编辑高级块）")
        edit_btn.clicked.connect(self._edit_bop_file)
        footer.addWidget(edit_btn)
        footer.addStretch(1)
        save_btn = QPushButton("💾 保存修改")
        save_btn.setStyleSheet(
            "font-weight:bold; background:%s; color:#fff;"
            % C["accent"])
        save_btn.setToolTip(
            "保存 BOP 文件与决策文件（原版自动复制到 mod）")
        save_btn.clicked.connect(self._save_changes)
        footer.addWidget(save_btn)
        root.addLayout(footer)

    def _build_header(self):
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Balance of Power")
        title.setStyleSheet("font-size:20px; font-weight:bold; color:%s;"
                            % C["accent"])
        loc_name = _loc_text(self._loc, self.bop.get("id", ""))
        if loc_name and loc_name != "国家权力平衡":
            subtitle = QLabel("国家权力平衡 · %s（%s）" % (
                loc_name, self.bop.get("tag", "")))
        else:
            subtitle = QLabel("国家权力平衡 · %s" % self.bop.get("tag", ""))
        subtitle.setStyleSheet("color:%s; font-size:14px;"
                               % C["text_secondary"])
        install_context_menu(
            subtitle, self.mod_path, self.hoi4_path,
            key_provider=lambda: self.bop.get("id", "") or "",
            desc_key_provider=lambda: (
                (self.bop.get("id", "") + "_desc")
                if self.bop.get("id") else ""),
            parent=self)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch(1)
        close_btn = QPushButton("✕")
        close_btn.setToolTip("关闭")
        close_btn.clicked.connect(self.accept)
        header.addWidget(close_btn)
        return header

    def _current_value(self):
        return self.slider.value() / 100.0

    def _on_initial_edit(self, value):
        self.slider.setValue(int(round(value * 100)))

    def _refresh_slider_text(self):
        v = self._current_value()
        self.value_label.setText("当前值：%+.2f" % v)
        self.initial_edit.blockSignals(True)
        self.initial_edit.setValue(round(v, 3))
        self.initial_edit.blockSignals(False)
        state = _state_label(self.bop, v)
        if state:
            self.status_label.setText("当前状态：%s" % _loc_text(self._loc, state))
        else:
            self.status_label.setText("当前状态：—")
        self._refresh_modifiers(v)

    def _refresh_modifiers(self, v=None):
        if v is None:
            v = self._current_value()
        _, rng = find_active_range(self.bop, v)
        mods = (rng or {}).get("modifier") or {}
        if mods:
            text = "当前修正：%s" % "，".join(
                "%s %s" % (self._modifier_name(k), _fmt_modifier_value(v))
                for k, v in mods.items())
        else:
            text = "当前修正：—"
        self.modifiers_label.setText(text)

    # ------------------------------------------------------------ 保存
    def _save_initial_value(self):
        """兼容旧调用：仅保存滑块初始值（实际走 _save_changes）。"""
        self._save_changes()

    def _save_changes(self):
        from bop_loader import (
            delete_bop_decision, delete_bop_range, insert_bop_decision,
            insert_bop_range, set_bop_action_block, set_bop_action_fields,
            set_bop_fields, set_bop_initial_value, set_bop_range,
            set_bop_range_modifiers, set_bop_range_side, set_bop_side_fields,
            upsert_bop_localisation,
        )
        self._sync_action_from_form()
        if not self.mod_path:
            QMessageBox.warning(self, "保存失败", "请先打开 mod 目录")
            return

        # 1) BOP 基础字段
        try:
            set_bop_initial_value(
                self.mod_path, self.hoi4_path,
                self.bop.get("id", ""), self._current_value())
            set_bop_fields(
                self.mod_path, self.hoi4_path, self.bop.get("id", ""),
                left_side=self.left_edit.text().strip(),
                right_side=self.right_edit.text().strip(),
                decision_category=self.decision_edit.text().strip())
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "BOP 基础字段保存失败：%s" % e)
            return

        # 2) side 字段与区间归属
        try:
            self._save_sides_and_ranges()
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "势力/区间保存失败：%s" % e)
            return

        # 3) 决议动作
        try:
            self._save_actions()
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "决议保存失败：%s" % e)
            return

        self._dirty = False
        self.bop["initial_value"] = self._current_value()
        self.bop["left_side"] = self.left_edit.text().strip()
        self.bop["right_side"] = self.right_edit.text().strip()
        self.bop["decision_category"] = self.decision_edit.text().strip()
        from bop_loader import _clear_cache
        _clear_cache()
        self.actions = load_bop_actions(
            self.mod_path, self.hoi4_path,
            self.bop.get("decision_category", ""), self._loc)
        self._orig_actions = {a["key"]: dict(a) for a in self.actions}
        self._orig_range_ids = {item["rng"].get("id", "")
                                for item in self._flat_ranges()}
        self._populate_action_list()
        self._loading_action_list = True
        try:
            if self.action_list.count() > 0:
                self.action_list.setCurrentRow(0)
                self._load_action_detail(self._current_action())
                self._detail_loaded = True
            else:
                self._load_action_detail(None)
        finally:
            self._loading_action_list = False
        QMessageBox.information(self, "已保存", "BOP 文件与决策文件已保存")

    def _save_sides_and_ranges(self):
        from bop_loader import (
            delete_bop_range, insert_bop_range, set_bop_range,
            set_bop_range_modifiers, set_bop_range_side, set_bop_side_fields,
            upsert_bop_localisation,
        )
        self._collect_range_card_data()
        bop_id = self.bop.get("id", "")
        # side 字段
        loc_entries = {}
        new_side_ids = {}
        for info in getattr(self, "side_cards", []):
            side = info["side"]
            old_id = side.get("id", "")
            new_id = info["loc_key_edit"].text().strip() or old_id
            icon = info["icon_edit"].text().strip()
            if old_id and icon:
                set_bop_side_fields(self.mod_path, self.hoi4_path, bop_id,
                                    old_id, icon=icon, loc_key=new_id)
            elif old_id and new_id != old_id:
                set_bop_side_fields(self.mod_path, self.hoi4_path, bop_id,
                                    old_id, icon=None, loc_key=new_id)
            side["id"] = new_id
            new_side_ids[old_id] = new_id
            cn = info["name_cn_edit"].text().strip()
            if cn:
                loc_entries[new_id] = cn
        # 同步 left/right 内存引用（若 side id 变了）
        for old, new in new_side_ids.items():
            if old != new:
                if self.bop.get("left_side") == old:
                    self.bop["left_side"] = new
                if self.bop.get("right_side") == old:
                    self.bop["right_side"] = new
                if self.left_edit.text().strip() == old:
                    self.left_edit.setText(new)
                if self.right_edit.text().strip() == old:
                    self.right_edit.setText(new)

        # 区间更新/新增/删除（按 range_id 追踪，side 变更走 set_bop_range_side）
        current_rids = set()
        for item in self._flat_ranges():
            rng = item["rng"]
            rid = rng.get("id", "")
            side_id = item["side_id"]
            current_rids.add(rid)
            if rid not in self._orig_range_ids:
                text = ("range = {\n"
                        "\t\tid = %s\n"
                        "\t\tmin = %s\n"
                        "\t\tmax = %s\n"
                        "\t}" % (rid, rng.get("min", -0.1),
                                 rng.get("max", 0.1)))
                insert_bop_range(self.mod_path, self.hoi4_path, bop_id,
                                 text, side_id=side_id)
                if rng.get("modifier"):
                    set_bop_range_modifiers(
                        self.mod_path, self.hoi4_path, bop_id, rid,
                        rng.get("modifier") or {})
            else:
                set_bop_range(
                    self.mod_path, self.hoi4_path, bop_id, rid,
                    min_v=rng.get("min", 0.0), max_v=rng.get("max", 0.0))
                set_bop_range_modifiers(
                    self.mod_path, self.hoi4_path, bop_id, rid,
                    rng.get("modifier") or {})
                set_bop_range_side(self.mod_path, self.hoi4_path, bop_id,
                                   rid, side_id=side_id)
        for old_rid in self._orig_range_ids:
            if old_rid not in current_rids:
                delete_bop_range(self.mod_path, self.hoi4_path, bop_id,
                                 old_rid)
        if loc_entries:
            upsert_bop_localisation(self.mod_path, loc_entries)

    def _save_actions(self):
        from bop_loader import (
            delete_bop_decision, insert_bop_decision, set_bop_action_block,
            set_bop_action_fields, upsert_bop_localisation,
        )
        category = self.decision_edit.text().strip()
        if not category:
            return
        bop_id = self.bop.get("id", "")
        current_keys = set()
        loc_entries = {}
        for action in self.actions:
            key = action.get("key", "")
            current_keys.add(key)
            cn = action.get("name_cn")
            if cn:
                loc_entries[key] = cn
            orig = self._orig_actions.get(key)
            is_new = action.get("new") or orig is None
            if is_new:
                if action.get("raw"):
                    insert_bop_decision(self.mod_path, self.hoi4_path,
                                        category, action["raw"], action_id=key)
                # 新动作也应用表单编辑
                self._apply_action_edits(
                    category, key, action, orig=None, bop_id=bop_id)
            else:
                self._apply_action_edits(
                    category, key, action, orig=orig, bop_id=bop_id)
        for old_key in self._orig_actions:
            if old_key not in current_keys:
                delete_bop_decision(self.mod_path, self.hoi4_path,
                                    category, old_key)
        if loc_entries:
            upsert_bop_localisation(self.mod_path, loc_entries)

    def _apply_action_edits(self, category, action_id, action, orig, bop_id):
        from bop_loader import (
            set_bop_action_block, set_bop_action_fields,
        )
        cost = action.get("cost")
        delta = action.get("delta")
        delta_edited = bool(action.get("delta_edited"))
        cost_changed = orig is None or (
            cost is not None and cost != orig.get("cost"))
        delta_changed = (orig is None and delta_edited) or (
            orig is not None and delta_edited
            and delta is not None and delta != orig.get("delta"))
        if cost_changed or delta_changed:
            set_bop_action_fields(
                self.mod_path, self.hoi4_path, category, action_id,
                cost=cost if cost_changed else None,
                add_power_balance_value=(
                    delta if delta_changed and delta is not None else None),
                bop_id=bop_id)
        blocks = self._action_blocks_for(action)
        if orig is not None:
            orig_blocks = self._action_blocks_for(orig)
        else:
            raw = action.get("raw", "") or ""
            orig_blocks = {
                bk: self._extract_direct_block(raw, bk)
                for bk in ("complete_effect", "visible", "available",
                           "remove_effect", "ai_will_do")
            }
        for bk, text in blocks.items():
            if text is None or text == "":
                continue
            if text != orig_blocks.get(bk, ""):
                set_bop_action_block(self.mod_path, self.hoi4_path,
                                     category, action_id, bk, text)

    # ------------------------------------------------------------ 树编辑器
    def _ensure_writable_file(self, fp):
        """确保编辑目标在 mod 内；原版文件自动复制到 mod。"""
        if not fp:
            return None, False
        fp = os.path.normpath(fp)
        if self.mod_path and os.path.normcase(fp).startswith(
                os.path.normcase(os.path.normpath(self.mod_path))):
            return fp, False
        if not self.mod_path:
            return None, False
        if self.hoi4_path:
            try:
                rel = os.path.relpath(fp, self.hoi4_path)
                if not rel.startswith(".."):
                    from state_build_ops import ensure_file_in_mod
                    mod_fp, copied = ensure_file_in_mod(
                        self.mod_path, self.hoi4_path,
                        rel.replace("\\", "/"))
                    if mod_fp:
                        return mod_fp, copied
            except Exception:
                pass
        return None, False

    def _edit_bop_file(self):
        fp = self.bop.get("file", "")
        if not fp:
            QMessageBox.warning(self, "无法编辑", "未找到 BOP 文件路径")
            return
        self._open_tree_editor_for_file(
            fp, "BOP 定义编辑 - %s" % self.bop.get("tag", ""),
            entity_id=self.bop.get("id", ""))

    def _edit_action(self, action):
        fp = action.get("file", "")
        if not fp:
            QMessageBox.warning(self, "无法编辑", "未找到动作文件路径")
            return
        self._open_tree_editor_for_file(
            fp, "动作编辑 - %s" % action.get("key", ""),
            entity_id=action.get("key", ""))

    def _open_tree_editor_for_file(self, fp, title, entity_id=None):
        """打开通用 PDX 树编辑器；原版文件先复制到 mod。"""
        mod_fp, copied = self._ensure_writable_file(fp)
        if not mod_fp:
            QMessageBox.warning(
                self, "无法编辑",
                "请先打开 mod 目录；原版文件只读，需复制到 mod 后才能编辑")
            return
        try:
            with open(mod_fp, "r", encoding="utf-8-sig",
                      errors="ignore") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "无法编辑", "读取文件失败：%s" % e)
            return

        from tree_node import tree_from_pdx_text
        from generic_tree_editor import GenericTreeEditor
        from gui_translator import get_translator
        from focus_view import CUSTOM_STATEMENT_PATH

        file_lines = content.splitlines()
        root = tree_from_pdx_text(content)
        editor = GenericTreeEditor(
            root_node=root,
            file_path=mod_fp,
            file_lines=file_lines,
            block_range=(1, len(file_lines) + 1),
            translator=get_translator(),
            custom_statement_path=CUSTOM_STATEMENT_PATH,
            loc_manager=self._loc,
            parent=self,
            title=title,
            hoi4_path=self.hoi4_path,
            mod_path=self.mod_path,
        )
        editor.show()
        if copied:
            # 原版复制到 mod 后，后续保存应指向 mod 文件
            if self.bop.get("file") and os.path.normpath(
                    self.bop["file"]) == os.path.normpath(fp):
                self.bop["file"] = mod_fp
        if entity_id:
            self._locate_entity_in_editor(editor, entity_id)

    def _locate_entity_in_editor(self, editor, entity_id):
        try:
            model = getattr(editor, "model", None)
            if model is None:
                return
            results = model.find_nodes(entity_id)
            if results:
                editor.tree_view.setCurrentIndex(results[0])
                editor.tree_view.scrollTo(results[0])
        except Exception:
            pass


def open_bop_editor(file_path, mod_path="", hoi4_path="", parent=None):
    """按文件路径打开 BOP 编辑器（文件模式/无文件模式共用）。"""
    from bop_loader import load_bop_definitions
    defs = load_bop_definitions(mod_path, hoi4_path)
    # 按文件路径匹配
    norm = os.path.normpath(file_path).replace("\\", "/")
    for bop in defs.values():
        if os.path.normpath(bop["file"]).replace("\\", "/") == norm:
            dlg = BopEditorDialog(bop, mod_path, hoi4_path, parent)
            dlg.exec()
            return True
    # 按 tag 匹配（无文件模式传入实体 key 时也可用）
    tag = os.path.splitext(os.path.basename(file_path))[0]
    bop = defs.get(tag)
    if bop is None:
        return False
    dlg = BopEditorDialog(bop, mod_path, hoi4_path, parent)
    dlg.exec()
    return True
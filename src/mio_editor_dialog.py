"""MIO 编辑器（主对话框，UI/信号槽层）。

视觉：主题与编辑器全局主题一致（theme.py 全局亮色）；
复用游戏自带 MIO 主视觉素材做图片组件（见 mio_ui_theme）：
- 标题栏 = mio_entry_bg 列表横幅底板（左图标位 + 标题 + 动作按钮）
- 头图 = mio_details_background_<type> 详情页插画（按装备类型选变体）

布局：
- 左栏：MIO 组织列表
- 顶部：横幅（MIO 图标选择 + 保存）
- 头图：详情插画 + 组织名/装备类型
- 左侧面板：属性 / 装备加成展示（取自 initial_trait）
- 中部：特质树画布（点击选特质）
- 右侧：特质实体 新增/删除/编辑（含图标选择）
- 底部：方针编辑器入口（主色按钮）
"""

from __future__ import annotations

import os
import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ai_ui_common import EntityListSidebar, file_tooltip
from mio_loader import (
    delete_mio,
    delete_trait,
    duplicate_mio,
    duplicate_trait,
    initial_trait_to_pdx,
    insert_mio,
    insert_trait,
    load_mios,
    rename_mio,
    rename_trait,
    replace_initial_trait,
    replace_mio_fields,
    replace_trait_block,
    trait_to_pdx,
)
from mio_trait_tree import MioTraitTreeView
from mio_ui_theme import (
    BannerWidget,
    IllustrationHeader,
    style_primary_button,
)
from state_build_ops import ensure_file_in_mod
from structure_view import StructureView
from theme import COLORS as C
from write_utils import atomic_write_text


def _shared_translator():
    """返回全局 GuiTranslator 单例（结构视图内联本地化用）；不可用则 None。"""
    try:
        from gui_translator import get_translator
        return get_translator()
    except Exception:
        return None


def _strip_block_wrapper(raw, name):
    """剥掉 `name = { ... }` 外层，返回花括号内部文本。"""
    raw = (raw or "").strip()
    if raw.startswith(name):
        start = raw.find("{")
        if start >= 0:
            depth = 0
            for i in range(start, len(raw)):
                if raw[i] == "{":
                    depth += 1
                elif raw[i] == "}":
                    depth -= 1
                    if depth == 0:
                        return raw[start + 1:i]
            return raw[start + 1:]
    return raw


class InitialTraitDialog(QDialog):
    """初始特质（初始加成）编辑对话框。

    覆盖三种数据形态：equipment_bonus / production_bonus 子块、
    BBA 直接属性键（direct_stats）、以及只读保留块
    （visible / available / organization_modifier / ai_will_do 等）。
    """

    def __init__(self, init, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑初始加成")
        self.resize(560, 560)
        init = init or {}
        self._extra_blocks = list(init.get("extra_blocks") or [])

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("名称（本地化键）"))
        self.name_edit = QLineEdit(init.get("name", ""))
        lay.addWidget(self.name_edit)

        tr = _shared_translator()
        lay.addWidget(QLabel("装备加成（equipment_bonus 内部 · 双击编辑 · 右键添加）"))
        self.equip_view = StructureView(translator=tr)
        self.equip_view.load_text(
            _strip_block_wrapper(init.get("equipment_bonus", ""),
                                 "equipment_bonus").strip())
        self.equip_view.setFixedHeight(130)
        lay.addWidget(self.equip_view)

        lay.addWidget(QLabel("生产加成（production_bonus 内部 · 双击编辑 · 右键添加）"))
        self.prod_view = StructureView(translator=tr)
        self.prod_view.load_text(
            _strip_block_wrapper(init.get("production_bonus", ""),
                                 "production_bonus").strip())
        self.prod_view.setFixedHeight(130)
        lay.addWidget(self.prod_view)

        lay.addWidget(QLabel("直接属性加成（每行一条：键 = 数值）"))
        self.direct_edit = QPlainTextEdit("\n".join(
            "%s = %s" % (k, v)
            for k, v in (init.get("direct_stats") or [])))
        self.direct_edit.setFixedHeight(110)
        lay.addWidget(self.direct_edit)

        kept = [b.splitlines()[0].strip() if b.splitlines() else b
                for b in self._extra_blocks]
        info = QLabel("保留块（写回原样保留）：%s" % (", ".join(kept) or "无"))
        info.setWordWrap(True)
        info.setStyleSheet("color:%s;" % C["text_secondary"])
        lay.addWidget(info)

        btns = QHBoxLayout()
        btns.addStretch(1)
        ok = QPushButton("💾 保存")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        lay.addLayout(btns)

    @staticmethod
    def _parse_direct(text):
        out = []
        for line in (text or "").splitlines():
            m = re.match(r"^\s*([\w\.\-]+)\s*=\s*([^\s#]+)", line)
            if m:
                out.append((m.group(1), m.group(2)))
        return out

    def build_block(self):
        """组装 initial_trait 块文本。"""
        return initial_trait_to_pdx(
            name=self.name_edit.text().strip(),
            equipment_bonus=self.equip_view.to_pdx_text().strip(),
            production_bonus=self.prod_view.to_pdx_text().strip(),
            direct_stats=self._parse_direct(self.direct_edit.toPlainText()),
            extra_blocks=self._extra_blocks,
        )


class MioEditorDialog(QDialog):
    """MIO 编辑器。"""

    def __init__(self, mod_path="", hoi4_path="", parent=None,
                 initial_id=None):
        super().__init__(parent)
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.setWindowTitle("MIO 编辑器")
        self.resize(1280, 780)

        self.mios = {}
        self._current_id = None
        self._trait_token = None
        self._orig_parents_text = ""
        self._trait_parent_blocks = {}
        self._trait_extra_blocks = []
        self._loc = self._make_loc()
        self._gfx_map = self._make_gfx_map()

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.sidebar = EntityListSidebar("MIO 组织", self)
        self.sidebar.set_paths(self.mod_path, self.hoi4_path)
        self.sidebar.currentChanged.connect(self._on_mio_changed)
        self.sidebar.createRequested.connect(self._on_create_mio)
        self.sidebar.duplicateRequested.connect(self._on_dup_mio)
        self.sidebar.renameRequested.connect(self._on_rename_mio)
        self.sidebar.deleteRequested.connect(self._on_delete_mio)
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        right.addWidget(self._build_top_bar())
        self.illus = IllustrationHeader(self.mod_path, self.hoi4_path)
        right.addWidget(self.illus)
        split = QHBoxLayout()
        split.addWidget(self._build_info_panel())
        self.tree = MioTraitTreeView(
            name_of=self._loc, gfx_map=self._gfx_map,
            mod_path=self.mod_path, hoi4_path=self.hoi4_path)
        self.tree.trait_selected.connect(self._on_trait_selected)
        split.addWidget(self.tree, 1)
        split.addWidget(self._build_trait_form())
        right.addLayout(split, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.policy_btn = QPushButton("🎯 方针编辑器…")
        self.policy_btn.clicked.connect(self._open_policies)
        style_primary_button(self.policy_btn)
        bottom.addWidget(self.policy_btn)
        right.addLayout(bottom)
        root.addLayout(right, 1)

        self._reload(initial_id)

    # ---------- 依赖 ----------

    def _make_loc(self):
        self._loc_cache = {"sig": None, "mgr": None}

        def name_of(key):
            try:
                from localization_mgr import LocalizationManager
                sig = (self.hoi4_path or "", self.mod_path or "")
                if self._loc_cache["sig"] != sig:
                    mgr = LocalizationManager()
                    mgr.reload(sig[0], sig[1])
                    self._loc_cache["sig"], self._loc_cache["mgr"] = sig, mgr
                return self._loc_cache["mgr"].get_name(key) or key
            except Exception:
                return key
        return name_of

    def _loc_raw(self, key):
        """本地化查询：命中返回文本，未命中返回空串。"""
        try:
            from localization_mgr import LocalizationManager
            sig = (self.hoi4_path or "", self.mod_path or "")
            if self._loc_cache["sig"] != sig:
                mgr = LocalizationManager()
                mgr.reload(sig[0], sig[1])
                self._loc_cache["sig"], self._loc_cache["mgr"] = sig, mgr
            return self._loc_cache["mgr"].get_name(key) or ""
        except Exception:
            return ""

    def _stat_label(self, key):
        """属性键本地化：loc 链优先，回退内置中文词典，最后原样键名。

        loc 结果需清洗：去掉 £图标 / $模板$ 片段与尾部冒号；
        清洗后为空的候选（纯模板串）跳过。
        """
        upper = key.upper()
        for cand in ("STAT_COMMON_" + upper, "STAT_" + upper, key):
            text = self._loc_raw(cand)
            if text:
                text = re.sub(r"£\S+|\$[^$]*\$", "", text).strip()
                if text:
                    return text.rstrip("：:").strip()
        return _STAT_ZH.get(key, key)

    @staticmethod
    def _bonus_inner(raw):
        """取加成块最外层花括号内部文本（剥外层键/花括号与尾随杂物）。"""
        start = raw.find("{")
        if start < 0:
            return raw
        depth = 0
        for i in range(start, len(raw)):
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1
                if depth == 0:
                    return raw[start + 1:i]
        return raw[start + 1:]

    def _format_bonus(self, raw):
        """把原始加成块渲染为本地化行（属性名 = 值；系数类显示百分比）。"""
        lines = []
        for key, val in _extract_kv(self._bonus_inner(raw or "")):
            shown_val = val
            try:
                num = float(val)
                if key.endswith("_factor") or key == "build_cost_ic":
                    shown_val = "%+d%%" % round(num * 100)
            except ValueError:
                pass
            lines.append("%s = %s" % (self._stat_label(key), shown_val))
        return lines

    def _make_gfx_map(self):
        gfx = {}
        try:
            from gui_translator import get_translator, scan_gfx_folder
            gfx = dict(get_translator().gfx_map)
            # 递归扫描 interface 子目录（MIO 特质/方针图标都在子目录里定义）
            if self.hoi4_path:
                scan_gfx_folder(self.hoi4_path, gfx, recursive=True)
            if self.mod_path:
                scan_gfx_folder(self.mod_path, gfx, recursive=True)
        except Exception:
            pass
        return gfx

    # ---------- 布局 ----------

    def _build_top_bar(self):
        """游戏条目横幅风格标题栏（mio_entry_bg 底板）。"""
        self.banner = BannerWidget(self.mod_path, self.hoi4_path)
        self.title_label = self.banner.title_label
        self.mio_icon_label = self.banner.icon_label
        self.mio_icon_btn = QPushButton("选择 MIO 图标")
        self.mio_icon_btn.clicked.connect(self._pick_mio_icon)
        self.name_loc_btn = QPushButton("本地化名称…")
        self.name_loc_btn.clicked.connect(self._edit_mio_name)
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self._on_save_mio)
        row = self.banner.layout()
        row.addWidget(self.mio_icon_btn)
        row.addWidget(self.name_loc_btn)
        row.addWidget(self.save_btn)
        return self.banner

    def _build_info_panel(self):
        host = QVBoxLayout()
        host.setContentsMargins(8, 8, 8, 8)
        host.setSpacing(6)
        title = QLabel("属性与装备加成")
        title.setStyleSheet("color:%s; font-weight:bold;" % C["accent"])
        host.addWidget(title)
        self.info_label = QLabel("—")
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.info_label.setStyleSheet(
            "color:%s; background:transparent;" % C["text_secondary"])
        host.addWidget(self.info_label, 1)
        self.init_edit_btn = QPushButton("✎ 编辑初始加成")
        self.init_edit_btn.clicked.connect(self._edit_initial_trait)
        host.addWidget(self.init_edit_btn)
        panel = QWidget()
        panel.setProperty("class", "card")
        panel.setFixedWidth(300)
        panel.setLayout(host)
        return panel

    def _build_trait_form(self):
        form = QVBoxLayout()
        form.setContentsMargins(8, 8, 8, 8)
        form.setSpacing(6)
        title = QLabel("特质编辑")
        title.setStyleSheet("color:%s; font-weight:bold;" % C["accent"])
        form.addWidget(title)
        self.trait_label = QLabel("—（点击左侧树节点选择）")
        self.trait_label.setStyleSheet(
            "color:%s; background:transparent;" % C["text_secondary"])
        form.addWidget(self.trait_label)

        self.token_edit = QLineEdit()
        self.token_edit.setPlaceholderText("token")
        form.addWidget(self._field_row("token", self.token_edit))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("name（本地化键）")
        form.addWidget(self._field_row("名称", self.name_edit))
        self.icon_row = self._field_row("图标", QLineEdit())
        self.icon_edit = self.icon_row._inner_widget
        self.icon_btn = QPushButton("🖼 选图标")
        self.icon_btn.clicked.connect(self._pick_trait_icon)
        self.icon_row._inner_layout.addWidget(self.icon_btn)
        form.addWidget(self.icon_row)
        self.x_edit = QLineEdit()
        self.x_edit.setPlaceholderText("x")
        self.y_edit = QLineEdit()
        self.y_edit.setPlaceholderText("y")
        xy = QHBoxLayout()
        xy.addWidget(QLabel("位置 x"))
        xy.addWidget(self.x_edit)
        xy.addWidget(QLabel("y"))
        xy.addWidget(self.y_edit)
        form.addLayout(xy)
        self.rel_edit = QLineEdit()
        self.rel_edit.setPlaceholderText("父特质 token")
        form.addWidget(self._field_row("相对父", self.rel_edit))
        self.parents_edit = QLineEdit()
        self.parents_edit.setPlaceholderText("空格分隔的父特质列表")
        form.addWidget(self._field_row("父列表", self.parents_edit))
        self.equip_view = StructureView(translator=_shared_translator())
        self.equip_view.setFixedHeight(150)
        form.addWidget(self._field_row(
            "装备加成（结构编辑：双击改值 · 右键加条目）", self.equip_view))
        self.prod_view = StructureView(translator=_shared_translator())
        self.prod_view.setFixedHeight(130)
        form.addWidget(self._field_row(
            "生产加成（结构编辑）", self.prod_view))
        self.direct_edit = QPlainTextEdit()
        self.direct_edit.setPlaceholderText("直接属性（BBA，每行：键 = 值）")
        self.direct_edit.setFixedHeight(70)
        form.addWidget(self._field_row("直接属性", self.direct_edit))

        btns = QHBoxLayout()
        for label, fn in (("💾 存特质", self._on_save_trait),
                          ("＋新增", self._on_add_trait),
                          ("⧉复制", self._on_dup_trait),
                          ("🗑删除", self._on_delete_trait)):
            b = QPushButton(label)
            b.clicked.connect(fn)
            btns.addWidget(b)
        form.addLayout(btns)
        form.addStretch(1)
        panel = QWidget()
        panel.setProperty("class", "card")
        panel.setFixedWidth(420)
        panel.setLayout(form)
        return panel

    def _field_row(self, label, widget):
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lab = QLabel(label)
        lab.setStyleSheet(
            "color:%s; font-weight:bold; background:transparent;"
            % C["text_secondary"])
        lay.addWidget(lab)
        lay.addWidget(widget)
        container._inner_widget = widget
        container._inner_layout = lay
        return container

    # ---------- 数据流 ----------

    def _reload(self, select_id=None):
        self.mios = load_mios(self.mod_path, self.hoi4_path)
        labels = [(mid, self._loc_name(mid),
                   file_tooltip(m, self.mod_path, self.hoi4_path)
                   or self._loc_name(mid))
                  for mid, m in self.mios.items()]
        self.sidebar.set_entities(labels)
        if select_id:
            self.sidebar.set_current(select_id)
        elif self.sidebar.list.count():
            self.sidebar.set_current(
                self.sidebar.list.item(0).data(Qt.ItemDataRole.UserRole))

    def _loc_name(self, key):
        """组织/方针显示名：本地化命中用译文，否则原 id。"""
        try:
            return self._loc_raw(key) or key
        except Exception:
            return key

    def _current_mio(self):
        return self.mios.get(self._current_id)

    def _on_mio_changed(self, mio_id):
        self._current_id = mio_id
        mio = self.mios.get(mio_id)
        loc_name = self._loc_name(mio_id) if mio_id else ""
        if loc_name and loc_name != mio_id:
            self.title_label.setText("%s（%s）" % (loc_name, mio_id))
        else:
            self.title_label.setText(mio_id or "—")
        self._trait_token = None
        self._clear_trait_form()
        if not mio:
            self.tree.set_mio(None)
            self.illus.set_org("", [], None)
            self.info_label.setText("—")
            self.mio_icon_label.setText("🖼")
            return
        self.tree.set_mio(mio)
        self.illus.set_org(mio_id, mio.get("equipment_type") or [],
                           loc=self._loc)
        self._refresh_info(mio)
        self._refresh_mio_icon(mio)

    def _refresh_info(self, mio):
        init = mio.get("initial_trait") or {}
        lines = []
        if init.get("name"):
            lines.append("初始特质：%s" % self._loc(init["name"]))
        for label, raw in (("装备加成", init.get("equipment_bonus") or ""),
                           ("生产加成", init.get("production_bonus") or "")):
            if not raw:
                continue
            lines.append("· %s：" % label)
            lines.extend("    %s" % ln for ln in self._format_bonus(raw))
        direct = init.get("direct_stats") or []
        if direct:
            lines.append("· 直接属性加成：")
            for k, v in direct:
                try:
                    shown = v
                    num = float(v)
                    if k.endswith("_factor") or k == "build_cost_ic":
                        shown = "%+d%%" % round(num * 100)
                except ValueError:
                    shown = v
                lines.append("    %s = %s" % (self._stat_label(k), shown))
        self.info_label.setText("\n".join(lines) or "（无 initial_trait 加成）")

    def _edit_initial_trait(self):
        mio = self._current_mio()
        if not mio:
            return
        dlg = InitialTraitDialog(mio.get("initial_trait") or {}, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        block = dlg.build_block()

        def transform(content):
            return replace_initial_trait(content, mio["id"], block)
        if self._write_rel(mio.get("rel", ""), transform):
            mio["initial_trait"] = None  # 触发重载
            self._reload(self._current_id)
            QMessageBox.information(self, "已保存", "已保存初始加成")

    # ---------- 组织实体 CRUD ----------

    def _target_rel(self):
        mio = self._current_mio()
        if mio and mio.get("rel"):
            return mio["rel"]
        for m in self.mios.values():
            if m.get("rel"):
                return m["rel"]
        return ""

    def _on_create_mio(self):
        mio_id, ok = QInputDialog.getText(self, "新建 MIO 组织", "新组织 id：")
        if not ok or not mio_id.strip():
            return
        mio_id = mio_id.strip()
        if mio_id in self.mios:
            QMessageBox.warning(self, "新建失败", "组织 id 已存在：%s" % mio_id)
            return
        template = ("%s = {\n\ticon = GFX_idea_generic_tank_manufacturer_1\n"
                    "\tequipment_type = { infantry_equipment }\n}" % mio_id)
        after = self._current_id or None
        rel = self._target_rel()
        if rel:
            def transform(content):
                return insert_mio(content, mio_id, template, after_id=after)
            if not self._write_rel(rel, transform):
                return
        else:
            if not self.mod_path:
                QMessageBox.warning(self, "新建失败", "未打开 mod")
                return
            d = os.path.join(self.mod_path, "common",
                             "military_industrial_organization",
                             "organizations")
            os.makedirs(d, exist_ok=True)
            try:
                atomic_write_text(os.path.join(d, "zzz_custom.txt"),
                                  template + "\n")
            except Exception as e:
                QMessageBox.warning(self, "新建失败", "写入失败：%s" % e)
                return
        self._reload(mio_id)

    def _on_dup_mio(self):
        if not self._current_id:
            return
        new_id, ok = QInputDialog.getText(
            self, "复制组织", "新组织 id：", text=self._current_id + "_copy")
        if not ok or not new_id.strip():
            return
        new_id = new_id.strip()
        if new_id in self.mios:
            QMessageBox.warning(self, "复制失败", "组织 id 已存在：%s" % new_id)
            return

        def transform(content):
            return duplicate_mio(content, self._current_id, new_id)
        if self._write_rel(self._target_rel(), transform):
            self._reload(new_id)

    def _on_rename_mio(self):
        if not self._current_id:
            return
        new_id, ok = QInputDialog.getText(
            self, "重命名组织", "新组织 id：", text=self._current_id)
        if not ok or not new_id.strip() or new_id.strip() == self._current_id:
            return
        new_id = new_id.strip()
        if new_id in self.mios:
            QMessageBox.warning(self, "重命名失败", "组织 id 已存在：%s" % new_id)
            return

        def transform(content):
            return rename_mio(content, self._current_id, new_id)
        if self._write_rel(self._target_rel(), transform):
            self._reload(new_id)

    def _on_delete_mio(self):
        if not self._current_id:
            return
        ret = QMessageBox.question(
            self, "删除组织", "确定删除组织 %s ？\n（将删除其在文件中的定义块）"
            % self._current_id,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return

        def transform(content):
            return delete_mio(content, self._current_id)
        if self._write_rel(self._target_rel(), transform):
            self._reload()

    # ---------- 名称本地化 ----------

    def _edit_mio_name(self):
        mio = self._current_mio()
        if not mio:
            return
        if not self.mod_path:
            QMessageBox.warning(self, "无法保存", "未打开 mod，无法写入本地化")
            return
        from translation_editor import TranslationEditor
        mod_loc = os.path.join(self.mod_path, "localisation", "simp_chinese")
        game_loc = os.path.join(self.hoi4_path, "localisation", "simp_chinese")
        os.makedirs(mod_loc, exist_ok=True)
        ed = TranslationEditor(game_loc, mod_loc, "mio_mod_l_simp_chinese.yml")
        ed.reload()
        cur = ed.get_effective(mio["id"]) or self._loc_raw(mio["id"]) or ""
        text, ok = QInputDialog.getText(self, "本地化名称",
                                        "中文名称（%s）：" % mio["id"], text=cur)
        if not ok:
            return
        text = text.strip()
        if not text or text == cur:
            return
        if not ed.save_name(mio["id"], text):
            QMessageBox.warning(self, "保存失败", "写入本地化文件失败")
            return
        self._loc_cache["sig"] = None  # 强制重载本地化缓存
        self._reload(self._current_id)
        QMessageBox.information(self, "已保存", "已保存本地化名称：%s" % text)

    def _refresh_mio_icon(self, mio):
        icon = (mio or {}).get("icon", "")
        self.mio_icon_label.setToolTip(icon)
        try:
            from icon_resolver import resolve_pixmap
            pm = resolve_pixmap(icon, gfx_map=self._gfx_map,
                                mod_path=self.mod_path,
                                hoi4_path=self.hoi4_path)
            if not pm.isNull():
                pm = pm.scaledToHeight(44, Qt.TransformationMode.SmoothTransformation)
                self.mio_icon_label.setPixmap(pm)
                return
        except Exception:
            pass
        self.mio_icon_label.setText("🖼")

    # ---------- 特质表单 ----------

    def _clear_trait_form(self):
        for w in (self.token_edit, self.name_edit, self.icon_edit,
                  self.x_edit, self.y_edit, self.rel_edit, self.parents_edit):
            w.setText("")
        self.equip_view.load_text("")
        self.prod_view.load_text("")
        self.direct_edit.setPlainText("")
        self.trait_label.setText("—（点击左侧树节点选择）")
        self._orig_parents_text = ""
        self._trait_parent_blocks = {}
        self._trait_extra_blocks = []

    def _on_trait_selected(self, token):
        mio = self._current_mio()
        if not mio:
            return
        for t in mio.get("traits", []) or []:
            if t.get("token") == token:
                self._trait_token = token
                self.trait_label.setText("编辑特质：%s" % self._loc(token))
                self.token_edit.setText(t.get("token", ""))
                self.name_edit.setText(t.get("name", ""))
                self.icon_edit.setText(t.get("icon", ""))
                self.x_edit.setText(str(t.get("x", 0)))
                self.y_edit.setText(str(t.get("y", 0)))
                self.rel_edit.setText(t.get("relative_position_id", ""))
                self.parents_edit.setText(" ".join(t.get("parents") or []))
                self.equip_view.load_text(t.get("equipment_bonus", ""))
                self.prod_view.load_text(t.get("production_bonus", ""))
                self.direct_edit.setPlainText("\n".join(
                    "%s = %s" % (k, v)
                    for k, v in (t.get("direct_stats") or [])))
                self._orig_parents_text = " ".join(t.get("parents") or [])
                self._trait_parent_blocks = dict(t.get("parent_blocks") or {})
                self._trait_extra_blocks = list(t.get("extra_blocks") or [])
                break

    def _form_trait(self, token):
        try:
            x = int(self.x_edit.text() or "0")
        except ValueError:
            x = 0
        try:
            y = int(self.y_edit.text() or "0")
        except ValueError:
            y = 0
        current_parents = [p for p in self.parents_edit.text().split() if p]
        current_parents_text = " ".join(current_parents)
        extra_blocks = list(self._trait_extra_blocks or [])
        parents = current_parents
        if current_parents_text == (self._orig_parents_text or ""):
            # 父列表未修改：保留原始 any_parent/all_parents 块，避免类型被改写
            for blocks in (self._trait_parent_blocks or {}).values():
                extra_blocks.extend(blocks)
            parents = []
        return trait_to_pdx(
            token,
            self.name_edit.text().strip() or token,
            self.icon_edit.text().strip(),
            x, y,
            self.rel_edit.text().strip(),
            parents,
            self.equip_view.to_pdx_text().strip(),
            self.prod_view.to_pdx_text().strip(),
            extra_blocks=extra_blocks,
            direct_stats=InitialTraitDialog._parse_direct(
                self.direct_edit.toPlainText()),
        )

    # ---------- 写文件 ----------

    def _write_rel(self, rel, transform, expect_change=True):
        if not rel:
            return False
        mod_fp, _copied = ensure_file_in_mod(self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位文件")
            return False
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        new_content = transform(content)
        if expect_change and new_content == content:
            QMessageBox.warning(
                self, "保存未生效",
                "内容未变化：目标块可能继承自 include 组织，"
                "在本文件中没有可写的定义块。")
            return False
        try:
            atomic_write_text(mod_fp, new_content)
        except Exception as e:
            QMessageBox.warning(self, "写入失败", "写入失败：%s" % e)
            return False
        return True

    # ---------- 保存 / CRUD ----------

    def _on_save_mio(self):
        mio = self._current_mio()
        if not mio:
            return
        icon = self.mio_icon_label.toolTip() or mio.get("icon", "")
        def transform(content):
            return replace_mio_fields(content, mio["id"], {"icon": icon})
        if self._write_rel(mio.get("rel", ""), transform):
            mio["icon"] = icon
            QMessageBox.information(self, "已保存", "已保存 %s" % mio["id"])

    def _on_save_trait(self):
        mio = self._current_mio()
        if not mio or not self._trait_token:
            return
        old_token = self._trait_token
        new_token = self.token_edit.text().strip() or old_token
        existing = {t.get("token") for t in mio.get("traits", []) or []}
        if new_token != old_token and new_token in existing:
            QMessageBox.warning(self, "保存失败", "特质 token 已存在：%s" % new_token)
            return
        new_pdx = self._form_trait(new_token)
        def transform(content):
            if new_token != old_token:
                content = rename_trait(content, mio["id"], old_token, new_token)
            return replace_trait_block(content, mio["id"], new_token, new_pdx)
        if self._write_rel(mio.get("rel", ""), transform):
            self._reload(self._current_id)
            self._on_trait_selected(new_token)
            QMessageBox.information(self, "已保存", "已保存特质 %s" % new_token)

    def _on_add_trait(self):
        mio = self._current_mio()
        if not mio:
            return
        token, ok = QInputDialog.getText(self, "新增特质", "新特质 token：")
        if not ok or not token.strip():
            return
        token = token.strip()
        if token in {t.get("token") for t in mio.get("traits", []) or []}:
            QMessageBox.warning(self, "新增失败", "特质 token 已存在：%s" % token)
            return
        after = self._trait_token or None
        def transform(content):
            return insert_trait(content, mio["id"], token, after_token=after)
        if self._write_rel(mio.get("rel", ""), transform):
            self._reload(self._current_id)
            self._on_trait_selected(token)

    def _on_dup_trait(self):
        mio = self._current_mio()
        if not mio or not self._trait_token:
            return
        new_token, ok = QInputDialog.getText(
            self, "复制特质", "新特质 token：", text=self._trait_token + "_copy")
        if not ok or not new_token.strip():
            return
        new_token = new_token.strip()
        if new_token in {t.get("token") for t in mio.get("traits", []) or []}:
            QMessageBox.warning(self, "复制失败", "特质 token 已存在：%s" % new_token)
            return
        def transform(content):
            return duplicate_trait(content, mio["id"], self._trait_token, new_token)
        if self._write_rel(mio.get("rel", ""), transform):
            self._reload(self._current_id)
            self._on_trait_selected(new_token)

    def _on_delete_trait(self):
        mio = self._current_mio()
        if not mio or not self._trait_token:
            return
        token = self._trait_token
        ret = QMessageBox.question(
            self, "删除特质", "确定删除特质 %s ？" % token,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        def transform(content):
            return delete_trait(content, mio["id"], token)
        if self._write_rel(mio.get("rel", ""), transform):
            self._reload(self._current_id)

    # ---------- 图标选择 ----------

    def _pick_icon(self, current, prefix, target_widget):
        from icon_picker_dialog import IconPickerDialog
        dlg = IconPickerDialog(
            self._gfx_map, parent=self, prefix=prefix,
            current_icon=current)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = dlg.get_selected_icon()
            if name:
                target_widget.setText(name)

    def _pick_mio_icon(self):
        mio = self._current_mio()
        if not mio:
            return
        self._pick_icon(mio.get("icon", ""), "GFX_", self.mio_icon_label)
        if self.mio_icon_label.text():
            mio["icon"] = self.mio_icon_label.text()
        self.mio_icon_label.setToolTip(mio.get("icon", ""))
        self._refresh_mio_icon(mio)

    def _pick_trait_icon(self):
        self._pick_icon(self.icon_edit.text().strip(), "GFX_", self.icon_edit)

    # ---------- 方针入口 ----------

    def _open_policies(self):
        from mio_policy_editor_dialog import MioPolicyEditorDialog
        dlg = MioPolicyEditorDialog(self.mod_path, self.hoi4_path,
                                    parent=self)
        dlg.show()


def _extract_kv(raw):
    """从原始加成块提取 key = value 行（浅层）。"""
    out = []
    for line in raw.splitlines():
        m = re.match(r"^\s*([\w\.\-]+)\s*=\s*([^\s#]+)", line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


# HOI4 装备/生产属性内置中文名（游戏 loc 缺失时的兜底；
# 命中 loc 的 STAT_COMMON_/STAT_ 键优先）
_STAT_ZH = {
    "build_cost_ic": "生产花费",
    "soft_attack": "软攻击",
    "hard_attack": "硬攻击",
    "ap_attack": "穿甲攻击",
    "armor_value": "装甲厚度",
    "defense": "防御",
    "breakthrough": "突破",
    "hardness": "相对厚度",
    "reliability": "可靠性",
    "maximum_speed": "最大速度",
    "fuel_consumption": "燃油使用",
    "fuel_consumption_factor": "燃油使用",
    "air_agility": "机动",
    "air_attack": "空对空攻击",
    "air_defence": "空中防御",
    "air_bombing": "战略轰炸",
    "air_ground_attack": "对地攻击",
    "air_range": "航程",
    "air_superiority": "制空能力",
    "anti_air_attack": "对空攻击",
    "anti_air": "对空攻击",
    "carrier_size": "搭载量",
    "naval_speed": "海军速度",
    "naval_range": "海军航程",
    "naval_hit_chance": "海军命中率",
    "naval_heavy_gun_hit_chance_factor": "重炮命中率",
    "naval_light_gun_hit_chance_factor": "轻炮命中率",
    "naval_torpedo_hit_chance_factor": "鱼雷命中率",
    "naval_torpedo_damage_reduction_factor": "鱼雷伤害减免",
    "naval_torpedo_enemy_critical_chance_factor": "敌方鱼雷暴击几率",
    "naval_strike_attack": "海军打击攻击",
    "naval_strike_targetting": "海军打击瞄准",
    "naval_weather_penalty_factor": "海军天气惩罚",
    "patrol_coordination": "巡逻协同",
    "mines_planting": "布雷能力",
    "mines_sweeping": "扫雷能力",
    "sub_attack": "潜艇攻击",
    "sub_detection": "潜艇探测",
    "sub_visibility": "潜艇可见度",
    "surface_detection": "水面探测",
    "surface_visibility": "水面可见度",
    "torpedo_attack": "鱼雷攻击",
    "hg_attack": "重炮攻击",
    "hg_armor_piercing": "重炮穿甲",
    "lg_attack": "轻炮攻击",
    "lg_armor_piercing": "轻炮穿甲",
    "production_capacity_factor": "生产容量",
    "production_conversion_speed_factor": "改装速度",
    "production_cost_factor": "生产花费",
    "production_efficiency_cap_factor": "生产效率上限",
    "production_efficiency_gain_factor": "生产效率增长",
    "production_resource_need_factor": "资源需求",
    "production_resource_penalty_factor": "资源惩罚",
    "conversion_cost_ic": "改装花费",
    "conversion_speed": "改装速度",
    "xp_cost": "经验消耗",
}


def open_mio_editor(file_path="", mod_path="", hoi4_path="",
                    entity_id=None, parent=None):
    """入口：加载并显示 MIO 编辑器（非模态）。"""
    dlg = MioEditorDialog(mod_path, hoi4_path, parent=parent,
                          initial_id=entity_id)
    dlg.show()
    return dlg

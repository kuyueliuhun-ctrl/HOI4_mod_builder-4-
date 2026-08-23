"""工作台式界面模块

仿 hagane.works 工作台设计：
- 左侧内容类型块列表（国策树/事件/决议/理念/科技/角色/本地化/通用）
- 右侧文件块状卡片列表（显示文件名/关联国家标签/相对路径）
- 点击卡片块状打开：
  - 国策树 → 复用现有设计视图（FocusView 渲染）
  - 图标型内容 → 在右侧国策组件（FocusView）中展示各实体图标
  - 其余类型 → 复用 GenericTreeEditor（树形编辑器）

界面模式通过主窗口菜单切换（经典文件树 / 工作台）。
"""

import os
import re

from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QLineEdit, QPushButton, QMessageBox,
    QMenu, QAbstractItemView, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal


# 有专门制作/编辑功能的类型（放在类型列表上方；其余为通用树形编辑）
from content_types import (
    SPECIAL_TYPE_KEYS,
    AI_TYPES,
    CONTENT_TYPES,
    TYPE_ROOT_LABELS,
    TOP_LEVEL_ENTITY_TYPES,
    ICON_RULES,
)
from entity_scanner import EntityScanner


class WorkbenchDock(QDockWidget):
    """工作台停靠面板 - 仿网站工作台式界面。

    信号：
        focus_file_selected(str): 选择国策树文件（主窗口加载设计视图）
        generic_file_selected(str, object): 选择其他文件（主窗口打开树编辑器，携带实体id可选）
        entity_gallery_requested(str, str): 图标型文件（主窗口在右侧国策组件中展示实体图标）
        entity_gallery_nofile_requested(str, list): 无文件模式实体（主窗口在右侧展示跨文件实体画廊）
        nofile_mode_changed(bool): 无文件模式切换（主窗口同步工具栏动作并持久化）
    """

    focus_file_selected = pyqtSignal(str)
    generic_file_selected = pyqtSignal(str, object)
    entity_gallery_requested = pyqtSignal(str, str)
    entity_gallery_nofile_requested = pyqtSignal(str, list)
    nofile_mode_changed = pyqtSignal(bool)
    country_changed = pyqtSignal(str)
    # 无文件模式国策树绘制请求（国家tag或""，国策文件列表）
    focus_tree_nofile_requested = pyqtSignal(str, list)
    # 科技树画布绘制请求（与国策树同一画布）
    tech_file_selected = pyqtSignal(str)
    tech_tree_nofile_requested = pyqtSignal(list)

    def __init__(self, mod_path="", parent=None):
        super().__init__("工作台", parent)
        self.mod_path = mod_path
        self._current_type = "focus"
        self._nofile = False
        self._nofile_entities = []
        # 无文件模式「当前国家」筛选；None 表示全部国家
        self._current_country = None

        self._build_ui()
        self.setObjectName("workbenchDock")

    def set_nofile_mode(self, nofile):
        """切换无文件模式（实体浏览）与文件模式（文件列表）。

        无文件模式下隐藏右侧文件/实体列表框，仅保留左侧类型列表，
        切换类型后自动在右侧图形化展示该类型全部实体。
        """
        nofile = bool(nofile)
        if nofile == self._nofile:
            return
        self._nofile = nofile
        if self._nofile:
            self.title_label.setText("工作台 · 无文件模式")
            self.search_edit.setPlaceholderText("搜索实体（id / 中文名 / 国家tag）…")
        else:
            self.title_label.setText("工作台")
            self.search_edit.setPlaceholderText("搜索文件…")
        self.search_bar.setVisible(True)
        self.file_list.setVisible(not nofile)
        self.country_bar.setVisible(nofile)
        self.nofile_mode_changed.emit(nofile)
        self._refresh()

    def is_nofile(self):
        """返回当前是否处于无文件模式。"""
        return self._nofile

    def _build_ui(self):
        """构建工作台 UI：左侧类型列表 + 右侧文件块列表。"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        # ── 标题行 ──
        title_row = QHBoxLayout()
        self.title_label = QLabel("工作台")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_row.addWidget(self.title_label)
        title_row.addStretch()
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self._refresh)
        title_row.addWidget(self.refresh_btn)
        layout.addLayout(title_row)

        # ── 无文件模式国家栏（仅在无文件模式显示，置于内容区下方） ──
        self.country_bar = QWidget()
        country_row = QHBoxLayout(self.country_bar)
        country_row.setContentsMargins(0, 4, 0, 0)
        self.country_label = QLabel("当前国家：全部")
        self.country_label.setStyleSheet("font-weight: bold;")
        country_row.addWidget(self.country_label)
        self.nofile_stats_label = QLabel("")
        self.nofile_stats_label.setStyleSheet("color: #5d6b7a;")
        country_row.addWidget(self.nofile_stats_label)
        country_row.addStretch()
        self.select_country_btn = QPushButton("🔍 选择国家…")
        self.select_country_btn.setToolTip("仅切换当前浏览国家（不修改任何文件）")
        self.select_country_btn.clicked.connect(self._on_select_country)
        country_row.addWidget(self.select_country_btn)
        self.country_setup_btn = QPushButton("🌐 国家设置（复制/创建）…")
        self.country_setup_btn.setToolTip("显式写操作：复制原版或创建空覆盖文件到 mod")
        self.country_setup_btn.clicked.connect(self._on_country_setup)
        country_row.addWidget(self.country_setup_btn)

        # ── 内容区：类型列表（左） + 文件块（右） ──
        content_row = QHBoxLayout()

        # 左侧：内容类型块
        type_box = QVBoxLayout()
        type_box.addWidget(QLabel("内容类型"))
        self.type_list = QListWidget()
        self.type_list.setFixedWidth(230)
        self.type_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        type_font = self.type_list.font()
        type_font.setPointSize(12)
        self.type_list.setFont(type_font)
        self.type_list.setStyleSheet(
            "QListWidget::item { padding: 6px 4px; }")
        # 专门功能类型（国策/科技/初始部队）置顶；其余通用类型放分界线下方
        def _type_text(key, name, icon, tpl_type):
            text = f"{icon} {name}"
            if tpl_type is None and key != "generic":
                text += "（无新建模板）"
            return text

        def _add_type_item(entry):
            key, name, icon, _folders, tpl_type, _ext = entry
            item = QListWidgetItem(_type_text(key, name, icon, tpl_type))
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.type_list.addItem(item)

        special = [e for e in CONTENT_TYPES if e[0] in SPECIAL_TYPE_KEYS]
        others = [e for e in CONTENT_TYPES if e[0] not in SPECIAL_TYPE_KEYS]
        for entry in special:
            _add_type_item(entry)
        # 分界线（不可选）
        sep = QListWidgetItem("────────── 通用类型（树形编辑）──────────")
        sep.setFlags(Qt.ItemFlag.NoItemFlags)
        sep.setForeground(Qt.GlobalColor.gray)
        self.type_list.addItem(sep)
        for entry in others:
            _add_type_item(entry)
        self.type_list.itemClicked.connect(self._on_type_clicked)
        self.type_list.setCurrentRow(0)
        type_box.addWidget(self.type_list)
        content_row.addLayout(type_box)

        # 右侧：文件/实体列表
        right_box = QVBoxLayout()
        self.search_bar = QWidget()
        search_row = QHBoxLayout(self.search_bar)
        search_row.setContentsMargins(0, 0, 0, 0)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索文件…")
        self.search_edit.textChanged.connect(self._refresh)
        search_row.addWidget(self.search_edit)
        right_box.addWidget(self.search_bar)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        file_font = self.file_list.font()
        file_font.setPointSize(11)
        self.file_list.setFont(file_font)
        self.file_list.setStyleSheet(
            "QListWidget::item { padding: 4px 2px; }")
        self.file_list.itemDoubleClicked.connect(self._on_file_double_clicked)
        self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self._show_file_menu)
        right_box.addWidget(self.file_list)
        content_row.addLayout(right_box)

        layout.addLayout(content_row)

        # 国家栏置于内容区下方（无文件模式显示）
        layout.addWidget(self.country_bar)
        self.country_bar.setVisible(False)

        self.setWidget(container)

        self._refresh()

    # ---------- 文件扫描 ----------

    # 国家 tag：2-4 位大写字母/数字，至少含一个字母
    _TAG_RE = re.compile(r'(?=[A-Z0-9]*[A-Z])[A-Z0-9]{2,4}')

    def _refresh(self):
        """按当前模式刷新右侧列表（文件模式 / 无文件模式）。

        无文件模式下收集实体后自动向右侧画廊推送（含关键词/国家筛选）；
        国策类型不推送画廊，而是发出国策树绘制请求（展示当前设计国家）。
        """
        if self._nofile:
            if self._current_type == "focus":
                self._emit_focus_tree_nofile()
                return
            if self._current_type == "tech":
                self._emit_tech_tree_nofile()
                return
            self._refresh_entities()
            self._update_nofile_stats()
            # 始终推送（0 实体也推送，画廊显示「无实体」，避免残留上一类型内容）
            self.entity_gallery_nofile_requested.emit(
                self._current_type, list(self._filtered_entities()))
        else:
            self._refresh_files()

    def _emit_focus_tree_nofile(self):
        """无文件模式：请求绘制国策树。

        未设置「当前国家」时先弹窗选择国家（只绘制一个国家，不画全部国家树）；
        选定后绘制该国全部国策文件的合并树。
        """
        files = self._collect_files()
        if not files:
            self._update_nofile_stats()
            return
        tag = self._current_country
        if not tag:
            tag = self._ask_focus_country(files)
            if not tag:
                # 用户取消：清空右侧场景（不绘制任何国家树）
                self.focus_tree_nofile_requested.emit("", [])
                return
            self.set_current_country(tag)
            return  # set_current_country 触发 _refresh，重新进入本方法并绘制
        kept = [fp for fp in files
                if tag in self._detect_country_tags(fp, self._read_file(fp))]
        self.focus_tree_nofile_requested.emit(tag, list(kept))

    def _emit_tech_tree_nofile(self):
        """无文件模式：请求绘制科技树（与国策树同一画布，跨文件合并全部科技）。"""
        files = self._collect_files()
        if not files:
            self._update_nofile_stats()
            return
        self.tech_tree_nofile_requested.emit(list(files))

    def _ask_focus_country(self, files):
        """弹窗选择要设计国策树的国家（从国策文件检测 tag）。"""
        from PyQt6.QtWidgets import QInputDialog
        tags = set()
        for fp in files:
            for t in self._detect_country_tags(fp, self._read_file(fp)):
                tags.add(t)
        if not tags:
            return None
        items = sorted(tags)
        item, ok = QInputDialog.getItem(
            self, "选择国家", "请选择要设计国策树的国家：", items, 0, False)
        if ok and item:
            return item
        return None

    def _collect_entities(self):
        """无文件模式：全局扫描当前类型的所有实体（不按下级目录/文件区分）。

        返回 list[dict]：
            {name, key, icon, range, file, tags:[国家tag]}

        有对应 ICON_RULES 的类型用图标规则提取实体（含 icon）；
        角色文件特殊处理（TAG 分组层下沉为角色）；
        其余类型提取顶层直接子块，无子块的文件视为单个实体（文件级）。
        """
        if not self.mod_path or not os.path.isdir(self.mod_path):
            return []

        key = self._current_type
        folders, exts = self._type_folders_ext(key)
        entities = []
        seen = set()
        for rel in folders:
            base = self.mod_path if rel == "." else os.path.join(self.mod_path, rel)
            if not os.path.isdir(base):
                continue
            for root, _dirs, names in os.walk(base):
                for name in sorted(names):
                    if not self._ext_matches(name, exts):
                        continue
                    fp = os.path.join(root, name)
                    if not os.path.isfile(fp):
                        continue
                    real = os.path.realpath(fp)
                    if real in seen:
                        continue
                    seen.add(real)
                    content = self._read_file(fp)
                    if not content:
                        continue
                    entities.extend(self._entities_for_file(key, content, fp))
        return self._filter_entities(entities)

    def _current_country_tags(self):
        """返回当前国家筛选对应的 tag 集合；None 表示全部。"""
        return {self._current_country} if self._current_country else None

    def _filter_entities(self, entities):
        """按「当前国家」过滤实体列表（tags 首项匹配）。"""
        if not self._current_country:
            return entities
        tag = self._current_country
        return [e for e in entities if (e.get("tags") or [""])[0] == tag]

    def _filtered_entities(self):
        """返回当前画廊应展示的实体（应用国家筛选 + 关键词筛选）。"""
        entities = self._nofile_entities
        if self._current_country:
            entities = self._filter_entities(entities)
        keyword = self.search_edit.text().strip().lower()
        if keyword:
            kw = keyword
            out = []
            for e in entities:
                name = e.get("name") or ""
                hay = f"{name} {e.get('key', '')} {' '.join(e.get('tags', []))}".lower()
                if kw in hay:
                    out.append(e)
            entities = out
        return list(entities)

    def _update_nofile_stats(self):
        """更新无文件模式统计标签（实体数 / 源文件数 / 筛选后数量）。"""
        total = len(self._nofile_entities)
        files = len({e.get("file", "") for e in self._nofile_entities if e.get("file")})
        shown = len(self._filtered_entities())
        text = f"共 {total} 实体 / {files} 文件"
        if shown != total:
            text += f"（显示 {shown}）"
        self.nofile_stats_label.setText(text)

    @classmethod
    def _collect_file_entities(cls, content_type, content, fp):
        return EntityScanner._collect_file_entities(content_type, content, fp)
    @classmethod
    def _extract_top_entities(cls, content):
        return EntityScanner._extract_top_entities(content)
    @classmethod
    def _extract_character_entities(cls, content, file_tags):
        return EntityScanner._extract_character_entities(content, file_tags)
    @classmethod
    def _extract_generic_entities(cls, content):
        return EntityScanner._extract_generic_entities(content)
    @classmethod
    def _make_generic_entity(cls, content, start, end, key):
        return EntityScanner._make_generic_entity(content, start, end, key)
    @classmethod
    def _quick_focus_scan(cls, content):
        return EntityScanner._quick_focus_scan(content)
    @staticmethod
    def _pair_block(content, brace_pos):
        return EntityScanner._pair_block(content, brace_pos)
    @staticmethod
    def _tech_node_from_block(tid, block):
        return EntityScanner._tech_node_from_block(tid, block)
    @classmethod
    def _quick_tech_scan(cls, content):
        return EntityScanner._quick_tech_scan(content)
    def _refresh_entities(self):
        """刷新无文件模式实体数据（右侧列表框在无文件模式下隐藏，仅收集实体供画廊使用）。

        有国家 tag 的实体按国家分组，无国家的平铺。
        """
        self._nofile_entities = self._collect_entities()
        if not self.file_list.isVisible():
            return
        self.file_list.clear()
        keyword = self.search_edit.text().strip().lower()

        grouped = {}
        no_tag = []
        for e in self._nofile_entities:
            name = e.get("name") or os.path.basename(e.get("file", ""))
            if keyword:
                hay = f"{name} {e.get('key', '')} {' '.join(e.get('tags', []))}".lower()
                if keyword not in hay:
                    continue
            e = dict(e)
            e["name"] = name
            tags = e.get("tags") or []
            if tags:
                grouped.setdefault(tags[0], []).append(e)
            else:
                no_tag.append(e)

        is_icon = self._current_type in ICON_RULES

        def add_entity_item(ent):
            name = ent["name"]
            sub = ent.get("key", "") or os.path.basename(ent.get("file", ""))
            fp = ent.get("file", "")
            text = name
            if sub != name:
                text += f"\n📄 {sub}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole,
                         {"entity": ent, "file": fp, "is_icon": is_icon})
            item.setToolTip(f"{name}\n文件: {os.path.relpath(fp, self.mod_path) if fp else ''}")
            self.file_list.addItem(item)

        for ent in sorted(no_tag, key=lambda x: x["name"].lower()):
            add_entity_item(ent)

        for tag in sorted(grouped):
            items = sorted(grouped[tag], key=lambda x: x["name"].lower())
            head = QListWidgetItem(f"🏷 {tag}（{len(items)}）")
            head.setFlags(Qt.ItemFlag.NoItemFlags)
            head.setForeground(Qt.GlobalColor.gray)
            self.file_list.addItem(head)
            for ent in items:
                add_entity_item(ent)

        if self.file_list.count() == 0:
            item = QListWidgetItem("（无匹配实体）")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.file_list.addItem(item)

    def _collect_files(self):
        """扫描当前内容类型对应的文件列表（递归子目录，如 organizations/projects）。"""
        if not self.mod_path or not os.path.isdir(self.mod_path):
            return []

        key = self._current_type
        folders, exts = self._type_folders_ext(key)
        files = []
        seen = set()
        for rel in folders:
            base = self.mod_path if rel == "." else os.path.join(self.mod_path, rel)
            if not os.path.isdir(base):
                continue
            for root, _dirs, names in os.walk(base):
                for name in sorted(names):
                    fp = os.path.join(root, name)
                    if os.path.isfile(fp) and self._ext_matches(name, exts):
                        real = os.path.realpath(fp)
                        if real in seen:
                            continue
                        seen.add(real)
                        files.append(fp)
        return files

    @staticmethod
    def _type_folders_ext(key):
        """返回内容类型的 (文件夹列表, 扩展名列表)。

        扩展名支持字符串（单个）或列表（多个），统一返回小写列表。
        """
        for c in CONTENT_TYPES:
            if c[0] == key:
                folders = c[3]
                ext = c[5]
                if isinstance(ext, str):
                    exts = [ext]
                else:
                    exts = list(ext or [])
                return list(folders), [e.lower() for e in exts]
        return [], [".txt"]

    @classmethod
    def _ext_matches(cls, name, exts):
        """判断文件名是否匹配扩展名列表（大小写不敏感）。"""
        lower = name.lower()
        return any(lower.endswith(e) for e in exts)

    @staticmethod
    def _blank_pdx(text):
        return EntityScanner._blank_pdx(text)
    @staticmethod
    def _scan_blocks(text):
        return EntityScanner._scan_blocks(text)
    @staticmethod
    def _block_spans(blocks):
        return EntityScanner._block_spans(blocks)
    @classmethod
    def _extract_entities(cls, content_type, content):
        return EntityScanner._extract_entities(content_type, content)
    @classmethod
    def _apply_locate_rule(cls, rule, content, spans, cfg):
        return EntityScanner._apply_locate_rule(rule, content, spans, cfg)
    @staticmethod
    def _top_level_fields(body):
        return EntityScanner._top_level_fields(body)
    @classmethod
    def _make_entity(cls, content, start, end, block_key, cfg):
        return EntityScanner._make_entity(content, start, end, block_key, cfg)
    def _refresh_files(self):
        """刷新右侧文件块列表（文件卡片，不含内嵌图片）。"""
        self.file_list.clear()
        keyword = self.search_edit.text().strip().lower()

        for fp in self._collect_files():
            name = os.path.basename(fp)
            if keyword:
                tags = self._file_tags(fp)
                if keyword not in name.lower() and \
                        not any(keyword in (t or "").lower() for t in tags):
                    continue
            self._add_file_item(fp, name)

        if self.file_list.count() == 0:
            item = QListWidgetItem("（无匹配文件）")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.file_list.addItem(item)

    def _add_file_item(self, fp, name):
        """添加单个文件卡片项（文件名 + 关联国家 tag）。"""
        tags = self._file_tags(fp)
        rel = os.path.relpath(fp, self.mod_path) if self.mod_path else fp
        is_icon = self._current_type in ICON_RULES
        item_text = f"{name}"
        if tags:
            shown = ', '.join(tags[:8])
            if len(tags) > 8:
                shown += "…"
            item_text += f"\n国家: {shown}"
        item = QListWidgetItem(item_text)
        item.setData(Qt.ItemDataRole.UserRole, fp)
        item.setData(Qt.ItemDataRole.UserRole + 1, None)
        item.setData(Qt.ItemDataRole.UserRole + 2, {"is_icon": is_icon})
        item.setToolTip(rel)
        self.file_list.addItem(item)

    # 国家标签缓存：path -> ((mtime_ns, size), tags)；文件未变化时跳过读取与检测
    _TAG_CACHE = {}
    _TAG_CACHE_MAX = 8192

    # 实体提取缓存：path -> ((mtime_ns, size), [entities])；增量复用避免重复解析
    _ENTITY_CACHE = {}
    _ENTITY_CACHE_MAX = 8192

    def _entities_for_file(self, content_type, content, fp):
        """带缓存的实体提取：文件 (mtime, size) 未变时直接返回上次结果（副本）。"""
        try:
            st = os.stat(fp)
            key = (st.st_mtime_ns, st.st_size)
        except OSError:
            return self._collect_file_entities(content_type, content, fp)
        hit = self._ENTITY_CACHE.get(fp)
        if hit is not None and hit[0] == key:
            return [dict(e) for e in hit[1]]
        es = self._collect_file_entities(content_type, content, fp)
        self._ENTITY_CACHE[fp] = (key, es)
        if len(self._ENTITY_CACHE) > self._ENTITY_CACHE_MAX:
            for k in list(self._ENTITY_CACHE)[: self._ENTITY_CACHE_MAX // 2]:
                del self._ENTITY_CACHE[k]
        return [dict(e) for e in es]

    def _file_tags(self, fp):
        """带缓存的国家标签识别：文件(mtime,size)未变时直接返回上次结果。"""
        try:
            st = os.stat(fp)
            key = (st.st_mtime_ns, st.st_size)
        except OSError:
            return []
        hit = self._TAG_CACHE.get(fp)
        if hit is not None and hit[0] == key:
            return hit[1]
        tags = self._detect_country_tags(fp, self._read_file(fp))
        self._TAG_CACHE[fp] = (key, tags)
        if len(self._TAG_CACHE) > self._TAG_CACHE_MAX:
            for k in list(self._TAG_CACHE)[: self._TAG_CACHE_MAX // 2]:
                del self._TAG_CACHE[k]
        return tags

    @staticmethod
    def _detect_country_tags(file_path, content):
        return EntityScanner._detect_country_tags(file_path, content)
    @staticmethod
    def _read_file(fp):
        return EntityScanner._read_file(fp)
    def _on_type_clicked(self, item):
        """切换内容类型。无文件模式下自动在右侧展示该类型全部实体。"""
        key = item.data(Qt.ItemDataRole.UserRole)
        if not key:
            return  # 分隔线项（NoItemFlags 无 data）
        self._current_type = key
        if self._nofile:
            self._refresh()
            return
        self._refresh_files()

    def _on_file_double_clicked(self, item):
        """双击文件块/实体项：国策→设计视图，图标型→画廊，其余→先展示实体再树编辑。"""
        if self._nofile:
            self._on_entity_double_clicked(item)
            return
        fp = item.data(Qt.ItemDataRole.UserRole)
        if not fp:
            return
        if self._current_type == "focus":
            self.focus_file_selected.emit(fp)
        elif self._current_type == "tech":
            # 科技：与国策树同一画布绘制科技树（树形自动布局）
            self.tech_file_selected.emit(fp)
        elif self._current_type == "event" or "/events/" in fp.replace("\\", "/"):
            # 事件：直接弹事件专用编辑器（不先进画廊）
            self.generic_file_selected.emit(fp, None)
        elif self._current_type in ICON_RULES:
            self.entity_gallery_requested.emit(self._current_type, fp)
        elif self._current_type in AI_TYPES:
            # AI 内容：直接交给主窗口分发（专用编辑器或树形编辑器）
            self.generic_file_selected.emit(fp, None)
        else:
            # 力量平衡（common/bop）→ 直接弹专用编辑器
            if self._current_type == "bop":
                self.generic_file_selected.emit(fp, None)
                return
            # 角色（common/characters）→ 直接弹角色编辑器
            norm_fp2 = fp.replace("\\", "/")
            if self._current_type == "character" or "/common/characters/" in norm_fp2:
                self.generic_file_selected.emit(fp, None)
                return
            # 初始部队（history/units）→ 直接弹设计器（编制/地编），不先进画廊
            norm_fp = fp.replace("\\", "/")
            if self._current_type == "initial_oob" or "/history/units/" in norm_fp:
                self.generic_file_selected.emit(fp, None)
                return
            # 普通模式也先展示实体：文件内有可提取的实体时进画廊，否则直接树编辑
            if self._file_has_entities(fp):
                self.entity_gallery_requested.emit(self._current_type, fp)
            else:
                self.generic_file_selected.emit(fp, None)

    def _file_has_entities(self, fp):
        """判断文件是否能提取出「非文件级」实体（区别于整文件一个实体）。"""
        try:
            content = self._read_file(fp)
            if not content.strip():
                return False
            base = os.path.splitext(os.path.basename(fp))[0]
            es = self._entities_for_file(self._current_type, content, fp)
            meaningful = [e for e in es
                          if e.get("name") and e["name"] != base]
            return bool(meaningful)
        except Exception:
            return False

    def _on_entity_double_clicked(self, item):
        """无文件模式双击实体：图标型在右侧图形化展示，均提供树编辑器弹窗。"""
        if item.flags() & Qt.ItemFlag.ItemIsSelectable == 0:
            return
        meta = item.data(Qt.ItemDataRole.UserRole)
        if not meta:
            return
        if self._current_type == "focus":
            fp = meta.get("file", "")
            if fp:
                self.focus_file_selected.emit(fp)
            return
        # 事件（无文件模式）：直接打开事件专用编辑器
        fp = meta.get("file", "") if isinstance(meta, dict) else ""
        norm_fp = (fp or "").replace("\\", "/")
        if self._current_type == "event" or "/events/" in norm_fp:
            if fp:
                self.generic_file_selected.emit(fp,
                    meta.get("key") if isinstance(meta, dict) else None)
            return
        # AI 内容（无文件模式也支持）：直接交给主窗口分发
        if self._current_type in AI_TYPES:
            if fp:
                self.generic_file_selected.emit(fp, meta.get("key") if isinstance(meta, dict) else None)
            return
        # 力量平衡（common/bop）→ 直接弹专用编辑器（无文件模式也支持）
        if self._current_type == "bop":
            if fp:
                self.generic_file_selected.emit(fp, meta.get("key"))
            return
        # 角色（common/characters）→ 直接弹角色编辑器（无文件模式也支持）
        if self._current_type == "character" or "/common/characters/" in norm_fp:
            if fp:
                self.generic_file_selected.emit(fp, meta.get("key") if isinstance(meta, dict) else None)
            return
        # 初始部队（history/units）→ 直接弹设计器（无文件模式也支持）
        if self._current_type == "initial_oob" or "/history/units/" in norm_fp:
            if fp:
                self.generic_file_selected.emit(fp, meta.get("key"))
            return
        # 右侧图形化展示当前类型全部实体（画廊）
        self.entity_gallery_nofile_requested.emit(
            self._current_type, list(self._filtered_entities()))

    def _show_file_menu(self, pos):
        """文件块右键菜单。"""
        item = self.file_list.itemAt(pos)
        is_head = item is not None and (item.flags() & Qt.ItemFlag.ItemIsSelectable) == 0
        if is_head:
            return
        if self._nofile:
            self._show_entity_menu(item, pos)
            return
        fp = item.data(Qt.ItemDataRole.UserRole) if item else None
        meta = item.data(Qt.ItemDataRole.UserRole + 2) if item else {}
        is_icon = bool(meta.get("is_icon")) if meta else False

        menu = QMenu(self)

        if fp:
            if self._current_type == "focus":
                open_action = menu.addAction("打开（国策设计视图）")
                open_action.triggered.connect(
                    lambda: self.focus_file_selected.emit(fp))
            elif self._current_type == "tech":
                open_action = menu.addAction("🔬 打开（科技树画布）")
                open_action.triggered.connect(
                    lambda: self.tech_file_selected.emit(fp))
                edit_action = menu.addAction("✏ 编辑科技词条…")
                edit_action.triggered.connect(
                    lambda: self.generic_file_selected.emit(fp, None))
            else:
                gallery_action = menu.addAction("🖼 在右侧展示实体")
                gallery_action.triggered.connect(
                    lambda: self.entity_gallery_requested.emit(self._current_type, fp))
                open_action = menu.addAction("✎ 打开（树形编辑器）")
                open_action.triggered.connect(
                    lambda: self.generic_file_selected.emit(fp, None))
            explorer_action = menu.addAction("📂 在资源管理器中显示")
            explorer_action.triggered.connect(lambda: self._show_in_explorer(fp))
            menu.addSeparator()

        new_file_action = menu.addAction("📄 新建文件（基础模板）…")
        new_file_action.triggered.connect(self._new_file)
        new_template_action = menu.addAction("🧩 从其他模板新建文件…")
        new_template_action.triggered.connect(self._new_file_from_template)
        if self._current_type == "generic":
            new_dir_action = menu.addAction("📁 新建文件夹…")
            new_dir_action.triggered.connect(self._new_folder)

        menu.exec(self.file_list.viewport().mapToGlobal(pos))

    def _show_entity_menu(self, item, pos):
        """无文件模式实体右键菜单。"""
        meta = item.data(Qt.ItemDataRole.UserRole) if item else None
        fp = meta.get("file", "") if meta else ""
        ent = meta.get("entity", {}) if meta else {}
        entity_id = ent.get("key") or ent.get("name") or None

        menu = QMenu(self)

        if fp:
            if self._current_type == "focus":
                open_action = menu.addAction("打开（国策设计视图）")
                open_action.triggered.connect(
                    lambda: self.focus_file_selected.emit(fp))
            else:
                if self._current_type in ICON_RULES:
                    gallery_action = menu.addAction("🖼 在右侧展示实体图标")
                    gallery_action.triggered.connect(
                        lambda: self.entity_gallery_nofile_requested.emit(
                            self._current_type, list(self._filtered_entities())))
                open_action = menu.addAction("✎ 打开（树形编辑器）")
                open_action.triggered.connect(
                    lambda: self.generic_file_selected.emit(fp, entity_id))
            explorer_action = menu.addAction("📂 在资源管理器中显示")
            explorer_action.triggered.connect(lambda: self._show_in_explorer(fp))
            menu.addSeparator()

        new_file_action = menu.addAction("📄 新建文件（基础模板）…")
        new_file_action.triggered.connect(self._new_file)
        new_template_action = menu.addAction("🧩 从其他模板新建文件…")
        new_template_action.triggered.connect(self._new_file_from_template)

        menu.exec(self.file_list.viewport().mapToGlobal(pos))

    # ---------- 无文件模式国家设置 ----------

    def _country_name(self, tag):
        """国家 tag → 显示名（文件名推断；无则空）。"""
        try:
            if not tag:
                return ""
            if getattr(self, "_country_names", None) is None:
                self._country_names = self._load_country_names()
            return self._country_names.get(tag, "")
        except Exception:
            return ""

    def _load_country_names(self):
        """预载 {tag: 国家名}（复用国家设置扫描 + history/countries 文件名）。"""
        names = {}
        try:
            from country_setup_dialog import scan_vanilla_countries
            game_path = self._game_path()
            for tag, rel in (scan_vanilla_countries(game_path) or {}).items():
                base = os.path.basename((rel or "").replace("\\", "/"))
                name = os.path.splitext(base)[0] if base else ""
                # "GER - Germany.txt" → "Germany"；无分隔则保留原名
                if " - " in name:
                    name = name.split(" - ", 1)[1]
                names[tag] = name
        except Exception:
            pass
        # 补充 history/countries 文件名前缀国家（scan_vanilla_countries 不扫该目录）
        try:
            for base in (self.mod_path, self._game_path()):
                if not base:
                    continue
                d = os.path.join(base, "history", "countries")
                if not os.path.isdir(d):
                    continue
                for fn in os.listdir(d):
                    if not fn.lower().endswith(".txt"):
                        continue
                    first = (fn.split()[0] if fn.split() else "").upper()
                    if not first or not first.isalnum() or not any(
                            ch.isalpha() for ch in first):
                        continue
                    stem = os.path.splitext(fn)[0]
                    name = stem
                    if " - " in stem:
                        name = stem.split(" - ", 1)[1]
                    names.setdefault(first, name)
        except Exception:
            pass
        return names

    def set_current_country(self, tag):
        """设置无文件模式「当前国家」筛选（None=全部），刷新画廊。"""
        tag = (tag or "").strip().upper() or None
        if tag == self._current_country:
            return
        self._current_country = tag
        if tag:
            name = self._country_name(tag)
            self.country_label.setText(
                f"当前国家：{tag}（{name}）" if name else f"当前国家：{tag}")
        else:
            self.country_label.setText("当前国家：全部")
        self.country_changed.emit(tag or "")
        if self._nofile:
            self._refresh()

    def current_country(self):
        """返回当前无文件模式国家筛选（None=全部）。"""
        return self._current_country

    def _on_select_country(self):
        """纯选择国家（不修改任何文件）：仅切换当前浏览国家。"""
        from PyQt6.QtWidgets import QInputDialog
        try:
            from country_setup_dialog import scan_vanilla_countries, \
                scan_mod_countries
        except Exception as e:
            QMessageBox.warning(self, "错误", f"国家列表加载失败: {e}")
            return
        countries = scan_vanilla_countries(self._game_path())
        mod_tags = scan_mod_countries(self.mod_path)
        # 合并 history/countries 文件名前缀国家（scan_vanilla_countries 不扫该目录）
        for base in (self.mod_path, self._game_path()):
            if not base:
                continue
            d = os.path.join(base, "history", "countries")
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                if not fn.lower().endswith(".txt"):
                    continue
                first = (fn.split()[0] if fn.split() else "").upper()
                if not first or not first.isalnum() or not any(
                        ch.isalpha() for ch in first):
                    continue
                countries.setdefault(first, "history/countries/" + fn)
        items = ["（全部）"]
        for tag in sorted(countries or {}):
            rel = (countries.get(tag) or "").replace("\\", "/")
            name = os.path.splitext(os.path.basename(rel))[0] if rel else ""
            if " - " in name:
                name = name.split(" - ", 1)[1]
            marked = " [mod 已接管]" if tag in mod_tags else ""
            items.append(f"{tag}  {name}{marked}")
        item, ok = QInputDialog.getItem(
            self, "选择国家", "选择要浏览的国家（仅切换，不写文件）：",
            items, 0, False)
        if not ok:
            return
        if item == "（全部）":
            tag = ""
        else:
            tag = (item.split()[0] if item.split() else "").upper()
        self.set_current_country(tag)

    def _on_country_setup(self):
        """打开国家设置对话框：选择/创建国家 + 复制原版或同名覆盖。"""
        try:
            from country_setup_dialog import (
                CountrySetupDialog, copy_country_files, create_blank_overrides,
                create_new_country_files)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"国家设置模块加载失败: {e}")
            return

        game_path = self._game_path()
        dlg = CountrySetupDialog(game_path, self.mod_path, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        tag, mode, dirs = dlg.get_result()
        if not tag:
            return

        if mode == "copy":
            copied = copy_country_files(game_path, self.mod_path, tag, dirs)
            msg = f"已复制 {len(copied)} 个原版文件到 mod：\n" + \
                "\n".join(copied[:12]) + ("\n…" if len(copied) > 12 else "")
            QMessageBox.information(self, "复制完成", msg or "无匹配文件")
        else:
            created = create_blank_overrides(self.mod_path, tag, dirs,
                                             game_path=game_path)
            if not created:
                # 新国家基础设施文件
                created = create_new_country_files(self.mod_path, tag, dirs,
                                                   game_path=game_path)
            msg = f"已创建 {len(created)} 个文件：\n" + \
                "\n".join(created[:12]) + ("\n…" if len(created) > 12 else "")
            QMessageBox.information(self, "覆盖完成", msg or "无匹配文件")

        # 完成国家流程后，将当前国家设为所选 tag，刷新画廊
        self.set_current_country(tag)

    def _game_path(self):
        """返回游戏根目录（读取 settings.json）。"""
        try:
            import json
            with open("settings.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("HOI4_path", "")
        except Exception:
            return ""

    def _new_file_directory(self):
        """确定新建文件的目录：通用类型手动选择，其余类型取首个内容文件夹。"""
        if self._current_type == "generic":
            from PyQt6.QtWidgets import QFileDialog
            start = self.mod_path if os.path.isdir(self.mod_path) else os.getcwd()
            directory = QFileDialog.getExistingDirectory(
                self, "选择新建文件目录", start)
            if not directory:
                return None
            return directory
        folders, _ext = self._type_folders_ext(self._current_type)
        if not folders or folders[0] == ".":
            return None
        directory = os.path.join(self.mod_path, folders[0]) if self.mod_path else folders[0]
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception:
            return None
        return directory

    def _ask_file_name(self, parent, default_name="", default_ext=None):
        """询问文件名，自动补当前类型的扩展名。

        default_ext: 无扩展名时补的扩展名；None 时取当前类型首个扩展名。
        """
        from PyQt6.QtWidgets import QInputDialog
        if default_ext is None:
            _folders, exts = self._type_folders_ext(self._current_type)
            default_ext = exts[0] if exts else ".txt"
        name, ok = QInputDialog.getText(
            parent, "新建文件", "文件名（含扩展名）:", text=default_name)
        if not ok or not name.strip():
            return None
        name = name.strip()
        if os.path.splitext(name)[1] == "":
            name += default_ext
        return name

    def _base_template(self):
        """获取当前内容类型的基础文件模板路径；无模板返回 None。"""
        tpl_type = None
        for c in CONTENT_TYPES:
            if c[0] == self._current_type:
                tpl_type = c[4]
                break
        if not tpl_type:
            return None
        try:
            from template_scheduler import get_template_scheduler
            scheduler = get_template_scheduler()
            matches = scheduler.search_templates(template_type=tpl_type,
                                                 usage="file")
            return matches[0]["filepath"] if matches else None
        except Exception:
            return None

    def _new_file(self):
        """在内容目录中新建文件：有基础模板则套用模板创建，否则提示暂未制作。"""
        if self._current_type == "generic":
            self._new_generic_file()
            return

        tpl_type = None
        for c in CONTENT_TYPES:
            if c[0] == self._current_type:
                tpl_type = c[4]
                break
        if not tpl_type:
            QMessageBox.information(
                self, "提示",
                f"「{self._current_type}」类型暂无新建文件模板（仍可树形编辑），无法新建文件。")
            return

        template_path = self._base_template()
        if not template_path:
            QMessageBox.information(
                self, "提示",
                f"「{self._current_type}」类型暂无新建文件模板（仍可树形编辑），无法新建文件。")
            return

        directory = self._new_file_directory()
        if not directory:
            return
        _, exts = self._type_folders_ext(self._current_type)
        ext = exts[0] if exts else ".txt"
        default_name = os.path.splitext(os.path.basename(template_path))[0] + ext
        name = self._ask_file_name(self, default_name=default_name, default_ext=ext)
        if not name:
            return
        path = os.path.join(directory, name)
        if os.path.exists(path):
            QMessageBox.warning(self, "错误", f"文件已存在: {path}")
            return
        from template_scheduler import get_template_scheduler
        scheduler = get_template_scheduler()
        replacements = {}
        if scheduler.apply_template(template_path, path, replacements):
            self._refresh_files()
            QMessageBox.information(self, "成功",
                                    f"文件已创建（基于基础模板）: {path}")
        else:
            QMessageBox.warning(self, "错误", "创建失败")

    def _new_generic_file(self):
        """通用类型：手动选择目录后新建空文件。"""
        directory = self._new_file_directory()
        if not directory:
            return
        name = self._ask_file_name(self)
        if not name:
            return
        path = os.path.join(directory, name)
        if os.path.exists(path):
            QMessageBox.warning(self, "错误", f"文件已存在: {path}")
            return
        try:
            from write_utils import atomic_write_text
            atomic_write_text(path, "", undo=False)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"创建失败: {e}")
            return
        self._refresh_files()
        QMessageBox.information(self, "成功", f"文件已创建: {path}")

    def _new_file_from_template(self):
        """选择模板并按模板新建文件。"""
        from template_dialog import TemplateDialog
        from template_scheduler import get_template_scheduler

        directory = self._new_file_directory()
        if not directory:
            return
        scheduler = get_template_scheduler()
        dlg = TemplateDialog(scheduler, parent=self)
        dlg.setWindowTitle("从模板新建文件")
        # 新建文件场景默认只显示创建文件用途的模板
        dlg.usage_combo.setCurrentIndex(1)

        def on_template_ok():
            data = dlg.get_template_data()
            if not data:
                dlg.deleteLater()
                return
            default = data["name"] + (os.path.splitext(data["filename"])[1] or ".txt")
            name = self._ask_file_name(self, default_name=default)
            if not name:
                dlg.deleteLater()
                return
            new_path = os.path.join(directory, name)
            if os.path.exists(new_path):
                QMessageBox.warning(self, "错误", f"文件已存在: {new_path}")
                dlg.deleteLater()
                return
            # 模板变量已在模板对话框内填写，优先使用替换后的内容
            applied = dlg.get_applied_content()
            if applied is not None:
                success = scheduler.apply_template(data["filepath"], new_path)
                if success:
                    try:
                        os.makedirs(os.path.dirname(new_path), exist_ok=True)
                        from write_utils import atomic_write_text
                        atomic_write_text(new_path, applied, undo=False)
                    except Exception:
                        success = False
            else:
                success = scheduler.apply_template(data["filepath"], new_path)
            if success:
                self._refresh_files()
                QMessageBox.information(self, "成功", f"文件已创建: {new_path}")
            else:
                QMessageBox.warning(self, "错误", "从模板创建文件失败")
            dlg.deleteLater()

        dlg.accepted.connect(on_template_ok)
        dlg.show()

    def _new_folder(self):
        """在 mod 根目录下新建文件夹（仅通用文件类型）。"""
        from PyQt6.QtWidgets import QInputDialog
        base = self.mod_path if os.path.isdir(self.mod_path) else os.getcwd()
        name, ok = QInputDialog.getText(self, "新建文件夹", "文件夹名称:")
        if not ok or not name.strip():
            return
        name = name.strip().replace("/", "_").replace("\\", "_")
        path = os.path.join(base, name)
        if os.path.exists(path):
            QMessageBox.warning(self, "错误", f"文件夹已存在: {path}")
            return
        try:
            os.makedirs(path)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"创建失败: {e}")
            return
        QMessageBox.information(self, "成功", f"文件夹已创建: {path}")

    @staticmethod
    def _show_in_explorer(file_path):
        """在系统文件资源管理器中定位文件。"""
        import subprocess
        import platform
        abs_path = os.path.abspath(file_path)
        if platform.system() == "Windows":
            subprocess.run(["explorer", "/select,", abs_path], check=False)
        elif platform.system() == "Darwin":
            subprocess.run(["open", "-R", abs_path], check=False)
        else:
            subprocess.run(["xdg-open", os.path.dirname(abs_path)], check=False)

    def set_mod_path(self, mod_path):
        """更新 mod 路径并刷新文件列表。"""
        self.mod_path = mod_path
        try:
            from icon_resolver import clear_cache
            clear_cache()
        except Exception:
            pass
        self._refresh()

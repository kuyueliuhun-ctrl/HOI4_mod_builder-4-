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


# 内容类型定义：key -> (显示名, 图标, 相对 mod 目录的文件夹列表, 基础模板类型或 None, 扩展名)
# 仿网站工作台内容类型；基础模板类型为 None 表示暂无对应模板（标注：暂未制作相关功能）
CONTENT_TYPES = [
    ("character", "角色", "👤", ["common/characters"], "character", ".txt"),
    ("idea", "民族精神", "💡", ["common/ideas"], "ideas_file", ".txt"),
    ("focus", "国策", "🌳", ["common/national_focus"], "focus_tree", ".txt"),
    ("event", "事件", "📜", ["events"], "event", ".txt"),
    ("decision", "决议", "📋", ["common/decisions"], "decision", ".txt"),
    ("tech", "科技", "🔬", ["common/technologies"], "tech", ".txt"),
    ("state", "地块", "🗺️", ["history/states"], "地块", ".txt"),
    ("super_event", "超事件", "📢", ["events"], "event", ".txt"),
    ("bookmark", "剧本", "🎬", ["common/bookmarks"], "bookmark", ".txt"),
    ("country_history", "国家设置", "🏛️", ["history/countries"], "country_history", ".txt"),
    ("advisor_assign", "顾问分配", "👔", ["history/general"], "顾问分配", ".txt"),
    ("scripted", "脚本化效果", "🧩", ["common/scripted_effects", "common/scripted_triggers"], "scripted", ".txt"),
    ("gui", "界面机制", "🖥️", ["interface"], "gui", ".gui"),
    ("mio", "MIO", "🏭", ["common/military_industrial_organization"], "MIO", ".txt"),
    ("equipment", "装备", "🎯", ["common/units/equipment"], "equipment", ".txt"),
    ("unit", "兵种", "🛡️", ["common/units"], "unit", ".txt"),
    ("initial_oob", "初始部队", "🚁", ["history/units"], "初始部队", ".txt"),
    ("special_project", "特殊计划", "🧪", ["common/special_projects"], "特殊计划", ".txt"),
    ("doctrine", "军事学说", "📚", ["common/doctrines"], "军事学说", ".txt"),
    ("intelligence", "情报机构", "🕵️", ["common/intelligence_agencies"], "情报机构", ".txt"),
    ("autonomy", "自治状态", "🤝", ["common/autonomous_states"], "自治状态", ".txt"),
    ("country_setup", "国家定义", "🏷️", ["common/country_tags", "common/countries"], "国家定义", ".txt"),
    ("dynamic_modifier", "动态修正", "⚡", ["common/dynamic_modifiers"], "动态修正", ".txt"),
    ("modifier_definition", "修正量定义", "📐", ["common/modifier_definitions"], "修正量定义", ".txt"),
    ("ai_strategy", "AI战略计划", "🤖", ["common/ai_strategy_plans", "common/ai_strategy"], "ai_strategy", ".txt"),
    ("ai_division", "AI师模板", "🤖", ["common/ai_templates"], "ai_strategy", ".txt"),
    ("wargoal", "战争目标", "⚔️", ["common/wargoals"], "战争目标", ".txt"),
    ("gui_edit", "GUI编辑", "🖼️", ["interface"], "gui", ".gui"),
    ("generic", "通用文件", "📁", ["."], None, ".txt"),
]

# 各类型在树编辑器中显示的类型标签
TYPE_ROOT_LABELS = {
    "focus": "focus_tree",
    "event": "event",
    "decision": "decision",
    "idea": "ideas",
    "generic": "",
}

# 图标型内容类型的图标配置：
#   locate      实体块定位规则（keys/wrap 语义，同实体提取）
#   field       图标字段路径（支持嵌套如 portraits>civilian>large）
#   picker_prefix 图标选择对话框的前缀过滤（"" = 全部）
#   dirs        图标回退搜索目录（相对 mod/游戏根目录）
#   upload      上传配置（subdir/gfx_file/gfx_name_pattern/ref_mode 等）
ICON_RULES = {
    "focus": {
        "locate": ("keys", ["focus", "shared_focus", "joint_focus"]),
        "field": "icon",
        "picker_prefix": "GFX_",
        "dirs": ["gfx/interface/goals"],
        "upload": {
            "subdir": "gfx/interface/goals",
            "gfx_file": "goals_mod.gfx",
            "shine_gfx_file": "goals_shine_mod.gfx",
            "gfx_name_pattern": "GFX_goal_{name}",
            "shine_sprite_pattern": "GFX_goal_{name}_shine",
            "shine": True,
            "ref_mode": "sprite",
        },
    },
    "decision": {
        "locate": [("wrap", [("decisions", 2)]), ("top_children",)],
        "field": "icon",
        "picker_prefix": "",
        "dirs": ["gfx/interface/goals", "gfx/interface/decisions"],
        "upload": {
            "subdir": "gfx/interface/goals",
            "gfx_file": "decisions_mod.gfx",
            "gfx_name_pattern": "GFX_goal_{name}",
            "shine": True,
            "ref_mode": "sprite",
        },
    },
    "idea": {
        "locate": ("wrap", [("ideas", 2)]),
        "field": "picture",
        "picker_prefix": "GFX_",
        "dirs": ["gfx/interface/ideas", "gfx/interface/goals", "gfx/event_pictures"],
        "upload": {
            "subdir": "gfx/interface/ideas",
            "gfx_file": "ideas_mod.gfx",
            "gfx_name_pattern": "GFX_idea_{name}",
            "shine": False,
            "ref_mode": "sprite",
        },
    },
    "event": {
        "locate": ("keys", ["country_event", "news_event", "state_event",
                            "operative_leader_event", "dynamic_event"]),
        "field": "picture",
        "picker_prefix": "",
        "dirs": ["gfx/event_pictures"],
        "upload": {
            "subdir": "gfx/event_pictures",
            "gfx_file": "eventpictures_mod.gfx",
            "gfx_name_pattern": "GFX_event_{name}",
            "shine": False,
            "ref_mode": "sprite",
        },
    },
    "super_event": {
        "locate": ("keys", ["news_event", "country_event", "event"]),
        "field": "picture",
        "picker_prefix": "",
        "dirs": ["gfx/event_pictures"],
        "upload": {
            "subdir": "gfx/event_pictures",
            "gfx_file": "eventpictures_mod.gfx",
            "gfx_name_pattern": "GFX_event_{name}",
            "shine": False,
            "ref_mode": "sprite",
        },
    },
    "tech": {
        "locate": ("wrap", [("technologies", 1), ("technology", 1)]),
        "field": "picture",
        "picker_prefix": "",
        "dirs": ["gfx/interface/technologies"],
        "upload": {
            "subdir": "gfx/interface/technologies",
            "gfx_file": "technologies_mod.gfx",
            "gfx_name_pattern": "GFX_tech_{name}",
            "shine": False,
            "ref_mode": "direct",
        },
    },
    "character": {
        "locate": ("wrap", [("characters", 1)]),
        "field": ["portraits>civilian>large",
                  "portraits>army>large",
                  "portraits>political>large",
                  "portraits>civilian>small",
                  "portraits>army>small",
                  "portraits>political>small"],
        "picker_prefix": "",
        "dirs": ["gfx/Leaders", "gfx/interface/portraits", "gfx/interface/ideas"],
        "slots": {
            "advisor_large": {"label": "大图标（顾问）", "field": "portraits>civilian>large", "suffix": ""},
            "advisor_small": {"label": "小图标（顾问）", "field": "portraits>civilian>small", "suffix": "_small"},
            "general_large": {"label": "大图标（将领）", "field": "portraits>army>large", "suffix": "_general"},
            "general_small": {"label": "小图标（将领）", "field": "portraits>army>small", "suffix": "_general_small"},
        },
        "upload": {
            "subdir": "gfx/Leaders",
            "gfx_file": "",
            "gfx_name_pattern": "",
            "shine": False,
            "ref_mode": "path",
        },
    },
    "bookmark": {
        "locate": ("keys", ["bookmark"]),
        "field": "picture",
        "picker_prefix": "GFX_select_date",
        "dirs": ["gfx/interface/bookmarks"],
        "upload": {
            "subdir": "gfx/interface/bookmarks",
            "gfx_file": "bookmarks_mod.gfx",
            "gfx_name_pattern": "GFX_bookmark_{name}",
            "shine": False,
            "ref_mode": "sprite",
        },
    },
    "special_project": {
        "locate": ("keys", ["special_project"]),
        "field": "icon",
        "picker_prefix": "",
        "dirs": ["gfx/interface/goals"],
        "upload": {
            "subdir": "gfx/interface/goals",
            "gfx_file": "special_projects_mod.gfx",
            "gfx_name_pattern": "GFX_special_project_{name}",
            "shine": False,
            "ref_mode": "sprite",
        },
    },
}


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

    def __init__(self, mod_path="", parent=None):
        super().__init__("工作台", parent)
        self.mod_path = mod_path
        self._current_type = "focus"
        self._nofile = False
        self._nofile_entities = []

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
            self.search_edit.setPlaceholderText("搜索实体…")
        else:
            self.title_label.setText("工作台")
            self.search_edit.setPlaceholderText("搜索文件…")
        self.search_bar.setVisible(not nofile)
        self.file_list.setVisible(not nofile)
        self.nofile_mode_changed.emit(nofile)
        self._refresh()
        if nofile and self._nofile_entities:
            self.entity_gallery_nofile_requested.emit(
                self._current_type, list(self._nofile_entities))

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
        for key, name, icon, _folders, tpl_type, _ext in CONTENT_TYPES:
            text = f"{icon} {name}"
            if tpl_type is None and key != "generic":
                text += "（暂未制作相关功能）"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.type_list.addItem(item)
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
        self.setWidget(container)

        self._refresh()

    # ---------- 文件扫描 ----------

    # 国家 tag：2-4 位大写字母/数字，至少含一个字母
    _TAG_RE = re.compile(r'(?=[A-Z0-9]*[A-Z])[A-Z0-9]{2,4}')

    def _refresh(self):
        """按当前模式刷新右侧列表（文件模式 / 无文件模式）。"""
        if self._nofile:
            self._refresh_entities()
        else:
            self._refresh_files()

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
        folders, ext = self._type_folders_ext(key)
        entities = []
        seen = set()
        for rel in folders:
            base = self.mod_path if rel == "." else os.path.join(self.mod_path, rel)
            if not os.path.isdir(base):
                continue
            for root, _dirs, names in os.walk(base):
                for name in sorted(names):
                    if not name.lower().endswith(ext):
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
                    entities.extend(self._collect_file_entities(key, content, fp))
        return entities

    @classmethod
    def _collect_file_entities(cls, content_type, content, fp):
        """提取单个文件内的实体并附带 file/tags 信息（无文件模式与画廊重载复用）。"""
        file_tags = cls._detect_country_tags(fp, content)
        if content_type == "character":
            es = cls._extract_character_entities(content, file_tags)
            for e in es:
                e["tags"] = [e["tag"]] if e.get("tag") else []
        elif content_type == "country_history":
            # 国家设置：文件即实体（文件名前缀即国家）
            es = [{"name": os.path.splitext(os.path.basename(fp))[0], "key": "",
                   "icon": "", "range": (0, len(content))}]
        elif content_type in ICON_RULES:
            es = cls._extract_entities(content_type, content)
            for e in es:
                e["icon"] = e.get("icon", "")
        else:
            es = cls._extract_generic_entities(content)
        for e in es:
            e["file"] = fp
            if not e.get("tags"):
                e["tags"] = list(file_tags)
            if not e.get("name"):
                e["name"] = os.path.splitext(os.path.basename(fp))[0]
        return es

    @classmethod
    def _extract_character_entities(cls, content, file_tags):
        """角色文件实体提取：TAG 分组层下沉为角色实体。

        - characters = { TAG = { 角色ID = {...} } }：角色实体 tag=TAG
        - characters = { 角色ID = {...} }：角色实体 tag=文件级 tag
        """
        try:
            spans = cls._block_spans(cls._scan_blocks(content))
        except Exception:
            return []
        entities = []
        file_tag = file_tags[0] if file_tags else ""
        for key, bdepth, bpos, bend in spans:
            if key != "characters":
                continue
            children = [s for s in spans
                        if s[2] > bpos and s[3] <= bend and s[1] == bdepth + 1]
            for ckey, cd, cstart, cend in children:
                if cls._TAG_RE.fullmatch(ckey):
                    subs = [s for s in spans
                            if s[2] > cstart and s[3] <= cend and s[1] == cd + 1]
                    for skey, _d, sstart, send in subs:
                        entities.append({"name": skey, "key": skey, "icon": "",
                                         "range": (sstart, send), "tag": ckey})
                else:
                    entities.append({"name": ckey, "key": ckey, "icon": "",
                                     "range": (cstart, cend), "tag": file_tag})
        return entities

    @classmethod
    def _extract_generic_entities(cls, content):
        """通用实体提取：单顶层包装块取其直接子块；多顶层块时顶层块即实体；无块时整个文件视为一个实体。"""
        try:
            spans = cls._block_spans(cls._scan_blocks(content))
        except Exception:
            return []
        if not spans:
            return [{"name": "", "key": "", "icon": "",
                     "range": (0, len(content))}]
        md = min(s[1] for s in spans)
        tops = [s for s in spans if s[1] == md]
        entities = []
        if len(tops) == 1:
            key, bd, bpos, bend = tops[0]
            children = [s for s in spans
                        if s[2] > bpos and s[3] <= bend and s[1] == bd + 1]
            for c in children:
                entities.append({"name": c[0], "key": c[0], "icon": "",
                                 "range": (c[2], c[3])})
        if not entities:
            for s in tops:
                entities.append({"name": s[0], "key": s[0], "icon": "",
                                 "range": (s[2], s[3])})
        return entities

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
        folders, ext = self._type_folders_ext(key)
        files = []
        seen = set()
        for rel in folders:
            base = self.mod_path if rel == "." else os.path.join(self.mod_path, rel)
            if not os.path.isdir(base):
                continue
            for root, _dirs, names in os.walk(base):
                for name in sorted(names):
                    fp = os.path.join(root, name)
                    if os.path.isfile(fp) and name.lower().endswith(ext):
                        real = os.path.realpath(fp)
                        if real in seen:
                            continue
                        seen.add(real)
                        files.append(fp)
        return files

    @staticmethod
    def _type_folders_ext(key):
        """返回内容类型的 (文件夹列表, 扩展名)。"""
        for c in CONTENT_TYPES:
            if c[0] == key:
                return c[3], c[5]
        return [], ".txt"

    @staticmethod
    def _blank_pdx(text):
        """将注释与引号字符串原地替换为空格（保持字符位置不变）。

        用于 _scan_blocks 定位块范围时，保证扫描结果位置与原文一致。
        """
        chars = list(text)
        n = len(chars)
        in_str = False
        i = 0
        while i < n:
            c = chars[i]
            if in_str:
                if c == '"':
                    in_str = False
                chars[i] = ' '
                i += 1
                continue
            if c == '"':
                in_str = True
                chars[i] = ' '
                i += 1
                continue
            if c == '#':
                while i < n and chars[i] != '\n':
                    chars[i] = ' '
                    i += 1
                continue
            i += 1
        return ''.join(chars)

    @staticmethod
    def _scan_blocks(text):
        """轻量扫描：返回所有 `key = {` 块的 (key, 深度, 起始位置) 列表。

        单遍正则扫描，同时跟踪括号深度；注释与引号内容已原地替换为空格
        （保持位置不变），避免误匹配且结果可直接索引原文本。
        深度为块自身所处的层级（顶层块为 0）。
        """
        import re
        clean = WorkbenchDock._blank_pdx(text)
        pattern = re.compile(r'(\{|\})|([\w\.\-]+)\s*=\s*\{')
        blocks = []
        depth = 0
        for m in pattern.finditer(clean):
            brace = m.group(1)
            if brace == "{":
                depth += 1
            elif brace == "}":
                depth -= 1
            else:
                blocks.append((m.group(2), depth, m.start()))
                depth += 1
        return blocks

    # ---------- 实体提取 ----------

    @staticmethod
    def _block_spans(blocks):
        """为 blocks 中每个 `key = {` 计算 (key, depth, start, end)。

        块结束位置 = 其后首个深度 <= 当前块深度的块位置；否则取到内容末尾。
        使用单调栈从右向左 O(n) 求解。
        """
        import math
        n = len(blocks)
        ends = [math.inf] * n
        stack = []
        for i in range(n - 1, -1, -1):
            depth = blocks[i][1]
            while stack and blocks[stack[-1]][1] > depth:
                stack.pop()
            if stack:
                ends[i] = blocks[stack[-1]][2]
            stack.append(i)
        return [(key, depth, start, ends[i]) for i, (key, depth, start) in enumerate(blocks)]

    @classmethod
    def _extract_entities(cls, content_type, content):
        """按图标配置提取实体列表。

        Returns:
            list[dict]: [{name, key, icon, range:(start,end)}, ...]
            非图标型类型或提取失败返回 []。
        """
        cfg = ICON_RULES.get(content_type)
        if not cfg:
            return []
        try:
            blocks = cls._scan_blocks(content)
            spans = cls._block_spans(blocks)
        except Exception:
            return []
        entities = []
        locate = cfg.get("locate")
        if not locate:
            return entities

        # locate 可为单个规则或规则列表（按顺序尝试，首个非空生效）
        rules = locate if isinstance(locate, list) and isinstance(locate[0], (tuple, list)) else [locate]
        for rule in rules:
            entities = cls._apply_locate_rule(rule, content, spans, cfg)
            if entities:
                break
        return entities

    @classmethod
    def _apply_locate_rule(cls, rule, content, spans, cfg):
        """应用单条实体定位规则，返回实体列表。"""
        kind = rule[0]
        entities = []
        if kind == "keys":
            keys = set(rule[1])
            cand = [s for s in spans if s[0] in keys]
            kept = []
            for s in cand:
                # 跳过被已保留实体块包含的块（避免嵌套同名块重复计数）
                if any(o[2] <= s[2] and s[3] <= o[3] for o in kept):
                    continue
                kept.append(s)
            for key, _d, start, end in kept:
                entities.append(cls._make_entity(content, start, end, key, cfg))
        elif kind == "wrap":
            for wrap_key, depth_n in rule[1]:
                for key, bdepth, bpos, bend in spans:
                    if key != wrap_key:
                        continue
                    children = [s for s in spans
                                if s[2] > bpos and s[3] <= bend and s[1] == bdepth + depth_n]
                    for ckey, _cd, cstart, cend in children:
                        entities.append(cls._make_entity(content, cstart, cend, ckey, cfg))
        elif kind == "top_children":
            # 未包裹的文件（如 decisions 顶层直接为类别块）：实体 = 顶层块直接子块
            md = min(s[1] for s in spans) if spans else 0
            for key, bdepth, bpos, bend in spans:
                if bdepth != md:
                    continue
                children = [s for s in spans
                            if s[2] > bpos and s[3] <= bend and s[1] == bdepth + 1]
                for ckey, _cd, cstart, cend in children:
                    entities.append(cls._make_entity(content, cstart, cend, ckey, cfg))
        return entities

    @staticmethod
    def _top_level_fields(body):
        """返回实体块顶层（括号深度1）的 key=value 映射（首次出现的值）。

        使用词法 token 扫描，忽略嵌套块与注释，仅取块直接层级的键值对。
        """
        token_pattern = r'("[^"]*"|#.*|\{|\}|=|[\w\.\-]+)'
        toks = list(re.finditer(token_pattern, body))
        depth = 0
        fields = {}
        i = 0
        while i < len(toks):
            t = toks[i].group(0)
            if t == '{':
                depth += 1
                i += 1
                continue
            if t == '}':
                depth -= 1
                i += 1
                continue
            if t.startswith('#') or t == '=':
                i += 1
                continue
            if depth == 1 and i + 2 < len(toks):
                eq = toks[i + 1].group(0)
                val = toks[i + 2].group(0)
                if (eq == '=' and val not in ('=', '{', '}') and not val.startswith('#')
                        and t not in fields):
                    fields[t] = val.strip('"')
            i += 1
        return fields

    @classmethod
    def _make_entity(cls, content, start, end, block_key, cfg):
        """从实体块范围构造实体信息字典。"""
        import math
        if math.isinf(end):
            end = len(content)
        block = content[start:end]
        fields = cls._top_level_fields(block)
        name = fields.get("id") or fields.get("name") or block_key

        field = cfg.get("field", "icon")
        if isinstance(field, (list, tuple)) or ">" in field:
            from icon_ops import get_entity_icon_field
            icon = get_entity_icon_field(content, start, end, field)
        else:
            icon = fields.get(field, "")
        return {"name": name, "key": block_key, "icon": icon, "range": (start, end)}

    # ---------- 文件扫描与列表刷新 ----------

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
        """检测文件关联的国家 tag，返回去重后的列表；无则返回空列表。

        检测来源（按优先级）：
          1. history/countries 文件名前缀（"A24 - Civil War.txt" → A24）
          2. common/countries 文件名为裸 tag（"14K.txt" → 14K）
          3. 文件名末尾大写标记（TFR_characters_A24.txt / TFR_ideas_APA.txt → A24/APA）
          4. common/country_tags 顶层 TAG = "..." 赋值（该文件夹专属）
          5. 内容模式：country = TAG / ideas = { TAG = {
        """
        import re
        rel = (file_path or "").replace("\\", "/")
        base = os.path.basename(file_path or "")
        stem = os.path.splitext(base)[0]
        # 国家 tag：2-4 位大写字母/数字，至少含一个字母
        tag = r'((?=[A-Z0-9]*[A-Z])[A-Z0-9]{2,4})'

        # 1) history/countries / history/units：文件名前缀即 tag
        #    "A24 - Civil War.txt" → A24；"APA_2020.txt" → APA（取下划线/连字符前的首段）
        if "/history/countries/" in rel or "/history/units/" in rel:
            m = re.match(tag + r'\b', stem)
            if m:
                return [m.group(1)]
            first = re.split(r'[-_]', stem, maxsplit=1)[0]
            if re.fullmatch(tag, first):
                return [first]

        # 2) common/countries：文件名为裸 tag
        if "/common/countries/" in rel:
            m = re.fullmatch(tag, stem)
            if m:
                return [m.group(1)]

        # 3) 文件名末尾大写标记
        m = re.search(r'_' + tag + r'$', stem)
        if m:
            return [m.group(1)]

        # 3.5) 文件名前缀 tag（内容目录通用）：TAG_xxx / TAG(xxx) / TAG-xxx / 裸 TAG
        #      "ALS_ideas.txt" → ALS；"AFA(Ethiopia liberalism).txt" → AFA；"BDY_.txt" → BDY
        m = re.match(r'^' + tag + r'(?=[_\-\.(（]|$)', stem)
        if m:
            return [m.group(1)]

        if not content:
            return []

        tags = []
        # 4) country_tags：顶层 TAG = "..." 赋值
        if "/common/country_tags/" in rel:
            for m in re.finditer(r'^\s*' + tag + r'\s*=', content, re.M):
                tags.append(m.group(1))
            return tags
        # 5) 内容模式
        for m in re.finditer(r'\bcountry\s*=\s*' + tag + r'\b', content):
            tags.append(m.group(1))
        for m in re.finditer(r'\bideas\s*=\s*\{\s*' + tag + r'\s*=\s*\{', content):
            tags.append(m.group(1))

        seen = set()
        result = []
        for t in tags:
            if t not in seen:
                seen.add(t)
                result.append(t)
        return result

    @staticmethod
    def _read_file(fp):
        try:
            with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

    # ---------- 交互 ----------
    def _on_type_clicked(self, item):
        """切换内容类型。无文件模式下自动在右侧展示该类型全部实体。"""
        key = item.data(Qt.ItemDataRole.UserRole)
        self._current_type = key
        if self._nofile:
            self._refresh_entities()
            if self._nofile_entities:
                self.entity_gallery_nofile_requested.emit(
                    self._current_type, list(self._nofile_entities))
            return
        self._refresh_files()

    def _on_file_double_clicked(self, item):
        """双击文件块/实体项：国策→设计视图，实体→树编辑器定位，其余→树编辑器。"""
        if self._nofile:
            self._on_entity_double_clicked(item)
            return
        fp = item.data(Qt.ItemDataRole.UserRole)
        if not fp:
            return
        if self._current_type == "focus":
            self.focus_file_selected.emit(fp)
        elif self._current_type in ICON_RULES:
            self.entity_gallery_requested.emit(self._current_type, fp)
        else:
            self.generic_file_selected.emit(fp, None)

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
        # 右侧图形化展示当前类型全部实体（画廊）
        self.entity_gallery_nofile_requested.emit(
            self._current_type, list(self._nofile_entities))

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
            else:
                if is_icon:
                    gallery_action = menu.addAction("🖼 在右侧展示实体图标")
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
                            self._current_type, list(self._nofile_entities)))
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

    @staticmethod
    def _ask_file_name(parent, default_name=""):
        """询问文件名，自动补当前类型的扩展名。"""
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            parent, "新建文件", "文件名（含扩展名）:", text=default_name)
        if not ok or not name.strip():
            return None
        name = name.strip()
        if os.path.splitext(name)[1] == "":
            name += ".txt"
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
                f"「{self._current_type}」类型暂未制作相关功能，无法新建文件。")
            return

        template_path = self._base_template()
        if not template_path:
            QMessageBox.information(
                self, "提示",
                f"「{self._current_type}」类型暂未制作相关功能，无法新建文件。")
            return

        directory = self._new_file_directory()
        if not directory:
            return
        _, ext = self._type_folders_ext(self._current_type)
        default_name = os.path.splitext(os.path.basename(template_path))[0] + ext
        name = self._ask_file_name(self, default_name=default_name)
        if not name:
            return
        path = os.path.join(directory, name)
        if os.path.exists(path):
            QMessageBox.warning(self, "错误", f"文件已存在: {path}")
            return
        from template_scheduler import get_template_scheduler
        scheduler = get_template_scheduler()
        replacements = {}
        enabled_vars = scheduler.get_enabled_variables(template_path)
        if enabled_vars:
            from template_manager_dialog import TemplateApplyDialog
            vdlg = TemplateApplyDialog(enabled_vars, parent=self)
            if vdlg.exec() != QDialog.DialogCode.Accepted:
                return
            replacements = vdlg.get_values()
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
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write("")
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
                        with open(new_path, "w", encoding="utf-8-sig") as f:
                            f.write(applied)
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

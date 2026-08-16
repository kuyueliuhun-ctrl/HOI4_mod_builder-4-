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
SPECIAL_TYPE_KEYS = ("focus", "tech", "initial_oob")


# 内容类型定义：key -> (显示名, 图标, 相对 mod 目录的文件夹列表, 基础模板类型或 None, 扩展名或扩展名列表)
# 覆盖范围：对照游戏 common/ 全部子目录、events/history/interface/localisation/map/gfx 顶层目录
# 与 E:\mods 中 5 个成熟 mod 实际使用的目录整理（详见 覆盖检查报告.md）。
# 基础模板类型为 None 表示暂无「新建文件」模板（标注：无新建模板；仍可树形编辑）。
CONTENT_TYPES = [
    # ── 政治 / 意识形态 ──
    ("character", "角色", "👤", ["common/characters"], "character", ".txt"),
    ("idea", "民族精神", "💡", ["common/ideas"], "ideas_file", ".txt"),
    ("idea_tag", "理念标签", "🏷️", ["common/idea_tags"], None, ".txt"),
    ("ideologies", "意识形态", "☭", ["common/ideologies"], "意识形态", ".txt"),
    ("country_leader", "国家领袖", "👑", ["common/country_leader"], None, ".txt"),
    ("country_tag_aliases", "国家别名", "🔀", ["common/country_tag_aliases"], None, ".txt"),
    # ── 国策 ──
    ("focus", "国策", "🌳", ["common/national_focus"], "focus_tree", ".txt"),
    ("continuous_focus", "持续国策", "♾️", ["common/continuous_focus"], "持续国策", ".txt"),
    ("focus_inlay_windows", "国策内嵌窗口", "🪟", ["common/focus_inlay_windows"], None, ".txt"),
    # ── 事件 / 决议 / 科技 ──
    ("event", "事件", "📜", ["events"], "event", ".txt"),
    ("super_event", "超事件", "📢", ["events"], "event", ".txt"),
    ("decision", "决议", "📋", ["common/decisions"], "decision", ".txt"),
    ("tech", "科技", "🔬", ["common/technologies"], "tech", ".txt"),
    ("technology_sharing", "科技共享", "🔗", ["common/technology_sharing"], "科技共享", ".txt"),
    ("technology_tags", "科技标签", "🏷️", ["common/technology_tags"], "科技标签", ".txt"),
    ("equipment_groups", "装备组", "🗂️", ["common/equipment_groups"], None, ".txt"),
    # ── 地块 / 地图 ──
    ("state", "地块", "🗺️", ["history/states"], "地块", ".txt"),
    ("state_category", "地块类别", "🏙️", ["common/state_category"], "地块类别", ".txt"),
    ("strategic_region", "战略区域", "🗺️", ["map/strategicregions"], None, ".txt"),
    ("supply_area", "补给区域", "🚚", ["map/supplyareas"], None, ".txt"),
    ("map_terrain", "地图地形", "⛰️", ["map/terrain", "common/terrain"], None, ".txt"),
    # ── 剧本 / 历史 ──
    ("bookmark", "剧本", "🎬", ["common/bookmarks"], "bookmark", ".txt"),
    ("country_history", "国家设置", "🏛️", ["history/countries"], "country_history", ".txt"),
    ("advisor_assign", "顾问分配", "👔", ["history/general"], "顾问分配", ".txt"),
    # ── 脚本 / 触发 ──
    ("scripted", "脚本化效果", "🧩", ["common/scripted_effects", "common/scripted_triggers"], "scripted", ".txt"),
    ("scripted_localisation", "脚本化本地化", "🌐", ["common/scripted_localisation"], "脚本化本地化", ".txt"),
    ("scripted_guis", "脚本化界面", "🖼️", ["common/scripted_guis"], "脚本化界面", ".txt"),
    ("scripted_diplomatic_actions", "脚本化外交行动", "🕊️", ["common/scripted_diplomatic_actions"], None, ".txt"),
    ("script_constants", "脚本常量", "🔧", ["common/script_constants"], None, ".txt"),
    ("synchronized_dynamic_tokens", "同步动态令牌", "🔄", ["common/synchronized_dynamic_tokens"], None, ".txt"),
    ("on_actions", "触发动作", "⚙️", ["common/on_actions"], "触发动作", ".txt"),
    ("mtth", "MTTH调整", "⏱️", ["common/mtth"], None, ".txt"),
    ("generation", "生成器", "🧬", ["common/generation"], None, ".txt"),
    # ── 军事 / 部队 ──
    ("mio", "MIO", "🏭", ["common/military_industrial_organization"], "MIO", ".txt"),
    ("equipment", "装备", "🎯", ["common/units/equipment"], "equipment", ".txt"),
    ("unit", "兵种", "🛡️", ["common/units"], "unit", ".txt"),
    ("unit_tags", "部队标签", "🏷️", ["common/unit_tags"], "部队标签", ".txt"),
    ("unit_leader", "部队领袖", "🎖️", ["common/unit_leader"], None, ".txt"),
    ("unit_medals", "部队勋章", "🎗️", ["common/unit_medals"], "部队勋章", ".txt"),
    ("initial_oob", "初始部队", "🚁", ["history/units"], "初始部队", ".txt"),
    ("doctrine", "军事学说", "📚", ["common/doctrines"], "军事学说", ".txt"),
    ("special_project", "特殊计划", "🧪", ["common/special_projects"], "特殊计划", ".txt"),
    ("abilities", "特种作战能力", "💥", ["common/abilities"], "特种作战能力", ".txt"),
    ("aces", "王牌", "✈️", ["common/aces"], "王牌", ".txt"),
    ("operations", "行动", "🕵️", ["common/operations"], "行动", ".txt"),
    ("operation_phases", "行动阶段", "📈", ["common/operation_phases"], None, ".txt"),
    ("operation_tokens", "行动令牌", "🔑", ["common/operation_tokens"], None, ".txt"),
    ("raids", "突袭", "🎯", ["common/raids"], "突袭", ".txt"),
    ("medals", "勋章", "🎖️", ["common/medals"], "勋章", ".txt"),
    ("ribbons", "勋表", "🎗️", ["common/ribbons"], None, ".txt"),
    ("strategic_locations", "战略要地", "📍", ["common/strategic_locations"], None, ".txt"),
    # ── 内政 / 经济 ──
    ("buildings", "建筑", "🏢", ["common/buildings"], "建筑", ".txt"),
    ("resources", "资源", "⛏️", ["common/resources"], "资源", ".txt"),
    ("occupation_laws", "占领法", "⚖️", ["common/occupation_laws"], "占领法", ".txt"),
    ("resistance_compliance_modifiers", "抵抗顺从修正", "🚨", ["common/resistance_compliance_modifiers"], "抵抗顺从修正", ".txt"),
    ("resistance_activity", "抵抗活动", "🔥", ["common/resistance_activity"], None, ".txt"),
    ("difficulty_settings", "难度设置", "🎚️", ["common/difficulty_settings"], "难度设置", ".txt"),
    ("game_rules", "游戏规则", "📜", ["common/game_rules"], "游戏规则", ".txt"),
    ("timed_activities", "限时活动", "⏰", ["common/timed_activities"], "限时活动", ".txt"),
    # ── 外交 / 政治机制 ──
    ("factions", "派系", "🤝", ["common/factions"], None, ".txt"),
    ("opinion_modifiers", "关系修正", "💬", ["common/opinion_modifiers"], "opinion_modifier", ".txt"),
    ("peace_conference", "和平会议", "🕊️", ["common/peace_conference"], "和平会议", ".txt"),
    ("bop", "力量平衡", "⚖️", ["common/bop"], "力量平衡", ".txt"),
    # ── 情报 ──
    ("intelligence", "情报机构", "🕵️", ["common/intelligence_agencies"], "情报机构", ".txt"),
    ("intelligence_agency_upgrades", "情报机构升级", "📈", ["common/intelligence_agency_upgrades"], "情报机构升级", ".txt"),
    # ── 自治 / 修正 ──
    ("autonomy", "自治状态", "🤝", ["common/autonomous_states"], "自治状态", ".txt"),
    ("dynamic_modifier", "动态修正", "⚡", ["common/dynamic_modifiers"], "动态修正", ".txt"),
    ("modifier_definition", "修正量定义", "📐", ["common/modifier_definitions"], "修正量定义", ".txt"),
    ("modifier_type", "修正类型", "🧮", ["common/modifiers"], "修正类型", ".txt"),
    # ── AI ──
    ("ai_strategy", "AI战略计划", "🤖", ["common/ai_strategy_plans", "common/ai_strategy"], "ai_strategy", ".txt"),
    ("ai_division", "AI师模板", "🤖", ["common/ai_templates"], "ai_strategy", ".txt"),
    ("ai_areas", "AI区域", "🗺️", ["common/ai_areas"], None, ".txt"),
    ("ai_equipment", "AI装备", "🎯", ["common/ai_equipment"], None, ".txt"),
    ("ai_faction_theaters", "AI战区", "🎭", ["common/ai_faction_theaters"], None, ".txt"),
    ("ai_focuses", "AI国策", "🌳", ["common/ai_focuses"], None, ".txt"),
    ("ai_navy", "AI海军", "⚓", ["common/ai_navy"], None, ".txt"),
    # ── 国家定义 / 其他 ──
    ("country_setup", "国家定义", "🏷️", ["common/country_tags", "common/countries"], "国家定义", ".txt"),
    ("wargoal", "战争目标", "⚔️", ["common/wargoals"], "战争目标", ".txt"),
    ("names", "命名列表", "📛", ["common/names"], "命名列表", ".txt"),
    ("map_modes", "地图模式", "🗺️", ["common/map_modes"], "地图模式", ".txt"),
    ("scientist_traits", "科学家特质", "🔬", ["common/scientist_traits"], "科学家特质", ".txt"),
    ("scorers", "计分器", "📊", ["common/scorers"], None, ".txt"),
    ("collections", "藏品", "📦", ["common/collections"], None, ".txt"),
    ("frontend", "主界面前端", "🎨", ["common/frontend"], None, ".txt"),
    ("profile_backgrounds", "档案背景", "🖼️", ["common/profile_backgrounds"], None, ".txt"),
    ("profile_pictures", "档案图片", "📸", ["common/profile_pictures"], None, ".txt"),
    ("defines", "游戏定义", "⚙️", ["common/defines"], None, ".lua"),
    # ── 界面 / 图形 / 本地化 / 描述 ──
    ("gui", "界面机制", "🖥️", ["interface"], "gui", ".gui"),
    ("gui_edit", "GUI编辑", "🖼️", ["interface"], "gui", ".gui"),
    ("gfx_definition", "图形定义", "🎨", ["gfx"], None, ".gfx"),
    ("localisation", "本地化文件", "🌐", ["localisation"], None, [".yml", ".yaml"]),
    ("mod_descriptor", "Mod描述", "📄", ["."], None, ".mod"),
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

# 顶层块即实体的类型（不做「单包装块取直接子块」下沉）：
# 这些类型的文件顶层就是一个个实体定义（如力量平衡、限时活动、修正类型）。
TOP_LEVEL_ENTITY_TYPES = {"bop", "timed_activities", "modifiers", "generation"}

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
        # 游戏加载民族精神 picture 时自动补全 GFX_idea_ 前缀（裸名存储，如 generic_exploit_mines）
        "picture_unprefixed": True,
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
        "field": "",
        "picker_prefix": "",
        "dirs": ["gfx/interface/technologies"],
        "upload": {
            "subdir": "gfx/interface/technologies",
            "gfx_file": "technologies_mod.gfx",
            "gfx_name_pattern": "GFX_{name}_medium",
            "shine": False,
            "ref_mode": "sprite",
            "tech_special": True,
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
        elif content_type in TOP_LEVEL_ENTITY_TYPES:
            # 顶层块即实体（如力量平衡/限时活动：`name = { ... }` 不做单包装块下沉）
            es = cls._extract_top_entities(content)
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
    def _extract_top_entities(cls, content):
        """顶层块即实体：不做「单包装块取直接子块」的下沉。"""
        try:
            spans = cls._block_spans(cls._scan_blocks(content))
        except Exception:
            return []
        md = min(s[1] for s in spans) if spans else 0
        return [cls._make_generic_entity(content, s[2], s[3], s[0])
                for s in spans if s[1] == md]

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
        """通用实体提取：单顶层包装块取其直接子块；多顶层块时顶层块即实体；无块时整个文件视为一个实体。

        实体附带 icon/picture 字段探测（顶层字段中取 icon 或 picture），
        供全局图标索引渲染科技/占领法/建筑等类型的图标。
        """
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
                entities.append(cls._make_generic_entity(content, c[2], c[3], c[0]))
        if not entities:
            for s in tops:
                entities.append(cls._make_generic_entity(content, s[2], s[3], s[0]))
        return entities

    @classmethod
    def _make_generic_entity(cls, content, start, end, key):
        """构造通用实体字典：提取顶层 icon/picture 字段作为图标值。"""
        import math
        if math.isinf(end):
            end = len(content)
        block = content[start:end]
        fields = cls._top_level_fields(block)
        icon = fields.get("icon") or fields.get("picture") or ""
        return {"name": key, "key": key, "icon": icon, "range": (start, end)}

    @classmethod
    def _quick_focus_scan(cls, content):
        """轻量国策扫描：快速提取绘制所需字段（id/x/y/icon/cost/relative/prerequisite）。

        无文件模式跨文件合并绘制国策树时使用（完整 parse_pdx_script 解析
        整文件过慢，60 文件需数十秒）；编辑仍走 parse_focus_file 精确定位。

        Returns:
            dict: {focus_id: node}，node 结构与 FocusProcessor.process 输出兼容
                （basic/draw/abs_x/abs_y/_abs_calculated）。
        """
        import math
        try:
            spans = cls._block_spans(cls._scan_blocks(content))
        except Exception:
            return {}
        result = {}
        n = len(content)

        def _fnum(v, default=0.0):
            try:
                return float(v)
            except Exception:
                return default

        for key, _depth, start, end in spans:
            if key not in ("focus", "shared_focus", "joint_focus"):
                continue
            if math.isinf(end):
                end = n
            block = content[start:end]
            fields = cls._top_level_fields(block)
            fid = fields.get("id") or ""
            if not fid:
                continue
            # prerequisite 引用：定位实体内的 prerequisite 块（括号配对），提取其中的 focus 值
            refs = []
            pm = re.search(r'\bprerequisite\s*=\s*\{', block)
            if pm:
                inner = block[pm.end():]
                depth = 1
                j = 0
                while j < len(inner) and depth > 0:
                    if inner[j] == '{':
                        depth += 1
                    elif inner[j] == '}':
                        depth -= 1
                    j += 1
                seg = inner[:max(j - 1, 0)]
                refs = re.findall(r'\bfocus\s*=\s*([\w\.\-]+)', seg)
            node = {
                'basic': {
                    'id': fid,
                    'icon': fields.get("icon", ""),
                    'x': _fnum(fields.get("x")),
                    'y': _fnum(fields.get("y")),
                    'cost': fields.get("cost", 10),
                    'ai_will_do': {},
                    'search_filters': {},
                },
                'draw': {
                    'relative_position_id': fields.get("relative_position_id") or None,
                    'prerequisite': refs,
                    'mutually_exclusive': [],
                },
                'conditions': {},
                'rewards': {},
                'abs_x': 0.0,
                'abs_y': 0.0,
                '_abs_calculated': False,
            }
            result[fid] = node
        return result

    # ---------- 科技扫描（科技树视图用） ----------

    @staticmethod
    def _pair_block(content, brace_pos):
        """从 '{' 位置做括号配对，返回 (内部文本, 结束位置)。"""
        depth = 0
        i = brace_pos
        n = len(content)
        while i < n:
            c = content[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return content[brace_pos + 1:i], i
            i += 1
        return content[brace_pos + 1:], n

    @staticmethod
    def _tech_node_from_block(tid, block):
        """从单个科技块提取绘制科技树所需字段。"""
        fields = WorkbenchDock._top_level_fields(block)
        node = {
            "id": tid,
            "folder": "",
            "folder_x": None,
            "folder_y": None,
            "leads_to": [],
            "sub_techs": [],
            "allow_tags": [],
            "unresearchable": False,
            "cost": fields.get("research_cost") or fields.get("cost") or "",
            "start_year": fields.get("start_year") or "",
            "hidden": bool(fields.get("hidden")),
        }
        fm = re.search(r'\bfolder\s*=\s*\{', block)
        if fm:
            inner, _ = WorkbenchDock._pair_block(block, fm.end() - 1)
            nm = re.search(r'\bname\s*=\s*([\w\.\-]+)', inner)
            if nm:
                node["folder"] = nm.group(1)
            px = re.search(r'\bposition\s*=\s*\{[^}]*?\bx\s*=\s*(-?[\d\.]+)', inner)
            py = re.search(r'\bposition\s*=\s*\{[^}]*?\by\s*=\s*(-?[\d\.]+)', inner)
            if px:
                node["folder_x"] = float(px.group(1))
            if py:
                node["folder_y"] = float(py.group(1))
        for pm in re.finditer(r'\bpath\s*=\s*\{', block):
            inner, _ = WorkbenchDock._pair_block(block, pm.end() - 1)
            node["leads_to"].extend(
                re.findall(r'\bleads_to_tech\s*=\s*([\w\.\-]+)', inner))
        sm = re.search(r'\bsub_technologies\s*=\s*\{', block)
        if sm:
            inner, _ = WorkbenchDock._pair_block(block, sm.end() - 1)
            node["sub_techs"] = re.findall(r'[\w\.\-]+', inner)
        am = re.search(r'\ballow\s*=\s*\{', block)
        if am:
            inner, _ = WorkbenchDock._pair_block(block, am.end() - 1)
            compact = re.sub(r'\s+', ' ', inner)
            if re.search(r'\balways\s*=\s*no\b', compact):
                node["unresearchable"] = True
            for kw, label in (
                    ("has_completed_focus", "国策解锁"),
                    ("has_any_global_flag", "全局flag"),
                    ("has_any_country_flag", "国家flag"),
                    ("has_global_flag", "全局flag"),
                    ("has_country_flag", "国家flag"),
                    ("has_war", "战争条件"),
                    ("has_government", "政体条件"),
                    ("has_idea", "理念条件"),
                    ("has_trait", "特质条件"),
                    ("has_any_idea", "理念条件")):
                if re.search(r'\b' + kw + r'\b', compact) and label not in node["allow_tags"]:
                    node["allow_tags"].append(label)
        return node

    @classmethod
    def _quick_tech_scan(cls, content):
        """轻量科技扫描：快速提取绘制科技树所需字段。

        科技文件结构：technologies = { tech_id = { ... } }。
        提取：folder（树归属 + 锚点网格坐标）、path 连线（leads_to_tech）、
        sub_technologies（子科技列表）、allow 获取方式标注、cost/start_year。

        Returns:
            dict: {tech_id: node}
        """
        import math
        try:
            spans = cls._block_spans(cls._scan_blocks(content))
        except Exception:
            return {}
        result = {}
        n = len(content)
        found_wrapper = False
        for key, _depth, start, end in spans:
            if key != "technologies":
                continue
            found_wrapper = True
            if math.isinf(end):
                end = n
            outer = content[start:end]
            try:
                inner = cls._block_spans(cls._scan_blocks(outer))
            except Exception:
                continue
            for tid, d2, s2, e2 in inner:
                # 只取包装块的直接子块（深度 1）；enable_equipments/allow 等
                # 科技内部子块深度 >= 2，会被跳过
                if d2 != 1:
                    continue
                if math.isinf(e2):
                    e2 = len(outer)
                node = cls._tech_node_from_block(tid, outer[s2:e2])
                if node:
                    result[tid] = node
        if not found_wrapper:
            # 无 technologies 包装的旧式文件：直接以顶层块作为科技
            for tid, bdepth, s2, e2 in spans:
                if bdepth != 0:
                    continue
                if math.isinf(e2):
                    e2 = n
                node = cls._tech_node_from_block(tid, content[s2:e2])
                if node:
                    result[tid] = node
        return result

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
        elif self._current_type in ICON_RULES:
            self.entity_gallery_requested.emit(self._current_type, fp)
        else:
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
        # 初始部队（history/units）→ 直接弹设计器（无文件模式也支持）
        fp = meta.get("file", "") if isinstance(meta, dict) else ""
        norm_fp = (fp or "").replace("\\", "/")
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

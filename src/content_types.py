"""算法/数据层：内容类型注册表与图标规则（纯数据，无 Qt 控件）。

四层分离规范见 AGENTS.md §4.9：
- 本模块只保存 CONTENT_TYPES / ICON_RULES / SPECIAL_TYPE_KEYS 等纯数据；
- 供 workbench（UI）、focus_view（控制器）、api_server 等模块共享；
- 禁止 import PyQt6 控件类。
"""

SPECIAL_TYPE_KEYS = (
    "focus", "tech", "initial_oob", "bop", "character", "event",
    "ai_strategy_plans", "ai_strategy", "ai_division", "ai_equipment",
    "ai_navy", "ai_faction_theaters", "ai_areas", "ai_focuses",
)

# AI 内容类型：文件/实体双击直接走 generic_file_selected（主窗口再分发到专用/树编辑器）
AI_TYPES = {
    "ai_strategy_plans", "ai_strategy", "ai_division", "ai_equipment",
    "ai_navy", "ai_faction_theaters", "ai_areas", "ai_focuses",
    "ai_attitudes", "ai_personalities", "ai_peace", "mio_ai_weights",
}


# 内容类型定义：key -> (显示名, 图标, 相对 mod 目录的文件夹列表, 基础模板类型或 None, 扩展名或扩展名列表)
# 覆盖范围：对照游戏 common/ 全部子目录、events/history/interface/localisation/map/gfx 顶层目录
# 与 E:\mods 中 5 个成熟 mod 实际使用的目录整理（详见 docs/综合报告.md）。
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
    ("ai_strategy_plans", "AI战略计划", "🤖", ["common/ai_strategy_plans"], "ai_strategy_plan", ".txt"),
    ("ai_strategy", "AI战略倾向", "🤖", ["common/ai_strategy"], "ai_strategy", ".txt"),
    ("ai_division", "AI师模板", "🤖", ["common/ai_templates"], "ai_template", ".txt"),
    ("ai_areas", "AI区域", "🗺️", ["common/ai_areas"], "ai_area", ".txt"),
    ("ai_equipment", "AI装备", "🎯", ["common/ai_equipment"], "ai_equipment", ".txt"),
    ("ai_faction_theaters", "AI派系战区", "🎭", ["common/ai_faction_theaters"], "ai_faction_theater", ".txt"),
    ("ai_focuses", "AI科研权重", "🌳", ["common/ai_focuses"], "ai_focus", ".txt"),
    ("ai_navy", "AI海军", "⚓", ["common/ai_navy"], "ai_navy", ".txt"),
    ("ai_attitudes", "AI态度", "🧠", ["common/ai_attitudes"], None, ".txt"),
    ("ai_personalities", "AI人格", "🎭", ["common/ai_personalities"], None, ".txt"),
    ("ai_peace", "AI和平", "🕊️", ["common/ai_peace"], None, ".txt"),
    ("mio_ai_weights", "MIO AI权重", "🏭", ["common/mio_ai_weights"], None, ".txt"),
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


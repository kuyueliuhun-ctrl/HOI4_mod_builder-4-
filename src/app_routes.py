"""信号槽层（路由表）：文件路径 → 专用编辑器打开函数的纯路由配置。

四层分离规范见 AGENTS.md §4.9：
- 本模块只保存「路径子串 → 打开函数」的映射与匹配逻辑；
- 打开函数延迟 import 编辑器模块（避免启动时拉起重 UI）；
- 不持有 QWidget 状态，main_window 负责把自身作为 parent 传入。
"""

import os


def norm_path(path):
    """统一路径分隔符为 / 并返回小写无关的规范化字符串。"""
    return os.path.normpath(path).replace("\\", "/")


def match_subpath(norm, subpath):
    """判断规范化路径是否命中子路径（支持目录前缀与精确尾路径）。"""
    sub = subpath.strip("/")
    if "/" in sub:
        return "/%s/" % sub in norm or norm.endswith("/%s" % sub)
    return norm.endswith("/%s" % sub) or "/%s/" % sub in norm


class RouteContext:
    """一次路由打开所需的上下文（纯数据容器）。"""

    def __init__(self, file_path, mod_path="", hoi4_path="", entity_id=None,
                 parent=None):
        self.file_path = file_path
        self.mod_path = mod_path
        self.hoi4_path = hoi4_path
        self.entity_id = entity_id
        self.parent = parent


def _open_initial_oob(ctx):
    from initial_oob_editor import open_oob_designer
    open_oob_designer(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        parent=ctx.parent)


def _open_bop(ctx):
    from bop_editor_dialog import open_bop_editor
    open_bop_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        parent=ctx.parent)


def _open_event(ctx):
    from event_editor_dialog import open_event_editor
    open_event_editor(
        ctx.mod_path,
        ctx.hoi4_path,
        file_path=ctx.file_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_tech(ctx):
    from tech_editor_dialog import open_tech_editor
    open_tech_editor(
        ctx.mod_path,
        ctx.hoi4_path,
        file_path=ctx.file_path,
        tech_id=ctx.entity_id or "",
        parent=ctx.parent)


def _open_character(ctx):
    from character_editor_dialog import open_character_editor
    open_character_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_ai_plan(ctx):
    from ai_plan_editor_dialog import open_ai_plan_editor
    open_ai_plan_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_ai_strategy(ctx):
    from ai_strategy_editor_dialog import open_ai_strategy_editor
    open_ai_strategy_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_ai_template(ctx):
    from ai_template_editor_dialog import open_ai_template_editor
    open_ai_template_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_ai_navy(ctx):
    from ai_navy_editor_dialog import open_ai_navy_editor
    open_ai_navy_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_ai_faction_theater(ctx):
    from ai_faction_theater_editor_dialog import open_ai_faction_theater_list
    open_ai_faction_theater_list(
        ctx.mod_path, ctx.hoi4_path, parent=ctx.parent)


def _open_ai_equipment(ctx):
    from ai_equipment_editor_dialog import open_ai_equipment_editor
    open_ai_equipment_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_ai_area(ctx):
    from ai_area_editor_dialog import open_ai_area_editor
    open_ai_area_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_ai_focus(ctx):
    from ai_focus_editor_dialog import open_ai_focus_editor
    open_ai_focus_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_ai_attitudes(ctx):
    from ai_attitudes_editor_dialog import open_ai_attitudes_editor
    open_ai_attitudes_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_ai_personalities(ctx):
    from ai_personalities_editor_dialog import open_ai_personalities_editor
    open_ai_personalities_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_mio_ai_weights(ctx):
    from ai_mio_weights_editor_dialog import open_mio_ai_weights_editor
    open_mio_ai_weights_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_ai_peace(ctx):
    from ai_peace_editor_dialog import open_ai_peace_editor
    open_ai_peace_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_special_project(ctx):
    from special_project_editor_dialog import open_special_project_editor
    open_special_project_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_unit_tags(ctx):
    from unit_tags_editor_dialog import open_unit_tags_editor
    open_unit_tags_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_state_category(ctx):
    from state_category_editor_dialog import open_state_category_editor
    open_state_category_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_resources(ctx):
    from resources_editor_dialog import open_resources_editor
    open_resources_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


# 路由表：按顺序匹配，命中即返回（不继续 fallback）。
# 元组：(路径子串, 打开函数, 说明)
ROUTES = (
    ("history/units", _open_initial_oob, "初始部队（编制 + 地图放置）"),
    ("common/bop", _open_bop, "力量平衡专用编辑器"),
    ("events", _open_event, "事件专用编辑器"),
    ("common/technologies", _open_tech, "科技专用编辑器"),
    ("common/characters", _open_character, "角色专用编辑器"),
    ("common/ai_strategy_plans", _open_ai_plan, "AI 战略计划"),
    ("common/ai_strategy", _open_ai_strategy, "AI 战略倾向"),
    ("common/ai_templates", _open_ai_template, "AI 师模板"),
    ("common/ai_navy", _open_ai_navy, "AI 海军"),
    ("common/ai_faction_theaters", _open_ai_faction_theater, "AI 派系战区"),
    ("common/ai_equipment", _open_ai_equipment, "AI 装备"),
    ("common/ai_areas", _open_ai_area, "AI 区域"),
    ("common/ai_focuses", _open_ai_focus, "AI 科研权重"),
    ("common/ai_attitudes", _open_ai_attitudes, "AI 态度"),
    ("common/ai_personalities", _open_ai_personalities, "AI 人格"),
    ("common/mio_ai_weights", _open_mio_ai_weights, "MIO AI 权重"),
    ("common/ai_peace", _open_ai_peace, "AI 和平"),
    ("common/special_projects", _open_special_project, "特殊计划"),
    ("common/unit_tags", _open_unit_tags, "部队标签"),
    ("common/state_category", _open_state_category, "州类别"),
    ("common/resources", _open_resources, "资源"),
)


def find_route(file_path):
    """返回 (norm_path, route) 或 (norm_path, None)。norm_path 供调用方复用。"""
    norm = norm_path(file_path)
    for subpath, opener, _desc in ROUTES:
        if match_subpath(norm, subpath):
            return norm, (subpath, opener, _desc)
    return norm, None

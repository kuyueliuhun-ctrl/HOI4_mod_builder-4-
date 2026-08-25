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


def _open_equipment_groups(ctx):
    from equipment_groups_editor_dialog import open_equipment_groups_editor
    open_equipment_groups_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_script_constants(ctx):
    from script_constants_editor_dialog import open_script_constants_editor
    open_script_constants_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_scripted_localisation(ctx):
    from scripted_localisation_editor_dialog import (
        open_scripted_localisation_editor)
    open_scripted_localisation_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_technology_sharing(ctx):
    from technology_sharing_editor_dialog import open_technology_sharing_editor
    open_technology_sharing_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_strategic_locations(ctx):
    from strategic_locations_editor_dialog import (
        open_strategic_locations_editor)
    open_strategic_locations_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_opinion_modifiers(ctx):
    from opinion_modifiers_editor_dialog import open_opinion_modifiers_editor
    open_opinion_modifiers_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_wargoals(ctx):
    from wargoals_editor_dialog import open_wargoals_editor
    open_wargoals_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_difficulty_settings(ctx):
    from difficulty_settings_editor_dialog import (
        open_difficulty_settings_editor)
    open_difficulty_settings_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_game_rules(ctx):
    from game_rules_editor_dialog import open_game_rules_editor
    open_game_rules_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_autonomous_states(ctx):
    from autonomous_states_editor_dialog import open_autonomous_states_editor
    open_autonomous_states_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_country_tag_aliases(ctx):
    from country_tag_aliases_editor_dialog import (
        open_country_tag_aliases_editor)
    open_country_tag_aliases_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_bookmarks(ctx):
    from bookmarks_editor_dialog import open_bookmarks_editor
    open_bookmarks_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_modifiers(ctx):
    from modifiers_editor_dialog import open_modifiers_editor
    open_modifiers_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)



def _open_occupation_laws(ctx):
    from occupation_laws_editor_dialog import open_occupation_laws_editor
    open_occupation_laws_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_resistance_activity(ctx):
    from resistance_activity_editor_dialog import open_resistance_activity_editor
    open_resistance_activity_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_peace_conference(ctx):
    from peace_conference_editor_dialog import open_peace_conference_editor
    open_peace_conference_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_abilities(ctx):
    from abilities_editor_dialog import open_abilities_editor
    open_abilities_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_aces(ctx):
    from aces_editor_dialog import open_aces_editor
    open_aces_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_collections(ctx):
    from collections_editor_dialog import open_collections_editor
    open_collections_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_mtth(ctx):
    from mtth_editor_dialog import open_mtth_editor
    open_mtth_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_frontend(ctx):
    from frontend_editor_dialog import open_frontend_editor
    open_frontend_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_medals(ctx):
    from medals_editor_dialog import open_medals_editor
    open_medals_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_ribbons(ctx):
    from ribbons_editor_dialog import open_ribbons_editor
    open_ribbons_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_unit_medals(ctx):
    from unit_medals_editor_dialog import open_unit_medals_editor
    open_unit_medals_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_raids(ctx):
    from raids_editor_dialog import open_raids_editor
    open_raids_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_timed_activities(ctx):
    from timed_activities_editor_dialog import open_timed_activities_editor
    open_timed_activities_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_intelligence(ctx):
    from intelligence_editor_dialog import open_intelligence_editor
    open_intelligence_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_generation(ctx):
    from generation_editor_dialog import open_generation_editor
    open_generation_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_operation_phases(ctx):
    from operation_phases_editor_dialog import open_operation_phases_editor
    open_operation_phases_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_map_modes(ctx):
    from map_modes_editor_dialog import open_map_modes_editor
    open_map_modes_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_operation_tokens(ctx):
    from operation_tokens_editor_dialog import open_operation_tokens_editor
    open_operation_tokens_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_scripted_diplomatic_actions(ctx):
    from scripted_diplomatic_actions_editor_dialog import open_scripted_diplomatic_actions_editor
    open_scripted_diplomatic_actions_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_scorers(ctx):
    from scorers_editor_dialog import open_scorers_editor
    open_scorers_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_modifier_definitions(ctx):
    from modifier_definitions_editor_dialog import open_modifier_definitions_editor
    open_modifier_definitions_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_technology_tags(ctx):
    from technology_tags_editor_dialog import open_technology_tags_editor
    open_technology_tags_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_resistance_compliance(ctx):
    from resistance_compliance_editor_dialog import open_resistance_compliance_editor
    open_resistance_compliance_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_scripted_guis(ctx):
    from scripted_guis_editor_dialog import open_scripted_guis_editor
    open_scripted_guis_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_country_leader(ctx):
    from country_leader_editor_dialog import open_country_leader_editor
    open_country_leader_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_ideologies(ctx):
    from ideologies_editor_dialog import open_ideologies_editor
    open_ideologies_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_dynamic_modifiers(ctx):
    from dynamic_modifiers_editor_dialog import open_dynamic_modifiers_editor
    open_dynamic_modifiers_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_operations(ctx):
    from operations_editor_dialog import open_operations_editor
    open_operations_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_scientist_traits(ctx):
    from scientist_traits_editor_dialog import open_scientist_traits_editor
    open_scientist_traits_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_combat_tactics(ctx):
    from combat_tactics_editor_dialog import open_combat_tactics_editor
    open_combat_tactics_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_triggered_modifiers(ctx):
    from triggered_modifiers_editor_dialog import open_triggered_modifiers_editor
    open_triggered_modifiers_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_event_modifiers(ctx):
    from event_modifiers_editor_dialog import open_event_modifiers_editor
    open_event_modifiers_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_scripted_effects(ctx):
    from scripted_effects_editor_dialog import open_scripted_effects_editor
    open_scripted_effects_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_scripted_triggers(ctx):
    from scripted_triggers_editor_dialog import open_scripted_triggers_editor
    open_scripted_triggers_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_script_enums(ctx):
    from script_enums_editor_dialog import open_script_enums_editor
    open_script_enums_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_factions(ctx):
    from factions_editor_dialog import open_factions_editor
    open_factions_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_focus_inlay_windows(ctx):
    from focus_inlay_windows_editor_dialog import open_focus_inlay_windows_editor
    open_focus_inlay_windows_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_equipment_definitions(ctx):
    from equipment_definitions_editor_dialog import open_equipment_definitions_editor
    open_equipment_definitions_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_names(ctx):
    from names_editor_dialog import open_names_editor
    open_names_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_defines(ctx):
    from defines_editor_dialog import open_defines_editor
    open_defines_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_mio(ctx):
    from mio_editor_dialog import open_mio_editor
    open_mio_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_mio_policies(ctx):
    from mio_policy_editor_dialog import open_mio_policy_editor
    open_mio_policy_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_doctrine(ctx):
    from doctrine_editor_dialog import open_doctrine_editor
    open_doctrine_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_on_actions(ctx):
    from on_actions_editor_dialog import open_on_actions_editor
    open_on_actions_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_continuous_focus(ctx):
    from continuous_focus_editor_dialog import open_continuous_focus_editor
    open_continuous_focus_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_unit_leader_traits(ctx):
    from unit_leader_traits_editor_dialog import open_unit_leader_traits_editor
    open_unit_leader_traits_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_idea_tags(ctx):
    from idea_tags_editor_dialog import open_idea_tags_editor
    open_idea_tags_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_ideas(ctx):
    from ideas_editor_dialog import open_ideas_editor
    open_ideas_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_decisions(ctx):
    from decisions_editor_dialog import open_decisions_editor
    open_decisions_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_buildings(ctx):
    from buildings_editor_dialog import open_buildings_editor
    open_buildings_editor(
        ctx.file_path,
        mod_path=ctx.mod_path,
        hoi4_path=ctx.hoi4_path,
        entity_id=ctx.entity_id,
        parent=ctx.parent)


def _open_terrain(ctx):
    from terrain_editor_dialog import open_terrain_editor
    open_terrain_editor(
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
    ("common/equipment_groups", _open_equipment_groups, "装备组"),
    ("common/script_constants", _open_script_constants, "脚本常量"),
    ("common/scripted_localisation", _open_scripted_localisation, "脚本化本地化"),
    ("common/technology_sharing", _open_technology_sharing, "科技共享"),
    ("common/strategic_locations", _open_strategic_locations, "战略要地"),
    ("common/opinion_modifiers", _open_opinion_modifiers, "观点修正"),
    ("common/wargoals", _open_wargoals, "战争目标"),
    ("common/difficulty_settings", _open_difficulty_settings, "难度设置"),
    ("common/game_rules", _open_game_rules, "游戏规则"),
    ("common/autonomous_states", _open_autonomous_states, "自治状态"),
    ("common/country_tag_aliases", _open_country_tag_aliases, "国家别名"),
    ("common/bookmarks", _open_bookmarks, "剧本"),
    ("common/modifiers", _open_modifiers, "修正类型"),
    ("common/occupation_laws", _open_occupation_laws, "占领法"),
    ("common/resistance_activity", _open_resistance_activity, "抵抗活动"),
    ("common/peace_conference", _open_peace_conference, "和会"),
    ("common/abilities", _open_abilities, "特种能力"),
    ("common/aces", _open_aces, "王牌"),
    ("common/collections", _open_collections, "集合"),
    ("common/mtth", _open_mtth, "MTTH"),
    ("common/frontend", _open_frontend, "主界面"),
    ("common/medals", _open_medals, "奖章"),
    ("common/ribbons", _open_ribbons, "缎带"),
    ("common/unit_medals", _open_unit_medals, "部队勋章"),
    ("common/raids", _open_raids, "突袭"),
    ("common/timed_activities", _open_timed_activities, "限时活动"),
    ("common/intelligence", _open_intelligence, "情报"),
    ("common/generation", _open_generation, "生成"),
    ("common/operation_phases", _open_operation_phases, "行动阶段"),
    ("common/map_modes", _open_map_modes, "地图模式"),
    ("common/operation_tokens", _open_operation_tokens, "行动令牌"),
    ("common/scripted_diplomatic_actions", _open_scripted_diplomatic_actions, "脚本化外交行动"),
    ("common/scorers", _open_scorers, "计分器"),
    ("common/modifier_definitions", _open_modifier_definitions, "修正量定义"),
    ("common/technology_tags", _open_technology_tags, "科技标签"),
    ("common/resistance_compliance", _open_resistance_compliance, "抵抗合规"),
    ("common/scripted_guis", _open_scripted_guis, "脚本 GUI "),
    ("common/country_leader", _open_country_leader, "国家领袖"),
    ("common/ideologies", _open_ideologies, "意识形态"),
    ("common/dynamic_modifiers", _open_dynamic_modifiers, "动态修正"),
    ("common/operations", _open_operations, "间谍行动"),
    ("common/scientist_traits", _open_scientist_traits, "科学家特质"),
    ("common/combat_tactics.txt", _open_combat_tactics, "战术"),
    ("common/triggered_modifiers.txt", _open_triggered_modifiers, "触发修正"),
    ("common/event_modifiers.txt", _open_event_modifiers, "事件修正"),
    ("common/on_actions", _open_on_actions, "on_actions 事件"),
    ("common/continuous_focus", _open_continuous_focus, "持续国策"),
    ("common/unit_leader", _open_unit_leader_traits, "将领特质"),
    ("common/idea_tags", _open_idea_tags, "理念槽位"),
    ("common/ideas", _open_ideas, "理念"),
    ("common/decisions", _open_decisions, "决议"),
    ("common/buildings", _open_buildings, "建筑"),
    ("common/terrain", _open_terrain, "地形"),
    ("common/scripted_effects", _open_scripted_effects, "效果结构体（脚本库）"),
    ("common/scripted_triggers", _open_scripted_triggers, "条件结构体（脚本库）"),
    ("common/script_enums.txt", _open_script_enums, "枚举结构体（脚本库）"),
    ("common/factions", _open_factions, "派系"),
    ("common/focus_inlay_windows", _open_focus_inlay_windows, "国策内嵌窗口"),
    ("common/units/equipment", _open_equipment_definitions, "装备定义"),
    ("common/names", _open_names, "命名列表"),
    ("common/defines", _open_defines, "游戏定义"),
    ("common/military_industrial_organization/organizations", _open_mio, "MIO 编辑器"),
    ("common/military_industrial_organization/policies", _open_mio_policies, "MIO 方针"),
    ("common/doctrines", _open_doctrine, "学说编辑器"),
)


def find_route(file_path):
    """返回 (norm_path, route) 或 (norm_path, None)。norm_path 供调用方复用。"""
    norm = norm_path(file_path)
    for subpath, opener, _desc in ROUTES:
        if match_subpath(norm, subpath):
            return norm, (subpath, opener, _desc)
    return norm, None

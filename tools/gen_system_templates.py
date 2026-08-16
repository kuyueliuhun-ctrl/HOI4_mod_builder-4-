# -*- coding: utf-8 -*-
"""为新增内容类型生成 系统模板/<类型>/基础模板.txt 与 项目模板.txt。

数据来源：游戏目录 common/ 实际文件骨架（
E:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV）。
模板目录名必须与 workbench.CONTENT_TYPES 的中文显示名完全一致
（template_scheduler._system_type_map 按中文名映射类型 key）。

运行：python tools/gen_system_templates.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL_ROOT = os.path.join(ROOT, "templates", "系统模板")

# 类型中文名 -> (基础模板内容, 项目模板内容)
TEMPLATES = {
    "意识形态": (
        """ideologies = {
\tdemocratic = {
\t\ttypes = {
\t\t\tconservatism = {
\t\t\t}
\t\t}
\t\tcolor = { 0 0 255 }
\t\t# 意识形态规则（rules = { ... }）
\t}
}
""",
        """democratic = {
\ttypes = {
\t\tconservatism = {
\t\t}
\t}
\tcolor = { 0 0 255 }
\t# rules = { ... }
}
""",
    ),
    "持续国策": (
        """continuous_focus_palette = {
\tid = __FOCUS_PALETTE_ID__
\tcountry = {
\t\tfactor = 1
\t}
\tposition = { x = 50 y = 50 }
\tfocus = {
\t\tid = __FOCUS_ID__
\t\tcost = 1
\t}
}
""",
        """focus = {
\tid = __FOCUS_ID__
\tcost = 1
\t# 持续国策的逐日效果
}
""",
    ),
    "触发动作": (
        """on_actions = {
\ton_startup = {
\t\t# 游戏启动时触发
\t}
}
""",
        """on_custom_action = {
\t# 触发后执行的效果 / 事件
}
""",
    ),
    "占领法": (
        """law_garrison = {
\ttooltip = "OCCUPATION_LAW_GARRISON"
\ticon = "GFX_occupation_policy_icon_strip:1"
\tvisible = {
\t\talways = yes
\t}
\tavailable = {
\t\talways = yes
\t}
\tstate_modifier = {
\t}
}
""",
        """law_custom = {
\ttooltip = "OCCUPATION_LAW_CUSTOM"
\ticon = "GFX_occupation_policy_icon_strip:1"
\tvisible = {
\t\talways = yes
\t}
\tavailable = {
\t\talways = yes
\t}
\tstate_modifier = {
\t}
}
""",
    ),
    "建筑": (
        """buildings = {
\tarms_factory = {
\t\t# show_on_map = 1
\t\t# province_max = 1
\t\t# cost = 1
\t\t# time = 1
\t\t# icon = "GFX_building_arms_factory"
\t\t# country_modifiers = { }
\t\t# state_modifiers = { }
\t}
}
""",
        """arms_factory = {
\t# 建筑字段：cost / time / icon / 修正
}
""",
    ),
    "资源": (
        """resources = {
\toil = {
\t\ticon_frame = 1
\t\tcic = 0.125
\t\tconvoys = 0.1
\t}
}
""",
        """oil = {
\ticon_frame = 1
\tcic = 0.125
\tconvoys = 0.1
}
""",
    ),
    "地块类别": (
        """state_categories = {
\tcity = {
\t\tlocal_building_slots = 6
\t\tcolor = { 0 200 0 }
\t}
}
""",
        """city = {
\tlocal_building_slots = 6
\tcolor = { 0 200 0 }
}
""",
    ),
    "地形": (
        """categories = {
\tplains = {
\t\tcolor = { 127 127 127 }
\t\tmovement_cost = 1.0
\t}
}
""",
        """plains = {
\tcolor = { 127 127 127 }
\tmovement_cost = 1.0
}
""",
    ),
    "难度设置": (
        """difficulty_settings = {
\tdifficulty_setting = {
\t\tkey = "custom_diff_strong_ai"
\t\tmodifier = diff_strong_ai_generic
\t\tcountries = { }
\t\tmultiplier = 2.0
\t}
}
""",
        """difficulty_setting = {
\tkey = "custom_diff_setting"
\tmodifier = diff_strong_ai_generic
\tcountries = { }
\tmultiplier = 2.0
}
""",
    ),
    "部队标签": (
        """sub_unit_categories = {
\tcategory_front_line
\tcategory_all_infantry
\tcategory_all_armor
\tcategory_support_battalions
}
""",
        """category_custom
""",
    ),
    "科技标签": (
        """technology_categories = {
\tinfantry_weapons
\tarmor
\tair_tech
}
""",
        """custom_category
""",
    ),
    "行动": (
        """operation_custom = {
\ticon = GFX_operations_custom
\tname = operation_custom
\tdesc = operation_custom_desc
\tpriority = 0
\tdays = 35
\tnetwork_strength = 30
\toperatives = 1
\tvisible = {
\t}
\tavailable = {
\t}
\trequirements = {
\t}
\tequipment = {
\t}
\trisk_chance = 0.1
\texperience = 2
}
""",
        """operation_custom = {
\ticon = GFX_operations_custom
\tname = operation_custom
\tdesc = operation_custom_desc
\tpriority = 0
\tdays = 35
\tnetwork_strength = 30
\toperatives = 1
\tvisible = {
\t}
\tavailable = {
\t}
\trequirements = {
\t}
\tequipment = {
\t}
\trisk_chance = 0.1
\texperience = 2
}
""",
    ),
    "突袭": (
        """types = {
\tfacility_strike = {
\t\tdays_to_prepare = 90
\t\tai_will_do = {
\t\t\tbase = 2
\t\t}
\t}
}
""",
        """facility_strike = {
\tdays_to_prepare = 90
\tai_will_do = {
\t\tbase = 2
\t}
}
""",
    ),
    "力量平衡": (
        """BRA_political_military_balance = {
\tinitial_value = 0.0
\tleft_side = BRA_bop_left_side
\tright_side = BRA_bop_right_side
\tdecision_category = BRA_balance_of_power_category
\trange = {
\t\tid = BRA_unstable_government
\t\tmin = -0.1
\t\tmax = 0.1
\t\tmodifier = {
\t\t}
\t\ton_activate = {
\t\t}
\t\ton_deactivate = {
\t\t}
\t}
\tside = {
\t\tid = BRA_bop_left_side
\t\ticon = GFX_bop_left_side
\t\trange = {
\t\t\tid = BRA_left_range
\t\t\tmin = -1
\t\t\tmax = -0.1
\t\t}
\t}
}
""",
        """custom_power_balance = {
\tinitial_value = 0.0
\tleft_side = custom_left_side
\tright_side = custom_right_side
\tdecision_category = custom_bop_category
\trange = {
\t\tid = custom_unstable
\t\tmin = -0.1
\t\tmax = 0.1
\t}
\tside = {
\t\tid = custom_left_side
\t\ticon = GFX_bop_left_side
\t\trange = {
\t\t\tid = custom_left_range
\t\t\tmin = -1
\t\t\tmax = -0.1
\t\t}
\t}
}
""",
    ),
    "游戏规则": (
        """allow_wargoals = {
\tname = "RULE_ALLOW_WARGOALS"
\tgroup = "RULE_GROUP_GENERAL"
\ticon = "GFX_wargoals"
\toption = {
\t\tname = "LIMITED"
\t\ttext = "RULE_OPTION_LIMITED"
\t}
}
""",
        """custom_rule = {
\tname = "RULE_CUSTOM"
\tgroup = "RULE_GROUP_GENERAL"
\toption = {
\t\tname = "DEFAULT_OPTION"
\t\ttext = "RULE_OPTION_DEFAULT"
\t}
}
""",
    ),
    "王牌": (
        """modifiers = {
\tfighter_good = {
\t\ttype = { fighter heavy_fighter interceptor }
\t\tchance = 0.9
\t\teffect = {
\t\t\tair_attack_factor = 0.03
\t\t}
\t}
}
""",
        """custom_ace_modifier = {
\ttype = fighter
\tchance = 0.5
\teffect = {
\t\tair_attack_factor = 0.03
\t}
}
""",
    ),
    "特种作战能力": (
        """ability = {
\tforce_attack = {
\t\tname = ABILITY_FORCE_ATTACK
\t\tdesc = ABILITY_FORCE_ATTACK_DESC
\t\ttype = army_leader
\t\tallowed = {
\t\t}
\t\teffect = {
\t\t}
\t}
}
""",
        """custom_ability = {
\tname = ABILITY_CUSTOM
\tdesc = ABILITY_CUSTOM_DESC
\ttype = army_leader
\tallowed = {
\t}
\teffect = {
\t}
}
""",
    ),
    "修正类型": (
        """stability = {
\ticon = "GFX_stability"
\tdefault = 50
\t# 修正项：stability = { 图标与默认值 }
}
""",
        """custom_modifier = {
\ticon = "GFX_custom"
\t# 修正默认值
}
""",
    ),
    "科技共享": (
        """technology_sharing_group = {
\tid = custom_research
\tname = custom_research_name
\tdesc = custom_research_desc
\tpicture = GFX_custom_research
\tresearch_sharing_per_country_bonus = 0.1
\tavailable = {
\t}
}
""",
        """technology_sharing_group = {
\tid = custom_research
\tname = custom_research_name
\tdesc = custom_research_desc
\tpicture = GFX_custom_research
\tresearch_sharing_per_country_bonus = 0.1
\tavailable = {
\t}
}
""",
    ),
    "科学家特质": (
        """scientist_trait = {
\tid = custom_scientist
\tpicture = GFX_scientist_custom
\t# 对特殊计划生效的修正
\tmodifiers = {
\t}
}
""",
        """custom_scientist_trait = {
\tpicture = GFX_scientist_custom
\t# 对特殊计划生效的修正
}
""",
    ),
    "情报机构升级": (
        """branch_intelligence = {
\tupgrade_economy_civilian = {
\t\tpicture = GFX_agency_economy_department
\t\tframe = GFX_upgrade_frame_economy
\t\tai_will_do = {
\t\t\tfactor = 1
\t\t}
\t\tmodifiers_during_progress = {
\t\t}
\t}
}
""",
        """upgrade_custom = {
\tpicture = GFX_agency_custom
\tframe = GFX_upgrade_frame_custom
\tai_will_do = {
\t\tfactor = 1
\t}
\tmodifiers_during_progress = {
\t}
}
""",
    ),
    "脚本化本地化": (
        """defined_text = {
\tname = GetCustomName
\ttext = {
\t\ttrigger = {
\t\t\talways = yes
\t\t}
\t\tlocalization_key = CUSTOM_KEY
\t}
}
""",
        """defined_text = {
\tname = GetCustomName
\ttext = {
\t\ttrigger = {
\t\t\talways = yes
\t\t}
\t\tlocalization_key = CUSTOM_KEY
\t}
}
""",
    ),
    "命名列表": (
        """names = {
\tdivisions = {
\t\t"1st Division"
\t}
\tships = {
\t\t"HM Ship"
\t}
}
""",
        """divisions = {
\t"1st Division"
}
""",
    ),
    "勋章": (
        """medals = {
\tcustom_medal = {
\t\tname = "CAREER_PROFILE_CUSTOM_MEDAL"
\t\tdescription = "CAREER_PROFILE_CUSTOM_MEDAL_DESCRIPTION"
\t\tframes = { 1 1 2 }
\t}
}
""",
        """custom_medal = {
\tname = "CAREER_PROFILE_CUSTOM_MEDAL"
\tdescription = "CAREER_PROFILE_CUSTOM_MEDAL_DESCRIPTION"
\tframes = { 1 1 2 }
}
""",
    ),
    "部队勋章": (
        """unit_medals = {
\tcustom_unit_medal = {
\t\tname = "CAREER_PROFILE_CUSTOM_UNIT_MEDAL"
\t\tdescription = "CAREER_PROFILE_CUSTOM_UNIT_MEDAL_DESCRIPTION"
\t\tframes = { 1 1 1 }
\t}
}
""",
        """custom_unit_medal = {
\tname = "CAREER_PROFILE_CUSTOM_UNIT_MEDAL"
\tdescription = "CAREER_PROFILE_CUSTOM_UNIT_MEDAL_DESCRIPTION"
\tframes = { 1 1 1 }
}
""",
    ),
    "限时活动": (
        """stage_coup = {
\tequipment_need = {
\t\tinfantry_equipment = 1000
\t}
}
""",
        """stage_custom = {
\t# 活动阶段定义
}
""",
    ),
    "关系修正": (
        """opinion_modifiers = {
\tpositive = {
\t\tai_will_do = {
\t\t\tfactor = 1
\t\t}
\t}
}
""",
        """custom_opinion_modifier = {
\tai_will_do = {
\t\tfactor = 1
\t}
}
""",
    ),
    "抵抗顺从修正": (
        """compliance_15 = {
\ttype = core_compliance_modifier
\ticon = "GFX_occupation_compliance_modifier_strip:1"
\tthreshold = 15
\tmargin = 2
\tstate_modifier = {
\t}
}
""",
        """custom_compliance_modifier = {
\ttype = core_compliance_modifier
\ticon = "GFX_occupation_compliance_modifier_strip:1"
\tthreshold = 15
\tmargin = 2
\tstate_modifier = {
\t}
}
""",
    ),
    "和平会议": (
        """peace_conference = {
\t# 和会阶段与选项
}
""",
        """peace_conference = {
\t# 和会阶段与选项
}
""",
    ),
}


def main():
    created = 0
    skipped = 0
    for cat, (base, node) in TEMPLATES.items():
        cat_dir = os.path.join(TPL_ROOT, cat)
        os.makedirs(cat_dir, exist_ok=True)
        for fname, content in (("基础模板.txt", base), ("项目模板.txt", node)):
            fp = os.path.join(cat_dir, fname)
            if os.path.exists(fp):
                skipped += 1
                continue
            with open(fp, "w", encoding="utf-8") as f:
                f.write(content)
            created += 1
    print(f"创建 {created} 个模板文件，跳过 {skipped} 个已存在文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())

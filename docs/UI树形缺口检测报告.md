# UI 树形缺口检测报告

> 由 `ui_gap_probe.py` 自动生成：以通用树形编辑器内容为基准，检测专用 UI 未展示/未编辑的词条。

汇总：缺失顶层词条/块 **133** 条，缺失嵌套词条/块 **3577** 条。

| 类型 | 扫描文件 | 缺失顶层条数 | 缺失嵌套条数 |
| --- | --- | --- | --- |
| 力量平衡工作台 | 10 | 0 | 0 |
| 角色编辑器 | 10 | 0 | 0 |
| 国家历史文件（变体/顾问等） | 10 | 0 | 890 |
| 事件编辑器 | 10 | 0 | 0 |
| 国策/科技画布（focus） | 10 | 133 | 2603 |
| 地图编辑器（州） | 10 | 0 | 84 |
| 科技编辑器 | 10 | 0 | 0 |

## 力量平衡工作台（bop）

> 说明：区间/势力/修正/决议表单全覆盖；动作块位于 common/decisions 文件，由 BOP 编辑器写回

扫描文件：10

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

（无缺口）


## 角色编辑器（character）

> 说明：portraits 表可编辑任意 scope/size/texture；role 已知字段可编辑；未知行保留原样；未知块（含 instance = { ... }）经 ScriptBlockEditorDialog 结构化编辑并写回（2026-08-23 复核：--max-files 0 缺口=0，无豁免）

扫描文件：10

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

（无缺口）


## 国家历史文件（变体/顾问等）（country_history）

> 说明：变体（模块/升级）由三设计器覆盖；其余块走树编辑器，逐步收敛（收敛计划挂 docs/整合计划.md 通用类型 F 批）

扫描文件：10

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

总缺失条数：**890**

##### history/countries

```text
history/countries  (x890) {
    1939  (x152) {
        1  (x152) {
            1  (x152) {
                IF  (x53) {
                    add_dynamic_modifier  (x2) {
                        modifier  (x1)
                    }
                    complete_national_focus  (x32)
                    diplomatic_relation  (x12) {
                        active  (x3)
                        country  (x3)
                        relation  (x3)
                    }
                    limit  (x5) {
                        NOT  (x2) {
                            has_dlc  (x1)
                        }
                        has_dlc  (x1)
                    }
                }
                add_command_power  (x1)
                add_political_power  (x1)
                complete_national_focus  (x18)
                complete_special_project  (x9) {
                    project  (x3)
                    sp_air_radar  (x3)
                }
                if  (x9) {
                    else  (x5) {
                        set_air_oob  (x1)
                        set_technology  (x3) {
                            CAS1  (x1)
                            early_fighter  (x1)
                        }
                    }
                    limit  (x2) {
                        has_dlc  (x1)
                    }
                    set_air_oob  (x1)
                }
                oob  (x1)
                set_grand_doctrine  (x6)
                set_politics  (x5) {
                    election_frequency  (x1)
                    elections_allowed  (x1)
                    last_election  (x1)
                    ruling_party  (x1)
                }
                set_popularities  (x4) {
                    communism  (x1)
                    fascism  (x1)
                    neutrality  (x1)
                }
                set_technology  (x41) {
                    advanced_machine_tools  (x3)
                    basic_machine_tools  (x3)
                    computing_machine  (x1)
                    construction1  (x3)
                    construction2  (x3)
                    dispersed_industry  (x3)
                    dispersed_industry2  (x3)
                    electronic_mechanical_engineering  (x3)
                    fuel_silos  (x2)
                    gw_artillery  (x2)
                    improved_machine_tools  (x3)
                    mechanical_computing  (x3)
                    radio  (x3)
                    support_weapons  (x1)
                    tech_recon  (x1)
                    tech_support  (x1)
                }
            }
        }
    }
    IF  (x274) {
        add_dynamic_modifier  (x4) {
            modifier  (x2)
        }
        add_ideas  (x3)
        clamp_variable  (x4) {
            max  (x1)
            min  (x1)
            var  (x1)
        }
        division_template  (x24) {
            force_allow_recruiting  (x1)
            is_locked  (x1)
            name  (x1)
            override_model  (x1)
            regiments  (x19) {
                irregular_infantry  (x18) {
                    x  (x6)
                    y  (x6)
                }
            }
        }
        every_owned_state  (x18) {
            add_dynamic_modifier  (x4) {
                modifier  (x2)
            }
            limit  (x6) {
                OR  (x3) {
                    state  (x2)
                }
                is_owned_by  (x1)
            }
            set_variable  (x6) {
                AFG_state_development_production_speed  (x1)
                AFG_state_development_state_resources_factor  (x1)
                AFG_state_production_speed_infrastructure_factor  (x1)
            }
        }
        limit  (x5) {
            NOT  (x2) {
                has_dlc  (x1)
            }
            has_dlc  (x1)
        }
        recruit_character  (x62)
        set_country_flag  (x1)
        set_politics  (x10) {
            election_frequency  (x2)
            elections_allowed  (x2)
            last_election  (x2)
            ruling_party  (x2)
        }
        set_popularities  (x9) {
            communism  (x2)
            democratic  (x1)
            fascism  (x2)
            neutrality  (x2)
        }
        set_stability  (x1)
        set_technology  (x4) {
            gw_artillery  (x2)
        }
        set_variable  (x128) {
            AFG_1923_const_modifier_mobilization_laws_cost_factor  (x1)
            AFG_1923_const_modifier_political_advisor_cost_factor  (x1)
            AFG_1923_const_modifier_production_factory_efficiency_gain_factor  (x1)
            AFG_1923_const_modifier_production_factory_max_efficiency_factor  (x1)
            AFG_1923_const_modifier_production_speed_industrial_complex_factor  (x1)
            AFG_1923_const_modifier_research_speed_factor  (x1)
            AFG_1923_const_modifier_stability_factor  (x1)
            AFG_acclimatization_cold_climate_gain_factor  (x2)
            AFG_acclimatization_hot_climate_gain_factor  (x2)
            AFG_amanullah_modifier_core_attack_factor  (x1)
            AFG_amanullah_modifier_core_defense_factor  (x1)
            AFG_amanullah_modifier_fascism_drift  (x1)
            AFG_amanullah_modifier_stability_factor  (x1)
            AFG_army_armor_attack_factor  (x1)
            AFG_army_armor_defence_factor  (x1)
            AFG_army_artillery_attack_factor  (x1)
            AFG_army_artillery_defence_factor  (x1)
            AFG_army_attack_factor  (x1)
            AFG_army_core_defence_factor  (x2)
            AFG_army_defence_factor  (x1)
            AFG_army_experience_gain_army_factor  (x1)
            AFG_army_org_factor  (x1)
            AFG_army_supply_combat_penalties_on_core_factor  (x1)
            AFG_army_supply_consumption_factor  (x1)
            AFG_command_power_gain_mult  (x1)
            AFG_conscription  (x1)
            AFG_conscription_factor  (x2)
            AFG_economy_industrial_capacity_factor  (x1)
            AFG_economy_production_efficiency_gain_factor  (x1)
            AFG_economy_production_max_efficiency_factor  (x1)
            AFG_electrification_cooldown  (x1)
            AFG_experience_gain_army_factor  (x2)
            AFG_extra_marine_supply_grace  (x1)
            AFG_levy_cap  (x1)
            AFG_levy_cap_max  (x1)
            AFG_levy_cap_min  (x1)
            AFG_levy_deployed  (x1)
            AFG_look_to_the_past_modifier_core_attack_factor  (x1)
            AFG_look_to_the_past_modifier_core_defense_factor  (x1)
            AFG_look_to_the_past_modifier_research_speed_factor  (x1)
            AFG_look_to_the_past_modifier_stability_factor  (x1)
            AFG_look_to_the_past_modifier_war_support_factor  (x1)
            AFG_max_command_power_mult  (x1)
            AFG_max_planning_factor  (x2)
            AFG_modifier_army_sub_unit_cavalry_attack_factor  (x1)
            AFG_modifier_army_sub_unit_cavalry_defence_factor  (x1)
            AFG_modifier_army_sub_unit_cavalry_speed_factor  (x1)
            AFG_modifier_army_sub_unit_irregular_infantry_attack_factor  (x1)
            AFG_modifier_army_sub_unit_irregular_infantry_defence_factor  (x1)
            AFG_modifier_army_sub_unit_irregular_infantry_max_org_factor  (x1)
            AFG_modifier_army_sub_unit_irregular_infantry_speed_factor  (x1)
            AFG_planning_speed  (x2)
            AFG_special_forces_cap  (x1)
            AFG_special_forces_out_of_supply_factor  (x1)
            AFG_stability_factor_dm  (x1)
            AFG_training_time_factor  (x2)
        }
        set_war_support  (x1)
    }
    ITA  (x1) {
        give_guarantee  (x1)
    }
    add_ideas  (x1) {
        bba_AFA_skilled_desert_warriors  (x1)
    }
    if  (x192) {
        else  (x40) {
            set_technology  (x35) {
                CAS1  (x5)
                CAS2  (x5)
                fighter1  (x5)
                fighter2  (x5)
                fighter3  (x4)
                scout_plane1  (x1)
                strategic_bomber1  (x4)
                transport_plane2  (x1)
            }
        }
        limit  (x36) {
            NOT  (x10) {
                has_dlc  (x5)
            }
            has_dlc  (x9)
            not  (x2) {
                has_dlc  (x1)
            }
        }
        set_oob  (x2)
        set_technology  (x114) {
            aa_cannon_1  (x5)
            aa_hmg  (x5)
            aa_lmg  (x5)
            aircraft_construction  (x5)
            basic_battery  (x1)
            basic_light_tank  (x2)
            basic_light_tank_chassis  (x1)
            basic_medium_airframe  (x5)
            basic_ship_hull_submarine  (x1)
            basic_small_airframe  (x5)
            basic_submarine  (x1)
            basic_torpedo  (x1)
            early_battlecruiser  (x1)
            early_battleship  (x1)
            early_bomber  (x2)
            early_bombs  (x5)
            early_destroyer  (x1)
            early_fighter  (x2)
            early_heavy_cruiser  (x1)
            early_light_cruiser  (x1)
            early_ship_hull_cruiser  (x1)
            early_ship_hull_heavy  (x1)
            early_ship_hull_light  (x1)
            early_ship_hull_submarine  (x1)
            early_submarine  (x1)
            engines_1  (x5)
            engines_2  (x5)
            fighter1  (x1)
            guided_bombs  (x5)
            gwtank  (x2)
            gwtank_chassis  (x2)
            iw_large_airframe  (x5)
            iw_medium_airframe  (x5)
            iw_small_airframe  (x5)
            mtg_transport  (x1)
            naval_bomber1  (x2)
            strategic_bomber1  (x1)
            survivability_studies  (x5)
            transport  (x1)
        }
    }
    set_party_name  (x24) {
        ideology  (x8)
        long_name  (x8)
        name  (x8)
    }
    set_politics  (x28) {
        election_frequency  (x5)
        elections_allowed  (x9)
        last_election  (x5)
        ruling_party  (x9)
    }
    set_popularities  (x22) {
        communism  (x3)
        conservative  (x1)
        democratic  (x3)
        fascism  (x3)
        nationalist  (x4)
        neutrality  (x4)
        totalitarian_socialist  (x4)
    }
    set_technology  (x196) {
        basic_machine_tools  (x4)
        body_armor  (x5)
        camelry  (x1)
        camouflage  (x5)
        electronic_mechanical_engineering  (x4)
        gw_artillery  (x7)
        infantry_rifle_upgrade  (x5)
        infantry_weapons  (x5)
        infantry_weapons1  (x7)
        infantry_weapons2  (x5)
        infantry_weapons3  (x1)
        infantry_weapons4  (x1)
        infantry_weapons5  (x1)
        interwar_antiair  (x6)
        interwar_antitank  (x5)
        light_mechanized_infantry1  (x5)
        light_mechanized_infantry2  (x4)
        light_tank1  (x5)
        light_tank2  (x4)
        main_battle_tank1  (x5)
        main_battle_tank2  (x5)
        main_battle_tank3  (x5)
        marines  (x4)
        mechanised_infantry1  (x5)
        mechanised_infantry2  (x4)
        motorised_infantry  (x6)
        night_vision  (x5)
        paratroopers  (x5)
        self_propelled_aa1  (x5)
        support_weapons  (x5)
        support_weapons2  (x4)
        tank_destroyer1  (x5)
        tech_engineers  (x7)
        tech_field_hospital  (x5)
        tech_logistics_company  (x4)
        tech_maintenance_company  (x4)
        tech_military_police  (x6)
        tech_mountaineers  (x6)
        tech_recon  (x8)
        tech_signal_company  (x4)
        tech_support  (x8)
        tech_trucks  (x1)
    }
}
```


## 事件编辑器（event）

> 说明：事件块全部子字段经表单+结构化块+其他字段表覆盖；文件级其他字段表覆盖顶层常量/add_namespace 等非事件键；.** 即整子树

扫描文件：10

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

（无缺口）


## 国策/科技画布（focus）（focus）

> 说明：节点弹窗常用字段已覆盖；文件级其他键（style/search_filter_prios/常量）与 focus 内部未列嵌套字段仍经通用树编辑器兜底，属长期收敛项（挂 docs/整合计划.md 通用类型 F 批）

扫描文件：10

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

总缺失条数：**133**

##### common/national_focus

```text
common/national_focus  (x133) {
    style  (x133) {
        available  (x22)
        completed  (x22)
        current  (x22)
        default  (x1)
        name  (x22)
        unavailable  (x22)
    }
}
```

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

总缺失条数：**2603**

##### common/national_focus

```text
common/national_focus  (x2603) {
    focus_tree  (x414) {
        continuous_focus_position  (x6) {
            x  (x2)
            y  (x2)
        }
        country  (x32) {
            base  (x1)
            factor  (x5)
            modifier  (x20) {
                add  (x6)
                has_dlc  (x2)
                tag  (x6)
            }
        }
        default  (x4)
        focus  (x363) {
            allow_branch  (x95) {
                IF  (x34) {
                    NOT  (x14) {
                        has_completed_focus  (x7)
                    }
                    limit  (x16) {
                        has_game_rule  (x12) {
                            option  (x4)
                            rule  (x4)
                        }
                    }
                }
                OR  (x10) {
                    has_country_flag  (x5)
                    has_global_flag  (x2)
                }
                has_country_flag  (x13)
                has_dlc  (x3)
                has_global_flag  (x5)
            }
            available_if_capitulated  (x149)
            bypass_if_unavailable  (x1)
            cancelable  (x2)
            continue_if_invalid  (x28)
            dynamic  (x1)
            icon  (x15) {
                GFX_focus_AFG_helmand_river_authority  (x4) {
                    OR  (x3) {
                        has_government  (x2)
                    }
                }
                GFX_focus_APA_revolutionary_bill_of_rights  (x2) {
                    has_country_flag  (x1)
                }
                GFX_focus_APA_smash_capitalist_excesses  (x6) {
                    NOT  (x4) {
                        OR  (x3) {
                            has_country_flag  (x2)
                        }
                    }
                }
                GFX_focus_APA_unite_the_american_people  (x2) {
                    has_country_flag  (x1)
                }
                GFX_focus_generic_electrification  (x1)
            }
            will_lead_to_war_with  (x72)
        }
        id  (x6)
        initial_show_position  (x3) {
            x  (x1)
            y  (x1)
        }
    }
    joint_focus  (x1398) {
        ai_will_do  (x54) {
            base  (x8)
            factor  (x10)
            modifier  (x18) {
                add  (x6)
                original_tag  (x6)
            }
        }
        allow_branch  (x21) {
            OR  (x10) {
                original_tag  (x6)
                tag  (x2)
            }
            has_dlc  (x2)
            if  (x6) {
                NOT  (x3) {
                    has_completed_focus  (x2)
                }
                limit  (x2) {
                    original_tag  (x1)
                }
            }
            is_vichy_france  (x1)
        }
        available  (x86) {
            1021  (x3) {
                is_controlled_by  (x1)
                is_owned_by  (x1)
            }
            1066  (x2) {
                is_fully_controlled_by  (x1)
            }
            OR  (x53) {
                AST  (x3) {
                    has_capitulated  (x1)
                    has_country_flag  (x1)
                }
                INS  (x3) {
                    has_capitulated  (x1)
                    has_country_flag  (x1)
                }
                has_completed_focus  (x10)
                has_country_flag  (x10)
                has_government  (x2)
                is_major  (x1)
                original_tag  (x8)
            }
            has_war_with  (x1)
            is_in_faction  (x1)
            original_tag  (x5)
            tag  (x3)
        }
        available_if_capitulated  (x18)
        bypass  (x7)
        cancel_if_invalid  (x7)
        completion_reward  (x164) {
            IF  (x102) {
                CHI  (x4) {
                    add_opinion_modifier  (x3) {
                        modifier  (x1)
                        target  (x1)
                    }
                }
                IF  (x5) {
                    custom_effect_tooltip  (x1)
                    limit  (x2) {
                        has_idea  (x1)
                    }
                    remove_ideas  (x1)
                }
                ROOT  (x4) {
                    add_opinion_modifier  (x3) {
                        modifier  (x1)
                        target  (x1)
                    }
                }
                add_equipment_to_stockpile  (x4) {
                    amount  (x1)
                    producer  (x1)
                    type  (x1)
                }
                add_political_power  (x4)
                add_war_support  (x1)
                hidden_effect  (x21) {
                    division_template  (x20) {
                        division_names_group  (x1)
                        name  (x1)
                        priority  (x1)
                        regiments  (x16) {
                            infantry  (x15) {
                                x  (x5)
                                y  (x5)
                            }
                        }
                    }
                }
                limit  (x28) {
                    OR  (x21) {
                        tag  (x14)
                    }
                }
                random_owned_controlled_state  (x24) {
                    create_unit  (x20) {
                        " division_template = \"  (x2)
                        " start_experience_factor = 0  (x2) {
                            3"  (x2)
                        }
                        1  (x1) {
                              (x1)
                        }
                        2  (x1) {
                              (x1)
                        }
                        Anti-Japanese  (x4)
                        Volunteers  (x4)
                        division  (x2)
                        owner  (x2)
                    }
                    limit  (x3) {
                        ROOT  (x2) {
                            has_full_control_of_state  (x1)
                        }
                    }
                }
            }
            else  (x2) {
                custom_effect_tooltip  (x1)
            }
            hidden_effect  (x35) {
                if  (x34) {
                    AST  (x13) {
                        random_owned_state  (x12) {
                            add_building_construction  (x4) {
                                instant_build  (x1)
                                level  (x1)
                                type  (x1)
                            }
                            limit  (x7) {
                                free_building_slots  (x4) {
                                    building  (x1)
                                    include_locked  (x1)
                                    size  (x1)
                                }
                                is_controlled_by  (x1)
                                is_core_of  (x1)
                            }
                        }
                    }
                    INS  (x13) {
                        random_owned_state  (x12) {
                            add_building_construction  (x4) {
                                instant_build  (x1)
                                level  (x1)
                                type  (x1)
                            }
                            limit  (x7) {
                                free_building_slots  (x4) {
                                    building  (x1)
                                    include_locked  (x1)
                                    size  (x1)
                                }
                                is_controlled_by  (x1)
                                is_core_of  (x1)
                            }
                        }
                    }
                    limit  (x6) {
                        AST  (x2) {
                            has_country_flag  (x1)
                        }
                        INS  (x2) {
                            has_country_flag  (x1)
                        }
                    }
                }
            }
            if  (x17) {
                if  (x10) {
                    custom_effect_tooltip  (x2)
                    limit  (x6) {
                        AST  (x2) {
                            has_country_flag  (x1)
                        }
                        INS  (x2) {
                            has_country_flag  (x1)
                        }
                    }
                }
                limit  (x6) {
                    OR  (x5) {
                        AST  (x2) {
                            has_country_flag  (x1)
                        }
                        INS  (x2) {
                            has_country_flag  (x1)
                        }
                    }
                }
            }
        }
        completion_reward_joint_member  (x31) {
            add_doctrine_cost_reduction  (x5) {
                category  (x1)
                cost_reduction  (x1)
                name  (x1)
                uses  (x1)
            }
            custom_effect_tooltip  (x4)
            hidden_effect  (x18) {
                add_to_variable  (x14) {
                    ABDA_convoy_escort_efficiency  (x1)
                    ABDA_experience_gain_navy_unit_factor  (x1)
                    ABDA_repair_speed_factor  (x1)
                    ABDA_screen_defence_factor  (x1)
                    ABDA_screening_efficiency  (x1)
                    ABDA_submarine_attack_factor  (x1)
                    ABDA_submarine_defence_factor  (x1)
                }
            }
        }
        completion_reward_joint_originator  (x567) {
            CHI  (x4) {
                country_event  (x3) {
                    hours  (x1)
                    id  (x1)
                }
            }
            ENG  (x5) {
                country_event  (x2) {
                    id  (x1)
                }
                custom_effect_tooltip  (x2)
            }
            FRA  (x61) {
                add_ideas  (x1)
                division_template  (x34) {
                    name  (x1)
                    regiments  (x28) {
                        infantry  (x27) {
                            x  (x9)
                            y  (x9)
                        }
                    }
                    support  (x4) {
                        artillery  (x3) {
                            x  (x1)
                            y  (x1)
                        }
                    }
                }
                if  (x25) {
                    limit  (x7) {
                        any_owned_state  (x6) {
                            OR  (x4) {
                                is_core_of  (x3)
                            }
                            is_controlled_by  (x1)
                        }
                    }
                    random_owned_state  (x17) {
                        create_unit  (x10) {
                            " division_template = \"  (x1)
                            " start_experience_factor = 0  (x1) {
                                3"  (x1)
                            }
                            Corps  (x2)
                            Expéditionnaire  (x2)
                            count  (x1)
                            division  (x1)
                            owner  (x1)
                        }
                        limit  (x6) {
                            OR  (x4) {
                                is_core_of  (x3)
                            }
                            is_controlled_by  (x1)
                        }
                    }
                }
            }
            GXC  (x8) {
                add_opinion_modifier  (x6) {
                    modifier  (x2)
                    target  (x2)
                }
            }
            USA  (x2) {
                add_ideas  (x1)
            }
            add_doctrine_cost_reduction  (x5) {
                category  (x1)
                cost_reduction  (x1)
                name  (x1)
                uses  (x1)
            }
            add_dynamic_modifier  (x2) {
                modifier  (x1)
            }
            add_ideas  (x1)
            add_political_power  (x2)
            add_stability  (x2)
            add_tech_bonus  (x5) {
                bonus  (x1)
                category  (x1)
                name  (x1)
                uses  (x1)
            }
            add_war_support  (x2)
            custom_effect_tooltip  (x6)
            else  (x2) {
                custom_effect_tooltip  (x1)
            }
            every_country  (x14) {
                country_event  (x2) {
                    id  (x1)
                }
                limit  (x11) {
                    NOT  (x2) {
                        tag  (x1)
                    }
                    OR  (x7) {
                        tag  (x6)
                    }
                    is_in_faction_with  (x1)
                }
            }
            every_state  (x28) {
                add_building_construction  (x14) {
                    instant_build  (x2)
                    level  (x2)
                    province  (x6) {
                        all_provinces  (x2)
                        limit_to_naval_base  (x2)
                    }
                    type  (x2)
                }
                limit  (x12) {
                    OR  (x6) {
                        is_controlled_by  (x2)
                        is_owned_by  (x2)
                    }
                    is_core_of  (x1)
                    is_in_array  (x3) {
                        array  (x1)
                        value  (x1)
                    }
                }
            }
            hidden_effect  (x352) {
                add_to_variable  (x14) {
                    ABDA_convoy_escort_efficiency  (x1)
                    ABDA_experience_gain_navy_unit_factor  (x1)
                    ABDA_repair_speed_factor  (x1)
                    ABDA_screen_defence_factor  (x1)
                    ABDA_screening_efficiency  (x1)
                    ABDA_submarine_attack_factor  (x1)
                    ABDA_submarine_defence_factor  (x1)
                }
                division_template  (x20) {
                    division_names_group  (x1)
                    name  (x1)
                    priority  (x1)
                    regiments  (x16) {
                        infantry  (x15) {
                            x  (x5)
                            y  (x5)
                        }
                    }
                }
                else  (x70) {
                    if  (x69) {
                        AST  (x19) {
                            create_ship  (x18) {
                                name  (x6)
                                type  (x6)
                            }
                        }
                        HOL  (x19) {
                            create_ship  (x18) {
                                name  (x6)
                                type  (x6)
                            }
                        }
                        INS  (x19) {
                            create_ship  (x18) {
                                name  (x6)
                                type  (x6)
                            }
                        }
                        limit  (x9) {
                            AST  (x2) {
                                has_country_flag  (x1)
                            }
                            HOL  (x2) {
                                has_country_flag  (x1)
                            }
                            INS  (x2) {
                                has_country_flag  (x1)
                            }
                        }
                    }
                }
                every_country  (x13) {
                    country_event  (x2) {
                        id  (x1)
                    }
                    limit  (x10) {
                        NOT  (x4) {
                            has_country_flag  (x2)
                        }
                        OR  (x4) {
                            tag  (x3)
                        }
                        is_in_faction_with  (x1)
                    }
                }
                if  (x196) {
                    USA  (x193) {
                        if  (x192) {
                            create_ship  (x90) {
                                creator  (x18)
                                equipment_variant  (x18)
                                name  (x18)
                                type  (x18)
                            }
                            limit  (x9) {
                                AST  (x2) {
                                    has_country_flag  (x1)
                                }
                                HOL  (x2) {
                                    has_country_flag  (x1)
                                }
                                INS  (x2) {
                                    has_country_flag  (x1)
                                }
                            }
                            transfer_ship  (x90) {
                                exclude_refitting  (x18)
                                prefer_name  (x18)
                                target  (x18)
                                type  (x18)
                            }
                        }
                    }
                    limit  (x2) {
                        has_dlc  (x1)
                    }
                }
                random_country  (x17) {
                    limit  (x2) {
                        has_country_flag  (x1)
                    }
                    set_variable  (x14) {
                        global  (x7) {
                            ABDA_convoy_escort_efficiency_snapshot  (x1)
                            ABDA_experience_gain_navy_unit_factor_snapshot  (x1)
                            ABDA_repair_speed_factor_snapshot  (x1)
                            ABDA_screen_defence_factor_snapshot  (x1)
                            ABDA_screening_efficiency_snapshot  (x1)
                            ABDA_submarine_attack_factor_snapshot  (x1)
                            ABDA_submarine_defence_factor_snapshot  (x1)
                        }
                    }
                }
                set_variable  (x14) {
                    ABDA_convoy_escort_efficiency  (x1)
                    ABDA_experience_gain_navy_unit_factor  (x1)
                    ABDA_repair_speed_factor  (x1)
                    ABDA_screen_defence_factor  (x1)
                    ABDA_screening_efficiency  (x1)
                    ABDA_submarine_attack_factor  (x1)
                    ABDA_submarine_defence_factor  (x1)
                }
            }
            if  (x24) {
                if  (x15) {
                    custom_effect_tooltip  (x3)
                    limit  (x9) {
                        AST  (x2) {
                            has_country_flag  (x1)
                        }
                        HOL  (x2) {
                            has_country_flag  (x1)
                        }
                        INS  (x2) {
                            has_country_flag  (x1)
                        }
                    }
                }
                limit  (x8) {
                    OR  (x7) {
                        AST  (x2) {
                            has_country_flag  (x1)
                        }
                        HOL  (x2) {
                            has_country_flag  (x1)
                        }
                        INS  (x2) {
                            has_country_flag  (x1)
                        }
                    }
                }
            }
            random_owned_controlled_state  (x24) {
                create_unit  (x20) {
                    " division_template = \"  (x2)
                    " start_experience_factor = 0  (x2) {
                        3"  (x2)
                    }
                    1  (x1) {
                          (x1)
                    }
                    2  (x1) {
                          (x1)
                    }
                    Anti-Japanese  (x4)
                    Volunteers  (x4)
                    division  (x2)
                    owner  (x2)
                }
                limit  (x3) {
                    ROOT  (x2) {
                        has_full_control_of_state  (x1)
                    }
                }
            }
            set_country_flag  (x1)
        }
        continue_if_invalid  (x7)
        cost  (x18)
        icon  (x18)
        id  (x18)
        offset  (x235) {
            trigger  (x148) {
                INS  (x2) {
                    has_completed_focus  (x1)
                }
                has_completed_focus  (x22)
                has_game_rule  (x66) {
                    option  (x22)
                    rule  (x22)
                }
                tag  (x29)
            }
            x  (x29)
            y  (x29)
        }
        prerequisite  (x41) {
            focus  (x22)
        }
        relative_position_id  (x16)
        search_filters  (x36) {
            FOCUS_FILTER_POLITICAL  (x18)
        }
        text_icon  (x18)
        x  (x18)
        y  (x18)
    }
    shared_focus  (x791) {
        ai_will_do  (x36) {
            factor  (x18)
        }
        allow_branch  (x4) {
            NOT  (x2) {
                is_ally_with  (x1)
            }
            has_global_flag  (x1)
        }
        available  (x42) {
            1148  (x2) {
                is_controlled_by_ROOT_or_ally  (x1)
            }
            1149  (x2) {
                is_controlled_by_ROOT_or_ally  (x1)
            }
            1150  (x2) {
                is_controlled_by_ROOT_or_ally  (x1)
            }
            1332  (x2) {
                is_controlled_by_ROOT_or_ally  (x1)
            }
            1418  (x2) {
                is_controlled_by_ROOT_or_ally  (x1)
            }
            285  (x2) {
                is_fully_controlled_by  (x1)
            }
            520  (x2) {
                is_fully_controlled_by  (x1)
            }
            521  (x2) {
                is_fully_controlled_by  (x1)
            }
            524  (x2) {
                is_controlled_by_ROOT_or_ally  (x1)
            }
            INS  (x2) {
                surrender_progress  (x1)
            }
            PRC  (x2) {
                surrender_progress  (x1)
            }
            always  (x1)
            is_ally_with  (x1)
        }
        available_if_capitulated  (x18)
        bypass  (x17) {
            NOT  (x4) {
                is_ally_with  (x2)
            }
            OR  (x10) {
                NOT  (x9) {
                    285  (x2) {
                        is_fully_controlled_by  (x1)
                    }
                    520  (x2) {
                        is_fully_controlled_by  (x1)
                    }
                    521  (x2) {
                        is_fully_controlled_by  (x1)
                    }
                }
            }
        }
        completion_reward  (x509) {
            285  (x16) {
                add_building_construction  (x15) {
                    instant_build  (x3)
                    level  (x3)
                    province  (x3)
                    type  (x3)
                }
            }
            520  (x12) {
                add_building_construction  (x10) {
                    instant_build  (x2)
                    level  (x2)
                    province  (x2)
                    type  (x2)
                }
            }
            521  (x17) {
                add_building_construction  (x15) {
                    instant_build  (x3)
                    level  (x3)
                    province  (x3)
                    type  (x3)
                }
            }
            522  (x11) {
                add_building_construction  (x9) {
                    instant_build  (x2)
                    level  (x2)
                    province  (x1)
                    type  (x2)
                }
                add_extra_state_shared_building_slots  (x1)
            }
            711  (x12) {
                add_building_construction  (x9) {
                    instant_build  (x2)
                    level  (x2)
                    province  (x1)
                    type  (x2)
                }
                add_extra_state_shared_building_slots  (x1)
                add_manpower  (x1)
            }
            712  (x12) {
                add_building_construction  (x9) {
                    instant_build  (x2)
                    level  (x2)
                    province  (x1)
                    type  (x2)
                }
                add_extra_state_shared_building_slots  (x1)
                add_manpower  (x1)
            }
            CHI  (x2) {
                add_ideas  (x1)
            }
            INS  (x7) {
                add_manpower  (x1)
                add_timed_idea  (x3) {
                    days  (x1)
                    idea  (x1)
                }
                add_war_support  (x1)
                army_experience  (x1)
            }
            JAP  (x2) {
                add_ideas  (x1)
            }
            NZL  (x2) {
                add_ideas  (x1)
            }
            RAJ  (x2) {
                add_ideas  (x1)
            }
            add_debt_with_inflation  (x1)
            add_doctrine_cost_reduction  (x4) {
                category  (x1)
                cost_reduction  (x1)
                uses  (x1)
            }
            add_ideas  (x4)
            add_manpower  (x5)
            add_offsite_building  (x3) {
                level  (x1)
                type  (x1)
            }
            add_stability  (x1)
            add_timed_idea  (x9) {
                days  (x3)
                idea  (x3)
            }
            add_war_support  (x2)
            annex_country  (x3) {
                target  (x1)
                transfer_troops  (x1)
            }
            army_experience  (x4)
            custom_effect_tooltip  (x23)
            every_country  (x21) {
                add_offsite_building  (x9) {
                    level  (x3)
                    type  (x3)
                }
                limit  (x11) {
                    OR  (x9) {
                        original_tag  (x8)
                    }
                    is_ally_with  (x1)
                }
            }
            hidden_effect  (x248) {
                1148  (x18) {
                    create_unit  (x16) {
                        " start_experience_factor = 0  (x2) {
                            6 start_equipment_factor = 1  (x2) {
                                0"  (x2)
                            }
                        }
                        Australian  (x1)
                        Brigade  (x2)
                        Defense  (x1)
                        Shock  (x1)
                        Taiwan  (x1)
                        count  (x2)
                        division  (x2)
                        owner  (x2)
                    }
                }
                1332  (x9) {
                    create_unit  (x8) {
                        " start_experience_factor = 0  (x1) {
                            6 start_equipment_factor = 1  (x1) {
                                0"  (x1)
                            }
                        }
                        Brigade  (x1)
                        Gaijin  (x1)
                        Marines  (x1)
                        count  (x1)
                        division  (x1)
                        owner  (x1)
                    }
                }
                NZL  (x8) {
                    transfer_units_fraction  (x7) {
                        air_ratio  (x1)
                        army_ratio  (x1)
                        navy_ratio  (x1)
                        size  (x1)
                        stockpile_ratio  (x1)
                        target  (x1)
                    }
                }
                add_ideas  (x2)
                add_state_core  (x7)
                capital_scope  (x10) {
                    create_unit  (x9) {
                        " start_experience_factor = 0  (x1) {
                            6 start_equipment_factor = 1  (x1) {
                                0"  (x1)
                            }
                        }
                        Brigade  (x1)
                        Islands  (x1)
                        Pacific  (x1)
                        South  (x1)
                        count  (x1)
                        division  (x1)
                        owner  (x1)
                    }
                }
                damage_units  (x8) {
                    army  (x1)
                    damage  (x1)
                    navy  (x1)
                    org_damage  (x1)
                    ratio  (x1)
                    state  (x1)
                    str_damage  (x1)
                }
                division_template  (x164) {
                    name  (x4)
                    priority  (x4)
                    regiments  (x97) {
                        infantry  (x18) {
                            x  (x6)
                            y  (x6)
                        }
                        marine  (x18) {
                            x  (x6)
                            y  (x6)
                        }
                        mechanized  (x18) {
                            x  (x6)
                            y  (x6)
                        }
                        modern_armor  (x3) {
                            x  (x1)
                            y  (x1)
                        }
                        modern_sp_artillery_brigade  (x18) {
                            x  (x6)
                            y  (x6)
                        }
                        recce  (x18) {
                            x  (x6)
                            y  (x6)
                        }
                    }
                    support  (x55) {
                        anti_tank  (x9) {
                            x  (x3)
                            y  (x3)
                        }
                        artillery  (x9) {
                            x  (x3)
                            y  (x3)
                        }
                        engineer  (x12) {
                            x  (x4)
                            y  (x4)
                        }
                        recon  (x12) {
                            x  (x4)
                            y  (x4)
                        }
                        spaa_company  (x9) {
                            x  (x3)
                            y  (x3)
                        }
                    }
                }
                else  (x2) {
                    load_oob  (x1)
                }
                every_state  (x4) {
                    add_core_of  (x1)
                    limit  (x2) {
                        is_core_of  (x1)
                    }
                }
                if  (x4) {
                    limit  (x2) {
                        has_dlc  (x1)
                    }
                    load_oob  (x1)
                }
                load_oob  (x2)
            }
            navy_experience  (x1)
            news_event  (x3) {
                days  (x1)
                id  (x1)
            }
            random_owned_controlled_state  (x52) {
                add_building_construction  (x16) {
                    instant_build  (x4)
                    level  (x4)
                    type  (x4)
                }
                add_extra_state_shared_building_slots  (x4)
                limit  (x28) {
                    free_building_slots  (x16) {
                        building  (x4)
                        include_locked  (x4)
                        size  (x4)
                    }
                    is_core_of  (x4)
                    state_population  (x4)
                }
            }
            set_temp_variable  (x3) {
                value  (x1)
                var  (x1)
            }
            show_ideas_tooltip  (x2)
            transfer_state  (x7)
        }
        cost  (x18)
        icon  (x18)
        id  (x18)
        mutually_exclusive  (x8) {
            focus  (x4)
        }
        prerequisite  (x50) {
            focus  (x26)
        }
        relative_position_id  (x17)
        x  (x18)
        y  (x18)
    }
}
```


## 地图编辑器（州）（state）

> 说明：resources/victory_points/manpower/州名/州类别由右侧州字段表单覆盖；history.resources 为兼容 mod 写法；其余 state 嵌套字段（天气/历史/高级建筑等）仍可能走树编辑器，属长期收敛项（收敛计划挂 docs/整合计划.md 通用类型 F 批）

扫描文件：10

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

总缺失条数：**84**

##### history/states

```text
history/states  (x84) {
    state  (x84) {
        buildings_max_level_factor  (x4)
        history  (x24) {
            add_core_of  (x14)
        }
        local_supplies  (x7)
        provinces  (x49) {
            11492  (x1)
            11804  (x2)
            12562  (x2)
            12674  (x2)
            12689  (x1)
            12773  (x1)
            12793  (x1)
            13266  (x1)
            13267  (x1)
            13268  (x1)
            13271  (x1)
            13563  (x1)
            13564  (x1)
            13566  (x1)
            13570  (x1)
            13571  (x1)
            14300  (x1)
            1445  (x1)
            14880  (x1)
            1896  (x1)
            2071  (x1)
            3458  (x1)
            3482  (x1)
            3544  (x1)
            3838  (x2)
            402  (x2)
            4452  (x1)
            467  (x2)
            4755  (x1)
            4825  (x1)
            4861  (x2)
            4943  (x1)
            5098  (x1)
            524  (x2)
            6511  (x2)
            9400  (x1)
            9727  (x1)
            9816  (x1)
            9851  (x2)
        }
    }
}
```


## 科技编辑器（tech）

> 说明：画布只读拓扑，编辑能力由本编辑器承担；technologies 包装与零散 folder 顶层均由编辑器处理；allow/ai_will_do/category_* 走结构化块，其余字段进 OtherFieldsTable

扫描文件：10

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

（无缺口）


---
生成时间：由运行命令记录
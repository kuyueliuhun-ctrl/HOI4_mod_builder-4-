# UI 树形缺口检测报告

> 由 `ui_gap_probe.py` 自动生成：以通用树形编辑器内容为基准，检测专用 UI 未展示/未编辑的词条。

汇总：缺失顶层词条/块 **251** 条，缺失嵌套词条/块 **19075** 条。

| 类型 | 扫描文件 | 缺失顶层条数 | 缺失嵌套条数 |
| --- | --- | --- | --- |
| AI 区域编辑器 | 2 | 0 | 407 |
| AI 师模板编辑器 | 10 | 0 | 1973 |
| AI 装备编辑器 | 10 | 0 | 7652 |
| AI 派系战区编辑器 | 1 | 0 | 949 |
| AI 科研权重编辑器 | 6 | 0 | 331 |
| AI 海军编辑器 | 10 | 0 | 67 |
| AI 战略倾向编辑器 | 10 | 0 | 715 |
| AI 战略计划编辑器 | 10 | 0 | 1089 |
| 力量平衡工作台 | 10 | 0 | 0 |
| 角色编辑器 | 10 | 0 | 0 |
| 国家历史文件（变体/顾问等） | 10 | 0 | 890 |
| 事件编辑器 | 10 | 0 | 0 |
| 国策/科技画布（focus） | 10 | 133 | 2603 |
| 师编制/OOB 地编/设计器 | 10 | 118 | 0 |
| 地图编辑器（州） | 10 | 0 | 84 |
| 区域编辑器（战略区域） | 10 | 0 | 2307 |
| 区域编辑器（补给区域） | 2 | 0 | 8 |
| 科技编辑器 | 10 | 0 | 0 |

## AI 区域编辑器（ai_areas）

> 说明：areas 包装块下的区域实体由侧边栏处理

扫描文件：2

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

总缺失条数：**407**

##### common/ai_areas

```text
common/ai_areas  (x407) {
    areas  (x407) {
        UK  (x6) {
            strategic_regions  (x5) {
                1  (x1)
                2  (x1)
                3  (x1)
                4  (x1)
            }
        }
        UK_excluding_ni  (x5) {
            strategic_regions  (x4) {
                1  (x1)
                2  (x1)
                3  (x1)
            }
        }
        africa  (x6) {
            continents  (x4) {
                africa  (x2)
            }
        }
        albania  (x3) {
            strategic_regions  (x2) {
                24  (x1)
            }
        }
        andaman_islands  (x3) {
            strategic_regions  (x2) {
                101  (x1)
            }
        }
        asia  (x6) {
            continents  (x4) {
                asia  (x2)
            }
        }
        belgian_congo  (x5) {
            strategic_regions  (x4) {
                227  (x1)
                271  (x1)
                272  (x1)
            }
        }
        bismarck_sea_area  (x3) {
            strategic_regions  (x2) {
                84  (x1)
            }
        }
        borneo_area  (x3) {
            strategic_regions  (x2) {
                159  (x1)
            }
        }
        burma  (x9) {
            strategic_regions  (x8) {
                141  (x1)
                142  (x1)
                189  (x1)
                292  (x1)
                293  (x1)
                294  (x1)
                295  (x1)
            }
        }
        central_north_africa  (x4) {
            strategic_regions  (x3) {
                126  (x1)
                225  (x1)
            }
        }
        defend_moscow_zone  (x5) {
            strategic_regions  (x4) {
                133  (x1)
                137  (x1)
                150  (x1)
            }
        }
        east_africa  (x9) {
            strategic_regions  (x8) {
                17  (x1)
                181  (x1)
                185  (x1)
                216  (x1)
                217  (x1)
                273  (x1)
                274  (x1)
            }
        }
        east_china_mainland  (x3) {
            strategic_regions  (x2) {
                164  (x1)
            }
        }
        east_indies  (x17) {
            strategic_regions  (x15) {
                158  (x2)
                159  (x2)
                167  (x2)
                187  (x2)
                91  (x1)
                92  (x1)
                93  (x2)
                99  (x1)
            }
        }
        eastern_med_control_zone  (x4) {
            strategic_regions  (x3) {
                29  (x1)
                69  (x1)
            }
        }
        europe  (x6) {
            continents  (x4) {
                europe  (x2)
            }
        }
        greater_balkans  (x5) {
            strategic_regions  (x4) {
                24  (x1)
                25  (x1)
                26  (x1)
            }
        }
        guam_area  (x3) {
            strategic_regions  (x2) {
                94  (x1)
            }
        }
        home_islands  (x12) {
            strategic_regions  (x10) {
                154  (x2)
                160  (x2)
                299  (x1)
                300  (x1)
                76  (x2)
            }
        }
        home_islands_control_zone  (x4) {
            strategic_regions  (x3) {
                76  (x1)
                90  (x1)
            }
        }
        horn_of_africa  (x5) {
            strategic_regions  (x4) {
                17  (x1)
                273  (x1)
                274  (x1)
            }
        }
        italy  (x4) {
            strategic_regions  (x3) {
                21  (x1)
                23  (x1)
            }
        }
        italy_med_control_zone  (x6) {
            strategic_regions  (x5) {
                168  (x1)
                202  (x1)
                29  (x1)
                69  (x1)
            }
        }
        japan  (x5) {
            strategic_regions  (x4) {
                154  (x1)
                299  (x1)
                300  (x1)
            }
        }
        java_area  (x3) {
            strategic_regions  (x2) {
                158  (x1)
            }
        }
        just_denmark_excluding_greenland  (x3) {
            strategic_regions  (x2) {
                275  (x1)
            }
        }
        just_finland  (x5) {
            strategic_regions  (x4) {
                13  (x1)
                277  (x1)
                278  (x1)
            }
        }
        just_iceland  (x3) {
            strategic_regions  (x2) {
                161  (x1)
            }
        }
        just_norway  (x4) {
            strategic_regions  (x3) {
                11  (x1)
                191  (x1)
            }
        }
        just_philippines  (x6) {
            strategic_regions  (x4) {
                160  (x2)
            }
        }
        kokoda_trail_area  (x3) {
            strategic_regions  (x2) {
                167  (x1)
            }
        }
        kuban_landing_zone  (x5) {
            strategic_regions  (x4) {
                134  (x1)
                135  (x1)
                208  (x1)
            }
        }
        mainland_europe  (x44) {
            strategic_regions  (x42) {
                19  (x2)
                20  (x2)
                208  (x2)
                209  (x2)
                21  (x2)
                210  (x2)
                22  (x2)
                23  (x2)
                24  (x2)
                25  (x2)
                26  (x2)
                27  (x2)
                37  (x2)
                38  (x2)
                39  (x2)
                41  (x2)
                5  (x2)
                6  (x2)
                7  (x2)
                8  (x2)
            }
        }
        mariana_pacific_control_zone  (x4) {
            strategic_regions  (x3) {
                78  (x1)
                94  (x1)
            }
        }
        med_invasion_zone  (x5) {
            strategic_regions  (x4) {
                169  (x1)
                29  (x1)
                68  (x1)
            }
        }
        micronesia_pacific_control_zone  (x5) {
            strategic_regions  (x4) {
                83  (x1)
                84  (x1)
                97  (x1)
            }
        }
        middle_east  (x6) {
            continents  (x4) {
                middle_east  (x2)
            }
        }
        normandy_landing_zone  (x5) {
            strategic_regions  (x4) {
                19  (x1)
                20  (x1)
                208  (x1)
            }
        }
        north_africa  (x6) {
            strategic_regions  (x5) {
                126  (x1)
                128  (x1)
                182  (x1)
                225  (x1)
            }
        }
        north_america  (x6) {
            continents  (x4) {
                north_america  (x2)
            }
        }
        north_australia  (x3) {
            strategic_regions  (x2) {
                193  (x1)
            }
        }
        north_east_africa  (x5) {
            strategic_regions  (x4) {
                128  (x1)
                225  (x1)
                232  (x1)
            }
        }
        north_pacific_control_zone  (x4) {
            strategic_regions  (x3) {
                177  (x1)
                96  (x1)
            }
        }
        northern_india  (x5) {
            strategic_regions  (x4) {
                146  (x1)
                153  (x1)
                190  (x1)
            }
        }
        oceania  (x17) {
            strategic_regions  (x15) {
                156  (x2)
                157  (x2)
                193  (x1)
                194  (x1)
                81  (x2)
                84  (x1)
                86  (x2)
                98  (x2)
            }
        }
        pacific  (x38) {
            strategic_regions  (x36) {
                105  (x2)
                109  (x2)
                160  (x2)
                167  (x2)
                172  (x2)
                177  (x2)
                178  (x2)
                179  (x2)
                180  (x2)
                32  (x2)
                78  (x2)
                83  (x2)
                84  (x2)
                91  (x2)
                94  (x2)
                95  (x2)
                97  (x2)
            }
        }
        pearl_harbor_pacific_control_zone  (x5) {
            strategic_regions  (x4) {
                105  (x1)
                180  (x1)
                95  (x1)
            }
        }
        sardinia  (x3) {
            strategic_regions  (x2) {
                169  (x1)
            }
        }
        scandinavia  (x19) {
            strategic_regions  (x17) {
                10  (x2)
                11  (x2)
                12  (x2)
                13  (x2)
                191  (x2)
                192  (x2)
                276  (x1)
                277  (x1)
                278  (x1)
            }
        }
        south_america  (x6) {
            continents  (x4) {
                south_america  (x2)
            }
        }
        sub_saharan_africa  (x8) {
            strategic_regions  (x7) {
                139  (x1)
                140  (x1)
                183  (x1)
                184  (x1)
                223  (x1)
                226  (x1)
            }
        }
        suez  (x9) {
            strategic_regions  (x7) {
                128  (x2)
                232  (x1)
                28  (x2)
            }
        }
        sumatra_area  (x3) {
            strategic_regions  (x2) {
                187  (x1)
            }
        }
        taiwan_okinawa  (x3) {
            strategic_regions  (x2) {
                76  (x1)
            }
        }
        torch_landing_zone  (x4) {
            strategic_regions  (x3) {
                126  (x1)
                182  (x1)
            }
        }
        turkish_landing_zone  (x4) {
            strategic_regions  (x3) {
                129  (x1)
                25  (x1)
            }
        }
        us_west_coast  (x5) {
            strategic_regions  (x4) {
                75  (x1)
                78  (x1)
                80  (x1)
            }
        }
        vichy_mainland  (x3) {
            strategic_regions  (x2) {
                20  (x1)
            }
        }
        western_med_control_zone  (x4) {
            strategic_regions  (x3) {
                169  (x1)
                68  (x1)
            }
        }
        winter_war_front  (x5) {
            strategic_regions  (x4) {
                13  (x1)
                132  (x1)
                265  (x1)
            }
        }
    }
}
```


## AI 师模板编辑器（ai_division）

> 说明：target_template 接 DivisionEditor；其余脚本块仍可能缺失

扫描文件：10

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

总缺失条数：**1973**

##### common/ai_templates

```text
common/ai_templates  (x1973) {
    amphibious_mechanized_AST  (x17) {
        amphibious_mechanized_default_AST  (x13) {
            target_template  (x8) {
                regiments  (x3) {
                    amphibious_mechanized  (x1)
                    modern_sp_artillery_brigade  (x1)
                }
                support  (x4) {
                    engineer  (x1)
                    mot_recon  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        available_for  (x1) {
            AST  (x1)
        }
        upgrade_prio  (x3) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    anti_air_CHI  (x18) {
        anti_air_default_CHI  (x14) {
            target_template  (x9) {
                regiments  (x3) {
                    infantry  (x1)
                    spaa_brigade  (x1)
                }
                support  (x5) {
                    anti_air  (x1)
                    engineer  (x1)
                    recon  (x1)
                    spaa_company  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        available_for  (x1) {
            CHI  (x1)
        }
        upgrade_prio  (x3) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    anti_armor_GER  (x33) {
        available_for  (x1) {
            GER  (x1)
        }
        infantry_anti_armor_GER  (x20) {
            custom_icon  (x1)
            division_names_group  (x1)
            target_template  (x12) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    anti_tank_battery  (x1)
                }
                regiments  (x3) {
                    anti_tank_brigade  (x1)
                    infantry  (x1)
                }
                support  (x5) {
                    artillery  (x1)
                    engineer  (x1)
                    field_hospital  (x1)
                    recon  (x1)
                }
            }
            upgrade_prio  (x5) {
                base  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
        }
        upgrade_prio  (x12) {
            base  (x1)
            modifier  (x11) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                add  (x1)
                any_enemy_country  (x5) {
                    ROOT  (x4) {
                        estimated_intel_max_armor  (x3) {
                            tag  (x1)
                            value  (x1)
                        }
                    }
                }
                factor  (x1)
            }
        }
    }
    armor_ATW_BRN  (x14) {
        available_for  (x2) {
            ATW  (x1)
            BRN  (x1)
        }
        modern_armor_default_ATW_BRN  (x11) {
            target_template  (x6) {
                regiments  (x3) {
                    modern_armor  (x1)
                    motorized  (x1)
                }
                support  (x2) {
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x1) {
            factor  (x1)
        }
    }
    armor_ENG  (x161) {
        available_for  (x1) {
            ENG  (x1)
        }
        light_armor_2_ENG  (x27) {
            replace_at_match  (x1)
            replace_with  (x1)
            target_min_match  (x1)
            target_template  (x11) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    anti_tank_battery  (x1)
                }
                regiments  (x3) {
                    light_armor  (x1)
                    motorized  (x1)
                }
                support  (x4) {
                    engineer  (x1)
                    logistics_company  (x1)
                    mot_recon  (x1)
                }
            }
            upgrade_prio  (x12) {
                factor  (x1)
                modifier  (x10) {
                    OR  (x6) {
                        has_tech  (x4)
                    }
                    factor  (x2)
                }
            }
        }
        light_armor_default_ENG  (x16) {
            replace_at_match  (x1)
            replace_with  (x1)
            target_min_match  (x1)
            target_template  (x7) {
                regiments  (x3) {
                    light_armor  (x1)
                    motorized  (x1)
                }
                support  (x3) {
                    engineer  (x1)
                    mot_recon  (x1)
                }
            }
            upgrade_prio  (x5) {
                factor  (x1)
                modifier  (x3) {
                    date  (x1)
                    factor  (x1)
                }
            }
        }
        medium_armor_2_ENG  (x30) {
            replace_at_match  (x1)
            replace_with  (x1)
            target_min_match  (x1)
            target_template  (x16) {
                regimental_support  (x4) {
                    anti_air_battery  (x1)
                    anti_tank_battery  (x1)
                    mot_fire_support  (x1)
                }
                regiments  (x5) {
                    medium_armor  (x1)
                    mot_anti_air_brigade  (x1)
                    mot_artillery_brigade  (x1)
                    motorized  (x1)
                }
                support  (x6) {
                    engineer  (x1)
                    light_tank_recon  (x1)
                    logistics_company  (x1)
                    maintenance_company  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x10) {
                factor  (x1)
                modifier  (x8) {
                    OR  (x3) {
                        has_tech  (x2)
                    }
                    factor  (x2)
                    num_of_military_factories  (x1)
                }
            }
        }
        medium_armor_default_ENG  (x26) {
            replace_at_match  (x1)
            replace_with  (x1)
            target_min_match  (x1)
            target_template  (x12) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    anti_tank_battery  (x1)
                }
                regiments  (x4) {
                    medium_armor  (x1)
                    mot_artillery_brigade  (x1)
                    motorized  (x1)
                }
                support  (x4) {
                    engineer  (x1)
                    logistics_company  (x1)
                    mot_recon  (x1)
                }
            }
            upgrade_prio  (x10) {
                factor  (x1)
                modifier  (x8) {
                    OR  (x3) {
                        has_tech  (x2)
                    }
                    factor  (x2)
                    num_of_military_factories  (x1)
                }
            }
        }
        medium_armor_early_ENG  (x23) {
            replace_at_match  (x1)
            replace_with  (x1)
            target_min_match  (x1)
            target_template  (x12) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    anti_tank_battery  (x1)
                }
                regiments  (x4) {
                    light_armor  (x1)
                    medium_armor  (x1)
                    motorized  (x1)
                }
                support  (x4) {
                    engineer  (x1)
                    logistics_company  (x1)
                    mot_recon  (x1)
                }
            }
            upgrade_prio  (x7) {
                factor  (x1)
                modifier  (x5) {
                    OR  (x3) {
                        has_tech  (x2)
                    }
                    factor  (x1)
                }
            }
        }
        modern_armor_default_ENG  (x27) {
            target_template  (x16) {
                regimental_support  (x2) {
                    mot_fire_support  (x1)
                }
                regiments  (x7) {
                    mechanized  (x1)
                    modern_armor  (x1)
                    mot_anti_air_brigade  (x1)
                    mot_anti_tank_brigade  (x1)
                    mot_artillery_brigade  (x1)
                    motorized  (x1)
                }
                support  (x6) {
                    engineer  (x1)
                    light_tank_recon  (x1)
                    logistics_company  (x1)
                    maintenance_company  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x10) {
                factor  (x1)
                modifier  (x8) {
                    OR  (x3) {
                        has_tech  (x2)
                    }
                    factor  (x2)
                    num_of_military_factories  (x1)
                }
            }
        }
        upgrade_prio  (x11) {
            factor  (x1)
            modifier  (x10) {
                OR  (x6) {
                    has_tech  (x4)
                }
                factor  (x2)
            }
        }
    }
    armor_NSM  (x17) {
        available_for  (x1) {
            NSM  (x1)
        }
        modern_armor_default_NSM  (x15) {
            target_template  (x10) {
                regiments  (x5) {
                    mechanized  (x1)
                    modern_armor  (x1)
                    modern_sp_artillery_brigade  (x1)
                    motorized  (x1)
                }
                support  (x4) {
                    engineer  (x1)
                    logistics_company  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x1) {
            factor  (x1)
        }
    }
    armor_generic  (x161) {
        blocked_for  (x22) {
            APA  (x1)
            ATW  (x1)
            BRN  (x1)
            CAR  (x1)
            ENG  (x2)
            GER  (x1)
            HRL  (x1)
            HUN  (x1)
            ITA  (x1)
            JAP  (x1)
            NSM  (x1)
            POL  (x1)
            PRC  (x1)
            PTF  (x1)
            SIA  (x1)
            SOV  (x2)
            UKR  (x1)
            USA  (x2)
            USB  (x1)
        }
        light_armor_default  (x19) {
            can_upgrade_in_field  (x3) {
                has_equipment  (x2) {
                    light_tank_chassis  (x1)
                }
            }
            replace_at_match  (x1)
            target_min_match  (x1)
            target_template  (x9) {
                regiments  (x3) {
                    light_armor  (x1)
                    motorized  (x1)
                }
                support  (x5) {
                    anti_tank  (x1)
                    artillery  (x1)
                    engineer  (x1)
                    mot_recon  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        light_armor_early  (x21) {
            can_upgrade_in_field  (x3) {
                has_equipment  (x2) {
                    light_tank_chassis  (x1)
                }
            }
            replace_at_match  (x1)
            replace_with  (x1)
            target_min_match  (x1)
            target_template  (x10) {
                regimental_support  (x2) {
                    anti_tank_battery  (x1)
                }
                regiments  (x3) {
                    light_armor  (x1)
                    motorized  (x1)
                }
                support  (x4) {
                    artillery  (x1)
                    engineer  (x1)
                    mot_recon  (x1)
                }
            }
            upgrade_prio  (x4) {
                base  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        medium_armor_early  (x25) {
            replace_at_match  (x1)
            replace_with  (x1)
            target_min_match  (x1)
            target_template  (x14) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    anti_tank_battery  (x1)
                }
                regiments  (x4) {
                    light_armor  (x1)
                    medium_armor  (x1)
                    motorized  (x1)
                }
                support  (x6) {
                    artillery  (x1)
                    engineer  (x1)
                    logistics_company  (x1)
                    maintenance_company  (x1)
                    mot_recon  (x1)
                }
            }
            upgrade_prio  (x7) {
                base  (x1)
                modifier  (x5) {
                    OR  (x3) {
                        has_tech  (x2)
                    }
                    factor  (x1)
                }
            }
        }
        medium_armor_mid  (x28) {
            replace_at_match  (x1)
            replace_with  (x1)
            target_min_match  (x1)
            target_template  (x13) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    anti_tank_battery  (x1)
                }
                regiments  (x3) {
                    medium_armor  (x1)
                    motorized  (x1)
                }
                support  (x6) {
                    artillery  (x1)
                    engineer  (x1)
                    logistics_company  (x1)
                    maintenance_company  (x1)
                    mot_recon  (x1)
                }
            }
            upgrade_prio  (x11) {
                base  (x1)
                modifier  (x9) {
                    NOT  (x2) {
                        has_tech  (x1)
                    }
                    OR  (x3) {
                        has_tech  (x2)
                    }
                    factor  (x2)
                }
            }
        }
        modern_armor_default  (x34) {
            target_template  (x21) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    anti_tank_battery  (x1)
                }
                regiments  (x8) {
                    mechanized  (x2)
                    modern_armor  (x2)
                    modern_sp_artillery_brigade  (x2)
                }
                support  (x8) {
                    apc_company  (x1)
                    engineer  (x1)
                    logistics_company  (x1)
                    maintenance_company  (x1)
                    mot_recon  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x11) {
                base  (x1)
                factor  (x1)
                modifier  (x7) {
                    OR  (x3) {
                        has_tech  (x2)
                    }
                    factor  (x2)
                }
            }
        }
        upgrade_prio  (x12) {
            base  (x1)
            factor  (x1)
            modifier  (x10) {
                OR  (x6) {
                    has_tech  (x4)
                }
                factor  (x2)
            }
        }
    }
    armored_GER  (x135) {
        available_for  (x1) {
            GER  (x1)
        }
        light_armor_early_GER  (x21) {
            division_names_group  (x1)
            replace_at_match  (x1)
            replace_with  (x1)
            target_min_match  (x1)
            target_template  (x12) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    mot_fire_support  (x1)
                }
                regiments  (x3) {
                    light_armor  (x1)
                    motorized  (x1)
                }
                support  (x5) {
                    artillery  (x1)
                    engineer  (x1)
                    mot_recon  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x4) {
                base  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        medium_armor_early_GER  (x29) {
            can_upgrade_in_field  (x3) {
                has_equipment  (x2) {
                    light_tank_chassis  (x1)
                }
            }
            division_names_group  (x1)
            replace_at_match  (x1)
            replace_with  (x1)
            target_min_match  (x1)
            target_template  (x14) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    mot_fire_support  (x1)
                }
                regiments  (x4) {
                    light_armor  (x1)
                    medium_armor  (x1)
                    motorized  (x1)
                }
                support  (x6) {
                    artillery  (x1)
                    engineer  (x1)
                    light_tank_recon  (x1)
                    logistics_company  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x7) {
                base  (x1)
                modifier  (x5) {
                    OR  (x3) {
                        has_tech  (x2)
                    }
                    factor  (x1)
                }
            }
        }
        medium_armor_late_GER  (x24) {
            division_names_group  (x1)
            target_template  (x15) {
                regimental_support  (x4) {
                    anti_air_battery  (x1)
                    medium_tank_destroyer_support  (x1)
                    mot_fire_support  (x1)
                }
                regiments  (x4) {
                    medium_armor  (x1)
                    mot_artillery_brigade  (x1)
                    motorized  (x1)
                }
                support  (x6) {
                    engineer  (x1)
                    light_tank_recon  (x1)
                    logistics_company  (x1)
                    maintenance_company  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x7) {
                base  (x1)
                modifier  (x5) {
                    OR  (x3) {
                        has_tech  (x2)
                    }
                    factor  (x1)
                }
            }
        }
        medium_armor_mid_GER  (x26) {
            division_names_group  (x1)
            replace_at_match  (x1)
            replace_with  (x1)
            target_min_match  (x1)
            target_template  (x13) {
                regimental_support  (x4) {
                    anti_air_battery  (x1)
                    medium_tank_destroyer_support  (x1)
                    mot_fire_support  (x1)
                }
                regiments  (x4) {
                    medium_armor  (x1)
                    mot_artillery_brigade  (x1)
                    motorized  (x1)
                }
                support  (x4) {
                    engineer  (x1)
                    light_tank_recon  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x8) {
                base  (x1)
                modifier  (x6) {
                    OR  (x3) {
                        has_tech  (x2)
                    }
                    date  (x1)
                    factor  (x1)
                }
            }
        }
        modern_armor_default_GER  (x23) {
            target_template  (x15) {
                regimental_support  (x2) {
                    mot_fire_support  (x1)
                }
                regiments  (x6) {
                    mechanized  (x1)
                    medium_sp_anti_air_brigade  (x1)
                    medium_sp_artillery_brigade  (x1)
                    medium_tank_destroyer_brigade  (x1)
                    modern_armor  (x1)
                }
                support  (x6) {
                    engineer  (x1)
                    light_tank_recon  (x1)
                    logistics_company  (x1)
                    maintenance_company  (x1)
                    medium_flame_tank  (x1)
                }
            }
            upgrade_prio  (x7) {
                base  (x1)
                modifier  (x5) {
                    OR  (x3) {
                        has_tech  (x2)
                    }
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x11) {
            base  (x1)
            modifier  (x10) {
                OR  (x6) {
                    has_tech  (x4)
                }
                factor  (x2)
            }
        }
    }
    armored_PTF  (x19) {
        available_for  (x1) {
            PTF  (x1)
        }
        modern_armor_default_PTF  (x14) {
            target_template  (x8) {
                regiments  (x5) {
                    mechanized  (x1)
                    modern_armor  (x1)
                    modern_sp_artillery_brigade  (x1)
                    motorized  (x1)
                }
                support  (x2) {
                    engineer  (x1)
                }
            }
            upgrade_prio  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
        }
        upgrade_prio  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                has_tech  (x1)
            }
        }
    }
    garrison_ENG  (x18) {
        available_for  (x1) {
            ENG  (x1)
        }
        garrison_ENG  (x12) {
            custom_icon  (x1)
            reinforce_prio  (x1)
            target_template  (x5) {
                regiments  (x2) {
                    infantry  (x1)
                }
                support  (x2) {
                    engineer  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x5) {
            base  (x1)
            modifier  (x4) {
                NOT  (x2) {
                    ai_has_role_template  (x1)
                }
                factor  (x1)
            }
        }
    }
    garrison_GER  (x23) {
        available_for  (x1) {
            GER  (x1)
        }
        garrison_GER  (x13) {
            custom_icon  (x1)
            division_names_group  (x1)
            reinforce_prio  (x1)
            target_template  (x5) {
                regiments  (x2) {
                    infantry  (x1)
                }
                support  (x2) {
                    engineer  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x9) {
            factor  (x1)
            modifier  (x8) {
                NOT  (x2) {
                    ai_has_role_template  (x1)
                }
                OR  (x4) {
                    any_country  (x2) {
                        is_justifying_wargoal_against  (x1)
                    }
                    has_completed_focus  (x1)
                }
                factor  (x1)
            }
        }
    }
    garrison_generic  (x50) {
        blocked_for  (x17) {
            APA  (x1)
            BRN  (x1)
            ENG  (x1)
            GER  (x1)
            HRL  (x1)
            HUN  (x1)
            ITA  (x1)
            JAP  (x1)
            NSM  (x1)
            PTF  (x1)
            SIA  (x1)
            SOV  (x2)
            UKR  (x1)
            USA  (x2)
            USB  (x1)
        }
        garrison_generic  (x24) {
            custom_icon  (x2)
            reinforce_prio  (x2)
            target_template  (x10) {
                regiments  (x4) {
                    infantry  (x2)
                }
                support  (x4) {
                    engineer  (x2)
                }
            }
            upgrade_prio  (x8) {
                base  (x1)
                factor  (x1)
                modifier  (x4) {
                    factor  (x2)
                }
            }
        }
        upgrade_prio  (x9) {
            base  (x1)
            factor  (x1)
            modifier  (x7) {
                NOT  (x2) {
                    ai_has_role_template  (x1)
                }
                ai_has_role_template  (x1)
                factor  (x2)
            }
        }
    }
    hq_generic  (x9) {
        hq_default  (x8) {
            target_template  (x5) {
                regiments  (x2) {
                    infantry  (x1)
                }
                support  (x2) {
                    hq_support_company  (x1)
                }
            }
            upgrade_prio  (x2) {
                base  (x1)
            }
        }
        upgrade_prio  (x1) {
            base  (x1)
        }
    }
    infantry_APA  (x17) {
        available_for  (x1) {
            APA  (x1)
        }
        infantry_default_APA  (x13) {
            target_template  (x8) {
                regiments  (x3) {
                    modern_sp_artillery_brigade  (x1)
                    motorized  (x1)
                }
                support  (x4) {
                    logistics_company  (x1)
                    mot_recon  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x3) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    infantry_AST  (x18) {
        available_for  (x1) {
            AST  (x1)
        }
        infantry_default_AST  (x14) {
            target_template  (x9) {
                regiments  (x4) {
                    artillery_brigade  (x1)
                    mechanized  (x1)
                    motorized  (x1)
                }
                support  (x4) {
                    engineer  (x1)
                    mot_recon  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x3) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    infantry_BRN  (x16) {
        available_for  (x1) {
            BRN  (x1)
        }
        infantry_default_BRN  (x12) {
            target_template  (x7) {
                regiments  (x3) {
                    artillery_brigade  (x1)
                    motorized  (x1)
                }
                support  (x3) {
                    engineer  (x1)
                    mot_recon  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x3) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    infantry_CAC  (x18) {
        available_for  (x1) {
            CAC  (x1)
        }
        infantry_default_CAC  (x14) {
            target_template  (x9) {
                regiments  (x3) {
                    artillery_brigade  (x1)
                    motorized  (x1)
                }
                support  (x5) {
                    engineer  (x1)
                    logistics_company  (x1)
                    rocket_artillery  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x3) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    infantry_CHI  (x48) {
        available_for  (x18) {
            CHI  (x1)
            GDC  (x1)
            GSM  (x1)
            GXC  (x1)
            HBC  (x1)
            KHM  (x1)
            KUM  (x1)
            MAN  (x1)
            MEN  (x1)
            NXM  (x1)
            PRC  (x1)
            SHX  (x1)
            SIC  (x1)
            SIK  (x1)
            SND  (x1)
            XIC  (x1)
            XSM  (x1)
            YUN  (x1)
        }
        infantry_2_CHI  (x15) {
            target_template  (x9) {
                regimental_support  (x2) {
                    field_guns  (x1)
                }
                regiments  (x3) {
                    artillery_brigade  (x1)
                    infantry  (x1)
                }
                support  (x3) {
                    engineer  (x1)
                    recon  (x1)
                }
            }
            upgrade_prio  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    num_of_factories  (x1)
                }
            }
        }
        infantry_default_CHI  (x12) {
            target_template  (x7) {
                regimental_support  (x2) {
                    field_guns  (x1)
                }
                regiments  (x2) {
                    infantry  (x1)
                }
                support  (x2) {
                    engineer  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x3) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    infantry_ENG  (x40) {
        available_for  (x1) {
            ENG  (x1)
        }
        infantry_default_ENG  (x19) {
            replace_at_match  (x1)
            replace_with  (x1)
            target_min_match  (x1)
            target_template  (x11) {
                regimental_support  (x4) {
                    anti_tank_battery  (x1)
                    field_guns  (x1)
                    fire_support  (x1)
                }
                regiments  (x3) {
                    artillery_brigade  (x1)
                    infantry  (x1)
                }
                support  (x3) {
                    engineer  (x1)
                    recon  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        infantry_improved_ENG  (x17) {
            target_template  (x12) {
                regimental_support  (x4) {
                    anti_air_battery  (x1)
                    anti_tank_battery  (x1)
                    fire_support  (x1)
                }
                regiments  (x3) {
                    artillery_brigade  (x1)
                    infantry  (x1)
                }
                support  (x4) {
                    engineer  (x1)
                    field_hospital  (x1)
                    recon  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x3) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    infantry_GER  (x86) {
        available_for  (x1) {
            GER  (x1)
        }
        infantry_Upgrade_2_GER  (x24) {
            can_upgrade_in_field  (x3) {
                has_equipment  (x2) {
                    artillery_equipment  (x1)
                }
            }
            target_template  (x11) {
                regimental_support  (x3) {
                    field_guns  (x1)
                    mot_fire_support  (x1)
                }
                regiments  (x3) {
                    artillery_brigade  (x1)
                    infantry  (x1)
                }
                support  (x4) {
                    artillery  (x1)
                    engineer  (x1)
                    recon  (x1)
                }
            }
            upgrade_prio  (x9) {
                base  (x1)
                modifier  (x7) {
                    date  (x2)
                    factor  (x2)
                    has_war_with_major  (x1)
                }
            }
        }
        infantry_Upgrade_3_GER  (x23) {
            target_template  (x13) {
                regimental_support  (x5) {
                    anti_air_battery  (x1)
                    anti_tank_battery  (x1)
                    field_guns  (x1)
                    fire_support  (x1)
                }
                regiments  (x3) {
                    artillery_brigade  (x1)
                    infantry  (x1)
                }
                support  (x4) {
                    artillery  (x1)
                    engineer  (x1)
                    recon  (x1)
                }
            }
            upgrade_prio  (x9) {
                base  (x1)
                modifier  (x7) {
                    date  (x2)
                    factor  (x2)
                    has_war_with_major  (x1)
                }
            }
        }
        infantry_Upgrade_GER  (x18) {
            target_template  (x9) {
                regimental_support  (x2) {
                    mot_fire_support  (x1)
                }
                regiments  (x3) {
                    artillery_brigade  (x1)
                    infantry  (x1)
                }
                support  (x3) {
                    artillery  (x1)
                    engineer  (x1)
                }
            }
            upgrade_prio  (x8) {
                base  (x1)
                modifier  (x6) {
                    date  (x2)
                    factor  (x2)
                }
            }
        }
        infantry_default_GER  (x13) {
            target_template  (x10) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    fire_support  (x1)
                }
                regiments  (x3) {
                    artillery_brigade  (x1)
                    infantry  (x1)
                }
                support  (x3) {
                    artillery  (x1)
                    engineer  (x1)
                }
            }
            upgrade_prio  (x2) {
                base  (x1)
            }
        }
        upgrade_prio  (x7) {
            base  (x1)
            modifier  (x6) {
                NOT  (x4) {
                    has_tech  (x2)
                }
                factor  (x1)
            }
        }
    }
    infantry_GMA  (x16) {
        available_for  (x1) {
            GMA  (x1)
        }
        infantry_default_GMA  (x12) {
            target_template  (x7) {
                regiments  (x3) {
                    artillery_brigade  (x1)
                    motorized  (x1)
                }
                support  (x3) {
                    engineer  (x1)
                    mot_recon  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x3) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    infantry_NSM  (x15) {
        available_for  (x1) {
            NSM  (x1)
        }
        infantry_default_NSM  (x13) {
            target_template  (x8) {
                regiments  (x3) {
                    artillery_brigade  (x1)
                    motorized  (x1)
                }
                support  (x4) {
                    engineer  (x1)
                    logistics_company  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x1) {
            factor  (x1)
        }
    }
    infantry_PTF  (x18) {
        available_for  (x1) {
            PTF  (x1)
        }
        infantry_default_PTF  (x14) {
            target_template  (x9) {
                regiments  (x3) {
                    mechanized  (x1)
                    modern_sp_artillery_brigade  (x1)
                }
                support  (x5) {
                    logistics_company  (x1)
                    mot_recon  (x1)
                    rocket_artillery  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x3) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    infantry_generic  (x123) {
        blocked_for  (x36) {
            APA  (x1)
            BRN  (x1)
            CHI  (x1)
            ENG  (x2)
            FRA  (x1)
            GER  (x2)
            GXC  (x1)
            HRL  (x1)
            HUN  (x2)
            IRQ  (x1)
            ITA  (x2)
            JAP  (x2)
            MAN  (x1)
            MEN  (x1)
            NSM  (x1)
            POL  (x1)
            PRC  (x2)
            PTF  (x1)
            ROM  (x1)
            SHX  (x1)
            SIA  (x1)
            SIK  (x1)
            SOV  (x2)
            UKR  (x1)
            USA  (x2)
            USB  (x1)
            XSM  (x1)
            YUN  (x1)
        }
        infantry_default  (x23) {
            target_template  (x8) {
                regiments  (x3) {
                    artillery_brigade  (x1)
                    motorized  (x1)
                }
                support  (x4) {
                    engineer  (x1)
                    recon  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x14) {
                factor  (x1)
                modifier  (x12) {
                    factor  (x4)
                    is_major  (x1)
                    num_of_factories  (x2)
                    surrender_progress  (x1)
                }
            }
        }
        infantry_division_2  (x21) {
            target_template  (x6) {
                regiments  (x3) {
                    artillery  (x1)
                    motorized  (x1)
                }
                support  (x2) {
                    engineer  (x1)
                }
            }
            upgrade_prio  (x14) {
                factor  (x1)
                modifier  (x12) {
                    factor  (x4)
                    is_major  (x1)
                    num_of_factories  (x2)
                    surrender_progress  (x1)
                }
            }
        }
        infantry_early  (x19) {
            replace_at_match  (x1)
            replace_with  (x1)
            target_min_match  (x1)
            target_template  (x11) {
                regimental_support  (x3) {
                    anti_tank_battery  (x1)
                    fire_support  (x1)
                }
                regiments  (x3) {
                    artillery_brigade  (x1)
                    infantry  (x1)
                }
                support  (x4) {
                    artillery  (x1)
                    engineer  (x1)
                    recon  (x1)
                }
            }
            upgrade_prio  (x4) {
                base  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        infantry_mid  (x19) {
            target_template  (x13) {
                regimental_support  (x4) {
                    anti_air_battery  (x1)
                    anti_tank_battery  (x1)
                    fire_support  (x1)
                }
                regiments  (x3) {
                    artillery_brigade  (x1)
                    infantry  (x1)
                }
                support  (x5) {
                    artillery  (x1)
                    engineer  (x1)
                    logistics_company  (x1)
                    recon  (x1)
                }
            }
            upgrade_prio  (x5) {
                base  (x1)
                modifier  (x3) {
                    date  (x1)
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x5) {
            base  (x1)
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                surrender_progress  (x1)
            }
        }
    }
    irregular_infantry_ETH  (x15) {
        available_for  (x1) {
            ETH  (x1)
        }
        irregular_infantry_ETH  (x10) {
            target_template  (x7) {
                regiments  (x2) {
                    irregular_infantry  (x1)
                }
                support  (x4) {
                    engineer  (x1)
                    field_hospital  (x1)
                    military_police  (x1)
                }
            }
            upgrade_prio  (x2) {
                factor  (x1)
            }
        }
        upgrade_prio  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                has_country_flag  (x1)
            }
        }
    }
    landcruiser_generic  (x20) {
        landcruiser_default  (x14) {
            target_template  (x9) {
                regiments  (x4) {
                    heavy_armor  (x1)
                    medium_armor  (x1)
                    motorized  (x1)
                }
                support  (x4) {
                    anti_air  (x1)
                    engineer  (x1)
                    land_cruiser  (x1)
                }
            }
            upgrade_prio  (x4) {
                base  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x6) {
            base  (x1)
            modifier  (x5) {
                NOT  (x3) {
                    is_special_project_completed  (x1)
                    sp_land_land_cruiser  (x1)
                }
                factor  (x1)
            }
        }
    }
    marines_ENG  (x22) {
        available_for  (x1) {
            ENG  (x1)
        }
        marine_default_ENG  (x16) {
            target_template  (x11) {
                regimental_support  (x3) {
                    anti_tank_battery  (x1)
                    fire_support  (x1)
                }
                regiments  (x2) {
                    marine  (x1)
                }
                support  (x5) {
                    artillery  (x1)
                    engineer  (x1)
                    logistics_company  (x1)
                    recon  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x5) {
            factor  (x1)
            modifier  (x4) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
    }
    marines_GER  (x20) {
        available_for  (x1) {
            GER  (x1)
        }
        marine_default_GER  (x14) {
            target_template  (x11) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    fire_support  (x1)
                }
                regiments  (x2) {
                    marine  (x1)
                }
                support  (x5) {
                    artillery  (x1)
                    engineer  (x1)
                    logistics_company  (x1)
                    recon  (x1)
                }
            }
            upgrade_prio  (x2) {
                base  (x1)
            }
        }
        upgrade_prio  (x5) {
            base  (x1)
            modifier  (x4) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
    }
    marines_generic  (x94) {
        blocked_for  (x12) {
            APA  (x1)
            ENG  (x1)
            GER  (x1)
            HRL  (x1)
            ITA  (x1)
            JAP  (x1)
            PRC  (x1)
            SOV  (x2)
            USA  (x2)
            USB  (x1)
        }
        marine_armored  (x46) {
            target_template  (x20) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    anti_tank_battery  (x1)
                }
                regiments  (x6) {
                    amphibious_armor  (x2)
                    amphibious_mechanized  (x2)
                }
                support  (x9) {
                    artillery  (x1)
                    engineer  (x2)
                    logistics_company  (x2)
                    mot_recon  (x1)
                    recon  (x1)
                }
            }
            upgrade_prio  (x24) {
                base  (x1)
                factor  (x1)
                modifier  (x20) {
                    NOT  (x3) {
                        has_tech  (x2)
                    }
                    OR  (x7) {
                        NOT  (x6) {
                            OR  (x3) {
                                has_tech  (x2)
                            }
                            has_tech  (x1)
                        }
                    }
                    factor  (x4)
                    is_major  (x2)
                }
            }
        }
        marine_default  (x26) {
            target_template  (x16) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    anti_tank_battery  (x1)
                }
                regiments  (x4) {
                    marine  (x2)
                }
                support  (x7) {
                    artillery  (x1)
                    engineer  (x1)
                    logistics_company  (x2)
                    recon  (x1)
                }
            }
            upgrade_prio  (x8) {
                base  (x1)
                factor  (x1)
                modifier  (x4) {
                    factor  (x2)
                }
            }
        }
        upgrade_prio  (x10) {
            base  (x1)
            factor  (x1)
            modifier  (x8) {
                NOT  (x4) {
                    has_tech  (x2)
                }
                factor  (x2)
            }
        }
    }
    mechanized_default  (x25) {
        blocked_for  (x8) {
            APA  (x1)
            HRL  (x1)
            NSM  (x1)
            PRC  (x1)
            SOV  (x1)
            UKR  (x1)
            USA  (x1)
            USB  (x1)
        }
        mechanized_default  (x16) {
            replace_at_match  (x1)
            target_min_match  (x1)
            target_template  (x9) {
                regiments  (x3) {
                    light_mechanized  (x1)
                    mechanized  (x1)
                }
                support  (x5) {
                    engineer  (x1)
                    logistics_company  (x1)
                    maintenance_company  (x1)
                    mot_recon  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x1) {
            factor  (x1)
        }
    }
    militia_ATW_BLA_ATH  (x44) {
        available_for  (x6) {
            ATH  (x1)
            ATW  (x1)
            BLA  (x1)
            DAG  (x1)
            TAT  (x1)
            YAK  (x1)
        }
        blocked_for  (x12) {
            APA  (x1)
            BRN  (x1)
            CAR  (x1)
            ENG  (x1)
            HRL  (x1)
            NSM  (x1)
            POL  (x1)
            PTF  (x1)
            SOV  (x1)
            UKR  (x1)
            USA  (x1)
            USB  (x1)
        }
        militia_2_ATW_BLA_ATH  (x12) {
            target_template  (x7) {
                regiments  (x4) {
                    artillery_brigade  (x1)
                    militia  (x1)
                    mot_militia  (x1)
                }
                support  (x2) {
                    engineer  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        militia_default_ATW_BLA_ATH  (x11) {
            target_template  (x6) {
                regiments  (x2) {
                    militia  (x1)
                }
                support  (x3) {
                    engineer  (x1)
                    rocket_artillery  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x3) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    militia_LOS  (x15) {
        available_for  (x1) {
            LOS  (x1)
        }
        militia_default_LOS  (x11) {
            target_template  (x6) {
                regiments  (x2) {
                    militia  (x1)
                }
                support  (x3) {
                    engineer  (x1)
                    rocket_artillery  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x3) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    militia_TRG  (x42) {
        available_for  (x2) {
            BSK  (x1)
            TRG  (x1)
        }
        blocked_for  (x13) {
            APA  (x1)
            ATW  (x1)
            BRN  (x1)
            CAR  (x1)
            ENG  (x1)
            HRL  (x1)
            NSM  (x1)
            POL  (x1)
            PTF  (x1)
            SOV  (x1)
            UKR  (x1)
            USA  (x1)
            USB  (x1)
        }
        militia_2_TRG  (x13) {
            target_template  (x8) {
                regiments  (x4) {
                    artillery_brigade  (x1)
                    militia  (x1)
                    mot_militia  (x1)
                }
                support  (x3) {
                    engineer  (x1)
                    mbt_company  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        militia_default_TRG  (x11) {
            target_template  (x6) {
                regiments  (x2) {
                    militia  (x1)
                }
                support  (x3) {
                    engineer  (x1)
                    rocket_artillery  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x3) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    militia_generic  (x66) {
        Militia_brigades1  (x19) {
            reinforce_prio  (x1)
            target_template  (x3) {
                regiments  (x2) {
                    militia  (x1)
                }
            }
            upgrade_prio  (x14) {
                factor  (x1)
                modifier  (x12) {
                    factor  (x4)
                    has_civil_war  (x1)
                    is_major  (x1)
                    num_of_factories  (x2)
                }
            }
        }
        militia_brigades2  (x21) {
            reinforce_prio  (x1)
            target_template  (x6) {
                regiments  (x2) {
                    militia  (x1)
                }
                support  (x3) {
                    engineer  (x1)
                    recon  (x1)
                }
            }
            upgrade_prio  (x13) {
                factor  (x1)
                modifier  (x11) {
                    factor  (x4)
                    has_civil_war  (x1)
                    is_major  (x1)
                    num_of_factories  (x1)
                }
            }
        }
        mot_militia_generic  (x19) {
            reinforce_prio  (x1)
            target_template  (x6) {
                regiments  (x2) {
                    mot_militia  (x1)
                }
                support  (x3) {
                    engineer  (x1)
                    mot_recon  (x1)
                }
            }
            upgrade_prio  (x11) {
                factor  (x1)
                modifier  (x9) {
                    add  (x1)
                    factor  (x2)
                    has_civil_war  (x1)
                    is_major  (x1)
                    num_of_factories  (x1)
                }
            }
        }
        upgrade_prio  (x7) {
            factor  (x1)
            modifier  (x6) {
                factor  (x2)
                has_civil_war  (x2)
            }
        }
    }
    modern_armor_APA  (x17) {
        armor_default_APA  (x13) {
            target_template  (x8) {
                regiments  (x4) {
                    mechanized  (x1)
                    modern_armor  (x1)
                    modern_sp_artillery_brigade  (x1)
                }
                support  (x3) {
                    engineer  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        available_for  (x1) {
            APA  (x1)
        }
        upgrade_prio  (x3) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    motorized_GER  (x70) {
        available_for  (x1) {
            GER  (x1)
        }
        basic_motorized_infantry_GER  (x14) {
            division_names_group  (x1)
            target_template  (x10) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    anti_tank_battery  (x1)
                }
                regiments  (x2) {
                    motorized  (x1)
                }
                support  (x4) {
                    artillery  (x1)
                    engineer  (x1)
                    mot_recon  (x1)
                }
            }
            upgrade_prio  (x2) {
                base  (x1)
            }
        }
        late_motorized_infantry_GER  (x28) {
            division_names_group  (x1)
            target_template  (x14) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    mot_fire_support  (x1)
                }
                regiments  (x4) {
                    medium_sp_artillery_brigade  (x1)
                    medium_tank_destroyer_brigade  (x1)
                    motorized  (x1)
                }
                support  (x6) {
                    artillery  (x1)
                    assault_engineer  (x1)
                    field_hospital  (x1)
                    logistics_company  (x1)
                    mot_recon  (x1)
                }
            }
            upgrade_prio  (x12) {
                base  (x1)
                modifier  (x10) {
                    NOT  (x2) {
                        has_dlc  (x1)
                    }
                    OR  (x3) {
                        has_tech  (x2)
                    }
                    date  (x1)
                    factor  (x2)
                }
            }
        }
        mid_motorized_infantry_GER  (x22) {
            division_names_group  (x1)
            target_template  (x13) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    mot_fire_support  (x1)
                }
                regiments  (x4) {
                    light_tank_destroyer_brigade  (x1)
                    mot_artillery_brigade  (x1)
                    motorized  (x1)
                }
                support  (x5) {
                    artillery  (x1)
                    engineer  (x1)
                    logistics_company  (x1)
                    mot_recon  (x1)
                }
            }
            upgrade_prio  (x7) {
                base  (x1)
                modifier  (x5) {
                    OR  (x3) {
                        has_tech  (x2)
                    }
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x5) {
            base  (x1)
            modifier  (x4) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
    }
    mountaineers_ENG  (x22) {
        available_for  (x1) {
            ENG  (x1)
        }
        mountaineers_default_ENG  (x16) {
            target_template  (x11) {
                regimental_support  (x3) {
                    anti_tank_battery  (x1)
                    fire_support  (x1)
                }
                regiments  (x2) {
                    mountaineers  (x1)
                }
                support  (x5) {
                    artillery  (x1)
                    engineer  (x1)
                    logistics_company  (x1)
                    recon  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x5) {
            factor  (x1)
            modifier  (x4) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
    }
    mountaineers_GER  (x20) {
        available_for  (x1) {
            GER  (x1)
        }
        mountaineers_default_GER  (x14) {
            target_template  (x11) {
                regimental_support  (x3) {
                    anti_tank_battery  (x1)
                    field_guns  (x1)
                }
                regiments  (x2) {
                    mountaineers  (x1)
                }
                support  (x5) {
                    artillery  (x1)
                    engineer  (x1)
                    logistics_company  (x1)
                    recon  (x1)
                }
            }
            upgrade_prio  (x2) {
                base  (x1)
            }
        }
        upgrade_prio  (x5) {
            factor  (x1)
            modifier  (x4) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
    }
    mountaineers_generic  (x52) {
        blocked_for  (x13) {
            APA  (x1)
            ENG  (x1)
            GER  (x1)
            HRL  (x1)
            ITA  (x1)
            JAP  (x1)
            PRC  (x1)
            SIA  (x1)
            SOV  (x2)
            USA  (x2)
            USB  (x1)
        }
        mountaineers_default  (x29) {
            target_template  (x19) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    anti_tank_battery  (x1)
                }
                regiments  (x5) {
                    artillery_brigade  (x1)
                    mountaineers  (x2)
                }
                support  (x9) {
                    anti_tank  (x1)
                    artillery  (x2)
                    engineer  (x2)
                    logistics_company  (x2)
                }
            }
            upgrade_prio  (x8) {
                base  (x1)
                factor  (x1)
                modifier  (x4) {
                    factor  (x2)
                }
            }
        }
        upgrade_prio  (x10) {
            base  (x1)
            factor  (x1)
            modifier  (x8) {
                NOT  (x4) {
                    has_tech  (x2)
                }
                factor  (x2)
            }
        }
    }
    panzergrenadier_GER  (x134) {
        available_for  (x1) {
            GER  (x1)
        }
        front_role_override  (x1)
        panzergrenadier_early_GER  (x19) {
            can_upgrade_in_field  (x3) {
                has_equipment  (x2) {
                    light_tank_chassis  (x1)
                }
            }
            division_names_group  (x1)
            target_template  (x12) {
                regimental_support  (x2) {
                    anti_tank_battery  (x1)
                }
                regiments  (x3) {
                    light_armor  (x1)
                    motorized  (x1)
                }
                support  (x6) {
                    artillery  (x1)
                    assault_engineer  (x1)
                    light_flame_tank  (x1)
                    light_tank_recon  (x1)
                    logistics_company  (x1)
                }
            }
            upgrade_prio  (x2) {
                base  (x1)
            }
        }
        panzergrenadier_early_medium_tanks_GER  (x27) {
            can_upgrade_in_field  (x3) {
                has_equipment  (x2) {
                    light_tank_chassis  (x1)
                }
            }
            division_names_group  (x1)
            target_template  (x14) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    medium_tank_destroyer_support  (x1)
                }
                regiments  (x4) {
                    light_armor  (x1)
                    medium_armor  (x1)
                    motorized  (x1)
                }
                support  (x6) {
                    artillery  (x1)
                    assault_engineer  (x1)
                    light_flame_tank  (x1)
                    light_tank_recon  (x1)
                    logistics_company  (x1)
                }
            }
            upgrade_prio  (x8) {
                base  (x1)
                modifier  (x6) {
                    OR  (x3) {
                        has_tech  (x2)
                    }
                    date  (x1)
                    factor  (x1)
                }
            }
        }
        panzergrenadier_late_GER  (x25) {
            division_names_group  (x1)
            target_template  (x15) {
                regimental_support  (x4) {
                    anti_air_battery  (x1)
                    medium_tank_destroyer_support  (x1)
                    mot_fire_support  (x1)
                }
                regiments  (x4) {
                    mechanized  (x1)
                    medium_armor  (x1)
                    mot_artillery_brigade  (x1)
                }
                support  (x6) {
                    assault_engineer  (x1)
                    light_tank_recon  (x1)
                    logistics_company  (x1)
                    maintenance_company  (x1)
                    medium_flame_tank  (x1)
                }
            }
            upgrade_prio  (x8) {
                base  (x1)
                modifier  (x6) {
                    OR  (x3) {
                        has_tech  (x2)
                    }
                    date  (x1)
                    factor  (x1)
                }
            }
        }
        panzergrenadier_mid_GER  (x26) {
            division_names_group  (x1)
            target_template  (x16) {
                regimental_support  (x4) {
                    anti_air_battery  (x1)
                    medium_tank_destroyer_support  (x1)
                    mot_fire_support  (x1)
                }
                regiments  (x5) {
                    mechanized  (x1)
                    medium_armor  (x1)
                    mot_artillery_brigade  (x1)
                    motorized  (x1)
                }
                support  (x6) {
                    artillery  (x1)
                    assault_engineer  (x1)
                    light_flame_tank  (x1)
                    light_tank_recon  (x1)
                    logistics_company  (x1)
                }
            }
            upgrade_prio  (x8) {
                base  (x1)
                modifier  (x6) {
                    OR  (x3) {
                        has_tech  (x2)
                    }
                    date  (x1)
                    factor  (x1)
                }
            }
        }
        panzergrenadier_modern_GER  (x25) {
            division_names_group  (x1)
            target_template  (x15) {
                regimental_support  (x4) {
                    anti_air_battery  (x1)
                    medium_tank_destroyer_support  (x1)
                    mot_fire_support  (x1)
                }
                regiments  (x4) {
                    mechanized  (x1)
                    medium_sp_artillery_brigade  (x1)
                    modern_armor  (x1)
                }
                support  (x6) {
                    assault_engineer  (x1)
                    light_tank_recon  (x1)
                    logistics_company  (x1)
                    maintenance_company  (x1)
                    medium_flame_tank  (x1)
                }
            }
            upgrade_prio  (x8) {
                base  (x1)
                modifier  (x6) {
                    OR  (x3) {
                        has_tech  (x2)
                    }
                    date  (x1)
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x10) {
            base  (x1)
            modifier  (x9) {
                OR  (x3) {
                    has_tech  (x2)
                }
                add  (x1)
                factor  (x1)
                is_special_project_completed  (x1)
                sp_land_flamethrower_tank  (x1)
            }
        }
    }
    paratrooper_APA  (x16) {
        available_for  (x1) {
            APA  (x1)
        }
        paratrooper_default_APA  (x12) {
            target_template  (x7) {
                regiments  (x2) {
                    paratrooper  (x1)
                }
                support  (x4) {
                    engineer  (x1)
                    logistics_company  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x3) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    paratrooper_ENG  (x20) {
        available_for  (x1) {
            ENG  (x1)
        }
        paratrooper_default_ENG  (x14) {
            target_template  (x9) {
                regimental_support  (x3) {
                    anti_tank_battery  (x1)
                    field_guns  (x1)
                }
                regiments  (x2) {
                    paratrooper  (x1)
                }
                support  (x3) {
                    engineer  (x1)
                    field_hospital  (x1)
                }
            }
            upgrade_prio  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x5) {
            factor  (x1)
            modifier  (x4) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
    }
    paratrooper_generic  (x48) {
        blocked_for  (x12) {
            APA  (x1)
            ENG  (x1)
            GER  (x1)
            HRL  (x1)
            ITA  (x1)
            JAP  (x1)
            PRC  (x1)
            SOV  (x2)
            USA  (x2)
            USB  (x1)
        }
        paratrooper_default  (x26) {
            target_template  (x16) {
                regimental_support  (x2) {
                    field_guns  (x1)
                }
                regiments  (x4) {
                    paratrooper  (x2)
                }
                support  (x8) {
                    anti_tank  (x1)
                    artillery  (x1)
                    engineer  (x2)
                    recon  (x1)
                    signal_company  (x1)
                }
            }
            upgrade_prio  (x8) {
                base  (x1)
                factor  (x1)
                modifier  (x4) {
                    factor  (x2)
                }
            }
        }
        upgrade_prio  (x10) {
            base  (x1)
            factor  (x1)
            modifier  (x8) {
                NOT  (x4) {
                    has_tech  (x2)
                }
                factor  (x2)
            }
        }
    }
    paratroopers_GER  (x45) {
        available_for  (x1) {
            GER  (x1)
        }
        paratrooper_default_GER  (x8) {
            target_template  (x5) {
                regiments  (x2) {
                    paratrooper  (x1)
                }
                support  (x2) {
                    engineer  (x1)
                }
            }
            upgrade_prio  (x2) {
                base  (x1)
            }
        }
        paratrooper_early_GER  (x15) {
            target_template  (x9) {
                regimental_support  (x3) {
                    anti_tank_battery  (x1)
                    field_guns  (x1)
                }
                regiments  (x2) {
                    paratrooper  (x1)
                }
                support  (x3) {
                    engineer  (x1)
                    field_hospital  (x1)
                }
            }
            upgrade_prio  (x5) {
                base  (x1)
                modifier  (x3) {
                    date  (x1)
                    factor  (x1)
                }
            }
        }
        paratrooper_mid_GER  (x16) {
            target_template  (x10) {
                regimental_support  (x3) {
                    anti_tank_battery  (x1)
                    field_guns  (x1)
                }
                regiments  (x2) {
                    paratrooper  (x1)
                }
                support  (x4) {
                    engineer  (x1)
                    field_hospital  (x1)
                    recon  (x1)
                }
            }
            upgrade_prio  (x5) {
                base  (x1)
                modifier  (x3) {
                    date  (x1)
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x5) {
            base  (x1)
            modifier  (x4) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
    }
    rangers_generic  (x21) {
        rangers_default  (x16) {
            target_template  (x11) {
                regimental_support  (x3) {
                    anti_air_battery  (x1)
                    anti_tank_battery  (x1)
                }
                regiments  (x2) {
                    ranger_battalion  (x1)
                }
                support  (x5) {
                    artillery  (x1)
                    engineer  (x1)
                    logistics_company  (x1)
                    rangers_support  (x1)
                }
            }
            upgrade_prio  (x4) {
                base  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x5) {
            base  (x1)
            modifier  (x4) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
    }
    super_heavy_generic  (x27) {
        super_heavy_default  (x13) {
            target_template  (x8) {
                regiments  (x3) {
                    medium_armor  (x1)
                    motorized  (x1)
                }
                support  (x4) {
                    anti_air  (x1)
                    engineer  (x1)
                    super_heavy_armor  (x1)
                }
            }
            upgrade_prio  (x4) {
                base  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
        }
        upgrade_prio  (x14) {
            base  (x1)
            modifier  (x13) {
                NOT  (x4) {
                    has_government  (x1)
                    has_tech  (x1)
                }
                add  (x1)
                date  (x1)
                factor  (x1)
                is_major  (x1)
                is_special_project_completed  (x1)
                num_of_military_factories  (x1)
                sp_land_land_cruiser  (x1)
            }
        }
    }
    suppression_generic  (x28) {
        blocked_for  (x1) {
            SIA  (x1)
        }
        suppression_generic  (x10) {
            custom_icon  (x1)
            reinforce_prio  (x1)
            target_template  (x5) {
                regiments  (x2) {
                    cavalry  (x1)
                }
                support  (x2) {
                    military_police  (x1)
                }
            }
            upgrade_prio  (x2) {
                base  (x1)
            }
        }
        upgrade_prio  (x17) {
            base  (x1)
            modifier  (x16) {
                OR  (x10) {
                    AND  (x9) {
                        NOT  (x4) {
                            ai_has_role_template  (x2)
                        }
                        any_country  (x2) {
                            is_justifying_wargoal_against  (x1)
                        }
                        has_completed_focus  (x1)
                    }
                }
                factor  (x2)
                has_war  (x1)
                tag  (x1)
            }
        }
    }
}
```


## AI 装备编辑器（ai_equipment）

> 说明：target_variant 接设计器；未知脚本块仍可能缺失

扫描文件：10

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

总缺失条数：**7652**

##### common/ai_equipment

```text
common/ai_equipment  (x7652) {
    AST_destroyers  (x101) {
        available_for  (x1) {
            AST  (x1)
        }
        destroyer_1_upgrade  (x26) {
            allowed_modules  (x7) {
                light_ship_engine_1  (x1)
                ship_anti_air_2  (x1)
                ship_depth_charge_1  (x1)
                ship_fire_control_system_0  (x1)
                ship_light_battery_2  (x1)
                ship_torpedo_1  (x1)
            }
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        destroyer_2  (x25) {
            allowed_modules  (x9) {
                dp_light_battery  (x1)
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        destroyer_3  (x24) {
            allowed_modules  (x7) {
                light_ship_engine_3  (x1)
                ship_anti_air_3  (x1)
                ship_depth_charge_1  (x1)
                ship_fire_control_system_1  (x1)
                ship_light_battery_3  (x1)
                ship_torpedo_3  (x1)
            }
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        destroyer_default  (x23) {
            allowed_modules  (x7) {
                light_ship_engine_1  (x1)
                ship_anti_air_1  (x1)
                ship_depth_charge_1  (x1)
                ship_fire_control_system_0  (x1)
                ship_light_battery_1  (x1)
                ship_torpedo_1  (x1)
            }
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            naval_screen  (x1)
        }
    }
    AST_naval_light_cruiser  (x282) {
        available_for  (x1) {
            AST  (x1)
        }
        cruiser_light_advanced  (x30) {
            allowed_modules  (x10) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x16) {
                match_value  (x1)
                modules  (x13) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                    rear_2_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        cruiser_light_advanced_improved  (x30) {
            allowed_modules  (x10) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x16) {
                match_value  (x1)
                modules  (x13) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                    rear_2_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        cruiser_light_basic  (x29) {
            allowed_modules  (x11) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        cruiser_light_basic_upgrade  (x32) {
            allowed_modules  (x11) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        cruiser_light_early  (x29) {
            allowed_modules  (x11) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_light_medium_battery_1  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        cruiser_light_early_aa_conversion  (x34) {
            allowed_modules  (x12) {
                cruiser_ship_engine  (x1)
                dp_light_battery  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_light_medium_battery_1  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        cruiser_light_early_aa_upgrade  (x32) {
            allowed_modules  (x11) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_light_medium_battery_1  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        cruiser_light_improved  (x30) {
            allowed_modules  (x11) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        cruiser_light_improved_upgrade  (x33) {
            allowed_modules  (x11) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_War  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            naval_cruiser_light  (x1)
        }
    }
    ENG_amphibious_tanks  (x49) {
        available_for  (x1) {
            ENG  (x1)
        }
        basic_amphibious_tank_default  (x45) {
            allowed_modules  (x8) {
                tank_bogie_suspension  (x1)
                tank_close_support_gun  (x1)
                tank_diesel_engine  (x1)
                tank_light_turret_type  (x1)
                tank_riveted_armor  (x1)
                tank_small_cannon  (x1)
                tank_small_cannon_2  (x1)
            }
            history  (x1)
            priority  (x7) {
                factor  (x1)
                modifier  (x5) {
                    OR  (x3) {
                        TAG  (x2)
                    }
                    factor  (x1)
                }
            }
            target_variant  (x28) {
                match_value  (x1)
                modules  (x14) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x5) {
                        any_of  (x4) {
                            tank_close_support_gun  (x1)
                            tank_small_cannon  (x1)
                            tank_small_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x11) {
                    tank_nsb_armor_upgrade  (x9) {
                        base  (x1)
                        modifier  (x7) {
                            add  (x2)
                            any_enemy_country  (x2) {
                                is_major  (x1)
                            }
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        blocked_for  (x1)
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            land_amphibious_tank  (x1)
        }
    }
    ENG_cas  (x70) {
        available_for  (x1) {
            ENG  (x1)
        }
        cas_1  (x18) {
            allowed_modules  (x6) {
                armor_plate_small  (x1)
                bomb_locks  (x1)
                engine_2_1x  (x1)
                fuel_tanks_small  (x1)
                small_bomb_bay  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x8) {
                match_value  (x1)
                modules  (x5) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                }
                type  (x1)
            }
        }
        cas_2  (x21) {
            allowed_modules  (x7) {
                armor_plate_small  (x1)
                bomb_locks  (x1)
                engine_2_2x  (x1)
                fuel_tanks_small  (x1)
                self_sealing_fuel_tanks_small  (x1)
                small_bomb_bay  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x10) {
                match_value  (x1)
                modules  (x7) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
        }
        cas_3  (x28) {
            allowed_modules  (x8) {
                armor_plate_small  (x1)
                bomb_locks  (x1)
                drop_tanks  (x1)
                engine_2_1x  (x1)
                engine_3_1x  (x1)
                rocket_rails  (x1)
                self_sealing_fuel_tanks_small  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x16) {
                match_value  (x1)
                modules  (x13) {
                    engine_type_slot  (x4) {
                        any_of  (x3) {
                            engine_2_1x  (x1)
                            engine_3_1x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x4) {
                        any_of  (x3) {
                            bomb_locks  (x1)
                            rocket_rails  (x1)
                        }
                    }
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            air_cas  (x1)
        }
    }
    ENG_cv_cas  (x77) {
        available_for  (x1) {
            ENG  (x1)
        }
        cv_cas_1  (x17) {
            allowed_modules  (x4) {
                bomb_locks  (x1)
                dive_brakes_small  (x1)
                engine_2_1x  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                }
                type  (x1)
            }
        }
        cv_cas_2  (x25) {
            allowed_modules  (x8) {
                armor_plate_small  (x1)
                bomb_locks  (x1)
                dive_brakes_small  (x1)
                engine_2_1x  (x1)
                engine_3_1x  (x1)
                self_sealing_fuel_tanks_small  (x1)
                small_bomb_bay  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    engine_type_slot  (x4) {
                        any_of  (x3) {
                            engine_2_1x  (x1)
                            engine_3_1x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
        }
        cv_cas_3  (x27) {
            allowed_modules  (x9) {
                armor_plate_small  (x1)
                bomb_locks  (x1)
                dive_brakes_small  (x1)
                drop_tanks  (x1)
                engine_3_1x  (x1)
                engine_4_1x  (x1)
                self_sealing_fuel_tanks_small  (x1)
                small_bomb_bay  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    engine_type_slot  (x4) {
                        any_of  (x3) {
                            engine_3_1x  (x1)
                            engine_4_1x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x2)
                }
                type  (x1)
            }
        }
        priority  (x6) {
            factor  (x1)
            modifier  (x5) {
                factor  (x1)
                has_navy_size  (x3) {
                    size  (x1)
                    unit  (x1)
                }
            }
        }
        roles  (x1) {
            air_cv_cas  (x1)
        }
    }
    ENG_cv_fighter  (x115) {
        advanced_cv_fighter_default  (x25) {
            allowed_modules  (x8) {
                aircraft_cannon_1_2x  (x1)
                aircraft_cannon_2_2x  (x1)
                armor_plate_small  (x1)
                drop_tanks  (x1)
                engine_3_1x  (x1)
                engine_4_1x  (x1)
                self_sealing_fuel_tanks_small  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    engine_type_slot  (x4) {
                        any_of  (x3) {
                            engine_3_1x  (x1)
                            engine_4_1x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
        }
        available_for  (x1) {
            ENG  (x1)
        }
        basic_cv_fighter_default  (x18) {
            allowed_modules  (x5) {
                armor_plate_small  (x1)
                engine_2_1x  (x1)
                light_mg_4x  (x1)
                self_sealing_fuel_tanks_small  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                }
                type  (x1)
            }
        }
        great_war_cv_fighter_default  (x19) {
            allowed_modules  (x3) {
                engine_1_1x  (x1)
                light_mg_4x  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                }
                type  (x1)
            }
        }
        improved_cv_fighter_default  (x24) {
            allowed_modules  (x7) {
                aircraft_cannon_1_2x  (x1)
                armor_plate_small  (x1)
                engine_2_1x  (x1)
                engine_3_1x  (x1)
                light_mg_4x  (x1)
                self_sealing_fuel_tanks_small  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    engine_type_slot  (x4) {
                        any_of  (x3) {
                            engine_2_1x  (x1)
                            engine_3_1x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
        }
        jet_cv_fighter_default  (x21) {
            allowed_modules  (x6) {
                aircraft_cannon_2_2x  (x1)
                armor_plate_small  (x1)
                drop_tanks  (x1)
                jet_engine_2x  (x1)
                self_sealing_fuel_tanks_small  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x10) {
                match_value  (x1)
                modules  (x7) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
            visible  (x1)
        }
        priority  (x6) {
            factor  (x1)
            modifier  (x5) {
                factor  (x1)
                has_navy_size  (x3) {
                    size  (x1)
                    unit  (x1)
                }
            }
        }
        roles  (x1) {
            air_cv_fighter  (x1)
        }
    }
    ENG_cv_naval_bomber  (x123) {
        available_for  (x1) {
            ENG  (x1)
        }
        cv_naval_bomber_1  (x17) {
            allowed_modules  (x4) {
                engine_2_1x  (x1)
                lmg_defense_turret  (x1)
                torpedo_mounting  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                }
                type  (x1)
            }
        }
        cv_naval_bomber_2  (x28) {
            allowed_modules  (x8) {
                bomb_locks  (x1)
                engine_2_1x  (x1)
                engine_3_1x  (x1)
                lmg_defense_turret  (x1)
                self_sealing_fuel_tanks_small  (x1)
                torpedo_mounting  (x1)
                torpedo_mounting_2  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x16) {
                match_value  (x1)
                modules  (x13) {
                    engine_type_slot  (x4) {
                        any_of  (x3) {
                            engine_2_1x  (x1)
                            engine_3_1x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x4) {
                        any_of  (x3) {
                            torpedo_mounting  (x1)
                            torpedo_mounting_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
        }
        cv_naval_bomber_3  (x29) {
            allowed_modules  (x9) {
                bomb_locks  (x1)
                drop_tanks  (x1)
                engine_3_1x  (x1)
                engine_4_1x  (x1)
                lmg_defense_turret  (x1)
                self_sealing_fuel_tanks_small  (x1)
                torpedo_mounting_2  (x1)
                torpedo_mounting_3  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x16) {
                match_value  (x1)
                modules  (x13) {
                    engine_type_slot  (x4) {
                        any_of  (x3) {
                            engine_3_1x  (x1)
                            engine_4_1x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x4) {
                        any_of  (x3) {
                            torpedo_mounting_2  (x1)
                            torpedo_mounting_3  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
        }
        gw_cv_naval_bomber_default  (x20) {
            allowed_modules  (x4) {
                engine_1_1x  (x1)
                lmg_defense_turret  (x1)
                torpedo_mounting  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                }
                type  (x1)
            }
        }
        jet_cv_naval_bomber_default  (x21) {
            allowed_modules  (x6) {
                bomb_locks  (x1)
                drop_tanks  (x1)
                jet_engine_2x  (x1)
                self_sealing_fuel_tanks_small  (x1)
                torpedo_mounting_3  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x10) {
                match_value  (x1)
                modules  (x7) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
            visible  (x1)
        }
        priority  (x6) {
            factor  (x1)
            modifier  (x5) {
                factor  (x1)
                has_navy_size  (x3) {
                    size  (x1)
                    unit  (x1)
                }
            }
        }
        roles  (x1) {
            air_cv_naval_bomber  (x1)
        }
    }
    ENG_destroyers  (x128) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        destroyer_advanced  (x32) {
            allowed_modules  (x9) {
                dp_light_battery  (x1)
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        destroyer_basic  (x30) {
            allowed_modules  (x9) {
                dp_light_battery  (x1)
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        destroyer_early  (x28) {
            allowed_modules  (x9) {
                dp_light_battery  (x1)
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            design_team  (x1)
            history  (x1)
            name  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        destroyer_improved  (x31) {
            allowed_modules  (x9) {
                dp_light_battery  (x1)
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                has_war  (x1)
            }
        }
        roles  (x1) {
            naval_screen  (x1)
        }
    }
    ENG_escorts  (x115) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        escort_advanced  (x27) {
            allowed_modules  (x8) {
                dp_light_battery  (x1)
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        escort_basic  (x26) {
            allowed_modules  (x8) {
                dp_light_battery  (x1)
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        escort_early  (x26) {
            allowed_modules  (x8) {
                dp_light_battery  (x1)
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        escort_improved  (x26) {
            allowed_modules  (x8) {
                dp_light_battery  (x1)
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x7) {
            factor  (x1)
            modifier  (x6) {
                anti_submarine_strategy_required_trigger  (x1)
                convoy_threat  (x1)
                factor  (x2)
            }
        }
        roles  (x1) {
            naval_escort  (x1)
        }
    }
    ENG_fighter  (x275) {
        advanced_fighter_default  (x34) {
            allowed_modules  (x10) {
                aircraft_cannon_1_2x  (x1)
                aircraft_cannon_2_2x  (x1)
                armor_plate_small  (x1)
                drop_tanks  (x1)
                engine_2_2x  (x1)
                engine_3_1x  (x1)
                engine_4_1x  (x1)
                heavy_mg_4x  (x1)
                self_sealing_fuel_tanks_small  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x17) {
                    engine_type_slot  (x5) {
                        any_of  (x4) {
                            engine_2_2x  (x1)
                            engine_3_1x  (x1)
                            engine_4_1x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x4) {
                        any_of  (x3) {
                            aircraft_cannon_1_2x  (x1)
                            aircraft_cannon_2_2x  (x1)
                        }
                    }
                    fixed_main_weapon_slot  (x4) {
                        any_of  (x3) {
                            aircraft_cannon_1_2x  (x1)
                            aircraft_cannon_2_2x  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
        }
        advanced_fighter_improved  (x35) {
            allowed_modules  (x10) {
                aircraft_cannon_1_2x  (x1)
                aircraft_cannon_2_2x  (x1)
                armor_plate_small  (x1)
                drop_tanks  (x1)
                engine_2_2x  (x1)
                engine_3_1x  (x1)
                engine_4_1x  (x1)
                heavy_mg_4x  (x1)
                self_sealing_fuel_tanks_small  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x17) {
                    engine_type_slot  (x5) {
                        any_of  (x4) {
                            engine_2_2x  (x1)
                            engine_3_1x  (x1)
                            engine_4_1x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x4) {
                        any_of  (x3) {
                            aircraft_cannon_1_2x  (x1)
                            aircraft_cannon_2_2x  (x1)
                        }
                    }
                    fixed_main_weapon_slot  (x4) {
                        any_of  (x3) {
                            aircraft_cannon_1_2x  (x1)
                            aircraft_cannon_2_2x  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
        }
        available_for  (x1) {
            ENG  (x1)
        }
        basic_fighter_default  (x25) {
            allowed_modules  (x6) {
                aircraft_cannon_1_1x  (x1)
                armor_plate_small  (x1)
                engine_1_1x  (x1)
                engine_2_1x  (x1)
                light_mg_4x  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    engine_type_slot  (x4) {
                        any_of  (x3) {
                            engine_1_1x  (x1)
                            engine_2_1x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                }
                type  (x1)
            }
        }
        basic_fighter_improved  (x28) {
            allowed_modules  (x7) {
                aircraft_cannon_1_1x  (x1)
                aircraft_cannon_1_2x  (x1)
                armor_plate_small  (x1)
                engine_2_1x  (x1)
                light_mg_4x  (x1)
                self_sealing_fuel_tanks_small  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x4) {
                        any_of  (x3) {
                            aircraft_cannon_1_1x  (x1)
                            aircraft_cannon_1_2x  (x1)
                        }
                    }
                    fixed_main_weapon_slot  (x4) {
                        any_of  (x3) {
                            aircraft_cannon_1_1x  (x1)
                            aircraft_cannon_1_2x  (x1)
                        }
                    }
                }
                type  (x1)
            }
        }
        blocked_for  (x1)
        great_war_fighter_default  (x19) {
            allowed_modules  (x3) {
                engine_1_1x  (x1)
                light_mg_4x  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                }
                type  (x1)
            }
        }
        improved_fighter_default  (x20) {
            allowed_modules  (x3) {
                engine_2_1x  (x1)
                light_mg_4x  (x1)
            }
            history  (x1)
            priority  (x8) {
                factor  (x1)
                modifier  (x6) {
                    factor  (x2)
                    has_tech  (x2)
                }
            }
            target_variant  (x7) {
                match_value  (x1)
                modules  (x4) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                }
                type  (x1)
            }
        }
        improved_fighter_improved  (x34) {
            allowed_modules  (x7) {
                aircraft_cannon_1_2x  (x1)
                armor_plate_small  (x1)
                engine_2_1x  (x1)
                engine_3_1x  (x1)
                light_mg_4x  (x1)
                self_sealing_fuel_tanks_small  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x12) {
                factor  (x1)
                modifier  (x10) {
                    factor  (x3)
                    has_tech  (x2)
                    not  (x2) {
                        has_tech  (x1)
                    }
                }
            }
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    engine_type_slot  (x4) {
                        any_of  (x3) {
                            engine_2_1x  (x1)
                            engine_3_1x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                }
                type  (x1)
            }
        }
        improved_fighter_improved_griffin  (x28) {
            allowed_modules  (x7) {
                aircraft_cannon_1_2x  (x1)
                armor_plate_small  (x1)
                engine_2_1x  (x1)
                engine_3_1x  (x1)
                engine_4_1x  (x1)
                self_sealing_fuel_tanks_small  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x9) {
                factor  (x1)
                modifier  (x7) {
                    factor  (x2)
                    has_tech  (x1)
                    not  (x2) {
                        has_tech  (x1)
                    }
                }
            }
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                }
                type  (x1)
            }
        }
        improved_fighter_improved_more  (x27) {
            allowed_modules  (x6) {
                aircraft_cannon_1_2x  (x1)
                armor_plate_small  (x1)
                engine_2_1x  (x1)
                engine_3_1x  (x1)
                self_sealing_fuel_tanks_small  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x9) {
                factor  (x1)
                modifier  (x7) {
                    factor  (x2)
                    has_tech  (x1)
                    not  (x2) {
                        has_tech  (x1)
                    }
                }
            }
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                }
                type  (x1)
            }
        }
        jet_fighter_default  (x21) {
            allowed_modules  (x6) {
                aircraft_cannon_2_2x  (x1)
                armor_plate_small  (x1)
                drop_tanks  (x1)
                jet_engine_2x  (x1)
                self_sealing_fuel_tanks_small  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x10) {
                match_value  (x1)
                modules  (x7) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
            visible  (x1)
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            air_fighter  (x1)
        }
    }
    ENG_heavy_fighter  (x83) {
        available_for  (x1) {
            ENG  (x1)
        }
        heavy_fighter_1  (x20) {
            allowed_modules  (x6) {
                aircraft_cannon_1_2x  (x1)
                engine_2_2x  (x1)
                fuel_tanks_medium  (x1)
                light_mg_4x  (x1)
                lmg_defense_turret  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x10) {
                match_value  (x1)
                modules  (x7) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_auxiliary_weapon_slot_2  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                }
                type  (x1)
            }
        }
        heavy_fighter_2  (x34) {
            allowed_modules  (x11) {
                aircraft_cannon_1_2x  (x1)
                armor_plate_medium  (x1)
                bomb_locks  (x1)
                engine_2_2x  (x1)
                engine_3_2x  (x1)
                fuel_tanks_medium  (x1)
                light_mg_4x  (x1)
                nav_bomber_weapon  (x1)
                rocket_rails  (x1)
                self_sealing_fuel_tanks_medium  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x19) {
                match_value  (x1)
                modules  (x16) {
                    engine_type_slot  (x4) {
                        any_of  (x3) {
                            engine_2_2x  (x1)
                            engine_3_2x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_auxiliary_weapon_slot_2  (x1)
                    fixed_auxiliary_weapon_slot_3  (x5) {
                        any_of  (x4) {
                            bomb_locks  (x1)
                            nav_bomber_weapon  (x1)
                            rocket_rails  (x1)
                        }
                    }
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
        }
        heavy_fighter_3  (x26) {
            allowed_modules  (x8) {
                aircraft_cannon_2_2x  (x1)
                armor_plate_medium  (x1)
                bomb_locks  (x1)
                engine_3_2x  (x1)
                engine_4_2x  (x1)
                fuel_tanks_medium  (x1)
                self_sealing_fuel_tanks_medium  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    engine_type_slot  (x4) {
                        any_of  (x3) {
                            engine_3_2x  (x1)
                            engine_4_2x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_auxiliary_weapon_slot_2  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            air_heavy_fighter  (x1)
        }
    }
    ENG_heavy_tank_anti_air  (x106) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        heavy_tank_anti_air_1  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_two_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        heavy_tank_anti_air_2  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon_2  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_two_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        heavy_tank_anti_air_3  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon_3  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_two_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x7) {
            factor  (x1)
            modifier  (x6) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                any_enemy_country  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
        roles  (x1) {
            land_heavy_tank_anti_air  (x1)
        }
    }
    ENG_heavy_tank_artillery  (x102) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        heavy_tank_artillery_1  (x32) {
            allowed_modules  (x6) {
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_fixed_superstructure_turret  (x1)
                tank_medium_howitzer  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        heavy_tank_artillery_2  (x33) {
            allowed_modules  (x7) {
                extra_ammo_storage  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_fixed_superstructure_turret  (x1)
                tank_medium_howitzer_2  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        heavy_tank_artillery_3  (x33) {
            allowed_modules  (x7) {
                extra_ammo_storage  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_fixed_superstructure_turret  (x1)
                tank_heavy_howitzer  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            land_heavy_tank_artillery  (x1)
        }
    }
    ENG_heavy_tank_destroyer  (x144) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        heavy_tank_destroyer_1  (x38) {
            allowed_modules  (x8) {
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_cannon  (x1)
                tank_heavy_cannon_2  (x1)
                tank_heavy_fixed_superstructure_turret  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x24) {
                match_value  (x1)
                modules  (x14) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x5) {
                        any_of  (x4) {
                            tank_heavy_cannon  (x1)
                            tank_heavy_cannon_2  (x1)
                            tank_high_velocity_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        heavy_tank_destroyer_2  (x48) {
            allowed_modules  (x14) {
                extra_ammo_storage  (x1)
                tank_bogie_suspension  (x1)
                tank_cast_armor  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_cannon  (x1)
                tank_heavy_cannon_2  (x1)
                tank_heavy_fixed_superstructure_turret  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_high_velocity_cannon_3  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_super_heavy_cannon  (x1)
            }
            enable  (x4) {
                OR  (x3) {
                    has_tech  (x2)
                }
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x26) {
                match_value  (x1)
                modules  (x16) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x7) {
                        any_of  (x6) {
                            tank_heavy_cannon  (x1)
                            tank_heavy_cannon_2  (x1)
                            tank_high_velocity_cannon_2  (x1)
                            tank_high_velocity_cannon_3  (x1)
                            tank_super_heavy_cannon  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        heavy_tank_destroyer_3  (x48) {
            allowed_modules  (x15) {
                extra_ammo_storage  (x1)
                sloped_armor  (x1)
                smoke_launchers  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_cannon_2  (x1)
                tank_heavy_fixed_superstructure_turret  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_high_velocity_cannon_3  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_super_heavy_cannon  (x1)
                tank_welded_armor  (x1)
            }
            enable  (x4) {
                OR  (x3) {
                    has_tech  (x2)
                }
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x25) {
                match_value  (x1)
                modules  (x15) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x6) {
                        any_of  (x5) {
                            tank_heavy_cannon_2  (x1)
                            tank_high_velocity_cannon_2  (x1)
                            tank_high_velocity_cannon_3  (x1)
                            tank_super_heavy_cannon  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x7) {
            factor  (x1)
            modifier  (x6) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                any_enemy_country  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
        roles  (x1) {
            land_heavy_tank_destroyer  (x1)
        }
    }
    ENG_heavy_tanks  (x134) {
        advanced_heavy_tank_default  (x37) {
            allowed_modules  (x9) {
                tank_bogie_suspension  (x1)
                tank_gasoline_engine  (x1)
                tank_heavy_three_man_tank_turret  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_welded_armor  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x24) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x11) {
                    tank_nsb_armor_upgrade  (x9) {
                        base  (x1)
                        modifier  (x7) {
                            add  (x2)
                            any_enemy_country  (x2) {
                                is_major  (x1)
                            }
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        available_for  (x1) {
            ENG  (x1)
        }
        basic_heavy_tank_default  (x44) {
            allowed_modules  (x13) {
                secondary_turret_hmg  (x1)
                tank_bogie_suspension  (x1)
                tank_close_support_gun  (x1)
                tank_gasoline_engine  (x1)
                tank_heavy_two_man_tank_turret  (x1)
                tank_high_velocity_cannon  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_riveted_armor  (x1)
                tank_small_cannon  (x1)
                tank_small_cannon_2  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x24) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x11) {
                    tank_nsb_armor_upgrade  (x9) {
                        base  (x1)
                        modifier  (x7) {
                            add  (x2)
                            any_enemy_country  (x2) {
                                is_major  (x1)
                            }
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        blocked_for  (x1)
        improved_heavy_tank_default  (x46) {
            allowed_modules  (x11) {
                tank_bogie_suspension  (x1)
                tank_cast_armor  (x1)
                tank_gasoline_engine  (x1)
                tank_heavy_three_man_tank_turret  (x1)
                tank_high_velocity_cannon  (x1)
                tank_medium_cannon  (x1)
                tank_medium_cannon_2  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x28) {
                match_value  (x1)
                modules  (x14) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x5) {
                        any_of  (x4) {
                            tank_high_velocity_cannon  (x1)
                            tank_medium_cannon  (x1)
                            tank_medium_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x11) {
                    tank_nsb_armor_upgrade  (x9) {
                        base  (x1)
                        modifier  (x7) {
                            add  (x2)
                            any_enemy_country  (x2) {
                                is_major  (x1)
                            }
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                num_of_factories  (x1)
            }
        }
        roles  (x1) {
            land_heavy_tank  (x1)
        }
    }
    ENG_light_tank_anti_air  (x106) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        light_tank_anti_air_1  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_light_one_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        light_tank_anti_air_2  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon_2  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_light_two_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        light_tank_anti_air_3  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon_2  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_light_two_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x7) {
            factor  (x1)
            modifier  (x6) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                any_enemy_country  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
        roles  (x1) {
            land_light_tank_anti_air  (x1)
        }
    }
    ENG_light_tank_artillery  (x104) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        light_tank_artillery_1  (x35) {
            allowed_modules  (x6) {
                tank_bogie_suspension  (x1)
                tank_close_support_gun  (x1)
                tank_diesel_engine  (x1)
                tank_light_fixed_superstructure_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_template_containing_unit  (x1)
                }
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        light_tank_artillery_2  (x32) {
            allowed_modules  (x6) {
                tank_bogie_suspension  (x1)
                tank_gasoline_engine  (x1)
                tank_light_fixed_superstructure_turret  (x1)
                tank_medium_howitzer  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        light_tank_artillery_3  (x33) {
            allowed_modules  (x7) {
                extra_ammo_storage  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_light_fixed_superstructure_turret  (x1)
                tank_medium_howitzer_2  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            land_light_tank_artillery  (x1)
        }
    }
    ENG_light_tank_destroyers  (x91) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        light_tank_destroyer_1  (x32) {
            allowed_modules  (x6) {
                tank_gasoline_engine  (x1)
                tank_high_velocity_cannon  (x1)
                tank_light_fixed_superstructure_turret  (x1)
                tank_riveted_armor  (x1)
                tank_wheeled_suspension  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        light_tank_destroyer_2  (x46) {
            allowed_modules  (x13) {
                extra_ammo_storage  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_high_velocity_cannon  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_light_fixed_superstructure_turret  (x1)
                tank_medium_cannon  (x1)
                tank_medium_cannon_2  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x4) {
                OR  (x3) {
                    has_tech  (x2)
                }
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x25) {
                match_value  (x1)
                modules  (x15) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x6) {
                        any_of  (x5) {
                            tank_high_velocity_cannon  (x1)
                            tank_high_velocity_cannon_2  (x1)
                            tank_medium_cannon  (x1)
                            tank_medium_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x10) {
            factor  (x1)
            modifier  (x9) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                any_enemy_country  (x2) {
                    has_tech  (x1)
                }
                factor  (x2)
                has_template_containing_unit  (x1)
            }
        }
        roles  (x1) {
            land_light_tank_destroyer  (x1)
        }
    }
    ENG_light_tanks  (x154) {
        advanced_light_tank_default  (x37) {
            allowed_modules  (x10) {
                tank_gasoline_engine  (x1)
                tank_high_velocity_cannon  (x1)
                tank_light_two_man_tank_turret  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_small_cannon_2  (x1)
                tank_torsion_bar_suspension  (x1)
                tank_welded_armor  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x23) {
                match_value  (x1)
                modules  (x13) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x4) {
                        any_of  (x3) {
                            tank_high_velocity_cannon  (x1)
                            tank_small_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        available_for  (x1) {
            ENG  (x1)
        }
        basic_light_tank_default  (x34) {
            allowed_modules  (x7) {
                tank_bogie_suspension  (x1)
                tank_gasoline_engine  (x1)
                tank_heavy_machine_gun  (x1)
                tank_high_velocity_cannon  (x1)
                tank_light_two_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        blocked_for  (x1)
        great_war_tank_default  (x33) {
            allowed_modules  (x6) {
                tank_bogie_suspension  (x1)
                tank_gasoline_engine  (x1)
                tank_heavy_machine_gun  (x1)
                tank_light_one_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        improved_light_tank_default  (x46) {
            allowed_modules  (x13) {
                smoke_launchers  (x1)
                tank_christie_suspension  (x1)
                tank_gasoline_engine  (x1)
                tank_high_velocity_cannon  (x1)
                tank_light_three_man_tank_turret  (x1)
                tank_light_two_man_tank_turret  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_riveted_armor  (x1)
                tank_small_cannon_2  (x1)
                tank_welded_armor  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x26) {
                match_value  (x1)
                modules  (x16) {
                    armor_type_slot  (x4) {
                        any_of  (x3) {
                            tank_riveted_armor  (x1)
                            tank_welded_armor  (x1)
                        }
                    }
                    engine_type_slot  (x1)
                    main_armament_slot  (x4) {
                        any_of  (x3) {
                            tank_high_velocity_cannon  (x1)
                            tank_small_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            land_light_tank  (x1)
        }
    }
    ENG_maritime_patrol  (x105) {
        available_for  (x1) {
            ENG  (x1)
        }
        maritime_patrol_1_default  (x29) {
            allowed_modules  (x8) {
                engine_1_4x  (x1)
                engine_2_4x  (x1)
                flying_boat_large  (x1)
                fuel_tanks_large  (x1)
                lmg_defense_turret  (x1)
                lmg_defense_turret_2x  (x1)
                nav_bomber_weapon  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x17) {
                match_value  (x1)
                modules  (x14) {
                    engine_type_slot  (x4) {
                        any_of  (x3) {
                            engine_1_4x  (x1)
                            engine_2_4x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_auxiliary_weapon_slot_2  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x4) {
                        any_of  (x3) {
                            lmg_defense_turret  (x1)
                            lmg_defense_turret_2x  (x1)
                        }
                    }
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
        }
        maritime_patrol_2_default  (x25) {
            allowed_modules  (x8) {
                engine_2_4x  (x1)
                flying_boat_large  (x1)
                fuel_tanks_large  (x1)
                hmg_defense_turret_2x  (x1)
                lmg_defense_turret_2x  (x1)
                nav_bomber_weapon  (x1)
                self_sealing_fuel_tanks_large  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_auxiliary_weapon_slot_2  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    special_type_slot_5  (x1)
                }
                type  (x1)
            }
        }
        maritime_patrol_3_default  (x41) {
            allowed_modules  (x12) {
                air_ground_radar_1  (x1)
                air_ground_radar_2  (x1)
                cannon_defense_turret_2x  (x1)
                engine_3_4x  (x1)
                engine_4_4x  (x1)
                flying_boat_large  (x1)
                fuel_tanks_large  (x1)
                hmg_defense_turret_2x  (x1)
                nav_bomber_weapon  (x1)
                recon_camera  (x1)
                self_sealing_fuel_tanks_large  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x25) {
                match_value  (x1)
                modules  (x22) {
                    engine_type_slot  (x4) {
                        any_of  (x3) {
                            engine_3_4x  (x1)
                            engine_4_4x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_auxiliary_weapon_slot_2  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x6) {
                        any_of  (x5) {
                            air_ground_radar_1  (x1)
                            air_ground_radar_2  (x1)
                            hmg_defense_turret_2x  (x1)
                            recon_camera  (x1)
                        }
                    }
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    special_type_slot_5  (x1)
                    special_type_slot_6  (x4) {
                        any_of  (x3) {
                            air_ground_radar_1  (x1)
                            air_ground_radar_2  (x1)
                        }
                    }
                }
                type  (x1)
            }
        }
        priority  (x8) {
            factor  (x1)
            modifier  (x7) {
                all_owned_state  (x2) {
                    is_coastal  (x1)
                }
                factor  (x2)
                num_of_factories  (x1)
            }
        }
        roles  (x1) {
            air_maritime_patrol  (x1)
        }
    }
    ENG_medium_tank_anti_air  (x106) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        medium_tank_anti_air_1  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_medium_one_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        medium_tank_anti_air_2  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon_2  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_medium_two_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        medium_tank_anti_air_3  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon_3  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_medium_two_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x7) {
            factor  (x1)
            modifier  (x6) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                any_enemy_country  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
        roles  (x1) {
            land_medium_tank_anti_air  (x1)
        }
    }
    ENG_medium_tank_artillery  (x101) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        medium_tank_artillery_1  (x32) {
            allowed_modules  (x6) {
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_medium_fixed_superstructure_turret  (x1)
                tank_medium_howitzer  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        medium_tank_artillery_2  (x32) {
            allowed_modules  (x6) {
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_medium_fixed_superstructure_turret  (x1)
                tank_medium_howitzer_2  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        medium_tank_artillery_3  (x33) {
            allowed_modules  (x7) {
                extra_ammo_storage  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_howitzer  (x1)
                tank_medium_fixed_superstructure_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            land_medium_tank_artillery  (x1)
        }
    }
    ENG_medium_tank_destroyer  (x142) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        medium_tank_destroyer_1  (x38) {
            allowed_modules  (x8) {
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_medium_cannon  (x1)
                tank_medium_cannon_2  (x1)
                tank_medium_fixed_superstructure_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x24) {
                match_value  (x1)
                modules  (x14) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x5) {
                        any_of  (x4) {
                            tank_high_velocity_cannon_2  (x1)
                            tank_medium_cannon  (x1)
                            tank_medium_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        medium_tank_destroyer_2  (x45) {
            allowed_modules  (x12) {
                tank_bogie_suspension  (x1)
                tank_cast_armor  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_cannon  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_medium_cannon  (x1)
                tank_medium_cannon_2  (x1)
                tank_medium_fixed_superstructure_turret  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
            }
            enable  (x4) {
                OR  (x3) {
                    has_tech  (x2)
                }
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x25) {
                match_value  (x1)
                modules  (x15) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x6) {
                        any_of  (x5) {
                            tank_heavy_cannon  (x1)
                            tank_high_velocity_cannon_2  (x1)
                            tank_medium_cannon  (x1)
                            tank_medium_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        medium_tank_destroyer_3  (x49) {
            allowed_modules  (x15) {
                sloped_armor  (x1)
                smoke_launchers  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_cannon  (x1)
                tank_heavy_cannon_2  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_high_velocity_cannon_3  (x1)
                tank_medium_cannon_2  (x1)
                tank_medium_fixed_superstructure_turret  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_welded_armor  (x1)
            }
            enable  (x4) {
                OR  (x3) {
                    has_tech  (x2)
                }
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x26) {
                match_value  (x1)
                modules  (x16) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x7) {
                        any_of  (x6) {
                            tank_heavy_cannon  (x1)
                            tank_heavy_cannon_2  (x1)
                            tank_high_velocity_cannon_2  (x1)
                            tank_high_velocity_cannon_3  (x1)
                            tank_medium_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x7) {
            factor  (x1)
            modifier  (x6) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                any_enemy_country  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
        roles  (x1) {
            land_medium_tank_destroyer  (x1)
        }
    }
    ENG_medium_tanks  (x140) {
        advanced_medium_tank_default  (x31) {
            allowed_modules  (x11) {
                smoke_launchers  (x1)
                tank_christie_suspension  (x1)
                tank_gasoline_engine  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_medium_cannon_2  (x1)
                tank_medium_three_man_tank_turret  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_welded_armor  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x16) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x3) {
                    tank_nsb_armor_upgrade  (x1)
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        available_for  (x1) {
            ENG  (x1)
        }
        basic_medium_tank_default  (x34) {
            allowed_modules  (x7) {
                tank_christie_suspension  (x1)
                tank_gasoline_engine  (x1)
                tank_high_velocity_cannon  (x1)
                tank_medium_three_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
                tank_small_cannon_2  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x19) {
                match_value  (x1)
                modules  (x13) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x4) {
                        any_of  (x3) {
                            tank_high_velocity_cannon  (x1)
                            tank_small_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x3) {
                    tank_nsb_armor_upgrade  (x1)
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        basic_medium_tank_improved  (x35) {
            allowed_modules  (x7) {
                tank_christie_suspension  (x1)
                tank_gasoline_engine  (x1)
                tank_high_velocity_cannon  (x1)
                tank_medium_cannon  (x1)
                tank_medium_two_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x19) {
                match_value  (x1)
                modules  (x13) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x4) {
                        any_of  (x3) {
                            tank_high_velocity_cannon  (x1)
                            tank_medium_cannon  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x3) {
                    tank_nsb_armor_upgrade  (x1)
                    tank_nsb_engine_upgrade  (x1)
                }
            }
            visible  (x1)
        }
        blocked_for  (x1)
        improved_medium_tank_default  (x36) {
            allowed_modules  (x11) {
                tank_christie_suspension  (x1)
                tank_gasoline_engine  (x1)
                tank_high_velocity_cannon  (x1)
                tank_medium_cannon  (x1)
                tank_medium_cannon_2  (x1)
                tank_medium_three_man_tank_turret  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_riveted_armor  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x18) {
                match_value  (x1)
                modules  (x12) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x3) {
                        any_of  (x2) {
                            tank_medium_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x3) {
                    tank_nsb_armor_upgrade  (x1)
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            land_medium_tank  (x1)
        }
    }
    ENG_modern_tank_destroyer  (x54) {
        available_for  (x1) {
            ENG  (x1)
        }
        basic_modern_tank_destroyer_default  (x47) {
            allowed_modules  (x16) {
                sloped_armor  (x1)
                smoke_launchers  (x1)
                tank_cast_armor  (x1)
                tank_gas_turbine_engine  (x1)
                tank_heavy_cannon  (x1)
                tank_heavy_cannon_2  (x1)
                tank_heavy_cannon_3  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_high_velocity_cannon_3  (x1)
                tank_modern_tank_turret  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_torsion_bar_suspension  (x1)
                wet_ammo_storage  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x27) {
                match_value  (x1)
                modules  (x13) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x4) {
                        any_of  (x3) {
                            tank_heavy_cannon_3  (x1)
                            tank_high_velocity_cannon_3  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x11) {
                    tank_nsb_armor_upgrade  (x9) {
                        base  (x1)
                        modifier  (x7) {
                            add  (x2)
                            any_enemy_country  (x2) {
                                is_major  (x1)
                            }
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        blocked_for  (x1)
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                num_of_factories  (x1)
            }
        }
        roles  (x1) {
            land_modern_tank_destroyer  (x1)
        }
    }
    ENG_modern_tanks  (x57) {
        available_for  (x1) {
            ENG  (x1)
        }
        basic_modern_tank_default  (x50) {
            allowed_modules  (x16) {
                sloped_armor  (x1)
                smoke_launchers  (x1)
                stabilizer  (x1)
                tank_bogie_suspension  (x1)
                tank_gasoline_engine  (x1)
                tank_heavy_cannon  (x1)
                tank_heavy_cannon_2  (x1)
                tank_heavy_cannon_3  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_high_velocity_cannon_3  (x1)
                tank_modern_tank_turret  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_welded_armor  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x30) {
                match_value  (x1)
                modules  (x16) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x7) {
                        any_of  (x6) {
                            tank_heavy_cannon  (x1)
                            tank_heavy_cannon_2  (x1)
                            tank_heavy_cannon_3  (x1)
                            tank_high_velocity_cannon_2  (x1)
                            tank_high_velocity_cannon_3  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x11) {
                    tank_nsb_armor_upgrade  (x9) {
                        base  (x1)
                        modifier  (x7) {
                            add  (x2)
                            any_enemy_country  (x2) {
                                is_major  (x1)
                            }
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        blocked_for  (x1)
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                num_of_factories  (x1)
            }
        }
        roles  (x1) {
            land_modern_tank  (x1)
        }
    }
    ENG_naval_bomber  (x65) {
        available_for  (x1) {
            ENG  (x1)
        }
        naval_bomber_1  (x16) {
            allowed_modules  (x3) {
                engine_2_1x  (x1)
                nav_bomber_weapon  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                }
                type  (x1)
            }
        }
        naval_bomber_2  (x20) {
            allowed_modules  (x6) {
                bomb_locks  (x1)
                engine_2_2x  (x1)
                lmg_defense_turret  (x1)
                nav_bomber_weapon  (x1)
                self_sealing_fuel_tanks_small  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x10) {
                match_value  (x1)
                modules  (x7) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
        }
        naval_bomber_3  (x26) {
            allowed_modules  (x8) {
                bomb_locks  (x1)
                engine_2_2x  (x1)
                engine_3_2x  (x1)
                lmg_defense_turret  (x1)
                nav_bomber_weapon  (x1)
                self_sealing_fuel_tanks_small  (x1)
                small_bomb_bay  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    engine_type_slot  (x4) {
                        any_of  (x3) {
                            engine_2_2x  (x1)
                            engine_3_2x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_auxiliary_weapon_slot_2  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            air_naval_bomber  (x1)
        }
    }
    ENG_naval_capital_battleship  (x142) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        capital_battleship_advanced  (x32) {
            allowed_modules  (x10) {
                heavy_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_heavy_armor  (x1)
                ship_heavy_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x16) {
                match_value  (x1)
                modules  (x13) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    mid_3_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_battleship_basic  (x34) {
            allowed_modules  (x10) {
                heavy_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_heavy_armor  (x1)
                ship_heavy_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_battleship_early  (x34) {
            allowed_modules  (x10) {
                heavy_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_heavy_armor  (x1)
                ship_heavy_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_battleship_improved  (x35) {
            allowed_modules  (x10) {
                heavy_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_heavy_armor  (x1)
                ship_heavy_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x16) {
                match_value  (x1)
                modules  (x13) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    mid_3_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                date  (x1)
                factor  (x1)
            }
        }
        roles  (x1) {
            naval_capital_bb  (x1)
        }
    }
    ENG_naval_capital_bc  (x132) {
        available_for  (x1) {
            ENG  (x1)
        }
        battlecruiser_early  (x29) {
            allowed_modules  (x9) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_heavy_armor  (x1)
                ship_heavy_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        battlecruiser_early_aa_upgrade  (x36) {
            allowed_modules  (x9) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_heavy_armor  (x1)
                ship_heavy_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x8) {
                factor  (x1)
                modifier  (x6) {
                    factor  (x1)
                    has_navy_size  (x3) {
                        size  (x1)
                        unit  (x1)
                    }
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        battlecruiser_improved  (x30) {
            allowed_modules  (x9) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_heavy_armor  (x1)
                ship_heavy_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        battlecruiser_improved_upgrade  (x33) {
            allowed_modules  (x9) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_heavy_armor  (x1)
                ship_heavy_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        blocked_for  (x1)
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            naval_capital_bc  (x1)
        }
    }
    ENG_naval_carrier  (x142) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        carrier_advanced  (x26) {
            allowed_modules  (x8) {
                carrier_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_carrier_armor  (x1)
                ship_deck_space  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_deck_slot_1  (x1)
                    fixed_ship_deck_slot_2  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        carrier_basic  (x27) {
            Name  (x1)
            allowed_modules  (x8) {
                carrier_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_carrier_armor  (x1)
                ship_deck_space  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
            }
            enable  (x3) {
                not  (x2) {
                    has_tech  (x1)
                }
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x10) {
                match_value  (x1)
                modules  (x7) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_deck_slot_1  (x1)
                    fixed_ship_deck_slot_2  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        carrier_early  (x30) {
            allowed_modules  (x10) {
                carrier_ship_engine  (x1)
                cruiser_ship_engine  (x1)
                heavy_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_carrier_armor  (x1)
                ship_deck_space  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x11) {
                match_value  (x1)
                modules  (x8) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_deck_slot_1  (x1)
                    fixed_ship_deck_slot_2  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        carrier_early_upgrade  (x30) {
            allowed_modules  (x10) {
                carrier_ship_engine  (x1)
                cruiser_ship_engine  (x1)
                heavy_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_carrier_armor  (x1)
                ship_deck_space  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x11) {
                match_value  (x1)
                modules  (x8) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_deck_slot_1  (x1)
                    fixed_ship_deck_slot_2  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        carrier_improved  (x25) {
            allowed_modules  (x8) {
                carrier_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_carrier_armor  (x1)
                ship_deck_space  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x11) {
                match_value  (x1)
                modules  (x8) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_deck_slot_1  (x1)
                    fixed_ship_deck_slot_2  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            naval_carrier  (x1)
        }
    }
    ENG_naval_cruiser_heavy  (x181) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        capital_cruiser_advanced  (x30) {
            allowed_modules  (x8) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x16) {
                match_value  (x1)
                modules  (x13) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                    rear_2_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_cruiser_basic  (x29) {
            allowed_modules  (x7) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_dp_secondaries  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_cruiser_basic_aa_upgrade  (x30) {
            allowed_modules  (x7) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_dp_secondaries  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_cruiser_early  (x28) {
            allowed_modules  (x7) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_dp_secondaries  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_cruiser_early_aa_upgrade  (x29) {
            allowed_modules  (x7) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_dp_secondaries  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_War  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_cruiser_improved  (x31) {
            allowed_modules  (x8) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            naval_cruiser_heavy  (x1)
        }
    }
    ENG_naval_escort_carrier  (x59) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        carrier_escort  (x26) {
            allowed_modules  (x7) {
                carrier_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_carrier_armor  (x1)
                ship_escort_deck_space  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_deck_slot_1  (x1)
                    fixed_ship_deck_slot_2  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        improved_carrier_escort  (x26) {
            allowed_modules  (x7) {
                carrier_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_carrier_armor  (x1)
                ship_escort_deck_space  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_deck_slot_1  (x1)
                    fixed_ship_deck_slot_2  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                is_major  (x1)
            }
        }
        roles  (x1) {
            naval_carrier_light  (x1)
        }
    }
    ENG_naval_light_cruiser  (x146) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        cruiser_light_advanced  (x34) {
            allowed_modules  (x12) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_cruiser_armor  (x1)
                ship_depth_charge  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_light_medium_battery  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x16) {
                match_value  (x1)
                modules  (x13) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                    rear_2_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        cruiser_light_basic  (x36) {
            allowed_modules  (x12) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_cruiser_armor  (x1)
                ship_depth_charge  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_light_medium_battery  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        cruiser_light_early  (x35) {
            allowed_modules  (x12) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_cruiser_armor  (x1)
                ship_depth_charge  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_light_medium_battery  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        cruiser_light_improved  (x37) {
            allowed_modules  (x12) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_cruiser_armor  (x1)
                ship_depth_charge  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_light_medium_battery  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x16) {
                match_value  (x1)
                modules  (x13) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                    rear_2_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            naval_cruiser_light  (x1)
        }
    }
    ENG_strategic_bomber  (x112) {
        available_for  (x1) {
            ENG  (x1)
        }
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                num_of_factories  (x1)
            }
        }
        roles  (x1) {
            air_strategic_bomber  (x1)
        }
        strat_bomber_1_default  (x19) {
            allowed_modules  (x5) {
                engine_2_4x  (x1)
                large_bomb_bay  (x1)
                lmg_defense_turret  (x1)
                lmg_defense_turret_2x  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x10) {
                match_value  (x1)
                modules  (x7) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_auxiliary_weapon_slot_2  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                }
                type  (x1)
            }
        }
        strat_bomber_2_default  (x41) {
            allowed_modules  (x13) {
                air_ground_radar_1  (x1)
                air_ground_radar_2  (x1)
                armor_plate_large  (x1)
                bomb_sights_1  (x1)
                bomb_sights_2  (x1)
                engine_3_4x  (x1)
                fuel_tanks_large  (x1)
                large_bomb_bay  (x1)
                lmg_defense_turret_2x  (x1)
                radio_navigation_1  (x1)
                radio_navigation_2  (x1)
                self_sealing_fuel_tanks_large  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x24) {
                match_value  (x1)
                modules  (x21) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_auxiliary_weapon_slot_2  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x7) {
                        any_of  (x6) {
                            air_ground_radar_1  (x1)
                            air_ground_radar_2  (x1)
                            fuel_tanks_large  (x1)
                            radio_navigation_1  (x1)
                            radio_navigation_2  (x1)
                        }
                    }
                    special_type_slot_4  (x5) {
                        any_of  (x4) {
                            bomb_sights_1  (x1)
                            bomb_sights_2  (x1)
                            fuel_tanks_large  (x1)
                        }
                    }
                    special_type_slot_5  (x1)
                    special_type_slot_6  (x1)
                }
                type  (x1)
            }
        }
        strat_bomber_3_default  (x46) {
            allowed_modules  (x15) {
                air_ground_radar_1  (x1)
                air_ground_radar_2  (x1)
                armor_plate_large  (x1)
                bomb_sights_1  (x1)
                bomb_sights_2  (x1)
                cannon_defense_turret_2x  (x1)
                engine_3_4x  (x1)
                engine_4_4x  (x1)
                fuel_tanks_large  (x1)
                hmg_defense_turret_2x  (x1)
                large_bomb_bay  (x1)
                radio_navigation_1  (x1)
                radio_navigation_2  (x1)
                self_sealing_fuel_tanks_large  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x27) {
                match_value  (x1)
                modules  (x24) {
                    engine_type_slot  (x4) {
                        any_of  (x3) {
                            engine_3_4x  (x1)
                            engine_4_4x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_auxiliary_weapon_slot_2  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x7) {
                        any_of  (x6) {
                            air_ground_radar_1  (x1)
                            air_ground_radar_2  (x1)
                            fuel_tanks_large  (x1)
                            radio_navigation_1  (x1)
                            radio_navigation_2  (x1)
                        }
                    }
                    special_type_slot_4  (x5) {
                        any_of  (x4) {
                            bomb_sights_1  (x1)
                            bomb_sights_2  (x1)
                            fuel_tanks_large  (x1)
                        }
                    }
                    special_type_slot_5  (x1)
                    special_type_slot_6  (x1)
                }
                type  (x1)
            }
        }
    }
    ENG_super_heavy_tanks  (x60) {
        available_for  (x1) {
            ENG  (x1)
        }
        basic_super_heavy_tank_default  (x53) {
            allowed_modules  (x15) {
                sloped_armor  (x1)
                tank_cast_armor  (x1)
                tank_gasoline_engine  (x1)
                tank_heavy_cannon  (x1)
                tank_heavy_cannon_2  (x1)
                tank_heavy_cannon_3  (x1)
                tank_heavy_fixed_superstructure_turret  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_high_velocity_cannon_3  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_super_heavy_cannon  (x1)
                tank_torsion_bar_suspension  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_government  (x1)
                }
            }
            target_variant  (x31) {
                match_value  (x1)
                modules  (x17) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x8) {
                        any_of  (x7) {
                            tank_heavy_cannon  (x1)
                            tank_heavy_cannon_2  (x1)
                            tank_heavy_cannon_3  (x1)
                            tank_high_velocity_cannon_2  (x1)
                            tank_high_velocity_cannon_3  (x1)
                            tank_super_heavy_cannon  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x11) {
                    tank_nsb_armor_upgrade  (x9) {
                        base  (x1)
                        modifier  (x7) {
                            add  (x2)
                            any_enemy_country  (x2) {
                                is_major  (x1)
                            }
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        blocked_for  (x1)
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                num_of_factories  (x1)
            }
        }
        roles  (x1) {
            land_super_heavy_tank  (x1)
        }
    }
    ENG_tactical_bomber  (x127) {
        available_for  (x1) {
            ENG  (x1)
        }
        gw_tac_bomber_default  (x20) {
            allowed_modules  (x4) {
                engine_1_2x  (x1)
                medium_bomb_bay  (x1)
                self_sealing_fuel_tanks_medium  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                }
                type  (x1)
            }
        }
        jet_tac_bomber_default  (x21) {
            allowed_modules  (x6) {
                bomb_locks  (x1)
                fuel_tanks_medium  (x1)
                jet_engine_2x  (x1)
                medium_bomb_bay  (x1)
                self_sealing_fuel_tanks_medium  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x10) {
                match_value  (x1)
                modules  (x7) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_auxiliary_weapon_slot_2  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                }
                type  (x1)
            }
            visible  (x1)
        }
        priority  (x7) {
            factor  (x1)
            modifier  (x6) {
                factor  (x2)
                num_of_factories  (x2)
            }
        }
        roles  (x1) {
            air_tactical_bomber  (x1)
        }
        tac_bomber_1_default  (x18) {
            allowed_modules  (x5) {
                engine_2_2x  (x1)
                fuel_tanks_medium  (x1)
                medium_bomb_bay  (x1)
                self_sealing_fuel_tanks_medium  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    engine_type_slot  (x1)
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                }
                type  (x1)
            }
        }
        tac_bomber_2_default  (x26) {
            allowed_modules  (x8) {
                bomb_locks  (x1)
                engine_2_2x  (x1)
                engine_3_2x  (x1)
                fuel_tanks_medium  (x1)
                lmg_defense_turret_2x  (x1)
                medium_bomb_bay  (x1)
                self_sealing_fuel_tanks_medium  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    engine_type_slot  (x4) {
                        any_of  (x3) {
                            engine_2_2x  (x1)
                            engine_3_2x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_auxiliary_weapon_slot_2  (x1)
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                }
                type  (x1)
            }
        }
        tac_bomber_3_default  (x33) {
            allowed_modules  (x9) {
                bomb_locks  (x1)
                engine_3_2x  (x1)
                engine_4_2x  (x1)
                fuel_tanks_medium  (x1)
                medium_bomb_bay  (x1)
                nav_bomber_weapon  (x1)
                rocket_rails  (x1)
                self_sealing_fuel_tanks_medium  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x17) {
                    engine_type_slot  (x4) {
                        any_of  (x3) {
                            engine_3_2x  (x1)
                            engine_4_2x  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_1  (x1)
                    fixed_auxiliary_weapon_slot_2  (x4) {
                        any_of  (x3) {
                            bomb_locks  (x1)
                            rocket_rails  (x1)
                        }
                    }
                    fixed_auxiliary_weapon_slot_3  (x4) {
                        any_of  (x3) {
                            nav_bomber_weapon  (x1)
                            rocket_rails  (x1)
                        }
                    }
                    fixed_main_weapon_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                }
                type  (x1)
            }
        }
    }
    FRA_amphibious_tanks  (x49) {
        available_for  (x1) {
            FRA  (x1)
        }
        basic_amphibious_tank_default  (x45) {
            allowed_modules  (x8) {
                tank_bogie_suspension  (x1)
                tank_close_support_gun  (x1)
                tank_diesel_engine  (x1)
                tank_light_turret_type  (x1)
                tank_riveted_armor  (x1)
                tank_small_cannon  (x1)
                tank_small_cannon_2  (x1)
            }
            history  (x1)
            priority  (x7) {
                factor  (x1)
                modifier  (x5) {
                    OR  (x3) {
                        TAG  (x2)
                    }
                    factor  (x1)
                }
            }
            target_variant  (x28) {
                match_value  (x1)
                modules  (x14) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x5) {
                        any_of  (x4) {
                            tank_close_support_gun  (x1)
                            tank_small_cannon  (x1)
                            tank_small_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x11) {
                    tank_nsb_armor_upgrade  (x9) {
                        base  (x1)
                        modifier  (x7) {
                            add  (x2)
                            any_enemy_country  (x2) {
                                is_major  (x1)
                            }
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        blocked_for  (x1)
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            land_amphibious_tank  (x1)
        }
    }
    FRA_destroyers  (x210) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        destroyer_1_upgrade  (x29) {
            allowed_modules  (x9) {
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_light_battery  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        destroyer_2  (x28) {
            allowed_modules  (x9) {
                dp_light_battery  (x1)
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        destroyer_2_upgrade  (x28) {
            allowed_modules  (x9) {
                dp_light_battery  (x1)
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        destroyer_3  (x28) {
            allowed_modules  (x9) {
                dp_light_battery  (x1)
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        destroyer_3_upgrade  (x29) {
            allowed_modules  (x9) {
                dp_light_battery  (x1)
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        destroyer_4  (x34) {
            allowed_modules  (x9) {
                dp_light_battery  (x1)
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x8) {
                factor  (x1)
                modifier  (x6) {
                    OR  (x4) {
                        has_war_with  (x3)
                    }
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        destroyer_default  (x28) {
            allowed_modules  (x9) {
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_light_battery  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x3) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
        roles  (x1) {
            naval_screen  (x1)
        }
    }
    FRA_heavy_tank_anti_air  (x106) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        heavy_tank_anti_air_1  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_two_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        heavy_tank_anti_air_2  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon_2  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_two_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        heavy_tank_anti_air_3  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon_3  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_two_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x7) {
            factor  (x1)
            modifier  (x6) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                any_enemy_country  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
        roles  (x1) {
            land_heavy_tank_anti_air  (x1)
        }
    }
    FRA_heavy_tank_artillery  (x102) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        heavy_tank_artillery_1  (x32) {
            allowed_modules  (x6) {
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_fixed_superstructure_turret  (x1)
                tank_medium_howitzer  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        heavy_tank_artillery_2  (x33) {
            allowed_modules  (x7) {
                extra_ammo_storage  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_fixed_superstructure_turret  (x1)
                tank_medium_howitzer_2  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        heavy_tank_artillery_3  (x33) {
            allowed_modules  (x7) {
                extra_ammo_storage  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_fixed_superstructure_turret  (x1)
                tank_heavy_howitzer  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            land_heavy_tank_artillery  (x1)
        }
    }
    FRA_heavy_tank_destroyer  (x144) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        heavy_tank_destroyer_1  (x38) {
            allowed_modules  (x8) {
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_cannon  (x1)
                tank_heavy_cannon_2  (x1)
                tank_heavy_fixed_superstructure_turret  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x24) {
                match_value  (x1)
                modules  (x14) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x5) {
                        any_of  (x4) {
                            tank_heavy_cannon  (x1)
                            tank_heavy_cannon_2  (x1)
                            tank_high_velocity_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        heavy_tank_destroyer_2  (x48) {
            allowed_modules  (x14) {
                extra_ammo_storage  (x1)
                tank_bogie_suspension  (x1)
                tank_cast_armor  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_cannon  (x1)
                tank_heavy_cannon_2  (x1)
                tank_heavy_fixed_superstructure_turret  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_high_velocity_cannon_3  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_super_heavy_cannon  (x1)
            }
            enable  (x4) {
                OR  (x3) {
                    has_tech  (x2)
                }
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x26) {
                match_value  (x1)
                modules  (x16) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x7) {
                        any_of  (x6) {
                            tank_heavy_cannon  (x1)
                            tank_heavy_cannon_2  (x1)
                            tank_high_velocity_cannon_2  (x1)
                            tank_high_velocity_cannon_3  (x1)
                            tank_super_heavy_cannon  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        heavy_tank_destroyer_3  (x48) {
            allowed_modules  (x15) {
                extra_ammo_storage  (x1)
                sloped_armor  (x1)
                smoke_launchers  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_cannon_2  (x1)
                tank_heavy_fixed_superstructure_turret  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_high_velocity_cannon_3  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_super_heavy_cannon  (x1)
                tank_welded_armor  (x1)
            }
            enable  (x4) {
                OR  (x3) {
                    has_tech  (x2)
                }
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x25) {
                match_value  (x1)
                modules  (x15) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x6) {
                        any_of  (x5) {
                            tank_heavy_cannon_2  (x1)
                            tank_high_velocity_cannon_2  (x1)
                            tank_high_velocity_cannon_3  (x1)
                            tank_super_heavy_cannon  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x7) {
            factor  (x1)
            modifier  (x6) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                any_enemy_country  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
        roles  (x1) {
            land_heavy_tank_destroyer  (x1)
        }
    }
    FRA_heavy_tanks  (x147) {
        advanced_heavy_tank_default  (x47) {
            allowed_modules  (x14) {
                sloped_armor  (x1)
                smoke_launchers  (x1)
                tank_gasoline_engine  (x1)
                tank_heavy_cannon_2  (x1)
                tank_heavy_cannon_3  (x1)
                tank_heavy_three_man_tank_turret  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_high_velocity_cannon_3  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_torsion_bar_suspension  (x1)
                tank_welded_armor  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x29) {
                match_value  (x1)
                modules  (x15) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x6) {
                        any_of  (x5) {
                            tank_heavy_cannon_2  (x1)
                            tank_heavy_cannon_3  (x1)
                            tank_high_velocity_cannon_2  (x1)
                            tank_high_velocity_cannon_3  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x11) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                }
            }
        }
        available_for  (x1) {
            FRA  (x1)
        }
        basic_heavy_tank_default  (x38) {
            allowed_modules  (x12) {
                armor_skirts  (x1)
                secondary_turret_small_cannon  (x1)
                sloped_armor  (x1)
                tank_bogie_suspension  (x1)
                tank_cast_armor  (x1)
                tank_gasoline_engine  (x1)
                tank_heavy_fixed_superstructure_turret  (x1)
                tank_medium_howitzer  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
            }
            history  (x1)
            priority  (x8) {
                factor  (x1)
                modifier  (x6) {
                    factor  (x2)
                    has_completed_focus  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x16) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x3) {
                    tank_nsb_armor_upgrade  (x1)
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        blocked_for  (x1)
        improved_heavy_tank_default  (x55) {
            allowed_modules  (x15) {
                armor_skirts  (x1)
                tank_bogie_suspension  (x1)
                tank_cast_armor  (x1)
                tank_close_support_gun  (x1)
                tank_gasoline_engine  (x1)
                tank_heavy_cannon  (x1)
                tank_heavy_cannon_2  (x1)
                tank_heavy_three_man_tank_turret  (x1)
                tank_heavy_two_man_tank_turret  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_high_velocity_cannon_3  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x33) {
                match_value  (x1)
                modules  (x19) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x7) {
                        any_of  (x6) {
                            tank_close_support_gun  (x1)
                            tank_heavy_cannon  (x1)
                            tank_heavy_cannon_2  (x1)
                            tank_high_velocity_cannon_2  (x1)
                            tank_high_velocity_cannon_3  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x4) {
                        any_of  (x3) {
                            tank_heavy_three_man_tank_turret  (x1)
                            tank_heavy_two_man_tank_turret  (x1)
                        }
                    }
                }
                type  (x1)
                upgrades  (x11) {
                    tank_nsb_armor_upgrade  (x9) {
                        base  (x1)
                        modifier  (x7) {
                            add  (x2)
                            any_enemy_country  (x2) {
                                is_major  (x1)
                            }
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                num_of_factories  (x1)
            }
        }
        roles  (x1) {
            land_heavy_tank  (x1)
        }
    }
    FRA_light_tank_anti_air  (x106) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        light_tank_anti_air_1  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_light_one_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        light_tank_anti_air_2  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon_2  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_light_two_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        light_tank_anti_air_3  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon_2  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_light_two_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x7) {
            factor  (x1)
            modifier  (x6) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                any_enemy_country  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
        roles  (x1) {
            land_light_tank_anti_air  (x1)
        }
    }
    FRA_light_tank_artillery  (x101) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        light_tank_artillery_1  (x32) {
            allowed_modules  (x6) {
                tank_bogie_suspension  (x1)
                tank_close_support_gun  (x1)
                tank_diesel_engine  (x1)
                tank_light_fixed_superstructure_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        light_tank_artillery_2  (x32) {
            allowed_modules  (x6) {
                tank_bogie_suspension  (x1)
                tank_gasoline_engine  (x1)
                tank_light_fixed_superstructure_turret  (x1)
                tank_medium_howitzer  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        light_tank_artillery_3  (x33) {
            allowed_modules  (x7) {
                extra_ammo_storage  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_light_fixed_superstructure_turret  (x1)
                tank_medium_howitzer_2  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            land_light_tank_artillery  (x1)
        }
    }
    FRA_light_tank_destroyers  (x88) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        light_tank_destroyer_1  (x32) {
            allowed_modules  (x6) {
                tank_bogie_suspension  (x1)
                tank_gasoline_engine  (x1)
                tank_high_velocity_cannon  (x1)
                tank_light_fixed_superstructure_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        light_tank_destroyer_2  (x46) {
            allowed_modules  (x13) {
                extra_ammo_storage  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_high_velocity_cannon  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_light_fixed_superstructure_turret  (x1)
                tank_medium_cannon  (x1)
                tank_medium_cannon_2  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x4) {
                OR  (x3) {
                    has_tech  (x2)
                }
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x25) {
                match_value  (x1)
                modules  (x15) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x6) {
                        any_of  (x5) {
                            tank_high_velocity_cannon  (x1)
                            tank_high_velocity_cannon_2  (x1)
                            tank_medium_cannon  (x1)
                            tank_medium_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x7) {
            factor  (x1)
            modifier  (x6) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                any_enemy_country  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
        roles  (x1) {
            land_light_tank_destroyer  (x1)
        }
    }
    FRA_light_tanks  (x162) {
        advanced_light_tank_default  (x40) {
            allowed_modules  (x12) {
                tank_auto_cannon_2  (x1)
                tank_close_support_gun  (x1)
                tank_gasoline_engine  (x1)
                tank_high_velocity_cannon  (x1)
                tank_light_three_man_tank_turret  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_small_cannon_2  (x1)
                tank_torsion_bar_suspension  (x1)
                tank_welded_armor  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x24) {
                match_value  (x1)
                modules  (x14) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x5) {
                        any_of  (x4) {
                            tank_close_support_gun  (x1)
                            tank_high_velocity_cannon  (x1)
                            tank_small_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        available_for  (x1) {
            FRA  (x1)
        }
        basic_light_tank_default  (x40) {
            allowed_modules  (x9) {
                sloped_armor  (x1)
                tank_bogie_suspension  (x1)
                tank_cast_armor  (x1)
                tank_close_support_gun  (x1)
                tank_gasoline_engine  (x1)
                tank_light_one_man_tank_turret  (x1)
                tank_small_cannon  (x1)
                tank_small_cannon_2  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x24) {
                match_value  (x1)
                modules  (x14) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x5) {
                        any_of  (x4) {
                            tank_close_support_gun  (x1)
                            tank_small_cannon  (x1)
                            tank_small_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        blocked_for  (x1)
        great_war_tank_default  (x33) {
            allowed_modules  (x6) {
                tank_bogie_suspension  (x1)
                tank_gasoline_engine  (x1)
                tank_heavy_machine_gun  (x1)
                tank_light_one_man_tank_turret  (x1)
                tank_riveted_armor  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        improved_light_tank_default  (x45) {
            allowed_modules  (x13) {
                sloped_armor  (x1)
                tank_bogie_suspension  (x1)
                tank_close_support_gun  (x1)
                tank_diesel_engine  (x1)
                tank_high_velocity_cannon  (x1)
                tank_light_one_man_tank_turret  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_small_cannon  (x1)
                tank_small_cannon_2  (x1)
                tank_welded_armor  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x25) {
                match_value  (x1)
                modules  (x15) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x6) {
                        any_of  (x5) {
                            tank_close_support_gun  (x1)
                            tank_high_velocity_cannon  (x1)
                            tank_small_cannon  (x1)
                            tank_small_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            land_light_tank  (x1)
        }
    }
    FRA_medium_tank_anti_air  (x106) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        medium_tank_anti_air_1  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_medium_one_man_tank_turret  (x1)
                tank_welded_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        medium_tank_anti_air_2  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon_2  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_medium_two_man_tank_turret  (x1)
                tank_welded_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        medium_tank_anti_air_3  (x32) {
            allowed_modules  (x6) {
                tank_anti_air_cannon_3  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_medium_two_man_tank_turret  (x1)
                tank_welded_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x7) {
            factor  (x1)
            modifier  (x6) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                any_enemy_country  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
        roles  (x1) {
            land_medium_tank_anti_air  (x1)
        }
    }
    FRA_medium_tank_artillery  (x101) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        medium_tank_artillery_1  (x32) {
            allowed_modules  (x6) {
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_medium_fixed_superstructure_turret  (x1)
                tank_medium_howitzer  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        medium_tank_artillery_2  (x32) {
            allowed_modules  (x6) {
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_medium_fixed_superstructure_turret  (x1)
                tank_medium_howitzer_2  (x1)
                tank_welded_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        medium_tank_artillery_3  (x33) {
            allowed_modules  (x7) {
                extra_ammo_storage  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_howitzer  (x1)
                tank_medium_fixed_superstructure_turret  (x1)
                tank_welded_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x20) {
                match_value  (x1)
                modules  (x10) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x1)
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            land_medium_tank_artillery  (x1)
        }
    }
    FRA_medium_tank_destroyer  (x142) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        medium_tank_destroyer_1  (x38) {
            allowed_modules  (x8) {
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_medium_cannon  (x1)
                tank_medium_cannon_2  (x1)
                tank_medium_fixed_superstructure_turret  (x1)
                tank_riveted_armor  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x24) {
                match_value  (x1)
                modules  (x14) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x5) {
                        any_of  (x4) {
                            tank_high_velocity_cannon_2  (x1)
                            tank_medium_cannon  (x1)
                            tank_medium_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        medium_tank_destroyer_2  (x45) {
            allowed_modules  (x12) {
                tank_bogie_suspension  (x1)
                tank_cast_armor  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_cannon  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_medium_cannon  (x1)
                tank_medium_cannon_2  (x1)
                tank_medium_fixed_superstructure_turret  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
            }
            enable  (x4) {
                OR  (x3) {
                    has_tech  (x2)
                }
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x25) {
                match_value  (x1)
                modules  (x15) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x6) {
                        any_of  (x5) {
                            tank_heavy_cannon  (x1)
                            tank_high_velocity_cannon_2  (x1)
                            tank_medium_cannon  (x1)
                            tank_medium_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        medium_tank_destroyer_3  (x49) {
            allowed_modules  (x15) {
                sloped_armor  (x1)
                smoke_launchers  (x1)
                tank_bogie_suspension  (x1)
                tank_diesel_engine  (x1)
                tank_heavy_cannon  (x1)
                tank_heavy_cannon_2  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_high_velocity_cannon_3  (x1)
                tank_medium_cannon_2  (x1)
                tank_medium_fixed_superstructure_turret  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_welded_armor  (x1)
            }
            enable  (x4) {
                OR  (x3) {
                    has_tech  (x2)
                }
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x26) {
                match_value  (x1)
                modules  (x16) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x7) {
                        any_of  (x6) {
                            tank_heavy_cannon  (x1)
                            tank_heavy_cannon_2  (x1)
                            tank_high_velocity_cannon_2  (x1)
                            tank_high_velocity_cannon_3  (x1)
                            tank_medium_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x7) {
            factor  (x1)
            modifier  (x6) {
                NOT  (x2) {
                    has_tech  (x1)
                }
                any_enemy_country  (x2) {
                    has_tech  (x1)
                }
                factor  (x1)
            }
        }
        roles  (x1) {
            land_medium_tank_destroyer  (x1)
        }
    }
    FRA_medium_tanks  (x136) {
        advanced_medium_tank_default  (x48) {
            allowed_modules  (x12) {
                sloped_armor  (x1)
                smoke_launchers  (x1)
                tank_cast_armor  (x1)
                tank_close_support_gun  (x1)
                tank_gasoline_engine  (x1)
                tank_medium_cannon  (x1)
                tank_medium_three_man_tank_turret  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_torsion_bar_suspension  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x32) {
                match_value  (x1)
                modules  (x14) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x5) {
                        any_of  (x4) {
                            tank_close_support_gun  (x1)
                            tank_medium_cannon  (x1)
                            tank_medium_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x15) {
                    tank_nsb_armor_upgrade  (x9) {
                        base  (x1)
                        modifier  (x7) {
                            add  (x2)
                            any_enemy_country  (x2) {
                                is_major  (x1)
                            }
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                }
            }
        }
        available_for  (x1) {
            FRA  (x1)
        }
        basic_medium_tank_default  (x40) {
            allowed_modules  (x9) {
                tank_bogie_suspension  (x1)
                tank_cast_armor  (x1)
                tank_close_support_gun  (x1)
                tank_gasoline_engine  (x1)
                tank_high_velocity_cannon  (x1)
                tank_medium_one_man_tank_turret  (x1)
                tank_small_cannon  (x1)
                tank_small_cannon_2  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x24) {
                match_value  (x1)
                modules  (x14) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x5) {
                        any_of  (x4) {
                            tank_high_velocity_cannon  (x1)
                            tank_small_cannon  (x1)
                            tank_small_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        blocked_for  (x1)
        improved_medium_tank_default  (x44) {
            allowed_modules  (x13) {
                tank_bogie_suspension  (x1)
                tank_cast_armor  (x1)
                tank_close_support_gun  (x1)
                tank_gasoline_engine  (x1)
                tank_high_velocity_cannon  (x1)
                tank_medium_three_man_tank_turret  (x1)
                tank_medium_two_man_tank_turret  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_riveted_armor  (x1)
                tank_small_cannon_2  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_tech  (x1)
                }
            }
            target_variant  (x24) {
                match_value  (x1)
                modules  (x14) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x5) {
                        any_of  (x4) {
                            tank_close_support_gun  (x1)
                            tank_high_velocity_cannon  (x1)
                            tank_small_cannon_2  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x7) {
                    tank_nsb_armor_upgrade  (x5) {
                        base  (x1)
                        modifier  (x3) {
                            add  (x1)
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            land_medium_tank  (x1)
        }
    }
    FRA_modern_tank_destroyer  (x57) {
        available_for  (x1) {
            FRA  (x1)
        }
        basic_modern_tank_destroyer_default  (x50) {
            allowed_modules  (x16) {
                auto_loader  (x1)
                sloped_armor  (x1)
                smoke_launchers  (x1)
                tank_cast_armor  (x1)
                tank_gas_turbine_engine  (x1)
                tank_heavy_cannon  (x1)
                tank_heavy_cannon_2  (x1)
                tank_heavy_cannon_3  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_high_velocity_cannon_3  (x1)
                tank_modern_tank_turret  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_torsion_bar_suspension  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x30) {
                match_value  (x1)
                modules  (x16) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x7) {
                        any_of  (x6) {
                            tank_heavy_cannon  (x1)
                            tank_heavy_cannon_2  (x1)
                            tank_heavy_cannon_3  (x1)
                            tank_high_velocity_cannon_2  (x1)
                            tank_high_velocity_cannon_3  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x11) {
                    tank_nsb_armor_upgrade  (x9) {
                        base  (x1)
                        modifier  (x7) {
                            add  (x2)
                            any_enemy_country  (x2) {
                                is_major  (x1)
                            }
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        blocked_for  (x1)
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                num_of_factories  (x1)
            }
        }
        roles  (x1) {
            land_modern_tank_destroyer  (x1)
        }
    }
    FRA_modern_tanks  (x57) {
        available_for  (x1) {
            FRA  (x1)
        }
        basic_modern_tank_default  (x50) {
            allowed_modules  (x16) {
                auto_loader  (x1)
                sloped_armor  (x1)
                smoke_launchers  (x1)
                tank_cast_armor  (x1)
                tank_gas_turbine_engine  (x1)
                tank_heavy_cannon  (x1)
                tank_heavy_cannon_2  (x1)
                tank_heavy_cannon_3  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_high_velocity_cannon_3  (x1)
                tank_modern_tank_turret  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_torsion_bar_suspension  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            target_variant  (x30) {
                match_value  (x1)
                modules  (x16) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x7) {
                        any_of  (x6) {
                            tank_heavy_cannon  (x1)
                            tank_heavy_cannon_2  (x1)
                            tank_heavy_cannon_3  (x1)
                            tank_high_velocity_cannon_2  (x1)
                            tank_high_velocity_cannon_3  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x11) {
                    tank_nsb_armor_upgrade  (x9) {
                        base  (x1)
                        modifier  (x7) {
                            add  (x2)
                            any_enemy_country  (x2) {
                                is_major  (x1)
                            }
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        blocked_for  (x1)
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                num_of_factories  (x1)
            }
        }
        roles  (x1) {
            land_modern_tank  (x1)
        }
    }
    FRA_naval_capital_battleship  (x185) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        capital_battleship_basic  (x28) {
            allowed_modules  (x8) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_fire_control_system  (x1)
                ship_heavy_armor  (x1)
                ship_heavy_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_battleship_basic_aa_upgrade  (x31) {
            allowed_modules  (x8) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_fire_control_system  (x1)
                ship_heavy_armor  (x1)
                ship_heavy_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_battleship_early  (x28) {
            allowed_modules  (x8) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_fire_control_system  (x1)
                ship_heavy_armor  (x1)
                ship_heavy_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_battleship_early_aa_upgrade  (x31) {
            allowed_modules  (x8) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_fire_control_system  (x1)
                ship_heavy_armor  (x1)
                ship_heavy_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_battleship_improved  (x29) {
            allowed_modules  (x8) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_fire_control_system  (x1)
                ship_heavy_armor  (x1)
                ship_heavy_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x16) {
                match_value  (x1)
                modules  (x13) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    mid_3_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_battleship_improved_upgrade  (x32) {
            allowed_modules  (x8) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_fire_control_system  (x1)
                ship_heavy_armor  (x1)
                ship_heavy_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x16) {
                match_value  (x1)
                modules  (x13) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    mid_3_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x3) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
        roles  (x1) {
            naval_capital_bb  (x1)
        }
    }
    FRA_naval_capital_bc  (x67) {
        available_for  (x1) {
            FRA  (x1)
        }
        battlecruiser_early  (x28) {
            allowed_modules  (x8) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_fire_control_system  (x1)
                ship_heavy_armor  (x1)
                ship_heavy_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        battlecruiser_early_aa_upgrade  (x34) {
            allowed_modules  (x8) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_fire_control_system  (x1)
                ship_heavy_armor  (x1)
                ship_heavy_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            priority  (x8) {
                factor  (x1)
                modifier  (x6) {
                    factor  (x1)
                    has_navy_size  (x3) {
                        size  (x1)
                        unit  (x1)
                    }
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        blocked_for  (x1)
        priority  (x2) {
            factor  (x1)
            modifier  (x1)
        }
        roles  (x1) {
            naval_capital_bc  (x1)
        }
    }
    FRA_naval_carrier  (x134) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        carrier_advanced  (x25) {
            allowed_modules  (x8) {
                carrier_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_carrier_armor  (x1)
                ship_deck_space  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_deck_slot_1  (x1)
                    fixed_ship_deck_slot_2  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        carrier_basic  (x24) {
            allowed_modules  (x8) {
                carrier_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_carrier_armor  (x1)
                ship_deck_space  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x11) {
                match_value  (x1)
                modules  (x8) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_deck_slot_1  (x1)
                    fixed_ship_deck_slot_2  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        carrier_early  (x28) {
            allowed_modules  (x10) {
                carrier_ship_engine  (x1)
                cruiser_ship_engine  (x1)
                heavy_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_carrier_armor  (x1)
                ship_deck_space  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x11) {
                match_value  (x1)
                modules  (x8) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_deck_slot_1  (x1)
                    fixed_ship_deck_slot_2  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        carrier_early_upgrade  (x28) {
            allowed_modules  (x10) {
                carrier_ship_engine  (x1)
                cruiser_ship_engine  (x1)
                heavy_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_carrier_armor  (x1)
                ship_deck_space  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x11) {
                match_value  (x1)
                modules  (x8) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_deck_slot_1  (x1)
                    fixed_ship_deck_slot_2  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        carrier_improved  (x25) {
            allowed_modules  (x8) {
                carrier_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_carrier_armor  (x1)
                ship_deck_space  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_deck_slot_1  (x1)
                    fixed_ship_deck_slot_2  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            naval_carrier  (x1)
        }
    }
    FRA_naval_carrier_light  (x59) {
        CVL_carrier  (x26) {
            allowed_modules  (x9) {
                carrier_ship_engine  (x1)
                cruiser_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_carrier_armor  (x1)
                ship_deck_space  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x10) {
                match_value  (x1)
                modules  (x7) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_deck_slot_1  (x1)
                    fixed_ship_deck_slot_2  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                }
                type  (x1)
            }
        }
        CVL_carrier_upgrade  (x26) {
            allowed_modules  (x9) {
                carrier_ship_engine  (x1)
                cruiser_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_carrier_armor  (x1)
                ship_deck_space  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x10) {
                match_value  (x1)
                modules  (x7) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_deck_slot_1  (x1)
                    fixed_ship_deck_slot_2  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                }
                type  (x1)
            }
        }
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                has_War  (x1)
            }
        }
        roles  (x1) {
            naval_carrier  (x1)
        }
    }
    FRA_naval_cruiser_heavy  (x224) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        capital_cruiser_advanced  (x27) {
            allowed_modules  (x7) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_fire_control_system  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_cruiser_advanced_upgrade  (x30) {
            allowed_modules  (x7) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_fire_control_system  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_cruiser_basic  (x26) {
            allowed_modules  (x6) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_cruiser_basic_aa_upgrade  (x27) {
            allowed_modules  (x6) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_cruiser_early  (x27) {
            allowed_modules  (x6) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_cruiser_early_aa_upgrade  (x28) {
            allowed_modules  (x6) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_War  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_cruiser_improved  (x27) {
            allowed_modules  (x7) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_fire_control_system  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        capital_cruiser_late  (x28) {
            allowed_modules  (x7) {
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_fire_control_system  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x16) {
                match_value  (x1)
                modules  (x13) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                    rear_2_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            naval_cruiser_heavy  (x1)
        }
    }
    FRA_naval_escort_carrier  (x32) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        carrier_escort  (x25) {
            allowed_modules  (x7) {
                carrier_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_carrier_armor  (x1)
                ship_escort_deck_space  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_deck_slot_1  (x1)
                    fixed_ship_deck_slot_2  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                is_major  (x1)
            }
        }
        roles  (x1) {
            naval_carrier_light  (x1)
        }
    }
    FRA_naval_light_AA_cruiser  (x46) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        cruiser_light_AA  (x36) {
            allowed_modules  (x11) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_light_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x7) {
            factor  (x1)
            modifier  (x6) {
                OR  (x4) {
                    has_war_with  (x3)
                }
                factor  (x1)
            }
        }
        roles  (x1) {
            naval_cruiser_light  (x1)
        }
    }
    FRA_naval_light_cruiser  (x227) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        cruiser_light_advanced  (x31) {
            allowed_modules  (x10) {
                cruiser_ship_engine  (x1)
                dp_ship_secondaries_1  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x16) {
                match_value  (x1)
                modules  (x13) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                    rear_2_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        cruiser_light_basic  (x31) {
            allowed_modules  (x11) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        cruiser_light_basic_upgrade  (x32) {
            allowed_modules  (x11) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        cruiser_light_early  (x30) {
            allowed_modules  (x11) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_light_medium_battery_1  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        cruiser_light_early_aa_conversion  (x36) {
            allowed_modules  (x12) {
                cruiser_ship_engine  (x1)
                dp_light_battery  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_light_medium_battery_1  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        cruiser_light_early_aa_upgrade  (x32) {
            allowed_modules  (x11) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_light_medium_battery_1  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x13) {
                match_value  (x1)
                modules  (x10) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        cruiser_light_improved  (x31) {
            allowed_modules  (x11) {
                cruiser_ship_engine  (x1)
                ship_airplane_launcher  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_medium_battery  (x1)
                ship_radar  (x1)
                ship_secondaries  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x15) {
                match_value  (x1)
                modules  (x12) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x1) {
            factor  (x1)
        }
        roles  (x1) {
            naval_cruiser_light  (x1)
        }
    }
    FRA_naval_mine_layer  (x95) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        mine_layer_cruiser  (x31) {
            allowed_modules  (x8) {
                cruiser_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_fire_control_system  (x1)
                ship_light_battery  (x1)
                ship_mine_layer_1  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            requirements  (x2) {
                module  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x4) {
                        any_of  (x2) {
                            ship_light_battery  (x1)
                        }
                        upgrade  (x1)
                    }
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        mine_layer_light  (x33) {
            allowed_modules  (x10) {
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_light_battery  (x1)
                ship_mine_layer_1  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            requirements  (x2) {
                module  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x4) {
                        any_of  (x3) {
                            ship_radar  (x1)
                            ship_sonar  (x1)
                        }
                    }
                    fixed_ship_torpedo_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                has_war  (x1)
            }
        }
        roles  (x1) {
            naval_mine_layer  (x1)
        }
        submarine_mine_layer  (x24) {
            allowed_modules  (x6) {
                ship_mine_layer_sub  (x1)
                ship_radar  (x1)
                ship_sub_snorkel  (x1)
                ship_torpedo_sub  (x1)
                sub_ship_engine  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            requirements  (x2) {
                module  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x8) {
                match_value  (x1)
                modules  (x5) {
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    front_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
    }
    FRA_naval_mine_sweeper  (x69) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        mine_sweeper_light_early  (x27) {
            allowed_modules  (x9) {
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_light_battery  (x1)
                ship_mine_warfare  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            requirements  (x2) {
                module  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        mine_sweeper_light_late  (x35) {
            allowed_modules  (x10) {
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_light_battery  (x1)
                ship_mine_sweeper_1  (x1)
                ship_mine_warfare  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            requirements  (x2) {
                module  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x5) {
                        any_of  (x3) {
                            dp_light_battery_1  (x1)
                            ship_light_battery_1  (x1)
                        }
                        upgrade  (x1)
                    }
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                has_war  (x1)
            }
        }
        roles  (x1) {
            naval_mine_sweeper  (x1)
        }
    }
    FRA_naval_submarine  (x115) {
        available_for  (x1) {
            FRA  (x1)
        }
        blocked_for  (x1)
        cruiser_submarine  (x23) {
            allowed_modules  (x6) {
                ship_mine_layer_sub  (x1)
                ship_radar  (x1)
                ship_sub_snorkel  (x1)
                ship_torpedo_sub  (x1)
                sub_ship_engine  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war_with  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                has_war  (x1)
            }
        }
        roles  (x1) {
            naval_submarine  (x1)
        }
        submarine_advanced  (x23) {
            allowed_modules  (x6) {
                ship_mine_layer_sub  (x1)
                ship_radar  (x1)
                ship_sub_snorkel  (x1)
                ship_torpedo_sub  (x1)
                sub_ship_engine  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war_with  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        submarine_basic  (x20) {
            allowed_modules  (x6) {
                ship_mine_layer_sub  (x1)
                ship_radar  (x1)
                ship_sub_snorkel  (x1)
                ship_torpedo_sub  (x1)
                sub_ship_engine  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x7) {
                match_value  (x1)
                modules  (x4) {
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        submarine_early  (x20) {
            allowed_modules  (x6) {
                ship_mine_layer_sub  (x1)
                ship_radar  (x1)
                ship_sub_snorkel  (x1)
                ship_torpedo_sub  (x1)
                sub_ship_engine  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x7) {
                match_value  (x1)
                modules  (x4) {
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        submarine_improved  (x22) {
            allowed_modules  (x6) {
                ship_mine_layer_sub  (x1)
                ship_radar  (x1)
                ship_sub_snorkel  (x1)
                ship_torpedo_sub  (x1)
                sub_ship_engine  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
    }
    FRA_super_heavy_tanks  (x62) {
        available_for  (x1) {
            FRA  (x1)
        }
        basic_super_heavy_tank_default  (x55) {
            allowed_modules  (x17) {
                auto_loader  (x1)
                secondary_turret_hmg  (x1)
                sloped_armor  (x1)
                tank_cast_armor  (x1)
                tank_heavy_cannon  (x1)
                tank_heavy_cannon_2  (x1)
                tank_heavy_cannon_3  (x1)
                tank_high_velocity_cannon_2  (x1)
                tank_high_velocity_cannon_3  (x1)
                tank_interleaved_suspension  (x1)
                tank_petrol_electric_engine  (x1)
                tank_radio_1  (x1)
                tank_radio_2  (x1)
                tank_radio_3  (x1)
                tank_super_heavy_cannon  (x1)
                tank_super_heavy_four_man_tank_turret  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_government  (x1)
                }
            }
            target_variant  (x31) {
                match_value  (x1)
                modules  (x17) {
                    armor_type_slot  (x1)
                    engine_type_slot  (x1)
                    main_armament_slot  (x8) {
                        any_of  (x7) {
                            tank_heavy_cannon  (x1)
                            tank_heavy_cannon_2  (x1)
                            tank_heavy_cannon_3  (x1)
                            tank_high_velocity_cannon_2  (x1)
                            tank_high_velocity_cannon_3  (x1)
                            tank_super_heavy_cannon  (x1)
                        }
                    }
                    special_type_slot_1  (x1)
                    special_type_slot_2  (x1)
                    special_type_slot_3  (x1)
                    special_type_slot_4  (x1)
                    suspension_type_slot  (x1)
                    turret_type_slot  (x1)
                }
                type  (x1)
                upgrades  (x11) {
                    tank_nsb_armor_upgrade  (x9) {
                        base  (x1)
                        modifier  (x7) {
                            add  (x2)
                            any_enemy_country  (x2) {
                                is_major  (x1)
                            }
                            has_war  (x1)
                        }
                    }
                    tank_nsb_engine_upgrade  (x1)
                }
            }
        }
        blocked_for  (x1)
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                num_of_factories  (x1)
            }
        }
        roles  (x1) {
            land_super_heavy_tank  (x1)
        }
    }
    naval_carrier_light  (x32) {
        CVL_carrier  (x25) {
            allowed_modules  (x9) {
                carrier_ship_engine  (x1)
                cruiser_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_carrier_armor  (x1)
                ship_deck_space  (x1)
                ship_dp_secondaries  (x1)
                ship_fire_control_system  (x1)
                ship_radar  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x2) {
                factor  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x10) {
                match_value  (x1)
                modules  (x7) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_deck_slot_1  (x1)
                    fixed_ship_deck_slot_2  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                }
                type  (x1)
            }
        }
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                has_War  (x1)
            }
        }
        roles  (x1) {
            naval_carrier_light  (x1)
        }
    }
    naval_mine_layer  (x91) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        mine_layer_cruiser  (x32) {
            allowed_modules  (x8) {
                cruiser_ship_engine  (x1)
                dp_light_battery  (x1)
                ship_anti_air  (x1)
                ship_fire_control_system  (x1)
                ship_mine_layer_1  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    num_of_naval_factories  (x1)
                }
            }
            requirements  (x2) {
                module  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x14) {
                match_value  (x1)
                modules  (x11) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_armor_slot  (x1)
                    fixed_ship_battery_slot  (x4) {
                        any_of  (x2) {
                            dp_light_battery  (x1)
                        }
                        upgrade  (x1)
                    }
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_secondaries_slot  (x1)
                    mid_2_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        mine_layer_light  (x29) {
            allowed_modules  (x8) {
                dp_light_battery  (x1)
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_mine_layer_1  (x1)
                ship_torpedo  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            requirements  (x2) {
                module  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x12) {
                match_value  (x1)
                modules  (x9) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                has_war  (x1)
            }
        }
        roles  (x1) {
            naval_mine_layer  (x1)
        }
        submarine_mine_layer  (x23) {
            allowed_modules  (x6) {
                ship_mine_layer_sub  (x1)
                ship_radar  (x1)
                ship_sub_snorkel  (x1)
                ship_torpedo_sub  (x1)
                sub_ship_engine  (x1)
            }
            history  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war  (x1)
                }
            }
            requirements  (x2) {
                module  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x7) {
                match_value  (x1)
                modules  (x4) {
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
    }
    naval_mine_sweeper  (x74) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        mine_sweeper_light_early  (x29) {
            allowed_modules  (x9) {
                dp_light_battery  (x1)
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_mine_warfare  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
            }
            enable  (x2) {
                has_tech  (x1)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            requirements  (x2) {
                module  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    fixed_ship_battery_slot  (x1)
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        mine_sweeper_light_late  (x38) {
            allowed_modules  (x10) {
                dp_light_battery  (x1)
                light_ship_engine  (x1)
                ship_anti_air  (x1)
                ship_depth_charge  (x1)
                ship_fire_control_system  (x1)
                ship_mine_sweeper_1  (x1)
                ship_mine_warfare  (x1)
                ship_radar  (x1)
                ship_sonar  (x1)
            }
            enable  (x3) {
                has_tech  (x2)
            }
            history  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            requirements  (x2) {
                module  (x1)
            }
            role_icon_index  (x1)
            target_variant  (x16) {
                match_value  (x1)
                modules  (x13) {
                    fixed_ship_anti_air_slot  (x1)
                    fixed_ship_battery_slot  (x5) {
                        any_of  (x3) {
                            dp_light_battery_1  (x1)
                            ship_light_battery_1  (x1)
                        }
                        upgrade  (x1)
                    }
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_fire_control_system_slot  (x1)
                    fixed_ship_radar_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                has_war  (x1)
            }
        }
        roles  (x1) {
            naval_mine_sweeper  (x1)
        }
    }
    naval_submarine  (x96) {
        available_for  (x1) {
            ENG  (x1)
        }
        blocked_for  (x1)
        priority  (x4) {
            factor  (x1)
            modifier  (x3) {
                factor  (x1)
                has_war  (x1)
            }
        }
        roles  (x1) {
            naval_submarine  (x1)
        }
        submarine_advanced  (x24) {
            allowed_modules  (x6) {
                ship_mine_layer_sub  (x1)
                ship_radar  (x1)
                ship_sub_snorkel  (x1)
                ship_torpedo_sub  (x1)
                sub_ship_engine  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x5) {
                factor  (x1)
                modifier  (x3) {
                    factor  (x1)
                    has_war_with  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        submarine_basic  (x21) {
            allowed_modules  (x6) {
                ship_mine_layer_sub  (x1)
                ship_radar  (x1)
                ship_sub_snorkel  (x1)
                ship_torpedo_sub  (x1)
                sub_ship_engine  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x7) {
                match_value  (x1)
                modules  (x4) {
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        submarine_early  (x21) {
            allowed_modules  (x6) {
                ship_mine_layer_sub  (x1)
                ship_radar  (x1)
                ship_sub_snorkel  (x1)
                ship_torpedo_sub  (x1)
                sub_ship_engine  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x7) {
                match_value  (x1)
                modules  (x4) {
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
        submarine_improved  (x23) {
            allowed_modules  (x6) {
                ship_mine_layer_sub  (x1)
                ship_radar  (x1)
                ship_sub_snorkel  (x1)
                ship_torpedo_sub  (x1)
                sub_ship_engine  (x1)
            }
            history  (x1)
            name  (x1)
            priority  (x4) {
                factor  (x1)
                modifier  (x2) {
                    factor  (x1)
                }
            }
            role_icon_index  (x1)
            target_variant  (x9) {
                match_value  (x1)
                modules  (x6) {
                    fixed_ship_engine_slot  (x1)
                    fixed_ship_torpedo_slot  (x1)
                    front_1_custom_slot  (x1)
                    mid_1_custom_slot  (x1)
                    rear_1_custom_slot  (x1)
                }
                type  (x1)
            }
        }
    }
}
```


## AI 派系战区编辑器（ai_faction_theaters）

> 说明：未知字段走 ScriptBlockEditor

扫描文件：1

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

总缺失条数：**949**

##### common/ai_faction_theaters

```text
common/ai_faction_theaters  (x949) {
    barbarossa_center  (x21) {
        ai_will_do  (x6) {
            base  (x1)
            modifier  (x4) {
                add  (x1)
                has_war_with  (x1)
                original_tag  (x1)
            }
        }
        cancel  (x3) {
            NOT  (x2) {
                has_war_with  (x1)
            }
        }
        preferred_countries  (x3) {
            GER  (x1)
            SLO  (x1)
        }
        regions  (x9) {
            131  (x1)
            133  (x1)
            138  (x1)
            14  (x1)
            22  (x1)
            38  (x1)
            39  (x1)
            40  (x1)
            8  (x1)
        }
    }
    barbarossa_north  (x26) {
        ai_will_do  (x10) {
            base  (x1)
            modifier  (x8) {
                add  (x2)
                has_war_with  (x2)
                is_in_faction_with  (x1)
                original_tag  (x1)
            }
        }
        cancel  (x3) {
            NOT  (x2) {
                has_war_with  (x1)
            }
        }
        regions  (x13) {
            12  (x1)
            13  (x1)
            132  (x1)
            150  (x1)
            191  (x1)
            206  (x1)
            265  (x1)
            277  (x1)
            278  (x1)
            279  (x1)
            37  (x1)
            46  (x1)
            9  (x1)
        }
    }
    barbarossa_south  (x22) {
        ai_will_do  (x8) {
            base  (x1)
            modifier  (x6) {
                OR  (x3) {
                    is_in_faction_with  (x1)
                    original_tag  (x1)
                }
                add  (x1)
                has_war_with  (x1)
            }
        }
        cancel  (x3) {
            NOT  (x2) {
                has_war_with  (x1)
            }
        }
        preferred_countries  (x3) {
            ITA  (x1)
            ROM  (x1)
        }
        regions  (x8) {
            130  (x1)
            135  (x1)
            137  (x1)
            26  (x1)
            267  (x1)
            27  (x1)
            270  (x1)
            30  (x1)
        }
    }
    bengal  (x32) {
        ai_will_do  (x22) {
            base  (x1)
            modifier  (x20) {
                OR  (x15) {
                    any_enemy_country  (x8) {
                        OR  (x7) {
                            controls_state  (x6)
                        }
                    }
                    controls_state  (x6)
                }
                add  (x1)
                factor  (x1)
                has_war  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x8) {
            101  (x1)
            141  (x1)
            230  (x1)
            231  (x1)
            290  (x1)
            293  (x1)
            294  (x1)
            31  (x1)
        }
    }
    black_sea_region  (x36) {
        ai_will_do  (x26) {
            base  (x1)
            modifier  (x24) {
                OR  (x10) {
                    controls_state  (x6)
                    has_war_with  (x1)
                    original_tag  (x1)
                }
                add  (x1)
                any_enemy_country  (x7) {
                    controls_state  (x6)
                }
                factor  (x2)
                has_war  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x8) {
            129  (x1)
            130  (x1)
            134  (x1)
            135  (x1)
            202  (x1)
            25  (x1)
            26  (x1)
            30  (x1)
        }
    }
    brazil  (x29) {
        ai_will_do  (x17) {
            base  (x1)
            modifier  (x15) {
                NOT  (x3) {
                    126  (x2) {
                        is_controlled_by_ROOT_or_ally  (x1)
                    }
                }
                OR  (x3) {
                    original_tag  (x2)
                }
                add  (x1)
                factor  (x2)
                has_war  (x1)
                has_war_with  (x1)
                is_historical_focus_on  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x10) {
            125  (x1)
            163  (x1)
            280  (x1)
            281  (x1)
            282  (x1)
            286  (x1)
            287  (x1)
            288  (x1)
            61  (x1)
            66  (x1)
        }
    }
    central_america  (x38) {
        ai_will_do  (x26) {
            base  (x1)
            modifier  (x24) {
                NOT  (x3) {
                    126  (x2) {
                        is_controlled_by_ROOT_or_ally  (x1)
                    }
                }
                OR  (x13) {
                    has_war_with  (x9)
                    original_tag  (x2)
                }
                add  (x1)
                factor  (x2)
                has_war  (x1)
                is_historical_focus_on  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x10) {
            106  (x1)
            107  (x1)
            123  (x1)
            124  (x1)
            170  (x1)
            204  (x1)
            205  (x1)
            34  (x1)
            52  (x1)
            53  (x1)
        }
    }
    central_pacific  (x32) {
        ai_will_do  (x18) {
            base  (x1)
            modifier  (x16) {
                add  (x3)
                any_enemy_country  (x2) {
                    controls_state  (x1)
                }
                controls_state  (x2)
                factor  (x1)
                has_war  (x1)
                has_war_with  (x2)
                original_tag  (x1)
            }
        }
        cancel  (x5) {
            AND  (x4) {
                any_enemy_country  (x2) {
                    controls_state  (x1)
                }
                original_tag  (x1)
            }
        }
        regions  (x9) {
            105  (x1)
            172  (x1)
            176  (x1)
            177  (x1)
            180  (x1)
            94  (x1)
            95  (x1)
            96  (x1)
            97  (x1)
        }
    }
    chinese_coastline  (x25) {
        ai_will_do  (x14) {
            base  (x1)
            modifier  (x12) {
                OR  (x3) {
                    is_literally_china  (x1)
                    original_tag  (x1)
                }
                add  (x2)
                any_enemy_country  (x2) {
                    is_literally_china  (x1)
                }
                factor  (x1)
                has_war  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x9) {
            143  (x1)
            155  (x1)
            164  (x1)
            186  (x1)
            247  (x1)
            248  (x1)
            75  (x1)
            76  (x1)
            77  (x1)
        }
    }
    chinese_mainland  (x25) {
        ai_will_do  (x12) {
            base  (x1)
            modifier  (x10) {
                OR  (x4) {
                    any_enemy_country  (x2) {
                        is_literally_china  (x1)
                    }
                    is_literally_china  (x1)
                }
                add  (x1)
                factor  (x1)
                has_war  (x2)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x11) {
            144  (x1)
            145  (x1)
            146  (x1)
            165  (x1)
            200  (x1)
            244  (x1)
            245  (x1)
            246  (x1)
            249  (x1)
            250  (x1)
            252  (x1)
        }
    }
    east_africa  (x30) {
        ai_will_do  (x17) {
            base  (x1)
            modifier  (x15) {
                add  (x2)
                capital_scope  (x2) {
                    is_on_continent  (x1)
                }
                factor  (x1)
                has_war  (x1)
                owns_any_state_of  (x6) {
                    217  (x1)
                    268  (x1)
                    269  (x1)
                    551  (x1)
                    559  (x1)
                }
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x11) {
            100  (x1)
            102  (x1)
            17  (x1)
            181  (x1)
            183  (x1)
            216  (x1)
            217  (x1)
            227  (x1)
            273  (x1)
            274  (x1)
            60  (x1)
        }
    }
    eastern_europe  (x32) {
        ai_will_do  (x19) {
            base  (x1)
            modifier  (x17) {
                OR  (x4) {
                    has_war_with  (x3)
                }
                add  (x3)
                capital_scope  (x2) {
                    is_on_continent  (x1)
                }
                factor  (x1)
                has_war  (x1)
                has_war_with  (x1)
                original_tag  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x11) {
            130  (x1)
            131  (x1)
            132  (x1)
            133  (x1)
            206  (x1)
            22  (x1)
            27  (x1)
            37  (x1)
            38  (x1)
            39  (x1)
            8  (x1)
        }
    }
    gran_columbia  (x32) {
        ai_will_do  (x22) {
            base  (x1)
            modifier  (x20) {
                NOT  (x3) {
                    126  (x2) {
                        is_controlled_by_ROOT_or_ally  (x1)
                    }
                }
                OR  (x9) {
                    has_war_with  (x5)
                    original_tag  (x2)
                }
                add  (x1)
                factor  (x2)
                has_war  (x1)
                is_historical_focus_on  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x8) {
            107  (x1)
            109  (x1)
            124  (x1)
            163  (x1)
            201  (x1)
            280  (x1)
            285  (x1)
            287  (x1)
        }
    }
    japanese_home_islands  (x36) {
        ai_will_do  (x24) {
            base  (x1)
            modifier  (x22) {
                OR  (x3) {
                    has_war_with  (x1)
                    original_tag  (x1)
                }
                add  (x3)
                any_enemy_country  (x2) {
                    controls_state  (x1)
                }
                controls_state  (x2)
                factor  (x1)
                has_navy_size  (x4) {
                    size  (x2)
                }
                has_war  (x1)
                has_war_with  (x1)
                original_tag  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x10) {
            154  (x1)
            177  (x1)
            299  (x1)
            300  (x1)
            76  (x1)
            78  (x1)
            79  (x1)
            87  (x1)
            90  (x1)
            94  (x1)
        }
    }
    middle_east  (x36) {
        ai_will_do  (x23) {
            base  (x1)
            modifier  (x21) {
                add  (x3)
                any_enemy_country  (x3) {
                    capital_scope  (x2) {
                        is_on_continent  (x1)
                    }
                }
                capital_scope  (x2) {
                    is_on_continent  (x1)
                }
                factor  (x1)
                has_war  (x1)
                owns_any_state_of  (x7) {
                    291  (x1)
                    292  (x1)
                    293  (x1)
                    294  (x1)
                    454  (x1)
                    554  (x1)
                }
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x11) {
            116  (x1)
            129  (x1)
            196  (x1)
            232  (x1)
            236  (x1)
            237  (x1)
            238  (x1)
            239  (x1)
            240  (x1)
            28  (x1)
            298  (x1)
        }
    }
    north_africa  (x33) {
        ai_will_do  (x22) {
            base  (x1)
            modifier  (x20) {
                add  (x2)
                capital_scope  (x2) {
                    is_on_continent  (x1)
                }
                factor  (x2)
                has_war  (x1)
                is_historical_focus_on  (x1)
                owns_any_state_of  (x7) {
                    447  (x1)
                    448  (x1)
                    458  (x1)
                    459  (x1)
                    461  (x1)
                    907  (x1)
                }
                tag  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x9) {
            100  (x1)
            126  (x1)
            128  (x1)
            182  (x1)
            225  (x1)
            29  (x1)
            48  (x1)
            68  (x1)
            69  (x1)
        }
    }
    north_africa_uk  (x35) {
        ai_will_do  (x22) {
            base  (x1)
            modifier  (x20) {
                add  (x1)
                date  (x1)
                factor  (x3)
                has_war  (x1)
                is_historical_focus_on  (x1)
                original_tag  (x1)
                owns_any_state_of  (x7) {
                    447  (x1)
                    448  (x1)
                    458  (x1)
                    459  (x1)
                    461  (x1)
                    907  (x1)
                }
                tag  (x1)
            }
        }
        cancel  (x1)
        preferred_countries  (x3) {
            AST  (x1)
            SAF  (x1)
        }
        regions  (x9) {
            100  (x1)
            126  (x1)
            128  (x1)
            182  (x1)
            225  (x1)
            29  (x1)
            48  (x1)
            68  (x1)
            69  (x1)
        }
    }
    north_sea_region  (x31) {
        ai_will_do  (x16) {
            base  (x1)
            modifier  (x14) {
                OR  (x9) {
                    has_war_with  (x4)
                    original_tag  (x4)
                }
                add  (x1)
                factor  (x1)
                has_war  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x13) {
            10  (x1)
            11  (x1)
            16  (x1)
            161  (x1)
            173  (x1)
            174  (x1)
            191  (x1)
            2  (x1)
            275  (x1)
            3  (x1)
            4  (x1)
            44  (x1)
            45  (x1)
        }
    }
    northern_india  (x30) {
        ai_will_do  (x19) {
            base  (x1)
            modifier  (x17) {
                OR  (x12) {
                    any_enemy_country  (x6) {
                        OR  (x5) {
                            controls_state  (x4)
                        }
                    }
                    controls_state  (x5)
                }
                add  (x1)
                factor  (x1)
                has_war  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x9) {
            104  (x1)
            153  (x1)
            162  (x1)
            190  (x1)
            251  (x1)
            289  (x1)
            291  (x1)
            296  (x1)
            297  (x1)
        }
    }
    persia  (x27) {
        ai_will_do  (x14) {
            base  (x1)
            modifier  (x12) {
                OR  (x3) {
                    has_war_with  (x1)
                    original_tag  (x1)
                }
                add  (x2)
                capital_scope  (x2) {
                    is_on_continent  (x1)
                }
                factor  (x1)
                has_war  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x11) {
            116  (x1)
            134  (x1)
            203  (x1)
            232  (x1)
            239  (x1)
            241  (x1)
            28  (x1)
            289  (x1)
            291  (x1)
            297  (x1)
            298  (x1)
        }
    }
    scandinavia  (x32) {
        ai_will_do  (x18) {
            base  (x1)
            modifier  (x16) {
                OR  (x7) {
                    has_war_with  (x3)
                    original_tag  (x3)
                }
                add  (x2)
                capital_scope  (x2) {
                    is_on_continent  (x1)
                }
                factor  (x1)
                has_war  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x12) {
            10  (x1)
            11  (x1)
            173  (x1)
            191  (x1)
            192  (x1)
            206  (x1)
            275  (x1)
            276  (x1)
            277  (x1)
            278  (x1)
            279  (x1)
            9  (x1)
        }
    }
    south_africa  (x25) {
        ai_will_do  (x16) {
            base  (x1)
            modifier  (x14) {
                add  (x2)
                capital_scope  (x2) {
                    is_on_continent  (x1)
                }
                factor  (x1)
                has_war  (x1)
                owns_any_state_of  (x5) {
                    274  (x1)
                    295  (x1)
                    298  (x1)
                    779  (x1)
                }
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x7) {
            103  (x1)
            139  (x1)
            185  (x1)
            215  (x1)
            223  (x1)
            224  (x1)
            65  (x1)
        }
    }
    south_east_asia  (x33) {
        ai_will_do  (x20) {
            base  (x1)
            modifier  (x18) {
                OR  (x13) {
                    any_enemy_country  (x7) {
                        OR  (x6) {
                            controls_state  (x5)
                        }
                    }
                    controls_state  (x5)
                }
                add  (x1)
                factor  (x1)
                has_war  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x11) {
            101  (x1)
            142  (x1)
            187  (x1)
            188  (x1)
            228  (x1)
            229  (x1)
            292  (x1)
            293  (x1)
            294  (x1)
            72  (x1)
            73  (x1)
        }
    }
    south_pacific  (x36) {
        ai_will_do  (x23) {
            base  (x1)
            modifier  (x21) {
                OR  (x10) {
                    capital_scope  (x5) {
                        is_on_continent  (x4)
                    }
                    has_war_with  (x1)
                    is_in_faction_with  (x1)
                    original_tag  (x1)
                }
                add  (x2)
                factor  (x1)
                has_navy_size  (x4) {
                    size  (x2)
                }
                has_war  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x11) {
            159  (x1)
            167  (x1)
            194  (x1)
            75  (x1)
            80  (x1)
            81  (x1)
            83  (x1)
            84  (x1)
            86  (x1)
            93  (x1)
            94  (x1)
        }
    }
    south_south_america  (x31) {
        ai_will_do  (x21) {
            base  (x1)
            modifier  (x19) {
                NOT  (x3) {
                    126  (x2) {
                        is_controlled_by_ROOT_or_ally  (x1)
                    }
                }
                OR  (x8) {
                    has_war_with  (x4)
                    original_tag  (x2)
                }
                add  (x1)
                factor  (x2)
                has_war  (x1)
                is_historical_focus_on  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x8) {
            108  (x1)
            281  (x1)
            282  (x1)
            283  (x1)
            284  (x1)
            35  (x1)
            63  (x1)
            64  (x1)
        }
    }
    southern_europe  (x29) {
        ai_will_do  (x18) {
            base  (x1)
            modifier  (x16) {
                OR  (x7) {
                    has_war_with  (x3)
                    original_tag  (x3)
                }
                add  (x2)
                capital_scope  (x2) {
                    is_on_continent  (x1)
                }
                factor  (x1)
                has_war  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x9) {
            168  (x1)
            169  (x1)
            202  (x1)
            21  (x1)
            23  (x1)
            24  (x1)
            25  (x1)
            29  (x1)
            68  (x1)
        }
    }
    us_east_coast  (x44) {
        ai_will_do  (x32) {
            base  (x1)
            modifier  (x30) {
                123  (x2) {
                    is_controlled_by_ROOT_or_ally  (x1)
                }
                126  (x2) {
                    is_controlled_by_ROOT_or_ally  (x1)
                }
                14  (x2) {
                    is_controlled_by_ROOT_or_ally  (x1)
                }
                OR  (x15) {
                    AND  (x13) {
                        OR  (x9) {
                            capital_scope  (x8) {
                                is_on_continent  (x4)
                            }
                        }
                        has_navy_size  (x2) {
                            size  (x1)
                        }
                        has_war_with  (x1)
                    }
                    original_tag  (x1)
                }
                add  (x2)
                factor  (x1)
                has_war  (x1)
                has_war_with  (x1)
                original_tag  (x1)
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x10) {
            117  (x1)
            119  (x1)
            170  (x1)
            197  (x1)
            198  (x1)
            211  (x1)
            213  (x1)
            214  (x1)
            54  (x1)
            55  (x1)
        }
    }
    us_west_coast  (x29) {
        ai_will_do  (x14) {
            base  (x1)
            modifier  (x12) {
                add  (x2)
                any_enemy_country  (x2) {
                    controls_state  (x1)
                }
                controls_state  (x1)
                factor  (x1)
                has_war  (x1)
                has_war_with  (x1)
                original_tag  (x1)
            }
        }
        cancel  (x4) {
            AND  (x3) {
                controls_state  (x1)
                original_tag  (x1)
            }
        }
        regions  (x11) {
            105  (x1)
            114  (x1)
            115  (x1)
            118  (x1)
            171  (x1)
            176  (x1)
            218  (x1)
            235  (x1)
            33  (x1)
            88  (x1)
            89  (x1)
        }
    }
    west_africa  (x26) {
        ai_will_do  (x16) {
            base  (x1)
            modifier  (x14) {
                add  (x2)
                capital_scope  (x2) {
                    is_on_continent  (x1)
                }
                factor  (x1)
                has_war  (x1)
                owns_any_state_of  (x5) {
                    274  (x1)
                    295  (x1)
                    298  (x1)
                    779  (x1)
                }
            }
        }
        cancel  (x2) {
            has_war  (x1)
        }
        regions  (x8) {
            140  (x1)
            183  (x1)
            184  (x1)
            226  (x1)
            271  (x1)
            272  (x1)
            61  (x1)
            62  (x1)
        }
    }
    western_europe  (x56) {
        ai_will_do  (x33) {
            base  (x1)
            modifier  (x31) {
                219  (x2) {
                    is_controlled_by_ROOT_or_ally  (x1)
                }
                FRA  (x3) {
                    has_capitulated  (x1)
                    is_in_faction_with  (x1)
                }
                OR  (x5) {
                    has_war_with  (x4)
                }
                add  (x2)
                capital_scope  (x2) {
                    is_on_continent  (x1)
                }
                factor  (x4)
                has_war  (x1)
                has_war_with  (x1)
                is_historical_focus_on  (x1)
                is_in_faction_with  (x1)
                original_tag  (x3)
            }
        }
        cancel  (x12) {
            OR  (x11) {
                AND  (x9) {
                    219  (x2) {
                        is_controlled_by_ROOT_or_ally  (x1)
                    }
                    FRA  (x3) {
                        has_capitulated  (x1)
                        is_in_faction_with  (x1)
                    }
                    has_war_with  (x1)
                    original_tag  (x1)
                }
                has_war  (x1)
            }
        }
        regions  (x11) {
            1  (x1)
            18  (x1)
            19  (x1)
            20  (x1)
            208  (x1)
            21  (x1)
            275  (x1)
            42  (x1)
            5  (x1)
            6  (x1)
            7  (x1)
        }
    }
}
```


## AI 科研权重编辑器（ai_focuses）

> 说明：research 键值表已覆盖；其余字段缺失

扫描文件：6

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

总缺失条数：**331**

##### common/ai_focuses

```text
common/ai_focuses  (x331) {
    ai_focus_aggressive  (x4) {
        research  (x4) {
            armor  (x1)
            motorized_equipment  (x1)
            offensive  (x1)
            synth_resources  (x1)
        }
    }
    ai_focus_aggressive_ENG  (x4) {
        research  (x4) {
            armor  (x1)
            motorized_equipment  (x1)
            offensive  (x1)
            synth_resources  (x1)
        }
    }
    ai_focus_aggressive_FRA  (x4) {
        research  (x4) {
            armor  (x1)
            motorized_equipment  (x1)
            offensive  (x1)
            synth_resources  (x1)
        }
    }
    ai_focus_aggressive_GER  (x4) {
        research  (x4) {
            armor  (x1)
            motorized_equipment  (x1)
            offensive  (x1)
            synth_resources  (x1)
        }
    }
    ai_focus_aggressive_ITA  (x4) {
        research  (x4) {
            armor  (x1)
            motorized_equipment  (x1)
            offensive  (x1)
            synth_resources  (x1)
        }
    }
    ai_focus_aggressive_JAP  (x4) {
        research  (x4) {
            armor  (x1)
            motorized_equipment  (x1)
            offensive  (x1)
            synth_resources  (x1)
        }
    }
    ai_focus_aviation  (x10) {
        research  (x10) {
            air_doctrine  (x1)
            air_equipment  (x1)
            cas_bomber  (x1)
            heavy_air  (x1)
            jet_technology  (x1)
            light_air  (x1)
            light_fighter  (x1)
            medium_air  (x1)
            para_tech  (x1)
            tactical_bomber  (x1)
        }
    }
    ai_focus_aviation_ENG  (x10) {
        research  (x10) {
            air_doctrine  (x1)
            air_equipment  (x1)
            cas_bomber  (x1)
            heavy_air  (x1)
            jet_technology  (x1)
            light_air  (x1)
            light_fighter  (x1)
            medium_air  (x1)
            para_tech  (x1)
            tactical_bomber  (x1)
        }
    }
    ai_focus_aviation_FRA  (x10) {
        research  (x10) {
            air_doctrine  (x1)
            air_equipment  (x1)
            cas_bomber  (x1)
            heavy_air  (x1)
            jet_technology  (x1)
            light_air  (x1)
            light_fighter  (x1)
            medium_air  (x1)
            para_tech  (x1)
            tactical_bomber  (x1)
        }
    }
    ai_focus_aviation_GER  (x10) {
        research  (x10) {
            air_doctrine  (x1)
            air_equipment  (x1)
            cas_bomber  (x1)
            heavy_air  (x1)
            jet_technology  (x1)
            light_air  (x1)
            light_fighter  (x1)
            medium_air  (x1)
            para_tech  (x1)
            tactical_bomber  (x1)
        }
    }
    ai_focus_aviation_ITA  (x10) {
        research  (x10) {
            air_doctrine  (x1)
            air_equipment  (x1)
            cas_bomber  (x1)
            heavy_air  (x1)
            jet_technology  (x1)
            light_air  (x1)
            light_fighter  (x1)
            medium_air  (x1)
            para_tech  (x1)
            tactical_bomber  (x1)
        }
    }
    ai_focus_aviation_JAP  (x10) {
        research  (x10) {
            air_doctrine  (x1)
            air_equipment  (x1)
            cas_bomber  (x1)
            heavy_air  (x1)
            jet_technology  (x1)
            light_air  (x1)
            light_fighter  (x1)
            medium_air  (x1)
            para_tech  (x1)
            tactical_bomber  (x1)
        }
    }
    ai_focus_defense  (x4) {
        research  (x4) {
            artillery  (x1)
            construction_tech  (x1)
            defensive  (x1)
            radar_tech  (x1)
        }
    }
    ai_focus_defense_ENG  (x4) {
        research  (x4) {
            artillery  (x1)
            construction_tech  (x1)
            defensive  (x1)
            radar_tech  (x1)
        }
    }
    ai_focus_defense_FRA  (x4) {
        research  (x4) {
            artillery  (x1)
            construction_tech  (x1)
            defensive  (x1)
            radar_tech  (x1)
        }
    }
    ai_focus_defense_GER  (x4) {
        research  (x4) {
            artillery  (x1)
            construction_tech  (x1)
            defensive  (x1)
            radar_tech  (x1)
        }
    }
    ai_focus_defense_ITA  (x4) {
        research  (x4) {
            artillery  (x1)
            construction_tech  (x1)
            defensive  (x1)
            radar_tech  (x1)
        }
    }
    ai_focus_defense_JAP  (x4) {
        research  (x4) {
            artillery  (x1)
            construction_tech  (x1)
            defensive  (x1)
            radar_tech  (x1)
        }
    }
    ai_focus_military_advancements  (x11) {
        research  (x11) {
            armor  (x1)
            decryption_tech  (x1)
            encryption_tech  (x1)
            jet_technology  (x1)
            land_doctrine  (x1)
            motorized_equipment  (x1)
            night_vision  (x1)
            nuclear  (x1)
            radar_tech  (x1)
            rocketry  (x1)
            synth_resources  (x1)
        }
    }
    ai_focus_military_advancements_ENG  (x12) {
        research  (x12) {
            armor  (x1)
            decryption_tech  (x1)
            encryption_tech  (x1)
            jet_technology  (x1)
            land_doctrine  (x1)
            motorized_equipment  (x1)
            night_vision  (x1)
            nuclear  (x1)
            radar_tech  (x1)
            rocketry  (x1)
            synth_resources  (x1)
            train_tech  (x1)
        }
    }
    ai_focus_military_advancements_FRA  (x12) {
        research  (x12) {
            armor  (x1)
            decryption_tech  (x1)
            encryption_tech  (x1)
            jet_technology  (x1)
            land_doctrine  (x1)
            motorized_equipment  (x1)
            night_vision  (x1)
            nuclear  (x1)
            radar_tech  (x1)
            rocketry  (x1)
            synth_resources  (x1)
            train_tech  (x1)
        }
    }
    ai_focus_military_advancements_GER  (x12) {
        research  (x12) {
            armor  (x1)
            decryption_tech  (x1)
            encryption_tech  (x1)
            jet_technology  (x1)
            land_doctrine  (x1)
            motorized_equipment  (x1)
            night_vision  (x1)
            nuclear  (x1)
            radar_tech  (x1)
            rocketry  (x1)
            synth_resources  (x1)
            train_tech  (x1)
        }
    }
    ai_focus_military_advancements_ITA  (x12) {
        research  (x12) {
            armor  (x1)
            decryption_tech  (x1)
            encryption_tech  (x1)
            jet_technology  (x1)
            land_doctrine  (x1)
            motorized_equipment  (x1)
            night_vision  (x1)
            nuclear  (x1)
            radar_tech  (x1)
            rocketry  (x1)
            synth_resources  (x1)
            train_tech  (x1)
        }
    }
    ai_focus_military_advancements_JAP  (x12) {
        research  (x12) {
            armor  (x1)
            decryption_tech  (x1)
            encryption_tech  (x1)
            jet_technology  (x1)
            land_doctrine  (x1)
            motorized_equipment  (x1)
            night_vision  (x1)
            nuclear  (x1)
            radar_tech  (x1)
            rocketry  (x1)
            synth_resources  (x1)
            train_tech  (x1)
        }
    }
    ai_focus_military_equipment  (x4) {
        research  (x4) {
            artillery  (x1)
            infantry_tech  (x1)
            infantry_weapons  (x1)
            support_tech  (x1)
        }
    }
    ai_focus_military_equipment_ENG  (x4) {
        research  (x4) {
            artillery  (x1)
            infantry_tech  (x1)
            infantry_weapons  (x1)
            support_tech  (x1)
        }
    }
    ai_focus_military_equipment_FRA  (x4) {
        research  (x4) {
            artillery  (x1)
            infantry_tech  (x1)
            infantry_weapons  (x1)
            support_tech  (x1)
        }
    }
    ai_focus_military_equipment_GER  (x4) {
        research  (x4) {
            artillery  (x1)
            infantry_tech  (x1)
            infantry_weapons  (x1)
            support_tech  (x1)
        }
    }
    ai_focus_military_equipment_ITA  (x4) {
        research  (x4) {
            artillery  (x1)
            infantry_tech  (x1)
            infantry_weapons  (x1)
            support_tech  (x1)
        }
    }
    ai_focus_military_equipment_JAP  (x4) {
        research  (x4) {
            artillery  (x1)
            infantry_tech  (x1)
            infantry_weapons  (x1)
            support_tech  (x1)
        }
    }
    ai_focus_naval  (x12) {
        research  (x12) {
            bb_tech  (x1)
            bc_tech  (x1)
            ca_tech  (x1)
            cl_tech  (x1)
            cv_tech  (x1)
            dd_tech  (x1)
            marine_tech  (x1)
            naval_doctrine  (x1)
            naval_equipment  (x1)
            shbb_tech  (x1)
            ss_tech  (x1)
            tp_tech  (x1)
        }
    }
    ai_focus_naval_ENG  (x12) {
        research  (x12) {
            asw_tech  (x1)
            bb_tech  (x1)
            bc_tech  (x1)
            ca_tech  (x1)
            cv_tech  (x1)
            dd_tech  (x1)
            marine_tech  (x1)
            naval_doctrine  (x1)
            naval_equipment  (x1)
            shbb_tech  (x1)
            ss_tech  (x1)
            tp_tech  (x1)
        }
    }
    ai_focus_naval_FRA  (x11) {
        research  (x11) {
            bb_tech  (x1)
            bc_tech  (x1)
            ca_tech  (x1)
            cv_tech  (x1)
            dd_tech  (x1)
            marine_tech  (x1)
            naval_doctrine  (x1)
            naval_equipment  (x1)
            shbb_tech  (x1)
            ss_tech  (x1)
            tp_tech  (x1)
        }
    }
    ai_focus_naval_GER  (x11) {
        research  (x11) {
            bb_tech  (x1)
            bc_tech  (x1)
            ca_tech  (x1)
            cv_tech  (x1)
            dd_tech  (x1)
            marine_tech  (x1)
            naval_doctrine  (x1)
            naval_equipment  (x1)
            shbb_tech  (x1)
            ss_tech  (x1)
            tp_tech  (x1)
        }
    }
    ai_focus_naval_ITA  (x11) {
        research  (x11) {
            bb_tech  (x1)
            bc_tech  (x1)
            ca_tech  (x1)
            cv_tech  (x1)
            dd_tech  (x1)
            marine_tech  (x1)
            naval_doctrine  (x1)
            naval_equipment  (x1)
            shbb_tech  (x1)
            ss_tech  (x1)
            tp_tech  (x1)
        }
    }
    ai_focus_naval_JAP  (x11) {
        research  (x11) {
            bb_tech  (x1)
            bc_tech  (x1)
            ca_tech  (x1)
            cv_tech  (x1)
            dd_tech  (x1)
            marine_tech  (x1)
            naval_doctrine  (x1)
            naval_equipment  (x1)
            shbb_tech  (x1)
            ss_tech  (x1)
            tp_tech  (x1)
        }
    }
    ai_focus_naval_air  (x2) {
        research  (x2) {
            naval_air  (x1)
            naval_bomber  (x1)
        }
    }
    ai_focus_naval_air_ENG  (x2) {
        research  (x2) {
            naval_air  (x1)
            naval_bomber  (x1)
        }
    }
    ai_focus_naval_air_FRA  (x2) {
        research  (x2) {
            naval_air  (x1)
            naval_bomber  (x1)
        }
    }
    ai_focus_naval_air_GER  (x2) {
        research  (x2) {
            naval_air  (x1)
            naval_bomber  (x1)
        }
    }
    ai_focus_naval_air_ITA  (x2) {
        research  (x2) {
            naval_air  (x1)
            naval_bomber  (x1)
        }
    }
    ai_focus_naval_air_JAP  (x2) {
        research  (x2) {
            naval_air  (x1)
            naval_bomber  (x1)
        }
    }
    ai_focus_peaceful  (x4) {
        research  (x4) {
            computing_tech  (x1)
            construction_tech  (x1)
            electronics  (x1)
            industry  (x1)
        }
    }
    ai_focus_peaceful_ENG  (x4) {
        research  (x4) {
            computing_tech  (x1)
            construction_tech  (x1)
            electronics  (x1)
            industry  (x1)
        }
    }
    ai_focus_peaceful_FRA  (x4) {
        research  (x4) {
            computing_tech  (x1)
            construction_tech  (x1)
            electronics  (x1)
            industry  (x1)
        }
    }
    ai_focus_peaceful_GER  (x4) {
        research  (x4) {
            computing_tech  (x1)
            construction_tech  (x1)
            electronics  (x1)
            industry  (x1)
        }
    }
    ai_focus_peaceful_ITA  (x4) {
        research  (x4) {
            computing_tech  (x1)
            construction_tech  (x1)
            electronics  (x1)
            industry  (x1)
        }
    }
    ai_focus_peaceful_JAP  (x4) {
        research  (x4) {
            computing_tech  (x1)
            construction_tech  (x1)
            electronics  (x1)
            industry  (x1)
        }
    }
    ai_focus_war_production  (x4) {
        research  (x4) {
            computing_tech  (x1)
            construction_tech  (x1)
            electronics  (x1)
            industry  (x1)
        }
    }
    ai_focus_war_production_ENG  (x4) {
        research  (x4) {
            computing_tech  (x1)
            construction_tech  (x1)
            electronics  (x1)
            industry  (x1)
        }
    }
    ai_focus_war_production_FRA  (x4) {
        research  (x4) {
            computing_tech  (x1)
            construction_tech  (x1)
            electronics  (x1)
            industry  (x1)
        }
    }
    ai_focus_war_production_GER  (x4) {
        research  (x4) {
            computing_tech  (x1)
            construction_tech  (x1)
            electronics  (x1)
            industry  (x1)
        }
    }
    ai_focus_war_production_ITA  (x4) {
        research  (x4) {
            computing_tech  (x1)
            construction_tech  (x1)
            electronics  (x1)
            industry  (x1)
        }
    }
    ai_focus_war_production_JAP  (x4) {
        research  (x4) {
            computing_tech  (x1)
            construction_tech  (x1)
            electronics  (x1)
            industry  (x1)
        }
    }
}
```


## AI 海军编辑器（ai_navy）

> 说明：复杂块走树编辑器/raw 兜底

扫描文件：10

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

总缺失条数：**67**

##### common/ai_navy/fleet

```text
common/ai_navy/fleet  (x67) {
    ENG_escort_fleet_3  (x2) {
        optional_taskforces  (x1) {
            ENG_ConvoyEscort_1  (x1)
        }
        required_taskforces  (x1) {
            ENG_ConvoyEscort_1  (x1)
        }
    }
    ENG_home_fleet  (x4) {
        optional_taskforces  (x2) {
            ENG_PatrolReconForce_1  (x1)
            ENG_StrikeForce_1  (x1)
        }
        required_taskforces  (x2) {
            ENG_PatrolReconForce_1  (x1)
            ENG_StrikeForce_1  (x1)
        }
    }
    ENG_mediterranean_fleet  (x5) {
        optional_taskforces  (x2) {
            ENG_PatrolDominanceForce_BC_1  (x1)
            ENG_PatrolReconForce_1  (x1)
        }
        required_taskforces  (x3) {
            ENG_NavalInvasionSupport_1  (x1)
            ENG_PatrolReconForce_1  (x1)
            ENG_StrikeForce_1  (x1)
        }
    }
    ENG_raiding_fleet_2  (x2) {
        optional_taskforces  (x1) {
            ENG_ConvoyRaiding_1  (x1)
        }
        required_taskforces  (x1) {
            ENG_ConvoyRaiding_1  (x1)
        }
    }
    FRA_dominance_fleet_1  (x6) {
        optional_taskforces  (x3) {
            FRA_PatrolDominanceForce_1  (x1)
            FRA_PatrolReconForce_1  (x1)
            FRA_StrikeForce_1  (x1)
        }
        required_taskforces  (x3) {
            FRA_PatrolDominanceForce_1  (x1)
            FRA_PatrolReconForce_1  (x1)
            FRA_StrikeForce_1  (x1)
        }
    }
    FRA_escort_fleet_3  (x2) {
        optional_taskforces  (x1) {
            FRA_ConvoyEscort_1  (x1)
        }
        required_taskforces  (x1) {
            FRA_ConvoyEscort_1  (x1)
        }
    }
    FRA_minelaying_fleet_4  (x1) {
        optional_taskforces  (x1) {
            FRA_MineLaying_1  (x1)
        }
    }
    FRA_raiding_fleet_2  (x2) {
        optional_taskforces  (x1) {
            FRA_ConvoyRaiding_1  (x1)
        }
        required_taskforces  (x1) {
            FRA_ConvoyRaiding_1  (x1)
        }
    }
    GER_dominance_fleet_1  (x6) {
        optional_taskforces  (x3) {
            GER_PatrolDominanceForce_1  (x1)
            GER_PatrolReconForce_1  (x1)
            GER_StrikeForce_1  (x1)
        }
        required_taskforces  (x3) {
            GER_PatrolDominanceForce_1  (x1)
            GER_PatrolReconForce_1  (x1)
            GER_StrikeForce_1  (x1)
        }
    }
    GER_escort_fleet_3  (x2) {
        optional_taskforces  (x1) {
            GER_ConvoyEscort_1  (x1)
        }
        required_taskforces  (x1) {
            GER_ConvoyEscort_1  (x1)
        }
    }
    GER_minelaying_fleet_4  (x1) {
        optional_taskforces  (x1) {
            GER_MineLaying_1  (x1)
        }
    }
    GER_raiding_fleet_2  (x2) {
        optional_taskforces  (x1) {
            GER_ConvoyRaiding_1  (x1)
        }
        required_taskforces  (x1) {
            GER_ConvoyRaiding_1  (x1)
        }
    }
    ITA_dominance_fleet_1  (x6) {
        optional_taskforces  (x3) {
            ITA_PatrolDominanceForce_1  (x1)
            ITA_PatrolReconForce_1  (x1)
            ITA_StrikeForceCarrier_1  (x1)
        }
        required_taskforces  (x3) {
            ITA_PatrolDominanceForce_1  (x1)
            ITA_PatrolReconForce_1  (x1)
            ITA_StrikeForce_1  (x1)
        }
    }
    ITA_escort_fleet_3  (x1) {
        optional_taskforces  (x1) {
            ITA_ConvoyEscort_1  (x1)
        }
    }
    ITA_minelaying_fleet_4  (x1) {
        optional_taskforces  (x1) {
            ITA_MineLaying_1  (x1)
        }
    }
    ITA_raiding_fleet_2  (x2) {
        optional_taskforces  (x1) {
            ITA_ConvoyRaiding_1  (x1)
        }
        required_taskforces  (x1) {
            ITA_ConvoyRaiding_1  (x1)
        }
    }
    JAP_dominance_fleet_1  (x6) {
        optional_taskforces  (x2) {
            JAP_PatrolDominanceForce_1  (x1)
            JAP_StrikeForce_1  (x1)
        }
        required_taskforces  (x4) {
            JAP_KidoButai_1  (x1)
            JAP_NavalInvasionSupport_1  (x1)
            JAP_PatrolDominanceForce_1  (x1)
            JAP_PatrolReconForce_1  (x1)
        }
    }
    JAP_escort_fleet_3  (x2) {
        optional_taskforces  (x1) {
            JAP_ConvoyEscort_1  (x1)
        }
        required_taskforces  (x1) {
            JAP_ConvoyEscort_1  (x1)
        }
    }
    JAP_minelaying_fleet_4  (x1) {
        optional_taskforces  (x1) {
            JAP_MineLaying_1  (x1)
        }
    }
    JAP_raiding_fleet_2  (x2) {
        optional_taskforces  (x1) {
            JAP_ConvoyRaiding_1  (x1)
        }
        required_taskforces  (x1) {
            JAP_ConvoyRaiding_1  (x1)
        }
    }
    generic_dominance_fleet_1  (x7) {
        optional_taskforces  (x3) {
            PatrolDominanceForce_CA_1  (x1)
            PatrolReconForce_1  (x1)
            StrikeForce_1  (x1)
        }
        required_taskforces  (x4) {
            PatrolDominanceForce_BC_1  (x1)
            PatrolDominanceForce_CA_1  (x1)
            PatrolReconForce_1  (x1)
            StrikeForce_1  (x1)
        }
    }
    generic_escort_fleet_3  (x2) {
        optional_taskforces  (x1) {
            ConvoyEscort_1  (x1)
        }
        required_taskforces  (x1) {
            ConvoyEscort_1  (x1)
        }
    }
    generic_raiding_fleet_2  (x2) {
        optional_taskforces  (x1) {
            ConvoyRaiding_1  (x1)
        }
        required_taskforces  (x1) {
            ConvoyRaiding_1  (x1)
        }
    }
}
```


## AI 战略倾向编辑器（ai_strategy）

> 说明：allowed/enable/abort 实际为脚本块，UI 可按需扩展

扫描文件：10

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

总缺失条数：**715**

##### common/ai_strategy

```text
common/ai_strategy  (x715) {
    APA_biden_not_a_friend  (x4) {
        abort  (x2) {
            USB  (x2) {
                exists  (x1)
            }
        }
        allowed  (x1) {
            tag  (x1)
        }
        enable  (x1) {
            country_exists  (x1)
        }
    }
    APA_doesnt_care_about_relation  (x4) {
        abort  (x1) {
            has_war  (x1)
        }
        allowed  (x1) {
            tag  (x1)
        }
        enable  (x2) {
            has_war  (x1)
            tag  (x1)
        }
    }
    APA_expand_fast_strategy  (x3) {
        allowed  (x1) {
            tag  (x1)
        }
        enable  (x2) {
            has_country_flag  (x1)
            has_global_flag  (x1)
        }
    }
    APA_maoists_are_thugs  (x4) {
        abort  (x2) {
            RGA  (x2) {
                exists  (x1)
            }
        }
        allowed  (x1) {
            tag  (x1)
        }
        enable  (x1) {
            country_exists  (x1)
        }
    }
    APA_unit_production  (x3) {
        abort  (x1) {
            always  (x1)
        }
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x1) {
            always  (x1)
        }
    }
    APA_wants_mils  (x3) {
        allowed  (x1) {
            tag  (x1)
        }
        enable  (x2) {
            date  (x1)
            tag  (x1)
        }
    }
    APA_we_love_china  (x2) {
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x1) {
            has_global_flag  (x1)
        }
    }
    APA_yasss_queen_slay_those_fashists_strategy  (x3) {
        allowed  (x1) {
            tag  (x1)
        }
        enable  (x2) {
            has_country_flag  (x1)
            has_global_flag  (x1)
        }
    }
    APA_you_should_be_prepared_for_war  (x2) {
        allowed  (x1) {
            tag  (x1)
        }
        enable  (x1) {
            has_global_flag  (x1)
        }
    }
    ARG_avoid_china  (x4) {
        abort  (x1) {
            date  (x1)
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x1) {
            is_historical_focus_on  (x1)
        }
    }
    AST_attack_prc  (x3) {
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x2) {
            has_global_flag  (x1)
            original_tag  (x1)
        }
    }
    AST_defend_the_rock_ai_jap  (x8) {
        abort  (x3) {
            OR  (x3) {
                has_global_flag  (x2)
            }
        }
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x4) {
            JAP  (x2) {
                is_ai  (x1)
            }
            is_in_faction_with  (x1)
            original_tag  (x1)
        }
    }
    AST_defend_the_rock_player_jap  (x8) {
        abort  (x3) {
            OR  (x3) {
                has_global_flag  (x2)
            }
        }
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x4) {
            JAP  (x2) {
                is_ai  (x1)
            }
            is_in_faction_with  (x1)
            original_tag  (x1)
        }
    }
    AST_naval_role_ratios  (x3) {
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x1) {
            always  (x1)
        }
    }
    ATW_everyone_hates_us_strategy  (x7) {
        allowed  (x6) {
            OR  (x6) {
                tag  (x5)
            }
        }
        enable  (x1) {
            country_exists  (x1)
        }
    }
    ATW_kill_commies_strategy  (x15) {
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x14) {
            APA  (x13) {
                OR  (x11) {
                    any_controlled_state  (x3) {
                        any_neighbor_state  (x2) {
                            is_controlled_by  (x1)
                        }
                    }
                    any_other_country  (x7) {
                        OR  (x3) {
                            is_in_faction_with  (x1)
                            is_puppet_of  (x1)
                        }
                        any_controlled_state  (x3) {
                            any_neighbor_state  (x2) {
                                is_controlled_by  (x1)
                            }
                        }
                    }
                }
                exists  (x1)
            }
            has_completed_focus  (x1)
        }
    }
    ATW_kill_confederates_strategy  (x15) {
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x14) {
            LOS  (x13) {
                OR  (x11) {
                    any_controlled_state  (x3) {
                        any_neighbor_state  (x2) {
                            is_controlled_by  (x1)
                        }
                    }
                    any_other_country  (x7) {
                        OR  (x3) {
                            is_in_faction_with  (x1)
                            is_puppet_of  (x1)
                        }
                        any_controlled_state  (x3) {
                            any_neighbor_state  (x2) {
                                is_controlled_by  (x1)
                            }
                        }
                    }
                }
                exists  (x1)
            }
            has_completed_focus  (x1)
        }
    }
    ATW_kill_feds_strategy  (x30) {
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x29) {
            OR  (x28) {
                USB  (x12) {
                    OR  (x11) {
                        any_controlled_state  (x3) {
                            any_neighbor_state  (x2) {
                                is_controlled_by  (x1)
                            }
                        }
                        any_other_country  (x7) {
                            OR  (x3) {
                                is_in_faction_with  (x1)
                                is_puppet_of  (x1)
                            }
                            any_controlled_state  (x3) {
                                any_neighbor_state  (x2) {
                                    is_controlled_by  (x1)
                                }
                            }
                        }
                    }
                }
                USC  (x12) {
                    OR  (x11) {
                        any_controlled_state  (x3) {
                            any_neighbor_state  (x2) {
                                is_controlled_by  (x1)
                            }
                        }
                        any_other_country  (x7) {
                            OR  (x3) {
                                is_in_faction_with  (x1)
                                is_puppet_of  (x1)
                            }
                            any_controlled_state  (x3) {
                                any_neighbor_state  (x2) {
                                    is_controlled_by  (x1)
                                }
                            }
                        }
                    }
                }
                country_exists  (x2)
            }
            has_completed_focus  (x1)
        }
    }
    AUS_dont_ally_germany  (x8) {
        abort  (x5) {
            GER  (x5) {
                OR  (x4) {
                    NOT  (x2) {
                        has_government  (x1)
                    }
                    is_in_faction_with  (x1)
                }
            }
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x1) {
            AUS_is_historical_ai  (x1)
        }
    }
    AUS_dont_ally_japan  (x5) {
        abort  (x2) {
            JAP  (x2) {
                is_in_faction_with  (x1)
            }
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x1) {
            AUS_is_historical_ai  (x1)
        }
    }
    AUS_dont_panic_train_divisions  (x12) {
        abort  (x3) {
            has_country_flag  (x3) {
                days  (x1)
                flag  (x1)
            }
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x7) {
            AUS_is_historical_ai  (x1)
            NOT  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
            has_completed_focus  (x1)
        }
    }
    AUS_no_historical_ai_austria_in_the_allies  (x5) {
        abort  (x1) {
            has_government  (x1)
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x2) {
            AUS_is_historical_ai  (x1)
            has_government  (x1)
        }
    }
    AUS_panic_befriend_guarantors_ENG  (x10) {
        abort  (x3) {
            has_completed_focus  (x1)
            has_war_with  (x1)
            is_guaranteed_by  (x1)
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x5) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
    }
    AUS_panic_befriend_guarantors_FRA  (x10) {
        abort  (x3) {
            has_completed_focus  (x1)
            has_war_with  (x1)
            is_guaranteed_by  (x1)
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x5) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
    }
    AUS_panic_befriend_guarantors_ITA  (x11) {
        abort  (x4) {
            OR  (x4) {
                has_completed_focus  (x1)
                has_war_with  (x1)
                is_guaranteed_by  (x1)
            }
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x5) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
    }
    AUS_panic_befriend_guarantors_USA  (x10) {
        abort  (x3) {
            has_completed_focus  (x1)
            has_war_with  (x1)
            is_guaranteed_by  (x1)
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x5) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
    }
    AUS_panic_train_divisions  (x8) {
        abort  (x1) {
            always  (x1)
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x5) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
    }
    BEL_build_a_nuclear_facility_anywhere  (x8) {
        allowed  (x5) {
            any_country_with_original_tag  (x3) {
                is_subject_of  (x1)
                original_tag_to_check  (x1)
            }
            has_tech  (x1)
            original_tag  (x1)
        }
        enable  (x3) {
            has_tech  (x1)
            nuclear_facility  (x1)
            num_of_civilian_factories  (x1)
        }
    }
    BLA_doesnt_care_about_relation  (x3) {
        abort  (x1) {
            has_war  (x1)
        }
        enable  (x2) {
            has_war  (x1)
            tag  (x1)
        }
    }
    BLA_everyone_is_weak  (x2) {
        enable  (x2) {
            has_global_flag  (x1)
            tag  (x1)
        }
    }
    BLA_wants_mils  (x2) {
        enable  (x2) {
            date  (x1)
            tag  (x1)
        }
    }
    BLA_you_should_be_prepared_for_war  (x1) {
        enable  (x1) {
            tag  (x1)
        }
    }
    BRN_doesnt_care_about_relation  (x3) {
        abort  (x1) {
            has_war  (x1)
        }
        enable  (x2) {
            has_war  (x1)
            tag  (x1)
        }
    }
    BRN_everyone_is_weak  (x3) {
        abort  (x1) {
            always  (x1)
        }
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x1) {
            always  (x1)
        }
    }
    BRN_wants_mils  (x2) {
        enable  (x2) {
            date  (x1)
            tag  (x1)
        }
    }
    BRN_you_should_be_prepared_for_war  (x1) {
        enable  (x1) {
            tag  (x1)
        }
    }
    BUL_address_internal_affairs_first  (x8) {
        abort  (x3) {
            OR  (x3) {
                date  (x1)
                has_war  (x1)
            }
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x3) {
            OR  (x3) {
                has_completed_focus  (x2)
            }
        }
    }
    BUL_befriend_ENG  (x33) {
        abort  (x13) {
            OR  (x13) {
                ENG  (x9) {
                    OR  (x8) {
                        has_capitulated  (x1)
                        has_government  (x2)
                        has_opinion  (x3) {
                            target  (x1)
                            value  (x1)
                        }
                        is_subject  (x1)
                    }
                }
                NOT  (x2) {
                    country_exists  (x1)
                }
                has_war_with  (x1)
            }
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x18) {
            ENG  (x6) {
                has_capitulated  (x1)
                has_opinion  (x3) {
                    target  (x1)
                    value  (x1)
                }
                is_subject  (x1)
            }
            OR  (x8) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
                has_government  (x2)
            }
            country_exists  (x1)
            focus_progress  (x3) {
                focus  (x1)
                progress  (x1)
            }
        }
    }
    BUL_befriend_GER  (x28) {
        abort  (x13) {
            OR  (x13) {
                GER  (x9) {
                    OR  (x8) {
                        has_capitulated  (x1)
                        has_government  (x2)
                        has_opinion  (x3) {
                            target  (x1)
                            value  (x1)
                        }
                        is_subject  (x1)
                    }
                }
                NOT  (x2) {
                    country_exists  (x1)
                }
                has_war_with  (x1)
            }
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x13) {
            GER  (x6) {
                has_capitulated  (x1)
                has_opinion  (x3) {
                    target  (x1)
                    value  (x1)
                }
                is_subject  (x1)
            }
            OR  (x3) {
                has_government  (x2)
            }
            country_exists  (x1)
            focus_progress  (x3) {
                focus  (x1)
                progress  (x1)
            }
        }
    }
    BUL_befriend_GRE  (x32) {
        abort  (x15) {
            OR  (x15) {
                GRE  (x11) {
                    OR  (x10) {
                        AND  (x4) {
                            NOT  (x2) {
                                is_in_faction_with  (x1)
                            }
                            is_in_faction  (x1)
                        }
                        has_capitulated  (x1)
                        has_opinion  (x3) {
                            target  (x1)
                            value  (x1)
                        }
                        is_subject  (x1)
                    }
                }
                NOT  (x2) {
                    country_exists  (x1)
                }
                has_war_with  (x1)
            }
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x15) {
            GRE  (x6) {
                has_capitulated  (x1)
                has_opinion  (x3) {
                    target  (x1)
                    value  (x1)
                }
                is_subject  (x1)
            }
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
            country_exists  (x1)
            focus_progress  (x3) {
                focus  (x1)
                progress  (x1)
            }
        }
    }
    BUL_befriend_ITA  (x26) {
        abort  (x13) {
            OR  (x13) {
                ITA  (x9) {
                    OR  (x8) {
                        has_capitulated  (x1)
                        has_government  (x2)
                        has_opinion  (x3) {
                            target  (x1)
                            value  (x1)
                        }
                        is_subject  (x1)
                    }
                }
                NOT  (x2) {
                    country_exists  (x1)
                }
                has_war_with  (x1)
            }
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x11) {
            ITA  (x6) {
                has_capitulated  (x1)
                has_opinion  (x3) {
                    target  (x1)
                    value  (x1)
                }
                is_subject  (x1)
            }
            OR  (x3) {
                has_government  (x2)
            }
            country_exists  (x1)
            has_completed_focus  (x1)
        }
    }
    BUL_befriend_SOV  (x31) {
        abort  (x13) {
            OR  (x13) {
                NOT  (x2) {
                    country_exists  (x1)
                }
                SOV  (x9) {
                    OR  (x8) {
                        NOT  (x2) {
                            has_government  (x1)
                        }
                        has_capitulated  (x1)
                        has_opinion  (x3) {
                            target  (x1)
                            value  (x1)
                        }
                        is_subject  (x1)
                    }
                }
                has_war_with  (x1)
            }
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x16) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
            SOV  (x6) {
                has_capitulated  (x1)
                has_opinion  (x3) {
                    target  (x1)
                    value  (x1)
                }
                is_subject  (x1)
            }
            country_exists  (x1)
            focus_progress  (x3) {
                focus  (x1)
                progress  (x1)
            }
            has_government  (x1)
        }
    }
    BUL_befriend_YUG  (x32) {
        abort  (x15) {
            OR  (x15) {
                NOT  (x2) {
                    country_exists  (x1)
                }
                YUG  (x11) {
                    OR  (x10) {
                        AND  (x4) {
                            NOT  (x2) {
                                is_in_faction_with  (x1)
                            }
                            is_in_faction  (x1)
                        }
                        has_capitulated  (x1)
                        has_opinion  (x3) {
                            target  (x1)
                            value  (x1)
                        }
                        is_subject  (x1)
                    }
                }
                has_war_with  (x1)
            }
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x15) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
            YUG  (x6) {
                has_capitulated  (x1)
                has_opinion  (x3) {
                    target  (x1)
                    value  (x1)
                }
                is_subject  (x1)
            }
            country_exists  (x1)
            focus_progress  (x3) {
                focus  (x1)
                progress  (x1)
            }
        }
    }
    BUL_cajole_the_brits  (x43) {
        abort  (x21) {
            OR  (x21) {
                ENG  (x8) {
                    OR  (x3) {
                        has_capitulated  (x1)
                        is_subject  (x1)
                    }
                    has_opinion  (x3) {
                        target  (x1)
                        value  (x1)
                    }
                }
                NOT  (x2) {
                    country_exists  (x1)
                }
                OR  (x5) {
                    NOT  (x4) {
                        has_idea  (x2)
                    }
                }
                has_country_flag  (x3) {
                    flag  (x1)
                    value  (x1)
                }
                has_political_power  (x1)
                has_war_with  (x1)
            }
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x20) {
            ENG  (x6) {
                has_capitulated  (x1)
                has_opinion  (x3) {
                    target  (x1)
                    value  (x1)
                }
                is_subject  (x1)
            }
            NOT  (x4) {
                has_country_flag  (x3) {
                    flag  (x1)
                    value  (x1)
                }
            }
            OR  (x8) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
                has_idea  (x2)
            }
            country_exists  (x1)
            has_completed_focus  (x1)
        }
    }
    BUL_dont_pressure_bulgarians_yet  (x21) {
        abort  (x9) {
            OR  (x9) {
                BUL  (x5) {
                    OR  (x4) {
                        has_government  (x2)
                        has_war  (x1)
                    }
                }
                NOT  (x2) {
                    is_in_faction_with  (x1)
                }
                date  (x1)
            }
        }
        allowed  (x1) {
            has_dlc  (x1)
        }
        enable  (x11) {
            BUL  (x4) {
                OR  (x3) {
                    has_government  (x2)
                }
            }
            OR  (x5) {
                is_in_faction_with  (x2)
                tag  (x2)
            }
            has_war  (x1)
            is_in_faction_with  (x1)
        }
    }
    BUL_occupying_instead_of_dieing  (x8) {
        abort  (x4) {
            OR  (x4) {
                NOT  (x2) {
                    country_exists  (x1)
                }
                date  (x1)
            }
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x2) {
            country_exists  (x1)
            is_historical_focus_on  (x1)
        }
    }
    BUL_reject_bulgarian_aggressive_ai  (x21) {
        abort  (x8) {
            OR  (x8) {
                BUL  (x6) {
                    OR  (x5) {
                        has_government  (x2)
                        has_war  (x1)
                        is_ai  (x1)
                    }
                }
                date  (x1)
            }
        }
        allowed  (x1) {
            has_dlc  (x1)
        }
        enable  (x12) {
            BUL  (x5) {
                OR  (x3) {
                    has_government  (x2)
                }
                is_ai  (x1)
            }
            OR  (x5) {
                is_in_faction_with  (x2)
                tag  (x2)
            }
            has_war  (x1)
            is_in_faction_with  (x1)
        }
    }
    BUL_we_dont_want_to_fight_sov  (x6) {
        abort  (x3) {
            OR  (x3) {
                date  (x1)
                has_completed_focus  (x1)
            }
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x1) {
            has_completed_focus  (x1)
        }
    }
    CHI_aifc_incompetent_officers  (x7) {
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x6) {
            OR  (x6) {
                NOT  (x4) {
                    has_completed_focus  (x2)
                }
                has_idea  (x1)
            }
        }
    }
    CHI_armored_production  (x3) {
        abort  (x1) {
            ai_wants_divisions  (x1)
        }
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x1) {
            ai_wants_divisions  (x1)
        }
    }
    CHI_bog_them_down_and_war_zones_concentrations  (x6) {
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x5) {
            OR  (x3) {
                has_completed_focus  (x2)
            }
            any_core_state  (x2) {
                has_state_flag  (x1)
            }
        }
    }
    CHI_buffer_in_interior_china  (x6) {
        allowed  (x2) {
            has_dlc  (x1)
            is_literally_china_not_prc  (x1)
        }
        enable  (x4) {
            OR  (x3) {
                is_in_faction_with  (x1)
                original_tag  (x1)
            }
            date  (x1)
        }
    }
    CHI_buffer_in_mainland  (x4) {
        allowed  (x3) {
            NOT  (x2) {
                has_dlc  (x1)
            }
            is_literally_china_not_prc  (x1)
        }
        enable  (x1) {
            date  (x1)
        }
    }
    CHI_buffer_on_northern_borders_and_coast  (x7) {
        allowed  (x2) {
            has_dlc  (x1)
            is_literally_china_not_prc  (x1)
        }
        enable  (x5) {
            OR  (x3) {
                is_in_faction_with  (x1)
                original_tag  (x1)
            }
            date  (x1)
            has_war  (x1)
        }
    }
    CHI_build_factories_inland  (x6) {
        abort  (x3) {
            NOT  (x2) {
                has_war_with  (x1)
            }
            date  (x1)
        }
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x1) {
            date  (x1)
        }
    }
    CHI_dont_defend_HBC  (x11) {
        allowed  (x2) {
            has_dlc  (x1)
            is_literally_china  (x1)
        }
        enable  (x9) {
            CHI  (x3) {
                NOT  (x2) {
                    has_completed_focus  (x1)
                }
            }
            OR  (x5) {
                1039  (x2) {
                    is_controlled_by  (x1)
                }
                608  (x2) {
                    is_controlled_by  (x1)
                }
            }
            is_in_faction_with  (x1)
        }
    }
    CHI_dont_defend_SND  (x7) {
        allowed  (x2) {
            has_dlc  (x1)
            is_literally_china  (x1)
        }
        enable  (x5) {
            1038  (x2) {
                is_controlled_by  (x1)
            }
            597  (x2) {
                is_controlled_by  (x1)
            }
            is_in_faction_with  (x1)
        }
    }
    CHI_dont_defend_northern_warlords  (x3) {
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x1) {
            num_faction_members  (x1)
        }
    }
    CHI_dont_join_ENG_if_not_democratic  (x6) {
        allowed  (x1) {
            WTT_is_chinese_country  (x1)
        }
        enable  (x5) {
            ENG  (x2) {
                has_government  (x1)
            }
            NOT  (x2) {
                has_government  (x1)
            }
            WTT_is_chinese_country  (x1)
        }
    }
    CHI_dont_join_USA_if_not_democratic  (x6) {
        allowed  (x1) {
            WTT_is_chinese_country  (x1)
        }
        enable  (x5) {
            NOT  (x2) {
                has_government  (x1)
            }
            USA  (x2) {
                has_government  (x1)
            }
            WTT_is_chinese_country  (x1)
        }
    }
    CHI_dont_mess_with_the_soviets  (x4) {
        abort  (x1) {
            has_war_with  (x1)
        }
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x2) {
            NOT  (x2) {
                has_war_with  (x1)
            }
        }
    }
    CHI_dont_upgrade_to_weapons_2_too_early  (x4) {
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x3) {
            has_equipment  (x2) {
                infantry_equipment  (x1)
            }
            is_historical_focus_on  (x1)
        }
    }
    CHI_dont_waste_on_offensive_air_early  (x3) {
        abort  (x1) {
            date  (x1)
        }
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x1) {
            date  (x1)
        }
    }
    CHI_highered_armored_production  (x3) {
        abort  (x1) {
            num_of_military_factories  (x1)
        }
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x1) {
            num_of_military_factories  (x1)
        }
    }
    CHI_hunker_down_now  (x5) {
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x4) {
            date  (x1)
            has_defensive_war  (x1)
            has_war_with  (x1)
            is_historical_focus_on  (x1)
        }
    }
    CHI_hunker_down_now_2  (x5) {
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x4) {
            date  (x1)
            has_defensive_war  (x1)
            has_war_with  (x1)
            is_historical_focus_on  (x1)
        }
    }
    CHI_prio_military_even_at_peace  (x2) {
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x1) {
            always  (x1)
        }
    }
    CHI_prioritize_coast_garrisons  (x13) {
        allowed  (x1) {
            is_literally_china  (x1)
        }
        enable  (x12) {
            CHI  (x3) {
                NOT  (x2) {
                    has_completed_focus  (x1)
                }
            }
            OR  (x5) {
                has_war_with  (x4)
            }
            any_core_state  (x3) {
                is_coastal  (x1)
                is_fully_controlled_by  (x1)
            }
            date  (x1)
        }
    }
    CHI_prioritize_coast_garrisons_low_effort  (x11) {
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x10) {
            OR  (x5) {
                has_war_with  (x4)
            }
            any_core_state  (x3) {
                is_coastal  (x1)
                is_fully_controlled_by  (x1)
            }
            date  (x1)
            has_completed_focus  (x1)
        }
    }
    CHI_some_safer_places_to_build  (x5) {
        abort  (x1) {
            date  (x1)
        }
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x3) {
            OR  (x3) {
                controls_state  (x2)
            }
        }
    }
    CHI_some_safer_places_to_build_2  (x3) {
        abort  (x1) {
            date  (x1)
        }
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x1) {
            always  (x1)
        }
    }
    CHI_southern_warlords_should_prioritize_southern_borders  (x7) {
        allowed  (x5) {
            OR  (x4) {
                original_tag  (x3)
            }
            has_dlc  (x1)
        }
        enable  (x2) {
            date  (x1)
            is_in_faction_with  (x1)
        }
    }
    CHI_stop_disbanding_your_army_during_war  (x3) {
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x1) {
            has_war  (x1)
        }
    }
    CHI_stop_disbanding_your_army_pre_war  (x4) {
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x2) {
            date  (x1)
            has_war  (x1)
        }
    }
    CHI_stop_helping_HBC  (x5) {
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x3) {
            NOT  (x3) {
                HBC  (x2) {
                    is_subject_of  (x1)
                }
            }
        }
    }
    CHI_unit_production  (x3) {
        abort  (x1) {
            always  (x1)
        }
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x1) {
            always  (x1)
        }
    }
    CHI_you_should_be_prepared_for_war  (x4) {
        allowed  (x3) {
            NOT  (x2) {
                has_dlc  (x1)
            }
            is_literally_china  (x1)
        }
        enable  (x1) {
            date  (x1)
        }
    }
    HBC_do_everything_possible_to_allow_japan_to_invade  (x6) {
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x5) {
            CHI  (x3) {
                NOT  (x2) {
                    has_completed_focus  (x1)
                }
            }
            date  (x1)
            has_war  (x1)
        }
    }
    PRC_focus_militias_early_game  (x2) {
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x1) {
            date  (x1)
        }
    }
    PRC_let_everyone_else_do_the_fighting  (x9) {
        allowed  (x2) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x7) {
            NOT  (x5) {
                any_controlled_state  (x4) {
                    any_neighbor_state  (x3) {
                        controller  (x2) {
                            has_war_with  (x1)
                        }
                    }
                }
            }
            date  (x1)
            is_in_faction_with  (x1)
        }
    }
    PRC_military_factories_and_production  (x2) {
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x1) {
            date  (x1)
        }
    }
    SIK_push_khotan  (x10) {
        abort  (x4) {
            KHM  (x4) {
                OR  (x3) {
                    exists  (x1)
                    has_capitulated  (x1)
                }
            }
        }
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x5) {
            OR  (x5) {
                focus_progress  (x3) {
                    focus  (x1)
                    progress  (x1)
                }
                has_war_with  (x1)
            }
        }
    }
    less_trucks_4_u_AST  (x2) {
        allowed  (x1) {
            original_tag  (x1)
        }
        enable  (x1) {
            date  (x1)
        }
    }
    warlords_help_pls  (x4) {
        allowed  (x1) {
            is_chinese_warlord  (x1)
        }
        enable  (x3) {
            has_war_with  (x1)
            is_historical_focus_on  (x1)
            is_in_faction_with  (x1)
        }
    }
    warlords_hunker_down_now  (x5) {
        allowed  (x1) {
            is_chinese_warlord  (x1)
        }
        enable  (x4) {
            date  (x1)
            has_defensive_war  (x1)
            has_war_with  (x1)
            is_historical_focus_on  (x1)
        }
    }
    warlords_hunker_down_now_2  (x5) {
        allowed  (x1) {
            is_chinese_warlord  (x1)
        }
        enable  (x4) {
            date  (x1)
            has_defensive_war  (x1)
            has_war_with  (x1)
            is_historical_focus_on  (x1)
        }
    }
}
```


## AI 战略计划编辑器（ai_strategy_plans）

> 说明：未知字段走 ScriptBlockEditor 原始 PDX 兜底

扫描文件：10

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

总缺失条数：**1089**

##### common/ai_strategy_plans

```text
common/ai_strategy_plans  (x1089) {
    AFG_caliphate_plan  (x70) {
        abort  (x2) {
            is_subject  (x1)
        }
        ai_national_focuses  (x52) {
            AFG_against_kabul  (x1)
            AFG_appraoch_anti_communist_theologians  (x1)
            AFG_asymmetric_warfare  (x1)
            AFG_clear_malarial_swamps  (x1)
            AFG_connect_the_cities  (x1)
            AFG_contact_rural_loyalists  (x1)
            AFG_crown_the_golden_emir  (x1)
            AFG_electrification  (x1)
            AFG_encourage_jezail_production  (x1)
            AFG_enforce_the_pashtunwali  (x1)
            AFG_establish_camelry_regiments  (x1)
            AFG_establish_radio_networks  (x1)
            AFG_expand_karakul_lambskin_industry  (x1)
            AFG_expand_quami_template  (x1)
            AFG_expand_telegraph_network  (x1)
            AFG_expand_the_madrasas  (x1)
            AFG_extend_a_hand_to_tokyo  (x1)
            AFG_form_the_khuddamul_furqan  (x1)
            AFG_form_the_turkestan_legion  (x1)
            AFG_fruit_packing  (x1)
            AFG_hold_a_loya_jirga  (x1)
            AFG_implement_currency_controls  (x1)
            AFG_infrastructure_construction  (x1)
            AFG_instate_a_compulsory_jizya  (x1)
            AFG_invite_waziristan_rebels  (x1)
            AFG_khyber_pass_riflining  (x1)
            AFG_maintain_quami  (x1)
            AFG_militia_cavalry  (x1)
            AFG_ministry_of_supply  (x1)
            AFG_mountain_training  (x1)
            AFG_mountain_training_2  (x1)
            AFG_prepare_the_war_industries  (x1)
            AFG_proclaim_a_new_caliphate  (x1)
            AFG_promote_muslim_work_ethic  (x1)
            AFG_rail_construction  (x1)
            AFG_raise_lashkar_regiments  (x1)
            AFG_reintroduce_war_elephants  (x1)
            AFG_remember_the_khost_rebellion  (x1)
            AFG_reorganize_the_royal_guard  (x1)
            AFG_request_japanese_support  (x1)
            AFG_revive_the_workshop_of_the_world  (x1)
            AFG_scavenging  (x1)
            AFG_spinzar_cotton_factory  (x1)
            AFG_stir_unrest_in_the_east  (x1)
            AFG_sugar_processing  (x1)
            AFG_support_nort_west_frontier_rebels  (x1)
            AFG_the_faqirs_revolt  (x1)
            AFG_ulugh_beg_academy  (x1)
            AFG_unite_pashtunistan  (x1)
            AFG_utilize_cameleers  (x1)
            SSB_expand_afghanistans_military_infrastructure  (x1)
        }
        allowed  (x3) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x6) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
        focus_factors  (x1)
        ideas  (x1)
        research  (x1)
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    AFG_communist_plan  (x53) {
        abort  (x2) {
            is_subject  (x1)
        }
        ai_national_focuses  (x35) {
            AFG_adopt_nufus  (x1)
            AFG_central_asian_unification  (x1)
            AFG_chromite_mines  (x1)
            AFG_clear_malarial_swamps  (x1)
            AFG_communist_industrialization  (x1)
            AFG_development_in_taj  (x1)
            AFG_development_in_tms  (x1)
            AFG_development_in_uzb  (x1)
            AFG_electrification  (x1)
            AFG_establish_radio_networks  (x1)
            AFG_expand_kabul_university  (x1)
            AFG_expand_telegraph_network  (x1)
            AFG_fruit_packing  (x1)
            AFG_infrastructure_construction  (x1)
            AFG_integrate_tajik_and_uzbek_republics  (x1)
            AFG_iron_mines  (x1)
            AFG_kajaki_dam  (x1)
            AFG_modern_economy  (x1)
            AFG_new_army  (x1)
            AFG_qargha_dam  (x1)
            AFG_renew_soviet_trade_agreement  (x1)
            AFG_retire_the_uncles  (x1)
            AFG_salang_pass  (x1)
            AFG_socialist_coup  (x1)
            AFG_soviet_research_cooperation  (x1)
            AFG_state_atheism  (x1)
            AFG_sugar_processing  (x1)
            AFG_support_king_zahir  (x1)
            AFG_support_soviets_in_asia  (x1)
            AFG_truck_factory  (x1)
            SSB_baghlan_sugar_factory_branches  (x1)
            SSB_economic_cooperation  (x1)
            SSB_expand_afghanistans_military_infrastructure  (x1)
            SSB_military_cooperation  (x1)
        }
        allowed  (x2) {
            original_tag  (x1)
        }
        enable  (x7) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
            has_dlc  (x1)
        }
        focus_factors  (x1)
        ideas  (x1)
        research  (x1)
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    AFG_democratic_plan  (x77) {
        abort  (x2) {
            is_subject  (x1)
        }
        ai_national_focuses  (x59) {
            AFG_75_year_oil_concessions  (x1)
            AFG_accelerate_integration  (x1)
            AFG_adopt_nufus  (x1)
            AFG_align_with_the_allies  (x1)
            AFG_anti_soviet_cooperation  (x1)
            AFG_chromite_mines  (x1)
            AFG_clear_malarial_swamps  (x1)
            AFG_concessions_to_pashtuns  (x1)
            AFG_electrification  (x1)
            AFG_establish_naval_bases  (x1)
            AFG_expand_academy  (x1)
            AFG_expand_border_guards  (x1)
            AFG_expand_karakul_lambskin_industry  (x1)
            AFG_expand_royal_guard  (x1)
            AFG_expand_telegraph_network  (x1)
            AFG_expand_the_kings_powerbase  (x1)
            AFG_fruit_packing  (x1)
            AFG_future_of_balochistan  (x1)
            AFG_gain_religious_support_for_reforms  (x1)
            AFG_implement_currency_controls  (x1)
            AFG_infrastructure_construction  (x1)
            AFG_iron_mines  (x1)
            AFG_kajaki_dam  (x1)
            AFG_linchpin_of_global_defense  (x1)
            AFG_look_to_other_partners  (x1)
            AFG_modern_economy  (x1)
            AFG_new_army  (x1)
            AFG_parliamentary_democracy  (x1)
            AFG_prepare_for_operation_countenance  (x1)
            AFG_promote_the_counter_elite  (x1)
            AFG_propose_confederation_with_pakistan  (x1)
            AFG_purchase_aircraft  (x1)
            AFG_purchase_capital_ships  (x1)
            AFG_purchase_destroyers  (x1)
            AFG_purchase_tanks  (x1)
            AFG_pursue_our_own_agenda  (x1)
            AFG_qargha_dam  (x2)
            AFG_rail_construction  (x1)
            AFG_rapprochement_with_non_pashtuns  (x1)
            AFG_reform_1  (x1)
            AFG_reform_3  (x1)
            AFG_reform_4  (x1)
            AFG_repeal_the_durand_line  (x1)
            AFG_retire_the_uncles  (x1)
            AFG_secure_iran  (x1)
            AFG_shipyards  (x1)
            AFG_sugar_processing  (x1)
            AFG_support_king_zahir  (x1)
            SSB_baghlan_sugar_factory_branches  (x1)
            SSB_combined_arms  (x1)
            SSB_coordinate_military_production  (x1)
            SSB_economic_cooperation  (x1)
            SSB_expand_afghanistans_military_infrastructure  (x1)
            SSB_expand_road_and_rail_connections  (x1)
            SSB_joint_military_exercises  (x1)
            SSB_military_cooperation  (x1)
            SSB_saadabad_research_cooperation  (x1)
        }
        allowed  (x2) {
            original_tag  (x1)
        }
        enable  (x7) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
            has_dlc  (x1)
        }
        focus_factors  (x1)
        ideas  (x1)
        research  (x1)
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    AFG_empire_plan  (x65) {
        abort  (x2) {
            is_subject  (x1)
        }
        ai_national_focuses  (x47) {
            AFG_adopt_nufus  (x1)
            AFG_against_kabul  (x1)
            AFG_ally_the_brahui_khanate  (x1)
            AFG_connect_the_cities  (x1)
            AFG_contact_rural_loyalists  (x1)
            AFG_crown_the_bukharan_emir  (x1)
            AFG_electrification  (x1)
            AFG_establish_camelry_regiments  (x1)
            AFG_expand_academy  (x1)
            AFG_expand_karakul_lambskin_industry  (x1)
            AFG_expand_standing_army  (x1)
            AFG_expand_telegraph_network  (x1)
            AFG_expand_the_madrasas  (x1)
            AFG_extend_a_hand_to_tokyo  (x1)
            AFG_foreign_military_advisors  (x1)
            AFG_fruit_packing  (x1)
            AFG_hold_a_loya_jirga  (x1)
            AFG_hone_the_shamshir  (x1)
            AFG_implement_currency_controls  (x1)
            AFG_infrastructure_construction  (x1)
            AFG_integrate_the_basmachi_movement  (x1)
            AFG_invite_waziristan_rebels  (x1)
            AFG_ministry_of_supply  (x1)
            AFG_mountain_training  (x1)
            AFG_mountain_training_2  (x1)
            AFG_new_army  (x1)
            AFG_prepare_the_war_industries  (x1)
            AFG_proclaim_the_second_afghan_empire  (x1)
            AFG_promote_muslim_work_ethic  (x1)
            AFG_rehabilitate_the_saqqawists  (x1)
            AFG_reintroduce_war_elephants  (x1)
            AFG_remember_the_khost_rebellion  (x1)
            AFG_reorganize_the_royal_guard  (x1)
            AFG_request_german_support  (x1)
            AFG_request_japanese_support  (x1)
            AFG_restore_herat  (x1)
            AFG_revive_the_workshop_of_the_world  (x1)
            AFG_spinzar_cotton_factory  (x1)
            AFG_stir_unrest_in_the_east  (x1)
            AFG_sugar_processing  (x1)
            AFG_the_amu_darya_plan  (x1)
            AFG_the_echoes_of_panipat  (x1)
            AFG_the_faqirs_revolt  (x1)
            AFG_ulugh_beg_academy  (x1)
            AFG_utilize_cameleers  (x1)
            SSB_expand_afghanistans_military_infrastructure  (x1)
        }
        allowed  (x3) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x6) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
        focus_factors  (x1)
        ideas  (x1)
        research  (x1)
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    AFG_fascism_plan  (x70) {
        abort  (x2) {
            is_subject  (x1)
        }
        ai_national_focuses  (x52) {
            AFG_adopt_nufus  (x1)
            AFG_against_kabul  (x1)
            AFG_agreement_with_germany  (x1)
            AFG_alliance_with_turkik_peoples  (x1)
            AFG_alternative_partnerships  (x1)
            AFG_axis_equipment  (x1)
            AFG_chromite_mines  (x1)
            AFG_clear_malarial_swamps  (x1)
            AFG_contact_amanullah_loyalists  (x1)
            AFG_contact_rural_loyalists  (x1)
            AFG_custail_pashtunwali_primacy  (x1)
            AFG_education_for_women_and_girls  (x1)
            AFG_electrification  (x1)
            AFG_enforce_western_attire  (x1)
            AFG_establish_camelry_regiments  (x1)
            AFG_establish_radio_networks  (x1)
            AFG_expand_border_guards  (x1)
            AFG_expand_equipment_purchases  (x1)
            AFG_expand_kabul_university  (x1)
            AFG_expand_karakul_lambskin_industry  (x1)
            AFG_expand_royal_guard  (x1)
            AFG_expand_state_run_factories  (x1)
            AFG_expand_telegraph_network  (x1)
            AFG_eyes_on_the_north  (x1)
            AFG_fruit_packing  (x1)
            AFG_increase_air_purchases  (x1)
            AFG_infrastructure_construction  (x1)
            AFG_iron_mines  (x1)
            AFG_join_axis  (x1)
            AFG_kabul_conference  (x1)
            AFG_kajaki_dam  (x1)
            AFG_modern_economy  (x1)
            AFG_new_army  (x1)
            AFG_officer_training  (x1)
            AFG_permit_axis_airbases  (x1)
            AFG_purchase_aircraft  (x1)
            AFG_purchase_tanks  (x1)
            AFG_qargha_dam  (x1)
            AFG_reinforce_the_royal_guard  (x1)
            AFG_request_german_support  (x1)
            AFG_return_of_the_emir  (x1)
            AFG_revive_the_1923_constitution  (x1)
            AFG_secure_army_support  (x1)
            AFG_spinzar_cotton_factory  (x1)
            AFG_sugar_processing  (x1)
            AFG_utilize_cameleers  (x1)
            SSB_baghlan_sugar_factory_branches  (x1)
            SSB_combined_arms  (x1)
            SSB_coordinate_military_production  (x1)
            SSB_expand_afghanistans_military_infrastructure  (x1)
            SSB_joint_military_exercises  (x1)
        }
        allowed  (x3) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x6) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
        focus_factors  (x1)
        ideas  (x1)
        research  (x1)
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    AFG_historical_plan  (x66) {
        abort  (x3) {
            has_war  (x1)
            is_subject  (x1)
        }
        ai_national_focuses  (x42) {
            AFG_afghan_pakistan_cold_War  (x1)
            AFG_anti_soviet_cooperation  (x1)
            AFG_asymmetric_warfare  (x1)
            AFG_biding_our_time  (x1)
            AFG_clear_malarial_swamps  (x1)
            AFG_electrification  (x1)
            AFG_establish_radio_networks  (x1)
            AFG_expand_academy  (x1)
            AFG_expand_border_guards  (x1)
            AFG_expand_karakul_lambskin_industry  (x1)
            AFG_expand_royal_guard  (x1)
            AFG_expand_telegraph_network  (x1)
            AFG_expel_axis_nationals  (x1)
            AFG_forge_a_national_identity  (x1)
            AFG_fruit_packing  (x1)
            AFG_graveyard_of_empires  (x1)
            AFG_implement_currency_controls  (x1)
            AFG_infrastructure_construction  (x1)
            AFG_introduce_national_service  (x1)
            AFG_kajaki_dam  (x1)
            AFG_maintain_neutrality  (x1)
            AFG_maintain_quami  (x1)
            AFG_ministry_of_supply  (x1)
            AFG_placeholder_1  (x1)
            AFG_purchase_aircraft  (x1)
            AFG_purchase_tanks  (x1)
            AFG_pursue_our_own_agenda  (x1)
            AFG_qargha_dam  (x1)
            AFG_reform_2  (x1)
            AFG_secure_dynasty  (x1)
            AFG_spinzar_cotton_factory  (x1)
            AFG_sugar_processing  (x1)
            AFG_support_king_zahir  (x1)
            AFG_utilize_cameleers  (x1)
            SSB_baghlan_sugar_factory_branches  (x1)
            SSB_combined_arms  (x1)
            SSB_coordinate_military_production  (x1)
            SSB_expand_afghanistans_military_infrastructure  (x1)
            SSB_expand_road_and_rail_connections  (x1)
            SSB_joint_military_exercises  (x1)
            SSB_saadabad_research_cooperation  (x1)
        }
        allowed  (x3) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x11) {
            OR  (x10) {
                AND  (x5) {
                    has_game_rule  (x3) {
                        option  (x1)
                        rule  (x1)
                    }
                    is_historical_focus_on  (x1)
                }
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
        focus_factors  (x1)
        ideas  (x1)
        research  (x1)
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    AFG_mughal_plan  (x73) {
        abort  (x5) {
            OR  (x4) {
                RAJ  (x2) {
                    has_completed_focus  (x1)
                }
                is_subject  (x1)
            }
        }
        ai_national_focuses  (x52) {
            AFG_adopt_nufus  (x1)
            AFG_against_kabul  (x1)
            AFG_ally_the_sikhs  (x1)
            AFG_connect_the_cities  (x1)
            AFG_contact_rural_loyalists  (x1)
            AFG_electrification  (x1)
            AFG_establish_camelry_regiments  (x1)
            AFG_establish_radio_networks  (x1)
            AFG_expand_academy  (x1)
            AFG_expand_karakul_lambskin_industry  (x1)
            AFG_expand_standing_army  (x1)
            AFG_expand_telegraph_network  (x1)
            AFG_expand_the_madrasas  (x1)
            AFG_extend_a_hand_to_tokyo  (x1)
            AFG_foreign_military_advisors  (x1)
            AFG_fruit_packing  (x1)
            AFG_hold_a_loya_jirga  (x1)
            AFG_hone_the_shamshir  (x1)
            AFG_implement_currency_controls  (x1)
            AFG_infrastructure_construction  (x1)
            AFG_invite_the_mughal_prince  (x1)
            AFG_invite_waziristan_rebels  (x1)
            AFG_ministry_of_supply  (x1)
            AFG_mountain_training  (x1)
            AFG_mountain_training_2  (x1)
            AFG_new_army  (x1)
            AFG_prepare_the_war_industries  (x1)
            AFG_promote_muslim_work_ethic  (x1)
            AFG_rail_construction  (x1)
            AFG_rebuild_the_silk_road  (x1)
            AFG_reclaim_moghulistan  (x1)
            AFG_reclaim_transoxiana  (x1)
            AFG_reintroduce_heavy_cavalry  (x1)
            AFG_reintroduce_war_elephants  (x1)
            AFG_remember_the_khost_rebellion  (x1)
            AFG_reorganize_the_royal_guard  (x1)
            AFG_request_german_support  (x1)
            AFG_request_japanese_support  (x1)
            AFG_restore_the_timurid_empire  (x1)
            AFG_return_to_delhi  (x1)
            AFG_revive_the_workshop_of_the_world  (x1)
            AFG_spinzar_cotton_factory  (x1)
            AFG_stir_unrest_in_the_east  (x1)
            AFG_sugar_processing  (x1)
            AFG_the_conquerors_of_persia  (x1)
            AFG_the_crown_and_the_world  (x1)
            AFG_the_faqirs_revolt  (x1)
            AFG_timurid_bureaucracy  (x1)
            AFG_ulugh_beg_academy  (x1)
            AFG_utilize_cameleers  (x1)
            SSB_expand_afghanistans_military_infrastructure  (x1)
        }
        allowed  (x3) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x6) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
        focus_factors  (x1)
        ideas  (x1)
        research  (x1)
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    ARG_communist_plan  (x54) {
        abort  (x2) {
            is_subject  (x1)
        }
        ai_national_focuses  (x36) {
            ARG_a_call_to_reform  (x1)
            ARG_a_new_trading_partner  (x1)
            ARG_a_red_south_america  (x2)
            ARG_agricultural_improvements  (x1)
            ARG_align_with_the_soviets  (x1)
            ARG_capitalize_the_beef_industry  (x1)
            ARG_centralize_power  (x1)
            ARG_committee_of_state_security  (x1)
            ARG_conquer_south_america  (x1)
            ARG_economic_reactivation_act  (x1)
            ARG_empower_the_fjc  (x1)
            ARG_industrial_expansion  (x1)
            ARG_integrate_the_motherland  (x1)
            ARG_invest_in_the_railways  (x1)
            ARG_invest_in_the_roads  (x1)
            ARG_invite_ghioldi_back_to_argentina  (x1)
            ARG_legitimize_the_PCA  (x1)
            ARG_military_production_lines  (x1)
            ARG_rapid_urbanization  (x1)
            ARG_reach_out_to_the_soviet_union  (x1)
            ARG_reform_our_industry  (x1)
            ARG_russian_manufacturers  (x1)
            ARG_socialist_researchers  (x1)
            ARG_soviet_industrial_model  (x1)
            ARG_state_atheism  (x1)
            ARG_support_the_spanish_republicans  (x1)
            ARG_unite_the_workers_of_argentina  (x1)
            ARG_viva_la_revolucion  (x1)
            ARG_workers_rights  (x1)
            SMB_air_force  (x1)
            SMB_army  (x1)
            SMB_construct_air_bases  (x1)
            SMB_navy  (x1)
            SMB_regular_infantry  (x1)
        }
        allowed  (x2) {
            original_tag  (x1)
        }
        enable  (x7) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
            has_DLC  (x1)
        }
        focus_factors  (x1)
        ideas  (x1)
        research  (x1)
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    ARG_democratic_plan  (x57) {
        abort  (x2) {
            is_subject  (x1)
        }
        ai_national_focuses  (x39) {
            ARG_a_true_democracy  (x1)
            ARG_agricultural_improvements  (x1)
            ARG_align_with_the_monroe_doctrine  (x1)
            ARG_american_allyship  (x1)
            ARG_anti_corruption_policies  (x1)
            ARG_argentina_for_all  (x1)
            ARG_banco_central_de_la_republica_argentina  (x1)
            ARG_british_gaurantee  (x1)
            ARG_capitalize_the_beef_industry  (x1)
            ARG_counter_intelligence_program  (x1)
            ARG_develop_civilian_economy  (x1)
            ARG_economic_reactivation_act  (x1)
            ARG_end_operation_bolivar  (x1)
            ARG_envoy_to_london  (x1)
            ARG_firmes_volamos  (x1)
            ARG_in_memory_of_yrigoyen  (x1)
            ARG_industrial_expansion  (x1)
            ARG_invest_in_the_railways  (x1)
            ARG_invest_in_the_roads  (x1)
            ARG_join_the_allies  (x1)
            ARG_military_production_lines  (x1)
            ARG_promote_urbanization  (x1)
            ARG_rapid_urbanization  (x1)
            ARG_regulated_national_salaries  (x1)
            ARG_reinforce_the_education_system  (x1)
            ARG_reinforced_alliance  (x1)
            ARG_revisit_the_roca_runciman_treaty  (x1)
            ARG_royal_airforce_influence  (x1)
            ARG_secure_the_opposition  (x1)
            ARG_social_welfare_fund  (x1)
            ARG_study_the_battle_of_the_river_plate  (x1)
            ARG_the_clean_election  (x1)
            ARG_university_reforms  (x1)
            SMB_air_force  (x1)
            SMB_army  (x1)
            SMB_construct_air_bases  (x1)
            SMB_navy  (x1)
            SMB_regular_infantry  (x1)
        }
        allowed  (x2) {
            original_tag  (x1)
        }
        enable  (x7) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
            has_DLC  (x1)
        }
        focus_factors  (x1)
        ideas  (x1)
        research  (x1)
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    ARG_fascism_plan  (x56) {
        abort  (x2) {
            is_subject  (x1)
        }
        ai_national_focuses  (x38) {
            ARG_agricultural_improvements  (x1)
            ARG_anti_american_propaganda  (x1)
            ARG_argentine_island_sovereignty  (x1)
            ARG_banco_central_de_la_republica_argentina  (x1)
            ARG_chilean_ultimatum  (x1)
            ARG_corporatism  (x1)
            ARG_crack_down_on_corruption  (x1)
            ARG_cut_ties_with_britain  (x1)
            ARG_dominate_the_south  (x1)
            ARG_economic_reactivation_act  (x1)
            ARG_encourage_german_investments  (x1)
            ARG_fascist_researchers  (x1)
            ARG_guardia_nacional  (x1)
            ARG_industrial_expansion  (x1)
            ARG_integrate_operation_bolivar  (x1)
            ARG_invite_spanish_nationalists  (x1)
            ARG_join_the_axis  (x1)
            ARG_military_production_lines  (x1)
            ARG_paraguayan_ultimatum  (x1)
            ARG_rapid_militirization  (x1)
            ARG_rapid_urbanization  (x1)
            ARG_reestablish_ligas_patrioticas  (x1)
            ARG_release_hellmuth  (x1)
            ARG_revive_the_colonial_plan  (x1)
            ARG_roberto_maria_ortiz  (x1)
            ARG_secure_the_borders  (x1)
            ARG_south_american_unity  (x1)
            ARG_support_radical_nationalism  (x1)
            ARG_support_the_spanish_coup  (x1)
            ARG_the_old_enemy  (x1)
            ARG_the_war_machine  (x1)
            ARG_war_division  (x1)
            ARG_work_with_the_nationalists  (x1)
            SMB_air_force  (x1)
            SMB_army  (x1)
            SMB_construct_air_bases  (x1)
            SMB_navy  (x1)
        }
        allowed  (x2) {
            original_tag  (x1)
        }
        enable  (x7) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
            has_DLC  (x1)
        }
        focus_factors  (x1)
        ideas  (x1)
        research  (x1)
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    ARG_historical_plan  (x89) {
        abort  (x3) {
            has_war  (x1)
            is_subject  (x1)
        }
        ai_national_focuses  (x66) {
            ARG_agricultural_improvements  (x1)
            ARG_align_with_the_monroe_doctrine  (x1)
            ARG_american_allyship  (x1)
            ARG_balancing_act  (x1)
            ARG_banco_central_de_la_republica_argentina  (x1)
            ARG_british_cooperation  (x1)
            ARG_capitalize_the_beef_industry  (x1)
            ARG_consolidating_power  (x1)
            ARG_crack_down_on_corruption  (x1)
            ARG_defense_and_democracy  (x1)
            ARG_develop_civilian_economy  (x1)
            ARG_economic_reactivation_act  (x1)
            ARG_economic_tax_reforms  (x1)
            ARG_emphasis_on_public_works  (x1)
            ARG_envoy_to_london  (x1)
            ARG_expand_aluminum_extraction  (x1)
            ARG_expand_steel_extraction  (x1)
            ARG_firmes_volamos  (x1)
            ARG_immigration_wave  (x1)
            ARG_import_substitution  (x1)
            ARG_industrial_expansion  (x1)
            ARG_invest_in_the_railways  (x1)
            ARG_invest_in_the_roads  (x1)
            ARG_join_the_allies  (x1)
            ARG_march_to_la_casa_rosada  (x1)
            ARG_military_production_lines  (x1)
            ARG_rapid_urbanization  (x1)
            ARG_revisit_the_roca_runciman_treaty  (x1)
            ARG_roberto_maria_ortiz  (x1)
            ARG_study_the_battle_of_the_river_plate  (x1)
            ARG_the_american_push  (x1)
            ARG_the_argentinian_metropole  (x1)
            ARG_the_castillo_cabinet  (x1)
            ARG_towards_a_greater_argentina  (x1)
            ARG_universidad_de_buenos_aires  (x1)
            ARG_yacimientos_petroliferos_fiscales  (x1)
            SMB_air_academy  (x1)
            SMB_air_defense  (x1)
            SMB_air_force  (x1)
            SMB_air_modifier_boost_1  (x1)
            SMB_army  (x1)
            SMB_army_academy  (x1)
            SMB_artillery  (x2)
            SMB_construct_air_bases  (x1)
            SMB_construct_naval_bases  (x2)
            SMB_domestic_production  (x1)
            SMB_enlarge_naval_facilities  (x1)
            SMB_establish_aircraft_industry  (x1)
            SMB_expand_repair_yards  (x1)
            SMB_foreign_advisors  (x1)
            SMB_fortification_effort  (x1)
            SMB_license_designs  (x1)
            SMB_military_facilities  (x1)
            SMB_naval_foreign_advisors  (x2)
            SMB_navy  (x1)
            SMB_nimble_air_force  (x1)
            SMB_purchase_destroyers_and_subs  (x1)
            SMB_regular_infantry  (x2)
            SMB_tank_warfare  (x1)
            SMB_tierra_del_fuego_training  (x1)
            SMB_winning_the_air_war  (x1)
        }
        allowed  (x2) {
            original_tag  (x1)
        }
        enable  (x11) {
            OR  (x10) {
                AND  (x5) {
                    has_game_rule  (x3) {
                        option  (x1)
                        rule  (x1)
                    }
                    is_historical_focus_on  (x1)
                }
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
        focus_factors  (x1)
        ideas  (x1)
        research  (x1)
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    AST_adela_fascist_ai  (x26) {
        abort  (x1)
        ai_national_focuses  (x7) {
            AST_australia_first  (x1)
            AST_lang_plan  (x1)
            AST_pankhurst_walsh  (x1)
            AST_public_works  (x1)
            AST_rile_up_veterans  (x1)
            AST_the_bolsheviks_counterforce  (x1)
        }
        allowed  (x3) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x6) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
        focus_factors  (x2) {
            AST_womens_armed_services  (x1)
        }
        ideas  (x1)
        research  (x1)
        traits  (x1)
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    AST_alternate_communist  (x82) {
        abort  (x1)
        ai_national_focuses  (x56) {
            AST_abandon_the_westminster_system  (x1)
            AST_additional_militia_training  (x1)
            AST_airborne_defence  (x1)
            AST_allied_works_council  (x1)
            AST_army_inventions_directorate  (x1)
            AST_australian_arms_production  (x1)
            AST_australian_army_catering_corps  (x1)
            AST_cac_boomerang  (x1)
            AST_cac_woomera  (x1)
            AST_citizen_military_forces  (x1)
            AST_civil_construction_corps  (x1)
            AST_classify_aliens  (x1)
            AST_cockatoo_island_shipyards  (x1)
            AST_commitment_to_the_cause  (x1)
            AST_cruisers  (x1)
            AST_daimler_dingo  (x1)
            AST_death_from_down_under  (x1)
            AST_delegation_to_china  (x1)
            AST_department_of_supply_and_development  (x1)
            AST_dominate_the_skies  (x1)
            AST_empower_the_workers  (x1)
            AST_establish_advisory_war_council  (x1)
            AST_expand_lithgow_small_arms_factory  (x1)
            AST_expand_northern_presence  (x1)
            AST_expand_the_northern_railway  (x1)
            AST_expand_the_raaf  (x1)
            AST_fight_work_or_perish  (x1)
            AST_fly_the_jolly_roger  (x1)
            AST_hmas_assault  (x1)
            AST_indirect_support  (x1)
            AST_industries_assistance_corporation  (x1)
            AST_introduce_unconventional_warfare  (x1)
            AST_invest_in_victory  (x1)
            AST_join_comintern  (x1)
            AST_kangaroo_point_shipyards  (x1)
            AST_m_special_unit  (x1)
            AST_national_security_act  (x1)
            AST_naval_auxiliary_patrol  (x1)
            AST_naval_bombers  (x1)
            AST_never_another_gallipoli  (x1)
            AST_pacific_area_navy  (x1)
            AST_promote_reservists  (x1)
            AST_rationing_and_recycling  (x1)
            AST_research_collaboration  (x1)
            AST_royal_australian_artillery  (x1)
            AST_royal_australian_submarine_service  (x1)
            AST_scrap_iron_flotilla  (x1)
            AST_sentinel_tank_project  (x1)
            AST_south_australian_housing_trust  (x1)
            AST_specialize_equipment  (x1)
            AST_squash_the_squanderbugs  (x1)
            AST_standard_gauge_railway  (x1)
            AST_volunteer_defence_corps  (x1)
            AST_western_australian_government_railways  (x1)
            AST_z_special_unit  (x1)
        }
        allowed  (x4) {
            NOT  (x2) {
                has_dlc  (x1)
            }
            original_tag  (x1)
        }
        enable  (x6) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
        focus_factors  (x1)
        ideas  (x1)
        research  (x6) {
            artillery  (x1)
            dd_tech  (x1)
            industry  (x1)
            infantry_tech  (x1)
            support_tech  (x1)
        }
        traits  (x3) {
            captain_of_industry  (x1)
            war_industrialist  (x1)
        }
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    AST_alternate_democratic  (x81) {
        abort  (x1)
        ai_national_focuses  (x55) {
            AST_additional_militia_training  (x1)
            AST_airborne_defence  (x1)
            AST_allied_works_council  (x1)
            AST_army_inventions_directorate  (x1)
            AST_australian_arms_production  (x1)
            AST_australian_army_catering_corps  (x1)
            AST_cac_boomerang  (x1)
            AST_cac_woomera  (x1)
            AST_citizen_military_forces  (x1)
            AST_civil_construction_corps  (x1)
            AST_classify_aliens  (x1)
            AST_cockatoo_island_shipyards  (x1)
            AST_cruisers  (x1)
            AST_daimler_dingo  (x1)
            AST_death_from_down_under  (x1)
            AST_department_of_supply_and_development  (x1)
            AST_dominate_the_skies  (x1)
            AST_establish_advisory_war_council  (x1)
            AST_expand_lithgow_small_arms_factory  (x1)
            AST_expand_northern_presence  (x1)
            AST_expand_the_northern_railway  (x1)
            AST_expand_the_raaf  (x1)
            AST_fight_work_or_perish  (x1)
            AST_fly_the_jolly_roger  (x1)
            AST_hmas_assault  (x1)
            AST_industries_assistance_corporation  (x1)
            AST_introduce_unconventional_warfare  (x1)
            AST_invest_in_victory  (x1)
            AST_kangaroo_point_shipyards  (x1)
            AST_m_special_unit  (x1)
            AST_national_security_act  (x1)
            AST_naval_auxiliary_patrol  (x1)
            AST_naval_bombers  (x1)
            AST_never_another_gallipoli  (x1)
            AST_pacific_area_navy  (x1)
            AST_promote_reservists  (x1)
            AST_protect_the_homeland  (x1)
            AST_rationing_and_recycling  (x1)
            AST_royal_australian_artillery  (x1)
            AST_royal_australian_submarine_service  (x1)
            AST_scrap_iron_flotilla  (x1)
            AST_sentinel_tank_project  (x1)
            AST_sever_ties_with_uk  (x1)
            AST_south_australian_housing_trust  (x1)
            AST_specialize_equipment  (x1)
            AST_squash_the_squanderbugs  (x1)
            AST_standard_gauge_railway  (x1)
            AST_swpa_protector  (x1)
            AST_the_south_west_pacific_initiative  (x1)
            AST_uranium_mining  (x1)
            AST_volunteer_defence_corps  (x1)
            AST_western_australian_government_railways  (x1)
            AST_woo_usa  (x1)
            AST_z_special_unit  (x1)
        }
        allowed  (x4) {
            NOT  (x2) {
                has_dlc  (x1)
            }
            original_tag  (x1)
        }
        enable  (x6) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
        focus_factors  (x1)
        ideas  (x1)
        research  (x6) {
            artillery  (x1)
            dd_tech  (x1)
            industry  (x1)
            infantry_tech  (x1)
            support_tech  (x1)
        }
        traits  (x3) {
            captain_of_industry  (x1)
            war_industrialist  (x1)
        }
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    AST_alternate_fascist  (x82) {
        abort  (x1)
        ai_national_focuses  (x56) {
            AST_a_deal_with_japan  (x1)
            AST_abandon_the_westminster_system  (x1)
            AST_additional_militia_training  (x1)
            AST_airborne_defence  (x1)
            AST_allied_works_council  (x1)
            AST_army_inventions_directorate  (x1)
            AST_australian_arms_production  (x1)
            AST_australian_army_catering_corps  (x1)
            AST_cac_boomerang  (x1)
            AST_cac_woomera  (x1)
            AST_citizen_military_forces  (x1)
            AST_civil_construction_corps  (x1)
            AST_classify_aliens  (x1)
            AST_cockatoo_island_shipyards  (x1)
            AST_cruisers  (x1)
            AST_daimler_dingo  (x1)
            AST_death_from_down_under  (x1)
            AST_department_of_supply_and_development  (x1)
            AST_dominate_the_skies  (x1)
            AST_establish_advisory_war_council  (x1)
            AST_expand_lithgow_small_arms_factory  (x1)
            AST_expand_northern_presence  (x1)
            AST_expand_the_northern_railway  (x1)
            AST_expand_the_raaf  (x1)
            AST_fight_work_or_perish  (x1)
            AST_fly_the_jolly_roger  (x1)
            AST_hmas_assault  (x1)
            AST_industries_assistance_corporation  (x1)
            AST_introduce_unconventional_warfare  (x1)
            AST_invest_in_victory  (x1)
            AST_kangaroo_point_shipyards  (x1)
            AST_m_special_unit  (x1)
            AST_national_security_act  (x1)
            AST_naval_auxiliary_patrol  (x1)
            AST_naval_bombers  (x1)
            AST_never_another_gallipoli  (x1)
            AST_pacific_area_navy  (x1)
            AST_promote_reservists  (x1)
            AST_protect_the_south_west_pacific  (x1)
            AST_rationing_and_recycling  (x1)
            AST_research_collaboration  (x1)
            AST_royal_australian_artillery  (x1)
            AST_royal_australian_submarine_service  (x1)
            AST_scrap_iron_flotilla  (x1)
            AST_sentinel_tank_project  (x1)
            AST_south_australian_housing_trust  (x1)
            AST_specialize_equipment  (x1)
            AST_squash_the_squanderbugs  (x1)
            AST_standard_gauge_railway  (x1)
            AST_supply_indonesian_nationalists  (x1)
            AST_support_indonesian_uprising  (x1)
            AST_support_the_centre_party  (x1)
            AST_volunteer_defence_corps  (x1)
            AST_western_australian_government_railways  (x1)
            AST_z_special_unit  (x1)
        }
        allowed  (x4) {
            NOT  (x2) {
                has_dlc  (x1)
            }
            original_tag  (x1)
        }
        enable  (x6) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
        focus_factors  (x1)
        ideas  (x1)
        research  (x6) {
            artillery  (x1)
            dd_tech  (x1)
            industry  (x1)
            infantry_tech  (x1)
            support_tech  (x1)
        }
        traits  (x3) {
            captain_of_industry  (x1)
            war_industrialist  (x1)
        }
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    AST_anti_commonwealth_communist_ai  (x21) {
        abort  (x1)
        ai_national_focuses  (x3) {
            AST_against_war_and_fascism  (x1)
            AST_the_australian_commonwealth  (x1)
        }
        allowed  (x3) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x6) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
        focus_factors  (x1)
        ideas  (x1)
        research  (x1)
        traits  (x1)
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    AST_comintern_communist_ai  (x21) {
        abort  (x1)
        ai_national_focuses  (x3) {
            AST_a_comrade_emancipated  (x1)
            AST_against_war_and_fascism  (x1)
        }
        allowed  (x3) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x6) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
        focus_factors  (x1)
        ideas  (x1)
        research  (x1)
        traits  (x1)
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    AST_peter_fascist_ai  (x26) {
        abort  (x1)
        ai_national_focuses  (x6) {
            AST_australia_first  (x1)
            AST_refuse_british_wars  (x1)
            AST_rile_up_veterans  (x1)
            AST_stephensen  (x1)
            AST_the_bolsheviks_counterforce  (x1)
        }
        allowed  (x3) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x6) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
        focus_factors  (x3) {
            AST_department_of_aboriginal_affairs  (x1)
        }
        ideas  (x1)
        research  (x1)
        traits  (x1)
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
    AST_random_democratic_ai  (x20) {
        abort  (x1)
        ai_national_focuses  (x2) {
            AST_war_is_coming  (x1)
        }
        allowed  (x3) {
            has_dlc  (x1)
            original_tag  (x1)
        }
        enable  (x6) {
            OR  (x5) {
                has_country_flag  (x1)
                has_game_rule  (x3) {
                    option  (x1)
                    rule  (x1)
                }
            }
        }
        focus_factors  (x1)
        ideas  (x1)
        research  (x1)
        traits  (x1)
        weight  (x4) {
            factor  (x1)
            modifier  (x2) {
                factor  (x1)
            }
        }
    }
}
```


## 力量平衡工作台（bop）

> 说明：区间/势力/修正/决议表单全覆盖；动作块位于 common/decisions 文件，由 BOP 编辑器写回

扫描文件：10

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

（无缺口）


## 角色编辑器（character）

> 说明：portraits 表可编辑任意 scope/size/texture；role 已知字段可编辑；未知行保留原样；未知块（含 instance = { ... }）经 ScriptBlockEditorDialog 结构化编辑并写回

扫描文件：10

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

（无缺口）


## 国家历史文件（变体/顾问等）（country_history）

> 说明：变体（模块/升级）由三设计器覆盖；其余块走树编辑器，逐步收敛

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

> 说明：节点弹窗常用字段已覆盖；未知字段仍可能只在树编辑器可见

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


## 师编制/OOB 地编/设计器（initial_oob）

> 说明：OOB_COVERED_TOP_KEYS 之外的顶层块（如 division_names_group、instant_effect）会报缺失

扫描文件：10

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

总缺失条数：**118**

##### history/units

```text
history/units  (x118) {
    NEW_INITIAL_OOB  (x12) {
        division  (x10) {
            division_template  (x2)
            location  (x2)
            name  (x2)
            start_experience_factor  (x2)
        }
    }
    instant_effect  (x106) {
        add_equipment_production  (x28) {
            efficiency  (x4)
            equipment  (x12) {
                creator  (x4)
                type  (x4)
            }
            progress  (x4)
            requested_factories  (x4)
        }
        add_equipment_to_stockpile  (x72) {
            amount  (x18)
            producer  (x18)
            type  (x18)
        }
    }
}
```

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

（无缺口）


## 地图编辑器（州）（state）

> 说明：resources/victory_points/manpower/州名/州类别由右侧州字段表单覆盖；history.resources 为兼容 mod 写法；其余 state 嵌套字段（天气/历史/高级建筑等）仍可能走树编辑器，属长期收敛项

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


## 区域编辑器（战略区域）（strategic_region）

> 说明：区域编辑器主要做框选划分；字段级编辑仍可能缺失

扫描文件：10

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

总缺失条数：**2307**

##### map/strategicregions

```text
map/strategicregions  (x2307) {
    strategic_region  (x2307) {
        provinces  (x387) {
            10321  (x2)
            11044  (x2)
            11070  (x2)
            11082  (x2)
            11114  (x2)
            11160  (x2)
            11163  (x2)
            11188  (x2)
            11215  (x2)
            11221  (x2)
            11231  (x2)
            11253  (x2)
            11278  (x2)
            11279  (x2)
            11280  (x2)
            11289  (x2)
            11311  (x2)
            11327  (x2)
            11333  (x2)
            11345  (x2)
            11374  (x2)
            11376  (x2)
            11380  (x2)
            11390  (x2)
            11406  (x2)
            11446  (x2)
            11471  (x2)
            12251  (x2)
            13070  (x2)
            13072  (x2)
            13095  (x2)
            13096  (x2)
            13097  (x2)
            13098  (x2)
            13259  (x1)
            13264  (x1)
            13265  (x1)
            14407  (x1)
            14408  (x1)
            14409  (x1)
            14410  (x1)
            147  (x2)
            161  (x2)
            171  (x2)
            211  (x2)
            221  (x2)
            2240  (x2)
            2266  (x2)
            2292  (x2)
            2318  (x2)
            2342  (x2)
            2368  (x2)
            2392  (x2)
            242  (x2)
            2605  (x2)
            2631  (x2)
            2654  (x2)
            2680  (x2)
            2704  (x2)
            271  (x2)
            2730  (x2)
            2753  (x2)
            2776  (x2)
            2800  (x2)
            2825  (x2)
            295  (x2)
            296  (x2)
            299  (x2)
            3063  (x2)
            3106  (x2)
            3128  (x2)
            3141  (x2)
            3182  (x2)
            322  (x2)
            3229  (x2)
            3241  (x2)
            3286  (x2)
            3287  (x2)
            329  (x2)
            3301  (x2)
            3307  (x2)
            3353  (x2)
            3369  (x2)
            3375  (x2)
            3386  (x2)
            3422  (x2)
            3463  (x2)
            35  (x2)
            3501  (x2)
            363  (x2)
            364  (x2)
            383  (x2)
            4694  (x2)
            4917  (x2)
            507  (x2)
            5130  (x2)
            5246  (x2)
            5271  (x2)
            5298  (x2)
            5324  (x2)
            5347  (x2)
            5369  (x2)
            5383  (x2)
            5388  (x2)
            5394  (x2)
            540  (x2)
            5418  (x2)
            5442  (x2)
            5466  (x2)
            5518  (x2)
            5692  (x2)
            5718  (x2)
            5745  (x2)
            5770  (x2)
            5797  (x2)
            5823  (x2)
            5850  (x2)
            5873  (x2)
            5900  (x2)
            5923  (x2)
            5947  (x2)
            5971  (x2)
            5994  (x2)
            6028  (x2)
            6037  (x2)
            6050  (x2)
            6084  (x2)
            6103  (x2)
            6120  (x2)
            6127  (x2)
            6148  (x2)
            6164  (x2)
            6188  (x2)
            6195  (x2)
            6209  (x2)
            6221  (x2)
            6237  (x2)
            6244  (x2)
            6270  (x2)
            6301  (x2)
            6310  (x2)
            6311  (x2)
            6331  (x2)
            6345  (x2)
            6351  (x2)
            6378  (x2)
            6397  (x2)
            6406  (x2)
            6412  (x2)
            6443  (x2)
            6489  (x2)
            6526  (x2)
            6633  (x2)
            6825  (x2)
            69  (x2)
            7029  (x2)
            7239  (x2)
            7253  (x2)
            7479  (x2)
            7705  (x2)
            7933  (x2)
            8151  (x2)
            8287  (x2)
            8313  (x2)
            8339  (x2)
            8366  (x2)
            8392  (x2)
            8417  (x2)
            8639  (x2)
            8665  (x2)
            8742  (x2)
            8766  (x2)
            8788  (x2)
            9054  (x2)
            9109  (x2)
            9138  (x2)
            9149  (x2)
            9185  (x2)
            9209  (x2)
            9218  (x2)
            9239  (x2)
            9250  (x2)
            9251  (x2)
            9268  (x2)
            9279  (x2)
            9297  (x2)
            9300  (x2)
            9308  (x2)
            9322  (x2)
            9329  (x2)
            9362  (x2)
            9393  (x2)
            9406  (x2)
            9410  (x2)
            9458  (x2)
            9484  (x2)
            9562  (x2)
        }
        weather  (x1920) {
            period  (x1920) {
                arctic_water  (x120)
                between  (x360) {
                    0  (x120) {
                        0  (x10)
                        1  (x10)
                        10  (x10)
                        11  (x10)
                        2  (x10)
                        3  (x10)
                        4  (x10)
                        5  (x10)
                        6  (x10)
                        7  (x10)
                        8  (x10)
                        9  (x10)
                    }
                    27  (x10) {
                        1  (x10)
                    }
                    29  (x40) {
                        10  (x10)
                        3  (x10)
                        5  (x10)
                        8  (x10)
                    }
                    30  (x70) {
                        0  (x10)
                        11  (x10)
                        2  (x10)
                        4  (x10)
                        6  (x10)
                        7  (x10)
                        9  (x10)
                    }
                }
                blizzard  (x120)
                min_snow_level  (x120)
                mud  (x120)
                no_phenomenon  (x120)
                rain_heavy  (x120)
                rain_light  (x120)
                sandstorm  (x120)
                snow  (x120)
                temperature  (x360) {
                    -1  (x1) {
                        0  (x1)
                    }
                    -10  (x1) {
                        0  (x1)
                    }
                    -12  (x2) {
                        0  (x2)
                    }
                    -14  (x1) {
                        0  (x1)
                    }
                    -16  (x2) {
                        0  (x2)
                    }
                    -2  (x2) {
                        0  (x2)
                    }
                    -4  (x1) {
                        0  (x1)
                    }
                    -5  (x5) {
                        0  (x5)
                    }
                    -6  (x2) {
                        0  (x2)
                    }
                    -7  (x1) {
                        0  (x1)
                    }
                    -9  (x1) {
                        0  (x1)
                    }
                    0  (x4) {
                        0  (x4)
                    }
                    1  (x1) {
                        0  (x1)
                    }
                    10  (x1) {
                        0  (x1)
                    }
                    11  (x2) {
                        0  (x2)
                    }
                    12  (x7) {
                        0  (x7)
                    }
                    13  (x4) {
                        0  (x4)
                    }
                    14  (x1) {
                        0  (x1)
                    }
                    15  (x3) {
                        0  (x3)
                    }
                    16  (x1) {
                        0  (x1)
                    }
                    17  (x2) {
                        0  (x2)
                    }
                    18  (x2) {
                        0  (x2)
                    }
                    19  (x3) {
                        0  (x3)
                    }
                    2  (x3) {
                        0  (x3)
                    }
                    20  (x2) {
                        0  (x2)
                    }
                    21  (x1) {
                        0  (x1)
                    }
                    22  (x5) {
                        0  (x5)
                    }
                    23  (x1) {
                        0  (x1)
                    }
                    24  (x4) {
                        0  (x4)
                    }
                    25  (x1) {
                        0  (x1)
                    }
                    3  (x4) {
                        0  (x4)
                    }
                    30  (x72) {
                        0  (x72)
                    }
                    4  (x1) {
                        0  (x1)
                    }
                    5  (x75) {
                        0  (x75)
                    }
                    6  (x5) {
                        0  (x5)
                    }
                    7  (x5) {
                        0  (x5)
                    }
                    8  (x6) {
                        0  (x6)
                    }
                    9  (x5) {
                        0  (x5)
                    }
                }
            }
        }
    }
}
```


## 区域编辑器（补给区域）（supply_area）

> 说明：区域编辑器主要做框选划分；字段级编辑仍可能缺失

扫描文件：2

#### 顶层缺口（文件有，专用 UI 未作为顶层处理）

（无缺口）

#### 嵌套词条缺口（在已处理顶层下，仍无展示/编辑）

总缺失条数：**8**

##### map/supplyareas

```text
map/supplyareas  (x8) {
    supply_area  (x8) {
        states  (x8) {
            5  (x2)
            763  (x2)
            807  (x2)
            85  (x2)
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
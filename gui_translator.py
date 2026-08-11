"""
GUI翻译器模块 — 多源翻译系统核心
提供PDX脚本关键字的中文翻译功能，支持以下翻译源：
  1. 内置字典（command_dict）— 硬编码的PDX命令关键字中英对照
  2. 游戏本地化文件（*_l_simp_chinese.yml）— HOI4官方中文翻译
  3. 用户自定义语句（custom_statements.json）— 用户可扩展的翻译
  4. GFX精灵映射（*.gfx文件）— 图标资源路径映射
  5. translations文件夹 — 外部翻译包自动加载

架构说明：
  GuiTranslator 是核心翻译引擎，负责合并所有翻译源并提供统一查询接口。
  get_translator() 是全局单例工厂函数，启动时自动扫描 translations 目录。
"""

import os
import re
import json


def scan_gfx_folder(base_path, gfx_map):
    """扫描 base_path/interface/*.gfx 文件，建立精灵名称到纹理路径的映射。

    用于同时从游戏目录和 mod 目录加载图标定义。
    纹理相对路径会基于 base_path 解析为绝对路径。

    Args:
        base_path: 游戏根目录或 mod 根目录
        gfx_map: 写入目标字典（精灵名 -> 纹理路径）
    """
    interface_dir = os.path.join(base_path, "interface")
    if not os.path.isdir(interface_dir):
        return

    block_pattern = re.compile(r'SpriteType\s*=\s*\{(.*?)\}', re.DOTALL | re.IGNORECASE)
    name_pattern = re.compile(r'name\s*=\s*"([^"]+)"')
    tex_pattern = re.compile(r'texturefile\s*=\s*"([^"]+)"', re.IGNORECASE)

    for filename in os.listdir(interface_dir):
        if not filename.lower().endswith(".gfx"):
            continue
        filepath = os.path.join(interface_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                content = f.read()
            for block in block_pattern.findall(content):
                n = name_pattern.search(block)
                t = tex_pattern.search(block)
                if n and t:
                    name = n.group(1)
                    tex = t.group(1).lower()
                    if not os.path.isabs(tex):
                        gfx_map[name] = os.path.join(base_path, tex)
                    else:
                        gfx_map[name] = tex
        except Exception:
            pass  # 忽略无法读取的GFX文件


class GuiTranslator:
    """多源翻译器：内置字典 + 游戏本地化文件 + 用户自定义语句"""

    def __init__(self, game_localisation_path=None, custom_statement_path=None, hoi4_path=None,
                 mod_path=None):
        # 加载内置PDX命令字典，这是最底层的翻译来源
        self.command_dict = self._build_command_dict()
        # 游戏本地化缓存：key -> 中文翻译
        self.loc_cache = {}
        # 用户自定义语句：key -> 完整语句信息（含cn_name, node_type等）
        self.custom_statements = {}
        # GFX精灵映射：精灵名称 -> 纹理文件路径
        self.gfx_map = {}
        # HOI4游戏根目录路径，用于GFX加载
        self.hoi4_path = hoi4_path
        # mod 根目录路径，用于加载 mod 本地化文件
        self.mod_path = mod_path

        # 按优先级加载翻译源：游戏本地化文件
        if game_localisation_path and os.path.isdir(game_localisation_path):
            self._load_localisation_files(game_localisation_path)

        # mod 本地化文件（后加载，覆盖游戏同名翻译）
        if mod_path and os.path.isdir(mod_path):
            self._load_mod_localisation_files(mod_path)

        # 用户自定义语句文件
        if custom_statement_path and os.path.isfile(custom_statement_path):
            self._load_custom_statements(custom_statement_path)

        # GFX精灵文件（界面图标资源映射）
        if hoi4_path and os.path.isdir(hoi4_path):
            self._load_gfx_files(hoi4_path)

    @staticmethod
    def _build_command_dict():
        """
        构建内置PDX命令字典
        包含国策树、事件、效果、触发器、科技等所有常用PDX关键字的翻译
        返回键值对字典：英文PDX关键字 -> 中文翻译
        """
        return {
            # ========== 国策树结构关键字 ==========
            "completion_reward": "完成奖励",
            "prerequisite": "前置国策",
            "mutually_exclusive": "互斥国策",
            "available": "可用条件",
            "available_if_capitulated": "投降后可用",
            "ai_will_do": "AI倾向",
            "bypass": "跳过条件",
            "select_effect": "选择效果",
            "historical_ai": "历史AI",
            "cancel": "取消条件",
            "cancel_if_invalid": "无效时取消",
            "cancelable": "可取消",
            "bypass_if_unavailable": "不可用时跳过",
            "continue_if_invalid": "无效时继续",
            "allow_branch": "允许分支",
            "will_lead_to_war_with": "将对以下国家宣战",
            "search_filters": "搜索标签",
            "hidden_effect": "隐藏效果",

            # ========== 控制流关键字 ==========
            "if": "如果",
            "else": "否则",
            "else_if": "否则如果",
            "limit": "条件满足时",
            "OR": "或",
            "AND": "且",
            "NOT": "非",
            "IF": "如果",
            "ELSE": "否则",
            "ELSE_IF": "否则如果",
            "LIMIT": "条件满足时",

            # ========== 作用域（Scope）关键字 ==========
            "every_other_country": "所有其他国家",
            "every_owned_state": "每个拥有州",
            "every_controlled_state": "每个控制州",
            "random_owned_controlled_state": "随机控制州",
            "random_state": "随机州",
            "capital_scope": "首都范围",
            "owner": "拥有者",
            "controller": "控制者",
            "root": "根",
            "this": "自身",
            "from": "从",

            # ========== 效果（Effect）关键字 ==========
            "add_ideas": "添加理念",
            "remove_ideas": "移除理念",
            "add_political_power": "添加政治点数",
            "add_stability": "添加稳定度",
            "add_war_support": "添加战争支持度",
            "add_research_slot": "添加科研槽",
            "add_tech_bonus": "添加科技加成",
            "add_doctrine_cost_reduction": "添加学说花费削减",
            "army_experience": "陆军经验",
            "navy_experience": "海军经验",
            "air_experience": "空军经验",
            "set_technology": "设置科技",
            "set_country_flag": "设置国家标志",
            "clr_country_flag": "清除国家标志",
            "set_rule": "设置规则",
            "custom_effect_tooltip": "自定义效果提示",
            "show_ideas_tooltip": "显示理念提示",
            "news_event": "新闻事件",
            "country_event": "国家事件",
            "state_event": "州事件",
            "send_equipment": "派遣装备",
            "add_equipment_to_stockpile": "添加装备至库存",
            "add_building_construction": "添加建筑建造",
            "add_extra_state_shared_building_slots": "添加共享建筑槽",
            "send_volunteers": "派遣志愿军",
            "declare_war": "宣战",
            "add_wargoal": "添加战争目标",
            "annex_country": "吞并国家",
            "release_country": "释放国家",
            "create_faction": "创建阵营",
            "join_faction": "加入阵营",
            "leave_faction": "离开阵营",
            "add_timed_idea": "添加限时理念",
            "remove_named_threat": "移除命名威胁",
            "transfer_state": "转移州",
            "set_politics": "设置政治",
            "set_cosmetic_tag": "设置装饰标签",
            "create_country_leader": "创建国家领导人",
            "retire_country_leader": "退休国家领导人",
            "add_country_leader_role": "添加国家领导人角色",
            "promote_leader": "晋升领导人",
            "add_popularity": "添加支持率",
            "add_dynamic_modifier": "添加动态修正器",
            "remove_dynamic_modifier": "移除动态修正器",
            "set_variable": "设置变量",
            "add_to_variable": "增加变量",
            "multiply_variable": "乘以变量",
            "divide_variable": "除以变量",
            "custom_trigger_tooltip": "自定义触发提示",
            "random_list": "随机列表",

            # ========== 触发器（Trigger）关键字 ==========
            "focus": "国策",
            "ideology": "意识形态",
            "tag": "国家标签",
            "has_government": "政府形态",
            "has_idea": "拥有理念",
            "has_country_flag": "拥有国家标志",
            "has_tech": "拥有科技",
            "has_dlc": "拥有DLC",
            "has_war": "处于战争",
            "has_war_with": "与某国处于战争",
            "has_civil_war": "处于内战",
            "is_coastal": "沿海",
            "is_subject": "是附属国",
            "is_in_faction": "处于阵营中",
            "is_major": "是主要国家",
            "is_historical_focus_on": "历史国策开启",

            # ========== 建筑关键字 ==========
            "infrastructure": "基础设施",
            "dockyard": "海军船坞",
            "arms_factory": "军用工厂",
            "industrial_complex": "民用工厂",
            "air_base": "空军基地",
            "naval_base": "海军基地",
            "synthetic_refinery": "合成炼油厂",
            "fort": "要塞",
            "bunker": "地堡",
            "coastal_battery": "海岸炮",
            "radar_station": "雷达站",
            "rocket_site": "火箭发射场",
            "nuclear_reactor": "核反应堆",

            # ========== 州/国家作用域 ==========
            "state": "州",
            "any_owned_state": "任一拥有州",
            "any_controlled_state": "任一控制州",
            "any_other_country": "任一其他国家",
            "any_neighbor_country": "任一邻国",
            "all_owned_state": "所有拥有州",
            "all_controlled_state": "所有控制州",
            "all_neighbor_country": "所有邻国",

            # ========== 变量与数值 ==========
            "num_of_factories": "工厂数量",
            "num_of_controlled_states": "控制州数量",
            "num_of_nukes": "核弹数量",
            "threat": "世界紧张度",
            "date": "日期",

            # ========== 意识形态 ==========
            "fascism": "法西斯主义",
            "communism": "共产主义",
            "democratic": "民主主义",
            "neutrality": "中立主义",

            # ========== 通用参数 ==========
            "factor": "系数",
            "base": "基础值",
            "always": "始终",
            "modifier": "修正器",
            "days": "天数",
            "uses": "使用次数",
            "category": "类别",
            "technology": "科技",
            "ahead_reduction": "提前削减",
            "cost_reduction": "花费削减",
            "bonus": "加成",
            "amount": "数量",
            "type": "类型",
            "target": "目标",
            "template_name": "模板名称",
            "instant_build": "立即建造",
            "level": "等级",
            "size": "大小",
            "include_locked": "包括锁定",

            # ========== 大陆 ==========
            "is_on_continent": "位于大陆",
            "south_america": "南美洲",
            "north_america": "北美洲",
            "europe": "欧洲",
            "asia": "亚洲",
            "africa": "非洲",
            "oceania": "大洋洲",

            # ========== 政治 ==========
            "ruling_party": "执政党",
            "last_election": "上次选举",
            "election_frequency": "选举频率",
            "elections_allowed": "允许选举",
            "can_create_factions": "能创建阵营",
            "can_send_volunteers": "能派遣志愿军",
            "can_use_kamikaze_pilots": "能使用神风飞行员",

            # ========== 突破/专精 ==========
            "add_breakthrough_progress": "添加突破进度",
            "specialization": "专精",
            "value": "数值",
            "specialization_land": "陆军专精",
            "specialization_air": "空军专精",
            "specialization_nuclear": "核专精",
            "add_mastery_bonus": "添加学说精通加成",

            # ========== 海军学说 ==========
            "grand_doctrine": "大法",
            "new_convoy_raiding": "新破交战术",
            "new_base_strike": "新基地打击",
            "new_fleet_in_being": "新存在舰队",

            # ========== 通用字段 ==========
            "name": "名称",
            "tooltip": "提示",
            "localization_key": "本地化键",
            "CHARACTER": "角色",

            # ========== 控制状态 ==========
            "is_fully_controlled_by": "被完全控制",
            "is_owned_by": "被拥有",
            "is_controlled_by": "被控制",
            "is_owned_and_controlled_by": "被拥有和控制",
            "free_building_slots": "空闲建筑槽",

            # ========== 装备与科技类别 ==========
            "building": "建筑",
            "industry": "工业",
            "infantry_weapons": "步兵武器",
            "artillery": "火炮",
            "armor": "装甲",
            "motorized_equipment": "摩托化装备",
            "land_doctrine": "陆军学说",
            "air_doctrine": "空军学说",
            "naval_doctrine": "海军学说",
            "light_fighter": "轻型战斗机",
            "cat_heavy_fighter": "重型战斗机",
            "cat_strategic_bomber": "战略轰炸机",
            "tactical_bomber": "战术轰炸机",
            "naval_bomber": "海军轰炸机",
            "cas_bomber": "近距支援机",
            "ss_tech": "潜艇科技",
            "ca_tech": "重巡洋舰科技",
            "dd_tech": "驱逐舰科技",
            "bb_tech": "战列舰科技",
            "bc_tech": "战列巡洋舰科技",
            "cv_tech": "航母科技",
            "infantry_weapons_research": "步兵武器研究",
            "electronics": "电子学",
            "nuclear": "核物理",
            "rocketry": "火箭学",
            "jet_technology": "喷气技术",
            "special_forces_doctrine": "特种部队学说",
            "motorised_infantry": "摩托化步兵",
            "paratroopers": "伞兵",
            "marines": "海军陆战队",
            "tech_mountaineers": "山地部队",
            "engineering": "工兵",
            "field_hospital": "野战医院",

            # ========== 数组/附属关系 ==========
            "is_in_array": "在数组中",
            "array": "数组",
            "is_subject_of": "是附属国",
            "original_tag": "原始标签",
            "original_research_slots": "原始科研槽",
            "ideology_group": "意识形态组",

            # ========== 政党 ==========
            "add_ruling_party_support": "添加执政党支持",
            "remove_opposition_party": "移除反对党",
            "party_popularity": "政党支持率",

            # ========== 阵营 ==========
            "add_to_faction": "加入阵营",
            "dismantle_faction": "解散阵营",

            # ========== 核弹 ==========
            "add_nuclear_bomb": "添加核弹",

            # ========== 国家统一 ==========
            "set_national_unity": "设置国家统一度",

            # ========== 将领/指挥官 ==========
            "army_leader": "陆军将领",
            "navy_leader": "海军将领",
            "create_field_marshal": "创建元帅",
            "create_corps_commander": "创建军师长",
            "create_naval_commander": "创建海军指挥官",
            "add_trait": "添加特质",
            "remove_trait": "移除特质",
            "add_corps_commander_role": "添加军师长角色",
            "add_field_marshal_role": "添加元帅角色",
            "add_navy_commander_role": "添加海军指挥官角色",
            "sector": "扇区",
            "country_leader": "国家领导人",
            "expire": "过期",
            "traits": "特质",
            "war_industrialist": "战争实业家",
            "ideology_plural": "意识形态复数",
            "fascism_party_long": "法西斯政党全称",
            "no": "否",
            "yes": "是",
        }

    def _load_gfx_files(self, hoi4_path):
        """
        解析 game/interface/*.gfx 文件，建立精灵名称到纹理路径的映射
        GFX文件定义了游戏界面中图标的纹理路径，用于在编辑器中显示对应的图标
        """
        scan_gfx_folder(hoi4_path, self.gfx_map)

    def reload(self, game_localisation_path=None, custom_statement_path=None, hoi4_path=None,
               mod_path=None):
        """
        重新加载本地化文件和gfx映射
        通常在用户更改了HOI4路径、mod路径或翻译文件后调用
        """
        # 清空所有缓存
        self.loc_cache.clear()
        self.gfx_map.clear()

        # 如果提供了新的HOI4路径则更新
        if hoi4_path:
            self.hoi4_path = hoi4_path
        if mod_path is not None:
            self.mod_path = mod_path

        # 重新加载各翻译源
        if game_localisation_path and os.path.isdir(game_localisation_path):
            self._load_localisation_files(game_localisation_path)
        if custom_statement_path and os.path.isfile(custom_statement_path):
            self._load_custom_statements(custom_statement_path)
        if self.hoi4_path and os.path.isdir(self.hoi4_path):
            self._load_gfx_files(self.hoi4_path)
        if self.mod_path and os.path.isdir(self.mod_path):
            self._load_mod_localisation_files(self.mod_path)

    def _load_localisation_files(self, path):
        """
        读取所有 *_l_simp_chinese.yml 文件
        HOI4的简体中文本地化文件，包含游戏内所有文本的翻译
        格式: key:0 "value" 或 key: "value"
        """
        from localization_mgr import load_loc_yml_dir
        if os.path.isdir(path):
            load_loc_yml_dir(path, self.loc_cache)

    def _load_mod_localisation_files(self, mod_path):
        """
        加载 mod 目录的简体中文本地化文件。
        支持 localisation / localization 两种拼写，mod 翻译覆盖游戏同名翻译。
        """
        for sub in ("localisation", "localization"):
            loc_dir = os.path.join(mod_path, sub, "simp_chinese")
            if os.path.isdir(loc_dir):
                self._load_localisation_files(loc_dir)

    def _load_custom_statements(self, path):
        """
        加载 custom_statements.json
        用户自定义语句文件，格式：
        {
          "statements": [
            {"key": "my_command", "cn_name": "我的命令", "node_type": "value", ...}
          ]
        }
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 遍历statements数组，按key存入字典
                for stmt in data.get("statements", []):
                    key = stmt.get("key", "")
                    if key:
                        self.custom_statements[key] = stmt
        except Exception:
            pass  # 忽略JSON解析错误

    def save_custom_statements(self, path):
        """
        保存 custom_statements.json
        将内存中的自定义语句序列化到文件
        """
        data = {
            "version": 1,
            "statements": list(self.custom_statements.values())
        }
        # 确保目标目录存在
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_custom_statement(self, key, cn_name, node_type="value", default_value=None,
                             value_translations=None, description=""):
        """
        添加或更新自定义语句
        Args:
            key: PDX命令键名
            cn_name: 中文名称
            node_type: 节点类型（"value" 或 "block"）
            default_value: 默认值
            value_translations: 值的翻译映射
            description: 描述文本
        """
        from datetime import datetime
        now = datetime.now().isoformat()
        # 保留原有的创建时间，新条目使用当前时间
        existing = self.custom_statements.get(key)
        created_at = existing.get("created_at", now) if existing else now

        self.custom_statements[key] = {
            "key": key,
            "cn_name": cn_name,
            "node_type": node_type,
            "default_value": default_value if default_value is not None else "",
            "value_translations": value_translations if value_translations else {},
            "description": description,
            "created_at": created_at,
            "updated_at": now,
        }

    def remove_custom_statement(self, key):
        """删除自定义语句"""
        self.custom_statements.pop(key, None)

    def translate_key(self, key: str) -> str:
        """
        翻译PDX命令键名到中文
        优先级：自定义语句 > 内置字典 > 本地化缓存 > 词条注册表 > 返回原key
        """
        if key in self.custom_statements:
            return self.custom_statements[key]["cn_name"]
        if key in self.command_dict:
            return self.command_dict[key]
        if key in self.loc_cache:
            return self.loc_cache[key]
        # 词条注册表回退（块/值词条的中文翻译）
        try:
            from term_registry import get_term_registry
            cn = get_term_registry().get_cn(key)
            if cn != key:
                return cn
        except Exception:
            pass
        # 无匹配翻译，返回原始key
        return key

    def translate_value(self, value: str) -> str:
        """
        翻译PDX值到中文
        优先级：自定义语句值翻译 > 本地化缓存 > 返回原值
        """
        # 空值、非字符串、数字、布尔值直接返回
        if not value or not isinstance(value, str):
            return value
        if value.isdigit() or value in ("yes", "no", "true", "false"):
            return value

        # 检查用户自定义语句中是否有该值的翻译
        for stmt in self.custom_statements.values():
            vt = stmt.get("value_translations", {})
            if value in vt:
                return vt[value]

        # 检查游戏本地化缓存
        if value in self.loc_cache:
            return self.loc_cache[value]

        # 无匹配翻译，返回原值
        return value

    def translate_node(self, key: str, value: str = None):
        """
        翻译完整节点，返回 (中文键名, 中文值)
        当value为None时不对值进行翻译
        """
        cn_key = self.translate_key(key)
        cn_val = self.translate_value(value) if value else value
        return cn_key, cn_val

    def search(self, keyword: str) -> list:
        """
        搜索匹配关键字（中英文均可，仅搜索内置词典和自定义语句）
        Returns:
            [{"key": ..., "cn": ..., "source": "builtin"|"custom"}, ...]
        """
        results = []
        seen = set()  # 去重，避免同key出现多次
        kw_lower = keyword.lower()

        # 搜索内置字典
        for key, cn in self.command_dict.items():
            if kw_lower in key.lower() or kw_lower in cn.lower():
                if key not in seen:
                    results.append({"key": key, "cn": cn, "source": "builtin"})
                    seen.add(key)

        # 搜索自定义语句
        for key, stmt in self.custom_statements.items():
            cn = stmt.get("cn_name", "")
            if kw_lower in key.lower() or kw_lower in cn.lower():
                if key not in seen:
                    results.append({"key": key, "cn": cn, "source": "custom"})
                    seen.add(key)

        return results

    def search_with_terms(self, keyword: str, term_type: str = "", limit=300) -> list:
        """
        搜索语句（词条）+ 模板，合并返回。

        词条数据源：translations 文件夹内的词条文件（effect_terms.json/custom_terms.json），
        与翻译文件夹内文件合并通用；模板来源：templates 文件夹（含效果器/触发器）。

        Args:
            term_type: 节点类型筛选，""=全部，"block"=块，"value"=值

        Returns:
            [
              {"key": ..., "cn": ..., "source": "builtin"|"custom"|"term", "type": ..., "tags": [...]},
              {"key": ..., "cn": ..., "source": "template", "type": ..., "filepath": ...}
            ]
        """
        results = []
        seen = set()
        kw = keyword.strip()

        # 1) 原有语句搜索（内置 + 自定义）
        for r in self.search(kw):
            seen.add(r["key"])
            results.append(r)

        # 2) 词条搜索（translations 词条文件）
        try:
            from term_registry import get_term_registry
            registry = get_term_registry()
            for term in registry.search(kw, node_type=term_type or None, limit=limit):
                key = term.get("key", "")
                if key in seen:
                    continue
                seen.add(key)
                results.append({
                    "key": key,
                    "cn": term.get("cn", key),
                    "source": "term",
                    "type": term.get("node_type", "value"),
                    "tags": term.get("tags", []),
                })
        except Exception:
            pass

        # 3) 模板搜索（templates 文件夹，按命名区分类型）
        try:
            from template_scheduler import get_template_scheduler, TEMPLATE_TYPES
            scheduler = get_template_scheduler()
            template_type = ""
            if term_type in ("effect", "trigger"):
                template_type = term_type
            for tpl in scheduler.search_templates(kw, template_type=template_type):
                key = tpl["name"]
                if key in seen:
                    continue
                seen.add(key)
                results.append({
                    "key": key,
                    "cn": tpl.get("type_label", "模板"),
                    "source": "template",
                    "type": tpl.get("type", "custom"),
                    "filepath": tpl.get("filepath", ""),
                })
        except Exception:
            pass

        return results

    def load_translations_folder(self) -> dict:
        """
        扫描 translations 文件夹，自动加载其中的翻译文件。
        将翻译文件拖入文件夹后调用此方法即可生效。

        Returns:
            加载结果 {"files_loaded": N, "keys_added": N, "errors": [...]}
        """
        from translation_loader import TranslationLoader
        loader = TranslationLoader(self)
        return loader.scan_and_load()


# 全局默认翻译器单例
_default_translator = None


def get_translator(game_localisation_path=None, custom_statement_path=None, hoi4_path=None,
                   mod_path=None):
    """
    获取单例翻译器
    首次调用时创建实例并自动扫描 translations 文件夹
    """
    global _default_translator
    if _default_translator is None:
        _default_translator = GuiTranslator(game_localisation_path, custom_statement_path,
                                            hoi4_path, mod_path)
        # 启动时自动扫描 translations 文件夹
        _default_translator.load_translations_folder()
    return _default_translator


def get_translations_dir() -> str:
    """获取翻译文件存放目录路径"""
    from translation_loader import get_translations_dir
    return get_translations_dir()

"""
固定字段识别器模块

本模块用于识别 PDX（Paradox Interactive）数据结构中的固定字段，
例如 focus_id、ideas/country 结构体名称等。
设计为可扩展架构，支持通过注册自定义识别规则来匹配各种语义块。

主要类：
    FieldPattern        -- 单个字段的识别模式
    FixedFieldRecognizer -- 固定字段识别器（组合多个 FieldPattern）

便捷函数：
    get_default_recognizer() -- 获取带有默认识别规则的识别器实例
"""

from typing import Dict, Optional, Callable


class FieldPattern:
    """
    单个字段的识别模式

    封装了一个识别规则，支持多种匹配策略：
        - "key"         : 精确匹配键名
        - "key_value"   : 匹配键名并提取对应的值
        - "block_inside": 匹配块内部出现的键
        - "custom"      : 使用自定义回调函数进行匹配

    Attributes:
        name        : 模式名称（唯一标识符）
        pattern_type: 匹配类型（"key" / "key_value" / "block_inside" / "custom"）
        matcher     : 匹配器（字符串精确匹配 / 回调函数 / 键名列表）
        description : 模式描述（用于输出和日志）
    """

    def __init__(self, name: str, pattern_type: str, matcher: str or Callable, description: str = ""):
        """
        初始化字段识别模式

        Args:
            name        : 模式名称，如 "focus_id"
            pattern_type: 匹配类型标识
            matcher     : 匹配器，可以是字符串（精确匹配）、可调用对象（自定义逻辑）、
                          或列表（用于 block_inside 类型的集合匹配）
            description : 可读的描述文本
        """
        self.name = name
        self.pattern_type = pattern_type  # "key" / "key_value" / "block_inside" / "custom"
        self.matcher = matcher
        self.description = description

    def test(self, key: str = "", value: str = "", parent_key: str = "", context: dict = None) -> Optional[dict]:
        """
        测试当前键值对是否匹配此模式

        根据 pattern_type 使用不同的匹配策略：
            - key         : 检查 key 是否等于 matcher
            - key_value   : 检查 key 是否等于 matcher，返回 value
            - block_inside: 检查 key 是否在 matcher 列表中
            - custom      : 调用 matcher 回调函数

        Args:
            key       : 当前字段的键名
            value     : 当前字段的值（字符串形式）
            parent_key: 父级节点的键名（用于上下文判断）
            context   : 补充的上下文信息字典

        Returns:
            匹配成功返回 dict（含 "value"、"parent_key" 等字段），否则返回 None
        """
        if self.pattern_type == "key":
            # key 模式：精确匹配键名
            if isinstance(self.matcher, str):
                return {"value": self.matcher} if key == self.matcher else None
            elif callable(self.matcher):
                return self.matcher(key, value, parent_key, context)
        elif self.pattern_type == "key_value":
            # key_value 模式：匹配键名的同时记录对应值
            if isinstance(self.matcher, str):
                return {"value": value} if key == self.matcher else None
            elif callable(self.matcher):
                return self.matcher(key, value, parent_key, context)
        elif self.pattern_type == "block_inside":
            # block_inside 模式：检查键是否出现在指定集合中
            if key in self.matcher:
                return {"parent_key": key, "value": value}
        elif self.pattern_type == "custom":
            # custom 模式：完全委托给回调函数
            if callable(self.matcher):
                return self.matcher(key, value, parent_key, context)
        return None


class FixedFieldRecognizer:
    """
    固定字段识别器

    管理一组 FieldPattern 实例，对外提供统一的固定字段查询接口。
    支持模式注册、移除、查询，并维护一个键值寄存器用于跨节点的状态存储。

    典型用法:
        recognizer = get_default_recognizer()
        result = recognizer.is_fixed_field("focus", "USA_war_plan_red")
        if result:
            print(f"识别到: {result['type']} = {result['value']}")

     Attributes:
        patterns       : 已注册的模式字典（名称 -> FieldPattern）
    """

    def __init__(self):
        """初始化识别器，创建空的模式字典"""
        self.patterns: Dict[str, FieldPattern] = {}  # 名称 -> 模式实例的映射

    def register_pattern(self, pattern: FieldPattern):
        """
        注册一个识别模式

        Args:
            pattern: 要注册的 FieldPattern 实例

        Note:
            如果已存在同名的模式，将被覆盖
        """
        self.patterns[pattern.name] = pattern

    def is_fixed_field(self, key: str, value: str = "", parent_key: str = "",
                       context: dict = None) -> Optional[dict]:
        """
        判断给定的 key-value 对是否为固定字段匹配

        遍历所有已注册的模式，返回第一个匹配的结果。

        Args:
            key       : 字段键名
            value     : 字段值（默认为空字符串）
            parent_key: 父级键名（默认为空字符串）
            context   : 附加上下文字典

        Returns:
            匹配成功返回 {"type"       : 模式名称,
                          "value"      : 匹配值,
                          "description": 模式描述,
                          "parent_key" : 父级键名}
            无匹配则返回 None
        """
        for pattern in self.patterns.values():
            result = pattern.test(key, value, parent_key, context)
            if result is not None:
                return {
                    "type": pattern.name,
                    "value": result.get("value", value),
                    "description": pattern.description,
                    "parent_key": result.get("parent_key", parent_key),
                }
        return None


# ========================================
# 内置识别模式的工厂函数
# 以下函数创建 HOI4 中常见的固定字段识别模式
# ========================================

def create_focus_id_pattern() -> FieldPattern:
    """
    创建 focus_id 识别模式

    匹配 key == "focus" 的键值对，用于识别国策文件中对其他国策的 ID 引用。
    例如：`focus = USA_war_plan_red`

    Returns:
        配置好的 FieldPattern 实例
    """
    return FieldPattern(
        name="focus_id",
        pattern_type="key_value",
        matcher="focus",
        description="国策ID引用，在ideas结构体中的country块内"
    )


def create_focus_block_id_pattern() -> FieldPattern:
    """
    创建块级 focus ID 识别模式

    匹配以 "focus_" 开头的键，且父键为 "ideas" 或 "country" 的情况。
    用于识别如 `.focus_xxx = { ... }` 中的结构体名称。
    例如：`focus_USA_war_plan_red = { ... }`

    Returns:
        配置好的 FieldPattern 实例
    """
    def match(key, value, parent_key, context):
        """自定义匹配逻辑：检查键前缀和父级上下文"""
        if key.startswith("focus_") and parent_key in ("ideas", "country"):
            return {"key": key, "value": value}
        return None

    return FieldPattern(
        name="focus_block_id",
        pattern_type="custom",
        matcher=match,
        description="ideas/country内的focus_xxx结构体"
    )


def create_idea_slot_pattern() -> FieldPattern:
    """
    创建理念槽位识别模式

    匹配在 ideas 块内部、不以 "_" 开头的键，用于识别理念（idea）的名称。
    例如在 ideas = { ... } 内：`my_idea_name = { ... }`

    Returns:
        配置好的 FieldPattern 实例
    """
    def match(key, value, parent_key, context):
        """自定义匹配逻辑：检查父键为 ideas 且键名不以 _ 开头"""
        if parent_key == "ideas" and not key.startswith("_"):
            return {"key": key, "value": "idea_name"}
        return None

    return FieldPattern(
        name="idea_slot",
        pattern_type="custom",
        matcher=match,
        description="ideas块中的理念槽位名称"
    )


def create_country_leader_pattern() -> FieldPattern:
    """
    创建国家领导人识别模式

    匹配在 country_leader 块内部的 "name" 字段，用于识别领导人名称定义。
    例如在 country_leader = { ... } 内：`name = "John Doe"`

    Returns:
        配置好的 FieldPattern 实例
    """
    def match(key, value, parent_key, context):
        """自定义匹配逻辑：检查父键为 country_leader 且当前键为 name"""
        if parent_key == "country_leader":
            if key == "name":
                return {"key": key, "value": value}
        return None

    return FieldPattern(
        name="country_leader_field",
        pattern_type="custom",
        matcher=match,
        description="country_leader字段"
    )


# ========================================
# 便捷函数：获取默认配置的识别器
# ========================================

def get_default_recognizer() -> FixedFieldRecognizer:
    """
    获取带有默认识别规则的识别器实例

    自动注册以下内置模式：
        - focus_id          : 国策 ID 引用
        - focus_block_id    : ideas/country 内的 focus_xxx 结构体
        - idea_slot         : ideas 块中的理念槽位名称
        - country_leader_field : country_leader 内的字段

    Returns:
        已完成默认规则注册的 FixedFieldRecognizer 实例
    """
    recognizer = FixedFieldRecognizer()
    recognizer.register_pattern(create_focus_id_pattern())
    recognizer.register_pattern(create_focus_block_id_pattern())
    recognizer.register_pattern(create_idea_slot_pattern())
    recognizer.register_pattern(create_country_leader_pattern())
    return recognizer

"""AI 效果提示词生成与回填解析模块

基于效果器/触发器词条生成带格式的提示词文本，
用户可将提示词复制到其他 AI（如 ChatGPT/Gemini/DeepSeek）进行创作，
AI 回复遵循约定的输出格式后，由本模块解析并自动回填到程序中。

输出格式约定（提示词中会明确要求 AI 严格遵守）：
    国策块标记:    [国策块: 新国策id]
    国策块结束:    [国策块结束]
    效果块标记:    [效果块: 目标国策id或'当前']
    效果块结束:    [效果块结束]
    触发块标记:    [触发块: 目标块名或'当前']
    触发块结束:    [触发块结束]

回填时程序自动解析标记块内容，将效果/触发词条填入树编辑器对应块。
"""

import re

# ---- 输出格式标记 ----
MARK_START_FOCUS = "[国策块:"
MARK_END_FOCUS = "[国策块结束]"
MARK_START_EFFECT = "[效果块:"
MARK_END_EFFECT = "[效果块结束]"
MARK_START_TRIGGER = "[触发块:"
MARK_END_TRIGGER = "[触发块结束]"

ALL_MARKS = (
    (MARK_START_FOCUS, MARK_END_FOCUS),
    (MARK_START_EFFECT, MARK_END_EFFECT),
    (MARK_START_TRIGGER, MARK_END_TRIGGER),
)


def build_prompt(context=None, scope="当前文件", node_type="", term_registry=None,
                 include_terms_limit=120):
    """生成带格式的 AI 效果提示词文本。

    Args:
        context (str): 上下文描述（当前文件/国策树/项目信息等）
        scope (str): 提示词应用范围描述
        node_type (str): 词条节点类型筛选，""=全部，"block"=块，"value"=值
        term_registry (TermRegistry): 词条注册表实例
        include_terms_limit (int): 提示词中包含的词条数量上限

    Returns:
        str: 完整提示词文本
    """
    registry = term_registry
    if registry is None:
        from term_registry import get_term_registry
        registry = get_term_registry()

    type_desc = {
        "": "块与值",
        "block": "块",
        "value": "值",
    }.get(node_type, "块与值")

    # 收集词条清单
    terms = registry.search("", node_type=node_type or None,
                            limit=include_terms_limit)
    lines = []
    for term in terms:
        key = term.get("key", "")
        cn = term.get("cn", "")
        tname = "块" if term.get("node_type") == "block" else "值"
        tags = "、".join(term.get("tags", []))
        lines.append(f"- {key}　{cn}（{tname} / {tags}）")

    terms_block = "\n".join(lines) if lines else "（无可用词条）"

    prompt = f"""# 角色
你是《钢铁雄心4》（Hearts of Iron IV）的 MOD 脚本专家，精通 PDX 脚本语言。
请根据下面的要求创作 {type_desc} 脚本，并严格遵守输出格式。

# 上下文
{scope}
{context}

# 可用词条参考（按需选用，命令名必须与词条一致）
{terms_block}

# 输出格式（必须严格遵守，不要输出其他内容）
- 新建国策时使用：
{MARK_START_FOCUS} 新国策id]
<国策 PDX 代码，含 id/icon/x/y/cost/completion_reward 等>
{MARK_END_FOCUS}

- 为国策/事件/决议添加效果时使用：
{MARK_START_EFFECT} 目标国策id]（不确定时写"当前"）
<效果 PDX 代码，如 add_political_power = 100>
{MARK_END_EFFECT}

- 为国策/事件/决议添加条件时使用：
{MARK_START_TRIGGER} 目标块名]（如 available，不确定时写"当前"）
<触发器 PDX 代码，如 has_war_with = GER>
{MARK_END_TRIGGER}

# 注意
1. 只能使用上面词条中的命令名，不要编造不存在的命令
2. 词条为"块"的命令用于包含子内容（key = { ... }），词条为"值"的命令直接赋值（key = value）
3. 代码中不要写注释，不要解释
"""
    return prompt


def parse_ai_reply(text):
    """解析 AI 回复，提取标记块内容。

    Args:
        text (str): AI 回复文本

    Returns:
        list[dict]: 每个元素含
            - kind: "focus" / "effect" / "trigger"
            - target: 标记中的目标（国策id/块名/当前）
            - content: 块内 PDX 代码文本
            - error: 解析错误信息（若有）
    """
    blocks = []
    for start_mark, end_mark in ALL_MARKS:
        pattern = re.escape(start_mark) + r"\s*([^\n\]]*)" + r"\]?\s*\n?" + \
                  r"(.*?)" + re.escape(end_mark)
        for m in re.finditer(pattern, text, re.S):
            target = m.group(1).strip()
            content = m.group(2).strip()
            kind = "focus" if start_mark == MARK_START_FOCUS else (
                "effect" if start_mark == MARK_START_EFFECT else "trigger")
            blocks.append({
                "kind": kind,
                "target": target or "当前",
                "content": content,
                "error": "",
            })

    # 若没有匹配到任何标记块，尝试整体作为效果块解析（宽松模式）
    if not blocks and text.strip():
        blocks.append({
            "kind": "effect",
            "target": "当前",
            "content": text.strip(),
            "error": "",
        })
    return blocks


def build_prompt_for_file(file_path, node_type="", registry=None):
    """为当前文件生成提示词（附带文件信息上下文）。

    Args:
        file_path (str): 当前打开的国策/内容文件路径
        node_type (str): 词条节点类型筛选（""=全部，"block"=块，"value"=值）
        registry (TermRegistry): 词条注册表

    Returns:
        str: 提示词文本
    """
    import os
    context_lines = [f"当前文件: {file_path}"]
    if file_path and os.path.isfile(file_path):
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
            # 提取国策树 id 与国策 id 清单
            tree_ids = re.findall(r'^\s*id\s*=\s*([^\s}]+)', content, re.M)
            focus_ids = re.findall(
                r'focus\s*=\s*\{\s*\n\s*id\s*=\s*([^\s}]+)', content)
            if tree_ids:
                context_lines.append(f"国策树ID: {tree_ids[0]}")
            if focus_ids:
                context_lines.append(
                    f"现有国策({len(focus_ids)}): {', '.join(focus_ids[:30])}")
        except Exception:
            pass
    return build_prompt(context="\n".join(context_lines), scope="当前文件",
                        node_type=node_type, term_registry=registry)


def build_prompt_for_project(mod_path, node_type="", registry=None):
    """为整个项目生成提示词（扫描 mod 各内容目录）。

    Args:
        mod_path (str): mod 根目录
        node_type (str): 词条节点类型筛选（""=全部，"block"=块，"value"=值）
        registry (TermRegistry): 词条注册表

    Returns:
        str: 提示词文本
    """
    import os
    content_dirs = [
        ("common/national_focus", "国策树"),
        ("events", "事件"),
        ("common/decisions", "决议"),
        ("common/ideas", "理念"),
        ("common/technologies", "科技"),
        ("common/characters", "角色"),
        ("localisation", "本地化"),
    ]
    context_lines = [f"项目目录: {mod_path}"]
    for rel, label in content_dirs:
        d = os.path.join(mod_path, rel)
        if os.path.isdir(d):
            files = [f for f in os.listdir(d)
                     if os.path.isfile(os.path.join(d, f)) and f.endswith(".txt")]
            if files:
                context_lines.append(f"{label}({len(files)}): {', '.join(files[:20])}")
    return build_prompt(context="\n".join(context_lines), scope="整个项目",
                        node_type=node_type, term_registry=registry)

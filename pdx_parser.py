import re


def parse_pdx_script(text):
    """将 Paradox 游戏引擎 PDX 脚本解析为嵌套的 Python 字典/列表结构。

    这是一个递归下降解析器（Recursive Descent Parser），将类似 JSON/
    XML 的自定义格式文本转换为 Python 原生数据结构。支持：
    - 键值对：`key = value`
    - 嵌套块：`key = { ... }`
    - 重复键自动转为列表
    - 以 `#` 开头的注释行

    参数:
        text: 原始 PDX 脚本文本字符串
    返回:
        嵌套的 dict/list 结构
    """
    # 移除注释（# 开头到行尾的内容）
    text = re.sub(r'#.*', '', text)
    # 分词：匹配符号、等号、大括号和字符串/关键字
    # 识别: { } = "字符串" 标识符(字母数字点连字符)
    # 同时记录每个 token 的行号（1-indexed）
    raw_tokens = []
    for m in re.finditer(r'\{|\}|=|"[^"]*"|[\w\.\-]+', text):
        line_no = text[:m.start()].count('\n') + 1
        raw_tokens.append((m.group(0), line_no))

    def parse_block(iterator):
        """递归解析一个代码块（大括号包裹的内容）。

        遍历 token 迭代器，构建当前块的字典表示。
        遇到 '}' 时返回当前构建的对象，表示块结束。

        参数:
            iterator: (token, line_number) 迭代器
        返回:
             当前块解析后的字典对象
        """
        obj = {}
        key = None  # 当前待赋值的键名（读到 = 左侧后暂存）
        key_line = 0  # 键名所在的行号
        for token, line_no in iterator:
            if token == '}':
                break  # 块结束，返回解析结果
            elif token == '=':
                continue  # 等号是分隔符，跳过
            elif token == '{':
                # 遇到子块：递归解析大括号内容
                value = parse_block(iterator)
                if key:
                    # 如果有键名，则作为键值对
                    if key in obj:
                        # 键已存在：将单值转为列表，追加新值
                        if isinstance(obj[key], list):
                            obj[key].append(value)
                        else:
                            obj[key] = [obj[key], value]
                    else:
                        obj[key] = value
                    key = None  # 已赋值，清除键名
                else:
                    # 无键名的匿名块：放入 'list' 键中
                    if 'list' not in obj:
                        obj['list'] = []
                    obj['list'].append(value)
            else:
                # 普通 token：可能是键名或值
                if key is None:
                    # 无待赋值键名 -> 当前 token 是新的键名
                    key = token
                    key_line = line_no
                else:
                    # 有待赋值键名 -> 检查是否在同一行
                    # 如果 token 和 key 不在同一行，说明是空值
                    if line_no != key_line and token not in ('{', '}'):
                        # 空值：清空 key，当前 token 作为新 key
                        obj[key] = ""
                        key = token
                        key_line = line_no
                        continue
                    # 当前 token 是值
                    value = token.strip('"')  # 去除可能的外层引号
                    if key in obj:
                        # 重复键：转为列表
                        if isinstance(obj[key], list):
                            obj[key].append(value)
                        else:
                            obj[key] = [obj[key], value]
                    else:
                        obj[key] = value
                    key = None  # 已赋值，清除键名
        # 处理结尾的未赋值 key
        if key is not None:
            obj[key] = ""
        return obj

    # 从 token 迭代器开始解析顶层块
    return parse_block(iter(raw_tokens))

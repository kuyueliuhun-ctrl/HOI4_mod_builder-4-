"""国家定义识别 —— mod 中"设置/重定义"的国家标签

规则：只要 mod 中定义了某国家（common/country_tags 赋值、common/countries 裸标签文件、
或 history/countries 文件名前缀），则视为该国家已被 mod 接管，
读取原版（游戏目录）内容时应屏蔽该国家的原版数据（军队/编制/科技/顾问等）。
"""

import os
import re


def find_defined_countries(mod_path):
    """扫描 mod 目录，返回 mod 定义/重定义的国家标签集合（大写）。

    数据源：
    - common/country_tags/*.txt：顶层 `TAG = "countries/xxx.txt"` 赋值
    - common/countries/*.txt：裸国家标签文件名（如 14K.txt -> 14K）
    - history/countries/*.txt：文件名前缀国家标签（如 "CHL - Chile.txt" -> CHL）
    """
    tags = set()
    if not mod_path or not os.path.isdir(mod_path):
        return tags

    # 1) common/country_tags：TAG = "..." 赋值
    d = os.path.join(mod_path, "common", "country_tags")
    if os.path.isdir(d):
        pat = re.compile(r'^\s*([A-Za-z0-9]{1,4})\s*=\s*"', re.IGNORECASE)
        for fn in os.listdir(d):
            if not fn.lower().endswith(".txt"):
                continue
            try:
                with open(os.path.join(d, fn), "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    for line in f:
                        m = pat.match(line)
                        if m:
                            tags.add(m.group(1).upper())
            except Exception:
                continue

    # 2) common/countries：裸国家标签文件名
    d = os.path.join(mod_path, "common", "countries")
    if os.path.isdir(d):
        for fn in os.listdir(d):
            name, ext = os.path.splitext(fn)
            if ext.lower() not in (".txt", ""):
                continue
            tag = name.strip().upper()
            if re.fullmatch(r"[A-Z0-9]{1,4}", tag):
                tags.add(tag)

    # 3) history/countries：文件名前缀国家标签
    d = os.path.join(mod_path, "history", "countries")
    if os.path.isdir(d):
        for fn in os.listdir(d):
            if not fn.lower().endswith(".txt"):
                continue
            m = re.match(r"^([A-Z]{2,4})(?=[\s_\-])", fn)
            if m:
                tags.add(m.group(1).upper())

    return tags


def is_defined_country(mod_path, tag):
    """判断某国家标签是否已被 mod 定义/接管（大写比较）。"""
    if not tag:
        return False
    return tag.upper() in find_defined_countries(mod_path)


def _file_country_tag(fp):
    """从文件路径推断其对应的国家标签（尽量复用文件名规则）。

    Returns:
        str: 大写国家标签；无法判断返回 ""
    """
    base = os.path.basename(fp or "")
    stem = os.path.splitext(base)[0]
    # 裸国家标签文件名（如 CHL.txt）
    if re.fullmatch(r"[A-Z0-9]{2,4}", stem):
        return stem.upper()
    # 常见前缀/后缀规则：TAG_xxx / xxx_TAG / TAG - name / TAG_name
    for pat in (r"^([A-Z]{2,4})(?=[_\-\s])", r"_([A-Z]{2,4})$"):
        m = re.search(pat, stem)
        if m:
            return m.group(1).upper()
    return ""


def filter_vanilla_files(mod_path, game_path, subpaths, ext=".txt"):
    """列出游戏目录下指定子路径的文件，但跳过属于 mod 已定义国家的原版文件。

    Args:
        mod_path: mod 目录（用于判定定义国家）
        game_path: 游戏根目录
        subpaths: 相对子路径列表（如 ["common/characters", "history/units"]）
        ext: 扩展名过滤（默认 .txt）
    Returns:
        list[str]: 过滤后的原版文件完整路径
    """
    if not game_path or not os.path.isdir(game_path):
        return []
    defined = find_defined_countries(mod_path)
    result = []
    for rel in subpaths:
        d = os.path.join(game_path, rel.replace("/", os.sep))
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if not fn.lower().endswith(ext):
                continue
            tag = _file_country_tag(fn)
            if tag and tag in defined:
                continue  # 该国家已被 mod 接管，屏蔽原版文件
            result.append(os.path.join(d, fn))
    return result

"""游戏数据字典与 mod 文件校验

构建自游戏目录的合法引用字典（traits / ideologies / modifiers / equipment /
GFX 精灵 / 科技 / 国策 / 理念），并扫描 mod 文件中的引用，报告未知引用。

用法（offscreen/CLI）：
    from game_data import build_dictionary, validate_file
    d = build_dictionary(r"E:\\...\\Hearts of Iron IV")
    issues = validate_file(d, file_path, content_type="character")
"""

import os
import re


# ---------- 字典构建 ----------

def _read_txt_lines(root, rel_subdir, ext=".txt"):
    """读取目录下所有文本文件并拼接（用于正则提取）。"""
    buf = []
    d = os.path.join(root, rel_subdir.replace("/", os.sep))
    if not os.path.isdir(d):
        return buf
    for dirpath, _dirs, files in os.walk(d):
        for fn in files:
            if not fn.lower().endswith(ext):
                continue
            try:
                with open(os.path.join(dirpath, fn), "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    buf.append(f.read())
            except Exception:
                continue
    return buf


def _collect_block_keys(text, min_letters=1):
    """收集 `key = {` 顶层块键名（首列缩进后，正则宽松匹配）。"""
    return set(re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{", text, re.M))


def _collect_gfx_names(text):
    """收集 .gfx 文件中的 spriteType name。"""
    return set(re.findall(r'name\s*=\s*"?(GFX_[A-Za-z0-9_]+)"?', text))


def build_dictionary(hoi4_path):
    """构建游戏数据字典。

    Returns:
        dict: {
            "traits": set[str],      # 领袖/将领/科学家特质
            "ideologies": set[str],  # 意识形态类型（子意识形态）
            "modifiers": set[str],   # modifier 键名（ideas/effect 中常见）
            "equipment": set[str],   # 装备 ID
            "techs": set[str],       # 科技 ID
            "focuses": set[str],     # 国策 ID
            "ideas": set[str],       # 理念/民族精神 ID
            "gfx": set[str],         # GFX 精灵名
        }
    """
    d = {
        "traits": set(), "ideologies": set(), "modifiers": set(),
        "equipment": set(), "techs": set(), "focuses": set(),
        "ideas": set(), "gfx": set(),
    }
    if not hoi4_path or not os.path.isdir(hoi4_path):
        return d

    # traits
    for sub in ("common/country_leader", "common/unit_leader",
                "common/scientist_traits"):
        for txt in _read_txt_lines(hoi4_path, sub):
            d["traits"] |= _collect_block_keys(txt)

    # ideologies（子意识形态，含 types 块内缩进两层的键）
    for txt in _read_txt_lines(hoi4_path, "common/ideologies"):
        # 00_ideologies.txt 内 `group = { type = {...} }` 用 tab 缩进
        for m in re.finditer(r"^\t\t([a-z_0-9]+)\s*=\s*\{", txt, re.M):
            d["ideologies"].add(m.group(1))
        d["ideologies"] |= _collect_block_keys(txt)

    # modifiers：从 ideas/effects/defines 中收集 `key = 数值` 的键名
    mod_text = []
    for sub in ("common/ideas", "common/national_focus",
                "common/dynamic_modifiers", "common/modifiers"):
        mod_text += _read_txt_lines(hoi4_path, sub)
    for txt in mod_text:
        for m in re.finditer(r"^\t{1,2}([a-z_0-9]+)\s*=\s*(-?[\d\.]+|[a-z_]+)\s*$",
                             txt, re.M):
            d["modifiers"].add(m.group(1))

    # equipment
    for txt in _read_txt_lines(hoi4_path, "common/units/equipment"):
        d["equipment"] |= _collect_block_keys(txt)

    # techs
    for txt in _read_txt_lines(hoi4_path, "common/technologies"):
        d["techs"] |= _collect_block_keys(txt)

    # focuses
    for txt in _read_txt_lines(hoi4_path, "common/national_focus"):
        d["focuses"] |= _collect_block_keys(txt)

    # ideas（含 ideas = { country = { TAG = {...} } } 内层）
    for txt in mod_text:
        d["ideas"] |= _collect_block_keys(txt)

    # gfx
    for txt in _read_txt_lines(hoi4_path, "interface", ext=".gfx"):
        d["gfx"] |= _collect_gfx_names(txt)

    return d


# ---------- 校验 ----------

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _tokens_in_traits(text):
    """提取 traits = { ... } 内的特质名。"""
    return [t for t in re.findall(r"traits\s*=\s*\{([^{}]*)\}", text)
            for t in t.split() if _IDENT.fullmatch(t)]


def _tokens_in_ideology(text):
    """提取 country_leader = { ideology = X } 的 X。"""
    return re.findall(r"ideology\s*=\s*([A-Za-z_][A-Za-z0-9_]*)", text)


def _tokens_in_picture(text):
    """提取 picture = GFX_xxx 的精灵名。"""
    return re.findall(r"picture\s*=\s*(GFX_[A-Za-z0-9_]+)", text)


def _tokens_in_icon(text):
    """提取 icon = GFX_xxx / large = GFX_xxx / small = GFX_xxx 的精灵名。"""
    out = []
    for m in re.finditer(r"(?:icon|large|small)\s*=\s*(GFX_[A-Za-z0-9_]+)", text):
        out.append(m.group(1))
    return out


def _tokens_in_ideas(text):
    """提取 add_ideas = X / remove_ideas = X（引用型）。

    idea_token 是角色/顾问的标识符而非引用，不在此检查（避免误报）。
    """
    return re.findall(r"(?:add_ideas|remove_ideas)\s*=\s*([A-Za-z_][A-Za-z0-9_]*)",
                      text)


def validate_file(dictionary, file_path, content_type="", local_ideas=None):
    """校验单个 mod 文件的未知引用。

    Args:
        dictionary: build_dictionary() 返回值
        file_path: 待校验文件
        content_type: 内容类型（保留扩展用）
        local_ideas: 本 mod 内已定义的 idea/角色 token 集合（避免误报）

    Returns:
        list[str]: 问题描述列表（空 = 无问题）
    """
    issues = []
    if not dictionary:
        return issues
    try:
        with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            text = f.read()
    except Exception as e:
        return [f"无法读取文件: {e}"]

    known_ideas = set(dictionary.get("ideas", ()))
    if local_ideas:
        known_ideas |= set(local_ideas)

    # traits
    for t in set(_tokens_in_traits(text)):
        if t not in dictionary["traits"]:
            issues.append(f"未知特质: {t}")
    # ideology
    for t in set(_tokens_in_ideology(text)):
        if t not in dictionary["ideologies"]:
            issues.append(f"未知意识形态: {t}")
    # picture/icon GFX
    for t in set(_tokens_in_picture(text) + _tokens_in_icon(text)):
        if t not in dictionary["gfx"]:
            issues.append(f"未知GFX: {t}")
    # ideas 引用
    for t in set(_tokens_in_ideas(text)):
        if t not in known_ideas:
            issues.append(f"未知理念引用: {t}")

    return issues


def collect_local_ideas(mod_path):
    """收集 mod 内定义的 idea/角色 token（common/ideas、common/characters）。"""
    local = set()
    if not mod_path or not os.path.isdir(mod_path):
        return local
    for sub in ("common/ideas", "common/characters"):
        d = os.path.join(mod_path, sub.replace("/", os.sep))
        if not os.path.isdir(d):
            continue
        for root, _dirs, files in os.walk(d):
            for fn in files:
                if not fn.lower().endswith(".txt"):
                    continue
                try:
                    text = open(os.path.join(root, fn), "r",
                                encoding="utf-8-sig",
                                errors="ignore").read()
                except Exception:
                    continue
                for key in _collect_block_keys(text):
                    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{2,}", key):
                        local.add(key)
    return local


def find_duplicate_ids(mod_path):
    """扫描 mod 内重复的实体 ID（角色/理念/国策/装备/科技等）。

    复用 workbench 的实体提取逻辑（能正确识别包装块下的实体键），
    只统计实体级 ID，避免把 allowed/modifier/traits 等字段名误判。
    """
    try:
        from content_types import CONTENT_TYPES
        from entity_scanner import EntityScanner as WorkbenchDock
    except Exception:
        return {}
    if not mod_path or not os.path.isdir(mod_path):
        return {}
    seen = {}
    # 各内容类型扫描目录
    type_dirs = {}
    for key, _name, _icon, folders, _tpl, ext in CONTENT_TYPES:
        if key in ("generic", "gui", "gui_edit", "state", "country_history"):
            continue
        for f in folders:
            if f == ".":
                continue
            exts = [ext] if isinstance(ext, str) else list(ext or [])
            type_dirs.setdefault(key, (f, tuple(exts)))
    for key, (rel, exts) in type_dirs.items():
        base = os.path.join(mod_path, rel.replace("/", os.sep))
        if not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            for fn in files:
                if not fn.lower().endswith(exts):
                    continue
                fp = os.path.join(root, fn)
                rp = os.path.relpath(fp, mod_path).replace(os.sep, "/")
                try:
                    content = open(fp, "r", encoding="utf-8-sig",
                                   errors="ignore").read()
                except Exception:
                    continue
                try:
                    ents = WorkbenchDock._extract_entities(key, content)
                except Exception:
                    ents = []
                for e in ents:
                    nm = e.get("name") or e.get("key")
                    if nm and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{2,}", nm):
                        seen.setdefault(nm, []).append(rp)
    return {k: sorted(set(v)) for k, v in seen.items() if len(set(v)) > 1}


def validate_directory(dictionary, mod_path):
    """校验 mod 目录下所有 .txt 文件（自动并入 mod 本地定义）。

    Returns:
        dict: {相对路径: [问题...]}
    """
    results = {}
    if not mod_path or not os.path.isdir(mod_path):
        return results
    local_ideas = collect_local_ideas(mod_path)
    for root, _dirs, files in os.walk(mod_path):
        for fn in files:
            if not fn.lower().endswith(".txt"):
                continue
            fp = os.path.join(root, fn)
            issues = validate_file(dictionary, fp, local_ideas=local_ideas)
            if issues:
                results[os.path.relpath(fp, mod_path).replace(os.sep, "/")] = issues
    return results

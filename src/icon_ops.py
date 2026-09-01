"""通用图标操作模块

提供内容实体图标字段的读改写与上传逻辑，供国策设计视图与工作台共用：
    - apply_icon_to_entity()   : 将图标值写入实体的图标字段（支持嵌套路径如 portraits>civilian>large）
    - get_entity_icon_field()  : 读取实体块内的图标字段值
    - upload_icon_and_update() : 处理上传图片 -> 生成资源 -> 更新 .gfx -> 写回字段
    - update_gfx_file()        : 在指定 .gfx 文件中添加/更新 SpriteType 精灵定义
"""

import os
import re


def find_block_range(content, entity_key, entity_id=None):
    """在文件内容中定位实体块范围，返回 (起始字符, 结束字符)，未找到返回 (-1, -1)。

    Args:
        content (str): 文件内容
        entity_key (str 或 set): 实体块关键字（如 focus / decision / bookmark），可为集合
        entity_id (str, optional): 实体 id（块内 id = X 的值），None 时取首个匹配块

    实现委托 pdx_span.find_block_range（单遍 O(n) 块扫描，P1-4），
    取代旧版「每次调用整文件 token 化逐块扫描」。
    """
    from pdx_span import find_block_range as _fast
    return _fast(content, entity_key, entity_id)


def get_entity_icon_field(content, block_start, block_end, field_path):
    """读取实体块内图标字段的值。

    Args:
        content (str): 文件内容
        block_start (int): 块起始字符
        block_end (int): 块结束字符
        field_path (str 或 list[str]): 字段路径，"icon" 或嵌套 "portraits>civilian>large"，
            可为候选列表，返回首个非空值

    Returns:
        str: 字段值（去引号），未找到返回 ""
    """
    if isinstance(field_path, (list, tuple)):
        for f in field_path:
            v = _read_single_icon_field(content, block_start, block_end, f)
            if v:
                return v
        return ""
    return _read_single_icon_field(content, block_start, block_end, field_path)


def _read_single_icon_field(content, block_start, block_end, field_path):
    if block_start < 0:
        return ""
    block = content[block_start:block_end]
    if ">" in field_path:
        # 嵌套路径：逐层定位块，最后一层为键值
        current = block
        path = field_path.split(">")
        for seg in path[:-1]:
            m = re.search(r'\b%s\s*=\s*\{' % re.escape(seg), current)
            if not m:
                return ""
            open_brace = current.find("{", m.start())
            d = 0
            k = open_brace
            while k < len(current) and d >= 0:
                if current[k] == "{":
                    d += 1
                elif current[k] == "}":
                    d -= 1
                    if d == 0:
                        break
                k += 1
            current = current[open_brace + 1:k]
        leaf = path[-1]
        vm = re.search(r'\b%s\s*=\s*([^\n#}]+)' % re.escape(leaf), current)
        return vm.group(1).strip().strip('"') if vm else ""
    # 简单字段
    m = re.search(r'\b%s\s*=\s*([^\n#}]+)' % re.escape(field_path), block)
    if m:
        return m.group(1).strip().strip('"')
    return ""


def primary_field(field):
    """返回字段的主路径（列表取首个），供写回使用。"""
    return field[0] if isinstance(field, (list, tuple)) else field


def apply_icon_to_entity(content, block_start, block_end, field_path, icon_value):
    """将图标值写入实体块的指定字段，返回替换后的完整文件内容。

    支持：
        - 已有字段：直接替换
        - 无字段：在 id 行后自动插入（无 id 则在块起始行后插入）
        - 嵌套字段（portraits>civilian>large）：找到最后一级键后替换其值
        - field_path 为候选列表时，写入首个父结构存在的路径（与读取回退对称）

    Args:
        content (str): 文件内容
        block_start (int): 块起始字符
        block_end (int): 块结束字符
        field_path (str 或 list[str]): 字段路径，"icon" 或 "portraits>civilian>large"
        icon_value (str): 要写入的图标值

    Returns:
        str: 替换后的文件内容；块范围无效时返回原内容
    """
    if isinstance(field_path, (list, tuple)):
        for f in field_path:
            new_content = _apply_single_icon_field(content, block_start, block_end, f, icon_value)
            if new_content is not content:
                return new_content
        return content
    return _apply_single_icon_field(content, block_start, block_end, field_path, icon_value)


def _strip_quotes(v):
    """去除首尾引号。"""
    v = v.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1]
    return v


def _build_missing_chain(parents, leaf_key, value):
    """构建缺失父块的链式结构文本。"""
    inner = f'\t{leaf_key} = "{_strip_quotes(value)}"'
    for seg in reversed(parents):
        inner = f'{seg} = {{\n{inner}\n}}'
    return inner


def _set_nested_value(block, parents, leaf_key, value):
    """在实体块内设置嵌套路径（parents 列表 + leaf_key 键值），缺失父块自动创建。

    Returns:
        替换后的块文本
    """
    if not parents:
        # 无父块：直接在块顶层写键值
        vm = re.search(r'\b%s\s*=\s*[^\n#}]+' % re.escape(leaf_key), block)
        if vm:
            return (block[:vm.start()]
                    + f'{leaf_key} = "{_strip_quotes(value)}"'
                    + block[vm.end():])
        m = block.find("{")
        if m < 0:
            return block + f'\n{leaf_key} = "{_strip_quotes(value)}"'
        return block[:m + 1] + f'\n{leaf_key} = "{_strip_quotes(value)}"' + block[m + 1:]

    seg = parents[0]
    m = re.search(r'\b%s\s*=\s*\{' % re.escape(seg), block)
    if m:
        open_brace = block.find("{", m.start())
        d = 0
        k = open_brace
        while k < len(block) and d >= 0:
            if block[k] == "{":
                d += 1
            elif block[k] == "}":
                d -= 1
                if d == 0:
                    break
            k += 1
        new_inner = _set_nested_value(block[open_brace + 1:k], parents[1:], leaf_key, value)
        return block[:open_brace + 1] + new_inner + block[k:]
    # 父块不存在：构建整条缺失链并插入到块顶层
    chain = _build_missing_chain(parents, leaf_key, value)
    m = block.find("{")
    if m < 0:
        return block + "\n" + chain
    return block[:m + 1] + "\n" + chain + block[m + 1:]


def _apply_single_icon_field(content, block_start, block_end, field_path, icon_value):
    if block_start < 0:
        return content
    block = content[block_start:block_end]

    if ">" in field_path:
        path = field_path.split(">")
        leaf_key = path[-1]
        parents = path[:-1]
        new_block = _set_nested_value(block, parents, leaf_key, icon_value)
        return content[:block_start] + new_block + content[block_end:]

    # 简单字段
    icon_match = re.search(r'\b%s\s*=\s*[^\s}\n]*' % re.escape(field_path), block)
    if icon_match:
        new_block = (block[:icon_match.start()]
                     + f'{field_path} = {icon_value}'
                     + block[icon_match.end():])
    else:
        id_match = re.search(r'^([ \t]*)id\s*=\s*[^\n]*', block, re.MULTILINE)
        if id_match:
            indent = id_match.group(1)
            new_block = (block[:id_match.end()]
                         + f"\n{indent}{field_path} = {icon_value}"
                         + block[id_match.end():])
        else:
            first_line, sep, rest = block.partition('\n')
            indent_m = re.match(r'^([ \t]*)', first_line)
            child_indent = indent_m.group(1) + "\t"
            new_block = (first_line + sep + child_indent
                         + f"{field_path} = {icon_value}\n" + rest)
    return content[:block_start] + new_block + content[block_end:]


def write_file_utf8(path, text):
    """以 UTF-8 无 BOM 原子写回文件（HOI4 脚本解析器对 BOM 敏感，BOM 会破坏整文件解析）。

    实现委托 write_utils.atomic_write_text：
      - 原子写（临时文件 + os.replace），写入失败不破坏原文件
      - 写前自动快照到撤销管理器（画布 Ctrl+Z / 工具菜单可撤销本次写入）
      - 文本以 BOM 开头时拒绝写入（WriteContractError）
    """
    from write_utils import atomic_write_text
    return atomic_write_text(path, text)


def update_gfx_file(gfx_path, sprite_name, texture_rel):
    """在指定 .gfx 文件中添加或更新一个 SpriteType 精灵定义。"""
    entries = {}  # sprite_name -> texture_rel
    if os.path.isfile(gfx_path):
        try:
            with open(gfx_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
            for m in re.finditer(r'SpriteType\s*=\s*\{(.*?)\}', content, re.DOTALL | re.IGNORECASE):
                block = m.group(1)
                nm = re.search(r'name\s*=\s*"([^"]+)"', block)
                tx = re.search(r'texturefile\s*=\s*"([^"]+)"', block)
                if nm:
                    entries[nm.group(1)] = tx.group(1) if tx else ""
        except Exception:
            pass
    entries[sprite_name] = texture_rel

    os.makedirs(os.path.dirname(gfx_path), exist_ok=True)
    lines = ["spriteTypes = {"]
    for sn, tx in entries.items():
        lines.append("\tspriteType = {")
        lines.append(f'\t\tname = "{sn}"')
        lines.append(f'\t\ttexturefile = "{tx}"')
        lines.append("\t}")
    lines.append("}")
    from write_utils import atomic_write_text
    atomic_write_text(gfx_path, "\n".join(lines) + "\n")


def upload_icon(mod_path, image_path, icon_base, type_cfg):
    """处理上传图片：复制到 mod 目标目录、生成/更新 .gfx 文件。

    Args:
        mod_path (str): mod 根目录
        image_path (str): 本地图片文件路径
        icon_base (str): 图标资源基础名
        type_cfg (dict): 类型配置，含 subdir / gfx_file / sprite_prefix / gfx_name_pattern

    Returns:
        str: 应写入实体字段的图标值（精灵名或直接路径）；失败抛异常
    """
    icon_base = (icon_base or "icon").strip()
    from PIL import Image
    img = Image.open(image_path).convert('RGBA')

    subdir = type_cfg.get("subdir", "gfx/interface/goals")
    target_dir = os.path.join(mod_path, subdir.replace("/", os.sep))
    os.makedirs(target_dir, exist_ok=True)

    ref_mode = type_cfg.get("ref_mode", "sprite")

    if ref_mode == "path":
        # 直接路径模式：保存图片并以相对 mod 的路径作为字段值
        ext = os.path.splitext(image_path)[1].lower() or ".dds"
        if ext not in (".png", ".jpg", ".jpeg", ".dds", ".tga"):
            ext = ".dds"
        rel_file = f"{subdir.rstrip('/')}/{icon_base}{ext}".replace("/", "/")
        img.save(os.path.join(target_dir, f"{icon_base}{ext}"), format='PNG' if ext == ".png" else 'DDS')
        return rel_file

    # 精灵模式：保存 64x64 dds（及 shine 变体），并更新 interface/*.gfx
    img = img.resize((64, 64), Image.Resampling.LANCZOS)
    img.save(os.path.join(target_dir, f"{icon_base}.dds"), format='DDS')
    if type_cfg.get("shine"):
        img.save(os.path.join(target_dir, f"{icon_base}_shine.dds"), format='DDS')

    interface_dir = os.path.join(mod_path, "interface")
    os.makedirs(interface_dir, exist_ok=True)
    gfx_file = type_cfg.get("gfx_file", "goals_mod.gfx")
    sprite_name = type_cfg.get("gfx_name_pattern", "GFX_goal_{name}").format(name=icon_base)
    texture_rel = f"{subdir.rstrip('/')}/{icon_base}.dds"
    update_gfx_file(os.path.join(interface_dir, gfx_file), sprite_name, texture_rel)

    if type_cfg.get("shine_gfx_file") and type_cfg.get("shine_sprite_pattern"):
        shine_sprite = type_cfg["shine_sprite_pattern"].format(name=icon_base)
        update_gfx_file(os.path.join(interface_dir, type_cfg["shine_gfx_file"]),
                        shine_sprite, f"{subdir.rstrip('/')}/{icon_base}_shine.dds")
    return sprite_name

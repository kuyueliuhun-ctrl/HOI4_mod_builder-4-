"""
科技图标上传与自动 gfx 注册（无 GUI 依赖，GUI / HTTP API / MCP 共用）。

HOI4 科技图标规则（见 docs/科技图标存储规则.md）：
- 图标由 interface/*.gfx 中的 spriteType 注册，名字必须是 GFX_<科技id>_medium
- 纹理放在 gfx/interface/technologies/（扁平目录），文件名任意，dds/png 均可
- 科技定义文件本身不写任何图片字段

本模块提供：
- upload_tech_icon(): 上传图片 → 等比缩放存 PNG → 自动注册/更新 sprite
- ensure_sprite_in_gfx_file(): 安全地向 .gfx 添加或更新一个 SpriteType
  （保留文件其余内容，不重建整个文件）
- find_sprite_gfx_file(): 在 mod 的 interface/*.gfx 中查找已注册的 sprite
"""

import os
import re
import base64
import io

from PIL import Image

TECH_SPRITE_PATTERN = "GFX_{name}_medium"
TECH_GFX_FILE = "technologies_mod.gfx"
TECH_TEXTURE_DIR = "gfx/interface/technologies"


def _read_text(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()


def _write_text(path, text):
    from icon_ops import write_file_utf8
    write_file_utf8(path, text)


def _block_inner(content, start):
    """从 '{' 所在位置起做括号配对，返回 (inner_text, end_pos)。"""
    depth = 0
    i = start
    n = len(content)
    while i < n:
        c = content[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return content[start + 1:i], i
        i += 1
    return content[start + 1:], n


def find_sprite_gfx_file(mod_path, sprite_name):
    """在 mod 的 interface/*.gfx 中查找已注册的同名 sprite。

    Returns:
        str 或 None: 找到时返回 gfx 文件路径
    """
    interface_dir = os.path.join(mod_path, "interface")
    if not os.path.isdir(interface_dir):
        return None
    pat = re.compile(r'name\s*=\s*"' + re.escape(sprite_name) + r'"')
    try:
        for fn in os.listdir(interface_dir):
            if not fn.lower().endswith(".gfx"):
                continue
            fp = os.path.join(interface_dir, fn)
            try:
                content = _read_text(fp)
            except Exception:
                continue
            if pat.search(content):
                return fp
    except Exception:
        return None
    return None


def ensure_sprite_in_gfx_file(gfx_path, sprite_name, texture_rel):
    """在指定 .gfx 文件中添加或更新一个 SpriteType 精灵定义。

    与 icon_ops.update_gfx_file（整文件重建）不同，本函数**保留文件的其余
    全部内容**（其他 sprite 类型、frameAnimatedSpriteType、注释等）：
    - sprite 已存在 → 仅替换/插入该块内的 texturefile 行
    - sprite 不存在且文件有 spriteTypes = { ... } 包装 → 插入到包装块尾
    - 文件不存在 → 创建标准 spriteTypes 包装文件
    """
    os.makedirs(os.path.dirname(gfx_path), exist_ok=True)
    if not os.path.isfile(gfx_path):
        lines = [
            "spriteTypes = {",
            "",
            "\tspriteType = {",
            f'\t\tname = "{sprite_name}"',
            f'\t\ttexturefile = "{texture_rel}"',
            "\t}",
            "}",
            "",
        ]
        _write_text(gfx_path, "\n".join(lines))
        return

    content = _read_text(gfx_path)

    # 1) 已存在同名字 spriteType 块 → 原位更新 texturefile
    block_pat = re.compile(
        r'(SpriteType\s*=\s*\{[^{}]*?name\s*=\s*"' + re.escape(sprite_name) +
        r'"[^{}]*?\})', re.IGNORECASE | re.DOTALL)
    m = block_pat.search(content)
    if m:
        block = m.group(1)
        if re.search(r'texturefile\s*=', block, re.IGNORECASE):
            new_block = re.sub(
                r'texturefile\s*=\s*"[^"]*"',
                f'texturefile = "{texture_rel}"', block,
                count=1, flags=re.IGNORECASE)
        else:
            new_block = re.sub(
                r'(name\s*=\s*"[^"]*")',
                r'\1\n\t\ttexturefile = "' + texture_rel + '"', block,
                count=1, flags=re.IGNORECASE)
        _write_text(gfx_path, content[:m.start(1)] + new_block + content[m.end(1):])
        return

    # 2) 找到 spriteTypes 顶层包装块尾，插入新 sprite
    wrapper = re.search(r'\bspriteTypes\s*=\s*\{', content)
    if wrapper:
        inner, end = _block_inner(content, wrapper.end() - 1)
        insert_at = wrapper.end() - 1 + len(inner)  # 包装块的 '}' 之前
        new_block = (
            "\n\tspriteType = {\n"
            f'\t\tname = "{sprite_name}"\n'
            f'\t\ttexturefile = "{texture_rel}"\n'
            "\t}\n")
        _write_text(gfx_path, content[:insert_at] + new_block + content[insert_at:])
        return

    # 3) 无包装：追加到文件尾（用 spriteTypes 包装）
    tail = "\n" if not content.endswith("\n") else ""
    new_block = (
        f"{tail}spriteTypes = {{\n"
        "\tspriteType = {\n"
        f'\t\tname = "{sprite_name}"\n'
        f'\t\ttexturefile = "{texture_rel}"\n'
        "\t}\n}\n")
    _write_text(gfx_path, content + new_block)


def _load_image_rgba(image_path_or_bytes):
    """读取图片为 RGBA PIL Image，支持 png/jpg/bmp/dds/tga/webp。"""
    from PIL import Image
    if isinstance(image_path_or_bytes, (bytes, bytearray)):
        img = Image.open(io.BytesIO(bytes(image_path_or_bytes)))
    else:
        img = Image.open(image_path_or_bytes)
    return img.convert("RGBA")


def _scale_keeping_ratio(img, max_side=512):
    """等比缩放（只缩小不放大），保持科技图标的宽条比例。"""
    w, h = img.size
    scale = min(1.0, max_side / max(w, h))
    if scale < 1.0:
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))),
                         Image.Resampling.LANCZOS)
    return img


def upload_tech_icon(mod_path, tech_id, image_path_or_bytes):
    """上传科技图标：复制图片到 mod 并自动完成 gfx sprite 注册。

    Args:
        mod_path (str): mod 根目录
        tech_id (str): 科技 id（sprite 名将生成为 GFX_<tech_id>_medium）
        image_path_or_bytes (str|bytes): 本地图片路径或图片字节

    Returns:
        dict: {tech_id, sprite_name, texture_rel, gfx_file, image_file,
               updated_existing, width, height}
    """
    if not mod_path or not os.path.isdir(mod_path):
        raise ValueError("mod 路径无效，请先打开一个 mod 文件夹")
    tech_id = (tech_id or "").strip()
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_.\-]*$', tech_id):
        raise ValueError(f"科技 id 非法: {tech_id!r}")

    img = _load_image_rgba(image_path_or_bytes)
    w0, h0 = img.size
    img = _scale_keeping_ratio(img)

    target_dir = os.path.join(mod_path, TECH_TEXTURE_DIR.replace("/", os.sep))
    os.makedirs(target_dir, exist_ok=True)
    image_file = os.path.join(target_dir, f"{tech_id}.png")
    img.save(image_file, format="PNG")

    sprite_name = TECH_SPRITE_PATTERN.format(name=tech_id)
    texture_rel = f"{TECH_TEXTURE_DIR}/{tech_id}.png"

    # 优先原位更新已注册该 sprite 的 gfx 文件（保留其文件其余内容）
    existing = find_sprite_gfx_file(mod_path, sprite_name)
    if existing:
        ensure_sprite_in_gfx_file(existing, sprite_name, texture_rel)
        gfx_file = os.path.relpath(existing, mod_path).replace("\\", "/")
        updated_existing = True
    else:
        gfx_path = os.path.join(mod_path, "interface", TECH_GFX_FILE)
        ensure_sprite_in_gfx_file(gfx_path, sprite_name, texture_rel)
        gfx_file = f"interface/{TECH_GFX_FILE}"
        updated_existing = False

    return {
        "tech_id": tech_id,
        "sprite_name": sprite_name,
        "texture_rel": texture_rel,
        "gfx_file": gfx_file,
        "image_file": image_file,
        "updated_existing": updated_existing,
        "width": img.size[0],
        "height": img.size[1],
        "src_width": w0,
        "src_height": h0,
    }


def upload_tech_icon_base64(mod_path, tech_id, image_base64):
    """base64 版本的 upload_tech_icon（供 HTTP API / MCP 使用）。"""
    raw = base64.b64decode(image_base64, validate=False)
    return upload_tech_icon(mod_path, tech_id, raw)


def tech_icon_path(mod_path, tech_id):
    """返回 mod 中已上传的科技图标文件路径（无则 None）。"""
    p = os.path.join(mod_path, TECH_TEXTURE_DIR.replace("/", os.sep), f"{tech_id}.png")
    return p if os.path.isfile(p) else None

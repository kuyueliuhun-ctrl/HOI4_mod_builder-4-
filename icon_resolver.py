"""图标解析服务模块

将内容实体中的图标字段值（精灵名 / 直接纹理路径 / 纹理名）解析为 QPixmap。
用于工作台实体卡片与国策设计视图的图标展示。

解析优先级：
    1. 直接路径（如 "gfx/Leaders/xxx.png"，引号包裹，相对 mod/游戏根目录）
    2. gfx_map 精灵名 -> 纹理路径（游戏+mod 合并映射）
    3. 按内容类型目录约定搜索（大小写不敏感，去 GFX_ 前缀，.dds/.png 变体）
    4. 灰色占位图

性能：模块级缓存，目录按需建立小写索引，查找 O(1)。
"""

import os

from dds_loader import DdsLoader

# 图标解码缓存：规范化纹理路径 -> QPixmap
_PIXMAP_CACHE = {}

# 目录小写索引：目录路径 -> {小写文件名: 完整路径}，按需惰性建立
_DIR_INDEX = {}

# 占位图（缓存）
_PLACEHOLDER = None


def _normalize(value):
    """去除引号并去掉空白，返回规范化后的图标值。"""
    if not value:
        return ""
    value = value.strip().strip('"').strip()
    return value


def _get_dir_index(directory):
    """获取目录的小写文件名索引（惰性建立并缓存）。"""
    idx = _DIR_INDEX.get(directory)
    if idx is None:
        idx = {}
        try:
            # 递归索引目录（含子目录），支持嵌套结构如 gfx/interface/ideas/laws/xxx.png
            for root, _dirs, files in os.walk(directory):
                for name in files:
                    base = name.lower()
                    if base not in idx:
                        idx[base] = os.path.join(root, name)
        except Exception:
            pass
        _DIR_INDEX[directory] = idx
    return idx


def _candidate_names(value):
    """根据图标值生成候选文件名（原始 / 去 GFX_ 前缀等）。"""
    names = [value]
    if value.startswith("GFX_goal_"):
        names.append(value[9:])
    elif value.startswith("GFX_"):
        names.append(value[4:])
    # 小写化变体交由目录小写索引处理，无需额外生成
    return names


def _search_in_dirs(value, dirs):
    """在指定目录列表中搜索纹理文件，返回绝对路径或 None。

    支持大小写不敏感匹配、扩展名容错（引用 .png 实际为 .dds 等）与
    .dds/.png/.jpg/.jpeg/.tga 变体。
    """
    for name in _candidate_names(value):
        base = name.lower()
        root, _ext = os.path.splitext(base)
        for ext in (".dds", ".png", ".jpg", ".jpeg", ".tga"):
            for directory in dirs:
                if not os.path.isdir(directory):
                    continue
                # 精确（大小写不敏感）命中
                idx = _get_dir_index(directory)
                target = idx.get(root + ext)
                if target:
                    return target
    return None


def _try_direct_path(v, bases):
    """尝试直接路径（含扩展名容错），返回绝对路径或 ""。"""
    for base in bases:
        if not base:
            continue
        p = os.path.join(base, v)
        if os.path.isfile(p):
            return p
    # 扩展名容错：引用 .png 但实际文件为 .dds / .tga 等
    base_no_ext, ext = os.path.splitext(v)
    ext = ext.lower().lstrip(".")
    for alt_ext in (".dds", ".png", ".jpg", ".jpeg", ".tga"):
        if alt_ext.lstrip(".") == ext:
            continue
        for base in bases:
            if not base:
                continue
            p = os.path.join(base, base_no_ext + alt_ext)
            if os.path.isfile(p):
                return p
    return ""


def _get_placeholder():
    """获取灰色占位图（懒创建并缓存）。"""
    global _PLACEHOLDER
    if _PLACEHOLDER is None:
        from PyQt6.QtGui import QPixmap, QColor, QPainter
        pm = QPixmap(48, 48)
        pm.fill(QColor(70, 70, 74))
        painter = QPainter(pm)
        painter.setPen(QColor(150, 150, 150))
        painter.drawRect(0, 0, 47, 47)
        painter.end()
        _PLACEHOLDER = pm
    return _PLACEHOLDER


def _sprite_candidates(value):
    """根据图标值生成精灵名候选（含 GFX_ / GFX_idea_ 前缀变体）。

    民族精神等内容的 picture 字段常写裸名（如 GMA_Post_Scarcity_Anarchism_idea），
    而 .gfx 文件中的精灵名带前缀（如 GFX_idea_GMA_Post_Scarcity_Anarchism_idea）。
    """
    cands = [value]
    if not value.startswith("GFX_"):
        cands.append("GFX_" + value)
        cands.append("GFX_idea_" + value)
    return cands


def resolve_pixmap(icon_value, dirs=None, gfx_map=None,
                   mod_path="", hoi4_path="", force_reload=False):
    """将图标字段值解析为 QPixmap。

    Args:
        icon_value (str): 图标字段值（精灵名 / 路径 / 纹理名），可为 None
        dirs (list[str], optional): 按内容类型的相对回退目录列表
        gfx_map (dict, optional): 精灵名 -> 纹理绝对路径 的映射
        mod_path (str): mod 根目录
        hoi4_path (str): 游戏根目录
        force_reload (bool): 强制重新解码（忽略缓存）

    Returns:
        QPixmap: 解析成功的图标或占位图（不会返回 None）
    """
    value = _normalize(icon_value)
    if not value:
        return _get_placeholder()

    # 解析真实纹理路径
    tex_path = ""
    v = value.replace("\\", "/")
    bases = [b for b in (mod_path, hoi4_path) if b]
    if v.startswith("gfx/") or v.startswith("./"):
        # 直接路径：相对 mod / 游戏根目录（含扩展名容错）
        tex_path = _try_direct_path(v, bases)
    elif gfx_map:
        # 精灵名查找：支持裸名 -> GFX_ 前缀变体
        for cand in _sprite_candidates(value):
            if cand in gfx_map:
                tex_path = gfx_map.get(cand) or ""
                break

    if not tex_path:
        # 目录约定搜索
        search_dirs = []
        for base in bases:
            for rel in (dirs or []):
                search_dirs.append(os.path.join(base, rel.replace("/", os.sep)))
        # 直接路径未命中时退回按文件名搜索（引用目录可能不同，如 gfx/interface/leaders vs gfx/Leaders）
        search_values = [value]
        if "/" in v and not v.startswith("./"):
            search_values.append(os.path.basename(v))
        for cand in search_values:
            tex_path = _search_in_dirs(cand, search_dirs)
            if tex_path:
                break

    if not tex_path or not os.path.isfile(tex_path):
        return _get_placeholder()

    key = os.path.normcase(os.path.abspath(tex_path))
    if not force_reload and key in _PIXMAP_CACHE:
        return _PIXMAP_CACHE[key]

    pm = DdsLoader.load_as_pixmap(tex_path)
    if pm is None or pm.isNull():
        return _get_placeholder()
    _PIXMAP_CACHE[key] = pm
    return pm


def clear_cache():
    """清空图标与目录索引缓存（mod/游戏路径变化时调用）。"""
    _PIXMAP_CACHE.clear()
    _DIR_INDEX.clear()

"""批量 DDS 转换（算法层，无 Qt 依赖）

用 Pillow 读取 DDS → 输出 PNG。DDS→PNG 批量安全。
PNG→DDS 写回依赖 PIL 对未压缩 DDS 的支持，能力有限，列为可选。
"""

from __future__ import annotations

import os
from typing import Optional


def dds_to_png(src: str, dst: Optional[str] = None) -> Optional[str]:
    """把单个 .dds 转成 .png。返回输出路径；失败返回 None。"""
    if not os.path.isfile(src):
        return None
    from PIL import Image
    try:
        img = Image.open(src)
        img.load()
    except Exception:
        return None
    if img.mode not in ("RGBA", "RGB", "LA", "L"):
        img = img.convert("RGBA")
    dst = dst or os.path.splitext(src)[0] + ".png"
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    img.save(dst, format="PNG")
    return dst


def convert_dir(src_dir: str, dst_dir: Optional[str] = None,
                recursive: bool = False) -> dict:
    """批量把目录下 .dds 转成 .png。返回 {converted:[...], failed:[...]}。"""
    src_dir = os.path.abspath(src_dir)
    dst_dir = dst_dir or src_dir
    os.makedirs(dst_dir, exist_ok=True)
    converted = []
    failed = []
    for root, _dirs, names in (os.walk(src_dir) if recursive
                               else [("", [], os.listdir(src_dir))]):
        base = root if root else src_dir
        for name in names:
            if not name.lower().endswith(".dds"):
                continue
            src = os.path.join(base, name)
            rel = os.path.relpath(src, src_dir)
            out = os.path.join(dst_dir, os.path.splitext(rel)[0] + ".png")
            try:
                r = dds_to_png(src, out)
                if r:
                    converted.append(rel)
                else:
                    failed.append(rel)
            except Exception:
                failed.append(rel)
    return {"converted": converted, "failed": failed, "count": len(converted),
            "fail_count": len(failed)}


def png_to_dds(src: str, dst: Optional[str] = None) -> Optional[str]:
    """PNG → DDS（尽力而为：仅当 PIL 能写 DDS 时）。"""
    from PIL import Image
    if not os.path.isfile(src):
        return None
    dst = dst or os.path.splitext(src)[0] + ".dds"
    os.makedirs(os.path.dirname(os.path.abspath(dst)) or ".", exist_ok=True)
    img = Image.open(src).convert("RGBA")
    try:
        img.save(dst, format="DDS")
    except Exception:
        return None
    return dst
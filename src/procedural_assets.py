"""程序化 GUI/GFX 资产生成（B3 批二③，纯 PIL，无外部模型）。

generate_asset_png 生成一张程序化 PNG：垂直渐变 + 圆角遮罩 + 顶部高光。
供 ApiCore.generate_gui_gfx_asset 调用；不依赖 Qt。
"""

from __future__ import annotations

from PIL import Image, ImageDraw


def _hex_color(value):
    value = str(value).lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def generate_asset_png(path, name="asset", size=(64, 64), colors=None):
    """生成程序化 PNG 到 path。

    colors: 渐变两端颜色（hex 或 rgb 元组），默认蓝系。
    Returns: path
    """
    colors = list(colors or ["#3b82f6", "#1d4ed8"])
    w, h = int(size[0]), int(size[1])
    top = _hex_color(colors[0])
    bot = _hex_color(colors[1] if len(colors) > 1 else colors[0])
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / (h - 1) if h > 1 else 0.0
        c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        d.line([(0, y), (w, y)], fill=c + (255,))
    mask = Image.new("L", (w, h), 0)
    dm = ImageDraw.Draw(mask)
    r = max(1, min(w, h) // 4)
    dm.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    img.putalpha(mask)
    d2 = ImageDraw.Draw(img)
    d2.line([(2, 2), (w - 3, 2)], fill=(255, 255, 255, 120), width=1)
    import os
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    img.save(path, format="PNG")
    return path

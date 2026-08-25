"""地图画布渲染性能基准（offscreen，不写任何文件）

测量矢量填充/边界缓存优化后的整帧渲染耗时：
    1. 各缩放档位下连续 grab 平均/最大耗时（瓦片命中率一并输出）
    2. 30x 下大步平移模拟帧耗时（每步都超出瓦片缓存区 = 最坏情形，
       每帧触发一次瓦片重渲染；真实小步平移大部分帧为纯 blit 的 ~5ms）

用法（Windows，双版本均可跑）：
    python tools/bench_map_render.py
    python tools/bench_map_render.py --mod E:\\mods\\3350890356 --size 1440x900 --rounds 20

参考基线（旧实现，docs/历史迭代日志.md §6.2/6.3）：
    30x 平移单帧 3.7~8.5s（边界长线每帧整条描边）；矢量填充 30x 11.7ms/帧。
    本工具输出的是整帧 grab 耗时（含 blit/合成），可直接对比。
"""

from __future__ import annotations

import argparse
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def _time_grabs(canvas, rounds, app):
    """连续 grab rounds 次，返回耗时列表（毫秒）。"""
    times = []
    for _ in range(rounds):
        t = time.perf_counter()
        canvas.grab()
        times.append((time.perf_counter() - t) * 1000.0)
    app.processEvents()
    return times


def main():
    ap = argparse.ArgumentParser(description="地图画布渲染基准（offscreen）")
    ap.add_argument("--mod", default=r"E:\mods\3350890356",
                    help="mod 目录（需含 map/provinces.bmp + definition.csv）")
    ap.add_argument("--size", default="1440x900", help="视口尺寸 WxH")
    ap.add_argument("--rounds", type=int, default=20, help="每档抓帧次数")
    args = ap.parse_args()

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    from map_loader import MapData
    md = MapData(args.mod)
    if md.id_map is None:
        print("无法加载地图: %s" % args.mod)
        return 1
    w, h = [int(v) for v in args.size.lower().split("x")]

    from map_canvas import MapCanvas
    from map_vector import get_edge_segments
    from map_fill import get_province_polygons

    t0 = time.perf_counter()
    segs = get_edge_segments(md)
    fill = get_province_polygons(md)
    print("矢量层构建: %.1fs（边界 %d 段 / 填充 %d 环）" % (
        time.perf_counter() - t0,
        segs.shape[0] if segs is not None else 0,
        fill.n_loops if fill is not None else 0))

    c = MapCanvas(md)
    c.resize(w, h)
    c.show()
    app.processEvents()
    c.enable_vector_borders(segs)
    c.enable_vector_fill(fill)
    c.fit_map()
    app.processEvents()

    print("\n缩放档位（%dx%d 视口, %d 帧/档）:" % (w, h, args.rounds))
    print("%-8s %-12s %-12s %-10s" % ("缩放", "平均(ms)", "最大(ms)", "瓦片命中"))
    for zoom in (1.5, 3.0, 8.0, 30.0, 90.0):
        c.resetTransform()
        c.scale(zoom, zoom)
        c.centerOn(md.width / 2.0, md.height / 2.0)
        app.processEvents()
        c.grab()                       # 预热：瓦片首渲染不计入
        hits0 = c.base_item._tile_hits
        times = _time_grabs(c, args.rounds, app)
        hits = c.base_item._tile_hits - hits0
        avg = sum(times) / len(times)
        print("%-8s %-12.2f %-12.2f %d/%d" % (
            zoom, avg, max(times), hits, args.rounds))

    print("\n平移模拟（30x, %d 帧）:" % args.rounds)
    c.resetTransform()
    c.scale(30, 30)
    c.centerOn(md.width / 2.0, md.height / 2.0)
    app.processEvents()
    c.grab()
    times = []
    for i in range(args.rounds):
        x = md.width * (0.3 + 0.4 * (i % 10) / 9.0)
        y = md.height * (0.3 + 0.4 * (i % 7) / 6.0)
        c.centerOn(x, y)
        t = time.perf_counter()
        c.grab()
        times.append((time.perf_counter() - t) * 1000.0)
    app.processEvents()
    times.sort()
    print("平均 %.2f ms | 中位 %.2f ms | 最大 %.2f ms" % (
        sum(times) / len(times),
        times[len(times) // 2],
        times[-1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

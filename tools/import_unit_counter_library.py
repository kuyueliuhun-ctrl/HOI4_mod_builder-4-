"""从游戏本体导入单位标牌库（SF 移植：import_hoi4_unit_counter_library）

从 <游戏目录>/gfx/interface/counters/ 提取各军种单位标牌（onmap_*.dds），
转换为 PNG 存入图标库目录并生成 manifest.json。

用法：
    python tools/import_unit_counter_library.py --game <游戏目录> [--out <库目录>]

默认输出：项目根 unit_counter_library/
"""

from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def main():
    ap = argparse.ArgumentParser(description="导入 HOI4 单位标牌图标库")
    ap.add_argument("--game", required=True, help="HOI4 游戏根目录")
    ap.add_argument("--out", default="", help="输出库目录（默认项目根）")
    args = ap.parse_args()

    from unit_counter_library import import_unit_counter_library
    t0 = __import__("time").time()
    result = import_unit_counter_library(args.game, args.out or None)
    print("已导入 %d 个标牌（%d 个跳过）到 %s，耗时 %.1fs"
          % (result["total"], result["skipped"], result["out_dir"],
             __import__("time").time() - t0))
    print("类别: %s" % ", ".join(result["categories"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

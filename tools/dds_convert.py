"""批量 DDS 转换 CLI。

用法：
    python tools/dds_convert.py <src文件或目录> [--out 目录] [-r]
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="DDS → PNG 批量转换")
    ap.add_argument("input", help="DDS 文件或目录")
    ap.add_argument("--out", default="", help="输出目录")
    ap.add_argument("-r", "--recursive", action="store_true", help="递归目录")
    args = ap.parse_args(argv)

    from dds_convert import dds_to_png, convert_dir
    if os.path.isdir(args.input):
        r = convert_dir(args.input, args.out or None, recursive=args.recursive)
        print("转换 {} 个，失败 {} 个".format(r["count"], r["fail_count"]))
        for fail in r["failed"]:
            print("  失败:", fail)
    else:
        out = dds_to_png(args.input, os.path.join(args.out or os.path.dirname(args.input),
                                                  os.path.splitext(os.path.basename(args.input))[0] + ".png")
                         if args.out else None)
        print("已转换 →", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

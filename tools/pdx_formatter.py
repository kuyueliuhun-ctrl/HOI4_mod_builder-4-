"""PDX 脚本格式化工具（CLI）

用法：
    python tools/pdx_formatter.py [-r] [--extensions ...] [-ws] [-ic] <文件或目录>...

只改缩进；本地化 .yml 自动用 utf-8-sig + BOM。走原子写 + 撤销快照。
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from pdx_format import format_paths  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="PDX 脚本格式化（括号计数缩进）")
    ap.add_argument("inputs", nargs="+", help="文件或目录")
    ap.add_argument("-r", "--recursive", action="store_true", help="递归处理目录")
    ap.add_argument("--extensions", nargs="*", default=[".txt", ".gfx", ".yml", ".yaml"],
                    help="处理的扩展名（默认 .txt .gfx .yml .yaml）")
    ap.add_argument("-ws", "--whitespace", action="store_true",
                    help="仅去除行尾空格，不重缩进")
    ap.add_argument("-ic", "--ignore-comments", action="store_true",
                    help="跳过以 # 开头的行")
    args = ap.parse_args(argv)

    n = format_paths(args.inputs, extensions=tuple(args.extensions),
                     recursive=args.recursive,
                     remove_whitespace=args.whitespace,
                     ignore_comments=args.ignore_comments)
    print("共格式化 {} 个文件".format(n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

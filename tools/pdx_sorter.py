"""state/province 排序与部署 CLI。

用法：
    python tools/pdx_sorter.py sort <文件> [--out 输出]
    python tools/pdx_sorter.py deploy <文件> --order 1,2,3 [--out 输出]
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


def _write(path, text, out):
    from write_utils import atomic_write_text
    if out:
        atomic_write_text(out, text, encoding="utf-8")
        print("已写 →", out)
    else:
        print(text)


def main(argv=None):
    ap = argparse.ArgumentParser(description="state/province 排序与部署")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("sort", help="按块内 id 排序")
    ps.add_argument("file")
    ps.add_argument("--out", default="")

    pd = sub.add_parser("deploy", help="按给定顺序部署块")
    pd.add_argument("file")
    pd.add_argument("--order", required=True, help="逗号分隔顺序")
    pd.add_argument("--out", default="")

    args = ap.parse_args(argv)

    with open(args.file, "r", encoding="utf-8") as f:
        text = f.read()
    if args.cmd == "sort":
        from pdx_sorter import sort_state_file
        _write(args.file, sort_state_file(text), args.out)
    else:
        from pdx_sorter import deploy_blocks
        order = [x.strip() for x in args.order.split(",")]
        _write(args.file, deploy_blocks(text, order=order), args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

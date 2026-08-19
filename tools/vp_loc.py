"""胜利点本地化生成 CLI。

用法：
    python tools/vp_loc.py <mod目录> [--lang simp_chinese] [--out 输出yml]
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="胜利点本地化生成")
    ap.add_argument("mod", help="mod 根目录")
    ap.add_argument("--lang", default="simp_chinese")
    ap.add_argument("--out", default="", help="输出 yml（缺省打印）")
    args = ap.parse_args(argv)

    from vp_loc import collect_vps, build_vp_loc_text
    vps = collect_vps(args.mod)
    text = build_vp_loc_text(vps, lang=args.lang)
    print("VP 数:", len(vps))
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        # 本地化 yml 合规写 BOM
        from write_utils import atomic_write_text
        atomic_write_text(args.out, text, encoding="utf-8-sig", allow_bom=True)
        print("已写 →", args.out)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

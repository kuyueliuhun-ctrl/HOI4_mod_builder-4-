"""事件生成器 CLI。

用法：
    python tools/event_generator.py --id MYNS.my_event [--out events/xxx.txt] [--loc out_l.yml]
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="HOI4 事件生成器")
    ap.add_argument("--id", required=True, help="事件 ID（可含 MYNS.xxx 或命名空间）")
    ap.add_argument("--namespace", default="", help="命名空间（id 未含点时生效）")
    ap.add_argument("--out", default="", help="写入事件脚本路径（缺省仅打印）")
    ap.add_argument("--loc-out", default="", help="写入本地化 yml 路径（可选）")
    args = ap.parse_args(argv)

    from event_gen import generate_event
    r = generate_event(args.id, namespace=args.namespace)
    ns = r["namespace"]
    eid = r["id"]

    from write_utils import atomic_write_text
    if args.loc_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.loc_out)) or ".", exist_ok=True)
        lines = ["l_english:"]
        for e in r["loc"]:
            lines.append(' {}: "{}"'.format(e["key"], e["value"]))
        atomic_write_text(args.loc_out, "\n".join(lines) + "\n",
                          encoding="utf-8-sig", allow_bom=True)
        print("已写本地化 →", args.loc_out)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        atomic_write_text(args.out, r["text"], encoding="utf-8")
        print("已写事件 →", args.out)
    else:
        print("事件 ID:", eid, "命名空间:", ns)
        print(r["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

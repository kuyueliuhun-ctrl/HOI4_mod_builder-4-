"""内容生成器合集 CLI（民族精神/意识形态/人物/将领/国家Tag/国策全套）。

用法示例见各子命令 --help：
    python tools/content_generators.py ideas --id MY_MOD --out ideas.txt --loc-out loc.yml
    python tools/content_generators.py country --tag GER --name Germany --out history/countries/
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from write_utils import atomic_write_text  # noqa: E402


def _write(path, text, loc=False):
    if not path:
        return
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    if loc:
        atomic_write_text(path, text, encoding="utf-8-sig", allow_bom=True)
    else:
        atomic_write_text(path, text, encoding="utf-8")


def _loc_text(locs):
    lines = ["l_english:"]
    for e in locs:
        lines.append(' {}: "{}"'.format(e["key"], e["value"]))
    return "\n".join(lines) + "\n"


def cmd_ideas(args):
    from idea_gen import generate_ideas
    r = generate_ideas([{"id": args.id, "picture": args.picture}])
    _write(args.out, r["text"]); _write(args.loc_out, _loc_text(r["loc"]), loc=True)
    print("ideas 已生成，词条 {} 条".format(r["count"]))


def cmd_ideology(args):
    from ideology_gen import generate_ideologies
    r = generate_ideologies([{"id": args.id}])
    _write(args.out, r["text"]); _write(args.loc_out, _loc_text(r["loc"]), loc=True)
    print("意识形态已生成，词条 {} 条".format(r["count"]))


def cmd_character(args):
    from character_gen import generate_characters
    r = generate_characters([{"tag": args.tag,
                              "characters": [{"id": args.id, "name_loc": args.name_loc or None}]}])
    _write(args.out, r["text"]); _write(args.loc_out, _loc_text(r["loc"]), loc=True)
    print("角色已生成，词条 {} 条".format(r["count"]))


def cmd_general(args):
    from general_gen import generate_leader_blocks
    r = generate_leader_blocks([{"name_loc": args.name_loc or None,
                                 "ideology": args.ideology}])
    _write(args.out, r["text"]); _write(args.loc_out, _loc_text(r["loc"]), loc=True)
    print("将领代码已生成，词条 {} 条".format(r["count"]))


def cmd_country(args):
    from country_boot import generate_country_bootstrap, country_tag_line
    r = generate_country_bootstrap([{"tag": args.tag, "name": args.name}])
    out_dir = args.out or "."
    for fn, text in r["histories"].items():
        _write(os.path.join(out_dir, fn), text)
    print("历史文件：", list(r["histories"].keys()))
    for line in r["tag_lines"]:
        print("  ", line)
    _write(args.loc_out, _loc_text(r["loc"]), loc=True)


def cmd_focus(args):
    from focus_package_gen import generate_package, generate_icon_gfx
    focuses = [{"id": fid.strip(), "x": args.x, "y": args.y}
               for fid in args.ids.split(",") if fid.strip()]
    pkg = generate_package(focuses, tree_id=args.tree)
    _write(args.out, pkg["tree"])
    _write(args.loc_out, _loc_text(pkg["loc"]), loc=True)
    if args.gfx:
        _write(args.gfx, generate_icon_gfx(focuses))
    print("国策全套已生成，国策 {} 个".format(pkg["count"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description="内容生成器合集")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ideas", help="民族精神"); p.add_argument("--id", required=True)
    p.add_argument("--picture"); p.add_argument("--out"); p.add_argument("--loc-out")
    p.set_defaults(func=cmd_ideas)

    p = sub.add_parser("ideology", help="意识形态"); p.add_argument("--id", required=True)
    p.add_argument("--out"); p.add_argument("--loc-out")
    p.set_defaults(func=cmd_ideology)

    p = sub.add_parser("character", help="角色"); p.add_argument("--tag", required=True)
    p.add_argument("--id", required=True); p.add_argument("--name-loc")
    p.add_argument("--out"); p.add_argument("--loc-out")
    p.set_defaults(func=cmd_character)

    p = sub.add_parser("general", help="将领"); p.add_argument("--name-loc")
    p.add_argument("--ideology", default="neutrality")
    p.add_argument("--out"); p.add_argument("--loc-out")
    p.set_defaults(func=cmd_general)

    p = sub.add_parser("country", help="国家Tag"); p.add_argument("--tag", required=True)
    p.add_argument("--name", required=True); p.add_argument("--out"); p.add_argument("--loc-out")
    p.set_defaults(func=cmd_country)

    p = sub.add_parser("focus", help="国策全套")
    p.add_argument("--ids", required=True, help="逗号分隔国策 id")
    p.add_argument("--tree", default="PROJECT")
    p.add_argument("--x", type=int, default=0); p.add_argument("--y", type=int, default=0)
    p.add_argument("--out"); p.add_argument("--loc-out"); p.add_argument("--gfx")
    p.set_defaults(func=cmd_focus)

    args = ap.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

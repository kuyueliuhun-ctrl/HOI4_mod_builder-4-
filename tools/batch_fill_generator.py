"""批量填鸭（AOR）生成 CLI——列表驱动模板批量生成。

用法：
    # 单列表格：每行一个名字，生成 idea 图标注册
    python tools/batch_fill_generator.py idea_sprite --list 文件.txt --out 输出.txt

    # 带表头的 TSV（首行字段名，字段与预设占位符对应）
    python tools/batch_fill_generator.py general --input 将领表.tsv --out 输出.txt

    # 不带 --input 时从 stdin 读取
    echo -e 'CH\\nAH' | python tools/batch_fill_generator.py idea_sprite

预设：
    idea_sprite / shine_sprite：单列图片名；general：TSV 含 name/job/skill/attack/defense/planning/logistics。
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="批量填鸭（AOR）列表驱动模板生成")
    ap.add_argument("preset", choices=("idea_sprite", "shine_sprite", "general"),
                    help="预设：idea_sprite / shine_sprite / general")
    ap.add_argument("--input", default="", help="输入文件（缺省读 stdin）")
    ap.add_argument("--list", dest="list_file", default="",
                    help="单列名字文件（每行一个，适用于 idea_sprite/shine_sprite）")
    ap.add_argument("--out", default="", help="输出文件（缺省打印到 stdout）")
    ap.add_argument("--sep", default="\t", help="表格分隔符（默认 Tab）")
    args = ap.parse_args(argv)

    from batch_fill import BATCH_PRESETS, generate_preset, parse_table

    if args.list_file:
        names = [line.strip() for line in _read_text(args.list_file).splitlines()
                 if line.strip()]
        rows = names
    elif args.input:
        text = _read_text(args.input)
        first = text.splitlines()[0] if text.splitlines() else ""
        if args.sep in first:
            rows = parse_table(text, delimiter=args.sep)
        else:
            rows = [line.strip() for line in text.splitlines() if line.strip()]
    else:
        text = sys.stdin.read()
        first = text.splitlines()[0] if text.splitlines() else ""
        if args.sep in first:
            rows = parse_table(text, delimiter=args.sep)
        else:
            rows = [line.strip() for line in text.splitlines() if line.strip()]

    if not rows:
        ap.error("没有可用输入行")
        return 2

    output = generate_preset(args.preset, rows)
    print(f"预设: {args.preset} | 行数: {len(rows)} | 字符数: {len(output)}",
          file=sys.stderr)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        from write_utils import atomic_write_text
        atomic_write_text(args.out, output, undo=False)
        print(f"已写 → {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
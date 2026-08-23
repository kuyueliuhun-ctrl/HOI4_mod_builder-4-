"""一次性脚本：按类名前缀拆分 tests/test_contracts.py 到按域测试文件（F1）。

用法：
    python tools/split_tests.py
退出码：
    0 = 成功；1 = 失败（不写文件）
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_FILE = os.path.join(ROOT, "tests", "test_contracts.py")

RULES = [
    ("test_map.py", re.compile(r"^(Map|State|Building|Region|Oob|Tile|Border|Hover)")),
    ("test_designers.py", re.compile(r"^(Ship|Plane|Tank|Designer|Variant|Derived|Module)")),
    ("test_ai.py", re.compile(r"^Ai")),
    ("test_bop.py", re.compile(r"^Bop")),
    ("test_localization.py", re.compile(r"^(Loc|Translation|Qiqi|Term|EntityResource)")),
    ("test_workbench.py", re.compile(r"^(Workbench|Route|TypeList|Nofile|OobFileMode|OobOpen|WorkbenchOob)")),
    ("test_infra.py", re.compile(r"^(Write|Undo|Health|Icon|Api|Mcp|Overlay|UnitCounter|Theme)")),
]


def main():
    with open(SRC_FILE, encoding="utf-8") as f:
        lines = f.readlines()

    class_entries = []
    for i, line in enumerate(lines):
        m = re.match(r"^class (\w+)", line)
        if m:
            class_entries.append((i, m.group(1)))

    if not class_entries:
        print("未找到测试类")
        return 1

    header = lines[:class_entries[0][0]]
    buckets = {}
    for idx, (start, name) in enumerate(class_entries):
        end = class_entries[idx + 1][0] if idx + 1 < len(class_entries) else len(lines)
        target = None
        for fname, pat in RULES:
            if pat.match(name):
                target = fname
                break
        buckets.setdefault(target, []).append((start, end))

    total_before = sum(1 for l in lines if l.startswith("    def test_"))
    total_after = 0

    for target, blocks in buckets.items():
        if target is None:
            continue
        out = list(header)
        for start, end in blocks:
            out.extend(lines[start:end])
            total_after += sum(1 for l in lines[start:end]
                               if l.startswith("    def test_"))
        path = os.path.join(ROOT, "tests", target)
        if os.path.exists(path):
            print("跳过已存在文件: %s" % target)
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write("".join(out))
        print("生成 %s（%d 类，%d 个 test 方法）"
              % (target, len(blocks),
                 sum(1 for s, e in blocks
                     for l in lines[s:e] if l.startswith("    def test_"))))

    core_blocks = buckets.get(None, [])
    core_lines = list(header)
    for start, end in core_blocks:
        core_lines.extend(lines[start:end])
        total_after += sum(1 for l in lines[start:end]
                           if l.startswith("    def test_"))
    with open(SRC_FILE, "w", encoding="utf-8") as f:
        f.write("".join(core_lines))

    print("test_contracts.py 剩余 %d 行 / %d 类 / %d 个 test 方法"
          % (len(core_lines), len(core_blocks),
             sum(1 for s, e in core_blocks
                 for l in lines[s:e] if l.startswith("    def test_"))))
    print("用例总数 before=%d after=%d" % (total_before, total_after))
    return 0 if total_before == total_after else 1


if __name__ == "__main__":
    sys.exit(main())
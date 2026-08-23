"""行数预算：>BUDGET 行的 src/*.py 必须在白名单内；白名单外超限即失败。

用法：
    python tools/check_file_budget.py
退出码：
    0 = 无白名单外超限文件
    1 = 存在超限且不在白名单的文件
"""

from __future__ import annotations

import json
import os
import sys

BUDGET = 1200
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWLIST = os.path.join(ROOT, "tools", "file_budget_allowlist.json")


def main():
    with open(ALLOWLIST, encoding="utf-8") as f:
        allow = set(json.load(f))
    bad, warn = [], []
    srcdir = os.path.join(ROOT, "src")
    for fn in os.listdir(srcdir):
        if not fn.endswith(".py"):
            continue
        p = os.path.join(srcdir, fn)
        with open(p, encoding="utf-8", errors="replace") as fh:
            n = sum(1 for _ in fh)
        if n <= BUDGET:
            continue
        rel = "src/" + fn
        (warn if rel in allow else bad).append("%s %d 行" % (rel, n))
    for w in warn:
        print("  [白名单] %s（拆分后从白名单移除）" % w)
    for b in bad:
        print("  [超限] %s（> %d 行且不在白名单）" % (b, BUDGET))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
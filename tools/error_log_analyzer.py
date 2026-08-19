"""错误日志分析 CLI。

用法：
    python tools/error_log_analyzer.py <error.log 或 text.log>
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="HOI4 游戏错误日志分析")
    ap.add_argument("log", help="error.log / text.log 路径")
    args = ap.parse_args(argv)

    from error_log import analyze_file, summarize, classify_by_subsystem
    results = analyze_file(args.log)
    summary = summarize(results)
    subsystems = classify_by_subsystem(results)
    print("匹配 {} 条".format(len(results)))
    print("-- 子系统归类 --")
    for sub, cnt in sorted(subsystems.items(), key=lambda x: -x[1]):
        print("  {}: {}".format(sub, cnt))
    print("-- 错误类别 --")
    for cat, cnt in sorted(summary.items(), key=lambda x: -x[1]):
        print("  {}: {}".format(cat, cnt))
    for r in results:
        print("L{} [{}] {}".format(r["lineno"], r["category"], r["message"]))
    return 0 if results else 0


if __name__ == "__main__":
    raise SystemExit(main())

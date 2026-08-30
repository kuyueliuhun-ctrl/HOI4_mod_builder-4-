#!/usr/bin/env python
"""MCP 正确调用模板生成/检查工具。

用法：
    python tools/gen_mcp_templates.py --check   # 只检查模板 schema 与 tool 存在（不调用 handler）
    python tools/gen_mcp_templates.py --list    # 列出模板
    python tools/gen_mcp_templates.py --run     # 额外在临时 core 调用 handler（较慢）

退出码：0 = 全部通过；1 = 存在错误。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

TEMPLATE_ROOT = os.path.join(ROOT, "templates", "mcp")


def _mkdtemp(prefix):
    root = os.path.join(ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


def _iter_templates():
    for dirpath, _dirs, names in os.walk(TEMPLATE_ROOT):
        for name in sorted(names):
            if name.endswith(".json"):
                fp = os.path.join(dirpath, name)
                with open(fp, encoding="utf-8") as f:
                    yield json.load(f), fp


def main():
    parser = argparse.ArgumentParser(description="MCP 正确调用模板工具")
    parser.add_argument("--check", action="store_true", help="校验模板 schema")
    parser.add_argument("--list", action="store_true", help="列出模板")
    parser.add_argument("--run", action="store_true", help="调用 handler（较慢）")
    args = parser.parse_args()

    from api_server import ApiCore
    from mcp_tools import build_tools
    from mcp_validator import validate_call

    core = ApiCore(mod_path=_mkdtemp("gen_tpl_"), game_path="")
    tools = {t["name"]: t for t in build_tools(core)}
    items = list(_iter_templates())
    if args.list:
        for data, fp in items:
            print("%s\t%s\t%s" % (data.get("tool"), data.get("name"), fp))
        return 0

    errors = []
    for data, fp in items:
        tool_name = data.get("tool", "")
        if tool_name not in tools:
            errors.append("%s: 未知工具 %s" % (fp, tool_name))
            continue
        issues = [i for i in validate_call(tools[tool_name], data.get("args", {}))
                  if i.severity == "error"]
        if issues:
            errors.append("%s: %s" % (fp, issues[0].message))
            continue
        if args.run:
            try:
                tools[tool_name]["_handler"](data.get("args", {}))
            except Exception as e:
                errors.append("%s: handler %s: %s" % (fp, type(e).__name__, e))

    if args.list:
        return 0
    if errors:
        print("模板检查失败 %d 条：" % len(errors))
        for e in errors:
            print("  " + e)
        return 1
    print("模板检查通过：%d 个模板" % len(items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
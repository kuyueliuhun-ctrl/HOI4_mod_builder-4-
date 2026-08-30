#!/usr/bin/env python
"""MCP 校验器 CLI：检查工具注册表 metadata/schema 是否符合正确范式。

用法：
    python tools/check_mcp_contracts.py
退出码：
    0 = 无 error（warning 不阻塞）
    1 = 存在 error
"""
from __future__ import annotations

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def _make_core():
    from api_server import ApiCore
    tmp = tempfile.mkdtemp(prefix="mcp_contract_", dir=os.path.join(ROOT, ".runtime", "test_tmp"))
    os.makedirs(tmp, exist_ok=True)
    return ApiCore(mod_path=tmp, game_path="")


def main():
    from mcp_tools import NAV_TOOLS_META, build_tools
    from mcp_validator import (Issue, format_issues,
                               validate_tool_metadata)

    core = _make_core()
    issues = []
    for tool in build_tools(core):
        issues.extend(validate_tool_metadata(tool))
    # 导航工具也要过 schema/描述基本校验
    for name, desc, schema in NAV_TOOLS_META:
        issues.extend(validate_tool_metadata({
            "name": name, "description": desc, "inputSchema": schema,
        }))

    print(format_issues(issues))
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
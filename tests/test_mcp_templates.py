"""MCP 正确调用模板回归测试。

加载 templates/mcp/**/*.json：
1. 模板中 tool 必须存在；
2. `mcp_validator.validate_call` 无 error；
3. 在临时 core 上调用 handler 不抛异常。
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

TEMPLATE_ROOT = os.path.join(PROJECT_ROOT, "templates", "mcp")


def _mkdtemp(prefix):
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


def _iter_templates():
    for dirpath, _dirs, names in os.walk(TEMPLATE_ROOT):
        for name in sorted(names):
            if name.endswith(".json"):
                fp = os.path.join(dirpath, name)
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
                yield data, fp


class McpTemplateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from api_server import ApiCore
        from mcp_tools import build_tools
        cls.core = ApiCore(mod_path=_mkdtemp("mcp_tpl_"), game_path="")
        cls.tools = {t["name"]: t for t in build_tools(cls.core)}

    def test_all_templates_exist_and_valid_call(self):
        from mcp_validator import validate_call
        for data, fp in _iter_templates():
            with self.subTest(template=data.get("name", fp)):
                tool_name = data.get("tool", "")
                self.assertIn(tool_name, self.tools,
                              "%s 引用未知工具 %s" % (fp, tool_name))
                issues = [i for i in
                          validate_call(self.tools[tool_name], data.get("args", {}))
                          if i.severity == "error"]
                self.assertEqual(issues, [], "%s 校验失败" % fp)

    def test_all_templates_handler_no_error(self):
        for data, fp in _iter_templates():
            with self.subTest(template=data.get("name", fp)):
                tool = self.tools[data["tool"]]
                try:
                    tool["_handler"](data.get("args", {}))
                except ValueError as e:
                    self.fail("%s handler 抛 ValueError: %s" % (fp, e))
                except Exception as e:
                    self.fail("%s handler 抛异常: %s: %s"
                              % (fp, type(e).__name__, e))


if __name__ == "__main__":
    unittest.main()
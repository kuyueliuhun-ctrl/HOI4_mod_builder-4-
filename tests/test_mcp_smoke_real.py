"""真实数据 MCP 全量工具冒烟（guarded：无真实 mod/game 目录时跳过）。

只在本机存在真实 mod 与游戏目录时运行；CI/无数据环境自动 skip。
覆盖 B3 批三②：对真实 mod 跑全量 178 工具的默认冒烟（重型工具跳过），
断言 0 error。ok/skipped/skip-data/skipped-heavy 均为预期。
"""

from __future__ import annotations

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

REAL_MOD = "/mnt/e/mods/3350890356"
REAL_GAME = ("/mnt/e/SteamLibrary/steamapps/common/Hearts of Iron IV")


@unittest.skipUnless(
    os.path.isdir(REAL_MOD) and os.path.isdir(REAL_GAME),
    "需要真实 mod/game 目录才运行",
)
class McpRealDataSmokeTest(unittest.TestCase):
    def test_default_smoke_all_tools_no_error(self):
        from api_server import ApiCore
        from tools.smoke_mcp_tools import run_smoke

        core = ApiCore(mod_path=REAL_MOD, game_path=REAL_GAME)
        results = run_smoke(core, REAL_MOD, limit=None, full=False)
        self.assertGreater(len(results), 0)
        errors = [r for r in results if r[1] == "error"]
        self.assertEqual(errors, [],
                         "存在冒烟 error:\n%s" % "\n".join(
                             "[%s] %s %s" % (r[1], r[0], r[2]) for r in errors))
        statuses = [r[1] for r in results]
        self.assertIn("ok", statuses)


if __name__ == "__main__":
    unittest.main()

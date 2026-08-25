"""ApiCore 扩展：调试启动预检 / 拉起（B3 批二④）。

- validate_hoi4_debug_run：预检游戏/可执行/文档/launcher/error_log；launch=true + approved=true 才拉起
  hoi4.exe -gdpr-compliant -debug_mode（安全边界：显式批准才启动进程）。
- launch_hoi4_debug_with_rchadow：Rchadow 为外部 Rust 工具，本项目未内置，返回不可用与引导。
"""

from __future__ import annotations

import os
import subprocess
import sys


class DebugMixin:
    """调试启动预检与拉起。"""

    def _debug_paths(self):
        game = self.game_path or ""
        exe = ""
        if game:
            for n in ("hoi4.exe", "dowser.exe"):
                c = os.path.join(game, n)
                if os.path.isfile(c):
                    exe = c
                    break
        doc = ""
        home = os.path.expanduser("~")
        candidate = os.path.join(home, "Documents", "Paradox Interactive",
                                 "Hearts of Iron IV")
        if os.path.isdir(candidate):
            doc = candidate
        launcher = os.path.join(game, "launcher-settings.json") if game else ""
        error_log = os.path.join(doc, "logs", "error.log") if doc else ""
        if error_log and not os.path.isfile(error_log):
            error_log = ""
        return {"game_path": game, "exe": exe, "document_path": doc,
                "launcher_settings": launcher, "error_log_path": error_log}

    def validate_hoi4_debug_run(self, data=None):
        """调试预检；{launch?, approved?} 显式批准才拉起游戏。"""
        data = data or {}
        p = self._debug_paths()
        checks = {
            "game_path": bool(p["game_path"]),
            "executable": bool(p["exe"]),
            "document_path": bool(p["document_path"]),
            "launcher_settings": bool(p["launcher_settings"]
                                      and os.path.isfile(p["launcher_settings"])),
            "error_log": bool(p["error_log_path"]),
        }
        green = all(checks.values())
        result = {"ok": True, "green": green, "checks": checks,
                  "paths": p, "rchadow_available": False, "guidance": ""}
        launch = bool(data.get("launch", False))
        approved = bool(data.get("approved", False))
        if not launch:
            result["guidance"] = ("预检完成；传 launch=true 且 approved=true 才会启动游戏"
                                  if green else "预检存在红项，需先修复")
            return result
        if not green:
            result["guidance"] = "预检未全绿，不启动；请先修复红项"
            return result
        if not approved:
            result["guidance"] = "预检通过；启动需显式 approved=true"
            return result
        spawned = self._spawn_debug(p["exe"])
        result["launched"] = spawned
        result["guidance"] = ("已启动 hoi4.exe -gdpr-compliant -debug_mode"
                              if spawned else "启动失败（进程拉起异常）")
        return result

    def launch_hoi4_debug_with_rchadow(self, data=None):
        """Rchadow 调试启动（外部工具，未内置）。"""
        return {"ok": True, "available": False,
                "guidance": "项目未内置 Rchadow（外部 Rust 工具）；"
                            "可用 validate_hoi4_debug_run(launch=true, approved=true) "
                            "直接拉起 hoi4.exe -debug_mode"}

    def _spawn_debug(self, exe):
        if not exe or not os.path.isfile(exe):
            return False
        try:
            flags = ["-gdpr-compliant", "-debug_mode"]
            if sys.platform.startswith("win"):
                subprocess.Popen([exe] + flags,
                                 cwd=os.path.dirname(exe), close_fds=True)
            else:
                subprocess.Popen([exe] + flags,
                                 cwd=os.path.dirname(exe),
                                 start_new_session=True)
            return True
        except Exception:
            return False
"""外置 AI Agent 接口：MCP Server（Model Context Protocol）

让支持 MCP 的 AI Agent（Claude Code / Cline / Cursor / DSH 等）通过标准
MCP 工具直接驱动本软件的 mod 制作能力。

实现说明：
  - 优先使用官方 `mcp` 库（若已安装：pip install mcp）
  - 否则回退到内置的**零依赖 stdio 实现**（MCP 协议 = newline-delimited
    JSON-RPC 2.0 over stdio，标准库即可），协议兼容 2024-11-05
  - 核心操作复用 api_server.ApiCore（与 HTTP API 同一套逻辑）

运行：
    python mcp_server.py [--mod <mod目录>] [--game <游戏目录>]

Agent 配置示例（Claude Code）：
    "mcpServers": { "hoi4-mod-builder": { "command": "python",
        "args": ["E:/hearts_of_iron_builder/mcp_server.py", "--mod", "E:/mods/my_mod"],
        "env": {} } }
"""
from project_paths import project_path

import argparse
import io
import json
import os
import sys


SRC = project_path("src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from api_server import ApiCore, load_settings  # noqa: E402

PROTOCOL_VERSION = "2024-11-05"


def _force_utf8_stdio():
    """MCP 协议要求 UTF-8 文本流；Windows 默认控制台编码为 GBK，需强制。"""
    for stream in (sys.stdin, sys.stdout):
        enc = getattr(stream, "encoding", "") or ""
        if enc and enc.lower() not in ("utf-8", "utf8"):
            try:
                if stream is sys.stdout:
                    sys.stdout = io.TextIOWrapper(stream.buffer, encoding="utf-8",
                                                  write_through=True)
                else:
                    sys.stdin = io.TextIOWrapper(stream.buffer, encoding="utf-8")
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════
# 工具注册表（HTTP API 与 MCP 共用同一 ApiCore）
# ══════════════════════════════════════════════════════════════

from mcp_tools import build_tools  # noqa: E402


# ══════════════════════════════════════════════════════════════
# 内置零依赖 MCP stdio 实现（协议 2024-11-05，newline JSON-RPC）
# ══════════════════════════════════════════════════════════════

def _result_to_text(result):
    """把操作结果 dict 序列化为 MCP text 内容。"""
    return json.dumps(result, ensure_ascii=False, indent=2)


class BuiltinMcpServer:
    """MCP server（stdio）：读 stdin 行 → 写 stdout 行。"""

    def __init__(self, core):
        self.core = core
        self.tools = [t for t in build_tools(core)]

    def _send(self, obj):
        sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    def _handle_message(self, msg):
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
            return
        method = msg.get("method")
        msg_id = msg.get("id")
        params = msg.get("params") or {}

        if method == "initialize":
            self._send({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "hoi4-mod-builder",
                                   "version": "1.0.0"},
                },
            })
        elif method == "notifications/initialized":
            return
        elif method == "ping":
            self._send({"jsonrpc": "2.0", "id": msg_id, "result": {}})
        elif method == "tools/list":
            self._send({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {"tools": [
                    {"name": t["name"], "description": t["description"],
                     "inputSchema": t["inputSchema"]} for t in self.tools]},
            })
        elif method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments") or {}
            tool = next((t for t in self.tools if t["name"] == name), None)
            if tool is None:
                self._send({
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {"content": [
                        {"type": "text", "text": f"未知工具: {name}"}],
                        "isError": True},
                })
                return
            try:
                result = tool["_handler"](args)
                self._send({
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {"content": [
                        {"type": "text", "text": _result_to_text(result)}],
                        "isError": False},
                })
            except Exception as e:
                self._send({
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {"content": [
                        {"type": "text", "text": f"错误: {e}"}],
                        "isError": True},
                })
        elif msg_id is not None:
            self._send({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {"content": [
                    {"type": "text", "text": f"未知方法: {method}"}],
                    "isError": True},
            })

    def run(self):
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except Exception:
                continue
            self._handle_message(msg)


def run_with_official_lib(core):
    """使用官方 mcp 库（若已安装）。"""
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("hoi4-mod-builder")
    for t in build_tools(core):
        name, desc, schema = t["name"], t["description"], t["inputSchema"]
        handler = t["_handler"]
        mcp.add_tool(name, desc, schema, handler)
    mcp.run(transport="stdio")


def main():
    _force_utf8_stdio()
    parser = argparse.ArgumentParser(description="HOI4 模组编辑器 · MCP Server")
    parser.add_argument("--mod", default="", help="mod 内容目录（缺省读 settings.json）")
    parser.add_argument("--game", default="", help="游戏根目录（缺省读 settings.json）")
    args = parser.parse_args()

    settings = load_settings()
    mod_path = args.mod or settings.get("mod_path", "")
    game_path = args.game or settings.get("HOI4_path", "")
    if not mod_path or not os.path.isdir(mod_path):
        sys.stderr.write(f"[错误] 无效的 mod 目录: {mod_path!r}\n")
        sys.exit(1)

    core = ApiCore(mod_path=mod_path, game_path=game_path)
    try:
        import mcp  # noqa: F401
        run_with_official_lib(core)
    except ImportError:
        # 未安装 mcp 库：使用内置零依赖实现
        BuiltinMcpServer(core).run()


if __name__ == "__main__":
    main()

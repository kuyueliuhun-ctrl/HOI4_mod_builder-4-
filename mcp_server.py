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

import argparse
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

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

def _tool(name, description, schema, handler):
    return {"name": name, "description": description,
            "inputSchema": schema, "_handler": handler}


def build_tools(core):
    return [
        _tool(
            "get_status",
            "获取当前 mod 与游戏目录、内容类型数量等状态信息",
            {"type": "object", "properties": {}},
            lambda args: core.status()),
        _tool(
            "list_types",
            "列出全部内容类型（角色/国策/事件/决议/科技/触发动作等 90+ 种）",
            {"type": "object", "properties": {}},
            lambda args: core.types()),
        _tool(
            "list_entities",
            "列出指定内容类型下的实体（可按国家/关键词过滤）",
            {"type": "object",
             "properties": {
                 "type": {"type": "string", "description": "内容类型 key，如 focus/event/decision/operation"},
                 "country": {"type": "string", "description": "国家 tag 过滤，如 GER（可选）"},
                 "keyword": {"type": "string", "description": "关键词过滤（可选）"},
             },
             "required": ["type"]},
            lambda args: core.list_entities(
                str(args.get("type", "")),
                str(args.get("country", "")),
                str(args.get("keyword", "")))),
        _tool(
            "get_entity",
            "获取单个实体的完整 PDX 块文本（用于读取内容后修改）",
            {"type": "object",
             "properties": {
                 "type": {"type": "string"},
                 "id": {"type": "string", "description": "实体 id，如 GER_anchluss"},
             },
             "required": ["type", "id"]},
            lambda args: core.get_entity(str(args["type"]), str(args["id"]))),
        _tool(
            "create_entity",
            "新建实体（写入该国现有文件或类型目录新文件），支持自定义块内容",
            {"type": "object",
             "properties": {
                 "type": {"type": "string"},
                 "id": {"type": "string", "description": "新实体 id"},
                 "country": {"type": "string", "description": "国家 tag（可选，优先写入该国文件）"},
                 "content": {"type": "string", "description": "自定义实体块文本（可选，缺省用模板骨架）"},
             },
             "required": ["type", "id"]},
            lambda args: core.create_entity(args)),
        _tool(
            "update_entity",
            "替换实体块内容（content 为新块文本）",
            {"type": "object",
             "properties": {
                 "type": {"type": "string"},
                 "id": {"type": "string"},
                 "content": {"type": "string", "description": "新的实体块文本"},
             },
             "required": ["type", "id", "content"]},
            lambda args: core.update_entity(str(args["type"]), str(args["id"]), args)),
        _tool(
            "delete_entity",
            "删除实体",
            {"type": "object",
             "properties": {
                 "type": {"type": "string"},
                 "id": {"type": "string"},
             },
             "required": ["type", "id"]},
            lambda args: core.delete_entity(str(args["type"]), str(args["id"]))),
        _tool(
            "create_focus_project",
            "项目级联动：一键生成国策+触发事件+决议+图标占位+本地化词条",
            {"type": "object",
             "properties": {
                 "country": {"type": "string", "description": "国家 tag，如 GER"},
                 "focus_id": {"type": "string", "description": "国策 id，如 GER_anchluss"},
                 "name": {"type": "string", "description": "中文名称（可选）"},
                 "desc": {"type": "string", "description": "中文描述（可选）"},
                 "x": {"type": "integer", "description": "国策网格 X（可选，默认 0）"},
                 "y": {"type": "integer", "description": "国策网格 Y（可选，默认 0）"},
                 "event": {"type": "boolean", "description": "是否生成触发事件（默认 true）"},
                 "decision": {"type": "boolean", "description": "是否生成决议（默认 true）"},
                 "icon": {"type": "boolean", "description": "是否生成图标占位（默认 true）"},
                 "localisation": {"type": "boolean", "description": "是否写本地化（默认 true）"},
             },
             "required": ["country", "focus_id"]},
            lambda args: core.create_focus_project(args)),
        _tool(
            "write_localisation",
            "写本地化词条到 mod 翻译文件",
            {"type": "object",
             "properties": {
                 "tag": {"type": "string", "description": "国家/前缀 tag（可选，默认 generic）"},
                 "entries": {"type": "object",
                             "description": "词条字典，如 {\"GER_anchluss\": \"德奥合并\"}"},
             },
             "required": ["entries"]},
            lambda args: core.write_localisation(args)),
        _tool(
            "validate_mod",
            "校验 mod：本地化缺失 / 国策引用悬空 / 未知引用 / 重复 ID",
            {"type": "object", "properties": {}},
            lambda args: core.validate()),
        _tool(
            "list_templates",
            "列出可用模板（可按类型/用途过滤）",
            {"type": "object",
             "properties": {
                 "type": {"type": "string", "description": "模板类型，如 focus/event（可选）"},
                 "usage": {"type": "string", "description": "用途 file/node/both（可选）"},
             }},
            lambda args: core.templates(str(args.get("type", "")), str(args.get("usage", "")))),
        _tool(
            "list_files",
            "列出指定内容类型目录下的全部文件（含路径/大小）",
            {"type": "object",
             "properties": {
                 "type": {"type": "string", "description": "内容类型 key"},
             },
             "required": ["type"]},
            lambda args: core.list_files(str(args.get("type", "")))),
        _tool(
            "read_file",
            "读取 mod 内指定相对路径文件的完整内容（用于文件级编辑/复现）",
            {"type": "object",
             "properties": {
                 "path": {"type": "string", "description": "mod 内相对路径，如 common/national_focus/GER.txt"},
             },
             "required": ["path"]},
            lambda args: core.get_file(str(args.get("path", "")))),
        _tool(
            "write_file",
            "整文件写入（新建/覆盖）：{path, content}，路径须为 mod 内相对路径",
            {"type": "object",
             "properties": {
                 "path": {"type": "string", "description": "mod 内相对路径"},
                 "content": {"type": "string", "description": "完整文件内容"},
             },
             "required": ["path", "content"]},
            lambda args: core.write_file(args)),
        _tool(
            "upload_tech_icon",
            "上传科技图标：图片 base64 写入 gfx/interface/technologies/，"
            "并自动注册/更新 GFX_<tech_id>_medium sprite 到 interface/*.gfx"
            "（科技定义文件无需修改，引擎按 sprite 名解析）",
            {"type": "object",
             "properties": {
                 "tech_id": {"type": "string", "description": "科技 id，如 GER_tiger_tank"},
                 "image_base64": {"type": "string",
                                  "description": "图片文件（png/jpg/dds 等）的 base64 编码"},
                 "filename": {"type": "string", "description": "原文件名（仅提示用，可选）"},
             },
             "required": ["tech_id", "image_base64"]},
            lambda args: core.upload_tech_icon(args)),
        _tool(
            "get_icon_manifest",
            "图标库 manifest：扫描 mod+游戏全部 gfx spriteType 定义，"
            "返回 sprite 名/贴图路径/来源/尺寸/贴图存在性",
            {"type": "object",
             "properties": {
                 "query": {"type": "string", "description": "sprite 名子串过滤（可选）"},
                 "source": {"type": "string", "description": "来源过滤 mod/vanilla（可选）"},
                 "limit": {"type": "integer", "description": "返回条数上限（默认 200）"},
             }},
            lambda args: core.get_icon_manifest(
                str(args.get("query", "")), str(args.get("source", "")),
                int(args.get("limit", 200) or 0))),
        _tool(
            "get_overlay_report",
            "mod 覆盖原版的增量报告（规则分层 + 文件级 delta）："
            "每个 mod 文件的分类（new/override/identical）、质量分级与行级增量",
            {"type": "object",
             "properties": {
                 "summary_only": {"type": "boolean",
                                  "description": "只返回统计（默认 false 返回全量文件列表）"},
             }},
            lambda args: core.get_overlay_report(
                bool(args.get("summary_only", False)))),
    ]


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

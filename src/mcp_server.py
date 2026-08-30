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

from mcp_tools import (  # noqa: E402
    NAV_TOOLS_META,
    build_tools,
    tool_category,
)
from mcp_tools import CORE_TOOLS  # noqa: E402
from mcp_validator import validate_call  # noqa: E402


# ══════════════════════════════════════════════════════════════
# A+B 分类方案：核心精选 + 分类白名单 + 导航工具
# ══════════════════════════════════════════════════════════════

def _schema_obj(properties, required=None):
    return {"type": "object", "properties": properties,
            "required": required or []}


def _schema_str(desc=""):
    return {"type": "string", "description": desc}


def _schema_obj_type(desc=""):
    return {"type": "object", "description": desc}


def _validated_invoke(tool, args):
    """调用前执行 MCP 校验器，有 error 直接抛 ValueError。"""
    issues = [i for i in validate_call(tool, args) if i.severity == "error"]
    if issues:
        msgs = "；".join(i.message for i in issues[:5])
        raise ValueError("MCP 校验拦截: %s" % msgs)
    return tool["_handler"](args)


def _nav_tool(name, description, schema, handler):
    return {"name": name, "description": description,
            "inputSchema": schema, "_handler": handler}


def _build_nav_tools(all_tools):
    """导航工具：概览 / 查 schema / 通用调度（全部工具皆可经 invoke_tool 调用）。"""

    def _overview(_args):
        cats = {}
        for t in all_tools:
            cats.setdefault(tool_category(t["name"]), []).append(t["name"])
        return {
            "total": len(all_tools),
            "categories": {k: sorted(v) for k, v in sorted(cats.items())},
            "note": "未直接暴露的工具请用 invoke_tool 调用；用 get_tool_schema 查参数。",
        }

    def _schema(args):
        name = str(args.get("name", ""))
        t = next((x for x in all_tools if x["name"] == name), None)
        if t is None:
            raise ValueError("未知工具: %s" % name)
        return {"name": t["name"], "description": t["description"],
                "inputSchema": t["inputSchema"],
                "category": tool_category(name)}

    def _invoke(args):
        name = str(args.get("name", ""))
        call_args = args.get("args") or {}
        t = next((x for x in all_tools if x["name"] == name), None)
        if t is None:
            raise ValueError("未知工具: %s" % name)
        return _validated_invoke(t, call_args)

    handlers = {"list_tools_overview": _overview,
                "get_tool_schema": _schema,
                "invoke_tool": _invoke}
    out = []
    for name, desc, schema in NAV_TOOLS_META:
        out.append(_nav_tool(name, desc, schema, handlers[name]))
    return out


def _exposed_names(all_tools):
    """A+B 暴露名单：核心精选 + 导航；MCP_EXPOSE_CATEGORIES 可追加分类或 all。"""
    names = set(CORE_TOOLS)
    env = os.environ.get("MCP_EXPOSE_CATEGORIES", "").strip()
    if env.lower() == "all":
        names = {t["name"] for t in all_tools}
    else:
        cats = {c.strip() for c in env.split(",") if c.strip()}
        for t in all_tools:
            if tool_category(t["name"]) in cats:
                names.add(t["name"])
    names.update({name for name, _desc, _schema in NAV_TOOLS_META})
    return names


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
        self.all_tools = [t for t in build_tools(core)]
        self.all_tools.extend(_build_nav_tools(self.all_tools))
        self.exposed_names = _exposed_names(self.all_tools)
        self.tools = [t for t in self.all_tools
                      if t["name"] in self.exposed_names]

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
                    "capabilities": {"tools": {}, "resources": {},
                                     "prompts": {}},
                    "serverInfo": {"name": "hoi4-mod-builder",
                                   "version": "1.0.0"},
                },
            })
        elif method == "notifications/initialized":
            return
        elif method == "ping":
            self._send({"jsonrpc": "2.0", "id": msg_id, "result": {}})
        elif method == "resources/list":
            self._send({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {"resources": self._list_resources()},
            })
        elif method == "resources/read":
            uri = params.get("uri", "")
            try:
                content = self._read_resource(uri)
                self._send({
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {"contents": [
                        {"uri": uri, "mimeType": "application/json",
                         "text": content}]},
                })
            except ValueError as e:
                self._send({
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {"content": [
                        {"type": "text", "text": f"资源错误: {e}"}],
                        "isError": True},
                })
        elif method == "prompts/list":
            self._send({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {"prompts": self._list_prompts()},
            })
        elif method == "prompts/get":
            name = params.get("name", "")
            args = params.get("arguments") or {}
            try:
                prompt = self._get_prompt(name, args)
                self._send({
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {"description": prompt["description"],
                               "messages": prompt["messages"]},
                })
            except ValueError as e:
                self._send({
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {"content": [
                        {"type": "text", "text": f"提示错误: {e}"}],
                        "isError": True},
                })
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
            tool = next((t for t in self.all_tools if t["name"] == name), None)
            if tool is None:
                self._send({
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {"content": [
                        {"type": "text", "text": f"未知工具: {name}"}],
                        "isError": True},
                })
                return
            try:
                result = _validated_invoke(tool, args)
                self._log_call(name, args, ok=True)
                self._send({
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {"content": [
                        {"type": "text", "text": _result_to_text(result)}],
                        "isError": False},
                })
            except Exception as e:
                self._log_call(name, args, ok=False)
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

    # ---------- resources / prompts（B3 批二 ①） ----------

    def _log_call(self, name, args, ok=True):
        """工具调用审计埋点（B3 批二②）。"""
        try:
            self.core.log_tool_call(name, args, ok=ok)
        except Exception:
            pass

    @staticmethod
    def _json_text(obj):
        return json.dumps(obj, ensure_ascii=False, indent=2)

    def _list_resources(self):
        return [
            {"uri": "hoi4://status", "name": "运行状态",
             "description": "当前 mod/game 路径与内容类型数量",
             "mimeType": "application/json"},
            {"uri": "hoi4://tools/overview", "name": "工具分类目录",
             "description": "全部 MCP 工具按分类概览",
             "mimeType": "application/json"},
            {"uri": "hoi4://terms", "name": "词条库",
             "description": "本地化/词条库（可带 ?keyword= 过滤）",
             "mimeType": "application/json"},
            {"uri": "hoi4://docs/rhoiscribe", "name": "RHoiScribe 补全文档",
             "description": "RHoiScribe 缺失能力落地与待拍板清单",
             "mimeType": "text/markdown"},
            {"uri": "hoi4://docs/mcp", "name": "MCP 接口规格",
             "description": "MCP 工具清单与 A+B 分类说明",
             "mimeType": "text/markdown"},
            {"uri": "hoi4://docs/quickstart", "name": "从零建 Mod 快速开始",
             "description": "最小可运行 mod 的端到端示例（create_mod → 内容 → 本地化 → 校验）",
             "mimeType": "text/markdown"},
            {"uri": "hoi4://docs/user", "name": "MCP 用户指南",
             "description": "MCP 使用者的知识文档（分类/正确范式/踩坑/模板/工作流）",
             "mimeType": "text/markdown"},
            {"uri": "hoi4://docs/developer", "name": "MCP 开发者指南",
             "description": "MCP 开发者的知识文档（注册/schema/校验器/模板/工作流）",
             "mimeType": "text/markdown"},
            {"uri": "hoi4://docs/pitfalls", "name": "全项目踩坑索引",
             "description": "按类别组织的踩坑索引；开发/使用前先查对应分类",
             "mimeType": "text/markdown"},
            {"uri": "hoi4://templates/mcp", "name": "MCP 正确调用模板",
             "description": "正确且无报错的 MCP 调用模板清单",
             "mimeType": "application/json"},
        ]

    def _read_resource(self, uri):
        from project_paths import PROJECT_ROOT
        if uri == "hoi4://status":
            return self._json_text(self.core.status())
        if uri == "hoi4://tools/overview":
            cats = {}
            for t in self.all_tools:
                cats.setdefault(tool_category(t["name"]), []).append(t["name"])
            return self._json_text({
                "total": len(self.all_tools),
                "categories": {k: sorted(v) for k, v in sorted(cats.items())}})
        if uri == "hoi4://terms" or uri.startswith("hoi4://terms?"):
            from urllib.parse import parse_qs
            qs = uri.split("?", 1)[1] if "?" in uri else ""
            q = parse_qs(qs)
            keyword = q.get("keyword", [""])[0] if q else ""
            try:
                return self._json_text(
                    self.core.search_terms({"keyword": keyword, "limit": 50}))
            except Exception as e:
                return self._json_text({"error": str(e)})
        if uri in ("hoi4://docs/rhoiscribe", "hoi4://docs/mcp",
                   "hoi4://docs/quickstart", "hoi4://docs/user",
                   "hoi4://docs/developer", "hoi4://docs/pitfalls"):
            doc_map = {
                "rhoiscribe": "RHoiScribe知识映射与补全.md",
                "quickstart": "MCP_quickstart.md",
                "mcp": "MCP与接口规格.md",
                "user": "MCP用户指南.md",
                "developer": "MCP开发者指南.md",
                "pitfalls": "踩坑索引.md",
            }
            key = uri.split("/")[-1]
            fname = doc_map[key]
            fp = os.path.join(PROJECT_ROOT, "docs", fname)
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                return str(e)
        if uri == "hoi4://templates/mcp":
            tpl_dir = os.path.join(PROJECT_ROOT, "templates", "mcp")
            items = []
            for dirpath, _dirs, names in os.walk(tpl_dir):
                for name in sorted(names):
                    if not name.endswith(".json"):
                        continue
                    fp = os.path.join(dirpath, name)
                    try:
                        with open(fp, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        data["file"] = os.path.relpath(fp, PROJECT_ROOT).replace("\\", "/")
                        items.append(data)
                    except Exception as e:
                        items.append({"file": os.path.relpath(fp, PROJECT_ROOT),
                                      "error": str(e)})
            return self._json_text({"total": len(items), "templates": items})
        raise ValueError("未知资源: %s" % uri)

    def _list_prompts(self):
        return [
            {"name": "create_focus", "description": "新建一个国策（含可用性/前置/奖励骨架）",
             "arguments": [
                 {"name": "country", "description": "国家 TAG", "required": False},
                 {"name": "focus_id", "description": "国策 id", "required": False}]},
            {"name": "validate_project", "description": "跑红黄绿校验并按结果修复",
             "arguments": []},
            {"name": "fix_error_log", "description": "分析 error.log 并解释/修复",
             "arguments": [
                 {"name": "path", "description": "error.log 相对 mod 路径",
                  "required": False}]},
            {"name": "edit_script_block", "description": "块级编辑一个脚本文件",
             "arguments": [
                 {"name": "path", "description": "文件相对路径", "required": False},
                 {"name": "block", "description": "块名", "required": False}]},
            {"name": "create_mod_from_scratch", "description": "从零新建一个 mod 并添加国策/事件/本地化的完整步骤",
             "arguments": [
                 {"name": "name", "description": "模组显示名", "required": False},
                 {"name": "folder_name", "description": "文件夹名", "required": False},
                 {"name": "mod_folder_path", "description": "mod 内容根目录", "required": False}]},
            {"name": "mcp_workflow", "description": "MCP 使用/开发工作流：先读知识文档与踩坑索引，再按模板调用/扩展工具",
             "arguments": [
                 {"name": "role", "description": "user 或 developer；默认 user", "required": False}]},
        ]

    def _get_prompt(self, name, args):
        country = str(args.get("country", ""))
        focus_id = str(args.get("focus_id", ""))
        path = str(args.get("path", ""))
        block = str(args.get("block", ""))
        mod_name = str(args.get("name", ""))
        folder = str(args.get("folder_name", ""))
        mod_folder = str(args.get("mod_folder_path", ""))
        if name == "create_focus":
            text = ("用 create_focus_project 或 create_entity 新建国策；country=%s focus=%s。"
                    "先 list_tools_overview 找可用工具，再按需补 localisation。"
                    ) % (country or "<TAG>", focus_id or "<id>")
        elif name == "validate_project":
            text = ("1) 调用 validate_project 得到红/黄/绿；2) 红色项（重复 id 等）立即修复；"
                    "3) 黄色项（引用/本地化缺失）用 find_references/explain_diagnostic 定位修复；"
                    "4) 修复后重新 validate_project 确认。")
        elif name == "fix_error_log":
            text = ("调用 analyze_error_log（path=%s），对每条用 explain_diagnostic 解释并修复；"
                    "error_log_path 可用 discover_environment 获取。") % (path or "<path>")
        elif name == "edit_script_block":
            text = ("用 edit_script_file 编辑 path=%s 的块 %s：先 dry_run=true 看 diff，"
                    "确认后 dry_run=false 落盘。") % (path or "<path>", block or "<block>")
        elif name == "create_mod_from_scratch":
            text = (
                "从零新建 mod 的标准流程：\n"
                "1) 先 discover_environment / get_status 确认 mod 根目录与游戏路径。\n"
                "2) 调用 create_mod：name=%s folder_name=%s mod_folder_path=%s；"
                "先 dry_run=true 预览文件清单，确认后 dry_run=false 且 approved=true 落盘。\n"
                "3) 用 list_tools_overview 查看全部隐藏工具；本任务常用 generate_focus_package、"
                "generate_event、write_localisation、validate_project。\n"
                "4) 若这些工具不在 tools/list 中，用 get_tool_schema 查参数，再经 invoke_tool 调用。\n"
                "5) 添加内容后调用 validate_project / validate_mod 修复红黄项。\n"
                "6) 可读取资源 hoi4://docs/quickstart 获取最小可运行示例。"
            ) % (mod_name or "<name>", folder or "<folder>",
                 mod_folder or "<mod_folder_path>")
        elif name == "mcp_workflow":
            role = str(args.get("role", "user") or "user")
            if role == "developer":
                text = (
                    "MCP 开发者工作流：\n"
                    "1) 读 hoi4://docs/developer 和 hoi4://docs/pitfalls 对应分类；\n"
                    "2) 在 src/mcp_tools.py 注册/修改工具，schema/description 必须符合正确范式；\n"
                    "3) 在 src/mcp_validator.py 补规则（如新安全要求）；\n"
                    "4) 把正确调用写入 templates/mcp/<category>/ 并用 tests/test_mcp_templates.py 回归；\n"
                    "5) 运行 python tools/check_mcp_contracts.py 与 tests/test_mcp_validator.py；\n"
                    "6) 同步 docs/MCP开发者指南.md、docs/MCP用户指南.md、docs/踩坑索引.md。"
                )
            else:
                text = (
                    "MCP 使用者工作流：\n"
                    "1) 读 hoi4://docs/user 和 hoi4://docs/pitfalls 对应分类；\n"
                    "2) 先 list_tools_overview 看分类，get_tool_schema 查参数；\n"
                    "3) 从 hoi4://templates/mcp 或 templates/mcp/ 复制正确调用；\n"
                    "4) 写操作先 dry_run，需要 approved 的确认后再落盘；\n"
                    "5) 完成后 validate_project 校验。"
                )
        else:
            raise ValueError("未知提示: %s" % name)
        return {
            "description": "工作流提示：%s" % name,
            "messages": [{"role": "user",
                          "content": {"type": "text", "text": text}}],
        }

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
    all_tools = [t for t in build_tools(core)]
    all_tools.extend(_build_nav_tools(all_tools))
    exposed_names = _exposed_names(all_tools)
    mcp = FastMCP("hoi4-mod-builder")
    for t in all_tools:
        if t["name"] not in exposed_names:
            continue  # A+B：只注册核心精选 + 白名单分类 + 导航工具
        name, desc, schema = t["name"], t["description"], t["inputSchema"]
        def handler(args, _tool=t):
            return _validated_invoke(_tool, args)
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

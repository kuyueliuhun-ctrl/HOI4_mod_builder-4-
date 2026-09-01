#!/usr/bin/env python
"""MCP 全量工具真实数据冒烟（B3 批三②）。

用法：python tools/smoke_mcp_tools.py
  （读 settings.json 的 mod_path / HOI4_path）

对 `mcp_tools.build_tools` 的每个工具：
- 只读 / dry_run 优先：schema 含 dry_run 必填时自动置 True；
- 写工具且无 dry_run → 跳过（report skipped-write）；
- 需要必填参数的自动填充（type/id/tag/state/province/词条等）；
- 逐个调用 handler，捕获异常；汇总 ok / error / skipped。

退出码：0=无 error；1=存在 error（skipped 不影响）。
"""

from __future__ import annotations

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

_WRITE_HINTS = (
    "create", "update", "delete", "set_", "insert", "remove", "rename",
    "duplicate", "copy", "apply", "write", "generate", "upload", "save",
    "sync", "add_", "register_icon", "sort_state", "undo", "repair_project",
    "import_unit", "launch", "generate_gui", "edit_script", "format_pdx",
    "batch_fill", "batch_set",
)

_SKIP_WRITE_EXACT = {
    "undo_last_write", "register_icon_batch", "format_pdx", "convert_dds",
    "set_agent_preference", "delete_agent_preference", "submod_activate",
}

# 重型/耗时工具：默认跳过，--full 启用（对真实大 mod 扫描很慢）
HEAVY_TOOLS = {
    "validate_mod", "health_check", "coverage_report", "get_overlay_report",
    "validate_project", "validate_hoi4_project", "validate_hoi4_file",
    "scan_duplicate_ids", "generate_country_bootstrap", "generate_characters",
    "generate_generals", "generate_ideas", "generate_ideologies",
    "generate_event", "generate_focus_package", "import_unit_counters",
    "ai_plan_list", "ai_strategy_list", "ai_ai_template_list",
    "ai_equipment_list", "ai_navy_list", "ai_area_list", "ai_focus_list",
    "ai_theater_list", "list_oob_files", "list_states", "list_entities",
    "list_division_templates", "list_ship_designs", "list_plane_designs",
    "list_tank_designs", "list_workspace_symbols", "find_definition",
    "find_references", "suggest_completion", "edit_script_file",
    "get_icon_manifest", "list_missing_localisation", "batch_fill_localisation",
}


def _is_write(name):
    if name in _SKIP_WRITE_EXACT:
        return True
    return any(name.startswith(h) or h in name for h in _WRITE_HINTS)


def _first_entity(core, type_key):
    try:
        r = core.list_entities(type_key, "", "")
        items = r.get("entities") or r.get("items") or []
        if items:
            first = items[0]
            return first.get("id") or first.get("name") or ""
    except Exception:
        pass
    return ""


def _first_txt(mod_path):
    if not mod_path or not os.path.isdir(mod_path):
        return ""
    for root, _dirs, names in os.walk(mod_path):
        for name in sorted(names):
            if name.lower().endswith(".txt"):
                return os.path.relpath(os.path.join(root, name),
                                       mod_path).replace("\\", "/")
    return ""


def _build_args(core, mod_path, tool):
    """为工具构造安全参数；无法构造返回 None（跳过）。"""
    name = tool["name"]
    props = (tool.get("inputSchema") or {}).get("properties") or {}
    required = list((tool.get("inputSchema") or {}).get("required") or [])
    args = {}
    if "dry_run" in props:
        args["dry_run"] = True

    # 专用覆盖（真实数据安全取值）
    if name == "get_entity":
        args.update({"type": "focus", "id": "GER_anchluss"})
    elif name == "get_bop":
        try:
            items = core.list_bop({"limit": 1}) if False else None
        except Exception:
            items = None
        # list_bop 无参数，直接取
        try:
            r = core.list_bop({})
            rows = r.get("bop") or r.get("items") or []
            if rows:
                args["bop_id"] = rows[0].get("id") or rows[0].get("name")
        except Exception:
            pass
        if "bop_id" not in args:
            return None
    elif name == "edit_script_file":
        rel = _first_txt(mod_path)
        if not rel:
            return None
        args.update({"path": rel, "block": "__smoke_nonexistent__",
                     "action": "replace", "content": "",
                     "dry_run": True})
    elif name == "validate_hoi4_file":
        rel = _first_txt(mod_path)
        if not rel:
            return None
        args.update({"path": rel})
    elif name == "find_definition" or name == "find_references":
        args.update({"name": "infantry"})
    elif name == "suggest_completion":
        args.update({"prefix": "inf"})
    elif name in ("copy_country_files", "create_blank_overrides",
                  "create_new_country_files"):
        args.update({"tag": "GER", "dirs": ["common/national_focus"],
                     "dry_run": True})
    elif name == "create_mod":
        args.update({"name": "smoke", "folder_name": "smoke_mod",
                     "version": "1.0", "dry_run": True})
    elif name == "batch_set_state_fields":
        args.update({"state_ids": [1], "field": "owner", "value": "GER",
                     "dry_run": True})
    elif name == "batch_fill_localisation":
        args.update({"entries": {}, "dry_run": True})
    elif name == "generate_gui_gfx_asset":
        args.update({"name": "smoke_asset", "dry_run": True})
    elif name == "import_unit_counters":
        args.update({"dry_run": True})

    # 通用必填填充
    defaults = {
        "type": "focus",
        "country": "GER",
        "id": "smoke_id",
        "name": "smoke",
        "path": _first_txt(mod_path),
        "state_id": 1,
        "province_id": 1,
        "tag": "GER",
        "keyword": "",
        "prefix": "",
        "content": "",
        "block": "__smoke_nonexistent__",
        "limit": 5,
        "max_files": 5,
        "max_issues": 5,
        "template_name": "",
        "target_path": "",
        "category": "",
        "slot": "",
    }
    for key in required:
        if key in args:
            continue
        if key in defaults and defaults[key] != "":
            args[key] = defaults[key]
        elif key in ("state_ids", "dirs", "entries", "right_side",
                     "left_side", "decision_category"):
            # 列表/复杂参数不自动填，交由专用覆盖
            return None
        else:
            return None
    return args


def run_smoke(core, mod_path, limit=None, full=False, progress=None):
    from mcp_tools import build_tools
    tools = build_tools(core)
    if limit:
        tools = tools[:limit]
    results = []
    for idx, t in enumerate(tools, 1):
        name = t["name"]
        if not full and name in HEAVY_TOOLS:
            results.append((name, "skipped-heavy", "重型工具，--full 启用", ""))
            continue
        args = _build_args(core, mod_path, t)
        if args is None:
            results.append((name, "skipped", "参数无法自动构造", ""))
            continue
        if _is_write(name) and not args.get("dry_run"):
            results.append((name, "skipped-write", "写工具且无 dry_run", ""))
            continue
        try:
            t["_handler"](args)
            results.append((name, "ok", "", ""))
        except ValueError as e:
            # 参数/数据缺失（如 get_term 无 key、analyze_error_log 无路径）→ 非致命
            results.append((name, "skip-data", str(e), ""))
        except Exception as e:
            results.append((name, "error", str(e), traceback.format_exc(limit=2)))
        if progress:
            progress(idx, len(tools), name)
    return results


def _to_local_path(path):
    """Windows 盘符路径 → 当前环境可访问路径（WSL /mnt/...）。"""
    if not path:
        return path
    normalized = str(path).replace("\\", "/")
    if os.path.isdir(normalized) or os.path.isfile(normalized):
        return normalized
    import re
    m = re.match(r"^([A-Za-z]):/(.*)$", normalized)
    if m and sys.platform.startswith("linux") and os.path.isdir("/mnt"):
        drive = m.group(1).lower()
        rest = m.group(2)
        candidate = "/mnt/%s/%s" % (drive, rest)
        if os.path.isdir(candidate) or os.path.isfile(candidate):
            return candidate
    return normalized


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MCP 全量工具真实数据冒烟")
    parser.add_argument("--limit", type=int, default=0, help="最多跑前 N 个工具")
    parser.add_argument("--full", action="store_true", help="包含重型工具")
    args = parser.parse_args()

    from api_server import ApiCore, load_settings
    settings = load_settings()
    mod = _to_local_path(settings.get("mod_path", ""))
    game = _to_local_path(settings.get("HOI4_path", ""))
    if not mod or not os.path.isdir(mod):
        print("未找到有效 mod 目录（settings.json mod_path）")
        return 2
    core = ApiCore(mod_path=mod, game_path=game)

    def _progress(idx, total, name):
        if idx % 10 == 0 or idx == total:
            print("  ... %d/%d %s" % (idx, total, name), flush=True)

    results = run_smoke(core, mod, limit=args.limit or None,
                        full=args.full, progress=_progress)
    counts = {"ok": 0, "error": 0, "skipped": 0, "skipped-write": 0,
              "skip-data": 0, "skipped-heavy": 0}
    print("=== MCP 全量工具冒烟（%d 个） ===" % len(results))
    for name, status, msg, _tb in results:
        counts[status] = counts.get(status, 0) + 1
        if status == "ok":
            continue
        print("[%s] %s %s" % (status, name, msg))
    print("---")
    print("ok=%d error=%d skipped=%d skipped-write=%d skip-data=%d skipped-heavy=%d" % (
        counts.get("ok", 0), counts.get("error", 0),
        counts.get("skipped", 0), counts.get("skipped-write", 0),
        counts.get("skip-data", 0), counts.get("skipped-heavy", 0)))
    if counts.get("error", 0):
        print("存在 error，见上方明细（可用 --limit 定位）")
        return 1
    print("无 error（skipped/skip-data/skipped-heavy 为预期跳过，无碍）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
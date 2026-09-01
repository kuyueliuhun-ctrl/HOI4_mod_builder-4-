#!/usr/bin/env python3
"""四层分离依赖方向静态检查（契约 #10）。

检查规则：
- 算法层模块（ALGO）不得 import UI 层 / 信号槽层模块；
- 绘图层模块（RENDER）不得 import UI 层 / 信号槽层模块；
- 允许：标准库、PyQt6（值类型/控件在算法层也应避免，但本检查只拦项目内反向依赖）。

用法：
    python tools/check_layer_deps.py
退出码：0 = 通过；1 = 存在违规。
"""

from __future__ import annotations

import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".venv", ".venv-linux", ".git", "__pycache__", ".runtime",
             "node_modules", "dist", "data", "_scenario_forge", "templates",
             "design_templates"}

# 算法层：纯逻辑/数据/解析（无 Qt 控件）
ALGO_MODULES = {
    "pdx_parser", "focus_parser", "tree_node", "focus_algo", "focus_processor",
    "ai_loader", "bop_loader", "oob_loader", "ship_design", "plane_design",
    "tank_design", "map_loader", "map_vector", "map_fill", "map_region_ops",
    "state_loader", "state_edit_ops", "state_build_ops", "building_lib",
    "content_types", "entity_scanner", "oob_format", "overlay_rules",
    "icon_manifest", "unit_counter_library", "validation", "export_health",
    "design_template", "game_data",
    "playset_loader", "mod_stack",
}

# 绘图层：图形项/绘制（可依赖算法层，禁止依赖 UI/信号槽层）
RENDER_MODULES = {
    "focus_render", "focus_renderer", "map_canvas", "tech_view", "tree_model",
}

# 基础设施（原子写/图标写/撤销等工具）：任何层都可调用，不作为反向依赖违规
INFRA_MODULES = {"write_utils", "icon_ops", "tech_icon_ops", "undo_mgr"}

# UI 层模块（控件/布局/样式/对话框/视图）
UI_MODULES = {
    "workbench", "main_window", "ai_ui_common", "menu_factory",
    "designer_common", "theme", "focus_view", "generic_tree_editor",
    "tree_info_dialog", "translation_widget", "country_filter",
    "reference_panel", "ui_untitled", "focus_base_builder",
}
UI_SUFFIXES = ("_dialog", "_view", "_widget", "_panel", "_picker",
               "_manager_dialog", "_library_dialog", "_editor_dialog")

# 信号槽层模块（控制器/路由/接口编排）
CTRL_MODULES = {
    "focus_view_ctrl", "app_routes", "api_server", "mcp_server",
}

IMPORT_RE = re.compile(
    r'^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))')


def _base(name):
    return name.split(".")[0]


def _is_ui_module(name):
    base = _base(name)
    if base in RENDER_MODULES or base in INFRA_MODULES:
        return False
    if base in UI_MODULES:
        return True
    return any(base.endswith(suf) for suf in UI_SUFFIXES)


def _is_ctrl_module(name):
    return _base(name) in CTRL_MODULES


def _py_files(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".py"):
                out.append(os.path.join(dirpath, fn))
    return out


def main():
    violations = []
    checked = 0
    for path in sorted(_py_files(PROJECT_ROOT)):
        rel = os.path.relpath(path, PROJECT_ROOT).replace("\\", "/")
        base = os.path.splitext(os.path.basename(path))[0]
        layer = None
        if base in ALGO_MODULES:
            layer = "algo"
        elif base in RENDER_MODULES:
            layer = "render"
        if layer is None:
            continue
        checked += 1
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            continue
        for lineno, line in enumerate(lines, 1):
            m = IMPORT_RE.match(line)
            if not m:
                continue
            target = m.group(1) or m.group(2)
            tbase = _base(target)
            if tbase in ("PyQt6", "PySide6", "numpy", "PIL"):
                continue
            if _is_ui_module(target) or _is_ctrl_module(target):
                violations.append(
                    "%s:%d: %s 层模块反向依赖 %s" % (rel, lineno, layer, tbase))
    if violations:
        print("四层依赖方向违规 %d 处：" % len(violations))
        for v in violations:
            print("  " + v)
        return 1
    print("依赖方向检查 OK（%d 个算法/绘图层模块）" % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main())

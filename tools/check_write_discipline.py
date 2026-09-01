"""写入纪律静态扫描器（可执行契约 #1）

扫描项目源码中绕过 write_utils.atomic_write_text / icon_ops.write_file_utf8
的直接文本写入（open(..., "w"/"a")、Path.write_text 等），防止新的
mod 内容写入绕过原子写与编码契约。

用法：
    python tools/check_write_discipline.py                 # 扫描项目根
    python tools/check_write_discipline.py --root <dir>    # 指定根目录
    python tools/check_write_discipline.py --json          # JSON 输出

退出码：
    0 = 无违规（未登记直写）
    1 = 存在未登记的文本直写（违反契约）

豁免机制（tools/write_discipline_allowlist.json）：
    {
      "modules": { "<相对路径.py>": {"reason": "..."} },          # 模块级豁免
      "lines": { "<相对路径.py>": {"lines": [12, 34], "reason": "..."} }  # 精确行豁免
    }
    新写入必须走原子写；确需直写时登记豁免并写明理由（配置类/程序数据等）。
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWLIST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "write_discipline_allowlist.json")

# 扫描时跳过的目录/文件
SKIP_DIRS = {".venv", ".venv-linux", ".venv314", ".git", "__pycache__", "dist", "portable",
             "node_modules", "data", "_scenario_forge", "tests", "prototypes",
             ".runtime", ".idea", ".ruff_cache", ".jspace"}


def _skip_dir(name):
    return name in SKIP_DIRS or name.startswith(".venv")
# tests 目录豁免理由：契约测试自身用临时目录夹具验证行为（tempfile + 直写），
# 其写入对象是测试临时目录而非 mod 内容，不受本纪律约束。
SKIP_FILES = {"write_utils.py"}  # 原子写实现本身

# 允许直接写的二进制操作（图片复制等，不破坏文本契约）——仅 info 提示
_BINARY_OK = True


def _static_path_hint(value):
    """静态提取写入目标提示：字符串常量 / os.path.join(..., "尾部字面量")。"""
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    if isinstance(value, ast.Call):
        func = value.func
        if isinstance(func, ast.Attribute) and func.attr == "join":
            base = func.value
            is_os_path = (
                isinstance(base, ast.Name) and base.id in ("os", "path")) or (
                isinstance(base, ast.Attribute) and base.attr == "path")
            if (is_os_path and value.args
                    and isinstance(value.args[-1], ast.Constant)
                    and isinstance(value.args[-1].value, str)):
                return value.args[-1].value
    return None


def _module_const_strings(tree):
    """收集模块级「名字 → 路径提示」常量（open 目标解析用，一层回溯）。"""
    consts = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = [t for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) \
                and isinstance(node.target, ast.Name):
            targets = [node.target]
        else:
            continue
        hint = _static_path_hint(node.value)
        if hint is not None:
            for t in targets:
                consts[t.id] = hint
    return consts


def _resolve_write_target(node, consts):
    """尽力解析 open(path, ...) 的写入目标提示；无法静态解析返回 None。"""
    if not node.args:
        return None
    arg = node.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    if isinstance(arg, ast.Name) and arg.id in consts:
        return consts[arg.id]
    return None


def _target_allowed(target, patterns):
    """豁免 allow_paths 匹配：后缀一致或 fnmatch 命中（统一 / 分隔）。"""
    t = (target or "").replace("\\", "/")
    for pat in patterns:
        p = str(pat).replace("\\", "/")
        if t.endswith(p) or fnmatch.fnmatch(t, p):
            return True
    return False


def scan_file(path, rel):
    """扫描单个文件，返回 (violations, registered, binaries)。

    violation: 未登记的文本直写（违反契约）
    registered: 已登记豁免的直写（信息）
    binaries: 二进制写入（信息）

    P2-8：模块级豁免可带 ``allow_paths``（后缀/fnmatch 模式列表）——
    豁免模块内的直写若能静态解析出目标且不匹配任何模式，改判违规。
    无法静态解析的目标维持放行（尽力而为的审计，不做误报）。
    """
    violations, registered, binaries = [], [], []
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception:
        return violations, registered, binaries
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return violations, registered, binaries

    allow = _load_allowlist()
    module_entry = allow.get("modules", {}).get(rel)
    module_allowed = module_entry is not None
    allow_paths = (module_entry or {}).get("allow_paths") or None
    line_allow = set((allow.get("lines", {}) or {}).get(rel, {})
                     .get("lines", []))
    consts = _module_const_strings(tree)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        kind = _call_write_kind(node)
        if kind is None:
            continue
        entry = (rel, node.lineno, kind)
        if kind == "binary":
            binaries.append(entry)
            continue
        if module_allowed or node.lineno in line_allow:
            if module_allowed and allow_paths:
                target = _resolve_write_target(node, consts)
                if target is not None \
                        and not _target_allowed(target, allow_paths):
                    violations.append(entry)
                    continue
            registered.append(entry)
        else:
            violations.append(entry)
    return violations, registered, binaries


def _call_write_kind(node):
    """判断 Call 是否为文本/二进制写入入口。返回 'text'/'binary'/None。"""
    func = node.func
    name = None
    if isinstance(func, ast.Name):
        name = func.id
    elif isinstance(func, ast.Attribute):
        name = func.attr

    if name == "open":
        mode = "r"
        if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
            mode = str(node.args[1].value)
        for kw in node.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                mode = str(kw.value.value)
        if not any(c in mode for c in ("w", "a", "x")):
            return None
        return "binary" if "b" in mode else "text"
    if name == "write_text":
        return "text"
    if name == "write_bytes":
        return "binary"
    if name in ("copy", "copyfile", "copy2", "move"):
        # shutil 复制：二进制安全，仅提示
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) \
                and func.value.id == "shutil":
            return "binary"
    return None


_allow_cache = None


def _load_allowlist():
    global _allow_cache
    if _allow_cache is not None:
        return _allow_cache
    try:
        with open(ALLOWLIST_PATH, "r", encoding="utf-8") as f:
            _allow_cache = json.load(f)
    except Exception:
        _allow_cache = {"modules": {}, "lines": {}}
    return _allow_cache


def scan_root(root):
    """扫描根目录，返回 (violations, registered, binaries, checked_files)。"""
    violations, registered, binaries = [], [], []
    checked = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not _skip_dir(d)]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            if fn in SKIP_FILES:
                continue
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, root).replace(os.sep, "/")
            if rel.startswith("tools/"):
                # tools 内脚本登记机制不同：整体豁免由 allowlist 的 modules 决定
                pass
            v, r, b = scan_file(fp, rel)
            violations.extend(v)
            registered.extend(r)
            binaries.extend(b)
            checked += 1
    return violations, registered, binaries, checked


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=PROJECT_ROOT)
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args(argv)

    violations, registered, binaries, checked = scan_root(args.root)

    if args.json:
        print(json.dumps({
            "checked_files": checked,
            "violations": [{"file": f, "line": l, "kind": k}
                           for f, l, k in violations],
            "registered": [{"file": f, "line": l, "kind": k}
                           for f, l, k in registered],
            "binary_writes": [{"file": f, "line": l, "kind": k}
                              for f, l, k in binaries],
        }, ensure_ascii=False, indent=2))
    else:
        print("写入纪律扫描：%d 个文件" % checked)
        for f, l, k in violations:
            print("  [违规] %s:%d  %s" % (f, l, k))
        for f, l, k in registered:
            print("  [豁免] %s:%d  %s" % (f, l, k))
        for f, l, k in binaries:
            print("  [二进制] %s:%d  %s" % (f, l, k))
        print("违规 %d / 已登记豁免 %d / 二进制写入 %d"
              % (len(violations), len(registered), len(binaries)))

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())

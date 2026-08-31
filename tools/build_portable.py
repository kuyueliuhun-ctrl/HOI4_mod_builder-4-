#!/usr/bin/env python3
"""便携版打包脚本：生成“解压即用、无需预装 Python/Qt”的 Windows 便携包。

用法（在 Windows 构建机上运行）：
    python tools/build_portable.py                 # 生成 dist/HOI4编辑器-便携版/
    python tools/build_portable.py --zip           # 额外压缩为 zip
    python tools/build_portable.py --output D:/out # 自定义输出目录

原理：
1. 复制当前 Windows Python 完整安装目录到 便携包/portable/python/；
2. 用包内 python.exe 安装 requirements.txt（含 PyQt6，自带 Qt）；
3. 复制项目源码、文档、模板等运行所需文件；
4. 生成 启动.bat，直接调用包内 Python，不再需要系统 Python。

限制：
- 当前版本仅支持 Windows 便携包；Linux/WSL 仍使用 launcher.py 自动创建虚拟环境。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PORTABLE_PYTHON_REL = Path("portable") / "python"
DEFAULT_OUTPUT = PROJECT_ROOT / "dist" / "HOI4编辑器-便携版"

# 需要复制进便携包的项目目录（运行期必需）。
COPY_DIRS = (
    "src",
    "docs",
    "templates",
    "translations",
    "tools",
    "unit_counter_library",
    "常用代码",
    "游戏素材",
)

# 需要复制进便携包的项目文件。
COPY_FILES = (
    "launcher.py",
    "启动.bat",
    "启动.sh",
    "setup.bat",
    "setup.sh",
    "requirements.txt",
    "requirements-wsl.txt",
    "README.md",
    "PROJECT_DOC.md",
    "ui_gap_probe.py",
)

# 复制 Python 安装目录时忽略的缓存/开发杂物。
PY_IGNORE = shutil.ignore_patterns(
    "__pycache__", "*.pyc", "*.pyo", ".git", ".svn",
    "Lib/site-packages/pip/_vendor/distlib/w64.exe",
)


def log(msg: str) -> None:
    print("[build_portable]", msg, flush=True)


def err(msg: str) -> None:
    print("[build_portable][错误]", msg, file=sys.stderr, flush=True)


def ensure_windows() -> None:
    if os.name != "nt" and sys.platform != "win32":
        err("当前便携版打包仅支持 Windows。")
        err("Linux/WSL 请使用 launcher.py 自动创建虚拟环境，暂不生成便携包。")
        raise SystemExit(1)


def python_install_root() -> Path:
    """返回当前 Windows Python 的安装根目录（完整、可整体复制）。"""
    root = Path(sys.base_prefix).resolve()
    if not (root / "python.exe").is_file():
        err("未找到可复制的 Python 安装目录：%s" % root)
        err("请用正常的 Windows Python 安装包运行本脚本（不要用 venv 解释器）。")
        raise SystemExit(1)
    return root


def copy_python(base: Path, dest: Path) -> None:
    log("复制 Python：%s -> %s" % (base, dest))
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(base, dest, ignore=PY_IGNORE, symlinks=False)
    log("Python 复制完成。")


def install_requirements(python_exe: Path, req: Path) -> None:
    log("安装依赖：%s" % req)
    if not python_exe.is_file():
        err("包内 Python 不存在：%s" % python_exe)
        raise SystemExit(1)
    cmd = [str(python_exe), "-m", "pip", "install",
           "--disable-pip-version-check", "-r", str(req)]
    log("执行：%s" % " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if proc.returncode != 0:
        err("依赖安装失败。")
        raise SystemExit(proc.returncode)


def copy_project(bundle_dir: Path) -> None:
    log("复制项目文件到：%s" % bundle_dir)
    for name in COPY_DIRS:
        src = PROJECT_ROOT / name
        if not src.is_dir():
            log("跳过不存在的目录：%s" % name)
            continue
        shutil.copytree(src, bundle_dir / name, ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", "*.pyo", ".pytest_cache", ".ruff_cache"))
    for name in COPY_FILES:
        src = PROJECT_ROOT / name
        if src.is_file():
            shutil.copy2(src, bundle_dir / name)
    log("项目文件复制完成。")


def write_launcher_bat(bundle_dir: Path) -> None:
    content = (
        "@echo off\r\n"
        "rem HOI4 Mod Editor portable launcher (no system Python required)\r\n"
        "setlocal\r\n"
        "set \"ROOT=%~dp0\"\r\n"
        "pushd \"%ROOT%\"\r\n"
        "\"%~dp0portable\\python\\python.exe\" -X utf8 \"%~dp0launcher.py\" %*\r\n"
        "set \"RC=%errorlevel%\"\r\n"
        "popd\r\n"
        "exit /b %RC%\r\n"
    )
    (bundle_dir / "启动.bat").write_text(content, encoding="utf-8")


def write_readme(bundle_dir: Path) -> None:
    content = """HOI4 Mod 编辑器 - 便携版
========================

本目录已包含 Python 和全部依赖，不需要在电脑上预装 Python 或 Qt。

使用方法：
1. 双击 `启动.bat` 即可打开编辑器。
2. 首次打开后，在设置中填写游戏路径和 Mod 路径。
3. 如果需要重装依赖，可运行 `setup.bat`。

目录说明：
- portable\\python\\  便携 Python + PyQt6/numpy/Pillow/mcp
- src\\               程序源码
- docs\\              文档
- templates\\         模板
- translations\\      本地化翻译

注意：请保留整个文件夹，不要单独移动 `portable` 或 `src`。
"""
    (bundle_dir / "README-便携版.txt").write_text(content, encoding="utf-8")


def make_zip(bundle_dir: Path) -> Path:
    parent = bundle_dir.parent
    base_name = bundle_dir.name
    log("压缩便携包：%s" % base_name)
    zip_path = shutil.make_archive(str(parent / base_name), "zip",
                                   root_dir=str(parent), base_dir=base_name)
    return Path(zip_path)


def build(output: Path, zip_output: bool) -> Path:
    ensure_windows()
    bundle_dir = output.resolve()
    if bundle_dir.exists():
        log("清空已有输出目录：%s" % bundle_dir)
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)

    python_root = python_install_root()
    portable_python = bundle_dir / PORTABLE_PYTHON_REL
    copy_python(python_root, portable_python)

    req = PROJECT_ROOT / "requirements.txt"
    install_requirements(portable_python / "python.exe", req)

    copy_project(bundle_dir)
    write_launcher_bat(bundle_dir)
    write_readme(bundle_dir)

    log("便携版已生成：%s" % bundle_dir)
    if zip_output:
        zip_path = make_zip(bundle_dir)
        log("压缩包已生成：%s" % zip_path)
    return bundle_dir


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="生成 HOI4 Mod 编辑器 Windows 便携版",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="输出目录（默认 dist/HOI4编辑器-便携版）")
    parser.add_argument("--zip", action="store_true",
                        help="生成后同时压缩为 zip")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        build(args.output, args.zip)
    except SystemExit as e:
        return int(e.code or 1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
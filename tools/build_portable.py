#!/usr/bin/env python3
"""便携版打包脚本：生成“解压即用、无需预装 Python/Qt”的便携 Python 运行时。

支持：
- Windows：复制当前 Windows Python 完整安装目录；
- Linux/WSL：下载 python-build-standalone 便携 Python 并安装依赖。

用法：
    # 在当前项目生成便携运行时（替换 .venv 用）
    python tools/build_portable.py --runtime-only
    python tools/build_portable.py --runtime-only --platform linux

    # 生成完整发布包
    python tools/build_portable.py --zip
    python tools/build_portable.py --platform linux --zip
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PORTABLE_ROOT = PROJECT_ROOT / "portable"
DEFAULT_OUTPUT = PROJECT_ROOT / "dist" / "HOI4编辑器-便携版"
PBS_CACHE = PROJECT_ROOT / ".runtime" / "pbs_cache"

# Linux 便携 Python 使用 python-build-standalone 的 3.14 x86_64 版本。
PBS_API = "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"
PBS_ARCH = "x86_64-unknown-linux-gnu"

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

PY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".git", ".svn")


def log(msg: str) -> None:
    print("[build_portable]", msg, flush=True)


def err(msg: str) -> None:
    print("[build_portable][错误]", msg, file=sys.stderr, flush=True)


def detect_platform(name: str | None) -> str:
    if name:
        return name.lower()
    if os.name == "nt" or sys.platform == "win32":
        return "win"
    return "linux"


def requirements_for(platform: str) -> Path:
    return PROJECT_ROOT / ("requirements.txt" if platform == "win" else "requirements-wsl.txt")


def portable_runtime_dir(platform: str, output: Path | None = None) -> Path:
    """运行时目录：项目内固定为 portable/<platform>；发布包内为 <output>/portable/python。"""
    if output is None:
        return PORTABLE_ROOT / platform
    return output / "portable" / "python"


def python_exe_for(runtime_root: Path, platform: str) -> Path:
    if platform == "win":
        return runtime_root / "python.exe"
    return runtime_root / "bin" / "python"


def run_command(cmd: list, cwd: Path | None = None) -> int:
    print("  >", " ".join(str(x) for x in cmd), flush=True)
    try:
        proc = subprocess.run([str(x) for x in cmd], cwd=str(cwd or PROJECT_ROOT))
    except OSError as e:
        err("无法执行命令：%s" % e)
        return 1
    return proc.returncode


def windows_python_root() -> Path:
    root = Path(sys.base_prefix).resolve()
    if not (root / "python.exe").is_file():
        err("未找到可复制的 Windows Python 安装目录：%s" % root)
        err("请用正常的 Windows Python 安装包运行本脚本（不要用 venv 解释器）。")
        raise SystemExit(1)
    return root


def copy_windows_python(base: Path, dest: Path) -> None:
    log("复制 Windows Python：%s -> %s" % (base, dest))
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(base, dest, ignore=PY_IGNORE, symlinks=False)
    log("Windows Python 复制完成。")


def latest_linux_pbs_url() -> str:
    log("查询 python-build-standalone 最新 Release...")
    try:
        with urllib.request.urlopen(PBS_API, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        err("获取 python-build-standalone Release 失败：%s" % e)
        raise SystemExit(1)
    for asset in data.get("assets", []):
        name = asset["name"]
        if (name.startswith("cpython-3.14")
                and PBS_ARCH in name
                and "install_only.tar.gz" in name
                and "freethreaded" not in name
                and "debug" not in name):
            return asset["browser_download_url"]
    err("未找到 Linux 便携 Python 3.14 资产。")
    raise SystemExit(1)


def download_linux_pbs(url: str) -> Path:
    name = url.rsplit("/", 1)[-1]
    PBS_CACHE.mkdir(parents=True, exist_ok=True)
    target = PBS_CACHE / name
    if target.is_file() and target.stat().st_size > 0:
        log("复用缓存：%s" % target)
        return target
    log("下载 Linux 便携 Python：%s" % url)
    try:
        with urllib.request.urlopen(url, timeout=600) as resp, open(target, "wb") as fh:
            shutil.copyfileobj(resp, fh)
    except Exception as e:
        err("下载失败：%s" % e)
        raise SystemExit(1)
    return target


def build_linux_python(dest: Path) -> None:
    log("准备 Linux 便携 Python：%s" % dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = latest_linux_pbs_url()
    archive = download_linux_pbs(url)

    # python-build-standalone 包含符号链接；直接在 /mnt 等 Windows 挂载盘解压
    # 可能触发 “Too many levels of symbolic links”。先在原生 Linux 临时目录解压，
    # 再以 dereference（symlinks=False）方式复制到项目内，得到无符号链接的便携树。
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="pbs_linux_", dir="/tmp"))
    try:
        log("解压：%s -> %s" % (archive, tmp))
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(tmp, filter="data")
        src = tmp / "python"
        if not (src / "bin" / "python3.14").is_file():
            err("解压后未找到 Linux Python3.14：%s" % (src / "bin" / "python3.14"))
            raise SystemExit(1)
        log("复制到项目：%s" % dest)
        # Windows 挂载盘大小写不敏感，standalone 自带的 share/terminfo 有大小写冲突且
        # 对 GUI 运行无必要，直接忽略。
        shutil.copytree(src, dest, symlinks=False,
                        ignore=shutil.ignore_patterns("terminfo"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not (dest / "bin" / "python").is_file():
        err("复制后未找到 Linux Python：%s" % (dest / "bin" / "python"))
        raise SystemExit(1)
    log("Linux 便携 Python 就绪。")


def build_runtime(platform: str, output: Path | None = None) -> Path:
    """构建单个平台的便携 Python 运行时，返回 runtime_root（内含 python 解释器）。"""
    runtime_root = portable_runtime_dir(platform, output)
    if platform == "win":
        copy_windows_python(windows_python_root(), runtime_root)
    else:
        build_linux_python(runtime_root)
    py = python_exe_for(runtime_root, platform)
    if not py.is_file():
        err("便携 Python 不存在：%s" % py)
        raise SystemExit(1)
    req = requirements_for(platform)
    log("安装依赖：%s" % req)
    rc = run_command([py, "-m", "pip", "install", "--disable-pip-version-check",
                      "-r", str(req)])
    if rc != 0:
        err("依赖安装失败。")
        raise SystemExit(rc)
    return runtime_root


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


def write_launcher_sh(bundle_dir: Path) -> None:
    content = """#!/usr/bin/env bash
# HOI4 Mod Editor portable launcher (no system Python required)
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
exec "$SCRIPT_DIR/portable/python/bin/python" -X utf8 "$SCRIPT_DIR/launcher.py" "$@"
"""
    (bundle_dir / "启动.sh").write_text(content, encoding="utf-8")


def write_readme(bundle_dir: Path) -> None:
    content = """HOI4 Mod 编辑器 - 便携版
========================

本目录已包含 Python 和全部依赖，不需要在电脑上预装 Python 或 Qt。

使用方法：
- Windows：双击 `启动.bat`
- Linux/WSL：`bash 启动.sh`

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


def build_runtime_only(platform: str, output: Path | None) -> Path:
    runtime_root = build_runtime(platform, output)
    log("便携运行时已生成：%s" % runtime_root)
    log("解释器：%s" % python_exe_for(runtime_root, platform))
    return runtime_root


def build_full_bundle(platform: str, output: Path, zip_output: bool) -> Path:
    bundle_dir = output.resolve()
    if bundle_dir.exists():
        log("清空已有输出目录：%s" % bundle_dir)
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)
    build_runtime(platform, bundle_dir)
    copy_project(bundle_dir)
    if platform == "win":
        write_launcher_bat(bundle_dir)
        write_launcher_sh(bundle_dir)
    else:
        write_launcher_sh(bundle_dir)
        write_readme(bundle_dir)
    log("便携版已生成：%s" % bundle_dir)
    if zip_output:
        zip_path = make_zip(bundle_dir)
        log("压缩包已生成：%s" % zip_path)
    return bundle_dir


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="生成 HOI4 Mod 编辑器便携版（Windows/Linux）",
    )
    parser.add_argument("--platform", choices=("win", "linux", "auto"),
                        default="auto", help="目标平台（默认自动检测当前系统）")
    parser.add_argument("--runtime-only", action="store_true",
                        help="只在项目内生成 portable/<platform>，不生成完整发布包")
    parser.add_argument("--output", type=Path, default=None,
                        help="输出目录（默认 dist/HOI4编辑器-便携版；runtime-only 默认 portable/<platform>）")
    parser.add_argument("--zip", action="store_true",
                        help="生成后同时压缩为 zip（仅完整发布包）")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    platform = detect_platform(args.platform)
    log("目标平台：%s" % platform)
    try:
        if args.runtime_only:
            build_runtime_only(platform, args.output)
        else:
            output = args.output or DEFAULT_OUTPUT
            build_full_bundle(platform, output, args.zip)
    except SystemExit as e:
        return int(e.code or 1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""HOI4 Mod 编辑器 — 跨平台启动器。

设计目标：完全排除“换电脑/换目录/路径含空格或中文/虚拟环境路径写死”导致的
启动脚本不可用。本文件是唯一的路径/环境入口，`启动.bat`、`启动.sh`、`setup.bat`、
`setup.sh` 都只是薄壳，最终都转到这里。

能力：
- 项目根目录由本文件位置解析，不依赖调用者当前工作目录；
- 支持 Windows 与 Linux/WSL，虚拟环境默认放在项目内；
- Windows 用 `.venv`（若 `.venv` 被 Linux 环境占用则自动改用 `.venv-win`）；
  WSL/Linux 若发现 `.venv` 是 Windows 环境则自动改用 `.venv-linux`，
  避免两个平台互相破坏；
- 没有可用虚拟环境时自动用本机 Python 创建并安装依赖；
- 工作目录固定为项目根，确保 settings.json / templates 等相对路径稳定；
- 支持 `--setup`（只准备环境）、`--verify`（跑全量契约）、`--check`（只检查不创建）、
  `--venv DIR`（自定义虚拟环境）；环境变量 `HOI4_VENV` 同样生效。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
APP_ENTRY = PROJECT_ROOT / "src" / "main.py"
REQUIREMENTS_WIN = PROJECT_ROOT / "requirements.txt"
REQUIREMENTS_POSIX = PROJECT_ROOT / "requirements-wsl.txt"
VERIFY_ENTRY = PROJECT_ROOT / "tools" / "verify_contracts.py"

MIN_PY = (3, 10)
MIN_PY_TEXT = "3.10"
PREFERRED_PY = (3, 14)

# 启动 GUI 前必须可导入的依赖（缺任一就自动重装 requirements）。
DEPS_CHECK_CODE = (
    "import PyQt6, numpy, PIL, mcp; import sys; "
    "sys.exit(0)"
)


def is_windows() -> bool:
    """当前是否 Windows 原生环境。"""
    return os.name == "nt" or sys.platform == "win32"


def log(msg: str) -> None:
    print("[启动器]", msg, flush=True)


def err(msg: str) -> None:
    print("[启动器][错误]", msg, file=sys.stderr, flush=True)


def venv_python(venv_dir: Path, win: bool | None = None) -> Path:
    """返回虚拟环境内的 Python 可执行文件。"""
    if win is None:
        win = is_windows()
    if win:
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def venv_usable(venv_dir: Path, win: bool | None = None) -> bool:
    """虚拟环境目录是否对当前平台可用（存在对应 python）。"""
    return venv_python(venv_dir, win).is_file()


def default_venv_dir(root: Path, win: bool | None = None) -> Path:
    """选择默认虚拟环境目录，避免 Windows/WSL 互相破坏对方的 .venv。"""
    if win is None:
        win = is_windows()
    if win:
        # Windows：已有 Windows .venv 直接用；若 .venv 是 Linux 环境则改用 .venv-win。
        if venv_usable(root / ".venv", True):
            return root / ".venv"
        if venv_usable(root / ".venv-win", True):
            return root / ".venv-win"
        if (root / ".venv" / "bin" / "python").is_file():
            return root / ".venv-win"
        return root / ".venv"
    # POSIX：已有 Linux venv 就直接用；.venv 是 Windows 环境时改用 .venv-linux。
    if venv_usable(root / ".venv", False):
        return root / ".venv"
    if venv_usable(root / ".venv-linux", False):
        return root / ".venv-linux"
    if (root / ".venv" / "Scripts" / "python.exe").is_file():
        return root / ".venv-linux"
    return root / ".venv"


def resolve_venv(override: str | None, root: Path | None = None,
                 win: bool | None = None) -> Path:
    """解析最终虚拟环境目录。

    优先级：`--venv` 参数 > 环境变量 `HOI4_VENV` > 平台默认。
    相对路径都按项目根解释。
    """
    root = root or PROJECT_ROOT
    raw = override or os.environ.get("HOI4_VENV")
    if raw:
        p = Path(raw).expanduser()
        return p if p.is_absolute() else root / p
    return default_venv_dir(root, win)


def requirements_file(win: bool | None = None) -> Path:
    if win is None:
        win = is_windows()
    return REQUIREMENTS_WIN if win else REQUIREMENTS_POSIX


def _find_pyqt6_qt_dir(venv_dir: Path, win: bool | None = None) -> Path | None:
    """定位 venv 内 PyQt6 的 Qt6 目录，供显式设置插件/DLL 路径。"""
    if win is None:
        win = is_windows()
    if win:
        cand = venv_dir / "Lib" / "site-packages" / "PyQt6" / "Qt6"
        return cand if cand.is_dir() else None
    lib = venv_dir / "lib"
    if not lib.is_dir():
        return None
    for py in sorted(lib.iterdir()):
        cand = py / "site-packages" / "PyQt6" / "Qt6"
        if cand.is_dir():
            return cand
    return None


def qt_env(venv_dir: Path, win: bool | None = None) -> dict:
    """返回让 PyQt6 更稳的 Qt 路径环境变量（存在才设置，避免破坏默认查找）。"""
    if win is None:
        win = is_windows()
    env: dict = {}
    qt_dir = _find_pyqt6_qt_dir(venv_dir, win)
    if qt_dir is None:
        return env
    dll_dir = qt_dir / ("bin" if win else "lib")
    if dll_dir.is_dir():
        env["PATH"] = str(dll_dir) + os.pathsep + env.get("PATH", "")
    platforms = qt_dir / "plugins" / "platforms"
    if platforms.is_dir():
        env["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms)
    return env


def _probe_python(candidate) -> tuple[int, int] | None:
    """探测候选 Python 的版本号；失败返回 None。"""
    argv = list(candidate) if isinstance(candidate, (list, tuple)) else [str(candidate)]
    code = "import sys; print('%d.%d' % (sys.version_info[0], sys.version_info[1]))"
    try:
        proc = subprocess.run(argv + ["-c", code], capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        major_s, minor_s = proc.stdout.strip().split(".")
        return int(major_s), int(minor_s)
    except (ValueError, AttributeError):
        return None


def _candidate_python_commands() -> list:
    """生成候选 Python 命令。优先使用当前解释器，其次 PATH 中的常见名称。"""
    candidates: list = []
    if sys.executable:
        candidates.append(Path(sys.executable))
    if is_windows():
        for ver in ("3.14", "3.13", "3.12", "3.11", "3.10", "3"):
            candidates.append(["py", "-" + ver])
        for name in ("python", "python3", "py"):
            if shutil.which(name):
                candidates.append(name)
    else:
        for name in ("python3.14", "python3.13", "python3.12", "python3.11",
                     "python3.10", "python3", "python"):
            if shutil.which(name):
                candidates.append(name)
    return candidates


def find_base_python() -> tuple[list | None, tuple[int, int] | None]:
    """返回可用于创建虚拟环境的基础 Python 命令与版本。"""
    for candidate in _candidate_python_commands():
        ver = _probe_python(candidate)
        if ver and ver >= MIN_PY:
            return list(candidate) if isinstance(candidate, (list, tuple)) else [str(candidate)], ver
    return None, None


def run_command(cmd: list, cwd: Path | None = None) -> int:
    """执行子进程并回显命令；返回退出码。"""
    display = " ".join(str(x) for x in cmd)
    print("  >", display, flush=True)
    try:
        proc = subprocess.run([str(x) for x in cmd], cwd=str(cwd or PROJECT_ROOT))
    except OSError as e:
        err("无法执行命令：%s" % e)
        return 1
    return proc.returncode


def create_venv(venv_dir: Path, base_python: list, win: bool | None = None) -> bool:
    """创建缺失的虚拟环境；已存在但不可用且非空时拒绝自动覆盖。"""
    if venv_usable(venv_dir, win):
        return True
    if venv_dir.exists() and any(venv_dir.iterdir()):
        err("虚拟环境目录已存在但不是当前平台可用环境：%s" % venv_dir)
        err("请手动删除该目录，或使用 --venv 指定其他目录。")
        return False
    log("未找到可用虚拟环境，正在创建：%s" % venv_dir)
    rc = run_command([*base_python, "-m", "venv", str(venv_dir)])
    if rc != 0:
        err("创建虚拟环境失败。")
        return False
    return venv_usable(venv_dir, win)


def deps_ok(venv_dir: Path, win: bool | None = None) -> bool:
    """检查虚拟环境内核心依赖是否可导入。"""
    py = venv_python(venv_dir, win)
    if not py.is_file():
        return False
    try:
        proc = subprocess.run([str(py), "-c", DEPS_CHECK_CODE],
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=120)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def install_requirements(venv_dir: Path, win: bool | None = None) -> bool:
    """用虚拟环境 pip 安装当前平台依赖。"""
    py = venv_python(venv_dir, win)
    req = requirements_file(win)
    log("安装依赖：%s（首次可能较慢）" % req.name)
    rc = run_command([py, "-m", "pip", "install", "--disable-pip-version-check",
                      "-r", str(req)])
    if rc != 0:
        err("依赖安装失败。")
        return False
    return True


def prepare_env(venv_dir: Path, win: bool | None = None) -> bool:
    """确保虚拟环境存在且核心依赖可导入；需要时自动安装。"""
    if not create_venv(venv_dir, find_base_python()[0] or [], win):
        return False
    if not deps_ok(venv_dir, win):
        if not install_requirements(venv_dir, win):
            return False
        if not deps_ok(venv_dir, win):
            err("依赖安装后仍无法导入 PyQt6/numpy/Pillow/mcp，请检查网络或 Python 版本。")
            return False
    return True


def build_app_command(venv_dir: Path, app_args: list[str],
                      win: bool | None = None) -> list[str]:
    """构造主程序启动命令（绝对路径 + 固定项目根）。"""
    py = venv_python(venv_dir, win)
    return [str(py), "-X", "utf8", str(APP_ENTRY), *app_args]


def build_verify_command(venv_dir: Path, win: bool | None = None) -> list[str]:
    """构造全量契约验证命令。"""
    py = venv_python(venv_dir, win)
    return [str(py), "-X", "utf8", str(VERIFY_ENTRY)]


def run_app(venv_dir: Path, app_args: list[str], win: bool | None = None) -> int:
    """以项目根为工作目录启动主程序，透传额外参数。"""
    log("启动编辑器：%s" % APP_ENTRY)
    cmd = build_app_command(venv_dir, app_args, win)
    env = dict(os.environ)
    env.update(qt_env(venv_dir, win))
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
    except OSError as e:
        err("启动主程序失败：%s" % e)
        return 1
    return proc.returncode


def run_verify(venv_dir: Path, win: bool | None = None) -> int:
    """用项目虚拟环境运行全量契约验证。"""
    log("运行全量契约验证：%s" % VERIFY_ENTRY)
    cmd = build_verify_command(venv_dir, win)
    env = dict(os.environ)
    env.update(qt_env(venv_dir, win))
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
    except OSError as e:
        err("无法运行契约验证：%s" % e)
        return 1
    return proc.returncode


def do_check(venv_dir: Path, win: bool | None = None) -> int:
    """只检查环境，不创建、不安装、不启动。"""
    ok = True
    print("[启动器] 项目根：%s" % PROJECT_ROOT)
    print("[启动器] 平台：%s" % ("Windows" if win else "Linux/POSIX"))
    print("[启动器] 虚拟环境：%s" % venv_dir)
    if venv_usable(venv_dir, win):
        print("[启动器] 虚拟环境：可用")
        if deps_ok(venv_dir, win):
            print("[启动器] 核心依赖：PyQt6/numpy/Pillow/mcp 可导入")
        else:
            print("[启动器] 核心依赖：缺失（运行启动器会自动安装）")
            ok = False
    else:
        print("[启动器] 虚拟环境：尚未创建（运行启动器会自动创建）")
        ok = False
    base_python, ver = find_base_python()
    if base_python:
        print("[启动器] 基础 Python：%s（%d.%d）" % (" ".join(base_python), *ver))
    else:
        print("[启动器] 基础 Python：未找到 %s 或更高版本" % MIN_PY_TEXT)
        ok = False
    if not ok:
        print("[启动器] 检查未通过：直接运行启动器可自动修复可修复项。")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="launcher.py",
        description="HOI4 Mod 编辑器跨平台启动器",
        epilog="其余参数会原样透传给 src/main.py。",
    )
    parser.add_argument("--setup", action="store_true",
                        help="只准备虚拟环境与依赖，不启动编辑器")
    parser.add_argument("--verify", action="store_true",
                        help="准备环境后运行 tools/verify_contracts.py")
    parser.add_argument("--check", action="store_true",
                        help="只检查环境状态，不创建/不安装/不启动")
    parser.add_argument("--venv", metavar="DIR",
                        help="指定虚拟环境目录（相对路径按项目根解释）")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args, app_args = parser.parse_known_args(argv)
    win = is_windows()
    venv_dir = resolve_venv(args.venv, PROJECT_ROOT, win)

    if args.check:
        return do_check(venv_dir, win)

    base_python, base_ver = find_base_python()
    if base_python is None:
        err("未找到 Python %s 或更高版本。请先安装 Python 后再运行启动器。"
            % MIN_PY_TEXT)
        return 1
    log("基础 Python：%s（%d.%d）" % (" ".join(base_python), *base_ver))
    log("虚拟环境：%s" % venv_dir)

    if not prepare_env(venv_dir, win):
        return 1

    if args.verify:
        return run_verify(venv_dir, win)
    if args.setup:
        log("环境已就绪，未启动编辑器。")
        return 0
    return run_app(venv_dir, app_args, win)


if __name__ == "__main__":
    sys.exit(main())

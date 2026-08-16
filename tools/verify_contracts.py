"""可执行契约一键验证（契约 #0：全部契约从这里跑）

运行全部写入纪律契约并汇总结果：
    1. 语法编译：项目全部 .py 模块 py_compile（3.8/3.13 均可用）
    2. 单元契约测试：tests/test_contracts.py
       （原子写 / BOM 拒绝 / 撤销快照 / 健康检查检出 / 纪律扫描）
    3. 写入纪律静态扫描：tools/check_write_discipline.py

用法：
    python tools/verify_contracts.py
退出码：0 = 全部通过；1 = 存在失败契约
"""

from __future__ import annotations

import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON = sys.executable

# 不参与编译的目录
SKIP_DIRS = {".venv", ".venv-linux", ".git", "__pycache__", "dist",
             "node_modules", "data", "_scenario_forge"}


def _py_files(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".py"):
                out.append(os.path.join(dirpath, fn))
    return out


def run_step(name, cmd, cwd=None):
    print("\n== [%s] ==" % name)
    try:
        proc = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT,
                              capture_output=True, text=True)
    except OSError as e:
        print("  无法启动: %s" % e)
        return False
    tail = (proc.stdout or "")[-1500:]
    if tail.strip():
        print(tail.rstrip())
    if proc.returncode != 0:
        err = (proc.stderr or "")[-1500:]
        if err.strip():
            print(err.rstrip())
    print("  退出码: %d" % proc.returncode)
    return proc.returncode == 0


def main():
    print("写入纪律契约验证（%s）" % PYTHON)
    results = []

    # 1. 全模块语法编译
    files = _py_files(PROJECT_ROOT)
    print("\n== [语法编译 %d 个模块] ==" % len(files))
    bad = []
    import py_compile
    for fp in files:
        try:
            py_compile.compile(fp, doraise=True)
        except Exception as e:
            bad.append((fp, str(e)))
    for fp, err in bad[:10]:
        print("  编译失败: %s (%s)" % (fp, err))
    results.append(("语法编译", not bad))

    # 2. 契约单元测试
    results.append(("契约单元测试",
                    run_step("契约单元测试",
                             [PYTHON, "-m", "unittest", "discover",
                              "-s", "tests", "-v"])))

    # 3. 写入纪律静态扫描
    results.append(("写入纪律扫描",
                    run_step("写入纪律扫描",
                             [PYTHON, os.path.join("tools", "check_write_discipline.py")])))

    print("\n" + "=" * 46)
    all_ok = True
    for name, ok in results:
        print("  %-14s %s" % (name, "[OK]" if ok else "[FAIL]"))
        all_ok = all_ok and ok
    print("=" * 46)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

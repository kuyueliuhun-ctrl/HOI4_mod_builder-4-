"""启动器路径解析与跨平台虚拟环境选择单元测试。

覆盖“换电脑/换目录/路径含空格/Windows.WSL 共用目录”最能出问题的纯逻辑：
- 项目根/venv 路径不写死；
- Windows 固定 .venv；
- WSL/Linux 检测到 .venv 是 Windows 环境时改用 .venv-linux；
- 已存在的 Linux .venv 被优先复用；
- 相对 --venv 按项目根解释；
- 启动/验证命令使用绝对路径与固定项目根。
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import launcher


def _mkdtemp(prefix: str) -> Path:
    root = PROJECT_ROOT / ".runtime" / "test_tmp"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=root))


class VenvPathTest(unittest.TestCase):
    def test_venv_python_windows(self):
        d = Path("D:/some project/.venv")
        self.assertEqual(launcher.venv_python(d, win=True),
                         d / "Scripts" / "python.exe")

    def test_venv_python_posix(self):
        d = Path("/some path/.venv")
        self.assertEqual(launcher.venv_python(d, win=False),
                         d / "bin" / "python")

    def test_venv_usable_true_false(self):
        root = _mkdtemp("launcher_venv_usable_")
        self.assertFalse(launcher.venv_usable(root, win=True))
        self.assertFalse(launcher.venv_usable(root, win=False))
        scripts = root / "Scripts"
        scripts.mkdir()
        (scripts / "python.exe").write_text("", encoding="utf-8")
        self.assertTrue(launcher.venv_usable(root, win=True))
        self.assertFalse(launcher.venv_usable(root, win=False))

    def test_default_venv_dir_windows(self):
        root = _mkdtemp("launcher_win_")
        self.assertEqual(launcher.default_venv_dir(root, win=True),
                         root / ".venv")

    def test_default_venv_dir_posix_uses_existing_linux_venv(self):
        root = _mkdtemp("launcher_posix_linux_")
        (root / ".venv" / "bin").mkdir(parents=True)
        (root / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
        self.assertEqual(launcher.default_venv_dir(root, win=False),
                         root / ".venv")

    def test_default_venv_dir_windows_avoids_linux_venv(self):
        root = _mkdtemp("launcher_win_linux_")
        (root / ".venv" / "bin").mkdir(parents=True)
        (root / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
        self.assertEqual(launcher.default_venv_dir(root, win=True),
                         root / ".venv-win")

    def test_default_venv_dir_windows_prefers_existing_venv_win(self):
        root = _mkdtemp("launcher_win_both_")
        (root / ".venv" / "bin").mkdir(parents=True)
        (root / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
        (root / ".venv-win" / "Scripts").mkdir(parents=True)
        (root / ".venv-win" / "Scripts" / "python.exe").write_text("", encoding="utf-8")
        self.assertEqual(launcher.default_venv_dir(root, win=True),
                         root / ".venv-win")

    def test_default_venv_dir_posix_avoids_windows_venv(self):
        root = _mkdtemp("launcher_posix_win_")
        (root / ".venv" / "Scripts").mkdir(parents=True)
        (root / ".venv" / "Scripts" / "python.exe").write_text("", encoding="utf-8")
        self.assertEqual(launcher.default_venv_dir(root, win=False),
                         root / ".venv-linux")

    def test_default_venv_dir_posix_prefers_venv_linux_when_existing(self):
        root = _mkdtemp("launcher_posix_both_")
        (root / ".venv" / "Scripts").mkdir(parents=True)
        (root / ".venv" / "Scripts" / "python.exe").write_text("", encoding="utf-8")
        (root / ".venv-linux" / "bin").mkdir(parents=True)
        (root / ".venv-linux" / "bin" / "python").write_text("", encoding="utf-8")
        self.assertEqual(launcher.default_venv_dir(root, win=False),
                         root / ".venv-linux")

    def test_resolve_venv_override_relative(self):
        root = _mkdtemp("launcher_rel_")
        self.assertEqual(launcher.resolve_venv("my-venv", root=root, win=True),
                         root / "my-venv")

    def test_resolve_venv_override_absolute(self):
        root = _mkdtemp("launcher_abs_")
        target = root / "elsewhere" / "venv dir"
        self.assertEqual(launcher.resolve_venv(str(target), root=root, win=True),
                         target)

    def test_resolve_venv_uses_hoi4_venv_env(self):
        root = _mkdtemp("launcher_env_")
        target = root / "custom env"
        with mock.patch.dict(os.environ, {"HOI4_VENV": str(target)}, clear=False):
            self.assertEqual(launcher.resolve_venv(None, root=root, win=True),
                             target)

    def test_requirements_file_by_platform(self):
        self.assertEqual(launcher.requirements_file(win=True), launcher.REQUIREMENTS_WIN)
        self.assertEqual(launcher.requirements_file(win=False), launcher.REQUIREMENTS_POSIX)

    def test_create_venv_refuses_foreign_nonempty_dir(self):
        root = _mkdtemp("launcher_foreign_")
        venv_dir = root / ".venv"
        venv_dir.mkdir()
        (venv_dir / "windows_marker.txt").write_text("x", encoding="utf-8")
        self.assertFalse(launcher.create_venv(venv_dir, [sys.executable], win=False))


class QtEnvTest(unittest.TestCase):
    def test_find_pyqt6_qt_dir_windows(self):
        root = _mkdtemp("launcher_qt_win_")
        qt = root / ".venv" / "Lib" / "site-packages" / "PyQt6" / "Qt6"
        (qt / "bin").mkdir(parents=True)
        self.assertEqual(launcher._find_pyqt6_qt_dir(root / ".venv", win=True), qt)

    def test_find_pyqt6_qt_dir_posix(self):
        root = _mkdtemp("launcher_qt_posix_")
        qt = root / ".venv" / "lib" / "python3.14" / "site-packages" / "PyQt6" / "Qt6"
        (qt / "lib").mkdir(parents=True)
        self.assertEqual(launcher._find_pyqt6_qt_dir(root / ".venv", win=False), qt)

    def test_qt_env_sets_path_and_plugin_path_windows(self):
        root = _mkdtemp("launcher_qt_env_win_")
        qt = root / ".venv" / "Lib" / "site-packages" / "PyQt6" / "Qt6"
        (qt / "bin").mkdir(parents=True)
        (qt / "plugins" / "platforms").mkdir(parents=True)
        env = launcher.qt_env(root / ".venv", win=True)
        self.assertIn(str(qt / "bin"), env.get("PATH", ""))
        self.assertEqual(env.get("QT_QPA_PLATFORM_PLUGIN_PATH"),
                         str(qt / "plugins" / "platforms"))

    def test_qt_env_returns_empty_when_missing(self):
        root = _mkdtemp("launcher_qt_missing_")
        self.assertEqual(launcher.qt_env(root / ".venv", win=True), {})


class CommandBuildTest(unittest.TestCase):
    def test_build_app_command_uses_absolute_venv_python_and_project_entry(self):
        venv_dir = Path("/some path/项目/.venv")
        cmd = launcher.build_app_command(venv_dir, ["--flag", "a b"], win=False)
        self.assertEqual(cmd[:3],
                         [str(venv_dir / "bin" / "python"), "-X", "utf8"])
        self.assertEqual(cmd[3], str(launcher.PROJECT_ROOT / "src" / "main.py"))
        self.assertEqual(cmd[4:], ["--flag", "a b"])

    def test_build_verify_command_uses_venv_python_and_verify_entry(self):
        venv_dir = Path("C:/my project/.venv")
        cmd = launcher.build_verify_command(venv_dir, win=True)
        self.assertEqual(cmd[:3],
                         [str(venv_dir / "Scripts" / "python.exe"), "-X", "utf8"])
        self.assertEqual(cmd[3], str(launcher.PROJECT_ROOT / "tools" / "verify_contracts.py"))

    def test_build_app_command_windows_uses_scripts_python(self):
        venv_dir = Path("D:/项目 目录/.venv")
        cmd = launcher.build_app_command(venv_dir, [], win=True)
        self.assertEqual(cmd[0], str(venv_dir / "Scripts" / "python.exe"))


if __name__ == "__main__":
    unittest.main()

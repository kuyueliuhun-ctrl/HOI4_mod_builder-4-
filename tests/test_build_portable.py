"""便携版打包脚本纯逻辑测试。

不实际复制 Python，只验证：
- 便携目录布局；
- 生成的启动器内容；
- 项目文件复制规则；
- README 内容。
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import build_portable


def _mkdtemp(prefix: str) -> Path:
    root = PROJECT_ROOT / ".runtime" / "test_tmp"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=root))


class PortableBuildTest(unittest.TestCase):
    def test_portable_python_rel_layout(self):
        self.assertEqual(build_portable.PORTABLE_PYTHON_REL,
                         Path("portable") / "python")

    def test_write_launcher_bat_uses_portable_python(self):
        bundle = _mkdtemp("portable_bat_")
        build_portable.write_launcher_bat(bundle)
        content = (bundle / "启动.bat").read_text(encoding="utf-8")
        self.assertIn("portable\\python\\python.exe", content)
        self.assertIn("launcher.py", content)

    def test_write_readme_contains_usage(self):
        bundle = _mkdtemp("portable_readme_")
        build_portable.write_readme(bundle)
        content = (bundle / "README-便携版.txt").read_text(encoding="utf-8")
        self.assertIn("启动.bat", content)
        self.assertIn("不需要在电脑上预装 Python 或 Qt", content)

    def test_copy_project_copies_expected_paths(self):
        fake_root = _mkdtemp("portable_copy_src_")
        bundle = _mkdtemp("portable_copy_dst_")
        (fake_root / "src").mkdir()
        (fake_root / "src" / "main.py").write_text("", encoding="utf-8")
        (fake_root / "templates").mkdir()
        (fake_root / "templates" / "x.json").write_text("{}", encoding="utf-8")
        (fake_root / "launcher.py").write_text("", encoding="utf-8")
        (fake_root / "requirements.txt").write_text("", encoding="utf-8")
        with mock.patch.object(build_portable, "PROJECT_ROOT", fake_root), \
             mock.patch.object(build_portable, "COPY_DIRS",
                               ("src", "templates", "missing_dir")), \
             mock.patch.object(build_portable, "COPY_FILES",
                               ("launcher.py", "requirements.txt", "no.txt")):
            build_portable.copy_project(bundle)
        self.assertTrue((bundle / "src" / "main.py").is_file())
        self.assertTrue((bundle / "templates" / "x.json").is_file())
        self.assertTrue((bundle / "launcher.py").is_file())
        self.assertTrue((bundle / "requirements.txt").is_file())
        self.assertFalse((bundle / "missing_dir").exists())
        self.assertFalse((bundle / "no.txt").exists())


if __name__ == "__main__":
    unittest.main()
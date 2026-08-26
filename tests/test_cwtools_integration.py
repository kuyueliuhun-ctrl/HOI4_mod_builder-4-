"""CWTools 审查适配测试（cwtools_integration.py）。"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


class CwtoolsIntegrationTest(unittest.TestCase):
    def test_parse_report_list(self):
        from cwtools_integration import parse_cwtools_report
        data = [
            {"severity": "error", "code": "CW001", "message": "x"},
            {"severity": "warning", "code": "CW002", "message": "y"},
            {"severity": "info", "code": "CW003", "message": "z"},
        ]
        r = parse_cwtools_report(data)
        self.assertEqual(r["error_count"], 1)
        self.assertEqual(r["warning_count"], 1)
        self.assertEqual(r["count"], 3)

    def test_parse_report_dict(self):
        from cwtools_integration import parse_cwtools_report
        r = parse_cwtools_report({"errors": ["a"], "warnings": ["b"]})
        self.assertEqual(r["errors"], ["a"])
        self.assertEqual(r["warnings"], ["b"])

    def test_not_installed_guide(self):
        from cwtools_integration import run_cwtools_check
        with patch("cwtools_integration.shutil.which", return_value=None), \
                patch.dict(os.environ, {}, clear=False):
            for k in ("CWTOOLS_BIN", "CWTools_BIN"):
                os.environ.pop(k, None)
            mod = tempfile.mkdtemp(prefix="cw_")
            self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
            r = run_cwtools_check(mod)
            self.assertFalse(r["ok"])
            self.assertIn("未安装", r["reason"])
            self.assertIn("CWTOOLS_BIN", r["guide"])

    def test_available_env(self):
        from cwtools_integration import cwtools_available
        with patch("cwtools_integration.shutil.which", return_value=None):
            os.environ["CWTOOLS_BIN"] = "/usr/bin/fake-cwtools"
            try:
                self.assertTrue(cwtools_available())
            finally:
                os.environ.pop("CWTOOLS_BIN", None)


if __name__ == "__main__":
    unittest.main()

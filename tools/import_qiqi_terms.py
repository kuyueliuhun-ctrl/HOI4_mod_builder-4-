"""导入 QIUQI-LIBRARY 词条 → translations/qiqi_terms.json

用法：
    python tools/import_qiqi_terms.py [--source E:\\QIUQI-LIBRARY] [--output translations/qiqi_terms.json]

缺省自动探测 QIUQI-LIBRARY 根目录（--source / 环境变量 QIUQI_LIBRARY / 常见路径）。
同键冲突以 QIUQI 为正确项目（qiqi_terms.json 排在 term_registry 词条文件末尾）。
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from qiqi_term_import import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())

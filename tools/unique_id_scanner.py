"""唯一标识符扫描器 CLI（薄包装，逻辑在 src/unique_id_scanner.py）。

用法：
    python tools/unique_id_scanner.py [--mod <mod_path>] [--game <game_path>] [--types focus,decision,event,...]
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


def main(argv=None):
    from unique_id_scanner import main as scan_main
    return scan_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""结构体展示组件（StructureView）样品启动器。

用法：
    python tools/structure_view_demo.py                 # 默认载入游戏 MIO 组织文件
    python tools/structure_view_demo.py --file <路径>   # 指定任意 PDX 文本文件
    python tools/structure_view_demo.py --shot out.png  # 离屏截图后退出（自检用）

演示功能：
- 块=列表行，子条目缩进嵌套，载入后默认全部展开；
- 双击键列改名、双击值列改值、双击块行"{ … }"展开/收起、双击块字段改块名；
- 第三列接入 LocalizationManager 展示中文翻译（双击翻译可复制）；
- "导出序列化"按钮把当前（可能已编辑的）结构写回文本，验证编辑真实生效。
"""

from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

DEFAULT_REL = os.path.join(
    "common", "military_industrial_organization", "organizations",
    "00_generic_organization.txt")


def _default_roots():
    """按运行环境返回 (游戏根, mod根) 候选：Windows 用 E:/，WSL 用 /mnt/e/。"""
    if os.name == "nt":
        return ("E:/SteamLibrary/steamapps/common/Hearts of Iron IV",
                "E:/mods/3350890356")
    return ("/mnt/e/SteamLibrary/steamapps/common/Hearts of Iron IV",
            "/mnt/e/mods/3350890356")


def pick_default_file(game_root):
    cand = os.path.join(game_root, DEFAULT_REL)
    if os.path.isfile(cand):
        return cand
    org_dir = os.path.join(game_root, "common", "military_industrial_organization",
                           "organizations")
    if os.path.isdir(org_dir):
        for name in sorted(os.listdir(org_dir)):
            if name.endswith(".txt"):
                return os.path.join(org_dir, name)
    return ""


def build_window(file_path, game, mod):
    from PyQt6.QtWidgets import (
        QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout)

    from localization_mgr import LocalizationManager
    from structure_view import StructureView
    import theme

    dlg = QDialog()
    dlg.setWindowTitle("结构体展示样品 — %s" % (os.path.basename(file_path) or "（未载入）"))
    dlg.resize(1080, 760)
    lay = QVBoxLayout(dlg)

    hint = QLabel("双击键列改名 · 双击值列改值 · 双击块行 { … } 展开/收起 · "
                  "双击块字段改块名 · 第三列为翻译器本地化（双击复制）")
    hint.setStyleSheet("color: %s; font-size: 12px;" % theme.COLORS["text_secondary"])
    lay.addWidget(hint)

    view = StructureView()

    mgr = LocalizationManager()
    mgr.add_game_path(game)
    mgr.add_mod_path(mod)
    view.set_localization(mgr)

    def load():
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                view.load_text(f.read())
        except Exception as exc:
            QMessageBox.warning(dlg, "载入失败", str(exc))

    load()
    lay.addWidget(view)

    btns = QHBoxLayout()
    b_reload = QPushButton("重新载入")
    b_reload.clicked.connect(load)
    b_loc = QPushButton("刷新本地化")
    b_loc.clicked.connect(view.refresh_localization)

    def export_text():
        from write_utils import atomic_write_text
        out_dir = os.path.join(ROOT, ".runtime")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "structure_demo_out.txt")
        atomic_write_text(out_path, view.to_pdx_text() + "\n")
        QMessageBox.information(dlg, "已导出", "序列化文本已写入：\n%s" % out_path)

    b_out = QPushButton("导出序列化")
    b_out.clicked.connect(export_text)
    b_out.setProperty("class", "primary")
    for b in (b_reload, b_loc, b_out):
        btns.addWidget(b)
    btns.addStretch(1)
    lay.addLayout(btns)

    return dlg, view


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="")
    ap.add_argument("--game", default="")
    ap.add_argument("--mod", default="")
    ap.add_argument("--shot", default="", help="离屏截图输出 png 后退出")
    args = ap.parse_args()

    game, mod = args.game or _default_roots()[0], args.mod or _default_roots()[1]
    file_path = args.file or pick_default_file(game)

    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    import theme
    theme.apply_theme(app)

    dlg, view = build_window(file_path, game, mod)

    if args.shot:
        os.makedirs(os.path.dirname(os.path.abspath(args.shot)), exist_ok=True)
        dlg.show()
        app.processEvents()
        dlg.grab().save(args.shot)
        tops = view.topLevelItemCount()
        total = 0
        stack = [view.topLevelItem(i) for i in range(tops)]
        while stack:
            it = stack.pop()
            total += 1
            stack.extend(it.child(j) for j in range(it.childCount()))
        print("file=%s" % file_path)
        print("top_rows=%d total_rows=%d" % (tops, total))
        print("shot=%s" % args.shot)
        return 0

    dlg.exec()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""文件类型覆盖检查报告模块

对照游戏目录 / 当前 mod / 工作台内容类型定义，检查工具对 HOI4 各类
可编辑文件的覆盖情况，并列出仍直接使用「树形编辑器」打开的类型与文件。

职责：
  - 汇总 CONTENT_TYPES 中每个类型的打开方式（设计视图 / 图标画廊 /
    专用编辑器 / 树形编辑器）
  - 扫描当前 mod 目录，统计每个类型实际命中的文件数
  - 提供 CoverageReportDialog：应用内查看 + 复制 Markdown 报告
  - build_markdown()：生成可读的覆盖检查报告文本（供导出/存档）
"""

import os

# 类型 key -> 打开方式说明（与 main_window 的分发逻辑保持一致）
#   design    → 国策设计视图（图形化）
#   gallery   → 实体图标画廊（图形化）
#   special   → 专用编辑器（初始部队等）
#   tree      → 通用 PDX 树形编辑器（含辅助功能的树编辑）
EDITOR_DISPATCH = {
    "focus": "国策设计视图",
    "character": "实体图标画廊",
    "idea": "实体图标画廊",
    "decision": "实体图标画廊",
    "event": "实体图标画廊",
    "super_event": "实体图标画廊",
    "tech": "实体图标画廊",
    "bookmark": "实体图标画廊",
    "special_project": "实体图标画廊",
    "initial_oob": "初始部队编辑器",
    "advisor_assign": "树形编辑器（含顾问分配辅助）",
    "country_history": "树形编辑器（含国家设置流程）",
    "gui": "树形编辑器",
    "gui_edit": "树形编辑器",
    "localisation": "树形编辑器",
    "gfx_definition": "树形编辑器",
    "mod_descriptor": "树形编辑器",
    "generic": "树形编辑器",
}

TREE_EDITOR_DEFAULT = "树形编辑器"


def opener_for(key):
    """返回类型 key 的打开方式描述（未显式登记的类型默认树形编辑器）。"""
    return EDITOR_DISPATCH.get(key, TREE_EDITOR_DEFAULT)


def is_tree_editor_opener(key):
    """判断该类型当前是否仍以树形编辑器为主要打开方式。"""
    return opener_for(key).startswith("树形编辑器")


def _ext_label(exts):
    """扩展名列表 → 显示文本（如 ".txt" 或 ".txt/.gui"）。"""
    if not exts:
        return ""
    return "/".join(exts)


def build_coverage_rows(mod_path=""):
    """构建覆盖报告行数据。

    Returns:
        list[dict]: {key, name, folders, exts, template, opener, count}
            count 为当前 mod 目录下该类型实际命中的文件数（未打开 mod 时为 -1）。
    """
    try:
        from workbench import CONTENT_TYPES, WorkbenchDock
    except Exception:
        return []

    rows = []
    for key, name, _icon, folders, tpl_type, ext in CONTENT_TYPES:
        exts = [ext] if isinstance(ext, str) else list(ext or [])
        count = -1
        if mod_path and os.path.isdir(mod_path):
            folders_l, exts_l = WorkbenchDock._type_folders_ext(key)
            count = 0
            seen = set()
            for rel in folders_l:
                base = mod_path if rel == "." else os.path.join(mod_path, rel)
                if not os.path.isdir(base):
                    continue
                for root, _dirs, names in os.walk(base):
                    for name_ in names:
                        fp = os.path.join(root, name_)
                        if os.path.isfile(fp) and WorkbenchDock._ext_matches(name_, exts_l):
                            real = os.path.realpath(fp)
                            if real not in seen:
                                seen.add(real)
                                count += 1
        rows.append({
            "key": key,
            "name": name,
            "folders": list(folders),
            "exts": exts,
            "template": bool(tpl_type),
            "opener": opener_for(key),
            "count": count,
        })
    return rows


def tree_editor_rows(rows):
    """筛选仍直接使用树形编辑器打开的类型行。"""
    return [r for r in rows if is_tree_editor_opener(r["key"])]


def build_markdown(mod_path="", game_path=""):
    """生成完整覆盖检查报告（Markdown 文本）。"""
    rows = build_coverage_rows(mod_path)
    if not rows:
        return "（无法加载内容类型定义）"

    lines = []
    lines.append("# HOI4 模组编辑器 · 文件类型覆盖检查报告")
    lines.append("")
    lines.append(f"- 生成时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- 当前 mod：{mod_path or '（未打开）'}")
    lines.append(f"- 游戏目录：{game_path or '（未配置）'}")
    lines.append("")

    total = len(rows)
    tree_rows = tree_editor_rows(rows)
    gallery = [r for r in rows if r["opener"] == "实体图标画廊"]
    design = [r for r in rows if r["opener"] == "国策设计视图"]
    special = [r for r in rows if r["opener"] == "初始部队编辑器"]
    notpl = [r for r in rows if not r["template"]]

    lines.append("## 一、总体统计")
    lines.append("")
    lines.append(f"- 内容类型总数：{total}")
    lines.append(f"- 图形化打开（设计视图/画廊/专用编辑器）：{len(design) + len(gallery) + len(special)}")
    lines.append(f"- 仍使用树形编辑器打开：{len(tree_rows)}")
    lines.append(f"- 暂无「新建文件」模板（可树形编辑）：{len(notpl)}")
    lines.append("")

    lines.append("## 二、仍直接使用树形编辑器打开的类型（待图形化）")
    lines.append("")
    if tree_rows:
        lines.append("| 类型 | 文件夹 | 扩展名 | 模板 | 当前mod文件数 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for r in tree_rows:
            tpl = "有" if r["template"] else "无"
            cnt = str(r["count"]) if r["count"] >= 0 else "—"
            lines.append(f"| {r['name']} | {', '.join(r['folders'])} | {_ext_label(r['exts'])} | {tpl} | {cnt} |")
    else:
        lines.append("（无）")
    lines.append("")

    lines.append("## 三、全部内容类型明细")
    lines.append("")
    lines.append("| 类型 | 文件夹 | 扩展名 | 模板 | 打开方式 | 当前mod文件数 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for r in rows:
        tpl = "有" if r["template"] else "无"
        cnt = str(r["count"]) if r["count"] >= 0 else "—"
        lines.append(f"| {r['name']} | {', '.join(r['folders'])} | {_ext_label(r['exts'])} | {tpl} | {r['opener']} | {cnt} |")
    lines.append("")

    lines.append("## 四、说明")
    lines.append("")
    lines.append("- 打开方式与实际分发逻辑一致：国策→设计视图；图标型→实体图标画廊；")
    lines.append("  history/units→初始部队编辑器；其余→通用 PDX 树形编辑器。")
    lines.append("- 「无新建模板」仅表示工作台「新建文件」未提供模板，文件仍可双击树形编辑，")
    lines.append("  无文件模式下也可直接新建实体（自动写入所选/当前国家文件）。")
    lines.append("- 无文件模式：左侧选类型，右侧跨文件浏览全部实体，支持国家筛选、关键词搜索、")
    lines.append("  新建/编辑/删除/移动/复制实体、选择/上传图标、编辑本地化名称与描述。")
    return "\n".join(lines)


class CoverageReportDialog:
    """应用内覆盖检查报告对话框（PyQt6）。"""

    def __init__(self, parent=None, mod_path="", game_path=""):
        self._parent = parent
        self._mod_path = mod_path
        self._game_path = game_path
        self._rows = []
        self._dlg = None

    def show(self):
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
            QTableWidgetItem, QPushButton, QMessageBox, QCheckBox, QApplication)

        rows = build_coverage_rows(self._mod_path)
        self._rows = rows
        dlg = QDialog(self._parent)
        dlg.setWindowTitle("文件类型覆盖检查报告")
        dlg.resize(980, 640)
        lay = QVBoxLayout(dlg)

        tree_rows = tree_editor_rows(rows)
        summary = (f"共 {len(rows)} 种内容类型；图形化打开 "
                   f"{len([r for r in rows if not r['opener'].startswith('树形编辑器')])} 种；"
                   f"仍用树形编辑器打开 {len(tree_rows)} 种；"
                   f"无新建模板 {len([r for r in rows if not r['template']])} 种")
        lay.addWidget(QLabel(summary))

        self._only_tree = QCheckBox("仅显示仍使用树形编辑器打开的类型")
        lay.addWidget(self._only_tree)

        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(
            ["类型", "文件夹", "扩展名", "模板", "打开方式", "当前mod文件数"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setStretchLastSection(False)
        table.setColumnWidth(0, 140)
        table.setColumnWidth(1, 320)
        table.setColumnWidth(4, 200)
        table.setColumnWidth(5, 90)
        lay.addWidget(table)

        def fill():
            shown = tree_rows if self._only_tree.isChecked() else rows
            table.setRowCount(len(shown))
            for i, r in enumerate(shown):
                table.setItem(i, 0, QTableWidgetItem(f"{r['name']}（{r['key']}）"))
                table.setItem(i, 1, QTableWidgetItem(", ".join(r["folders"])))
                table.setItem(i, 2, QTableWidgetItem(_ext_label(r["exts"])))
                table.setItem(i, 3, QTableWidgetItem("有" if r["template"] else "无"))
                table.setItem(i, 4, QTableWidgetItem(r["opener"]))
                table.setItem(i, 5, QTableWidgetItem(
                    str(r["count"]) if r["count"] >= 0 else "—"))

        self._only_tree.toggled.connect(lambda _c: fill())
        fill()

        btn_row = QHBoxLayout()
        copy_btn = QPushButton("📋 复制 Markdown 报告")
        copy_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(build_markdown(self._mod_path, self._game_path)))
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dlg.accept)
        btn_row.addStretch()
        btn_row.addWidget(copy_btn)
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)
        self._dlg = dlg
        dlg.exec()

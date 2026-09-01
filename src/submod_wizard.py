"""子 Mod 制作向导（阶段C）。

概念（见 docs/多mod冲突检查与子mod制作_设计计划.md §2）：
子 mod = 真实可玩的独立 mod，descriptor `dependencies` 声明依附的底层 mod；
编辑器进入子 mod 模式后：读取 = 层栈合并视图（子 mod → 底层 → 原版），
写入 = 恒落子 mod。

模块分两层：
  - 纯函数：build_submod_files（文件清单）/ submod_settings_fields
    （settings 字段）—— 可契约测试；
  - SubmodWizard：三步向导 UI（选播放集 → 勾底层 mod → 填信息），
    完成回调 activate_cb 由主窗口注入（负责写盘 + 激活层栈 +
    持久化 settings），向导自身不写 settings.json。

生成清单复用 mod_creator.write_mod_files 原子写；
.mod 内容用 mod_descriptor_loader 序列化（dependencies 引号转义）。
"""
from __future__ import annotations

import os

from mod_descriptor_loader import build_entries, format_mod_entries
from PyQt6.QtCore import Qt

from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout)


def _force_quote_path(text):
    """path 字段恒定加引号（游戏要求；目录含空格时不加引号会坏档）。"""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("path") and "=" in stripped \
                and '"' not in stripped:
            key, _, value = stripped.partition("=")
            lines.append('%s="%s"' % (key.strip(), value.strip()))
        else:
            lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def build_submod_files(name, folder_name, version="1.19.*", tags=None,
                       base_names=(), mod_folder_path="",
                       mod_file_path=""):
    """生成子 mod 项目文件清单（形状与 mod_creator.build_mod_files 一致）。

    与普通 mod 的差异：.mod / descriptor.mod 带 dependencies 块
    （逐字使用底层 mod 的 descriptor name），不含 country_tags。

    Returns:
        list[dict]: [{"path": absolute, "content": str, "bom": bool}]
    """
    tags = list(tags or [])
    base_names = [b for b in (base_names or ()) if b]
    submod_dir = os.path.join(mod_folder_path, folder_name)
    mod_file_full = os.path.join(mod_file_path, folder_name + ".mod")
    fields = {
        "name": name,
        "path": submod_dir.replace("\\", "/"),
        "supported_version": version or "1.19.*",
        "tags": tags,
        "dependencies": base_names,
    }
    mod_content = _force_quote_path(format_mod_entries(build_entries(fields)))
    files = [
        {"path": mod_file_full, "content": mod_content, "bom": False},
        {"path": os.path.join(submod_dir, "descriptor.mod"),
         "content": mod_content, "bom": False},
        {"path": os.path.join(submod_dir, "interface", folder_name + ".gfx"),
         "content": "spriteTypes = {\n\n}\n", "bom": False},
        {"path": os.path.join(submod_dir, "localisation", "simp_chinese",
                              folder_name + "_l_simp_chinese.yml"),
         "content": "l_simp_chinese:\n", "bom": True},
    ]
    return files


def submod_settings_fields(submod_path, submod_name, base_paths,
                           active=True):
    """子 mod 模式的 settings 字段（写入由 main_window 负责）。"""
    return {
        "submod_active": bool(active),
        "submod_path": submod_path or "",
        "submod_name": submod_name or "",
        "submod_bases": [p for p in (base_paths or ()) if p],
    }


def resolve_folder_name(name, existing_names=()):
    """由子 mod 名生成文件夹名（保留中文字符，替换路径非法字符，重名加序号）。"""
    folder = "".join(
        c for c in (name or "").strip()
        if c not in '\\/:*?"<>|' and c not in "\t\n\r")
    folder = folder or "submod"
    base = folder
    i = 2
    while folder in set(existing_names or ()):
        folder = "%s_%d" % (base, i)
        i += 1
    return folder


class SubmodWizard(QWizard):
    """三步向导：选播放集 → 勾底层 mod → 填子 mod 信息并创建。"""

    def __init__(self, parent=None, settings=None, user_dir="",
                 activate_cb=None):
        super().__init__(parent)
        self.setWindowTitle("子 Mod 制作向导")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.settings = settings or {}
        self.user_dir = user_dir
        self.activate_cb = activate_cb      # main_window 注入
        self.playset = None                 # 上一步加载的 Playset
        self._playset_id = None
        self._build_pages()
        self.setButtonText(QWizard.WizardButton.FinishButton, "创建并激活")

    # ---------- 页面 ----------

    def _build_pages(self):
        from playset_loader import list_playsets

        # 第 1 步：选播放集
        p1 = QWizardPage()
        p1.setTitle("选择播放集")
        p1.setSubTitle("读取 launcher-v2.sqlite 的播放集；"
                       "「dlc_load」为最近一次启动游戏的实际加载集合")
        lay = QVBoxLayout(p1)
        self.playset_combo = QComboBox()
        for entry in list_playsets(self.user_dir):
            self.playset_combo.addItem(entry["name"], entry["id"])
        lay.addWidget(self.playset_combo)
        self.hint1 = QLabel("")
        lay.addWidget(self.hint1)
        lay.addStretch()
        self.addPage(p1)

        # 第 2 步：勾选底层 mod
        p2 = QWizardPage()
        p2.setTitle("勾选底层 Mod")
        p2.setSubTitle("勾选的 mod 将写入子 mod 的 dependencies；"
                       "读取范围默认覆盖整个播放集")
        lay2 = QVBoxLayout(p2)
        self.mods_list = QListWidget()
        self.mods_list.setSelectionMode(
            QListWidget.SelectionMode.NoSelection)
        lay2.addWidget(self.mods_list)
        self.chk_read_all = QCheckBox("读取整个播放集（取消则只读勾选项）")
        self.chk_read_all.setChecked(True)
        lay2.addWidget(self.chk_read_all)
        self.hint2 = QLabel("")
        lay2.addWidget(self.hint2)
        self.addPage(p2)

        # 第 3 步：子 mod 信息
        p3 = QWizardPage()
        p3.setTitle("子 Mod 信息")
        p3.setSubTitle("创建位置：默认 mod 目录（settings.mod_folder_path）")
        lay3 = QVBoxLayout(p3)
        lay3.addWidget(QLabel("名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self._auto_folder)
        lay3.addWidget(self.name_edit)
        lay3.addWidget(QLabel("文件夹名:"))
        self.folder_edit = QLineEdit()
        lay3.addWidget(self.folder_edit)
        lay3.addWidget(QLabel("版本:"))
        self.version_edit = QLineEdit("1.19.*")
        lay3.addWidget(self.version_edit)
        lay3.addWidget(QLabel("标签（逗号分隔）:"))
        self.tags_edit = QLineEdit("Balance")
        lay3.addWidget(self.tags_edit)
        self.hint3 = QLabel("")
        lay3.addWidget(self.hint3)
        lay3.addStretch()
        self.addPage(p3)

        self.currentIdChanged.connect(self._on_page_changed)

    def _on_page_changed(self, page_id):
        from playset_loader import load_playset
        if page_id == 1 and self._playset_id != \
                self.playset_combo.currentData():
            self._playset_id = self.playset_combo.currentData()
            self.playset = load_playset(self.user_dir, self._playset_id)
            self.mods_list.clear()
            for m in self.playset.mods:
                item = QListWidgetItem(
                    "%s（%s）" % (m.name, m.source or "local"))
                item.setData(Qt.ItemDataRole.UserRole, m.content_dir)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked
                                   if m.content_dir
                                   else Qt.CheckState.Unchecked)
                if not m.content_dir:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                self.mods_list.addItem(item)
            self.hint2.setText("播放集共 %d 个 mod" % len(self.playset.mods))

    def _auto_folder(self):
        # 手动改过文件夹名则不覆盖
        if self.folder_edit.property("_manual"):
            return
        self.folder_edit.setText(resolve_folder_name(self.name_edit.text()))

    # ---------- 完成 ----------

    def selected_base_paths(self):
        out = []
        for i in range(self.mods_list.count()):
            it = self.mods_list.item(i)
            if it.checkState() == Qt.CheckState.Checked:
                p = it.data(Qt.ItemDataRole.UserRole)
                if p:
                    out.append(p)
        return out

    def all_playset_paths(self):
        if self.playset is None:
            return []
        return [m.content_dir for m in self.playset.mods if m.content_dir]

    def accept(self):
        """创建子 mod 并请求主窗口激活（写盘走 mod_creator 原子写）。"""
        from mod_creator import write_mod_files
        name = self.name_edit.text().strip()
        if not name:
            self.hint3.setText("请填写子 mod 名称")
            return
        folder = self.folder_edit.text().strip() or \
            resolve_folder_name(name)
        self.folder_edit.setText(folder)
        mod_folder_path = self.settings.get("mod_folder_path", "") or \
            QFileDialog.getExistingDirectory(
                self, "选择子 mod 创建目录")
        if not mod_folder_path:
            return
        mod_file_path = self.settings.get("mod_file_path", "") or \
            mod_folder_path
        base_names = []
        if self.playset is not None:
            checked_paths = set(self.selected_base_paths())
            for m in self.playset.mods:
                if m.content_dir and (not checked_paths
                                      or m.content_dir in checked_paths):
                    base_names.append(m.name)
        base_paths = (self.all_playset_paths()
                      if self.chk_read_all.isChecked()
                      else self.selected_base_paths())
        files = build_submod_files(
            name=name, folder_name=folder,
            version=self.version_edit.text().strip() or "1.19.*",
            tags=[t.strip() for t in self.tags_edit.text().split(",")
                  if t.strip()],
            base_names=base_names,
            mod_folder_path=mod_folder_path, mod_file_path=mod_file_path)
        try:
            write_mod_files(files)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "创建失败", str(e))
            return
        submod_path = os.path.dirname(files[1]["path"])
        if self.activate_cb is not None:
            self.activate_cb(submod_path, name, base_paths)
        super().accept()

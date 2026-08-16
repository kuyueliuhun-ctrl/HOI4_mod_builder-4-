"""区域编辑界面（工具菜单 → 区域编辑…）

对定义区域的 mod/游戏文件（strategicregions / supplyareas / states）：
- 左侧：类型 + 文件 + 区域列表（id、地块数），选中区域高亮其地块
- 中央：地图画布（框选 / 点选 / 手型）
- 操作：框选地块 → 新建区域（自动/手动 id）｜追加到选中区域｜从选中区域移除｜删除区域
- 写回：块级替换 provinces 内容（保留文件其余内容），原子写 + 撤销快照
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QGroupBox, QHBoxLayout, QInputDialog, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QToolButton,
    QVBoxLayout,
)

from map_canvas import (MapCanvas, MODE_PAN, MODE_RECT,
                        MODE_MULTI)
from map_region_ops import (
    REGION_KINDS, append_region, next_region_id, remove_region,
    scan_region_files, set_region_provinces,
)

_KIND_CN = {"strategic_region": "战略区域",
            "supply_area": "补给区域",
            "state": "州"}


class RegionEditorDialog(QDialog):
    """区域划分编辑界面。"""

    def __init__(self, parent=None, mod_path="", game_path=""):
        super().__init__(parent)
        self.mod_path = mod_path or ""
        self.game_path = game_path or ""
        self.files = []            # scan_region_files 结果（可编辑文件）
        self.current_file = None   # 当前编辑文件 dict
        self._last_pids = []

        self.setWindowTitle("区域编辑（框选划分区域）")
        self.resize(1440, 900)   # 默认大窗口，减少打开后的留白
        self._build_ui()
        self._reload_files()

    # ------------------------------------------------------------ UI
    def _build_ui(self):
        layout = QHBoxLayout(self)

        # 左栏
        left = QVBoxLayout()
        self.kind_combo = QComboBox()
        for k, cn in _KIND_CN.items():
            self.kind_combo.addItem(cn, k)
        self.kind_combo.currentIndexChanged.connect(self._reload_files)
        left.addWidget(QLabel("区域类型:"))
        left.addWidget(self.kind_combo)

        self.file_combo = QComboBox()
        self.file_combo.currentIndexChanged.connect(self._on_file_changed)
        left.addWidget(QLabel("文件:"))
        left.addWidget(self.file_combo)

        self.region_list = QListWidget()
        self.region_list.itemClicked.connect(self._on_region_clicked)
        left.addWidget(QLabel("区域（id · 地块数）:"))
        left.addWidget(self.region_list, 1)

        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        left.addWidget(self.info_label)
        layout.addLayout(left, 0)

        # 中央画布
        mid = QVBoxLayout()
        bar = QHBoxLayout()
        self.mode_group = []
        for mode, label, tip in (
            (MODE_PAN, "✋ 手型", "拖拽平移；单击/悬停查看地块信息"),
            (MODE_RECT, "▭ 框选", "拖拽框选地块"),
            (MODE_MULTI, "☑ 多选", "逐个点选地块加入/移出选区"),
        ):
            btn = QToolButton()
            btn.setText(label)
            btn.setToolTip(tip)
            btn.setCheckable(True)
            btn.setChecked(mode == MODE_PAN)
            btn.clicked.connect(lambda _c, m=mode: self.canvas.set_mode(m))
            self.mode_group.append(btn)
            bar.addWidget(btn)
        bar.addStretch(1)
        self.fit_btn = QPushButton("⌂ 全景")
        bar.addWidget(self.fit_btn)
        mid.addLayout(bar)

        self.canvas = MapCanvas(self.map_data())
        self.canvas.province_clicked.connect(self._on_province_clicked)
        self.canvas.rect_selected.connect(self._on_rect_selected)
        self.canvas.selection_changed.connect(self._on_selection_changed)
        self.fit_btn.clicked.connect(self.canvas.fit_map)
        try:
            from map_vector import get_edge_segments
            self.canvas.enable_vector_borders(
                get_edge_segments(self.map_data()))
            from map_fill import get_province_polygons
            fill = get_province_polygons(self.map_data())
            if fill is not None:
                self.canvas.enable_vector_fill(fill)
        except Exception:
            pass
        mid.addWidget(self.canvas, 1)

        # 初始视野：全景基础上放大（map_initial_zoom，默认 1.3，减少留白）
        from map_canvas import read_map_settings
        self.canvas.fit_map(factor=read_map_settings()["initial_zoom"])

        # 操作区
        ops = QHBoxLayout()
        self.btn_new = QPushButton("＋ 新建区域（用选区）")
        self.btn_new.clicked.connect(self._new_region)
        self.btn_append = QPushButton("＋ 追加到选中区域")
        self.btn_append.clicked.connect(self._append_to_region)
        self.btn_remove = QPushButton("－ 从选中区域移除选区")
        self.btn_remove.clicked.connect(self._remove_from_region)
        self.btn_delete = QPushButton("🗑 删除选中区域")
        self.btn_delete.clicked.connect(self._delete_region)
        self.btn_clear_sel = QPushButton("✕ 清空选区")
        self.btn_clear_sel.clicked.connect(self.canvas.clear_selection)
        self.btn_save = QPushButton("💾 保存当前文件")
        self.btn_save.setProperty("class", "primary")
        self.btn_save.clicked.connect(self._save_file)
        for b in (self.btn_new, self.btn_append, self.btn_remove,
                  self.btn_delete, self.btn_clear_sel, self.btn_save):
            ops.addWidget(b)
        ops.addStretch(1)
        mid.addLayout(ops)
        layout.addLayout(mid, 1)

    def map_data(self):
        from oob_map_editor import get_map_data
        return get_map_data(self.mod_path, self.game_path)

    # ------------------------------------------------------------ 数据
    def _reload_files(self):
        kind = self.kind_combo.currentData()
        self.files = [f for f in scan_region_files(self.mod_path,
                                                   self.game_path)
                      if f["kind"] == kind]
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        for f in self.files:
            mark = "（mod）" if f["source"] == "mod" else "（游戏）"
            self.file_combo.addItem("%s %s" % (os.path.basename(f["rel"]),
                                               mark))
        self.file_combo.blockSignals(False)
        if self.files:
            self.file_combo.setCurrentIndex(0)
            self._on_file_changed(0)
        else:
            self.current_file = None
            self.region_list.clear()
            self.info_label.setText("当前类型下没有可编辑的区域文件")

    def _on_file_changed(self, index):
        if not (0 <= index < len(self.files)):
            self.current_file = None
            self.region_list.clear()
            return
        self.current_file = self.files[index]
        self.region_list.blockSignals(True)
        self.region_list.clear()
        for r in self.current_file["regions"]:
            item = QListWidgetItem("%d · %d 地块" % (r["id"], len(r["provinces"])))
            item.setData(Qt.ItemDataRole.UserRole, r["id"])
            self.region_list.addItem(item)
        self.region_list.blockSignals(False)
        self.canvas.clear_highlight()
        self.info_label.setText(
            "%s：%d 个区域（点选区域查看地块，框选后可用右侧操作）"
            % (os.path.basename(self.current_file["rel"]),
               len(self.current_file["regions"])))

    def _on_region_clicked(self, item):
        rid = item.data(Qt.ItemDataRole.UserRole)
        for r in self.current_file["regions"]:
            if r["id"] == rid:
                self.canvas.highlight_pids(r["provinces"])
                self.info_label.setText(
                    "区域 %d：%d 个地块（%s）"
                    % (rid, len(r["provinces"]),
                       ", ".join(str(p) for p in r["provinces"][:20])
                       + ("…" if len(r["provinces"]) > 20 else "")))
                break

    def _on_province_clicked(self, pid, x, y):
        md = self.map_data()
        info = md.province_table.get(pid, {})
        self.info_label.setText("地块 %d ｜ 类型 %s ｜ 地形 %s"
                                % (pid, info.get("type", "?"),
                                   info.get("terrain", "?")))

    # ------------------------------------------------------------ 框选/选区
    def _on_rect_selected(self, pids, x0, y0, x1, y1):
        self._last_pids = list(pids)
        self.info_label.setText(
            "框选 %d 个地块（%d,%d → %d,%d）：\n%s"
            % (len(pids), x0, y0, x1, y1,
               ", ".join(str(p) for p in pids[:30])
               + ("…" if len(pids) > 30 else "")))

    def _on_selection_changed(self, pids):
        """选区变化（框选/多选）：更新反馈。"""
        self._last_pids = list(pids)
        if not pids:
            return
        if not self.info_label.text().startswith("框选"):
            self.info_label.setText(
                "已选 %d 个地块：\n%s"
                % (len(pids),
                   ", ".join(str(p) for p in pids[:30])
                   + ("…" if len(pids) > 30 else "")))

    def _require_pids(self, what):
        if not self._last_pids:
            QMessageBox.information(self, "提示",
                                    "请先在地图上框选地块（▭ 框选模式）")
            return None
        return list(self._last_pids)

    def _selected_region_id(self):
        item = self.region_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------ 操作
    def _new_region(self):
        pids = self._require_pids("新建区域")
        if pids is None or self.current_file is None:
            return
        nxt = next_region_id(self.current_file["regions"])
        rid_text, ok = QInputDialog.getText(
            self, "新建区域", "区域 id（留空自动使用 %d）：" % nxt, text=str(nxt))
        if not ok:
            return
        try:
            rid = int(rid_text.strip())
        except ValueError:
            QMessageBox.warning(self, "新建区域", "id 必须是数字")
            return
        content = append_region(self.current_file["content"],
                                self.current_file["kind"], rid, pids)
        if content is None:
            return
        self._apply_content(content)
        self.info_label.setText("已新建区域 %d（%d 个地块），点击保存写回文件"
                                % (rid, len(pids)))

    def _append_to_region(self):
        pids = self._require_pids("追加")
        if pids is None or self.current_file is None:
            return
        rid = self._selected_region_id()
        if rid is None:
            QMessageBox.information(self, "提示", "请先在左侧选中目标区域")
            return
        merged = list(pids)
        for r in self.current_file["regions"]:
            if r["id"] == rid:
                merged = list(dict.fromkeys(r["provinces"] + pids))
                break
        content = set_region_provinces(self.current_file["content"],
                                       self.current_file["kind"], rid, merged)
        if content is None:
            return
        self._apply_content(content)
        self.info_label.setText("已把 %d 个地块追加到区域 %d（共 %d 个），点击保存"
                                % (len(pids), rid, len(merged)))

    def _remove_from_region(self):
        pids = self._require_pids("移除")
        if pids is None or self.current_file is None:
            return
        rid = self._selected_region_id()
        if rid is None:
            QMessageBox.information(self, "提示", "请先在左侧选中目标区域")
            return
        for r in self.current_file["regions"]:
            if r["id"] == rid:
                rest = [p for p in r["provinces"] if p not in pids]
                content = set_region_provinces(
                    self.current_file["content"],
                    self.current_file["kind"], rid, rest)
                if content is None:
                    return
                self._apply_content(content)
                self.info_label.setText("已从区域 %d 移除 %d 个地块（剩 %d 个），点击保存"
                                        % (rid, len(pids), len(rest)))
                return
        QMessageBox.information(self, "提示", "未找到区域 %d" % rid)

    def _delete_region(self):
        if self.current_file is None:
            return
        rid = self._selected_region_id()
        if rid is None:
            QMessageBox.information(self, "提示", "请先在左侧选中要删除的区域")
            return
        if QMessageBox.question(
                self, "删除区域",
                "确定删除区域 %d？（保存后生效，可通过撤销恢复）" % rid) \
                != QMessageBox.StandardButton.Yes:
            return
        content = remove_region(self.current_file["content"],
                                self.current_file["kind"], rid)
        if content is None:
            return
        self._apply_content(content)
        self.info_label.setText("已删除区域 %d，点击保存写回文件" % rid)

    def _apply_content(self, content):
        """应用内存内容变更并刷新列表/高亮。"""
        from map_region_ops import parse_region_file
        self.current_file["content"] = content
        self.current_file["regions"] = parse_region_file(
            content, self.current_file["kind"])
        self._on_file_changed(self.file_combo.currentIndex())

    def _save_file(self):
        if self.current_file is None:
            return
        fp = self._current_file_path()
        if not fp:
            QMessageBox.warning(
                self, "保存",
                "当前文件来自游戏本体（mod 未覆盖）。\n"
                "请在 mod 中创建对应文件后再保存（本工具不修改游戏文件）。")
            return
        from write_utils import atomic_write_text
        try:
            atomic_write_text(fp, self.current_file["content"])
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return
        QMessageBox.information(
            self, "已保存", "已写回：\n%s\n（可在「工具 → 撤销上次文件写入」撤销）"
            % os.path.relpath(fp, self.mod_path))

    def _current_file_path(self):
        """mod 内文件路径（游戏源文件返回 None）。"""
        if self.current_file is None:
            return None
        rel = self.current_file["rel"].replace("/", os.sep)
        fp = os.path.join(self.mod_path, rel)
        return fp if os.path.isfile(fp) else None

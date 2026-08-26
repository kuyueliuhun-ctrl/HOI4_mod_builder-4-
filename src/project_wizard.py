"""内容项目向导：无文件模式一键生成「国策项目」的配套文件

思想：用户只描述一个「国策项目」（国家、国策 id、中文名、可选配套），
程序自动完成相关文件编写：

- 国策块 → 写入该国的国策文件（focus_tree 包装块内）
- 触发事件 → events/<TAG>_events.txt（追加 country_event，国策 completion_reward 自动关联）
- 决议 → common/decisions/<TAG>_decisions.txt（追加类别 + 决议）
- 图标占位 → gfx/interface/goals/<id>.png（Pillow 生成灰底占位图）+ goals_mod.gfx 精灵定义
- 本地化 → localisation/simp_chinese/<TAG>_mod_l_simp_chinese.yml（自动追加词条）

所有写入使用 UTF-8 无 BOM（HOI4 脚本解析器要求），只写 mod 目录。
"""

import os

import icon_ops
import path_safety


def _append_block(path, block, header=""):
    """将块文本追加到文件末尾（文件不存在则创建目录与骨架）。

    Args:
        path: 目标文件
        block: 追加的块文本（不含缩进调整）
        header: 新文件时的头部骨架（如 "decisions = {"），None 表示不加包装
    Returns:
        str: 文件相对 mod 的路径（用于汇总展示）
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
    else:
        content = ""
    rstripped = content.rstrip()
    if header:
        # 包装块文件：块插入包装块闭合 } 前；无包装块则新建包装
        if header in content:
            idx = content.rfind("}")
            new_content = content[:idx] + "\n" + block + content[idx:]
        else:
            new_content = (rstripped + ("\n" if rstripped else "")
                           + header + "\n" + block + "}\n")
    else:
        new_content = rstripped + ("\n" if rstripped else "") + block
    icon_ops.write_file_utf8(path, new_content)
    return path


def _write_loc_entries(mod_path, tag, entries):
    """把词条写入 mod 本地化文件（追加式，不覆盖已有词条）。"""
    if not entries:
        return ""
    path_safety.validate_component(tag, "tag")
    loc_dir = os.path.join(mod_path, "localisation", "simp_chinese")
    os.makedirs(loc_dir, exist_ok=True)
    path = os.path.join(loc_dir, f"{tag}_mod_l_simp_chinese.yml")
    existing = {}
    if os.path.isfile(path):
        try:
            from localization_mgr import parse_loc_yml_file
            parse_loc_yml_file(path, existing)
        except Exception:
            existing = {}
    lines = ["l_simp_chinese:"]
    for key in sorted(entries):
        if key in existing:
            continue
        val = entries[key].replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        lines.append(f' {key}: "{val}"')
    icon_ops.write_file_utf8(path, "\n".join(lines) + "\n")
    return path


def _create_placeholder_icon(mod_path, focus_id):
    """生成 130x130 灰底占位图标 + goals_mod.gfx 精灵定义。

    Returns:
        str: 图标引用值（GFX_goal_<focus_id>）
    """
    img_dir = os.path.join(mod_path, "gfx", "interface", "goals")
    os.makedirs(img_dir, exist_ok=True)
    png_path = os.path.join(img_dir, f"{focus_id}.png")
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (130, 130), (90, 90, 96))
        d = ImageDraw.Draw(img)
        d.rectangle([2, 2, 127, 127], outline=(150, 150, 150), width=2)
        d.line([(10, 65), (120, 65)], fill=(150, 150, 150), width=1)
        d.line([(65, 10), (65, 120)], fill=(150, 150, 150), width=1)
        img.save(png_path, "PNG")
    except Exception:
        pass
    sprite = f"GFX_goal_{focus_id}"
    gfx_file = os.path.join(mod_path, "gfx", "interface", "goals_mod.gfx")
    icon_ops.update_gfx_file(gfx_file, sprite, f"gfx/interface/goals/{focus_id}.png")
    return sprite


def _insert_focus_block(focus_file, block):
    """把国策块插入 focus_tree/shared_focus 包装块内（无包装则新建）。"""
    os.makedirs(os.path.dirname(focus_file), exist_ok=True)
    if os.path.isfile(focus_file):
        with open(focus_file, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
    else:
        content = ""
    start, end = icon_ops.find_block_range(
        content, {"focus_tree", "shared_focus", "joint_focus"})
    if start >= 0 and end > start:
        insert_pos = end - 1
        new_content = content[:insert_pos] + block + content[insert_pos:]
    else:
        new_content = (content.rstrip() + ("\n" if content.strip() else "")
                       + "focus_tree = {\n" + block + "}\n")
    icon_ops.write_file_utf8(focus_file, new_content)


def build_focus_block(focus_id, event_id, x, y, include_event):
    """构造国策块文本。"""
    lines = [
        f"\t{focus_id} = {{",
        f"\t\tid = {focus_id}",
        f"\t\ticon = GFX_goal_{focus_id}",
        f"\t\tx = {x}",
        f"\t\ty = {y}",
        f"\t\tcost = 10",
    ]
    if include_event and event_id:
        lines.append(f"\t\tcompletion_reward = {{")
        lines.append(f"\t\t\tcountry_event = {{ id = {event_id} }}")
        lines.append(f"\t\t}}")
    lines.append(f"\t}}")
    return "\n".join(lines) + "\n"


def build_event_block(event_id):
    """构造触发事件块文本。"""
    return (
        f"country_event = {{\n"
        f"\tid = {event_id}\n"
        f"\ttitle = {event_id}_t\n"
        f"\tdesc = {event_id}_d\n"
        f"\tpicture = GFX_event_generic\n"
        f"\tis_triggered_only = yes\n"
        f"}}\n"
    )


def build_decision_block(tag, decision_id):
    """构造决议类别 + 决议块文本。"""
    return (
        f"decisions = {{\n"
        f"\t{tag}_category = {{\n"
        f"\t\ticon = GFX_decision_generic\n"
        f"\t\t{decision_id} = {{\n"
        f"\t\t\tvisible = {{ always = yes }}\n"
        f"\t\t\tavailable = {{ always = yes }}\n"
        f"\t\t\tdays_remove = 1\n"
        f"\t\t\tcustom_cost_trigger = {{ always = yes }}\n"
        f"\t\t\tcustom_cost_text = \"\"\n"
        f"\t\t\tcomplete_effect = {{ }}\n"
        f"\t\t}}\n"
        f"\t}}\n"
        f"}}\n"
    )


def generate_project(data, mod_path, focus_file):
    """按向导数据生成整套项目文件。

    Args:
        data: ContentProjectDialog.get_data() 返回值
        mod_path: mod 根目录
        focus_file: 国策写入目标文件（该国现有 focus 文件）

    Returns:
        list[str]: 生成结果汇总（每行一个说明）
    """
    summary = []
    focus_id = data["focus_id"]
    tag = (data.get("country") or "").strip().upper()
    event_id = f"{focus_id}_event"
    decision_id = f"{focus_id}_decision"

    # 1. 国策块（插入包装块内）
    _insert_focus_block(
        focus_file,
        build_focus_block(focus_id, event_id, data["x"], data["y"],
                          bool(data.get("event"))))
    summary.append(f"🌳 国策已写入: {os.path.relpath(focus_file, mod_path)}")

    # 2. 触发事件
    if data.get("event"):
        ev_path = os.path.join(mod_path, "events", f"{tag}_events.txt")
        _append_block(ev_path, build_event_block(event_id))
        summary.append(f"📜 事件已写入: events/{tag}_events.txt")

    # 3. 决议
    if data.get("decision"):
        dec_path = os.path.join(mod_path, "common", "decisions", f"{tag}_decisions.txt")
        _append_block(dec_path, build_decision_block(tag, decision_id))
        summary.append(f"📋 决议已写入: common/decisions/{tag}_decisions.txt")

    # 4. 图标占位
    if data.get("icon"):
        try:
            sprite = _create_placeholder_icon(mod_path, focus_id)
            summary.append(f"🎨 图标占位已生成: {sprite}")
        except Exception as e:
            summary.append(f"⚠ 图标占位生成失败: {e}")

    # 5. 本地化
    if data.get("localisation"):
        entries = {focus_id: data["name"]}
        if data.get("desc"):
            entries[f"{focus_id}_desc"] = data["desc"]
        if data.get("event"):
            entries[f"{event_id}_t"] = data["name"]
            if data.get("desc"):
                entries[f"{event_id}_d"] = data["desc"]
        if data.get("decision"):
            entries[f"{decision_id}_name"] = data["name"]
            if data.get("desc"):
                entries[f"{decision_id}_desc"] = data["desc"]
        loc_path = _write_loc_entries(mod_path, tag or "generic", entries)
        if loc_path:
            summary.append(f"🌐 本地化已写入: localisation/simp_chinese/{os.path.basename(loc_path)}")

    return summary


class ContentProjectDialog:
    """内容项目向导对话框（PyQt6）：输入项目信息并勾选配套生成项。"""

    def __init__(self, parent=None, country="", mod_path=""):
        self._parent = parent
        self._default_country = (country or "").strip().upper()
        self._mod_path = mod_path
        self._dlg = None
        self._data = None

    def exec(self):
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QFormLayout, QLineEdit, QCheckBox,
            QSpinBox, QDialogButtonBox, QLabel)

        dlg = QDialog(self._parent)
        dlg.setWindowTitle("新建国策项目（联动生成）")
        dlg.resize(480, 420)
        lay = QVBoxLayout(dlg)

        hint = QLabel(
            "填写项目信息后，程序自动完成相关文件编写：\n"
            "国策块 → 事件 → 决议 → 图标占位 → 本地化词条")
        hint.setStyleSheet("color: #5d6b7a;")
        lay.addWidget(hint)

        form = QFormLayout()
        self.country_edit = QLineEdit(self._default_country)
        form.addRow("国家 tag：", self.country_edit)
        self.id_edit = QLineEdit(f"{self._default_country}_new_focus" if self._default_country else "new_focus")
        form.addRow("国策 id：", self.id_edit)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：整合奥地利（中文）")
        form.addRow("中文名称：", self.name_edit)
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("（可选）")
        form.addRow("中文描述：", self.desc_edit)
        self.x_spin = QSpinBox()
        self.x_spin.setRange(-200, 200)
        self.y_spin = QSpinBox()
        self.y_spin.setRange(-200, 200)
        form.addRow("国策坐标 X：", self.x_spin)
        form.addRow("国策坐标 Y：", self.y_spin)
        lay.addLayout(form)

        self.cb_event = QCheckBox("生成触发事件（国策完成后触发，自动关联）")
        self.cb_event.setChecked(True)
        self.cb_decision = QCheckBox("生成决议（同国家类别下）")
        self.cb_decision.setChecked(True)
        self.cb_icon = QCheckBox("生成图标占位（130×130 PNG + .gfx 精灵）")
        self.cb_icon.setChecked(True)
        self.cb_loc = QCheckBox("自动写入本地化词条（名称/描述）")
        self.cb_loc.setChecked(True)
        lay.addWidget(self.cb_event)
        lay.addWidget(self.cb_decision)
        lay.addWidget(self.cb_icon)
        lay.addWidget(self.cb_loc)

        btnbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btnbox.button(QDialogButtonBox.StandardButton.Ok).setText("生成")
        btnbox.accepted.connect(self._on_ok)
        btnbox.rejected.connect(dlg.reject)
        lay.addWidget(btnbox)
        self._dlg = dlg
        return dlg.exec()

    def _on_ok(self):
        focus_id = self.id_edit.text().strip()
        name = self.name_edit.text().strip()
        if not focus_id or not name:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self._dlg, "提示", "请填写国策 id 与中文名称")
            return
        self._data = {
            "country": self.country_edit.text().strip(),
            "focus_id": focus_id,
            "name": name,
            "desc": self.desc_edit.text().strip(),
            "x": self.x_spin.value(),
            "y": self.y_spin.value(),
            "event": self.cb_event.isChecked(),
            "decision": self.cb_decision.isChecked(),
            "icon": self.cb_icon.isChecked(),
            "localisation": self.cb_loc.isChecked(),
        }
        self._dlg.accept()

    def get_data(self):
        return self._data

"""内容生成器工作台对话框

把第二批生成的六个生成器（民族精神/意识形态/角色/将领/国家Tag/国策全套）
统一成一个表单式对话框，选择类型 → 填字段 → 生成并写文件。
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
)

from write_utils import atomic_write_text


def _loc_text(locs):
    lines = ["l_english:"]
    for e in locs:
        lines.append(' {}: "{}"'.format(e["key"], e["value"]))
    return "\n".join(lines) + "\n"


class ContentGeneratorDialog(QDialog):
    """内容生成器工作台（非模态）。"""

    GEN_TYPES = [
        ("ideas", "民族精神（ideas）"),
        ("ideology", "意识形态"),
        ("character", "角色 Character"),
        ("general", "将领代码"),
        ("country", "批量创建国家 Tag"),
        ("focus", "国策全套"),
    ]

    def __init__(self, mod_path=""):
        super().__init__()
        self.mod_path = mod_path or ""
        self.setWindowTitle("内容生成器工作台")
        self.setMinimumWidth(620)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.type_combo = QComboBox()
        for key, label in self.GEN_TYPES:
            self.type_combo.addItem(label, key)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("类型:", self.type_combo)

        # 通用字段
        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("实体 ID / 逗号分隔（国策全套）")
        form.addRow("ID:", self.id_edit)

        self.extra1_edit = QLineEdit()
        form.addRow("图片/名称:", self.extra1_edit)

        self.extra2_edit = QLineEdit()
        form.addRow("TAG/命名空间:", self.extra2_edit)

        # 输出路径
        self.out_edit = QLineEdit()
        self.out_edit.setPlaceholderText("输出文件（缺省仅预览）")
        browse = QPushButton("浏览…")
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.out_edit, 1)
        row.addWidget(browse)
        form.addRow("输出文件:", row)

        self.loc_edit = QLineEdit()
        self.loc_edit.setPlaceholderText("本地化输出 yml（可选）")
        loc_browse = QPushButton("…")
        loc_browse.clicked.connect(self._browse_loc)
        lrow = QHBoxLayout()
        lrow.addWidget(self.loc_edit, 1)
        lrow.addWidget(loc_browse)
        form.addRow("本地化输出:", lrow)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        gen_btn = QPushButton("生成")
        gen_btn.clicked.connect(self._on_generate)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        btns.addWidget(gen_btn)
        btns.addWidget(close_btn)
        layout.addLayout(btns)

        self._on_type_changed()

    def _on_type_changed(self):
        gtype = self.type_combo.currentData()
        self.extra1_edit.setPlaceholderText(
            {"ideas": "图片名（缺省 GFX_idea_<id>）",
             "ideology": "",
             "character": "姓名本地化键",
             "general": "将领本地化键",
             "country": "国家名（显示名）",
             "focus": ""}[gtype])
        self.extra2_edit.setPlaceholderText(
            {"character": "国家 TAG",
             "general": "意识形态（缺省 neutrality）",
             "country": "",
             "focus": "国策树 ID（缺省 PROJECT）",
             "ideas": "",
             "ideology": ""}[gtype])

    def _browse(self):
        gtype = self.type_combo.currentData()
        start = self.mod_path or ""
        if gtype == "country":
            path = QFileDialog.getExistingDirectory(self, "选择输出目录", start)
            if path:
                self.out_edit.setText(path)
            return
        f = "PDX 脚本 (*.txt);;所有文件 (*)" if gtype != "general" else "脚本 (*.txt)"
        path, _ = QFileDialog.getSaveFileName(self, "生成输出文件", start, f)
        if path:
            self.out_edit.setText(path)

    def _browse_loc(self):
        path, _ = QFileDialog.getSaveFileName(self, "本地化输出", "", "本地化 (*.yml)")
        if path:
            self.loc_edit.setText(path)

    def _on_generate(self):
        gtype = self.type_combo.currentData()
        gid = self.id_edit.text().strip()
        if not gid and gtype != "country":
            QMessageBox.warning(self, "错误", "请填写 ID")
            return
        try:
            text, loc = self._generate(gtype, gid)
        except Exception as e:
            QMessageBox.warning(self, "生成失败", str(e))
            return
        out = self.out_edit.text().strip()
        loc_out = self.loc_edit.text().strip()
        if out:
            if gtype == "country":
                os.makedirs(out, exist_ok=True)
                for fn, t in text.items():
                    atomic_write_text(os.path.join(out, fn), t, encoding="utf-8")
            else:
                os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
                atomic_write_text(out, text, encoding="utf-8")
        if loc_out and loc:
            os.makedirs(os.path.dirname(os.path.abspath(loc_out)) or ".", exist_ok=True)
            atomic_write_text(loc_out, _loc_text(loc), encoding="utf-8-sig", allow_bom=True)
        QMessageBox.information(self, "完成",
                                "已生成{}。\n输出：{}\n本地化：{}".format(
                                    "（预览）" if not out else "",
                                    out or "—", loc_out or "—"))

    def _generate(self, gtype, gid):
        import idea_gen, ideology_gen, character_gen, general_gen, country_boot, focus_package_gen
        if gtype == "ideas":
            r = idea_gen.generate_ideas([{"id": gid, "picture": self.extra1_edit.text().strip() or None}])
            return r["text"], r["loc"]
        if gtype == "ideology":
            r = ideology_gen.generate_ideologies([{"id": gid}])
            return r["text"], r["loc"]
        if gtype == "character":
            tag = self.extra2_edit.text().strip() or "AAA"
            r = character_gen.generate_characters([{"tag": tag, "characters": [
                {"id": gid, "name_loc": self.extra1_edit.text().strip() or None}]}])
            return r["text"], r["loc"]
        if gtype == "general":
            r = general_gen.generate_leader_blocks([{"name_loc": self.extra1_edit.text().strip() or None,
                                                     "ideology": self.extra2_edit.text().strip() or "neutrality"}])
            return r["text"], r["loc"]
        if gtype == "country":
            name = self.extra1_edit.text().strip()
            r = country_boot.generate_country_bootstrap([{"tag": gid, "name": name or gid}])
            return r["histories"], r["loc"]
        if gtype == "focus":
            tree = self.extra2_edit.text().strip() or "PROJECT"
            focuses = [{"id": x.strip(), "x": 0, "y": 0}
                       for x in gid.split(",") if x.strip()]
            pkg = focus_package_gen.generate_package(focuses, tree_id=tree)
            return pkg["tree"]["text"], pkg["loc"]
        raise ValueError("未知类型")


def open_content_generator_dialog(mod_path="", parent=None):
    dlg = ContentGeneratorDialog(mod_path=mod_path)
    dlg.setParent(parent) if parent else None
    dlg.show()
    return dlg
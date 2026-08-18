"""AI 集成对话框：配置对话框 + 创作助手对话框

创作助手流程：
    选择内容类型 → 输入需求 → 生成（后台线程调用 API）→
    解析代码块预览 → 选择写入目标文件 → 落盘并刷新界面

写入规则：
    - 国策类型：插入 focus_tree 包装块内（复用项目向导逻辑）
    - 其余类型：追加到文件末尾（复用项目向导 _append_block）
"""

import os

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QLabel,
    QPushButton, QPlainTextEdit, QComboBox, QInputDialog, QMessageBox,
    QDoubleSpinBox, QApplication)


# ────────────── 配置对话框 ──────────────

class AiConfigDialog(QDialog):
    """AI 服务配置对话框（base_url / api_key / model / temperature）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 设置")
        self.resize(460, 240)
        from ai_assist import get_ai_config
        cfg = get_ai_config()

        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.url_edit = QLineEdit(cfg.get("base_url", ""))
        self.url_edit.setPlaceholderText("https://api.deepseek.com")
        form.addRow("API 地址：", self.url_edit)
        self.key_edit = QLineEdit(cfg.get("api_key", ""))
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("sk-…")
        form.addRow("API Key：", self.key_edit)
        self.model_edit = QLineEdit(cfg.get("model", "deepseek-chat"))
        self.model_edit.setPlaceholderText("deepseek-chat / gpt-4o-mini …")
        form.addRow("模型：", self.model_edit)
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(float(cfg.get("temperature", 0.7)))
        form.addRow("温度：", self.temp_spin)
        lay.addLayout(form)

        hint = QLabel("支持 OpenAI 兼容接口（DeepSeek / OpenAI / 通义千问等），"
                      "Key 仅保存在本地 settings.json")
        hint.setStyleSheet("color: #5d6b7a;")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        lay.addLayout(btn_row)

    def _save(self):
        from ai_assist import save_ai_config
        try:
            save_ai_config(
                base_url=self.url_edit.text(),
                api_key=self.key_edit.text(),
                model=self.model_edit.text(),
                temperature=self.temp_spin.value())
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
            return
        QMessageBox.information(self, "成功", "AI 配置已保存")
        self.accept()


# ────────────── 生成线程 ──────────────

class _GenWorker(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, messages, parent=None):
        super().__init__(parent)
        self._messages = messages

    def run(self):
        try:
            from ai_assist import chat
            self.done.emit(chat(self._messages))
        except Exception as e:
            self.failed.emit(str(e))


# ────────────── 创作助手对话框 ──────────────

class AiAssistDialog(QDialog):
    """AI 创作助手：需求 → 生成 → 预览 → 落盘。"""

    def __init__(self, parent=None, content_type_key="", mod_path=""):
        super().__init__(parent)
        self.setWindowTitle("AI 创作助手")
        self.resize(760, 640)
        self._mod_path = mod_path
        self._content_type_key = content_type_key or ""
        self._gen_worker = None
        self._preview_text = ""

        from workbench import CONTENT_TYPES
        self._types = [(c[1], c[0]) for c in CONTENT_TYPES]

        lay = QVBoxLayout(self)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("内容类型："))
        self.type_combo = QComboBox()
        for name, key in self._types:
            self.type_combo.addItem(name, key)
        idx = 0
        for i, (_n, k) in enumerate(self._types):
            if k == self._content_type_key:
                idx = i
                break
        self.type_combo.setCurrentIndex(idx)
        top_row.addWidget(self.type_combo)
        top_row.addStretch()
        cfg_btn = QPushButton("⚙ AI 设置…")
        cfg_btn.clicked.connect(self._open_config)
        top_row.addWidget(cfg_btn)
        lay.addLayout(top_row)

        lay.addWidget(QLabel("需求描述："))
        self.req_edit = QPlainTextEdit()
        self.req_edit.setPlaceholderText(
            "例如：为德国添加一个国策，完成时触发事件，效果为获得 2 点稳定度并吞并奥地利")
        self.req_edit.setFixedHeight(100)
        lay.addWidget(self.req_edit)

        gen_row = QHBoxLayout()
        gen_row.addStretch()
        self.gen_btn = QPushButton("🚀 生成")
        self.gen_btn.clicked.connect(self._generate)
        gen_row.addWidget(self.gen_btn)
        lay.addLayout(gen_row)

        lay.addWidget(QLabel("生成预览（可手动修改后写入）："))
        self.preview_edit = QPlainTextEdit()
        self.preview_edit.setPlaceholderText("AI 生成的 PDX 脚本将显示在这里…")
        lay.addWidget(self.preview_edit, 1)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(QLabel("写入文件："))
        self.file_combo = QComboBox()
        self.file_combo.setMinimumWidth(320)
        bottom_row.addWidget(self.file_combo, 1)
        new_file_btn = QPushButton("＋ 新建文件")
        new_file_btn.clicked.connect(self._new_target_file)
        bottom_row.addWidget(new_file_btn)
        bottom_row.addStretch()
        self.write_btn = QPushButton("💾 写入 mod")
        self.write_btn.clicked.connect(self._write)
        bottom_row.addWidget(self.write_btn)
        lay.addLayout(bottom_row)

        self._reload_target_files()
        if self.file_combo.count() == 0:
            self._ensure_default_target()

    # ---------- 目标文件 ----------

    def _type_folders_ext(self, key):
        try:
            from workbench import WorkbenchDock
            return WorkbenchDock._type_folders_ext(key)
        except Exception:
            return [], [".txt"]

    def _reload_target_files(self):
        """列出当前类型目录下的现有文件。"""
        self.file_combo.clear()
        key = self.type_combo.currentData()
        if not self._mod_path or not os.path.isdir(self._mod_path):
            return
        folders, exts = self._type_folders_ext(key)
        seen = set()
        for rel in folders:
            base = self._mod_path if rel == "." else os.path.join(self._mod_path, rel)
            if not os.path.isdir(base):
                continue
            for root, _dirs, names in os.walk(base):
                for name in sorted(names):
                    if not name.lower().endswith(tuple(exts)):
                        continue
                    fp = os.path.join(root, name)
                    real = os.path.realpath(fp)
                    if real in seen:
                        continue
                    seen.add(real)
                    self.file_combo.addItem(
                        os.path.relpath(fp, self._mod_path).replace(os.sep, "/"), fp)

    def _ensure_default_target(self):
        """无现有文件时生成默认目标文件路径。"""
        key = self.type_combo.currentData()
        folders, exts = self._type_folders_ext(key)
        ext = exts[0] if exts else ".txt"
        if folders and folders[0] != ".":
            rel = os.path.join(folders[0], f"ai_generated{ext}")
        else:
            rel = f"ai_generated{ext}"
        self.file_combo.addItem(rel + "（新建）", os.path.join(self._mod_path, rel))

    def _new_target_file(self):
        key = self.type_combo.currentData()
        folders, exts = self._type_folders_ext(key)
        ext = exts[0] if exts else ".txt"
        name, ok = QInputDialog.getText(
            self, "新建文件", "文件名（不含扩展名）:", text="ai_generated")
        if not ok or not name.strip():
            return
        name = name.strip() + ext
        if folders and folders[0] != ".":
            rel = os.path.join(folders[0], name)
        else:
            rel = name
        fp = os.path.join(self._mod_path, rel)
        self.file_combo.addItem(rel, fp)
        self.file_combo.setCurrentIndex(self.file_combo.count() - 1)

    # ---------- 生成 ----------

    def _open_config(self):
        dlg = AiConfigDialog(self)
        dlg.exec()

    def _generate(self):
        from ai_assist import build_messages
        user_text = self.req_edit.toPlainText().strip()
        if not user_text:
            QMessageBox.information(self, "提示", "请先填写需求描述")
            return
        if self._gen_worker is not None and self._gen_worker.isRunning():
            return
        name, key = self._types[self.type_combo.currentIndex()]
        extra = ""
        if self._content_type_key == "focus":
            extra = "目标国家国策使用 focus_tree = { focus = { ... } } 结构"
        self._gen_worker = _GenWorker(build_messages(name, user_text, extra), self)
        self._gen_worker.done.connect(self._on_generated)
        self._gen_worker.failed.connect(self._on_gen_failed)
        self.gen_btn.setEnabled(False)
        self.gen_btn.setText("⏳ 生成中…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self._gen_worker.start()

    def _on_generated(self, content):
        self.gen_btn.setEnabled(True)
        self.gen_btn.setText("🚀 生成")
        QApplication.restoreOverrideCursor()
        from ai_assist import extract_code_blocks
        blocks = extract_code_blocks(content)
        self._preview_text = "\n\n".join(blocks)
        self.preview_edit.setPlainText(self._preview_text)

    def _on_gen_failed(self, error):
        self.gen_btn.setEnabled(True)
        self.gen_btn.setText("🚀 生成")
        QApplication.restoreOverrideCursor()
        QMessageBox.critical(self, "生成失败", error)

    # ---------- 写入 ----------

    def _write(self):
        from project_wizard import _append_block, _insert_focus_block
        key = self.type_combo.currentData()
        text = self.preview_edit.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "提示", "没有可写入的内容")
            return
        fp = self.file_combo.currentData()
        if not fp:
            QMessageBox.warning(self, "错误", "请选择写入文件")
            return
        reply = QMessageBox.question(
            self, "确认写入",
            f"将以下内容写入:\n{os.path.relpath(fp, self._mod_path)}\n\n"
            f"{text[:200]}…\n\n确定？")
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            if key == "focus":
                _insert_focus_block(fp, "\t" + text.replace("\n", "\n\t").rstrip("\t") + "\n")
            else:
                _append_block(fp, text)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"写入失败: {e}")
            return
        # 刷新主窗口（文件树 + 工作台）
        window = self.window()
        if window is not None:
            try:
                window._refresh_tree()
            except Exception:
                pass
            wb = getattr(window, "workbench_dock", None)
            if wb is not None:
                try:
                    wb._refresh()
                except Exception:
                    pass
            try:
                window.custom_view.redraw()
            except Exception:
                pass
        QMessageBox.information(self, "成功", f"已写入:\n{os.path.relpath(fp, self._mod_path)}")

"""外部接口对话框：在 GUI 内启动/停止 HTTP API 服务

- 端口与 token 管理（随机生成，可复制）
- 启动后所有写操作自动刷新主窗口界面（文件树 / 工作台 / 画布）
- 提供 curl 示例，便于外置 Agent 接入
"""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QLabel,
    QPushButton, QPlainTextEdit, QMessageBox, QApplication)

DEFAULT_PORT = 8765


class ApiDialog(QDialog):
    """外部接口控制对话框（HTTP API + MCP 说明）。"""

    def __init__(self, parent=None, mod_path="", game_path=""):
        super().__init__(parent)
        self.setWindowTitle("外部接口（外置 Agent）")
        self.resize(560, 460)
        self._mod_path = mod_path
        self._game_path = game_path
        self._server = None

        lay = QVBoxLayout(self)

        hint = QLabel(
            "让外置 Agent（AI / 脚本）通过 HTTP API 驱动本软件制作 mod。\n"
            "启动后仅监听 127.0.0.1，请求需携带 Authorization: Bearer <token>。")
        hint.setStyleSheet("color: #5d6b7a;")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        form = QFormLayout()
        self.port_edit = QLineEdit(str(DEFAULT_PORT))
        self.port_edit.setFixedWidth(100)
        form.addRow("端口：", self.port_edit)
        token_row = QHBoxLayout()
        self.token_edit = QLineEdit()
        self.token_edit.setReadOnly(True)
        self.token_edit.setPlaceholderText("（启动时自动生成）")
        token_row.addWidget(self.token_edit)
        regen_btn = QPushButton("重新生成")
        regen_btn.clicked.connect(self._regenerate_token)
        token_row.addWidget(regen_btn)
        form.addRow("Token：", token_row)
        lay.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.toggle_btn = QPushButton("🚀 启动服务")
        self.toggle_btn.clicked.connect(self._toggle)
        btn_row.addWidget(self.toggle_btn)
        lay.addLayout(btn_row)

        self.status_label = QLabel("状态：未启动")
        lay.addWidget(self.status_label)

        lay.addWidget(QLabel("curl 示例："))
        self.curl_edit = QPlainTextEdit()
        self.curl_edit.setReadOnly(True)
        self.curl_edit.setPlaceholderText("启动服务后显示调用示例…")
        self.curl_edit.setFixedHeight(140)
        lay.addWidget(self.curl_edit)

        btn_row2 = QHBoxLayout()
        btn_row2.addStretch()
        copy_btn = QPushButton("📋 复制 curl 示例")
        copy_btn.clicked.connect(self._copy_curl)
        btn_row2.addWidget(copy_btn)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_row2.addWidget(close_btn)
        lay.addLayout(btn_row2)

        self._update_curl()
        self._regenerate_token()

    # ---------- 控制 ----------

    def _regenerate_token(self):
        import secrets
        self.token_edit.setText(secrets.token_hex(16))
        self._update_curl()

    def _toggle(self):
        if self._server is not None and self._server.running:
            self._stop()
        else:
            self._start()

    def _start(self):
        from api_server import ApiServer
        try:
            port = int(self.port_edit.text().strip() or DEFAULT_PORT)
        except ValueError:
            QMessageBox.warning(self, "错误", "端口必须是数字")
            return
        if not self._mod_path or not os.path.isdir(self._mod_path):
            QMessageBox.warning(self, "错误", "请先打开一个 mod 目录")
            return
        self._server = ApiServer(mod_path=self._mod_path, game_path=self._game_path,
                                 port=port, token=self.token_edit.text().strip())
        if not self._server.start():
            QMessageBox.warning(self, "错误", f"端口 {port} 被占用，请更换端口")
            return
        # 写操作后刷新主窗口
        window = self.window()

        def _on_change(_path):
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

        self._server.core.on_change(_on_change)
        self.toggle_btn.setText("⏹ 停止服务")
        self.status_label.setText(
            f"状态：✅ 运行中（{self._server.url()}，token 已启用）")
        self._update_curl()
        QMessageBox.information(
            self, "已启动",
            f"HTTP API 已启动：{self._server.url()}\n"
            f"Token: {self._server.token}\n\n"
            "外置 Agent 调用示例见对话框中的 curl 说明。")

    def _stop(self):
        if self._server is not None:
            self._server.stop()
        self.toggle_btn.setText("🚀 启动服务")
        self.status_label.setText("状态：已停止")
        self._update_curl()

    def _update_curl(self):
        port = self.port_edit.text().strip() or str(DEFAULT_PORT)
        token = self.token_edit.text().strip()
        lines = [
            f"# 1) 查看状态",
            f"curl -H 'Authorization: Bearer {token}' http://127.0.0.1:{port}/api/status",
            f"",
            f"# 2) 列出 GER 国策",
            f"curl -H 'Authorization: Bearer {token}' 'http://127.0.0.1:{port}/api/entities?type=focus&country=GER'",
            f"",
            f"# 3) 项目级联动（国策+事件+决议+图标+本地化）",
            f"curl -X POST -H 'Authorization: Bearer {token}' -H 'Content-Type: application/json' \\",
            f"  -d '{{\"country\":\"GER\",\"focus_id\":\"GER_anchluss\",\"name\":\"德奥合并\"}}' \\",
            f"  http://127.0.0.1:{port}/api/project",
            f"",
            f"# MCP：python mcp_server.py --mod <mod目录>",
        ]
        self.curl_edit.setPlainText("\n".join(lines))

    def _copy_curl(self):
        QApplication.clipboard().setText(self.curl_edit.toPlainText())
        QMessageBox.information(self, "已复制", "curl 示例已复制到剪贴板")

    def closeEvent(self, event):
        self._stop()
        super().closeEvent(event)

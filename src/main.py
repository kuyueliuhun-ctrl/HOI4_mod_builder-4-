"""主入口模块，启动 PyQt6 应用并加载主窗口。"""
import sys
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication
from main_window import MyWindow
import traceback

def excepthook(exc_type, exc_value, exc_tb):
    """全局异常钩子：打印 traceback + 落盘崩溃报告 + 弹窗指明报告位置。

    6.94 内容补全：此前只打印到 stderr（Windows 双击启动时不可见）。
    现在崩溃报告写入 .runtime/crash/crash_<时间戳>.txt（含带 文件:行号
    的完整 traceback），并有 GUI 弹窗告知报告的确切保存位置。
    """
    traceback.print_exception(exc_type, exc_value, exc_tb)
    report = ""
    try:
        from crash_report import write_crash_report
        report = write_crash_report(exc_type, exc_value, exc_tb)
    except Exception:
        pass
    if not report:
        return
    try:
        from PyQt6.QtWidgets import QMessageBox
        from crash_report import format_crash_text
        if QApplication.instance() is None:
            return
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("编辑器崩溃")
        box.setText("发生未捕获异常：%s" % (exc_value,))
        box.setInformativeText(
            "崩溃报告（含出错 文件:行号）已保存到：\n%s\n\n"
            "反馈问题时请一并附上该文件。" % report)
        box.setDetailedText(format_crash_text(exc_type, exc_value, exc_tb))
        box.exec()
    except Exception:
        pass  # 崩溃处理本身不允许再抛异常打断退出流程

if __name__ == "__main__":
    sys.excepthook = excepthook                     # 注册全局异常钩子，便于调试
    app = QApplication(sys.argv)                    # 创建 Qt 应用实例
    app.setFont(QFont("Microsoft YaHei", 10))       # 显式设置字体，避免回退到 DirectWrite 不支持的旧式字体
    try:
        from theme import apply_theme
        apply_theme(app)                            # 应用全局主题（设计令牌 + QSS）
    except Exception:
        pass
    win = MyWindow()                                # 创建主窗口
    win.show()                                      # 显示主窗口
    sys.exit(app.exec())                            # 进入 Qt 事件循环

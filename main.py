"""主入口模块，启动 PyQt6 应用并加载主窗口。"""
import sys
from PyQt6.QtWidgets import QApplication
from main_window import MyWindow
import traceback

def excepthook(exc_type, exc_value, exc_tb):
    """全局异常钩子：将未捕获的异常打印到标准错误输出。"""
    traceback.print_exception(exc_type, exc_value, exc_tb)

if __name__ == "__main__":
    sys.excepthook = excepthook                     # 注册全局异常钩子，便于调试
    app = QApplication(sys.argv)                    # 创建 Qt 应用实例
    win = MyWindow()                                # 创建主窗口
    win.show()                                      # 显示主窗口
    sys.exit(app.exec())                            # 进入 Qt 事件循环

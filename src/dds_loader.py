"""
DDS 图片加载器模块

本模块提供将 DDS（DirectDraw Surface）格式的纹理文件加载为 QPixmap 的功能。
在 Hearts of Iron IV 中，游戏资源和图标广泛使用 DDS 格式，
此加载器使用 Pillow (PIL) 作为中间转换，将 DDS 转为 PNG 字节流后交给 Qt 处理。

主要类：
    DdsLoader -- DDS 文件加载器（静态工具类）

依赖：
    PyQt6.QtGui.QPixmap  -- Qt 像素图
    PIL.Image            -- Python 图像处理库（用于 DDS 解码）
"""

import os
import io
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QByteArray


class DdsLoader:
    """
    DDS 文件加载器（静态工具类）

    提供将各种图片格式（含 DDS）加载为 QPixmap 的统一接口。
    对于 .dds 文件，使用 Pillow 库进行解码并转换为 PNG 格式的字节流，
    再通过 QPixmap.loadFromData 创建像素图。
    对于其他格式（如 .png, .jpg），直接使用 QPixmap 的构造函数加载。

    典型用法:
        pixmap = DdsLoader.load_as_pixmap("path/to/image.dds")
        if pixmap:
            self.label.setPixmap(pixmap)
    """

    @staticmethod
    def load_as_pixmap(file_path: str):
        """
        从文件路径加载图片为 QPixmap 对象

        支持格式：.dds（通过 Pillow 转换）、.png、.jpg 等 Qt 原生支持的格式。

        工作流程：
            1. 检查文件路径是否有效且文件存在
            2. 根据扩展名判断文件类型
            3. 如果是 .dds 文件：
               a. 使用 PIL.Image 打开 DDS 文件
               b. 将图像数据写入内存字节缓冲区（PNG 格式）
               c. 将字节流封装为 QByteArray
               d. 调用 QPixmap.loadFromData 加载为像素图
            4. 如果是其他格式：直接使用 QPixmap(file_path) 加载
            5. 加载失败时静默返回 None

        Args:
            file_path: 图片文件的完整路径（字符串）

        Returns:
            成功返回 QPixmap 对象，失败或文件不存在返回 None

        Note:
            此方法为静态方法，无需实例化 DdsLoader 类即可调用
        """
        # 检查文件路径有效性和文件存在性，不满足则返回 None
        if not file_path or not os.path.isfile(file_path):
            return None
        ext = os.path.splitext(file_path)[1].lower()  # 获取小写扩展名
        if ext == '.dds':
            # DDS 格式：通过 Pillow 转换为 PNG 字节流后交给 Qt 处理
            try:
                from PIL import Image
                img = Image.open(file_path)       # 使用 Pillow 打开 DDS 文件
                buf = io.BytesIO()                 # 创建内存缓冲区
                img.save(buf, format='PNG')        # 将图像保存为 PNG 格式到缓冲区
                data = QByteArray(buf.getvalue())  # 将字节数据封装为 QByteArray
                pixmap = QPixmap()
                if pixmap.loadFromData(data, 'PNG'):  # 从 PNG 字节流加载像素图
                    return pixmap
            except Exception:
                # 转换过程中任何异常都静默处理，返回 None
                return None
        else:
            # 非 DDS 格式：直接使用 Qt 的 QPixmap 构造函数加载
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():  # 判断像素图是否有效（非空）
                return pixmap
        return None

#!/usr/bin/env bash
# HOI4 Mod 编辑器 — WSL/Linux 启动脚本
# 用法：bash 启动.sh   （或 chmod +x 启动.sh 后直接 ./启动.sh）
# 环境：/root/hoi4_builder_venv（Linux venv，Python 3.14 + PyQt6/Pillow/numpy/mcp）
set -e
cd "$(dirname "$0")"

VENV="/root/hoi4_builder_venv"
if [ ! -x "$VENV/bin/python" ]; then
  echo "[错误] 未找到 Linux 虚拟环境: $VENV"
  echo "      请先用 venv 重新创建并安装依赖，例如："
  echo "        python3 -m venv $VENV"
  echo "        $VENV/bin/pip install PyQt6 numpy Pillow mcp"
  exit 1
fi

# 关闭 GUI 时可用 QT_QPA_PLATFORM=offscreen 无头运行：
#   QT_QPA_PLATFORM=offscreen bash 启动.sh
exec "$VENV/bin/python" -X utf8 main.py

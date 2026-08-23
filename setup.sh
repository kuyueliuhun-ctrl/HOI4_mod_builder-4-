#!/usr/bin/env bash
# HOI4 Mod 编辑器 — WSL/Linux 一键环境搭建（Python 3.14）
set -e
cd "$(dirname "$0")"

VENV="${VENV:-/root/hoi4_builder_venv}"
echo "[1/3] 创建虚拟环境: $VENV"
python3 -m venv "$VENV"

echo "[2/3] 安装依赖"
"$VENV/bin/pip" install -r requirements-wsl.txt

echo "[3/3] 运行契约验证"
QT_QPA_PLATFORM=offscreen "$VENV/bin/python" -X utf8 tools/verify_contracts.py

echo
echo "环境搭建完成：可以使用 bash 启动.sh 启动（无头验证加 QT_QPA_PLATFORM=offscreen）。"
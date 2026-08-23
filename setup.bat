@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [1/3] 创建虚拟环境 .venv（Python 3.14）
py -3.14 -m venv .venv || goto :error

echo [2/3] 安装依赖
".venv\Scripts\pip" install -r requirements.txt || goto :error

echo [3/3] 运行契约验证
".venv\Scripts\python.exe" -X utf8 tools\verify_contracts.py || goto :error

echo.
echo 环境搭建完成：可以使用 启动.bat 启动。
exit /b 0

:error
echo.
echo 环境搭建失败，请检查上方错误信息。
exit /b 1
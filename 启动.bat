@echo off
set "VIRTUAL_ENV=%cd%\.venv"
call ".venv\Scripts\activate.bat"
python main.py

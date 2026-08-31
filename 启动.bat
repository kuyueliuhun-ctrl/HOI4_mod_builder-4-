@echo off
rem HOI4 Mod Editor launcher (Windows)
rem This is a thin wrapper. All path/env logic lives in launcher.py.
setlocal
set "ROOT=%~dp0"
pushd "%ROOT%"

where py >nul 2>nul
if errorlevel 1 goto :try_python
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 goto :try_python
py -3 -X utf8 "launcher.py" %*
set "RC=%errorlevel%"
popd
exit /b %RC%

:try_python
where python >nul 2>nul
if errorlevel 1 goto :try_python3
python -X utf8 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 goto :try_python3
python -X utf8 "launcher.py" %*
set "RC=%errorlevel%"
popd
exit /b %RC%

:try_python3
where python3 >nul 2>nul
if errorlevel 1 goto :fail
python3 -X utf8 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 goto :fail
python3 -X utf8 "launcher.py" %*
set "RC=%errorlevel%"
popd
exit /b %RC%

:fail
echo [ERROR] Python 3.10+ not found. Please install Python first.
popd
exit /b 1

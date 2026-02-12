@echo off
setlocal
cd /d %~dp0\..
echo [SAFE_E2E] Ensure log files are files (not dirs)
if exist logs\activity.log\NUL rmdir logs\activity.log
if exist logs\decision.log\NUL rmdir logs\decision.log
if exist logs\error.log\NUL rmdir logs\error.log
if not exist logs mkdir logs
if not exist logs\activity.log type nul > logs\activity.log
if not exist logs\decision.log type nul > logs\decision.log
if not exist logs\error.log type nul > logs\error.log
attrib -R logs\activity.log logs\decision.log logs\error.log >nul 2>&1
echo [SAFE_E2E] Run create_master
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
py -X utf8 scripts\create_master.py
exit /b %errorlevel%

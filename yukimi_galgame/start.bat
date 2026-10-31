@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul && (py server.py & goto end)
where python >nul 2>nul && (python server.py & goto end)
echo 找不到 Python：請先到 https://www.python.org/downloads/ 安裝，安裝時記得勾選 "Add python.exe to PATH"。
:end
pause

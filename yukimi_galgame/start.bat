@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py server.py
  goto done
)
where python >nul 2>nul
if %errorlevel%==0 (
  python server.py
  goto done
)
echo Python not found. Install it from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" during install.
:done
pause

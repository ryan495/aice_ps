@echo off
rem Browser tool for Yukimi (Playwright MCP). Keep this window open while she browses.
where npx >nul 2>nul
if not %errorlevel%==0 (
  echo Node.js not found. Install the LTS version from https://nodejs.org/ and run this again.
  goto done
)
echo Starting browser tool on http://localhost:8931/mcp ...
call npx -y @playwright/mcp@0.0.84 --port 8931 --browser msedge --user-data-dir C:\yukimi-browser --image-responses omit
echo.
echo The browser tool stopped. If there is an error above, take a screenshot.
:done
pause

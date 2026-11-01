@echo off
rem Open Yukimi's browser profile so you can log in by hand (alt accounts only).
echo 1. Close the start_browser.bat window first (the profile can only be used by one browser at a time).
echo 2. Log in to X / Bilibili / Instagram (alt accounts) in the Edge window that opens.
echo 3. Close that Edge window completely, then start start_browser.bat again.
start "" msedge --user-data-dir="C:\yukimi-browser" https://x.com/login https://passport.bilibili.com/login https://www.instagram.com/accounts/login/
pause

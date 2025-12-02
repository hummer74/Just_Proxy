@echo off
cd /d "%~dp0"

:: Stopping SOCKS5 proxy...
call venv\Scripts\activate.bat
python proxy_stop.py

:: Remove proxy shortcuts from Desktop (Optional)
set desktop=%USERPROFILE%\Desktop
if exist "%desktop%\!Proxy_Chrome.lnk" del "%desktop%\!Proxy_Chrome.lnk" /f /q
if exist "%desktop%\!Proxy_Edge.lnk" del "%desktop%\!Proxy_Edge.lnk" /f /q

timeout /t 6 /nobreak
exit
@echo off
cd /d "%~dp0"
:: Stopping SOCKS5 proxy...
echo Stopping SOCKS5 proxy...
call venv\Scripts\activate.bat
python proxy_stop.py

:: Remove proxy shortcuts from Desktop
echo Removing proxy shortcuts from Desktop...
set desktop=%USERPROFILE%\Desktop
del "%desktop%\!Proxy_Chrome.lnk" /f /q
del "%desktop%\!Proxy_Edge.lnk" /f /q

timeout /t 5 /nobreak > nul
exit

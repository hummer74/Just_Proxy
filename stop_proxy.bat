@echo off
cd /d "%~dp0"
:: Stopping SOCKS5 proxy...
echo Stopping SOCKS5 proxy...
call venv\Scripts\activate.bat
python proxy_stop.py
timeout /t 1 /nobreak > nul
exit
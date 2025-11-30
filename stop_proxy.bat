@echo off
cd /d "%~dp0"

echo Stopping SOCKS5 proxy...
call venv\Scripts\activate.bat
python proxy_stop.py
timeout /t 3 /nobreak > nul
call venv\Scripts\deactivate.bat
rem pause
timeout /t 5 /nobreak
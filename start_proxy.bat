@echo off
cd /d "%~dp0"

:: Creating virtual environment...
if not exist "venv\" (
    echo Creating new VENV...
    python -m venv venv
)

:: Activating virtual environment...
call venv\Scripts\activate.bat

:: Installing required packages (Optimized check)
if not exist "venv\Lib\site-packages\pystray" (
    echo Installing required packages...
    python.exe -m pip install --upgrade pip
    pip install pystray Pillow pysocks winshell pywin32 paramiko cryptography
) else (
    echo Packages already installed. Skipping pip...
)

:: Start monitoring tray (Background)
echo Starting tray monitor...
start "" pythonw proxy_tray.pyw
timeout /t 2 /nobreak > nul

:: Start SOCKS5 proxy main script
python proxy_start_v25.py

:: Keep window open briefly to see status
timeout /t 5 /nobreak
exit
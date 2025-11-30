@echo off
cd /d "%~dp0"

echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing required packages...
python.exe -m pip install --upgrade pip
pip install paramiko cryptography

echo Starting proxy...
python proxy_start.py
timeout /t 3 /nobreak > nul
call venv\Scripts\deactivate.bat
rem pause
timeout /t 10 /nobreak

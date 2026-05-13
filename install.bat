@echo off
chcp 65001 >nul
echo ========================================
echo   Video to Documents - Installer
echo ========================================
echo.

REM Check Python
where python >nul 2>nul
if errorlevel 1 (
    echo [X] Khong tim thay Python.
    echo     Tai Python tai: https://www.python.org/downloads/
    echo     Nho tick "Add Python to PATH" khi cai dat.
    pause
    exit /b 1
)

echo [1/3] Tao moi truong ao Python (venv)...
python -m venv .venv
if errorlevel 1 (
    echo [X] Khong tao duoc venv. Thu chay: python -m pip install --upgrade pip virtualenv
    pause
    exit /b 1
)

echo [2/3] Kich hoat venv va cai dat goi...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [X] Loi khi cai dat goi.
    pause
    exit /b 1
)

echo [3/3] Tao file .env mau...
if not exist .env (
    copy .env.example .env >nul
    echo     File .env da duoc tao. Mo bang notepad de nhap API key.
)

echo.
echo ========================================
echo   CAI DAT XONG!
echo ========================================
echo.
echo Buoc tiep theo:
echo   1. Mo file .env va nhap GOOGLE_API_KEY
echo      (Lay key tai: https://aistudio.google.com/app/apikey)
echo   2. Kich hoat venv: .venv\Scripts\activate
echo   3. Chay: python main.py duong_dan_video.mp4
echo.
pause

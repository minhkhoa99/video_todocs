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
    echo     Tai Python 3.8+ tai: https://www.python.org/downloads/
    echo     Nho tick "Add Python to PATH" khi cai dat.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo Phien ban Python: %PYVER%

REM Check >= 3.7 (toi thieu)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)" >nul 2>nul
if errorlevel 1 (
    echo [X] Yeu cau Python 3.7 tro len. Hien tai: %PYVER%
    pause
    exit /b 1
)

REM Warn if Python < 3.9 (vi 3.8 da EOL)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
if errorlevel 1 (
    echo.
    echo [!] CANH BAO: Python 3.8 da het ho tro chinh thuc (EOL 10/2024).
    echo     Khuyen khich nang cap len Python 3.11+ de an toan va nhanh hon.
    echo     Tuy nhien code se van chay duoc tren 3.8.
    echo.
)

echo [1/4] Tao moi truong ao Python (venv)...
if exist .venv (
    echo     Da co .venv, bo qua tao moi.
) else (
    python -m venv .venv
    if errorlevel 1 (
        echo [X] Khong tao duoc venv.
        pause
        exit /b 1
    )
)

echo [2/4] Nang cap pip...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo [!] Khong nang cap duoc pip nhung van thu tiep tuc...
)

echo [3/4] Cai dat cac goi phu thuoc...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [X] Loi khi cai dat goi. Thu chay lai voi quyen Admin hoac kiem tra ket noi mang.
    pause
    exit /b 1
)

echo [4/4] Tao file .env mau...
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
echo   1. Mo file .env va nhap GOOGLE_API_KEY (neu chua co)
echo      Lay key tai: https://aistudio.google.com/app/apikey
echo   2. Chay: run.bat duong_dan_video.mp4
echo      Hoac: .venv\Scripts\activate ^&^& python main.py video.mp4
echo.
pause

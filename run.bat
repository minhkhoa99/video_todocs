@echo off
chcp 65001 >nul
if "%~1"=="" (
    echo Cach dung: run.bat duong_dan_video.mp4 [tham_so_them]
    echo Vi du:    run.bat C:\Videos\bai1.mp4
    echo            run.bat C:\Videos\bai1.mp4 --mode exercise --formats docx,pdf
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
python main.py %*
pause

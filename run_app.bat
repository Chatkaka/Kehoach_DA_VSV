@echo off
title Khoi Chay He Thong Quan Ly Ven Song Vinh
color 0a

echo =====================================================================
echo    HE THONG QUAN LY TIEN DO & NGAN SACH DU AN VEN SONG VINH
echo                 TU DONG KHOI CHAY TOAN BO UNG DUNG
echo =====================================================================
echo.

:: 1. Kiem tra Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Python chua duoc cai dat hoac chua duoc them vao PATH!
    echo Vui long cai dat Python va thu lai.
    pause
    exit /b
)

:: 2. Khoi chay FastAPI Backend (Port 8000) trong cua so moi
echo [1/3] Dang khoi chay FastAPI Backend tai cong 8000...
start "FastAPI Backend (Cong 8000)" cmd /k "python -m uvicorn main:app --port 8000"

:: Cho 3 giay de Backend on dinh
timeout /t 3 /nobreak >nul

:: 3. Khoi chay Streamlit Frontend (Port 8501) trong cua so moi
echo [2/3] Dang khoi chay Streamlit App tai cong 8501...
start "Streamlit Frontend (Cong 8501)" cmd /k "python -m streamlit run app.py --server.port 8501"

:: Cho 2 giay
timeout /t 2 /nobreak >nul

:: 4. Tu dong mo trinh duyet
echo [3/3] Dang mo trinh duyet Web Dashboard va Streamlit App...
start http://127.0.0.1:8000
start http://localhost:8501

echo.
echo =====================================================================
echo KHOI CHAY HOAN TAT!
echo  - Giao dien Web Dashboard dang chay tai: http://127.0.0.1:8000
echo  - Giao dien Streamlit dang chay tai: http://localhost:8501
echo.
echo Giu nguyen hai cua so terminal (cmd) vua mo ra de duy tri App.
echo De tat ung dung, ban chi can dong cac cua so terminal do.
echo =====================================================================
echo.
pause

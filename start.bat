@echo off
chcp 65001 >nul
echo ========================================================
echo          KHOI DONG HE THONG CROWDSIGHT
echo ========================================================
echo.
echo [1/2] Dang khoi dong Backend FastAPI (Port 8001)...
start "CrowdSight Backend (FastAPI)" cmd /k "cd /d %~dp0 && .venv\Scripts\python.exe -m uvicorn crowdsight.service.api.app:app --reload --host 127.0.0.1 --port 8001"

echo [2/2] Dang khoi dong Frontend Vite (Port 3000)...
start "CrowdSight Frontend (Vite)" cmd /k "cd /d %~dp0\web && pnpm run dev"

echo.
echo ========================================================
echo  Ca hai server dang duoc mo trong 2 cua so rieng biet:
echo  - Giao dien Web:   http://localhost:3000
echo  - Backend API:     http://127.0.0.1:8001
echo  - Swagger API Doc: http://127.0.0.1:8001/docs
echo ========================================================
echo Nhan phim bat ky de dong cua so thong bao nay (2 server van tiep tuc chay).
pause >nul

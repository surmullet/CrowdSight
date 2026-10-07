@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" scripts/test_db_connection.py %*
) else (
    python scripts/test_db_connection.py %*
)
pause

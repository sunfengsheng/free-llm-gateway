@echo off
chcp 65001 > nul
title Free LLM Gateway
echo.
echo  Free LLM Gateway
echo  ================
echo  Starting server...
echo.

:: Open browser after 3s in background
start "" cmd /c "timeout /t 3 /nobreak > nul && start http://localhost:8000"

:: Run server in foreground (Ctrl+C to stop)
python main.py

echo.
echo  Server stopped.
pause

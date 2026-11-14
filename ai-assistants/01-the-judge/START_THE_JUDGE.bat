@echo off
setlocal
title The Judge - Demo Launcher

cd /d "%~dp0"

set "PYTHON=%~dp0.venv\Scripts\python.exe"
set "STREAMLIT=%~dp0.venv\Scripts\streamlit.exe"
set "API_URL=http://127.0.0.1:8000/health"
set "APP_URL=http://localhost:8501"

echo.
echo ============================================================
echo                 THE JUDGE - DEMO LAUNCHER
echo ============================================================
echo.

if not exist "%PYTHON%" (
    echo [ERROR] Python virtual environment not found.
    echo Expected: %PYTHON%
    echo.
    pause
    exit /b 1
)

echo [1/3] Checking Mock Production API...

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri '%API_URL%' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"

if errorlevel 1 (
    echo [INFO] API is not running. Starting FastAPI...
    start "The Judge - FastAPI" /min "%PYTHON%" -m uvicorn mock_config_api:app --host 127.0.0.1 --port 8000

    echo [2/3] Waiting for configuration API...

    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; for($i=0;$i -lt 30;$i++){ try { Invoke-WebRequest -Uri '%API_URL%' -UseBasicParsing -TimeoutSec 1 | Out-Null; $ok=$true; break } catch { Start-Sleep -Milliseconds 500 } }; if(-not $ok){ exit 1 }"

    if errorlevel 1 (
        echo [ERROR] FastAPI did not start on port 8000.
        echo.
        pause
        exit /b 1
    )
) else (
    echo [OK] Configuration API is already running.
)

echo [3/3] Starting The Judge dashboard...

if exist "%STREAMLIT%" (
    start "The Judge - Streamlit" /min "%STREAMLIT%" run "%~dp0judge_app.py" --server.headless true --browser.gatherUsageStats false
) else (
    start "The Judge - Streamlit" /min "%PYTHON%" -m streamlit run "%~dp0judge_app.py" --server.headless true --browser.gatherUsageStats false
)

echo.
echo Waiting for The Judge dashboard...

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; for($i=0;$i -lt 40;$i++){ try { Invoke-WebRequest -Uri '%APP_URL%' -UseBasicParsing -TimeoutSec 1 | Out-Null; $ok=$true; break } catch { Start-Sleep -Milliseconds 500 } }; if(-not $ok){ exit 1 }"

if errorlevel 1 (
    echo [ERROR] Streamlit did not start on port 8501.
    echo.
    pause
    exit /b 1
)

start "" "%APP_URL%"

echo.
echo ============================================================
echo                 THE JUDGE IS READY
echo ============================================================
echo.
echo Dashboard: %APP_URL%
echo.
echo You can close this launcher window.
echo The Judge services are running in the background.
echo ============================================================
echo.

timeout /t 3 /nobreak >nul
exit /b 0

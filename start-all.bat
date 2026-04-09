@echo off
setlocal enabledelayedexpansion
title AI Caption Lab - Launcher
color 0E

echo.
echo ========================================
echo      AI Caption Lab - Launcher
echo ========================================
echo.

REM Check if Ollama is running via tasklist first
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe" >NUL
if %errorlevel% neq 0 (
    echo [WARN] Ollama process not detected.
    where ollama >nul 2>&1
    if !errorlevel! equ 0 (
        echo [START] Attempting to start Ollama...
        start "" ollama serve
        echo Waiting for Ollama to initialize for 10 seconds...
        timeout /t 10 /nobreak >nul
    ) else (
        echo [ERROR] 'ollama' command not found in PATH. 
        echo Please ensure Ollama is installed.
    )
) else (
    echo [OK] Ollama process is already running.
)

REM Verify API is responsive
echo [INFO] Checking Ollama API...
curl -s -m 5 http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Ollama API is responsive!
    echo.
    echo [INFO] Installed Models:
    ollama list
) else (
    echo [WARN] Ollama API not responding on localhost:11434.
    echo Proceeding anyway, but image analysis may fail.
)

echo.
echo ========================================
echo [START] Starting Backend and Frontend...
echo ========================================
echo.

REM Start Backend
echo [INFO] Starting Backend Server...
start "Backend" cmd /k "cd Backend && call ..\.venv\Scripts\activate && python app.py"

REM Wait for backend
timeout /t 3 /nobreak >nul

REM Start Frontend
echo [INFO] Starting Frontend Server...
start "Frontend" cmd /k "cd Frontend && npm start"

echo.
echo ========================================
echo [OK] All systems starting!
echo ========================================
echo.
echo Backend:  http://localhost:8001
echo Frontend: http://localhost:3000
echo.
echo Press any key to close this launcher...
pause >nul

@echo off
echo Stopping all Neuro-Transfer services...

REM Kill Python processes (Backend)
taskkill /f /im python.exe 2>nul
if %errorlevel% equ 0 (
    echo ✓ Stopped Python backend
) else (
    echo No Python processes found
)

REM Kill Node processes (Frontend)  
taskkill /f /im node.exe 2>nul
if %errorlevel% equ 0 (
    echo ✓ Stopped Node.js frontend
) else (
    echo No Node.js processes found
)

REM Kill any other related processes
taskkill /f /im ollama.exe 2>nul
taskkill /f /im ollama_app.exe 2>nul

REM Kill any remaining command windows
taskkill /f /im cmd.exe 2>nul
taskkill /f /im powershell.exe 2>nul

echo.
echo All services stopped successfully!
echo.
pause
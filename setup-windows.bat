@echo off
setlocal enabledelayedexpansion
title AI Caption Lab - Smart Setup
color 0A

echo.
echo ============================================================
echo        AI Caption Lab - Smart Auto Setup
echo        Built by Mohd Inamul Hassan
echo        GitHub: github.com/Inamulhassan-dev
echo ============================================================
echo.
echo  This setup will:
echo  [1] Check your system specs (GPU, RAM, CPU)
echo  [2] Install Python dependencies
echo  [3] Install Node.js dependencies
echo  [4] Check and install Ollama
echo  [5] Pull the best AI models for YOUR system
echo  [6] Build the frontend
echo  [7] Launch the app
echo.
echo ============================================================
pause

:: ============================================================
:: STEP 1 - CHECK SYSTEM SPECS
:: ============================================================
echo.
echo [STEP 1/7] Checking your system specs...
echo ============================================================

:: Check RAM
for /f "tokens=2 delims==" %%a in ('wmic computersystem get TotalPhysicalMemory /value') do set RAM_BYTES=%%a
set /a RAM_GB=!RAM_BYTES:~0,-9!
if !RAM_GB! LSS 1 set RAM_GB=1
echo  RAM: !RAM_GB! GB detected

:: Check CPU
for /f "tokens=2 delims==" %%a in ('wmic cpu get Name /value') do set CPU_NAME=%%a
echo  CPU: !CPU_NAME!

:: Check GPU
set GPU_NAME=None
set HAS_NVIDIA=0
set HAS_AMD=0

nvidia-smi >nul 2>&1
if !errorlevel! equ 0 (
    set HAS_NVIDIA=1
    for /f "tokens=1 delims=," %%a in ('nvidia-smi --query-gpu=name --format=csv^,noheader 2^>nul') do set GPU_NAME=%%a
    echo  GPU: !GPU_NAME! [NVIDIA - DETECTED]
) else (
    :: Check AMD
    wmic path win32_VideoController get name 2>nul | findstr /i "AMD Radeon RX" >nul
    if !errorlevel! equ 0 (
        set HAS_AMD=1
        for /f "tokens=2 delims==" %%a in ('wmic path win32_VideoController get name /value 2^>nul ^| findstr /i "AMD"') do set GPU_NAME=%%a
        echo  GPU: !GPU_NAME! [AMD - DETECTED]
    ) else (
        echo  GPU: No dedicated GPU detected [CPU MODE]
    )
)

:: Decide model profile based on specs
set MODEL_PROFILE=minimal
set VISION_MODEL=moondream:latest
set TEXT_MODEL=moondream:latest

if !RAM_GB! GEQ 32 (
    if !HAS_NVIDIA! equ 1 (
        set MODEL_PROFILE=quality
        set VISION_MODEL=llava:latest
        set TEXT_MODEL=llama3.2:3b
        echo  Profile: QUALITY MODE [32GB+ RAM + NVIDIA GPU]
    ) else (
        set MODEL_PROFILE=balanced
        set VISION_MODEL=moondream:latest
        set TEXT_MODEL=llama3.2:3b
        echo  Profile: BALANCED MODE [32GB+ RAM]
    )
) else if !RAM_GB! GEQ 16 (
    if !HAS_NVIDIA! equ 1 (
        set MODEL_PROFILE=balanced
        set VISION_MODEL=moondream:latest
        set TEXT_MODEL=llama3.2:3b
        echo  Profile: BALANCED MODE [16GB RAM + NVIDIA GPU]
    ) else (
        set MODEL_PROFILE=fast
        set VISION_MODEL=moondream:latest
        set TEXT_MODEL=moondream:latest
        echo  Profile: FAST MODE [16GB RAM, No GPU]
    )
) else (
    set MODEL_PROFILE=minimal
    set VISION_MODEL=moondream:latest
    set TEXT_MODEL=moondream:latest
    echo  Profile: MINIMAL MODE [Less than 16GB RAM]
)

echo.
echo  Selected Models:
echo    Vision: !VISION_MODEL!
echo    Text:   !TEXT_MODEL!
echo    Mode:   !MODEL_PROFILE!
echo.
timeout /t 3 /nobreak >nul

:: ============================================================
:: STEP 2 - CHECK PYTHON
:: ============================================================
echo [STEP 2/7] Checking Python...
echo ============================================================

python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo  [ERROR] Python not found!
    echo.
    echo  Please install Python 3.10+ from:
    echo  https://www.python.org/downloads/
    echo.
    echo  Make sure to check "Add Python to PATH" during install!
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo  [OK] Python !PY_VER! found

:: Create virtual environment
if not exist ".venv" (
    echo  Creating virtual environment...
    python -m venv .venv
    echo  [OK] Virtual environment created
) else (
    echo  [OK] Virtual environment already exists
)

:: Activate and install packages
echo  Installing Python packages...
call .venv\Scripts\activate
pip install -r Backend\requirements.txt --quiet --disable-pip-version-check
if !errorlevel! neq 0 (
    echo  [ERROR] Failed to install Python packages!
    echo  Try running: pip install -r Backend\requirements.txt
    pause
    exit /b 1
)
echo  [OK] Python packages installed
echo.

:: ============================================================
:: STEP 3 - CHECK NODE.JS
:: ============================================================
echo [STEP 3/7] Checking Node.js...
echo ============================================================

node --version >nul 2>&1
if !errorlevel! neq 0 (
    echo  [ERROR] Node.js not found!
    echo.
    echo  Please install Node.js from:
    echo  https://nodejs.org/
    echo  (Download the LTS version)
    pause
    exit /b 1
)

for /f %%v in ('node --version') do set NODE_VER=%%v
echo  [OK] Node.js !NODE_VER! found

:: Install frontend packages
if not exist "Frontend\node_modules" (
    echo  Installing frontend packages (this may take a few minutes)...
    cd Frontend
    npm install --silent
    cd ..
    echo  [OK] Frontend packages installed
) else (
    echo  [OK] Frontend packages already installed
)
echo.

:: ============================================================
:: STEP 4 - CHECK OLLAMA
:: ============================================================
echo [STEP 4/7] Checking Ollama...
echo ============================================================

ollama --version >nul 2>&1
if !errorlevel! neq 0 (
    echo  [WARN] Ollama not found!
    echo.
    echo  Downloading Ollama installer...
    echo  Please install from: https://ollama.ai/download
    echo.
    echo  Opening download page...
    start https://ollama.ai/download
    echo.
    echo  After installing Ollama, run this setup again.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('ollama --version 2^>^&1') do set OLLAMA_VER=%%v
echo  [OK] Ollama found

:: Start Ollama if not running
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if !errorlevel! neq 0 (
    echo  Starting Ollama service...
    start "" /min ollama serve
    echo  Waiting for Ollama to start...
    timeout /t 8 /nobreak >nul
) else (
    echo  [OK] Ollama already running
)

:: Verify Ollama API
curl -s -m 5 http://localhost:11434/api/tags >nul 2>&1
if !errorlevel! neq 0 (
    echo  [WARN] Ollama API not responding, waiting more...
    timeout /t 10 /nobreak >nul
)
echo.

:: ============================================================
:: STEP 5 - PULL AI MODELS
:: ============================================================
echo [STEP 5/7] Setting up AI Models...
echo ============================================================
echo  This may take a while depending on your internet speed.
echo  Models are downloaded once and reused forever.
echo.

:: Check and pull vision model
echo  Checking vision model: !VISION_MODEL!
ollama list 2>nul | findstr /i "!VISION_MODEL!" >nul
if !errorlevel! neq 0 (
    echo  Pulling !VISION_MODEL! (Vision AI)...
    echo  Please wait, this is a one-time download...
    ollama pull !VISION_MODEL!
    if !errorlevel! equ 0 (
        echo  [OK] !VISION_MODEL! downloaded successfully
    ) else (
        echo  [WARN] Failed to pull !VISION_MODEL!, trying moondream...
        ollama pull moondream:latest
    )
) else (
    echo  [OK] !VISION_MODEL! already installed
)

:: Check and pull text model (only if different from vision)
if not "!TEXT_MODEL!"=="!VISION_MODEL!" (
    echo  Checking text model: !TEXT_MODEL!
    ollama list 2>nul | findstr /i "!TEXT_MODEL!" >nul
    if !errorlevel! neq 0 (
        echo  Pulling !TEXT_MODEL! (Text AI)...
        echo  Please wait, this is a one-time download...
        ollama pull !TEXT_MODEL!
        if !errorlevel! equ 0 (
            echo  [OK] !TEXT_MODEL! downloaded successfully
        ) else (
            echo  [WARN] Failed to pull !TEXT_MODEL!, will use vision model for text
        )
    ) else (
        echo  [OK] !TEXT_MODEL! already installed
    )
)

echo.
echo  Installed models:
ollama list
echo.

:: ============================================================
:: STEP 6 - CREATE ENV FILE
:: ============================================================
echo [STEP 6/7] Creating configuration...
echo ============================================================

if not exist "Backend\.env" (
    echo  Creating Backend\.env config file...
    (
        echo OLLAMA_HOST=http://localhost:11434
        echo VISION_MODEL=!VISION_MODEL!
        echo TEXT_MODEL=!TEXT_MODEL!
        echo FAST_LOCAL=0
        echo AUTO_TUNE=0
    ) > Backend\.env
    echo  [OK] Config file created
) else (
    echo  [OK] Config file already exists
)

:: ============================================================
:: STEP 7 - BUILD FRONTEND
:: ============================================================
echo.
echo [STEP 7/7] Building Frontend...
echo ============================================================
echo  Building optimized production files...

cd Frontend
npm run build --silent
if !errorlevel! neq 0 (
    echo  [ERROR] Frontend build failed!
    cd ..
    pause
    exit /b 1
)
cd ..
echo  [OK] Frontend built successfully
echo.

:: ============================================================
:: ALL DONE - LAUNCH!
:: ============================================================
echo.
echo ============================================================
echo  SETUP COMPLETE!
echo ============================================================
echo.
echo  System Profile: !MODEL_PROFILE!
echo  Vision Model:   !VISION_MODEL!
echo  Text Model:     !TEXT_MODEL!
echo  RAM:            !RAM_GB! GB
echo  GPU:            !GPU_NAME!
echo.
echo ============================================================
echo  Launching AI Caption Lab...
echo ============================================================
echo.

:: Start Backend
echo  Starting Backend...
start "AI Caption Lab - Backend" cmd /k "call .venv\Scripts\activate && cd Backend && python app.py"
timeout /t 4 /nobreak >nul

:: Start Frontend
echo  Starting Frontend...
start "AI Caption Lab - Frontend" cmd /k "cd Frontend && node serve-build.js"
timeout /t 3 /nobreak >nul

:: Open browser
echo  Opening browser...
timeout /t 2 /nobreak >nul
start http://localhost:3000

echo.
echo ============================================================
echo  AI Caption Lab is now running!
echo.
echo  Frontend:  http://localhost:3000
echo  Backend:   http://localhost:8001
echo  API Docs:  http://localhost:8001/docs
echo.
echo  Built by: Mohd Inamul Hassan
echo  GitHub:   github.com/Inamulhassan-dev
echo  Email:    inamulhassan20006@gmail.com
echo ============================================================
echo.
echo  To stop all services, run: stop-services.bat
echo  To start again later, run: start-all.bat
echo.
pause

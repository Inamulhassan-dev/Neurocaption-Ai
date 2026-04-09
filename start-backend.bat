@echo off
title AI Caption Lab - Backend Server
color 0A
echo.
echo ========================================
echo   AI Caption Lab - Backend Server
echo ========================================
echo.
echo Starting FastAPI backend...
echo.

cd Backend
if "%MODEL_PROFILE%"=="" set MODEL_PROFILE=fast
if /I "%MODEL_PROFILE%"=="quality" (
  set VISION_MODEL=moondream:latest
  set TEXT_MODEL=moondream:latest
  set VISION_NUM_PREDICT=24
  set VISION_MAX_SIZE=192
  set TEXT_NUM_PREDICT=32
  set VISION_USE_CHAT=0
  set VISION_JPEG_QUALITY=75
) else (
  set VISION_MODEL=moondream:latest
  set TEXT_MODEL=moondream:latest
  set VISION_NUM_PREDICT=16
  set VISION_MAX_SIZE=160
  set TEXT_NUM_PREDICT=20
  set VISION_USE_CHAT=0
  set VISION_JPEG_QUALITY=70
)
call ..\.venv\Scripts\activate
python app.py

pause

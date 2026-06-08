@echo off
REM Kazumi Startup Script for Windows

echo 🚀 Starting Kazumi...

REM Check if virtual environment exists
if not exist ".venv" (
    echo ❌ Virtual environment not found. Run: python -m venv .venv
    pause
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Start FastAPI backend
echo 📡 Starting FastAPI backend on port 8000...
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

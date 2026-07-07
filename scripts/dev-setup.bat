@echo off
REM ============================================
REM Edge AI CCTV Analytics — Windows Dev Setup
REM ============================================

echo ============================================
echo   Edge AI CCTV Analytics - Dev Setup
echo ============================================
echo.

REM Check Python
echo [1/6] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11 or 3.12 from https://python.org
    pause
    exit /b 1
)
python --version

REM Check Node.js
echo.
echo [2/6] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Node.js not found. Frontend will not work.
    echo Install from https://nodejs.org
) else (
    node --version
)

REM Create backend venv
echo.
echo [3/6] Creating Python virtual environment...
cd backend
if not exist venv (
    python -m venv venv
    echo Created venv
) else (
    echo venv already exists
)

REM Install backend dependencies
echo.
echo [4/6] Installing Python dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel >nul 2>&1
pip install -r requirements\base.txt -r requirements\inference.txt
if errorlevel 1 (
    echo WARNING: Some packages failed to install. Check Python version compatibility.
)

REM Copy .env
if not exist .env (
    copy .env.example .env >nul
    echo Created .env from template
)
cd ..

REM Install frontend dependencies
echo.
echo [5/6] Installing frontend dependencies...
cd frontend
if exist package.json (
    call npm install
) else (
    echo WARNING: frontend/package.json not found. Skipping.
)
cd ..

REM Create data directory
echo.
echo [6/6] Creating data directories...
if not exist data mkdir data
if not exist models\registry\detection mkdir models\registry\detection

echo.
echo ============================================
echo   Setup Complete!
echo ============================================
echo.
echo Next steps:
echo   1. Download models:    python scripts\model_downloader.py
echo   2. Generate test video: python scripts\camera_simulator.py
echo   3. Start backend:      cd backend ^& venv\Scripts\activate ^& uvicorn app.main:app --reload
echo   4. Start frontend:     cd frontend ^& npm run dev
echo.
pause

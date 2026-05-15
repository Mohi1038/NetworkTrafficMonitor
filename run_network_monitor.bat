@echo off
REM Network Traffic Monitor Launcher for Windows
REM This script starts both the backend server and frontend application

setlocal enabledelayedexpansion

echo.
echo ================================
echo Network Traffic Monitor Launcher
echo ================================
echo.

SET PROJECT_ROOT=%~dp0
SET BACKEND_PATH=%PROJECT_ROOT%backend
SET FRONTEND_PATH=%PROJECT_ROOT%frontend

REM Load environment variables from .env if it exists
if exist "%PROJECT_ROOT%.env" (
    echo [INFO] Loading environment variables from .env
    for /f "tokens=*" %%i in ('type "%PROJECT_ROOT%.env" ^| findstr /v "^REM" ^| findstr /v "^$"') do set %%i
)

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

echo [INFO] Python version:
python --version
echo.

REM Check if Node.js is installed
node --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not installed. Please install Node.js 14 or higher.
    pause
    exit /b 1
)

echo [INFO] Node.js version:
node --version
echo [INFO] npm version:
npm --version
echo.

REM Install Python dependencies
echo [INFO] Checking Python dependencies...
cd /d "%BACKEND_PATH%"

if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

echo [INFO] Installing Python dependencies...
pip install -q -r requirements.txt

REM Install Node dependencies
echo [INFO] Installing Node dependencies...
cd /d "%FRONTEND_PATH%"

if not exist "node_modules" (
    echo [INFO] Installing npm packages...
    call npm install
)

echo.
echo [INFO] All dependencies installed successfully!
echo.

REM Start the backend server with administrator privileges
echo [INFO] Starting backend server with administrator privileges...
cd /d "%BACKEND_PATH%"

powershell -Command "Start-Process cmd -ArgumentList '/k python app2.py' -Verb RunAs -WindowStyle Normal" -NoExit

echo [INFO] Waiting for backend to initialize (10 seconds)...
timeout /t 10 /nobreak

echo [INFO] Starting frontend application...
cd /d "%FRONTEND_PATH%"
start cmd /k "npm start"

echo.
echo [INFO] Startup complete! Check the opened windows for application status.
echo [INFO] Press Ctrl+C in the windows to stop the applications.
echo.

@echo off
REM Quick start script for Django backend on Windows
REM This script helps you start the backend server with proper configuration

echo ========================================
echo  Django Backend Server - Quick Start
echo ========================================
echo.

REM Check if .env exists
if not exist .env (
    echo [WARNING] .env file not found!
    echo.
    echo Please create .env file with your database password.
    echo You can run: powershell -ExecutionPolicy Bypass -File setup_env.ps1
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] Virtual environment not found!
    echo Please create it first: python -m venv venv
    pause
    exit /b 1
)

echo.
echo Starting Django development server...
echo Server will be accessible at:
echo   - http://localhost:8000 (from your computer)
echo   - http://10.0.2.2:8000 (from Android emulator)
echo.
echo Press CTRL+C to stop the server
echo.

REM Start the server on 0.0.0.0:8000 so emulator can access it
python manage.py runserver 0.0.0.0:8000

pause


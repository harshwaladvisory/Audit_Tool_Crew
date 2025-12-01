@echo off
REM Accufund Formatter - Windows Startup Script
REM This script starts the Flask web application

echo.
echo ========================================
echo   Accufund Formatter Web Application
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or higher
    pause
    exit /b 1
)

echo [1/3] Checking Python installation...
python --version

echo.
echo [2/3] Checking MongoDB connection...
python -c "from pymongo import MongoClient; client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=2000); client.admin.command('ping'); print('MongoDB is running!')" 2>nul
if errorlevel 1 (
    echo.
    echo WARNING: Cannot connect to MongoDB
    echo Please make sure MongoDB is installed and running
    echo.
    echo To start MongoDB:
    echo   net start MongoDB
    echo.
    pause
    exit /b 1
)

echo.
echo [3/3] Starting Flask application...
echo.
echo ========================================
echo   Application will start on:
echo   http://localhost:5000
echo.
echo   Press Ctrl+C to stop the server
echo ========================================
echo.

python app.py

pause
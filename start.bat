@echo off
echo ====================================================================
echo Streaming Service - Quick Start
echo ====================================================================
echo.

REM Check if PostgreSQL is running
echo [1/4] Checking if PostgreSQL is running...
docker ps | findstr "jobtrak-postgres" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PostgreSQL container 'jobtrak-postgres' is not running!
    echo.
    echo Please start your JobTrak services first:
    echo   cd path\to\JobTrak
    echo   docker-compose up -d postgres
    echo.
    pause
    exit /b 1
)
echo [OK] PostgreSQL is running
echo.

REM Check Python
echo [2/4] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)
echo [OK] Python found
echo.

REM Setup database (if needed)
echo [3/4] Setting up database...
python setup_database_in_existing_pg.py
if %errorlevel% neq 0 (
    echo [ERROR] Database setup failed
    pause
    exit /b 1
)
echo.

REM Start the application
echo [4/4] Starting Flask backend...
echo.
echo ====================================================================
echo Backend is starting on http://localhost:5000
echo Press Ctrl+C to stop
echo ====================================================================
echo.

python app.py

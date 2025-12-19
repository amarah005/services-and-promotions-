@echo off
REM Database Setup Script for BuyVaultHub (Windows)
REM This script sets up the PostgreSQL database using the SQL backup file

setlocal enabledelayedexpansion

echo =========================================
echo BuyVaultHub Database Setup
echo =========================================
echo.

set DB_NAME=buyvaulthub_db
set DB_USER=postgres
set DB_HOST=localhost
set DB_PORT=5432
set SQL_FILE=backup_20251029_020655.sql

REM Check if SQL file exists
if not exist "%SQL_FILE%" (
    echo Error: SQL file '%SQL_FILE%' not found!
    echo Please make sure the SQL backup file is in the project root directory.
    pause
    exit /b 1
)

echo [OK] Found SQL file: %SQL_FILE%
echo.

REM Prompt for database password
set /p DB_PASSWORD="Enter PostgreSQL password for user '%DB_USER%': "
echo.

REM Check if PostgreSQL is running
echo Checking PostgreSQL connection...
set PGPASSWORD=%DB_PASSWORD%
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -c "\q" >nul 2>&1
if errorlevel 1 (
    echo Error: Cannot connect to PostgreSQL!
    echo Please make sure:
    echo   1. PostgreSQL is installed and running
    echo   2. The password is correct
    echo   3. PostgreSQL is accessible on %DB_HOST%:%DB_PORT%
    pause
    exit /b 1
)

echo [OK] PostgreSQL connection successful
echo.

REM Check if database exists
echo Checking if database '%DB_NAME%' exists...
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -lqt | findstr /C:"%DB_NAME%" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Database '%DB_NAME%' already exists
    set /p RECREATE="Do you want to drop and recreate it? (y/N): "
    if /i "!RECREATE!"=="y" (
        echo Dropping existing database...
        psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -c "DROP DATABASE IF EXISTS %DB_NAME%;" >nul 2>&1
        echo [OK] Database dropped
    ) else (
        echo Skipping database creation. Using existing database.
        set SKIP_CREATE=true
    )
)

REM Create database if it doesn't exist
if not defined SKIP_CREATE (
    echo Creating database '%DB_NAME%'...
    psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -c "CREATE DATABASE %DB_NAME%;" >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] Database might already exist, continuing...
    ) else (
        echo [OK] Database created
    )
)

echo.

REM Import SQL file
echo Importing SQL backup file...
echo This may take a few minutes...
set PGPASSWORD=%DB_PASSWORD%
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f %SQL_FILE%

if errorlevel 1 (
    echo [ERROR] Error importing SQL file
    pause
    exit /b 1
) else (
    echo [OK] SQL file imported successfully
)

echo.

REM Verify import
echo Verifying database import...
for /f "tokens=*" %%i in ('psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"') do set TABLE_COUNT=%%i
set TABLE_COUNT=!TABLE_COUNT: =!

if !TABLE_COUNT! GTR 0 (
    echo [OK] Database verification successful
    echo    Found !TABLE_COUNT! tables in the database
) else (
    echo [WARNING] No tables found. Database might be empty.
)

echo.
echo =========================================
echo Database setup completed!
echo =========================================
echo.
echo Next steps:
echo 1. Update backend\.env with database credentials:
echo    DATABASE_NAME=%DB_NAME%
echo    DATABASE_USER=%DB_USER%
echo    DATABASE_PASSWORD=^<your_password^>
echo    DATABASE_HOST=%DB_HOST%
echo    DATABASE_PORT=%DB_PORT%
echo.
echo 2. Run backend migrations (if needed):
echo    cd backend
echo    python manage.py migrate
echo.
echo 3. Start the backend server:
echo    python manage.py runserver
echo.
pause

@echo off
REM Fixed SQL Import Script for PostgreSQL 17.6
REM This script properly handles COPY ... FROM stdin; commands

echo =========================================
echo PostgreSQL SQL Import - Fixed Version
echo =========================================
echo.

setlocal enabledelayedexpansion

set DB_NAME=buyvaulthub_db
set DB_USER=postgres
set SQL_FILE=backup_20251029_020655.sql

REM Check if SQL file exists
if not exist "%SQL_FILE%" (
    echo [ERROR] SQL file '%SQL_FILE%' not found!
    echo Please make sure the file is in the current directory.
    pause
    exit /b 1
)

echo [OK] Found SQL file: %SQL_FILE%
echo.

REM Get PostgreSQL password
set /p DB_PASSWORD="Enter PostgreSQL password for user '%DB_USER%': "
echo.

REM Set password as environment variable
set PGPASSWORD=%DB_PASSWORD%

REM Check PostgreSQL connection
echo Checking PostgreSQL connection...
psql -U %DB_USER% -c "\q" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Cannot connect to PostgreSQL!
    echo Please check:
    echo   1. PostgreSQL is running
    echo   2. Password is correct
    echo   3. PostgreSQL is accessible
    pause
    exit /b 1
)

echo [OK] PostgreSQL connection successful
echo.

REM Drop and recreate database for clean import
echo Dropping existing database (if exists)...
psql -U %DB_USER% -c "DROP DATABASE IF EXISTS %DB_NAME%;" >nul 2>&1

echo Creating fresh database...
psql -U %DB_USER% -c "CREATE DATABASE %DB_NAME%;" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Database might already exist, continuing...
) else (
    echo [OK] Database created
)

echo.

REM Import SQL file
echo =========================================
echo Importing SQL file...
echo This will take 3-5 minutes. Please wait...
echo =========================================
echo.

REM Use full path and handle errors
psql -U %DB_USER% -d %DB_NAME% -f "%CD%\%SQL_FILE%" -v ON_ERROR_STOP=0

if errorlevel 1 (
    echo.
    echo [WARNING] Import completed with some errors.
    echo This might be normal if some objects already exist.
    echo Verifying data...
) else (
    echo.
    echo [OK] SQL file imported successfully
)

echo.

REM Verify import
echo Verifying import...
for /f "tokens=*" %%i in ('psql -U %DB_USER% -d %DB_NAME% -t -c "SELECT COUNT(*) FROM products_coreproduct;" 2^>nul') do set PRODUCT_COUNT=%%i
set PRODUCT_COUNT=!PRODUCT_COUNT: =!

if !PRODUCT_COUNT! GTR 0 (
    echo [OK] Import verified successfully!
    echo    Found !PRODUCT_COUNT! products in database
) else (
    echo [WARNING] No products found. Import might have failed.
    echo    Please check error messages above.
)

echo.

REM Check tables
echo Checking tables...
for /f "tokens=*" %%i in ('psql -U %DB_USER% -d %DB_NAME% -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2^>nul') do set TABLE_COUNT=%%i
set TABLE_COUNT=!TABLE_COUNT: =!

if !TABLE_COUNT! GTR 0 (
    echo [OK] Found !TABLE_COUNT! tables in database
) else (
    echo [ERROR] No tables found. Import failed.
    pause
    exit /b 1
)

echo.
echo =========================================
echo Import Process Complete!
echo =========================================
echo.
echo Next steps:
echo 1. Update backend\.env with database credentials
echo 2. Test backend connection: python manage.py dbshell
echo 3. Start backend: python manage.py runserver
echo.
pause

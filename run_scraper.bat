@echo off
echo IndiaMART Lead Scraper
echo =====================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python 3.7 or higher.
    pause
    exit /b
)

REM Check if requirements are installed
echo Checking dependencies...
pip show selenium >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing required packages...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo Failed to install dependencies. Please run 'pip install -r requirements.txt' manually.
        pause
        exit /b
    )
)

echo Starting IndiaMART Lead Scraper...
echo.
python indiamart_scraper.py

echo.
if exist leads.csv (
    echo Leads have been exported to leads.csv
    echo Opening file location...
    explorer .
)

pause
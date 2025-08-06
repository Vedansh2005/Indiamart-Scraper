@echo off
echo IndiaMART Lead Scraper (CLI Version)
echo ===================================
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

echo.
echo Starting IndiaMART Lead Scraper CLI...
echo.
echo Available options:
echo   --keyword, -k     : Product keyword to search for
echo   --output, -o      : Output CSV file name (default: leads.csv)
echo   --min-leads, -m   : Minimum number of leads to collect (default: 100)
echo   --headless, -H    : Run in headless mode (no browser UI)
echo.

set /p params=Enter command line parameters (or leave empty for interactive mode): 

python cli.py %params%

echo.
if exist leads.csv (
    echo Leads have been exported successfully
    echo Opening file location...
    explorer .
)

pause
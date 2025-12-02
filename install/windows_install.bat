@echo off
REM Highright Native Messaging Host Installer for Windows
REM This script launches the Python installer

echo ========================================
echo Highright Installer for Windows
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.7+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo Python found. Starting installation...
echo.

REM Run installer
python "%~dp0install.py"

if errorlevel 1 (
    echo.
    echo Installation failed. Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo Installation complete!
pause

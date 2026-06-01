@echo off
REM Ravinala Installation Script for Windows
REM This script sets up the Ravinala environment and installs the package

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║  🌴 RAVINALA INSTALLATION WIZARD                             ║
echo ║  The Cross-Asset Quantum Structuring Lab                     ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

echo ✓ Python detected
python --version
echo.

REM Create virtual environment
echo 📦 Creating virtual environment...
if exist .venv (
    echo ⚠️  Virtual environment already exists. Skipping...
) else (
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
)
echo ✓ Virtual environment ready

REM Activate virtual environment
echo 📦 Activating virtual environment...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)
echo ✓ Environment activated

REM Upgrade pip
echo 📥 Upgrading pip...
python -m pip install --upgrade pip setuptools wheel >nul 2>&1

REM Install Ravinala in editable mode
echo 📥 Installing Ravinala...
pip install -e .
if %errorlevel% neq 0 (
    echo ❌ Installation failed
    pause
    exit /b 1
)
echo ✓ Ravinala installed successfully

REM Create desktop shortcut (optional)
echo.
echo 🎯 Installation Complete!
echo.
echo ════════════════════════════════════════════════════════════════
echo To launch Ravinala, simply run:
echo.
echo     ravinala
echo.
echo Or use Python directly:
echo.
echo     python -m ravinala
echo.
echo ════════════════════════════════════════════════════════════════
echo.
pause

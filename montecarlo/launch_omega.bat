@echo off
REM ============================================================================
REM OMEGA v2.0.0 - Launch Script
REM Advanced AI Portfolio Allocator
REM ============================================================================

echo.
echo  ╔════════════════════════════════════════════════════════════════════════╗
echo  ║                                                                        ║
echo  ║                    🚀 OMEGA v2.0.0 - Launching...                    ║
echo  ║                   Advanced AI Portfolio Allocator                      ║
echo  ║                                                                        ║
echo  ╚════════════════════════════════════════════════════════════════════════╝
echo.

REM Change to project directory
cd /d "%~dp0montecarlo"

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Python not found. Please install Python 3.10+ and try again.
    pause
    exit /b 1
)

echo ✅ Python found
echo.
echo 📦 Starting Streamlit server...
echo.

REM Launch Streamlit
python -m streamlit run src/app.py --logger.level=error

REM If Streamlit closes, pause to show any error messages
if %errorlevel% neq 0 (
    echo.
    echo ❌ ERROR: Failed to start Streamlit
    pause
    exit /b 1
)

pause

@echo off
REM Verification script for Ravinala deployment (Windows)
REM Run this after docker-compose up -d to verify all services are working

setlocal enabledelayedexpansion

color 0A
cls

echo.
echo ==================================================
echo   Ravinala Deployment Verification
echo ==================================================
echo.

set PASSED=0
set FAILED=0

REM Test function for HTTP endpoints
setlocal enabledelayedexpansion
:test_endpoint
set url=%1
set name=%2
set expected_code=%3

echo Testing %name%...
timeout /t 1 /nobreak >nul

for /f %%A in ('powershell -Command "try { $response = Invoke-WebRequest -Uri %url% -UseBasicParsing -ErrorAction SilentlyContinue; if ($response) { Write-Host $response.StatusCode } else { Write-Host '000' } } catch { Write-Host '000' }"') do set response=%%A

if "%response%"=="%expected_code%" (
    echo   [OK] HTTP %response%
    set /a PASSED+=1
) else (
    echo   [FAIL] HTTP %response% (expected %expected_code%)
    set /a FAILED+=1
)
endlocal & set PASSED=%PASSED% & set FAILED=%FAILED%
goto :eof

:main

echo ℹ Service Connectivity
echo ==================================================
echo.

echo Testing Docker containers status...
docker-compose ps
if %errorlevel% neq 0 (
    echo [FAIL] Docker compose not running or not in deployment directory
    echo.
    echo Please run: cd montecarlo\deployment
    echo Then run: docker-compose up -d
    pause
    exit /b 1
)

echo.
echo ℹ HTTP API Endpoints (requires netcat or PowerShell)
echo ==================================================
echo.

echo Testing Frontend (http://localhost:5173)...
timeout /t 1 /nobreak >nul
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:5173' -UseBasicParsing; if ($r.StatusCode -eq 200) { Write-Host '[OK] Frontend responding'; exit 0 } } catch { Write-Host '[FAIL] Frontend not responding'; exit 1 }"

echo.
echo Testing Backend (http://localhost:8000/health)...
timeout /t 1 /nobreak >nul
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing; if ($r.StatusCode -eq 200) { Write-Host '[OK] Backend responding'; exit 0 } } catch { Write-Host '[FAIL] Backend not responding'; exit 1 }"

echo.
echo Testing API Docs (http://localhost:8000/docs)...
timeout /t 1 /nobreak >nul
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/docs' -UseBasicParsing; if ($r.StatusCode -eq 200) { Write-Host '[OK] API Docs available'; exit 0 } } catch { Write-Host '[FAIL] API Docs not available'; exit 1 }"

echo.
echo ℹ Database Checks
echo ==================================================
echo.

echo Testing PostgreSQL connection...
docker exec ravinala_postgres psql -U ravinala -d ravinala -c "SELECT 1;" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] PostgreSQL connected
) else (
    echo [FAIL] PostgreSQL connection failed
)

echo.
echo Testing Redis connection...
docker exec ravinala_redis redis-cli ping >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Redis responding
) else (
    echo [FAIL] Redis connection failed
)

echo.
echo ==================================================
echo   Verification Complete
echo ==================================================
echo.
echo You can now access the application at:
echo   - Frontend: http://localhost:5173
echo   - Backend API: http://localhost:8000/docs
echo   - Agent Monitor: http://localhost:5173/agents/monitor
echo.
echo To view logs: docker-compose logs -f
echo To stop services: docker-compose down
echo.
pause

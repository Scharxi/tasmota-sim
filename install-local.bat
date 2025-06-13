@echo off
echo Installing Tasmota Simulator CLI locally...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Install in development mode
echo Installing dependencies...
pip install -e .

if errorlevel 1 (
    echo ERROR: Installation failed
    pause
    exit /b 1
)

echo.
echo ✓ Installation successful!
echo.
echo You can now use the CLI with:
echo   tasmota-sim --help
echo.
echo Or directly with Python:
echo   python -m tasmota_sim.cli --help
echo.
echo To start the Docker services (RabbitMQ + Devices):
echo   docker-compose -f docker-compose.services.yml up -d
echo   docker-compose -f docker-compose.override.yml up -d
echo.
pause 
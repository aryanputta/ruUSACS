@echo off
REM RuParks Backend Startup Script

echo [INFO] Checking for Python...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARN] 'python' command not found. Trying 'py'...
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python not found. Please install Python from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)

echo [INFO] Using Python command: %PYTHON_CMD%

echo [INFO] Installing dependencies...
%PYTHON_CMD% -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [INFO] Starting Server...
echo [INFO] Swagger UI will be available at http://localhost:8000/docs
%PYTHON_CMD% -m uvicorn main:app --reload
pause

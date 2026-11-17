@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating Obsidrop virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Could not create the virtual environment. Check that Python is installed.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" app.py
if errorlevel 1 (
    echo.
    echo Obsidrop exited with an error. See README.md and the application log.
    pause
)
endlocal

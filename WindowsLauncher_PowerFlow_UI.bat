@echo off
setlocal

REM Double-click launcher for the GridSolver UI (Windows)
cd /d "%~dp0" || exit /b 1

REM Ensure local imports resolve correctly.
set "PYTHONPATH=%CD%"

REM Ensure virtual environment exists.
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Failed with "py -3". Trying "python"...
        python -m venv .venv
        if errorlevel 1 (
            echo Failed to create .venv
            pause
            exit /b 1
        )
    )
)

REM Install/update dependencies.
echo Installing dependencies (if needed)...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b 1
)

REM Launch Streamlit UI.
echo Starting GridSolver UI...
echo If browser does not open automatically, go to: http://localhost:8501
".venv\Scripts\python.exe" -m streamlit run src\ui\streamlit_app.py

REM Keep terminal window open if Streamlit exits unexpectedly.
echo UI stopped.
pause

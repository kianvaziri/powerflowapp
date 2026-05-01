@echo off
setlocal

REM Double-click launcher for the GridSolver UI (Windows)
set "SCRIPT_DIR=%~dp0"
set "APP_DIR=%SCRIPT_DIR%"

REM Resolve app directory robustly (handles nested folder layouts).
if exist "%APP_DIR%requirements.txt" if exist "%APP_DIR%src\ui\streamlit_app.py" goto app_found
if exist "%SCRIPT_DIR%powerflowapp\requirements.txt" if exist "%SCRIPT_DIR%powerflowapp\src\ui\streamlit_app.py" (
    set "APP_DIR=%SCRIPT_DIR%powerflowapp\"
    goto app_found
)
if exist "%SCRIPT_DIR%..\powerflowapp\requirements.txt" if exist "%SCRIPT_DIR%..\powerflowapp\src\ui\streamlit_app.py" (
    set "APP_DIR=%SCRIPT_DIR%..\powerflowapp\"
    goto app_found
)

echo Could not locate app root.
echo Expected to find requirements.txt and src\ui\streamlit_app.py near:
echo   %SCRIPT_DIR%
pause
exit /b 1

:app_found
cd /d "%APP_DIR%" || exit /b 1

REM Ensure local imports resolve correctly.
set "PYTHONPATH=%APP_DIR%"

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
".venv\Scripts\python.exe" -m pip install -r "%APP_DIR%requirements.txt"
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

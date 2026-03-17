@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "PYTHON_EXE=W:\ComfyUI_windows_portable\python_embeded\python.exe"
set "SCRIPT_PATH=%~dp0scripts\check_fail_png_metadata.py"

cd /d "%~dp0"

if not exist "%PYTHON_EXE%" (
    echo ERROR: Python executable not found: %PYTHON_EXE%
    pause
    exit /b 1
)

if not exist "%SCRIPT_PATH%" (
    echo ERROR: Script file not found: %SCRIPT_PATH%
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%SCRIPT_PATH%"

if errorlevel 1 (
    echo.
    echo ERROR: Script execution failed.
    pause
    exit /b 1
)

pause

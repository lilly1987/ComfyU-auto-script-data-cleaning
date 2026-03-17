@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "PYTHON_EXE=W:\ComfyUI_windows_portable\python_embeded\python.exe"
set "SCRIPT_PATH=%~dp0scripts\calculate_sha256_lora.py"

cd /d "%~dp0"

if not exist "%PYTHON_EXE%" (
    echo 오류: Python 실행 파일을 찾을 수 없습니다: %PYTHON_EXE%
    pause
    exit /b 1
)

if not exist "%SCRIPT_PATH%" (
    echo 오류: 스크립트 파일을 찾을 수 없습니다: %SCRIPT_PATH%
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%SCRIPT_PATH%"

if errorlevel 1 (
    echo.
    echo 오류가 발생했습니다.
    pause
    exit /b 1
)

pause


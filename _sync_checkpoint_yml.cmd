@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON_EXE=W:\ComfyUI_windows_portable\python_embeded\python.exe"
set "SCRIPT_PATH=%ROOT%scripts\sync_checkpoint_yml.py"

if not exist "%PYTHON_EXE%" (
    echo error: python not found: %PYTHON_EXE%
    exit /b 1
)

if not exist "%SCRIPT_PATH%" (
    echo error: script not found: %SCRIPT_PATH%
    exit /b 1
)

pushd "%ROOT%" >nul 2>&1
if errorlevel 1 (
    echo error: failed to change directory: %ROOT%
    exit /b 1
)

"%PYTHON_EXE%" "%SCRIPT_PATH%" %*
set "EXIT_CODE=%ERRORLEVEL%"

popd >nul 2>&1
exit /b %EXIT_CODE%
pause
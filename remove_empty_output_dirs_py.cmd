@echo off
REM Wrapper to run the Python version. Usage:
REM   remove_empty_output_dirs_py.cmd [path] [--dry]

setlocal
set "PY_SCRIPT=%~dp0remove_empty_output_dirs.py"

if not exist "%PY_SCRIPT%" (
    echo Python script not found: "%PY_SCRIPT%"
    endlocal
    exit /b 1
)

REM Pass all arguments through to python
python "%PY_SCRIPT%" %*
set "RC=%ERRORLEVEL%"
endlocal
exit /b %RC%

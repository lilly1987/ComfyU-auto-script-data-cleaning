@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "PYTHON_PATH=W:\ComfyUI_windows_portable\python_embeded\python.exe"
set "NODES_PATH=W:\ComfyU-auto-script-data-cleaning"

echo [ComfyUI 커스텀 노드 업데이트 시작]


if exist "%NODES_PATH%\requirements.txt" (
	echo.
	echo 경로 처리 중: %NODES_PATH%
	echo 설치 중: %NODES_PATH%\requirements.txt
	"%PYTHON_PATH%" -m pip install -r "%NODES_PATH%\requirements.txt"
)


echo.
echo [모든 업데이트가 완료되었습니다]
pause


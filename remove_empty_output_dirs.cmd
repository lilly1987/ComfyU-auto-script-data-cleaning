@echo off
REM remove_empty_output_dirs.cmd
REM 삭제 대상: W:\ComfyUI_windows_portable\output 내부의 빈 폴더들을 재귀적으로 삭제
REM 사용법: double-click 하거나 명령행에서 실행
REM   remove_empty_output_dirs.cmd           -> 실제 삭제 수행
REM   remove_empty_output_dirs.cmd dry       -> Dry-run: 삭제될 폴더만 출력 (실제 삭제 안함)

setlocal
set "TARGET=W:\ComfyUI_windows_portable\output"
set "DRY=0"
if /I "%~1"=="dry" set "DRY=1"
if /I "%~1"=="/dry" set "DRY=1"

if not exist "%TARGET%" (
    echo Target folder "%TARGET%" not found.
    endlocal
    exit /b 1
)

echo Removing empty directories under "%TARGET%"...
if "%DRY%"=="1" (
    echo "(Dry run) -- no directories will be removed"
)

REM 안전하게 PowerShell 스크립트를 임시로 생성하여 실행
set "TMPPS=%TEMP%\remove_empty_output_dirs.ps1"
(
    echo param([string]$target, [string]$dry)
    echo if(-not (Test-Path $target)){ Write-Host "Target not found: $target"; exit 1 }
    echo $dirs = Get-ChildItem -Path $target -Directory -Recurse ^| Sort-Object FullName -Descending
    echo $count = 0
    echo foreach($d in $dirs) {
    echo     if((Get-ChildItem -LiteralPath $d.FullName -Force ^| Measure-Object).Count -eq 0) {
    echo         if($dry -eq '1') { Write-Host "Would remove: $($d.FullName)" } else { Remove-Item -LiteralPath $d.FullName -Force -Recurse; Write-Host "Removed: $($d.FullName)"; $count++ }
    echo     }
    echo }
    echo if($dry -ne '1') { Write-Host "Done. Removed $count directories." } else { Write-Host "Dry run complete." }
) > "%TMPPS%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%TMPPS%" "%TARGET%" "%DRY%"
set "RC=%ERRORLEVEL%"
if exist "%TMPPS%" del "%TMPPS%"

endlocal
exit /b %RC%

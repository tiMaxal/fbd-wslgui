@echo off
setlocal
REM Tiny A/B launcher for test UI toolkit mode
REM Usage:
REM   fbdwslgui-test_mode.bat ttk
REM   fbdwslgui-test_mode.bat ctk

set "MODE=%~1"
if /i "%MODE%"=="" (
    echo Select toolkit mode:
    echo   1. Legacy ttk
    echo   2. CustomTkinter
    set /p MODE_CHOICE=Enter choice ^(1/2^): 
    if "%MODE_CHOICE%"=="2" (
        set "MODE=customtkinter"
    ) else (
        set "MODE=ttk"
    )
)

if /i "%MODE%"=="2" set "MODE=customtkinter"
if /i "%MODE%"=="1" set "MODE=ttk"
if /i "%MODE%"=="ctk" set "MODE=customtkinter"
if /i not "%MODE%"=="ttk" if /i not "%MODE%"=="customtkinter" (
    echo Invalid mode: %MODE%
    echo Use: ttk ^| ctk ^| customtkinter
    exit /b 1
)

echo Launching test GUI with mode: %MODE%

set "CFG_DIR=%USERPROFILE%\.fbdgui"
set "CFG_FILE=%CFG_DIR%\fbdgui_config.json"
if not exist "%CFG_DIR%" mkdir "%CFG_DIR%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$cfgPath = '%CFG_FILE%';" ^
    "$mode = '%MODE%';" ^
    "$cfg = @{};" ^
    "if (Test-Path $cfgPath) { try { $cfg = Get-Content -Raw $cfgPath | ConvertFrom-Json -AsHashtable } catch { $cfg = @{} } };" ^
    "$cfg['ui_toolkit'] = $mode;" ^
    "$cfg | ConvertTo-Json -Depth 16 | Set-Content -Encoding UTF8 $cfgPath"

if errorlevel 1 (
        echo [!] Failed to write toolkit mode to config.
        exit /b 1
)

call "%~dp0fbdwslgui-test_launch.bat"

@echo off
:: fbdwslgui_docmode_capture.bat
::
:: Thin Windows launcher — converts this file's directory to a WSL path and
:: calls fbdwslgui_docmode_capture.sh inside WSL.
::
:: Requirements: WSL installed, with an Ubuntu (or Debian) distro available.
:: Usage: double-click, or run from a command prompt.

setlocal

:choose_theme

echo ======================================
echo   FBD GUI Doc-Mode Screenshot Capture
echo ======================================
echo.
echo   1. Light Theme (default)
echo   2. Dark Theme
echo.
set /p THEME_CHOICE="Choose theme [1/2]: "
if "%THEME_CHOICE%"=="2" (
    set "THEME=dark"
) else (
    set "THEME=light"
)
echo [*] Theme selected: %THEME%
echo.

:: Resolve the .sh sitting alongside this .bat into a WSL path
FOR /F "delims=" %%i IN ('wsl wslpath -a "%~dp0fbdwslgui_docmode_capture.sh"') DO SET WSL_SCRIPT=%%i

IF "%WSL_SCRIPT%"=="" (
    echo [!] Could not resolve WSL path.  Is WSL installed and configured?
    pause
    exit /b 1
)

echo [*] FBD GUI doc-mode capture launcher
echo [*] WSL script: %WSL_SCRIPT%
echo [*] Theme: %THEME%
echo [!] Do not run the normal GUI/node/miner launchers while doc-mode capture is running.
echo [!] Wait for the completion message in this window before starting the app normally again.
echo.

wsl bash "%WSL_SCRIPT%" "%THEME%"

set "CAPTURE_EXIT=%ERRORLEVEL%"

IF %CAPTURE_EXIT% GEQ 1 (
    echo.
    echo [!] Capture script exited with an error ^(see output above^).
    echo [!] Resolve the issue before running the normal app launcher.
) ELSE (
    echo.
    echo [OK] Doc-mode capture completed.
    echo [OK] Screenshots are in:
    echo        %~dp0..\fbdwslgui_docs_screens\
    echo [OK] You can now run the app normally again.
)

echo.
pause

endlocal
exit /b %CAPTURE_EXIT%

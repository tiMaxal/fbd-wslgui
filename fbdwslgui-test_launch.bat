@echo off
setlocal enabledelayedexpansion
REM FBD GUI Test Version Launcher for Windows
REM This launches the TEST Python GUI in WSL with automatic X11 server setup

echo ================================
echo FBD Node Manager GUI - TEST VERSION
echo ================================
echo.

REM Check if WSL is installed
wsl --list >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: WSL is not installed or not available
    echo Please install WSL first: wsl --install
    pause
    exit /b 1
)

echo Checking for X11 server...
echo.

REM Set marker file path
set "VCXSRV_MARKER=%~dp0.vcxsrv_running"

REM Clean up stale marker if VcXsrv isn't actually running
if exist "%VCXSRV_MARKER%" (
    tasklist /FI "IMAGENAME eq vcxsrv.exe" 2>NUL | find /I /N "vcxsrv.exe">NUL
    if not "%ERRORLEVEL%"=="0" (
        del "%VCXSRV_MARKER%" >nul 2>&1
    )
)

REM Check if VcXsrv is running
tasklist /FI "IMAGENAME eq vcxsrv.exe" 2>NUL | find /I /N "vcxsrv.exe">NUL
if "%ERRORLEVEL%"=="0" (
    REM Check if marker file exists (indicates we started it with correct flags)
    if exist "%VCXSRV_MARKER%" (
        echo [OK] VcXsrv is running (started by this script)
        echo Verifying X11 connection...
        
        REM Quick test to verify -ac flag is working
        wsl -e bash -c "timeout 2 xset q >/dev/null 2>&1"
        if "%ERRORLEVEL%"=="0" (
            echo [OK] X11 connection verified
            echo.
            goto :launch_gui
        ) else (
            echo [!] X11 connection test failed - VcXsrv may have been restarted without -ac flag
            echo Restarting VcXsrv with correct settings...
            echo.
            taskkill /IM vcxsrv.exe /F >nul 2>&1
            timeout /t 2 /nobreak >nul
            del "%VCXSRV_MARKER%" >nul 2>&1
            goto :start_vcxsrv
        )
    )
    
    echo [!] VcXsrv is already running
    echo.
    echo VcXsrv must be started with '-ac' flag for WSL compatibility.
    echo.
    echo Options:
    echo   1. Restart VcXsrv with correct settings (recommended)
    echo   2. Continue with current VcXsrv (may fail if not configured correctly)
    echo   3. Stop VcXsrv and exit
    echo.
    set "vcxchoice="
    set /p "vcxchoice=Enter choice (1/2/3): "
    
    if "!vcxchoice!"=="" set "vcxchoice=1"
    
    if "!vcxchoice!"=="1" (
        echo.
        echo Stopping current VcXsrv instance...
        taskkill /IM vcxsrv.exe /F >nul 2>&1
        timeout /t 2 /nobreak >nul
        del "%VCXSRV_MARKER%" >nul 2>&1
        goto :start_vcxsrv
    ) else if "!vcxchoice!"=="2" (
        echo.
        echo [!] Continuing with existing VcXsrv instance...
        echo If connection fails, please restart this script and choose option 1.
        echo.
        
        REM Still check firewall even with existing instance
        echo Checking Windows Firewall...
        netsh advfirewall firewall show rule name="VcXsrv X11 Server (WSL)" >nul 2>&1
        if errorlevel 1 (
            echo [!] Warning: Firewall rule not found
            echo This may prevent WSL from connecting to VcXsrv.
            echo.
            set "fwchoice2="
            set /p "fwchoice2=Add firewall rule? (Y/N): "
            if "!fwchoice2!"=="" set "fwchoice2=N"
            if /i "!fwchoice2!"=="Y" (
                powershell -Command "Start-Process '%~dp0Add_Firewall_Rule.bat' -Verb RunAs" 2>nul
                timeout /t 2 /nobreak >nul
                pause
            )
        )
        
        goto :launch_gui
    ) else (
        echo.
        echo Stopping VcXsrv and exiting...
        taskkill /IM vcxsrv.exe /F >nul 2>&1
        del "%VCXSRV_MARKER%" >nul 2>&1
        echo Done.
        pause
        exit /b 0
    )
)

:start_vcxsrv

REM Check if VcXsrv is installed
set "VCXSRV_PATH="

REM Check common installation paths
if exist "C:\Program Files\VcXsrv\vcxsrv.exe" (
    set "VCXSRV_PATH=C:\Program Files\VcXsrv\vcxsrv.exe"
) else if exist "C:\Program Files (x86)\VcXsrv\vcxsrv.exe" (
    set "VCXSRV_PATH=C:\Program Files (x86)\VcXsrv\vcxsrv.exe"
) else (
    REM Search in PATH
    where vcxsrv.exe >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=*" %%i in ('where vcxsrv.exe') do set "VCXSRV_PATH=%%i"
    )
)

if not defined VCXSRV_PATH (
    goto :vcxsrv_not_found
)

echo [OK] VcXsrv found
echo Starting VcXsrv X11 server...
echo.

REM Start VcXsrv with required flags
REM -multiwindow = integrate X11 windows with Windows desktop
REM -clipboard = enable clipboard sharing
REM -wgl = use Windows OpenGL (better performance)
REM -ac = disable access control (required for WSL)
REM :0 = use display :0
start "" "%VCXSRV_PATH%" :0 -ac -multiwindow -clipboard -wgl

REM Wait for VcXsrv to start
timeout /t 3 /nobreak >nul

REM Create marker file to indicate we started it
echo. > "%VCXSRV_MARKER%"

REM Verify VcXsrv started
tasklist /FI "IMAGENAME eq vcxsrv.exe" 2>NUL | find /I /N "vcxsrv.exe">NUL
if not "%ERRORLEVEL%"=="0" (
    echo [!] Error: VcXsrv failed to start
    echo.
    pause
    exit /b 1
)

echo [OK] VcXsrv started successfully
echo.

REM Check firewall
echo Checking Windows Firewall...
netsh advfirewall firewall show rule name="VcXsrv X11 Server (WSL)" >nul 2>&1
if errorlevel 1 (
    echo [!] Warning: Firewall rule not found
    echo.
    echo Windows Firewall may block WSL from connecting to VcXsrv.
    echo.
    echo To fix this, you need to add a firewall rule.
    echo This requires administrator privileges.
    echo.
    set "fwchoice="
    set /p "fwchoice=Add firewall rule now? (Y/N): "
    
    if "!fwchoice!"=="" set "fwchoice=N"
    
    if /i "!fwchoice!"=="Y" (
        echo.
        echo Opening Add_Firewall_Rule.bat with administrator privileges...
        echo Please approve the UAC prompt when it appears.
        echo.
        
        REM Run the firewall script with admin privileges
        powershell -Command "Start-Process '%~dp0Add_Firewall_Rule.bat' -Verb RunAs" 2>nul
        
        if errorlevel 1 (
            echo [!] Failed to launch with administrator privileges
            echo Please run Add_Firewall_Rule.bat manually as administrator.
            echo.
        ) else (
            echo.
            echo Waiting for firewall configuration...
            timeout /t 2 /nobreak >nul
            
            echo.
            echo [!] IMPORTANT: After adding the firewall rule, VcXsrv must
            echo be restarted to accept connections from WSL.
            echo.
            echo Restarting VcXsrv now...
            taskkill /IM vcxsrv.exe /F >nul 2>&1
            timeout /t 2 /nobreak >nul
            
            REM Restart VcXsrv
            start "" "%VCXSRV_PATH%" :0 -ac -multiwindow -clipboard -wgl
            timeout /t 3 /nobreak >nul
            
            REM Recreate marker file
            echo. > "%VCXSRV_MARKER%"
            
            echo [OK] VcXsrv restarted
            echo.
        )
        
        pause
    ) else (
        echo.
        echo [!] Skipping firewall configuration
        echo Connection may fail. If so, run Add_Firewall_Rule.bat as administrator.
        echo.
    )
) else (
    echo [OK] Firewall rule exists
    echo.
)

REM Test X11 connection
echo Testing X11 connection...
wsl -e bash -c "timeout 3 xset q >/dev/null 2>&1"
if not "%ERRORLEVEL%"=="0" (
    echo [!] Warning: X11 connection test failed
    echo.
    echo This may indicate a firewall or network issue.
    echo The GUI may not display correctly.
    echo.
    pause
)

goto :launch_gui

:vcxsrv_not_found

REM VcXsrv not found, offer to download
echo [!] VcXsrv is not installed
echo.
echo VcXsrv is required to run GUI applications from WSL.
echo.
echo Please install VcXsrv from:
echo https://github.com/marchaesen/vcxsrv/releases/latest
echo.
echo After installation, run this script again.
echo.
pause
exit /b 1

:launch_gui

echo Launching FBD GUI TEST VERSION in WSL...
echo.
echo Note: The GUI window should appear shortly.
echo       This window will remain open while the GUI is running.
echo       Close the GUI to return here.
echo.
echo ========================================
echo.

REM Set DISPLAY for WSL
set WSL_DISPLAY=:0

REM Get the directory where this script is located (Windows path)
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Convert Windows path to WSL path (without calling wslpath)
set "SCRIPT_DIR_SLASH=%SCRIPT_DIR:\=/%"
set "DRIVE_LETTER=%SCRIPT_DIR_SLASH:~0,1%"
for %%A in (a b c d e f g h i j k l m n o p q r s t u v w x y z) do (
    if /I "%DRIVE_LETTER%"=="%%A" set "DRIVE_LETTER=%%A"
)
set "PATH_REST=%SCRIPT_DIR_SLASH:~2%"
set "WSL_PATH=/mnt/%DRIVE_LETTER%%PATH_REST%"

REM Launch in default WSL distro (venv is used when present)
REM old lauch line
REM wsl -e bash -c "cd $1 && if [ -f .venv-wslgui/bin/activate ]; then . .venv-wslgui/bin/activate; fi && python3 -u fbd_wslgui.test.py" _ "%WSL_PATH%" 2>&1
wsl -e bash -c "export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0; cd '%WSL_PATH%' && if [ -f .venv-wslgui/bin/activate ]; then . .venv-wslgui/bin/activate; fi && python3 -u fbd_wslgui.test.py"
echo.
echo GUI closed.
echo.

REM Check if VcXsrv is still running
tasklist /FI "IMAGENAME eq vcxsrv.exe" 2>NUL | find /I /N "vcxsrv.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo VcXsrv is still running in the background.
    echo You can close it from the system tray if needed.
) else (
    echo VcXsrv has stopped.
)
echo.
pause

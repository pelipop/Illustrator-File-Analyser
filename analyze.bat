@echo off
setlocal EnableDelayedExpansion

echo.
echo ============================================================
echo    AI File Analyzer
echo ============================================================
echo.

:: -----------------------------------------------------------
:: 1. Locate Python
:: -----------------------------------------------------------
set "PYTHON_CMD="

where py >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "PYTHON_CMD=py -3"
    goto :get_folder
)

where python >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "PYTHON_CMD=python"
    goto :get_folder
)

echo  [ERROR] Python is not installed or not in PATH.
echo  Please run setup.bat first.
echo.
pause
exit /b 1

:: -----------------------------------------------------------
:: 2. Get the target folder
::    - Supports drag-and-drop (argument) or manual input
:: -----------------------------------------------------------
:get_folder

:: Check if a folder was passed as an argument (drag-and-drop)
if not "%~1"=="" (
    set "TARGET_DIR=%~1"
    echo  Using folder: !TARGET_DIR!
    goto :run_analysis
)

:: Otherwise prompt the user
echo  Enter the full path to your folder of .ai files.
echo  (You can also drag-and-drop a folder onto this .bat file)
echo.
set /p "TARGET_DIR=  Folder path: "

:: Remove surrounding quotes if present
set "TARGET_DIR=!TARGET_DIR:"=!"

if "!TARGET_DIR!"=="" (
    echo.
    echo  [ERROR] No folder path provided.
    pause
    exit /b 1
)

:: -----------------------------------------------------------
:: 3. Run the analysis
:: -----------------------------------------------------------
:run_analysis
echo.
echo  Starting analysis...
echo  -------------------------------------------------------
echo.

%PYTHON_CMD% "%~dp0analyze_ai_files.py" "!TARGET_DIR!"

echo.
pause

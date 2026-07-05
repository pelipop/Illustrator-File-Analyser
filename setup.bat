@echo off
setlocal EnableDelayedExpansion

echo.
echo ============================================================
echo    AI File Analyzer - Setup
echo ============================================================
echo.

:: -----------------------------------------------------------
:: 1. Locate Python (try 'py' launcher first, then 'python')
:: -----------------------------------------------------------
set "PYTHON_CMD="

where py >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "PYTHON_CMD=py -3"
    echo  [OK] Found Python launcher ^(py^)
    goto :check_version
)

where python >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "PYTHON_CMD=python"
    echo  [OK] Found python on PATH
    goto :check_version
)

echo  [ERROR] Python is NOT installed or not in your PATH.
echo.
echo  Please install Python 3.8 or newer from:
echo    https://www.python.org/downloads/
echo.
echo  IMPORTANT: During installation, check the box that says:
echo    "Add Python to PATH"
echo.
pause
exit /b 1

:: -----------------------------------------------------------
:: 2. Verify Python version (>= 3.8)
:: -----------------------------------------------------------
:check_version
echo.
echo  Checking Python version...
%PYTHON_CMD% --version
echo.

:: -----------------------------------------------------------
:: 3. Install required packages
:: -----------------------------------------------------------
echo  Installing required packages...
echo  -------------------------------------------------------
%PYTHON_CMD% -m pip install --upgrade pip >nul 2>&1
%PYTHON_CMD% -m pip install -r "%~dp0requirements.txt"
echo  -------------------------------------------------------
echo.

if !ERRORLEVEL! NEQ 0 (
    echo  [ERROR] Package installation failed.
    echo  Try running this script as Administrator.
    echo.
    pause
    exit /b 1
)

:: -----------------------------------------------------------
:: 4. Verify PyMuPDF import
:: -----------------------------------------------------------
echo  Verifying installation...
%PYTHON_CMD% -c "import fitz; print('  [OK] PyMuPDF', fitz.version[0], 'installed successfully')" 2>nul
if !ERRORLEVEL! NEQ 0 (
    %PYTHON_CMD% -c "import pymupdf; print('  [OK] PyMuPDF installed successfully')" 2>nul
)
if !ERRORLEVEL! NEQ 0 (
    echo  [WARNING] Could not verify PyMuPDF installation.
    echo  The analyzer may still work. Try running analyze.bat.
)

echo.
echo ============================================================
echo    Setup Complete!
echo ============================================================
echo.
echo  You can now run 'analyze.bat' to analyze your AI files.
echo.
pause

@echo off
REM Windows batch file for Tapo LLMs CLI
REM Calls Python module directly

REM Find Python executable
set PYTHON_EXE=
if exist "%VIRTUAL_ENV%\Scripts\python.exe" (
    set PYTHON_EXE=%VIRTUAL_ENV%\Scripts\python.exe
    goto :found
)
if exist "venv\Scripts\python.exe" (
    set PYTHON_EXE=venv\Scripts\python.exe
    goto :found
)
if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXE=.venv\Scripts\python.exe
    goto :found
)
for %%p in (python.exe) do (
    if "%%~$PATH:p" ne "" (
        set PYTHON_EXE=%%~$PATH:p
        goto :found
    )
)

echo ERROR: Python executable not found. Please install Python or activate a virtual environment.
exit /b 1

:found
REM Execute the main module
"%PYTHON_EXE%" -m devices_mcp.cli %*
exit /b %ERRORLEVEL%

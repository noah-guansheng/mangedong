@echo off
cd /d "%~dp0"
where python >nul 2>&1
if %ERRORLEVEL%==0 goto :run_python
where py >nul 2>&1
if %ERRORLEVEL%==0 goto :run_py
echo Install Python 3.11+ from https://www.python.org/downloads/ and tick Add python.exe to PATH.
pause
exit /b 1
:run_python
python start.py %*
exit /b %ERRORLEVEL%
:run_py
py -3 start.py %*
exit /b %ERRORLEVEL%

@echo off
setlocal
cd /d "%~dp0"
if exist ".env" (
  for /f "usebackq tokens=* eol=#" %%A in (".env") do set "%%A"
)
if "%MANGEDONG_PORT%"=="" set MANGEDONG_PORT=8000
if "%MANGEDONG_HOST%"=="" set MANGEDONG_HOST=0.0.0.0
if "%MANGEDONG_NO_VENV%"=="" (
  if not exist ".venv\Scripts\python.exe" python -m venv .venv
  call .venv\Scripts\activate.bat
)
if not "%MANGEDONG_SKIP_INSTALL%"=="1" python -m pip install -q -e .
if "%MANGEDONG_DATABASE_URL%"=="" set MANGEDONG_DATABASE_URL=sqlite:///./mangedong.db
if "%MANGEDONG_STORAGE_DIR%"=="" set MANGEDONG_STORAGE_DIR=./mangedong_storage
if "%MANGEDONG_SECRET_KEY%"=="" set MANGEDONG_SECRET_KEY=dev-secret-change-me
echo mangedong 工作台: http://127.0.0.1:%MANGEDONG_PORT%/app
python -m uvicorn "mangedong.api.app:create_app" --factory --host %MANGEDONG_HOST% --port %MANGEDONG_PORT%

@echo off
setlocal

@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment tapilmadi: .venv\Scripts\python.exe
  exit /b 1
)

if not exist "logs" mkdir "logs"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set "STAMP=%%i"
set "LOG_FILE=%CD%\logs\news-agent-%STAMP%.log"

echo [%date% %time%] News agent started
echo [%date% %time%] News agent started>> "%LOG_FILE%"

powershell -NoProfile -Command ^
  "& { " ^
  "  & '.\.venv\Scripts\python.exe' '-u' 'run.py' 2>&1 | Tee-Object -FilePath $env:LOG_FILE -Append; " ^
  "  exit $LASTEXITCODE " ^
  "}"
set "EXIT_CODE=%ERRORLEVEL%"

echo [%date% %time%] News agent finished with code %EXIT_CODE%
echo [%date% %time%] News agent finished with code %EXIT_CODE%>> "%LOG_FILE%"

exit /b %EXIT_CODE%
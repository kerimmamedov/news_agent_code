@echo off
setlocal

cd /d "%~dp0"
set "TASK_NAME_1=NewsAgent Morning Run"
set "TASK_NAME_2=NewsAgent Afternoon Run"
set "RUN_BAT=%~dp0run_news_agent.bat"

schtasks /Create /F /SC DAILY /ST 08:00 /TN "%TASK_NAME_1%" /TR "\"%RUN_BAT%\""
if errorlevel 1 (
  echo Seher task-i yaradilarken xeta bas verdi.
  exit /b 1
)

schtasks /Create /F /SC DAILY /ST 16:00 /TN "%TASK_NAME_2%" /TR "\"%RUN_BAT%\""
if errorlevel 1 (
  echo Gunorta task-i yaradilarken xeta bas verdi.
  exit /b 1
)

echo Task-lar ugurla yarandi:
echo - %TASK_NAME_1% ^(08:00^)
echo - %TASK_NAME_2% ^(16:00^)

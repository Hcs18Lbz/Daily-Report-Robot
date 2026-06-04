@echo off
cd /d E:\Clone_repository\Daily-Report-Robot
call .venv\Scripts\activate
if errorlevel 1 (
  echo Failed to activate virtual environment.
  pause
  exit /b 1
)
python -m src.webapp.app
if errorlevel 1 (
  echo Web app exited with error.
  pause
)

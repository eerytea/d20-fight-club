@echo off
REM Run Ruff (fix) then Black from your venv
IF NOT EXIST ".venv\Scripts\python.exe" (
  echo Please create and activate your virtual environment first: python -m venv .venv && .venv\Scripts\activate
  exit /b 1
)

".venv\Scripts\python.exe" -m pip install -q ruff black
".venv\Scripts\python.exe" -m ruff . --fix
".venv\Scripts\python.exe" -m black .
echo Formatting complete.

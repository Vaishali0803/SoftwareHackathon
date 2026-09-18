@echo off
echo Starting SH-405 Backend...
cd /d "%~dp0backend"

echo Installing/verifying dependencies...
python -m pip install -r requirements.txt --quiet

echo Generating demo dataset...
python generate_demo_data.py

echo.
echo Starting FastAPI server on http://localhost:8000
echo NOTE: Running without --reload to ensure background generation threads are stable.
echo       Restart manually after code changes.
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

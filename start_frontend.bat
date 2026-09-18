@echo off
echo Starting SH-405 Frontend...
cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo Installing npm dependencies...
    npm install
)

echo Starting Vite dev server on http://localhost:5173
npm run dev

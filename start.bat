@echo off
REM Start backend (Flask API)
start cmd /k "py -3.10 backend/app.py"

REM Start frontend (Vite)
cd frontend
start cmd /k "npm run dev"
cd ..
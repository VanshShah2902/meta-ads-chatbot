@echo off
echo ============================================
echo   Meta Ads Chatbot - Starting Services
echo ============================================
echo.

echo [1/2] Starting Backend (FastAPI on port 8000)...
cd backend
start "Meta Ads Backend" cmd /k "pip install -r requirements.txt && uvicorn main:app --reload --port 8000"
cd ..

echo [2/2] Starting Frontend (Next.js on port 3000)...
cd frontend
start "Meta Ads Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ============================================
echo   Backend: http://localhost:8000
echo   Frontend: http://localhost:3000
echo   API Docs: http://localhost:8000/docs
echo ============================================
echo.
echo Both services are starting in separate windows.
pause

@echo off
echo ============================================
echo   Meta Ads Chatbot - First Time Setup
echo ============================================
echo.

echo [1/4] Installing Python dependencies...
cd backend
pip install -r requirements.txt
cd ..

echo.
echo [2/4] Installing Node.js dependencies...
cd frontend
call npm install
cd ..

echo.
echo [3/4] Generating sample data...
cd sample_data
python generate_sample.py
cd ..

echo.
echo [4/4] Loading sample data into database...
cd backend
python -c "from database import init_db, ingest_csv; init_db(); [print(ingest_csv(f'../sample_data/{f}')) for f in ['campaigns_oct_2024.csv','campaigns_nov_2024.csv','adsets_oct_2024.csv','adsets_nov_2024.csv']]"
cd ..

echo.
echo ============================================
echo   Setup complete!
echo.
echo   NEXT STEPS:
echo   1. Get a free Groq API key from https://console.groq.com
echo   2. Copy backend\.env.example to backend\.env
echo   3. Add your GROQ_API_KEY to backend\.env
echo   4. Run start.bat to launch the app
echo ============================================
pause

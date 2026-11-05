@echo off
REM Usage:
REM   run.bat            start the app (seeds the DB first if it has no movies table)
REM   run.bat --reset    delete backend\movies.db, re-seed it from seed_db.py, then start
setlocal

REM Always run from the project root (the folder this script lives in)
cd /d "%~dp0"

REM 1. Virtual environment: create if missing, then activate
if not exist venv\Scripts\activate.bat (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install --quiet flask
) else (
    call venv\Scripts\activate.bat
)

REM 2. Install from requirements.txt if the project has one
if exist requirements.txt pip install --quiet -r requirements.txt

REM 3. Database: reset on request, otherwise seed only if the table is missing
if "%1"=="--reset" (
    echo Resetting database...
    if exist backend\movies.db del backend\movies.db
)

python -m backend.scripts.init_db
if errorlevel 1 exit /b 1

REM Seed movies only when the movies table is empty
for /f %%A in ('python -c "import sqlite3; c=sqlite3.connect('backend/movies.db'); print(c.execute('SELECT COUNT(*) FROM movies').fetchone()[0]); c.close()"') do set MOVIE_COUNT=%%A

if "%MOVIE_COUNT%"=="0" (
    echo Seeding initial movies...
    python -m backend.scripts.seed_db
    if errorlevel 1 exit /b 1
)

REM 4. Start the server
echo Starting app at http://127.0.0.1:5000
python -m backend.presentation.app
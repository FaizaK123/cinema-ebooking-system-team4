#!/usr/bin/env bash
# Usage:
#   ./run.sh            start the app (creates/updates the DB and seeds demo data first)
#   ./run.sh --reset    delete backend/movies.db, re-seed it from seed_db.py, then start
set -e

# Always run from the project root (the folder this script lives in)
cd "$(dirname "$0")"

# 1. Virtual environment: create if missing, then activate
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --quiet flask
else
    source venv/bin/activate
fi

# 2. Install from requirements.txt if the project has one
if [ -f "requirements.txt" ]; then
    pip install --quiet -r requirements.txt
fi

# 3. Database: initialize schema and seed if empty
if [ "$1" = "--reset" ]; then
    echo "Resetting database..."
    rm -f backend/movies.db
fi

# Create missing database tables
echo "Initializing database schema..."
python3 -m backend.scripts.init_db

# Seed movies, showtimes and pre-booked seats (safe to repeat: it only adds what is missing)
echo "Seeding demo data..."
python3 -m backend.scripts.seed_db

# 4. Start the server
echo "Starting app at http://127.0.0.1:5000"
python3 -m backend.presentation.app
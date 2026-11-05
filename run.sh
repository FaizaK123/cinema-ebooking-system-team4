#!/usr/bin/env bash
# Usage:
#   ./run.sh            start the app (seeds the DB first if it has no movies table)
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

# Seed movies only if the movies table is empty
if [ "$(python3 -c "import sqlite3; c=sqlite3.connect('backend/movies.db'); print(c.execute('SELECT COUNT(*) FROM movies').fetchone()[0]); c.close()")" = "0" ]; then
    echo "Seeding initial movies..."
    python3 -m backend.scripts.seed_db
fi

# 4. Start the server
echo "Starting app at http://127.0.0.1:5000"
python3 -m backend.presentation.app
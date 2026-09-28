#!/usr/bin/env bash
# Usage:
#   ./run.sh            start the app (seeds the DB first if it has no movies table)
#   ./run.sh --reset    delete backend/movies.db, re-seed it from dummy_db.py, then start
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

# 3. Database: reset on request, otherwise seed only if the table is missing
if [ "$1" = "--reset" ]; then
    echo "Resetting database..."
    rm -f backend/movies.db
fi

if ! python3 - <<'EOF'
import sqlite3, sys
try:
    conn = sqlite3.connect("backend/movies.db")
    conn.execute("SELECT 1 FROM movies LIMIT 1")
except sqlite3.OperationalError:
    sys.exit(1)
EOF
then
    echo "Seeding database from dummy_db.py..."
    (cd backend && python3 dummy_db.py)
fi

# 4. Start the server
echo "Starting app at http://127.0.0.1:5000"
python3 backend/app.py
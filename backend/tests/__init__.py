"""Sprint 3 test cases. Run from the project root:  python -m unittest discover -s backend/tests -t .

The tests use a throwaway database and never send real email, so they are safe to run any time.
This file runs before any test module imports the app, so the settings below take effect first.
"""
import os
import tempfile
from pathlib import Path

_TEST_DIR = Path(tempfile.mkdtemp(prefix="ces-tests-"))
os.environ["CES_DB_PATH"] = str(_TEST_DIR / "test.db")  # not backend/movies.db
os.environ["SMTP_HOST"] = ""                            # emails go to the outbox folder, never over the network

# cinema-ebooking-system-team4
Cinema E-Booking System for CSCI 4050/6050


## Running the app:
### On Windows:
- run run.bat

### On MacOS:
- run run.sh

Then open http://127.0.0.1:5000. Add `--reset` (e.g. `run.bat --reset`) to rebuild the database from scratch.

The scripts install the packages in `requirements.txt`, create or upgrade the database
(`backend/init_db.py` adds any missing tables/columns without deleting data), seed the movies, and start Flask.

## Email setup (needed for the demo)
Registration confirmation, password reset and profile-change notices are sent by email.

1. Copy `backend/.env.example` to `backend/.env`.
2. Fill in the Gmail account and App Password as described in that file.
3. Restart the app.

Without a `.env` file the app still works: each email is saved as a text file in
`backend/instance/outbox/` and printed in the terminal, so you can open the links from there.

## Accounts
- **Admin:** `admin@ces.local` / `Admin1234!` (created automatically; change it in `backend/.env` before the first run).
- **Customers:** register on the Sign Up page, then click the link in the confirmation email to activate the account.

## Project structure
| Layer | Location |
|---|---|
| Presentation | `frontend/` (HTML pages, `css/main.css`, `js/`) |
| Controllers (API routes) | `backend/routes/` (`movies.py`, `auth.py`, `profile.py`, `admin.py`) |
| Services | `backend/security.py` (hashing, encryption, access control), `email_service.py`, `validators.py` |
| Data access | `backend/repositories.py`, `backend/db.py`, `backend/schema.sql` |

## Security notes
- Passwords are hashed with scrypt (Werkzeug); they are never stored in plain text.
- Card numbers are encrypted (Fernet/AES) before storage; only the last 4 digits are shown. CVVs are never stored.
- Email-link tokens are random, single-use, expire (24 h confirm / 30 min reset) and are stored only as SHA-256 hashes.
- `backend/instance/` holds the session and card-encryption keys. It is git-ignored; don't delete `card.key`,
  or saved card numbers can no longer be decrypted.

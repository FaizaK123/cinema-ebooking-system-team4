# cinema-ebooking-system-team4
Cinema E-Booking System for CSCI 4050/6050


## Setup

### 1. Create the `.env` file
Registration confirmation, password reset and profile-change notices are sent by email,
so the app needs the team Gmail account's credentials. From the project root, run:

```
# Windows
copy backend\.env.example backend\.env

# macOS / Linux
cp backend/.env.example backend/.env
```

Then replace these fields in the new `backend/.env`:

```
SMTP_USERNAME=parkercant12345@gmail.com
SMTP_PASSWORD=<app password, shared privately - ask Anto>
MAIL_FROM=parkercant12345@gmail.com
```

`backend/.env` is git-ignored. Never commit it or paste the password anywhere public.

Without a `.env` file the app still works: each email is saved as a text file in
`backend/instance/outbox/` and printed in the terminal, so you can open the links from there.

### 2. Run the app
- **Windows:** run `run.bat`
- **macOS:** run `run.sh`

Then open http://127.0.0.1:5000. Add `--reset` (e.g. `run.bat --reset`) to rebuild the database from scratch.
If you change `backend/.env`, restart the app.

The scripts install the packages in `requirements.txt`, create or upgrade the database
(`backend/scripts/init_db.py` adds any missing tables/columns without deleting data), seed the movies, and start Flask.

## Accounts
- **Admin:** `admin@ces.local` / `Admin1234!` (created automatically; change it in `backend/.env` before the first run).
- **Customers:** register on the Sign Up page, then click the link in the confirmation email to activate the account.

## Project structure
| Layer | Location |
|---|---|
| Presentation | `frontend/pages/` (pages grouped under `public/`, `auth/`, `admin/`, `profile/`, and `errors/`); shared assets and components live in `frontend/css/`, `frontend/js/`, `frontend/images/`, and `frontend/components/`; `backend/presentation/` (Flask app, HTTP routes, response presenters) |
| Application | `backend/application/services/` (authentication, profile, movie catalog, and admin use cases) |
| Data access | `backend/data_access/` (repositories, SQLite connections/transactions, schema) |
| Infrastructure | `backend/infrastructure/` (configuration, security/session helpers, email, validation) |
| Operational scripts | `backend/scripts/` (database initialization, movie/user seeding, database inspection) |

For normal HTTP requests, the primary flow is presentation → application services →
data access. Routes translate HTTP requests and service results; application services
coordinate use cases; repositories contain the SQL for runtime features. Schema and
setup, seeding, and inspection SQL live in `backend/data_access/schema.sql` and
`backend/scripts/`.

Infrastructure is shared by presentation and application code. In particular,
`infrastructure/security.py` provides session/access-control helpers and currently loads
the signed-in user through data access, so dependencies are not strictly one-way.
`backend/routes/` contains older route modules and is not used by the current app, which
registers routes from `backend/presentation/routes/`. `backend/app.py` remains a
compatibility entry point; the launch scripts use `backend.presentation.app`.

## Security notes
- Passwords are hashed with scrypt (Werkzeug); they are never stored in plain text.
- Card numbers are encrypted (Fernet/AES) before storage; only the last 4 digits are shown. CVVs are never stored.
- Email-link tokens are random, single-use, expire (24 h confirm / 30 min reset) and are stored only as SHA-256 hashes.
- `backend/instance/` holds the session and card-encryption keys. It is git-ignored; don't delete `card.key`,
  or saved card numbers can no longer be decrypted.

# RailEase — Railway Reservation System

A full-stack prototype: **Flask + SQLite** backend with a REST JSON API,
**HTML/CSS/vanilla JS** frontend consuming that API via `fetch()`, session-cookie
auth with hashed passwords, and CRUD for both trains and bookings.

## Stack

- **Backend:** Python 3, Flask, raw `sqlite3` (no ORM, so the DB layer is easy to read)
- **Auth:** Flask session cookies + Werkzeug password hashing (no plaintext passwords, ever)
- **Frontend:** Server-rendered Jinja templates for page structure + vanilla JS/CSS for
  all interactivity (search, booking, CRUD) via the REST API — a clean separation between
  backend and frontend even though they're served from the same app
- **DB:** SQLite file (`railway.db`), 3 tables: `users`, `trains`, `bookings`

## Project structure

```
railway_reservation_system/
├── app.py                # Flask app: page routes + /api/* REST endpoints
├── db.py                 # SQLite connection handling, schema, seed data
├── requirements.txt
├── static/
│   ├── css/style.css      # theme + layout
│   ├── js/main.js         # shared fetch() wrapper + toast notifications
│   ├── js/auth.js         # login/register form logic
│   ├── js/dashboard.js    # search, booking, bookings CRUD, trains CRUD
│   └── images/train-logo.svg
└── templates/
    ├── base.html, index.html, login.html, register.html, dashboard.html
```

## Setup & run

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize the database (creates railway.db + seeds 8 demo trains)
flask --app app init-db

# 4. Run the dev server
flask --app app run --debug
# (or simply: python app.py — it auto-initializes the DB on first run)
```

Open **http://127.0.0.1:5000** in your browser. Register an account, then:
- **Search & Book** tab — filter trains by source/destination/date, book seats
- **My Bookings** tab — edit seat count/date or cancel a booking
- **Manage Trains** tab — add/edit/delete trains (demonstrates full CRUD)

## REST API reference

| Method | Endpoint              | Auth | Description                     |
|--------|------------------------|------|----------------------------------|
| POST   | `/api/register`        | –    | Create account, starts session   |
| POST   | `/api/login`           | –    | Log in, starts session           |
| POST   | `/api/logout`          | –    | Clear session                    |
| GET    | `/api/me`               | ✓    | Current user info                |
| GET    | `/api/trains`           | –    | List/search trains (`?source=&destination=&date=`) |
| GET    | `/api/trains/<id>`      | –    | Get one train                    |
| POST   | `/api/trains`           | ✓    | Create train                     |
| PUT    | `/api/trains/<id>`      | ✓    | Update train                     |
| DELETE | `/api/trains/<id>`      | ✓    | Delete train                     |
| GET    | `/api/bookings`         | ✓    | List current user's bookings     |
| GET    | `/api/bookings/<id>`    | ✓    | Get one booking                  |
| POST   | `/api/bookings`         | ✓    | Create booking (checks seat availability, returns PNR) |
| PUT    | `/api/bookings/<id>`    | ✓    | Change seats/date on a booking   |
| DELETE | `/api/bookings/<id>`    | ✓    | Cancel a booking (soft delete → `status = CANCELLED`)  |

All endpoints return JSON. Auth endpoints use a Flask session cookie (`credentials: "same-origin"` in the frontend's `fetch()` calls) — no separate token handling needed for this prototype.

## Design notes / shortcuts taken (intentional, for a prototype)

- **No admin role** — any logged-in user can add/edit/delete trains, to keep the demo
  self-contained. See "extend first" below.
- **Seat availability** is computed on the fly (`total_seats - SUM(confirmed bookings)` for
  a given date) rather than stored as a running counter, so it can never drift out of sync.
- **Cancellation is soft** — cancelled bookings stay in the table with `status = CANCELLED`
  instead of being deleted, so seats free up automatically without losing history.
- **Passwords** are hashed with Werkzeug's `generate_password_hash` (PBKDF2) — never stored
  or logged in plaintext.

## What I'd extend first

1. **Real admin role** — add a `role` column to `users`, gate `/api/trains` POST/PUT/DELETE
   behind `role == 'admin'` instead of "any logged-in user."
2. **Payments** — hook `POST /api/bookings` up to a mock/real payment step before marking
   `CONFIRMED`, with a `PENDING` intermediate status.
3. **Email confirmation** — send the PNR by email on booking (Flask-Mail or a background task).
4. **Pagination & indexes** — add `LIMIT/OFFSET` to `/api/trains` and `/api/bookings`, and a
   DB index on `bookings(train_id, journey_date)` once the seed data grows past a demo size.
5. **Tests** — the route logic is intentionally simple/flat, which makes it easy to wrap in
   `pytest` + Flask's test client for the auth flow and the seat-availability edge cases.
6. **Swap SQLite → Postgres** — the `db.py` module isolates all connection logic, so this is
   mostly a matter of swapping the driver and adjusting `PRAGMA`/autoincrement syntax.

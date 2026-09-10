"""
db.py
-----
All raw SQLite database plumbing lives here: connection handling
(request-scoped, via Flask's `g`), schema creation, and seed data.
Kept separate from app.py so the API/route layer stays clean.
"""

import sqlite3
import os
from flask import g

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "railway.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trains (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    train_number    TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    source          TEXT NOT NULL,
    destination     TEXT NOT NULL,
    departure_time  TEXT NOT NULL,
    arrival_time    TEXT NOT NULL,
    total_seats     INTEGER NOT NULL,
    fare            REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    pnr           TEXT UNIQUE NOT NULL,
    user_id       INTEGER NOT NULL,
    train_id      INTEGER NOT NULL,
    journey_date  TEXT NOT NULL,
    seats         INTEGER NOT NULL,
    total_fare    REAL NOT NULL,
    status        TEXT NOT NULL DEFAULT 'CONFIRMED',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)  REFERENCES users  (id) ON DELETE CASCADE,
    FOREIGN KEY (train_id) REFERENCES trains (id) ON DELETE CASCADE
);
"""

SEED_TRAINS = [
    ("12951", "Rajdhani Express", "Mumbai", "Delhi", "16:35", "08:35", 120, 1850.00),
    ("12301", "Howrah Rajdhani", "Kolkata", "Delhi", "16:50", "10:05", 120, 1990.00),
    ("12259", "Sealdah Duronto", "Sealdah", "New Delhi", "20:00", "17:20", 100, 2100.00),
    ("12622", "Tamil Nadu Express", "Chennai", "Delhi", "22:30", "06:40", 150, 1720.00),
    ("12002", "Shatabdi Express", "Delhi", "Bhopal", "06:00", "14:05", 90, 990.00),
    ("12628", "Karnataka Express", "Bangalore", "Delhi", "19:20", "05:30", 130, 1650.00),
    ("12839", "Howrah Chennai Mail", "Howrah", "Chennai", "23:45", "05:30", 140, 1550.00),
    ("12903", "Golden Temple Mail", "Mumbai", "Amritsar", "21:40", "05:10", 110, 1480.00),
]


def get_db():
    """Return a request-scoped SQLite connection (creates one if needed)."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    """Close the request-scoped connection. Registered as a teardown hook."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app=None):
    """Create tables (if they don't exist yet) and seed demo trains."""
    db = sqlite3.connect(DATABASE)
    db.executescript(SCHEMA)

    count = db.execute("SELECT COUNT(*) FROM trains").fetchone()[0]
    if count == 0:
        db.executemany(
            """INSERT INTO trains
               (train_number, name, source, destination, departure_time,
                arrival_time, total_seats, fare)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            SEED_TRAINS,
        )
    db.commit()
    db.close()


def init_app(app):
    """Register DB lifecycle hooks + `flask init-db` CLI command on the app."""
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        """Flask CLI: `flask --app app init-db`"""
        init_db(app)
        print("Initialized the database.")

"""
app.py
------
Railway Reservation System — Flask backend.

Serves:
  * Server-rendered pages (Jinja templates) for index/login/register/dashboard
  * A JSON REST API under /api/* consumed by static/js via fetch()
  * Session-cookie based auth (werkzeug password hashing, no plaintext ever stored)

Run:
    pip install -r requirements.txt
    flask --app app init-db      # one-time: creates railway.db + seed trains
    flask --app app run --debug
"""

import os
import random
import string
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, g
from werkzeug.security import generate_password_hash, check_password_hash

import db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
db.init_app(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login_required(view):
    """Decorator for API endpoints that require an authenticated session."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_id") is None:
            return jsonify({"error": "Authentication required"}), 401
        return view(*args, **kwargs)
    return wrapped


def generate_pnr():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=10))


def row_to_dict(row):
    return dict(row) if row is not None else None


def seats_booked(conn, train_id, journey_date):
    """Sum of seats already CONFIRMED for a given train + date."""
    result = conn.execute(
        """SELECT COALESCE(SUM(seats), 0) AS n FROM bookings
           WHERE train_id = ? AND journey_date = ? AND status = 'CONFIRMED'""",
        (train_id, journey_date),
    ).fetchone()
    return result["n"]


# ---------------------------------------------------------------------------
# Page routes (server-rendered HTML)
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", logged_in="user_id" in session)


@app.route("/login")
def login_page():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/register")
def register_page():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    return render_template("dashboard.html", full_name=session.get("full_name"))


@app.route("/logout")
def logout_page():
    session.clear()
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# REST API — Auth
# ---------------------------------------------------------------------------

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not full_name or not email or not password:
        return jsonify({"error": "full_name, email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    conn = db.get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        return jsonify({"error": "An account with this email already exists"}), 409

    password_hash = generate_password_hash(password)
    cur = conn.execute(
        "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
        (full_name, email, password_hash),
    )
    conn.commit()

    session["user_id"] = cur.lastrowid
    session["full_name"] = full_name
    return jsonify({"id": cur.lastrowid, "full_name": full_name, "email": email}), 201


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    conn = db.get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"] = user["id"]
    session["full_name"] = user["full_name"]
    return jsonify({"id": user["id"], "full_name": user["full_name"], "email": user["email"]})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@app.route("/api/me", methods=["GET"])
def api_me():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    conn = db.get_db()
    user = conn.execute(
        "SELECT id, full_name, email, created_at FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    return jsonify(row_to_dict(user))


# ---------------------------------------------------------------------------
# REST API — Trains (CRUD)
# ---------------------------------------------------------------------------

@app.route("/api/trains", methods=["GET"])
def api_list_trains():
    """List trains, optionally filtered by source / destination / journey_date."""
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip()
    journey_date = request.args.get("date", "").strip()

    query = "SELECT * FROM trains WHERE 1=1"
    params = []
    if source:
        query += " AND source LIKE ?"
        params.append(f"%{source}%")
    if destination:
        query += " AND destination LIKE ?"
        params.append(f"%{destination}%")
    query += " ORDER BY departure_time"

    conn = db.get_db()
    trains = conn.execute(query, params).fetchall()

    results = []
    for t in trains:
        t = dict(t)
        booked = seats_booked(conn, t["id"], journey_date) if journey_date else 0
        t["available_seats"] = t["total_seats"] - booked
        results.append(t)
    return jsonify(results)


@app.route("/api/trains/<int:train_id>", methods=["GET"])
def api_get_train(train_id):
    conn = db.get_db()
    train = conn.execute("SELECT * FROM trains WHERE id = ?", (train_id,)).fetchone()
    if train is None:
        return jsonify({"error": "Train not found"}), 404
    return jsonify(row_to_dict(train))


@app.route("/api/trains", methods=["POST"])
@login_required
def api_create_train():
    """Create a train. In this prototype any logged-in user may add trains —
    see README 'What to extend first' for adding a real admin role."""
    data = request.get_json(silent=True) or {}
    required = ["train_number", "name", "source", "destination",
                "departure_time", "arrival_time", "total_seats", "fare"]
    missing = [f for f in required if not data.get(f) and data.get(f) != 0]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    conn = db.get_db()
    try:
        cur = conn.execute(
            """INSERT INTO trains
               (train_number, name, source, destination, departure_time,
                arrival_time, total_seats, fare)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (data["train_number"], data["name"], data["source"], data["destination"],
             data["departure_time"], data["arrival_time"],
             int(data["total_seats"]), float(data["fare"])),
        )
        conn.commit()
    except db.sqlite3.IntegrityError:
        return jsonify({"error": "A train with this train_number already exists"}), 409

    return jsonify({"id": cur.lastrowid, **data}), 201


@app.route("/api/trains/<int:train_id>", methods=["PUT"])
@login_required
def api_update_train(train_id):
    conn = db.get_db()
    train = conn.execute("SELECT * FROM trains WHERE id = ?", (train_id,)).fetchone()
    if train is None:
        return jsonify({"error": "Train not found"}), 404

    data = request.get_json(silent=True) or {}
    fields = ["train_number", "name", "source", "destination",
              "departure_time", "arrival_time", "total_seats", "fare"]
    updated = {f: data.get(f, train[f]) for f in fields}

    conn.execute(
        """UPDATE trains SET train_number=?, name=?, source=?, destination=?,
           departure_time=?, arrival_time=?, total_seats=?, fare=? WHERE id=?""",
        (updated["train_number"], updated["name"], updated["source"], updated["destination"],
         updated["departure_time"], updated["arrival_time"],
         int(updated["total_seats"]), float(updated["fare"]), train_id),
    )
    conn.commit()
    return jsonify({"id": train_id, **updated})


@app.route("/api/trains/<int:train_id>", methods=["DELETE"])
@login_required
def api_delete_train(train_id):
    conn = db.get_db()
    train = conn.execute("SELECT id FROM trains WHERE id = ?", (train_id,)).fetchone()
    if train is None:
        return jsonify({"error": "Train not found"}), 404
    conn.execute("DELETE FROM trains WHERE id = ?", (train_id,))
    conn.commit()
    return jsonify({"message": "Train deleted"})


# ---------------------------------------------------------------------------
# REST API — Bookings (CRUD, scoped to the logged-in user)
# ---------------------------------------------------------------------------

@app.route("/api/bookings", methods=["GET"])
@login_required
def api_list_bookings():
    conn = db.get_db()
    rows = conn.execute(
        """SELECT b.*, t.name AS train_name, t.train_number, t.source, t.destination,
                  t.departure_time, t.arrival_time
           FROM bookings b JOIN trains t ON b.train_id = t.id
           WHERE b.user_id = ?
           ORDER BY b.created_at DESC""",
        (session["user_id"],),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/bookings/<int:booking_id>", methods=["GET"])
@login_required
def api_get_booking(booking_id):
    conn = db.get_db()
    row = conn.execute(
        """SELECT b.*, t.name AS train_name, t.train_number, t.source, t.destination
           FROM bookings b JOIN trains t ON b.train_id = t.id
           WHERE b.id = ? AND b.user_id = ?""",
        (booking_id, session["user_id"]),
    ).fetchone()
    if row is None:
        return jsonify({"error": "Booking not found"}), 404
    return jsonify(dict(row))


@app.route("/api/bookings", methods=["POST"])
@login_required
def api_create_booking():
    data = request.get_json(silent=True) or {}
    train_id = data.get("train_id")
    journey_date = (data.get("journey_date") or "").strip()
    seats = data.get("seats")

    if not train_id or not journey_date or not seats:
        return jsonify({"error": "train_id, journey_date and seats are required"}), 400
    try:
        seats = int(seats)
        datetime.strptime(journey_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return jsonify({"error": "seats must be an integer and journey_date must be YYYY-MM-DD"}), 400
    if seats < 1:
        return jsonify({"error": "seats must be at least 1"}), 400

    conn = db.get_db()
    train = conn.execute("SELECT * FROM trains WHERE id = ?", (train_id,)).fetchone()
    if train is None:
        return jsonify({"error": "Train not found"}), 404

    available = train["total_seats"] - seats_booked(conn, train_id, journey_date)
    if seats > available:
        return jsonify({"error": f"Only {available} seat(s) available on this date"}), 409

    pnr = generate_pnr()
    total_fare = round(train["fare"] * seats, 2)
    cur = conn.execute(
        """INSERT INTO bookings (pnr, user_id, train_id, journey_date, seats, total_fare, status)
           VALUES (?, ?, ?, ?, ?, ?, 'CONFIRMED')""",
        (pnr, session["user_id"], train_id, journey_date, seats, total_fare),
    )
    conn.commit()

    return jsonify({
        "id": cur.lastrowid, "pnr": pnr, "train_id": train_id, "journey_date": journey_date,
        "seats": seats, "total_fare": total_fare, "status": "CONFIRMED",
    }), 201


@app.route("/api/bookings/<int:booking_id>", methods=["PUT"])
@login_required
def api_update_booking(booking_id):
    """Update seat count / journey date on an existing CONFIRMED booking."""
    conn = db.get_db()
    booking = conn.execute(
        "SELECT * FROM bookings WHERE id = ? AND user_id = ?",
        (booking_id, session["user_id"]),
    ).fetchone()
    if booking is None:
        return jsonify({"error": "Booking not found"}), 404
    if booking["status"] != "CONFIRMED":
        return jsonify({"error": "Only confirmed bookings can be modified"}), 400

    data = request.get_json(silent=True) or {}
    new_seats = int(data.get("seats", booking["seats"]))
    new_date = (data.get("journey_date") or booking["journey_date"]).strip()

    train = conn.execute("SELECT * FROM trains WHERE id = ?", (booking["train_id"],)).fetchone()
    already_booked_by_others = seats_booked(conn, booking["train_id"], new_date)
    if new_date == booking["journey_date"]:
        already_booked_by_others -= booking["seats"]
    available = train["total_seats"] - already_booked_by_others
    if new_seats > available:
        return jsonify({"error": f"Only {available} seat(s) available on this date"}), 409

    total_fare = round(train["fare"] * new_seats, 2)
    conn.execute(
        "UPDATE bookings SET seats=?, journey_date=?, total_fare=? WHERE id=?",
        (new_seats, new_date, total_fare, booking_id),
    )
    conn.commit()
    return jsonify({"id": booking_id, "seats": new_seats, "journey_date": new_date, "total_fare": total_fare})


@app.route("/api/bookings/<int:booking_id>", methods=["DELETE"])
@login_required
def api_cancel_booking(booking_id):
    conn = db.get_db()
    booking = conn.execute(
        "SELECT * FROM bookings WHERE id = ? AND user_id = ?",
        (booking_id, session["user_id"]),
    ).fetchone()
    if booking is None:
        return jsonify({"error": "Booking not found"}), 404

    conn.execute("UPDATE bookings SET status = 'CANCELLED' WHERE id = ?", (booking_id,))
    conn.commit()
    return jsonify({"message": "Booking cancelled", "id": booking_id})


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Convenience: auto-create the DB on first run of `python app.py`
    if not os.path.exists(db.DATABASE):
        db.init_db(app)
        print("Database initialized with seed trains.")
    app.run(debug=True)

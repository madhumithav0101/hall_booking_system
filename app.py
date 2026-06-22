import os
import sqlite3
from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "meeting-booking-secret-2024")

# On Vercel the only writable directory is /tmp
DB_PATH = os.path.join("/tmp", "bookings.db")

ADMIN_EMAIL = "admin123@gmail.com"
ADMIN_PASSWORD = "123"

HALLS = {
    "Hall A": {
        "capacity": "20 seats",
        "features": "Projector, whiteboard, video call setup"
    },
    "Hall B": {
        "capacity": "50 seats",
        "features": "Large screen, sound system, podium"
    },
    "Hall C": {
        "capacity": "12 seats",
        "features": "Private room, TV display, whiteboard"
    }
}

SLOTS = [
    "09:00 AM - 10:00 AM",
    "10:00 AM - 11:00 AM",
    "11:00 AM - 12:00 PM",
    "02:00 PM - 03:00 PM",
    "03:00 PM - 04:00 PM",
    "04:00 PM - 05:00 PM"
]


def get_db():
    """Open a new DB connection for the current request context."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    """Close DB connection at end of request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the bookings table if it does not exist."""
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            hall    TEXT NOT NULL,
            booking_date TEXT NOT NULL,
            slot    TEXT NOT NULL,
            name    TEXT NOT NULL DEFAULT '',
            email   TEXT NOT NULL DEFAULT '',
            phone   TEXT NOT NULL DEFAULT '',
            purpose TEXT NOT NULL DEFAULT ''
        )
    """)
    db.commit()


@app.before_request
def ensure_db():
    """Initialise DB schema before every request."""
    init_db()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    selected_date = request.args.get('date', '')
    selected_hall = request.args.get('hall', '')

    db = get_db()
    query = """
        SELECT id, hall, booking_date, slot, name, email, phone, purpose
        FROM bookings
    """
    conditions = []
    params = []

    if selected_date:
        conditions.append("booking_date = ?")
        params.append(selected_date)
    if selected_hall:
        conditions.append("hall = ?")
        params.append(selected_hall)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY booking_date DESC, hall ASC, slot ASC"
    rows = db.execute(query, params).fetchall()

    bookings = [dict(row) for row in rows]

    return render_template(
        'index.html',
        halls=HALLS,
        slots=SLOTS,
        bookings=bookings,
        selected_date=selected_date,
        selected_hall=selected_hall
    )


@app.route('/booking')
def booking_page():
    return redirect(url_for('home'))


@app.route('/availability-page')
def availability_page():
    return redirect(url_for('home'))


@app.route('/booked-slots')
def booked_slots():
    return redirect(url_for('home'))


@app.route('/cancel-page')
def cancel_page():
    return redirect(url_for('home'))


@app.route('/book', methods=['POST'])
def book():
    hall         = request.form['hall']
    booking_date = request.form['booking_date']
    slot         = request.form['slot']
    name         = request.form['name'].strip()
    email        = request.form['email'].strip()
    phone        = request.form['phone'].strip()
    purpose      = request.form['purpose'].strip()

    db = get_db()

    existing = db.execute(
        "SELECT id FROM bookings WHERE hall=? AND booking_date=? AND slot=?",
        (hall, booking_date, slot)
    ).fetchone()

    if existing:
        flash("Already booked. Please select another slot.", "error")
        return redirect(url_for('home'))

    cursor = db.execute(
        """
        INSERT INTO bookings (hall, booking_date, slot, name, email, phone, purpose)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (hall, booking_date, slot, name, email, phone, purpose)
    )
    db.commit()

    flash(f"Booking successful. Your booking ID is {cursor.lastrowid}.", "success")
    return redirect(url_for('home', date=booking_date, hall=hall))


@app.route('/availability')
def availability():
    booking_date = request.args.get('date')
    hall         = request.args.get('hall')

    if not booking_date or not hall:
        return jsonify({"booked": [], "available": SLOTS})

    db = get_db()
    rows = db.execute(
        "SELECT slot FROM bookings WHERE hall=? AND booking_date=?",
        (hall, booking_date)
    ).fetchall()

    booked    = [row["slot"] for row in rows]
    available = [s for s in SLOTS if s not in booked]

    return jsonify({"booked": booked, "available": available})


@app.route('/cancel', methods=['POST'])
def cancel_booking():
    booking_id = request.form['booking_id']
    phone      = request.form['phone'].strip()

    db = get_db()
    cursor = db.execute(
        "DELETE FROM bookings WHERE id=? AND phone=?",
        (booking_id, phone)
    )
    db.commit()

    if cursor.rowcount:
        flash("Booking cancelled successfully.", "success")
    else:
        flash("Booking not found. Check booking ID and phone number.", "error")

    return redirect(url_for('home'))


@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    selected_date = request.args.get('date', '')
    selected_hall = request.args.get('hall', '')

    db = get_db()
    query = """
        SELECT id, hall, booking_date, slot, name, email, phone, purpose
        FROM bookings
    """
    conditions = []
    params = []

    if selected_date:
        conditions.append("booking_date = ?")
        params.append(selected_date)
    if selected_hall:
        conditions.append("hall = ?")
        params.append(selected_hall)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY booking_date DESC, hall ASC, slot ASC"
    rows = db.execute(query, params).fetchall()
    bookings = [dict(row) for row in rows]

    return render_template(
        'admin.html',
        halls=HALLS,
        bookings=bookings,
        selected_date=selected_date,
        selected_hall=selected_hall
    )


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email    = request.form['email'].strip()
        password = request.form['password'].strip()

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash("Admin login successful.", "success")
            return redirect(url_for('admin'))

        flash("Invalid admin mail id or password.", "error")

    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash("Admin logged out.", "success")
    return redirect(url_for('home'))


@app.route('/admin/delete/<int:booking_id>', methods=['POST'])
def admin_delete(booking_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    db = get_db()
    db.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
    db.commit()
    flash("Booking deleted from admin panel.", "success")
    return redirect(url_for('admin'))


if __name__ == '__main__':
    app.run(debug=True)

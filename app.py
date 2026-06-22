from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
import mysql.connector

app = Flask(__name__)
app.secret_key = "meeting-booking-secret"

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

try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Madhu*@17V",
        database="meetingdbs2"
    )
    cursor = db.cursor()

except Exception as e:
    print("Database connection failed:", e)
    db = None
    cursor = None

cursor = db.cursor()

if cursor:
    ensure_booking_columns()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hall VARCHAR(50) NOT NULL,
            booking_date DATE NOT NULL,
            slot VARCHAR(50) NOT NULL,
            name VARCHAR(100) NOT NULL DEFAULT '',
            email VARCHAR(120) NOT NULL DEFAULT '',
            phone VARCHAR(20) NOT NULL DEFAULT '',
            purpose VARCHAR(255) NOT NULL DEFAULT ''
        )
    """)

    required_columns = {
        "id": "INT AUTO_INCREMENT PRIMARY KEY FIRST",
        "name": "VARCHAR(100) NOT NULL DEFAULT ''",
        "email": "VARCHAR(120) NOT NULL DEFAULT ''",
        "phone": "VARCHAR(20) NOT NULL DEFAULT ''",
        "purpose": "VARCHAR(255) NOT NULL DEFAULT ''"
    }

    cursor.execute("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'bookings'
    """)
    existing_columns = {row[0] for row in cursor.fetchall()}

    for column, definition in required_columns.items():
        if column not in existing_columns:
            cursor.execute(f"ALTER TABLE bookings ADD COLUMN {column} {definition}")

    db.commit()

def get_bookings(booking_date=None, hall=None):
    query = "SELECT id, hall, booking_date, slot, name, email, phone, purpose FROM bookings"
    conditions = []
    params = []

    if booking_date:
        conditions.append("booking_date=%s")
        params.append(booking_date)

    if hall:
        conditions.append("hall=%s")
        params.append(hall)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY booking_date DESC, hall ASC, slot ASC"
    cursor.execute(query, tuple(params))

    bookings = []
    for row in cursor.fetchall():
        bookings.append({
            "id": row[0],
            "hall": row[1],
            "booking_date": row[2],
            "slot": row[3],
            "name": row[4],
            "email": row[5],
            "phone": row[6],
            "purpose": row[7]
        })

    return bookings

ensure_booking_columns()

@app.route('/')
def home():
    selected_date = request.args.get('date', '')
    selected_hall = request.args.get('hall', '')
    bookings = get_bookings(selected_date or None, selected_hall or None)

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
    hall = request.form['hall']
    booking_date = request.form['booking_date']
    slot = request.form['slot']
    name = request.form['name'].strip()
    email = request.form['email'].strip()
    phone = request.form['phone'].strip()
    purpose = request.form['purpose'].strip()

    cursor.execute(
        "SELECT * FROM bookings WHERE hall=%s AND booking_date=%s AND slot=%s",
        (hall, booking_date, slot)
    )

    existing = cursor.fetchone()

    if existing:
        flash("Already booked. Please select another slot.", "error")
        return redirect(url_for('home'))

    cursor.execute(
        """
        INSERT INTO bookings(hall, booking_date, slot, name, email, phone, purpose)
        VALUES(%s,%s,%s,%s,%s,%s,%s)
        """,
        (hall, booking_date, slot, name, email, phone, purpose)
    )
    

    db.commit()

    flash(f"Booking successful. Your booking ID is {cursor.lastrowid}.", "success")
    return redirect(url_for('home', date=booking_date, hall=hall))

@app.route('/availability')
def availability():
    booking_date = request.args.get('date')
    hall = request.args.get('hall')

    if not booking_date or not hall:
        return jsonify({"booked": [], "available": SLOTS})

    cursor.execute(
        "SELECT slot FROM bookings WHERE hall=%s AND booking_date=%s",
        (hall, booking_date)
    )
    booked = [row[0] for row in cursor.fetchall()]
    available = [slot for slot in SLOTS if slot not in booked]

    return jsonify({"booked": booked, "available": available})

@app.route('/cancel', methods=['POST'])
def cancel_booking():
    booking_id = request.form['booking_id']
    phone = request.form['phone'].strip()

    cursor.execute(
        "DELETE FROM bookings WHERE id=%s AND phone=%s",
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
    bookings = get_bookings(selected_date or None, selected_hall or None)

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
        email = request.form['email'].strip()
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

    cursor.execute("DELETE FROM bookings WHERE id=%s", (booking_id,))
    db.commit()
    flash("Booking deleted from admin panel.", "success")
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)

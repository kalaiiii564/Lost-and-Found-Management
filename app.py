import os
import sqlite3
import time
import smtplib
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "sies_campus_lost_found_secret_key"

# ==================================================
# EMAIL CONFIGURATION
# ==================================================
# For Gmail: use your Gmail address + an APP PASSWORD
# Get App Password: https://myaccount.google.com/apppasswords
SENDER_EMAIL = "your-email@gmail.com"        # <-- CHANGE THIS
SENDER_PASSWORD = "your-16-char-app-pass"    # <-- CHANGE THIS (no spaces)

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db():
    conn = sqlite3.connect("lostnfound.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            roll_number TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            colour TEXT NOT NULL,
            brand TEXT,
            building TEXT NOT NULL,
            floor TEXT NOT NULL,
            classroom TEXT NOT NULL,
            location_description TEXT,
            date_event TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'approved',
            image_filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    if not c.execute("SELECT id FROM users WHERE email = 'admin@sies.edu'").fetchone():
        c.execute("INSERT INTO users (full_name, roll_number, email, password, is_admin) VALUES ('Admin Administrator', 'ADMIN001', 'admin@sies.edu', 'admin123', 1)")
    if not c.execute("SELECT id FROM users WHERE email = 'student@sies.edu'").fetchone():
        c.execute("INSERT INTO users (full_name, roll_number, email, password, is_admin) VALUES ('Rahul Sharma', '21IT105', 'student@sies.edu', 'student123', 0)")
    conn.commit()
    conn.close()


def save_uploaded_file():
    if "image" in request.files:
        file = request.files["image"]
        if file and file.filename != "":
            ext = file.filename.rsplit(".", 1)[-1].lower()
            if ext in ["jpg", "jpeg", "png", "webp", "gif"]:
                filename = f"img_{int(time.time())}.{ext}"
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                return filename
    return None


# ==================================================
# SIMPLE EMAIL FUNCTION
# ==================================================
def send_email(to_email, subject, body):
    """Send a plain-text email using Gmail SMTP. Returns True on success."""
    try:
        message = f"Subject: {subject}\n\n{body}"
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, message)
        server.quit()
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


# ---------- PUBLIC ROUTES ----------
@app.route("/")
@app.route("/index.html")
def index():
    filter_type = request.args.get("type", "all")
    search_query = request.args.get("q", "").strip().lower()
    db = get_db()
    if filter_type in ["lost", "found"]:
        reports = db.execute('''SELECT r.*, u.full_name, u.email, u.roll_number 
            FROM reports r JOIN users u ON r.user_id = u.id
            WHERE r.status = 'approved' AND r.type = ? ORDER BY r.created_at DESC''', (filter_type,)).fetchall()
    else:
        reports = db.execute('''SELECT r.*, u.full_name, u.email, u.roll_number 
            FROM reports r JOIN users u ON r.user_id = u.id
            WHERE r.status = 'approved' ORDER BY r.created_at DESC''').fetchall()
    db.close()
    if search_query:
        reports = [r for r in reports if search_query in r["item_name"].lower()
                   or search_query in r["building"].lower()
                   or search_query in r["classroom"].lower()]
    return render_template("index.html", reports=reports, current_filter=filter_type, search_query=search_query)


@app.route("/login", methods=["GET", "POST"])
@app.route("/login.html", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("admin_dashboard" if session.get("is_admin") else "dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        db.close()
        if user and user["password"] == password:
            session["user_id"] = user["id"]
            session["full_name"] = user["full_name"]
            session["email"] = user["email"]
            session["is_admin"] = bool(user["is_admin"])
            flash(f"Welcome back, {user['full_name']}!", "success")
            if user["is_admin"]:
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password!", "error")
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
@app.route("/signup.html", methods=["GET", "POST"])
def signup():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        roll_number = request.form.get("roll_number", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return render_template("signup.html")
        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            db.close()
            flash("Email already registered!", "error")
            return render_template("signup.html")
        cursor = db.cursor()
        cursor.execute('''INSERT INTO users (full_name, roll_number, email, password, is_admin)
            VALUES (?, ?, ?, ?, 0)''', (full_name, roll_number, email, password))
        user_id = cursor.lastrowid
        db.commit()
        db.close()
        session["user_id"] = user_id
        session["full_name"] = full_name
        session["email"] = email
        session["is_admin"] = False
        flash("Account created successfully!", "success")
        return redirect(url_for("dashboard"))
    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("index"))


# ---------- DASHBOARD ----------
@app.route("/dashboard")
@app.route("/dashboard.html")
def dashboard():
    if "user_id" not in session:
        flash("Please login to view dashboard!", "error")
        return redirect(url_for("login"))
    filter_type = request.args.get("type", "all")
    search_query = request.args.get("q", "").strip().lower()
    db = get_db()
    if filter_type in ["lost", "found"]:
        reports = db.execute('''SELECT r.*, u.full_name, u.email, u.roll_number 
            FROM reports r JOIN users u ON r.user_id = u.id
            WHERE r.status = 'approved' AND r.type = ? ORDER BY r.created_at DESC''', (filter_type,)).fetchall()
    else:
        reports = db.execute('''SELECT r.*, u.full_name, u.email, u.roll_number 
            FROM reports r JOIN users u ON r.user_id = u.id
            WHERE r.status = 'approved' ORDER BY r.created_at DESC''').fetchall()
    db.close()
    if search_query:
        reports = [r for r in reports if search_query in r["item_name"].lower()
                   or search_query in r["building"].lower()
                   or search_query in r["classroom"].lower()]
    return render_template("dashboard.html", reports=reports, current_filter=filter_type, search_query=search_query)


@app.route("/item/<int:report_id>")
def item_detail(report_id):
    db = get_db()
    item = db.execute('''SELECT r.*, u.full_name, u.email, u.roll_number 
        FROM reports r JOIN users u ON r.user_id = u.id
        WHERE r.id = ?''', (report_id,)).fetchone()
    db.close()
    if not item:
        flash("Item not found!", "error")
        return redirect(url_for("index"))
    return render_template("item_detail.html", item=item)


# ==================================================
# NOTIFY OWNER (SEND EMAIL WHEN LOST ITEM IS FOUND)
# ==================================================
@app.route("/item/<int:report_id>/notify-owner", methods=["POST"])
def notify_owner(report_id):
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))

    db = get_db()
    item = db.execute('''SELECT r.*, u.full_name, u.email, u.roll_number
        FROM reports r JOIN users u ON r.user_id = u.id
        WHERE r.id = ?''', (report_id,)).fetchone()
    db.close()

    if not item:
        flash("Item not found!", "error")
        return redirect(url_for("dashboard"))

    subject = f"Good News! Your lost '{item['item_name']}' may have been found"
    body = f"""Hello {item['full_name']},

Good news! Someone has indicated that they may have found your lost item on campus.

ITEM DETAILS:
- Item Name : {item['item_name']}
- Category  : {item['category']}
- Colour    : {item['colour']}
- Brand     : {item['brand'] if item['brand'] else 'Not specified'}
- Building  : {item['building']}
- Floor     : {item['floor']}
- Classroom : {item['classroom']}
- Date Lost : {item['date_event']}
- Description: {item['description']}

Please login to the SIES Campus Lost & Found Portal to view full details.

Regards,
SIES College Lost & Found System
"""

    success = send_email(item["email"], subject, body)

    if success:
        flash(f"✅ Email sent to {item['full_name']} ({item['email']}) successfully!", "success")
    else:
        flash("❌ Could not send email. Please check the email settings in app.py.", "error")

    return redirect(url_for("item_detail", report_id=report_id))


@app.route("/report-lost", methods=["GET", "POST"])
@app.route("/report_lost.html", methods=["GET", "POST"])
def report_lost():
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    if request.method == "POST":
        return save_new_report(report_type="lost")
    return render_template("report_lost.html")


@app.route("/report-found", methods=["GET", "POST"])
@app.route("/report_found.html", methods=["GET", "POST"])
def report_found():
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    if request.method == "POST":
        return save_new_report(report_type="found")
    return render_template("report_found.html")


def save_new_report(report_type):
    item_name = request.form.get("item_name", "").strip()
    category = request.form.get("category", "").strip()
    colour = request.form.get("colour", "").strip()
    brand = request.form.get("brand", "").strip()
    building = request.form.get("building", "").strip()
    floor = request.form.get("floor", "").strip()
    classroom = request.form.get("classroom", "").strip()
    location_description = request.form.get("location_description", "").strip()
    date_event = request.form.get("date_event", "").strip()
    description = request.form.get("description", "").strip()
    image_filename = save_uploaded_file()
    db = get_db()
    db.execute('''INSERT INTO reports (user_id, type, item_name, category, colour, brand,
        building, floor, classroom, location_description, date_event, description, image_filename, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved')''',
        (session["user_id"], report_type, item_name, category, colour, brand,
         building, floor, classroom, location_description, date_event, description, image_filename))
    db.commit()
    db.close()
    flash(f"Your {report_type.upper()} report for '{item_name}' has been posted!", "success")
    return redirect(url_for("dashboard"))


@app.route("/my-reports")
@app.route("/my_reports.html")
def my_reports():
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    db = get_db()
    reports = db.execute("SELECT * FROM reports WHERE user_id = ? ORDER BY created_at DESC", (session["user_id"],)).fetchall()
    db.close()
    return render_template("my_reports.html", reports=reports)


@app.route("/report/<int:report_id>/resolve", methods=["POST"])
def resolve_report(report_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    db.execute("UPDATE reports SET status = 'resolved' WHERE id = ? AND user_id = ?", (report_id, session["user_id"]))
    db.commit()
    db.close()
    flash("Report marked as resolved!", "success")
    return redirect(url_for("my_reports"))


@app.route("/report/<int:report_id>/delete", methods=["POST"])
def delete_report(report_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    db.execute("DELETE FROM reports WHERE id = ? AND user_id = ?", (report_id, session["user_id"]))
    db.commit()
    db.close()
    flash("Report deleted.", "success")
    return redirect(url_for("my_reports"))


# ---------- ADMIN ROUTES ----------
@app.route("/admin")
@app.route("/admin.html")
def admin_dashboard():
    if "user_id" not in session or not session.get("is_admin"):
        flash("Admin access required!", "error")
        return redirect(url_for("login"))
    db = get_db()
    total_users = db.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0").fetchone()[0]
    total_lost = db.execute("SELECT COUNT(*) FROM reports WHERE type = 'lost'").fetchone()[0]
    total_found = db.execute("SELECT COUNT(*) FROM reports WHERE type = 'found'").fetchone()[0]
    total_reports = db.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    recent_reports = db.execute('''SELECT r.*, u.full_name, u.roll_number, u.email
        FROM reports r JOIN users u ON r.user_id = u.id ORDER BY r.created_at DESC''').fetchall()
    db.close()
    stats = {"total_users": total_users, "total_lost": total_lost,
             "total_found": total_found, "pending_reports": total_reports}
    return render_template("admin.html", stats=stats, recent_reports=recent_reports)


@app.route("/admin/reports")
@app.route("/admin_reports.html")
def admin_reports():
    if "user_id" not in session or not session.get("is_admin"):
        return redirect(url_for("login"))
    status_filter = request.args.get("status", "all")
    db = get_db()
    if status_filter in ["approved", "rejected", "resolved", "pending"]:
        reports = db.execute('''SELECT r.*, u.full_name, u.roll_number, u.email
            FROM reports r JOIN users u ON r.user_id = u.id WHERE r.status = ? 
            ORDER BY r.created_at DESC''', (status_filter,)).fetchall()
    else:
        status_filter = "all"
        reports = db.execute('''SELECT r.*, u.full_name, u.roll_number, u.email
            FROM reports r JOIN users u ON r.user_id = u.id ORDER BY r.created_at DESC''').fetchall()
    db.close()
    return render_template("admin_reports.html", reports=reports, current_status=status_filter)


@app.route("/admin/report/<int:report_id>/approve", methods=["POST"])
def admin_approve_report(report_id):
    if "user_id" not in session or not session.get("is_admin"):
        return redirect(url_for("login"))
    db = get_db()
    db.execute("UPDATE reports SET status = 'approved' WHERE id = ?", (report_id,))
    db.commit()
    db.close()
    flash("Report approved!", "success")
    return redirect(request.referrer or url_for("admin_reports"))


@app.route("/admin/report/<int:report_id>/reject", methods=["POST"])
def admin_reject_report(report_id):
    if "user_id" not in session or not session.get("is_admin"):
        return redirect(url_for("login"))
    db = get_db()
    db.execute("UPDATE reports SET status = 'rejected' WHERE id = ?", (report_id,))
    db.commit()
    db.close()
    flash("Report rejected.", "error")
    return redirect(request.referrer or url_for("admin_reports"))


@app.route("/admin/report/<int:report_id>/delete", methods=["POST"])
def admin_delete_report(report_id):
    if "user_id" not in session or not session.get("is_admin"):
        return redirect(url_for("login"))
    db = get_db()
    db.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    db.commit()
    db.close()
    flash("Report deleted.", "success")
    return redirect(request.referrer or url_for("admin_reports"))


@app.route("/admin/users")
@app.route("/admin_users.html")
def admin_users():
    if "user_id" not in session or not session.get("is_admin"):
        return redirect(url_for("login"))
    db = get_db()
    users = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    db.close()
    return render_template("admin_users.html", users=users)


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def admin_delete_user(user_id):
    if "user_id" not in session or not session.get("is_admin"):
        return redirect(url_for("login"))
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user and not user["is_admin"]:
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()
        flash(f"User '{user['full_name']}' deleted.", "success")
    db.close()
    return redirect(url_for("admin_users"))


if __name__ == "__main__":
    init_db()
    print("=" * 55)
    print("  SIES COLLEGE CAMPUS LOST & FOUND SYSTEM")
    print("=" * 55)
    print("  Server: http://127.0.0.1:5000")
    print("  Admin:  admin@sies.edu / admin123")
    print("  Student: student@sies.edu / student123")
    print("=" * 55)
    app.run(debug=True, host="127.0.0.1", port=5000)
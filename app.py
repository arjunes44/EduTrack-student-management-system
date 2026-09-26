import hmac
import os
import secrets
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
DATABASE = Path(app.root_path) / "edutrack.db"
UPLOAD_FOLDER = Path(app.static_folder) / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config.update(SECRET_KEY=os.environ.get("EDUTRACK_SECRET_KEY", secrets.token_hex(32)), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024


def staff_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("staff_authenticated"):
            return view(*args, **kwargs)
        if request.path.startswith("/api/"):
            return jsonify({"error": "Please sign in to continue."}), 401
        return redirect(url_for("login", next=request.path))
    return wrapped


def connection():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with connection() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, course TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Active', grade TEXT NOT NULL DEFAULT '1', section TEXT NOT NULL DEFAULT 'A', guardian TEXT NOT NULL DEFAULT '', phone TEXT NOT NULL DEFAULT '', photo TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        columns = {row[1] for row in db.execute("PRAGMA table_info(students)")}
        for name, definition in {"grade": "TEXT NOT NULL DEFAULT '1'", "section": "TEXT NOT NULL DEFAULT 'A'", "guardian": "TEXT NOT NULL DEFAULT ''", "phone": "TEXT NOT NULL DEFAULT ''", "photo": "TEXT NOT NULL DEFAULT ''"}.items():
            if name not in columns:
                db.execute(f"ALTER TABLE students ADD COLUMN {name} {definition}")
        db.execute("""CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, attendance_date TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('Present', 'Late', 'Absent')), UNIQUE(student_id, attendance_date), FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE)""")
        db.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, role TEXT NOT NULL CHECK(role IN ('Student', 'Parent')), username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(student_id, role), FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE)""")
        db.execute("""CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('Leave', 'Contact update')), message TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Approved', 'Declined')), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE)""")
        if db.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
            db.executemany("INSERT INTO students (name, course) VALUES (?, ?)", [("Aarav Sharma", "Computer Science"), ("Meera Patel", "Business Studies"), ("Kabir Singh", "Mathematics")])


def validate(data):
    name, course = str(data.get("name", "")).strip(), str(data.get("course", "")).strip()
    status = str(data.get("status", "Active")).strip().title()
    grade, section = str(data.get("grade", "1")).strip(), str(data.get("section", "A")).strip().upper()
    guardian, phone = str(data.get("guardian", "")).strip(), str(data.get("phone", "")).strip()
    if not name or not course:
        return None, "Name and course are required."
    if len(name) > 80 or len(course) > 80:
        return None, "Name and course must be 80 characters or fewer."
    if status not in {"Active", "Inactive"}:
        return None, "Status must be Active or Inactive."
    if grade not in {str(number) for number in range(1, 13)}:
        return None, "Class must be between 1 and 12."
    if len(section) > 4 or len(guardian) > 80 or len(phone) > 25:
        return None, "One of the additional fields is too long."
    return (name, course, status, grade, section or "A", guardian, phone), None


def save_photo(upload):
    if not upload or not upload.filename:
        return None, None
    extension = Path(secure_filename(upload.filename)).suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
        return None, "Use a JPG, PNG, or WebP photo."
    filename = f"{secrets.token_hex(12)}{extension}"
    upload.save(UPLOAD_FOLDER / filename)
    return filename, None


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        role = request.form.get("role", "Staff")
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        configured_password = os.environ.get("EDUTRACK_ADMIN_PASSWORD")
        if role == "Staff" and not configured_password:
            error = "The administrator password has not been configured yet."
        elif role == "Staff" and username.lower() == "admin" and hmac.compare_digest(password, configured_password):
            session.clear()
            session["staff_authenticated"], session["role"] = True, "Staff"
            return redirect(request.args.get("next") or url_for("home"))
        elif role in {"Student", "Parent"}:
            with connection() as db:
                user = db.execute("SELECT * FROM users WHERE username = ? AND role = ?", (username, role)).fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["role"], session["student_id"] = role, user["student_id"]
                return redirect(url_for("portal"))
            error = "Incorrect username, role, or password."
        else:
            error = "Incorrect staff username or password."
    return render_template("login.html", error=error)


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/")
def home():
    if session.get("role") in {"Student", "Parent"}:
        return redirect(url_for("portal"))
    if not session.get("staff_authenticated"):
        return redirect(url_for("login"))
    return render_template("index.html")


@app.get("/portal")
def portal():
    if session.get("role") not in {"Student", "Parent"}:
        return redirect(url_for("login"))
    with connection() as db:
        student = db.execute("SELECT * FROM students WHERE id = ?", (session["student_id"],)).fetchone()
        attendance = db.execute("SELECT attendance_date, status FROM attendance WHERE student_id = ? ORDER BY attendance_date DESC LIMIT 12", (session["student_id"],)).fetchall()
        requests = db.execute("SELECT * FROM requests WHERE student_id = ? ORDER BY id DESC LIMIT 8", (session["student_id"],)).fetchall()
    return render_template("portal.html", student=dict(student), attendance=[dict(row) for row in attendance], requests=[dict(row) for row in requests], role=session["role"])


@app.post("/portal/request")
def portal_request():
    if session.get("role") not in {"Student", "Parent"}:
        return redirect(url_for("login"))
    kind, message = request.form.get("kind", ""), request.form.get("message", "").strip()
    if kind not in {"Leave", "Contact update"} or not message or len(message) > 500:
        return redirect(url_for("portal"))
    with connection() as db:
        db.execute("INSERT INTO requests (student_id, kind, message) VALUES (?, ?, ?)", (session["student_id"], kind, message))
    return redirect(url_for("portal"))


@app.get("/accounts")
@staff_required
def accounts_page():
    with connection() as db:
        students = db.execute("SELECT id, name, grade, section FROM students ORDER BY name").fetchall()
        accounts = db.execute("SELECT users.role, users.username, students.name FROM users JOIN students ON students.id = users.student_id ORDER BY users.id DESC").fetchall()
    return render_template("accounts.html", students=[dict(row) for row in students], accounts=[dict(row) for row in accounts])


@app.get("/requests")
@staff_required
def requests_page():
    with connection() as db:
        items = db.execute("SELECT requests.*, students.name FROM requests JOIN students ON students.id = requests.student_id ORDER BY CASE requests.status WHEN 'Pending' THEN 0 ELSE 1 END, requests.id DESC").fetchall()
    return render_template("requests.html", items=[dict(row) for row in items])


@app.post("/requests/<int:request_id>")
@staff_required
def update_request(request_id):
    status = request.form.get("status")
    if status in {"Approved", "Declined"}:
        with connection() as db:
            db.execute("UPDATE requests SET status = ? WHERE id = ?", (status, request_id))
    return redirect(url_for("requests_page"))


MODULES = {
    "students": {"title": "Student profiles", "eyebrow": "Student management", "description": "Add, edit, search, and organize every learner from one reliable directory.", "next": "attendance", "next_label": "Go to attendance"},
    "attendance": {"title": "Live attendance", "eyebrow": "Daily operations", "description": "Monitor attendance at a glance and highlight learners who need follow-up.", "next": "insights", "next_label": "View progress insights"},
    "insights": {"title": "Progress insights", "eyebrow": "Academic overview", "description": "Turn student data into clear next actions for staff and learners.", "next": "students", "next_label": "Open student profiles"},
}


@app.get("/<module>")
@staff_required
def module_page(module):
    page = MODULES.get(module)
    if not page:
        return "Page not found", 404
    return render_template("module.html", page=page, module=module)


@app.get("/api/summary")
@staff_required
def summary():
    with connection() as db:
        total = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        active = db.execute("SELECT COUNT(*) FROM students WHERE status = 'Active'").fetchone()[0]
    return jsonify({"total": total, "active": active, "attendance": 94.8})


@app.get("/api/activity")
@staff_required
def activity():
    with connection() as db:
        rows = db.execute("SELECT name, course, created_at FROM students ORDER BY id DESC LIMIT 4").fetchall()
    return jsonify([{"title": "Student record added", "detail": f"{row['name']} · {row['course']}", "time": row["created_at"]} for row in rows])


@app.route("/api/attendance", methods=["GET", "POST"])
@staff_required
def attendance_api():
    if request.method == "GET":
        grade, date = request.args.get("grade", "1"), request.args.get("date", "")
        with connection() as db:
            rows = db.execute("""SELECT students.id, students.name, students.section, attendance.status FROM students LEFT JOIN attendance ON attendance.student_id = students.id AND attendance.attendance_date = ? WHERE students.grade = ? AND students.status = 'Active' ORDER BY students.section, students.name""", (date, grade)).fetchall()
        return jsonify([dict(row) for row in rows])

    data = request.get_json(silent=True) or {}
    date, records = str(data.get("date", "")).strip(), data.get("records", [])
    if not date or not isinstance(records, list):
        return jsonify({"error": "A date and attendance records are required."}), 400
    allowed = {"Present", "Late", "Absent"}
    if any(not isinstance(record.get("id"), int) or record.get("status") not in allowed for record in records):
        return jsonify({"error": "Each record needs a valid student and attendance status."}), 400
    with connection() as db:
        db.executemany("""INSERT INTO attendance (student_id, attendance_date, status) VALUES (?, ?, ?) ON CONFLICT(student_id, attendance_date) DO UPDATE SET status = excluded.status""", [(record["id"], date, record["status"]) for record in records])
    return jsonify({"saved": len(records)})


@app.route("/api/students", methods=["GET", "POST"])
@staff_required
def students_api():
    if request.method == "GET":
        query = request.args.get("q", "").strip()
        with connection() as db:
            rows = db.execute("SELECT * FROM students WHERE name LIKE ? OR course LIKE ? ORDER BY id DESC", (f"%{query}%", f"%{query}%")).fetchall()
        return jsonify([dict(row) for row in rows])
    values, error = validate(request.form or request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), 400
    photo, error = save_photo(request.files.get("photo"))
    if error:
        return jsonify({"error": error}), 400
    with connection() as db:
        cursor = db.execute("INSERT INTO students (name, course, status, grade, section, guardian, phone, photo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (*values, photo or ""))
        row = db.execute("SELECT * FROM students WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/students/<int:student_id>", methods=["PUT", "DELETE"])
@staff_required
def student_api(student_id):
    with connection() as db:
        existing = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        if not existing:
            return jsonify({"error": "Student not found."}), 404
        if request.method == "DELETE":
            db.execute("DELETE FROM students WHERE id = ?", (student_id,))
            return "", 204
        values, error = validate(request.form or request.get_json(silent=True) or {})
        if error:
            return jsonify({"error": error}), 400
        photo, error = save_photo(request.files.get("photo"))
        if error:
            return jsonify({"error": error}), 400
        db.execute("UPDATE students SET name = ?, course = ?, status = ?, grade = ?, section = ?, guardian = ?, phone = ?, photo = ? WHERE id = ?", (*values, photo or existing["photo"], student_id))
        row = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    return jsonify(dict(row))


@app.post("/api/accounts")
@staff_required
def create_account():
    data = request.get_json(silent=True) or {}
    try:
        student_id = int(data.get("student_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "Choose a student."}), 400
    role, username, password = data.get("role", ""), str(data.get("username", "")).strip(), str(data.get("password", ""))
    if role not in {"Student", "Parent"} or len(username) < 3 or len(password) < 8:
        return jsonify({"error": "Use Student or Parent, a 3+ character username, and an 8+ character password."}), 400
    with connection() as db:
        if not db.execute("SELECT id FROM students WHERE id = ?", (student_id,)).fetchone():
            return jsonify({"error": "Student not found."}), 404
        try:
            db.execute("INSERT INTO users (student_id, role, username, password_hash) VALUES (?, ?, ?, ?)", (student_id, role, username, generate_password_hash(password)))
        except sqlite3.IntegrityError:
            return jsonify({"error": "That username or role account already exists."}), 409
    return jsonify({"message": f"{role} account created."}), 201


init_db()

if __name__ == "__main__":
    app.run(debug=True)

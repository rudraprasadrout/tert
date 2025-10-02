# app.py (FINAL, CORRECTED, AND INTEGRATED)
import os
import sqlite3
from datetime import datetime, timedelta

import matplotlib
import pandas as pd
from flask import (Flask, flash, redirect, render_template, request,
                   send_from_directory, session, url_for, jsonify) # <-- IMPORT jsonify
from werkzeug.utils import secure_filename

# Use non-interactive backend for servers
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# --- 1. Import your new modular Blueprints ---
from chatbot import chat_bp
from uploads import upload_bp
from features import api_bp, admin_features_bp

# --- 2. Import the database functions from database.py ---
from database import (get_all_complaints, get_complaint_by_id, get_db_connection,
                      get_db_df, get_user_complaints, update_complaint_status)
from piu import generate_odisha_heatmap

# ==================== APP SETUP ====================
app = Flask(__name__)
app.secret_key = "supersecretkey"  # required for sessions

# --- File Upload Config ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ADMIN_PROOF_FOLDER = os.path.join(BASE_DIR, "static", "admin_proofs")
CHART_FOLDER = os.path.join(BASE_DIR, "static", "admin_charts")

for d in (UPLOAD_FOLDER, ADMIN_PROOF_FOLDER, CHART_FOLDER):
    os.makedirs(d, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["ADMIN_PROOF_FOLDER"] = ADMIN_PROOF_FOLDER
app.config["CHART_FOLDER"] = CHART_FOLDER


# --- Database Initializer ---
def init_db():
    conn = get_db_connection()
    # Users table
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     phone TEXT UNIQUE NOT NULL,
                     password TEXT NOT NULL
                 )''')
    # Complaints table
    conn.execute('''CREATE TABLE IF NOT EXISTS complaints (
                     id INTEGER PRIMARY KEY AUTOINCREMENT, user_phone TEXT NOT NULL, name TEXT,
                     phone TEXT, district TEXT, block TEXT, gp TEXT, village TEXT,
                     landmark TEXT, pincode TEXT, department TEXT, complaint TEXT,
                     proof TEXT, status TEXT DEFAULT 'Pending', admin_proof TEXT,
                     updated_at TEXT, FOREIGN KEY(user_phone) REFERENCES users(phone)
                 )''')
    # Feedback table
    conn.execute('''CREATE TABLE IF NOT EXISTS feedback (
                     id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                     email TEXT NOT NULL, type TEXT NOT NULL, rating INTEGER NOT NULL,
                     message TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
                 )''')
    conn.commit()
    conn.close()

init_db()


# --- Jinja Filter ---
@app.template_filter('datetimeformat')
def datetimeformat(value, format="%d %b %Y"):
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
            return dt.strftime(format)
        except ValueError:
            return value
    elif isinstance(value, datetime):
        return value.strftime(format)
    return value


# NOTE: The "DB HELPERS" functions have been REMOVED from here
# because they now live in database.py


# -------------------- CHART GENERATION --------------------
def generate_charts():
    df = get_db_df()
    if df.empty:
        return {}

    chart_paths = {}

    # Complaints by Status
    status_counts = df['status'].fillna('Pending').value_counts()
    status_counts.plot(kind='bar', edgecolor='black', color='#0a66ff')
    plt.title('Complaints by Status')
    plt.tight_layout()
    path = os.path.join(CHART_FOLDER, 'status_bar.png')
    plt.savefig(path); plt.close()
    chart_paths['status'] = 'admin_charts/status_bar.png'

    # Complaints by Department
    dept_counts = df['department'].fillna('Unknown').value_counts()
    dept_counts.plot(kind='pie', autopct='%1.1f%%')
    plt.ylabel('')
    plt.title('Complaints by Department')
    plt.tight_layout()
    path = os.path.join(CHART_FOLDER, 'department_pie.png')
    plt.savefig(path); plt.close()
    chart_paths['department'] = 'admin_charts/department_pie.png'

    # Top Pincodes
    pincode_counts = df['pincode'].fillna('Unknown').value_counts().head(10)
    pincode_counts.plot(kind='bar', edgecolor='black', color='#28a745')
    plt.title('Top 10 Pincodes by Complaints')
    plt.xlabel('Pincode'); plt.ylabel('Complaints')
    plt.tight_layout()
    path = os.path.join(CHART_FOLDER, 'pincode_bar.png')
    plt.savefig(path); plt.close()
    chart_paths['pincode'] = 'admin_charts/pincode_bar.png'

    # Complaints Over Time
    if 'updated_at' in df.columns:
        df['updated_at'] = pd.to_datetime(df['updated_at'], errors='coerce')
        time_counts = df.dropna(subset=['updated_at']).groupby(df['updated_at'].dt.date).size()
        if not time_counts.empty:
            time_counts.plot(kind='line', marker='o')
            plt.title('Complaints Over Time')
            plt.xlabel('Date'); plt.ylabel('Count')
            plt.tight_layout()
            path = os.path.join(CHART_FOLDER, 'time_line.png')
            plt.savefig(path); plt.close()
            chart_paths['time'] = 'admin_charts/time_line.png'

    # Complaints by District
    district_counts = df['district'].fillna('Unknown').value_counts().head(10)
    district_counts.plot(kind='bar', edgecolor='black', color='#ffc107')
    plt.title('Complaints by District (Top 10)')
    plt.xlabel('District'); plt.ylabel('Complaints')
    plt.tight_layout()
    path = os.path.join(CHART_FOLDER, 'district_bar.png')
    plt.savefig(path); plt.close()
    chart_paths['district'] = 'admin_charts/district_bar.png'

    # Dept vs Status
    dept_status = df.pivot_table(index='department', columns='status',
                                 aggfunc='size', fill_value=0)
    if not dept_status.empty:
        dept_status.plot(kind='bar', stacked=True)
        plt.title('Department vs Status')
        plt.xlabel('Department'); plt.ylabel('Complaints')
        plt.tight_layout()
        path = os.path.join(CHART_FOLDER, 'dept_status.png')
        plt.savefig(path); plt.close()
        chart_paths['dept_status'] = 'admin_charts/dept_status.png'

    return chart_paths

# -------------------- ROUTES --------------------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/report")
def report():
    if not session.get("user"):
        flash("Please login first to submit a report.", "warning")
        return redirect(url_for("user_login", next="report"))
    return render_template("report.html")

@app.route("/about")
def about():
    return render_template("about.html")

# -------------------- AUTH --------------------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if email == "admin@example.com" and password == "admin123":
            session["role"] = "admin"
            flash("Admin login successful!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid admin credentials", "danger")
            return redirect(url_for("admin_login"))
    return render_template("admin_login.html")

@app.route("/user_login", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        phone = request.form["phone"]
        password = request.form["password"]
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE phone=? AND password=?", (phone, password))
        user = c.fetchone()
        conn.close()
        if user:
            session["user"] = phone
            session["role"] = "user"
            flash("Login successful!", "success")
            next_page = request.args.get("next")
            if next_page == "report":
                return redirect(url_for("report"))
            return redirect(url_for("home"))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for("user_login"))
    return render_template("user_login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        phone = request.form["phone"]
        password = request.form["password"]
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (phone, password) VALUES (?, ?)", (phone, password))
            conn.commit()
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("user_login"))
        except sqlite3.IntegrityError:
            flash("Phone number already registered.", "danger")
            return redirect(url_for("signup"))
        finally:
            conn.close()
    return render_template("signup_page.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("home"))

@app.route("/submit_complaint", methods=["POST"])
def submit_complaint():
    if session.get("role") != "user":
        flash("Please log in to submit a complaint.", "danger")
        return redirect(url_for("user_login"))

    name = request.form["name"]
    phone = request.form["phone"]
    district = request.form["district"]
    block = request.form["block"]
    gp = request.form["gp"]
    village = request.form["village"]
    landmark = request.form["landmark"]
    pincode = request.form["pincode"]
    department = request.form["department"]
    complaint = request.form["complaint"]

    # Handle standard proof file
    proof_file = request.files.get("proof")
    proof_filename = None
    if proof_file and proof_file.filename:
        proof_filename = secure_filename(f"proof_{phone}_{proof_file.filename}")
        proof_file.save(os.path.join(app.config["UPLOAD_FOLDER"], proof_filename))

    # --- NEW: Handle voice proof file ---
    voice_file = request.files.get("voice_complaint")
    voice_filename = None
    if voice_file and voice_file.filename:
        voice_filename = secure_filename(f"voice_{phone}_{voice_file.filename}")
        voice_file.save(os.path.join(app.config["UPLOAD_FOLDER"], voice_filename))
    # --- END NEW ---

    conn = get_db_connection()
    c = conn.cursor()
    # --- UPDATED: Add voice_proof to INSERT query ---
    c.execute('''INSERT INTO complaints 
                  (user_phone, name, phone, district, block, gp, village, landmark, pincode, department, complaint, proof, voice_proof) 
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (session["user"], name, phone, district, block, gp, village, landmark, pincode, department, complaint, proof_filename, voice_filename))
    # --- END UPDATE ---
    conn.commit()
    conn.close()

    flash("Complaint submitted successfully!", "success")
    return redirect(url_for("mycomplaints"))

# ======================= NEW DELETE ROUTE =======================
@app.route("/api/complaint/<int:cid>", methods=["DELETE"])
def delete_complaint(cid):
    # 1. Authentication: Ensure a user is logged in
    if session.get("role") != "user":
        return jsonify({"success": False, "error": "Authentication required."}), 401

    conn = get_db_connection()
    # 2. Authorization: Check if the complaint exists and belongs to the logged-in user
    complaint = conn.execute("SELECT user_phone, status FROM complaints WHERE id = ?", (cid,)).fetchone()
    
    if not complaint:
        conn.close()
        return jsonify({"success": False, "error": "Complaint not found."}), 404

    if complaint["user_phone"] != session["user"]:
        conn.close()
        return jsonify({"success": False, "error": "You are not authorized to delete this complaint."}), 403

    # 3. Business Logic: Only allow deletion if the status is 'Pending'
    if (complaint["status"] or "Pending").lower() != "pending":
        conn.close()
        return jsonify({"success": False, "error": "Only pending complaints can be deleted."}), 400

    # 4. Deletion: If all checks pass, delete the complaint
    conn.execute("DELETE FROM complaints WHERE id = ?", (cid,))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Complaint deleted successfully."}), 200
# ===================== END NEW DELETE ROUTE =====================


# -------------------- FEEDBACK --------------------
@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    name = request.form.get("name")
    email = request.form.get("email")
    ftype = request.form.get("type")
    rating = request.form.get("rating")
    message = request.form.get("message")

    if not all([name, email, ftype, rating, message]):
        flash("All fields are required.", "danger")
        return redirect(url_for("mycomplaints"))

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO feedback (name, email, type, rating, message)
                 VALUES (?, ?, ?, ?, ?)''',
              (name, email, ftype, rating, message))
    conn.commit()
    conn.close()

    flash("Thank you for your feedback!", "success")
    return redirect(url_for("mycomplaints"))

# -------------------- ADMIN --------------------
def admin_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required", "danger")
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/admin_dashboard")
@admin_required
def admin_dashboard():
    q = request.args.get("q", "").strip()

    charts = generate_charts()
    charts['odisha_map'] = generate_odisha_heatmap()
    df = get_db_df()
    total = len(df)
    by_status = df['status'].fillna('Pending').value_counts().to_dict()
    by_dept = df['department'].fillna('Unknown').value_counts().to_dict()

    conn = get_db_connection()
    c = conn.cursor()

    if q:
        like_q = f"%{q}%"
        c.execute("""SELECT id, user_phone, name, phone, district, block, gp, village, landmark, pincode,
                             department, complaint, proof, status, admin_proof, updated_at
                       FROM complaints
                       WHERE user_phone LIKE ? OR phone LIKE ? OR department LIKE ? 
                             OR pincode LIKE ? OR district LIKE ? OR village LIKE ?
                             OR complaint LIKE ?
                       ORDER BY id DESC""",
                  (like_q, like_q, like_q, like_q, like_q, like_q, like_q))
    else:
        c.execute("""SELECT id, user_phone, name, phone, district, block, gp, village, landmark, pincode,
                             department, complaint, proof, status, admin_proof, updated_at
                       FROM complaints ORDER BY id DESC""")

    complaints = c.fetchall()

    # Feedback
    c.execute("SELECT id, name, email, type, rating, message, created_at FROM feedback ORDER BY id DESC")
    feedbacks = c.fetchall()

    # Pending complaints > 5 days
    five_days_ago = datetime.utcnow() - timedelta(days=5)
    c.execute("""SELECT id, district, department, complaint, updated_at
                 FROM complaints
                 WHERE status='Pending' AND updated_at IS NOT NULL 
                       AND datetime(updated_at) <= ?""", (five_days_ago.isoformat(),))
    alerts = c.fetchall()

    conn.close()

    return render_template("admin_dashboard.html",
                           charts=charts, total=total,
                           by_status=by_status, by_dept=by_dept,
                           complaints=complaints,
                           feedbacks=feedbacks,
                           alerts=alerts)  # 👈 new variable



@app.route("/admin_update_status", methods=["POST"])
@admin_required
def admin_update_status_route():
    cid = request.form.get("cid")
    new_status = request.form.get("status")
    proof_file = request.files.get("admin_proof")

    admin_proof_filename = None
    if proof_file and proof_file.filename:
        admin_proof_filename = secure_filename(proof_file.filename)
        proof_file.save(os.path.join(app.config["ADMIN_PROOF_FOLDER"], admin_proof_filename))

    # Ensure "Resolved" always requires proof
    if new_status and new_status.lower().strip() == "resolved" and not admin_proof_filename:
        flash("Please attach proof when marking resolved.", "danger")
        return redirect(request.referrer or url_for("admin_dashboard"))

    update_complaint_status(cid, new_status, admin_proof_filename)
    flash("Complaint status updated.", "success")
    return redirect(request.referrer or url_for("admin_dashboard"))


@app.route('/admin_charts/<path:filename>')
@admin_required
def admin_charts(filename):
    return send_from_directory(CHART_FOLDER, filename)

@app.route('/admin_proofs/<path:filename>')
# @admin_required
def admin_proofs(filename):
    return send_from_directory(ADMIN_PROOF_FOLDER, filename)

# -------------------- NEW ADMIN ROUTES --------------------
@app.route("/admin/user/<user_phone>")
@admin_required
def admin_user_view(user_phone):
    complaints = get_user_complaints(user_phone)
    return render_template("admin_user_view.html", user_phone=user_phone, complaints=complaints)

@app.route("/admin/complaint/<int:cid>")
@admin_required
def admin_complaint_view(cid):
    complaint = get_complaint_by_id(cid)
    if not complaint:
        flash("Complaint not found", "danger")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_complaint_view.html", complaint=complaint)

# -------------------- USER --------------------
@app.route("/mycomplaints")
def mycomplaints():
    if session.get("role") == "user":
        user_phone = session.get("user")
        # Use the get_db_connection to ensure you can access columns by name
        conn = get_db_connection() 
        # The query now uses SELECT * to get ALL columns, including voice_proof
        complaints = conn.execute("SELECT * FROM complaints WHERE user_phone = ? ORDER BY id DESC", (user_phone,)).fetchall()
        conn.close()
        return render_template("mycomplaints.html", complaints=complaints)
    return redirect(url_for("home"))

@app.route("/community")
def community():
    department = request.args.get("department", "all")
    rating = request.args.get("rating", "all")
    sort = request.args.get("sort", "newest")

    query = "SELECT id, name, email, type, rating, message, created_at FROM feedback WHERE 1=1"
    params = []

    # Department filter
    if department != "all":
        query += " AND type = ?"
        params.append(department)

    # Rating filter
    if rating != "all":
        query += " AND rating >= ?"
        params.append(int(rating))

    # Sorting
    if sort == "newest":
        query += " ORDER BY id DESC"
    elif sort == "oldest":
        query += " ORDER BY id ASC"
    elif sort == "highest":
        query += " ORDER BY rating DESC"
    elif sort == "lowest":
        query += " ORDER BY rating ASC"

    conn = get_db_connection()
    c = conn.cursor()
    c.execute(query, params)
    feedbacks = c.fetchall()
    conn.close()

    return render_template("community.html",
                           feedbacks=feedbacks,
                           selected_department=department,
                           selected_rating=rating,
                           selected_sort=sort)


# ==================== BLUEPRINT REGISTRATION ====================
# --- 3. Register your new blueprints alongside the old ones ---
app.register_blueprint(api_bp)
app.register_blueprint(admin_features_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(upload_bp)

# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    app.run(debug=True)
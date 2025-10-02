# database.py

import sqlite3
import os
from datetime import datetime
import pandas as pd

# --- Constants ---
DB_NAME = "civic.db"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")


# --- Main Database Connection Function ---

def get_db_connection():
    """Establishes a database connection that returns dictionary-like rows."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # This lets you access columns by name (e.g., complaint['status'])
    return conn


# --- All Database Helper Functions ---

def get_db_df():
    """Fetches all complaints into a pandas DataFrame for chart generation."""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM complaints", conn)
    conn.close()
    return df

def get_all_complaints():
    """Fetches all complaints, ordered by the newest first."""
    conn = get_db_connection()
    complaints = conn.execute("SELECT * FROM complaints ORDER BY id DESC").fetchall()
    conn.close()
    return complaints

def get_user_complaints(user_phone):
    """Fetches all complaints for a specific user."""
    conn = get_db_connection()
    complaints = conn.execute("SELECT * FROM complaints WHERE user_phone = ? ORDER BY id DESC", (user_phone,)).fetchall()
    conn.close()
    return complaints

def get_complaint_by_id(cid):
    """Fetches a single complaint by its ID."""
    conn = get_db_connection()
    complaint = conn.execute("SELECT * FROM complaints WHERE id = ?", (cid,)).fetchone()
    conn.close()
    return complaint

def update_complaint_status(cid, status, admin_proof_filename=None):
    """Updates the status and optionally the admin proof for a complaint."""
    conn = get_db_connection()
    updated_at = datetime.utcnow().isoformat()
    if admin_proof_filename:
        conn.execute("UPDATE complaints SET status = ?, admin_proof = ?, updated_at = ? WHERE id = ?",
                     (status, admin_proof_filename, updated_at, cid))
    else:
        conn.execute("UPDATE complaints SET status = ?, updated_at = ? WHERE id = ?",
                     (status, updated_at, cid))
    conn.commit()
    conn.close()

def update_complaint_proof(cid, proof_filename):
    """Updates the user's proof filename for a specific complaint."""
    conn = get_db_connection()
    conn.execute("UPDATE complaints SET proof = ? WHERE id = ?", (proof_filename, cid))
    conn.commit()
    conn.close()
# database.py (add this new function at the end)

def update_complaint_details(cid, data):
    """Updates the editable fields of a specific complaint."""
    conn = get_db_connection()
    conn.execute("""
        UPDATE complaints 
        SET name = ?, phone = ?, district = ?, block = ?, gp = ?, 
            village = ?, landmark = ?, pincode = ?, department = ?, complaint = ?
        WHERE id = ?
    """, (
        data.get('name'), data.get('phone'), data.get('district'), data.get('block'),
        data.get('gp'), data.get('village'), data.get('landmark'), data.get('pincode'),
        data.get('department'), data.get('complaint'), cid
    ))
    conn.commit()
    conn.close()
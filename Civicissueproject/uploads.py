from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
# Import from the new database.py file
from database import get_complaint_by_id, update_complaint_proof, UPLOAD_FOLDER

upload_bp = Blueprint('uploads', __name__)

@upload_bp.route('/upload_proof/<int:cid>', methods=['GET', 'POST'])
def upload_proof_page(cid):
    if "user" not in session:
        flash("Please log in to upload proof.", "warning")
        return redirect(url_for('user_login'))

    complaint = get_complaint_by_id(cid)
    if not complaint:
        flash("Complaint not found.", "danger")
        return redirect(url_for('mycomplaints'))

    if complaint['user_phone'] != session['user']:
        flash("You are not authorized to edit this complaint.", "danger")
        return redirect(url_for('mycomplaints'))

    if request.method == 'POST':
        proof_file = request.files.get("proof")
        if proof_file and proof_file.filename:
            proof_filename = secure_filename(f"proof_{cid}_{proof_file.filename}")
            proof_file.save(os.path.join(UPLOAD_FOLDER, proof_filename))
            update_complaint_proof(cid, proof_filename)
            flash("Proof uploaded successfully!", "success")
            return redirect(url_for('mycomplaints'))
        else:
            flash("No file selected for upload.", "warning")

    return render_template('upload_proof.html', complaint=complaint)


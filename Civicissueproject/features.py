from flask import Blueprint, jsonify, request, session, make_response
from database import get_complaint_by_id, update_complaint_details, get_db_df
import pandas as pd
import io

api_bp = Blueprint('api', __name__, url_prefix='/api')
admin_features_bp = Blueprint('admin_features', __name__)

# --- FIX: ADD THIS NEW ROUTE ---
@admin_features_bp.route('/admin/export/complaints.csv')
def export_complaints_csv():
    """
    Fetches all complaints from the database and returns them as a downloadable CSV file.
    """
    # Security check: ensure an admin is logged in
    if session.get("role") != "admin":
        return "Unauthorized", 401

    try:
        # Get all complaints as a pandas DataFrame
        df = get_db_df()

        if df.empty:
            return "No complaints to export.", 404

        # Use an in-memory string buffer to create the CSV
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)

        # Create a Flask response to send the file
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=complaints.csv"
        response.headers["Content-type"] = "text/csv"
        
        return response

    except Exception as e:
        print(f"Error exporting CSV: {e}")
        return "Failed to generate CSV.", 500


@api_bp.route('/complaint/<int:cid>', methods=['PUT'])
def update_complaint(cid):
    # Security Check 1: User must be logged in
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401

    complaint = get_complaint_by_id(cid)
    
    # Security Check 2: User must own the complaint they are trying to edit
    if not complaint or complaint['user_phone'] != session['user']:
        return jsonify({'success': False, 'error': 'Forbidden'}), 403

    # Logic Check: Only pending complaints can be edited
    if complaint['status'].lower() != 'pending':
        return jsonify({'success': False, 'error': 'Only pending complaints can be edited'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    # Call the database function to update the complaint
    update_complaint_details(cid, data)
    
    return jsonify({'success': True, 'message': 'Complaint updated successfully'})

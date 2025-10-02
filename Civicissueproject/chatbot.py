from flask import Blueprint, request, jsonify, session, url_for
from datetime import datetime
import sqlite3
# Import from the new database.py file, NOT from app.py
from database import get_complaint_by_id, DB_NAME

chat_bp = Blueprint('chatbot', __name__)

@chat_bp.route('/chat', methods=['POST'])
def chat():
    if 'chat_state' not in session:
        session['chat_state'] = {'stage': 'INIT'}
    
    state = session['chat_state']
    user_message = request.json.get('message', '').lower()
    
    bot_response = "I'm sorry, I don't understand."
    options = []
    current_stage = state.get('stage', 'INIT')

    if current_stage == 'INIT':
        if 'report an issue' in user_message:
            if 'user' in session:
                state.clear() # Start a new report
                state['stage'] = 'ASK_DEPARTMENT'
                bot_response = "Okay, let's file a detailed report. Please choose the concerned department."
                options = ["Water Supply", "Electricity", "Roads & Transport", "Health & Sanitation", "Education", "Other"]
            else:
                bot_response = "You must be logged in to report an issue. Please log in first."
        elif 'check status' in user_message:
            if 'user' in session:
                state.clear() # Start a new status check
                state['stage'] = 'ASK_TICKET_ID'
                bot_response = "Sure, I can check a complaint's status. What is the ticket ID number?"
            else:
                bot_response = "You must be logged in to check a status. Please log in first."
        else: # Handles "initial_greeting" and any other unrecognized text
            if 'user' in session:
                bot_response = "Hi! I’m Citra, your CityZen assistant. 😊 You can report any city issues here or check the status of a report you’ve submitted. How can I help you today?"
                options = ["Report an Issue", "Check Status"]
            else:
                bot_response = "Welcome! Please log in to use the chatbot."

    elif current_stage == 'ASK_DEPARTMENT':
        state['department'] = request.json.get('message', '').title()
        bot_response = f"Department: {state['department']}. Now, please describe your complaint in detail."
        state['stage'] = 'ASK_COMPLAINT'

    elif current_stage == 'ASK_COMPLAINT':
        state['complaint'] = request.json.get('message', '')
        bot_response = "Thank you. What is your full name?"
        state['stage'] = 'ASK_NAME'
        
    elif current_stage == 'ASK_NAME':
        state['name'] = request.json.get('message', '').title()
        bot_response = "Got it. What is your 10-digit phone number?"
        state['stage'] = 'ASK_PHONE'
        
    elif current_stage == 'ASK_PHONE':
        if user_message.isdigit() and len(user_message) == 10:
            state['phone'] = user_message
            bot_response = "Thanks. Now for the location. Which district is this in?"
            state['stage'] = 'ASK_DISTRICT'
        else:
            bot_response = "That doesn't seem like a valid 10-digit phone number. Please try again."

    elif current_stage == 'ASK_DISTRICT':
        state['district'] = user_message.title()
        bot_response = "Which block?"
        state['stage'] = 'ASK_BLOCK'

    elif current_stage == 'ASK_BLOCK':
        state['block'] = user_message.title()
        bot_response = "And the Gram Panchayat (GP) name?"
        state['stage'] = 'ASK_GP'

    elif current_stage == 'ASK_GP':
        state['gp'] = user_message.title()
        bot_response = "What is the village name?"
        state['stage'] = 'ASK_VILLAGE'

    elif current_stage == 'ASK_VILLAGE':
        state['village'] = user_message.title()
        bot_response = "Please provide a nearby landmark."
        state['stage'] = 'ASK_LANDMARK'

    elif current_stage == 'ASK_LANDMARK':
        state['landmark'] = user_message
        bot_response = "Finally, what is the 6-digit PIN code?"
        state['stage'] = 'ASK_PINCODE'
        
    elif current_stage == 'ASK_PINCODE':
        if user_message.isdigit() and len(user_message) == 6:
            state['pincode'] = user_message
            summary = (f"Please confirm: Name: {state.get('name')}, Phone: {state.get('phone')}, Location: {state.get('village')}, Dept: {state.get('department')}.")
            bot_response = summary
            options = ["Yes, submit", "No, cancel"]
            state['stage'] = 'CONFIRM_SUBMIT'
        else:
            bot_response = "That doesn't look like a valid 6-digit PIN code. Please try again."

    elif current_stage == 'CONFIRM_SUBMIT':
        if 'yes' in user_message:
            try:
                user_phone = session.get('user')
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute('''INSERT INTO complaints (user_phone, name, phone, district, block, gp, village, landmark, pincode, department, complaint, status, updated_at) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (user_phone, state.get('name'), state.get('phone'), state.get('district'), state.get('block'), state.get('gp'), state.get('village'),
                           state.get('landmark'), state.get('pincode'), state.get('department'), state.get('complaint'), 'Pending', datetime.utcnow().isoformat()))
                conn.commit()
                complaint_id = c.lastrowid
                conn.close()
                upload_url = url_for('uploads.upload_proof_page', cid=complaint_id)
                bot_response = f"Thank you! Your complaint is submitted. Your ticket ID is #{complaint_id}. <a href='{upload_url}' target='_blank'>Click here to upload photo/video proof now.</a>"
                state.clear(); state['stage'] = 'INIT'
            except Exception as e:
                bot_response = f"An error occurred: {e}. I've canceled this report. Please try again."
                state.clear(); state['stage'] = 'INIT'
        else: # Handles "No, cancel"
            bot_response = "Okay, I've canceled the report. How else can I help?"
            options = ["Report an Issue", "Check Status"]
            state.clear(); state['stage'] = 'INIT'
    
    elif current_stage == 'ASK_TICKET_ID':
        try:
            ticket_id = int(user_message.strip())
            complaint = get_complaint_by_id(ticket_id)
            if complaint and complaint['user_phone'] == session['user']:
                status = complaint['status']
                bot_response = f"The status for ticket #{ticket_id} is: '{status}'."
            elif complaint:
                bot_response = "This ticket does not belong to you."
            else:
                bot_response = f"Sorry, I could not find a complaint with ticket ID #{ticket_id}."
            state.clear(); state['stage'] = 'INIT'
        except (ValueError, TypeError):
             bot_response = "That doesn't look like a valid ticket ID. Please provide a number."
            
    session['chat_state'] = state
    session.modified = True
    
    return jsonify({'response': bot_response, 'options': options})


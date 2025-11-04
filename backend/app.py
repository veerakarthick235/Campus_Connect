import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, g, send_from_directory
from db import users_collection, internships_collection, applications_collection
import bcrypt
from bson import ObjectId
from dotenv import load_dotenv
import jwt
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

load_dotenv()

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# --- Configurations ---
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads', 'resumes')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB limit for files

# Mail Configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't']
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)

# --- Helper Functions ---
def objectid_to_str(data):
    if isinstance(data, list): return [objectid_to_str(item) for item in data]
    if isinstance(data, dict): return {key: objectid_to_str(value) for key, value in data.items()}
    if isinstance(data, ObjectId): return str(data)
    return data

# --- JWT Authentication ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        if not token:
            return jsonify({'error': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = users_collection.find_one({'_id': ObjectId(data['user_id'])})
            if not current_user:
                 return jsonify({'error': 'User not found'}), 404
            g.current_user = objectid_to_str(current_user)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid!'}), 401
        return f(*args, **kwargs)
    return decorated

# --- Email Notification ---
def send_email(to, subject, body):
    try:
        with app.app_context():
            msg = Message(subject, recipients=[to])
            msg.body = body
            mail.send(msg)
    except Exception as e:
        print(f"Error sending email: {e}")

# --- USER AUTH ROUTES ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    name, email, password, role = data.get('name'), data.get('email'), data.get('password'), data.get('role')
    if not all([name, email, password, role]):
        return jsonify({"error": "Missing fields"}), 400
    if users_collection.find_one({"email": email}):
        return jsonify({"error": "User with this email already exists"}), 409
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user_data = {"name": name, "email": email, "password": hashed_password, "role": role}
    if role == 'student':
        user_data.update({"department": data.get('department'), "gpa": 0.0, "skills": [], "projects": [], "resume_filename": None})
    users_collection.insert_one(user_data)
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email, password = data.get('email'), data.get('password')
    user = users_collection.find_one({"email": email})
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        token = jwt.encode({'user_id': str(user['_id']), 'role': user['role'], 'exp': datetime.utcnow() + timedelta(hours=24)}, app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({'token': token, 'role': user['role']}), 200
    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/api/current_user', methods=['GET'])
@token_required
def get_current_user():
    user_data = g.current_user
    del user_data['password']
    return jsonify(user_data), 200

# --- PROFILE & INTERNSHIP ROUTES ---
@app.route('/api/student/profile', methods=['PUT'])
@token_required
def update_student_profile():
    if g.current_user['role'] != 'student': return jsonify({"error": "Unauthorized"}), 403
    user_id = g.current_user['_id']
    update_data = {}
    if 'gpa' in request.form: update_data['gpa'] = float(request.form['gpa'])
    if 'skills' in request.form: update_data['skills'] = [s.strip() for s in request.form['skills'].split(',')]
    if 'projects' in request.form: update_data['projects'] = [p.strip() for p in request.form['projects'].split(',')]
    if 'resume' in request.files:
        file = request.files['resume']
        if file.filename != '':
            filename = secure_filename(f"{user_id}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            update_data['resume_filename'] = filename
    if update_data:
        users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': update_data})
    return jsonify({"message": "Profile updated successfully"}), 200

@app.route('/api/internships', methods=['GET'])
@token_required
def get_internships():
    internships = list(internships_collection.find({}))
    return jsonify(objectid_to_str(internships)), 200
    
@app.route('/api/internships', methods=['POST'])
@token_required
def create_internship():
    if g.current_user['role'] != 'placement_cell': return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    internships_collection.insert_one(data)
    return jsonify({"message": "Internship created successfully"}), 201

# --- APPLICATION WORKFLOW ROUTES ---
@app.route('/api/apply/<internship_id>', methods=['POST'])
@token_required
def apply_for_internship(internship_id):
    if g.current_user['role'] != 'student': return jsonify({"error": "Only students can apply"}), 403
    student_id = g.current_user['_id']
    if applications_collection.find_one({"student_id": ObjectId(student_id), "internship_id": ObjectId(internship_id)}):
        return jsonify({"error": "You have already applied for this internship"}), 409
    application_data = {"student_id": ObjectId(student_id), "internship_id": ObjectId(internship_id), "status": "Applied"}
    applications_collection.insert_one(application_data)
    return jsonify({"message": "Applied successfully"}), 201

@app.route('/api/student/applications', methods=['GET'])
@token_required
def get_student_applications():
    if g.current_user['role'] != 'student': return jsonify({"error": "Unauthorized"}), 403
    pipeline = [{"$match": {"student_id": ObjectId(g.current_user['_id'])}},{"$lookup": {"from": "internships", "localField": "internship_id", "foreignField": "_id", "as": "internship_details"}}, {"$unwind": "$internship_details"}]
    applications = list(applications_collection.aggregate(pipeline))
    return jsonify(objectid_to_str(applications)), 200

@app.route('/api/placement/applications', methods=['GET'])
@token_required
def get_all_applications():
    if g.current_user['role'] != 'placement_cell': return jsonify({"error": "Unauthorized"}), 403
    pipeline = [{"$lookup": {"from": "users", "localField": "student_id", "foreignField": "_id", "as": "student_info"}}, {"$lookup": {"from": "internships", "localField": "internship_id", "foreignField": "_id", "as": "internship_info"}}, {"$unwind": "$student_info"}, {"$unwind": "$internship_info"}, {"$project": {"student_info.password": 0}}]
    applications = list(applications_collection.aggregate(pipeline))
    return jsonify(objectid_to_str(applications)), 200

@app.route('/api/mentor/applications', methods=['GET'])
@token_required
def get_mentor_applications():
    if g.current_user['role'] != 'mentor': return jsonify({"error": "Unauthorized"}), 403
    pipeline = [{"$match": {"status": "Applied"}}, {"$lookup": {"from": "users", "localField": "student_id", "foreignField": "_id", "as": "student_info"}}, {"$lookup": {"from": "internships", "localField": "internship_id", "foreignField": "_id", "as": "internship_info"}}, {"$unwind": "$student_info"}, {"$unwind": "$internship_info"}, {"$project": {"student_info.password": 0}}]
    applications = list(applications_collection.aggregate(pipeline))
    return jsonify(objectid_to_str(applications)), 200

@app.route('/api/applications/<application_id>/status', methods=['PUT'])
@token_required
def update_application_status(application_id):
    if g.current_user['role'] not in ['mentor', 'placement_cell']: return jsonify({"error": "Unauthorized"}), 403
    new_status = request.json.get('status')
    applications_collection.update_one({"_id": ObjectId(application_id)}, {"$set": {"status": new_status}})
    app_details = applications_collection.find_one({"_id": ObjectId(application_id)})
    student = users_collection.find_one({"_id": app_details['student_id']})
    internship = internships_collection.find_one({"_id": app_details['internship_id']})
    subject = f"Update on your application for {internship['title']}"
    body = f"Hello {student['name']},\n\nThe status of your application for {internship['title']} at {internship['company']} has been updated to: {new_status}.\n\nRegards,\nCampusConnect"
    send_email(student['email'], subject, body)
    return jsonify({"message": f"Status updated to {new_status}"}), 200

@app.route('/api/applications/<application_id>/schedule', methods=['PUT'])
@token_required
def schedule_interview(application_id):
    if g.current_user['role'] != 'placement_cell': return jsonify({"error": "Unauthorized"}), 403
    interview_slot = request.json.get('interview_slot')
    applications_collection.update_one({"_id": ObjectId(application_id)}, {"$set": {"interview_slot": interview_slot, "status": "Interview Scheduled"}})
    app_details = applications_collection.find_one({"_id": ObjectId(application_id)})
    student = users_collection.find_one({"_id": app_details['student_id']})
    internship = internships_collection.find_one({"_id": app_details['internship_id']})
    subject = f"Interview Scheduled for {internship['title']}"
    body = f"Hello {student['name']},\n\nAn interview has been scheduled for {internship['company']}.\n\nTime: {datetime.fromisoformat(interview_slot).strftime('%A, %B %d, %Y at %I:%M %p')}\n\nRegards,\nCampusConnect"
    send_email(student['email'], subject, body)
    return jsonify({"message": "Interview scheduled successfully"}), 200

# --- ADVANCED FEATURE ROUTES ---
@app.route('/api/student/recommendations', methods=['GET'])
@token_required
def get_recommendations():
    if g.current_user['role'] != 'student': return jsonify({"error": "Unauthorized"}), 403
    student_skills = set(g.current_user.get('skills', []))
    if not student_skills: return jsonify([]), 200
    all_internships = list(internships_collection.find({}))
    recommended = []
    for internship in all_internships:
        required_skills = set(internship.get('required_skills', []))
        match_count = len(student_skills.intersection(required_skills))
        if match_count > 0:
            internship['match_score'] = match_count
            internship['total_skills'] = len(required_skills)
            recommended.append(internship)
    recommended.sort(key=lambda x: x['match_score'], reverse=True)
    return jsonify(objectid_to_str(recommended)), 200

@app.route('/api/placement/analytics', methods=['GET'])
@token_required
def get_analytics():
    if g.current_user['role'] != 'placement_cell': return jsonify({"error": "Unauthorized"}), 403
    status_pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    status_data = list(applications_collection.aggregate(status_pipeline))
    company_pipeline = [{"$lookup": {"from": "internships", "localField": "internship_id", "foreignField": "_id", "as": "internship"}}, {"$unwind": "$internship"}, {"$group": {"_id": "$internship.company", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
    company_data = list(applications_collection.aggregate(company_pipeline))
    return jsonify({"status_distribution": status_data, "company_engagement": company_data}), 200

# --- FILE SERVING ---
@app.route('/uploads/resumes/<filename>')
@token_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- FRONTEND RENDERING ---
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/dashboard/student')
def student_dashboard():
    return render_template('dashboard_student.html')
@app.route('/dashboard/placement_cell')
def placement_dashboard():
    return render_template('dashboard_placement.html')
@app.route('/dashboard/mentor')
def mentor_dashboard():
    return render_template('dashboard_mentor.html')

# --- MAIN EXECUTION BLOCK ---
if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    app.run(debug=True, port=5000)

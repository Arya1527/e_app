from datetime import datetime
import smtplib
import qrcode
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from werkzeug.utils import secure_filename
import sqlite3
import base64
import json
import random
import threading
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey_jyoti_niketan_2026")

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ==================== CONFIG / SETTINGS HELPER ====================
CONFIG_FILE = 'school_config.json'

def get_school_config():
    default_config = {
        "school_name": "JYOTI NIKETAN H.S SCHOOL",
        "principal_name": "R.S Dwivedi",
        "school_address": "School Address Here",
        "academic_session": "2026"
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print("Config read error:", e)
            return default_config
    return default_config

def save_school_config(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.context_processor
def inject_config():
    return dict(config_data=get_school_config())

# =================== ADMIN OTP NOTIFIER (RENDER READY) ====================
# Render के Environment Variables रीड करना (अगर न मिले तो फ़ॉलबैक)
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "arya.ahirwar1998@gmail.com")
# ध्यान दें: अगर आप नए App Password जनरेट करें तो Render Dashboard पर अपडेट कर दें
ADMIN_APP_PASSWORD = os.environ.get("ADMIN_APP_PASSWORD", "cvts oqbw ephp wkhe")

def send_otp_to_admin(otp, user_identity):
    try:
        # App Password से स्पेस हटाना सुरक्षित रहता है
        pwd = ADMIN_APP_PASSWORD.replace(" ", "")
        
        subject = "🔑 Login OTP Alert for School Portal"
        body = f"नमस्कार,\n\nकिसी यूज़र ({user_identity}) ने आपके स्कूल प्रबंधन पोर्टल पर लॉगिन करने का प्रयास किया है।\n\nआपका Login OTP है: {otp}\n\nयह OTP केवल आपके पास भेजा गया है।"

        msg = MIMEMultipart()
        msg['From'] = ADMIN_EMAIL
        msg['To'] = ADMIN_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # SSL Port 465 (Render के लिए सबसे बेहतर और फ़ास्ट)
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10)
        server.login(ADMIN_EMAIL, pwd)
        server.sendmail(ADMIN_EMAIL, ADMIN_EMAIL, msg.as_string())
        server.quit()
        print("✅ OTP Email successfully sent to Admin!", flush=True)
    except Exception as e:
        print("❌ Email sending failed:", e, flush=True)

# Database Connection Helper
def get_db_connection():
    conn = sqlite3.connect('students.db', timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

# Login Protection Helper
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_authenticated'):
            flash('⚠️ Aryan_sir secure this please login first with OTP !', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Database Initialization
def init_db():
    conn = get_db_connection()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS student_master (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scholar_no TEXT UNIQUE NOT NULL,
        roll_no TEXT,
        name TEXT NOT NULL,
        father_name TEXT NOT NULL,
        mother_name TEXT,
        dob TEXT NOT NULL,
        gender TEXT,
        class_name TEXT NOT NULL,
        group_name TEXT,
        samagra_id TEXT,
        aadhaar_id TEXT,
        apaar_id TEXT,
        pen_number TEXT,
        mobile_no TEXT,
        bank_account TEXT,
        ifsc_code TEXT,
        address TEXT,
        admission_year TEXT DEFAULT "2026",
        status TEXT DEFAULT "Active",
        tc_reason TEXT,
        tc_date TEXT,
        photo_path TEXT,
        applicant_type TEXT DEFAULT 'नियमित-1',
        district_code TEXT,
        block_code TEXT,
        school_code TEXT,
        enrollment_code TEXT,
        sambal_no TEXT,
        caste TEXT,
        medium TEXT DEFAULT 'Hindi',
        stream TEXT
    )
    ''')

    cols = [col[1] for col in conn.execute("PRAGMA table_info(student_master)").fetchall()]
    fields_to_add = {
        'address': 'TEXT',
        'mobile_no': 'TEXT',
        'apaar_id': 'TEXT',
        'samagra_id': 'TEXT',
        'family_id': 'TEXT',
        'aadhaar_id': 'TEXT',
        'bank_account': 'TEXT',
        'ifsc_code': 'TEXT',
        'tc_reason': 'TEXT',
        'tc_date': 'TEXT',
        'applicant_type': "TEXT DEFAULT 'नियमित-1'",
        'district_code': 'TEXT',
        'block_code': 'TEXT',
        'school_code': 'TEXT',
        'enrollment_code': 'TEXT',
        'sambal_no': 'TEXT',
        'medium': "TEXT DEFAULT 'Hindi'",
        'stream': 'TEXT',
        'group_name': 'TEXT',
        'caste': 'TEXT'
    }

    for column_name, data_type in fields_to_add.items():
        if column_name not in cols:
            try:
                conn.execute(f"ALTER TABLE student_master ADD COLUMN {column_name} {data_type}")
            except Exception:
                pass

    conn.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            father_name TEXT,
            dob TEXT,
            roll_no TEXT NOT NULL,
            scholar_no TEXT,
            class_name TEXT NOT NULL,
            group_name TEXT,
            exam_type TEXT,
            teacher_name TEXT,
            scores TEXT NOT NULL,
            total_obtained REAL,
            total_max REAL,
            percentage REAL,
            result TEXT NOT NULL
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS exam_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT NOT NULL,
            paper_no INTEGER NOT NULL,
            exam_date TEXT,
            subject_name TEXT,
            UNIQUE(class_name, paper_no)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS teacher_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_name TEXT NOT NULL,
            mobile_no TEXT NOT NULL,
            email TEXT,
            aadhaar_no TEXT,
            subject_designation TEXT,
            photo_path TEXT,
            joining_date TEXT
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS student_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Present',
            FOREIGN KEY(student_id) REFERENCES student_master(id),
            UNIQUE(student_id, attendance_date)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS teacher_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Present',
            FOREIGN KEY(teacher_id) REFERENCES teacher_master(id),
            UNIQUE(teacher_id, attendance_date)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS fee_structure (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT UNIQUE,
            total_fee REAL
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS fee_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            amount_paid REAL,
            payment_date TEXT,
            payment_mode TEXT,
            receipt_no TEXT UNIQUE,
            FOREIGN KEY(student_id) REFERENCES student_master(id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS school_settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            school_name TEXT,
            address TEXT,
            phone TEXT,
            session TEXT,
            logo_path TEXT
        )
    ''')
    conn.execute('''
        INSERT OR IGNORE INTO school_settings (id, school_name, address, phone, session, logo_path)
        VALUES (1, 'JYOTI NIKETAN H.S SCHOOL', 'School Address Here', '9876543210', '2026-27', '')
    ''')

    conn.commit()
    conn.close()

# ऐप स्टार्ट होते ही DB इनिशियलाइज़ होगी
init_db()

# Save Camera Photo Helper
def save_camera_photo(photo_data, scholar_no):
    if not photo_data or not photo_data.startswith('data:image'):
        return ''
    try:
        header, encoded = photo_data.split(",", 1)
        data = base64.b64decode(encoded)
        filename = f"{scholar_no}_photo.png"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(filepath, "wb") as f:
            f.write(data)
        return filepath
    except Exception as e:
        print("Photo save error:", e)
        return ''

# Result Calculation Core Logic
def calculate_result(class_name, group_name, marks_dict):
    result = "Pass"
    processed_scores = {}
    total_obtained = 0.0
    total_max = 0.0

    def process_sub(sub, cutoff=19.8):
        nonlocal result, total_obtained, total_max
        t = float(marks_dict.get(f"{sub}_theory", 0) or 0)
        p = float(marks_dict.get(f"{sub}_project", 0) or 0)
        tot = round(t + p, 2)
        status = "Pass" if t >= cutoff else "Fail"
        if status == "Fail":
            result = "Fail"
        processed_scores[sub] = {'theory': t, 'project': p, 'total': tot, 'status': status}
        total_obtained += tot
        total_max += 100

    if class_name in ['Nursery', 'LKG', 'UKG']:
        for s in ['English', 'Hindi', 'Maths', 'Drawing']: process_sub(s, 19.8)
    elif class_name in ['1st', '2nd', '3rd', '4th', '5th']:
        for s in ['Hindi', 'English', 'Maths', 'Environment']: process_sub(s, 19.8)
    elif class_name in ['6th', '7th', '8th', '9th', '10th']:
        cutoff = 19.8 if class_name in ['6th', '7th', '8th'] else 24.75
        for s in ['Hindi', 'English', 'Maths', 'Science', 'Social_Science', 'Sanskrit']: process_sub(s, cutoff)
    elif class_name in ['11th', '12th']:
        for s in ['Hindi', 'English']: process_sub(s, 26.4)
        if group_name == 'Science':
            for s in ['Physics', 'Chemistry', 'Biology']: process_sub(s, 23.1)
        elif group_name == 'Maths':
            for s in ['Physics', 'Chemistry', 'Maths']: process_sub(s, 23.1)
        elif group_name == 'Commerce':
            for s in ['Accountancy', 'Business_Studies']: process_sub(s, 26.4)
            opt_sub = 'Informatics_Practices' if 'Informatics_Practices_theory' in marks_dict else 'Economics'
            process_sub(opt_sub, 26.4)
        elif group_name == 'Arts':
            for s in ['History', 'Political_Science', 'Geography']: process_sub(s, 26.4)

    percentage = round((total_obtained / total_max) * 100, 2) if total_max > 0 else 0.0
    return json.dumps(processed_scores), round(total_obtained, 2), round(total_max, 2), percentage, result

# ROUTES
@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/verify_otp_page')
def verify_otp_page():
    return render_template('verify_otp.html')

@app.route('/send_otp', methods=['POST'])
def send_otp():
    identity = request.form.get('identity', '').strip()
    if not identity:
        flash('❌ कृपया मोबाइल नंबर या ईमेल दर्ज करें!', 'danger')
        return redirect(url_for('login'))

    otp = str(random.randint(100000, 999999))
    session['generated_otp'] = otp
    session['user_identity'] = identity

    print(f"\n==========================================", flush=True)
    print(f"🔑 OTP FOR [{identity}]: {otp}", flush=True)
    print(f"==========================================", flush=True)

    # थ्रेडिंग द्वारा ईमेल भेजना
    threading.Thread(target=send_otp_to_admin, args=(otp, identity)).start()

    flash('✅ OTP आपके पंजीकृत ईमेल पर भेज दिया गया है!', 'info')
    return redirect(url_for('verify_otp_page'))

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    entered_otp = request.form.get('otp', '').strip()
    saved_otp = session.get('generated_otp')

    if saved_otp and entered_otp == saved_otp:
        session['is_authenticated'] = True
        session.pop('generated_otp', None)
        flash('🎉 Welcome! Login successful.', 'success')
        return redirect(url_for('index'))
    else:
        flash('❌ अमान्य OTP! कृपया दोबारा प्रयास करें।', 'danger')
        return redirect(url_for('verify_otp_page'))

@app.route('/logout')
def logout():
    session.clear()
    flash('🔒 आप सफलतापूर्वक लॉगआउट हो चुके हैं।', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    class_filter = request.args.get('class_name', '')
    filter_type = request.args.get('filter', '')
    search_query = request.args.get('search', '').strip()

    conn = get_db_connection()
    query = "SELECT * FROM students WHERE 1=1"
    params = []

    if class_filter:
        query += " AND class_name = ?"
        params.append(class_filter)
    if search_query:
        query += " AND (name LIKE ? OR roll_no LIKE ? OR scholar_no LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])

    if filter_type == 'above_80':
        query += " AND percentage >= 80"
    elif filter_type == 'fail':
        query += " AND result = 'Fail'"

    query += " ORDER BY class_name, CAST(roll_no AS INTEGER)"
    students = conn.execute(query, params).fetchall()

    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_fail = conn.execute("SELECT COUNT(*) FROM students WHERE result='Fail'").fetchone()[0]
    total_above_80 = conn.execute("SELECT COUNT(*) FROM students WHERE percentage>=80").fetchone()[0]
    conn.close()

    formatted_students = []
    for s in students:
        try:
            scores_dict = json.loads(s['scores'])
        except Exception:
            scores_dict = {}
        formatted_students.append({
            'id': s['id'], 'name': s['name'], 'father_name': s['father_name'], 'dob': s['dob'],
            'roll_no': s['roll_no'], 'scholar_no': s['scholar_no'], 'class_name': s['class_name'],
            'group_name': s['group_name'], 'exam_type': s['exam_type'], 'teacher_name': s['teacher_name'],
            'scores': scores_dict, 'total_obtained': s['total_obtained'],
            'total_max': s['total_max'], 'percentage': s['percentage'], 'result': s['result']
        })

    return render_template('index.html', students=formatted_students, stats={'total': total_students, 'fail': total_fail, 'above_80': total_above_80}, selected_class=class_filter)

# ==================== RENDER DEPLOYMENT ENTRY POINT ====================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

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
app.secret_key = "supersecretkey_jyoti_niketan"

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

# ==================== ADMIN OTP NOTIFIER ====================
ADMIN_EMAIL = "arya.ahirwar1998@gmail.com"
ADMIN_APP_PASSWORD = "cvts oqbw ephp wkhe"

def send_otp_to_admin(otp, user_identity):
    try:
        subject = "🔑 Login OTP Alert for School Portal"
        body = f"नमस्कार,\n\nकिसी यूज़र ({user_identity}) ने आपके स्कूल प्रबंधन पोर्टल पर लॉगिन करने का प्रयास किया है।\n\nआपका Login OTP है: {otp}\n\nयह OTP केवल आपके पास भेजा गया है।"

        msg = MIMEMultipart()
        msg['From'] = ADMIN_EMAIL
        msg['To'] = ADMIN_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(ADMIN_EMAIL, ADMIN_APP_PASSWORD)
        text = msg.as_string()
        server.sendmail(ADMIN_EMAIL, ADMIN_EMAIL, text)
        server.quit()
        print("✅ OTP Email successfully sent to Admin!")
    except Exception as e:
        print("❌ Email sending failed:", e)

# Database Connection Helper
def get_db_connection():
    conn = sqlite3.connect('students.db', timeout=20)
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

# Database Initialization & Auto Migration Helper
# Database Initialization & Auto Migration Helper
def init_db():
    conn = get_db_connection()
    
    # 1. Master Student Records Table
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

    # Migration Check for Existing Database
    cols = [col[1] for col in conn.execute("PRAGMA table_info(student_master)").fetchall()]
    if 'address' not in cols:
        conn.execute("ALTER TABLE student_master ADD COLUMN address TEXT")
    if 'bank_account' not in cols:
        conn.execute("ALTER TABLE student_master ADD COLUMN bank_account TEXT")
    if 'ifsc_code' not in cols:
        conn.execute("ALTER TABLE student_master ADD COLUMN ifsc_code TEXT")
    if 'tc_reason' not in cols:
        conn.execute("ALTER TABLE student_master ADD COLUMN tc_reason TEXT")
    if 'tc_date' not in cols:
        conn.execute("ALTER TABLE student_master ADD COLUMN tc_date TEXT")
    if 'gender' not in cols:
        conn.execute("ALTER TABLE student_master ADD COLUMN gender TEXT")
    
    # Exam Form Additional Columns Migration Check
    if 'applicant_type' not in cols:
        conn.execute("ALTER TABLE student_master ADD COLUMN applicant_type TEXT DEFAULT 'नियमित-1'")
    if 'district_code' not in cols:
        conn.execute("ALTER TABLE student_master ADD COLUMN district_code TEXT")
    if 'block_code' not in cols:
        conn.execute("ALTER TABLE student_master ADD COLUMN block_code TEXT")
    if 'school_code' not in cols:
        conn.execute("ALTER TABLE student_master ADD COLUMN school_code TEXT")
    if 'enrollment_code' not in cols:
        conn.execute("ALTER TABLE student_master ADD COLUMN enrollment_code TEXT")
    if 'sambal_no' not in cols:
        conn.execute("ALTER TABLE student_master ADD COLUMN sambal_no TEXT")
    if 'medium' not in cols:
        conn.execute("ALTER TABLE student_master ADD COLUMN medium TEXT DEFAULT 'Hindi'")
    if 'stream' not in cols:
        conn.execute("ALTER TABLE student_master ADD COLUMN stream TEXT")
    if 'group_name' not in cols:
        conn.execute("ALTER TABLE student_master ADD COLUMN group_name TEXT")
    if "caste" not in cols:
        conn.execute("ALTER TABLE student_master ADD COLUMN caste TEXT")

    # Complete Migration Check for student_master Table
    cols = [col[1] for col in conn.execute("PRAGMA table_info(student_master)").fetchall()]
    
    fields_to_add = {
        'address': 'TEXT',
        'mobile': 'TEXT',
        'apaar_id': 'TEXT',
        'sssmid': 'TEXT',
        'family_id': 'TEXT',
        'aadhaar': 'TEXT',
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
        'group_name': 'TEXT'
    }

    for column_name, data_type in fields_to_add.items():
        if column_name not in cols:
            conn.execute(f"ALTER TABLE student_master ADD COLUMN {column_name} {data_type}")


    # 2. Student Marks & Results Table
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

    # 3. Exam Schedule Table
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

    # 4. Teacher Master Table
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

    # 5. Exam Marks Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS exam_marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            exam_term TEXT,
            subject_name TEXT,
            marks_obtained REAL,
            total_marks REAL,
            FOREIGN KEY(student_id) REFERENCES student_master(id),
            UNIQUE(student_id, exam_term, subject_name)
        )
    ''')

    # 6. Student Attendance Table
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

    # 7. Teacher Attendance Table
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

    # 8. Fee Structure Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS fee_structure (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT UNIQUE,
            total_fee REAL
        )
    ''')

    # 9. Fee Transactions Table
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

    # 10. School Settings Table
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


# Save Camera Base64 Image Helper
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

# Result & Marks Calculation Core Logic
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
        for s in ['English', 'Hindi', 'Maths', 'Drawing']:
            process_sub(s, 19.8)
    elif class_name in ['1st', '2nd', '3rd', '4th', '5th']:
        for s in ['Hindi', 'English', 'Maths', 'Environment']:
            process_sub(s, 19.8)
    elif class_name in ['6th', '7th', '8th', '9th', '10th']:
        cutoff = 19.8 if class_name in ['6th', '7th', '8th'] else 24.75
        for s in ['Hindi', 'English', 'Maths', 'Science', 'Social_Science', 'Sanskrit']:
            process_sub(s, cutoff)
    elif class_name in ['11th', '12th']:
        for s in ['Hindi', 'English']:
            process_sub(s, 26.4)
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
# JSON डेटा लोड और सेव फंक्शन
def load_students():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_students(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route('/update_form', methods=['POST'])
def update_form():
    data = request.json
    scholar_no = data.get('scholar_no')

    # यहाँ अपने डेटाबेस या JSON फाइल को अपडेट करने का लॉजिक लिखें
    # उदाहरण के लिए:
    # db.execute("UPDATE students SET name=?, father_name=? WHERE scholar_no=?", (data['name'], data['father_name'], scholar_no))

    print("Updated Data Received:", data)  # कंसोल में चेक करने के लिए

    return jsonify({'success': True, 'message': 'Data updated successfully!'})
# 1. सभी फ़ॉर्म्स देखने और प्रिंट करने का Route
@app.route('/print_form')
def print_form():
    students = load_students()
    return render_template('print_form.html', students=students)


# 3. फॉर्म एडिट (Edit) करने का Route
@app.route('/edit_form/<scholar_no>')
def edit_form(scholar_no):
    students = load_students()
    student = next((s for s in students if str(s.get('scholar_no')) == str(scholar_no)), None)
    if student:
        return render_template('exam_form.html', data=student)
    return redirect(url_for('print_form'))

# 4. फॉर्म डिलीट (Delete) करने का Route
@app.route('/delete_form/<scholar_no>')
def delete_form(scholar_no):
    students = load_students()
    students = [s for s in students if str(s.get('scholar_no')) != str(scholar_no)]
    save_students(students)
    return redirect(url_for('print_form'))


# ALL ROUTE HANDLERS
@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/send_otp', methods=['POST'])
def send_otp():
    identity = request.form.get('identity', '').strip()
    if not identity:
        flash('❌ कृपया मोबाइल नंबर या ईमेल दर्ज करें!', 'danger')
        return redirect(url_for('login'))

    otp = str(random.randint(100000, 999999))
    session['generated_otp'] = otp
    session['user_identity'] = identity

    print(f"\n==========================================")
    print(f"🔑 OTP FOR [{identity}]: {otp}")
    print(f"==========================================\n")

    threading.Thread(target=send_otp_to_admin, args=(otp, identity)).start()

    flash(f'✅ OTP आपके पंजीकृत ईमेल पर भेज दिया गया है!', 'info')
    return redirect(url_for('verify_otp_page'))

@app.route('/verify_otp_page')
def verify_otp_page():
    if 'generated_otp' not in session:
        return redirect(url_for('login'))
    return render_template('verify_otp.html')

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


@app.route('/student_quick_view')
@login_required
def student_quick_view():
    selected_class = request.args.get('class_name', '').strip()
    search = request.args.get('search', '').strip()
    sort_alpha = request.args.get('sort_alpha')  # A-Z Sorting के लिए
    selected_fields = request.args.getlist('fields')
    
    if not selected_fields and 'class_name' not in request.args:
        selected_fields = ['scholar_no', 'father_name', 'mother_name', 'dob']
        
    conn = get_db_connection()
    sql = "SELECT * FROM student_master WHERE 1=1"
    params = []
    
    if selected_class:
        sql += " AND class_name = ?"
        params.append(selected_class)
    if search:
        sql += " AND (scholar_no LIKE ? OR name LIKE ? OR roll_no LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        
    # अल्फाबेटिकल सॉर्टिंग या डिफ़ॉल्ट सॉर्टिंग
    if sort_alpha:
        sql += " ORDER BY name ASC"
    else:
        sql += " ORDER BY class_name, scholar_no"
        
    students_raw = conn.execute(sql, params).fetchall()
    conn.close()
    
    students = []
    for s in students_raw:
        students.append({
            'id': s['id'],
            'class_name': s['class_name'],
            'name': s['name'],
            'scholar_no': s['scholar_no'],
            'father_name': s['father_name'],
            'mother_name': s['mother_name'] if 'mother_name' in s.keys() else '',
            'dob': s['dob'] if 'dob' in s.keys() else '',
            'mobile_no': s['mobile_no'] if 'mobile_no' in s.keys() else '',
            'aadhaar_no': s['aadhaar_id'] if 'aadhaar_id' in s.keys() else '',
            'bank_acc_no': s['bank_account'] if 'bank_account' in s.keys() else '',
            'ifsc_code': s['ifsc_code'] if 'ifsc_code' in s.keys() else ''
        })
        
    return render_template(
        'student_quick_view.html',
        students=students,
        selected_class=selected_class,
        selected_fields=selected_fields
    )


@app.route('/promote_students', methods=['GET', 'POST'])
@login_required
def promote_students():
    conn = get_db_connection()
    classes = ['Nursery', 'LKG', 'UKG', '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', '11th', '12th']

    selected_class = request.args.get('class_name', '').strip()
    students = []

    if selected_class:
        students = conn.execute(
            "SELECT * FROM student_master WHERE class_name = ? AND (status IS NULL OR status = 'Active') ORDER BY scholar_no",
            (selected_class,)
        ).fetchall()

    if request.method == 'POST':
        current_class = request.form.get('current_class', '').strip()
        target_class = request.form.get('target_class', '').strip()
        student_ids = request.form.getlist('student_ids')

        if target_class and student_ids:
            placeholders = ','.join(['?'] * len(student_ids))
            query = f"UPDATE student_master SET class_name = ? WHERE id IN ({placeholders})"
            params = [target_class] + student_ids
            conn.execute(query, params)
            conn.commit()
            flash(f"✅ चुने गए छात्रों को सफलतापूर्वक कक्षा {target_class} में प्रमोट कर दिया गया है!", "success")
        else:
            flash("⚠️ कृपया नई कक्षा चुनें और कम से कम एक छात्र को टिक (Select) करें।", "warning")

        conn.close()
        return redirect(url_for('promote_students', class_name=current_class))

    conn.close()
    return render_template('promote_students.html', students=students, selected_class=selected_class, classes=classes)

@app.route('/tc_management', methods=['GET', 'POST'])
@login_required
def tc_management():
    conn = get_db_connection()
    classes = ['Nursery', 'LKG', 'UKG', '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', '11th', '12th']

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        tc_reason = request.form.get('tc_reason', 'School Left / Relocation')
        tc_date = request.form.get('tc_date')

        if student_id:
            conn.execute(
                "UPDATE student_master SET status = 'TC Issued', tc_reason = ?, tc_date = ? WHERE id = ?",
                (tc_reason, tc_date, student_id)
            )
            conn.commit()
            flash("✅ छात्र का T.C. सफलतापूर्वक दर्ज (Issue) कर दिया गया है!", "success")
        conn.close()
        return redirect(url_for('tc_management'))

    selected_class = request.args.get('class_name', '').strip()
    search = request.args.get('search', '').strip()

    active_students = []
    if selected_class or search:
        sql = "SELECT * FROM student_master WHERE (status IS NULL OR status = 'Active')"
        params = []
        if selected_class:
            sql += " AND class_name = ?"
            params.append(selected_class)
        if search:
            sql += " AND (scholar_no LIKE ? OR name LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        sql += " ORDER BY scholar_no"
        active_students = conn.execute(sql, params).fetchall()

    tc_issued_students = conn.execute(
        "SELECT * FROM student_master WHERE status = 'TC Issued' ORDER BY id DESC"
    ).fetchall()

    conn.close()
    return render_template(
        'tc_management.html',
        classes=classes,
        active_students=active_students,
        tc_issued_students=tc_issued_students,
        selected_class=selected_class
    )

from datetime import datetime

@app.route('/class_result_list')
@login_required
def class_result_list():
    selected_class = request.args.get('class_name', '10th')
    conn = get_db_connection()

    # Get all students of selected class ordered by Roll No / Scholar No
    students_raw = conn.execute(
        "SELECT * FROM students WHERE class_name = ? ORDER BY CAST(roll_no AS INTEGER), scholar_no",
        (selected_class,)
    ).fetchall()

    conn.close()

    config = get_school_config()
    students = []
    
    # Calculate Summary Stats
    total_appeared = len(students_raw)
    total_passed = 0
    total_failed = 0

    for s in students_raw:
        s_dict = dict(s)
        try:
            s_dict['scores'] = json.loads(s_dict['scores'])
        except Exception:
            s_dict['scores'] = {}

        if s_dict.get('result') == 'Pass':
            total_passed += 1
        else:
            total_failed += 1

        students.append(s_dict)

    pass_percentage = round((total_passed / total_appeared) * 100, 2) if total_appeared > 0 else 0

    stats = {
        'total': total_appeared,
        'passed': total_passed,
        'failed': total_failed,
        'pass_percentage': pass_percentage
    }

    return render_template(
        'class_result_list.html',
        students=students,
        selected_class=selected_class,
        stats=stats,
        principal_name=config.get('principal_name', 'Principal')
    )

# ==================== QR CODE GENERATOR ROUTE ====================
@app.route('/student_qr/<scholar_no>')
def student_qr(scholar_no):
    # यह URL वही है जिसे स्कैन करके टीचर पब्लिक डिटेल पेज पर पहुंचेगा
    target_url = request.host_url.rstrip('/') + url_for('view_student_by_scholar', scholar_no=scholar_no)
    
    # QR Code इमेज बनाना
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(target_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # मेमोरी में ही इमेज रिटर्न करना (बिना सेव किए)
    from io import BytesIO
    from flask import send_file
    buf = BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


# Direct QR Scan View Route (बिना फॉर्म भरे सीधा देखने के लिए)
@app.route('/view_student/<scholar_no>')
def view_student_by_scholar(scholar_no):
    conn = get_db_connection()
    student = conn.execute(
        "SELECT * FROM student_master WHERE scholar_no = ?",
        (scholar_no,)
    ).fetchone()
    conn.close()

    if student:
        return render_template('public_student_view.html', student=dict(student))
        
    flash('❌ इस स्कॉलर नंबर का कोई छात्र नहीं मिला!', 'danger')
    return redirect(url_for('public_student_search'))


#STUDENT_ ATTENDANCE VIEW / MONTHLY REPORT
@app.route('/attendance_report', methods=['GET'])
@login_required
def attendance_report():
    cls = request.args.get('class_name', '')
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    
    conn = get_db_connection()
    report = []
    working_days = 0
    
    if cls and month:
        # 1. कुल कार्य दिवस (Working Days) की सही क्वेरी
        wd_row = conn.execute("""
            SELECT COUNT(DISTINCT a.attendance_date) as total 
            FROM student_attendance a
            JOIN student_master s ON a.student_id = s.id
            WHERE s.class_name = ? AND strftime('%Y-%m', a.attendance_date) = ?
        """, (cls, month)).fetchone()
        
        working_days = wd_row['total'] if wd_row and wd_row['total'] else 0

        # 2. छात्रवार उपस्थिति का विवरण
        students = conn.execute("""
            SELECT s.scholar_no, s.name, s.mobile_no as father_phone,
                   SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present_days,
                   SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as absent_days
            FROM student_master s
            LEFT JOIN student_attendance a ON s.id = a.student_id AND strftime('%Y-%m', a.attendance_date) = ?
            WHERE s.class_name = ?
            GROUP BY s.id, s.scholar_no, s.name, s.mobile_no
            ORDER BY s.name
        """, (month, cls)).fetchall()
        
        for st in students:
            p_days = st['present_days'] or 0
            a_days = st['absent_days'] or 0
            pct = round((p_days / working_days) * 100, 1) if working_days > 0 else 0
            
            sms_text = f"पूज्य अभिभावक, आपके छात्र {st['name']} की माह {month} की उपस्थिति रिपोर्ट: कुल {working_days} दिन में से {p_days} दिन उपस्थित, {a_days} दिन अनुपस्थित रहे। उपस्थिति: {pct}%"
            
            report.append({
                'scholar_no': st['scholar_no'],
                'name': st['name'],
                'father_phone': st['father_phone'],
                'present_days': p_days,
                'absent_days': a_days,
                'percentage': pct,
                'sms_text': sms_text
            })
            
    conn.close()
    return render_template('attendance_report.html', report=report, selected_class=cls, selected_month=month, working_days=working_days)


@app.route('/register', methods=['GET', 'POST'])
@login_required
def register_student():
    if request.method == 'POST':
        scholar_no = request.form.get('scholar_no', '').strip()
        name = request.form.get('name', '').strip()
        father_name = request.form.get('father_name', '').strip()
        mother_name = request.form.get('mother_name', '').strip()
        dob = request.form.get('dob', '').strip()

        gender = request.form.get('gender', 'Boy').strip()
        class_name = request.form.get('class_name', '').strip()
        samagra_id = request.form.get('samagra_id', '').strip()
        aadhaar_id = request.form.get('aadhaar_id', '').strip()
        apaar_id = request.form.get('apaar_id', '').strip()
        pen_number = request.form.get('pen_number', '').strip()
        mobile_no = request.form.get('mobile_no', '').strip()

        address = request.form.get('address', '').strip()
        bank_account = request.form.get('bank_account', '').strip()
        ifsc_code = request.form.get('ifsc_code', '').strip()

        photo_path = ''

        file = (request.files.get('student_photo') or
                request.files.get('student_photo_back') or
                request.files.get('student_photo_front'))
        captured_data = request.form.get('captured_image_data')

        if file and file.filename != '':
            filename = f"{scholar_no}_{file.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            photo_path = filepath
        elif captured_data and captured_data != '':
            photo_path = save_camera_photo(captured_data, scholar_no)

        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO student_master
                (scholar_no, name, father_name, mother_name, dob, gender, class_name, samagra_id, aadhaar_id, apaar_id, pen_number, mobile_no, bank_account, ifsc_code, address, photo_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (scholar_no, name, father_name, mother_name, dob, gender, class_name, samagra_id, aadhaar_id, apaar_id, pen_number, mobile_no, bank_account, ifsc_code, address, photo_path))
            conn.commit()
            flash('✅ Student registration successful!', 'success')
        except sqlite3.IntegrityError:
            flash('⚠️ Duplicate Scholar No! Record already exists.', 'danger')
        except Exception as e:
            flash(f'❌ Registration failed: {str(e)}', 'danger')
        finally:
            conn.close()

        return redirect(url_for('register_student'))

    return render_template('register.html')

@app.route("/student_info")
@login_required
def student_info_panel():
    selected_class = request.args.get("class_name", "").strip()
    selected_year = request.args.get("birth_year", "").strip()
    selected_gender = request.args.get("gender", "").strip()
    selected_caste = request.args.get("caste", "").strip()
    missing_info = request.args.get("missing_info", "").strip()
    search_q = request.args.get("search", "").strip()

    conn = get_db_connection()

    # Dropdowns ke liye Lists
    classes_list = conn.execute("SELECT DISTINCT class_name FROM student_master WHERE class_name IS NOT NULL AND class_name != '' ORDER BY class_name").fetchall()
    classes = [c['class_name'] for c in classes_list]

    castes_list = conn.execute("SELECT DISTINCT caste FROM student_master WHERE caste IS NOT NULL AND caste != '' ORDER BY caste").fetchall()
    castes = [c['caste'] for c in castes_list]

    # Dynamic SQL Query Building
    sql = "SELECT * FROM student_master WHERE 1=1"
    params = []

    if selected_class:
        sql += " AND class_name = ?"
        params.append(selected_class)

    if selected_year:
        sql += " AND (dob LIKE ? OR dob LIKE ?)"
        params.extend([f"%{selected_year}%", f"{selected_year}-%"])

    if selected_gender:
        sql += " AND gender = ?"
        params.append(selected_gender)

    if selected_caste:
        sql += " AND caste = ?"
        params.append(selected_caste)

    if missing_info == "no_mobile":
        sql += " AND (mobile_no IS NULL OR mobile_no = '')"
    elif missing_info == "no_aadhaar":
        sql += " AND (aadhaar_id IS NULL OR aadhaar_id = '')"
    elif missing_info == "no_samagra":
        sql += " AND (samagra_id IS NULL OR samagra_id = '')"
    elif missing_info == "incomplete":
        sql += " AND (mobile_no IS NULL OR mobile_no = '' OR aadhaar_id IS NULL OR aadhaar_id = '' OR samagra_id IS NULL OR samagra_id = '')"

    if search_q:
        sql += " AND (scholar_no LIKE ? OR name LIKE ? OR father_name LIKE ?)"
        params.extend([f"%{search_q}%", f"%{search_q}%", f"%{search_q}%"])

    sql += " ORDER BY class_name, scholar_no"
    students = conn.execute(sql, params).fetchall()

    # --- Analytics & Counts ---
    # Class-wise Counts
    summary_rows = conn.execute("SELECT class_name, COUNT(*) as count FROM student_master WHERE class_name IS NOT NULL AND class_name != '' GROUP BY class_name").fetchall()
    class_counts = {r['class_name']: r['count'] for r in summary_rows}
    total_students = sum(class_counts.values())

    # Caste-wise Counts
    caste_rows = conn.execute("SELECT CASE WHEN caste IS NULL OR caste = '' THEN 'Unassigned' ELSE caste END as caste_name, COUNT(*) as count FROM student_master GROUP BY caste_name").fetchall()
    caste_counts = {r['caste_name']: r['count'] for r in caste_rows}

    # Gender Counts
    total_boys = conn.execute("SELECT COUNT(*) FROM student_master WHERE gender = 'Boy'").fetchone()[0]
    total_girls = conn.execute("SELECT COUNT(*) FROM student_master WHERE gender = 'Girl'").fetchone()[0]

    # Missing Info Counts
    has_mobile_count = conn.execute("SELECT COUNT(*) FROM student_master WHERE mobile_no IS NOT NULL AND mobile_no != ''").fetchone()[0]
    no_mobile_count = total_students - has_mobile_count

    conn.close()

    return render_template('student_info.html',
                           students=students,
                           classes=classes,
                           castes=castes,
                           class_counts=class_counts,
                           caste_counts=caste_counts,
                           total_students=total_students,
                           total_boys=total_boys,
                           total_girls=total_girls,
                           no_mobile_count=no_mobile_count,
                           selected_class=selected_class,
                           selected_year=selected_year,
                           selected_gender=selected_gender,
                           selected_caste=selected_caste,
                           missing_info=missing_info,
                           search_q=search_q)


@app.route('/update_photo/<int:id>', methods=['POST'])
def update_student_photo(id):
    conn = get_db_connection()
    student = conn.execute("SELECT scholar_no FROM student_master WHERE id = ?", (id,)).fetchone()
    if not student:
        conn.close()
        flash("Student record not found!", "danger")
        return redirect(url_for('student_info_panel'))

    scholar_no = student['scholar_no']
    photo_path = ''
    file = request.files.get('student_photo')
    captured_data = request.form.get('captured_image_data')

    if file and file.filename != '':
        filename = f"{scholar_no}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        photo_path = filepath
    elif captured_data and captured_data != '':
        photo_path = save_camera_photo(captured_data, scholar_no)

    if photo_path:
        conn.execute("UPDATE student_master SET photo_path = ? WHERE id = ?", (photo_path, id))
        conn.commit()
        flash(" Photo Updated Successfully!", "success")
    else:
        flash(" No photo selected or captured!", "warning")

    conn.close()
    return redirect(request.referrer or url_for('student_info_panel'))

@app.route('/get_student_info', methods=['GET'])
@login_required
def get_student_info():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({'success': False, 'message': 'Query empty'})

    conn = get_db_connection()
    student = conn.execute("SELECT * FROM student_master WHERE scholar_no = ? OR roll_no = ?", (query, query)).fetchone()
    conn.close()

    if student:
        return jsonify({
            'success': True,
            'name': student['name'],
            'father_name': student['father_name'],
            'dob': student['dob'],
            'roll_no': student['roll_no'] or '',
            'scholar_no': student['scholar_no'],
            'class_name': student['class_name'],
            'group_name': student['group_name'] or ''
        })
    return jsonify({'success': False, 'message': 'Student Not Found'})

@app.route('/teacher', methods=['GET', 'POST'])
def teacher_panel():
    if request.method == 'POST':
        name = request.form['name'].strip()
        father_name = request.form.get('father_name', '').strip()
        dob = request.form.get('dob', '')
        roll_no = request.form['roll_no'].strip()
        scholar_no = request.form.get('scholar_no', '').strip()
        class_name = request.form['class_name']
        group_name = request.form.get('group_name', '')
        exam_type = request.form.get('exam_type', 'Annual Exam')
        teacher_name = request.form.get('teacher_name', '').strip()

        scores_str, tot_ob, tot_mx, pct, result = calculate_result(class_name, group_name, request.form)
        conn = get_db_connection()
        conn.execute('''INSERT OR REPLACE INTO students
            (name, father_name, dob, roll_no, scholar_no, class_name, group_name, exam_type, teacher_name, scores, total_obtained, total_max, percentage, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (name, father_name, dob, roll_no, scholar_no, class_name, group_name, exam_type, teacher_name, scores_str, tot_ob, tot_mx, pct, result))
        conn.commit()
        conn.close()
        flash("✅ Marks Saved Successfully!", "success")
        return redirect(url_for('index'))

    return render_template('teacher.html')

@app.route('/timetable', methods=['GET', 'POST'])
def timetable_view():
    conn = get_db_connection()
    selected_class = request.args.get('class_name', '10th')

    schedules = conn.execute("SELECT * FROM exam_schedule WHERE class_name = ? ORDER BY paper_no", (selected_class,)).fetchall()

    if request.method == 'POST':
        selected_class = request.form.get('class_name')
        for i in range(1, 7):
            exam_date = request.form.get(f'date_{i}', '').strip()
            subject_name = request.form.get(f'subject_{i}', '').strip()
            if subject_name:
                conn.execute('''
                    INSERT INTO exam_schedule (class_name, paper_no, exam_date, subject_name)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(class_name, paper_no) DO UPDATE SET
                        exam_date = excluded.exam_date,
                        subject_name = excluded.subject_name
                ''', (selected_class, i, exam_date, subject_name))
        conn.commit()
        flash("✅ Timetable Saved Successfully!", "success")
        return redirect(url_for('timetable_view', class_name=selected_class))

    conn.close()
    return render_template('timetable.html', schedules=schedules, selected_class=selected_class)

@app.route('/save_timetable', methods=['POST'])
@login_required
def save_timetable():
    selected_class = request.form.get('class_name', '10th')
    conn = get_db_connection()

    # 1. इस क्लास का पुराना टाइमटेबल डिलीट करें (जिससे पुराना/हटाया गया डेटा पूरी तरह हट जाए)
    conn.execute("DELETE FROM exam_schedule WHERE class_name = ?", (selected_class,))

    # 2. नए इनपुट्स को सेव करें
    for i in range(1, 7):
        date_val = request.form.get(f'date_{i}', '').strip()
        subj_val = request.form.get(f'subject_{i}', '').strip()

        # अगर विषय या तारीख में से कुछ भी भरा हो तो ही डेटाबेस में डालें
        if subj_val or date_val:
            conn.execute('''
                INSERT INTO exam_schedule (class_name, paper_no, exam_date, subject_name)
                VALUES (?, ?, ?, ?)
            ''', (selected_class, i, date_val, subj_val))

    conn.commit()
    conn.close()
    
    flash("✅ Timetable Saved Successfully!", "success")
    return redirect(url_for('admit_card_panel', class_name=selected_class))


@app.route('/admit_card', methods=['GET', 'POST'])
@login_required
def admit_card_panel():
    conn = get_db_connection()

    # रोल नंबर सेव करने का लॉजिक
    if request.method == 'POST':
        student_ids = request.form.getlist('student_ids')
        for sid in student_ids:
            roll = request.form.get(f'roll_{sid}', '').strip()
            conn.execute("UPDATE student_master SET roll_no = ? WHERE id = ?", (roll, sid))
        conn.commit()
        flash('✅ Roll Numbers Saved Successfully!', 'success')

    selected_class = request.args.get('class_name', '10th')

    # डेटाबेस से छात्रों को फेच करना
    students_raw = conn.execute("SELECT * FROM student_master WHERE class_name = ?", (selected_class,)).fetchall()

    # छात्रों को नाम के हिसाब से A-Z सॉर्ट करना
    students = sorted(students_raw, key=lambda s: s['name'].lower() if s['name'] else '')

    # टाइमटेबल को paper_no के क्रम में फेच करना (ORDER BY paper_no ASC जोड़ा गया है)
    timetable = conn.execute(
        "SELECT * FROM exam_schedule WHERE class_name = ? ORDER BY paper_no ASC", 
        (selected_class,)
    ).fetchall()

    conn.close()
    return render_template('admit_card.html', students=students, timetable=timetable, selected_class=selected_class)


@app.route('/exam_control')
def exam_control():
    conn = get_db_connection()
    c1 = request.args.get('class1', '9th')
    c2 = request.args.get('class2', '')

    # 1. Students को Fetch करें (अगर Merged Class2 चुनी है तो दोनों क्लासेस के स्टूडेंट्स आएँगे)
    if c2:
        students_raw = conn.execute(
            "SELECT * FROM student_master WHERE class_name IN (?, ?)", (c1, c2)
        ).fetchall()
    else:
        students_raw = conn.execute(
            "SELECT * FROM student_master WHERE class_name = ?", (c1,)
        ).fetchall()

    # dict में कन्वर्ट करें ताकि Template में roll_no और डेटा सही से रीड हो सके
    students = [dict(s) for s in students_raw]

    # 2. Exam Timetable Fetch करें (Class 1 के आधार पर)
    timetable_raw = conn.execute(
        "SELECT * FROM exam_schedule WHERE class_name = ? ORDER BY paper_no ASC", (c1,)
    ).fetchall()
    timetable = [dict(t) for t in timetable_raw]

    conn.close()

    return render_template(
        'exam_sheet.html', 
        students=students, 
        timetable=timetable, 
        c1=c1, 
        c2=c2
    )


@app.route('/report_card/<int:id>')
def report_card(id):
    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (id,)).fetchone()
    
    # सेटिंग्स डेटाबेस से स्कूल सेटिंग्स निकालना
    settings_data = conn.execute("SELECT * FROM school_settings WHERE id = 1").fetchone()
    conn.close()

    config = get_school_config()
    s_data = dict(student) if student else {}
    try:
        s_data['scores'] = json.loads(s_data['scores'])
    except Exception:
        s_data['scores'] = {}

    return render_template(
        'report_card.html', 
        student=s_data, 
        principal_name=config.get('principal_name'),
        settings=dict(settings_data) if settings_data else {}
    )


@app.route('/bulk_report_cards')
def bulk_report_cards():
    conn = get_db_connection()
    class_name = request.args.get('class_name', '')
    scholar_no = request.args.get('scholar_no', '')
    exam_type = request.args.get('exam_type', 'First Terminal Exam')

    query = "SELECT * FROM students WHERE 1=1"
    params = []

    if class_name:
        query += " AND class_name = ?"
        params.append(class_name)
    if scholar_no:
        query += " AND (scholar_no LIKE ? OR name LIKE ? OR roll_no LIKE ?)"
        params.extend([f"%{scholar_no}%", f"%{scholar_no}%", f"%{scholar_no}%"])

    raw_students = conn.execute(query, params).fetchall()
    conn.close()

    config = get_school_config()
    students = []
    for s in raw_students:
        s_dict = dict(s)

        if isinstance(s_dict.get('scores'), str):
            try:
                s_dict['scores'] = json.loads(s_dict['scores'])
            except Exception:
                s_dict['scores'] = {}
        elif not s_dict.get('scores'):
            s_dict['scores'] = {}

        total_obtained = 0.0
        total_max = 0.0
        for sub, marks in s_dict['scores'].items():
            if isinstance(marks, dict):
                th = float(marks.get('theory', 0) or 0)
                pr = float(marks.get('project', marks.get('practical', 0)) or 0)
                tot = float(marks.get('total', th + pr) or 0)
                total_obtained += tot
                total_max += 100.0

        s_dict['total_obtained'] = s_dict.get('total_obtained') or round(total_obtained, 2)
        s_dict['total_max'] = s_dict.get('total_max') or round(total_max, 2)
        students.append(s_dict)

    return render_template('bulk_report_card.html', students=students, exam_type=exam_type, principal_name=config.get('principal_name', 'Principal'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (id,)).fetchone()

    if request.method == 'POST':
        name = request.form['name'].strip()
        father_name = request.form.get('father_name', '').strip()
        dob = request.form.get('dob', '')
        roll_no = request.form['roll_no'].strip()
        scholar_no = request.form.get('scholar_no', '').strip()
        class_name = request.form['class_name']
        group_name = request.form.get('group_name', '')

        scores_str, tot_ob, tot_mx, pct, result = calculate_result(class_name, group_name, request.form)

        conn.execute('''UPDATE students
            SET name=?, father_name=?, dob=?, roll_no=?, scholar_no=?, class_name=?, group_name=?, scores=?, total_obtained=?, total_max=?, percentage=?, result=?
            WHERE id=?''', (name, father_name, dob, roll_no, scholar_no, class_name, group_name, scores_str, tot_ob, tot_mx, pct, result, id))
        conn.commit()
        conn.close()
        flash("✅ Record Updated Successfully!", "success")
        return redirect(url_for('index'))

    s_data = dict(student)
    try:
        s_data['scores'] = json.loads(s_data['scores'])
    except Exception:
        s_data['scores'] = {}
    conn.close()
    return render_template('edit.html', s=s_data)

@app.route('/delete/<int:id>')
@login_required
def delete_student(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM students WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("🗑️ Record Deleted Successfully!", "success")
    return redirect(url_for('index'))

@app.route('/edit_master/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_master_student(id):
    conn = get_db_connection()
    student = conn.execute("SELECT * FROM student_master WHERE id = ?", (id,)).fetchone()

    if not student:
        conn.close()
        flash("❌ Student Record Not Found!", "danger")
        return redirect(url_for('student_info_panel'))

    if request.method == 'POST':
        scholar_no = request.form.get('scholar_no')
        roll_no = request.form.get('roll_no')
        name = request.form.get('name')
        father_name = request.form.get('father_name')
        mother_name = request.form.get('mother_name')
        dob = request.form.get('dob')
        class_name = request.form.get('class_name')
        group_name = request.form.get('group_name')
        gender = request.form.get('gender', 'Boy')
        caste = request.form.get('caste', '')
        admission_year = request.form.get('admission_year')
        status = request.form.get('status')
        samagra_id = request.form.get('samagra_id')
        aadhaar_id = request.form.get('aadhaar_id')
        apaar_id = request.form.get('apaar_id')
        pen_number = request.form.get('pen_number')
        mobile_no = request.form.get('mobile_no')
        bank_account = request.form.get('bank_account')
        ifsc_code = request.form.get('ifsc_code')
        address = request.form.get('address')

        photo_path = student['photo_path'] if 'photo_path' in student.keys() else None
        file = request.files.get('student_photo')
        captured_data = request.form.get('captured_image_data')

        if file and file.filename != '':
            filename = f"{scholar_no}_{file.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            photo_path = filepath
        elif captured_data and captured_data != '':
            photo_path = save_camera_photo(captured_data, scholar_no)

        conn.execute('''
            UPDATE student_master 
            SET scholar_no=?, roll_no=?, name=?, father_name=?, mother_name=?, dob=?, 
                class_name=?, group_name=?, gender=?, caste=?, admission_year=?, status=?, 
                samagra_id=?, aadhaar_id=?, apaar_id=?, pen_number=?, mobile_no=?, 
                bank_account=?, ifsc_code=?, address=?, photo_path=?
            WHERE id=?
        ''', (scholar_no, roll_no, name, father_name, mother_name, dob, 
              class_name, group_name, gender, caste, admission_year, status, 
              samagra_id, aadhaar_id, apaar_id, pen_number, mobile_no, 
              bank_account, ifsc_code, address, photo_path, id))

        conn.commit()
        conn.close()
        flash("📢 Master Student Record Updated Successfully!", "success")
        return redirect(url_for('student_info_panel'))

    s_data = dict(student)
    conn.close()
    # Yahan 's' aur 'student' dono pass kar diye hain taaki HTML me koi error na aaye
    return render_template('edit_master.html', s=s_data, student=s_data)



@app.route('/delete_master/<int:id>')
@login_required
def delete_master_student(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM student_master WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash(" छात्र का रिकॉर्ड सफलतापूर्वक डिलीट कर दिया गया है!", "danger")
    return redirect(url_for('student_info_panel'))

@app.route('/id_card_generator')
@login_required
def id_card_generator():
    class_name = request.args.get('class_name', '').strip()
    scholar_no = request.args.get('scholar_no', '').strip()

    conn = get_db_connection()
    query = "SELECT * FROM student_master WHERE 1=1"
    params = []

    if scholar_no:
        query += " AND (scholar_no LIKE ? OR name LIKE ?)"
        params.extend([f"%{scholar_no}%", f"%{scholar_no}%"])
    elif class_name:
        query += " AND class_name = ?"
        params.append(class_name)

    query += " ORDER BY class_name, scholar_no"
    students = conn.execute(query, params).fetchall()

    classes_list = conn.execute("SELECT DISTINCT class_name FROM student_master WHERE class_name IS NOT NULL AND class_name != '' ORDER BY class_name").fetchall()
    classes = [c['class_name'] for c in classes_list]
    conn.close()

    return render_template('id_cards.html', students=students, classes=classes, selected_class=class_name, scholar_no=scholar_no)

def send_bulk_email_thread(email_list, subject, message_text):
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(ADMIN_EMAIL, ADMIN_APP_PASSWORD)

        for email in email_list:
            msg = MIMEMultipart()
            msg['From'] = ADMIN_EMAIL
            msg['To'] = email
            msg['Subject'] = subject
            msg.attach(MIMEText(message_text, 'plain', 'utf-8'))
            server.sendmail(ADMIN_EMAIL, email, msg.as_string())

        server.quit()
        print(f"✅ Bulk Email successfully sent to {len(email_list)} recipients!")
    except Exception as e:
        print("❌ Bulk Email sending failed:", e)

@app.route('/send_class_msg', methods=['GET', 'POST'])
@login_required
def send_class_msg():
    conn = get_db_connection()
    classes_list = conn.execute("SELECT DISTINCT class_name FROM student_master WHERE class_name IS NOT NULL AND class_name != '' ORDER BY class_name").fetchall()
    classes = [c['class_name'] for c in classes_list]

    students = []
    selected_class = ""
    message_text = ""

    if request.method == 'POST':
        selected_class = request.form.get('class_name', '').strip()
        message_text = request.form.get('message', '').strip()

        students = conn.execute("SELECT scholar_no, name, mobile_no FROM student_master WHERE class_name = ? AND mobile_no IS NOT NULL AND mobile_no != '' AND mobile_no != 'N/A'", (selected_class,)).fetchall()

        if not students:
            flash(f"⚠️ कक्षा {selected_class} के छात्रों का कोई मोबाइल नंबर दर्ज नहीं मिला!", "warning")

    conn.close()
    return render_template('send_class_msg.html', classes=classes, students=students, selected_class=selected_class, message_text=message_text)

@app.route('/teachers_panel', methods=['GET', 'POST'])
@login_required
def teachers_panel():
    conn = get_db_connection()

    if request.method == 'POST':
        teacher_name = request.form.get('teacher_name', '').strip()
        mobile_no = request.form.get('mobile_no', '').strip()
        email = request.form.get('email', '').strip()
        aadhaar_no = request.form.get('aadhaar_no', '').strip()
        subject_designation = request.form.get('subject_designation', '').strip()

        photo_path = ''
        file = request.files.get('teacher_photo')
        captured_data = request.form.get('captured_image_data')

        if file and file.filename != '':
            filename = f"teacher_{mobile_no}_{file.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            photo_path = filepath
        elif captured_data and captured_data != '':
            photo_path = save_camera_photo(captured_data, f"teacher_{mobile_no}")

        try:
            conn.execute('''
                INSERT INTO teacher_master (teacher_name, mobile_no, email, aadhaar_no, subject_designation, photo_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (teacher_name, mobile_no, email, aadhaar_no, subject_designation, photo_path))
            conn.commit()
            flash('✅ शिक्षक का रिकॉर्ड सफलतापूर्वक जोड़ा गया!', 'success')
        except Exception as e:
            flash(f'❌ त्रुटि: {str(e)}', 'danger')

        return redirect(url_for('teachers_panel'))

    teachers = conn.execute("SELECT * FROM teacher_master ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('teachers.html', teachers=teachers)

@app.route('/delete_teacher/<int:id>')
@login_required
def delete_teacher(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM teacher_master WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash('🗑️ शिक्षक का रिकॉर्ड डिलीट कर दिया गया है!', 'info')
    return redirect(url_for('teachers_panel'))

@app.route('/send_teacher_msg', methods=['GET', 'POST'])
@login_required
def send_teacher_msg():
    conn = get_db_connection()

    teachers = []
    message_text = ""

    if request.method == 'POST':
        message_text = request.form.get('message', '').strip()

        teachers = conn.execute(
            "SELECT teacher_name, mobile_no, subject_designation FROM teacher_master WHERE mobile_no IS NOT NULL AND mobile_no != ''"
        ).fetchall()

        if not teachers:
            flash("⚠️ किसी भी शिक्षक का मोबाइल नंबर दर्ज नहीं मिला!", "warning")

    conn.close()
    return render_template('send_teacher_msg.html', teachers=teachers, message_text=message_text)

# ==================== ONLINE PUBLIC RESULT PORTAL ====================

@app.route('/student_result')
def student_result():
    return render_template('public_result_search.html')

@app.route('/check_result', methods=['POST'])
def check_result():
    search_query = request.form.get('search_query', '').strip()
    dob = request.form.get('dob', '').strip()

    if not search_query:
        flash('⚠️ कृपया स्कॉलर नंबर या रोल नंबर दर्ज करें!', 'danger')
        return redirect(url_for('student_result'))

    conn = get_db_connection()

    query = "SELECT * FROM student_master WHERE scholar_no = ? OR roll_no = ?"
    student_master = conn.execute(query, (search_query, search_query)).fetchone()

    result_query = "SELECT * FROM students WHERE scholar_no = ? OR roll_no = ?"
    student_marks = conn.execute(result_query, (search_query, search_query)).fetchall()

    conn.close()

    if not student_marks:
        flash('❌ दर्ज की गई जानकारी का कोई परीक्षा परिणाम नहीं मिला!', 'danger')
        return redirect(url_for('student_result'))

    config = get_school_config()
    formatted_results = []
    for s in student_marks:
        s_dict = dict(s)
        try:
            s_dict['scores'] = json.loads(s_dict['scores'])
        except Exception:
            s_dict['scores'] = {}
        formatted_results.append(s_dict)

    return render_template('public_result_view.html',
                           student_info=student_master,
                           results=formatted_results,
                           principal_name=config.get('principal_name', 'Principal'))

# ==================== PUBLIC STUDENT DETAIL VIEW (NO LOGIN REQUIRED) ====================

@app.route('/public_student_search', methods=['GET', 'POST'])
def public_student_search():
    if request.method == 'POST':
        scholar_no = request.form.get('scholar_no', '').strip()
        
        if not scholar_no:
            flash('⚠️ कृपया स्कॉलर नंबर दर्ज करें!', 'danger')
            return redirect(url_for('public_student_search'))

        conn = get_db_connection()
        student = conn.execute(
            "SELECT * FROM student_master WHERE scholar_no = ?", 
            (scholar_no,)
        ).fetchone()
        conn.close()

        if student:
            return render_template('public_student_view.html', student=dict(student))
        else:
            flash('❌ इस स्कॉलर नंबर का कोई छात्र नहीं मिला!', 'danger')
            return redirect(url_for('public_student_search'))

    return render_template('public_student_search.html')


# ==================== ATTENDANCE MANAGEMENT ROUTES ====================

@app.route('/student_attendance', methods=['GET', 'POST'])
@login_required
def student_attendance():
    conn = get_db_connection()
    classes = ['Nursery', 'LKG', 'UKG', '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', '11th', '12th']

    selected_class = request.args.get('class_name', '').strip()
    attendance_date = request.args.get('date', '').strip() or request.form.get('attendance_date', '').strip()

    if request.method == 'POST':
        attendance_date = request.form.get('attendance_date')
        selected_class = request.form.get('class_name')
        student_ids = request.form.getlist('student_ids')

        for sid in student_ids:
            status = request.form.get(f'status_{sid}', 'Present')
            conn.execute('''
                INSERT INTO student_attendance (student_id, attendance_date, status)
                VALUES (?, ?, ?)
                ON CONFLICT(student_id, attendance_date) DO UPDATE SET status = excluded.status
            ''', (sid, attendance_date, status))

        conn.commit()
        flash(f"✅ कक्षा {selected_class} की {attendance_date} की उपस्थिति दर्ज हो गई है!", "success")
        conn.close()
        return redirect(url_for('student_attendance', class_name=selected_class, date=attendance_date))

    students = []
    if selected_class:
        sql = """
            SELECT s.id, s.scholar_no, s.roll_no, s.name, s.father_name,
                   COALESCE(a.status, 'Present') as status
            FROM student_master s
            LEFT JOIN student_attendance a ON s.id = a.student_id AND a.attendance_date = ?
            WHERE s.class_name = ? AND (s.status IS NULL OR s.status = 'Active')
            ORDER BY s.scholar_no
        """
        students = conn.execute(sql, (attendance_date, selected_class)).fetchall()

    conn.close()
    return render_template('student_attendance.html', classes=classes, students=students, selected_class=selected_class, attendance_date=attendance_date)


@app.route('/teacher_attendance', methods=['GET', 'POST'])
@login_required
def teacher_attendance():
    conn = get_db_connection()
    attendance_date = request.args.get('date', '').strip() or request.form.get('attendance_date', '').strip()

    if request.method == 'POST':
        attendance_date = request.form.get('attendance_date')
        teacher_ids = request.form.getlist('teacher_ids')

        for tid in teacher_ids:
            status = request.form.get(f'status_{tid}', 'Present')
            conn.execute('''
                INSERT INTO teacher_attendance (teacher_id, attendance_date, status)
                VALUES (?, ?, ?)
                ON CONFLICT(teacher_id, attendance_date) DO UPDATE SET status = excluded.status
            ''', (tid, attendance_date, status))

        conn.commit()
        flash(f"✅ शिक्षकों की {attendance_date} की उपस्थिति सफलतापूर्वक दर्ज हो गई है!", "success")
        conn.close()
        return redirect(url_for('teacher_attendance', date=attendance_date))

    sql = """
        SELECT t.id, t.teacher_name, t.mobile_no, t.subject_designation,
               COALESCE(a.status, 'Present') as status
        FROM teacher_master t
        LEFT JOIN teacher_attendance a ON t.id = a.teacher_id AND a.attendance_date = ?
        ORDER BY t.teacher_name
    """
    teachers = conn.execute(sql, (attendance_date,)).fetchall()

    conn.close()
    return render_template('teacher_attendance.html', teachers=teachers, attendance_date=attendance_date)

@app.route('/teacher_attendance_report')
@login_required
def teacher_attendance_report():
    conn = get_db_connection()
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    
    # महीने के अनुसार कुल कार्य दिवस (Working Days)
    working_days_row = conn.execute("""
        SELECT COUNT(DISTINCT attendance_date) as total 
        FROM teacher_attendance 
        WHERE strftime('%Y-%m', attendance_date) = ?
    """, (month,)).fetchone()
    
    working_days = working_days_row['total'] if working_days_row and working_days_row['total'] else 0

    # शिक्षक वार उपस्थिति का विवरण (यहाँ WHERE और GROUP BY को सही किया गया है)
    report = conn.execute("""
        SELECT 
            t.id,
            t.teacher_name,
            t.mobile_no,
            t.subject_designation,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present_days,
            SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as absent_days,
            SUM(CASE WHEN a.status = 'Half Day' THEN 1 ELSE 0 END) as half_days,
            SUM(CASE WHEN a.status = 'Leave' THEN 1 ELSE 0 END) as leaves_taken
        FROM teacher_master t
        LEFT JOIN teacher_attendance a ON t.id = a.teacher_id 
             AND strftime('%Y-%m', a.attendance_date) = ?
        GROUP BY t.id, t.teacher_name, t.mobile_no, t.subject_designation
        ORDER BY t.teacher_name
    """, (month,)).fetchall()
    
    conn.close()
    return render_template('teacher_report.html', report=report, working_days=working_days, selected_month=month)


# =========================================================
# 1. स्टूडेंट अटेंडेंस रीसेट/डिलीट रूट
@app.route('/delete_student_attendance', methods=['POST'])
@login_required
def delete_student_attendance():
    cls = request.form.get('class_name')
    month = request.form.get('month')
    
    if cls and month:
        conn = get_db_connection()
        conn.execute('''
            DELETE FROM student_attendance 
            WHERE student_id IN (SELECT id FROM student_master WHERE class_name = ?)
            AND strftime('%Y-%m', attendance_date) = ?
        ''', (cls, month))
        conn.commit()
        conn.close()
        
    return redirect(url_for('attendance_report', class_name=cls, month=month))


# 2. टीचर अटेंडेंस रीसेट/डिलीट रूट
@app.route('/delete_teacher_attendance', methods=['POST'])
@login_required
def delete_teacher_attendance():
    month = request.form.get('month')
    
    if month:
        conn = get_db_connection()
        conn.execute('''
            DELETE FROM teacher_attendance 
            WHERE strftime('%Y-%m', attendance_date) = ?
        ''', (month,))
        conn.commit()
        conn.close()
        
    return redirect(url_for('teacher_attendance_report', month=month))

import uuid
from datetime import datetime

# 1. फीस स्ट्रक्चर और फीस कलेक्शन पेज (Updated)
@app.route('/fee_management', methods=['GET', 'POST'])
@login_required
def fee_management():
    conn = get_db_connection()

    # कक्षा-वार फीस सेट करने के लिए
    if request.method == 'POST' and 'set_structure' in request.form:
        cls = request.form.get('class_name')
        total_fee = request.form.get('total_fee')
        conn.execute('''
            INSERT INTO fee_structure (class_name, total_fee)
            VALUES (?, ?)
            ON CONFLICT(class_name) DO UPDATE SET total_fee = excluded.total_fee
        ''', (cls, total_fee))
        conn.commit()

    # फीस कलेक्शन (जमा) करने के लिए
    elif request.method == 'POST' and 'collect_fee' in request.form:
        student_id = request.form.get('student_id')
        amount_paid = float(request.form.get('amount_paid', 0))
        payment_mode = request.form.get('payment_mode', 'Cash')
        payment_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        receipt_no = "REC-" + datetime.now().strftime('%Y%m%d') + "-" + str(uuid.uuid4().hex[:4].upper())

        conn.execute('''
            INSERT INTO fee_transactions (student_id, amount_paid, payment_date, payment_mode, receipt_no)
            VALUES (?, ?, ?, ?, ?)
        ''', (student_id, amount_paid, payment_date, payment_mode, receipt_no))
        conn.commit()
        conn.close()
        return redirect(url_for('fee_receipt', receipt_no=receipt_no))

    # फ़िल्टर छात्र
    selected_class = request.args.get('class_name', '')
    students_data = []

    if selected_class:
        students = conn.execute('SELECT * FROM student_master WHERE class_name = ?', (selected_class,)).fetchall()

        # फीस स्ट्रक्चर
        fee_struct = conn.execute('SELECT total_fee FROM fee_structure WHERE class_name = ?', (selected_class,)).fetchone()
        total_fee = fee_struct['total_fee'] if fee_struct else 0.0

        # स्कूल का नाम मैसेज के लिए
        school_name = config_data.get('school_name', 'स्कूल प्रबंधन') if 'config_data' in globals() else 'स्कूल प्रबंधन'

        for s in students:
            # छात्र का भुगतान इतिहास (गलत फीस डिलीट करने के लिए)
            txs = conn.execute('SELECT * FROM fee_transactions WHERE student_id = ? ORDER BY id DESC', (s['id'],)).fetchall()

            # कुल जमा फीस
            paid_res = conn.execute('SELECT SUM(amount_paid) as total_paid FROM fee_transactions WHERE student_id = ?', (s['id'],)).fetchone()
            total_paid = paid_res['total_paid'] or 0.0
            due_amount = total_fee - total_paid

            # WhatsApp रिमाइंडर मैसेज
            sms_text = f"आदरणीय अभिभावक, {s['name']} (कक्षा: {s['class_name']}) की शेष फीस ₹{due_amount} बकाया है। कृपया शीघ्र जमा करें। - {school_name}"

            students_data.append({
                'id': s['id'],
                'scholar_no': s['scholar_no'],
                'name': s['name'],
                'father_name': s['father_name'],
                'mobile_no': s['mobile_no'] if 'mobile_no' in s.keys() else '',
                'total_fee': total_fee,
                'total_paid': total_paid,
                'due_amount': due_amount,
                'transactions': txs,
                'sms_text': sms_text
            })

    structures = conn.execute('SELECT * FROM fee_structure').fetchall()
    conn.close()

    return render_template('fee_management.html',
                           students=students_data,
                           selected_class=selected_class,
                           structures=structures)


# 2. गलत जमा फीस प्रविष्टि डिलीट करने के लिए नया रूट
@app.route('/delete_fee_transaction/<int:tx_id>', methods=['POST'])
@login_required
def delete_fee_transaction(tx_id):
    conn = get_db_connection()
    selected_class = request.form.get('class_name', '')
    conn.execute('DELETE FROM fee_transactions WHERE id = ?', (tx_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('fee_management', class_name=selected_class))


# 3. कक्षा की फीस स्ट्रक्चर डिलीट / रीसेट करने के लिए नया रूट
@app.route('/delete_fee_structure/<class_name>', methods=['POST'])
@login_required
def delete_fee_structure(class_name):
    conn = get_db_connection()
    conn.execute('DELETE FROM fee_structure WHERE class_name = ?', (class_name,))
    conn.commit()
    conn.close()
    return redirect(url_for('fee_management', class_name=class_name))


# 4. डिजिटल रसीद (PDF/Print Fee Receipt)
@app.route('/fee_receipt/<receipt_no>')
@login_required
def fee_receipt(receipt_no):
    conn = get_db_connection()
    tx = conn.execute('''
        SELECT t.*, s.name, s.father_name, s.scholar_no, s.class_name, s.mobile_no
        FROM fee_transactions t
        JOIN student_master s ON t.student_id = s.id
        WHERE t.receipt_no = ?
    ''', (receipt_no,)).fetchone()

    if not tx:
        conn.close()
        return "रसीद नहीं मिली!", 404

    # कुल जमा और बकाया का हिसाब
    fee_struct = conn.execute('SELECT total_fee FROM fee_structure WHERE class_name = ?', (tx['class_name'],)).fetchone()
    total_fee = fee_struct['total_fee'] if fee_struct else 0.0

    total_paid_res = conn.execute('SELECT SUM(amount_paid) as sum_paid FROM fee_transactions WHERE student_id = ?', (tx['student_id'],)).fetchone()
    total_paid = total_paid_res['sum_paid'] or 0.0
    due_amount = total_fee - total_paid

    conn.close()
    return render_template('fee_receipt.html', tx=tx, total_fee=total_fee, total_paid=total_paid, due_amount=due_amount)
# छात्र की फीस इतिहास समरी (Fee History Summary & Print Page)
# छात्र की फीस इतिहास समरी (Fee History Summary Page)
@app.route('/fee_summary/<int:student_id>')
@login_required
def fee_summary(student_id):
    conn = get_db_connection()
    
    student = conn.execute('SELECT * FROM student_master WHERE id = ?', (student_id,)).fetchone()
    if not student:
        conn.close()
        return "छात्र नहीं मिला!", 404

    fee_struct = conn.execute('SELECT total_fee FROM fee_structure WHERE class_name = ?', (student['class_name'],)).fetchone()
    total_fee = fee_struct['total_fee'] if fee_struct else 0.0

    transactions = conn.execute('SELECT * FROM fee_transactions WHERE student_id = ? ORDER BY id ASC', (student_id,)).fetchall()
    
    total_paid = sum(tx['amount_paid'] for tx in transactions) if transactions else 0.0
    due_amount = total_fee - total_paid

    # आज की तारीख पाइथन से ही भेज रहे हैं
    today_date = datetime.now().strftime('%d-%m-%Y')

    conn.close()
    return render_template('fee_summary.html', 
                           student=student, 
                           total_fee=total_fee, 
                           total_paid=total_paid, 
                           due_amount=due_amount, 
                           transactions=transactions,
                           today_date=today_date)


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    conn = get_db_connection()
    
    if request.method == 'POST':
        school_name = request.form.get('school_name')
        address = request.form.get('address')
        phone = request.form.get('phone')
        session = request.form.get('session')
        
        # Logo Handle
        logo = request.files.get('logo')
        logo_path = request.form.get('existing_logo')
        
        if logo and logo.filename != '':
            filename = secure_filename(logo.filename)
            upload_dir = os.path.join('static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, filename)
            logo.save(save_path)
            logo_path = f"uploads/{filename}"

        conn.execute('''
            UPDATE school_settings 
            SET school_name=?, address=?, phone=?, session=?, logo_path=?
            WHERE id=1
        ''', (school_name, address, phone, session, logo_path))
        conn.commit()
        conn.close()
        flash('⚙️ सेटिंग्स सफलतापूर्वक सेव हो गईं!', 'success')
        return redirect(url_for('settings'))

    settings_data = conn.execute("SELECT * FROM school_settings WHERE id=1").fetchone()
    conn.close()
    return render_template('settings.html', settings=dict(settings_data) if settings_data else {})


# ==================== BOARD EXAM APPLICATION FORM ROUTES ====================

@app.route('/exam_application_form', methods=['GET', 'POST'])
@login_required
def exam_application_form():
    conn = get_db_connection()
    student = None
    
    # यदि स्कॉलर नंबर से डेटा फेच करना हो
    scholar_no = request.args.get('scholar_no', '').strip()
    if scholar_no:
        student = conn.execute("SELECT * FROM student_master WHERE scholar_no = ?", (scholar_no,)).fetchone()

    if request.method == 'POST':
        s_no = request.form.get('scholar_no', '').strip()
        class_name = request.form.get('class_name', '')
        stream = request.form.get('stream', '')
        name = request.form.get('name', '')
        father = request.form.get('father', '')
        mother = request.form.get('mother', '')
        dob = request.form.get('dob', '')
        caste = request.form.get('caste', '')
        gender = request.form.get('gender', '')
        applicant_type = request.form.get('applicant_type', '')
        district_code = request.form.get('district_code', '')
        block_code = request.form.get('block_code', '')
        school_code = request.form.get('school_code', '')
        enrollment_code = request.form.get('enrollment_code', '')
        sambal_no = request.form.get('sambal_no', '')
        medium = request.form.get('medium', '')
        address = request.form.get('address', '')
        mobile = request.form.get('mobile', '')
        apaar_id = request.form.get('apaar_id', '')
        sssmid = request.form.get('sssmid', '')
        family_id = request.form.get('family_id', '')
        aadhaar = request.form.get('aadhaar', '')
        bank_ac = request.form.get('bank_ac', '')
        ifsc = request.form.get('ifsc', '')

        # डेटाबेस में अपडेट या इन्सर्ट करें
        conn.execute('''
            UPDATE student_master SET 
                class_name=?, stream=?, name=?, father_name=?, mother_name=?, dob=?, caste=?, gender=?, 
                applicant_type=?, district_code=?, block_code=?, school_code=?, enrollment_code=?, 
                sambal_no=?, medium=?, address=?, mobile_no=?, apaar_id=?, samagra_id=?, family_id=?, 
                aadhaar_id=?, bank_account=?, ifsc_code=?
            WHERE scholar_no=?
        ''', (class_name, stream, name, father, mother, dob, caste, gender, applicant_type, 
              district_code, block_code, school_code, enrollment_code, sambal_no, medium, 
              address, mobile, apaar_id, sssmid, family_id, aadhaar, bank_ac, ifsc, s_no))
        
        conn.commit()
        conn.close()
        flash("✅ परीक्षा फॉर्म सफलतापूर्वक अपडेट और सेव हो गया है!", "success")
        return redirect(url_for('print_exam_form_by_scholar', scholar_no=s_no))

    conn.close()
    return render_template('form.html', student=dict(student) if student else None)


@app.route('/print_exam_form/<scholar_no>')
@login_required
def print_exam_form_by_scholar(scholar_no):
    conn = get_db_connection()
    student = conn.execute("SELECT * FROM student_master WHERE scholar_no = ?", (scholar_no,)).fetchone()
    conn.close()

    if not student:
        flash("❌ छात्र का रिकॉर्ड नहीं मिला!", "danger")
        return redirect(url_for('exam_application_form'))

    return render_template('print_form.html', data=dict(student))


# Server Start
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)

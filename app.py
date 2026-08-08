import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
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
            gender  TEXT,
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
            admission_year TEXT DEFAULT '2026',
            status TEXT DEFAULT 'Active',
            photo_path TEXT
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

# 5. exam_marks table
#Exam Marks Table with UNIQUE constraint on (student_id, exam_term, subject_name)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS exam_marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            exam_term TEXT,        -- उदा: 'Quarterly', 'Half Yearly', 'Final'
            subject_name TEXT,     -- उदा: 'Hindi', 'Maths'
            marks_obtained REAL,
            total_marks REAL,
            FOREIGN KEY(student_id) REFERENCES student_master(id),
            UNIQUE(student_id, exam_term, subject_name)
        );
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
        total_max += 100.0

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

# ==================== NEW SETTINGS & CUSTOM EXTRACTOR ROUTES ====================

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    msg = None
    if request.method == 'POST':
        new_config = {
            "school_name": request.form.get('school_name', '').strip(),
            "principal_name": request.form.get('principal_name', '').strip(),
            "school_address": request.form.get('school_address', '').strip(),
            "academic_session": request.form.get('academic_session', '').strip()
        }
        save_school_config(new_config)
        msg = "✅ School & System Settings updated successfully!"
    
    return render_template('settings.html', msg=msg)

@app.route('/student_quick_view')
@login_required
def student_quick_view():
    selected_class = request.args.get('class_name', '').strip()
    search = request.args.get('search', '').strip()
    selected_fields = request.args.getlist('fields')

    # Default selected fields if nothing is checked initially
    if not selected_fields and 'class_name' not in request.args:
        selected_fields = ['scholar_no', 'father_name', 'bank_acc', 'ifsc']

    conn = get_db_connection()
    sql = "SELECT * FROM student_master WHERE 1=1"
    params = []

    if selected_class:
        sql += " AND class_name = ?"
        params.append(selected_class)
    if search:
        sql += " AND (scholar_no LIKE ? OR name LIKE ? OR roll_no LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    sql += " ORDER BY class_name, scholar_no"
    students_raw = conn.execute(sql, params).fetchall()
    conn.close()

    # Field mapping for student_quick_view.html template (Bank Name replaced with DOB)
    students = []
    for s in students_raw:
        students.append({
            'class_name': s['class_name'],
            'name': s['name'],
            'scholar_no': s['scholar_no'],
            'father_name': s['father_name'],
            'dob': s['dob'] if 'dob' in s.keys() else '',
            'mobile_no': s['mobile_no'],
            'aadhaar_no': s['aadhaar_id'],
            'bank_acc_no': s['bank_account'],
            'ifsc_code': s['ifsc_code']
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
    
    # Handle TC Issue Action
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
    
    # Fetch Active Students for Issuing TC
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

    # Fetch Issued TC List
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


@app.route('/term_marks_entry', methods=['GET', 'POST'])
@login_required
def term_marks_entry():
    conn = get_db_connection()
    classes = ['Nursery', 'LKG', 'UKG', '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', '11th', '12th']
    terms = ['Quarterly Exam', 'Half Yearly Exam', 'Final Exam']
    
    selected_class = request.args.get('class_name', '').strip()
    selected_term = request.args.get('exam_term', 'Quarterly Exam').strip()
    students = []

    if request.method == 'POST':
        exam_term = request.form.get('exam_term')
        class_name = request.form.get('class_name')
        
        # Save or Update Student Marks per Term
        student_ids = request.form.getlist('student_id')
        for sid in student_ids:
            marks_obtained = request.form.get(f'marks_{sid}', 0)
            total_marks = request.form.get(f'total_{sid}', 100)
            
            # Check existing entry
            existing = conn.execute(
                "SELECT id FROM exam_marks WHERE student_id = ? AND exam_term = ?",
                (sid, exam_term)
            ).fetchone()
            
            if existing:
                conn.execute(
                    "UPDATE exam_marks SET marks_obtained = ?, total_marks = ? WHERE student_id = ? AND exam_term = ?",
                    (marks_obtained, total_marks, sid, exam_term)
                )
            else:
                conn.execute(
                    "INSERT INTO exam_marks (student_id, exam_term, marks_obtained, total_marks) VALUES (?, ?, ?, ?)",
                    (sid, exam_term, marks_obtained, total_marks)
                )
        conn.commit()
        flash(f"✅ {exam_term} के अंक सफलतापूर्वक सुरक्षित कर दिए गए हैं!", "success")
        conn.close()
        return redirect(url_for('term_marks_entry', class_name=class_name, exam_term=exam_term))

    if selected_class:
        sql = """
            SELECT s.id, s.scholar_no, s.name, s.father_name, s.class_name, 
                   m.marks_obtained, m.total_marks 
            FROM student_master s 
            LEFT JOIN exam_marks m ON s.id = m.student_id AND m.exam_term = ?
            WHERE s.class_name = ? AND (s.status IS NULL OR s.status = 'Active')
            ORDER BY s.scholar_no
        """
        students = conn.execute(sql, (selected_term, selected_class)).fetchall()

    conn.close()
    return render_template(
        'term_marks_entry.html',
        classes=classes,
        terms=terms,
        students=students,
        selected_class=selected_class,
        selected_term=selected_term
    )



# ================================================================================

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

@app.route('/student_info')
@login_required
def student_info_panel():
    selected_class = request.args.get('class_name', '').strip()
    selected_year = request.args.get('birth_year', '').strip()
    selected_gender = request.args.get('gender', '').strip()
    missing_info = request.args.get('missing_info', '').strip()
    search_q = request.args.get('search', '').strip()

    conn = get_db_connection()

    cols = [col[1] for col in conn.execute("PRAGMA table_info(student_master)").fetchall()]
    if 'gender' not in cols:
        conn.execute("ALTER TABLE student_master ADD COLUMN gender TEXT DEFAULT 'Boy'")
        conn.commit()

    classes_list = conn.execute("SELECT DISTINCT class_name FROM student_master WHERE class_name IS NOT NULL AND class_name != '' ORDER BY class_name").fetchall()
    classes = [c['class_name'] for c in classes_list]

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

    if missing_info == 'no_mobile':
        sql += " AND (mobile_no IS NULL OR mobile_no = '' OR mobile_no = 'N/A')"
    elif missing_info == 'no_aadhaar':
        sql += " AND (aadhaar_id IS NULL OR aadhaar_id = '' OR aadhaar_id = 'N/A')"
    elif missing_info == 'no_samagra':
        sql += " AND (samagra_id IS NULL OR samagra_id = '' OR samagra_id = 'N/A')"
    elif missing_info == 'incomplete':
        sql += " AND (mobile_no IS NULL OR mobile_no = '' OR aadhaar_id IS NULL OR aadhaar_id = '' OR samagra_id IS NULL OR samagra_id = '')"

    if search_q:
        sql += " AND (scholar_no LIKE ? OR name LIKE ? OR father_name LIKE ?)"
        params.extend([f"%{search_q}%", f"%{search_q}%", f"%{search_q}%"])

    sql += " ORDER BY class_name, scholar_no"
    students = conn.execute(sql, params).fetchall()

    summary_rows = conn.execute("SELECT class_name, COUNT(*) as count FROM student_master GROUP BY class_name").fetchall()
    class_counts = {r['class_name']: r['count'] for r in summary_rows}
    total_students = sum(class_counts.values())

    total_boys = conn.execute("SELECT COUNT(*) FROM student_master WHERE gender = 'Boy' OR gender IS NULL OR gender = ''").fetchone()[0]
    total_girls = conn.execute("SELECT COUNT(*) FROM student_master WHERE gender = 'Girl'").fetchone()[0]

    has_mobile_count = conn.execute("SELECT COUNT(*) FROM student_master WHERE mobile_no IS NOT NULL AND mobile_no != '' AND mobile_no != 'N/A'").fetchone()[0]
    no_mobile_count = total_students - has_mobile_count

    conn.close()

    return render_template('student_info.html',
                           students=students,
                           selected_class=selected_class,
                           selected_year=selected_year,
                           selected_gender=selected_gender,
                           missing_info=missing_info,
                           search_q=search_q,
                           classes=classes,
                           class_counts=class_counts,
                           total_students=total_students,
                           total_boys=total_boys,
                           total_girls=total_girls,
                           has_mobile_count=has_mobile_count,
                           no_mobile_count=no_mobile_count)

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

@app.route('/admit_card', methods=['GET', 'POST'])
def admit_card_panel():
    conn = get_db_connection()

    if request.method == 'POST':
        student_ids = request.form.getlist('student_ids')
        for sid in student_ids:
            roll = request.form.get(f'roll_{sid}', '').strip()
            conn.execute("UPDATE student_master SET roll_no = ? WHERE id = ?", (roll, sid))
        conn.commit()
        flash("✅ Roll Numbers Saved Successfully!", "success")

    selected_class = request.args.get('class_name', '10th')
    students = conn.execute("SELECT * FROM student_master WHERE class_name = ? ORDER BY scholar_no", (selected_class,)).fetchall()
    timetable = conn.execute("SELECT * FROM exam_schedule WHERE class_name = ? ORDER BY paper_no", (selected_class,)).fetchall()

    conn.close()
    return render_template('admit_card.html', students=students, selected_class=selected_class, timetable=timetable)

@app.route('/save_timetable', methods=['POST'])
def save_timetable():
    selected_class = request.form.get('class_name', '10th')
    conn = get_db_connection()

    for i in range(1, 7):
        date_val = request.form.get(f'date_{i}', '').strip()
        subj_val = request.form.get(f'subject_{i}', '').strip()

        if subj_val:
            conn.execute('''
                INSERT INTO exam_schedule (class_name, paper_no, exam_date, subject_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(class_name, paper_no) DO UPDATE SET
                    exam_date = excluded.exam_date,
                    subject_name = excluded.subject_name
            ''', (selected_class, i, date_val, subj_val))

    conn.commit()
    conn.close()
    flash("✅ Timetable Saved Successfully!", "success")
    return redirect(url_for('admit_card_panel', class_name=selected_class))

@app.route('/exam_control')
def exam_control():
    conn = get_db_connection()
    c1 = request.args.get('class1', '9th')
    students = conn.execute("SELECT * FROM student_master WHERE class_name = ? ORDER BY scholar_no", (c1,)).fetchall()
    conn.close()
    return render_template('exam_sheet.html', students=students, c1=c1)

@app.route('/report_card/<int:id>')
def report_card(id):
    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (id,)).fetchone()
    conn.close()

    config = get_school_config()
    s_data = dict(student)
    try:
        s_data['scores'] = json.loads(s_data['scores'])
    except Exception:
        s_data['scores'] = {}
    return render_template('report_card.html', student=s_data, principal_name=config.get('principal_name', 'Principal'))

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

        photo_path = student['photo_path'] if 'photo_path' in student.keys() else ''
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
            SET scholar_no=?, roll_no=?, name=?, father_name=?, mother_name=?, dob=?, class_name=?,
                group_name=?, gender=?, admission_year=?, status=?, samagra_id=?, aadhaar_id=?, apaar_id=?,
                pen_number=?, mobile_no=?, bank_account=?, ifsc_code=?, address=?, photo_path=?
            WHERE id=?
        ''', (scholar_no, roll_no, name, father_name, mother_name, dob, class_name,
              group_name, gender, admission_year, status, samagra_id, aadhaar_id, apaar_id,
              pen_number, mobile_no, bank_account, ifsc_code, address, photo_path, id))

        conn.commit()
        conn.close()
        flash(" Master Student Record Updated Successfully!", "success")
        return redirect(url_for('student_info_panel'))

    conn.close()
    return render_template('edit_master.html', s=dict(student))

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
            flash('✅ शिक्षक का रिकॉर्ड सफलतापूर्वक जोड़ा गया!', 'success')
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

# Server Start
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)

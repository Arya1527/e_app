import sqlite3
import requests
import json

# 1. आपके SQLite डेटाबेस से कनेक्ट करें (app.py के अनुसार यह students.db है)
DB_NAME = 'students.db'

# Firebase Project ID (Acode वाले HTML प्रोजेक्ट के आधार पर)
PROJECT_ID = "mystudent-db"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def upload_students_master():
    print("\n[1/3] 📤 'student_master' टेबल अपलोड हो रही है...")
    conn = get_db()
    rows = conn.execute("SELECT * FROM student_master").fetchall()
    conn.close()

    count = 0
    for row in rows:
        data = dict(row)
        scholar_no = str(data.get('scholar_no', '')).strip()
        if not scholar_no:
            continue

        # Firestore Payload Format
        payload = {
            "fields": {
                "scholar_no": {"stringValue": scholar_no},
                "roll_no": {"stringValue": str(data.get('roll_no') or '')},
                "name": {"stringValue": str(data.get('name') or '')},
                "father_name": {"stringValue": str(data.get('father_name') or '')},
                "mother_name": {"stringValue": str(data.get('mother_name') or '')},
                "dob": {"stringValue": str(data.get('dob') or '')},
                "gender": {"stringValue": str(data.get('gender') or 'Boy')},
                "class_name": {"stringValue": str(data.get('class_name') or '')},
                "mobile_no": {"stringValue": str(data.get('mobile_no') or '')},
                "status": {"stringValue": str(data.get('status') or 'Active')}
            }
        }

        # Google Cloud (Firebase) पर पोस्ट करें
        url = f"{BASE_URL}/students/{scholar_no}"
        res = requests.patch(url, json=payload)
        if res.status_code in [200, 201]:
            count += 1
            print(f"  ✅ Uploaded Master: {scholar_no} - {data.get('name')}")
        else:
            print(f"  ❌ Failed: {scholar_no}")

    print(f"🎉 'student_master' से कुल {count} छात्र Firebase पर सिंक हुए!")

def upload_teacher_master():
    print("\n[2/3] 📤 'teacher_master' टेबल अपलोड हो रही है...")
    conn = get_db()
    rows = conn.execute("SELECT * FROM teacher_master").fetchall()
    conn.close()

    count = 0
    for row in rows:
        data = dict(row)
        mobile_no = str(data.get('mobile_no', '')).strip()
        
        payload = {
            "fields": {
                "teacher_name": {"stringValue": str(data.get('teacher_name') or '')},
                "mobile_no": {"stringValue": mobile_no},
                "email": {"stringValue": str(data.get('email') or '')},
                "subject_designation": {"stringValue": str(data.get('subject_designation') or '')}
            }
        }

        url = f"{BASE_URL}/teachers"
        res = requests.post(url, json=payload)
        if res.status_code in [200, 201]:
            count += 1
            print(f"  ✅ Uploaded Teacher: {data.get('teacher_name')}")

    print(f"🎉 'teacher_master' से कुल {count} शिक्षक सिंक हुए!")

if __name__ == '__main__':
    print("==================================================")
    print("🚀 Jyoti Niketan School Database -> Firebase Sync")
    print("==================================================")
    try:
        upload_students_master()
        upload_teacher_master()
        print("\n✨ बधाई हो! आपका सारा डेटा सुरक्षित Google Cloud Firebase पर अपलोड हो गया है!")
    except Exception as e:
        print(f"\n❌ त्रुटि आई: {e}")

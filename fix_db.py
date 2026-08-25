import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# 1. Attendance Table
cursor.execute('''
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scholar_no TEXT,
    class_name TEXT,
    date TEXT,
    status TEXT
)
''')

# 2. Exam Marks Table
cursor.execute('''
CREATE TABLE IF NOT EXISTS exam_marks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    exam_term TEXT,
    subject_name TEXT DEFAULT 'Overall Term',
    marks_obtained REAL,
    total_marks REAL
)
''')

# Safely add subject_name column if missing
try:
    cursor.execute("ALTER TABLE exam_marks ADD COLUMN subject_name TEXT DEFAULT 'Overall Term'")
except Exception:
    pass

conn.commit()
conn.close()
print("✅ Database tables updated successfully!")

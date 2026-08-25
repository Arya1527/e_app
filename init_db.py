import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Create attendance table if missing
cursor.execute('''
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scholar_no TEXT,
    class_name TEXT,
    date TEXT,
    status TEXT
)
''')

# Create exam_marks table if missing
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

conn.commit()
conn.close()
print("✅ Tables Created/Verified Successfully!")

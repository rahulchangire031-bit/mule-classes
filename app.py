import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'gallery')
app.config['NOTES_FOLDER'] = os.path.join(BASE_DIR, 'static', 'notes')
app.config['HOMEWORK_FOLDER'] = os.path.join(BASE_DIR, 'static', 'homework')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = 'mule_classes_super_secret_key'  # Required for sessions

for folder in [app.config['UPLOAD_FOLDER'], app.config['NOTES_FOLDER'], app.config['HOMEWORK_FOLDER']]:
    if not os.path.exists(folder):
        os.makedirs(folder)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect('inquiries.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            student_class TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            student_class TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS homework (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            due_date TEXT NOT NULL,
            student_class TEXT NOT NULL,
            file_path TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            student_class TEXT NOT NULL,
            file_path TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            test_name TEXT NOT NULL,
            score REAL NOT NULL,
            max_score REAL NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/', methods=['GET', 'POST'])
def index():
    images = [img for img in os.listdir(app.config['UPLOAD_FOLDER']) if allowed_file(img)]
    import time
    mentor_exists = os.path.exists(os.path.join('static', 'mentor.jpg'))
    ts = time.time()
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        student_class = request.form.get('class')
        
        conn = sqlite3.connect('inquiries.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO inquiries (name, phone, student_class) VALUES (?, ?, ?)", 
                       (name, phone, student_class))
        conn.commit()
        conn.close()
        
        return render_template('index.html', success=True, gallery_images=images, mentor_exists=mentor_exists, ts=ts)
    
    return render_template('index.html', success=False, gallery_images=images, mentor_exists=mentor_exists, ts=ts)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('admin'))
            
    conn = sqlite3.connect('inquiries.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inquiries ORDER BY timestamp DESC")
    inquiries = cursor.fetchall()
    conn.close()
    
    images = [img for img in os.listdir(app.config['UPLOAD_FOLDER']) if allowed_file(img)]
    return render_template('admin.html', inquiries=inquiries, images=images)

@app.route('/admin/delete/<filename>', methods=['POST'])
def delete_image(filename):
    if filename and allowed_file(filename):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        if os.path.exists(filepath):
            os.remove(filepath)
    return redirect(url_for('admin'))

# --- Student Portal Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = sqlite3.connect('inquiries.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, password, name, student_class FROM students WHERE username = ?", (username,))
        student = cursor.fetchone()
        conn.close()
        
        if student and check_password_hash(student[1], password):
            session['student_id'] = student[0]
            session['student_name'] = student[2]
            session['student_class'] = student[3]
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', name=session['student_name'], student_class=session['student_class'])

@app.route('/homework')
def homework():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('inquiries.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, description, due_date, file_path FROM homework WHERE student_class = ?", (session['student_class'],))
    homeworks = cursor.fetchall()
    conn.close()
    return render_template('homework.html', homeworks=homeworks)

@app.route('/attendance')
def attendance():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('inquiries.db')
    cursor = conn.cursor()
    cursor.execute("SELECT date, status FROM attendance WHERE student_id = ? ORDER BY date DESC", (session['student_id'],))
    records = cursor.fetchall()
    conn.close()
    return render_template('attendance.html', records=records)

@app.route('/notes')
def notes():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('inquiries.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, file_path FROM notes WHERE student_class = ?", (session['student_class'],))
    notes_list = cursor.fetchall()
    conn.close()
    return render_template('notes.html', notes=notes_list)

@app.route('/marks')
def marks():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('inquiries.db')
    cursor = conn.cursor()
    cursor.execute("SELECT test_name, score, max_score, date FROM test_marks WHERE student_id = ? ORDER BY date DESC", (session['student_id'],))
    test_marks = cursor.fetchall()
    conn.close()
    return render_template('marks.html', marks=test_marks)

# --- Admin Management Routes for Student Data ---
@app.route('/admin/add_student', methods=['POST'])
def admin_add_student():
    username = request.form.get('username')
    password = generate_password_hash(request.form.get('password'))
    name = request.form.get('name')
    student_class = request.form.get('student_class')
    conn = sqlite3.connect('inquiries.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO students (username, password, name, student_class) VALUES (?, ?, ?, ?)", (username, password, name, student_class))
        conn.commit()
    except sqlite3.IntegrityError:
        flash("Username already exists.")
    finally:
        conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/add_homework', methods=['POST'])
def admin_add_homework():
    title = request.form.get('title')
    description = request.form.get('description')
    due_date = request.form.get('due_date')
    student_class = request.form.get('student_class')
    file_path = ""
    if 'file' in request.files and request.files['file'].filename != '':
        file = request.files['file']
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['HOMEWORK_FOLDER'], filename))
            file_path = filename
    conn = sqlite3.connect('inquiries.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO homework (title, description, due_date, student_class, file_path) VALUES (?, ?, ?, ?, ?)", (title, description, due_date, student_class, file_path))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/add_attendance', methods=['POST'])
def admin_add_attendance():
    student_id = request.form.get('student_id')
    date = request.form.get('date')
    status = request.form.get('status')
    conn = sqlite3.connect('inquiries.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)", (student_id, date, status))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/add_note', methods=['POST'])
def admin_add_note():
    title = request.form.get('title')
    student_class = request.form.get('student_class')
    file_path = ""
    if 'file' in request.files and request.files['file'].filename != '':
        file = request.files['file']
        if allowed_file(file.filename): # We might want to allow PDFs for notes later
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['NOTES_FOLDER'], filename))
            file_path = filename
    conn = sqlite3.connect('inquiries.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notes (title, student_class, file_path) VALUES (?, ?, ?)", (title, student_class, file_path))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/add_mark', methods=['POST'])
def admin_add_mark():
    student_id = request.form.get('student_id')
    test_name = request.form.get('test_name')
    score = request.form.get('score')
    max_score = request.form.get('max_score')
    date = request.form.get('date')
    conn = sqlite3.connect('inquiries.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO test_marks (student_id, test_name, score, max_score, date) VALUES (?, ?, ?, ?, ?)", (student_id, test_name, score, max_score, date))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

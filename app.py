import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'gallery')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

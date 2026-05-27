"""
AttendAI Sync Pro — Flask Backend
Real face recognition using face_recognition + OpenCV + SQLite
Run: pip install flask flask-cors face_recognition opencv-python pillow
Then: python app.py
"""

from flask import Flask, request, jsonify, session
from flask_cors import CORS
import sqlite3, base64, json, os, io
from datetime import datetime, date
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'attendai-secret-2026')
CORS(app, supports_credentials=True, origins=['*'])

DB_PATH = os.environ.get('DB_PATH', 'attendai.db')

# ── Optional: real face_recognition (comment out if not installed) ──
try:
    import face_recognition
    import numpy as np
    from PIL import Image
    FACE_REC_AVAILABLE = True
    print("✓ face_recognition loaded — real AI recognition active")
except ImportError:
    FACE_REC_AVAILABLE = False
    print("⚠ face_recognition not installed — using simulated matching")

# ═══════════════════════════════════
# DATABASE
# ═══════════════════════════════════
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS students (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                usn TEXT UNIQUE NOT NULL,
                dept TEXT,
                year TEXT,
                email TEXT,
                phone TEXT,
                photo BLOB,
                face_encoding TEXT,
                registered_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS attendance (
                id TEXT PRIMARY KEY,
                student_id TEXT NOT NULL,
                method TEXT DEFAULT 'Face ID',
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id)
            );
            CREATE TABLE IF NOT EXISTS admins (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'admin'
            );
        """)
        # Seed default admin
        existing = db.execute("SELECT id FROM admins WHERE email='admin@attendai.io'").fetchone()
        if not existing:
            db.execute("INSERT INTO admins VALUES (?, ?, ?, ?)",
                       ('admin_1', 'admin@attendai.io', 'admin123', 'super_admin'))
        db.commit()
    print(f"✓ Database initialized at {DB_PATH}")

# ═══════════════════════════════════
# AUTH
# ═══════════════════════════════════
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_id'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '')
    with get_db() as db:
        admin = db.execute("SELECT * FROM admins WHERE email=? AND password=?", (email, password)).fetchone()
    if not admin:
        return jsonify({'error': 'Invalid credentials'}), 401
    session['admin_id'] = admin['id']
    session['admin_email'] = admin['email']
    return jsonify({'success': True, 'role': admin['role'], 'email': admin['email']})

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def me():
    return jsonify({'admin_id': session['admin_id'], 'email': session['admin_email']})

# ═══════════════════════════════════
# STUDENTS
# ═══════════════════════════════════
@app.route('/api/students', methods=['GET'])
@require_auth
def get_students():
    with get_db() as db:
        rows = db.execute("SELECT id,name,usn,dept,year,email,phone,registered_at FROM students ORDER BY registered_at DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/students', methods=['POST'])
@require_auth
def register_student():
    data = request.json
    name = data.get('name', '').strip()
    usn = data.get('usn', '').strip()
    photo_b64 = data.get('photo', '')

    if not name or not usn:
        return jsonify({'error': 'Name and USN required'}), 400
    if not photo_b64:
        return jsonify({'error': 'Face photo required'}), 400

    # Encode face
    face_encoding = None
    if FACE_REC_AVAILABLE and photo_b64:
        try:
            img_data = base64.b64decode(photo_b64.split(',')[-1])
            img = face_recognition.load_image_file(io.BytesIO(img_data))
            encodings = face_recognition.face_encodings(img)
            if encodings:
                face_encoding = json.dumps(encodings[0].tolist())
            else:
                return jsonify({'error': 'No face detected in photo. Please retake.'}), 400
        except Exception as e:
            return jsonify({'error': f'Face processing failed: {str(e)}'}), 500

    student_id = f"S_{int(datetime.now().timestamp()*1000)}"
    with get_db() as db:
        try:
            db.execute(
                "INSERT INTO students VALUES (?,?,?,?,?,?,?,?,?,?)",
                (student_id, name, usn, data.get('dept',''), data.get('year',''),
                 data.get('email',''), data.get('phone',''),
                 photo_b64, face_encoding, int(datetime.now().timestamp()*1000))
            )
            db.commit()
        except sqlite3.IntegrityError:
            return jsonify({'error': f'USN {usn} already registered'}), 409

    return jsonify({'success': True, 'student_id': student_id, 'face_encoded': face_encoding is not None})

@app.route('/api/students/<student_id>', methods=['PUT'])
@require_auth
def update_student(student_id):
    data = request.json
    with get_db() as db:
        db.execute(
            "UPDATE students SET name=?,dept=?,year=?,email=?,phone=? WHERE id=?",
            (data.get('name'), data.get('dept'), data.get('year'),
             data.get('email'), data.get('phone'), student_id)
        )
        db.commit()
    return jsonify({'success': True})

@app.route('/api/students/<student_id>', methods=['DELETE'])
@require_auth
def delete_student(student_id):
    with get_db() as db:
        db.execute("DELETE FROM attendance WHERE student_id=?", (student_id,))
        db.execute("DELETE FROM students WHERE id=?", (student_id,))
        db.commit()
    return jsonify({'success': True})

# ═══════════════════════════════════
# FACE RECOGNITION
# ═══════════════════════════════════
@app.route('/api/face/recognize', methods=['POST'])
@require_auth
def recognize_face():
    data = request.json
    photo_b64 = data.get('photo', '')
    if not photo_b64:
        return jsonify({'error': 'No photo provided'}), 400

    if not FACE_REC_AVAILABLE:
        return jsonify({'error': 'face_recognition not installed', 'simulated': True}), 200

    try:
        img_data = base64.b64decode(photo_b64.split(',')[-1])
        unknown_img = face_recognition.load_image_file(io.BytesIO(img_data))
        unknown_encs = face_recognition.face_encodings(unknown_img)
        if not unknown_encs:
            return jsonify({'recognized': False, 'message': 'No face detected'})

        unknown_enc = unknown_encs[0]
        with get_db() as db:
            students = db.execute("SELECT id, name, usn, dept, face_encoding FROM students WHERE face_encoding IS NOT NULL").fetchall()

        best_match = None
        best_distance = 0.6  # threshold

        for s in students:
            known_enc = np.array(json.loads(s['face_encoding']))
            distance = face_recognition.face_distance([known_enc], unknown_enc)[0]
            if distance < best_distance:
                best_distance = distance
                best_match = s

        if best_match:
            confidence = round((1 - best_distance) * 100, 1)
            return jsonify({
                'recognized': True,
                'student_id': best_match['id'],
                'name': best_match['name'],
                'usn': best_match['usn'],
                'dept': best_match['dept'],
                'confidence': confidence,
                'distance': round(best_distance, 4),
            })
        return jsonify({'recognized': False, 'message': 'Unknown face'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ═══════════════════════════════════
# ATTENDANCE
# ═══════════════════════════════════
@app.route('/api/attendance', methods=['GET'])
@require_auth
def get_attendance():
    date_str = request.args.get('date', date.today().isoformat())
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        d = date.today()

    start = int(datetime(d.year, d.month, d.day).timestamp() * 1000)
    end = start + 86400000  # +24h

    with get_db() as db:
        rows = db.execute("""
            SELECT a.id, a.student_id, a.method, a.timestamp,
                   s.name, s.usn, s.dept, s.year
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE a.timestamp >= ? AND a.timestamp < ?
            ORDER BY a.timestamp DESC
        """, (start, end)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/attendance/mark', methods=['POST'])
@require_auth
def mark_attendance():
    data = request.json
    student_id = data.get('student_id')
    method = data.get('method', 'Face ID')

    if not student_id:
        return jsonify({'error': 'student_id required'}), 400

    today = date.today()
    start = int(datetime(today.year, today.month, today.day).timestamp() * 1000)
    end = start + 86400000

    with get_db() as db:
        already = db.execute(
            "SELECT id FROM attendance WHERE student_id=? AND timestamp>=? AND timestamp<?",
            (student_id, start, end)
        ).fetchone()
        if already:
            return jsonify({'error': 'Already marked today', 'duplicate': True}), 409

        att_id = f"A_{int(datetime.now().timestamp()*1000)}"
        ts = int(datetime.now().timestamp() * 1000)
        db.execute("INSERT INTO attendance VALUES (?,?,?,?)", (att_id, student_id, method, ts))
        db.commit()

    return jsonify({'success': True, 'attendance_id': att_id, 'timestamp': ts})

@app.route('/api/attendance/stats', methods=['GET'])
@require_auth
def get_stats():
    today = date.today()
    start = int(datetime(today.year, today.month, today.day).timestamp() * 1000)
    end = start + 86400000

    with get_db() as db:
        total = db.execute("SELECT COUNT(*) as c FROM students").fetchone()['c']
        present_today = db.execute(
            "SELECT COUNT(DISTINCT student_id) as c FROM attendance WHERE timestamp>=? AND timestamp<?",
            (start, end)
        ).fetchone()['c']

    absent = max(0, total - present_today)
    rate = round((present_today / total * 100), 1) if total > 0 else 0
    return jsonify({'total': total, 'present': present_today, 'absent': absent, 'rate': rate})

@app.route('/api/attendance/history', methods=['GET'])
@require_auth
def get_history():
    days = int(request.args.get('days', 7))
    results = []
    for i in range(days - 1, -1, -1):
        d = date.today()
        from datetime import timedelta
        d = d - timedelta(days=i)
        start = int(datetime(d.year, d.month, d.day).timestamp() * 1000)
        end = start + 86400000
        with get_db() as db:
            count = db.execute(
                "SELECT COUNT(DISTINCT student_id) as c FROM attendance WHERE timestamp>=? AND timestamp<?",
                (start, end)
            ).fetchone()['c']
        results.append({'date': d.isoformat(), 'count': count, 'label': d.strftime('%a')})
    return jsonify(results)

# ═══════════════════════════════════
# DASHBOARD SUMMARY
# ═══════════════════════════════════
@app.route('/api/dashboard', methods=['GET'])
@require_auth
def dashboard():
    today = date.today()
    start = int(datetime(today.year, today.month, today.day).timestamp() * 1000)
    end = start + 86400000
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) as c FROM students").fetchone()['c']
        present = db.execute("SELECT COUNT(DISTINCT student_id) as c FROM attendance WHERE timestamp>=? AND timestamp<?", (start, end)).fetchone()['c']
        recent = db.execute("""SELECT a.timestamp, a.method, s.name, s.dept FROM attendance a
            JOIN students s ON a.student_id=s.id WHERE a.timestamp>=? ORDER BY a.timestamp DESC LIMIT 10""", (start,)).fetchall()
    absent = max(0, total - present)
    rate = round((present / total * 100), 1) if total > 0 else 0
    return jsonify({
        'total': total, 'present': present, 'absent': absent, 'rate': rate,
        'recent_checkins': [dict(r) for r in recent]
    })

# ═══════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'version': '2.4.1',
        'face_recognition': FACE_REC_AVAILABLE,
        'db': DB_PATH,
    })

# ═══════════════════════════════════
# BOOT
# ═══════════════════════════════════
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    print(f"\n🚀 AttendAI Sync Pro backend running on http://localhost:{port}")
    print(f"   Face recognition: {'✓ Active' if FACE_REC_AVAILABLE else '✗ Not installed'}")
    print(f"   API docs: http://localhost:{port}/api/health\n")
    app.run(host='0.0.0.0', port=port, debug=debug)

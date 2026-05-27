# AttendAI Sync Pro 2.0

> Real full-stack AI attendance system — face recognition, live dashboard, export, RBAC, QR codes.

---

## 🚀 Quick Start

### Frontend Only (zero setup)
Just open `index.html` in any modern browser. Everything works via localStorage — no server needed.

### Full Stack (with real face recognition)

```bash
# 1. Install Python deps
cd backend
pip install -r requirements.txt

# 2. Copy env file
cp .env.example .env

# 3. Run backend
python app.py
# → http://localhost:5000

# 4. Open index.html in browser
```

---

## 📁 Folder Structure

```
attendai-upgraded/
├── index.html              ← Full frontend (single file, zero deps)
├── backend/
│   ├── app.py              ← Flask API server
│   ├── requirements.txt    ← Python dependencies
│   ├── .env.example        ← Environment variables template
│   └── attendai.db         ← SQLite database (auto-created)
└── README.md
```

---

## ✨ Features

| Feature | Status | Notes |
|---|---|---|
| Student Registration | ✅ | Form + webcam photo capture |
| Face Recognition Attendance | ✅ | Simulated in browser; real AI with backend |
| Live Dashboard | ✅ | Real stats, charts, heatmap |
| Attendance Log | ✅ | Search, filter, export CSV/PDF |
| Student Records | ✅ | Edit, delete, search |
| QR Code Attendance | ✅ | Rotating QR, 30s expiry |
| Role-Based Access | ✅ | Admin/Teacher/HOD/Student roles |
| AI Analytics | ✅ | Claude AI insights via Anthropic API |
| Dark/Light Mode | ✅ | Toggle in topbar |
| Export CSV | ✅ | Full attendance + student export |
| Auth / Session | ✅ | Admin login, session management |
| Mobile Responsive | ✅ | Sidebar collapses on mobile |

---

## 🔐 Default Login

| Field | Value |
|---|---|
| Email | admin@attendai.io |
| Password | admin123 |

---

## 🧠 Face Recognition

**Browser mode** (default): Simulates recognition by cycling through registered students. All photos are stored in localStorage.

**Real AI mode** (with backend):
- Uses `face_recognition` (dlib) + OpenCV
- Encodes face on registration (128-dimensional vector)
- Matches unknown face against all encodings at ≤0.6 Euclidean distance
- Returns confidence % and student details

### Install face_recognition (Linux/Mac)

```bash
# Ubuntu/Debian
sudo apt-get install cmake libopenblas-dev liblapack-dev
pip install dlib face_recognition

# Mac (Homebrew)
brew install cmake
pip install dlib face_recognition
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/login` | Admin login |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/students` | List all students |
| POST | `/api/students` | Register student + encode face |
| PUT | `/api/students/:id` | Update student |
| DELETE | `/api/students/:id` | Delete student |
| POST | `/api/face/recognize` | Recognize face from photo |
| GET | `/api/attendance` | Get attendance (by date) |
| POST | `/api/attendance/mark` | Mark student present |
| GET | `/api/attendance/stats` | Today's stats |
| GET | `/api/attendance/history` | Last N days trend |
| GET | `/api/dashboard` | Full dashboard summary |
| GET | `/api/health` | System health check |

---

## 🔧 Connect Frontend to Backend

In `index.html`, the app uses localStorage by default. To switch to the real backend, update the `DB` object's methods to call the REST API instead:

```js
// Example: replace DB.getStudents() with API call
async function getStudentsFromAPI() {
  const res = await fetch('http://localhost:5000/api/students', { credentials: 'include' });
  return res.json();
}
```

---

## 📦 Tech Stack

**Frontend**
- Vanilla JS (ES2022) — zero frameworks, zero build step
- CSS custom properties (glassmorphism, dark/light mode)
- Web APIs: MediaDevices (webcam), Canvas, localStorage
- Anthropic Claude API (AI analytics insights)

**Backend**
- Python 3.10+
- Flask 3.x + Flask-CORS
- face_recognition (dlib) + OpenCV
- SQLite (or swap DB_PATH for any SQLite-compatible path)

---

## 🛡 Security Notes

- Passwords are stored plaintext in the demo — hash with `bcrypt` for production
- Add HTTPS in production (use nginx + certbot)
- Rotate `SECRET_KEY` before deploying
- Face encodings are stored as JSON arrays in SQLite — encrypt at rest for sensitive deployments

---

## 📄 License

MIT — free to use, modify, and deploy.

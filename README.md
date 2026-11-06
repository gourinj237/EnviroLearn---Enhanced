# EnviroLearn – Enhanced Edition

> A Gamified Environmental Education Platform for Schools  
> Enhanced with Gemini AI, PWA support, and AI-powered image verification.

🌐 **Original Live Demo:** https://cst334-s6-2023-27batch-envirolearn-a.onrender.com

---

## ✨ New Features Added

| Feature | Description |
|---|---|
| 🤖 **Gemini Dynamic Quizzes** | AI-generated MCQs after each video — different questions every attempt |
| 🖼️ **AI Image Verification** | Gemini Vision checks challenge photo relevance before teacher review |
| 📱 **PWA Support** | Installable app with offline fallback and caching |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask 3.1 |
| Database | SQLite via Flask-SQLAlchemy |
| Auth | Flask-Login + Werkzeug |
| AI | Google Gemini 1.5 Flash (text + vision) |
| Frontend | Jinja2, Vanilla CSS, Vanilla JS |
| PWA | Web App Manifest + Service Worker |

---

## 🚀 Setup & Run

### 1. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Gemini API Key
```bash
copy .env.example .env
```
Edit `.env` and add your key:
```
GEMINI_API_KEY=your_key_here
```
Get your free API key at: https://aistudio.google.com/app/apikey

### 4. Run Database Migration (if upgrading from original)
```bash
python migrate.py
```

### 5. Start the App
```bash
python app.py
```
Open http://localhost:5000

---

## 📁 New Files

```
gemini_service.py          ← Gemini AI quiz generation + image verification
migrate.py                 ← One-time DB migration script
create_icons.py            ← PWA icon generator
.env.example               ← Environment variables template
static/manifest.json       ← PWA manifest
static/service-worker.js   ← PWA service worker
static/icons/              ← PWA app icons
templates/dynamic_quiz.html   ← AI quiz UI
templates/offline.html        ← PWA offline page
templates/weekly_report.html  ← Weekly teacher report
```

## 📝 Modified Files (minimal changes only)

```
requirements.txt           ← Added google-generativeai, python-dotenv
models.py                  ← Added DynamicQuizAttempt model + AI columns
app.py                     ← Added 6 new routes, AI call in challenge submit
templates/home.html         ← 3 lines: PWA manifest + SW registration
templates/pollution.html    ← 1 line: redirect to AI quiz
templates/globalwarming.html ← 1 line: redirect to AI quiz
templates/biodiversity.html  ← 1 line: redirect to AI quiz
templates/teacherviewreport.html ← AI verdict badge in submission cards
```

---

## 👥 Original Team
- Gouri Nandana J · Jerena Ann Jacob · Jyothika Sasi · Nandana S Nair

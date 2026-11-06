from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from datetime import datetime
import os
import json
from flask import jsonify
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()   # loads .env file into os.environ

from models import (
    db, User, Score, PuzzleScore,
    OceanScore, WasteScore,
    Quiz1Score, Quiz2Score, Quiz3Score,
    Quiz4Score, Quiz5Score, Quiz6Score,
    VideoProgress, ChallengeAttempt, ChallengeSubmission, UserBadge,
    DynamicQuizAttempt,
    VIDEO_CATALOGUE, CHALLENGE_CATALOGUE
)
import gemini_service

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret123')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database_new3.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "student_login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ── GENERAL ──────────────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/role')
def role():
    return render_template('role.html')


# ── STUDENT AUTH ─────────────────────────────────────────────────

@app.route('/student-signup', methods=['GET', 'POST'])
def student_signup():
    if request.method == 'POST':
        name          = request.form['name']
        student_class = request.form['class']
        email         = request.form['email']
        password      = generate_password_hash(request.form['password'])
        if User.query.filter_by(email=email).first():
            flash("⚠️ Email already exists!")
            return redirect(url_for('student_signup'))
        if User.query.filter_by(name=name).first():
            flash("⚠️ Name already exists!")
            return redirect(url_for('student_signup'))
        db.session.add(User(name=name, email=email, password=password,
                            role="student", student_class=student_class))
        db.session.commit()
        flash("✅ Signup successful! Please login.")
        return redirect(url_for('student_login'))
    return render_template("studentsignup.html")

@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']
        user     = User.query.filter_by(email=email, role="student").first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('index'))
        flash("Invalid credentials")
        return redirect(url_for('student_login'))
    return render_template("student.html")


# ── TEACHER AUTH ─────────────────────────────────────────────────

@app.route('/teacher-signup', methods=['GET', 'POST'])
def teacher_signup():
    if request.method == 'POST':
        name     = request.form['name']
        email    = request.form['email']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(email=email).first():
            flash("Email already exists!")
            return redirect(url_for('teacher_signup'))
        db.session.add(User(name=name, email=email, password=password, role="teacher"))
        db.session.commit()
        flash("Signup successful! Please login.")
        return redirect(url_for('teacher_login'))
    return render_template("teachersignup.html")

@app.route('/teacher-login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']
        user     = User.query.filter_by(email=email, role="teacher").first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('teacherviewreport'))
        flash("Invalid credentials")
        return redirect(url_for('teacher_login'))
    return render_template("teacher.html")

@app.route('/about')
def about():
    return render_template('about.html')
# ── MAIN PAGES ───────────────────────────────────────────────────

@app.route('/index')
@login_required
def index():
    return render_template('index.html')

@app.route('/games')
@login_required
def games():
    return render_template('games.html')

@app.route('/quizzes')
@login_required
def quizzes():
    return render_template('quizzes.html')

@app.route('/videos')
@login_required
def videos():
    return render_template('videos.html')


# ── VIDEO PAGES ──────────────────────────────────────────────────

@app.route('/pollution')
@login_required
def pollution_video():
    return render_template('pollution.html', video_id=1)

@app.route('/globalwarming')
@login_required
def globalwarming_video():
    return render_template('globalwarming.html', video_id=2)

@app.route('/biodiversity')
@login_required
def biodiversity_video():
    return render_template('biodiversity.html', video_id=3)


# ── SAVE VIDEO PROGRESS ──────────────────────────────────────────

@app.route('/save-video-progress', methods=['POST'])
@login_required
def save_video_progress():
    video_id  = int(request.form.get('video_id', 0))
    percent   = min(int(request.form.get('percent', 0)), 100)
    completed = percent >= 80
    points    = VIDEO_CATALOGUE.get(video_id, {}).get('max_points', 10) if completed else 0
    existing  = VideoProgress.query.filter_by(user_id=current_user.id, video_id=video_id).first()
    if existing:
        if percent > existing.percent_watched:
            existing.percent_watched = percent
            existing.completed       = completed
            existing.points_awarded  = points
            existing.last_updated    = datetime.utcnow()
    else:
        db.session.add(VideoProgress(user_id=current_user.id, video_id=video_id,
                                     percent_watched=percent, completed=completed,
                                     points_awarded=points))
    db.session.commit()
    return ('', 204)


# ── CHALLENGES ───────────────────────────────────────────────────

@app.route('/challenges')
@login_required
def challenges():
    attempts = ChallengeAttempt.query.filter_by(user_id=current_user.id).all()
    best = {}
    for a in attempts:
        cid = a.challenge_id
        if cid not in best or a.points_awarded > best[cid].points_awarded:
            best[cid] = a
    challenge_data = []
    for cid, info in CHALLENGE_CATALOGUE.items():
        attempt = best.get(cid)
        challenge_data.append({
            'id': cid,
            'title': info.get('title', ''),
            'desc': info.get('desc', ''),
            'icon': info.get('icon', ''), 'time_limit': info.get('time_limit_sec', 0),
            'points': info['points'],
            'completed':  attempt.completed      if attempt else False,
            'time_taken': attempt.time_taken_sec if attempt else None,
            'pts_earned': attempt.points_awarded if attempt else 0,
        })
    return render_template('challenges.html', challenges=challenge_data)


# ── SAVE CHALLENGE ────────────────────────────────────────────────

@app.route('/save-challenge', methods=['POST'])
@login_required
def save_challenge():
    challenge_id = int(request.form.get('challenge_id'))
    completed    = request.form.get('completed', 'false').lower() == 'true'
    time_taken   = int(request.form.get('time_taken', 0))
    points       = CHALLENGE_CATALOGUE.get(challenge_id, {}).get('points', 50) if completed else 0
    db.session.add(ChallengeAttempt(user_id=current_user.id, challenge_id=challenge_id,
                                    completed=completed,
                                    time_taken_sec=time_taken if completed else None,
                                    points_awarded=points))
    db.session.commit()
    return ('', 204)


# ── QUIZ PAGES ───────────────────────────────────────────────────

@app.route('/biodiversity_quiz')
@login_required
def biodiversity_quiz():
    return render_template('biodiversity_quiz.html')

@app.route('/pollution_quiz')
@login_required
def pollution_quiz():
    return render_template('pollution_quiz.html')

@app.route('/globalwarming_quiz')
@login_required
def globalwarming_quiz():
    return render_template('globalwarming_quiz.html')

@app.route("/quiz1")
@login_required
def quiz1():
    return render_template("quiz1.html")

@app.route("/quiz2")
@login_required
def quiz2():
    return render_template("quiz2.html")

@app.route("/quiz3")
@login_required
def quiz3():
    return render_template("quiz3.html")

@app.route("/quiz4")
@login_required
def quiz4():
    return render_template("quiz4.html")

@app.route("/quiz5")
@login_required
def quiz5():
    return render_template("quiz5.html")

@app.route("/quiz6")
@login_required
def quiz6():
    return render_template("quiz6.html")


# ── GAME PAGES ───────────────────────────────────────────────────

@app.route('/waste')
@login_required
def waste():
    return render_template('waste.html')

@app.route('/ocean')
@login_required
def ocean():
    return render_template('ocean.html')

@app.route('/carbon', methods=['GET', 'POST'])
@login_required
def carbon():
    if request.method == 'POST':
        db.session.add(Score(value=int(request.form['score']), user_id=current_user.id))
        db.session.commit()
        return redirect(url_for('games'))
    return render_template('carbon.html')

@app.route('/puzzle', methods=['GET', 'POST'])
@login_required
def puzzle():
    if request.method == 'POST':
        db.session.add(PuzzleScore(value=int(request.form['score']), user_id=current_user.id))
        db.session.commit()
        return redirect(url_for('games'))
    return render_template('puzzle.html')


# ── SAVE SCORE ROUTES ────────────────────────────────────────────

@app.route("/save_carbon_score", methods=["POST"])
@login_required
def save_carbon_score():
    db.session.add(Score(value=int(request.form.get("score")), user_id=current_user.id))
    db.session.commit()
    return '', 204

@app.route("/save_puzzle_score", methods=["POST"])
@login_required
def save_puzzle_score():
    db.session.add(PuzzleScore(value=int(request.form.get("score")), user_id=current_user.id))
    db.session.commit()
    return '', 204

@app.route('/save-waste-score', methods=['POST'])
@login_required
def save_waste_score():
    db.session.add(WasteScore(score=int(request.form['score']), user_id=current_user.id))
    db.session.commit()
    return '', 204

@app.route('/save-ocean-score', methods=['POST'])
@login_required
def save_ocean_score():
    db.session.add(OceanScore(score=int(request.form['score']), user_id=current_user.id))
    db.session.commit()
    return '', 204

@app.route('/save-quiz1-score', methods=['POST'])
@login_required
def save_quiz1_score():
    db.session.add(Quiz1Score(user_id=current_user.id, score=int(request.form['score'])))
    db.session.commit()
    return '', 204

@app.route('/save-quiz2-score', methods=['POST'])
@login_required
def save_quiz2_score():
    db.session.add(Quiz2Score(user_id=current_user.id, score=int(request.form['score'])))
    db.session.commit()
    return '', 204

@app.route('/save-quiz3-score', methods=['POST'])
@login_required
def save_quiz3_score():
    db.session.add(Quiz3Score(user_id=current_user.id, score=int(request.form['score'])))
    db.session.commit()
    return '', 204

@app.route('/save-quiz4-score', methods=['POST'])
@login_required
def save_quiz4_score():
    db.session.add(Quiz4Score(user_id=current_user.id, score=int(request.form['score'])))
    db.session.commit()
    return '', 204

@app.route('/save-quiz5-score', methods=['POST'])
@login_required
def save_quiz5_score():
    db.session.add(Quiz5Score(user_id=current_user.id, score=int(request.form['score'])))
    db.session.commit()
    return '', 204

@app.route('/save-quiz6-score', methods=['POST'])
@login_required
def save_quiz6_score():
    db.session.add(Quiz6Score(user_id=current_user.id, score=int(request.form['score'])))
    db.session.commit()
    return '', 204


# ── LEADERBOARDS ─────────────────────────────────────────────────

@app.route('/leaderboard')
@login_required
def leaderboard():
    return redirect(url_for("games_leaderboard"))

@app.route('/puzzle_leaderboard')
@login_required
def puzzle_leaderboard():
    top_players = (
        db.session.query(User.name.label("username"), func.max(PuzzleScore.value).label("max_score"))
        .join(PuzzleScore, PuzzleScore.user_id == User.id).group_by(User.id)
        .order_by(func.max(PuzzleScore.value).desc()).limit(5).all()
    )
    return render_template("leaderboard.html", leaderboard=top_players)


# ── MAIN COMBINED LEADERBOARD ─────────────────────────────────────

@app.route('/games_leaderboard')
@login_required
def games_leaderboard():
    users = User.query.filter_by(role="student").all()
    rows = []

    for u in users:
        g = u.game_xp()
        q = u.quiz_xp()
        v = u.video_xp()
        c = u.challenge_xp()

        total = g + q + v + c

        # use the reward function
        reward = get_reward(c)

        rows.append({
            'name': u.name,
            'student_class': u.student_class or '—',
            'game_xp': g,
            'quiz_xp': q,
            'video_xp': v,
            'challenge_xp': c,
            'total': total,
            'reward': reward,
            'is_me': u.id == current_user.id
        })

    rows.sort(key=lambda x: x['total'], reverse=True)

    for i, row in enumerate(rows):
        row['rank'] = i + 1

    return render_template("leaderboard.html", leaderboard=rows)


# ── STUDENT REPORT ───────────────────────────────────────────────

@app.route('/studentreport')
@login_required
def studentreport():
    students = User.query.filter_by(role='student').all()
    all_students = []
    for s in students:
        all_students.append({
            "id": s.id,
            "name": s.name,
            "student_class": s.student_class or "",
            "game_xp": s.game_xp() or 0,
            "quiz_xp": s.quiz_xp() or 0,
            "video_xp": s.video_xp() or 0,
            "challenge_xp": s.challenge_xp() or 0
        })
    me = {
        "id": current_user.id,
        "name": current_user.name,
        "student_class": current_user.student_class or "",
        "game_xp": current_user.game_xp() or 0,
        "quiz_xp": current_user.quiz_xp() or 0,
        "video_xp": current_user.video_xp() or 0,
        "challenge_xp": current_user.challenge_xp() or 0,
        "badges": [b.badge_key for b in current_user.badges],
    }
    return render_template("studentreport.html", me=me, all_students=all_students)


# ── TEACHER REPORT ───────────────────────────────────────────────

@app.route('/teacherviewreport')
@login_required
def teacherviewreport():
    if current_user.role != 'teacher':
        flash("Access restricted to teachers.")
        return redirect(url_for('index'))

    students = User.query.filter_by(role='student').order_by(User.name).all()

    def best(scores, col='score'):
        vals = [getattr(s, col) for s in scores]
        return max(vals) if vals else 0

    student_data = []
    for s in students:
        g = s.game_xp(); q = s.quiz_xp(); v = s.video_xp(); c = s.challenge_xp()
        student_data.append({
            'id': s.id, 'name': s.name, 'email': s.email,
            'student_class': s.student_class or '—',
            'game_xp': g, 'quiz_xp': q, 'video_xp': v, 'challenge_xp': c,
            'total': g + q + v + c,
            'carbon': best(s.scores, 'value'), 'puzzle': best(s.puzzle_scores, 'value'),
            'waste':  best(s.waste_scores),    'ocean':  best(s.ocean_scores),
            'quiz1':  best(s.quiz1_scores),    'quiz2':  best(s.quiz2_scores),
            'quiz3':  best(s.quiz3_scores),    'quiz4':  best(s.quiz4_scores),
            'quiz5':  best(s.quiz5_scores),    'quiz6':  best(s.quiz6_scores),
            'challenges_done': sum(1 for ca in s.challenge_attempts if ca.completed),
            'last_login': s.last_login.strftime("%Y-%m-%d %H:%M") if s.last_login else None,
            'badges_count': len(s.badges),
        })

    student_data.sort(key=lambda x: x['total'], reverse=True)
    for i, s in enumerate(student_data):
        s['rank'] = i + 1

    # ── Build submission data for the Photo Review panel ──────────
    all_submissions = (
        ChallengeSubmission.query
        .order_by(ChallengeSubmission.submitted_at.desc())
        .all()
    )
    submission_data = []
    for sub in all_submissions:
        def make_url(photo_path):
            """Convert stored file path to a browser-accessible URL."""
            if not photo_path:
                return ''
            # Normalize backslashes (Windows), ensure starts with /
            url = photo_path.replace("\\", "/")
            if not url.startswith("/"):
                url = "/" + url
            return url

        submission_data.append({
            'id':               sub.id,
            'student_name':     sub.user.name,
            'student_class':    sub.user.student_class or '—',
            'challenge_id':     sub.challenge_id,
            'challenge_name':   sub.challenge_name,
            'before_photo':     make_url(sub.before_photo),
            'after_photo':      make_url(sub.after_photo),
            'duration_sec':     sub.duration_sec,
            'submitted_at':     sub.submitted_at.strftime("%d %b %Y, %I:%M %p") if sub.submitted_at else '',
            'status':           sub.status,
            'reward_enabled':   sub.reward_enabled,
            'teacher_feedback': sub.teacher_feedback or '',
            'points': CHALLENGE_CATALOGUE.get(sub.challenge_id, {}).get('points', 50),
        })

    class_avg = round(sum(s['total'] for s in student_data) / len(student_data), 1) if student_data else 0
    return render_template(
        'teacherviewreport.html',
        students=student_data,
        submissions=submission_data,
        class_avg=class_avg,
        total_students=len(student_data)
    )


# ── TEACHER: VERIFY / REJECT SUBMISSION ─────────────────────────

@app.route('/api/teacher/submissions/<int:submission_id>/review', methods=['POST'])
@login_required
def review_submission(submission_id):
    if current_user.role != 'teacher':
        return jsonify({"error": "Access denied"}), 403

    sub = ChallengeSubmission.query.get_or_404(submission_id)
    action   = request.form.get('action')          # 'verify' or 'reject'
    feedback = request.form.get('feedback', '')
    reward   = request.form.get('reward_points', type=int,
                                default=CHALLENGE_CATALOGUE.get(sub.challenge_id, {}).get('points', 50))

    if action == 'verify':
        sub.status         = 'verified'
        sub.reward_enabled = True
        sub.verified_at    = datetime.utcnow()
        sub.teacher_feedback = feedback

        # Update (or create) the ChallengeAttempt so XP is correct
        attempt = ChallengeAttempt.query.filter_by(
            user_id=sub.user_id, challenge_id=sub.challenge_id
        ).order_by(ChallengeAttempt.id.desc()).first()

        if attempt:
            attempt.points_awarded = reward
            attempt.completed      = True
        else:
            db.session.add(ChallengeAttempt(
                user_id=sub.user_id,
                challenge_id=sub.challenge_id,
                completed=True,
                points_awarded=reward,
                time_taken_sec=sub.duration_sec
            ))

        # Award badge
        award_badges(sub.user_id, sub.challenge_id)

    elif action == 'reject':
        sub.status           = 'rejected'
        sub.reward_enabled   = False
        sub.teacher_feedback = feedback

        # Zero out any XP for this challenge if previously awarded via this submission
        attempt = ChallengeAttempt.query.filter_by(
            user_id=sub.user_id, challenge_id=sub.challenge_id
        ).order_by(ChallengeAttempt.id.desc()).first()
        if attempt:
            attempt.points_awarded = 0
            attempt.completed      = False
    else:
        return jsonify({"error": "action must be 'verify' or 'reject'"}), 400

    db.session.commit()
    return jsonify({"message": f"Submission {submission_id} {action}d successfully."})


# ── EXISTING API ROUTES ──────────────────────────────────────────

@app.route('/api/challenges/<int:challenge_id>/cooldown')
@login_required
def check_cooldown(challenge_id):
    last = (
        ChallengeSubmission.query
        .filter_by(user_id=current_user.id, challenge_id=challenge_id)
        .order_by(ChallengeSubmission.submitted_at.desc())
        .first()
    )
    if not last:
        return jsonify({"locked": False, "hours_remaining": None})
    elapsed  = datetime.utcnow() - last.submitted_at
    cooldown = timedelta(hours=24)
    if elapsed < cooldown:
        hours_left = int((cooldown - elapsed).total_seconds() // 3600) + 1
        return jsonify({"locked": True, "hours_remaining": hours_left})
    return jsonify({"locked": False, "hours_remaining": None})


@app.route('/api/challenges/<int:challenge_id>/submit', methods=['POST'])
@login_required
def submit_challenge(challenge_id):
    if challenge_id not in range(1, 9):
        return jsonify({"error": "Invalid challenge ID (must be 1–8)"}), 400

    last = (
        ChallengeSubmission.query
        .filter_by(user_id=current_user.id, challenge_id=challenge_id)
        .order_by(ChallengeSubmission.submitted_at.desc())
        .first()
    )
    if last:
        elapsed = datetime.utcnow() - last.submitted_at
        if elapsed < timedelta(hours=24):
            hours_left = int((timedelta(hours=24) - elapsed).total_seconds() // 3600) + 1
            return jsonify({"error": f"Task already completed. Try again in {hours_left} hour(s)."}), 429

    before_file = request.files.get("before_photo")
    after_file  = request.files.get("after_photo")

    if not before_file or not after_file:
        return jsonify({"error": "Both before_photo and after_photo are required."}), 400
    if not allowed_file(before_file.filename) or not allowed_file(after_file.filename):
        return jsonify({"error": "Only JPG / PNG / WEBP images are accepted."}), 400

    try:
        start_dt = datetime.fromisoformat(request.form["start_time"])
        end_dt   = datetime.fromisoformat(request.form["end_time"])
    except (KeyError, ValueError):
        return jsonify({"error": "start_time and end_time must be valid ISO datetime strings."}), 400

    duration_sec = int((end_dt - start_dt).total_seconds())
    if duration_sec < 60:
        return jsonify({"error": "Task must take at least 1 minute."}), 400

    before_path = save_photo(before_file, current_user.id, f"task{challenge_id}_before")
    after_path  = save_photo(after_file,  current_user.id, f"task{challenge_id}_after")

    # ── FEATURE 2: AI IMAGE VERIFICATION ──────────────────────
    after_file.seek(0)   # reset stream after save_photo() read it
    image_bytes = after_file.read()
    ai_result   = gemini_service.verify_image(image_bytes, challenge_id)

    # Block clearly irrelevant uploads (high confidence threshold = 85%)
    if ai_result["status"] == "not_relevant" and (ai_result.get("confidence") or 0) > 0.85:
        # Clean up saved files since we're rejecting
        for path in [before_path, after_path]:
            full = os.path.join(os.getcwd(), path.lstrip('/'))
            if os.path.exists(full):
                os.remove(full)
        return jsonify({
            "error": f"⚠️ Photo doesn't match this challenge. "
                     f"{ai_result.get('explanation', '')} "
                     f"Please upload a relevant photo."
        }), 422
    # ───────────────────────────────────────────────

    submission = ChallengeSubmission(
        user_id        = current_user.id,
        challenge_id   = challenge_id,
        challenge_name = CHALLENGE_NAMES.get(challenge_id, ""),
        before_photo   = before_path,
        after_photo    = after_path,
        start_time     = start_dt,
        end_time       = end_dt,
        duration_sec   = duration_sec,
        latitude       = request.form.get("latitude",  type=float),
        longitude      = request.form.get("longitude", type=float),
        status         = 'submitted',
        reward_enabled = False,
        ai_status      = ai_result.get("status"),
        ai_confidence  = ai_result.get("confidence"),
        ai_explanation = ai_result.get("explanation"),
    )
    db.session.add(submission)
    db.session.flush()

    # Add a pending ChallengeAttempt with 0 points — XP granted only on teacher verify
    db.session.add(ChallengeAttempt(
        user_id=current_user.id,
        challenge_id=challenge_id,
        completed=False,
        points_awarded=0,
        time_taken_sec=duration_sec
    ))

    db.session.commit()

    return jsonify({
        "message":       "Challenge submitted! Awaiting teacher verification. 🎉",
        "submission_id": submission.id,
        "duration_sec":  duration_sec,
        "submitted_at":  submission.submitted_at.isoformat(),
    }), 201


@app.route('/api/challenges/my-submissions')
@login_required
def my_submissions():
    subs = (
        ChallengeSubmission.query
        .filter_by(user_id=current_user.id)
        .order_by(ChallengeSubmission.submitted_at.desc())
        .all()
    )
    return jsonify([{
        "id":             s.id,
        "challenge_id":   s.challenge_id,
        "challenge_name": s.challenge_name,
        "duration_sec":   s.duration_sec,
        "submitted_at":   s.submitted_at.isoformat(),
        "status":         s.status,
        "reward_enabled": s.reward_enabled,
    } for s in subs])


@app.route('/api/badges/my-badges')
@login_required
def my_badges():
    badges = UserBadge.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        "badge_key":    b.badge_key,
        "challenge_id": b.challenge_id,
        "earned_at":    b.earned_at.isoformat(),
    } for b in badges])


@app.route('/api/teacher/submissions')
@login_required
def teacher_submissions():
    if current_user.role != "teacher":
        return jsonify({"error": "Access denied"}), 403
    subs = ChallengeSubmission.query.order_by(ChallengeSubmission.submitted_at.desc()).all()
    return jsonify([{
        "id":             s.id,
        "student_name":   s.user.name,
        "student_class":  s.user.student_class,
        "challenge_id":   s.challenge_id,
        "challenge_name": s.challenge_name,
        "duration_sec":   s.duration_sec,
        "latitude":       s.latitude,
        "longitude":      s.longitude,
        "submitted_at":   s.submitted_at.isoformat(),
        "status":         s.status,
        "reward_enabled": s.reward_enabled,
    } for s in subs])


@app.route('/api/teacher/submissions/<int:submission_id>/status', methods=['PATCH'])
@login_required
def update_submission_status(submission_id):
    if current_user.role != "teacher":
        return jsonify({"error": "Access denied"}), 403
    sub        = ChallengeSubmission.query.get_or_404(submission_id)
    data       = request.get_json()
    new_status = data.get("status")
    if new_status not in ("submitted", "verified", "rejected"):
        return jsonify({"error": "status must be: submitted / verified / rejected"}), 400
    sub.status = new_status
    db.session.commit()
    return jsonify({"message": f"Submission {submission_id} marked as {new_status}."})


# ── AUTH ─────────────────────────────────────────────────────────

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/submit-quiz-score", methods=["POST"])
def submit_quiz_score():
    video_id = request.form["video_id"]
    score    = request.form["score"]
    return "OK"


# ── FEATURE 1: GEMINI DYNAMIC QUIZ ───────────────────────────────

@app.route('/dynamic-quiz/<int:video_id>')
@login_required
def dynamic_quiz_page(video_id):
    """Render the Gemini-powered dynamic quiz page."""
    if video_id not in (1, 2, 3):
        return redirect(url_for('videos'))
    video_names = {1: 'Pollution', 2: 'Global Warming', 3: 'Biodiversity'}
    return render_template('dynamic_quiz.html',
                           video_id=video_id,
                           video_name=video_names[video_id])


@app.route('/api/generate-quiz/<int:video_id>')
@login_required
def generate_dynamic_quiz(video_id):
    """Generate 5 MCQs via Gemini and return as JSON."""
    if video_id not in (1, 2, 3):
        return jsonify({"error": "Invalid video_id"}), 400

    # Collect previous questions so Gemini avoids repeating them
    past_attempts = (
        DynamicQuizAttempt.query
        .filter_by(user_id=current_user.id, video_id=video_id)
        .order_by(DynamicQuizAttempt.attempted_at.desc())
        .limit(5)
        .all()
    )
    previous_questions = []
    for attempt in past_attempts:
        try:
            qs = json.loads(attempt.questions_json)
            previous_questions.extend([q.get('question', '') for q in qs])
        except Exception:
            pass

    try:
        questions = gemini_service.generate_quiz(video_id, previous_questions)
        return jsonify({"questions": questions, "video_id": video_id})
    except EnvironmentError:
        return jsonify({"error": "Gemini API key not configured. Please set GEMINI_API_KEY in .env"}), 503
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        return jsonify({"error": f"Quiz generation failed: {str(exc)}"}), 500


@app.route('/api/submit-dynamic-quiz', methods=['POST'])
@login_required
def submit_dynamic_quiz():
    """Save a completed Gemini quiz attempt and update XP."""
    video_id       = request.form.get('video_id', type=int)
    score          = request.form.get('score',    type=int, default=0)
    max_score      = request.form.get('max_score', type=int, default=50)
    questions_json = request.form.get('questions_json', '[]')

    if video_id not in (1, 2, 3):
        return jsonify({"error": "Invalid video_id"}), 400

    # Store the attempt
    db.session.add(DynamicQuizAttempt(
        user_id        = current_user.id,
        video_id       = video_id,
        questions_json = questions_json,
        score          = score,
        max_score      = max_score,
    ))

    # Also update the matching static Quiz model so XP is consistent
    # Quiz1 = Biodiversity (video 3), Quiz2 = Pollution (video 1), Quiz3 = Global Warming (video 2)
    quiz_model_map = {1: Quiz2, 2: Quiz3, 3: Quiz1}
    QuizModel = quiz_model_map.get(video_id)
    if QuizModel:
        db.session.add(QuizModel(user_id=current_user.id, score=score))

    db.session.commit()
    return jsonify({"message": "Score saved!", "score": score, "max_score": max_score})


# ── FEATURE 3: PWA OFFLINE PAGE ────────────────────────────────

@app.route('/offline')
def offline():
    return render_template('offline.html')


@app.route('/service-worker.js')
def service_worker():
    """Serve service worker from root scope (required for PWA)."""
    from flask import send_from_directory
    return send_from_directory('static', 'service-worker.js',
                               mimetype='application/javascript')


# ── FEATURE 4: WEEKLY TEACHER REPORT ───────────────────────────

@app.route('/teacher-weekly-report')
@login_required
def teacher_weekly_report():
    """Weekly class-wise student performance report for teachers."""
    if current_user.role != 'teacher':
        flash("Access restricted to teachers.")
        return redirect(url_for('index'))

    # Query params
    selected_class = request.args.get('class', '').strip()
    from_date_str  = request.args.get('from', '')
    to_date_str    = request.args.get('to',   '')

    # Parse dates
    try:
        from_dt = datetime.strptime(from_date_str, '%Y-%m-%d') if from_date_str else None
        to_dt   = datetime.strptime(to_date_str,   '%Y-%m-%d') if to_date_str   else None
        if to_dt:
            to_dt = to_dt.replace(hour=23, minute=59, second=59)
    except ValueError:
        from_dt = to_dt = None

    # Get all classes for the dropdown
    all_classes = [
        row[0] for row in
        db.session.query(User.student_class)
        .filter(User.role == 'student', User.student_class.isnot(None))
        .distinct().all()
        if row[0]
    ]
    all_classes.sort()

    if not selected_class or not from_dt or not to_dt:
        return render_template('weekly_report.html',
                               all_classes=all_classes,
                               selected_class=selected_class,
                               from_date=from_date_str,
                               to_date=to_date_str,
                               students=None,
                               class_summary=None)

    # Fetch students for the selected class
    students_in_class = User.query.filter_by(role='student', student_class=selected_class).all()

    report_rows = []
    for s in students_in_class:
        # Videos completed in date range
        videos_done = VideoProgress.query.filter(
            VideoProgress.user_id == s.id,
            VideoProgress.completed == True
        ).count()

        # Dynamic quiz attempts in date range
        dyn_attempts = DynamicQuizAttempt.query.filter(
            DynamicQuizAttempt.user_id == s.id,
            DynamicQuizAttempt.attempted_at >= from_dt,
            DynamicQuizAttempt.attempted_at <= to_dt
        ).all()
        dyn_quiz_count = len(dyn_attempts)
        dyn_best_score = max((a.score for a in dyn_attempts), default=0)

        # Challenge submissions in date range
        submissions = ChallengeSubmission.query.filter(
            ChallengeSubmission.user_id == s.id,
            ChallengeSubmission.submitted_at >= from_dt,
            ChallengeSubmission.submitted_at <= to_dt
        ).all()
        challenges_submitted = len(submissions)
        challenges_verified  = sum(1 for sub in submissions if sub.status == 'verified')
        challenges_pending   = sum(1 for sub in submissions if sub.status == 'submitted')
        challenges_rejected  = sum(1 for sub in submissions if sub.status == 'rejected')

        # XP earned in the week
        xp_from_dyn_quiz   = sum(a.score for a in dyn_attempts)
        xp_from_challenges = sum(
            CHALLENGE_CATALOGUE.get(sub.challenge_id, {}).get('points', 50)
            for sub in submissions if sub.status == 'verified'
        )
        weekly_xp = xp_from_dyn_quiz + xp_from_challenges

        # Badges
        badges = [b.badge_key for b in s.badges]

        report_rows.append({
            'id':                    s.id,
            'name':                  s.name,
            'email':                 s.email,
            'student_class':         s.student_class or '—',
            'videos_completed':      videos_done,
            'dyn_quiz_attempts':     dyn_quiz_count,
            'dyn_quiz_best_score':   dyn_best_score,
            'challenges_submitted':  challenges_submitted,
            'challenges_verified':   challenges_verified,
            'challenges_pending':    challenges_pending,
            'challenges_rejected':   challenges_rejected,
            'weekly_xp':             weekly_xp,
            'badges':                badges,
            'total_xp_all_time':     s.total_xp(),
            'last_login':            s.last_login.strftime('%d %b %Y') if s.last_login else 'Never',
        })

    report_rows.sort(key=lambda x: x['weekly_xp'], reverse=True)
    for i, row in enumerate(report_rows):
        row['rank'] = i + 1

    class_summary = {
        'total_students':        len(report_rows),
        'avg_weekly_xp':         round(sum(r['weekly_xp'] for r in report_rows) / len(report_rows), 1) if report_rows else 0,
        'total_videos_watched':  sum(r['videos_completed'] for r in report_rows),
        'total_quizzes_taken':   sum(r['dyn_quiz_attempts'] for r in report_rows),
        'total_challenges_done': sum(r['challenges_verified'] for r in report_rows),
        'top_student':           report_rows[0]['name'] if report_rows else '—',
    }

    return render_template('weekly_report.html',
                           all_classes=all_classes,
                           selected_class=selected_class,
                           from_date=from_date_str,
                           to_date=to_date_str,
                           students=report_rows,
                           class_summary=class_summary)


# ── HELPERS ──────────────────────────────────────────────────────

CHALLENGE_NAMES = {
    1: "Clean Study Area",
    2: "Waste Segregation",
    3: "Energy Saver",
    4: "Plant Care",
    5: "Cleanup Drive",
    6: "Organize School Bag",
    7: "Water Saving",
    8: "Cloth Bag Mission",
}

BADGE_MAP = {
    1: "seedling",
    2: "recycling",
    3: "energy",
    4: "nature",
    5: "eco",
    6: "discipline",
    7: "water",
    8: "earth",
}

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_photo(file, user_id, label):
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"user{user_id}_{label}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{ext}"

    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    # Return browser-friendly URL
    return f"/static/uploads/{filename}"

def get_reward(points):
    if points >= 50:
        return "🏆🌍"
    elif points >= 40:
        return "🥇"
    elif points >= 30:
        return "🥈"
    elif points >= 20:
        return "🥉"
    elif points >= 10:
        return "🌱"
    else:
        return "🍃"

def award_badges(user_id, challenge_id):
    badge_key = BADGE_MAP.get(challenge_id)
    if badge_key:
        if not UserBadge.query.filter_by(user_id=user_id, badge_key=badge_key).first():
            db.session.add(UserBadge(user_id=user_id, badge_key=badge_key, challenge_id=challenge_id))
    completed_count = (
        db.session.query(ChallengeSubmission.challenge_id)
        .filter_by(user_id=user_id)
        .distinct()
        .count()
    )
    if completed_count >= 8:
        if not UserBadge.query.filter_by(user_id=user_id, badge_key="ultimate").first():
            db.session.add(UserBadge(user_id=user_id, badge_key="ultimate"))
    db.session.commit()


# ── RUN ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

VIDEO_CATALOGUE = {
    1: {"title": "Pollution", "max_points": 10},
    2: {"title": "Global Warming", "max_points": 10},
    3: {"title": "Biodiversity", "max_points": 10},
}

CHALLENGE_CATALOGUE = {
    1: {"title": "Clean Study Area", "points": 50},
    2: {"title": "Waste Segregation", "points": 50},
    3: {"title": "Energy Saver", "points": 50},
    4: {"title": "Plant Care", "points": 50},
    5: {"title": "Cleanup Drive", "points": 50},
    6: {"title": "Organize School Bag", "points": 50},
    7: {"title": "Water Saving", "points": 50},
    8: {"title": "Cloth Bag Mission", "points": 50},
}


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))
    student_class = db.Column(db.String(20))
    last_login = db.Column(db.DateTime, nullable=True)   # ← added

    scores = db.relationship('Score', backref='user')
    puzzle_scores = db.relationship('PuzzleScore', backref='user')
    ocean_scores = db.relationship('OceanScore', backref='user')
    waste_scores = db.relationship('WasteScore', backref='user')

    quiz1_scores = db.relationship('Quiz1Score', backref='user')
    quiz2_scores = db.relationship('Quiz2Score', backref='user')
    quiz3_scores = db.relationship('Quiz3Score', backref='user')
    quiz4_scores = db.relationship('Quiz4Score', backref='user')
    quiz5_scores = db.relationship('Quiz5Score', backref='user')
    quiz6_scores = db.relationship('Quiz6Score', backref='user')

    quiz1 = db.relationship('Quiz1', backref='user')
    quiz2 = db.relationship('Quiz2', backref='user')
    quiz3 = db.relationship('Quiz3', backref='user')

    video_progress = db.relationship('VideoProgress', backref='user')
    challenge_attempts = db.relationship('ChallengeAttempt', backref='user')

    badges = db.relationship("UserBadge", backref="user")

    def game_xp(self):
        return (
            max((s.value for s in self.scores), default=0) +
            max((s.value for s in self.puzzle_scores), default=0) +
            max((s.score for s in self.waste_scores), default=0) +
            max((s.score for s in self.ocean_scores), default=0)
        )

    def quiz_xp(self):
        return sum([
            max((s.score for s in self.quiz1_scores), default=0),
            max((s.score for s in self.quiz2_scores), default=0),
            max((s.score for s in self.quiz3_scores), default=0),
            max((s.score for s in self.quiz4_scores), default=0),
            max((s.score for s in self.quiz5_scores), default=0),
            max((s.score for s in self.quiz6_scores), default=0),
        ])

    def video_xp(self):
        video_points = sum(v.points_awarded for v in self.video_progress)
        biodiversity_points  = max([q.score for q in self.quiz1], default=0)
        pollution_points     = max([q.score for q in self.quiz2], default=0)
        globalwarming_points = max([q.score for q in self.quiz3], default=0)
        return video_points + biodiversity_points + pollution_points + globalwarming_points

    def challenge_xp(self):
        return sum(c.points_awarded for c in self.challenge_attempts if c.completed)

    def total_xp(self):
        return self.game_xp() + self.quiz_xp() + self.video_xp() + self.challenge_xp()


class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class PuzzleScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class OceanScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class WasteScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Quiz1Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Quiz2Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Quiz3Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Quiz4Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Quiz5Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Quiz6Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class VideoProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer)
    percent_watched = db.Column(db.Integer)
    completed = db.Column(db.Boolean)
    points_awarded = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Quiz1(db.Model):   # Biodiversity (Video Quiz)
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Quiz2(db.Model):   # Pollution (Video Quiz)
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Quiz3(db.Model):   # Global Warming (Video Quiz)
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class ChallengeAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer)
    completed = db.Column(db.Boolean)
    points_awarded = db.Column(db.Integer)
    time_taken_sec = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class ChallengeSubmission(db.Model):
    __tablename__ = "challenge_submissions"

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    challenge_id   = db.Column(db.Integer, nullable=False)
    challenge_name = db.Column(db.String(100))

    before_photo   = db.Column(db.String(300))
    after_photo    = db.Column(db.String(300))

    start_time     = db.Column(db.DateTime, nullable=False)
    end_time       = db.Column(db.DateTime, nullable=False)
    duration_sec   = db.Column(db.Integer)

    latitude       = db.Column(db.Float)
    longitude      = db.Column(db.Float)

    submitted_at   = db.Column(db.DateTime, default=datetime.utcnow)

    status         = db.Column(db.String(20), default="submitted")
    reward_enabled = db.Column(db.Boolean, default=False)

    teacher_feedback = db.Column(db.Text)
    verified_at      = db.Column(db.DateTime)

    # ── AI image-verification results (Feature 2) ──────────────────
    ai_status      = db.Column(db.String(20))   # relevant / not_relevant / uncertain / ai_unavailable
    ai_confidence  = db.Column(db.Float)
    ai_explanation = db.Column(db.Text)

    user = db.relationship("User", backref="submissions")


class UserBadge(db.Model):
    __tablename__ = "user_badges"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    badge_key    = db.Column(db.String(50), nullable=False)
    challenge_id = db.Column(db.Integer)
    earned_at    = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "badge_key"),)


# ── Feature 1: Dynamic (Gemini-generated) quiz attempts ──────────

class DynamicQuizAttempt(db.Model):
    """Stores every Gemini-generated quiz attempt and its score."""
    __tablename__ = "dynamic_quiz_attempts"

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    video_id       = db.Column(db.Integer, nullable=False)   # 1=Pollution, 2=GlobalWarming, 3=Biodiversity
    questions_json = db.Column(db.Text, nullable=False)      # JSON-serialised list of generated questions
    score          = db.Column(db.Integer, nullable=False)
    max_score      = db.Column(db.Integer, nullable=False)
    attempted_at   = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="dynamic_quiz_attempts")
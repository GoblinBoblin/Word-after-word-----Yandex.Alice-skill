from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class UserProgress(db.Model):
    __tablename__ = 'user_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), unique=True, nullable=False)
    total_score = db.Column(db.Integer, default=0)
    games_played = db.Column(db.Integer, default=0)
    last_played = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.user_id} | Score: {self.total_score}>'

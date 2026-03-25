from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='farmer')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sensor_readings = db.relationship('SensorReading', backref='user', lazy=True)
    field_analyses = db.relationship('FieldAnalysis', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'


class SensorReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    moisture = db.Column(db.Float)
    temperature = db.Column(db.Float)
    ph = db.Column(db.Float)
    nitrogen = db.Column(db.Float)
    phosphorus = db.Column(db.Float)
    potassium = db.Column(db.Float)


class FieldAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    soil_type = db.Column(db.String(200))
    elevation_min = db.Column(db.Integer)
    elevation_max = db.Column(db.Integer)
    maize_suitability = db.Column(db.Integer)
    tomato_suitability = db.Column(db.Integer)
    recommended_crop = db.Column(db.String(100))
    recommendation_text = db.Column(db.Text)

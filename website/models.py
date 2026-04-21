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
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    # Core soil sensors (RS485)
    nitrogen    = db.Column(db.Float)
    phosphorus  = db.Column(db.Float)
    potassium   = db.Column(db.Float)
    temperature = db.Column(db.Float)
    humidity    = db.Column(db.Float)   # soil humidity from RS485 sensor
    ec          = db.Column(db.Float)   # electrical conductivity (µS/cm)
    # Legacy / calculated
    moisture    = db.Column(db.Float)   # alias for humidity when simulated
    ph          = db.Column(db.Float)
    # Rover GPS position at time of reading
    latitude    = db.Column(db.Float)
    longitude   = db.Column(db.Float)

    def to_dict(self):
        return {
            'timestamp':   self.timestamp.strftime('%H:%M'),
            'nitrogen':    self.nitrogen,
            'phosphorus':  self.phosphorus,
            'potassium':   self.potassium,
            'temperature': self.temperature,
            'humidity':    self.humidity,
            'moisture':    self.humidity or self.moisture,
            'ec':          self.ec,
            'ph':          self.ph,
            'latitude':    self.latitude,
            'longitude':   self.longitude,
        }


class RoverCommand(db.Model):
    """Stores the latest path-detection direction for each user's rover to poll."""
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    direction = db.Column(db.String(10), default='STOP')
    coverage  = db.Column(db.Float,    default=0)
    set_at    = db.Column(db.DateTime, default=datetime.utcnow)


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

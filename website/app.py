from flask import Flask, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)

    from config import Config
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    from routes.auth import auth_bp
    from routes.farmer import farmer_bp
    from routes.admin import admin_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(farmer_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    with app.app_context():
        db.create_all()
        _seed_defaults()

    return app


def _seed_defaults():
    from models import User
    if not User.query.filter_by(email='admin@agrobot.com').first():
        admin = User(name='Admin', email='admin@agrobot.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

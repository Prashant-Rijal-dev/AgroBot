from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db

farmer_bp = Blueprint('farmer', __name__, url_prefix='/farmer')


@farmer_bp.route('/dashboard')
@login_required
def dashboard():
    from services.sensor_sim import get_current_readings, get_ai_recommendations, get_alerts
    readings = get_current_readings(current_user.id)
    recommendations = get_ai_recommendations(readings)
    alerts = get_alerts(readings)
    return render_template('farmer/dashboard.html',
                           readings=readings,
                           recommendations=recommendations,
                           alerts=alerts)


@farmer_bp.route('/field-analysis')
@login_required
def field_analysis():
    from models import FieldAnalysis
    history = (FieldAnalysis.query
               .filter_by(user_id=current_user.id)
               .order_by(FieldAnalysis.timestamp.desc())
               .limit(5).all())
    return render_template('farmer/field_analysis.html', history=history)


@farmer_bp.route('/history')
@login_required
def history():
    from models import FieldAnalysis
    page = request.args.get('page', 1, type=int)
    analyses = (FieldAnalysis.query
                .filter_by(user_id=current_user.id)
                .order_by(FieldAnalysis.timestamp.desc())
                .paginate(page=page, per_page=15))
    return render_template('farmer/history.html', analyses=analyses)


@farmer_bp.route('/rover')
@login_required
def rover_control():
    return render_template('farmer/rover_control.html')


@farmer_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            from models import User
            if not name or not email:
                flash('Name and email are required.', 'danger')
            elif email != current_user.email and User.query.filter_by(email=email).first():
                flash('That email is already in use.', 'danger')
            else:
                current_user.name = name
                current_user.email = email
                db.session.commit()
                flash('Profile updated successfully.', 'success')

        elif action == 'change_password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')
            if not current_user.check_password(current_pw):
                flash('Current password is incorrect.', 'danger')
            elif len(new_pw) < 6:
                flash('New password must be at least 6 characters.', 'danger')
            elif new_pw != confirm_pw:
                flash('New passwords do not match.', 'danger')
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                flash('Password changed successfully.', 'success')

        return redirect(url_for('farmer.profile'))

    from models import FieldAnalysis
    analysis_count = FieldAnalysis.query.filter_by(user_id=current_user.id).count()
    return render_template('farmer/profile.html', analysis_count=analysis_count)

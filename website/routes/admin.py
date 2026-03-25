from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.index'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/panel')
@admin_required
def panel():
    from models import User, FieldAnalysis
    from services.sensor_sim import get_current_readings
    users = User.query.order_by(User.created_at.desc()).all()
    total_farmers = User.query.filter_by(role='farmer').count()
    total_admins = User.query.filter_by(role='admin').count()
    total_analyses = FieldAnalysis.query.count()
    sample_readings = get_current_readings()
    return render_template('admin/panel.html',
                           users=users,
                           total_farmers=total_farmers,
                           total_admins=total_admins,
                           total_analyses=total_analyses,
                           sample_readings=sample_readings)

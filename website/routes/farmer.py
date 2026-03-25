from flask import Blueprint, render_template
from flask_login import login_required, current_user

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
               .limit(5)
               .all())
    return render_template('farmer/field_analysis.html', history=history)

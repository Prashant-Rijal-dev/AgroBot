from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/sensor/current')
@login_required
def sensor_current():
    from services.sensor_sim import get_current_readings, get_ai_recommendations, get_alerts
    readings = get_current_readings(current_user.id)
    return jsonify({
        'readings': readings,
        'recommendations': get_ai_recommendations(readings),
        'alerts': get_alerts(readings),
    })


@api_bp.route('/sensor/history')
@login_required
def sensor_history():
    from services.sensor_sim import get_historical_readings
    hours = request.args.get('hours', 24, type=int)
    return jsonify(get_historical_readings(hours=hours, user_id=current_user.id))


@api_bp.route('/field/analyze', methods=['POST'])
def field_analyze():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        lat = float(data['lat'])
        lon = float(data['lon'])
    except (KeyError, ValueError, TypeError):
        return jsonify({'error': 'Valid lat and lon required'}), 400

    from services.field_analysis import query_field
    result = query_field(lat, lon)

    if current_user.is_authenticated:
        from app import db
        from models import FieldAnalysis
        fa = FieldAnalysis(
            user_id=current_user.id,
            latitude=lat,
            longitude=lon,
            soil_type=result.get('soil_type'),
            elevation_min=result.get('elevation_min'),
            elevation_max=result.get('elevation_max'),
            maize_suitability=result.get('maize_suitability'),
            tomato_suitability=result.get('tomato_suitability'),
            recommended_crop=result.get('recommended_crop'),
            recommendation_text=result.get('recommendation_text'),
        )
        db.session.add(fa)
        db.session.commit()

    return jsonify(result)

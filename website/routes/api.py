from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/health')
def health():
    from app import db
    try:
        db.session.execute(db.text('SELECT 1'))
        db_status = 'ok'
    except Exception:
        db_status = 'error'
    return jsonify({'status': 'ok', 'db': db_status})


@api_bp.route('/sensor/current')
@login_required
def sensor_current():
    from services.sensor_sim import get_current_readings, get_ai_recommendations, get_alerts
    from services.ai_model import predict as ml_predict
    readings = get_current_readings(current_user.id)
    ml = ml_predict(
        readings['nitrogen'], readings['phosphorus'], readings['potassium'],
        readings['temperature'], readings['moisture'], readings['ph'],
    )
    return jsonify({
        'readings':        readings,
        'recommendations': get_ai_recommendations(readings),
        'alerts':          get_alerts(readings),
        'ml_prediction':   ml,
    })


@api_bp.route('/crop/predict', methods=['POST'])
@login_required
def crop_predict():
    data = request.get_json() or {}
    try:
        result = __import__('services.ai_model', fromlist=['predict']).predict(
            float(data['nitrogen']),   float(data['phosphorus']),
            float(data['potassium']),  float(data['temperature']),
            float(data['moisture']),   float(data['ph']),
        )
        return jsonify(result)
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/sensor/history')
@login_required
def sensor_history():
    from services.sensor_sim import get_historical_readings
    hours = request.args.get('hours', 24, type=int)
    return jsonify(get_historical_readings(hours=hours, user_id=current_user.id))


@api_bp.route('/field/analyze', methods=['POST'])
@login_required
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

    # Persist to DB
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

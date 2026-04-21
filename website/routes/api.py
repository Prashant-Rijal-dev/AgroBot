from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api')


def _rover_auth():
    """Check X-Rover-Key header. Returns error response or None if OK."""
    key = request.headers.get('X-Rover-Key') or request.args.get('key')
    if key != current_app.config.get('ROVER_API_KEY'):
        return jsonify({'error': 'Unauthorized — invalid rover key'}), 401
    return None


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


@api_bp.route('/rover/data', methods=['POST'])
def rover_data():
    """
    Receive sensor readings from the ESP32 rover and store in DB.
    Auth: X-Rover-Key header.
    Body JSON: { user_id, nitrogen, phosphorus, potassium, temperature,
                 humidity, ec, ph (optional), latitude (optional), longitude (optional) }
    """
    err = _rover_auth()
    if err: return err

    data = request.get_json() or {}
    try:
        user_id = int(data.get('user_id', 1))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid user_id'}), 400

    from models import SensorReading
    from app import db

    row = SensorReading(
        user_id     = user_id,
        nitrogen    = data.get('nitrogen'),
        phosphorus  = data.get('phosphorus'),
        potassium   = data.get('potassium'),
        temperature = data.get('temperature'),
        humidity    = data.get('humidity'),
        moisture    = data.get('humidity'),   # keep in sync
        ec          = data.get('ec'),
        ph          = data.get('ph'),
        latitude    = data.get('latitude'),
        longitude   = data.get('longitude'),
    )
    db.session.add(row)
    db.session.commit()
    return jsonify({'status': 'ok', 'id': row.id})



@api_bp.route('/rover/status')
@login_required
def rover_status():
    """
    Return the last N rover readings with GPS for the rover control page.
    """
    limit = request.args.get('limit', 50, type=int)
    from models import SensorReading
    rows = (SensorReading.query
            .filter_by(user_id=current_user.id)
            .order_by(SensorReading.timestamp.desc())
            .limit(limit).all())

    if not rows:
        return jsonify({'online': False, 'readings': [], 'trail': []})

    latest = rows[0]
    age_seconds = (datetime.utcnow() - latest.timestamp).total_seconds()
    trail = [
        {'lat': r.latitude, 'lng': r.longitude,
         'timestamp': r.timestamp.isoformat()}
        for r in reversed(rows) if r.latitude and r.longitude
    ]
    return jsonify({
        'online':   age_seconds < 120,   # online if data within last 2 min
        'last_seen': latest.timestamp.isoformat(),
        'latest':   latest.to_dict(),
        'trail':    trail,
        'readings': [r.to_dict() for r in reversed(rows[:20])],
    })


@api_bp.route('/rover/path', methods=['POST'])
@login_required
def rover_path():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    file = request.files['image']
    if not file or file.filename == '':
        return jsonify({'error': 'Empty file'}), 400
    image_bytes = file.read()
    from services.path_detection import predict_path
    result = predict_path(image_bytes)

    # Save direction so the rover can poll it
    from models import RoverCommand
    from app import db
    cmd = RoverCommand.query.filter_by(user_id=current_user.id).first()
    if cmd:
        cmd.direction = result.get('direction', 'STOP')
        cmd.coverage  = result.get('coverage', 0)
        cmd.set_at    = datetime.utcnow()
    else:
        cmd = RoverCommand(user_id=current_user.id,
                           direction=result.get('direction', 'STOP'),
                           coverage=result.get('coverage', 0))
        db.session.add(cmd)
    db.session.commit()

    return jsonify(result)


@api_bp.route('/rover/command')
def rover_command():
    """
    ESP32 polls this to get the latest direction command.
    Auth: X-Rover-Key header + user_id query param.
    """
    err = _rover_auth()
    if err: return err

    user_id = request.args.get('user_id', 1, type=int)
    from models import RoverCommand
    cmd = RoverCommand.query.filter_by(user_id=user_id).first()
    if not cmd:
        return jsonify({'direction': 'STOP', 'coverage': 0, 'set_at': None})
    return jsonify({
        'direction': cmd.direction,
        'coverage':  cmd.coverage,
        'set_at':    cmd.set_at.isoformat(),
    })


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

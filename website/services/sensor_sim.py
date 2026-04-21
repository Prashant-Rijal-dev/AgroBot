import random
import math
from datetime import datetime, timedelta


# ── Helpers ────────────────────────────────────────────────────────────────

def _base(user_id):
    seed = (user_id or 1) * 13
    rng  = random.Random(seed)
    return {
        'moisture':     rng.uniform(45, 70),
        'temperature':  rng.uniform(20, 30),
        'ph':           rng.uniform(5.8, 7.2),
        'nitrogen':     rng.uniform(30, 60),
        'phosphorus':   rng.uniform(20, 45),
        'potassium':    rng.uniform(40, 80),
        'humidity':     rng.uniform(45, 70),
        'ec':           rng.uniform(200, 800),
    }


def _reading_to_dict(r):
    """Convert a SensorReading ORM row to the standard readings dict."""
    return {
        'moisture':    round(r.humidity or r.moisture or 0, 1),
        'humidity':    round(r.humidity or 0, 1),
        'temperature': round(r.temperature or 0, 1),
        'ph':          round(r.ph or 6.5, 2),
        'nitrogen':    round(r.nitrogen or 0, 1),
        'phosphorus':  round(r.phosphorus or 0, 1),
        'potassium':   round(r.potassium or 0, 1),
        'ec':          round(r.ec or 0, 1),
        'timestamp':   r.timestamp.isoformat(),
    }


# ── Public API ────────────────────────────────────────────────────────────

def get_current_readings(user_id=None):
    """Return the latest sensor reading — real DB data if available, else simulated."""
    try:
        from models import SensorReading
        row = (SensorReading.query
               .filter_by(user_id=user_id)
               .order_by(SensorReading.timestamp.desc())
               .first())
        if row:
            return _reading_to_dict(row)
    except Exception:
        pass

    # Fallback: simulate
    b = _base(user_id)
    return {
        'moisture':    round(b['moisture']    + random.uniform(-2, 2), 1),
        'humidity':    round(b['humidity']    + random.uniform(-2, 2), 1),
        'temperature': round(b['temperature'] + random.uniform(-0.5, 0.5), 1),
        'ph':          round(b['ph']          + random.uniform(-0.1, 0.1), 2),
        'nitrogen':    round(b['nitrogen']    + random.uniform(-2, 2), 1),
        'phosphorus':  round(b['phosphorus']  + random.uniform(-1, 1), 1),
        'potassium':   round(b['potassium']   + random.uniform(-3, 3), 1),
        'ec':          round(b['ec']          + random.uniform(-20, 20), 1),
        'timestamp':   datetime.utcnow().isoformat(),
    }


def get_historical_readings(hours=24, user_id=None):
    """Return hourly readings — real DB rows if available, else simulated."""
    try:
        from models import SensorReading
        since = datetime.utcnow() - timedelta(hours=hours)
        rows = (SensorReading.query
                .filter_by(user_id=user_id)
                .filter(SensorReading.timestamp >= since)
                .order_by(SensorReading.timestamp.asc())
                .all())
        if rows:
            return [r.to_dict() for r in rows]
    except Exception:
        pass

    # Fallback: simulate
    b   = _base(user_id)
    now = datetime.utcnow()
    rng = random.Random((user_id or 1) * 7)
    result = []
    for i in range(hours, 0, -1):
        t    = now - timedelta(hours=i)
        wave = math.sin(2 * math.pi * t.hour / 24)
        result.append({
            'timestamp':   t.strftime('%H:%M'),
            'moisture':    round(b['moisture']    + wave * 5  + rng.uniform(-1, 1),    1),
            'humidity':    round(b['humidity']    + wave * 5  + rng.uniform(-1, 1),    1),
            'temperature': round(b['temperature'] + wave * 3  + rng.uniform(-0.3, 0.3), 1),
            'ph':          round(b['ph']          + rng.uniform(-0.05, 0.05),           2),
            'nitrogen':    round(b['nitrogen']    + rng.uniform(-3, 3),                 1),
            'phosphorus':  round(b['phosphorus']  + rng.uniform(-2, 2),                 1),
            'potassium':   round(b['potassium']   + rng.uniform(-4, 4),                 1),
            'ec':          round(b['ec']          + rng.uniform(-30, 30),               1),
        })
    return result


def get_ai_recommendations(readings):
    moisture = readings.get('moisture') or readings.get('humidity') or 60
    temp     = readings.get('temperature', 25)
    ph       = readings.get('ph', 6.5)
    nitrogen = readings.get('nitrogen', 40)
    phos     = readings.get('phosphorus', 30)
    potass   = readings.get('potassium', 50)
    ec       = readings.get('ec', 400)

    recs = []

    if moisture < 40:
        recs.append({'type': 'warning', 'icon': 'droplet',
                     'message': f'Soil humidity is low ({moisture}%). Consider irrigation within 24 hours.'})
    elif moisture > 80:
        recs.append({'type': 'info', 'icon': 'droplet-fill',
                     'message': f'Soil humidity is high ({moisture}%). Ensure proper drainage to prevent root rot.'})
    else:
        recs.append({'type': 'success', 'icon': 'droplet-half',
                     'message': f'Soil humidity is optimal ({moisture}%). No irrigation needed.'})

    if temp > 35:
        recs.append({'type': 'danger', 'icon': 'thermometer-high',
                     'message': f'Temperature is very high ({temp}°C). Consider shade nets or evening irrigation.'})
    elif temp < 10:
        recs.append({'type': 'warning', 'icon': 'thermometer-low',
                     'message': f'Temperature is low ({temp}°C). Risk of frost — protect sensitive crops.'})
    else:
        recs.append({'type': 'success', 'icon': 'thermometer-half',
                     'message': f'Temperature is within safe range ({temp}°C).'})

    if ph < 5.5:
        recs.append({'type': 'warning', 'icon': 'flask',
                     'message': f'Soil is too acidic (pH {ph}). Apply lime to raise pH.'})
    elif ph > 7.5:
        recs.append({'type': 'warning', 'icon': 'flask',
                     'message': f'Soil is too alkaline (pH {ph}). Add sulfur or organic matter to lower pH.'})
    else:
        recs.append({'type': 'success', 'icon': 'flask',
                     'message': f'Soil pH is ideal ({ph}) for most crops.'})

    if nitrogen < 30:
        recs.append({'type': 'danger', 'icon': 'bar-chart-fill',
                     'message': f'Nitrogen critically low ({nitrogen} mg/kg). Apply nitrogen-rich fertilizer immediately.'})
    elif nitrogen < 50:
        recs.append({'type': 'warning', 'icon': 'bar-chart',
                     'message': f'Nitrogen slightly low ({nitrogen} mg/kg). Consider urea or compost top-dressing.'})
    else:
        recs.append({'type': 'success', 'icon': 'bar-chart',
                     'message': f'Nitrogen levels are adequate ({nitrogen} mg/kg).'})

    if phos < 20:
        recs.append({'type': 'warning', 'icon': 'activity',
                     'message': f'Phosphorus is low ({phos} mg/kg). Apply DAP or bone meal.'})
    if potass < 35:
        recs.append({'type': 'warning', 'icon': 'lightning',
                     'message': f'Potassium is low ({potass} mg/kg). Apply potash fertilizer.'})
    if ec > 1200:
        recs.append({'type': 'danger', 'icon': 'plug',
                     'message': f'EC is very high ({ec} µS/cm). Soil salinity may inhibit crop growth — leach with water.'})
    elif ec < 150:
        recs.append({'type': 'warning', 'icon': 'plug',
                     'message': f'EC is very low ({ec} µS/cm). Soil may lack soluble nutrients.'})

    return recs


def get_alerts(readings):
    alerts = []
    moisture = readings.get('moisture') or readings.get('humidity') or 60
    temp     = readings.get('temperature', 25)
    ph       = readings.get('ph', 6.5)
    nitrogen = readings.get('nitrogen', 40)
    ec       = readings.get('ec', 400)

    if moisture < 35:
        alerts.append({'level': 'danger',  'message': f'Critical: Soil humidity below 35% ({moisture}%)', 'time': 'Just now'})
    if temp > 38:
        alerts.append({'level': 'danger',  'message': f'Critical: Temperature {temp}°C exceeds safe limit', 'time': 'Just now'})
    if nitrogen < 25:
        alerts.append({'level': 'warning', 'message': f'Low nitrogen detected ({nitrogen} mg/kg)', 'time': '5 min ago'})
    if ph < 5.0 or ph > 8.0:
        alerts.append({'level': 'warning', 'message': f'pH out of safe range: {ph}', 'time': '10 min ago'})
    if ec > 1500:
        alerts.append({'level': 'danger',  'message': f'High soil salinity: EC {ec} µS/cm', 'time': 'Just now'})

    if not alerts:
        alerts.append({'level': 'success', 'message': 'All sensors operating within normal range', 'time': 'Just now'})

    return alerts

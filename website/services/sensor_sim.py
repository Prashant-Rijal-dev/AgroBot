import random
import math
from datetime import datetime, timedelta


def _base(user_id):
    """Stable per-user base values."""
    seed = (user_id or 1) * 13
    rng = random.Random(seed)
    return {
        'moisture':     rng.uniform(45, 70),
        'temperature':  rng.uniform(20, 30),
        'ph':           rng.uniform(5.8, 7.2),
        'nitrogen':     rng.uniform(30, 60),
        'phosphorus':   rng.uniform(20, 45),
        'potassium':    rng.uniform(40, 80),
    }


def get_current_readings(user_id=None):
    b = _base(user_id)
    return {
        'moisture':    round(b['moisture']    + random.uniform(-2, 2), 1),
        'temperature': round(b['temperature'] + random.uniform(-0.5, 0.5), 1),
        'ph':          round(b['ph']          + random.uniform(-0.1, 0.1), 2),
        'nitrogen':    round(b['nitrogen']    + random.uniform(-2, 2), 1),
        'phosphorus':  round(b['phosphorus']  + random.uniform(-1, 1), 1),
        'potassium':   round(b['potassium']   + random.uniform(-3, 3), 1),
        'timestamp':   datetime.utcnow().isoformat(),
    }


def get_historical_readings(hours=24, user_id=None):
    b = _base(user_id)
    now = datetime.utcnow()
    readings = []
    rng = random.Random((user_id or 1) * 7)

    for i in range(hours, 0, -1):
        t = now - timedelta(hours=i)
        wave = math.sin(2 * math.pi * t.hour / 24)
        readings.append({
            'timestamp':   t.strftime('%H:%M'),
            'moisture':    round(b['moisture']    + wave * 5  + rng.uniform(-1, 1),   1),
            'temperature': round(b['temperature'] + wave * 3  + rng.uniform(-0.3, 0.3), 1),
            'ph':          round(b['ph']          + rng.uniform(-0.05, 0.05),          2),
            'nitrogen':    round(b['nitrogen']    + rng.uniform(-3, 3),                1),
            'phosphorus':  round(b['phosphorus']  + rng.uniform(-2, 2),                1),
            'potassium':   round(b['potassium']   + rng.uniform(-4, 4),                1),
        })
    return readings


def get_ai_recommendations(readings):
    moisture = readings.get('moisture', 60)
    temp     = readings.get('temperature', 25)
    ph       = readings.get('ph', 6.5)
    nitrogen = readings.get('nitrogen', 40)
    phos     = readings.get('phosphorus', 30)
    potass   = readings.get('potassium', 50)

    recs = []

    # Moisture
    if moisture < 40:
        recs.append({'type': 'warning', 'icon': 'droplet',
                     'message': f'Soil moisture is low ({moisture}%). Consider irrigation within 24 hours.'})
    elif moisture > 80:
        recs.append({'type': 'info', 'icon': 'droplet-fill',
                     'message': f'Soil moisture is high ({moisture}%). Ensure proper drainage to prevent root rot.'})
    else:
        recs.append({'type': 'success', 'icon': 'droplet-half',
                     'message': f'Soil moisture is optimal ({moisture}%). No irrigation needed.'})

    # Temperature
    if temp > 35:
        recs.append({'type': 'danger', 'icon': 'thermometer-high',
                     'message': f'Temperature is very high ({temp}°C). Consider shade nets or evening irrigation.'})
    elif temp < 10:
        recs.append({'type': 'warning', 'icon': 'thermometer-low',
                     'message': f'Temperature is low ({temp}°C). Risk of frost — protect sensitive crops.'})
    else:
        recs.append({'type': 'success', 'icon': 'thermometer-half',
                     'message': f'Temperature is within safe range ({temp}°C).'})

    # pH
    if ph < 5.5:
        recs.append({'type': 'warning', 'icon': 'flask',
                     'message': f'Soil is too acidic (pH {ph}). Apply lime to raise pH.'})
    elif ph > 7.5:
        recs.append({'type': 'warning', 'icon': 'flask',
                     'message': f'Soil is too alkaline (pH {ph}). Add sulfur or organic matter to lower pH.'})
    else:
        recs.append({'type': 'success', 'icon': 'flask',
                     'message': f'Soil pH is ideal ({ph}) for most crops.'})

    # NPK
    if nitrogen < 30:
        recs.append({'type': 'danger', 'icon': 'bar-chart-fill',
                     'message': f'Nitrogen critically low ({nitrogen} mg/kg). Apply nitrogen-rich fertilizer immediately.'})
    elif nitrogen < 50:
        recs.append({'type': 'warning', 'icon': 'bar-chart',
                     'message': f'Nitrogen slightly low ({nitrogen} mg/kg). Consider a urea or compost top-dressing.'})
    else:
        recs.append({'type': 'success', 'icon': 'bar-chart',
                     'message': f'Nitrogen levels are adequate ({nitrogen} mg/kg).'})

    if phos < 20:
        recs.append({'type': 'warning', 'icon': 'activity',
                     'message': f'Phosphorus is low ({phos} mg/kg). Apply DAP or bone meal.'})

    if potass < 35:
        recs.append({'type': 'warning', 'icon': 'lightning',
                     'message': f'Potassium is low ({potass} mg/kg). Apply potash fertilizer.'})

    return recs


def get_alerts(readings):
    alerts = []
    moisture = readings.get('moisture', 60)
    temp     = readings.get('temperature', 25)
    ph       = readings.get('ph', 6.5)
    nitrogen = readings.get('nitrogen', 40)

    if moisture < 35:
        alerts.append({'level': 'danger', 'message': 'Critical: Soil moisture below 35%', 'time': 'Just now'})
    if temp > 38:
        alerts.append({'level': 'danger', 'message': f'Critical: Temperature {temp}°C exceeds safe limit', 'time': 'Just now'})
    if nitrogen < 25:
        alerts.append({'level': 'warning', 'message': f'Low nitrogen detected ({nitrogen} mg/kg)', 'time': '5 min ago'})
    if ph < 5.0 or ph > 8.0:
        alerts.append({'level': 'warning', 'message': f'pH out of safe range: {ph}', 'time': '10 min ago'})

    if not alerts:
        alerts.append({'level': 'success', 'message': 'All sensors operating within normal range', 'time': 'Just now'})

    return alerts

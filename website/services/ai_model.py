"""
AgroBot — ML Crop Recommendation Service
Loads the trained Random Forest model and provides predictions.
"""
import os
import numpy as np

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')

_model   = None
_encoder = None


def _load():
    global _model, _encoder
    if _model is None:
        try:
            import joblib
            _model   = joblib.load(os.path.join(MODEL_DIR, 'crop_model.pkl'))
            _encoder = joblib.load(os.path.join(MODEL_DIR, 'label_encoder.pkl'))
        except Exception as e:
            print(f'[ai_model] Could not load model: {e}')


def predict(nitrogen, phosphorus, potassium, temperature, moisture, ph):
    """
    Predict the recommended crop from sensor readings.
    Returns a dict with crop name, confidence, and top-3 probabilities.
    """
    _load()
    if _model is None:
        return {'crop': 'Unknown', 'confidence': 0, 'top3': []}

    inp = np.array([[nitrogen, phosphorus, potassium, temperature, moisture, ph]])
    pred_idx = _model.predict(inp)[0]
    proba    = _model.predict_proba(inp)[0]
    crop     = _encoder.inverse_transform([pred_idx])[0]
    confidence = round(float(proba[pred_idx]) * 100, 1)

    top3 = sorted(
        [{'crop': _encoder.inverse_transform([i])[0], 'probability': round(float(p) * 100, 1)}
         for i, p in enumerate(proba)],
        key=lambda x: -x['probability']
    )[:3]

    return {
        'crop':       crop,
        'confidence': confidence,
        'top3':       top3,
    }

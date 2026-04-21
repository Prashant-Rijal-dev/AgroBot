import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'agrobot-dev-secret-key'
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') or
        'sqlite:///' + os.path.join(BASE_DIR, 'agrobot.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Geospatial data paths — overridable via environment (used in Docker)
    # Rover authentication token — ESP32 must send this in X-Rover-Key header
    ROVER_API_KEY  = os.environ.get('ROVER_API_KEY') or 'agrobot-rover-key-2025'

    SOIL_SHAPEFILE = os.environ.get('SOIL_SHAPEFILE') or os.path.join(PROJECT_ROOT, 'parentsoil', 'soilparent.shp')
    MAIZE_TIF      = os.environ.get('MAIZE_TIF')      or os.path.join(PROJECT_ROOT, 'Datasets', 'Maize.tif')
    TOMATO_TIF     = os.environ.get('TOMATO_TIF')     or os.path.join(PROJECT_ROOT, 'Datasets', 'Tomato.tif')

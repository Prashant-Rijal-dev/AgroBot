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

    # Geospatial data paths
    SOIL_SHAPEFILE = os.path.join(PROJECT_ROOT, 'parentsoil', 'soilparent.shp')
    MAIZE_TIF = os.path.join(PROJECT_ROOT, 'Datasets', 'Maize.tif')
    TOMATO_TIF = os.path.join(PROJECT_ROOT, 'Datasets', 'Tomato.tif')

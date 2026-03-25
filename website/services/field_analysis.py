import os

try:
    import geopandas as gpd
    from shapely.geometry import Point
    import rasterio
    GEO_AVAILABLE = True
except ImportError:
    GEO_AVAILABLE = False

_soil_gdf = None


def _load_soil(app):
    global _soil_gdf
    if _soil_gdf is None and GEO_AVAILABLE:
        try:
            path = app.config['SOIL_SHAPEFILE']
            _soil_gdf = gpd.read_file(path)
        except Exception as e:
            app.logger.error(f'Failed to load soil shapefile: {e}')
    return _soil_gdf


def _sample_tif(tif_path, lat, lon):
    try:
        with rasterio.open(tif_path) as src:
            row, col = src.index(lon, lat)
            if 0 <= row < src.height and 0 <= col < src.width:
                val = src.read(1)[row, col]
                if src.nodata is None or val != src.nodata:
                    return int(val)
    except Exception:
        pass
    return None


def _suitability_label(value):
    if value is None:
        return 'Unknown', 'secondary'
    if value >= 100:
        return 'Very High', 'success'
    if value >= 70:
        return 'High', 'primary'
    if value >= 40:
        return 'Moderate', 'warning'
    return 'Low', 'danger'


def _generate_recommendation(maize, tomato, soil, elev_min, elev_max):
    maize_label, _ = _suitability_label(maize)
    tomato_label, _ = _suitability_label(tomato)

    if maize is None and tomato is None:
        return {
            'recommended_crop': 'Outside mapped area',
            'recommendation_text': 'Location is outside the mapped area. Please click within Nepal.',
            'maize_label': 'Unknown',
            'tomato_label': 'Unknown',
            'maize_pct': 0,
            'tomato_pct': 0,
        }

    maize_pct = round((maize / 127) * 100) if maize else 0
    tomato_pct = round((tomato / 127) * 100) if tomato else 0

    if maize is not None and tomato is not None:
        primary, secondary = ('Maize', 'Tomato') if maize >= tomato else ('Tomato', 'Maize')
        primary_val = maize if primary == 'Maize' else tomato
        secondary_val = tomato if primary == 'Maize' else maize
        primary_label, _ = _suitability_label(primary_val)
        secondary_label, _ = _suitability_label(secondary_val)
    elif maize is not None:
        primary, primary_val, primary_label = 'Maize', maize, maize_label
        secondary = secondary_val = secondary_label = None
    else:
        primary, primary_val, primary_label = 'Tomato', tomato, tomato_label
        secondary = secondary_val = secondary_label = None

    text = (f"Based on your soil type ({soil}) and geospatial data, "
            f"{primary} is the recommended crop with {primary_label.lower()} suitability "
            f"(score: {primary_val}/127).")

    if secondary:
        text += (f" {secondary} also shows {secondary_label.lower()} suitability "
                 f"(score: {secondary_val}/127).")

    if elev_min and elev_max:
        text += f" Field elevation: {elev_min}m – {elev_max}m."

    return {
        'recommended_crop': primary,
        'recommendation_text': text,
        'maize_label': maize_label,
        'tomato_label': tomato_label,
        'maize_pct': maize_pct,
        'tomato_pct': tomato_pct,
    }


def query_field(lat, lon):
    from flask import current_app

    result = {
        'latitude': round(lat, 5),
        'longitude': round(lon, 5),
        'soil_type': 'Unknown',
        'elevation_min': None,
        'elevation_max': None,
        'maize_suitability': None,
        'tomato_suitability': None,
    }

    if GEO_AVAILABLE:
        gdf = _load_soil(current_app)
        if gdf is not None:
            try:
                point = Point(lon, lat)
                match = gdf[gdf.contains(point)]
                if not match.empty:
                    row = match.iloc[0]
                    result['soil_type'] = str(row.get('NAME', 'Unknown'))
                    result['elevation_min'] = int(row.get('Elev_min', 0) or 0)
                    result['elevation_max'] = int(row.get('Elev_max', 0) or 0)
            except Exception as e:
                current_app.logger.error(f'Soil query error: {e}')

        maize_val = _sample_tif(current_app.config['MAIZE_TIF'], lat, lon)
        tomato_val = _sample_tif(current_app.config['TOMATO_TIF'], lat, lon)
        result['maize_suitability'] = maize_val
        result['tomato_suitability'] = tomato_val
    else:
        # Fallback mock for Nepal bounds
        if 80.0 <= lon <= 88.5 and 26.0 <= lat <= 30.5:
            result['soil_type'] = 'Fluvial non calcareous'
            result['elevation_min'] = 300
            result['elevation_max'] = 1500
            result['maize_suitability'] = 85
            result['tomato_suitability'] = 72

    rec = _generate_recommendation(
        result['maize_suitability'],
        result['tomato_suitability'],
        result['soil_type'],
        result['elevation_min'],
        result['elevation_max'],
    )
    result.update(rec)
    return result

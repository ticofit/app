# Archivo de compatibilidad para mapview
try:
    from mapview import MapView, MapMarker, MapLayer
    try:
        from mapview import MarkerMapLayer
    except ImportError:
        # Si MarkerMapLayer no existe, crear una clase vacía
        class MarkerMapLayer(MapLayer):
            pass
except ImportError as e:
    print(f"Error importando mapview: {e}")
    raise

# Configuración específica para Android
import kivy
from kivy.utils import platform

def configure_for_platform():
    if platform == 'android':
        # Configuraciones específicas para Android
        from android.permissions import request_permissions, Permission
        request_permissions([
            Permission.ACCESS_FINE_LOCATION,
            Permission.ACCESS_COARSE_LOCATION,
            Permission.VIBRATE,
            Permission.WRITE_EXTERNAL_STORAGE
        ])
    else:
        # En PC, deshabilitar sensores
        import os
        os.environ['KIVY_WINDOW'] = 'sdl2'
        
# Llamar al inicio de la app
configure_for_platform()

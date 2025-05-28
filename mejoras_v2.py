# TicoFit v2.0 - Mejoras adicionales

from kivy.properties import BooleanProperty

# Método mejorado para pantalla de completado
def mostrar_pantalla_completado_mejorada(self):
    """Mostrar pantalla cuando se completa toda la rutina"""
    self.ejercicio_actual = "🎉 ¡MUY BUEN TRABAJO!"
    self.frase = "Lo logramos juntos. Has completado tu rutina diaria. ¡Felicitaciones! 💪"
    self.pasos = [
        "✅ Rutina completada exitosamente",
        "🔥 Has quemado calorías y fortalecido tu cuerpo", 
        "💚 Tu salud te lo agradece",
        "📈 Cada día eres más fuerte",
        "🎯 ¡Nos vemos mañana para más!"
    ]
    self.musculos = "Todo tu cuerpo se benefició hoy"
    self.cantidad_recomendada = "¡Descansa y hidrátate!"
    self.tiempo_formateado = "00:00"
    
    # Detener servicio en segundo plano
    if 'background_service' in globals():
        background_service.stop()
    
    # Marcar rutina como completada
    self.rutina_completada = True
    print("🎉 Rutina completada - Pantalla de felicitación mostrada")

print("✅ Mejoras v2.0 cargadas")

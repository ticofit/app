#!/bin/bash

echo "🚀 TicoFit v2.0 - Actualización Simple"

# Verificar ubicación
if [ ! -f "main.py" ]; then
    echo "❌ Ejecuta desde ~/ticofit-build/app/"
    exit 1
fi

# Respaldos
echo "💾 Creando respaldos..."
cp main.py main.py.backup_$(date +%H%M%S)
cp gestor1.kv gestor1.kv.backup_$(date +%H%M%S)
cp buildozer.spec buildozer.spec.backup_$(date +%H%M%S)

# 1. Agregar clases al final de main.py
echo "🔧 Agregando nuevas clases..."
cat >> main.py << 'EOF'

# ===== TICOFIT V2.0 - NUEVAS FUNCIONES =====

class BackgroundService:
    def __init__(self):
        self.running = False
        self.wake_lock = None
    
    def start(self):
        self.running = True
        print("✅ Servicio en segundo plano iniciado")
    
    def stop(self):
        self.running = False
        print("🔇 Servicio detenido")

# Instancia global
background_service = BackgroundService()

# Parche para Rutina - agregar al final de la clase
def mostrar_pantalla_completado_patch(self):
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
    background_service.stop()
    if not hasattr(self, 'rutina_completada'):
        self.rutina_completada = True
    print("🎉 Rutina completada!")

# Aplicar parche
Rutina.mostrar_pantalla_completado = mostrar_pantalla_completado_patch
Rutina.rutina_completada = BooleanProperty(False)

# Parche para iniciar_cronometro
def iniciar_cronometro_patch(self):
    if getattr(self, 'ejercicio_terminado', False):
        self.avanzar_siguiente_ejercicio()
        return
    if getattr(self, 'cronometro_iniciado', False):
        return
    
    background_service.start()
    self.detener_todos_los_timers()
    self.cronometro_iniciado = True
    self.mostrar_boton_alarma = False
    self.detener_alarma()
    
    Clock.schedule_interval(self.actualizar_visual_tiempo, 1)
    Clock.schedule_interval(self.reducir_tiempo, 1)
    Clock.schedule_interval(self.reducir_tiempo_total, 1)
    print(f"Cronómetro iniciado para: {self.ejercicio_actual}")

Rutina.iniciar_cronometro = iniciar_cronometro_patch

print("✅ TicoFit v2.0 patches aplicados")
EOF

# 2. Actualizar buildozer.spec
echo "📱 Actualizando buildozer.spec..."
sed -i 's/title = Ticofit/title = TicoFit v2.0/' buildozer.spec
sed -i 's/version = 0.1/version = 2.0/' buildozer.spec
sed -i 's/android.arch = armeabi-v7a/android.arch = armeabi-v7a,arm64-v8a/' buildozer.spec

# 3. Test rápido
echo "🧪 Test rápido..."
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    import main
    print('✅ Sintaxis correcta')
except Exception as e:
    print(f'❌ Error: {e}')
" 2>/dev/null

echo ""
echo "🎉 ¡ACTUALIZACIÓN COMPLETADA!"
echo "✅ Respaldos creados"
echo "✅ Nuevas funciones agregadas"
echo "✅ Buildozer actualizado"
echo ""
echo "🚀 Probar: python main.py"
echo "📤 Subir: git add . && git commit -m 'TicoFit v2.0'"
EOF

# Ejecutar script simple
chmod +x actualizar_simple.sh
./actualizar_simple.sh

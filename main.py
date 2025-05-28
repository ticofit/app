from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty, NumericProperty, ListProperty, BooleanProperty, ObjectProperty
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.core.audio import SoundLoader
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp
from kivy_garden.mapview import MapView, MapMarker, MapLayer
try:
    from kivy_garden.mapview import MarkerMapLayer
except ImportError:
    MarkerMapLayer = MapLayer
from plyer import gps, accelerometer, notification, vibrator, filechooser
import json
import datetime
import os
import time
import math
import webbrowser
import threading
import shutil
import requests
from io import BytesIO
from functools import partial


# Variables para controlar disponibilidad de sensores
ACCELEROMETER_AVAILABLE = False
GPS_AVAILABLE = False

# Verificar disponibilidad de sensores
try:
    from plyer import accelerometer
    accelerometer.enable()
    ACCELEROMETER_AVAILABLE = True
    accelerometer.disable()
except:
    print("Acelerómetro no disponible en este dispositivo")

try:
    from plyer import gps
    GPS_AVAILABLE = True
except:
    print("GPS no disponible en este dispositivo")


# Constantes de configuración
MAX_DIAS_HISTORIAL = 30
RUTA_DATOS = "datos_salud"
RUTA_MAPAS = os.path.join(RUTA_DATOS, "mapas")

# Asegurar que existan las carpetas necesarias
os.makedirs(RUTA_DATOS, exist_ok=True)
os.makedirs(RUTA_MAPAS, exist_ok=True)

# Clase para dibujar la ruta en el mapa
class RouteMapLayer(MapLayer):
    def __init__(self, **kwargs):
        super(RouteMapLayer, self).__init__(**kwargs)
        self.points = []
        self.line_width = 3
        self.line_color = (0, 0.7, 1, 1)  # Azul claro

    def add_point(self, lat, lon):
        self.points.append((lat, lon))
        self.reposition()

    def clear_points(self):
        self.points = []
        self.reposition()

    def reposition(self):
        mapview = self.parent
        if not mapview:
            return
        
        self.canvas.clear()
        if len(self.points) < 2:
            return
            
        from kivy.graphics import Line, Color
        with self.canvas:
            Color(*self.line_color)
            for i in range(len(self.points) - 1):
                x1, y1 = mapview.get_window_xy_from_coordinate(self.points[i][0], self.points[i][1])
                x2, y2 = mapview.get_window_xy_from_coordinate(self.points[i+1][0], self.points[i+1][1])
                Line(points=[x1, y1, x2, y2], width=self.line_width)

class Bienvenida(Screen):
    frase_dia = StringProperty("")

    def on_enter(self):
        try:
            with open("frases.json", encoding="utf-8") as f:
                frases = json.load(f)
                self.frase_dia = frases[datetime.datetime.now().day % len(frases)]
        except Exception as e:
            print(f"Error al cargar frase: {e}")
            self.frase_dia = "¡Hoy será un gran día para sudar con amor!"

class Rutina(Screen):
    mostrar_boton_alarma = BooleanProperty(False)
    tiempo_formateado = StringProperty("00:00")
    tiempo_total_formateado = StringProperty("00:00")
    ejercicios_del_dia = ListProperty([])
    indice_actual = NumericProperty(0)
    tiempo_restante = NumericProperty(0)
    ejercicio_actual = StringProperty("")
    pasos = ListProperty([])
    frase = StringProperty("")
    musculos = StringProperty("")
    contador_ejercicios = NumericProperty(0)
    cantidad_recomendada = StringProperty("")
    cronometro_total = NumericProperty(5400)
    alarma_activa = None
    cronometro_iniciado = BooleanProperty(False)
    ejercicio_terminado = BooleanProperty(False)

    def on_pre_enter(self):
        self.cargar_rutina_del_dia()
        self.cronometro_total = 90 * 60
        minutos, segundos = divmod(self.cronometro_total, 60)
        self.tiempo_total_formateado = f"{minutos:02d}:{segundos:02d}"
        self.ejercicio_terminado = False

    def cargar_rutina_del_dia(self):
        dias_traducidos = {
            "monday": "Lunes",
            "tuesday": "Martes",
            "wednesday": "Miércoles",
            "thursday": "Jueves",
            "friday": "Viernes",
            "saturday": "Sábado",
            "sunday": "Domingo"
        }
        dia_actual_en = datetime.datetime.now().strftime("%A").strip().lower()
        dia_actual = dias_traducidos.get(dia_actual_en, "Lunes")
        print("📆 Día detectado:", dia_actual)

        try:
            with open("rutina_diaria.json", encoding="utf-8") as f:
                data = json.load(f)
                self.ejercicios_del_dia = [
                    ej for ej in data if ej["Día"].strip().lower() == dia_actual.lower()
                ]
                print("📋 Ejercicios encontrados:", len(self.ejercicios_del_dia))
                
            if not self.ejercicios_del_dia:
                print("⚠️ No se encontraron ejercicios para hoy")
                
            self.indice_actual = 0
            self.contador_ejercicios = 0
            self.mostrar_ejercicio()
        except Exception as e:
            print(f"Error al cargar rutina: {e}")
            self.ejercicio_actual = "Error al cargar la rutina"
            self.frase = "Verifica el archivo rutina_diaria.json"

    def mostrar_ejercicio(self):
        # Reiniciar estado del ejercicio
        self.ejercicio_terminado = False
        self.cronometro_iniciado = False
        self.mostrar_boton_alarma = False
        
        if self.indice_actual >= len(self.ejercicios_del_dia):
            self.ejercicio_actual = "¡Rutina completada!"
            self.pasos = []
            self.frase = "Hoy diste un paso más hacia tu mejor versión 💪"
            self.musculos = ""
            self.cantidad_recomendada = ""
            self.tiempo_formateado = "00:00"
            return

        ejercicio = self.ejercicios_del_dia[self.indice_actual]
        self.ejercicio_actual = ejercicio["Ejercicio"]
        self.frase = ejercicio.get("Frase inspiracional", "¡Tú puedes!")
        self.cantidad_recomendada = ejercicio.get("Cantidad recomendada", "")
        
        try:
            tiempo_str = ejercicio.get("Tiempo estimado", "0 min")
            tiempo = int(tiempo_str.split()[0])
            self.tiempo_restante = tiempo * 60
            minutos, segundos = divmod(self.tiempo_restante, 60)
            self.tiempo_formateado = f"{minutos:02d}:{segundos:02d}"
        except (ValueError, IndexError):
            print(f"Error al procesar tiempo para {self.ejercicio_actual}")
            self.tiempo_restante = 60
            self.tiempo_formateado = "01:00"
            
        self.pasos = []
        self.musculos = ""
        self.cargar_detalles_ejercicio()
        print(f"Mostrando ejercicio: {self.ejercicio_actual} (índice {self.indice_actual})")

    def cargar_detalles_ejercicio(self):
        try:
            if os.path.exists("ejercicios_crossfit_basico.json"):
                with open("ejercicios_crossfit_basico.json", encoding="utf-8") as f:
                    detalles = json.load(f)
                    ejercicio_encontrado = False
                    for d in detalles:
                        if d["Ejercicio"].strip().lower() == self.ejercicio_actual.strip().lower():
                            self.pasos = d.get("Pasos clave", [])
                            self.musculos = d.get("Músculos trabajados", "No especificado")
                            ejercicio_encontrado = True
                            break
                    
                    if not ejercicio_encontrado:
                        self.pasos = ["Ejercicio de movilidad, descanso o respiración guiada."]
                        self.musculos = "Todo el cuerpo / Relajación"
            else:
                print("⚠️ Archivo de ejercicios no encontrado")
                self.pasos = ["Archivo de ejercicios no encontrado."]
                self.musculos = "Desconocido"
        except Exception as e:
            print(f"Error al cargar detalles del ejercicio: {e}")
            self.pasos = ["No se pudo cargar la información del ejercicio."]
            self.musculos = "Desconocido"

    def iniciar_cronometro(self):
        # Si el ejercicio ya se completó, avanzar al siguiente en lugar de reiniciar
        if self.ejercicio_terminado:
            self.avanzar_siguiente_ejercicio()
            return
            
        # Evitar iniciar múltiples cronómetros
        if self.cronometro_iniciado:
            return
            
        self.detener_todos_los_timers()
        self.cronometro_iniciado = True
        self.mostrar_boton_alarma = False
        
        # Detener cualquier alarma activa
        self.detener_alarma()
        
        # Iniciar los cronómetros
        Clock.schedule_interval(self.actualizar_visual_tiempo, 1)
        Clock.schedule_interval(self.reducir_tiempo, 1)
        Clock.schedule_interval(self.reducir_tiempo_total, 1)
        print(f"Cronómetro iniciado para: {self.ejercicio_actual}")

    def actualizar_visual_tiempo(self, dt):
        if self.tiempo_restante > 0:
            minutos, segundos = divmod(self.tiempo_restante, 60)
            self.tiempo_formateado = f"{minutos:02d}:{segundos:02d}"
        else:
            self.tiempo_formateado = "00:00"
            Clock.unschedule(self.actualizar_visual_tiempo)

    def reducir_tiempo(self, dt):
        if self.tiempo_restante > 0:
            self.tiempo_restante -= 1
            minutos, segundos = divmod(self.tiempo_restante, 60)
            self.tiempo_formateado = f"{minutos:02d}:{segundos:02d}"

            # Alerta en caminata a los 23 minutos
            if self.ejercicio_actual.lower() == "caminata" and self.tiempo_restante == 1380:
                self.sonar_bosque()
                print("🔔 Alerta a mitad de caminata (23 minutos)")
        else:
            # Fin del ejercicio
            print(f"⏱️ Tiempo terminado para: {self.ejercicio_actual}")
            self.ejercicio_terminado = True
            self.cronometro_iniciado = False
            Clock.unschedule(self.reducir_tiempo)
            Clock.unschedule(self.actualizar_visual_tiempo)
            self.sonar_bosque()

    def reducir_tiempo_total(self, dt):
        if self.cronometro_total > 0:
            self.cronometro_total -= 1
            minutos, segundos = divmod(self.cronometro_total, 60)
            self.tiempo_total_formateado = f"{minutos:02d}:{segundos:02d}"
        else:
            Clock.unschedule(self.reducir_tiempo_total)
            if not self.alarma_activa:
                self.sonar_bosque()
                self.mostrar_boton_alarma = True

    def avanzar_siguiente_ejercicio(self):
        self.detener_todos_los_timers()
        self.detener_alarma()
        self.indice_actual += 1
        self.contador_ejercicios += 1
        self.mostrar_ejercicio()
        print(f"Avanzando al siguiente ejercicio: índice {self.indice_actual}")

    def siguiente(self):
        # Esta función se llama desde la interfaz
        self.detener_todos_los_timers()
        self.detener_alarma()
        self.avanzar_siguiente_ejercicio()

    def detener_todos_los_timers(self):
        Clock.unschedule(self.reducir_tiempo)
        Clock.unschedule(self.reducir_tiempo_total)
        Clock.unschedule(self.actualizar_visual_tiempo)
        print("⏹️ Todos los timers detenidos")

    def sonar_bosque(self):
        # Evitar sonar si ya hay una alarma activa
        if self.alarma_activa:
            return
            
        try:
            self.alarma_activa = SoundLoader.load("bosque.wav")
            if self.alarma_activa:
                self.alarma_activa.loop = True
                self.alarma_activa.play()
                self.mostrar_boton_alarma = True
                print("🔊 Alarma sonando")
                
                # Vibrar dispositivo si está disponible
                try:
                    vibrator.vibrate(2)  # 2 segundos de vibración
                except:
                    pass
            else:
                print("⚠️ No se pudo cargar el archivo de sonido")
        except Exception as e:
            print(f"Error al reproducir sonido: {e}")

    def detener_alarma(self):
        if self.alarma_activa:
            try:
                self.alarma_activa.stop()
                print("🔇 Alarma detenida")
            except Exception as e:
                print(f"Error al detener alarma: {e}")
            self.alarma_activa = None
        self.mostrar_boton_alarma = False
        
        # Si el ejercicio ha terminado, avanzar al siguiente automáticamente
        if self.ejercicio_terminado:
            Clock.schedule_once(lambda dt: self.avanzar_siguiente_ejercicio(), 0.5)

    def comenzar_rutina(self):
        self.iniciar_cronometro()

class Registro(Screen):
    agua = NumericProperty(0)
    sueno = NumericProperty(0)
    fecha_actual = StringProperty("")
    peso = NumericProperty(70)
    presion_sistolica = NumericProperty(120)
    presion_diastolica = NumericProperty(80)
    
    # Nuevas propiedades
    frutas_verduras = NumericProperty(0)
    pasos_diarios = NumericProperty(0)
    meditacion = NumericProperty(0)
    animo = NumericProperty(5)
    estres = NumericProperty(5)
    
    def on_enter(self):
        # Obtener fecha actual
        fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
        
        # Si la fecha ha cambiado, reiniciar los contadores diarios
        if self.fecha_actual != fecha_hoy:
            self.reiniciar_contadores_diarios()
            
        self.fecha_actual = fecha_hoy
        self.cargar_ultimo_registro()
        print(f"Sueno actual: {self.sueno}")
    
    def reiniciar_contadores_diarios(self):
        print("Reiniciando contadores diarios")
        self.agua = 0
        self.sueno = 0
        self.frutas_verduras = 0
        self.pasos_diarios = 0
        self.meditacion = 0
        # No reiniciamos el peso ni la presión arterial
    
    def cargar_ultimo_registro(self):
        try:
            if os.path.exists(os.path.join(RUTA_DATOS, "ultimo_registro.json")):
                with open(os.path.join(RUTA_DATOS, "ultimo_registro.json"), "r") as f:
                    datos = json.load(f)
                    
                    # Verificar si el registro es de hoy
                    if datos.get("fecha", "") == self.fecha_actual:
                        self.agua = datos.get("agua", 0)
                        self.sueno = datos.get("sueno", 0)
                        self.frutas_verduras = datos.get("frutas_verduras", 0)
                        self.pasos_diarios = datos.get("pasos_diarios", 0)
                        self.meditacion = datos.get("meditacion", 0)
                    
                    # Estos valores se mantienen independientemente de la fecha
                    self.peso = datos.get("peso", 70)
                    self.presion_sistolica = datos.get("presion_sistolica", 120)
                    self.presion_diastolica = datos.get("presion_diastolica", 80)
                    self.animo = datos.get("animo", 5)
                    self.estres = datos.get("estres", 5)
        except Exception as e:
            print(f"Error al cargar último registro: {e}")
    
    def agregar_agua(self):
        self.agua += 1
        self.guardar_registro()

    def reducir_agua(self):
        if self.agua > 0:
            self.agua -= 1
            self.guardar_registro()

    def agregar_sueno(self):
        print("Agregando 0.5 horas de sueno")
        self.sueno += 0.5
        self.guardar_registro()
        print(f"Nuevo valor de sueno: {self.sueno}")

    def reducir_sueno(self):
        if self.sueno >= 0.5:
            self.sueno -= 0.5
            self.guardar_registro()
            
    def actualizar_peso(self, valor):
        try:
            if isinstance(valor, str):
                valor = float(valor)
            self.peso = valor
            self.guardar_registro()
        except:
            pass
            
    def actualizar_presion(self, sistolica, diastolica):
        try:
            self.presion_sistolica = int(sistolica)
            self.presion_diastolica = int(diastolica)
            self.guardar_registro()
        except:
            pass
    
    # Nuevos métodos para otras métricas
    def agregar_frutas_verduras(self):
        self.frutas_verduras += 1
        self.guardar_registro()
        
    def reducir_frutas_verduras(self):
        if self.frutas_verduras > 0:
            self.frutas_verduras -= 1
            self.guardar_registro()
            
    def agregar_pasos(self, valor):
        try:
            self.pasos_diarios = int(valor)
            self.guardar_registro()
        except:
            pass
            
    def agregar_meditacion(self, valor):
        try:
            self.meditacion = int(valor)
            self.guardar_registro()
        except:
            pass
            
    def actualizar_animo(self, valor):
        try:
            self.animo = int(valor)
            self.guardar_registro()
        except:
            pass
    
    def guardar_registro(self):
        try:
            datos = {
                "fecha": self.fecha_actual,
                "agua": self.agua,
                "sueno": self.sueno,
                "peso": self.peso,
                "presion_sistolica": self.presion_sistolica,
                "presion_diastolica": self.presion_diastolica,
                "frutas_verduras": self.frutas_verduras,
                "pasos_diarios": self.pasos_diarios,
                "meditacion": self.meditacion,
                "animo": self.animo,
                "estres": self.estres
            }
            
            # Guardar último registro
            with open(os.path.join(RUTA_DATOS, "ultimo_registro.json"), "w") as f:
                json.dump(datos, f)
                
            # Guardar en historial diario
            fecha_archivo = datetime.datetime.now().strftime("%Y%m%d")
            ruta_historial = os.path.join(RUTA_DATOS, f"historial_{fecha_archivo}.json")
            
            historial = []
            if os.path.exists(ruta_historial):
                try:
                    with open(ruta_historial, "r") as f:
                        historial = json.load(f)
                except:
                    historial = []
            
            # Buscar si ya existe un registro de hoy
            registro_actualizado = False
            for i, reg in enumerate(historial):
                if reg.get("fecha") == self.fecha_actual:
                    historial[i] = datos
                    registro_actualizado = True
                    break
                    
            if not registro_actualizado:
                historial.append(datos)
            
            with open(ruta_historial, "w") as f:
                json.dump(historial, f)
                
            print(f"Registro guardado: {self.fecha_actual}")
        except Exception as e:
            print(f"Error al guardar registro: {e}")
    
    def mostrar_historial(self):
        self.manager.get_screen('historial').cargar_datos()
        self.manager.current = 'historial'
        
    def volver_menu(self):
        self.manager.current = 'bienvenida'

class MonitoreoRuta(Screen):
    tiempo_caminata = NumericProperty(0)
    distancia_total = NumericProperty(0)  # En metros
    velocidad_actual = NumericProperty(0)  # En km/h
    calorias_quemadas = NumericProperty(0)
    pasos_contados = NumericProperty(0)
    grabando_ruta = BooleanProperty(False)
    
    # Variables para el mapa
    mapview = ObjectProperty(None)
    route_layer = ObjectProperty(None)
    ultima_lat = NumericProperty(0)
    ultima_lon = NumericProperty(0)
    puntos_ruta = ListProperty([])
    
    # Datos de la sesión
    datos_sesion = {}
    
    def __init__(self, **kwargs):
        super(MonitoreoRuta, self).__init__(**kwargs)
        self.weight_kg = 70  # Peso por defecto para cálculo de calorías
        self.marcador_actual = None
        
    def on_enter(self):
        # Configurar mapa si no existe
        if not self.mapview:
            try:
                self.mapview = MapView(zoom=15, lat=0, lon=0)
                self.route_layer = RouteMapLayer()
                self.mapview.add_layer(self.route_layer)
                self.ids.mapa_container.add_widget(self.mapview)
            except Exception as e:
                print(f"Error al inicializar mapa: {e}")
        
        # Intentar cargar el peso del usuario si está guardado
        try:
            if os.path.exists(os.path.join(RUTA_DATOS, "ultimo_registro.json")):
                with open(os.path.join(RUTA_DATOS, "ultimo_registro.json"), "r") as f:
                    data = json.load(f)
                    self.weight_kg = data.get("peso", 70)
        except Exception as e:
            print(f"Error al cargar datos de usuario: {e}")
    
    def iniciar_monitoreo(self):
        if self.grabando_ruta:
            return
            
        self.grabando_ruta = True
        self.tiempo_caminata = 0
        self.distancia_total = 0
        self.velocidad_actual = 0
        self.calorias_quemadas = 0
        self.pasos_contados = 0
        self.puntos_ruta = []
        
        # Limpiar mapa
        if self.route_layer:
            self.route_layer.clear_points()
        
        # Iniciar GPS
        try:
            gps.configure(on_location=self.actualizar_ubicacion)
            gps.start(minTime=1000, minDistance=1)
        except Exception as e:
            print(f"Error al iniciar GPS: {e}")
            self.mostrar_mensaje("Error", "No se pudo iniciar el GPS. Verifica los permisos.")
        
        # Iniciar acelerómetro para contar pasos
        try:
            accelerometer.enable()
        except Exception as e:
            print(f"Error al iniciar acelerómetro: {e}")
        
        # Iniciar cronómetros
        Clock.schedule_interval(self.actualizar_tiempo, 1)
        Clock.schedule_interval(self.actualizar_pasos, 0.5)
        
        # Registrar hora de inicio
        self.hora_inicio = datetime.datetime.now()
        
        # Inicializar datos de sesión
        self.datos_sesion = {
            "fecha": self.hora_inicio.strftime("%Y-%m-%d %H:%M:%S"),
            "duracion_segundos": 0,
            "distancia_metros": 0,
            "pasos": 0,
            "calorias": 0,
            "ruta": []
        }
        
        try:
            notification.notify(
                title='Monitoreo iniciado',
                message='Se está registrando tu actividad física',
                app_name='Gestor de Ejercicios'
            )
        except:
            pass
    
    def detener_monitoreo(self):
        if not self.grabando_ruta:
            return
            
        self.grabando_ruta = False
        
        # Detener GPS
        try:
            gps.stop()
        except:
            pass
        
        # Detener acelerómetro
        try:
            accelerometer.disable()
        except:
            pass
        
        # Detener cronómetros
        Clock.unschedule(self.actualizar_tiempo)
        Clock.unschedule(self.actualizar_pasos)
        
        # Guardar datos de la sesión
        self.datos_sesion["duracion_segundos"] = self.tiempo_caminata
        self.datos_sesion["distancia_metros"] = self.distancia_total
        self.datos_sesion["pasos"] = self.pasos_contados
        self.datos_sesion["calorias"] = self.calorias_quemadas
        
        # Guardar en historial
        self.guardar_sesion()
        
        # Mostrar resumen
        self.mostrar_resumen()
        
        try:
            notification.notify(
                title='Monitoreo finalizado',
                message=f'Has caminado {self.distancia_total/1000:.2f} km en {self.formato_tiempo(self.tiempo_caminata)}',
                app_name='Gestor de Ejercicios'
            )
        except:
            pass
    
    def actualizar_tiempo(self, dt):
        self.tiempo_caminata += 1
        # Actualizar calorías quemadas cada segundo
        # Fórmula simplificada: METs * peso en kg * tiempo en horas
        # METs para caminata: ~3.5
        mets = 3.5
        horas = self.tiempo_caminata / 3600
        self.calorias_quemadas = mets * self.weight_kg * horas * 1.05
    
    def actualizar_pasos(self, dt):
        if not self.grabando_ruta:
            return
            
        try:
            datos = accelerometer.acceleration
            if datos:
                # Algoritmo simplificado para detectar pasos basado en cambios en la aceleración
                magnitud = (datos[0]**2 + datos[1]**2 + datos[2]**2)**0.5
                if not hasattr(self, 'ultimo_pico'):
                    self.ultimo_pico = False
                    self.umbral_pico = 10.5  # Ajustar según pruebas
                
                if magnitud > self.umbral_pico and not self.ultimo_pico:
                    self.pasos_contados += 1
                    self.ultimo_pico = True
                elif magnitud < self.umbral_pico:
                    self.ultimo_pico = False
        except Exception as e:
            print(f"Error al leer acelerómetro: {e}")
    
    def actualizar_ubicacion(self, **kwargs):
        lat = kwargs.get('lat', 0)
        lon = kwargs.get('lon', 0)
        
        if lat == 0 and lon == 0:
            return
        
        # Si es el primer punto, centrar mapa
        if len(self.puntos_ruta) == 0:
            self.mapview.center_on(lat, lon)
        
        # Calcular distancia desde el último punto
        if self.ultima_lat != 0 and self.ultima_lon != 0:
            distancia = self.calcular_distancia(self.ultima_lat, self.ultima_lon, lat, lon)
            self.distancia_total += distancia
            
            # Calcular velocidad actual (km/h)
            if distancia > 0:
                self.velocidad_actual = (distancia / 1000) / (1 / 3600)  # m/s a km/h
        
        # Actualizar posición
        self.ultima_lat = lat
        self.ultima_lon = lon
        
        # Guardar punto en la ruta
        self.puntos_ruta.append((lat, lon))
        self.datos_sesion["ruta"].append({
            "lat": lat,
            "lon": lon,
            "tiempo": self.tiempo_caminata,
            "velocidad": self.velocidad_actual
        })
        
        # Actualizar ruta en el mapa
        self.route_layer.add_point(lat, lon)
        
        # Actualizar marcador de posición actual
        if hasattr(self, 'marcador_actual') and self.marcador_actual:
            self.mapview.remove_marker(self.marcador_actual)
        self.marcador_actual = MapMarker(lat=lat, lon=lon)
        self.mapview.add_marker(self.marcador_actual)
    
    def calcular_distancia(self, lat1, lon1, lat2, lon2):
        # Fórmula de Haversine para calcular distancia entre coordenadas
        R = 6371000  # Radio de la Tierra en metros
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2) * math.sin(delta_phi/2) + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda/2) * math.sin(delta_lambda/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c  # Distancia en metros
    
    def formato_tiempo(self, segundos):
        horas = segundos // 3600
        minutos = (segundos % 3600) // 60
        segs = segundos % 60
        return f"{horas:02d}:{minutos:02d}:{segs:02d}"
    
    def guardar_sesion(self):
        fecha_archivo = self.hora_inicio.strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"sesion_{fecha_archivo}.json"
        ruta_completa = os.path.join(RUTA_DATOS, nombre_archivo)
        
        try:
            with open(ruta_completa, "w") as f:
                json.dump(self.datos_sesion, f)
            print(f"Sesión guardada en {ruta_completa}")
            
            # Guardar captura del mapa
            self.guardar_captura_mapa(fecha_archivo)
            
            # Limpiar sesiones antiguas (más de 30 días)
            self.limpiar_sesiones_antiguas()
        except Exception as e:
            print(f"Error al guardar sesión: {e}")
            self.mostrar_mensaje("Error", "No se pudo guardar la sesión correctamente.")
    
    def guardar_captura_mapa(self, fecha_archivo):
        # Implementación simplificada - en un caso real se podría usar una API de mapas
        try:
            if len(self.puntos_ruta) < 2:
                return
                
            # Crear un archivo de texto con las coordenadas como alternativa
            ruta_txt = os.path.join(RUTA_MAPAS, f"ruta_{fecha_archivo}.txt")
            with open(ruta_txt, 'w') as f:
                for lat, lon in self.puntos_ruta:
                    f.write(f"{lat},{lon}\n")
            print(f"Ruta guardada como texto en {ruta_txt}")
            
        except Exception as e:
            print(f"Error al guardar captura de mapa: {e}")
    
    def limpiar_sesiones_antiguas(self):
        try:
            fecha_limite = datetime.datetime.now() - datetime.timedelta(days=MAX_DIAS_HISTORIAL)
            for root, dirs, files in os.walk(RUTA_DATOS):
                for file in files:
                    if file.startswith("sesion_"):
                        try:
                            fecha_str = file[7:15]  # Formato YYYYMMDD
                            fecha_archivo = datetime.datetime.strptime(fecha_str, "%Y%m%d")
                            
                            if fecha_archivo < fecha_limite:
                                os.remove(os.path.join(root, file))
                                print(f"Archivo antiguo eliminado: {file}")
                        except:
                            pass
        except Exception as e:
            print(f"Error al limpiar sesiones antiguas: {e}")
    
    def mostrar_resumen(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        titulo = Label(text="Resumen de Actividad", font_size=20, size_hint_y=None, height=dp(40))
        layout.add_widget(titulo)
        
        stats = [
            f"Duración: {self.formato_tiempo(self.tiempo_caminata)}",
            f"Distancia: {self.distancia_total/1000:.2f} km",
            f"Pasos: {self.pasos_contados}",
            f"Calorías: {int(self.calorias_quemadas)} kcal",
            f"Velocidad media: {(self.distancia_total/1000)/(max(self.tiempo_caminata, 1)/3600):.2f} km/h"
        ]
        
        for stat in stats:
            layout.add_widget(Label(text=stat, size_hint_y=None, height=dp(30)))
        
        botones = BoxLayout(size_hint_y=None, height=dp(50), spacing=10)
        
        btn_cerrar = Button(text="Cerrar")
        btn_compartir = Button(text="Compartir en Facebook")
        
        botones.add_widget(btn_cerrar)
        botones.add_widget(btn_compartir)
        
        layout.add_widget(botones)
        
        popup = Popup(title="Actividad Completada", 
                     content=layout,
                     size_hint=(0.9, 0.7))
        
        btn_cerrar.bind(on_release=popup.dismiss)
        btn_compartir.bind(on_release=lambda x: self.compartir_facebook())
        
        popup.open()
    
    def compartir_facebook(self):
        try:
            # Formato de mensaje para Facebook
            mensaje = f"¡He completado una actividad física! Caminé {self.distancia_total/1000:.2f} km en {self.formato_tiempo(self.tiempo_caminata)} y quemé {int(self.calorias_quemadas)} calorías. #FitnessGoals #HealthyLife"
            
            # URL encode del mensaje
            import urllib.parse
            mensaje_codificado = urllib.parse.quote(mensaje)
            
            # Abrir navegador con URL de compartir en Facebook
            url = f"https://www.facebook.com/sharer/sharer.php?u=https://example.com&quote={mensaje_codificado}"
            webbrowser.open(url)
        except Exception as e:
            print(f"Error al compartir en Facebook: {e}")
            self.mostrar_mensaje("Error", "No se pudo compartir en Facebook")
    
    def mostrar_mensaje(self, titulo, mensaje):
        content = BoxLayout(orientation='vertical', padding=10)
        content.add_widget(Label(text=mensaje))
        btn = Button(text="OK", size_hint=(1, 0.3))
        content.add_widget(btn)
        popup = Popup(title=titulo, content=content, size_hint=(0.7, 0.3))
        btn.bind(on_release=popup.dismiss)
        popup.open()


class Historial(Screen):
    historial_datos = ListProperty([])
    
    def on_enter(self):
        print("Entrando a pantalla de Historial")
        self.cargar_datos()
    
    def cargar_datos(self):
        self.historial_datos = []
        try:
            # Limpiar cualquier contenido anterior
            if 'historial_container' in self.ids:
                self.ids.historial_container.clear_widgets()
            
            # Buscar archivos de historial
            for root, dirs, files in os.walk(RUTA_DATOS):
                for file in files:
                    if file.startswith("historial_") and file.endswith(".json"):
                        try:
                            with open(os.path.join(root, file), "r") as f:
                                registros = json.load(f)
                                for registro in registros:
                                    self.historial_datos.append(registro)
                        except Exception as e:
                            print(f"Error al cargar archivo {file}: {e}")
            
            # Ordenar por fecha, más reciente primero
            self.historial_datos.sort(key=lambda x: x.get("fecha", ""), reverse=True)
            
            # Limitar a últimos 30 días
            self.historial_datos = self.historial_datos[:30]
            
            print(f"Historial cargado: {len(self.historial_datos)} registros")
            
            # Mostrar los registros en la interfaz
            if 'historial_container' in self.ids:
                if not self.historial_datos:
                    self.ids.historial_container.add_widget(
                        Label(text="No hay registros disponibles", 
                              size_hint_y=None, height=50,
                              color=(0.7, 0.7, 0.7, 1))
                    )
                else:
                    for registro in self.historial_datos:
                        fecha = registro.get("fecha", "")
                        agua = registro.get("agua", 0)
                        sueno = registro.get("sueno", 0)
                        
                        # Crear widget de registro
                        box = BoxLayout(orientation='vertical', 
                                        size_hint_y=None, 
                                        height=100,
                                        padding=10,
                                        spacing=5)
                        
                        box.add_widget(Label(text=f"Fecha: {fecha}", 
                                            color=(0, 1, 0.6, 1),
                                            font_size=18,
                                            bold=True,
                                            size_hint_y=None, height=30))
                        
                        info = f"Agua: {agua} vasos | Sueno: {sueno} hrs"
                        if "peso" in registro:
                            info += f" | Peso: {registro['peso']} kg"
                        
                        box.add_widget(Label(text=info,
                                            color=(1, 1, 1, 1),
                                            size_hint_y=None, height=30))
                        
                        self.ids.historial_container.add_widget(box)
            else:
                print("Error: no se encuentra el contenedor de historial en la interfaz")
                
        except Exception as e:
            print(f"Error general al cargar historial: {e}")
    
    def volver_menu(self):
        self.manager.current = 'bienvenida'


class GestorApp(App):
    def build(self):
        self.verificar_archivos()
        
        # Cargar archivo KV
        try:
            Builder.load_file("gestor1.kv")
        except Exception as e:
            print(f"Error al cargar archivo KV: {e}")
            self.crear_archivo_kv()
            Builder.load_file("gestor1.kv")
        
        # Crear administrador de pantallas
        sm = ScreenManager()
        sm.add_widget(Bienvenida(name='bienvenida'))
        sm.add_widget(Rutina(name='rutina'))
        sm.add_widget(Registro(name='registro'))
        sm.add_widget(MonitoreoRuta(name='monitoreo'))
        sm.add_widget(Historial(name='historial'))
        
        return sm
        
    def verificar_archivos(self):
        # Verificar existencia de archivos necesarios
        archivos_requeridos = [
            "frases.json", 
            "rutina_diaria.json", 
            "ejercicios_crossfit_basico.json",
            "bosque.wav"
        ]
        
        for archivo in archivos_requeridos:
            if not os.path.exists(archivo):
                print(f"⚠️ Archivo requerido no encontrado: {archivo}")
                if archivo.endswith('.json'):
                    self.crear_archivo_json_ejemplo(archivo)
                elif archivo == "bosque.wav":
                    print("⚠️ Archivo de sonido bosque.wav no encontrado. Necesitarás proporcionar tu propio archivo de sonido.")

    def crear_archivo_json_ejemplo(self, nombre_archivo):
        datos_ejemplo = {
            "frases.json": [
                "¡Hoy será un gran día para sudar con amor!",
                "El mejor momento para empezar es ahora",
                "Pequeños pasos, grandes cambios"
            ],
            "rutina_diaria.json": [
                {
                    "Día": "Lunes",
                    "Ejercicio": "Sentadillas",
                    "Tiempo estimado": "2 min",
                    "Frase inspiracional": "¡Activa esas piernas!",
                    "Cantidad recomendada": "15 repeticiones"
                },
                {
                    "Día": "Lunes",
                    "Ejercicio": "Caminata",
                    "Tiempo estimado": "30 min",
                    "Frase inspiracional": "¡A disfrutar del aire libre!"
                }
            ],
            "ejercicios_crossfit_basico.json": [
                {
                    "Ejercicio": "Sentadillas",
                    "Pasos clave": [
                        "Pies a la anchura de los hombros",
                        "Espalda recta",
                        "Flexiona rodillas como si te sentaras"
                    ],
                    "Músculos trabajados": "Cuádriceps, glúteos, isquiotibiales"
                },
                {
                    "Ejercicio": "Caminata",
                    "Pasos clave": [
                        "Mantén un ritmo constante",
                        "Respira profundamente",
                        "Disfruta del entorno"
                    ],
                    "Músculos trabajados": "Piernas, sistema cardiovascular"
                }
            ]
        }
        
        try:
            with open(nombre_archivo, 'w', encoding='utf-8') as f:
                json.dump(datos_ejemplo.get(nombre_archivo, []), f, ensure_ascii=False, indent=2)
            print(f"✅ Archivo de ejemplo creado: {nombre_archivo}")
        except Exception as e:
            print(f"❌ Error al crear archivo de ejemplo {nombre_archivo}: {e}")
    
    def crear_archivo_kv(self):
        contenido_kv = """
#:kivy 2.0.0

<Bienvenida>:
    BoxLayout:
        orientation: 'vertical'
        padding: 20
        spacing: 10
        
        Label:
            text: 'Bienvenido a tu App de Ejercicios'
            font_size: 24
            size_hint_y: 0.2
        
        Label:
            text: root.frase_dia
            font_size: 18
            text_size: self.width, None
            halign: 'center'
            valign: 'middle'
            size_hint_y: 0.3
        
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: 0.5
            spacing: 20
            
            Button:
                text: 'Comenzar Rutina'
                font_size: 20
                on_release: app.root.current = 'rutina'
            
            Button:
                text: 'Monitorear Actividad'
                font_size: 20
                on_release: app.root.current = 'monitoreo'
            
            Button:
                text: 'Registro de Salud'
                font_size: 20
                on_release: app.root.current = 'registro'
            
            Button:
                text: 'Ver Historial'
                font_size: 20
                on_release: app.root.current = 'historial'

<Rutina>:
    BoxLayout:
        orientation: 'vertical'
        padding: 15
        spacing: 10
        
        BoxLayout:
            size_hint_y: 0.1
            
            Button:
                text: 'Volver'
                size_hint_x: 0.3
                on_release: app.root.current = 'bienvenida'
            
            Label:
                text: 'Rutina Diaria'
                font_size: 22
        
        Label:
            text: root.ejercicio_actual
            font_size: 26
            size_hint_y: 0.15
        
        Label:
            text: root.frase
            font_size: 16
            text_size: self.width, None
            halign: 'center'
            valign: 'middle'
            size_hint_y: 0.1
        
        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: 0.15
            
            Label:
                text: 'Tiempo:'
                size_hint_x: 0.3
            
            Label:
                text: root.tiempo_formateado
                font_size: 24
                size_hint_x: 0.4
            
            Label:
                text: 'Total: ' + root.tiempo_total_formateado
                size_hint_x: 0.3
        
        ScrollView:
            size_hint_y: 0.3
            
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: 10
                padding: 10
                
                Label:
                    text: 'Pasos:'
                    font_size: 18
                    size_hint_y: None
                    height: 30
                
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    
                    Label:
                        text: '\\n'.join(root.pasos)
                        text_size: self.width, None
                        size_hint_y: None
                        height: self.texture_size[1]
                
                Label:
                    text: 'Músculos trabajados: ' + root.musculos
                    text_size: self.width, None
                    size_hint_y: None
                    height: self.texture_size[1]
                    padding_y: 10
                
                Label:
                    text: 'Cantidad recomendada: ' + root.cantidad_recomendada
                    text_size: self.width, None
                    size_hint_y: None
                    height: self.texture_size[1]
                    padding_y: 10
        
        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: 0.2
            padding: 10
            spacing: 10
            
            Button:
                text: 'Iniciar'
                font_size: 18
                on_release: root.comenzar_rutina()
            
            Button:
                text: 'Detener Alarma'
                font_size: 18
                disabled: not root.mostrar_boton_alarma
                on_release: root.detener_alarma()
            
            Button:
                text: 'Siguiente'
                font_size: 18
                on_release: root.siguiente()

<Registro>:
    BoxLayout:
        orientation: 'vertical'
        padding: 15
        spacing: 10
        
        BoxLayout:
            size_hint_y: 0.1
            
            Button:
                text: 'Volver'
                size_hint_x: 0.3
                on_release: app.root.current = 'bienvenida'
            
            Label:
                text: 'Registro de Salud'
                font_size: 22
        
        Label:
            text: 'Fecha: ' + root.fecha_actual
            size_hint_y: 0.1
        
        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: 0.15
            
            Label:
                text: 'Peso (kg):'
                size_hint_x: 0.3
            
            TextInput:
                text: str(root.peso)
                input_filter: 'float'
                multiline: False
                size_hint_x: 0.4
                on_text_validate: root.actualizar_peso(self.text)
        
        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: 0.15
            
            Label:
                text: 'Presión arterial:'
                size_hint_x: 0.3
            
            TextInput:
                text: str(root.presion_sistolica)
                input_filter: 'int'
                multiline: False
                size_hint_x: 0.2
                on_text_validate: root.actualizar_presion(self.text, str(root.presion_diastolica))
            
            Label:
                text: '/'
                size_hint_x: 0.1
            
            TextInput:
                text: str(root.presion_diastolica)
                input_filter: 'int'
                multiline: False
                size_hint_x: 0.2
                on_text_validate: root.actualizar_presion(str(root.presion_sistolica), self.text)
        
        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: 0.15
            
            Label:
                text: 'Vasos de agua:'
                size_hint_x: 0.3
            
            Button:
                text: '-'
                size_hint_x: 0.15
                on_release: root.reducir_agua()
            
            Label:
                text: str(root.agua)
                size_hint_x: 0.1
            
            Button:
                text: '+'
                size_hint_x: 0.15
                on_release: root.agregar_agua()
        
        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: 0.15
            
            Label:
                text: 'Horas de sueno:'
                size_hint_x: 0.3
            
            Button:
                text: '-'
                size_hint_x: 0.15
                on_release: root.reducir_sueno()
            
            Label:
                text: str(root.sueno)
                size_hint_x: 0.1
            
            Button:
                text: '+'
                size_hint_x: 0.15
                on_release: root.agregar_sueno()
        
        Button:
            text: 'Ver Historial'
            size_hint_y: 0.1
            on_release: root.mostrar_historial()

<MonitoreoRuta>:
    BoxLayout:
        orientation: 'vertical'
        padding: 15
        spacing: 10
        
        BoxLayout:
            size_hint_y: 0.1
            
            Button:
                text: 'Volver'
                size_hint_x: 0.3
                on_release: app.root.current = 'bienvenida'
            
            Label:
                text: 'Monitoreo de Actividad'
                font_size: 22
        
        BoxLayout:
            id: mapa_container
            size_hint_y: 0.4
        
        GridLayout:
            cols: 2
            size_hint_y: 0.3
            padding: 10
            spacing: 5
            
            Label:
                text: 'Tiempo:'
                halign: 'right'
            
            Label:
                text: root.formato_tiempo(root.tiempo_caminata)
                font_size: 18
            
            Label:
                text: 'Distancia:'
                halign: 'right'
            
            Label:
                text: f"{root.distancia_total/1000:.2f} km"
                font_size: 18
            
            Label:
                text: 'Velocidad:'
                halign: 'right'
            
            Label:
                text: f"{root.velocidad_actual:.1f} km/h"
                font_size: 18
            
            Label:
                text: 'Pasos:'
                halign: 'right'
            
            Label:
                text: str(root.pasos_contados)
                font_size: 18
            
            Label:
                text: 'Calorías:'
                halign: 'right'
            
            Label:
                text: f"{int(root.calorias_quemadas)} kcal"
                font_size: 18
        
        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: 0.2
            padding: 10
            spacing: 10
            
            Button:
                text: 'Iniciar'
                font_size: 18
                disabled: root.grabando_ruta
                on_release: root.iniciar_monitoreo()
            
            Button:
                text: 'Detener'
                font_size: 18
                disabled: not root.grabando_ruta
                on_release: root.detener_monitoreo()
        
<Historial>:
    BoxLayout:
        orientation: 'vertical'
        padding: 15
        spacing: 10
        
        BoxLayout:
            size_hint_y: 0.1
            
            Button:
                text: 'Volver'
                size_hint_x: 0.3
                on_release: app.root.current = 'bienvenida'
            
            Label:
                text: 'Historial de Actividad'
                font_size: 22
        
        ScrollView:
            size_hint_y: 0.9
            
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: 10
                padding: 10
                
                Label:
                    text: 'Sin registros' if not root.historial_datos else ''
                    size_hint_y: None
                    height: 40 if not root.historial_datos else 0
                
                GridLayout:
                    cols: 1
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: 10
                    
                    # Este GridLayout se llenará programáticamente
        """
        
        try:
            with open("gestor1.kv", 'w') as f:
                f.write(contenido_kv)
            print("✅ Archivo KV creado correctamente")
        except Exception as e:
            print(f"❌ Error al crear archivo KV: {e}")


if __name__ == '__main__':
    try:
        # Verificar y crear directorios necesarios
        os.makedirs(RUTA_DATOS, exist_ok=True)
        os.makedirs(RUTA_MAPAS, exist_ok=True)
        
        # Ejecutar la aplicación
        GestorApp().run()
    except Exception as e:
        print(f"Error al iniciar la aplicación: {e}")

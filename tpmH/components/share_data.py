import zoneinfo

# Definimos INFINITY para uso en límites
INFINITY = float('inf')

days_of_week = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
duration_options = ['30 minutos', '1 hora']
availability_options = ['Ocupado', 'Libre']
pack_of_classes = ["Básico", "Personalizado", "Intensivo", "Flexible"]
goals_list = [
    "Mantener conversaciones básicas sobre temas cotidianos",
    "Mejorar la pronunciación y la fluidez al hablar",
    "Ampliar el vocabulario para situaciones reales",
    "Comprender mejor audios y vídeos en inglés",
    "Escribir mensajes y correos simples sin errores comunes",
    "Aprender y usar correctamente los tiempos verbales",
    "Entender textos cortos y noticias sencillas",
    "Prepararse para exámenes oficiales (A1, A2, B1, etc.)",
    "Ganar confianza al participar en conversaciones",
    "Poder viajar al extranjero usando solo inglés"
]
method_list = ["Paypal", "Binance", "Zelle"]

# Limite total de clases por paquete (Usado en el Registro/Signup)
PACKAGE_LIMITS = {
    "Básico": 4,
    "Personalizado": 8,
    "Intensivo": 12,
    "Flexible": INFINITY
}

# Límites para reglas del calendario (días a la semana)
max_days_per_plan = {
    "Básico": 1, 
    "Personalizado": 2, 
    "Intensivo": 3, 
    "Flexible": INFINITY
}

# Límites de clases por día (si aplica)
max_classes_per_plan = {
    "Básico": 1, 
    "Personalizado": 1, 
    "Intensivo": 3, 
    "Flexible": INFINITY
}

hours_of_day = [f'{h:02d}:{m:02d}' for h in range(24) for m in (0, 30)]

# Tablas globales
group_data = {h: {d: '' for d in days_of_week} for h in hours_of_day}
group_data1 = {h: {d: '' for d in days_of_week} for h in hours_of_day}
group_data2 = {h: {d: '' for d in days_of_week} for h in hours_of_day}
group_data3 = {}
group_data4 = {h: {d: "" for d in days_of_week} for h in hours_of_day}
group_data5 = {h: {d: "" for d in days_of_week} for h in hours_of_day}
group_data6 = {}



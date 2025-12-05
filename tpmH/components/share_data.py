# components/share_data.py

# Definimos INFINITY para uso en límites
INFINITY = float('inf')

# --- 1. LISTAS BÁSICAS (VALORES INTERNOS/ESPAÑOL) ---
days_of_week = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

duration_options = ['30 minutos', '1 hora']

availability_options = ['Ocupado', 'Libre']

pack_of_classes = ["Básico", "Personalizado", "Intensivo", "Flexible"]

# Generador de horas (00:00 a 23:30)
hours_of_day = [f'{h:02d}:{m:02d}' for h in range(24) for m in (0, 30)]

# --- 2. LÓGICA DE NEGOCIO (LÍMITES) ---

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

# --- 3. DICCIONARIO MAESTRO DE TRADUCCIONES (Para Selectores y Tablas) ---
VALUE_TRANSLATIONS = {
    # Días de la semana
    'Lunes': {'es': 'Lunes', 'en': 'Monday'},
    'Martes': {'es': 'Martes', 'en': 'Tuesday'},
    'Miércoles': {'es': 'Miércoles', 'en': 'Wednesday'},
    'Jueves': {'es': 'Jueves', 'en': 'Thursday'},
    'Viernes': {'es': 'Viernes', 'en': 'Friday'},
    'Sábado': {'es': 'Sábado', 'en': 'Saturday'},
    'Domingo': {'es': 'Domingo', 'en': 'Sunday'},

    # Duraciones
    '30 minutos': {'es': '30 minutos', 'en': '30 minutes'},
    '1 hora': {'es': '1 hora', 'en': '1 hour'},

    # Disponibilidad
    'Ocupado': {'es': 'Ocupado', 'en': 'Busy'},
    'Libre': {'es': 'Libre', 'en': 'Free'},

    # Paquetes
    'Básico': {'es': 'Básico', 'en': 'Basic'},
    'Personalizado': {'es': 'Personalizado', 'en': 'Custom'},
    'Intensivo': {'es': 'Intensivo', 'en': 'Intensive'},
    'Flexible': {'es': 'Flexible', 'en': 'Flexible'},
}

# --- 4. HELPER DE TRADUCCIÓN ---
def t_val(value, lang):
    """
    Traduce un valor de base de datos (interno) al idioma actual.
    Si no encuentra el valor en el diccionario, devuelve el original.
    """
    # Convertimos a string por seguridad si viene None
    if not value:
        return ""
    
    val_str = str(value)
    
    if val_str in VALUE_TRANSLATIONS:
        return VALUE_TRANSLATIONS[val_str].get(lang, val_str)
    
    return val_str

# Tablas globales
group_data = {h: {d: '' for d in days_of_week} for h in hours_of_day}
group_data1 = {h: {d: '' for d in days_of_week} for h in hours_of_day}
group_data2 = {h: {d: '' for d in days_of_week} for h in hours_of_day}
group_data3 = {}
group_data4 = {h: {d: "" for d in days_of_week} for h in hours_of_day}
group_data5 = {h: {d: "" for d in days_of_week} for h in hours_of_day}
group_data6 = {}



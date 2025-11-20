from components.header import create_main_screen
from components.share_data import *
from components.clear_table import clear_table
from datetime import datetime
from nicegui import ui

def make_add_hours_by_date_button(
        button,
        *,
        start_time_input,
        end_time_input,   # Ahora es obligatorio para el cálculo
        availability,
        date_input,
        group_data,
        table,
        button_id=None,
        notify_no_package="Selecciona un paquete primero",
        notify_no_start="Selecciona la hora de inicio",
        notify_no_end="Selecciona la hora de fin",
        notify_no_date="Selecciona una fecha",
        notify_bad_format="Formato de hora incorrecto HH:MM",
        notify_success="Horas agregadas"
    ):

    dias_es = {
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
        "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
    }

    def add_hours_action():

        # -------------------------
        # 1. Validaciones
        # -------------------------
        if not availability.value:
            ui.notify(notify_no_package, color='warning')
            return

        if not start_time_input.value:
            ui.notify(notify_no_start, color='warning')
            return
        
        if not end_time_input.value:
            ui.notify(notify_no_end, color='warning')
            return

        if not date_input.value:
            ui.notify(notify_no_date, color='warning')
            return

        # -------------------------
        # 2. Parsear y Validar formato de Hora Inicio
        # -------------------------
        try:
            h_start, m_start = map(int, start_time_input.value.split(":"))
            hora_inicio_fmt = f"{h_start:02d}:{m_start:02d}"
        except:
            ui.notify(notify_bad_format + " (Inicio)", color="warning")
            return

        # -------------------------
        # 3. Parsear y Validar formato de Hora Fin
        # -------------------------
        try:
            h_end, m_end = map(int, end_time_input.value.split(":"))
            hora_fin_fmt = f"{h_end:02d}:{m_end:02d}"
        except:
            ui.notify(notify_bad_format + " (Fin)", color="warning")
            return

        # Opcional: Validar que la hora fin sea mayor que la de inicio
        if (h_end * 60 + m_end) <= (h_start * 60 + m_start):
             ui.notify("La hora de fin debe ser mayor a la de inicio", color="warning")
             return

        # -------------------------
        # 4. Crear intervalo y obtener datos de fecha
        # -------------------------
        intervalo = f"{hora_inicio_fmt}-{hora_fin_fmt}"
        
        fecha = date_input.value
        try:
            fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
            dia = dias_es[fecha_dt.strftime('%A')]
        except:
            ui.notify("Formato de fecha inválido", color="warning")
            return

        # Inicializar la estructura si la fecha no existe
        if fecha not in group_data:
            group_data[fecha] = {}

        # -------------------------
        # 5. Guardar intervalo
        # -------------------------
        group_data[fecha][intervalo] = {
            'fecha': fecha,
            'dia': dia,
            'hora': intervalo, 
            'button_id': button_id
        }

        # -------------------------
        # 6. Actualizar tabla
        # -------------------------
        new_rows = []
        for fecha_key, horas in group_data.items():
            for h_lbl, data in horas.items():
                new_rows.append(data)

        # Ordenar por fecha y luego por hora (cadena)
        new_rows.sort(key=lambda x: (x['fecha'], x['hora']))
        table.rows = new_rows
        table.update()
        
        ui.notify(notify_success, type='positive')

        # Limpiar inputs
        start_time_input.value = ""
        end_time_input.value = ""

    button.on('click', add_hours_action)
    return add_hours_action
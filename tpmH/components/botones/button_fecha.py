from components.header import create_main_screen
from components.share_data import *
from components.clear_table import clear_table
from datetime import datetime

from nicegui import ui
from datetime import datetime

def make_add_hours_by_date_button(
        button,
        *,
        package_selector,
        start_time_input,
        duration_selector,
        date_input,
        group_data,
        table,
        button_id=None,
        notify_no_package="Selecciona un paquete primero",
        notify_no_start="Selecciona la hora de inicio",
        notify_no_duration="Selecciona una duración",
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
        # Validaciones
        # -------------------------
        if not package_selector.value:
            ui.notify(notify_no_package, color='warning')
            return

        if not start_time_input.value:
            ui.notify(notify_no_start, color='warning')
            return

        if not duration_selector.value:
            ui.notify(notify_no_duration, color='warning')
            return

        if not date_input.value:
            ui.notify(notify_no_date, color='warning')
            return

        # -------------------------
        # Parsear hora de inicio
        # -------------------------
        try:
            h_start, m_start = map(int, start_time_input.value.split(":"))
        except:
            ui.notify(notify_bad_format, color="warning")
            return

        # -------------------------
        # Calcular hora final según duración
        # -------------------------
        dur = duration_selector.value

        if dur == "30 minutos":
            total_minutes = h_start * 60 + m_start + 30
        elif dur == "1 hora":
            total_minutes = h_start * 60 + m_start + 60
        else:
            ui.notify("Duración desconocida", color="warning")
            return

        h_end = total_minutes // 60
        m_end = total_minutes % 60

        hora_inicio = f"{h_start:02d}:{m_start:02d}"
        hora_fin = f"{h_end:02d}:{m_end:02d}"
        intervalo = f"{hora_inicio}-{hora_fin}"  # <-- formato final

        # -------------------------
        # Obtener fecha y día
        # -------------------------
        fecha = date_input.value
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
        dia = dias_es[fecha_dt.strftime('%A')]

        if fecha not in group_data:
            group_data[fecha] = {}

        # -------------------------
        # Guardar intervalo con identificador del botón
        # -------------------------
        group_data[fecha][intervalo] = {
            'fecha': fecha,
            'dia': dia,
            'hora': intervalo,  # <-- ahora la columna 'hora' muestra inicio-fin
            'button_id': button_id
        }

        # -------------------------
        # Actualizar tabla
        # -------------------------
        new_rows = []
        for fecha_key, horas in group_data.items():
            for h_lbl, data in horas.items():
                new_rows.append(data)

        new_rows.sort(key=lambda x: (x['fecha'], x['hora']))
        table.rows = new_rows
        table.update()
        ui.notify(notify_success, type='positive')

        # Limpiar input de hora de inicio
        start_time_input.value = ""

    button.on('click', add_hours_action)
    return add_hours_action

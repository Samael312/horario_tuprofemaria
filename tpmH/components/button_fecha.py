from nicegui import ui
from components.header import create_main_screen
from components.share_data import *
from components.clear_table import clear_table
from datetime import datetime

def make_add_hours_by_date_button(
        button,
        *,
        package_selector,
        start_time_input,
        end_time_input,
        date_input,
        group_data,
        table,
        notify_no_package="Selecciona un paquete primero",
        notify_no_times="Selecciona hora de inicio y fin",
        notify_no_date="Selecciona una fecha",
        notify_bad_format="Formato de hora incorrecto HH:MM",
        notify_success="Horas agregadas"
    ):
    """
    Molde reutilizable para agregar horas exactas en una tabla según fecha seleccionada.
    """
    dias_es = {
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
        "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
    }

    def add_hours_action():
        # Validaciones básicas
        if not package_selector.value:
            ui.notify(notify_no_package, color='warning')
            return

        if not start_time_input.value or not end_time_input.value:
            ui.notify(notify_no_times, color='warning')
            return

        if not date_input.value:
            ui.notify(notify_no_date, color='warning')
            return

        # Convertir horas a enteros
        try:
            h_start, m_start = map(int, start_time_input.value.split(':'))
            h_end, m_end = map(int, end_time_input.value.split(':'))
        except:
            ui.notify(notify_bad_format, color='warning')
            return

        # Crear intervalos EXACTOS
        intervalos = [f"{h_start:02d}:{m_start:02d}"]
        if not (h_start == h_end and m_start == m_end):
            intervalos.append(f"{h_end:02d}:{m_end:02d}")

        # Obtener fecha y día
        fecha = date_input.value
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
        dia = dias_es[fecha_dt.strftime('%A')]

        # Crear dict para esa fecha si no existe
        if fecha not in group_data:
            group_data[fecha] = {}

        # Guardar intervalos en group_data
        for h_lbl in intervalos:
            group_data[fecha][h_lbl] = {
                'fecha': fecha,
                'dia': dia,
                'hora': h_lbl
            }

        # Reconstruir filas de la tabla
        new_rows = []
        for fecha_key, horas in group_data.items():
            for h_lbl, data in horas.items():
                new_rows.append(data)

        # Ordenar tabla por fecha y hora
        new_rows.sort(key=lambda x: (x['fecha'], x['hora']))

        table.rows = new_rows
        table.update()
        ui.notify(notify_success, type='positive')

    button.on('click', add_hours_action)
    return add_hours_action

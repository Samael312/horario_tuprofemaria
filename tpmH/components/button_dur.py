from nicegui import ui
from components.header import create_main_screen
from components.share_data import *
from components.clear_table import clear_table



def make_add_hour_button(
        button,
        *,
        day_selector,
        duration_selector,
        time_input,
        valid_hours,          # lista de horas válidas ej: ["08:00","08:30",...]
        group_data,           # dict donde modificar valores
        days_of_week,         # lista de días ej: ["Lun","Mar",...]
        table,                # tabla a actualizar
        notify_success="Hora agregada",
        notify_missing_day="Selecciona al menos un día",
        notify_missing_duration="Selecciona duración",
        notify_missing_time="Selecciona hora de inicio",
        notify_invalid_hour="Hora no válida",
        notify_bad_format="Formato incorrecto HH:MM",
        notify_interval_invalid="Hora {h_lbl} es invalida, solo intervalos válidos"
    ):
    """
    Molde reutilizable para crear un botón que agrega intervalos horarios
    a una tabla según el grupo seleccionado.
    """

    def add_hour_action():
        selected_days = day_selector.value
        duration = duration_selector.value
        hora_inicio = time_input.value

        # Validaciones generales
        if not selected_days:
            ui.notify(notify_missing_day, color='warning')
            return

        if not duration:
            ui.notify(notify_missing_duration, color='warning')
            return

        if not hora_inicio:
            ui.notify(notify_missing_time, color='warning')
            return

        # Validar formato HH:MM
        try:
            h, m = map(int, hora_inicio.split(':'))
            hora_label = f"{h:02d}:{m:02d}"
            if hora_label not in valid_hours:
                ui.notify(notify_invalid_hour, color='warning')
                return
        except:
            ui.notify(notify_bad_format, color='warning')
            return

        # Calcular intervalos según duración
        intervalos = [hora_label]

        if duration == '30 minutos':
            m2 = m + 30
            h2 = h + (m2 // 60)
            m2 = m2 % 60
            next_label = f"{h2:02d}:{m2:02d}"
            if next_label in valid_hours:
                intervalos.append(next_label)

        elif duration == '1 hora':
            h2 = h + 1
            next_label = f"{h2:02d}:00"
            if next_label in valid_hours:
                intervalos.append(next_label)

        # Escribir en group_data
        for h_lbl in intervalos:
            if h_lbl not in group_data:
                ui.notify(notify_interval_invalid.format(h_lbl=h_lbl), color='warning')
                continue

            for d in days_of_week:
                group_data[h_lbl][d] = "Elegida" if d in selected_days else ""

        # Reconstruir filas
        new_rows = [
            {"hora": h_lbl, **group_data[h_lbl]}
            for h_lbl in valid_hours
            if any(group_data[h_lbl][d] for d in days_of_week)
        ]

        # Actualizar UI
        table.rows = new_rows
        table.update()
        ui.notify(notify_success, type='positive')

        # Limpiar input
        time_input.value = ""

    # Conectar acción al botón
    button.on("click", add_hour_action)

    return add_hour_action



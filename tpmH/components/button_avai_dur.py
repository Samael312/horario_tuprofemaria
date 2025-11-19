from nicegui import ui
from components.share_data import *
from components.clear_table import clear_table


def make_add_hour_avai_button(
        button,
        *,
        button_id,             # ← NUEVO IDENTIFICADOR DEL BOTÓN
        day_selector,
        availability,
        time_input,
        end_time_input,
        valid_hours,
        group_data,
        days_of_week,
        table,
        notify_success="Hora agregada",
        notify_missing_day="Selecciona al menos un día",
        notify_missing_avai="Selecciona disponibilidad",
        notify_missing_time="Selecciona hora de inicio",
        notify_missing_end_time="Selecciona hora de fin",
        notify_invalid_hour="Hora no válida",
        notify_bad_format="Formato incorrecto HH:MM",
        notify_interval_invalid="Hora {h_lbl} es invalida, solo intervalos válidos"
    ):

    def add_hour_action_avai():
        selected_days = day_selector.value
        hora_inicio = time_input.value
        hora_fin = end_time_input.value

        # Validaciones básicas
        if not selected_days:
            ui.notify(notify_missing_day, color='warning')
            return

        if not hora_inicio:
            ui.notify(notify_missing_time, color='warning')
            return

        if not hora_fin:
            ui.notify(notify_missing_end_time, color='warning')
            return

        # Validar formato HH:MM
        try:
            h_i, m_i = map(int, hora_inicio.split(':'))
            hora_inicio_lbl = f"{h_i:02d}:{m_i:02d}"
        except:
            ui.notify(notify_bad_format, color='warning')
            return

        try:
            h_f, m_f = map(int, hora_fin.split(':'))
            hora_fin_lbl = f"{h_f:02d}:{m_f:02d}"
        except:
            ui.notify(notify_bad_format, color='warning')
            return

        # Validar horas dentro de valid_hours
        if hora_inicio_lbl not in valid_hours:
            ui.notify(f"Hora inicio inválida: {hora_inicio_lbl}", color='warning')
            return

        if hora_fin_lbl not in valid_hours:
            ui.notify(f"Hora fin inválida: {hora_fin_lbl}", color='warning')
            return

        # Guardar ambas horas
        intervalos = [hora_inicio_lbl, hora_fin_lbl]

        # Guardar en group_data incluyendo IDENTIFICADOR DEL BOTÓN
        # Guardar el mismo intervalo en la hora de inicio y la hora final
        for h_lbl in intervalos:
            if h_lbl not in group_data:
                ui.notify(notify_interval_invalid.format(h_lbl=h_lbl), color='warning')
                continue

            for d in days_of_week:
                if d in selected_days:
                    group_data[h_lbl][d] = f"{hora_inicio_lbl}-{hora_fin_lbl}"

            # Guardar fuente del botón
            group_data[h_lbl]["source"] = button_id

        # Actualizar tabla
        new_rows = [
            {"hora": h_lbl, **group_data[h_lbl]}
            for h_lbl in valid_hours
            if any(group_data[h_lbl][d] for d in days_of_week)
        ]

        table.rows = new_rows
        table.update()
        ui.notify(notify_success, type='positive')

        # Limpiar inputs
        time_input.value = ""
        end_time_input.value = ""

    button.on("click", add_hour_action_avai)
    return add_hour_action_avai

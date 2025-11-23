from nicegui import ui

def make_add_hour_avai_button(
    add_btn,
    day_selector,
    availability,
    button_id,
    time_input,
    end_time_input,
    valid_hours,
    group_data,
    days_of_week,
    table,
    notify_success="Hora agregada",
    notify_missing_time="Falta hora inicio",
    notify_missing_end_time="Falta hora fin",
    notify_missing_avai="Falta disponibilidad",
    notify_invalid_hour="Hora no válida",
    notify_bad_format="Formato incorrecto HH:MM",
    notify_interval_invalid="Hora {h_lbl} inválida"
):
    """
    Lógica para agregar horas al Horario General (Grid).
    CORRECCIÓN: Formato de salida incluye disponibilidad: "HH:MM-HH:MM (Disponibilidad)"
    """
    
    def add_hour():
        days = day_selector.value
        avai_val = availability.value
        t1 = time_input.value
        t2 = end_time_input.value

        # Validaciones
        if not days:
            ui.notify("Selecciona al menos un día", type='warning')
            return
        if not avai_val:
            ui.notify(notify_missing_avai, type='warning')
            return
        if not t1:
            ui.notify(notify_missing_time, type='warning')
            return
        if not t2:
            ui.notify(notify_missing_end_time, type='warning')
            return

        # --- CORRECCIÓN CLAVE ---
        # Creamos el string con el formato exacto que espera el parser al guardar
        texto_celda = f"{t1}-{t2} ({avai_val})"

        # Insertar en la estructura de datos
        if t1 in group_data:
            for d in days:
                group_data[t1][d] = texto_celda
        
        # Opcional: Insertar también en la hora de fin para visualización de bloque
        if t2 in group_data:
            for d in days:
                group_data[t2][d] = texto_celda

        # Refrescar tabla visualmente
        new_rows = []
        for h in valid_hours:
            row_data = group_data.get(h, {d: "" for d in days_of_week})
            # Solo agregamos la fila si tiene algún dato
            if any(row_data.values()):
                new_rows.append({'hora': h, **row_data})
        
        table.rows = new_rows
        table.update()
        
        ui.notify(notify_success, type='positive')

    add_btn.on('click', add_hour)
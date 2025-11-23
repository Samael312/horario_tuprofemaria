from nicegui import ui
import uuid

def make_add_hours_by_date_button(
    add_btn,
    start_time_input,
    end_time_input,
    availability,
    date_input,
    group_data, # No se usa realmente en tabla específica tipo lista, pero se mantiene firma
    table,
    button_id=None,
    notify_no_package="Falta disponibilidad",
    notify_no_start="Falta hora inicio",
    notify_no_end="Falta hora fin",
    notify_no_date="Falta fecha",
    notify_bad_format="Formato incorrecto",
    notify_success="Fecha agregada"
):
    """
    Lógica para agregar filas a la tabla de Fechas Específicas.
    """
    
    def add_specific():
        date_val = date_input.value
        t1 = start_time_input.value
        t2 = end_time_input.value
        avai_val = availability.value

        # Validaciones
        if not date_val:
            ui.notify(notify_no_date, type='warning')
            return
        if not avai_val:
            ui.notify(notify_no_package, type='warning')
            return
        if not t1:
            ui.notify(notify_no_start, type='warning')
            return
        if not t2:
            ui.notify(notify_no_end, type='warning')
            return

        # Calcular día de la semana automáticamente
        from datetime import datetime
        try:
            dt = datetime.strptime(date_val, '%Y-%m-%d')
            dia_semana = dt.strftime('%A') 
            # Mapeo simple opcional a español
            dias_map = {'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miercoles', 
                        'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sabado', 'Sunday': 'Domingo'}
            dia_semana = dias_map.get(dia_semana, dia_semana)
        except:
            dia_semana = "-"

        # Crear nueva fila con ID único temporal
        new_row = {
            'id': str(uuid.uuid4()), 
            'fecha': date_val,
            'dia': dia_semana,
            'hora': f"{t1}-{t2}",
            'disponibilidad': avai_val # <--- ESTA CLAVE DEBE COINCIDIR CON LA COLUMNA DE LA TABLA
        }

        # --- CORRECCIÓN DEL ERROR 'str' object has no attribute 'get' ---
        # Usamos append directamente a la lista rows para evitar desambiguación incorrecta de add_rows
        table.rows.append(new_row)
        table.update()
        
        # Scroll al final para ver el nuevo elemento
        table.run_method('scrollTo', len(table.rows)-1)
        
        ui.notify(notify_success, type='positive')

    add_btn.on('click', add_specific)
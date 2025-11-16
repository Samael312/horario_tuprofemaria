from nicegui import ui
import logging

logger = logging.getLogger(__name__)

def display_table(self):
    """
    Actualiza table3 usando los datos almacenados en self.group_data3
    o la estructura que estés usando para las filas de la tabla.
    """
    try:
        # Validación básica
        if not hasattr(self, "table3"):
            ui.notify("table3 no está inicializada.", type='warning')
            return

        if not hasattr(self, "days_of_week") or not hasattr(self, "hours_of_day"):
            ui.notify("days_of_week u hours_of_day no están definidos.", type='warning')
            return

        # Determinar la fuente de datos
        if hasattr(self, "table3_data"):
            data_source = self.table3_data
        elif hasattr(self, "group_data3"):
            data_source = self.group_data3
        else:
            ui.notify("No existe data para mostrar en table3.", type='warning')
            return

        # Convertir dicts a lista de filas estándar
        rows = []

        # Si viene como dict nested tipo group_data[h][day] = value
        if isinstance(data_source, dict):
            for h in self.hours_of_day:
                if h in data_source:
                    row = {'hora': h}
                    for d in self.days_of_week:
                        row[d] = data_source[h].get(d, '')
                    rows.append(row)

        # Si ya viene como lista de dicts
        elif isinstance(data_source, list):
            rows = data_source

        else:
            ui.notify("Formato de datos no soportado para table3.", type='negative')
            return

        # --- Construcción de columnas (hora + días) ---
        columns = (
            [{'name': 'hora', 'label': 'Hora', 'field': 'hora', 'sortable': True}] +
            [{'name': d, 'label': d, 'field': d} for d in self.days_of_week]
        )

        # Actualizar tabla
        self.table3.columns = columns
        self.table3.rows = rows
        self.table3.update()

        # Mostrar tarjeta si existe
        if hasattr(self, "table3_card"):
            self.table3_card.visible = True

        ui.notify("Tabla actualizada.", type="positive")

    except Exception as ex:
        logger.exception(f"Error al mostrar table3: {ex}")
        ui.notify(f"Error al actualizar tabla: {ex}", type="negative")

from nicegui import ui
import logging

logger = logging.getLogger(__name__)

def update_dynamic_table(
    self,
    *,
    table_attr="table",
    data_attr="data",
    fixed_column="hora",
    dynamic_columns=None,      # lista: ej. days_of_week
    card_attr=None,
):
    """
    Actualiza una tabla con:
    - una columna fija
    - columnas dinámicas generadas por lista
    Tal como table3 del usuario.
    """

    table = getattr(self, table_attr, None)
    data = getattr(self, data_attr, None)

    if table is None:
        return

    # Si no hay columnas dinámicas definidas
    if dynamic_columns is None:
        dynamic_columns = []

    try:

        if data is not None and len(data) > 0:

            # --- Construir columnas ---
            columns = (
                [{'name': fixed_column,
                  'label': fixed_column.title(),
                  'field': fixed_column,
                  'sortable': True}]
                +
                [{'name': d, 'label': d, 'field': d} for d in dynamic_columns]
            )

            table.columns = columns

            # --- Preparar filas ---
            if hasattr(data, "to_dict"):   # DataFrame
                rows = data.fillna('').to_dict('records')
            else:
                rows = data

            table.rows = rows

            # Mostrar tarjeta (si existe un card asociado)
            if card_attr:
                getattr(self, card_attr).visible = True

        else:
            table.rows = []
            if card_attr:
                getattr(self, card_attr).visible = True

    except Exception as ex:
        logger.exception(f"Error actualizando tabla dinámica: {ex}")
        ui.notify(f"Error actualizando tabla: {ex}", type="negative")

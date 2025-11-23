from nicegui import ui
import logging

logger = logging.getLogger(__name__)

def delete_selected_rows_v2(
    table,
    selection_state,
    *,
    id_column="id",           # Clave primaria real de tus filas
    success_message="Se eliminaron {count} fila(s).",
    empty_selection_msg="Selecciona una o más filas para eliminar.",
):
    """
    Elimina filas seleccionadas directamente desde nicegui.table.
    """
    selected = selection_state.get("selected_rows", [])

    if not selected:
        ui.notify(empty_selection_msg, type='warning')
        return

    try:
        data = table.rows
        before = len(data)

        # Convertimos ambos lados a str para evitar problemas de tipo
        selected_ids = {str(s) for s in selected}

        # Filtrar filas que NO están seleccionadas
        new_data = [
            row for row in data
            if str(row.get(id_column)) not in selected_ids
        ]

        # Actualizar la tabla
        table.rows = new_data
        table.update()

        # Limpiar selección
        table.selected.clear()
        selection_state["selected_rows"] = []

        # Notificación
        removed = before - len(new_data)
        ui.notify(success_message.format(count=removed), type='positive')

    except Exception as ex:
        logger.exception(f"Error al eliminar filas: {ex}")
        ui.notify(f"Error al eliminar filas: {ex}", type='negative')

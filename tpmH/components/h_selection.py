import logging


logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

def make_selection_handler(table, *, logger=None):
    selected_state = {"selected_rows": []}

    def extract_id(item):
        try:
            if isinstance(item, dict) and 'hora' in item:
                return item['hora']     # <-- La clave real de tu tabla
            if hasattr(item, 'get') and 'hora' in item:
                return item['hora']
            return item
        except:
            return item

    def handler(e):
        try:
            if logger:
                logger.debug(f"EVENTO RECIBIDO: {e}")

            # NiceGUI mantiene automáticamente table.selected
            current = [
                extract_id(row)
                for row in table.selected
            ]

            selected_state["selected_rows"] = current

            if logger:
                logger.info(f"SELECCIÓN FINAL: {current}")

        except Exception as ex:
            if logger:
                logger.exception(f"Error procesando selección: {ex}")
            selected_state["selected_rows"] = []

    return handler, selected_state
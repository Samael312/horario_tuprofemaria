# main.py
import logging
from nicegui import ui
from frontend.ui import init_ui

# =====================================================
# CONFIGURACIÓN
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =====================================================
# FUNCIÓN PRINCIPAL
# =====================================================

def main():
    """Inicializa la aplicación NiceGUI."""
    logger.info("Inicializando aplicación UI")
    init_ui()
    logger.info("Aplicación iniciada correctamente")


if __name__ in {'__main__', '__mp_main__'}:
    main()
    ui.run(title="Tuprofemaria: Creador de Horarios", 
           reload=True, 
           storage_secret='maria_2025_horarios_secret_key_!@#987')

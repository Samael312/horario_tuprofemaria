import logging
import os
from nicegui import ui

# =====================================================
# PRE-CONFIGURACIÓN (FIX RENDER)
# =====================================================
# Asegurar que el directorio 'db' existe antes de importar módulos que lo usan
current_dir = os.path.dirname(os.path.abspath(__file__))
db_dir = os.path.join(current_dir, 'db')
os.makedirs(db_dir, exist_ok=True)

# Ahora sí importamos la UI (que a su vez importa la DB)
from frontend.ui import init_ui

# =====================================================
# LOGGING
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
    
    # Iniciar servidor
    ui.run(
        title="Tuprofemaria: Tu clase, tu ritmo, tu ingles", 
        reload=True, 
        storage_secret='maria_2025_horarios_secret_key_!@#987',
        favicon='./components/icon/logo.png' 
    )
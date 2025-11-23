import logging
import os
from nicegui import ui

# =====================================================
# PRE-CONFIGURACIÓN (FIX RENDER)
# =====================================================
# 1. Obtener ruta base absoluta (donde está main.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Asegurar que el directorio 'db' existe
db_dir = os.path.join(BASE_DIR, 'db')
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
    
    # -------------------------------------------------
    # CONFIGURACIÓN CRÍTICA PARA RENDER
    # -------------------------------------------------
    
    # 1. PUERTO Y HOST
    port = int(os.environ.get("PORT", 8080))
    
    # 2. RUTA ABSOLUTA DEL FAVICON (FIX ICONO)
    # Construimos la ruta uniendo: BASE_DIR + components + icon + logo.png
    favicon_path = os.path.join(BASE_DIR, 'components', 'icon', 'logo.png')
    
    # Iniciar servidor
    ui.run(
        title="Tuprofemaria: Tu clase, tu ritmo, tu ingles", 
        reload=False, 
        storage_secret='maria_2025_horarios_secret_key_!@#987',
        favicon=favicon_path, # Usamos la ruta absoluta
        host='0.0.0.0', 
        port=port       
    )
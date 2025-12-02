import logging
import os
from nicegui import ui

from dotenv import load_dotenv  
from frontend.ui import init_ui

# 2. CARGAR VARIABLES DE ENTORNO ANTES DE NADA
load_dotenv() 

# 3. INICIALIZAR LAS BASES DE DATOS
import db.postgres_db
import db.sqlite_db  

# =====================================================
# PRE-CONFIGURACIÓN 
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_dir = os.path.join(BASE_DIR, 'db')
os.makedirs(db_dir, exist_ok=True)

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
    
    # 2. RUTA ABSOLUTA DEL FAVICON 
    favicon_path = os.path.join(BASE_DIR, 'components', 'icon', 'logo.png')
    
    # Iniciar servidor
    ui.run(
        title="Tuprofemaria: Tu clase, tu ritmo, tu ingles", 
        reload=True, 
        storage_secret='maria_2025_horarios_secret_key_!@#987',
        favicon=favicon_path, 
        host='0.0.0.0', 
        port=port       
    )
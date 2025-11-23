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
    
    # Iniciar servidor
    # MOVIMOS EL FAVICON AQUÍ: Usamos el parámetro nativo 'favicon'
    # Nota: Asegúrate de que la ruta al archivo sea correcta relativa a main.py
    ui.run(
        title="Tuprofemaria: Tu clase, tu ritmo, tu ingles", 
        reload=True, 
        storage_secret='maria_2025_horarios_secret_key_!@#987',
        favicon='./components/icon/logo.png' 
    )
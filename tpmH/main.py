import logging
import os
from fastapi import Request
from nicegui import ui, app
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv
from frontend.ui import init_ui

# 1. CARGAR VARIABLES DE ENTORNO
load_dotenv()

# 2. CONFIGURACIÓN DE RUTAS (CRÍTICO PARA RENDER)
# Esto asegura que encontremos las carpetas sin importar desde dónde se ejecuta el comando
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_dir = os.path.join(BASE_DIR, 'db')
components_dir = os.path.join(BASE_DIR, 'components')

# Crear carpeta db si no existe
os.makedirs(db_dir, exist_ok=True)

# 3. INICIALIZAR BASES DE DATOS
# Importamos después de configurar rutas por si los módulos usan rutas relativas
import db.postgres_db
import db.sqlite_db

# =====================================================
# LOGGING
# =====================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =====================================================
# CONFIGURACIÓN DE SEGURIDAD (MIDDLEWARE)
# =====================================================

unrestricted_page_routes = {
    '/login',
    '/signup',
    '/reset',
    '/MainPage',
    '/method',
    '/planScreen'
}

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # A. No bloquear NiceGUI ni estáticos
        if (request.url.path.startswith('/_nicegui') or
                request.url.path.startswith('/static') or
                request.url.path.startswith('/components') or # Por seguridad si teacher.py monta components
                request.url.path.startswith('/uploads')):
            return await call_next(request)

        # B. Verificar estado de autenticación
        authenticated = app.storage.user.get('authenticated', False)
        path = request.url.path

        # C. USUARIO LOGUEADO
        if authenticated:
            if path in {'/login', '/signup', '/MainPage', '/'}:
                return RedirectResponse('/mainscreen')
            return await call_next(request)

        # D. VISITANTE (NO LOGUEADO)
        else:
            if path == '/':
                return RedirectResponse('/MainPage')
            
            if path in unrestricted_page_routes:
                return await call_next(request)
            
            # Redirigir al login guardando la intención
            return RedirectResponse(f'/login?redirect_to={path}')

# =====================================================
# FUNCIÓN PRINCIPAL
# =====================================================

def main():
    """Inicializa la aplicación NiceGUI."""
    
    # 1. Activar Middleware
    app.add_middleware(AuthMiddleware)

    # 2. Servir Archivos Estáticos (Con validación)
    if os.path.exists(components_dir):
        app.add_static_files('/static', components_dir)
        logger.info(f"📂 Carpeta estática servida en /static: {components_dir}")
    else:
        logger.warning(f"⚠️ NO se encontró la carpeta: {components_dir}. Las imágenes no cargarán.")

    # 3. Iniciar UI
    logger.info("Inicializando aplicación UI")
    init_ui()
    logger.info("Aplicación iniciada correctamente")


if __name__ in {'__main__', '__mp_main__'}:
    main()

    # -------------------------------------------------
    # CONFIGURACIÓN PARA RENDER
    # -------------------------------------------------
    
    # Puerto dinámico de Render (default 8080)
    port = int(os.environ.get("PORT", 8080))
    
    # Ruta del favicon con validación
    favicon_path = os.path.join(components_dir, 'icon', 'logo.png')
    if not os.path.exists(favicon_path):
        logger.warning(f"⚠️ Favicon no encontrado en: {favicon_path}")
        favicon_path = None  # Evita que falle si no está la imagen

    ui.run(
        title="Tuprofemaria: Tu clase, tu ritmo, tu ingles",
        reload=False,  # En producción (Render) reload debe ser False para mejor rendimiento
        storage_secret=os.environ.get('STORAGE_SECRET', 'clave_secreta_default_segura'),
        favicon=favicon_path,
        host='0.0.0.0',
        port=port
    )
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
# BASE_DIR será la carpeta 'tpmH'
# BASE_DIR será la carpeta 'tpmH'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Definir rutas absolutas

# Definir rutas absolutas
db_dir = os.path.join(BASE_DIR, 'db')
components_dir = os.path.join(BASE_DIR, 'components')
uploads_dir = os.path.join(BASE_DIR, 'uploads') # <--- Agregamos uploads aquí
uploads_dir = os.path.join(BASE_DIR, 'uploads') # <--- Agregamos uploads aquí

# Crear carpetas necesarias si no existen
# Crear carpetas necesarias si no existen
os.makedirs(db_dir, exist_ok=True)
os.makedirs(uploads_dir, exist_ok=True) # <--- Aseguramos que uploads exista
os.makedirs(uploads_dir, exist_ok=True) # <--- Aseguramos que uploads exista

# 3. INICIALIZAR BASES DE DATOS
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
    '/login', '/signup', '/reset', '/MainPage', '/method', '/planScreen'
    '/login', '/signup', '/reset', '/MainPage', '/method', '/planScreen'
}

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # A. No bloquear NiceGUI ni estáticos
        if (request.url.path.startswith('/_nicegui') or
                request.url.path.startswith('/static') or
                request.url.path.startswith('/components') or 
                request.url.path.startswith('/uploads')):
            return await call_next(request)

        # B. Verificar estado de autenticación y ROL
        authenticated = app.storage.user.get('authenticated', False)
        role = app.storage.user.get('role', 'client') # Obtenemos el rol (default 'client')
        path = request.url.path

        # C. USUARIO LOGUEADO
        if authenticated:
            # Si intenta entrar al Login, Signup o Landing Page estando ya logueado:
            if path in {'/login', '/signup', '/MainPage', '/'}:
                
                # --- CORRECCIÓN AQUÍ: Redirección inteligente ---
                if role == 'admin':
                    return RedirectResponse('/admin') # Redirigir al panel de admin
                else:
                    return RedirectResponse('/mainscreen') # Redirigir al panel de estudiante
                # -----------------------------------------------
                
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

    # 2. SERVIR ARCHIVOS ESTÁTICOS (CENTRALIZADO)
    
    # A. Components (Usamos /components para coincidir con teacher.py)
    # 2. SERVIR ARCHIVOS ESTÁTICOS (CENTRALIZADO)
    
    # A. Components (Usamos /components para coincidir con teacher.py)
    if os.path.exists(components_dir):
        app.add_static_files('/components', components_dir)
        # Opcional: También servir como /static por compatibilidad
        app.add_static_files('/static', components_dir) 
        logger.info(f"📂 Components montado en: {components_dir}")
    else:
        logger.warning(f"⚠️ NO se encontró components: {components_dir}")

    # B. Uploads (CRÍTICO: Aquí arreglamos el error de 'Not Found')
    if os.path.exists(uploads_dir):
        app.add_static_files('/uploads', uploads_dir)
        logger.info(f"📂 Uploads montado en: {uploads_dir}")
        app.add_static_files('/components', components_dir)
        # Opcional: También servir como /static por compatibilidad
        app.add_static_files('/static', components_dir) 
        logger.info(f"📂 Components montado en: {components_dir}")
    else:
        logger.warning(f"⚠️ NO se encontró components: {components_dir}")

    # B. Uploads (CRÍTICO: Aquí arreglamos el error de 'Not Found')
    if os.path.exists(uploads_dir):
        app.add_static_files('/uploads', uploads_dir)
        logger.info(f"📂 Uploads montado en: {uploads_dir}")
    else:
        logger.warning("⚠️ Carpeta uploads no creada, aunque se intentó crear.")
        logger.warning("⚠️ Carpeta uploads no creada, aunque se intentó crear.")

    # 3. Iniciar UI
    logger.info("Inicializando aplicación UI")
    init_ui()
    logger.info("Aplicación iniciada correctamente")


if __name__ in {'__main__', '__mp_main__'}:
    main()

    # -------------------------------------------------
    # CONFIGURACIÓN PARA RENDER
    # -------------------------------------------------
    port = int(os.environ.get("PORT", 8080))
    
    favicon_path = os.path.join(components_dir, 'icon', 'logo.png')
    if not os.path.exists(favicon_path):
        favicon_path = None
        favicon_path = None

    ui.run(
        title="Tuprofemaria: Tu clase, tu ritmo, tu ingles",
        reload=False,
        reload=False,
        storage_secret=os.environ.get('STORAGE_SECRET', 'clave_secreta_default_segura'),
        favicon=favicon_path,
        host='0.0.0.0',
        port=port
    )
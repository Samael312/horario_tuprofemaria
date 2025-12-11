import logging
import os
from fastapi import Request
from nicegui import ui, app # <--- IMPORTANTE: Importamos 'app'
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
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
# Esta es la ruta base de tu proyecto (donde está main.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Rutas importantes
db_dir = os.path.join(BASE_DIR, 'db')
components_dir = os.path.join(BASE_DIR, 'components') # <--- Ruta a tus recursos

os.makedirs(db_dir, exist_ok=True)

# =====================================================
# LOGGING
# =====================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 1. LISTA DE ACCESO PÚBLICO (Sin login)
unrestricted_page_routes = {
    '/login', 
    '/signup', 
    '/reset', 
    '/MainPage', 
    '/method', 
    '/planScreen'
}

# 2. EL MIDDLEWARE (Copia esto tal cual)
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        
        # A. REGLA DE ORO: No bloquear nunca a NiceGUI ni a los estáticos
        # Si bloqueas esto, sale "Connection Lost"
        if (request.url.path.startswith('/_nicegui') or 
            request.url.path.startswith('/static') or 
            request.url.path.startswith('/uploads')):
            return await call_next(request)

        # B. Verificar si está logueado
        authenticated = app.storage.user.get('authenticated', False)
        path = request.url.path

        # C. SI ESTÁ LOGUEADO (Usuario registrado)
        if authenticated:
            # Si intenta ir al Login o a la Landing Page, lo mandamos a su Dashboard
            if path in {'/login', '/signup', '/MainPage', '/'}:
                return RedirectResponse('/mainscreen')
            # Si va a cualquier otra cosa, lo dejamos pasar
            return await call_next(request)

        # D. SI NO ESTÁ LOGUEADO (Visitante)
        else:
            # Si entra a la raíz, mandarlo a la Landing Page
            if path == '/':
                return RedirectResponse('/MainPage')
            
            # Si quiere entrar a una página pública permitida, déjalo pasar
            if path in unrestricted_page_routes:
                return await call_next(request)
            
            # Si quiere entrar a algo privado (ej: /myclasses), mándalo al Login
            # (Guardamos a donde quería ir para redirigirlo luego)
            return RedirectResponse(f'/login?redirect_to={path}')

# =====================================================
# FUNCIÓN PRINCIPAL
# =====================================================

def main():
    """Inicializa la aplicación NiceGUI."""
    # Activar el middleware
    app.add_middleware(AuthMiddleware)
    
    # --- CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS (CRÍTICO) ---
    # Esto le dice a NiceGUI: "Todo lo que esté en 'components_dir', 
    # sírvelo en la web cuando pidan '/static'"
    app.add_static_files('/static', components_dir)
    logger.info(f"📂 Carpeta estática servida: {components_dir}")
    # -----------------------------------------------------

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
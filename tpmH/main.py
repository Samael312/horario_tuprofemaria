import logging
import os
from dotenv import load_dotenv

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.openapi.utils import get_openapi
from starlette.middleware.base import BaseHTTPMiddleware

from nicegui import ui, app

from api_routes import router as api_router
from frontend.ui import init_ui

# =====================================================
# 1. CARGAR VARIABLES DE ENTORNO
# =====================================================
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

db_dir = os.path.join(BASE_DIR, 'db')
components_dir = os.path.join(BASE_DIR, 'components')
uploads_dir = os.path.join(BASE_DIR, 'uploads')
prompts_dir = os.path.join(BASE_DIR, 'prompts')

os.makedirs(db_dir, exist_ok=True)
os.makedirs(uploads_dir, exist_ok=True)
os.makedirs(prompts_dir, exist_ok=True)

# =====================================================
# LOGGING
# =====================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =====================================================
# MIDDLEWARE DE AUTENTICACIÓN (SOLO WEB)
# =====================================================
unrestricted_page_routes = {
    '/login', '/signup', '/resetpass', '/MainPage', '/method', '/planScreen'
}

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        path = request.url.path

        # 🔹 NO TOCAR API NI NICEGUI
        if (
            path.startswith('/api') or
            path.startswith('/_nicegui') or
            path.startswith('/static') or
            path.startswith('/components') or
            path.startswith('/uploads') or
            path.startswith('/docs') or
            path.startswith('/openapi.json')
        ):
            return await call_next(request)

        authenticated = app.storage.user.get('authenticated', False)
        role = app.storage.user.get('role', 'client')

        # USUARIO LOGUEADO
        if authenticated:
            if path in {'/', '/login', '/signup', '/MainPage'}:
                return RedirectResponse(
                    '/admin' if role == 'admin' else '/mainscreen'
                )
            return await call_next(request)

        # VISITANTE
        if path == '/':
            return RedirectResponse('/MainPage')

        if path in unrestricted_page_routes:
            return await call_next(request)

        return RedirectResponse(f'/login?redirect_to={path}')

# =====================================================
# REGISTRAR API 
# =====================================================
app.include_router(api_router)

# =====================================================
# OPENAPI 
# =====================================================
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Tuprofemaria API",
        version="1.0.0",
        description="API para la aplicación móvil (Flutter)",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# =====================================================
# FUNCIÓN PRINCIPAL
# =====================================================
def main():

    logger.info("Inicializando aplicación...")

    app.add_middleware(AuthMiddleware)

    # Inicializar UI
    init_ui()

    logger.info("Aplicación inicializada correctamente")
    logger.info("POSTGRES_URL: %s", os.environ.get("POSTGRES_URL"))
    logger.info("CALENDAR_ID: %s", os.environ.get("CALENDAR_ID"))

# =====================================================
# ENTRYPOINT
# =====================================================
if __name__ in {'__main__', '__mp_main__'}:
    main()

    port = int(os.environ.get("PORT", 8080))

    favicon_path = os.path.join(components_dir, 'icon', 'logo.png')
    if not os.path.exists(favicon_path):
        favicon_path = None

    ui.run(
        title="Tuprofemaria: Tu clase, tu ritmo, tu inglés",
        reload=True,
        storage_secret=os.environ.get(
            'STORAGE_SECRET', 'clave_secreta_default_segura'
        ),
        favicon=favicon_path,
        host='0.0.0.0',
        port=port,
        fastapi_docs=True,  # ← Swagger activo (opcional)
    )

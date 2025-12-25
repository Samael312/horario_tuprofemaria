# Archivo: backend_config.py
from fastapi import Request, FastAPI
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from api.api_routes import router as api_router

# --- 2. FUNCIÓN DE CONFIGURACIÓN PRINCIPAL ---
def configure_fastapi_app(app_nicegui):
    """
    Recibe la app de NiceGUI y le inyecta la configuración de FastAPI backend.
    """
    
    # A. Configuración de Documentación
    # Forzamos las rutas de Swagger UI
    app_nicegui.openapi_url = "/openapi.json"
    app_nicegui.docs_url = "/docs"
    app_nicegui.redoc_url = "/redoc"

    # B. CORS (Para que Flutter pueda conectarse)
    app_nicegui.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # C. Middleware de Autenticación (Si decides activarlo, descomenta la línea)
    # app_nicegui.add_middleware(AuthMiddleware) 

    # D. Inyectar Rutas de API
    app_nicegui.include_router(api_router)
    
    print("✅ Backend Configurado: CORS, Rutas API y Docs activos.")
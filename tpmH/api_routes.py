# Archivo: api_routes.py
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from db.models import User, AsignedClasses, Material, HWork

# --- 1. SCHEMAS (Modelos de datos para enviar a Flutter) ---
class UserSchema(BaseModel):
    id: int
    username: str
    name: str
    surname: str
    role: str
    class_count: Optional[str] = ""
    payment_info: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class ClassSchema(BaseModel):
    id: int
    date: str
    start_time: int
    end_time: int
    status: str
    topic: Optional[str] = "General English"

class LoginRequest(BaseModel):
    username: str
    password: str

# --- 2. CONFIGURACIÓN DEL ROUTER ---
# Esto agrupa todas las URLs bajo /api
router = APIRouter(prefix="/api", tags=["Mobile App"])

# --- 3. HELPER DE PAGINACIÓN (Estilo de tu referencia) ---
def paginate_list(data: list, limit: int, offset: int):
    """Corta la lista según los parámetros de la app"""
    if offset >= len(data):
        return []
    return data[offset : offset + limit]

# ==========================================
# ENDPOINT 1: LOGIN (Auth)
# ==========================================
@router.post("/login", response_model=UserSchema)
async def login_app(creds: LoginRequest):
    print(f"📱 Intento de login App: {creds.username}")
    
    # AQUI CONECTARIAS CON TU DB REAL
    # user = session.query(User).filter...
    
    # Simulación (Mock) para que Flutter funcione YA:
    if creds.password == "123456": # Password maestra temporal
        return UserSchema(
            id=1,
            username=creds.username,
            name="Estudiante",
            surname="Demo",
            role="student",
            class_count="4/12",
            payment_info={"plan": "Gold", "active": True}
        )
    raise HTTPException(status_code=401, detail="Credenciales inválidas")

# ==========================================
# ENDPOINT 2: CLASES (Dashboard)
# ==========================================
@router.get("/classes")
def get_student_classes(
    username: str,
    limit: int = Query(10, ge=1, description="Clases por página"),
    offset: int = Query(0, ge=0, description="Paginación")
):
    try:
        # 1. Obtener datos (Simulado DB)
        # raw_classes = session.query(AsignedClasses).filter...
        
        # Mock Data
        raw_classes = [
            {"id": 1, "date": "2023-10-25", "start_time": 1000, "end_time": 1100, "status": "Confirmed"},
            {"id": 2, "date": "2023-10-27", "start_time": 1500, "end_time": 1600, "status": "Pending"},
            {"id": 3, "date": "2023-10-30", "start_time": 900, "end_time": 1000, "status": "Done"},
        ]

        # 2. Paginación (Usando el helper)
        paginated = paginate_list(raw_classes, limit, offset)
        
        return paginated
        
    except Exception as e:
        print(f"❌ Error en Classes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# ENDPOINT 3: CHATBOT (Conexión real)
# ==========================================
from prompts.chatbot import get_bot_response

@router.post("/chat")
async def chat_api(request: Request):
    try:
        data = await request.json()
        msg = data.get("message", "")
        # Reutilizamos tu lógica de IA existente
        response = await get_bot_response(msg, "mobile_app")
        return {"response": response}
    except Exception as e:
        print(f"❌ Error en Chat: {e}")
        raise HTTPException(status_code=500, detail="Error en el cerebro de Chipi")
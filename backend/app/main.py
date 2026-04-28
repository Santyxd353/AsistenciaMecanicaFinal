from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.db.session import init_db
from app.models.user import User
from app.models.domain import Vehiculo, Solicitud, Evidencia, Tecnico, Taller
from app.api import auth, solicitudes, tecnicos, vehiculos, talleres
from app.services.storage import UPLOAD_ROOT, ensure_upload_root

app = FastAPI(
    title="Plataforma Inteligente de Emergencias Vehiculares",
    description="Backend para la gestión de incidentes mecánicos y asignación de talleres.",
    version="0.1.0"
)

# Inicializar Base de Datos
@app.on_event("startup")
def on_startup():
    init_db()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción deberías restringir esto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
ensure_upload_root()
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_ROOT)), name="uploads")

@app.get("/")
async def root():
    return {"message": "Bienvenido a la API de Emergencias Vehiculares"}

# Incluir routers de la API
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(vehiculos.router, prefix="/api/v1/vehiculos", tags=["Vehiculos"])
app.include_router(solicitudes.router, prefix="/api/v1/solicitudes", tags=["Solicitudes"])
app.include_router(tecnicos.router, prefix="/api/v1/tecnicos", tags=["Técnicos"])
app.include_router(talleres.router, prefix="/api/v1/talleres", tags=["Talleres"])

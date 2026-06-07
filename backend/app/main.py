"""FastAPI entrypoint.

Key changes vs the original version:

* `on_event` was deprecated by FastAPI; we use the modern `lifespan` async
  context manager instead.
* CORS was previously configured with `allow_origins=["*"]` together with
  `allow_credentials=True`, which the CORS spec forbids: browsers reject the
  preflight. We now read an explicit comma-separated allow-list from
  `CORS_ALLOWED_ORIGINS` (defaults to localhost dev origins).
* New routers wired in for chat, pagos, calificaciones, tracking, auditoría,
  admin and IA-multimodal. Realtime endpoints live in `app.api.realtime`.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.db.session import init_db
from app.models.user import User  # noqa: F401 ensures table registration
from app.models.domain import (  # noqa: F401 ensures table registration
    AnalisisIA,
    AuditLog,
    CalificacionMecanico,
    CalificacionServicio,
    ChatMensaje,
    Cotizacion,
    SolicitudCandidato,
    SolicitudHistorial,
    Especialidad,
    EspecialidadTaller,
    DispositivoToken,
    Evidencia,
    Notificacion,
    Pago,
    SaaSPlan,
    Solicitud,
    Taller,
    TalleresEspecialidades,
    TalleresTiposVehiculo,
    TipoVehiculo,
    Tecnico,
    Tenant,
    TenantSubscription,
    TrackingPing,
    SubscriptionPaymentMock,
    Vehiculo,
)
from app.api import (
    admin,
    auditoria,
    auth,
    calificaciones,
    chat,
    cotizaciones,
    dispositivos,
    especialidades,
    especialidades_taller,
    tecnicos_perfil,
    tipos_vehiculo,
    ia,
    kpis,
    notificaciones,
    onboarding,
    pagos,
    plans,
    realtime as realtime_api,
    solicitudes,
    subscriptions,
    talleres,
    tecnicos,
    tenants,
    tracking,
    vehiculos,
    workshop_admins,
)
from app.services.storage import UPLOAD_ROOT, ensure_upload_root


def _allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if not raw.strip():
        # Sensible defaults for local dev (Angular + Flutter web + Vite ports).
        return [
            "http://localhost:4200",
            "http://127.0.0.1:4200",
            "http://localhost:8080",
            "http://localhost:5173",
        ]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    ensure_upload_root()
    yield


app = FastAPI(
    title="Plataforma Inteligente de Emergencias Vehiculares",
    description=(
        "Backend para la gestión de incidentes mecánicos, asignación inteligente "
        "de talleres y tracking en tiempo real estilo Uber/Yango."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.get("/", tags=["Meta"])
async def root():
    return {
        "message": "API Plataforma Emergencias Vehiculares",
        "version": app.version,
        "docs": "/docs",
    }


@app.get("/health", tags=["Meta"])
async def health():
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(plans.router, prefix="/api/v1/plans", tags=["Plans"])
app.include_router(subscriptions.router, prefix="/api/v1/subscriptions", tags=["Subscriptions"])
app.include_router(onboarding.router, prefix="/api/v1/onboarding", tags=["Onboarding"])
app.include_router(vehiculos.router, prefix="/api/v1/vehiculos", tags=["Vehiculos"])
app.include_router(solicitudes.router, prefix="/api/v1/solicitudes", tags=["Solicitudes"])
app.include_router(tecnicos.router, prefix="/api/v1/tecnicos", tags=["Técnicos"])
# Sub-router para perfil público + calificaciones (mismo prefijo, tag aparte
# para que el Swagger los agrupe lógicamente).
app.include_router(tecnicos_perfil.router, prefix="/api/v1/tecnicos", tags=["Mecánicos - Perfil"])
app.include_router(talleres.router, prefix="/api/v1/talleres", tags=["Talleres"])
app.include_router(especialidades.router, prefix="/api/v1/especialidades", tags=["Especialidades"])
app.include_router(especialidades_taller.router, prefix="/api/v1/especialidades-taller", tags=["Especialidades Taller"])
app.include_router(tipos_vehiculo.router, prefix="/api/v1/tipos-vehiculo", tags=["Tipos de vehículo"])
app.include_router(notificaciones.router, prefix="/api/v1/notificaciones", tags=["Notificaciones"])
app.include_router(dispositivos.router, prefix="/api/v1/dispositivos", tags=["Dispositivos"])
app.include_router(tracking.router, prefix="/api/v1/tracking", tags=["Tracking"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(pagos.router, prefix="/api/v1/pagos", tags=["Pagos"])
app.include_router(calificaciones.router, prefix="/api/v1/calificaciones", tags=["Calificaciones"])
app.include_router(auditoria.router, prefix="/api/v1/auditoria", tags=["Auditoría"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(ia.router, prefix="/api/v1/ia", tags=["IA"])
app.include_router(cotizaciones.router, prefix="/api/v1/cotizaciones", tags=["Cotizaciones"])
app.include_router(kpis.router, prefix="/api/v1/kpis", tags=["KPIs"])
app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["Tenants"])
app.include_router(workshop_admins.router, prefix="/api/v1/workshop-admins", tags=["Workshop Admins"])
app.include_router(realtime_api.router, prefix="/api/v1/ws", tags=["Realtime"])

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_ROOT)), name="uploads")

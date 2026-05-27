# PlanClaude — Diagnóstico y Plan de la Plataforma de Emergencias Vehiculares

> Fecha del diagnóstico: 2026-05-27
> Examen 2 — Deadlines: Presentación 1 = 29/05/2026, Presentación 2 = 07/06/2026, Defensa = 09/06/2026
> Stack: FastAPI + PostgreSQL (backend) · Angular (web) · Flutter (móvil) · IA (Gemini visión, Whisper audio) · FCM push · Cloud Run/Cloud Build

---

## 1. Resumen ejecutivo

El sistema está **mucho más avanzado de lo que parece por el git status**: casi todo el trabajo de la fase 2 (los 4 módulos obligatorios + extras SaaS) ya está implementado por Codex pero **sin commitear**. La arquitectura es sólida y los módulos NO son decorativos: tocan el flujo real.

**Estado de los 4 módulos obligatorios:**

| Módulo obligatorio | Backend | Web (Angular) | Móvil (Flutter) | Veredicto |
|---|---|---|---|---|
| 1. Tiempo real (WebSockets + tracking) | ✅ Real | ✅ Real | ⚠️ Solo FCM push | **Casi completo** |
| 2. Offline + sincronización | ✅ Endpoint con dedup | ✅ PWA real | ❌ **No existe** | **Incompleto (móvil)** |
| 3. KPIs operacionales | ✅ Desde BD real | ✅ Dashboard real | — | **Completo** |
| 4. Multi-tenant SaaS | ✅ Real y aislado | ✅ Real | parcial | **Completo** |

**El mayor hueco**: el modo offline está en la web (PWA) pero **NO en la app móvil**, y el enunciado pide offline *principalmente en el móvil* ("Permitir que la app móvil pueda registrar emergencias incluso cuando el usuario no tenga conexión estable").

**Acciones inmediatas recomendadas:**
1. Commitear el trabajo de Codex ya hecho (evitar pérdida).
2. Implementar offline real en Flutter (mayor riesgo de nota).
3. Endurecer infraestructura (migraciones, escalado de WebSockets).
4. Definir el "aporte propio" del grupo que exige el enunciado.

---

## 2. Qué tenemos (inventario por módulo)

### 2.1 Tiempo real (WebSockets + tracking) — ✅ REAL
- **Backend** `api/realtime.py`: 4 endpoints WS (`/ws/solicitudes/{id}`, `/ws/talleres/{id}`, `/ws/tecnicos/{id}`, `/ws/chat/{id}`), auth por token, salas (rooms), heartbeat ping/pong.
- `services/realtime.py`: manager de conexiones con suscripción por sala/usuario, broadcast, limpieza al desconectar.
- `api/tracking.py` + `services/tracking.py`: ping de ubicación del técnico, persiste `TrackingPing`, calcula distancia (Haversine) y ETA dinámico, hace broadcast por WS.
- **Web** `core/realtime.service.ts`: cliente WS con reconexión exponencial (1s→30s), heartbeat, salas con ref-count. Usado por `taller-solicitudes.component.ts` y `client-portal.component.ts`.
- **Estados** (`EstadoSolicitud`, domain.py:178): PENDIENTE, BUSCANDO_TALLER, ASIGNADA, TECNICO_EN_CAMINO, TECNICO_LLEGO, EN_PROCESO, FINALIZADO, CANCELADO — coinciden con los sugeridos por el enunciado.

### 2.2 Offline + sincronización — ⚠️ PARCIAL
- **Backend** `api/solicitudes.py:868-910`: acepta `cliente_sync_id`, busca duplicado antes de crear → **dedup de incidentes real** (cumple "evitar duplicar incidentes"). Columna indexada `domain.py:411`.
- **Web (PWA)** ✅ completa:
  - Service worker registrado (`app.config.ts:14`), `manifest.webmanifest`, `ngsw-config.json` (cachea KPIs/talleres/solicitudes/tracking, TTL 6h).
  - `core/offline-queue.service.ts`: cola en IndexedDB, `enqueue()` offline / `flush()` al reconectar, con clave de idempotencia.
  - `incident.service.ts:66-77`: detecta `navigator.onLine`, encola si no hay red.
- **Móvil (Flutter)** ❌ **NO implementado**: solo `SharedPreferences` para tokens/cache (`app_controller.dart`). Sin `sqflite`/`hive`/`drift`, sin cola de incidentes offline, sin reintento de sincronización.

### 2.3 KPIs operacionales — ✅ REAL
- **Backend** `api/kpis.py`: 7 KPIs calculados con queries reales (no hardcode), todos scoped por tenant:
  - Tiempo promedio de asignación (creación → asignación)
  - Tiempo promedio de llegada (asignación → técnico llegó)
  - Incidentes por tipo (agrupa por `clasificacion_ia`)
  - Talleres más eficientes (50% tasa finalización + 50% inverso del tiempo)
  - Zonas con más incidentes (agrupa por lat/lng redondeada)
  - Casos cancelados
  - Cumplimiento SLA (% dentro de `sla_esperado_minutos`)
- **Web** `core/kpi.service.ts` + `KpiDashboardComponent` compartido por `dashboard.component.ts` (admin) y `workshop-dashboard.component.ts` (taller). Cumple "Dashboard para los talleres por tenant".

### 2.4 Multi-tenant SaaS — ✅ REAL
- **Modelo** (`domain.py`): tabla `Tenant` (id, nombre, slug único, activo). `tenant_id` FK en User, Taller, Tecnico, Vehiculo, Solicitud, Pago, Calificacion, ChatMensaje, Notificacion, TrackingPing, AuditLog, Cotizacion, etc. (~31 referencias).
- **Aislamiento** (`api/deps.py`): `get_tenant_id()` y `scope_by_tenant()` filtran por `tenant_id`; admin global (`tenant_id=NULL`) puede ver todo. Queries de KPIs/subscriptions/etc. filtran por tenant.
- **SaaS**: `SaaSPlan`, `TenantSubscription`, `SubscriptionPaymentMock`. Planes: Gratis/Intermedio/Premium/Pro con límites (admins, mecánicos, requests/mes). `services/subscription_limits.py` valida cuotas.

### 2.5 Extras y otras funcionalidades — ✅ MAYORMENTE REAL
- **Cotizaciones** `api/cotizaciones.py`: taller cotiza, cliente ve/selecciona, transición automática de estado, emite por WS. `Cotizacion.tiempo_reparacion_horas` cubre "tiempo que tardará en repararse".
- **Pagos** `api/pagos.py`: pago (proveedor mock), comisión 10% de plataforma, scoped por tenant. Último commit añadió flujo de QR. **Es mock, no pasarela real.**
- **Calificaciones** `api/calificaciones.py`: rating 1 por solicitud, actualiza promedio del taller.
- **Chat** `api/chat.py`: mensajes cliente↔taller, por WS.
- **Auditoría** `api/auditoria.py` + `services/audit.py`: log de actor/acción/entidad + historial de transiciones de estado.
- **Admin / Onboarding / Login** : `api/admin.py`, `api/onboarding.py`, `api/workshop_admins.py`, `api/plans.py`, `api/subscriptions.py` — todos reales y wired. Frontend: `/login/admin`, `/login/trabajadores`, `/planes`, `/checkout/:plan`, `/onboarding/taller`, `/upgrade-plan`, `/superadmin`, `/taller/administradores`. Guards: AdminGuard, WorkshopGuard, TecnicoGuard, ClientGuard, CreateWorkshopGuard.
- **IA** `api/ia.py`: `/transcribir-audio` (Whisper), `/analizar-imagen` (`vision_damage.py`: Gemini → HF → heurística), `/generar-resumen`.

---

## 3. Qué falta (priorizado)

### P0 — Crítico (bloquea cumplir el enunciado)
1. **Offline real en la app móvil (Flutter).** El enunciado lo pide explícitamente en móvil. Hoy no existe. Necesita:
   - DB local (`sqflite` o `hive`/`drift`).
   - Guardar emergencia localmente sin internet, marcarla "pendiente de sincronización".
   - Generar `cliente_sync_id` (UUID) en cliente → reusar el dedup que ya existe en backend.
   - Detectar reconexión (`connectivity_plus`), reintentar envío, actualizar estado local (enviado/pendiente/error).
   - Mostrar al usuario el estado de cada emergencia (enviada vs pendiente).
2. **Commit del trabajo sin guardar.** Hay decenas de archivos nuevos/modificados sin commitear (riesgo de pérdida). Ver `git status`.

### P1 — Importante (calidad / requisitos de doc y robustez)
3. **Verificar offline web end-to-end** en navegador real: registrar incidente offline → reconectar → confirmar sync + no-duplicado en BD.
4. **Mostrar al cliente el tiempo estimado de reparación** (`tiempo_reparacion_horas`) en web y móvil si aún no está visible.
5. **Aporte propio del grupo** (exigido: "CADA GRUPO TIENE QUE HACER SU APORTE PROPIO, CON NUEVAS FUNCIONALIDADES"). Definirlo. Ideas en §5.
6. **Documentación PUDS-UML (Ciclos 4 y 5)**: Perfil, Captura de Requisitos, Análisis, Diseño, Implementación, Pruebas, Conclusión, Bibliografía, URL+QR. Es entregable obligatorio aparte del código.

### P2 — Deseable
7. **Pruebas** (el enunciado pide "Flujo de Trabajo: Pruebas"). No hay tests backend/frontend visibles.
8. **Pasarela de pagos** más realista (hoy mock). El enunciado dice "utilizar pasarela de pagos".

---

## 4. Qué es mejorable (deuda técnica)

1. **Migraciones de BD**: no hay Alembic. El esquema se evoluciona con `ALTER TABLE ... IF NOT EXISTS` crudo en `db/session.py:32-107`. Funciona para MVP pero no es profesional/escalable (sin rollback, un solo camino hacia adelante). → Introducir Alembic.
2. **Escalado de WebSockets**: el manager de realtime es **en memoria del proceso**. En Cloud Run con >1 instancia, un broadcast no llega a clientes conectados a otra instancia. → Redis Pub/Sub (o fijar 1 instancia / sticky sessions como mínimo). Sin Redis/Celery en `requirements.txt`.
3. **Offline móvil con DB estructurada** (ver P0) en vez de SharedPreferences.
4. **Cobertura de pruebas** prácticamente nula.
5. **Pagos mock** → integración real o simulación más fiel con webhooks.
6. **Observabilidad**: no se ve logging estructurado/metrics más allá de auditoría.

---

## 5. Plan de acción

### Fase A — Asegurar lo hecho (hoy)
- [ ] `git add` + commits temáticos del trabajo de Codex (separar por módulo: realtime, tracking, kpis, multi-tenant/SaaS, pagos, PWA). Mensajes claros.
- [ ] Arrancar el stack con `docker-compose up` y verificar que levanta (backend + Postgres + frontend).
- [ ] Smoke test de los 4 módulos en local.

### Fase B — Cerrar el hueco P0: offline móvil (Flutter)
- [ ] Añadir `sqflite` (o `drift`) + `connectivity_plus` a `mobile/pubspec.yaml`.
- [ ] Crear `LocalEmergencyStore` (tabla local: payload, estado, cliente_sync_id, timestamps).
- [ ] En `report_screen.dart` / `repositories.dart`: si offline → guardar local con `cliente_sync_id` (UUID) y estado "pendiente".
- [ ] `SyncService`: escucha reconexión, envía pendientes al endpoint existente (reusa dedup `cliente_sync_id`), marca enviado/error.
- [ ] UI: badge de estado por emergencia (enviada / pendiente / error de sync).
- [ ] Probar los 5 casos obligatorios del enunciado (registrar sin internet → recuperar conexión → sincroniza → backend registra → app actualiza estado).

### Fase C — Robustez / infra (P1-P2)
- [ ] Introducir Alembic y migrar `ensure_legacy_schema()` a migraciones versionadas.
- [ ] Redis Pub/Sub para realtime multi-instancia (o documentar limitación + fijar instancia única).
- [ ] Pruebas: unit (servicios assignment/kpis/subscription_limits) + integración (flujo solicitud→asignación→tracking→pago) + e2e web offline.
- [ ] Verificar tiempo estimado de reparación visible al cliente.

### Fase D — Aporte propio del grupo (definir y construir)
Candidatos (elegir 1-2 y que afecten el flujo real, no decorativo):
- **Reasignación automática inteligente con timeout**: ya existe `services/reasignacion.py`; convertirlo en feature destacada (si el taller no responde en X min, reasigna al siguiente candidato y notifica). Alto impacto, bajo costo.
- **Predicción de ETA / demanda** usando histórico de la BD (los datos de tracking ya existen).
- **Panel de salud del técnico en ruta** (tracking en vivo en mapa con desvíos).
- **Sistema de incentivos/ranking** de talleres basado en KPIs ya calculados.
- **Chat con sugerencias de IA** para el taller (resumen + acciones recomendadas).

### Fase E — Documentación (entregable obligatorio)
- [ ] Documento PUDS-UML Ciclos 4 y 5: Perfil, Requisitos, Análisis, Diseño (diagramas UML: casos de uso, secuencia para tiempo real y offline-sync, clases del modelo multi-tenant), Implementación, Pruebas, Conclusión, Bibliografía, URL + QR.
- [ ] Diagramas clave: secuencia de WebSocket tracking, secuencia de sync offline con dedup, ER multi-tenant.

---

## 6. Riesgos y notas

- **Riesgo principal**: offline móvil ausente y deadline cercano (P1 = 29/05). Priorizar Fase B.
- **Riesgo de pérdida**: mucho código sin commit. Hacer Fase A ya.
- **Riesgo de escalado**: WebSockets en memoria — si el demo corre en Cloud Run con autoscaling, el realtime puede fallar de forma intermitente. Para la defensa, fijar 1 instancia o usar Redis.
- **Coherencia con la "regla clave"**: los módulos actuales sí afectan el flujo real (estados reales, dedup real, KPIs desde BD, aislamiento real), lo cual es justo lo que el enunciado exige.

---

## 7. Archivos de referencia clave
- Backend modelos: `backend/app/models/domain.py`, `backend/app/models/user.py`
- Aislamiento tenant: `backend/app/api/deps.py`
- Realtime: `backend/app/api/realtime.py`, `backend/app/services/realtime.py`
- KPIs: `backend/app/api/kpis.py`
- Offline backend (dedup): `backend/app/api/solicitudes.py:868-910`
- Esquema/seeds: `backend/app/db/session.py`
- PWA web: `frontend/ngsw-config.json`, `frontend/src/app/core/offline-queue.service.ts`, `frontend/src/app/core/realtime.service.ts`
- Rutas web: `frontend/src/app/app.routes.ts`
- Móvil: `mobile/lib/src/app_controller.dart`, `mobile/lib/src/repositories.dart`, `mobile/pubspec.yaml`
- Plan SaaS de Codex: `PLAN_SAAS_LOGIN_TALLERES.txt`

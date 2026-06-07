# Seed manual - Ciclo 4

Este documento explica como poblar datos de prueba del ciclo 4 **paso a paso**.

## Alcance del seed

El script `backend/scripts/seed_ciclo4.py` crea o actualiza datos seed con prefijo controlado:

- 4 tenants
- 4 talleres, uno por tenant
- 1 usuario propietario/admin operativo por taller
- 5 conductores
- 3 tecnicos por taller
- 1 vehiculo por conductor
- 10 solicitudes
- 10 cotizaciones
- 10 pagos mock SaaS (`subscription_payment_mock`)
- pagos de servicio adicionales para que KPIs de ingresos no queden en cero
- 10 notificaciones
- 10 tracking pings

## Password comun de usuarios seed

Todos los usuarios creados por este seed usan:

`Prueba*2026`

## Recomendacion de ejecucion

Ejecuta los pasos **en este orden**.

## Opcion A - desde Docker

Desde la raiz del repo:

```powershell
docker compose exec backend python scripts/seed_ciclo4.py --step bootstrap
docker compose exec backend python scripts/seed_ciclo4.py --step tenants
docker compose exec backend python scripts/seed_ciclo4.py --step workshops
docker compose exec backend python scripts/seed_ciclo4.py --step drivers
docker compose exec backend python scripts/seed_ciclo4.py --step technicians
docker compose exec backend python scripts/seed_ciclo4.py --step vehicles
docker compose exec backend python scripts/seed_ciclo4.py --step requests
docker compose exec backend python scripts/seed_ciclo4.py --step quotes
docker compose exec backend python scripts/seed_ciclo4.py --step payments
docker compose exec backend python scripts/seed_ciclo4.py --step notifications
docker compose exec backend python scripts/seed_ciclo4.py --step tracking
docker compose exec backend python scripts/seed_ciclo4.py --step summary
```

## Opcion B - desde entorno local Python

Desde `backend`:

```powershell
python scripts/seed_ciclo4.py --step bootstrap
python scripts/seed_ciclo4.py --step tenants
python scripts/seed_ciclo4.py --step workshops
python scripts/seed_ciclo4.py --step drivers
python scripts/seed_ciclo4.py --step technicians
python scripts/seed_ciclo4.py --step vehicles
python scripts/seed_ciclo4.py --step requests
python scripts/seed_ciclo4.py --step quotes
python scripts/seed_ciclo4.py --step payments
python scripts/seed_ciclo4.py --step notifications
python scripts/seed_ciclo4.py --step tracking
python scripts/seed_ciclo4.py --step summary
```

## Significado de cada paso

- `bootstrap`
  - crea tablas si faltan
  - asegura tenant `default`
  - asegura planes SaaS
  - asegura especialidades base
  - asegura admin global

- `tenants`
  - crea los 4 tenants seed
  - asigna o actualiza su suscripcion activa

- `workshops`
  - crea 1 usuario propietario por tenant
  - crea 1 taller por tenant
  - vincula especialidades

- `drivers`
  - crea 5 usuarios conductores

- `technicians`
  - crea 12 usuarios tecnicos
  - crea 12 perfiles `Tecnico`
  - vincula especialidades

- `vehicles`
  - crea 1 vehiculo por conductor

- `requests`
  - crea 10 solicitudes seed
  - incluye timestamps y estados utiles para KPI

- `quotes`
  - crea 10 cotizaciones
  - deja algunas aceptadas y otras rechazadas/enviadas segun el caso

- `payments`
  - crea 10 `SubscriptionPaymentMock`
  - crea pagos de servicio extra en `Pago` para que KPIs de ingresos tengan datos

- `notifications`
  - crea 10 notificaciones persistidas en BD

- `tracking`
  - crea 10 pings de tracking

- `summary`
  - imprime conteos de control

## Ejecucion total en un solo comando

Si luego quieres correr todo de una vez:

```powershell
docker compose exec backend python scripts/seed_ciclo4.py --step all
```

o en local:

```powershell
python scripts/seed_ciclo4.py --step all
```

## Notas importantes

- El script esta pensado para ser **idempotente en lo posible**.
- Si vuelves a ejecutar un paso, intenta **actualizar** los registros seed en vez de duplicarlos.
- El script usa prefijos como:
  - `seed-c4-req-*`
  - `seed-c4-subpay-*`
  - `seed-c4-servicepay-*`
  - `seed_*`
- Las notificaciones creadas en el paso `notifications` son persistidas en BD. No dependen de que FCM o OneSignal esten configurados.
- En el paso `payments`, los `pagos mock` pedidos se modelaron sobre `SubscriptionPaymentMock`, y ademas se crean pagos de servicio minimos para soportar KPIs de ingresos.

## Usuarios seed principales

- Admin global existente del sistema:
  - `admin`
  - password segun seed base del proyecto

- Propietarios de taller seed:
  - `seed_owner_01`
  - `seed_owner_02`
  - `seed_owner_03`
  - `seed_owner_04`

- Conductores:
  - `seed_driver_01`
  - `seed_driver_02`
  - `seed_driver_03`
  - `seed_driver_04`
  - `seed_driver_05`

- Tecnicos:
  - `seed_tech_01_01` ... `seed_tech_04_03`

## Verificacion rapida sugerida

Despues de ejecutar todo:

```powershell
docker compose exec backend python scripts/seed_ciclo4.py --step summary
```

Si quieres inspeccionar directamente por API despues del seed:

- `GET /api/v1/kpis/`
- `GET /api/v1/notificaciones/`
- `GET /api/v1/solicitudes/`
- `GET /api/v1/cotizaciones/taller`


# Notificaciones

Este documento registra la primera etapa de implementacion del sistema de notificaciones internas tipo push para la plataforma de asistencia mecanica.

## Alcance de esta etapa

Se implemento una base de notificaciones persistentes en backend. Las notificaciones quedan guardadas en base de datos y pueden ser consultadas por el usuario autenticado mediante endpoints REST.

Esta etapa no incluye todavia Firebase Cloud Messaging, service workers, WebSocket, Stripe ni notificaciones reales del sistema operativo. La intencion es dejar primero estable la logica de negocio: quien recibe una notificacion, cuando la recibe y con que solicitud queda asociada.

## Archivos creados o modificados

- `backend/app/models/domain.py`
  - Modelo `Notificacion`.
  - Tabla `notificacion`.
  - Enum `TipoNotificacion`.
  - Esquemas `NotificacionCreate`, `NotificacionRead` y `NotificacionesNoLeidasRead`.

- `backend/app/api/notificaciones.py`
  - Router REST para consultar y marcar notificaciones.

- `backend/app/services/notificaciones.py`
  - Servicio reutilizable para crear una notificacion o varias notificaciones para usuarios.

- `backend/app/main.py`
  - Registro del router `/api/v1/notificaciones`.

- `backend/app/api/solicitudes.py`
  - Integracion de notificaciones con eventos reales de solicitudes.
  - Ajuste de flujo para que las solicitudes no se autoasignen al crearse.
  - Filtro de talleres candidatos por especialidad y cercania.
  - Validacion de visibilidad para talleres candidatos.
  - Notificaciones de cancelacion.

## Modelo de notificacion

Tabla: `notificacion`

Campos principales:

- `id`
- `destinatario_id`
- `tipo`
- `titulo`
- `mensaje`
- `solicitud_id`
- `leida`
- `accion_url`
- `fecha_creacion`

## Tipos de notificacion

Se agregaron los siguientes tipos en `TipoNotificacion`:

- `nueva_solicitud_taller`
- `solicitud_aceptada_conductor`
- `tecnico_asignado`
- `tecnico_en_camino`
- `solicitud_cancelada_conductor`
- `solicitud_cancelada_taller`
- `servicio_concluido_pago`
- `general`

## Endpoints de notificaciones

Base URL:

```text
/api/v1/notificaciones
```

Endpoints implementados:

```text
GET /api/v1/notificaciones/
```

Lista las notificaciones del usuario autenticado.

Parametros:

- `solo_no_leidas`: filtra solo notificaciones no leidas.
- `solicitud_id`: filtra por solicitud.
- `skip`
- `limit`

```text
GET /api/v1/notificaciones/no-leidas/count
```

Devuelve el total de notificaciones no leidas del usuario autenticado.

```text
PATCH /api/v1/notificaciones/{notificacion_id}/leida
```

Marca una notificacion como leida.

```text
PATCH /api/v1/notificaciones/marcar-todas-leidas
```

Marca todas las notificaciones del usuario autenticado como leidas.

## Servicios internos

Archivo:

```text
backend/app/services/notificaciones.py
```

Funciones:

- `crear_notificacion`
- `crear_notificaciones_para_usuarios`

Ambas funciones usan nombres en espanol, siguiendo la convencion solicitada para esta implementacion.

## Flujo de solicitudes ajustado

Antes, al crear una solicitud, el backend intentaba asignar automaticamente un tecnico o un taller.

Ahora, al crear una solicitud:

- queda con estado `pendiente`;
- `taller_id` queda en `None`;
- `tecnico_id` queda en `None`;
- `tiempo_estimado_minutos` queda en `None`;
- se buscan talleres candidatos por especialidad y cercania;
- se crean notificaciones para los talleres candidatos.

Esto permite el flujo esperado:

1. El conductor crea una solicitud.
2. Varios talleres candidatos reciben notificacion.
3. Un taller candidato acepta la solicitud.
4. Ese taller queda asignado a la solicitud.
5. Luego el taller asigna un tecnico.

## Seleccion de talleres candidatos

La seleccion de talleres candidatos esta implementada en `backend/app/api/solicitudes.py`.

Funciones principales:

- `normalizar_texto_busqueda`
- `palabras_clave_para_solicitud`
- `distancia_taller_solicitud`
- `taller_es_compatible_con_solicitud`
- `obtener_talleres_candidatos_para_notificar`
- `taller_es_candidato_para_solicitud`

Reglas actuales:

- Radio maximo: `25 km`.
- Maximo de talleres candidatos: `12`.
- El taller debe tener activas:
  - `notificaciones_push`
  - `notificaciones_nuevas_asignaciones`
- El taller debe tener especialidades compatibles con la clasificacion o descripcion de la solicitud.
- Si el taller no tiene coordenadas, no entra como candidato cercano.

## Eventos implementados

### 1. Conductor crea una solicitud

Evento:

```text
POST /api/v1/solicitudes/
```

Resultado:

- Se crea la solicitud pendiente.
- Se notifican talleres candidatos.

Tipo:

```text
nueva_solicitud_taller
```

Destinatarios:

- Usuarios propietarios de talleres candidatos.

### 2. Taller acepta una solicitud

Evento:

```text
PATCH /api/v1/solicitudes/{solicitud_id}/aceptar
```

Resultado:

- Se valida que el taller sea candidato.
- Se asigna `taller_id`.
- Se calcula `tiempo_estimado_minutos`.
- Se notifica al conductor.

Tipo:

```text
solicitud_aceptada_conductor
```

Destinatario:

- Propietario del vehiculo de la solicitud.

### 3. Taller asigna tecnico

Evento:

```text
PATCH /api/v1/solicitudes/{solicitud_id}/asignar-tecnico
```

Resultado:

- Se asigna `tecnico_id`.
- La solicitud pasa a `asignada`.
- El tecnico queda como no disponible.
- Se notifica al tecnico si tiene `id_usuario`.

Tipo:

```text
tecnico_asignado
```

Destinatario:

- Usuario vinculado al tecnico mediante `id_usuario`.

Nota:

Este evento queda listo para cuando exista UI o app movil del tecnico.

### 4. Tecnico marca solicitud en progreso

Evento:

```text
PATCH /api/v1/solicitudes/mis-asignaciones/{solicitud_id}/estado?estado=en_progreso
```

Resultado:

- La solicitud pasa a `en_progreso`.
- El tecnico queda no disponible.
- Se notifica al conductor que el tecnico esta en camino.

Tipo:

```text
tecnico_en_camino
```

Destinatario:

- Propietario del vehiculo de la solicitud.

### 5. Conductor cancela solicitud

Evento:

```text
PATCH /api/v1/solicitudes/{solicitud_id}/cancelar
```

Resultado:

- La solicitud pasa a `cancelada`.
- Si ya tenia taller asignado, se notifica a ese taller.
- Si estaba pendiente sin taller asignado, se notifica a los talleres candidatos.
- Si habia tecnico asignado, vuelve a estar disponible.

Tipo:

```text
solicitud_cancelada_conductor
```

Destinatarios:

- Taller asignado, o talleres candidatos si todavia no habia taller asignado.

### 6. Taller cancela solicitud

Evento:

```text
PATCH /api/v1/solicitudes/{solicitud_id}/cancelar
```

Resultado:

- La solicitud pasa a `cancelada`.
- Se notifica al conductor.
- Si habia tecnico asignado, vuelve a estar disponible.

Tipo:

```text
solicitud_cancelada_taller
```

Destinatario:

- Propietario del vehiculo de la solicitud.

## Visibilidad de solicitudes

Se ajusto la visibilidad para talleres:

- Un taller puede ver solicitudes asignadas a su taller.
- Un taller puede ver solicitudes pendientes solo si es candidato por especialidad y cercania.

Esto aplica en:

- listado de solicitudes pendientes del taller;
- aceptacion de solicitud;
- consulta de detalle de solicitud.

## Validacion realizada

Se valido compilacion del backend con:

```powershell
python -m compileall backend\app
```

La validacion paso correctamente.

## Pendiente para cerrar fase funcional

Falta ejecutar pruebas con base de datos levantada:

1. Crear solicitud como conductor.
2. Verificar notificaciones para talleres candidatos.
3. Consultar pendientes desde un taller candidato.
4. Aceptar solicitud como taller.
5. Verificar notificacion al conductor.
6. Asignar tecnico con `id_usuario`.
7. Verificar notificacion al tecnico.
8. Marcar solicitud como `en_progreso`.
9. Verificar notificacion al conductor.
10. Cancelar desde conductor y desde taller.
11. Verificar notificaciones de cancelacion.

## Pendientes para siguientes etapas

- UI Angular para listar notificaciones.
- Contador de no leidas.
- Marcar notificaciones como leidas desde frontend.
- Polling o WebSocket.
- Firebase Cloud Messaging para push real.
- Tabla futura de tokens de dispositivo.
- Integracion con pagos cuando Stripe este implementado.
- Notificacion `servicio_concluido_pago`.

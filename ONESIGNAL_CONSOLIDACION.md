# Consolidación OneSignal backend

## Estado actual

- El móvil registra al usuario en OneSignal con `external_id = tenant_id:user_id`.
- El backend intenta enviar primero por OneSignal.
- Si OneSignal falla o no está configurado, puede hacer fallback a FCM legado.

## Variable nueva

- `ENABLE_LEGACY_FCM_FALLBACK`
  - `true` por defecto
  - `false` para desactivar FCM legado y usar solo OneSignal

## Recomendación operativa

### Fase actual

Mantener:

- `ENABLE_LEGACY_FCM_FALLBACK=true`

Mientras:

- se validan más eventos reales
- se revisan dispositivos antiguos
- se confirma que no queda ningún usuario móvil fuera de OneSignal

### Fase siguiente

Cambiar a:

```env
ENABLE_LEGACY_FCM_FALLBACK=false
```

Cuando:

- las pruebas reales en móvil ya sean estables
- los eventos críticos ya lleguen por OneSignal
- ya no dependan del endpoint `/api/v1/dispositivos/token`

## Duplicados

No se detectaron duplicados internos obvios en los flujos validados de:

- aceptar solicitud
- cancelar solicitud

Sí existen dos endpoints de actualización operativa en `solicitudes.py`, por lo que dos clientes distintos podrían disparar el mismo cambio si el frontend los usa mal. Eso no es un duplicado automático del backend, pero conviene mantener una sola ruta por actor en frontend.

## Logs esperados

Cuando OneSignal funcione bien, backend imprimirá algo como:

```text
OneSignal push enviado: message_id=... external_id=1:25 recipients=1 tipo=solicitud_aceptada_conductor solicitud_id=12
```

Si faltan variables:

```text
OneSignal deshabilitado: faltan ONESIGNAL_APP_ID o ONESIGNAL_REST_API_KEY.
```

Si OneSignal falla y fallback está activo, el flujo continuará por FCM legado.

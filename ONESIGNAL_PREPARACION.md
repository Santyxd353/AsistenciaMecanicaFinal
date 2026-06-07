# Preparacion OneSignal - Fase 1

Esta fase deja lista la **preparacion** para integrar OneSignal en el proyecto.

## Estado actual del proyecto

- Cliente movil: `Flutter`
- Backend: `FastAPI`
- Web administrativa: `Angular`
- Bundle / application id actual movil:
  - Android: `com.example.mobile`
  - iOS: `com.example.mobile`

## Importante antes de continuar

El identificador actual `com.example.mobile` sirve para pruebas locales, pero para una integracion seria de OneSignal y notificaciones push conviene definir un identificador propio del proyecto antes de ir a produccion.

Ejemplo recomendado:

- `bo.edu.uagrm.asistenciamecanica`

Si por ahora solo haremos pruebas, se puede continuar con `com.example.mobile`.

## Variables preparadas en el proyecto

Se dejaron listas estas variables para el backend:

- `ONESIGNAL_APP_ID`
- `ONESIGNAL_REST_API_KEY`

Archivos tocados:

- `.env`
- `docker-compose.yml`

## Paso 1 - Crear la app en OneSignal

1. Entrar al dashboard de OneSignal
2. Crear una nueva app
3. Nombre sugerido:
   - `SI2 Examen2 - Asistencia Mecanica`
4. Elegir primero la plataforma:
   - `Android (FCM)`

Referencia oficial:

- `https://documentation.onesignal.com/docs/en/flutter-sdk-setup`
- `https://documentation.onesignal.com/docs/es/android-sdk-setup`

## Paso 2 - Configurar Android en OneSignal

OneSignal para Android requiere credenciales FCM del proyecto Firebase.

Debes:

1. Crear o usar un proyecto Firebase
2. Registrar la app Android con el package name actual:
   - `com.example.mobile`
3. Descargar `google-services.json`
4. Subir/configurar en OneSignal las credenciales FCM correspondientes

### Donde ira el archivo despues

Cuando pasemos a implementacion:

- `mobile/android/app/google-services.json`

## Paso 3 - Obtener llaves necesarias de OneSignal

Debes guardar estos valores del dashboard:

- `OneSignal App ID`
- `REST API Key`

Normalmente se obtienen en:

- `Settings`
- `Keys & IDs`

## Paso 4 - Cargar variables locales del proyecto

Completa `.env` con los valores reales:

```ini
ONESIGNAL_APP_ID=tu_app_id_real
ONESIGNAL_REST_API_KEY=tu_rest_api_key_real
```

Luego recrea el backend:

```powershell
docker compose up -d --build --force-recreate backend
```

## Paso 5 - Validar preparacion backend

Verifica que el contenedor vea las variables:

```powershell
docker compose exec backend printenv ONESIGNAL_APP_ID
docker compose exec backend printenv ONESIGNAL_REST_API_KEY
```

## Paso 6 - Decidir estrategia de identificacion de usuarios

Antes de integrar el SDK, ya dejamos recomendada la estrategia para `external_id`.

### Recomendacion

Usar:

- `tenantId:userId`

Ejemplos:

- `1:25`
- `4:103`

### Por que

Porque el sistema es multi-tenant y asi evitamos colisiones futuras.

## Paso 7 - Definir tags iniciales

Cuando integremos Flutter, los primeros tags recomendados seran:

- `tenant_id`
- `role`
- `taller_id` si aplica

## Checklist de salida de esta fase

La Fase 1 queda completa cuando tengas:

- [ ] App creada en OneSignal
- [ ] Android configurado en OneSignal
- [ ] `google-services.json` disponible
- [ ] `ONESIGNAL_APP_ID` definido
- [ ] `ONESIGNAL_REST_API_KEY` definido
- [ ] Backend recreado con esas variables
- [ ] Estrategia de `external_id` confirmada: `tenantId:userId`

## Siguiente fase

La siguiente fase ya sera de implementacion:

- agregar SDK en Flutter
- inicializar OneSignal
- hacer `login(externalId)` tras autenticacion
- luego conectar el backend para envio transaccional


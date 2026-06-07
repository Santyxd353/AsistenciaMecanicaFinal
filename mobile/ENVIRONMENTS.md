# Entornos Flutter móvil

## Variables soportadas

- `APP_ENV`
  - `dev` (por defecto)
  - `prod`
- `API_BASE_URL`
  - opcional
  - si se define, tiene prioridad sobre cualquier URL guardada localmente
- `ONESIGNAL_APP_ID`
  - requerido para pruebas/uso real de OneSignal

## Reglas actuales

- En `dev`:
  - Android emulador usa `http://10.0.2.2:8000`
  - Web/desktop usan `http://localhost:8000`
  - Si pruebas en teléfono físico, debes pasar `API_BASE_URL`
- En `prod`:
  - la app ignora URLs locales guardadas
  - usa el backend cloud por defecto
  - o el `API_BASE_URL` que se pase explícitamente en el build

## Comandos útiles

### Dev web

```powershell
flutter run -d chrome --web-port 4201 --dart-define=APP_ENV=dev --dart-define=ONESIGNAL_APP_ID=TU_APP_ID
```

### Dev Android emulador

```powershell
flutter run -d emulator-5554 --dart-define=APP_ENV=dev --dart-define=ONESIGNAL_APP_ID=TU_APP_ID
```

### Dev teléfono físico

```powershell
flutter run -d TU_DEVICE_ID --dart-define=APP_ENV=dev --dart-define=ONESIGNAL_APP_ID=TU_APP_ID --dart-define=API_BASE_URL=http://TU_IP_LAN:8000
```

### Build producción Android

```powershell
flutter build apk --dart-define=APP_ENV=prod --dart-define=ONESIGNAL_APP_ID=TU_APP_ID
```

### Build producción Android con backend explícito

```powershell
flutter build apk --dart-define=APP_ENV=prod --dart-define=ONESIGNAL_APP_ID=TU_APP_ID --dart-define=API_BASE_URL=https://tu-backend-produccion.com
```

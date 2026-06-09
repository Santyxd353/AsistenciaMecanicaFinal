# Despliegue en Google Cloud con Compute Engine

Esta guia usa una VM de Compute Engine con Docker Compose. Es la ruta mas
directa para este proyecto porque conserva PostgreSQL, uploads, audios,
WebSockets, PWA y backend sin migrar almacenamiento todavia.

## 1. Crear la VM

En Google Cloud Console:

1. Entra a **Compute Engine**.
2. Crea una instancia.
3. Configuracion recomendada para demo:
   - Region cercana: `southamerica-east1` si esta disponible, o `us-central1`.
   - Maquina: `e2-standard-4` para que Piper/Whisper no se queden sin memoria.
   - Disco: Ubuntu 22.04 LTS, minimo 50 GB.
   - Firewall: permitir HTTP y HTTPS.
4. Reserva una IP estatica si vas a usar dominio.

## 2. Instalar Docker en la VM

Conectate por SSH a la VM y ejecuta:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc >/dev/null
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

Cierra la sesion SSH y vuelve a entrar para que el permiso de Docker se aplique.

## 3. Subir el proyecto

En la VM:

```bash
git clone https://github.com/Santyxd353/SI2_Examen2.git
cd SI2_Examen2
```

Si ya clonaste el repo:

```bash
git pull origin main
```

## 4. Configurar variables

```bash
cp .env.production.example .env
nano .env
```

Para prueba rapida con IP publica:

```env
APP_DOMAIN=:80
FRONTEND_BASE_URL=http://TU_IP_PUBLICA
CORS_ALLOWED_ORIGINS=http://TU_IP_PUBLICA
```

Cuando tengas dominio apuntando a la VM:

```env
APP_DOMAIN=rutasos.tudominio.com
FRONTEND_BASE_URL=https://rutasos.tudominio.com
CORS_ALLOWED_ORIGINS=https://rutasos.tudominio.com
```

Cambia tambien:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `SECRET_KEY`
- `ONESIGNAL_APP_ID`
- `ONESIGNAL_REST_API_KEY`
- `GEMINI_API_KEY` / `GROQ_API_KEY` si los usaran

## 5. Levantar produccion

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

Verificar:

```bash
docker compose -f docker-compose.prod.yml ps
curl http://localhost/health
```

Abrir en navegador:

```text
http://TU_IP_PUBLICA
```

Con dominio:

```text
https://rutasos.tudominio.com
```

Caddy emitira HTTPS automatico cuando `APP_DOMAIN` sea un dominio real que
apunte a la IP de la VM.

## 6. Poblar datos de demo

Solo para demo/examen:

```bash
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_ciclo4.py --step all
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_ciclo4.py --step summary
```

No ejecutes seed en produccion real con clientes reales.

## 7. Compilar la app movil para produccion

Desde tu PC, usando la URL publica:

```bash
cd mobile
flutter build apk --release ^
  --dart-define=APP_ENV=prod ^
  --dart-define=API_BASE_URL=https://rutasos.tudominio.com ^
  --dart-define=ONESIGNAL_APP_ID=TU_ONESIGNAL_APP_ID
```

Para generar AAB:

```bash
flutter build appbundle --release ^
  --dart-define=APP_ENV=prod ^
  --dart-define=API_BASE_URL=https://rutasos.tudominio.com ^
  --dart-define=ONESIGNAL_APP_ID=TU_ONESIGNAL_APP_ID
```

## 8. Comandos utiles

Ver logs:

```bash
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend
docker compose -f docker-compose.prod.yml logs -f caddy
```

Actualizar despues de subir cambios:

```bash
git pull origin main
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

Backup de base de datos:

```bash
docker compose -f docker-compose.prod.yml exec db pg_dump -U rutasos rutasos > backup_rutasos.sql
```

## Notas importantes

- No expongas PostgreSQL a internet.
- No subas `.env` real a GitHub.
- Las fotos, audios y modelos Piper quedan en volumen Docker `backend_uploads`.
- Si la VM se borra sin snapshot/backup, se pierden BD y uploads.
- Para una version mas empresarial despues conviene migrar:
  - PostgreSQL a Cloud SQL.
  - uploads a Cloud Storage.
  - backend a Cloud Run.
  - frontend a Firebase Hosting o Cloud Run.

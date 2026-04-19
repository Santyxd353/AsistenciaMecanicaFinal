# PROYECTO: PLATAFORMA INTELIGENTE DE ATENCIÓN DE EMERGENCIAS VEHICULARES
## MATERIA: SISTEMAS 2 - GESTIÓN S1-2026

## DESCRIPCIÓN DEL PROBLEMA
En entornos urbanos y carreteras, los conductores enfrentan fallas mecánicas, pinchazos o accidentes donde el auxilio suele ser ineficiente y lento. Las alternativas actuales dependen de llamadas telefónicas y carecen de trazabilidad o información clara sobre el problema. Por su parte, los talleres no tienen una forma organizada de recibir solicitudes ni priorizar casos efectivamente.

## OBJETIVO GENERAL
Desarrollar una plataforma que conecte usuarios con talleres mediante el análisis automatizado de incidentes usando datos multimodales (imagen, audio, texto y geolocalización) para optimizar el diagnóstico y la asignación del servicio.

## PLAN DE DESARROLLO (4 ETAPAS)

### ETAPA 1: BACKEND CORE Y PERSISTENCIA (FASTAPI + POSTGRESQL)
- Configuración de FastAPI para la gestión de autenticación y autorización de usuarios y talleres.
- Diseño del modelo relacional en PostgreSQL incluyendo tablas para vehículos, incidentes, estados y evidencias.
- Implementación de la integridad de datos y relaciones complejas para la trazabilidad del servicio.

### ETAPA 2: INTELIGENCIA ARTIFICIAL Y LÓGICA DE ASIGNACIÓN
- Módulo de audio: Transcripción de voz a texto y extracción de información relevante del incidente.
- Módulo de visión: Clasificación automática mediante fotos en categorías como batería, llanta, choque o motor.
- Motor de asignación: Algoritmo para generar la lista de talleres candidatos según ubicación, disponibilidad, capacidad y prioridad.

### ETAPA 3: GESTIÓN DE TALLERES (FRONTEND WEB - ANGULAR)
- Interfaz para visualizar solicitudes con información estructurada, resúmenes automáticos e IA.
- Panel operativo para aceptar/rechazar servicios y actualizar el estado de la atención en tiempo real.
- Gestión de pagos: Registro de la comisión del 10% cobrada por la plataforma sobre el precio del servicio.

### ETAPA 4: APLICACIÓN CLIENTE (MÓVIL - FLUTTER)
- Registro de usuarios y vehículos para reportar emergencias enviando ubicación, fotos y audio.
- Módulo de interacción para visualizar el taller asignado, tiempo estimado de llegada y notificaciones push.
- Pasarela de pagos integrada para que el cliente finalice la transacción desde la aplicación.

## CRONOGRAMA DE HITOS (2026)
- **Avance 1**: Domingo 12 de Abril (23:59).
- **Avance 2**: Domingo 19 de Abril (23:59).
- **Entrega Final Documento**: Domingo 26 de Abril (23:59).
- **Defensa de Examen y App**: Martes 28 de Abril (07:00).

---

## GUÍA DE EJECUCIÓN CON DOCKER 🐳

Esta sección te explica cómo correr el proyecto desde cero utilizando **Docker** y **Docker Compose**. Esto levantará la base de datos (PostgreSQL), la API (FastAPI) y la interfaz de administrador (Angular) automáticamente.

### Prerrequisitos
- Tener [Docker Desktop](https://www.docker.com/products/docker-desktop/) (o el motor de Docker) instalado y corriendo en tu computadora.
- Estar en la raíz de este proyecto en tu terminal.

### Paso a Paso para Levantar el Proyecto

1. **Configuración del entorno**:
   Cerciórate de que tienes el archivo `.env` en la raíz del proyecto. Si no existe, créalo guiándote con el apartado _"Configuración de Variables de Entorno (.env)"_ de este README.

2. **Construir y levantar los contenedores**:
   Abre una terminal en la raíz del proyecto y ejecuta el siguiente comando:
   ```bash
   docker-compose up --build
   ```
   > El flag `--build` forzará a que Docker reconstruya las imágenes (es útil para asegurar que se tome el código más reciente).

3. **Verificar que todo corre**:
   - **Frontend (Angular)**: [http://localhost:4200](http://localhost:4200)
   - **Backend (FastAPI)**: [http://localhost:8000](http://localhost:8000)
   - **Documentación de la API (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Base de Datos (PostgreSQL)**: Servidor en `localhost:5432`.

4. **Para apagar los contenedores**:
   Presiona `Ctrl + C` en la terminal donde está corriendo, o si está en segundo plano (detached), ejecuta:
   ```bash
   docker-compose down
   ```

---

## CONFIGURACIÓN DE VARIABLES DE ENTORNO (`.env`) ⚙️

El proyecto maneja sus credenciales de manera segura con un archivo `.env` en la raíz, que utiliza el servicio `docker-compose.yml`. A continuación se explica qué poner en el este archivo (ejemplo de configuración local para desarrollo):

```ini
# Configuración de PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=sistema_mecanico
POSTGRES_HOST=db
POSTGRES_PORT=5432

# URL de conexión para la base de datos desde el backend
# Utiliza "db" como host porque los contenedores dentro de Docker Compose se comunican a través de los nombres de servicio
DATABASE_URL=postgresql://postgres:postgres@db:5432/sistema_mecanico

# Seguridad para la autenticación y tokens en FastAPI
SECRET_KEY=your-super-secret-key-12345
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Nota para desarrollo local:** Al estar orquestados los servicios en `docker-compose`, el backend ubica la base de datos a través de la red de contenedores usando el host `db` (que referencía al contenedor `db`), por eso el `DATABASE_URL` lleva `@db:5432`.

---

## ESTADO ACTUAL DEL CÓDIGO (Qué hay hasta ahora) 🏗️

Se encuentran armadas las bases estructurales funcionales y de orquestación local para comenzar a integrar con Flutter:

- **Orquestación**: Está listo el archivo `docker-compose.yml` que engrana la arquitectura cliente-servidor (tres servicios: base de datos, backend y frontend).
- **Backend (FastAPI)**:
  - Repositorio con Dockerfile configurado y hot-reload habilitado (`uvicorn app.main:app`).
  - **Modelos de Dominio en Español**: Configuración de Base de Datos relacional usando SQLModel (`Usuario`, `Vehiculo`, `Tecnico`, `Solicitud`, `Evidencia`). Todo el flujo de persistencia está en español para alinear con el requerimiento.
  - **Modelo Taller Implementado**: Nuevo modelo `Taller` separado con perfil completo (ubicación, especialidades, estadísticas, configuración de notificaciones). Relaciones actualizadas para que `Tecnico` y `Solicitud` apunten a `taller.id` en lugar de `user.id`.
  - **API de Talleres Completa**: Endpoints RESTful implementados para gestión completa de talleres (`/api/v1/talleres/`):
    - `POST /` - Crear taller (solo WORKSHOP)
    - `GET /mi-taller` - Obtener perfil del taller
    - `PUT /mi-taller` - Actualizar perfil del taller
    - `GET /estadisticas` - Obtener métricas y KPIs
  - **API de Técnicos Actualizada**: Endpoints modificados para trabajar con talleres (`/api/v1/tecnicos/`):
    - `POST /` - Crear técnico (asociado automáticamente al taller del usuario)
    - `GET /` - Listar técnicos del taller propio
    - `PATCH /{id}/disponibilidad` - Cambiar disponibilidad (con validación de propiedad)
  - **API de Solicitudes Extendida**: Nuevos endpoints para talleres (`/api/v1/solicitudes/`):
    - `GET /mis-solicitudes` - Ver solicitudes asignadas al taller
    - `PATCH /{id}/estado` - Actualizar estado y asignar técnicos
  - **Autenticación Base y Seed de DB**: Funcionalidad instalada de encriptación de Password con Hash `bcrypt` y JWT Tokens. Existe una generación automática de un usuario administrador inicial al levantar la DB.
  - **Inteligencia Artificial (Simulación Preparada)**: El endpoint `POST /api/v1/solicitudes` ya se encarga de parsear las transcripciones enviadas por el aplicativo móvil (para los casos de problema de batería, llanta y motor) clasificando automáticamente y determinando la prioridad y resumen de los mismos antes de asignarlos a los talleres.
  - **Motor Operacional de Asignación**: Preparación para que se crucen disponibilidades de los componentes `Tecnicos` dentro del `Taller`.
- **Frontend (Angular)**:
  - Aplicativo corriendo en entorno `ng serve` con diseño Minimalista e Integrado.
  - **Gestión Visual de Login**: Dashboard que lee el JWT.
  - **Dashboard Operativo**: Dividido en Split-View, permitiendo a un Administrador Operativo revisar su pool de Técnicos en tiempo real (poder marcarlos como Ocupados/Libres) e interactuar con la bandeja de Solicitudes Pendientes.
  - **Representación de Datos Multimodales y Monetarios**: La interfaz del ticket muestra claramente los resultados de la analítica IA (Prioridad y Clasificador en base al transcrito) así como el cobro desglosado indicando el 10% de comisión reservado a la Plataforma por parte del Taller.
- **Base de Datos (PostgreSQL)**:
  - Totalmente lista. Volumen persistente conectado (`postgres_data`) expuesto al puerto externo `5432`. El Backend hace drop/create de sus tablas en cada startup de manera limpia usando comandos cascade.
  - **Nueva tabla `taller`**: Incluye campos para perfil completo, estadísticas, configuración de notificaciones y relación con propietario (usuario WORKSHOP).
  - **Foreign Keys Actualizadas**: `tecnico.taller_id` y `solicitud.taller_id` ahora apuntan correctamente a `taller.id`.

## NOTAS TÉCNICAS ADICIONALES
- La IA debe ser parte integral del flujo principal, manejando casos de incertidumbre si la información es ambigua.
- El sistema debe garantizar notificaciones en tiempo real para mantener la comunicación entre ambas partes.

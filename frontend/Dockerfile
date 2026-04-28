# Stage 1: Build
FROM node:22-alpine

WORKDIR /app

# Instalar Angular CLI globalmente
RUN npm install -g @angular/cli

COPY package*.json ./
RUN npm install

COPY . .

# Exponer el puerto por defecto para desarrollo local
EXPOSE 4200

# Cloud Run inyecta PORT; en local conserva 4200.
CMD ["sh", "-c", "ng serve --host 0.0.0.0 --port ${PORT:-4200} --poll 2000"]

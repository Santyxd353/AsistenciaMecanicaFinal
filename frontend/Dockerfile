FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build -- --configuration production
# Mantiene PWA en app-worker.js y deja ngsw-worker.js como safety worker.
# Esto limpia caches viejos que estaban sirviendo pantallas anteriores en 127.0.0.1.
RUN cp /app/dist/frontend/browser/ngsw-worker.js /app/dist/frontend/browser/app-worker.js \
    && cp /app/dist/frontend/browser/safety-worker.js /app/dist/frontend/browser/ngsw-worker.js

FROM node:22-alpine

WORKDIR /app

RUN npm install -g serve

COPY --from=build /app/dist/frontend/browser ./dist

EXPOSE 4200

CMD ["sh", "-c", "serve -s dist -l tcp://0.0.0.0:${PORT:-4200}"]

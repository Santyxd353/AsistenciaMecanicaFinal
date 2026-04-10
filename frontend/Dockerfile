# Stage 1: Build
FROM node:22-alpine

WORKDIR /app

# Instalar Angular CLI globalmente
RUN npm install -g @angular/cli

COPY package*.json ./
RUN npm install

COPY . .

# Exponer el puerto para ng serve
EXPOSE 4200

# Comando para desarrollo con hot reload
CMD ["ng", "serve", "--host", "0.0.0.0", "--poll", "2000"]

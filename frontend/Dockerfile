FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build -- --configuration production

FROM node:22-alpine

WORKDIR /app

RUN npm install -g serve

COPY --from=build /app/dist/frontend/browser ./dist

EXPOSE 4200

CMD ["sh", "-c", "serve -s dist -l tcp://0.0.0.0:${PORT:-4200}"]

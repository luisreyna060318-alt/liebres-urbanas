# Imagen del frontend (React + Vite) en dos etapas. Se construye con la carpeta frontend/ como contexto:
#   docker build -t liebre-urbana-web --build-arg VITE_API_URL=http://localhost:8000 frontend
#
# Etapa 1: Node compila la aplicación a archivos estáticos (carpeta dist).
FROM node:22-alpine AS build
WORKDIR /app

# Primero solo los archivos de dependencias: Docker reutiliza esta capa mientras no cambien
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# Vite escribe la URL de la API DENTRO del código al compilar, por eso es un argumento de construcción
# y no una variable de entorno del contenedor. Para otra URL hay que volver a construir la imagen.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Etapa 2: nginx solo sirve los archivos ya compilados (la imagen final no lleva Node ni el código fuente).
# La versión "unprivileged" corre sin root y escucha en el puerto 8080 (un usuario normal no puede usar el 80).
FROM nginxinc/nginx-unprivileged:1.28-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

# Docker marca el contenedor como "healthy" cuando nginx responde la página principal
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1

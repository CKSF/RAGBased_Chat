# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app

# Copy package.json from frontend folder
COPY frontend/package*.json ./
RUN npm install

# Copy the rest of the frontend source code
COPY frontend/ .

# FORCE relative paths for production (fixes CORS)
ENV NEXT_PUBLIC_API_URL=""

# Build
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine
COPY --from=builder /app/out /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
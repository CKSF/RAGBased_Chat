FROM node:20-alpine AS builder
WORKDIR /app

# 🇨🇳 CHINA FIX: Use Aliyun NPM Mirror
RUN npm config set registry https://registry.npmmirror.com

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .
ENV NEXT_PUBLIC_API_URL=""
RUN npm run build

FROM nginx:alpine
# 🇨🇳 CHINA FIX: Alpine Mirror
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories

COPY --from=builder /app/out /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
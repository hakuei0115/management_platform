# --- Build stage ---
FROM node:22-slim AS build
WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# --- Nginx stage ---
FROM nginx:1.25-alpine
WORKDIR /usr/share/nginx/html

# 複製 Vue build 出來的 dist
COPY --from=build /app/dist .

# 複製你的 nginx 設定檔
COPY ./nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

FROM node:22-slim

WORKDIR /app

# 設定時區
ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

# 確保 /app 權限屬於 node 使用者
RUN chown -R node:node /app

# 安裝正式環境依賴（使用 npm ci 確保版本一致）
COPY --chown=node:node package*.json ./
RUN npm ci --omit=dev

# 複製應用程式碼
COPY --chown=node:node . .

# 安全性：切換為非 root 使用者
USER node

EXPOSE 3000

CMD ["node", "index.js"]
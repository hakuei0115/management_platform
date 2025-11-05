FROM node:22-slim

WORKDIR /app

# 安裝依賴（利用快取）
COPY package*.json ./
RUN npm install --production

# 複製程式碼
COPY . .

# 對外開放 API port
EXPOSE 3000

# 啟動 Node.js 應用
CMD ["node", "index.js"]
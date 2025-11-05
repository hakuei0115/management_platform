FROM node:22-slim

# 設定時區與工作目錄
ENV TZ=Asia/Taipei
WORKDIR /app

# 複製 package.json 並安裝依賴
COPY package*.json ./
RUN npm install

# 複製專案
COPY . .

# Vue 開發伺服器使用 5173 port
EXPOSE 5173

# 啟動 Vue 開發伺服器
CMD ["npm", "run", "dev", "--", "--host"]
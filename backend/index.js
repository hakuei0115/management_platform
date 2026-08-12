import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import authRoutes from "./routes/auth.js";
import roleRoutes from "./routes/role.js";
import userRouter from "./routes/userRoutes.js";
import equipmentRouter from "./routes/equipmentRouter.js";
import stationRouter from "./routes/stationRouter.js";
import modelMappingRouter from "./routes/modelMappingRouter.js";
import equipmentDataRouter from "./routes/equipmentDataRouter.js";

dotenv.config();
const app = express();

const allowedOrigin = process.env.CORS_ORIGIN || "*";
app.use(cors({
    origin: allowedOrigin === "*" ? "*" : allowedOrigin.split(",").map(s => s.trim()),
    methods: ["GET", "POST", "PUT", "DELETE"],
    allowedHeaders: ["Content-Type", "Authorization"]
}));

// 解析 JSON 請求
app.use(express.json());

// 註冊 API 路由
app.use("/api", authRoutes);
app.use("/api", roleRoutes);
app.use("/api", userRouter);
app.use("/api", equipmentRouter);
app.use("/api", stationRouter);
app.use("/api", modelMappingRouter);
app.use("/api", equipmentDataRouter);

// 啟動伺服器
app.listen(process.env.PORT, () => {
    console.log(`🚀 API Server running at http://localhost:${process.env.PORT}`);
});

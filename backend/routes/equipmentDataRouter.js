import express from "express";
import pool from "../db.js";

const router = express.Router();

router.get("/data", async (req, res) => {
    try {
        const [results] = await pool.query("SELECT * FROM testresults");

        res.json({ data: results });
    } catch (error) {
        console.error("取得設備數據失敗:", error);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

export default router;
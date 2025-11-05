import express from "express";
import pool from "../db.js";
import { translateRecord } from "../utils/plcDecoder.js";

const router = express.Router();

router.get("/data", async (req, res) => {
    try {
        const { start_no, end_no, start_time, end_time } = req.query;

        const [rows] = await pool.query("SELECT * FROM testresults");

        const translated = rows.map(r => translateRecord(r)).filter(Boolean);

        let filtered = translated;

        if (start_no && end_no) {
            const s = parseInt(start_no);
            const e = parseInt(end_no);
            filtered = filtered.filter(r => {
                const num = parseInt(r.serial_no.replace(/\D/g, "")); // 去掉字母取數字部分
                return num >= s && num <= e;
            });
        }

        if (start_time && end_time) {
            const s = new Date(start_time);
            const e = new Date(end_time);
            filtered = filtered.filter(r => {
                const t = new Date(r.test_time);
                return t >= s && t <= e;
            });
        }

        res.json({
            total: translated.length,
            count: filtered.length,
            records: filtered,
        });
    } catch (error) {
        console.error("取得設備數據失敗:", error);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

export default router;
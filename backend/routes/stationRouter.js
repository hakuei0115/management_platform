import express from "express";
import pool from "../db.js";

const router = express.Router();

router.get("/equipments/:equipmentId/stations", async (req, res) => {
    try {
        const equipmentId = req.params.equipmentId;
        const [stations] = await pool.query("SELECT * FROM stations WHERE equipment_id = ?", [equipmentId]);

        res.json({ success: true, data: stations, message: "取得設備站點列表成功" });
    } catch (error) {
        console.error("取得設備站點列表失敗:", error);
        res.status(500).json({ success: false, message: "伺服器錯誤" });
    }
});

router.post("/equipments/:equipmentId/stations", async (req, res) => {
    try {
        const equipmentId = req.params.equipmentId;
        const { id, station_no } = req.body;

        if (!id || !station_no)
            return res.status(400).json({ success: false, message: "缺少必要欄位 station_no" });

        const [result] = await pool.query(
            "INSERT INTO stations (id, equipment_id, station_no) VALUES (?, ?, ?)",
            [id, equipmentId, station_no]
        );

        res.status(200).json({ success: true, message: "站點新增成功" });
    } catch (error) {
        console.error("新增站點失敗:", error);
        res.status(500).json({ success: false, message: "伺服器錯誤" });
    }
});

router.put("/equipments/:equipmentId/stations/:stationId", async (req, res) => {
    try {
        const equipmentId = req.params.equipmentId;
        const stationId = req.params.stationId;
        const { enabled } = req.body;

        if (enabled === undefined)
            return res.status(400).json({ success: false, message: "缺少必要欄位" });

        const [result] = await pool.query("UPDATE stations SET enabled = ? WHERE id = ? AND equipment_id = ?", [enabled, stationId, equipmentId]);

        if (result.affectedRows === 0) {
            return res.status(404).json({ success: false, message: "站點未找到" });
        }

        res.status(200).json({ success: true, message: "站點更新成功" });
    } catch (error) {
        console.error("更新站點失敗:", error);
        res.status(500).json({ success: false, message: "伺服器錯誤" });
    }
});

router.delete("/equipments/:equipmentId/stations/:stationId", async (req, res) => {
    try {
        const equipmentId = req.params.equipmentId;
        const stationId = req.params.stationId;

        const [result] = await pool.query("DELETE FROM stations WHERE id = ? AND equipment_id = ?", [stationId, equipmentId]);

        if (result.affectedRows === 0) {
            return res.status(404).json({ success: false, message: "站點未找到" });
        }

        res.status(200).json({ success: true, message: "站點已刪除" });
    } catch (error) {
        console.error("刪除站點失敗:", error);
        res.status(500).json({ success: false, message: "伺服器錯誤" });
    }
});

export default router;
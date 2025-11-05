import express from "express";
import pool from "../db.js";

const router = express.Router();

router.get("/equipment/:equipmentId/stations", async (req, res) => {
    try {
        const equipmentId = req.params.equipmentId;
        const [stations] = await pool.query("SELECT * FROM stations WHERE equipment_id = ?", [equipmentId]);

        res.json({ stations });
    } catch (error) {
        console.error("取得設備站點列表失敗:", error);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

router.post("/equipments/:equipmentId/stations", async (req, res) => {
    try {
        const equipmentId = req.params.equipmentId;
        const { station_no } = req.body;

        if (!station_no)
            return res.status(400).json({ message: "缺少必要欄位 station_no" });

        const [result] = await pool.query(
            "INSERT INTO stations (equipment_id, station_no) VALUES (?, ?)",
            [equipmentId, station_no]
        );

        res.status(201).json({
            id: result.insertId,
            equipment_id: equipmentId,
            station_no,
            enabled: result.enabled
        });
    } catch (error) {
        console.error("新增站點失敗:", error);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

router.put("/equipments/:equipmentId/stations/:stationId", async (req, res) => {
    try {
        const equipmentId = req.params.equipmentId;
        const stationId = req.params.stationId;
        const { enabled } = req.body;

        if (enabled === undefined)
            return res.status(400).json({ message: "缺少必要欄位" });

        const [result] = await pool.query("UPDATE stations SET enabled = ? WHERE id = ? AND equipment_id = ?", [enabled, stationId, equipmentId]);

        if (result.affectedRows === 0) {
            return res.status(404).json({ message: "站點未找到" });
        }

        res.json({ id: stationId, station_no: result.station_no, equipment_id: equipmentId, enabled });
    } catch (error) {
        console.error("更新站點失敗:", error);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

router.delete("/equipments/:equipmentId/stations/:stationId", async (req, res) => {
    try {
        const equipmentId = req.params.equipmentId;
        const stationId = req.params.stationId;

        const [result] = await pool.query("DELETE FROM stations WHERE id = ? AND equipment_id = ?", [stationId, equipmentId]);

        if (result.affectedRows === 0) {
            return res.status(404).json({ message: "站點未找到" });
        }

        res.json({ message: "站點已刪除" });
    } catch (error) {
        console.error("刪除站點失敗:", error);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

export default router;
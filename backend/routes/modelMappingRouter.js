import express from "express";
import pool from "../db.js";

const router = express.Router();

router.get("/equipments/:equipmentId/model_mappings", async (req, res) => {
    try {
        const { equipmentId } = req.params;
        const [result] = await pool.query(
            "SELECT * FROM model_mappings WHERE equipment_id = ?",
            [equipmentId]
        );

        console.log(result);
        res.json({ equipment_id: equipmentId, channel: result.channel, model_mappings: result });
    } catch (error) {
        console.error("取得型號對照表失敗:", error);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

router.post("/equipments/:equipmentId/model_mappings", async (req, res) => {
    try {
        const equipmentId = req.params.equipmentId;

        const { channel, model_name } = req.body;

        if (channel === undefined || !model_name) {
            return res.status(400).json({ message: "缺少必要欄位" });
        }
        
        const [result] = await pool.query("INSERT INTO model_mappings (equipment_id, channel, model_name) VALUES (?, ?, ?)", [equipmentId, channel, model_name]);

        res.status(201).json({ id: result.insertId, equipment_id: equipmentId, channel, model_name });
    } catch (error) {
        console.error("更新設備映射失敗:", error);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

router.put("/equipments/:equipmentId/model_mappings/:mappingId", async (req, res) => {
    try {
        const equipmentId = req.params.equipmentId;
        const mappingId = req.params.mappingId;

        const { channel, model_name } = req.body;

        if (channel === undefined || !model_name) {
            return res.status(400).json({ message: "缺少必要欄位" });
        }

        const [result] = await pool.query("UPDATE model_mappings SET channel = ?, model_name = ? WHERE id = ? AND equipment_id = ?", [channel, model_name, mappingId, equipmentId]);

        if (result.affectedRows === 0) {
            return res.status(404).json({ message: "型號對照表未找到" });
        }
    } catch (error) {
        console.error("更新型號對照表失敗:", error);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

router.delete("/equipments/:equipmentId/model_mappings/:mappingId", async (req, res) => {
    try {
        const equipmentId = req.params.equipmentId;
        const mappingId = req.params.mappingId;

        const [result] = await pool.query("DELETE FROM model_mappings WHERE id = ? AND equipment_id = ?", [mappingId, equipmentId]);

        if (result.affectedRows === 0) {
            return res.status(404).json({ message: "型號對照表未找到" });
        }

        res.status(204).send();
    } catch (error) {
        console.error("刪除型號對照表失敗:", error);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

export default router;
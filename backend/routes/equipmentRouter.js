import express from "express";
import pool from "../db.js";

const router = express.Router();

router.get("/equipments", async (req, res) => {
    try {
        const [equipment] = await pool.query("SELECT * FROM equipments");

        res.json({ equipment });
    } catch (error) {
        console.error("取得設備列表失敗:", error);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

router.post("/equipments", async (req, res) => {
    try {
        const { equipment_code, name, install_location } = req.body;

        if (!equipment_code || !name || !install_location) {
            return res.status(400).json({ message: "缺少必要欄位" });
        }

        const [exists] = await pool.query("SELECT id FROM equipments WHERE equipment_code = ?", [equipment_code]);

        if (exists.length > 0) {
            return res.status(409).json({ message: "設備代碼已存在" });
        }

        const [result] = await pool.query("INSERT INTO equipments (equipment_code, name, install_location) VALUES (?, ?, ?)", [equipment_code, name, install_location]);

        res.status(201).json({ id: result.insertId, equipment_code, name, install_location, status: result.status });
    } catch (error) {
        console.error("新增設備失敗:", error);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

router.put("/equipments/:id", async (req, res) => {
    try {
        const equipmentId = req.params.id;
        const { equipment_code, name, install_location } = req.body;

        if (!equipment_code || !name || !install_location) {
            return res.status(400).json({ message: "缺少必要欄位" });
        }

        const [result] = await pool.query("UPDATE equipments SET equipment_code = ?, name = ?, install_location = ? WHERE id = ?", [equipment_code, name, install_location, equipmentId]);

        if (result.affectedRows === 0) {
            return res.status(404).json({ message: "設備未找到" });
        }

        res.json({ id: equipmentId, equipment_code, name, install_location });
    } catch (error) {
        console.error("更新設備失敗:", error);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

router.delete("/equipments/:id", async (req, res) => {
    try {
        const equipmentId = req.params.id;

        const [result] = await pool.query("DELETE FROM equipments WHERE id = ?", [equipmentId]);

        if (result.affectedRows === 0) {
            return res.status(404).json({ message: "設備未找到" });
        }

        res.json({ message: "設備已刪除" });
    } catch (error) {
        console.error("刪除設備失敗:", error);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

export default router;
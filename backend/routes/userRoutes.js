import express from "express";
import pool from "../db.js";
import bcrypt from "bcrypt";
import { verifyToken } from "../middleware/authMiddleware.js";
import { requireRole } from "../middleware/roleMiddleware.js";

const router = express.Router();

// 取得所有使用者列表
router.get("/users", verifyToken, requireRole("admin"), async (req, res) => {
    try {
        const [users] = await pool.query("SELECT * FROM users");

        res.json({ users });
    } catch (error) {
        console.error("取得使用者列表失敗:", error);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

// 新增使用者
router.post("/users", verifyToken, requireRole("admin"), async (req, res) => {
    try {
        const { name, email, password } = req.body;

        if (!name || !email || !password) {
            return res.status(400).json({ message: "缺少必要欄位" });
        }

        const [exists] = await pool.query("SELECT id FROM users WHERE email = ?", [email]);

        if (exists.length > 0) {
            return res.status(409).json({ message: "Email 已註冊" });
        }

        const hashedPassword = await bcrypt.hash(password, 10);
        const [result] = await pool.query("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", [name, email, hashedPassword]);

        res.status(201).json({ success: true, message: "使用者註冊成功" });

    } catch (error) {
        console.error("註冊失敗:", error);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

router.put("/users/:id", verifyToken, requireRole("admin"), async (req, res) => {
    try {
        const userId = req.params.id;
        const { name, email } = req.body;

        // 建立動態更新欄位與參數
        const fields = [];
        const params = [];

        if (name !== undefined) {
            fields.push("name = ?");
            params.push(name);
        }

        if (email !== undefined) {
            // 檢查 email 是否已被其他使用者使用
            const [exists] = await pool.query("SELECT id FROM users WHERE email = ? AND id <> ?", [email, userId]);
            if (exists.length > 0) {
                return res.status(409).json({ success: false, message: "Email 已註冊" });
            }
            fields.push("email = ?");
            params.push(email);
        }

        if (fields.length === 0) {
            return res.status(400).json({ success: false, message: "沒有要更新的欄位" });
        }

        params.push(userId);
        const sql = `UPDATE users SET ${fields.join(", ")} WHERE id = ?`;
        const [result] = await pool.query(sql, params);

        if (result.affectedRows === 0) {
            return res.status(404).json({ success: false, message: "使用者不存在" });
        }

        res.status(200).json({ success: true, message: "使用者資料更新成功" });
    } catch (error) {
        console.error("更新使用者失敗:", error);
        res.status(500).json({ success: false, message: "伺服器錯誤" });
    }
});

router.delete("/users/:id", verifyToken, requireRole("admin"), async (req, res) => {
    try {
        const userId = req.params.id;
        const [result] = await pool.query("DELETE FROM users WHERE id = ?", [userId]);

        if (result.affectedRows === 0) {
            return res.status(404).json({ success: false, message: "使用者不存在" });
        }

        res.json({ success: true, message: "使用者已刪除" });
    } catch (error) {
        console.error("刪除使用者失敗:", error);
        res.status(500).json({ success: false, message: "伺服器錯誤" });
    }
});

export default router;
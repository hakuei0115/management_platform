import express from "express";
import bcrypt from "bcrypt";
import pool from "../db.js";
import { verifyToken } from "../middleware/authMiddleware.js";
import { requireRole } from "../middleware/roleMiddleware.js";

const router = express.Router();

router.get("/users", verifyToken, requireRole("admin"), async (req, res) => {
    try {
        const [users] = await pool.query(`
            SELECT 
                u.id, u.name, u.email, u.status,
                r.id AS role_id, r.name AS role_name
            FROM users u
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            LEFT JOIN roles r ON ur.role_id = r.id
            ORDER BY u.id
        `);

        res.json({ success: true, data: users, message: "取得使用者列表成功" });
    } catch (err) {
        console.error("取得使用者列表失敗:", err);
        res.status(500).json({ success: false, message: "伺服器錯誤" });
    }
});

router.post("/users", verifyToken, requireRole("admin"), async (req, res) => {
    const conn = await pool.getConnection();
    try {
        const { name, email, password, role } = req.body;
        if (!name || !email || !password || !role) {
            return res.status(400).json({ success: false, message: "缺少必要欄位" });
        }

        const hash = await bcrypt.hash(password, 10);
        await conn.beginTransaction();

        const [userResult] = await conn.query(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            [name, email, hash]
        );
        const userId = userResult.insertId;

        await conn.query("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", [userId, role]);

        await conn.commit();
        res.json({ success: true, message: "使用者建立成功", user_id: userId });
    } catch (err) {
        await conn.rollback();
        console.error("新增使用者失敗:", err);
        if (err.code === "ER_DUP_ENTRY") {
            return res.status(409).json({ success: false, message: "Email 已存在" });
        }
        res.status(500).json({ success: false, message: "伺服器錯誤" });
    } finally {
        conn.release();
    }
});

router.put("/users/:id", verifyToken, requireRole("admin"), async (req, res) => {
    const conn = await pool.getConnection();
    try {
        const userId = req.params.id;
        const { name, email, password, role } = req.body;

        await conn.beginTransaction();

        await conn.query(
            "UPDATE users SET name = ?, email = ? WHERE id = ?",
            [name, email, userId]
        );

        if (password && password.trim() !== "") {
            const hashed = await bcrypt.hash(password, 10);
            await conn.query(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                [hashed, userId]
            );
        }

        await conn.query(
            "UPDATE user_roles SET role_id = ? WHERE user_id = ?",
            [role, userId]
        );

        await conn.commit();
        res.json({ success: true, message: "使用者更新成功" });
    } catch (err) {
        await conn.rollback();
        console.error("更新使用者失敗:", err);
        res.status(500).json({ success: false, message: "伺服器錯誤" });
    } finally {
        conn.release();
    }
});

router.delete("/users/:id", verifyToken, requireRole("admin"), async (req, res) => {
    const conn = await pool.getConnection();
    try {
        const userId = req.params.id;
        await conn.beginTransaction();

        await conn.query("DELETE FROM user_roles WHERE user_id = ?", [userId]);
        await conn.query("DELETE FROM users WHERE id = ?", [userId]);

        await conn.commit();
        res.json({ success: true, message: "使用者已刪除" });
    } catch (err) {
        await conn.rollback();
        console.error("刪除使用者失敗:", err);
        res.status(500).json({ success: false, message: "伺服器錯誤" });
    } finally {
        conn.release();
    }
});

export default router;
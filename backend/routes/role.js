import express from "express";
import pool from "../db.js";
import { verifyToken } from "../middleware/authMiddleware.js";
import { requireRole } from "../middleware/roleMiddleware.js";

const router = express.Router();

// 取得所有角色列表
router.get("/roles", verifyToken, requireRole("admin"), async (req, res) => {
    try {
        const [roles] = await pool.query("SELECT * FROM roles");
        res.json({ roles });
    } catch (error) {
        console.error("取得角色列表失敗:", error);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

// 給使用者角色
router.post("/roles", verifyToken, requireRole("admin"), async (req, res) => {
    try {
        const { user_id, role_id } = req.body;
        if (!user_id || !role_id)
            return res.status(400).json({ message: "缺少 user_id 或 role_id" });

        const [user] = await pool.query("SELECT * FROM users WHERE id = ?", [user_id]);
        if (user.length === 0)
            return res.status(404).json({ message: "找不到使用者" });

        const [role] = await pool.query("SELECT * FROM roles WHERE id = ?", [role_id]);
        if (role.length === 0)
            return res.status(404).json({ message: "找不到角色" });

        await pool.query(
            "INSERT IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)",
            [user_id, role_id]
        );

        res.json({ message: "已成功指派角色" });
    } catch (err) {
        console.error("指派角色錯誤:", err);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

// 更新使用者角色
router.put("/roles", verifyToken, requireRole("admin"), async (req, res) => {
    try {
        const { user_id, old_role_id, new_role_id } = req.body;
        if (!user_id || !old_role_id || !new_role_id)
            return res.status(400).json({ message: "缺少必要欄位" });

        await pool.query("UPDATE user_roles SET role_id = ? WHERE user_id = ? AND role_id = ?", [new_role_id, user_id, old_role_id]);
        res.json({ message: "已成功更新角色" });
    } catch (err) {
        console.error("更新角色錯誤:", err);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

// 刪除使用者角色
router.delete("/roles", verifyToken, requireRole("admin"), async (req, res) => {
    try {
        const { user_id, role_id } = req.body;
        if (!user_id || !role_id)
            return res.status(400).json({ message: "缺少 user_id 或 role_id" });

        await pool.query("DELETE FROM user_roles WHERE user_id = ? AND role_id = ?", [user_id, role_id]);
        res.json({ message: "已成功刪除角色" });
    } catch (err) {
        console.error("刪除角色錯誤:", err);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

export default router;

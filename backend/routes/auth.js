import express from "express";
import bcrypt from "bcrypt";
import jwt from "jsonwebtoken";
import pool from "../db.js";
import dotenv from "dotenv";

dotenv.config();
const router = express.Router();

// 登入
router.post("/login", async (req, res) => {
    try {
        const { email, password } = req.body;
        const [rows] = await pool.query("SELECT * FROM users WHERE email = ?", [email]);

        if (rows.length === 0)
            return res.status(401).json({ message: "帳號或密碼錯誤" });

        const user = rows[0];
        const valid = await bcrypt.compare(password, user.password_hash);
        if (!valid) return res.status(401).json({ message: "帳號或密碼錯誤" });

        const token = jwt.sign(
            { id: user.id, email: user.email, role: user.role },
            process.env.JWT_SECRET,
            { expiresIn: "15m" }
        );

        res.json({ message: "登入成功", token });
    } catch (err) {
        console.error("❌ 登入錯誤:", err);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

export default router;

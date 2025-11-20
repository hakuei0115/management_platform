import express from "express";
import pool from "../db.js";
import { translateRecord } from "../utils/plcDecoder.js";

const router = express.Router();

router.get("/data", async (req, res) => {
    try {
        let {
            page = 1,
            pageSize = 20,
            start_id,
            end_id,
            product_spec,
            start_time,
            end_time,
            only_ng
        } = req.query;

        // NG CODE (from PLC table)
        const NG_SQL = `
        (
            D008 IN (11,13,15,16,17) OR
            D009 IN (11,13,15,16,17) OR
            D010 IN (11,13,15,16,17) OR
            D011 IN (11,13,15,16,17) OR
            D012 IN (11,13,15,16,17) OR
            D013 IN (11,13,15,16,17) OR
            D014 IN (11,13,15,16,17) OR
            D015 IN (11,13,15,16,17) OR
            D016 IN (11,13,15,16,17) OR
            D017 IN (11,13,15,16,17) OR
            D018 IN (11,13,15,16,17) OR
            D019 IN (11,13,15,16,17)
        )
        `;

        page = Number(page) || 1;
        pageSize = Number(pageSize) || 20;

        const whereClauses = [];
        const whereParams = [];

        // 時間範圍
        if (start_time && end_time) {
            let s = start_time;
            let e = end_time;
            if (s > e) [s, e] = [e, s];

            whereClauses.push("test_time BETWEEN ? AND ?");
            whereParams.push(s, e);
        }

        // 序號範圍
        const hasStartId = typeof start_id === "string" && start_id.trim() !== "";
        const hasEndId   = typeof end_id === "string" && end_id.trim() !== "";

        if (hasStartId || hasEndId) {
            let s = hasStartId ? Number(start_id) : Number(end_id);
            let e = hasEndId   ? Number(end_id)   : Number(start_id);

            if (Number.isNaN(s) || Number.isNaN(e)) {
                return res.status(400).json({ message: "序號格式錯誤" });
            }

            if (s > e) [s, e] = [e, s];

            whereClauses.push("serial_no BETWEEN ? AND ?");
            whereParams.push(s, e);
        }

        // 型號 / D003
        if (product_spec && String(product_spec).trim() !== "") {
            const ch = Number(product_spec);
            if (!Number.isNaN(ch)) {
                whereClauses.push("D003 = ?");
                whereParams.push(ch);
            } else {
                whereClauses.push("D003 = ?");
                whereParams.push(product_spec);
            }
        }

        // 只看 NG
        if (only_ng === "true") {
            whereClauses.push(NG_SQL);
        }

        const whereSQL = whereClauses.length
            ? "WHERE " + whereClauses.join(" AND ")
            : "";

        // ========== count ==========
        const countSql = `
            SELECT COUNT(*) AS total
            FROM testresults
            ${whereSQL}
        `;
        const [countRows] = await pool.query(countSql, whereParams);
        const total = countRows[0]?.total ?? 0;
        const totalPages = Math.ceil(total / pageSize) || 1;

        if (total === 0) {
            return res.json({
                success: true,
                data: { page, pageSize, total, totalPages, records: [] }
            });
        }

        const offset = (page - 1) * pageSize;

        // ========== data ==========
        const dataSql = `
            SELECT *
            FROM testresults
            ${whereSQL}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        `;
        const dataParams = [...whereParams, pageSize, offset];

        const [rows] = await pool.query(dataSql, dataParams);

        const records = rows
            .map(r => translateRecord(r))
            .filter(Boolean);

        res.json({
            success: true,
            data: { page, pageSize, total, totalPages, records }
        });

    } catch (err) {
        console.error("查詢錯誤:", err);
        res.status(500).json({ message: "伺服器錯誤" });
    }
});

export default router;

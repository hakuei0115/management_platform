export function requireRole(...allowedRoles) {
    return (req, res, next) => {
        // 如果沒有 req.user，代表沒經過 JWT 驗證
        if (!req.user) {
            return res.status(401).json({ message: "未登入或 Token 無效" });
        }

        const userRole = req.user.role;

        // 如果使用者角色不在允許列表中
        if (!allowedRoles.includes(userRole)) {
            return res.status(403).json({ message: "權限不足" });
        }

        // 通過檢查，繼續執行下一層
        next();
    };
}
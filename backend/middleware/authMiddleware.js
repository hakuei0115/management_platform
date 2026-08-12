import jwt from "jsonwebtoken";

export const verifyToken = (req, res, next) => {
    const authHeader = req.headers.authorization;
    if (!authHeader)
        return res.status(401).json({ success: false, message: "缺少 Token" });

    const token = authHeader.split(" ")[1];
    const secret = process.env.JWT_SECRET;
    if (!secret) {
        console.error("❌ 伺服器錯誤: 未設定 JWT_SECRET");
        return res.status(500).json({ success: false, message: "伺服器配置錯誤" });
    }

    jwt.verify(token, secret, (err, decoded) => {
        if (err) 
            return res.status(403).json({ success: false, message: "Token 無效或過期" });
        
        req.user = decoded;
        
        next();
    });
};

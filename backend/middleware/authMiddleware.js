import jwt from "jsonwebtoken";

export const verifyToken = (req, res, next) => {
    const authHeader = req.headers.authorization;
    if (!authHeader)
        return res.status(401).json({ success: false, message: "缺少 Token" });

    const token = authHeader.split(" ")[1];
    jwt.verify(token, process.env.JWT_SECRET, (err, decoded) => {
        if (err) 
            return res.status(403).json({ success: false, message: "Token 無效或過期" });
        
        req.user = decoded;
        
        next();
    });
};

export async function fakeLoginAPI(username, password) {
    // 模擬登入驗證
    if (username === "admin" && password === "1234") {
        return {
            success: true,
            token: "mocked-token-123456",
            username: "admin",
        };
    }
    return { success: false };
}

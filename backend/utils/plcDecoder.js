export function codeConvert(result) {
    const map = {
        0: "未測試",
        3: "條件載入",
        4: "加壓中",
        5: "動作中",
        6: "測試中",
        7: "手動調壓",
        9: "迴路異常",
        10: "中止",
        11: "加壓_NG",
        12: "加壓_OK",
        13: "調壓_NG",
        14: "調壓_OK",
        15: "下錶孔_NG",
        16: "上錶孔_NG",
        17: "檢出_NG",
        18: "檢出_OK",
        19: "不測試",
    };
    return map[result] || "未知";
}

function combineHL(high, low) {
  return (high * 0x10000) + low;
}

function signed16ToValue(val, scale = 1) {
    if (val & 0x8000) val = (0x10000 - val) * -1;
    return (val / scale).toFixed(3);
}

export function translateRecord(data) {
    try {
        // === 基本欄位 ===
        const serial_no = combineHL(Number(data.D001), Number(data.D000));
        const station = data.D002;
        const recipe_channel = data.D003;
        const act_low = data.D004;
        const act_high = data.D005;
        const leak_low = data.D006;
        const leak_high = data.D007;

        // === 測試結果 ===
        const results = {};
        for (let i = 0; i < 12; i++) {
            results[`m${(i + 1).toString().padStart(2, "0")}`] = codeConvert(data[`D${(8 + i).toString().padStart(3, "0")}`]);
        }

        // === 各測試項目轉譯 ===
        const decodeLeak = (judgeAddr, leakL, leakH, hi, lo, diffL, diffH) => ({
            judge: String.fromCharCode(data[judgeAddr]) || "",
            leak: (combineHL(data[leakL], data[leakH]) / 1000).toFixed(3),
            hi: signed16ToValue(data[hi], 10),
            lo: signed16ToValue(data[lo], 10),
            diff: (combineHL(data[diffL], data[diffH]) / 1000).toFixed(3),
        });

        const M04 = decodeLeak("D020", "D021", "D022", "D023", "D024", "D025", "D026");
        const M05 = decodeLeak("D028", "D029", "D030", "D031", "D032", "D033", "D034");
        const M08 = decodeLeak("D036", "D037", "D038", "D039", "D040", "D041", "D042");
        const M11 = decodeLeak("D044", "D045", "D046", "D047", "D048", "D049", "D050");

        return {
            serial_no,
            station,
            recipe_channel,
            act_low,
            act_high,
            leak_low,
            leak_high,
            ...results,
            M04,
            M05,
            M08,
            M11,
            time: data.test_time,
        };
    } catch (err) {
        console.error("PLC 轉譯錯誤:", err);
        return null;
    }
}

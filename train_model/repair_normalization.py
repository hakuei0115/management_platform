from __future__ import annotations

import re
from typing import Any


TEXT_REPLACEMENTS = {
    "帽形蓋": "帽型蓋",
    "濾杯吹淨": "吹淨濾杯",
    "清潔": "吹淨",
}

EXACT_REPLACEMENTS = {
    "換氣閥支撐": "更換氣閥支撐",
    "更換D-3環": "更換D-3 O-RING",
    "更換D3環": "更換D-3 O-RING",
    "更換D3 環": "更換D-3 O-RING",
    "更換D-3ORING": "更換D-3 O-RING",
    "吹淨D3環": "吹淨D-3 O-RING",
    "吹淨D3 環": "吹淨D-3 O-RING",
    "吹淨D-3ORING": "吹淨D-3 O-RING",
    "D-3ORING掉落": "D-3 O-RING掉落",
    "D-3ORING缺裝": "D-3 O-RING缺裝",
    "清潔S28異物": "吹淨S28",
    "吹淨S28異物": "吹淨S28",
    "清潔帽型蓋": "吹淨帽型蓋",
}


def normalize_repair_suggestion(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""

    text = re.sub(r"\s+", "", text)

    # 歸一化規格編號：S-28 -> S28, D3 / D-3 -> D-3, O-RING 格式化
    text = re.sub(r"S-(\d+)", r"S\1", text, flags=re.IGNORECASE)
    text = re.sub(r"D-?3", "D-3", text, flags=re.IGNORECASE)
    text = re.sub(r"O-?RING", "O-RING", text, flags=re.IGNORECASE)
    text = text.replace("D-3O-RING", "D-3 O-RING")
    text = text.replace("D-3環", "D-3 O-RING")

    if text in EXACT_REPLACEMENTS:
        text = EXACT_REPLACEMENTS[text]

    for source, target in TEXT_REPLACEMENTS.items():
        text = text.replace(source, target)

    return text

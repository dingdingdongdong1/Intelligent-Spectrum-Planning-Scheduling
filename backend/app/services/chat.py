from __future__ import annotations

import re


def parse_chat_instruction(message: str) -> dict:
    objective = None
    if any(keyword in message for keyword in ["减少频点", "频点数量", "频谱利用率", "少占频"]):
        objective = "minimize_frequency_count"
    elif any(keyword in message for keyword in ["历史", "切换次数", "变更最少", "少改"]):
        objective = "minimize_changes"
    elif any(keyword in message for keyword in ["干扰", "风险最低", "同频", "邻频"]):
        objective = "minimize_interference"

    forbidden_frequencies = []
    if any(keyword in message for keyword in ["禁用", "不能用", "避开", "屏蔽"]):
        forbidden_frequencies = _extract_frequencies(message)

    priority_updates = []
    if "优先级" in message:
        explicit = re.findall(r"([A-Za-z0-9_-]{2,})\s*.*?优先级.*?(?:提高|升高|设为|调整为)?\s*(\d+)?", message)
        for station_id, priority in explicit:
            priority_updates.append({"station_id": station_id, "priority": int(priority) if priority else None})
        service_match = re.search(r"(.{1,12}?)(?:业务|类型).*?优先级.*?(?:提高|升高|设为|调整为)?\s*(\d+)?", message)
        if service_match:
            priority_updates.append({"service_type_contains": service_match.group(1).strip(), "priority": int(service_match.group(2)) if service_match.group(2) else None})

    return {
        "objective": objective,
        "forbidden_frequencies": forbidden_frequencies,
        "priority_updates": priority_updates,
    }


def _extract_frequencies(message: str) -> list[float]:
    values = []
    for match in re.finditer(r"(\d{2,5}(?:\.\d+)?)\s*(?:MHz|mhz|兆赫)?", message):
        value = float(match.group(1))
        if 1 <= value <= 100000:
            values.append(value)
    return values

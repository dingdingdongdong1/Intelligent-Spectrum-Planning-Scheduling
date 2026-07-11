from __future__ import annotations

import re
from typing import Any


OBJECTIVE_RULES = (
    ("minimize_interference", ("干扰最低", "降低干扰", "风险最低", "压降风险", "干扰抑制")),
    ("minimize_bandwidth", ("少占频", "节约频谱", "压缩带宽", "占用最小")),
    ("priority_equipment", ("高优先级装备", "优先装备", "优先保障装备")),
    ("minimize_switching", ("少切换", "减少切换", "变更最少", "保持现有")),
    ("maximize_reuse_efficiency", ("提高复用", "复用效率", "最大复用")),
    ("communication_continuity", ("保通", "通信连续", "链路连续", "抗扰保通")),
    ("task_assurance", ("任务保障", "关键任务", "保障率", "必须保障")),
)


WEIGHT_PRESETS = {
    "task_assurance": {"task": 95, "risk": 70, "spectrum": 45, "priority": 85, "switching": 30, "reuse": 35},
    "minimize_interference": {"task": 70, "risk": 95, "spectrum": 45, "priority": 70, "switching": 25, "reuse": 30},
    "minimize_bandwidth": {"task": 70, "risk": 60, "spectrum": 95, "priority": 60, "switching": 35, "reuse": 75},
    "priority_equipment": {"task": 80, "risk": 70, "spectrum": 45, "priority": 95, "switching": 30, "reuse": 35},
    "minimize_switching": {"task": 75, "risk": 65, "spectrum": 50, "priority": 65, "switching": 95, "reuse": 45},
    "maximize_reuse_efficiency": {"task": 70, "risk": 65, "spectrum": 75, "priority": 55, "switching": 35, "reuse": 95},
    "communication_continuity": {"task": 90, "risk": 85, "spectrum": 40, "priority": 85, "switching": 55, "reuse": 30},
}


def parse_task_intent(message: str) -> dict[str, Any]:
    text = str(message or "").strip()
    objective = _objective(text)
    weights = dict(WEIGHT_PRESETS[objective])
    payload: dict[str, Any] = {
        "message": text,
        "objective": objective,
        "constraint_weights": weights,
        "strategy_profile": _strategy_profile(objective),
    }
    recognized: list[dict[str, str]] = [
        {"type": "规划目标", "target": objective, "detail": _objective_label(objective)},
        {"type": "六维权重", "target": "constraint_weights", "detail": _weight_summary(weights)},
    ]
    warnings: list[str] = []

    available_ranges: list[dict[str, Any]] = []
    forbidden_ranges: list[dict[str, Any]] = []
    for match in re.finditer(r"(\d{1,6}(?:\.\d+)?)\s*(?:-|~|～|至|到)\s*(\d{1,6}(?:\.\d+)?)\s*(?:MHz|mhz|兆赫)?", text):
        start, end = sorted((float(match.group(1)), float(match.group(2))))
        context_start = max(text.rfind("，", 0, match.start()), text.rfind("；", 0, match.start()), text.rfind("。", 0, match.start())) + 1
        context = text[context_start : match.end()]
        if any(word in context for word in ("释放", "新增可用", "补充", "恢复可用", "可用频段")):
            available_ranges.append({"start_mhz": start, "end_mhz": end, "reason": "指挥意图补充可用频段"})
            recognized.append({"type": "补充可用频段", "target": f"{start:g}-{end:g} MHz", "detail": context})
        else:
            reason = "指挥意图避用频段"
            if "干扰" in context:
                reason = "指挥意图标记干扰影响频段"
            forbidden_ranges.append({"start_mhz": start, "end_mhz": end, "reason": reason})
            recognized.append({"type": "禁用/避用频段", "target": f"{start:g}-{end:g} MHz", "detail": context})
    if available_ranges:
        payload["available_ranges"] = available_ranges
    if forbidden_ranges:
        payload["forbidden_ranges"] = forbidden_ranges

    locked_equipment = sorted(set(re.findall(r"\bEG-[A-Za-z0-9_-]+", text, flags=re.IGNORECASE))) if any(word in text for word in ("锁定", "保持", "不得切换")) else []
    locked_units = sorted(set(re.findall(r"\bTU-[A-Za-z0-9_-]+", text, flags=re.IGNORECASE))) if any(word in text for word in ("锁定", "保持", "不得切换")) else []
    if locked_equipment:
        payload["locked_equipment_group_ids"] = locked_equipment
        recognized.append({"type": "锁定装备组", "target": ", ".join(locked_equipment), "detail": "重规划时保持当前指配"})
    if locked_units:
        payload["locked_task_unit_ids"] = locked_units
        recognized.append({"type": "锁定任务单元", "target": ", ".join(locked_units), "detail": "重规划时保持所属装备指配"})

    required_targets = [
        match.group(1)
        for match in re.finditer(
            r"((?:EG|TU)-[A-Za-z0-9_-]+)[^，。；;]{0,18}?(?:必须完全满足|必须保障|不可降级|优先保障)",
            text,
            flags=re.IGNORECASE,
        )
    ]
    if required_targets:
        payload["required_full_targets"] = sorted(set(required_targets))
        recognized.append({"type": "必须满足", "target": ", ".join(payload["required_full_targets"]), "detail": "作为硬约束进入试算"})

    priority_updates = []
    for match in re.finditer(r"((?:EG|TU)-[A-Za-z0-9_-]+)\s*优先级\s*(?:调整为|设为|提高到)?\s*(\d{1,2})", text, flags=re.IGNORECASE):
        priority_updates.append({"target": match.group(1), "priority": min(10, max(1, int(match.group(2))))})
    if priority_updates:
        payload["priority_updates"] = priority_updates
        recognized.extend({"type": "优先级调整", "target": item["target"], "detail": f"调整为 {item['priority']}"} for item in priority_updates)

    avoid_bands = []
    for band in re.findall(r"\b[A-Za-z][A-Za-z0-9-]*-SIM-\d+\b", text):
        position = text.find(band)
        context = text[max(0, position - 10) : position + len(band)]
        if any(word in context for word in ("避开", "避用", "不使用")):
            avoid_bands.append(band)
    if avoid_bands:
        payload["avoid_band_groups"] = sorted(set(avoid_bands))
        recognized.append({"type": "避用频段池", "target": ", ".join(payload["avoid_band_groups"]), "detail": "降低该频段池候选优先级"})

    if any(word in text for word in ("不允许降级", "不可降级", "禁止降级")):
        payload["allow_low_priority_degrade"] = False
        recognized.append({"type": "降级策略", "target": "全部装备组", "detail": "不允许低优先级降级保障"})

    if len(recognized) <= 2:
        warnings.append("未识别到具体对象或频段变化，将仅调整规划目标和六维权重。")
    if "干扰源" in text and not forbidden_ranges:
        warnings.append("检测到干扰源描述，但缺少完整频率范围；请补充起止频率后再转为预案。")

    confidence = min(0.98, 0.56 + 0.07 * (len(recognized) - 2) + (0.08 if objective != "task_assurance" else 0))
    return {
        "message": text,
        "objective": objective,
        "objective_label": _objective_label(objective),
        "confidence": round(confidence, 2),
        "recognized_items": recognized,
        "warnings": warnings,
        "deterministic_payload": payload,
        "requires_confirmation": True,
        "explanation": _fallback_explanation(objective, recognized, warnings),
        "explanation_source": "deterministic",
    }


def _objective(text: str) -> str:
    for objective, keywords in OBJECTIVE_RULES:
        if any(keyword in text for keyword in keywords):
            return objective
    return "task_assurance"


def _strategy_profile(objective: str) -> str:
    return {
        "minimize_interference": "risk_first",
        "minimize_bandwidth": "spectrum_saving",
        "minimize_switching": "minimal_change",
        "communication_continuity": "continuity_first",
    }.get(objective, "balanced")


def _objective_label(objective: str) -> str:
    return {
        "task_assurance": "关键任务保障优先",
        "minimize_interference": "干扰风险最低",
        "minimize_bandwidth": "频谱占用最小",
        "priority_equipment": "高优先级装备优先",
        "minimize_switching": "最小切换代价",
        "maximize_reuse_efficiency": "频谱复用效率最高",
        "communication_continuity": "抗扰保通优先",
    }[objective]


def _weight_summary(weights: dict[str, int]) -> str:
    labels = {"task": "保障", "risk": "风险", "spectrum": "频谱", "priority": "优先级", "switching": "切换", "reuse": "复用"}
    return "、".join(f"{labels[key]} {value}" for key, value in weights.items())


def _fallback_explanation(objective: str, recognized: list[dict[str, str]], warnings: list[str]) -> str:
    detail_count = max(0, len(recognized) - 2)
    suffix = f"；另有 {len(warnings)} 项需要补充确认" if warnings else ""
    return f"已将意图映射为“{_objective_label(objective)}”，识别 {detail_count} 项对象或资源变化{suffix}。确定性优化器将在人工确认后执行。"

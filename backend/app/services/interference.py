from __future__ import annotations

from itertools import combinations

from .geo import haversine_km


def risk_level(score: float) -> str:
    if score >= 80:
        return "高"
    if score >= 35:
        return "中"
    return "低"


def pairwise_risk(station_a: dict, station_b: dict, freq_a: float | None, freq_b: float | None, rules: list[dict]) -> dict | None:
    if freq_a is None or freq_b is None:
        return None
    distance = haversine_km(station_a.get("latitude"), station_a.get("longitude"), station_b.get("latitude"), station_b.get("longitude"))
    if distance is None:
        return None

    spacing_khz = abs(float(freq_a) - float(freq_b)) * 1000
    min_spacing = max(_rule_min_spacing(station_a, rules), _rule_min_spacing(station_b, rules))
    protection = max(
        float(station_a.get("protection_distance_km") or 0),
        float(station_b.get("protection_distance_km") or 0),
        _rule_protection(station_a, rules),
        _rule_protection(station_b, rules),
    )
    power_factor = ((float(station_a.get("tx_power_w") or 0) + float(station_b.get("tx_power_w") or 0)) / 100) * 10
    antenna_factor = max(float(station_a.get("antenna_gain_dbi") or 0), float(station_b.get("antenna_gain_dbi") or 0)) * 0.5

    if spacing_khz <= 0.5 and distance < protection:
        score = 90 + max(0, protection - distance) * 2 + power_factor + antenna_factor
        return {
            "risk_type": "同频干扰",
            "severity": risk_level(score),
            "score": round(min(score, 100), 2),
            "reason": f"两台站同频且距离 {distance:.2f} km 小于保护距离 {protection:.2f} km",
        }
    if 0 < spacing_khz < min_spacing and distance < protection:
        score = 55 + (min_spacing - spacing_khz) / max(min_spacing, 1) * 20 + max(0, protection - distance) + power_factor
        return {
            "risk_type": "邻频干扰",
            "severity": risk_level(score),
            "score": round(min(score, 100), 2),
            "reason": f"频率间隔 {spacing_khz:.1f} kHz 小于要求 {min_spacing:.1f} kHz，距离 {distance:.2f} km",
        }
    if distance < protection * 0.5 and power_factor + antenna_factor > 8:
        score = 25 + power_factor + antenna_factor
        return {
            "risk_type": "近距离高功率风险",
            "severity": risk_level(score),
            "score": round(min(score, 100), 2),
            "reason": f"距离 {distance:.2f} km 较近且功率/天线增益偏高",
        }
    return None


def estimate_interference_risk(assignments: list[dict], stations: list[dict], rules: list[dict]) -> dict:
    station_by_id = {station["station_id"]: station for station in stations}
    assignment_by_station = {item["station_id"]: item for item in assignments}
    risks: list[dict] = []
    station_scores: dict[str, float] = {station["station_id"]: 0 for station in stations}

    for station_a, station_b in combinations(stations, 2):
        assignment_a = assignment_by_station.get(station_a["station_id"])
        assignment_b = assignment_by_station.get(station_b["station_id"])
        if not assignment_a or not assignment_b:
            continue
        risk = pairwise_risk(
            station_a,
            station_b,
            assignment_a.get("assigned_frequency_mhz"),
            assignment_b.get("assigned_frequency_mhz"),
            rules,
        )
        if risk:
            item = {
                **risk,
                "station_a": station_a["station_id"],
                "station_b": station_b["station_id"],
                "frequency_a_mhz": assignment_a.get("assigned_frequency_mhz"),
                "frequency_b_mhz": assignment_b.get("assigned_frequency_mhz"),
            }
            risks.append(item)
            weighted = risk["score"] * max(int(station_a.get("priority") or 1), int(station_b.get("priority") or 1))
            station_scores[station_a["station_id"]] += weighted
            station_scores[station_b["station_id"]] += weighted

    for assignment in assignments:
        score = station_scores.get(assignment["station_id"], 0)
        assignment["risk_score"] = round(score, 2)
        assignment["risk_level"] = risk_level(score)
        if not assignment.get("notes"):
            assignment["notes"] = "未发现明显同频/邻频风险" if score < 35 else "存在干扰风险，请查看风险明细"

    return {
        "assignments": assignments,
        "risk_items": sorted(risks, key=lambda item: item["score"], reverse=True),
        "summary": {
            "risk_item_count": len(risks),
            "high_risk_count": sum(1 for item in risks if item["severity"] == "高"),
            "medium_risk_count": sum(1 for item in risks if item["severity"] == "中"),
            "average_station_risk": round(sum(station_scores.values()) / max(len(station_scores), 1), 2),
        },
    }


def _matching_rules(station: dict, rules: list[dict]) -> list[dict]:
    return [
        rule
        for rule in rules
        if rule.get("band_group") == station.get("available_band_group") and rule.get("service_type") == station.get("service_type")
    ]


def _rule_min_spacing(station: dict, rules: list[dict]) -> float:
    values = [float(rule.get("min_spacing_khz") or 0) for rule in _matching_rules(station, rules)]
    return max(values) if values else 0


def _rule_protection(station: dict, rules: list[dict]) -> float:
    values = [float(rule.get("protection_distance_km") or 0) for rule in _matching_rules(station, rules)]
    return max(values) if values else 0

from __future__ import annotations

from collections import Counter, defaultdict

from .channels import generate_channels


def build_visualization_data(
    stations: list[dict],
    rules: list[dict],
    assignments: list[dict],
    risks: list[dict],
) -> dict:
    station_by_id = {item["station_id"]: item for item in stations}
    assignment_by_station = {item["station_id"]: item for item in assignments}

    station_points = []
    for station in stations:
        assignment = assignment_by_station.get(station["station_id"], {})
        station_points.append(
            {
                "station_id": station["station_id"],
                "name": station.get("name") or station["station_id"],
                "latitude": station.get("latitude"),
                "longitude": station.get("longitude"),
                "service_type": station.get("service_type"),
                "band_group": station.get("available_band_group"),
                "priority": station.get("priority") or 1,
                "frequency_mhz": assignment.get("assigned_frequency_mhz"),
                "risk_score": assignment.get("risk_score", 0),
                "risk_level": assignment.get("risk_level", "低"),
            }
        )

    risk_links = [
        {
            "station_a": item.get("station_a"),
            "station_b": item.get("station_b"),
            "frequency_a_mhz": item.get("frequency_a_mhz"),
            "frequency_b_mhz": item.get("frequency_b_mhz"),
            "risk_type": item.get("risk_type"),
            "severity": item.get("severity"),
            "score": item.get("score", 0),
            "reason": item.get("reason", ""),
        }
        for item in risks
        if item.get("station_a") and item.get("station_b")
    ]

    candidate_channels = generate_channels(rules)
    candidates_by_key: Counter[tuple[str, str]] = Counter((item.band_group, item.service_type) for item in candidate_channels)
    used_by_key: dict[tuple[str, str], set[float]] = defaultdict(set)
    assignments_by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for assignment in assignments:
        station = station_by_id.get(assignment["station_id"])
        if not station or assignment.get("assigned_frequency_mhz") is None:
            continue
        key = (station.get("available_band_group"), station.get("service_type"))
        used_by_key[key].add(round(float(assignment["assigned_frequency_mhz"]), 6))
        assignments_by_key[key].append(
            {
                "station_id": assignment["station_id"],
                "frequency_mhz": assignment["assigned_frequency_mhz"],
                "risk_level": assignment.get("risk_level", "低"),
            }
        )

    spectrum = []
    for key in sorted(set(candidates_by_key) | set(used_by_key)):
        band_group, service_type = key
        rule_matches = [rule for rule in rules if rule.get("band_group") == band_group and rule.get("service_type") == service_type]
        start = min((float(rule["start_mhz"]) for rule in rule_matches if rule.get("start_mhz") is not None), default=None)
        end = max((float(rule["end_mhz"]) for rule in rule_matches if rule.get("end_mhz") is not None), default=None)
        candidate_count = candidates_by_key.get(key, 0)
        used_count = len(used_by_key.get(key, set()))
        spectrum.append(
            {
                "band_group": band_group,
                "service_type": service_type,
                "start_mhz": start,
                "end_mhz": end,
                "candidate_channel_count": candidate_count,
                "used_channel_count": used_count,
                "utilization_pct": round(used_count / candidate_count * 100, 2) if candidate_count else 0,
                "assignments": sorted(assignments_by_key.get(key, []), key=lambda item: item["frequency_mhz"]),
            }
        )

    risk_distribution = Counter(item.get("severity", "低") for item in risks)
    station_risk_distribution = Counter(item.get("risk_level", "低") for item in assignments)
    service_distribution = Counter(item.get("service_type") or "未分类" for item in stations)
    frequency_values = [float(item["assigned_frequency_mhz"]) for item in assignments if item.get("assigned_frequency_mhz") is not None]

    return {
        "summary": {
            "station_count": len(stations),
            "assigned_count": len([item for item in assignments if item.get("assigned_frequency_mhz") is not None]),
            "risk_link_count": len(risk_links),
            "high_risk_link_count": risk_distribution.get("高", 0),
            "medium_risk_link_count": risk_distribution.get("中", 0),
            "frequency_min_mhz": min(frequency_values) if frequency_values else None,
            "frequency_max_mhz": max(frequency_values) if frequency_values else None,
            "band_count": len(spectrum),
        },
        "stations": station_points,
        "risk_links": sorted(risk_links, key=lambda item: item["score"], reverse=True),
        "spectrum": spectrum,
        "risk_distribution": [
            {"level": "高", "count": risk_distribution.get("高", 0)},
            {"level": "中", "count": risk_distribution.get("中", 0)},
            {"level": "低", "count": risk_distribution.get("低", 0)},
        ],
        "station_risk_distribution": [
            {"level": "高", "count": station_risk_distribution.get("高", 0)},
            {"level": "中", "count": station_risk_distribution.get("中", 0)},
            {"level": "低", "count": station_risk_distribution.get("低", 0)},
        ],
        "service_distribution": [{"service_type": key, "count": value} for key, value in sorted(service_distribution.items())],
    }

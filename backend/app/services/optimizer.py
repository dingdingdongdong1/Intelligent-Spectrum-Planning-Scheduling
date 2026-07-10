from __future__ import annotations

import time
from itertools import combinations

from ortools.sat.python import cp_model

from .channels import Channel, candidate_channels_for_station
from .geo import haversine_km


def solve_frequency_assignment(stations: list[dict], rules: list[dict], objective: str = "minimize_interference") -> dict:
    start = time.perf_counter()
    candidates_by_station = {station["station_id"]: candidate_channels_for_station(station, rules) for station in stations}
    empty = [station_id for station_id, candidates in candidates_by_station.items() if not candidates]
    if empty:
        return {
            "status": "infeasible",
            "message": "部分台站没有可用候选频点：" + "、".join(empty),
            "assignments": [],
            "elapsed_ms": int((time.perf_counter() - start) * 1000),
            "summary": {"empty_candidate_stations": empty},
        }

    model = cp_model.CpModel()
    variables: dict[tuple[str, float], cp_model.IntVar] = {}
    for station in stations:
        station_id = station["station_id"]
        for channel in candidates_by_station[station_id]:
            variables[(station_id, channel.frequency_mhz)] = model.NewBoolVar(f"x_{station_id}_{channel.frequency_mhz}")
        model.AddExactlyOne(variables[(station_id, channel.frequency_mhz)] for channel in candidates_by_station[station_id])

    penalties = []
    for station_a, station_b in combinations(stations, 2):
        pair_penalties = _build_pair_penalties(station_a, station_b, candidates_by_station, rules, objective)
        for freq_a, freq_b, penalty in pair_penalties:
            both = model.NewBoolVar(f"risk_{station_a['station_id']}_{station_b['station_id']}_{freq_a}_{freq_b}")
            model.AddBoolAnd([variables[(station_a["station_id"], freq_a)], variables[(station_b["station_id"], freq_b)]]).OnlyEnforceIf(both)
            model.AddBoolOr([variables[(station_a["station_id"], freq_a)].Not(), variables[(station_b["station_id"], freq_b)].Not()]).OnlyEnforceIf(both.Not())
            penalties.append(both * penalty)

    if objective == "minimize_frequency_count":
        unique_freqs = sorted({channel.frequency_mhz for candidates in candidates_by_station.values() for channel in candidates})
        used_vars = []
        for freq in unique_freqs:
            used = model.NewBoolVar(f"used_{freq}")
            related = [var for (station_id, item_freq), var in variables.items() if abs(item_freq - freq) <= 0.0005]
            model.AddMaxEquality(used, related)
            used_vars.append(used * 10)
        penalties.extend(used_vars)
    elif objective == "minimize_changes":
        for station in stations:
            existing = station.get("existing_frequency_mhz")
            if existing is None:
                continue
            for channel in candidates_by_station[station["station_id"]]:
                if abs(channel.frequency_mhz - float(existing)) > 0.0005:
                    penalties.append(variables[(station["station_id"], channel.frequency_mhz)] * max(1, int(station.get("priority") or 1)) * 3)

    model.Minimize(sum(penalties) if penalties else 0)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {
            "status": "infeasible",
            "message": "优化器未找到可行解，请放宽规则或增加候选频点",
            "assignments": [],
            "elapsed_ms": int((time.perf_counter() - start) * 1000),
            "summary": {"solver_status": solver.StatusName(status)},
        }

    assignments = []
    for station in stations:
        station_id = station["station_id"]
        selected: Channel | None = None
        for channel in candidates_by_station[station_id]:
            if solver.Value(variables[(station_id, channel.frequency_mhz)]) == 1:
                selected = channel
                break
        alternatives = [channel.frequency_mhz for channel in candidates_by_station[station_id] if selected and channel.frequency_mhz != selected.frequency_mhz][:5]
        assignments.append(
            {
                "station_id": station_id,
                "assigned_frequency_mhz": selected.frequency_mhz if selected else None,
                "alternative_frequencies_mhz": ",".join(f"{item:.6f}" for item in alternatives),
                "risk_score": 0,
                "risk_level": "低",
                "notes": "",
            }
        )

    return {
        "status": "success",
        "message": f"已生成 {len(assignments)} 个台站的频率规划方案",
        "assignments": assignments,
        "elapsed_ms": int((time.perf_counter() - start) * 1000),
        "summary": {
            "solver_status": solver.StatusName(status),
            "objective_value": solver.ObjectiveValue(),
            "station_count": len(stations),
            "candidate_count": sum(len(items) for items in candidates_by_station.values()),
        },
    }


def _build_pair_penalties(
    station_a: dict,
    station_b: dict,
    candidates_by_station: dict[str, list[Channel]],
    rules: list[dict],
    objective: str,
) -> list[tuple[float, float, int]]:
    distance = haversine_km(station_a.get("latitude"), station_a.get("longitude"), station_b.get("latitude"), station_b.get("longitude"))
    if distance is None:
        return []
    base_priority = max(1, int(station_a.get("priority") or 1), int(station_b.get("priority") or 1))
    priority_weight = base_priority * base_priority if objective == "priority_protection" else base_priority
    protection = max(
        float(station_a.get("protection_distance_km") or 0),
        float(station_b.get("protection_distance_km") or 0),
        _max_rule_value(station_a, rules, "protection_distance_km"),
        _max_rule_value(station_b, rules, "protection_distance_km"),
    )
    min_spacing = max(_max_rule_value(station_a, rules, "min_spacing_khz"), _max_rule_value(station_b, rules, "min_spacing_khz"))
    if distance >= max(protection, 0.001):
        return []

    penalties: list[tuple[float, float, int]] = []
    for channel_a in candidates_by_station[station_a["station_id"]]:
        for channel_b in candidates_by_station[station_b["station_id"]]:
            spacing_khz = abs(channel_a.frequency_mhz - channel_b.frequency_mhz) * 1000
            if spacing_khz <= 0.5:
                penalty = int((100 + (protection - distance) * 10) * priority_weight)
                penalties.append((channel_a.frequency_mhz, channel_b.frequency_mhz, penalty))
            elif spacing_khz < min_spacing:
                penalty = int((35 + (min_spacing - spacing_khz) / max(min_spacing, 1) * 40) * priority_weight)
                penalties.append((channel_a.frequency_mhz, channel_b.frequency_mhz, penalty))
    return penalties


def _max_rule_value(station: dict, rules: list[dict], field: str) -> float:
    values = [
        float(rule.get(field) or 0)
        for rule in rules
        if rule.get("band_group") == station.get("available_band_group") and rule.get("service_type") == station.get("service_type")
    ]
    return max(values) if values else 0

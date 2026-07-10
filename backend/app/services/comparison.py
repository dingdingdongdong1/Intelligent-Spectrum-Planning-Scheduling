from __future__ import annotations

import json

from sqlmodel import Session

from ..models import PlanningRun
from .planning import assignments_for_run, db_stations_to_dicts, risks_for_run, run_planning


COMPARISON_OBJECTIVES = [
    {
        "objective": "minimize_interference",
        "label": "干扰最低方案",
        "description": "优先降低同频、邻频和近距离高功率风险。",
    },
    {
        "objective": "minimize_frequency_count",
        "label": "频点数量最少方案",
        "description": "在风险可控前提下尽量减少使用的不同频点数量。",
    },
    {
        "objective": "minimize_changes",
        "label": "历史变更最少方案",
        "description": "有历史频点时尽量减少既有规划调整。",
    },
    {
        "objective": "priority_protection",
        "label": "高优先级保障方案",
        "description": "对高优先级台站的冲突施加更高惩罚。",
    },
]


def compare_plans(session: Session, project_id: int) -> dict:
    plans = []
    for item in COMPARISON_OBJECTIVES:
        run = run_planning(session, project_id, item["objective"])
        plans.append(_build_plan_summary(session, project_id, run, item))

    successful = [item for item in plans if item["status"] == "success"]
    recommended_run_id = None
    if successful:
        recommended_run_id = min(successful, key=_comparison_sort_key)["run_id"]
        for item in plans:
            item["recommended"] = item["run_id"] == recommended_run_id

    return {
        "plans": plans,
        "recommended_run_id": recommended_run_id,
        "objectives": COMPARISON_OBJECTIVES,
    }


def _build_plan_summary(session: Session, project_id: int, run: PlanningRun, objective_info: dict) -> dict:
    summary = json.loads(run.summary_json or "{}")
    assignments = assignments_for_run(session, project_id, run.id) if run.status == "success" else []
    risks = risks_for_run(session, project_id, run.id) if run.status == "success" else []
    station_by_id = {item["station_id"]: item for item in db_stations_to_dicts(session, project_id)}
    assigned_frequencies = {
        round(float(item["assigned_frequency_mhz"]), 6)
        for item in assignments
        if item.get("assigned_frequency_mhz") is not None
    }
    station_risks = [float(item.get("risk_score") or 0) for item in assignments]
    change_count = _count_frequency_changes(assignments, station_by_id)

    return {
        "run_id": run.id,
        "objective": objective_info["objective"],
        "label": objective_info["label"],
        "description": objective_info["description"],
        "status": run.status,
        "message": run.message,
        "recommended": False,
        "station_count": summary.get("station_count", len(assignments)),
        "assigned_count": len([item for item in assignments if item.get("assigned_frequency_mhz") is not None]),
        "used_frequency_count": len(assigned_frequencies),
        "risk_item_count": len(risks),
        "high_risk_count": summary.get("high_risk_count", 0),
        "medium_risk_count": summary.get("medium_risk_count", 0),
        "average_station_risk": summary.get("average_station_risk", 0),
        "max_station_risk": round(max(station_risks), 2) if station_risks else 0,
        "change_count": change_count,
        "objective_value": summary.get("objective_value"),
        "elapsed_ms": run.elapsed_ms,
    }


def _count_frequency_changes(assignments: list[dict], station_by_id: dict[str, dict]) -> int:
    count = 0
    for item in assignments:
        existing = station_by_id.get(item["station_id"], {}).get("existing_frequency_mhz")
        assigned = item.get("assigned_frequency_mhz")
        if existing is None or assigned is None:
            continue
        if abs(float(existing) - float(assigned)) > 0.0005:
            count += 1
    return count


def _comparison_sort_key(item: dict) -> tuple:
    return (
        int(item.get("high_risk_count") or 0),
        int(item.get("medium_risk_count") or 0),
        float(item.get("average_station_risk") or 0),
        int(item.get("used_frequency_count") or 0),
        int(item.get("change_count") or 0),
    )

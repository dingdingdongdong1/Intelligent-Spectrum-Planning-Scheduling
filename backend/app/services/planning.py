from __future__ import annotations

import json
from datetime import datetime

from sqlmodel import Session, delete, select

from ..models import Assignment, AuditLog, FrequencyRule, PlanningRun, Project, RiskItem, Station
from .interference import estimate_interference_risk
from .optimizer import solve_frequency_assignment


def db_stations_to_dicts(session: Session, project_id: int) -> list[dict]:
    stations = session.exec(select(Station).where(Station.project_id == project_id)).all()
    return [station.model_dump() for station in stations]


def db_rules_to_dicts(session: Session, project_id: int) -> list[dict]:
    rules = session.exec(select(FrequencyRule).where(FrequencyRule.project_id == project_id)).all()
    return [rule.model_dump() for rule in rules]


def replace_stations(session: Session, project_id: int, records: list[dict]) -> None:
    session.exec(delete(Station).where(Station.project_id == project_id))
    for record in records:
        session.add(Station(project_id=project_id, **record))
    _touch_project(session, project_id, "stations_uploaded")
    session.add(AuditLog(project_id=project_id, actor="user", action="upload_stations", detail=f"上传 {len(records)} 条台站记录"))
    session.commit()


def replace_rules(session: Session, project_id: int, records: list[dict]) -> None:
    session.exec(delete(FrequencyRule).where(FrequencyRule.project_id == project_id))
    for record in records:
        session.add(FrequencyRule(project_id=project_id, **record))
    _touch_project(session, project_id, "rules_uploaded")
    session.add(AuditLog(project_id=project_id, actor="user", action="upload_rules", detail=f"上传 {len(records)} 条规则记录"))
    session.commit()


def run_planning(session: Session, project_id: int, objective: str = "minimize_interference") -> PlanningRun:
    stations = db_stations_to_dicts(session, project_id)
    rules = db_rules_to_dicts(session, project_id)
    run = PlanningRun(project_id=project_id, objective=objective, status="running")
    session.add(run)
    session.commit()
    session.refresh(run)

    solve_result = solve_frequency_assignment(stations, rules, objective=objective)
    if solve_result["status"] != "success":
        run.status = solve_result["status"]
        run.message = solve_result["message"]
        run.elapsed_ms = solve_result["elapsed_ms"]
        run.summary_json = json.dumps(solve_result.get("summary", {}), ensure_ascii=False)
        session.add(AuditLog(project_id=project_id, run_id=run.id, action="plan_failed", detail=run.message))
        session.commit()
        return run

    risk_result = estimate_interference_risk(solve_result["assignments"], stations, rules)
    summary = {**solve_result["summary"], **risk_result["summary"]}

    session.exec(delete(Assignment).where(Assignment.project_id == project_id, Assignment.run_id == run.id))
    session.exec(delete(RiskItem).where(RiskItem.project_id == project_id, RiskItem.run_id == run.id))
    for item in risk_result["assignments"]:
        session.add(Assignment(project_id=project_id, run_id=run.id, **item))
    for item in risk_result["risk_items"]:
        session.add(RiskItem(project_id=project_id, run_id=run.id, **item))

    run.status = "success"
    run.message = solve_result["message"]
    run.elapsed_ms = solve_result["elapsed_ms"]
    run.summary_json = json.dumps(summary, ensure_ascii=False)
    _touch_project(session, project_id, "planned")
    session.add(AuditLog(project_id=project_id, run_id=run.id, action="plan_success", detail=run.message))
    session.commit()
    session.refresh(run)
    return run


def latest_successful_run(session: Session, project_id: int) -> PlanningRun | None:
    return session.exec(
        select(PlanningRun)
        .where(PlanningRun.project_id == project_id, PlanningRun.status == "success")
        .order_by(PlanningRun.id.desc())
    ).first()


def assignments_for_run(session: Session, project_id: int, run_id: int) -> list[dict]:
    rows = session.exec(select(Assignment).where(Assignment.project_id == project_id, Assignment.run_id == run_id)).all()
    return [row.model_dump() for row in rows]


def risks_for_run(session: Session, project_id: int, run_id: int) -> list[dict]:
    rows = session.exec(select(RiskItem).where(RiskItem.project_id == project_id, RiskItem.run_id == run_id)).all()
    return [row.model_dump() for row in rows]


def add_forbidden_frequencies(session: Session, project_id: int, frequencies: list[float]) -> int:
    rules = session.exec(select(FrequencyRule).where(FrequencyRule.project_id == project_id)).all()
    count = 0
    for freq in frequencies:
        for rule in rules:
            if rule.start_mhz <= freq <= rule.end_mhz:
                duplicate = rule.model_dump(exclude={"id"})
                duplicate["forbidden_frequency_mhz"] = freq
                session.add(FrequencyRule(**duplicate))
                count += 1
    if count:
        session.add(AuditLog(project_id=project_id, action="chat_add_forbidden_frequency", detail=f"追加禁用频点：{frequencies}"))
        session.commit()
    return count


def apply_priority_updates(session: Session, project_id: int, updates: list[dict]) -> int:
    if not updates:
        return 0
    stations = session.exec(select(Station).where(Station.project_id == project_id)).all()
    changed = 0
    for update in updates:
        for station in stations:
            matched = False
            if update.get("station_id") and station.station_id == update["station_id"]:
                matched = True
            if update.get("service_type_contains") and station.service_type and update["service_type_contains"] in station.service_type:
                matched = True
            if matched:
                station.priority = update.get("priority") or min(10, max(1, station.priority + 2))
                changed += 1
    if changed:
        session.add(AuditLog(project_id=project_id, action="chat_update_priority", detail=f"调整 {changed} 个台站优先级"))
        session.commit()
    return changed


def _touch_project(session: Session, project_id: int, status: str) -> None:
    project = session.get(Project, project_id)
    if not project:
        return
    project.status = status
    project.updated_at = datetime.utcnow()

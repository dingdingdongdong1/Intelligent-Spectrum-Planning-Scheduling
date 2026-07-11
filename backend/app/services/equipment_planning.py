from __future__ import annotations

import io
import json
import math
import re
import time
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass
from html import escape
from itertools import combinations

import pandas as pd
from sqlmodel import Session, delete, select

from ..models import (
    AuditLog,
    EquipmentAssignment,
    EquipmentGroup,
    PlanningRun,
    Project,
    SpectrumRule,
    TaskRiskItem,
    TaskUnit,
)
from .geo import haversine_km
from .sim_scenarios import SIM_SCENARIO_KEYS, sim_scenario_records
from .task_catalog import (
    BATCH_PERFORMANCE_SCALES,
    EQUIPMENT_LIBRARY,
    PARAMETRIC_SAMPLE_DEFAULTS,
    PLANNING_WEIGHT_TEMPLATES,
    SAMPLE_GENERATOR_PRESETS,
    TASK_OBJECTIVES,
    TASK_SCENARIOS,
    TRIAL_METRIC_KEYS,
    TRIAL_METRIC_LABELS,
)


@dataclass
class Segment:
    start: float
    end: float

    @property
    def width_mhz(self) -> float:
        return max(0.0, self.end - self.start)


def db_task_units_to_dicts(session: Session, project_id: int) -> list[dict]:
    rows = session.exec(select(TaskUnit).where(TaskUnit.project_id == project_id).order_by(TaskUnit.id)).all()
    return [row.model_dump() for row in rows]


def db_equipment_groups_to_dicts(session: Session, project_id: int) -> list[dict]:
    rows = session.exec(select(EquipmentGroup).where(EquipmentGroup.project_id == project_id).order_by(EquipmentGroup.id)).all()
    return [row.model_dump() for row in rows]


def db_spectrum_rules_to_dicts(session: Session, project_id: int) -> list[dict]:
    rows = session.exec(select(SpectrumRule).where(SpectrumRule.project_id == project_id).order_by(SpectrumRule.id)).all()
    return [row.model_dump() for row in rows]


def _replace_task_units_without_commit(session: Session, project_id: int, records: list[dict]) -> None:
    session.exec(delete(TaskUnit).where(TaskUnit.project_id == project_id))
    for record in records:
        session.add(TaskUnit(project_id=project_id, **record))
    _touch_project(session, project_id, "task_units_uploaded")
    session.add(AuditLog(project_id=project_id, actor="user", action="upload_task_units", detail=f"上传 {len(records)} 个任务单元"))


def replace_task_units(session: Session, project_id: int, records: list[dict]) -> None:
    _replace_task_units_without_commit(session, project_id, records)
    session.commit()


def _replace_equipment_groups_without_commit(session: Session, project_id: int, records: list[dict]) -> None:
    session.exec(delete(EquipmentGroup).where(EquipmentGroup.project_id == project_id))
    for record in records:
        session.add(EquipmentGroup(project_id=project_id, **record))
    _touch_project(session, project_id, "equipment_groups_uploaded")
    session.add(AuditLog(project_id=project_id, actor="user", action="upload_equipment_groups", detail=f"上传 {len(records)} 个装备组"))


def replace_equipment_groups(session: Session, project_id: int, records: list[dict]) -> None:
    _replace_equipment_groups_without_commit(session, project_id, records)
    session.commit()


def _replace_spectrum_rules_without_commit(session: Session, project_id: int, records: list[dict]) -> None:
    session.exec(delete(SpectrumRule).where(SpectrumRule.project_id == project_id))
    for record in records:
        session.add(SpectrumRule(project_id=project_id, **record))
    _touch_project(session, project_id, "spectrum_rules_uploaded")
    session.add(AuditLog(project_id=project_id, actor="user", action="upload_spectrum_rules", detail=f"上传 {len(records)} 条频段规则"))


def replace_spectrum_rules(session: Session, project_id: int, records: list[dict]) -> None:
    _replace_spectrum_rules_without_commit(session, project_id, records)
    session.commit()


def _replace_demo_scenario_records(
    session: Session,
    project_id: int,
    task_units: list[dict],
    equipment_groups: list[dict],
    spectrum_rules: list[dict],
    audit_log: AuditLog,
) -> None:
    try:
        _replace_task_units_without_commit(session, project_id, task_units)
        _replace_equipment_groups_without_commit(session, project_id, equipment_groups)
        _replace_spectrum_rules_without_commit(session, project_id, spectrum_rules)
        session.add(audit_log)
        session.commit()
    except Exception:
        session.rollback()
        raise


def task_scenario_library() -> list[dict]:
    return TASK_SCENARIOS


def generate_demo_scenario(session: Session, project_id: int, scenario: str = "baseline") -> dict:
    task_units, equipment_groups, spectrum_rules = demo_scenario_records(scenario)
    scenario_info = next((item for item in TASK_SCENARIOS if item["key"] == scenario), TASK_SCENARIOS[0])
    _replace_demo_scenario_records(
        session,
        project_id,
        task_units,
        equipment_groups,
        spectrum_rules,
        AuditLog(project_id=project_id, action="generate_demo_scenario", detail=f"生成{scenario_info['name']}仿真场景"),
    )
    return {
        "scenario": scenario_info,
        "task_unit_count": len(task_units),
        "equipment_group_count": len(equipment_groups),
        "equipment_sample_count": sum(item["count"] for item in equipment_groups),
        "spectrum_rule_count": len(spectrum_rules),
    }


def generate_parametric_demo_scenario(session: Session, project_id: int, payload: dict) -> dict:
    task_units, equipment_groups, spectrum_rules = parametric_demo_records(payload)
    _replace_demo_scenario_records(
        session,
        project_id,
        task_units,
        equipment_groups,
        spectrum_rules,
        AuditLog(
            project_id=project_id,
            action="generate_parametric_demo_scenario",
            detail=json.dumps(
                {
                    "unit_count": len(task_units),
                    "equipment_group_count": len(equipment_groups),
                    "equipment_sample_count": sum(item["count"] for item in equipment_groups),
                    "payload": payload,
                },
                ensure_ascii=False,
            ),
        ),
    )
    return {
        "scenario": {"key": "parametric", "name": "参数化仿真样例", "description": "按用户参数生成的任务单元和装备组。"},
        "task_unit_count": len(task_units),
        "equipment_group_count": len(equipment_groups),
        "equipment_sample_count": sum(item["count"] for item in equipment_groups),
        "spectrum_rule_count": len(spectrum_rules),
        "parameters": _normalized_parametric_payload(payload),
    }


def equipment_parameter_library() -> list[dict]:
    return EQUIPMENT_LIBRARY


def task_sample_catalog() -> dict:
    profiles = []
    for template in _scaled_unit_templates():
        equipment_types = sorted({item["equipment_type"] for item in template["groups"]})
        profiles.append(
            {
                "code": template["code"],
                "name": template["name"],
                "unit_type": template["unit_type"],
                "spectrum_relation": template["relation"],
                "preferred_band_groups": template["bands"],
                "default_priority": template["priority"],
                "min_satisfaction_ratio": template["ratio"],
                "equipment_group_count": len(template["groups"]),
                "equipment_types": equipment_types,
            }
        )
    return {
        "presets": SAMPLE_GENERATOR_PRESETS,
        "task_unit_profiles": profiles,
        "equipment_types": EQUIPMENT_LIBRARY,
        "batch_scales": BATCH_PERFORMANCE_SCALES,
        "weight_templates": PLANNING_WEIGHT_TEMPLATES,
        "parametric_defaults": PARAMETRIC_SAMPLE_DEFAULTS,
        "objective_count": len(TASK_OBJECTIVES),
    }


def list_spectrum_rules(session: Session, project_id: int) -> list[dict]:
    return db_spectrum_rules_to_dicts(session, project_id)


def create_spectrum_rule(session: Session, project_id: int, payload: dict) -> dict:
    data = _normalize_spectrum_rule_payload(payload)
    rule = SpectrumRule(project_id=project_id, raw_json=json.dumps(data, ensure_ascii=False), **data)
    session.add(rule)
    _touch_project(session, project_id, "task_constraints_updated")
    session.add(AuditLog(project_id=project_id, actor="user", action="create_spectrum_rule", detail=json.dumps(data, ensure_ascii=False)))
    session.commit()
    session.refresh(rule)
    return rule.model_dump()


def update_spectrum_rule(session: Session, project_id: int, row_id: int, payload: dict) -> dict | None:
    rule = session.get(SpectrumRule, row_id)
    if not rule or rule.project_id != project_id:
        return None
    data = _normalize_spectrum_rule_payload(payload)
    for key, value in data.items():
        setattr(rule, key, value)
    rule.raw_json = json.dumps(data, ensure_ascii=False)
    session.add(rule)
    _touch_project(session, project_id, "task_constraints_updated")
    session.add(AuditLog(project_id=project_id, actor="user", action="update_spectrum_rule", detail=json.dumps(data, ensure_ascii=False)))
    session.commit()
    session.refresh(rule)
    return rule.model_dump()


def delete_spectrum_rule(session: Session, project_id: int, row_id: int) -> bool:
    rule = session.get(SpectrumRule, row_id)
    if not rule or rule.project_id != project_id:
        return False
    session.delete(rule)
    _touch_project(session, project_id, "task_constraints_updated")
    session.add(AuditLog(project_id=project_id, actor="user", action="delete_spectrum_rule", detail=str(row_id)))
    session.commit()
    return True


def preview_task_replan(session: Session, project_id: int, payload: dict) -> dict:
    message = str(payload.get("message") or "")
    changes = _parse_replan_changes(session, project_id, payload)
    items = _replan_change_items(changes)
    result = {
        "objective": changes["objective"],
        "objective_label": _objective_label(changes["objective"]),
        "change_items": items,
        "changes": changes,
        "requires_confirmation": bool(items),
    }
    session.add(
        AuditLog(
            project_id=project_id,
            actor="user",
            action="task_replan_preview",
            detail=json.dumps(
                {
                    "objective": changes["objective"],
                    "change_count": len(items),
                    "message": message,
                    "changes": changes,
                    "trial_context": changes.get("trial_context", {}),
                },
                ensure_ascii=False,
                default=str,
            ),
        )
    )
    session.commit()
    return result


def preview_task_strategy_trials(session: Session, project_id: int, payload: dict) -> dict:
    changes = _parse_replan_changes(session, project_id, payload)
    task_units = db_task_units_to_dicts(session, project_id)
    equipment_groups = db_equipment_groups_to_dicts(session, project_id)
    spectrum_rules = db_spectrum_rules_to_dicts(session, project_id)
    base_run_id, base_summary = _replan_base_summary(session, project_id, changes.get("base_run_id"))
    locked_assignments = _locked_assignments_for_run(session, project_id, changes["locked_equipment_group_ids"], base_run_id)
    base_assignments = task_assignments_for_run(session, project_id, base_run_id) if base_run_id else []
    base_risks = task_risks_for_run(session, project_id, base_run_id) if base_run_id else []
    base_visualization = (
        build_task_visualization_data(
            task_units=task_units,
            equipment_groups=equipment_groups,
            spectrum_rules=spectrum_rules,
            assignments=base_assignments,
            risk_items=base_risks,
            summary=base_summary,
        )
        if base_run_id
        else {}
    )
    constraint_variants = _strategy_constraint_variants(changes, base_summary, base_assignments, base_visualization)
    result = build_task_strategy_trials(
        task_units,
        equipment_groups,
        spectrum_rules,
        changes,
        base_summary=base_summary,
        base_run_id=base_run_id,
        locked_assignments=locked_assignments,
        constraint_variants=constraint_variants,
    )
    session.add(
        AuditLog(
            project_id=project_id,
            run_id=base_run_id,
            actor="system",
            action="task_strategy_trials",
            detail=json.dumps(
                {
                    "base_run_id": base_run_id,
                    "candidate_count": len(result.get("candidates", [])),
                    "constraint_variant_count": len(constraint_variants),
                    "recommended_trial_id": result.get("recommended_trial_id"),
                    "decision_summary": {
                        "recommended_trial_id": (result.get("decision_summary") or {}).get("recommended_trial_id"),
                        "frontier_count": len(((result.get("decision_summary") or {}).get("pareto_frontier") or [])),
                    },
                    "message": payload.get("message", ""),
                },
                ensure_ascii=False,
            ),
        )
    )
    session.commit()
    return result


def _normalize_spectrum_rule_payload(payload: dict) -> dict:
    start = float(payload.get("start_mhz") or 0)
    end = float(payload.get("end_mhz") or 0)
    data = {
        "rule_id": str(payload.get("rule_id") or f"SR-USER-{int(time.time() * 1000)}"),
        "rule_type": str(payload.get("rule_type") or "可用"),
        "band_group": str(payload.get("band_group") or "").strip(),
        "spectrum_relation": str(payload.get("spectrum_relation") or payload.get("rule_type") or "可复用"),
        "start_mhz": min(start, end),
        "end_mhz": max(start, end),
        "channel_step_khz": float(payload.get("channel_step_khz") or 25),
        "max_bandwidth_khz": float(payload.get("max_bandwidth_khz") or 0),
        "max_power_w": float(payload.get("max_power_w") or 0),
        "guard_band_khz": float(payload.get("guard_band_khz") or 0),
        "compatible_unit_types": str(payload.get("compatible_unit_types") or ""),
        "compatible_equipment_types": str(payload.get("compatible_equipment_types") or ""),
        "reason": str(payload.get("reason") or ""),
        "source": str(payload.get("source") or "USER_UI"),
        "severity": str(payload.get("severity") or "中"),
    }
    return data


def _replan_change_items(changes: dict) -> list[dict]:
    items = []
    trial_context = changes.get("trial_context") or {}
    if trial_context:
        items.append(
            {
                "type": "采用试算候选",
                "target": trial_context.get("label") or trial_context.get("trial_id") or "-",
                "detail": _trial_context_change_detail(trial_context),
            }
        )
    if changes.get("reuse_strategy_from_run_id"):
        items.append(
            {
                "type": "复用历史策略",
                "target": f"#{changes.get('reuse_strategy_from_run_id')}",
                "detail": f"{_objective_label(changes.get('objective'))} / {changes.get('strategy_profile', 'balanced')}",
            }
        )
    if changes.get("objective_changed"):
        items.append({"type": "目标函数", "target": changes["objective"], "detail": _objective_label(changes["objective"])})
    for item in changes.get("available_ranges", []):
        items.append(
            {
                "type": "新增可用频段",
                "target": item.get("band_group") or "自动判断",
                "detail": f"{float(item.get('start_mhz') or 0):g}-{float(item.get('end_mhz') or 0):g} MHz",
            }
        )
    for item in changes.get("forbidden_ranges", []):
        items.append(
            {
                "type": "新增禁用频段",
                "target": item.get("band_group") or "自动判断",
                "detail": f"{float(item.get('start_mhz') or 0):g}-{float(item.get('end_mhz') or 0):g} MHz",
            }
        )
    for item in changes.get("priority_updates", []):
        items.append({"type": "调整优先级", "target": item.get("target", ""), "detail": f"设为 {item.get('priority')}"})
    for item in changes.get("satisfaction_updates", []):
        items.append({"type": "调整最低保障率", "target": item.get("task_unit_id", ""), "detail": f"{float(item.get('min_satisfaction_ratio') or 0) * 100:.0f}%"})
    for group_id in changes.get("locked_equipment_group_ids", []):
        items.append({"type": "锁定装备组", "target": group_id, "detail": "保持上一版指配资源"})
    for unit_id in changes.get("locked_task_unit_ids", []):
        items.append({"type": "锁定任务单元", "target": unit_id, "detail": "该任务单元下装备组保持上一版资源"})
    for band in changes.get("avoid_band_groups", []):
        items.append({"type": "避用频段池", "target": band, "detail": "仅在其他候选不足时使用"})
    for target, band in changes.get("forced_band_groups", {}).items():
        items.append({"type": "强制频段", "target": target, "detail": f"优先/强制使用 {band}"})
    for target in changes.get("required_full_targets", []):
        items.append({"type": "必须完全满足", "target": target, "detail": "若不能完全满足将标记高风险"})
    if changes.get("constraint_weights_changed"):
        items.append({"type": "约束权重", "target": changes.get("strategy_profile", "balanced"), "detail": "按当前权重模板参与重算"})
    return items


def validate_task_inputs(task_units: list[dict], equipment_groups: list[dict], spectrum_rules: list[dict]) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    task_ids = {item.get("task_unit_id") for item in task_units}
    available_bands = {item.get("band_group") for item in spectrum_rules if item.get("rule_type") == "可用"}

    if not task_units:
        errors.append("缺少任务单元数据")
    if not equipment_groups:
        errors.append("缺少装备组数据")
    if not any(item.get("rule_type") == "可用" for item in spectrum_rules):
        errors.append("缺少可用频段规则")

    for unit in task_units:
        if not unit.get("task_unit_id"):
            errors.append("任务单元存在空编号")
        if not unit.get("unit_type"):
            errors.append(f"任务单元 {unit.get('task_unit_id') or '-'} 缺少类型")
        ratio = float(unit.get("min_satisfaction_ratio") or 0)
        if ratio <= 0 or ratio > 1:
            warnings.append(f"任务单元 {unit.get('task_unit_id')} 的最低保障率建议在 0-1 之间")

    for group in equipment_groups:
        if group.get("task_unit_id") not in task_ids:
            errors.append(f"装备组 {group.get('equipment_group_id')} 关联了不存在的任务单元 {group.get('task_unit_id')}")
        if not group.get("preferred_band_group"):
            warnings.append(f"装备组 {group.get('equipment_group_id')} 未指定首选频段池")
        elif group.get("preferred_band_group") not in available_bands:
            warnings.append(f"装备组 {group.get('equipment_group_id')} 的首选频段池 {group.get('preferred_band_group')} 没有可用规则")
        if float(group.get("bandwidth_khz") or 0) <= 0:
            errors.append(f"装备组 {group.get('equipment_group_id')} 带宽必须大于 0")

    for rule in spectrum_rules:
        if float(rule.get("end_mhz") or 0) <= float(rule.get("start_mhz") or 0):
            errors.append(f"频段规则 {rule.get('rule_id')} 终止频率必须大于起始频率")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "task_unit_count": len(task_units),
            "equipment_group_count": len(equipment_groups),
            "equipment_sample_count": sum(int(item.get("count") or 0) for item in equipment_groups),
            "spectrum_rule_count": len(spectrum_rules),
            "available_band_count": len(available_bands),
        },
    }


def _scope_task_records(task_units: list[dict], equipment_groups: list[dict], constraints: dict | None) -> tuple[list[dict], list[dict]]:
    include_ids = {str(item).strip() for item in (constraints or {}).get("include_task_unit_ids", []) if str(item).strip()}
    if not include_ids:
        return task_units, equipment_groups
    scoped_units = [unit for unit in task_units if str(unit.get("task_unit_id") or "") in include_ids]
    valid_ids = {unit["task_unit_id"] for unit in scoped_units}
    scoped_groups = [group for group in equipment_groups if group.get("task_unit_id") in valid_ids]
    return scoped_units, scoped_groups


def _normalized_batch_context(value: object, task_unit_count: int, equipment_group_count: int) -> dict:
    if not isinstance(value, dict) or not value.get("batch_id"):
        return {}
    task_unit_ids = [str(item) for item in value.get("task_unit_ids", []) if str(item).strip()]
    return {
        "base_run_id": _normalized_run_id(value.get("base_run_id")),
        "batch_id": str(value.get("batch_id")),
        "batch_name": str(value.get("batch_name") or value.get("batch_id")),
        "batch_index": int(value.get("batch_index") or 0),
        "batch_count": int(value.get("batch_count") or 0),
        "task_unit_ids": task_unit_ids,
        "task_unit_count": task_unit_count,
        "equipment_group_count": equipment_group_count,
        "recommended_limits": value.get("recommended_limits") if isinstance(value.get("recommended_limits"), dict) else {},
        "cross_batch_risk_count": int(value.get("cross_batch_risk_count") or 0),
    }


def run_task_planning(session: Session, project_id: int, objective: str = "task_assurance", constraints: dict | None = None) -> PlanningRun:
    start = time.perf_counter()
    constraints = constraints or {}
    task_units = db_task_units_to_dicts(session, project_id)
    equipment_groups = db_equipment_groups_to_dicts(session, project_id)
    spectrum_rules = db_spectrum_rules_to_dicts(session, project_id)
    task_units, equipment_groups = _scope_task_records(task_units, equipment_groups, constraints)
    run = PlanningRun(project_id=project_id, objective=objective, status="running")
    session.add(run)
    session.commit()
    session.refresh(run)

    validation = validate_task_inputs(task_units, equipment_groups, spectrum_rules)
    if not validation["ok"]:
        run.status = "infeasible"
        run.message = "任务单元规划输入不完整：" + "；".join(validation["errors"][:5])
        run.elapsed_ms = int((time.perf_counter() - start) * 1000)
        run.summary_json = json.dumps(validation["summary"], ensure_ascii=False)
        session.add(AuditLog(project_id=project_id, run_id=run.id, action="task_plan_failed", detail=run.message))
        session.commit()
        return run

    result = solve_task_assignment(task_units, equipment_groups, spectrum_rules, objective, constraints=constraints)
    batch_context = _normalized_batch_context(constraints.get("batch_context"), len(task_units), len(equipment_groups))
    if batch_context:
        result["summary"]["batch_context"] = batch_context
        result["message"] = f"{batch_context['batch_name']} 子规划完成：{result['message']}"
    if isinstance(constraints.get("risk_closure_context"), dict):
        result["summary"]["risk_closure_context"] = constraints["risk_closure_context"]
    session.exec(delete(EquipmentAssignment).where(EquipmentAssignment.project_id == project_id, EquipmentAssignment.run_id == run.id))
    session.exec(delete(TaskRiskItem).where(TaskRiskItem.project_id == project_id, TaskRiskItem.run_id == run.id))
    for assignment in result["assignments"]:
        session.add(EquipmentAssignment(project_id=project_id, run_id=run.id, **assignment))
    for risk in result["risk_items"]:
        session.add(TaskRiskItem(project_id=project_id, run_id=run.id, **risk))

    run.status = "success"
    run.message = result["message"]
    run.elapsed_ms = int((time.perf_counter() - start) * 1000)
    run.summary_json = json.dumps(result["summary"], ensure_ascii=False)
    _touch_project(session, project_id, "task_planned")
    session.add(AuditLog(project_id=project_id, run_id=run.id, action="task_plan_success", detail=run.message))
    session.commit()
    session.refresh(run)
    return run


def execute_capacity_batch_planning(session: Session, project_id: int, payload: dict | None = None) -> dict:
    payload = payload or {}
    base_run = _task_run_for_assessment(session, project_id, _normalized_run_id(payload.get("base_run_id")) or None)
    if base_run is None:
        return {"ok": False, "message": "当前项目还没有可用于拆批的成功规划版本。", "runs": []}

    base_summary = _json_dict(base_run.summary_json or "{}")
    task_units = db_task_units_to_dicts(session, project_id)
    equipment_groups = db_equipment_groups_to_dicts(session, project_id)
    spectrum_rules = db_spectrum_rules_to_dicts(session, project_id)
    base_assignments = task_assignments_for_run(session, project_id, base_run.id)
    base_risks = task_risks_for_run(session, project_id, base_run.id)
    visualization = build_task_visualization_data(
        task_units=task_units,
        equipment_groups=equipment_groups,
        spectrum_rules=spectrum_rules,
        assignments=base_assignments,
        risk_items=base_risks,
        summary=base_summary,
    )
    scale_evidence = _agent_scale_evidence(task_versions_and_audit(session, project_id))
    batch_plan = _agent_capacity_batch_plan(visualization, base_risks, scale_evidence)
    if not batch_plan.get("available") or not batch_plan.get("batches"):
        session.add(
            AuditLog(
                project_id=project_id,
                run_id=base_run.id,
                actor="system",
                action="capacity_batch_execute_blocked",
                detail=json.dumps({"reason": batch_plan.get("reason"), "base_run_id": base_run.id}, ensure_ascii=False),
            )
        )
        session.commit()
        return {"ok": False, "message": batch_plan.get("reason") or "尚未形成可执行拆批预案。", "base_run_id": base_run.id, "batch_plan": batch_plan, "runs": []}

    requested_batch_ids = {str(item) for item in payload.get("batch_ids") or [] if str(item).strip()}
    selected_batches = [batch for batch in batch_plan["batches"] if not requested_batch_ids or batch.get("batch_id") in requested_batch_ids]
    if not selected_batches:
        return {"ok": False, "message": "没有匹配到需要执行的拆批批次。", "base_run_id": base_run.id, "batch_plan": batch_plan, "runs": []}

    objective = str(payload.get("objective") or base_summary.get("requested_objective") or base_run.objective or "task_assurance")
    weights = _normalize_constraint_weights(payload.get("constraint_weights") or base_summary.get("constraint_weights") or {})
    strategy_profile = str(payload.get("strategy_profile") or base_summary.get("strategy_profile") or "balanced")
    generated_runs = []
    for index, batch in enumerate(selected_batches, start=1):
        task_unit_ids = [str(item.get("task_unit_id")) for item in batch.get("task_units", []) if item.get("task_unit_id")]
        constraints = {
            "weights": weights,
            "strategy_profile": strategy_profile,
            "include_task_unit_ids": task_unit_ids,
            "batch_context": {
                "base_run_id": base_run.id,
                "batch_id": batch.get("batch_id"),
                "batch_name": batch.get("name") or f"批次 {index}",
                "batch_index": index,
                "batch_count": len(selected_batches),
                "task_unit_ids": task_unit_ids,
                "recommended_limits": batch_plan.get("recommended_limits") or {},
                "cross_batch_risk_count": batch_plan.get("cross_batch_risk_count") or 0,
            },
        }
        run = run_task_planning(session, project_id, objective, constraints=constraints)
        summary = _json_dict(run.summary_json or "{}")
        generated_runs.append(
            {
                "run_id": run.id,
                "batch_id": batch.get("batch_id"),
                "batch_name": batch.get("name"),
                "status": run.status,
                "message": run.message,
                "elapsed_ms": run.elapsed_ms,
                "task_unit_count": summary.get("task_unit_count", 0),
                "equipment_group_count": summary.get("equipment_group_count", 0),
                "equipment_sample_count": summary.get("equipment_sample_count", 0),
                "task_satisfaction_avg": summary.get("task_satisfaction_avg", 0),
                "full_group_count": summary.get("full_group_count", 0),
                "partial_group_count": summary.get("partial_group_count", 0),
                "unsatisfied_group_count": summary.get("unsatisfied_group_count", 0),
                "high_risk_count": summary.get("high_risk_count", 0),
                "medium_risk_count": summary.get("medium_risk_count", 0),
                "used_bandwidth_mhz": summary.get("used_bandwidth_mhz", 0),
                "quality_total": (summary.get("quality_scores") or {}).get("total", 0),
                "summary": summary,
            }
        )

    cross_batch_review = _capacity_batch_cross_batch_review(batch_plan, generated_runs)
    merged_plan = _capacity_batch_merged_plan(base_run.id, objective, strategy_profile, generated_runs, cross_batch_review)
    session.add(
        AuditLog(
            project_id=project_id,
            run_id=generated_runs[-1]["run_id"] if generated_runs else base_run.id,
            actor="system",
            action="capacity_batch_execute",
            detail=json.dumps(
                {
                    "base_run_id": base_run.id,
                    "batch_count": len(generated_runs),
                    "run_ids": [item["run_id"] for item in generated_runs],
                    "batch_plan": batch_plan,
                    "cross_batch_review": cross_batch_review,
                    "merged_plan": merged_plan,
                },
                ensure_ascii=False,
                default=str,
            ),
        )
    )
    session.commit()
    return {
        "ok": True,
        "message": f"已按容量边界生成 {len(generated_runs)} 个子规划版本。",
        "base_run_id": base_run.id,
        "objective": objective,
        "strategy_profile": strategy_profile,
        "batch_plan": batch_plan,
        "runs": generated_runs,
        "cross_batch_review": cross_batch_review,
        "merged_plan": merged_plan,
    }


def execute_capacity_batch_risk_closure(session: Session, project_id: int, payload: dict | None = None) -> dict:
    payload = payload or {}
    audit = session.exec(
        select(AuditLog)
        .where(AuditLog.project_id == project_id, AuditLog.action == "capacity_batch_execute")
        .order_by(AuditLog.id.desc())
    ).first()
    if audit is None:
        return {"ok": False, "message": "当前项目还没有可用于风险闭环的容量拆批方案。", "runs": []}
    audit_payload = _json_dict(audit.detail or "{}")
    base_run_id = _normalized_run_id(audit_payload.get("base_run_id"))
    base_run = _task_run_for_assessment(session, project_id, base_run_id or None)
    if base_run is None:
        return {"ok": False, "message": "容量拆批基线版本不存在，无法执行风险闭环。", "runs": []}

    base_summary = _json_dict(base_run.summary_json or "{}")
    batch_plan = audit_payload.get("batch_plan") if isinstance(audit_payload.get("batch_plan"), dict) else {}
    if not batch_plan:
        task_units = db_task_units_to_dicts(session, project_id)
        equipment_groups = db_equipment_groups_to_dicts(session, project_id)
        spectrum_rules = db_spectrum_rules_to_dicts(session, project_id)
        visualization = build_task_visualization_data(
            task_units=task_units,
            equipment_groups=equipment_groups,
            spectrum_rules=spectrum_rules,
            assignments=task_assignments_for_run(session, project_id, base_run.id),
            risk_items=task_risks_for_run(session, project_id, base_run.id),
            summary=base_summary,
        )
        batch_plan = _agent_capacity_batch_plan(visualization, task_risks_for_run(session, project_id, base_run.id), _agent_scale_evidence(task_versions_and_audit(session, project_id)))
    cross_links = list(batch_plan.get("cross_batch_links") or (audit_payload.get("cross_batch_review") or {}).get("top_links") or [])
    closure_rules = _capacity_closure_rules(cross_links, db_task_units_to_dicts(session, project_id))
    if not closure_rules.get("by_batch"):
        return {
            "ok": False,
            "message": "当前跨批风险缺少可转换为硬约束的频段信息，请先重新生成容量子规划版本。",
            "base_run_id": base_run.id,
            "batch_plan": batch_plan,
            "runs": [],
            "closure": closure_rules,
        }

    objective = str(payload.get("objective") or base_summary.get("requested_objective") or base_run.objective or "minimize_interference")
    weights = _normalize_constraint_weights(payload.get("constraint_weights") or {"risk": 98, "task": 70, "spectrum": 45, "priority": 75, "switching": 25, "reuse": 20})
    strategy_profile = str(payload.get("strategy_profile") or "risk_closure")
    selected_batches = list(batch_plan.get("batches") or [])
    generated_runs = []
    for index, batch in enumerate(selected_batches, start=1):
        batch_id = str(batch.get("batch_id") or f"B{index:02d}")
        task_unit_ids = [str(item.get("task_unit_id")) for item in batch.get("task_units", []) if item.get("task_unit_id")]
        constraints = {
            "weights": weights,
            "strategy_profile": strategy_profile,
            "include_task_unit_ids": task_unit_ids,
            "hard_avoid_band_groups_by_task_unit": closure_rules["by_batch"].get(batch_id, {}),
            "batch_context": {
                "base_run_id": base_run.id,
                "batch_id": batch_id,
                "batch_name": batch.get("name") or f"批次 {index}",
                "batch_index": index,
                "batch_count": len(selected_batches),
                "task_unit_ids": task_unit_ids,
                "recommended_limits": batch_plan.get("recommended_limits") or {},
                "cross_batch_risk_count": batch_plan.get("cross_batch_risk_count") or 0,
            },
            "risk_closure_context": {
                "source_audit_id": audit.id,
                "applied_rule_count": closure_rules.get("applied_rule_count", 0),
                "hard_avoid_band_groups_by_task_unit": closure_rules["by_batch"].get(batch_id, {}),
            },
        }
        run = run_task_planning(session, project_id, objective, constraints=constraints)
        summary = _json_dict(run.summary_json or "{}")
        generated_runs.append(
            {
                "run_id": run.id,
                "batch_id": batch_id,
                "batch_name": batch.get("name"),
                "status": run.status,
                "message": run.message,
                "elapsed_ms": run.elapsed_ms,
                "task_unit_count": summary.get("task_unit_count", 0),
                "equipment_group_count": summary.get("equipment_group_count", 0),
                "equipment_sample_count": summary.get("equipment_sample_count", 0),
                "task_satisfaction_avg": summary.get("task_satisfaction_avg", 0),
                "full_group_count": summary.get("full_group_count", 0),
                "partial_group_count": summary.get("partial_group_count", 0),
                "unsatisfied_group_count": summary.get("unsatisfied_group_count", 0),
                "high_risk_count": summary.get("high_risk_count", 0),
                "medium_risk_count": summary.get("medium_risk_count", 0),
                "used_bandwidth_mhz": summary.get("used_bandwidth_mhz", 0),
                "quality_total": (summary.get("quality_scores") or {}).get("total", 0),
                "summary": summary,
            }
        )

    before_review = _capacity_batch_cross_batch_review_from_links(cross_links, generated_runs)
    after_review = _capacity_batch_review_from_generated_runs(session, project_id, generated_runs)
    closure_after_links = _capacity_links_matching_original(
        cross_links,
        list(after_review.get("links") or after_review.get("top_links") or []),
    )
    closure_after_review = _capacity_batch_cross_batch_review_from_links(
        closure_after_links,
        generated_runs,
        list(after_review.get("guardrails") or []),
    )
    merged_plan = _capacity_batch_merged_plan(base_run.id, objective, strategy_profile, generated_runs, after_review)
    closure = {
        **closure_rules,
        "source_audit_id": audit.id,
        "before_cross_batch_risk_count": before_review.get("cross_batch_risk_count", 0),
        "after_cross_batch_risk_count": closure_after_review.get("cross_batch_risk_count", 0),
        "before_high_risk_count": before_review.get("high_risk_count", 0),
        "after_high_risk_count": closure_after_review.get("high_risk_count", 0),
        "before_medium_risk_count": before_review.get("medium_risk_count", 0),
        "after_medium_risk_count": closure_after_review.get("medium_risk_count", 0),
        "before_affected_batch_count": len(before_review.get("affected_batches") or []),
        "after_affected_batch_count": len(closure_after_review.get("affected_batches") or []),
        "delta_cross_batch_risk_count": int(before_review.get("cross_batch_risk_count") or 0) - int(closure_after_review.get("cross_batch_risk_count") or 0),
        "resolved_cross_batch_risk_count": max(0, int(before_review.get("cross_batch_risk_count") or 0) - int(closure_after_review.get("cross_batch_risk_count") or 0)),
        "improved": int(closure_after_review.get("cross_batch_risk_count") or 0) < int(before_review.get("cross_batch_risk_count") or 0),
        "summary": (
            f"已将 {closure_rules.get('applied_rule_count', 0)} 条跨批风险转换为硬避让约束；"
            f"原始跨批风险 {before_review.get('cross_batch_risk_count', 0)} -> {closure_after_review.get('cross_batch_risk_count', 0)}；"
            f"闭环后完整复核发现 {after_review.get('cross_batch_risk_count', 0)} 项跨批风险。"
        ),
    }
    session.add(
        AuditLog(
            project_id=project_id,
            run_id=generated_runs[-1]["run_id"] if generated_runs else base_run.id,
            actor="system",
            action="capacity_batch_risk_closure",
            detail=json.dumps(
                {
                    "base_run_id": base_run.id,
                    "source_audit_id": audit.id,
                    "batch_plan": batch_plan,
                    "run_ids": [item["run_id"] for item in generated_runs],
                    "closure": closure,
                    "cross_batch_review": after_review,
                    "merged_plan": merged_plan,
                },
                ensure_ascii=False,
                default=str,
            ),
        )
    )
    session.commit()
    return {
        "ok": True,
        "message": "已完成跨批风险闭环重算。",
        "base_run_id": base_run.id,
        "objective": objective,
        "strategy_profile": strategy_profile,
        "batch_plan": batch_plan,
        "runs": generated_runs,
        "cross_batch_review": after_review,
        "merged_plan": merged_plan,
        "closure": closure,
    }


def _capacity_closure_rules(cross_links: list[dict], task_units: list[dict]) -> dict:
    priority_by_unit = {str(item.get("task_unit_id") or ""): int(item.get("priority") or 1) for item in task_units}
    by_batch: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    rules = []
    skipped = 0
    for link in cross_links:
        source_unit = str(link.get("source_unit") or "")
        target_unit = str(link.get("target_unit") or "")
        source_batch = str(link.get("source_batch") or "")
        target_batch = str(link.get("target_batch") or "")
        source_band = str(link.get("source_band_group") or "")
        target_band = str(link.get("target_band_group") or "")
        if not source_unit or not target_unit or not source_batch or not target_batch:
            skipped += 1
            continue
        if not source_band and not target_band:
            skipped += 1
            continue
        source_priority = priority_by_unit.get(source_unit, 1)
        target_priority = priority_by_unit.get(target_unit, 1)
        if source_priority < target_priority:
            chosen_unit, chosen_batch, avoided_band = source_unit, source_batch, source_band or target_band
            protected_unit = target_unit
        else:
            chosen_unit, chosen_batch, avoided_band = target_unit, target_batch, target_band or source_band
            protected_unit = source_unit
        if not avoided_band:
            skipped += 1
            continue
        by_batch[chosen_batch][chosen_unit].add(avoided_band)
        rules.append(
            {
                "batch_id": chosen_batch,
                "task_unit_id": chosen_unit,
                "avoid_band_group": avoided_band,
                "protected_task_unit_id": protected_unit,
                "reason": link.get("reason") or "跨批复用距离不足",
            }
        )
    return {
        "applied_rule_count": len(rules),
        "skipped_link_count": skipped,
        "rules": rules,
        "by_batch": {batch: {unit: sorted(bands) for unit, bands in units.items()} for batch, units in by_batch.items()},
    }


def _capacity_batch_cross_batch_review(batch_plan: dict, generated_runs: list[dict]) -> dict:
    links = list(batch_plan.get("cross_batch_links") or [])
    return _capacity_batch_cross_batch_review_from_links(links, generated_runs, list(batch_plan.get("guardrails") or []))


def _capacity_batch_cross_batch_review_from_links(links: list[dict], generated_runs: list[dict], guardrails: list[str] | None = None) -> dict:
    severity_counter = Counter(str(item.get("severity") or "中") for item in links)
    high_count = int(severity_counter.get("高") or 0)
    medium_count = int(severity_counter.get("中") or 0)
    status = "需人工复核" if high_count or medium_count else "通过"
    affected_batches = sorted(
        {
            str(value)
            for item in links
            for value in (item.get("source_batch"), item.get("target_batch"))
            if value
        }
    )
    unsatisfied_total = sum(int(item.get("unsatisfied_group_count") or 0) for item in generated_runs)
    partial_total = sum(int(item.get("partial_group_count") or 0) for item in generated_runs)
    summary = (
        f"生成 {len(generated_runs)} 个子规划版本，跨批复用风险 {len(links)} 项；"
        f"子规划仍有未满足 {unsatisfied_total} 个、部分满足 {partial_total} 个装备组。"
    )
    if status == "通过":
        summary = f"生成 {len(generated_runs)} 个子规划版本，未发现需要单独提示的跨批复用风险。"
    return {
        "status": status,
        "summary": summary,
        "cross_batch_risk_count": len(links),
        "high_risk_count": high_count,
        "medium_risk_count": medium_count,
        "affected_batches": affected_batches,
        "top_links": links[:8],
        "links": links,
        "guardrails": list(guardrails or []),
        "recommendation": (
            "先复核跨批高/中风险链路，再把各批次报告合并为总方案。"
            if links
            else "可把子规划版本作为分批执行方案进入人工审核。"
        ),
    }


def _capacity_links_matching_original(original_links: list[dict], current_links: list[dict]) -> list[dict]:
    original_signatures = {_capacity_link_signature(link) for link in original_links}
    original_signatures.discard(())
    matched = []
    seen: set[tuple[tuple[str, str], tuple[str, str]]] = set()
    for link in current_links:
        signature = _capacity_link_signature(link)
        if not signature or signature not in original_signatures or signature in seen:
            continue
        matched.append(link)
        seen.add(signature)
    return matched


def _capacity_link_signature(link: dict) -> tuple[tuple[str, str], tuple[str, str]] | tuple[()]:
    source = (
        str(link.get("source_unit") or ""),
        str(link.get("source_equipment_group") or ""),
    )
    target = (
        str(link.get("target_unit") or ""),
        str(link.get("target_equipment_group") or ""),
    )
    if not any(source) or not any(target):
        return ()
    ordered = sorted([source, target])
    return (ordered[0], ordered[1])


def _capacity_batch_review_from_generated_runs(session: Session, project_id: int, generated_runs: list[dict]) -> dict:
    unit_to_batch: dict[str, str] = {}
    group_to_batch: dict[str, str] = {}
    all_assignments: list[dict] = []
    selected_unit_ids: set[str] = set()
    for item in generated_runs:
        run_id = _normalized_run_id(item.get("run_id"))
        batch_id = str(item.get("batch_id") or "")
        summary = item.get("summary") if isinstance(item.get("summary"), dict) else {}
        context = summary.get("batch_context") if isinstance(summary.get("batch_context"), dict) else {}
        for unit_id in context.get("task_unit_ids", []) or []:
            unit = str(unit_id)
            selected_unit_ids.add(unit)
            if batch_id:
                unit_to_batch[unit] = batch_id
        if not run_id:
            continue
        for assignment in task_assignments_for_run(session, project_id, run_id):
            if batch_id:
                group_to_batch[str(assignment.get("equipment_group_id") or "")] = batch_id
            all_assignments.append(assignment)

    task_units = [unit for unit in db_task_units_to_dicts(session, project_id) if str(unit.get("task_unit_id") or "") in selected_unit_ids]
    equipment_groups = [group for group in db_equipment_groups_to_dicts(session, project_id) if str(group.get("task_unit_id") or "") in selected_unit_ids]
    assignments_by_group = {str(item.get("equipment_group_id") or ""): item for item in all_assignments}
    links = []
    for risk in sorted(_reuse_risks(all_assignments, task_units, equipment_groups), key=lambda item: float(item.get("score") or 0), reverse=True):
        source = str(risk.get("task_unit_a") or "")
        target = str(risk.get("task_unit_b") or "")
        source_batch = unit_to_batch.get(source) or group_to_batch.get(str(risk.get("equipment_group_a") or ""))
        target_batch = unit_to_batch.get(target) or group_to_batch.get(str(risk.get("equipment_group_b") or ""))
        if not source_batch or not target_batch or source_batch == target_batch:
            continue
        source_assignment = assignments_by_group.get(str(risk.get("equipment_group_a") or ""))
        target_assignment = assignments_by_group.get(str(risk.get("equipment_group_b") or ""))
        links.append(
            {
                "source_unit": source,
                "target_unit": target,
                "source_equipment_group": risk.get("equipment_group_a"),
                "target_equipment_group": risk.get("equipment_group_b"),
                "source_batch": source_batch,
                "target_batch": target_batch,
                "source_band_group": (source_assignment or {}).get("band_group"),
                "target_band_group": (target_assignment or {}).get("band_group"),
                "source_resource": risk.get("resource_a"),
                "target_resource": risk.get("resource_b"),
                "severity": risk.get("severity"),
                "score": risk.get("score"),
                "reason": risk.get("reason") or risk.get("risk_type") or "跨批复用风险",
            }
        )
    return _capacity_batch_cross_batch_review_from_links(links, generated_runs)


def _capacity_batch_merged_plan(base_run_id: int, objective: str, strategy_profile: str, generated_runs: list[dict], cross_batch_review: dict) -> dict:
    successful_runs = [item for item in generated_runs if item.get("status") == "success"]
    task_unit_count = sum(int(item.get("task_unit_count") or 0) for item in successful_runs)
    equipment_group_count = sum(int(item.get("equipment_group_count") or 0) for item in successful_runs)
    equipment_sample_count = sum(int(item.get("equipment_sample_count") or 0) for item in successful_runs)
    full_group_count = sum(int(item.get("full_group_count") or 0) for item in successful_runs)
    partial_group_count = sum(int(item.get("partial_group_count") or 0) for item in successful_runs)
    unsatisfied_group_count = sum(int(item.get("unsatisfied_group_count") or 0) for item in successful_runs)
    high_risk_count = sum(int(item.get("high_risk_count") or 0) for item in successful_runs)
    medium_risk_count = sum(int(item.get("medium_risk_count") or 0) for item in successful_runs)
    used_bandwidth_mhz = round(sum(float(item.get("used_bandwidth_mhz") or 0) for item in successful_runs), 3)
    total_elapsed_ms = sum(int(item.get("elapsed_ms") or 0) for item in successful_runs)
    weighted_satisfaction = _weighted_average(
        [(float(item.get("task_satisfaction_avg") or 0), int(item.get("equipment_group_count") or 0)) for item in successful_runs]
    )
    weighted_quality = _weighted_average(
        [(float(item.get("quality_total") or 0), int(item.get("equipment_group_count") or 0)) for item in successful_runs]
    )
    cross_batch_risk_count = int(cross_batch_review.get("cross_batch_risk_count") or 0)
    cross_batch_high_count = int(cross_batch_review.get("high_risk_count") or 0)
    unresolved_count = unsatisfied_group_count + partial_group_count + high_risk_count + cross_batch_risk_count
    if not successful_runs:
        status = "blocked"
        status_label = "无可合并版本"
    elif unsatisfied_group_count or high_risk_count or cross_batch_high_count:
        status = "needs_review"
        status_label = "需复核后执行"
    elif partial_group_count or cross_batch_risk_count:
        status = "conditional"
        status_label = "有条件可执行"
    else:
        status = "ready"
        status_label = "可进入执行审核"

    batch_summaries = []
    for item in successful_runs:
        batch_summaries.append(
            {
                "run_id": item.get("run_id"),
                "batch_id": item.get("batch_id"),
                "batch_name": item.get("batch_name") or item.get("batch_id"),
                "task_unit_count": int(item.get("task_unit_count") or 0),
                "equipment_group_count": int(item.get("equipment_group_count") or 0),
                "task_satisfaction_avg": float(item.get("task_satisfaction_avg") or 0),
                "quality_total": float(item.get("quality_total") or 0),
                "unsatisfied_group_count": int(item.get("unsatisfied_group_count") or 0),
                "partial_group_count": int(item.get("partial_group_count") or 0),
                "high_risk_count": int(item.get("high_risk_count") or 0),
                "decision": _batch_execution_decision(item),
            }
        )

    audit_items = []
    if cross_batch_risk_count:
        audit_items.append(f"复核 {cross_batch_risk_count} 项跨批复用风险，优先处置跨批高/中风险链路。")
    if unsatisfied_group_count:
        audit_items.append(f"处置 {unsatisfied_group_count} 个未满足装备组，确认补充频段、降低需求或人工接受缺口。")
    if partial_group_count:
        audit_items.append(f"确认 {partial_group_count} 个部分满足装备组的降级保障是否可接受。")
    if high_risk_count:
        audit_items.append(f"复核 {high_risk_count} 项批内高风险，重点检查保护频率、复用距离和高功率近距离链路。")
    if not audit_items:
        audit_items.append("跨批和批内风险未触发阻断项，可进入人工终审。")

    summary = (
        f"合并 {len(successful_runs)} 个子规划版本，覆盖 {task_unit_count} 个任务单元、"
        f"{equipment_group_count} 个装备组；平均保障率 {round(weighted_satisfaction, 1)}%，"
        f"未满足 {unsatisfied_group_count} 个，跨批风险 {cross_batch_risk_count} 项。"
    )
    return {
        "status": status,
        "status_label": status_label,
        "summary": summary,
        "base_run_id": base_run_id,
        "objective": objective,
        "strategy_profile": strategy_profile,
        "run_ids": [item.get("run_id") for item in successful_runs],
        "batch_count": len(successful_runs),
        "task_unit_count": task_unit_count,
        "equipment_group_count": equipment_group_count,
        "equipment_sample_count": equipment_sample_count,
        "full_group_count": full_group_count,
        "partial_group_count": partial_group_count,
        "unsatisfied_group_count": unsatisfied_group_count,
        "high_risk_count": high_risk_count,
        "medium_risk_count": medium_risk_count,
        "cross_batch_risk_count": cross_batch_risk_count,
        "cross_batch_high_count": cross_batch_high_count,
        "used_bandwidth_mhz": used_bandwidth_mhz,
        "total_elapsed_ms": total_elapsed_ms,
        "task_satisfaction_avg": round(weighted_satisfaction, 1),
        "quality_total": round(weighted_quality, 1),
        "unresolved_count": unresolved_count,
        "batch_summaries": batch_summaries,
        "audit_items": audit_items,
        "recommendation": _capacity_batch_master_recommendation(status, cross_batch_risk_count, unsatisfied_group_count, partial_group_count, high_risk_count),
    }


def _weighted_average(values: list[tuple[float, int]]) -> float:
    total_weight = sum(max(0, weight) for _, weight in values)
    if total_weight <= 0:
        return 0.0
    return sum(value * max(0, weight) for value, weight in values) / total_weight


def _batch_execution_decision(item: dict) -> str:
    if int(item.get("unsatisfied_group_count") or 0) or int(item.get("high_risk_count") or 0):
        return "先复核"
    if int(item.get("partial_group_count") or 0) or int(item.get("medium_risk_count") or 0):
        return "有条件执行"
    return "可执行"


def _capacity_batch_master_recommendation(
    status: str,
    cross_batch_risk_count: int,
    unsatisfied_group_count: int,
    partial_group_count: int,
    high_risk_count: int,
) -> str:
    if status == "ready":
        return "总方案可进入人工终审，并以批次导出表作为执行附件。"
    if cross_batch_risk_count:
        return "先按跨批保护复核清单调整相邻批次频段或复用距离，再生成新的合并总方案。"
    if unsatisfied_group_count:
        return "优先为未满足装备组补充可用窗口或降低非关键装备需求，再重算对应批次。"
    if high_risk_count:
        return "先切换风险优先策略重算高风险批次，降低保护频率和近距离复用冲突。"
    if partial_group_count:
        return "部分满足项需要人工确认降级可接受性，确认后可作为有条件执行方案。"
    return "保持当前批次边界，进入人工复核。"


def latest_capacity_batch_export_xlsx(session: Session, project_id: int) -> tuple[bytes, int]:
    audit = session.exec(
        select(AuditLog)
        .where(AuditLog.project_id == project_id, AuditLog.action == "capacity_batch_execute")
        .order_by(AuditLog.id.desc())
    ).first()
    if audit is None:
        raise ValueError("当前项目还没有容量拆批总方案")
    payload = _json_dict(audit.detail or "{}")
    merged_plan = payload.get("merged_plan") if isinstance(payload.get("merged_plan"), dict) else {}
    cross_batch_review = payload.get("cross_batch_review") if isinstance(payload.get("cross_batch_review"), dict) else {}
    run_ids = [int(item) for item in payload.get("run_ids", []) if _normalized_run_id(item)]
    batch_lookup = {
        int(item.get("run_id")): item
        for item in merged_plan.get("batch_summaries", [])
        if _normalized_run_id(item.get("run_id"))
    }
    assignment_rows = []
    risk_rows = []
    for run_id in run_ids:
        batch = batch_lookup.get(run_id, {})
        batch_prefix = {
            "run_id": run_id,
            "batch_id": batch.get("batch_id", ""),
            "batch_name": batch.get("batch_name", ""),
        }
        for assignment in task_assignments_for_run(session, project_id, run_id):
            assignment_rows.append({**batch_prefix, **assignment})
        for risk in task_risks_for_run(session, project_id, run_id):
            risk_rows.append({**batch_prefix, **risk})

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame([merged_plan]).to_excel(writer, index=False, sheet_name="合并总方案")
        pd.DataFrame(merged_plan.get("batch_summaries", [])).to_excel(writer, index=False, sheet_name="子规划摘要")
        pd.DataFrame(cross_batch_review.get("top_links", [])).to_excel(writer, index=False, sheet_name="跨批风险")
        pd.DataFrame({"audit_item": merged_plan.get("audit_items", [])}).to_excel(writer, index=False, sheet_name="审核清单")
        pd.DataFrame(assignment_rows).to_excel(writer, index=False, sheet_name="合并指配明细")
        pd.DataFrame(risk_rows).to_excel(writer, index=False, sheet_name="批内风险明细")
        guardrails = cross_batch_review.get("guardrails", [])
        pd.DataFrame({"guardrail": guardrails}).to_excel(writer, index=False, sheet_name="保护边界")
    return buffer.getvalue(), int(audit.id or 0)


def latest_capacity_batch_closure_export_xlsx(session: Session, project_id: int) -> tuple[bytes, int]:
    audit = session.exec(
        select(AuditLog)
        .where(AuditLog.project_id == project_id, AuditLog.action == "capacity_batch_risk_closure")
        .order_by(AuditLog.id.desc())
    ).first()
    if audit is None:
        raise ValueError("当前项目还没有跨批风险闭环重算结果")
    payload = _json_dict(audit.detail or "{}")
    merged_plan = payload.get("merged_plan") if isinstance(payload.get("merged_plan"), dict) else {}
    closure = payload.get("closure") if isinstance(payload.get("closure"), dict) else {}
    cross_batch_review = payload.get("cross_batch_review") if isinstance(payload.get("cross_batch_review"), dict) else {}
    run_ids = [int(item) for item in payload.get("run_ids", []) if _normalized_run_id(item)]
    batch_lookup = {
        int(item.get("run_id")): item
        for item in merged_plan.get("batch_summaries", [])
        if _normalized_run_id(item.get("run_id"))
    }
    assignment_rows = []
    risk_rows = []
    for run_id in run_ids:
        batch = batch_lookup.get(run_id, {})
        batch_prefix = {
            "run_id": run_id,
            "batch_id": batch.get("batch_id", ""),
            "batch_name": batch.get("batch_name", ""),
        }
        for assignment in task_assignments_for_run(session, project_id, run_id):
            assignment_rows.append({**batch_prefix, **assignment})
        for risk in task_risks_for_run(session, project_id, run_id):
            risk_rows.append({**batch_prefix, **risk})
    comparison_rows = [
        {
            "metric": "跨批风险",
            "before": closure.get("before_cross_batch_risk_count", 0),
            "after": closure.get("after_cross_batch_risk_count", 0),
            "delta": closure.get("delta_cross_batch_risk_count", 0),
        },
        {
            "metric": "高风险",
            "before": closure.get("before_high_risk_count", 0),
            "after": closure.get("after_high_risk_count", 0),
            "delta": int(closure.get("before_high_risk_count") or 0) - int(closure.get("after_high_risk_count") or 0),
        },
        {
            "metric": "中风险",
            "before": closure.get("before_medium_risk_count", 0),
            "after": closure.get("after_medium_risk_count", 0),
            "delta": int(closure.get("before_medium_risk_count") or 0) - int(closure.get("after_medium_risk_count") or 0),
        },
        {
            "metric": "影响批次",
            "before": closure.get("before_affected_batch_count", 0),
            "after": closure.get("after_affected_batch_count", 0),
            "delta": int(closure.get("before_affected_batch_count") or 0) - int(closure.get("after_affected_batch_count") or 0),
        },
    ]

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame([closure]).to_excel(writer, index=False, sheet_name="闭环摘要")
        pd.DataFrame(comparison_rows).to_excel(writer, index=False, sheet_name="闭环前后对比")
        pd.DataFrame(closure.get("rules", [])).to_excel(writer, index=False, sheet_name="闭环硬约束")
        pd.DataFrame([merged_plan]).to_excel(writer, index=False, sheet_name="闭环合并总方案")
        pd.DataFrame(merged_plan.get("batch_summaries", [])).to_excel(writer, index=False, sheet_name="闭环子规划摘要")
        pd.DataFrame(cross_batch_review.get("top_links", [])).to_excel(writer, index=False, sheet_name="闭环后跨批风险")
        pd.DataFrame({"audit_item": merged_plan.get("audit_items", [])}).to_excel(writer, index=False, sheet_name="审核清单")
        pd.DataFrame(assignment_rows).to_excel(writer, index=False, sheet_name="闭环指配明细")
        pd.DataFrame(risk_rows).to_excel(writer, index=False, sheet_name="闭环批内风险")
        pd.DataFrame({"guardrail": cross_batch_review.get("guardrails", [])}).to_excel(writer, index=False, sheet_name="保护边界")
    return buffer.getvalue(), int(audit.id or 0)


def replan_task_project(session: Session, project_id: int, payload: dict) -> dict:
    changes = _parse_replan_changes(session, project_id, payload)
    applied = _apply_replan_changes(session, project_id, changes)
    locked_assignments = _locked_assignments_for_run(session, project_id, changes["locked_equipment_group_ids"], payload.get("base_run_id"))
    constraints = {
        "locked_assignments": locked_assignments,
        "avoid_band_groups": changes["avoid_band_groups"],
        "forced_band_groups": changes["forced_band_groups"],
        "required_full_targets": changes["required_full_targets"],
        "allow_low_priority_degrade": changes["allow_low_priority_degrade"],
        "weights": changes["constraint_weights"],
        "strategy_profile": changes["strategy_profile"],
    }
    run = run_task_planning(session, project_id, changes["objective"], constraints=constraints)
    summary = json.loads(run.summary_json or "{}")
    session.add(
        AuditLog(
            project_id=project_id,
            run_id=run.id,
            actor="user",
            action="task_replan",
            detail=json.dumps(
                {
                    "message": payload.get("message", ""),
                    "applied": applied,
                    "available_ranges": changes["available_ranges"],
                    "locked_equipment_group_ids": changes["locked_equipment_group_ids"],
                    "avoid_band_groups": changes["avoid_band_groups"],
                    "forced_band_groups": changes["forced_band_groups"],
                    "required_full_targets": changes["required_full_targets"],
                    "objective": changes["objective"],
                    "base_run_id": changes.get("base_run_id"),
                    "reuse_strategy_from_run_id": changes.get("reuse_strategy_from_run_id"),
                    "strategy_profile": changes.get("strategy_profile"),
                    "trial_context": changes.get("trial_context", {}),
                },
                ensure_ascii=False,
            ),
        )
    )
    session.commit()
    replan_effect = _replan_effect_for_run(session, project_id, run)
    explanation = _replan_explanation(applied, changes, summary)
    return {"reply": explanation, "run_id": run.id, "summary": summary, "replan_effect": replan_effect}


def compare_task_plans(session: Session, project_id: int) -> dict:
    plans = []
    for item in TASK_OBJECTIVES:
        run = run_task_planning(session, project_id, item["objective"])
        summary = json.loads(run.summary_json or "{}")
        plans.append(
            {
                "run_id": run.id,
                "objective": item["objective"],
                "label": item["label"],
                "description": item["description"],
                "status": run.status,
                "message": run.message,
                "task_satisfaction_avg": summary.get("task_satisfaction_avg", 0),
                "full_group_count": summary.get("full_group_count", 0),
                "partial_group_count": summary.get("partial_group_count", 0),
                "unsatisfied_group_count": summary.get("unsatisfied_group_count", 0),
                "used_bandwidth_mhz": summary.get("used_bandwidth_mhz", 0),
                "risk_item_count": summary.get("risk_item_count", 0),
                "high_risk_count": summary.get("high_risk_count", 0),
                "objective_score": _task_plan_score(summary),
                "score_explanation": summary.get("score_explanation", {}),
                "recommendation_reason": _recommendation_reason(summary, item["label"]),
                "recommended": False,
                "elapsed_ms": run.elapsed_ms,
            }
        )
    successful = [item for item in plans if item["status"] == "success"]
    recommended = min(successful, key=lambda item: item["objective_score"], default=None)
    if recommended:
        recommended["recommended"] = True
    return {
        "plans": plans,
        "recommended_run_id": recommended["run_id"] if recommended else None,
        "objectives": TASK_OBJECTIVES,
        "decision_table": _decision_table_from_plans(plans),
    }


def build_task_strategy_trials(
    task_units: list[dict],
    equipment_groups: list[dict],
    spectrum_rules: list[dict],
    changes: dict,
    base_summary: dict | None = None,
    base_run_id: int | None = None,
    locked_assignments: dict[str, dict] | None = None,
    constraint_variants: list[dict] | None = None,
) -> dict:
    base_summary = base_summary or {}
    candidates = []
    diagnostics = []
    variants = constraint_variants or [_base_constraint_variant()]
    for variant in variants:
        trial_changes = _merge_trial_changes(changes, variant.get("overrides") or {})
        trial_units, trial_groups, trial_rules = _apply_replan_changes_to_records(task_units, equipment_groups, spectrum_rules, trial_changes)
        validation = validate_task_inputs(trial_units, trial_groups, trial_rules)
        if not validation["ok"]:
            diagnostics.extend(f"{variant.get('label', '约束变体')}：{item}" for item in validation["errors"])
            continue
        for profile in _strategy_trial_profiles(trial_changes):
            constraints = {
                "locked_assignments": locked_assignments or {},
                "avoid_band_groups": trial_changes.get("avoid_band_groups", []),
                "forced_band_groups": trial_changes.get("forced_band_groups", {}),
                "required_full_targets": trial_changes.get("required_full_targets", []),
                "allow_low_priority_degrade": trial_changes.get("allow_low_priority_degrade", True),
                "weights": profile["constraint_weights"],
                "strategy_profile": profile["strategy_profile"],
            }
            result = solve_task_assignment(trial_units, trial_groups, trial_rules, profile["objective"], constraints=constraints)
            summary = result.get("summary", {})
            deltas = _trial_deltas(summary, base_summary)
            apply_payload = _trial_apply_payload(profile, trial_changes, base_run_id, variant)
            objective_score = _task_plan_score(summary)
            recommendation_score = _trial_recommendation_score(summary, deltas, variant)
            trial_id = f"{profile['trial_id']}__{variant.get('variant_id', 'current_constraints')}"
            candidates.append(
                {
                    "trial_id": trial_id,
                    "label": profile["label"] if variant.get("variant_id") == "current_constraints" else f"{profile['label']} + {variant.get('label')}",
                    "objective": profile["objective"],
                    "objective_label": _objective_label(profile["objective"]),
                    "strategy_profile": profile["strategy_profile"],
                    "constraint_variant": variant.get("variant_id", "current_constraints"),
                    "constraint_label": variant.get("label", "当前约束"),
                    "constraint_changes": variant.get("change_items", []),
                    "constraint_weights": profile["constraint_weights"],
                    "reason": _trial_reason(profile, variant),
                    "tradeoff": _trial_tradeoff(profile, variant),
                    "status": result.get("status", "success"),
                    "message": result.get("message", ""),
                    "task_satisfaction_avg": summary.get("task_satisfaction_avg", 0),
                    "quality_total": _summary_quality(summary),
                    "high_risk_count": int(summary.get("high_risk_count") or 0),
                    "medium_risk_count": int(summary.get("medium_risk_count") or 0),
                    "partial_group_count": int(summary.get("partial_group_count") or 0),
                    "unsatisfied_group_count": int(summary.get("unsatisfied_group_count") or 0),
                    "used_bandwidth_mhz": float(summary.get("used_bandwidth_mhz") or 0),
                    "objective_score": objective_score,
                    "recommendation_score": recommendation_score,
                    "deltas": deltas,
                    "decision": _trial_decision(summary, deltas),
                    "suggested_message": f"采用“{profile['label']} + {variant.get('label', '当前约束')}”联合试算方案重新规划。",
                    "apply_payload": apply_payload,
                }
            )

    if not candidates:
        return {
            "ok": False,
            "base_run_id": base_run_id,
            "base_metrics": _trial_metrics(base_summary),
            "recommended_trial_id": None,
            "candidates": [],
            "decision_summary": _strategy_trial_decision_summary([], base_summary),
            "diagnostics": diagnostics or ["没有生成可用试算候选。"],
        }

    candidates = sorted(candidates, key=lambda item: (-float(item.get("recommendation_score") or 0), float(item.get("objective_score") or 0), item["trial_id"]))
    for item in candidates:
        item["recommended"] = False
    if candidates:
        candidates[0]["recommended"] = True
    return {
        "ok": True,
        "base_run_id": base_run_id,
        "base_metrics": _trial_metrics(base_summary),
        "recommended_trial_id": candidates[0]["trial_id"] if candidates else None,
        "candidates": candidates,
        "decision_summary": _strategy_trial_decision_summary(candidates, base_summary),
        "diagnostics": _strategy_trial_diagnostics(candidates, base_summary) + diagnostics[:3],
    }


def _strategy_trial_decision_summary(candidates: list[dict], base_summary: dict) -> dict:
    base_metrics = _trial_metrics(base_summary)
    if not candidates:
        return {
            "recommended_trial_id": None,
            "baseline": base_metrics,
            "role_picks": [],
            "pareto_frontier": [],
            "tradeoff_notes": ["尚未形成可用候选，建议先放宽频段、保护距离或任务满足率约束。"],
            "adoption_guardrails": ["没有候选方案时不得直接重规划，应先补齐可用资源或降低不可满足约束。"],
        }

    recommended = next((item for item in candidates if item.get("recommended")), candidates[0])
    risk_pick = min(
        candidates,
        key=lambda item: (
            int(item.get("high_risk_count") or 0),
            int(item.get("medium_risk_count") or 0),
            int(item.get("unsatisfied_group_count") or 0),
            -float(item.get("quality_total") or 0),
        ),
    )
    satisfaction_pick = max(
        candidates,
        key=lambda item: (
            float(item.get("task_satisfaction_avg") or 0),
            -int(item.get("unsatisfied_group_count") or 0),
            float(item.get("quality_total") or 0),
        ),
    )
    bandwidth_pick = min(
        candidates,
        key=lambda item: (
            float(item.get("used_bandwidth_mhz") or 0),
            int(item.get("unsatisfied_group_count") or 0),
            int(item.get("high_risk_count") or 0),
        ),
    )
    quality_pick = max(candidates, key=lambda item: (float(item.get("quality_total") or 0), float(item.get("recommendation_score") or 0)))

    role_picks = [
        _strategy_trial_role_pick("recommended", "综合推荐", recommended, "recommendation_score"),
        _strategy_trial_role_pick("risk_minimum", "风险最低", risk_pick, "high_risk_count"),
        _strategy_trial_role_pick("satisfaction_maximum", "保障最高", satisfaction_pick, "task_satisfaction_avg"),
        _strategy_trial_role_pick("bandwidth_minimum", "占频最少", bandwidth_pick, "used_bandwidth_mhz"),
        _strategy_trial_role_pick("quality_maximum", "质量最高", quality_pick, "quality_total"),
    ]
    frontier = _strategy_trial_pareto_frontier(candidates)
    return {
        "recommended_trial_id": recommended.get("trial_id"),
        "baseline": base_metrics,
        "role_picks": role_picks,
        "pareto_frontier": [_strategy_trial_compact(item) for item in frontier[:8]],
        "tradeoff_notes": _strategy_trial_tradeoff_notes(recommended, risk_pick, satisfaction_pick, bandwidth_pick),
        "adoption_guardrails": _strategy_trial_adoption_guardrails(recommended, base_metrics),
    }


def _strategy_trial_role_pick(role: str, label: str, trial: dict, metric_key: str) -> dict:
    return {
        "role": role,
        "label": label,
        "trial_id": trial.get("trial_id"),
        "trial_label": trial.get("label"),
        "objective": trial.get("objective"),
        "objective_label": trial.get("objective_label"),
        "strategy_profile": trial.get("strategy_profile"),
        "constraint_variant": trial.get("constraint_variant"),
        "constraint_label": trial.get("constraint_label"),
        "metric_key": metric_key,
        "metric_value": trial.get(metric_key),
        "deltas": trial.get("deltas") or {},
        "decision": trial.get("decision"),
    }


def _strategy_trial_compact(trial: dict) -> dict:
    return {
        "trial_id": trial.get("trial_id"),
        "label": trial.get("label"),
        "objective_label": trial.get("objective_label"),
        "constraint_label": trial.get("constraint_label"),
        "task_satisfaction_avg": trial.get("task_satisfaction_avg"),
        "quality_total": trial.get("quality_total"),
        "high_risk_count": trial.get("high_risk_count"),
        "unsatisfied_group_count": trial.get("unsatisfied_group_count"),
        "used_bandwidth_mhz": trial.get("used_bandwidth_mhz"),
        "recommendation_score": trial.get("recommendation_score"),
    }


def _strategy_trial_pareto_frontier(candidates: list[dict]) -> list[dict]:
    frontier = []
    for candidate in candidates:
        dominated = any(_strategy_trial_dominates(other, candidate) for other in candidates if other is not candidate)
        if not dominated:
            frontier.append(candidate)
    return sorted(frontier, key=lambda item: (-float(item.get("recommendation_score") or 0), item.get("trial_id") or ""))


def _strategy_trial_dominates(left: dict, right: dict) -> bool:
    left_values = {
        "quality_total": float(left.get("quality_total") or 0),
        "task_satisfaction_avg": float(left.get("task_satisfaction_avg") or 0),
        "high_risk_count": int(left.get("high_risk_count") or 0),
        "unsatisfied_group_count": int(left.get("unsatisfied_group_count") or 0),
        "used_bandwidth_mhz": float(left.get("used_bandwidth_mhz") or 0),
    }
    right_values = {
        "quality_total": float(right.get("quality_total") or 0),
        "task_satisfaction_avg": float(right.get("task_satisfaction_avg") or 0),
        "high_risk_count": int(right.get("high_risk_count") or 0),
        "unsatisfied_group_count": int(right.get("unsatisfied_group_count") or 0),
        "used_bandwidth_mhz": float(right.get("used_bandwidth_mhz") or 0),
    }
    better_or_equal = (
        left_values["quality_total"] >= right_values["quality_total"]
        and left_values["task_satisfaction_avg"] >= right_values["task_satisfaction_avg"]
        and left_values["high_risk_count"] <= right_values["high_risk_count"]
        and left_values["unsatisfied_group_count"] <= right_values["unsatisfied_group_count"]
        and left_values["used_bandwidth_mhz"] <= right_values["used_bandwidth_mhz"]
    )
    strictly_better = (
        left_values["quality_total"] > right_values["quality_total"]
        or left_values["task_satisfaction_avg"] > right_values["task_satisfaction_avg"]
        or left_values["high_risk_count"] < right_values["high_risk_count"]
        or left_values["unsatisfied_group_count"] < right_values["unsatisfied_group_count"]
        or left_values["used_bandwidth_mhz"] < right_values["used_bandwidth_mhz"]
    )
    return better_or_equal and strictly_better


def _strategy_trial_tradeoff_notes(recommended: dict, risk_pick: dict, satisfaction_pick: dict, bandwidth_pick: dict) -> list[str]:
    deltas = recommended.get("deltas") or {}
    notes = [
        (
            f"推荐方案 {recommended.get('label')}：质量 {float(deltas.get('quality_total') or 0):+g}，"
            f"保障率 {float(deltas.get('task_satisfaction_avg') or 0):+g}% ，"
            f"高风险 {int(deltas.get('high_risk_count') or 0):+d}，"
            f"占频 {float(deltas.get('used_bandwidth_mhz') or 0):+g} MHz。"
        )
    ]
    if risk_pick.get("trial_id") != recommended.get("trial_id"):
        notes.append(
            f"若首要目标是压低风险，可比较 {risk_pick.get('label')}；该方案高风险 {risk_pick.get('high_risk_count')} 项，"
            f"平均保障率 {risk_pick.get('task_satisfaction_avg')}%。"
        )
    if satisfaction_pick.get("trial_id") != recommended.get("trial_id"):
        notes.append(
            f"若首要目标是任务保障，可比较 {satisfaction_pick.get('label')}；该方案平均保障率 {satisfaction_pick.get('task_satisfaction_avg')}%。"
        )
    if bandwidth_pick.get("trial_id") != recommended.get("trial_id"):
        notes.append(
            f"若首要目标是节省频谱，可比较 {bandwidth_pick.get('label')}；该方案占用 {bandwidth_pick.get('used_bandwidth_mhz')} MHz。"
        )
    return notes[:4]


def _strategy_trial_adoption_guardrails(recommended: dict, base_metrics: dict) -> list[str]:
    guardrails = []
    deltas = recommended.get("deltas") or {}
    if int(recommended.get("unsatisfied_group_count") or 0) > 0:
        guardrails.append("推荐候选仍存在未满足装备组，正式采用前应补充频段或调整最低满足率。")
    if int(deltas.get("high_risk_count") or 0) > 0:
        guardrails.append("推荐候选高风险数量高于基线，必须复核保护距离和高功率近距离链路。")
    if float(deltas.get("used_bandwidth_mhz") or 0) > 0:
        guardrails.append("推荐候选占频增加，需确认该增量符合任务优先级和频谱资源边界。")
    if recommended.get("constraint_variant") != "current_constraints":
        guardrails.append("推荐候选使用了约束变体，正式执行前需要确认新增频段、强制满足或避让条件。")
    if float(recommended.get("task_satisfaction_avg") or 0) < float(base_metrics.get("task_satisfaction_avg") or 0):
        guardrails.append("推荐候选保障率低于基线，除非风险或占频收益明确，否则不建议直接采用。")
    if not guardrails:
        guardrails.append("推荐候选未触发主要护栏，可进入人工复核并一键重规划。")
    return guardrails[:4]


def _base_constraint_variant() -> dict:
    return {
        "variant_id": "current_constraints",
        "label": "当前约束",
        "overrides": {},
        "change_items": ["沿用当前重规划约束"],
        "rank_bonus": 0.0,
    }


def _strategy_constraint_variants(changes: dict, base_summary: dict, base_assignments: list[dict], base_visualization: dict) -> list[dict]:
    variants = [_base_constraint_variant()]
    shortfalls = [item for item in base_assignments if item.get("status") != "完全满足"]
    shortfalls = sorted(
        shortfalls,
        key=lambda row: (
            int(row.get("priority") or 0),
            int(row.get("requested_channels") or 0) - int(row.get("assigned_channels") or 0),
            int(row.get("requested_channels") or 0),
        ),
        reverse=True,
    )
    target_ids = _unique_keep_order([str(item.get("equipment_group_id") or "") for item in shortfalls[:3] if item.get("equipment_group_id")])
    supplements = _supplement_ranges_for_unmet_assignments(shortfalls, base_visualization, limit=2) if shortfalls and base_visualization else []
    if target_ids:
        variants.append(
            {
                "variant_id": "required_full_shortfalls",
                "label": "必须满足短板",
                "overrides": {"required_full_targets": target_ids, "allow_low_priority_degrade": False},
                "change_items": [f"要求 {', '.join(target_ids)} 完全满足", "禁止低优先级自动降级"],
                "rank_bonus": 6.0,
            }
        )
    if supplements:
        variants.append(
            {
                "variant_id": "supplement_shortfall_band",
                "label": "补充短板频段",
                "overrides": {"available_ranges": supplements},
                "change_items": [_trial_range_change_text(item, "补充") for item in supplements],
                "rank_bonus": 8.0,
            }
        )
    bottlenecks = ((base_summary.get("bottleneck_analysis") or {}).get("band_bottlenecks") or [])
    top_bottleneck = next((item for item in bottlenecks if item.get("band_group")), None)
    if top_bottleneck:
        band_group = str(top_bottleneck.get("band_group"))
        variants.append(
            {
                "variant_id": "avoid_bottleneck_band",
                "label": "避用瓶颈频段",
                "overrides": {"avoid_band_groups": [band_group]},
                "change_items": [f"避用瓶颈频段 {band_group}"],
                "rank_bonus": 3.0,
            }
        )
    if target_ids and supplements:
        variants.append(
            {
                "variant_id": "recover_with_supplement",
                "label": "补频并强保短板",
                "overrides": {
                    "required_full_targets": target_ids,
                    "available_ranges": supplements,
                    "allow_low_priority_degrade": False,
                    "constraint_weights": {"task": 95, "risk": 75, "spectrum": 45, "priority": 85, "switching": 25, "reuse": 30},
                    "objective": "task_assurance",
                    "strategy_profile": "task_guard",
                },
                "change_items": [f"要求 {', '.join(target_ids)} 完全满足", *[_trial_range_change_text(item, "补充") for item in supplements]],
                "rank_bonus": 10.0,
            }
        )
    return _dedupe_constraint_variants(variants, changes)


def _merge_trial_changes(changes: dict, overrides: dict) -> dict:
    merged = {
        "base_run_id": changes.get("base_run_id"),
        "base_objective": changes.get("base_objective"),
        "reuse_strategy_from_run_id": changes.get("reuse_strategy_from_run_id"),
        "objective": overrides.get("objective", changes.get("objective")),
        "base_strategy_profile": changes.get("base_strategy_profile"),
        "strategy_profile": overrides.get("strategy_profile", changes.get("strategy_profile")),
        "objective_changed": changes.get("objective_changed", False) or ("objective" in overrides),
        "constraint_weights_changed": changes.get("constraint_weights_changed", False) or ("constraint_weights" in overrides),
        "allow_low_priority_degrade": overrides.get("allow_low_priority_degrade", changes.get("allow_low_priority_degrade", True)),
        "constraint_weights": _normalize_constraint_weights(overrides.get("constraint_weights", changes.get("constraint_weights") or {})),
        "forced_band_groups": dict(changes.get("forced_band_groups", {}) or {}),
    }
    if overrides.get("forced_band_groups"):
        merged["forced_band_groups"].update(dict(overrides.get("forced_band_groups") or {}))
    for key in (
        "priority_updates",
        "satisfaction_updates",
    ):
        merged[key] = [dict(item) for item in changes.get(key, [])] + [dict(item) for item in overrides.get(key, [])]
    for key in ("available_ranges", "forbidden_ranges"):
        merged[key] = _unique_frequency_ranges([dict(item) for item in changes.get(key, [])] + [dict(item) for item in overrides.get(key, [])])
    for key in (
        "locked_equipment_group_ids",
        "locked_task_unit_ids",
        "avoid_band_groups",
        "required_full_targets",
    ):
        merged[key] = _unique_keep_order([str(item) for item in changes.get(key, [])] + [str(item) for item in overrides.get(key, [])])
    return merged


def _dedupe_constraint_variants(variants: list[dict], changes: dict) -> list[dict]:
    result = []
    seen = set()
    base_signature = _constraint_variant_signature(_merge_trial_changes(changes, {}))
    for variant in variants:
        merged_changes = _merge_trial_changes(changes, variant.get("overrides") or {})
        signature = _constraint_variant_signature(merged_changes)
        if signature in seen:
            continue
        seen.add(signature)
        if signature == base_signature and variant.get("variant_id") != "current_constraints":
            continue
        result.append(variant)
    return result or [_base_constraint_variant()]


def _constraint_variant_signature(changes: dict) -> tuple:
    return (
        tuple((item.get("band_group") or "", item.get("start_mhz"), item.get("end_mhz")) for item in changes.get("available_ranges", [])),
        tuple((item.get("band_group") or "", item.get("start_mhz"), item.get("end_mhz")) for item in changes.get("forbidden_ranges", [])),
        tuple(changes.get("avoid_band_groups", [])),
        tuple(changes.get("required_full_targets", [])),
        bool(changes.get("allow_low_priority_degrade", True)),
        tuple(sorted((changes.get("forced_band_groups") or {}).items())),
        changes.get("objective"),
        changes.get("strategy_profile"),
        tuple(sorted((changes.get("constraint_weights") or {}).items())),
    )


def _trial_range_change_text(item: dict, prefix: str) -> str:
    return f"{prefix} {item.get('band_group') or '备用'} {float(item.get('start_mhz') or 0):g}-{float(item.get('end_mhz') or 0):g} MHz"


def _strategy_trial_profiles(changes: dict) -> list[dict]:
    requested_weights = _normalize_constraint_weights(changes.get("constraint_weights") or {})
    profiles = [
        {
            "trial_id": "current_request",
            "label": "当前请求策略",
            "objective": changes.get("objective") or "task_assurance",
            "strategy_profile": changes.get("strategy_profile") or "balanced",
            "constraint_weights": requested_weights,
            "reason": "按当前重规划输入、目标函数和权重直接试算。",
            "tradeoff": "可验证当前输入本身是否带来收益。",
        },
        {
            "trial_id": "risk_first",
            "label": "风险优先",
            "objective": "minimize_interference",
            "strategy_profile": "risk_first",
            "constraint_weights": {"risk": 95, "task": 65, "spectrum": 45, "priority": 70, "switching": 25, "reuse": 25},
            "reason": "优先压降保护频率靠近、邻频和复用距离不足风险。",
            "tradeoff": "可能占用更多频谱或降低复用效率。",
        },
        {
            "trial_id": "spectrum_saving",
            "label": "频谱节约",
            "objective": "minimize_bandwidth",
            "strategy_profile": "spectrum_saving",
            "constraint_weights": {"task": 65, "risk": 55, "spectrum": 95, "priority": 55, "switching": 35, "reuse": 70},
            "reason": "优先压缩总占用带宽并提高可复用资源利用率。",
            "tradeoff": "可能增加局部风险或降低部分低优先级保障。",
        },
        {
            "trial_id": "task_guard",
            "label": "任务保障",
            "objective": "task_assurance",
            "strategy_profile": "task_guard",
            "constraint_weights": {"task": 95, "risk": 70, "spectrum": 45, "priority": 80, "switching": 25, "reuse": 25},
            "reason": "优先补齐未满足和部分满足装备组。",
            "tradeoff": "可能牺牲频谱节约目标。",
        },
        {
            "trial_id": "priority_guard",
            "label": "高优先级保障",
            "objective": "priority_equipment",
            "strategy_profile": "priority_guard",
            "constraint_weights": {"task": 80, "risk": 70, "spectrum": 45, "priority": 95, "switching": 30, "reuse": 30},
            "reason": "优先保障高优先级任务单元和装备组。",
            "tradeoff": "低优先级对象可能被降级。",
        },
        {
            "trial_id": "reuse_efficiency",
            "label": "复用效率",
            "objective": "maximize_reuse_efficiency",
            "strategy_profile": "reuse_efficiency",
            "constraint_weights": {"task": 70, "risk": 60, "spectrum": 80, "priority": 55, "switching": 35, "reuse": 90},
            "reason": "在可接受风险下提高低功率、共享型资源复用。",
            "tradeoff": "需要重点复核复用距离和邻频风险。",
        },
    ]
    deduped = []
    seen = set()
    for profile in profiles:
        key = (
            profile["objective"],
            profile["strategy_profile"],
            tuple(sorted((profile.get("constraint_weights") or {}).items())),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(profile)
    return deduped


def _apply_replan_changes_to_records(
    task_units: list[dict],
    equipment_groups: list[dict],
    spectrum_rules: list[dict],
    changes: dict,
) -> tuple[list[dict], list[dict], list[dict]]:
    units = [dict(item) for item in task_units]
    groups = [dict(item) for item in equipment_groups]
    rules = [dict(item) for item in spectrum_rules]
    for idx, item in enumerate(changes.get("available_ranges", [])):
        rule = _trial_range_rule(item, rules, idx, available=True)
        if rule:
            rules.append(rule)
    for idx, item in enumerate(changes.get("forbidden_ranges", [])):
        rule = _trial_range_rule(item, rules, idx, available=False)
        if rule:
            rules.append(rule)
    for update in changes.get("priority_updates", []):
        target = str(update.get("target") or "").strip()
        priority = max(1, min(10, int(update.get("priority") or 1)))
        for unit in units:
            if _target_matches(target, unit.get("task_unit_id"), unit.get("name"), unit.get("unit_type")):
                unit["priority"] = priority
        for group in groups:
            if _target_matches(target, group.get("equipment_group_id"), group.get("equipment_type")):
                group["priority"] = priority
    for update in changes.get("satisfaction_updates", []):
        target = str(update.get("task_unit_id") or "").strip()
        ratio = max(0.1, min(1.0, float(update.get("min_satisfaction_ratio") or 1.0)))
        for unit in units:
            if _target_matches(target, unit.get("task_unit_id"), unit.get("name"), unit.get("unit_type")):
                unit["min_satisfaction_ratio"] = ratio
                break
    return units, groups, rules


def _trial_range_rule(item: dict, rules: list[dict], idx: int, available: bool) -> dict | None:
    start = float(item.get("start_mhz") or 0)
    end = float(item.get("end_mhz") or 0)
    if end <= start:
        return None
    band_group = item.get("band_group") or _infer_band_group(start, end, rules)
    if not band_group:
        return None
    defaults = _available_rule_defaults_for_band(rules, band_group)
    if available:
        return {
            "rule_id": f"SR-TRIAL-AVAIL-{idx}",
            "rule_type": "可用",
            "band_group": band_group,
            "spectrum_relation": defaults.get("spectrum_relation", "可复用"),
            "start_mhz": start,
            "end_mhz": end,
            "channel_step_khz": defaults.get("channel_step_khz", 25),
            "max_bandwidth_khz": defaults.get("max_bandwidth_khz", 25),
            "max_power_w": defaults.get("max_power_w", 1),
            "guard_band_khz": defaults.get("guard_band_khz", 0),
            "compatible_unit_types": defaults.get("compatible_unit_types", ""),
            "compatible_equipment_types": defaults.get("compatible_equipment_types", ""),
            "reason": item.get("reason") or "策略试算补充可用频段",
            "source": "TRIAL",
            "severity": "低",
            "raw_json": "{}",
        }
    return {
        "rule_id": f"SR-TRIAL-FORBID-{idx}",
        "rule_type": "禁用",
        "band_group": band_group,
        "spectrum_relation": "禁用",
        "start_mhz": start,
        "end_mhz": end,
        "channel_step_khz": 25,
        "max_bandwidth_khz": 0,
        "max_power_w": 0,
        "guard_band_khz": float(item.get("guard_band_khz") or 0),
        "compatible_unit_types": "",
        "compatible_equipment_types": "",
        "reason": item.get("reason") or "策略试算临时禁用",
        "source": "TRIAL",
        "severity": "高",
        "raw_json": "{}",
    }


def _trial_apply_payload(profile: dict, changes: dict, base_run_id: int | None, variant: dict | None = None) -> dict:
    variant = variant or _base_constraint_variant()
    label = profile["label"] if variant.get("variant_id") == "current_constraints" else f"{profile['label']} + {variant.get('label', '当前约束')}"
    return {
        "message": f"采用“{label}”联合试算方案重新规划。",
        "objective": profile["objective"],
        "base_run_id": base_run_id,
        "locked_equipment_group_ids": changes.get("locked_equipment_group_ids", []),
        "locked_task_unit_ids": changes.get("locked_task_unit_ids", []),
        "available_ranges": changes.get("available_ranges", []),
        "forbidden_ranges": changes.get("forbidden_ranges", []),
        "priority_updates": changes.get("priority_updates", []),
        "satisfaction_updates": changes.get("satisfaction_updates", []),
        "avoid_band_groups": changes.get("avoid_band_groups", []),
        "forced_band_groups": changes.get("forced_band_groups", {}),
        "required_full_targets": changes.get("required_full_targets", []),
        "allow_low_priority_degrade": changes.get("allow_low_priority_degrade", True),
        "constraint_weights": profile["constraint_weights"],
        "strategy_profile": profile["strategy_profile"],
    }


def _trial_metrics(summary: dict) -> dict:
    return {
        "task_satisfaction_avg": float(summary.get("task_satisfaction_avg") or 0),
        "quality_total": _summary_quality(summary),
        "high_risk_count": int(summary.get("high_risk_count") or 0),
        "medium_risk_count": int(summary.get("medium_risk_count") or 0),
        "partial_group_count": int(summary.get("partial_group_count") or 0),
        "unsatisfied_group_count": int(summary.get("unsatisfied_group_count") or 0),
        "used_bandwidth_mhz": float(summary.get("used_bandwidth_mhz") or 0),
    }


def _trial_deltas(summary: dict, base_summary: dict) -> dict:
    base = _trial_metrics(base_summary)
    current = _trial_metrics(summary)
    return {
        "task_satisfaction_avg": round(current["task_satisfaction_avg"] - base["task_satisfaction_avg"], 3),
        "quality_total": round(current["quality_total"] - base["quality_total"], 3),
        "high_risk_count": current["high_risk_count"] - base["high_risk_count"],
        "medium_risk_count": current["medium_risk_count"] - base["medium_risk_count"],
        "partial_group_count": current["partial_group_count"] - base["partial_group_count"],
        "unsatisfied_group_count": current["unsatisfied_group_count"] - base["unsatisfied_group_count"],
        "used_bandwidth_mhz": round(current["used_bandwidth_mhz"] - base["used_bandwidth_mhz"], 3),
    }


def _trial_recommendation_score(summary: dict, deltas: dict, variant: dict | None = None) -> float:
    score = _summary_quality(summary)
    score += max(0.0, float(deltas.get("quality_total") or 0)) * 0.8
    score += max(0.0, float(deltas.get("task_satisfaction_avg") or 0)) * 0.4
    score += max(0, -int(deltas.get("unsatisfied_group_count") or 0)) * 10
    score += max(0, -int(deltas.get("partial_group_count") or 0)) * 4
    score += max(0, -int(deltas.get("high_risk_count") or 0)) * 8
    score += max(0.0, -float(deltas.get("used_bandwidth_mhz") or 0)) * 0.15
    score -= max(0, int(deltas.get("unsatisfied_group_count") or 0)) * 12
    score -= max(0, int(deltas.get("high_risk_count") or 0)) * 10
    score += float((variant or {}).get("rank_bonus") or 0)
    return round(score, 3)


def _trial_reason(profile: dict, variant: dict | None) -> str:
    variant = variant or _base_constraint_variant()
    if variant.get("variant_id") == "current_constraints":
        return profile["reason"]
    changes = "；".join(str(item) for item in (variant.get("change_items") or [])[:2])
    return f"{profile['reason']} 约束变体：{changes}。"


def _trial_tradeoff(profile: dict, variant: dict | None) -> str:
    variant = variant or _base_constraint_variant()
    if variant.get("variant_id") == "current_constraints":
        return profile["tradeoff"]
    return f"{profile['tradeoff']} 该变体会改变约束边界，正式执行前仍需人工确认。"


def _trial_decision(summary: dict, deltas: dict) -> str:
    if int(summary.get("unsatisfied_group_count") or 0):
        return "保留为备选，需先处理未满足装备组"
    if float(deltas.get("quality_total") or 0) > 0 or int(deltas.get("high_risk_count") or 0) < 0:
        return "建议采用并进入重规划确认"
    if abs(float(deltas.get("quality_total") or 0)) <= 0.05 and abs(float(deltas.get("task_satisfaction_avg") or 0)) <= 0.05:
        return "收益不明显，作为对照方案"
    if int(deltas.get("high_risk_count") or 0) > 0 or int(deltas.get("unsatisfied_group_count") or 0) > 0:
        return "谨慎采用，关键指标有回退"
    return "可作为候选方案"


def _strategy_trial_diagnostics(candidates: list[dict], base_summary: dict) -> list[str]:
    if not candidates:
        return ["没有生成可用试算候选。"]
    recommended = candidates[0]
    deltas = recommended.get("deltas") or {}
    notes = [
        f"推荐“{recommended.get('label')}”，综合质量变化 {deltas.get('quality_total', 0):+g}，保障率变化 {deltas.get('task_satisfaction_avg', 0):+g}%。"
    ]
    if abs(float(deltas.get("quality_total") or 0)) <= 0.05 and abs(float(deltas.get("task_satisfaction_avg") or 0)) <= 0.05:
        notes.append("最优候选与基线基本持平，建议优先检查资源瓶颈、强制约束或任务拆分。")
    if int(base_summary.get("high_risk_count") or 0) and int(recommended.get("high_risk_count") or 0) < int(base_summary.get("high_risk_count") or 0):
        notes.append("推荐候选减少了高风险项，适合进入人工复核。")
    return notes


def task_assignments_for_run(session: Session, project_id: int, run_id: int) -> list[dict]:
    rows = session.exec(select(EquipmentAssignment).where(EquipmentAssignment.project_id == project_id, EquipmentAssignment.run_id == run_id)).all()
    return [row.model_dump() for row in rows]


def task_risks_for_run(session: Session, project_id: int, run_id: int) -> list[dict]:
    rows = session.exec(select(TaskRiskItem).where(TaskRiskItem.project_id == project_id, TaskRiskItem.run_id == run_id)).all()
    return [row.model_dump() for row in rows]


def solve_task_assignment(
    task_units: list[dict],
    equipment_groups: list[dict],
    spectrum_rules: list[dict],
    objective: str,
    constraints: dict | None = None,
) -> dict:
    constraints = constraints or {}
    weights = _normalize_constraint_weights(constraints.get("weights") or {})
    effective_objective = _effective_objective_from_weights(objective, weights)
    units_by_id = {unit["task_unit_id"]: unit for unit in task_units}
    rules_by_band = _available_segments_by_band(spectrum_rules)
    protected = [rule for rule in spectrum_rules if rule.get("rule_type") == "保护"]
    forbidden = [rule for rule in spectrum_rules if rule.get("rule_type") == "禁用"]
    locked_assignments = constraints.get("locked_assignments") or {}
    avoid_band_groups = set(constraints.get("avoid_band_groups") or [])
    hard_avoid_by_unit = _normalize_band_avoid_map(constraints.get("hard_avoid_band_groups_by_task_unit") or {})
    hard_avoid_by_group = _normalize_band_avoid_map(constraints.get("hard_avoid_band_groups_by_equipment_group") or {})
    forced_band_groups = constraints.get("forced_band_groups") or {}
    required_full_targets = set(constraints.get("required_full_targets") or [])
    allow_low_priority_degrade = bool(constraints.get("allow_low_priority_degrade", True))
    consumption: dict[tuple[str, str], list[Segment]] = defaultdict(list)
    assignments: list[dict] = []
    risk_items: list[dict] = []

    for group in sorted(equipment_groups, key=lambda item: _group_sort_key(item, units_by_id, effective_objective)):
        unit = units_by_id.get(group["task_unit_id"], {})
        if group["equipment_group_id"] in locked_assignments:
            allocation = _allocation_from_locked(group, unit, locked_assignments[group["equipment_group_id"]], effective_objective)
            if (unit.get("spectrum_relation") or "独占") == "独占" and allocation.get("band_group"):
                consumption[(allocation["band_group"], "exclusive")].extend(_parse_resource_segments(allocation.get("assigned_resource") or ""))
            assignments.append(allocation)
            risk_items.extend(_risk_items_for_assignment(allocation, group, unit, protected, forbidden))
            continue
        preferred_bands = _ordered_band_candidates(group, unit, rules_by_band, avoid_band_groups, forced_band_groups=forced_band_groups)
        hard_avoid_bands = _hard_avoid_bands_for_group(group, unit, hard_avoid_by_unit, hard_avoid_by_group)
        if hard_avoid_bands:
            preferred_bands = [band for band in preferred_bands if band not in hard_avoid_bands]
        allocation = _allocate_group(group, unit, preferred_bands, rules_by_band, spectrum_rules, consumption, effective_objective)
        _apply_required_full_flag(allocation, group, unit, required_full_targets, allow_low_priority_degrade)
        assignments.append(allocation)
        risk_items.extend(_risk_items_for_assignment(allocation, group, unit, protected, forbidden))

    risk_items.extend(_reuse_risks(assignments, task_units, equipment_groups))
    unit_summaries = _task_unit_summaries(task_units, assignments)
    summary = _task_summary(task_units, equipment_groups, assignments, risk_items, unit_summaries)
    summary["spectrum_rule_count"] = len(spectrum_rules)
    summary["requested_objective"] = objective
    summary["effective_objective"] = effective_objective
    summary["constraint_weights"] = weights
    summary["strategy_profile"] = constraints.get("strategy_profile") or "balanced"
    summary["hard_avoid_rule_count"] = sum(len(value) for value in hard_avoid_by_unit.values()) + sum(len(value) for value in hard_avoid_by_group.values())
    summary["bottleneck_analysis"] = _bottleneck_analysis(task_units, equipment_groups, spectrum_rules, assignments, risk_items)
    summary["spectrum_contention"] = _spectrum_contention_analysis(task_units, equipment_groups, spectrum_rules, assignments, risk_items)
    summary["diagnostics"] = _diagnose_task_plan(task_units, equipment_groups, spectrum_rules, assignments, risk_items)
    summary["score_explanation"] = _task_plan_score_explanation(summary)
    summary["decision_recommendations"] = _decision_recommendations(assignments, risk_items)
    summary["quality_scores"] = _quality_scores(summary)
    summary["leader_summary"] = _leader_summary(summary)
    summary["technical_summary"] = _technical_summary(summary)
    return {
        "status": "success",
        "message": f"已生成 {len(task_units)} 个任务单元、{len(equipment_groups)} 个装备组的用频方案",
        "assignments": assignments,
        "risk_items": risk_items,
        "summary": summary,
    }


def build_task_visualization_data(
    task_units: list[dict],
    equipment_groups: list[dict],
    spectrum_rules: list[dict],
    assignments: list[dict],
    risk_items: list[dict],
    summary: dict,
) -> dict:
    groups_by_id = {item["equipment_group_id"]: item for item in equipment_groups}
    units_by_id = {item["task_unit_id"]: item for item in task_units}
    unit_summaries = _task_unit_summaries(task_units, assignments)
    unit_cards = []
    for unit in task_units:
        item = unit_summaries.get(unit["task_unit_id"], {})
        unit_cards.append(
            {
                **unit,
                "satisfaction_ratio": item.get("satisfaction_ratio", 0),
                "satisfied_count": item.get("satisfied_count", 0),
                "requested_count": item.get("requested_count", 0),
                "status": _status_from_ratio(item.get("satisfaction_ratio", 0), unit.get("min_satisfaction_ratio", 1.0)),
            }
        )

    band_usage = []
    for band in sorted({rule.get("band_group") for rule in spectrum_rules if rule.get("band_group")}):
        available_width = sum(
            max(0, float(rule.get("end_mhz") or 0) - float(rule.get("start_mhz") or 0))
            for rule in spectrum_rules
            if rule.get("band_group") == band and rule.get("rule_type") == "可用"
        )
        used_segments = []
        for assignment in assignments:
            if assignment.get("band_group") != band:
                continue
            used_segments.extend(_parse_resource_segments(assignment.get("assigned_resource") or ""))
        used_width = sum(segment.width_mhz for segment in used_segments)
        band_usage.append(
            {
                "band_group": band,
                "available_width_mhz": round(available_width, 3),
                "used_width_mhz": round(used_width, 3),
                "utilization_pct": round(used_width / available_width * 100, 2) if available_width else 0,
                "assignment_count": len([item for item in assignments if item.get("band_group") == band]),
                "rules": [rule for rule in spectrum_rules if rule.get("band_group") == band and rule.get("rule_type") in {"禁用", "保护"}],
            }
        )

    matrix = []
    for assignment in assignments:
        group = groups_by_id.get(assignment["equipment_group_id"], {})
        unit = units_by_id.get(assignment["task_unit_id"], {})
        alternatives = _alternative_resources_for_assignment(group, unit, spectrum_rules, assignment)
        matrix.append(
            {
                **assignment,
                "count": group.get("count", assignment.get("requested_count", 0)),
                "priority": group.get("priority", 1),
                "mobility": group.get("mobility", ""),
                "bandwidth_khz": group.get("bandwidth_khz", 0),
                "alternative_resources": alternatives,
                "explanation_chain": _assignment_explanation_chain(group, unit, spectrum_rules, assignment, alternatives),
            }
        )

    reason_counter = Counter(item.get("reason") or item.get("risk_type") for item in risk_items)
    partial_reason_counter = Counter(item.get("reason") for item in assignments if item.get("status") != "完全满足")
    return {
        "summary": summary,
        "task_units": unit_cards,
        "equipment_groups": equipment_groups,
        "assignments": matrix,
        "band_usage": band_usage,
        "spectrum_timeline": _build_spectrum_timeline(spectrum_rules, assignments),
        "risk_items": sorted(risk_items, key=lambda item: item.get("score", 0), reverse=True),
        "satisfaction_distribution": _distribution([item["status"] for item in unit_cards], ["完全满足", "部分满足", "未满足"]),
        "assignment_status_distribution": _distribution([item["status"] for item in assignments], ["完全满足", "部分满足", "未满足"]),
        "risk_reason_rank": [{"reason": key, "count": value} for key, value in reason_counter.most_common(8)],
        "partial_reason_rank": [{"reason": key, "count": value} for key, value in partial_reason_counter.most_common(8) if key],
    }


def build_task_report(project: dict, run: dict, assignments: list[dict], risks: list[dict], summary: dict, visualization: dict | None = None) -> str:
    visualization = visualization or {}
    task_rows = "\n".join(
        f"""
        <tr>
          <td>{escape(item.get("task_unit_id", ""))}</td>
          <td>{escape(item.get("name", ""))}</td>
          <td>{escape(str(item.get("priority", "")))}</td>
          <td>{escape(str(round(float(item.get("satisfaction_ratio", 0)) * 100, 1)))}%</td>
          <td>{escape(item.get("status", ""))}</td>
        </tr>
        """
        for item in visualization.get("task_units", [])
    )
    assignment_rows = "\n".join(
        f"""
        <tr>
          <td>{escape(item.get("task_unit_id", ""))}</td>
          <td>{escape(item.get("equipment_group_id", ""))}</td>
          <td>{escape(item.get("equipment_type", ""))}</td>
          <td>{escape(item.get("assignment_mode", ""))}</td>
          <td>{escape(item.get("band_group") or "")}</td>
          <td>{escape(item.get("assigned_resource", ""))}</td>
          <td>{escape(str(item.get("satisfied_count", 0)))}/{escape(str(item.get("requested_count", 0)))}</td>
          <td>{escape(str(round(float(item.get("satisfaction_ratio", 0)) * 100, 1)))}%</td>
          <td>{escape(item.get("status", ""))}</td>
          <td>{escape(item.get("reason", ""))}</td>
        </tr>
        """
        for item in assignments
    )
    risk_rows = "\n".join(
        f"""
        <tr>
          <td>{escape(item.get("risk_type", ""))}</td>
          <td>{escape(item.get("severity", ""))}</td>
          <td>{escape(item.get("task_unit_a") or "")}</td>
          <td>{escape(item.get("equipment_group_a") or "")}</td>
          <td>{escape(item.get("resource_a") or "")}</td>
          <td>{escape(str(item.get("score", 0)))}</td>
          <td>{escape(item.get("reason", ""))}</td>
        </tr>
        """
        for item in risks
    )
    diagnostic_rows = "\n".join(
        f"""
        <tr>
          <td>{escape(item.get("category", ""))}</td>
          <td>{escape(item.get("severity", ""))}</td>
          <td>{escape(item.get("target", ""))}</td>
          <td>{escape(item.get("reason", ""))}</td>
          <td>{escape(item.get("suggestion", ""))}</td>
        </tr>
        """
        for item in summary.get("diagnostics", [])
    )
    score = summary.get("score_explanation", {})
    score_rows = "\n".join(
        f"""
        <tr>
          <td>{escape(item.get("label", ""))}</td>
          <td>{escape(str(item.get("value", "")))}</td>
          <td>{escape(item.get("note", ""))}</td>
        </tr>
        """
        for item in score.get("components", [])
    )
    quality = summary.get("quality_scores", {})
    quality_rows = "\n".join(
        f"""
        <tr>
          <td>{escape(item.get("label", ""))}</td>
          <td>{escape(str(item.get("score", "")))}</td>
          <td>{escape(item.get("note", ""))}</td>
        </tr>
        """
        for item in quality.get("items", [])
    )
    explanation_rows = "\n".join(
        f"""
        <tr>
          <td>{escape(item.get("equipment_group_id", ""))}</td>
          <td>{escape(item.get("equipment_type", ""))}</td>
          <td>{escape(item.get("band_group") or "")}</td>
          <td>{escape("；".join((item.get("explanation_chain") or {}).get("why_selected", [])[:3]))}</td>
          <td>{escape(((item.get("explanation_chain") or {}).get("required_extra_resource") or {}).get("suggestion", ""))}</td>
          <td>{escape((item.get("explanation_chain") or {}).get("audit_hint", ""))}</td>
        </tr>
        """
        for item in visualization.get("assignments", [])[:20]
    )
    bottleneck = summary.get("bottleneck_analysis", {})
    bottleneck_rows = "\n".join(
        f"""
        <tr>
          <td>{escape(item.get("band_group", ""))}</td>
          <td>{escape(str(item.get("pressure_score", "")))}</td>
          <td>{escape(str(item.get("clean_available_width_mhz", "")))}</td>
          <td>{escape(str(item.get("used_width_mhz", "")))}</td>
          <td>{escape(str(item.get("blocker_count", "")))}</td>
          <td>{escape(str(item.get("pressure_group_count", "")))}</td>
        </tr>
        """
        for item in bottleneck.get("band_bottlenecks", [])[:10]
    )
    audit_rows = "\n".join(
        f"<li>{escape(item)}</li>"
        for item in _audit_checklist(summary, visualization.get("assignments", []))
    )
    conclusion = _report_conclusion(summary)
    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>任务单元用频规划报告 - {escape(project.get("name", ""))}</title>
  <style>
    body {{ font-family: Arial, "Microsoft YaHei", sans-serif; margin: 32px; color: #172033; }}
    h1, h2 {{ margin: 0 0 16px; }}
    section {{ margin: 28px 0; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border: 1px solid #d8dde8; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f6fb; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 12px; }}
    .metric {{ border: 1px solid #d8dde8; padding: 12px; border-radius: 6px; background: #fbfcff; }}
    .metric strong {{ display: block; font-size: 22px; margin-top: 4px; }}
    .conclusion {{ background: #f7f9fd; border: 1px solid #d8dde8; border-radius: 8px; padding: 14px 16px; }}
  </style>
</head>
<body>
  <h1>任务单元用频规划报告</h1>
  <p>项目：{escape(project.get("name", ""))}｜运行编号：{escape(str(run.get("id", "")))}｜目标：{escape(run.get("objective", ""))}</p>
  <section class="conclusion">
    <strong>总体结论</strong>
    <p>{escape(conclusion)}</p>
    <p>{escape(summary.get("leader_summary", ""))}</p>
    <p>{escape(summary.get("technical_summary", ""))}</p>
  </section>
  <section class="summary">
    <div class="metric">任务单元<strong>{escape(str(summary.get("task_unit_count", "-")))}</strong></div>
    <div class="metric">装备组<strong>{escape(str(summary.get("equipment_group_count", "-")))}</strong></div>
    <div class="metric">平均保障率<strong>{escape(str(summary.get("task_satisfaction_avg", 0)))}%</strong></div>
    <div class="metric">部分/未满足<strong>{escape(str(summary.get("partial_group_count", 0) + summary.get("unsatisfied_group_count", 0)))}</strong></div>
  </section>
  <section>
    <h2>任务单元保障表</h2>
    <table>
      <thead><tr><th>任务单元</th><th>名称</th><th>优先级</th><th>保障率</th><th>状态</th></tr></thead>
      <tbody>{task_rows or '<tr><td colspan="5">暂无任务单元数据。</td></tr>'}</tbody>
    </table>
  </section>
  <section>
    <h2>装备组指配明细</h2>
    <table>
      <thead><tr><th>任务单元</th><th>装备组</th><th>装备类型</th><th>模式</th><th>频段池</th><th>指配资源</th><th>满足数量</th><th>保障率</th><th>状态</th><th>原因</th></tr></thead>
      <tbody>{assignment_rows}</tbody>
    </table>
  </section>
  <section>
    <h2>风险、保护和部分满足原因</h2>
    <table>
      <thead><tr><th>类型</th><th>等级</th><th>任务单元</th><th>装备组</th><th>资源</th><th>分值</th><th>原因</th></tr></thead>
      <tbody>{risk_rows or '<tr><td colspan="7">未发现明显冲突。</td></tr>'}</tbody>
    </table>
  </section>
  <section>
    <h2>不可行/部分满足诊断</h2>
    <table>
      <thead><tr><th>类别</th><th>等级</th><th>对象</th><th>原因</th><th>建议</th></tr></thead>
      <tbody>{diagnostic_rows or '<tr><td colspan="5">当前没有需要处置的诊断项。</td></tr>'}</tbody>
    </table>
  </section>
  <section>
    <h2>瓶颈频段与审核清单</h2>
    <table>
      <thead><tr><th>频段池</th><th>压力分</th><th>净可用 MHz</th><th>已用 MHz</th><th>阻塞窗口</th><th>受压装备组</th></tr></thead>
      <tbody>{bottleneck_rows or '<tr><td colspan="6">暂无瓶颈频段。</td></tr>'}</tbody>
    </table>
    <ul>{audit_rows or '<li>当前方案可进入常规审核。</li>'}</ul>
  </section>
  <section>
    <h2>装备组解释链</h2>
    <table>
      <thead><tr><th>装备组</th><th>类型</th><th>频段池</th><th>选择依据</th><th>资源建议</th><th>审核提示</th></tr></thead>
      <tbody>{explanation_rows or '<tr><td colspan="6">暂无解释链。</td></tr>'}</tbody>
    </table>
  </section>
  <section>
    <h2>方案质量看板</h2>
    <p>综合质量：{escape(str(quality.get("total", "-")))} 分。</p>
    <table>
      <thead><tr><th>质量项</th><th>得分</th><th>说明</th></tr></thead>
      <tbody>{quality_rows or '<tr><td colspan="3">暂无质量评分。</td></tr>'}</tbody>
    </table>
  </section>
  <section>
    <h2>多目标评分解释</h2>
    <p>综合分：{escape(str(score.get("total_score", "-")))}，分值越低表示方案综合代价越小。</p>
    <table>
      <thead><tr><th>评分项</th><th>贡献值</th><th>说明</th></tr></thead>
      <tbody>{score_rows or '<tr><td colspan="3">暂无评分解释。</td></tr>'}</tbody>
    </table>
  </section>
</body>
</html>
"""


def build_task_export_xlsx(assignments: list[dict], risks: list[dict], summary: dict, visualization: dict | None = None) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(assignments).to_excel(writer, index=False, sheet_name="装备组指配")
        pd.DataFrame(risks).to_excel(writer, index=False, sheet_name="风险与原因")
        pd.DataFrame([summary]).to_excel(writer, index=False, sheet_name="汇总")
        if visualization:
            pd.DataFrame(visualization.get("task_units", [])).to_excel(writer, index=False, sheet_name="任务单元保障")
            pd.DataFrame(visualization.get("band_usage", [])).to_excel(writer, index=False, sheet_name="频段池占用")
            pd.DataFrame(visualization.get("spectrum_timeline", [])).to_excel(writer, index=False, sheet_name="频谱条带")
            alternatives = []
            for assignment in visualization.get("assignments", []):
                for alt in assignment.get("alternative_resources", []) or []:
                    alternatives.append({"equipment_group_id": assignment.get("equipment_group_id"), **alt})
            pd.DataFrame(alternatives).to_excel(writer, index=False, sheet_name="备选资源")
            explanations = []
            for assignment in visualization.get("assignments", []):
                chain = assignment.get("explanation_chain") or {}
                extra = chain.get("required_extra_resource") or {}
                explanations.append(
                    {
                        "equipment_group_id": assignment.get("equipment_group_id"),
                        "equipment_type": assignment.get("equipment_type"),
                        "band_group": assignment.get("band_group"),
                        "status": assignment.get("status"),
                        "why_selected": "；".join(chain.get("why_selected", [])),
                        "why_rejected": "；".join(f"{item.get('band_group')}:{item.get('reason')}" for item in chain.get("why_rejected", [])),
                        "missing_channels": extra.get("missing_channels", 0),
                        "estimated_extra_width_mhz": extra.get("estimated_extra_width_mhz", 0),
                        "audit_hint": chain.get("audit_hint", ""),
                    }
                )
            pd.DataFrame(explanations).to_excel(writer, index=False, sheet_name="解释链")
        pd.DataFrame(summary.get("diagnostics", [])).to_excel(writer, index=False, sheet_name="诊断建议")
        score = summary.get("score_explanation", {})
        pd.DataFrame(score.get("components", [])).to_excel(writer, index=False, sheet_name="评分解释")
        quality = summary.get("quality_scores", {})
        pd.DataFrame(quality.get("items", [])).to_excel(writer, index=False, sheet_name="质量看板")
        bottleneck = summary.get("bottleneck_analysis", {})
        pd.DataFrame(bottleneck.get("band_bottlenecks", [])).to_excel(writer, index=False, sheet_name="瓶颈频段")
        pd.DataFrame(bottleneck.get("equipment_gaps", [])).to_excel(writer, index=False, sheet_name="装备缺口")
        pd.DataFrame(bottleneck.get("task_unit_pressure", [])).to_excel(writer, index=False, sheet_name="任务压力")
        pd.DataFrame(bottleneck.get("contention_links", [])).to_excel(writer, index=False, sheet_name="冲突链路")
        contention = summary.get("spectrum_contention", {})
        pd.DataFrame(contention.get("top_loss_sources", [])).to_excel(writer, index=False, sheet_name="频谱损失来源")
        pd.DataFrame(_audit_checklist(summary, visualization.get("assignments", []) if visualization else [])).to_excel(writer, index=False, sheet_name="审核清单")
    return buffer.getvalue()


def demo_scenario_records(scenario: str = "baseline") -> tuple[list[dict], list[dict], list[dict]]:
    if scenario in SIM_SCENARIO_KEYS:
        return sim_scenario_records(scenario)
    if scenario == "large_joint_exercise":
        return _scaled_demo_records("LG", 18, 1.85)
    if scenario == "stress_performance":
        return _scaled_demo_records("ST", 36, 2.4)

    task_units, groups, rules = _high_density_joint_demo_records()
    _apply_demo_variant(scenario, task_units, groups, rules)
    return task_units, groups, rules


def _high_density_joint_demo_records() -> tuple[list[dict], list[dict], list[dict]]:
    base_lat = 31.23
    base_lon = 121.47
    task_units = [
        _task_unit("TU-CMD", "指挥通信单元", "指挥通信单元", base_lat, base_lon, 8, 10, "独占", "UHF-SIM-1,VHF-SIM-1", 0.98),
        _task_unit("TU-MOB-A", "机动通信单元 A", "机动通信单元", base_lat + 0.10, base_lon + 0.08, 12, 8, "可复用", "VHF-SIM-1,UHF-SIM-1", 0.90),
        _task_unit("TU-MOB-B", "机动通信单元 B", "机动通信单元", base_lat - 0.06, base_lon + 0.12, 14, 7, "可复用", "VHF-SIM-1,UHF-SIM-1", 0.85),
        _task_unit("TU-UAV", "无人机侦察单元", "无人机侦察单元", base_lat + 0.04, base_lon + 0.16, 18, 9, "独占", "L-SIM-1,S-SIM-1", 0.95),
        _task_unit("TU-UAV-SWARM", "无人机集群单元", "无人机侦察单元", base_lat + 0.16, base_lon + 0.18, 22, 8, "可复用", "L-SIM-1,S-SIM-1,EW-SIM-1", 0.88),
        _task_unit("TU-RAD", "低空探测单元", "雷达探测单元", base_lat + 0.18, base_lon - 0.06, 25, 9, "独占", "S-SIM-1,C-SIM-1", 0.95),
        _task_unit("TU-RAD-TRACK", "跟踪监视单元", "雷达探测单元", base_lat + 0.22, base_lon - 0.12, 26, 8, "独占", "C-SIM-1,S-SIM-1", 0.90),
        _task_unit("TU-BH", "回传保障单元", "回传保障单元", base_lat - 0.08, base_lon + 0.04, 20, 8, "可复用", "C-SIM-1,Ku-SIM-1", 0.90),
        _task_unit("TU-EW-SIM", "电磁环境仿真单元", "电子对抗单元", base_lat + 0.02, base_lon - 0.18, 18, 6, "独占", "EW-SIM-1,S-SIM-1", 0.70),
        _task_unit("TU-PNT", "导航授时保障单元", "导航授时单元", base_lat - 0.12, base_lon - 0.05, 16, 10, "独占", "PNT-SIM-1,L-SIM-1", 1.00),
        _task_unit("TU-LOG", "后勤保障通信单元", "机动通信单元", base_lat - 0.18, base_lon + 0.10, 18, 5, "可复用", "VHF-SIM-1,UHF-SIM-1", 0.70),
        _task_unit("TU-EMG", "应急备份通信单元", "机动通信单元", base_lat - 0.15, base_lon - 0.14, 18, 7, "可复用", "UHF-SIM-1,VHF-SIM-1,L-SIM-1", 0.80),
    ]
    groups = [
        _group("EG-CMD-BASE", "TU-CMD", "固定基站", 4, "双工", "固定", 50, 45, 8, 35, -112, "数字窄带", "双工", 4, "离散信道", "UHF-SIM-1", 10, 8, 50, 25),
        _group("EG-CMD-VEH", "TU-CMD", "指挥车", 8, "双工", "机动", 25, 35, 6, 12, -110, "数字窄带", "双工", 8, "离散信道", "UHF-SIM-1", 9, 6, 50, 25),
        _group("EG-CMD-HAND", "TU-CMD", "手持终端", 40, "双工", "便携", 12.5, 5, 0, 1.5, -105, "数字窄带", "单工", 12, "共享信道", "VHF-SIM-1", 8, 2, 12.5, 12.5),
        _group("EG-MOB-A-VEH", "TU-MOB-A", "车载电台", 24, "双工", "机动", 25, 30, 4, 3, -108, "数字窄带", "单工", 16, "离散信道", "UHF-SIM-1", 8, 5, 50, 25),
        _group("EG-MOB-A-HAND", "TU-MOB-A", "手持终端", 80, "双工", "便携", 12.5, 5, 0, 1.5, -104, "数字窄带", "单工", 20, "共享信道", "VHF-SIM-1", 7, 2, 12.5, 12.5),
        _group("EG-MOB-B-VEH", "TU-MOB-B", "车载电台", 18, "双工", "机动", 25, 30, 4, 3, -108, "数字窄带", "单工", 12, "离散信道", "UHF-SIM-1", 7, 5, 50, 25),
        _group("EG-MOB-RELAY", "TU-EMG", "中继设备", 4, "双工", "机动", 25, 35, 5, 8, -110, "数字窄带", "双工", 4, "收发频点对", "UHF-SIM-1", 8, 8, 100, 50),
        _group("EG-UAV-CTRL", "TU-UAV", "无人机遥控链路", 18, "双工", "机动", 250, 5, 5, 2, -102, "扩频", "双工", 12, "离散信道", "L-SIM-1", 9, 10, 250, 100),
        _group("EG-UAV-DATA", "TU-UAV", "无人机数传链路", 12, "双工", "空中机动", 2000, 8, 8, 0.5, -95, "OFDM", "双工", 8, "连续频段", "S-SIM-1", 9, 12, 1000, 500),
        _group("EG-UAV-GCS", "TU-UAV", "地面控制站", 2, "双工", "固定", 500, 20, 10, 8, -105, "扩频/OFDM", "双工", 2, "连续频段", "L-SIM-1", 9, 12, 500, 250),
        _group("EG-SWARM-CTRL", "TU-UAV-SWARM", "无人机遥控链路", 36, "双工", "空中机动", 100, 3, 5, 1, -100, "扩频", "双工", 24, "离散信道", "L-SIM-1", 8, 8, 100, 50),
        _group("EG-SWARM-DATA", "TU-UAV-SWARM", "无人机数传链路", 10, "双工", "空中机动", 1000, 5, 7, 0.5, -96, "OFDM", "双工", 8, "连续频段", "EW-SIM-1", 7, 10, 1000, 500),
        _group("EG-RAD-LOW", "TU-RAD", "低空探测雷达", 3, "发射", "固定", 8000, 1800, 32, 16, -82, "脉冲压缩", "单工", 3, "宽带连续频段", "C-SIM-1", 9, 30, 8000, 3000),
        _group("EG-RAD-TRACK", "TU-RAD-TRACK", "跟踪类雷达仿真装备", 2, "发射", "固定", 10000, 2500, 35, 18, -84, "脉冲多普勒", "单工", 2, "宽带连续频段", "C-SIM-1", 8, 35, 1000, 1000),
        _group("EG-BH-MW", "TU-BH", "微波回传链路", 6, "双工", "固定", 5000, 2, 22, 20, -85, "QAM", "双工", 6, "连续频段", "C-SIM-1", 8, 15, 5000, 1000),
        _group("EG-BH-SAT", "TU-BH", "卫星通信终端", 3, "双工", "机动", 4000, 4, 18, 3, -90, "QPSK/8PSK", "双工", 3, "连续频段", "Ku-SIM-1", 8, 10, 2000, 1000),
        _group("EG-EW-MON", "TU-EW-SIM", "电子压制设备", 4, "发射", "机动", 3000, 160, 18, 8, -80, "宽带噪声/扫频", "单工", 4, "连续频段", "EW-SIM-1", 6, 24, 1000, 500),
        _group("EG-PNT-TERM", "TU-PNT", "导航授时终端", 16, "接收/低功率发射", "便携", 100, 2, 2, 1.5, -118, "扩频/授时", "单工", 4, "离散信道", "PNT-SIM-1", 10, 6, 100, 50),
        _group("EG-LOG-HAND", "TU-LOG", "手持终端", 50, "双工", "便携", 12.5, 4, 0, 1.5, -104, "数字窄带", "单工", 10, "共享信道", "VHF-SIM-1", 5, 2, 12.5, 12.5),
        _group("EG-EMG-RELAY", "TU-EMG", "中继设备", 4, "双工", "机动", 50, 35, 5, 8, -110, "数字窄带", "双工", 4, "收发频点对", "UHF-SIM-1", 7, 8, 100, 50),
    ]
    rules = _high_density_spectrum_rules()
    return task_units, groups, rules


def parametric_demo_records(payload: dict) -> tuple[list[dict], list[dict], list[dict]]:
    params = _normalized_parametric_payload(payload)
    template_codes = _parametric_template_codes(params["unit_count"], params["radar_ratio"], params["uav_ratio"])
    task_units, groups, rules = _scaled_demo_records("PX", params["unit_count"], params["density_multiplier"], template_codes=template_codes)
    rules.extend(_parametric_density_rules(params["protection_density"], params["forbidden_density"]))
    return task_units, groups, rules


def task_planning_performance_test(scenarios: list[str] | None = None) -> dict:
    scenario_keys = scenarios or ["baseline", "large_joint_exercise", "stress_performance"]
    rows = []
    for scenario_key in scenario_keys:
        scenario_info = next((item for item in TASK_SCENARIOS if item["key"] == scenario_key), None)
        if not scenario_info:
            continue
        task_units, equipment_groups, spectrum_rules = demo_scenario_records(scenario_key)
        rows.extend(_performance_rows_for_dataset(scenario_key, scenario_info["name"], task_units, equipment_groups, spectrum_rules))
    return _performance_result(rows)


def task_planning_batch_performance_test() -> dict:
    rows = []
    for scale in BATCH_PERFORMANCE_SCALES:
        if scale.get("scenario"):
            task_units, equipment_groups, spectrum_rules = demo_scenario_records(str(scale["scenario"]))
        else:
            task_units, equipment_groups, spectrum_rules = _scaled_demo_records(
                str(scale.get("prefix") or scale["key"]).upper(),
                int(scale["unit_count"]),
                float(scale["density_multiplier"]),
            )
        rows.extend(_performance_rows_for_dataset(scale["key"], scale["name"], task_units, equipment_groups, spectrum_rules, scale=scale))
    result = _performance_result(rows)
    result["scales"] = BATCH_PERFORMANCE_SCALES
    return result


def task_project_batch_performance_test(session: Session, project_id: int) -> dict:
    result = task_planning_batch_performance_test()
    session.add(
        AuditLog(
            project_id=project_id,
            actor="system",
            action="task_performance_batch",
            detail=json.dumps(
                {
                    "summary": result["summary"],
                    "leader_summary": result["analysis"].get("leader_summary", ""),
                    "capacity_profile": result["analysis"].get("capacity_profile", {}),
                },
                ensure_ascii=False,
            ),
        )
    )
    session.commit()
    result["history"] = _performance_history_from_logs(session, project_id)
    return result


def _performance_rows_for_dataset(
    scenario_key: str,
    scenario_name: str,
    task_units: list[dict],
    equipment_groups: list[dict],
    spectrum_rules: list[dict],
    scale: dict | None = None,
) -> list[dict]:
    rows = []
    validation = validate_task_inputs(task_units, equipment_groups, spectrum_rules)
    for objective in TASK_OBJECTIVES:
        started = time.perf_counter()
        if validation["ok"]:
            result = solve_task_assignment(task_units, equipment_groups, spectrum_rules, objective["objective"])
            summary = result["summary"]
            status = result["status"]
            message = result["message"]
        else:
            summary = {
                "task_unit_count": len(task_units),
                "equipment_group_count": len(equipment_groups),
                "equipment_sample_count": sum(int(item.get("count") or 0) for item in equipment_groups),
                "task_satisfaction_avg": 0,
                "full_group_count": 0,
                "partial_group_count": 0,
                "unsatisfied_group_count": len(equipment_groups),
                "used_bandwidth_mhz": 0,
                "risk_item_count": 0,
                "high_risk_count": 0,
                "quality_scores": {"total": 0},
            }
            status = "invalid"
            message = "输入数据未通过校验"
        elapsed_ms = max(1, int((time.perf_counter() - started) * 1000))
        row = {
            "scenario": scenario_key,
            "scenario_name": scenario_name,
            "objective": objective["objective"],
            "objective_label": objective["label"],
            "status": status,
            "message": message,
            "task_unit_count": summary.get("task_unit_count", len(task_units)),
            "equipment_group_count": summary.get("equipment_group_count", len(equipment_groups)),
            "equipment_sample_count": summary.get("equipment_sample_count", 0),
            "spectrum_rule_count": len(spectrum_rules),
            "elapsed_ms": elapsed_ms,
            "groups_per_second": round(len(equipment_groups) / (elapsed_ms / 1000), 2),
            "task_satisfaction_avg": summary.get("task_satisfaction_avg", 0),
            "full_group_count": summary.get("full_group_count", 0),
            "partial_group_count": summary.get("partial_group_count", 0),
            "unsatisfied_group_count": summary.get("unsatisfied_group_count", 0),
            "risk_item_count": summary.get("risk_item_count", 0),
            "high_risk_count": summary.get("high_risk_count", 0),
            "used_bandwidth_mhz": summary.get("used_bandwidth_mhz", 0),
            "quality_total": (summary.get("quality_scores") or {}).get("total", 0),
        }
        if scale:
            row["scale_key"] = scale.get("key")
            row["scale_name"] = scale.get("name")
            row["density_multiplier"] = scale.get("density_multiplier")
        rows.append(row)
    return rows


def _performance_result(rows: list[dict]) -> dict:
    elapsed_values = [float(row["elapsed_ms"]) for row in rows]
    sample_values = [int(row["equipment_sample_count"]) for row in rows]
    group_values = [int(row["equipment_group_count"]) for row in rows]
    quality_values = [float(row["quality_total"] or 0) for row in rows]
    analysis = _performance_analysis(rows)
    return {
        "rows": rows,
        "summary": {
            "scenario_count": len({row["scenario"] for row in rows}),
            "run_count": len(rows),
            "max_elapsed_ms": max(elapsed_values, default=0),
            "avg_elapsed_ms": round(sum(elapsed_values) / len(elapsed_values), 1) if elapsed_values else 0,
            "max_equipment_group_count": max(group_values, default=0),
            "max_equipment_sample_count": max(sample_values, default=0),
            "best_quality_total": max(quality_values, default=0),
        },
        "analysis": analysis,
    }


def _performance_analysis(rows: list[dict]) -> dict:
    by_scenario: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_scenario[row["scenario"]].append(row)

    scale_curve = []
    objective_rankings = []
    best_rows = []
    for scenario, items in by_scenario.items():
        best = max(items, key=lambda item: (float(item.get("quality_total") or 0), float(item.get("task_satisfaction_avg") or 0), -float(item.get("high_risk_count") or 0)))
        fastest = min(items, key=lambda item: float(item.get("elapsed_ms") or 0))
        best_rows.append(best)
        objective_rankings.append(
            {
                "scenario": scenario,
                "scenario_name": best["scenario_name"],
                "recommended_objective": best["objective"],
                "recommended_label": best["objective_label"],
                "quality_total": best["quality_total"],
                "task_satisfaction_avg": best["task_satisfaction_avg"],
                "elapsed_ms": best["elapsed_ms"],
                "reason": _performance_recommendation_reason(best),
            }
        )
        scale_curve.append(
            {
                "scenario": scenario,
                "scenario_name": best["scenario_name"],
                "task_unit_count": best["task_unit_count"],
                "equipment_group_count": best["equipment_group_count"],
                "equipment_sample_count": best["equipment_sample_count"],
                "avg_elapsed_ms": round(sum(float(item["elapsed_ms"]) for item in items) / len(items), 1),
                "max_elapsed_ms": max(float(item["elapsed_ms"]) for item in items),
                "best_quality_total": best["quality_total"],
                "best_satisfaction_avg": best["task_satisfaction_avg"],
                "fastest_objective_label": fastest["objective_label"],
            }
        )

    all_items = [item for items in by_scenario.values() for item in items]
    fastest_overall = min(all_items, key=lambda item: float(item.get("elapsed_ms") or 0), default=None)
    slowest_overall = max(all_items, key=lambda item: float(item.get("elapsed_ms") or 0), default=None)
    scenario_size = {
        scenario: max((int(item.get("equipment_group_count") or 0) for item in items), default=0)
        for scenario, items in by_scenario.items()
    }
    stress_key = "stress_performance" if "stress_performance" in by_scenario else max(scenario_size, key=scenario_size.get, default="")
    baseline_key = "baseline" if "baseline" in by_scenario else min(scenario_size, key=scenario_size.get, default="")
    stress_items = by_scenario.get(stress_key, [])
    stress_best = max(stress_items, key=lambda item: float(item.get("quality_total") or 0), default=None)
    baseline_best = max(by_scenario.get(baseline_key, []), key=lambda item: float(item.get("quality_total") or 0), default=None)
    diagnostics = _performance_diagnostics(baseline_best, stress_best, slowest_overall)
    return {
        "scale_curve": scale_curve,
        "objective_rankings": objective_rankings,
        "diagnostics": diagnostics,
        "leader_summary": _performance_leader_summary(baseline_best, stress_best, slowest_overall),
        "capacity_profile": _performance_capacity_profile(best_rows, slowest_overall),
        "fastest_case": fastest_overall,
        "slowest_case": slowest_overall,
    }


def _performance_capacity_profile(best_rows: list[dict], slowest: dict | None = None) -> dict:
    if not best_rows:
        return {
            "status": "暂无数据",
            "decision": "尚未形成压测样本，无法判断容量边界。",
            "interactive_threshold_ms": 1000,
            "quality_floor": 60.0,
            "recommended": {},
            "largest": {},
            "quality_drop": 0,
            "satisfaction_drop": 0,
            "elapsed_growth": 0,
            "problem_focus": "缺少压测数据",
            "actions": ["先运行阶梯压测，形成不同规模下的耗时和质量曲线。"],
        }

    rows = sorted(
        best_rows,
        key=lambda item: (int(item.get("task_unit_count") or 0), int(item.get("equipment_group_count") or 0)),
    )
    first = rows[0]
    largest = rows[-1]
    interactive_threshold_ms = 1000
    quality_floor = 60.0

    def unsatisfied_limit(row: dict) -> int:
        groups = int(row.get("equipment_group_count") or 0)
        return max(1, int(math.ceil(groups * 0.03)))

    def acceptable(row: dict) -> bool:
        return (
            float(row.get("elapsed_ms") or 0) <= interactive_threshold_ms
            and float(row.get("quality_total") or 0) >= quality_floor
            and int(row.get("unsatisfied_group_count") or 0) <= unsatisfied_limit(row)
        )

    acceptable_rows = [row for row in rows if acceptable(row)]
    recommended = acceptable_rows[-1] if acceptable_rows else rows[0]
    if acceptable(largest):
        status = "容量充足"
        decision = "当前最大压测规模仍满足交互耗时和质量门槛，可继续扩大样例或接入更复杂模型验证。"
    elif acceptable_rows:
        status = "需分批规划"
        decision = (
            f"建议单次交互规划控制在 {recommended.get('task_unit_count')} 个任务单元、"
            f"{recommended.get('equipment_group_count')} 个装备组以内；更大规模应分任务区域或分频段批处理。"
        )
    else:
        status = "需扩容规则"
        decision = "当前最小压测规模也未达到质量门槛，应先补充可用频段、降低低优先级需求或调整规则后再扩大规模。"

    quality_drop = round(float(first.get("quality_total") or 0) - float(largest.get("quality_total") or 0), 1)
    satisfaction_drop = round(float(first.get("task_satisfaction_avg") or 0) - float(largest.get("task_satisfaction_avg") or 0), 1)
    elapsed_growth = round(float(largest.get("elapsed_ms") or 0) / max(1.0, float(first.get("elapsed_ms") or 0)), 1)
    unsatisfied = int(largest.get("unsatisfied_group_count") or 0)
    high_risk = int(largest.get("high_risk_count") or 0)
    if unsatisfied > unsatisfied_limit(largest):
        problem_focus = "可用窗口或连续带宽不足"
    elif high_risk:
        problem_focus = "复用距离和保护频率风险上升"
    elif float(largest.get("quality_total") or 0) < quality_floor:
        problem_focus = "综合质量低于压测门槛"
    else:
        problem_focus = "容量与质量基本稳定"

    actions = []
    if not acceptable(largest):
        actions.append("将超出容量边界的任务按区域、任务类型或频段池拆分后求解。")
    if unsatisfied:
        actions.append("优先补充 S/C/Ku 等连续宽带窗口，或允许低优先级宽带装备部分满足。")
    if high_risk:
        actions.append("对雷达、回传和高功率通信装备提高复用保护距离并重新压测。")
    if not actions:
        actions.append("保留该容量画像作为后续传播模型和地理仿真接入后的回归基线。")

    return {
        "status": status,
        "decision": decision,
        "interactive_threshold_ms": interactive_threshold_ms,
        "quality_floor": quality_floor,
        "recommended": _capacity_row_summary(recommended),
        "largest": _capacity_row_summary(largest),
        "slowest": _capacity_row_summary(slowest) if slowest else {},
        "quality_drop": quality_drop,
        "satisfaction_drop": satisfaction_drop,
        "elapsed_growth": elapsed_growth,
        "problem_focus": problem_focus,
        "actions": actions,
    }


def _capacity_row_summary(row: dict | None) -> dict:
    if not row:
        return {}
    return {
        "scenario": row.get("scenario"),
        "scenario_name": row.get("scenario_name"),
        "objective": row.get("objective"),
        "objective_label": row.get("objective_label"),
        "task_unit_count": int(row.get("task_unit_count") or 0),
        "equipment_group_count": int(row.get("equipment_group_count") or 0),
        "equipment_sample_count": int(row.get("equipment_sample_count") or 0),
        "elapsed_ms": float(row.get("elapsed_ms") or 0),
        "quality_total": float(row.get("quality_total") or 0),
        "task_satisfaction_avg": float(row.get("task_satisfaction_avg") or 0),
        "unsatisfied_group_count": int(row.get("unsatisfied_group_count") or 0),
        "high_risk_count": int(row.get("high_risk_count") or 0),
    }


def _performance_recommendation_reason(row: dict) -> str:
    if int(row.get("unsatisfied_group_count") or 0):
        return f"该目标质量分最高，但仍有 {row.get('unsatisfied_group_count')} 个装备组未满足，需要扩展频段或降低部分需求。"
    if int(row.get("high_risk_count") or 0):
        return f"该目标保障率较高，但仍有 {row.get('high_risk_count')} 项高风险，适合作为人工复核候选。"
    return "该目标在当前场景下质量分最高，保障和风险指标相对均衡。"


def _performance_diagnostics(baseline_best: dict | None, stress_best: dict | None, slowest: dict | None) -> list[dict]:
    diagnostics = []
    if slowest:
        elapsed = float(slowest.get("elapsed_ms") or 0)
        diagnostics.append(
            {
                "severity": "低" if elapsed < 100 else "中",
                "title": "求解耗时余量",
                "detail": f"最大压力用例耗时 {elapsed:g} ms，当前工程近似模型具备本地交互式演示余量。",
                "suggestion": "后续接入更复杂传播模型或地形栅格后，应继续保留该基准测试作为回归门槛。",
            }
        )
    if baseline_best and stress_best:
        quality_drop = round(float(baseline_best.get("quality_total") or 0) - float(stress_best.get("quality_total") or 0), 1)
        satisfaction_drop = round(float(baseline_best.get("task_satisfaction_avg") or 0) - float(stress_best.get("task_satisfaction_avg") or 0), 1)
        diagnostics.append(
            {
                "severity": "高" if quality_drop >= 30 else "中" if quality_drop >= 15 else "低",
                "title": "规模放大质量变化",
                "detail": f"从基线到压力场景，最佳质量分下降 {quality_drop}，平均保障率变化 {satisfaction_drop} 个百分点。",
                "suggestion": "优先检查压力场景中的连续宽带装备、独占任务单元和保护窗口密集频段。",
            }
        )
    if stress_best:
        unsatisfied = int(stress_best.get("unsatisfied_group_count") or 0)
        high_risk = int(stress_best.get("high_risk_count") or 0)
        if unsatisfied:
            diagnostics.append(
                {
                    "severity": "高",
                    "title": "压力场景未满足装备组",
                    "detail": f"压力场景推荐目标仍有 {unsatisfied} 个装备组未满足，说明可用窗口或连续带宽成为主要瓶颈。",
                    "suggestion": "增加 S/C/Ku 备用连续窗口，或对低优先级宽带装备启用部分满足策略。",
                }
            )
        if high_risk:
            diagnostics.append(
                {
                    "severity": "中",
                    "title": "压力场景复用风险",
                    "detail": f"压力场景推荐目标存在 {high_risk} 项高风险，主要由近距离复用、保护频率和高功率装备叠加造成。",
                    "suggestion": "按任务区域分簇规划，并对雷达、回传和高功率通信装备提高保护距离约束。",
                }
            )
    return diagnostics


def _performance_leader_summary(baseline_best: dict | None, stress_best: dict | None, slowest: dict | None) -> str:
    if not stress_best:
        return "效能测试尚未形成压力场景结果。"
    elapsed = slowest.get("elapsed_ms", 0) if slowest else 0
    return (
        f"压力场景最大规模为 {stress_best.get('task_unit_count')} 个任务单元、{stress_best.get('equipment_group_count')} 个装备组、"
        f"{stress_best.get('equipment_sample_count')} 台套装备；推荐目标为“{stress_best.get('objective_label')}”，"
        f"保障率 {stress_best.get('task_satisfaction_avg')}%，质量分 {stress_best.get('quality_total')}，最大耗时 {elapsed} ms。"
    )


def _apply_demo_variant(scenario: str, task_units: list[dict], groups: list[dict], rules: list[dict]) -> None:
    if scenario == "urban_dense":
        for group in groups:
            if group["equipment_type"] in {"手持终端", "车载电台"}:
                group["count"] = int(group["count"] * 1.35)
                group["required_channels"] = int(group["required_channels"]) + 1
                group["raw_json"] = json.dumps({key: value for key, value in group.items() if key != "raw_json"}, ensure_ascii=False)
        rules.append(_rule("SR-UHF-URBAN-PROTECT", "保护", "UHF-SIM-1", "保护", 412.5, 413.0, 25, 25, 10, 50, "", "", "城区公共业务保护窗口仿真", "SIM_SCENARIO", "中"))
    elif scenario == "uav_priority":
        for unit in task_units:
            if unit["task_unit_id"] == "TU-UAV":
                unit["priority"] = 10
                unit["min_satisfaction_ratio"] = 0.95
                unit["preferred_band_groups"] = "L-SIM-1,S-SIM-1,S-SIM-2"
                unit["raw_json"] = json.dumps({key: value for key, value in unit.items() if key != "raw_json"}, ensure_ascii=False)
        groups.append(_group("EG-UAV-VIDEO", "TU-UAV", "无人机高清视频链路", 4, "双工", "空中机动", 2000, 12, 10, 0.5, -92, "OFDM", "双工", 2, "连续频段", "S-SIM-1", 9, 15, 2000, 1000))
        rules.append(_rule("SR-S-UAV-EXTRA", "可用", "S-SIM-2", "独占", 2250, 2270, 500, 3000, 100, 500, "无人机侦察单元", "无人机高清视频链路,无人机数传链路", "无人机链路备用仿真频段池", "SIM_SCENARIO", "低"))
    elif scenario == "radar_priority":
        for unit in task_units:
            if unit["task_unit_id"] == "TU-RAD":
                unit["priority"] = 10
                unit["min_satisfaction_ratio"] = 0.9
                unit["raw_json"] = json.dumps({key: value for key, value in unit.items() if key != "raw_json"}, ensure_ascii=False)
        for group in groups:
            if "雷达" in group["equipment_type"]:
                group["priority"] = 10
                group["raw_json"] = json.dumps({key: value for key, value in group.items() if key != "raw_json"}, ensure_ascii=False)
        rules.append(_rule("SR-C-RADAR-EXTRA", "可用", "C-SIM-2", "独占", 4520, 4570, 1000, 30000, 3000, 1000, "雷达探测单元", "低空探测雷达,跟踪类雷达仿真装备", "雷达任务备用连续窗口", "SIM_SCENARIO", "低"))
    elif scenario == "backhaul_limited":
        rules.extend(
            [
                _rule("SR-C-BH-LIMIT-FORBID", "禁用", "C-SIM-1", "禁用", 4412, 4428, 1000, 1000, 0, 1000, "", "", "回传频段临时禁用窗口仿真", "SIM_SCENARIO", "高"),
                _rule("SR-KU-BH-LIMIT-PROTECT", "保护", "Ku-SIM-1", "保护", 14532, 14540, 1000, 1000, 5, 1000, "", "", "卫星保护窗口密集仿真", "SIM_SCENARIO", "高"),
            ]
        )
    elif scenario == "high_protection_density":
        rules.extend(
            [
                _rule("SR-VHF-DENSE-PROTECT", "保护", "VHF-SIM-1", "保护", 140.0, 140.4, 12.5, 25, 10, 25, "", "", "密集保护频率仿真", "SIM_SCENARIO", "中"),
                _rule("SR-UHF-DENSE-PROTECT", "保护", "UHF-SIM-1", "保护", 425.0, 426.0, 25, 50, 10, 100, "", "", "密集保护频率仿真", "SIM_SCENARIO", "中"),
                _rule("SR-S-DENSE-PROTECT", "保护", "S-SIM-1", "保护", 2224.0, 2228.0, 500, 500, 100, 1000, "", "", "密集保护频率仿真", "SIM_SCENARIO", "高"),
                _rule("SR-C-DENSE-PROTECT", "保护", "C-SIM-1", "保护", 4430.0, 4438.0, 1000, 1000, 100, 2000, "", "", "密集保护频率仿真", "SIM_SCENARIO", "高"),
            ]
        )


def _normalized_parametric_payload(payload: dict) -> dict:
    defaults = dict(PARAMETRIC_SAMPLE_DEFAULTS)
    defaults.update(payload or {})
    return {
        "unit_count": max(5, min(60, int(defaults.get("unit_count") or PARAMETRIC_SAMPLE_DEFAULTS["unit_count"]))),
        "density_multiplier": max(0.6, min(3.5, float(defaults.get("density_multiplier") or PARAMETRIC_SAMPLE_DEFAULTS["density_multiplier"]))),
        "radar_ratio": max(0, min(45, int(defaults.get("radar_ratio") or 0))),
        "uav_ratio": max(0, min(45, int(defaults.get("uav_ratio") or 0))),
        "protection_density": max(0, min(5, int(defaults.get("protection_density") or 0))),
        "forbidden_density": max(0, min(5, int(defaults.get("forbidden_density") or 0))),
    }


def _parametric_template_codes(unit_count: int, radar_ratio: int, uav_ratio: int) -> list[str]:
    radar_count = max(0, round(unit_count * radar_ratio / 100))
    uav_count = max(0, round(unit_count * uav_ratio / 100))
    base_codes = ["CMD", "MOB", "BH", "TDL", "BB", "PNT", "ISR", "EW"]
    codes = ["RAD"] * radar_count + ["UAV"] * uav_count
    idx = 0
    while len(codes) < unit_count:
        codes.append(base_codes[idx % len(base_codes)])
        idx += 1
    return codes[:unit_count]


def _parametric_density_rules(protection_density: int, forbidden_density: int) -> list[dict]:
    rules = []
    protection_specs = [
        ("PX-PROTECT-UHF", "UHF-SIM-2", 440.0, 440.3, 25, "参数化保护频率窗口"),
        ("PX-PROTECT-L", "L-SIM-2", 1384.0, 1385.0, 100, "参数化数据链保护窗口"),
        ("PX-PROTECT-S", "S-SIM-2", 2276.0, 2279.0, 500, "参数化无人机/雷达保护窗口"),
        ("PX-PROTECT-C", "C-SIM-2", 4570.0, 4578.0, 1000, "参数化雷达保护窗口"),
        ("PX-PROTECT-PNT", "PNT-SIM-2", 1597.0, 1597.8, 50, "参数化导航授时保护窗口"),
    ]
    forbidden_specs = [
        ("PX-FORBID-VHF", "VHF-SIM-2", 150.0, 150.4, 12.5, "参数化 VHF 禁用窗口"),
        ("PX-FORBID-UHF", "UHF-SIM-2", 448.0, 449.2, 25, "参数化 UHF 禁用窗口"),
        ("PX-FORBID-S", "S-SIM-2", 2290.0, 2295.0, 500, "参数化 S 频段禁用窗口"),
        ("PX-FORBID-KU", "Ku-SIM-2", 14592.0, 14597.0, 1000, "参数化 Ku 频段禁用窗口"),
        ("PX-FORBID-EW", "EW-SIM-2", 2512.0, 2518.0, 500, "参数化电子对抗禁用窗口"),
    ]
    for idx, (rule_id, band, start, end, step, reason) in enumerate(protection_specs[:protection_density]):
        rules.append(_rule(rule_id, "保护", band, "保护", start, end, step, step, 10, step, "", "", reason, "SIM_PARAMETRIC", "高" if idx >= 2 else "中"))
    for idx, (rule_id, band, start, end, step, reason) in enumerate(forbidden_specs[:forbidden_density]):
        rules.append(_rule(rule_id, "禁用", band, "禁用", start, end, step, step, 0, step, "", "", reason, "SIM_PARAMETRIC", "高"))
    return rules


def _scaled_demo_records(prefix: str, unit_count: int, count_multiplier: float, template_codes: list[str] | None = None) -> tuple[list[dict], list[dict], list[dict]]:
    base_lat = 31.05
    base_lon = 121.18
    templates = _scaled_unit_templates()
    templates_by_code = {template["code"]: template for template in templates}
    task_units = []
    groups = []
    for idx in range(unit_count):
        if template_codes:
            template = templates_by_code.get(template_codes[idx % len(template_codes)], templates[idx % len(templates)])
        else:
            template = templates[idx % len(templates)]
        row = idx // 6
        col = idx % 6
        task_unit_id = f"TU-{prefix}-{idx + 1:02d}-{template['code']}"
        priority = max(5, min(10, int(template["priority"]) + (1 if idx % 7 == 0 else 0) - (1 if idx % 5 == 0 else 0)))
        task_units.append(
            _task_unit(
                task_unit_id,
                f"{template['name']}{idx + 1:02d}",
                template["unit_type"],
                base_lat + row * 0.075 + (idx % 2) * 0.018,
                base_lon + col * 0.085 + (idx % 3) * 0.012,
                float(template["radius"]) + (idx % 3) * 2,
                priority,
                template["relation"],
                template["bands"],
                float(template["ratio"]),
            )
        )
        for spec in template["groups"]:
            channel_boost = 1 if count_multiplier > 2 and idx % 4 == 0 and spec["assignment_mode"] != "宽带连续频段" else 0
            count = max(1, int(round(float(spec["count"]) * count_multiplier * (1 + (idx % 4) * 0.04))))
            groups.append(
                _group(
                    f"EG-{prefix}-{idx + 1:02d}-{spec['code']}",
                    task_unit_id,
                    spec["equipment_type"],
                    count,
                    spec["tx_rx_role"],
                    spec["mobility"],
                    spec["bandwidth_khz"],
                    spec["tx_power_w"],
                    spec["antenna_gain_dbi"],
                    spec["antenna_height_m"],
                    spec["receiver_sensitivity_dbm"],
                    spec["modulation"],
                    spec["duplex_mode"],
                    int(spec["required_channels"]) + channel_boost,
                    spec["assignment_mode"],
                    spec["preferred_band_group"],
                    max(5, min(10, int(spec["priority"]) + (1 if idx % 6 == 0 else 0))),
                    spec["protection_distance_km"],
                    spec["min_spacing_khz"],
                    spec["guard_band_khz"],
                )
            )
    rules = _demo_spectrum_rules()
    rules.extend(_scaled_spectrum_rules(prefix))
    return task_units, groups, rules


def _scaled_unit_templates() -> list[dict]:
    return [
        {
            "code": "CMD",
            "name": "指挥通信单元",
            "unit_type": "指挥通信单元",
            "relation": "可复用",
            "bands": "UHF-SIM-1,UHF-SIM-2,VHF-SIM-1,VHF-SIM-2",
            "radius": 9,
            "priority": 9,
            "ratio": 0.9,
            "groups": [
                _scaled_group_spec("BASE", "固定基站", 2, "双工", "固定", 25, 45, 8, 35, -112, "数字窄带", "双工", 2, "离散信道", "UHF-SIM-1", 9, 8, 50, 25),
                _scaled_group_spec("VEH", "指挥车", 5, "双工", "机动", 25, 35, 6, 12, -110, "数字窄带", "双工", 4, "离散信道", "UHF-SIM-2", 9, 6, 50, 25),
                _scaled_group_spec("RADIO", "车载电台", 22, "双工", "机动", 25, 25, 4, 3, -108, "FM/数字窄带", "单工", 6, "共享信道", "VHF-SIM-1", 8, 4, 25, 25),
                _scaled_group_spec("HAND", "手持终端", 40, "双工", "便携", 12.5, 5, 0, 1.5, -105, "数字窄带", "单工", 6, "共享信道", "VHF-SIM-2", 7, 2, 12.5, 12.5),
                _scaled_group_spec("RELAY", "中继设备", 3, "双工", "机动", 25, 35, 5, 8, -110, "数字窄带", "双工", 3, "收发频点对", "UHF-SIM-1", 8, 8, 100, 50),
            ],
        },
        {
            "code": "MOB",
            "name": "机动通信单元",
            "unit_type": "机动通信单元",
            "relation": "可复用",
            "bands": "UHF-SIM-1,UHF-SIM-2,VHF-SIM-1,VHF-SIM-2",
            "radius": 12,
            "priority": 8,
            "ratio": 0.82,
            "groups": [
                _scaled_group_spec("VEH-A", "车载电台", 28, "双工", "机动", 25, 30, 4, 3, -108, "数字窄带", "单工", 8, "离散信道", "UHF-SIM-1", 8, 5, 50, 25),
                _scaled_group_spec("VEH-B", "车载电台", 18, "双工", "机动", 25, 35, 4, 3, -108, "数字窄带", "单工", 6, "离散信道", "UHF-SIM-2", 8, 6, 50, 25),
                _scaled_group_spec("HAND", "手持终端", 46, "双工", "便携", 12.5, 5, 0, 1.5, -104, "数字窄带", "单工", 7, "共享信道", "VHF-SIM-1", 6, 2, 12.5, 12.5),
                _scaled_group_spec("RELAY", "中继设备", 4, "双工", "机动", 25, 35, 5, 8, -110, "数字窄带", "双工", 4, "收发频点对", "UHF-SIM-1", 8, 8, 100, 50),
                _scaled_group_spec("BASE", "固定基站", 2, "双工", "固定", 25, 50, 8, 25, -112, "数字窄带", "双工", 2, "离散信道", "UHF-SIM-2", 8, 8, 50, 25),
            ],
        },
        {
            "code": "UAV",
            "name": "无人机侦察单元",
            "unit_type": "无人机侦察单元",
            "relation": "独占",
            "bands": "L-SIM-1,L-SIM-2,S-SIM-1,S-SIM-2",
            "radius": 18,
            "priority": 8,
            "ratio": 0.78,
            "groups": [
                _scaled_group_spec("DATA", "无人机数传链路", 14, "双工", "空中机动", 1000, 8, 8, 0.5, -95, "OFDM", "双工", 4, "连续频段", "S-SIM-1", 8, 12, 1000, 500),
                _scaled_group_spec("CTRL", "无人机遥控链路", 5, "双工", "机动", 200, 5, 5, 2, -102, "扩频", "双工", 4, "离散信道", "L-SIM-1", 8, 10, 200, 100),
                _scaled_group_spec("GCS", "地面控制站", 2, "双工", "固定", 500, 20, 10, 8, -105, "扩频/OFDM", "双工", 2, "连续频段", "L-SIM-2", 9, 12, 500, 250),
                _scaled_group_spec("VIDEO", "无人机高清视频链路", 4, "双工", "空中机动", 2000, 12, 10, 0.5, -92, "OFDM", "双工", 2, "连续频段", "S-SIM-2", 9, 15, 2000, 1000),
                _scaled_group_spec("CTRL-B", "无人机遥控链路", 4, "双工", "机动", 200, 5, 5, 2, -102, "扩频", "双工", 3, "离散信道", "L-SIM-2", 7, 10, 200, 100),
            ],
        },
        {
            "code": "BH",
            "name": "回传保障单元",
            "unit_type": "回传保障单元",
            "relation": "可复用",
            "bands": "C-SIM-1,C-SIM-2,Ku-SIM-1,Ku-SIM-2,S-SIM-1",
            "radius": 20,
            "priority": 7,
            "ratio": 0.74,
            "groups": [
                _scaled_group_spec("MW-A", "微波回传链路", 5, "双工", "固定", 5000, 2, 22, 20, -85, "QAM", "双工", 3, "连续频段", "C-SIM-1", 7, 15, 5000, 1000),
                _scaled_group_spec("MW-B", "微波回传链路", 4, "双工", "固定", 8000, 3, 24, 18, -85, "QAM", "双工", 2, "连续频段", "C-SIM-2", 7, 16, 5000, 1000),
                _scaled_group_spec("SAT", "卫星通信终端", 4, "双工", "机动", 2000, 4, 18, 3, -90, "QPSK/8PSK", "双工", 2, "连续频段", "Ku-SIM-1", 7, 10, 2000, 1000),
                _scaled_group_spec("SAT-B", "卫星通信终端", 3, "双工", "固定", 3000, 5, 20, 4, -90, "QPSK/8PSK", "双工", 2, "连续频段", "Ku-SIM-2", 7, 10, 2000, 1000),
            ],
        },
        {
            "code": "RAD",
            "name": "雷达探测单元",
            "unit_type": "雷达探测单元",
            "relation": "独占",
            "bands": "S-SIM-1,S-SIM-2,C-SIM-1,C-SIM-2",
            "radius": 26,
            "priority": 9,
            "ratio": 0.68,
            "groups": [
                _scaled_group_spec("SHORT", "近程警戒雷达", 2, "发射", "固定", 10000, 1200, 28, 12, -80, "脉冲/调频", "单工", 2, "宽带连续频段", "S-SIM-1", 9, 25, 10000, 2000),
                _scaled_group_spec("SHORT-B", "近程警戒雷达", 2, "发射", "机动", 8000, 1000, 26, 10, -80, "脉冲/调频", "单工", 1, "宽带连续频段", "S-SIM-2", 8, 22, 8000, 2000),
                _scaled_group_spec("LOW", "低空探测雷达", 2, "发射", "固定", 15000, 1800, 32, 16, -82, "脉冲压缩", "单工", 3, "宽带连续频段", "C-SIM-1", 9, 30, 15000, 3000),
                _scaled_group_spec("TRACK", "跟踪类雷达仿真装备", 1, "发射", "固定", 20000, 2500, 35, 18, -84, "脉冲多普勒", "单工", 1, "宽带连续频段", "C-SIM-2", 10, 35, 20000, 5000),
            ],
        },
        {
            "code": "TDL",
            "name": "数据链协同单元",
            "unit_type": "数据链协同单元",
            "relation": "独占",
            "bands": "L-SIM-1,L-SIM-2,S-SIM-1,S-SIM-2",
            "radius": 16,
            "priority": 8,
            "ratio": 0.82,
            "groups": [
                _scaled_group_spec("TDL-AIR", "战术数据链终端", 8, "双工", "空中机动", 1000, 20, 8, 0.8, -98, "跳频/OFDM", "双工", 4, "连续频段", "L-SIM-2", 8, 14, 1000, 500),
                _scaled_group_spec("TDL-GND", "战术数据链终端", 12, "双工", "机动", 750, 25, 6, 4, -100, "跳频/OFDM", "双工", 4, "连续频段", "S-SIM-1", 8, 12, 750, 500),
                _scaled_group_spec("MESH", "宽带自组网节点", 16, "双工", "机动", 2000, 15, 6, 3, -95, "MANET/OFDM", "双工", 3, "连续频段", "S-SIM-2", 7, 10, 2000, 1000),
                _scaled_group_spec("GW", "固定基站", 2, "双工", "固定", 50, 55, 10, 24, -112, "数字窄带", "双工", 2, "离散信道", "UHF-SIM-2", 8, 8, 50, 25),
            ],
        },
        {
            "code": "BB",
            "name": "应急宽带单元",
            "unit_type": "应急宽带单元",
            "relation": "可复用",
            "bands": "L-SIM-2,S-SIM-2,C-SIM-1,C-SIM-2",
            "radius": 14,
            "priority": 7,
            "ratio": 0.76,
            "groups": [
                _scaled_group_spec("MESH-A", "宽带自组网节点", 24, "双工", "机动", 2500, 12, 5, 3, -94, "MANET/OFDM", "双工", 4, "连续频段", "S-SIM-2", 7, 10, 2500, 1000),
                _scaled_group_spec("MESH-B", "宽带自组网节点", 18, "双工", "机动", 1500, 10, 4, 2, -94, "MANET/OFDM", "双工", 3, "连续频段", "L-SIM-2", 7, 8, 1500, 750),
                _scaled_group_spec("MW-ACCESS", "微波回传链路", 3, "双工", "固定", 5000, 2, 22, 18, -85, "QAM", "双工", 2, "连续频段", "C-SIM-2", 7, 14, 5000, 1000),
                _scaled_group_spec("HAND-BB", "手持终端", 30, "双工", "便携", 25, 5, 0, 1.5, -104, "数字窄带", "单工", 4, "共享信道", "VHF-SIM-2", 6, 2, 25, 12.5),
            ],
        },
        {
            "code": "PNT",
            "name": "导航授时单元",
            "unit_type": "导航授时单元",
            "relation": "可复用",
            "bands": "PNT-SIM-1,PNT-SIM-2,L-SIM-1,L-SIM-2",
            "radius": 10,
            "priority": 8,
            "ratio": 0.9,
            "groups": [
                _scaled_group_spec("PNT-TERM", "导航授时终端", 26, "接收/低功率发射", "便携", 100, 2, 2, 1.5, -118, "扩频/授时", "单工", 4, "离散信道", "PNT-SIM-1", 8, 6, 100, 50),
                _scaled_group_spec("PNT-VEH", "导航授时终端", 12, "接收/低功率发射", "机动", 200, 3, 3, 3, -118, "扩频/授时", "单工", 3, "离散信道", "PNT-SIM-2", 8, 8, 200, 50),
                _scaled_group_spec("PNT-REF", "地面控制站", 2, "双工", "固定", 500, 10, 10, 12, -105, "扩频/OFDM", "双工", 2, "连续频段", "L-SIM-1", 8, 12, 500, 250),
            ],
        },
        {
            "code": "ISR",
            "name": "情报侦察单元",
            "unit_type": "情报侦察单元",
            "relation": "可复用",
            "bands": "RX-SIM-1,RX-SIM-2,L-SIM-1,S-SIM-1",
            "radius": 22,
            "priority": 8,
            "ratio": 0.78,
            "groups": [
                _scaled_group_spec("RX-WIDE", "频谱侦察接收机", 4, "接收", "机动", 3000, 0.5, 12, 10, -120, "宽带接收", "单工", 3, "连续频段", "RX-SIM-1", 8, 12, 1000, 500),
                _scaled_group_spec("RX-DIR", "被动测向站", 3, "接收", "固定", 1500, 0.2, 14, 16, -122, "宽带接收/测向", "单工", 3, "连续频段", "RX-SIM-2", 8, 18, 1000, 500),
                _scaled_group_spec("UAV-RX", "无人机数传链路", 6, "双工", "空中机动", 1000, 8, 8, 0.5, -95, "OFDM", "双工", 2, "连续频段", "S-SIM-1", 7, 12, 1000, 500),
                _scaled_group_spec("CTRL-RX", "无人机遥控链路", 3, "双工", "机动", 200, 5, 5, 2, -102, "扩频", "双工", 2, "离散信道", "L-SIM-1", 7, 10, 200, 100),
            ],
        },
        {
            "code": "EW",
            "name": "电子对抗单元",
            "unit_type": "电子对抗单元",
            "relation": "独占",
            "bands": "EW-SIM-1,EW-SIM-2,S-SIM-1,S-SIM-2",
            "radius": 24,
            "priority": 9,
            "ratio": 0.7,
            "groups": [
                _scaled_group_spec("JAM-WIDE", "电子压制设备", 3, "发射", "机动", 4000, 180, 18, 8, -80, "宽带噪声/扫频", "单工", 2, "连续频段", "EW-SIM-1", 9, 28, 2000, 1000),
                _scaled_group_spec("JAM-NAR", "诱骗干扰设备", 4, "发射", "机动", 500, 60, 14, 6, -85, "窄带诱骗", "单工", 4, "离散信道", "EW-SIM-2", 8, 20, 500, 250),
                _scaled_group_spec("RX-EW", "频谱侦察接收机", 3, "接收", "机动", 2500, 0.5, 12, 8, -120, "宽带接收", "单工", 2, "连续频段", "RX-SIM-1", 8, 14, 1000, 500),
                _scaled_group_spec("TDL-EW", "战术数据链终端", 6, "双工", "机动", 750, 20, 6, 4, -100, "跳频/OFDM", "双工", 2, "连续频段", "S-SIM-2", 8, 12, 750, 500),
            ],
        },
    ]


def _scaled_group_spec(
    code: str,
    equipment_type: str,
    count: int,
    tx_rx_role: str,
    mobility: str,
    bandwidth_khz: float,
    tx_power_w: float,
    antenna_gain_dbi: float,
    antenna_height_m: float,
    receiver_sensitivity_dbm: float,
    modulation: str,
    duplex_mode: str,
    required_channels: int,
    assignment_mode: str,
    preferred_band_group: str,
    priority: int,
    protection_distance_km: float,
    min_spacing_khz: float,
    guard_band_khz: float,
) -> dict:
    return {
        "code": code,
        "equipment_type": equipment_type,
        "count": count,
        "tx_rx_role": tx_rx_role,
        "mobility": mobility,
        "bandwidth_khz": bandwidth_khz,
        "tx_power_w": tx_power_w,
        "antenna_gain_dbi": antenna_gain_dbi,
        "antenna_height_m": antenna_height_m,
        "receiver_sensitivity_dbm": receiver_sensitivity_dbm,
        "modulation": modulation,
        "duplex_mode": duplex_mode,
        "required_channels": required_channels,
        "assignment_mode": assignment_mode,
        "preferred_band_group": preferred_band_group,
        "priority": priority,
        "protection_distance_km": protection_distance_km,
        "min_spacing_khz": min_spacing_khz,
        "guard_band_khz": guard_band_khz,
    }


def _scaled_spectrum_rules(prefix: str) -> list[dict]:
    return [
        _rule(f"SR-{prefix}-VHF-AV", "可用", "VHF-SIM-2", "可复用", 144, 156, 12.5, 25, 30, 12.5, "指挥通信单元,机动通信单元", "手持终端,车载电台", "扩展 VHF 窄带通信仿真频段池", "SIM_PERFORMANCE", "低"),
        _rule(f"SR-{prefix}-UHF-AV", "可用", "UHF-SIM-2", "可复用", 430, 455, 25, 50, 80, 25, "指挥通信单元,机动通信单元,数据链协同单元", "固定基站,指挥车,车载电台,中继设备", "扩展 UHF 通信仿真频段池", "SIM_PERFORMANCE", "低"),
        _rule(f"SR-{prefix}-L-AV", "可用", "L-SIM-2", "独占", 1372, 1398, 100, 5000, 60, 100, "无人机侦察单元,数据链协同单元,应急宽带单元,导航授时单元,情报侦察单元", "无人机遥控链路,地面控制站,战术数据链终端,宽带自组网节点,导航授时终端", "扩展 L 频段控制/数据链仿真池", "SIM_PERFORMANCE", "低"),
        _rule(f"SR-{prefix}-S-AV", "可用", "S-SIM-2", "独占", 2250, 2300, 500, 15000, 1500, 500, "无人机侦察单元,雷达探测单元,数据链协同单元,应急宽带单元,电子对抗单元", "无人机数传链路,无人机高清视频链路,近程警戒雷达,战术数据链终端,宽带自组网节点,电子压制设备,诱骗干扰设备", "扩展 S 频段数据/雷达/电子对抗仿真池", "SIM_PERFORMANCE", "低"),
        _rule(f"SR-{prefix}-C-AV", "可用", "C-SIM-2", "独占", 4520, 4620, 1000, 30000, 3200, 1000, "回传保障单元,雷达探测单元,应急宽带单元", "微波回传链路,低空探测雷达,跟踪类雷达仿真装备,宽带自组网节点", "扩展 C 频段回传/雷达/宽带仿真池", "SIM_PERFORMANCE", "低"),
        _rule(f"SR-{prefix}-KU-AV", "可用", "Ku-SIM-2", "可复用", 14560, 14620, 1000, 5000, 25, 1000, "回传保障单元", "卫星通信终端", "扩展 Ku 频段卫星通信仿真池", "SIM_PERFORMANCE", "低"),
        _rule(f"SR-{prefix}-PNT-AV", "可用", "PNT-SIM-2", "可复用", 1586, 1606, 50, 500, 10, 50, "导航授时单元", "导航授时终端", "扩展导航授时仿真频段池", "SIM_PERFORMANCE", "低"),
        _rule(f"SR-{prefix}-RX-AV", "可用", "RX-SIM-2", "可复用", 930, 960, 100, 5000, 5, 100, "情报侦察单元,电子对抗单元", "频谱侦察接收机,被动测向站", "扩展侦察接收仿真频段池", "SIM_PERFORMANCE", "低"),
        _rule(f"SR-{prefix}-EW-AV", "可用", "EW-SIM-2", "独占", 2486, 2526, 500, 5000, 300, 500, "电子对抗单元", "电子压制设备,诱骗干扰设备", "扩展电子对抗仿真频段池", "SIM_PERFORMANCE", "低"),
        _rule(f"SR-{prefix}-UHF-FORBID", "禁用", "UHF-SIM-2", "禁用", 438, 439, 25, 25, 0, 25, "", "", "大型演训临时禁用窗口仿真", "SIM_PERFORMANCE", "高"),
        _rule(f"SR-{prefix}-S-PROTECT", "保护", "S-SIM-2", "保护", 2268, 2272, 500, 500, 100, 1000, "", "", "S 频段保护窗口仿真", "SIM_PERFORMANCE", "高"),
        _rule(f"SR-{prefix}-C-PROTECT", "保护", "C-SIM-2", "保护", 4550, 4558, 1000, 1000, 100, 2000, "", "", "C 频段保护窗口仿真", "SIM_PERFORMANCE", "中"),
        _rule(f"SR-{prefix}-KU-FORBID", "禁用", "Ku-SIM-2", "禁用", 14580, 14584, 1000, 1000, 0, 1000, "", "", "Ku 频段临时禁用窗口仿真", "SIM_PERFORMANCE", "高"),
        _rule(f"SR-{prefix}-PNT-PROTECT", "保护", "PNT-SIM-2", "保护", 1594, 1595, 50, 50, 5, 100, "", "", "导航授时保护窗口仿真", "SIM_PERFORMANCE", "高"),
        _rule(f"SR-{prefix}-EW-FORBID", "禁用", "EW-SIM-2", "禁用", 2502, 2505, 500, 500, 0, 500, "", "", "电子对抗临时禁用窗口仿真", "SIM_PERFORMANCE", "高"),
    ]


def _high_density_spectrum_rules() -> list[dict]:
    rows = [
        _rule("SR-HD-VHF-AV", "可用", "VHF-SIM-1", "可复用", 138, 144, 12.5, 25, 30, 12.5, "指挥通信单元,机动通信单元", "手持终端,车载电台,中继设备", "高密度演训 VHF 窄带通信池", "SIM_HIGH_DENSITY", "低"),
        _rule("SR-HD-UHF-AV", "可用", "UHF-SIM-1", "可复用", 410, 430, 25, 50, 50, 25, "指挥通信单元,机动通信单元", "固定基站,指挥车,车载电台,中继设备", "高密度演训 UHF 指挥与机动通信池", "SIM_HIGH_DENSITY", "低"),
        _rule("SR-HD-L-AV", "可用", "L-SIM-1", "独占", 1350, 1370, 100, 5000, 60, 100, "无人机侦察单元,导航授时单元,机动通信单元", "无人机遥控链路,地面控制站,导航授时终端,中继设备", "高密度演训 L 频段控制链路池", "SIM_HIGH_DENSITY", "低"),
        _rule("SR-HD-S-AV", "可用", "S-SIM-1", "独占", 2200, 2240, 500, 10000, 1500, 500, "无人机侦察单元,雷达探测单元,电子对抗单元", "无人机数传链路,无人机高清视频链路,低空探测雷达,近程警戒雷达,电子压制设备", "高密度演训 S 频段数据/雷达共享池", "SIM_HIGH_DENSITY", "低"),
        _rule("SR-HD-C-AV", "可用", "C-SIM-1", "独占", 4400, 4500, 1000, 20000, 2500, 1000, "回传保障单元,雷达探测单元", "微波回传链路,低空探测雷达,跟踪类雷达仿真装备", "高密度演训 C 频段回传/雷达池", "SIM_HIGH_DENSITY", "低"),
        _rule("SR-HD-KU-AV", "可用", "Ku-SIM-1", "可复用", 14500, 14550, 1000, 5000, 20, 1000, "回传保障单元", "卫星通信终端", "高密度演训 Ku 卫星回传池", "SIM_HIGH_DENSITY", "低"),
        _rule("SR-HD-PNT-AV", "可用", "PNT-SIM-1", "可复用", 1565, 1585, 50, 500, 10, 50, "导航授时单元", "导航授时终端", "高密度演训导航授时池", "SIM_HIGH_DENSITY", "低"),
        _rule("SR-HD-EW-AV", "可用", "EW-SIM-1", "独占", 2400, 2485, 500, 5000, 300, 500, "电子对抗单元,无人机侦察单元", "电子压制设备,无人机数传链路", "高密度演训电磁环境仿真池", "SIM_HIGH_DENSITY", "低"),
    ]
    rows.extend(
        [
            _rule("SR-HD-VHF-PROTECT", "保护", "VHF-SIM-1", "保护", 140.0, 140.2, 12.5, 25, 10, 25, "", "", "既有保障通信保护窗口", "SIM_HIGH_DENSITY", "中"),
            _rule("SR-HD-VHF-FORBID", "禁用", "VHF-SIM-1", "禁用", 142.6, 143.0, 12.5, 25, 0, 25, "", "", "演训区域 VHF 临时禁用窗口", "SIM_HIGH_DENSITY", "高"),
            _rule("SR-HD-UHF-FORBID", "禁用", "UHF-SIM-1", "禁用", 418.0, 419.0, 25, 25, 0, 25, "", "", "UHF 机动通信冲突避让窗口", "SIM_HIGH_DENSITY", "高"),
            _rule("SR-HD-UHF-PROTECT", "保护", "UHF-SIM-1", "保护", 421.0, 422.0, 25, 25, 10, 100, "", "", "UHF 固定业务保护窗口", "SIM_HIGH_DENSITY", "中"),
            _rule("SR-HD-L-PROTECT", "保护", "L-SIM-1", "保护", 1358.0, 1362.0, 100, 100, 10, 500, "", "", "L 频段遥测保护窗口", "SIM_HIGH_DENSITY", "高"),
            _rule("SR-HD-L-FORBID", "禁用", "L-SIM-1", "禁用", 1367.0, 1370.0, 100, 100, 0, 200, "", "", "L 频段末端临时禁用窗口", "SIM_HIGH_DENSITY", "高"),
            _rule("SR-HD-S-PROTECT", "保护", "S-SIM-1", "保护", 2210.0, 2212.0, 500, 500, 100, 1000, "", "", "S 频段测控保护窗口", "SIM_HIGH_DENSITY", "高"),
            _rule("SR-HD-S-FORBID", "禁用", "S-SIM-1", "禁用", 2218.0, 2224.0, 500, 500, 0, 1000, "", "", "S 频段雷达/数据链冲突禁用窗口", "SIM_HIGH_DENSITY", "高"),
            _rule("SR-HD-C-PROTECT", "保护", "C-SIM-1", "保护", 4450.0, 4460.0, 1000, 1000, 100, 2000, "", "", "C 频段雷达保护窗口", "SIM_HIGH_DENSITY", "中"),
            _rule("SR-HD-C-FORBID", "禁用", "C-SIM-1", "禁用", 4475.0, 4490.0, 1000, 1000, 0, 1000, "", "", "C 频段回传与探测冲突禁用窗口", "SIM_HIGH_DENSITY", "高"),
            _rule("SR-HD-KU-PROTECT", "保护", "Ku-SIM-1", "保护", 14520.0, 14530.0, 1000, 1000, 5, 1000, "", "", "Ku 卫星链路保护窗口", "SIM_HIGH_DENSITY", "中"),
            _rule("SR-HD-PNT-PROTECT", "保护", "PNT-SIM-1", "保护", 1574.0, 1576.0, 50, 50, 5, 100, "", "", "导航授时保护窗口", "SIM_HIGH_DENSITY", "高"),
            _rule("SR-HD-EW-FORBID", "禁用", "EW-SIM-1", "禁用", 2440.0, 2460.0, 500, 500, 0, 500, "", "", "电磁环境仿真临时禁用窗口", "SIM_HIGH_DENSITY", "高"),
            _rule("SR-HD-EW-PROTECT", "保护", "EW-SIM-1", "保护", 2420.0, 2425.0, 500, 500, 20, 500, "", "", "2.4 GHz 业务保护窗口", "SIM_HIGH_DENSITY", "中"),
        ]
    )
    return rows


def _demo_spectrum_rules() -> list[dict]:
    rows = []
    rows.extend(
        [
            _rule("SR-VHF-AV", "可用", "VHF-SIM-1", "可复用", 138, 144, 12.5, 25, 30, 12.5, "指挥通信单元,机动通信单元", "手持终端,车载电台", "仿真 VHF 窄带通信频段池", "SIM_PUBLIC_REFERENCE", "低"),
            _rule("SR-UHF-AV", "可用", "UHF-SIM-1", "可复用", 410, 430, 25, 50, 50, 25, "指挥通信单元,机动通信单元", "固定基站,指挥车,车载电台,中继设备", "仿真 UHF 通信频段池", "SIM_PUBLIC_REFERENCE", "低"),
            _rule("SR-L-AV", "可用", "L-SIM-1", "独占", 1350, 1370, 100, 5000, 60, 100, "无人机侦察单元,数据链协同单元,导航授时单元,情报侦察单元", "无人机遥控链路,地面控制站,战术数据链终端,宽带自组网节点,导航授时终端", "仿真 L 频段控制/数据链频段池", "SIM_PUBLIC_REFERENCE", "低"),
            _rule("SR-S-AV", "可用", "S-SIM-1", "独占", 2200, 2240, 500, 10000, 1500, 500, "无人机侦察单元,雷达探测单元,数据链协同单元,应急宽带单元,电子对抗单元,情报侦察单元", "无人机数传链路,无人机高清视频链路,近程警戒雷达,战术数据链终端,宽带自组网节点,电子压制设备,诱骗干扰设备", "仿真 S 频段数据/雷达/电子对抗频段池", "SIM_PUBLIC_REFERENCE", "低"),
            _rule("SR-C-AV", "可用", "C-SIM-1", "独占", 4400, 4500, 1000, 20000, 2500, 1000, "回传保障单元,雷达探测单元,应急宽带单元", "微波回传链路,低空探测雷达,跟踪类雷达仿真装备,宽带自组网节点", "仿真 C 频段回传/雷达/宽带频段池", "SIM_PUBLIC_REFERENCE", "低"),
            _rule("SR-KU-AV", "可用", "Ku-SIM-1", "可复用", 14500, 14550, 1000, 5000, 20, 1000, "回传保障单元", "卫星通信终端", "仿真 Ku 频段卫星通信池", "SIM_PUBLIC_REFERENCE", "低"),
            _rule("SR-PNT-AV", "可用", "PNT-SIM-1", "可复用", 1565, 1585, 50, 500, 10, 50, "导航授时单元", "导航授时终端", "仿真导航授时频段池", "SIM_PUBLIC_REFERENCE", "低"),
            _rule("SR-RX-AV", "可用", "RX-SIM-1", "可复用", 900, 930, 100, 5000, 5, 100, "情报侦察单元,电子对抗单元", "频谱侦察接收机,被动测向站", "仿真侦察接收频段池", "SIM_PUBLIC_REFERENCE", "低"),
            _rule("SR-EW-AV", "可用", "EW-SIM-1", "独占", 2400, 2485, 500, 5000, 300, 500, "电子对抗单元", "电子压制设备,诱骗干扰设备", "仿真电子对抗频段池", "SIM_PUBLIC_REFERENCE", "低"),
        ]
    )
    rows.extend(
        [
            _rule("SR-UHF-FORBID", "禁用", "UHF-SIM-1", "禁用", 418, 418.5, 25, 25, 0, 25, "", "", "演训区域仿真禁用窗口", "SIM_PUBLIC_REFERENCE", "高"),
            _rule("SR-C-FORBID", "禁用", "C-SIM-1", "禁用", 4475, 4478, 1000, 1000, 0, 1000, "", "", "演训区域仿真禁用窗口", "SIM_PUBLIC_REFERENCE", "高"),
            _rule("SR-UHF-PROTECT", "保护", "UHF-SIM-1", "保护", 421, 421.5, 25, 25, 10, 100, "", "", "公开业务保护建模示例，规划需避让保护带", "SIM_PUBLIC_REFERENCE", "中"),
            _rule("SR-L-PROTECT", "保护", "L-SIM-1", "保护", 1358, 1360, 100, 100, 10, 500, "", "", "导航/遥测类保护建模示例", "SIM_PUBLIC_REFERENCE", "高"),
            _rule("SR-S-PROTECT", "保护", "S-SIM-1", "保护", 2210, 2212, 500, 500, 100, 1000, "", "", "卫星测控保护建模示例", "SIM_PUBLIC_REFERENCE", "高"),
            _rule("SR-C-PROTECT", "保护", "C-SIM-1", "保护", 4450, 4455, 1000, 1000, 100, 2000, "", "", "雷达保护建模示例", "SIM_PUBLIC_REFERENCE", "中"),
            _rule("SR-KU-PROTECT", "保护", "Ku-SIM-1", "保护", 14520, 14524, 1000, 1000, 5, 1000, "", "", "卫星链路保护建模示例", "SIM_PUBLIC_REFERENCE", "中"),
            _rule("SR-PNT-PROTECT", "保护", "PNT-SIM-1", "保护", 1574, 1575, 50, 50, 5, 100, "", "", "导航授时保护建模示例", "SIM_PUBLIC_REFERENCE", "高"),
            _rule("SR-EW-FORBID", "禁用", "EW-SIM-1", "禁用", 2440, 2445, 500, 500, 0, 500, "", "", "电子对抗临时禁用窗口仿真", "SIM_PUBLIC_REFERENCE", "高"),
        ]
    )
    return rows


def _available_segments_by_band(rules: list[dict]) -> dict[str, list[Segment]]:
    available: dict[str, list[Segment]] = defaultdict(list)
    blockers: dict[str, list[Segment]] = defaultdict(list)
    for rule in rules:
        band = rule.get("band_group")
        if not band:
            continue
        segment = Segment(float(rule.get("start_mhz") or 0), float(rule.get("end_mhz") or 0))
        if segment.end <= segment.start:
            continue
        if rule.get("rule_type") == "可用":
            available[band].append(segment)
        elif rule.get("rule_type") in {"禁用", "保护"}:
            guard = float(rule.get("guard_band_khz") or 0) / 1000
            blockers[band].append(Segment(segment.start - guard, segment.end + guard))

    result: dict[str, list[Segment]] = {}
    for band, segments in available.items():
        clean: list[Segment] = []
        for segment in segments:
            pieces = [segment]
            for blocker in blockers.get(band, []):
                next_pieces: list[Segment] = []
                for piece in pieces:
                    next_pieces.extend(_subtract_segment(piece, blocker))
                pieces = next_pieces
            clean.extend(piece for piece in pieces if piece.width_mhz > 0.0001)
        result[band] = sorted(clean, key=lambda item: item.start)
    return result


def _allocate_group(
    group: dict,
    unit: dict,
    preferred_bands: list[str],
    rules_by_band: dict[str, list[Segment]],
    spectrum_rules: list[dict],
    consumption: dict[tuple[str, str], list[Segment]],
    objective: str,
) -> dict:
    requested_count = int(group.get("count") or 0)
    requested_channels = max(1, int(group.get("required_channels") or 1))
    mode = group.get("assignment_mode") or "离散信道"
    best: dict | None = None
    skipped_reasons: list[str] = []
    for band in preferred_bands:
        band_rules = _available_rules_for_band(spectrum_rules, band)
        constraint_reason = _band_constraint_reason(group, unit, band_rules, band)
        if constraint_reason:
            skipped_reasons.append(constraint_reason)
            continue
        segments = rules_by_band.get(band, [])
        if not segments:
            skipped_reasons.append(f"{band} 被禁用/保护窗口切分后无可用资源")
            continue
        relation = unit.get("spectrum_relation") or "独占"
        available_segments = _segments_after_consumption(segments, consumption.get((band, "exclusive"), [])) if relation == "独占" else list(segments)
        allocation = _allocate_in_band(group, unit, band, available_segments, objective)
        if allocation and (best is None or allocation["assigned_channels"] > best["assigned_channels"]):
            best = allocation
        if best and best["assigned_channels"] >= requested_channels:
            break

    if best is None:
        return {
            "task_unit_id": group["task_unit_id"],
            "equipment_group_id": group["equipment_group_id"],
            "equipment_type": group["equipment_type"],
            "assignment_mode": mode,
            "band_group": preferred_bands[0] if preferred_bands else None,
            "assigned_resource": "",
            "requested_count": requested_count,
            "satisfied_count": 0,
            "requested_channels": requested_channels,
            "assigned_channels": 0,
            "satisfaction_ratio": 0,
            "status": "未满足",
            "risk_score": 100,
            "risk_level": "高",
            "reason": skipped_reasons[0] if skipped_reasons else "可用频段池不足或被禁用/保护频率切分后无可用资源",
            "decision_notes": "建议扩大频段池、启用备用频段或降低该装备组所需带宽/信道数",
        }

    assigned_channels = best["assigned_channels"]
    ratio = min(1.0, assigned_channels / requested_channels)
    satisfied_count = math.floor(requested_count * ratio)
    status = "完全满足" if ratio >= 0.999 else "部分满足" if ratio > 0 else "未满足"
    reason = "已满足装备组用频需求" if status == "完全满足" else _partial_reason(group, assigned_channels, requested_channels)
    assignment = {
        "task_unit_id": group["task_unit_id"],
        "equipment_group_id": group["equipment_group_id"],
        "equipment_type": group["equipment_type"],
        "assignment_mode": mode,
        "band_group": best["band_group"],
        "assigned_resource": best["resource"],
        "requested_count": requested_count,
        "satisfied_count": satisfied_count,
        "requested_channels": requested_channels,
        "assigned_channels": assigned_channels,
        "satisfaction_ratio": round(ratio, 4),
        "status": status,
        "risk_score": 0 if status == "完全满足" else 45 if status == "部分满足" else 90,
        "risk_level": "低" if status == "完全满足" else "中" if status == "部分满足" else "高",
        "reason": reason,
        "decision_notes": _decision_note(group, best["band_group"], objective, status),
    }
    if (unit.get("spectrum_relation") or "独占") == "独占":
        consumption[(best["band_group"], "exclusive")].extend(_parse_resource_segments(best["resource"]))
    return assignment


def _allocate_in_band(group: dict, unit: dict, band: str, segments: list[Segment], objective: str) -> dict | None:
    if not segments:
        return None
    requested_channels = max(1, int(group.get("required_channels") or 1))
    bandwidth_mhz = max(0.0001, float(group.get("bandwidth_khz") or 25) / 1000)
    guard_mhz = max(float(group.get("guard_band_khz") or 0), float(group.get("min_spacing_khz") or 0)) / 1000
    mode = group.get("assignment_mode") or "离散信道"

    if mode in {"连续频段", "宽带连续频段"}:
        per_channel_width = bandwidth_mhz + guard_mhz
        resources = []
        for segment in sorted(segments, key=lambda item: item.width_mhz if objective == "minimize_bandwidth" else item.start):
            if "雷达" in str(group.get("equipment_type", "")) and segment.width_mhz < bandwidth_mhz + guard_mhz:
                continue
            cursor = segment.start
            while cursor + bandwidth_mhz <= segment.end + 1e-9 and len(resources) < requested_channels:
                resources.append(Segment(cursor, cursor + bandwidth_mhz))
                cursor += per_channel_width
            if len(resources) >= requested_channels:
                break
        if not resources:
            return None
        return {"band_group": band, "assigned_channels": len(resources), "resource": "; ".join(_fmt_segment(item) for item in resources)}

    step_mhz = max(0.001, max(float(group.get("min_spacing_khz") or 0), bandwidth_mhz * 1000) / 1000)
    if mode == "收发频点对":
        duplex_spacing_mhz = max(step_mhz, guard_mhz, bandwidth_mhz)
        pairs = []
        for segment in segments:
            cursor = _ceil_to_step(segment.start, step_mhz)
            while cursor + duplex_spacing_mhz <= segment.end + 1e-9 and len(pairs) < requested_channels:
                tx = round(cursor, 6)
                rx = round(cursor + duplex_spacing_mhz, 6)
                pairs.append(f"{tx:.6f}/{rx:.6f} MHz")
                cursor += duplex_spacing_mhz + max(step_mhz, bandwidth_mhz)
            if len(pairs) >= requested_channels:
                break
        if not pairs:
            return None
        return {"band_group": band, "assigned_channels": len(pairs), "resource": "; ".join(pairs)}

    freqs = []
    for segment in segments:
        cursor = _ceil_to_step(segment.start, step_mhz)
        while cursor <= segment.end + 1e-9 and len(freqs) < requested_channels:
            freqs.append(round(cursor, 6))
            cursor += step_mhz
        if len(freqs) >= requested_channels:
            break
    if not freqs:
        return None
    resource = ", ".join(f"{item:.6f} MHz" for item in freqs)
    return {"band_group": band, "assigned_channels": len(freqs), "resource": resource}


def _risk_items_for_assignment(assignment: dict, group: dict, unit: dict, protected: list[dict], forbidden: list[dict]) -> list[dict]:
    items = []
    if assignment["status"] != "完全满足":
        items.append(
            {
                "risk_type": "部分满足",
                "severity": "中" if assignment["status"] == "部分满足" else "高",
                "task_unit_a": assignment["task_unit_id"],
                "equipment_group_a": assignment["equipment_group_id"],
                "task_unit_b": None,
                "equipment_group_b": None,
                "resource_a": assignment["assigned_resource"],
                "resource_b": None,
                "score": assignment["risk_score"],
                "reason": assignment["reason"],
            }
        )

    segments = _parse_resource_segments(assignment.get("assigned_resource") or "")
    for rule in protected:
        if rule.get("band_group") != assignment.get("band_group"):
            continue
        guard_mhz = float(rule.get("guard_band_khz") or 0) / 1000
        protected_segment = Segment(float(rule.get("start_mhz") or 0) - guard_mhz, float(rule.get("end_mhz") or 0) + guard_mhz)
        if any(_overlaps(segment, protected_segment) for segment in segments):
            severity = rule.get("severity") or "中"
            items.append(
                {
                    "risk_type": "保护频率靠近",
                    "severity": severity,
                    "task_unit_a": assignment["task_unit_id"],
                    "equipment_group_a": assignment["equipment_group_id"],
                    "task_unit_b": None,
                    "equipment_group_b": None,
                    "resource_a": assignment["assigned_resource"],
                    "resource_b": f"{rule.get('start_mhz')}-{rule.get('end_mhz')} MHz",
                    "score": 80 if severity == "高" else 45,
                    "reason": f"靠近保护频率：{rule.get('reason')}",
                }
            )
    for rule in forbidden:
        if rule.get("band_group") != assignment.get("band_group"):
            continue
        forbidden_segment = Segment(float(rule.get("start_mhz") or 0), float(rule.get("end_mhz") or 0))
        if any(_overlaps(segment, forbidden_segment) for segment in segments):
            items.append(
                {
                    "risk_type": "禁用频率冲突",
                    "severity": "高",
                    "task_unit_a": assignment["task_unit_id"],
                    "equipment_group_a": assignment["equipment_group_id"],
                    "task_unit_b": None,
                    "equipment_group_b": None,
                    "resource_a": assignment["assigned_resource"],
                    "resource_b": f"{rule.get('start_mhz')}-{rule.get('end_mhz')} MHz",
                    "score": 100,
                    "reason": f"落入禁用频率：{rule.get('reason')}",
                }
            )
    return items


def _reuse_risks(assignments: list[dict], task_units: list[dict], equipment_groups: list[dict]) -> list[dict]:
    units = {item["task_unit_id"]: item for item in task_units}
    groups = {item["equipment_group_id"]: item for item in equipment_groups}
    segments_by_group = {
        item["equipment_group_id"]: _parse_resource_segments(item.get("assigned_resource") or "")
        for item in assignments
    }
    items: list[dict] = []
    for a, b in combinations(assignments, 2):
        if a.get("band_group") != b.get("band_group") or not a.get("assigned_resource") or not b.get("assigned_resource"):
            continue
        segments_a = segments_by_group.get(a["equipment_group_id"], [])
        segments_b = segments_by_group.get(b["equipment_group_id"], [])
        if not segments_a or not segments_b:
            continue
        unit_a = units.get(a["task_unit_id"], {})
        unit_b = units.get(b["task_unit_id"], {})
        group_a = groups.get(a["equipment_group_id"], {})
        group_b = groups.get(b["equipment_group_id"], {})
        items.extend(_pair_spectrum_risks(a, b, unit_a, unit_b, group_a, group_b, segments_a, segments_b))
    items.extend(_intermodulation_risks(assignments, units, groups))
    return items


def _pair_spectrum_risks(
    assignment_a: dict,
    assignment_b: dict,
    unit_a: dict,
    unit_b: dict,
    group_a: dict,
    group_b: dict,
    segments_a: list[Segment],
    segments_b: list[Segment],
) -> list[dict]:
    gap_mhz, overlap_mhz = _segment_relation_metrics(segments_a, segments_b)
    distance = haversine_km(
        unit_a.get("area_center_lat"),
        unit_a.get("area_center_lon"),
        unit_b.get("area_center_lat"),
        unit_b.get("area_center_lon"),
    )
    protection = max(float(group_a.get("protection_distance_km") or 0), float(group_b.get("protection_distance_km") or 0))
    spacing_khz = max(
        float(group_a.get("min_spacing_khz") or 0),
        float(group_b.get("min_spacing_khz") or 0),
        float(group_a.get("guard_band_khz") or 0),
        float(group_b.get("guard_band_khz") or 0),
    )
    combined_power = float(group_a.get("tx_power_w") or 0) + float(group_b.get("tx_power_w") or 0)
    max_priority = max(int(group_a.get("priority") or 1), int(group_b.get("priority") or 1), int(unit_a.get("priority") or 1), int(unit_b.get("priority") or 1))
    distance_pressure = 0.0
    if distance is not None and protection > 0:
        distance_pressure = max(0.0, 1 - distance / protection)
    power_pressure = min(1.0, math.log10(max(combined_power, 1)) / 3)
    priority_pressure = min(1.0, max_priority / 5)
    common = {
        "task_unit_a": assignment_a["task_unit_id"],
        "equipment_group_a": assignment_a["equipment_group_id"],
        "task_unit_b": assignment_b["task_unit_id"],
        "equipment_group_b": assignment_b["equipment_group_id"],
        "resource_a": assignment_a["assigned_resource"],
        "resource_b": assignment_b["assigned_resource"],
    }
    distance_text = f"{distance:.1f} km" if distance is not None else "未提供坐标"
    risks: list[dict] = []

    if overlap_mhz > 0:
        occupied_width = max(
            sum(item.width_mhz for item in segments_a),
            sum(item.width_mhz for item in segments_b),
            0.001,
        )
        overlap_pressure = min(1.0, overlap_mhz / occupied_width)
        score = min(100.0, 48 + overlap_pressure * 14 + distance_pressure * 22 + power_pressure * 10 + priority_pressure * 6)
        risks.append(
            {
                **common,
                "risk_type": "同频冲突",
                "severity": _task_risk_severity(score),
                "score": round(score, 1),
                "reason": (
                    f"频谱重叠 {overlap_mhz * 1000:.1f} kHz；单元距离 {distance_text}，"
                    f"保护距离 {protection:.1f} km；合计发射功率 {combined_power:.1f} W"
                ),
            }
        )
        if assignment_a.get("task_unit_id") != assignment_b.get("task_unit_id"):
            competition_score = min(100.0, score + (10 if unit_a.get("spectrum_relation") == "独占" or unit_b.get("spectrum_relation") == "独占" else 0))
            risks.append(
                {
                    **common,
                    "risk_type": "任务频谱竞争",
                    "severity": _task_risk_severity(competition_score),
                    "score": round(competition_score, 1),
                    "reason": f"两个任务单元在 {assignment_a.get('band_group')} 频段争用同一资源，最高任务/装备优先级为 {max_priority}",
                }
            )
    elif spacing_khz > 0 and gap_mhz * 1000 < spacing_khz:
        shortage_khz = spacing_khz - gap_mhz * 1000
        score = min(100.0, 42 + shortage_khz / spacing_khz * 30 + distance_pressure * 18 + power_pressure * 10)
        risks.append(
            {
                **common,
                "risk_type": "邻频冲突",
                "severity": _task_risk_severity(score),
                "score": round(score, 1),
                "reason": f"实际频谱间隔 {gap_mhz * 1000:.1f} kHz，小于要求 {spacing_khz:.1f} kHz；单元距离 {distance_text}",
            }
        )
        risks.append(
            {
                **common,
                "risk_type": "保护间隔不足",
                "severity": _task_risk_severity(max(35.0, score - 8)),
                "score": round(max(35.0, score - 8), 1),
                "reason": f"保护间隔缺口 {shortage_khz:.1f} kHz，需调整信道、带宽或保护带参数",
            }
        )

    if distance is not None and protection > 0 and distance < protection and combined_power >= 100:
        score = min(100.0, 35 + distance_pressure * 35 + power_pressure * 25 + priority_pressure * 5)
        risks.append(
            {
                **common,
                "risk_type": "高功率近距耦合",
                "severity": _task_risk_severity(score),
                "score": round(score, 1),
                "reason": f"合计发射功率 {combined_power:.1f} W，距离 {distance:.1f} km 小于保护距离 {protection:.1f} km",
            }
        )
    return risks


def _intermodulation_risks(assignments: list[dict], units: dict[str, dict], groups: dict[str, dict]) -> list[dict]:
    del units
    by_band: dict[str, list[tuple[float, dict, float]]] = defaultdict(list)
    for item in assignments:
        center = _assignment_center_frequency(item)
        band = str(item.get("band_group") or "")
        if center is None or not band:
            continue
        group = groups.get(item["equipment_group_id"], {})
        tolerance_mhz = max(
            0.001,
            float(group.get("bandwidth_khz") or 0) / 2000,
            float(group.get("guard_band_khz") or 0) / 1000,
            float(group.get("min_spacing_khz") or 0) / 1000,
        )
        by_band[band].append((center, item, tolerance_mhz))

    risks: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for records in by_band.values():
        records.sort(key=lambda row: row[0])
        frequencies = [row[0] for row in records]
        max_tolerance = max((row[2] for row in records), default=0.001)
        band_risk_count = 0
        for (freq_a, first, _), (freq_b, second, _) in combinations(records, 2):
            if band_risk_count >= 100:
                break
            source_ids = {first["equipment_group_id"], second["equipment_group_id"]}
            for product in (2 * freq_a - freq_b, 2 * freq_b - freq_a):
                if band_risk_count >= 100:
                    break
                start = bisect_left(frequencies, product - max_tolerance)
                end = bisect_right(frequencies, product + max_tolerance)
                for victim_freq, target, tolerance_mhz in records[start:end]:
                    if target["equipment_group_id"] in source_ids:
                        continue
                    delta = abs(product - victim_freq)
                    if delta > tolerance_mhz:
                        continue
                    key = tuple(sorted(source_ids)) + (target["equipment_group_id"],)
                    if key in seen:
                        continue
                    seen.add(key)
                    band_risk_count += 1
                    power = float(groups.get(first["equipment_group_id"], {}).get("tx_power_w") or 0) + float(groups.get(second["equipment_group_id"], {}).get("tx_power_w") or 0)
                    score = min(100.0, 58 + (1 - delta / tolerance_mhz) * 22 + min(15.0, math.log10(max(power, 1)) * 5))
                    risks.append(
                        {
                            "risk_type": "三阶互调风险",
                            "severity": _task_risk_severity(score),
                            "task_unit_a": first["task_unit_id"],
                            "equipment_group_a": first["equipment_group_id"],
                            "task_unit_b": target["task_unit_id"],
                            "equipment_group_b": target["equipment_group_id"],
                            "resource_a": f"{first['assigned_resource']} + {second['assigned_resource']}",
                            "resource_b": target["assigned_resource"],
                            "score": round(score, 1),
                            "reason": (
                                f"{first['equipment_group_id']} 与 {second['equipment_group_id']} 的三阶产物 {product:.6f} MHz "
                                f"距受扰频率 {victim_freq:.6f} MHz 仅 {delta * 1000:.1f} kHz"
                            ),
                        }
                    )
    return risks


def _segment_gap_mhz(left: Segment, right: Segment) -> float:
    if _overlaps(left, right):
        return 0.0
    return max(left.start - right.end, right.start - left.end, 0.0)


def _segment_overlap_mhz(left: Segment, right: Segment) -> float:
    return max(0.0, min(left.end, right.end) - max(left.start, right.start))


def _segment_relation_metrics(left_segments: list[Segment], right_segments: list[Segment]) -> tuple[float, float]:
    left = sorted(left_segments, key=lambda item: item.start)
    right = sorted(right_segments, key=lambda item: item.start)
    left_index = 0
    right_index = 0
    min_gap = math.inf
    overlap = 0.0
    while left_index < len(left) and right_index < len(right):
        left_item = left[left_index]
        right_item = right[right_index]
        overlap += _segment_overlap_mhz(left_item, right_item)
        min_gap = min(min_gap, _segment_gap_mhz(left_item, right_item))
        if left_item.end <= right_item.end:
            left_index += 1
        else:
            right_index += 1
    return (0.0 if math.isinf(min_gap) else min_gap, overlap)


def _assignment_center_frequency(assignment: dict) -> float | None:
    segments = _parse_resource_segments(assignment.get("assigned_resource") or "")
    if not segments:
        return None
    return sum((item.start + item.end) / 2 for item in segments) / len(segments)


def _task_risk_severity(score: float) -> str:
    if score >= 75:
        return "高"
    if score >= 35:
        return "中"
    return "低"


def task_versions_and_audit(session: Session, project_id: int) -> dict:
    task_objective_names = [item["objective"] for item in TASK_OBJECTIVES]
    runs = session.exec(
        select(PlanningRun)
        .where(PlanningRun.project_id == project_id, PlanningRun.objective.in_(task_objective_names), PlanningRun.status == "success")
        .order_by(PlanningRun.id.desc())
        .limit(20)
    ).all()
    logs = session.exec(select(AuditLog).where(AuditLog.project_id == project_id).order_by(AuditLog.id.desc()).limit(40)).all()
    return {
        "runs": [
            {
                "run_id": run.id,
                "objective": run.objective,
                "status": run.status,
                "message": run.message,
                "elapsed_ms": run.elapsed_ms,
                "created_at": run.created_at.isoformat(),
                "summary": json.loads(run.summary_json or "{}"),
                "replan_effect": _replan_effect_for_run(session, project_id, run),
            }
            for run in runs
        ],
        "performance_history": _performance_history_from_logs(session, project_id),
        "closure_events": _capacity_closure_events_from_logs(logs),
        "audit_logs": [
            {
                "id": log.id,
                "run_id": log.run_id,
                "actor": log.actor,
                "action": log.action,
                "detail": log.detail,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }


def _capacity_closure_events_from_logs(logs: list[AuditLog]) -> list[dict]:
    events = []
    for log in logs:
        if log.action != "capacity_batch_risk_closure":
            continue
        payload = _json_dict(log.detail or "{}")
        closure = payload.get("closure") if isinstance(payload.get("closure"), dict) else {}
        review = payload.get("cross_batch_review") if isinstance(payload.get("cross_batch_review"), dict) else {}
        rules = closure.get("rules") if isinstance(closure.get("rules"), list) else []
        events.append(
            {
                "id": log.id,
                "run_id": log.run_id,
                "source_audit_id": closure.get("source_audit_id") or payload.get("source_audit_id"),
                "created_at": log.created_at.isoformat(),
                "summary": closure.get("summary") or "",
                "improved": bool(closure.get("improved")),
                "applied_rule_count": int(closure.get("applied_rule_count") or 0),
                "skipped_link_count": int(closure.get("skipped_link_count") or 0),
                "before_cross_batch_risk_count": int(closure.get("before_cross_batch_risk_count") or 0),
                "after_cross_batch_risk_count": int(closure.get("after_cross_batch_risk_count") or 0),
                "before_high_risk_count": int(closure.get("before_high_risk_count") or 0),
                "after_high_risk_count": int(closure.get("after_high_risk_count") or 0),
                "resolved_cross_batch_risk_count": int(closure.get("resolved_cross_batch_risk_count") or 0),
                "affected_batches": list(review.get("affected_batches") or []),
                "run_ids": [int(item) for item in payload.get("run_ids", []) if _normalized_run_id(item)],
                "rules": rules[:6],
            }
        )
    return events[:8]


def _replan_effect_for_run(session: Session, project_id: int, run: PlanningRun | None) -> dict | None:
    if run is None or run.id is None:
        return None
    task_objective_names = [item["objective"] for item in TASK_OBJECTIVES]
    audit = session.exec(
        select(AuditLog)
        .where(AuditLog.project_id == project_id, AuditLog.run_id == run.id, AuditLog.action == "task_replan")
        .order_by(AuditLog.id.desc())
    ).first()
    audit_detail = _json_dict(audit.detail if audit else "")
    requested_base_run_id = _normalized_run_id(audit_detail.get("base_run_id"))
    previous = None
    if requested_base_run_id:
        candidate = session.get(PlanningRun, requested_base_run_id)
        if candidate and candidate.project_id == project_id and candidate.status == "success":
            previous = candidate
    if previous is None:
        previous = session.exec(
            select(PlanningRun)
            .where(
                PlanningRun.project_id == project_id,
                PlanningRun.objective.in_(task_objective_names),
                PlanningRun.status == "success",
                PlanningRun.id < run.id,
            )
            .order_by(PlanningRun.id.desc())
        ).first()
    if previous is None:
        return None

    current_summary = json.loads(run.summary_json or "{}")
    previous_summary = json.loads(previous.summary_json or "{}")
    current_assignments = task_assignments_for_run(session, project_id, run.id)
    previous_assignments = task_assignments_for_run(session, project_id, previous.id)
    added_ranges = audit_detail.get("available_ranges") or []
    trial_context = _sanitize_trial_context(audit_detail.get("trial_context"))

    deltas = {
        "task_satisfaction_avg": _round_delta(current_summary.get("task_satisfaction_avg"), previous_summary.get("task_satisfaction_avg")),
        "quality_total": _round_delta(_summary_quality(current_summary), _summary_quality(previous_summary)),
        "risk_item_count": int(current_summary.get("risk_item_count") or 0) - int(previous_summary.get("risk_item_count") or 0),
        "high_risk_count": int(current_summary.get("high_risk_count") or 0) - int(previous_summary.get("high_risk_count") or 0),
        "partial_group_count": int(current_summary.get("partial_group_count") or 0) - int(previous_summary.get("partial_group_count") or 0),
        "unsatisfied_group_count": int(current_summary.get("unsatisfied_group_count") or 0) - int(previous_summary.get("unsatisfied_group_count") or 0),
        "used_bandwidth_mhz": _round_delta(current_summary.get("used_bandwidth_mhz"), previous_summary.get("used_bandwidth_mhz")),
    }
    assignment_delta = _assignment_delta(previous_assignments, current_assignments)
    added_range_usage = _added_range_usage(added_ranges, current_assignments)
    status = _replan_effect_status(deltas, assignment_delta)
    reasons = _replan_effect_reasons(status, deltas, assignment_delta, added_ranges, added_range_usage, current_summary, current_assignments)
    prediction_alignment = _trial_prediction_alignment(trial_context.get("expected_deltas") or {}, deltas)
    return {
        "base_run_id": previous.id,
        "current_run_id": run.id,
        "base_objective": previous_summary.get("requested_objective") or previous_summary.get("effective_objective"),
        "current_objective": current_summary.get("requested_objective") or current_summary.get("effective_objective"),
        "base_effective_objective": previous_summary.get("effective_objective"),
        "current_effective_objective": current_summary.get("effective_objective"),
        "base_strategy_profile": previous_summary.get("strategy_profile") or "balanced",
        "current_strategy_profile": current_summary.get("strategy_profile") or "balanced",
        "status": status,
        "status_label": {"improved": "有收益", "flat": "收益不明显", "regressed": "效果下降"}.get(status, "已对比"),
        "summary": _replan_effect_summary(status, deltas, assignment_delta),
        "deltas": deltas,
        "assignment_delta": assignment_delta,
        "added_ranges": added_ranges,
        "added_range_usage": added_range_usage,
        "trial_context": trial_context,
        "prediction_alignment": prediction_alignment,
        "reasons": reasons,
        "recommendation": _replan_effect_recommendation(status, reasons, current_summary),
    }


def _json_dict(value: str) -> dict:
    try:
        data = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _sanitize_trial_context(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    text_keys = [
        "trial_id",
        "label",
        "objective",
        "objective_label",
        "strategy_profile",
        "constraint_variant",
        "constraint_label",
        "decision",
        "reason",
        "tradeoff",
    ]
    result = {key: str(value.get(key) or "").strip() for key in text_keys if str(value.get(key) or "").strip()}
    result["recommendation_score"] = _safe_float(value.get("recommendation_score"), 0.0)
    result["expected_metrics"] = _numeric_metric_dict(value.get("expected_metrics"))
    result["expected_deltas"] = _numeric_metric_dict(value.get("expected_deltas"))
    constraint_changes = value.get("constraint_changes")
    if isinstance(constraint_changes, list):
        result["constraint_changes"] = [str(item).strip() for item in constraint_changes[:5] if str(item).strip()]
    return {key: item for key, item in result.items() if item not in ("", [], {})}


def _numeric_metric_dict(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    result = {}
    for key in TRIAL_METRIC_KEYS:
        if key in value:
            result[key] = _safe_float(value.get(key), 0.0)
    return result


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return round(number, 3)


def _trial_context_change_detail(trial_context: dict) -> str:
    objective = trial_context.get("objective_label") or trial_context.get("objective") or "当前目标"
    constraint = trial_context.get("constraint_label") or "当前约束"
    decision = trial_context.get("decision") or "待执行后复核"
    return f"{objective} / {constraint}；{decision}"


def _trial_prediction_alignment(expected_deltas: dict, actual_deltas: dict) -> dict:
    rows = []
    for key in TRIAL_METRIC_KEYS:
        if key not in expected_deltas:
            continue
        expected = _safe_float(expected_deltas.get(key), 0.0)
        actual = _safe_float(actual_deltas.get(key), 0.0)
        aligned = _delta_direction(expected) == _delta_direction(actual) or (abs(expected) < 0.001 and abs(actual) < 0.001)
        rows.append(
            {
                "key": key,
                "label": TRIAL_METRIC_LABELS.get(key, key),
                "expected_delta": expected,
                "actual_delta": actual,
                "direction_matched": aligned,
            }
        )
    matched = sum(1 for item in rows if item["direction_matched"])
    total = len(rows)
    return {
        "matched_count": matched,
        "total_count": total,
        "summary": f"试算预期方向命中 {matched}/{total} 项" if total else "无试算预期可对照",
        "rows": rows[:8],
    }


def _delta_direction(value: float) -> int:
    if value > 0.001:
        return 1
    if value < -0.001:
        return -1
    return 0


def _summary_quality(summary: dict) -> float:
    return float((summary.get("quality_scores") or {}).get("total") or 0)


def _round_delta(current: object, previous: object) -> float:
    return round(float(current or 0) - float(previous or 0), 3)


def _assignment_delta(previous_assignments: list[dict], current_assignments: list[dict]) -> dict:
    previous_by_group = {item["equipment_group_id"]: item for item in previous_assignments}
    current_by_group = {item["equipment_group_id"]: item for item in current_assignments}
    group_ids = sorted(set(previous_by_group) | set(current_by_group))
    changed = []
    improved = 0
    worsened = 0
    for group_id in group_ids:
        before = previous_by_group.get(group_id, {})
        after = current_by_group.get(group_id, {})
        ratio_delta = round(float(after.get("satisfaction_ratio") or 0) - float(before.get("satisfaction_ratio") or 0), 4)
        resource_changed = (before.get("assigned_resource") or "") != (after.get("assigned_resource") or "")
        status_changed = (before.get("status") or "") != (after.get("status") or "")
        if ratio_delta > 0:
            improved += 1
        elif ratio_delta < 0:
            worsened += 1
        if resource_changed or status_changed or abs(ratio_delta) > 0.0001:
            changed.append(
                {
                    "equipment_group_id": group_id,
                    "before_status": before.get("status", "-"),
                    "after_status": after.get("status", "-"),
                    "ratio_delta": ratio_delta,
                    "resource_changed": resource_changed,
                }
            )
    return {
        "changed_assignment_count": len(changed),
        "improved_group_count": improved,
        "worsened_group_count": worsened,
        "top_changes": sorted(changed, key=lambda item: abs(float(item["ratio_delta"])), reverse=True)[:8],
    }


def _added_range_usage(added_ranges: list[dict], assignments: list[dict]) -> list[dict]:
    rows = []
    for item in added_ranges:
        band = str(item.get("band_group") or "").strip()
        start = float(item.get("start_mhz") or 0)
        end = float(item.get("end_mhz") or 0)
        if end <= start:
            continue
        used_width = 0.0
        used_groups: set[str] = set()
        for assignment in assignments:
            if band and assignment.get("band_group") != band:
                continue
            for segment in _parse_resource_segments(assignment.get("assigned_resource") or ""):
                overlap = _segment_overlap_width(segment, Segment(start, end))
                if overlap > 0:
                    used_width += overlap
                    used_groups.add(assignment.get("equipment_group_id", ""))
        rows.append(
            {
                "band_group": band,
                "start_mhz": start,
                "end_mhz": end,
                "width_mhz": round(end - start, 3),
                "used_width_mhz": round(used_width, 3),
                "used_assignment_count": len([item for item in used_groups if item]),
            }
        )
    return rows


def _segment_overlap_width(a: Segment, b: Segment) -> float:
    return max(0.0, min(a.end, b.end) - max(a.start, b.start))


def _replan_effect_status(deltas: dict, assignment_delta: dict) -> str:
    if (
        deltas["task_satisfaction_avg"] > 0.05
        or deltas["quality_total"] > 0.05
        or deltas["unsatisfied_group_count"] < 0
        or deltas["high_risk_count"] < 0
        or assignment_delta["improved_group_count"] > assignment_delta["worsened_group_count"]
    ):
        return "improved"
    if (
        deltas["task_satisfaction_avg"] < -0.05
        or deltas["quality_total"] < -0.05
        or deltas["unsatisfied_group_count"] > 0
        or deltas["high_risk_count"] > 0
        or assignment_delta["worsened_group_count"] > assignment_delta["improved_group_count"]
    ):
        return "regressed"
    return "flat"


def _replan_effect_reasons(
    status: str,
    deltas: dict,
    assignment_delta: dict,
    added_ranges: list[dict],
    added_range_usage: list[dict],
    current_summary: dict,
    current_assignments: list[dict],
) -> list[str]:
    reasons: list[str] = []
    if status == "improved":
        reasons.append("重规划带来了可量化收益，建议保留该版本并进入人工复核。")
    elif status == "regressed":
        reasons.append("重规划后关键指标下降，建议回退到上一版本或重新约束目标函数。")
    else:
        reasons.append("重规划后核心指标变化很小，需要继续定位剩余约束。")

    if added_ranges:
        used_count = sum(int(item.get("used_assignment_count") or 0) for item in added_range_usage)
        if used_count == 0:
            reasons.append("新增可用频段尚未被任何装备组采用，通常说明新增窗口不匹配未满足装备类型、任务单元或带宽模式。")
        else:
            reasons.append(f"新增可用频段已被 {used_count} 个装备组采用，但仍需观察保障率和风险是否同步改善。")

    if deltas["unsatisfied_group_count"] >= 0 and int(current_summary.get("unsatisfied_group_count") or 0):
        reasons.append(f"当前仍有 {current_summary.get('unsatisfied_group_count')} 个未满足装备组，资源补给应优先对准这些对象的首选/兼容频段。")
    if deltas["partial_group_count"] >= 0 and int(current_summary.get("partial_group_count") or 0):
        reasons.append(f"当前仍有 {current_summary.get('partial_group_count')} 个部分满足装备组，可能需要补连续窗口或降低信道数。")
    if assignment_delta["changed_assignment_count"] == 0:
        reasons.append("装备组指配基本未变化，说明本次变更没有触发求解器选择新的可行资源。")

    diagnostics = current_summary.get("diagnostics") or []
    if diagnostics:
        first = diagnostics[0]
        reasons.append(f"首要诊断：{first.get('target', '-')} - {first.get('suggestion', first.get('reason', '继续复核约束'))}")
    else:
        remaining = [item for item in current_assignments if item.get("status") != "完全满足"]
        if remaining:
            reasons.append(f"剩余缺口集中在 {remaining[0].get('equipment_group_id')}：{remaining[0].get('reason', '资源不足')}")
    return reasons[:5]


def _replan_effect_summary(status: str, deltas: dict, assignment_delta: dict) -> str:
    if status == "improved":
        prefix = "本次重规划有效"
    elif status == "regressed":
        prefix = "本次重规划效果下降"
    else:
        prefix = "本次重规划收益不明显"
    return (
        f"{prefix}：保障率变化 {deltas['task_satisfaction_avg']:+.1f}%、质量分变化 {deltas['quality_total']:+.1f}、"
        f"未满足变化 {deltas['unsatisfied_group_count']:+d}、高风险变化 {deltas['high_risk_count']:+d}、"
        f"指配变化 {assignment_delta['changed_assignment_count']} 个。"
    )


def _replan_effect_recommendation(status: str, reasons: list[str], current_summary: dict) -> str:
    if status == "improved":
        return "保留该版本，继续针对剩余高风险或部分满足对象做小步重规划。"
    if status == "regressed":
        return "先回退或降低新增约束强度，再用风险最低/任务保障优先两套目标做对比。"
    if int(current_summary.get("unsatisfied_group_count") or 0) or int(current_summary.get("partial_group_count") or 0):
        return "下一轮应按未满足/部分满足装备组反推频段、带宽和兼容规则，而不是只按频段压力补资源。"
    return "当前变化较小，可转向风险压降、频谱节约或版本审计补强。"


def task_agent_capability_assessment(session: Session, project_id: int, run_id: int | None = None) -> dict:
    run = _task_run_for_assessment(session, project_id, run_id)
    if run is None:
        return {
            "status": "needs_plan",
            "maturity_score": 0,
            "maturity_level": "未形成规划版本",
            "leader_summary": "当前项目还没有成功的任务用频规划版本，无法进行动态规划智能体能力评估。",
            "run_id": None,
            "capability_items": [],
            "acceptance_gates": [
                {"name": "存在成功规划版本", "passed": False, "evidence": "未找到成功运行", "next_step": "先生成样例或上传数据，并执行一次任务规划。"}
            ],
            "next_actions": [
                {
                    "action_id": "create_baseline_plan",
                    "priority": "高",
                    "title": "生成基线规划版本",
                    "why": "没有基线版本就无法比较重规划收益。",
                    "suggested_message": "生成一个任务保障优先的基线规划版本。",
                    "deterministic_payload": {"objective": "task_assurance"},
                }
            ],
            "artifact_checklist": [],
        }
    assignments = task_assignments_for_run(session, project_id, run.id)
    risk_items = task_risks_for_run(session, project_id, run.id)
    summary = json.loads(run.summary_json or "{}")
    visualization = build_task_visualization_data(
        task_units=db_task_units_to_dicts(session, project_id),
        equipment_groups=db_equipment_groups_to_dicts(session, project_id),
        spectrum_rules=db_spectrum_rules_to_dicts(session, project_id),
        assignments=assignments,
        risk_items=risk_items,
        summary=summary,
    )
    versions = task_versions_and_audit(session, project_id)
    replan_effect = _replan_effect_for_run(session, project_id, run)
    return build_task_agent_assessment(summary, assignments, risk_items, visualization, versions, run, replan_effect=replan_effect)


def build_task_agent_assessment(
    summary: dict,
    assignments: list[dict],
    risk_items: list[dict],
    visualization: dict,
    versions: dict | None = None,
    run: PlanningRun | dict | None = None,
    replan_effect: dict | None = None,
) -> dict:
    versions = versions or {"runs": [], "audit_logs": [], "performance_history": []}
    run_id = getattr(run, "id", None) if run is not None else None
    if run_id is None and isinstance(run, dict):
        run_id = run.get("run_id") or run.get("id")
    elapsed_ms = getattr(run, "elapsed_ms", None) if run is not None else None
    if elapsed_ms is None and isinstance(run, dict):
        elapsed_ms = run.get("elapsed_ms")
    avg_satisfaction = float(summary.get("task_satisfaction_avg") or 0)
    quality_total = float((summary.get("quality_scores") or {}).get("total") or 0)
    unsatisfied = int(summary.get("unsatisfied_group_count") or 0)
    partial = int(summary.get("partial_group_count") or 0)
    high_risk = int(summary.get("high_risk_count") or 0)
    medium_risk = sum(1 for item in risk_items if item.get("severity") == "中")
    run_count = len(versions.get("runs", []))
    audit_actions = [str(item.get("action", "")) for item in versions.get("audit_logs", [])]
    replan_preview_count = sum(1 for action in audit_actions if action == "task_replan_preview")
    replan_count = sum(1 for action in audit_actions if action == "task_replan")
    scale_evidence = _agent_scale_evidence(versions)
    scale_evidence["batch_plan"] = _agent_capacity_batch_plan(visualization, risk_items, scale_evidence)
    performance_count = int(scale_evidence.get("history_count") or 0)
    explanation_count = sum(1 for item in visualization.get("assignments", []) if item.get("explanation_chain"))
    assignment_count = max(1, len(assignments))
    spectrum_rule_count = int(
        summary.get("spectrum_rule_count")
        or sum(len(item.get("rules", []) or []) for item in visualization.get("band_usage", []))
        or len(visualization.get("spectrum_timeline", []))
    )

    scores = {
        "data_foundation": _bounded_score(70 + min(30, assignment_count)),
        "multi_objective": _bounded_score(65 + min(25, run_count * 5) + (10 if summary.get("score_explanation") else 0)),
        "dynamic_replanning": _bounded_score(35 + min(30, run_count * 6) + min(10, replan_preview_count * 4) + min(20, replan_count * 10) + (15 if performance_count else 0)),
        "explainability": _bounded_score((explanation_count / assignment_count) * 70 + (15 if summary.get("diagnostics") else 0) + (15 if summary.get("bottleneck_analysis") else 0)),
        "risk_control": _bounded_score(100 - high_risk * 18 - medium_risk * 4 - partial * 2 - unsatisfied * 12),
        "efficiency": _efficiency_score(elapsed_ms),
        "auditability": _bounded_score(50 + min(30, len(versions.get("audit_logs", [])) * 2) + min(20, run_count * 4)),
        "scalability": _agent_scalability_score(summary, scale_evidence),
    }
    maturity_score = round(
        scores["data_foundation"] * 0.10
        + scores["multi_objective"] * 0.12
        + scores["dynamic_replanning"] * 0.16
        + scores["explainability"] * 0.14
        + scores["risk_control"] * 0.18
        + scores["efficiency"] * 0.10
        + scores["auditability"] * 0.10
        + scores["scalability"] * 0.10,
        1,
    )
    capability_items = [
        _capability_item("data_foundation", "数据与约束基础", scores["data_foundation"], f"{summary.get('task_unit_count', 0)} 个任务单元、{summary.get('equipment_group_count', 0)} 个装备组、{spectrum_rule_count} 条频段规则证据", "继续补充真实设备模板和地区化规则。"),
        _capability_item("multi_objective", "多目标规划", scores["multi_objective"], f"已支持 {len(TASK_OBJECTIVES)} 类目标，当前有效目标 {summary.get('effective_objective', summary.get('objective', '-'))}", "对常用目标组合固化为任务场景策略包。"),
        _capability_item("dynamic_replanning", "动态重规划闭环", scores["dynamic_replanning"], f"{run_count} 个成功版本、{replan_preview_count} 次重规划预览、{replan_count} 次执行重规划、{performance_count} 次项目压测记录", "把建议动作一键转为预览变更清单并做收益对比。"),
        _capability_item("explainability", "可解释性", scores["explainability"], f"{explanation_count}/{assignment_count} 个装备组具备解释链，诊断项 {len(summary.get('diagnostics', []))} 个", "把解释链和审核清单联动到报告审批流程。"),
        _capability_item("risk_control", "风险控制", scores["risk_control"], f"高风险 {high_risk} 个、中风险 {medium_risk} 个、部分满足 {partial} 个、未满足 {unsatisfied} 个", "优先消除高风险和未满足项，再压缩中风险复用链路。"),
        _capability_item("efficiency", "求解效率", scores["efficiency"], f"当前运行耗时 {elapsed_ms if elapsed_ms is not None else '-'} ms", "记录不同规模曲线并设置大规模求解告警阈值。"),
        _capability_item("auditability", "审计与版本", scores["auditability"], f"审计记录 {len(versions.get('audit_logs', []))} 条，成功版本 {run_count} 个", "补充变更前后约束差异和人工确认状态。"),
        _capability_item("scalability", "规模扩展", scores["scalability"], f"当前装备组 {summary.get('equipment_group_count', 0)} 个，{scale_evidence.get('evidence')}", str(scale_evidence.get("decision") or "将参数化样例与真实规模分层压测纳入验收。")),
    ]
    gates = _agent_acceptance_gates(summary, risk_items, versions, scores)
    next_actions = _agent_next_actions(summary, assignments, risk_items, visualization, versions, scores, replan_effect, scale_evidence)
    return {
        "status": "ready",
        "run_id": run_id,
        "maturity_score": maturity_score,
        "maturity_level": _maturity_level(maturity_score),
        "leader_summary": _agent_leader_summary(maturity_score, summary, high_risk, medium_risk, partial, unsatisfied),
        "replan_effect": replan_effect,
        "strategy_history": _agent_strategy_history(versions, run_id),
        "scale_evidence": scale_evidence,
        "capability_items": capability_items,
        "acceptance_gates": gates,
        "next_actions": next_actions,
        "artifact_checklist": _agent_artifact_checklist(run_id, summary, assignments, risk_items, visualization, versions),
    }


def _task_run_for_assessment(session: Session, project_id: int, run_id: int | None) -> PlanningRun | None:
    task_objective_names = [item["objective"] for item in TASK_OBJECTIVES]
    if run_id is not None:
        run = session.get(PlanningRun, run_id)
        if run and run.project_id == project_id and run.objective in task_objective_names and run.status == "success":
            return run
        return None
    return session.exec(
        select(PlanningRun)
        .where(PlanningRun.project_id == project_id, PlanningRun.objective.in_(task_objective_names), PlanningRun.status == "success")
        .order_by(PlanningRun.id.desc())
    ).first()


def _bounded_score(value: float) -> float:
    return round(max(0.0, min(100.0, float(value))), 1)


def _efficiency_score(elapsed_ms: int | float | None) -> float:
    if elapsed_ms is None:
        return 50.0
    elapsed = float(elapsed_ms)
    if elapsed <= 500:
        return 100.0
    if elapsed <= 1500:
        return 90.0
    if elapsed <= 3000:
        return 78.0
    if elapsed <= 8000:
        return 62.0
    if elapsed <= 15000:
        return 45.0
    return 30.0


def _capability_item(key: str, label: str, score: float, evidence: str, next_step: str) -> dict:
    return {
        "key": key,
        "label": label,
        "score": score,
        "status": _score_status(score),
        "evidence": evidence,
        "next_step": next_step if score < 90 else "当前能力较稳，继续用压测和真实数据验证。",
    }


def _score_status(score: float) -> str:
    if score >= 90:
        return "优秀"
    if score >= 75:
        return "可用"
    if score >= 60:
        return "待增强"
    return "薄弱"


def _maturity_level(score: float) -> str:
    if score >= 90:
        return "完善高效动态规划智能体"
    if score >= 80:
        return "动态智能体候选"
    if score >= 68:
        return "可迭代规划助手"
    if score >= 50:
        return "可演示 MVP"
    return "原型阶段"


def _capacity_count_label(row: dict | None) -> str:
    row = row or {}
    units = row.get("task_unit_count")
    groups = row.get("equipment_group_count")
    samples = row.get("equipment_sample_count")
    label = f"{units if units is not None else '-'} 单元/{groups if groups is not None else '-'} 装备组"
    if samples is not None:
        label += f"/{samples} 台套"
    return label


def _agent_scale_evidence(versions: dict) -> dict:
    history = versions.get("performance_history", []) or []
    if not history:
        return {
            "available": False,
            "capacity_defined": False,
            "status": "缺少压测",
            "history_count": 0,
            "evidence": "尚未形成项目压测历史，容量边界未验证",
            "decision": "先运行阶梯压测，形成不同任务单元和装备组规模下的耗时、质量和风险曲线。",
            "actions": ["运行阶梯压测", "比较推荐规模与最大压力规模", "把容量边界纳入验收门槛"],
            "recommended": {},
            "largest": {},
            "capacity_profile": {},
        }
    latest = history[0] or {}
    profile = latest.get("capacity_profile") or {}
    recommended = profile.get("recommended") or {}
    largest = profile.get("largest") or {}
    status = str(profile.get("status") or "已有压测")
    capacity_defined = bool(recommended and largest)
    run_count = int(latest.get("run_count") or 0)
    scenario_count = int(latest.get("scenario_count") or 0)
    max_elapsed_ms = int(latest.get("max_elapsed_ms") or 0)
    avg_elapsed_ms = round(float(latest.get("avg_elapsed_ms") or 0), 1)
    best_quality_total = float(latest.get("best_quality_total") or 0)
    decision = str(profile.get("decision") or "")
    if not decision:
        if status == "容量充足":
            decision = "当前压测规模内质量和耗时表现可接受，可继续按现有单次规划流程推进。"
        elif status == "需分批规划":
            decision = "超过推荐规模时按任务单元或装备组拆批规划，并保留跨批频率保护约束。"
        elif status == "需扩容规则":
            decision = "当前频段或规则容量不足，需要补充可用频段、调整保护距离或拆分任务后再规划。"
        else:
            decision = "已有压测记录，但容量画像不完整，建议重新运行阶梯压测补齐推荐边界。"
    actions = list(profile.get("actions") or [])
    if not actions:
        actions = ["复核压测场景覆盖", "保存推荐容量边界", "在新任务导入时触发规模预警"]

    parts = [f"项目压测记录 {len(history)} 次"]
    if run_count:
        parts.append(f"最近 {run_count} 次求解")
    if scenario_count:
        parts.append(f"{scenario_count} 个规模场景")
    parts.append(f"容量状态：{status}")
    if recommended:
        parts.append(f"推荐单次 { _capacity_count_label(recommended) }")
    if largest:
        parts.append(f"最大压测 { _capacity_count_label(largest) }")
    if max_elapsed_ms:
        parts.append(f"最大耗时 {max_elapsed_ms} ms")
    if best_quality_total:
        parts.append(f"最佳质量 {round(best_quality_total, 1)} 分")
    return {
        "available": True,
        "capacity_defined": capacity_defined,
        "status": status,
        "history_count": len(history),
        "scenario_count": scenario_count,
        "run_count": run_count,
        "max_elapsed_ms": max_elapsed_ms,
        "avg_elapsed_ms": avg_elapsed_ms,
        "best_quality_total": round(best_quality_total, 1),
        "interactive_threshold_ms": profile.get("interactive_threshold_ms"),
        "quality_floor": profile.get("quality_floor"),
        "recommended": recommended,
        "largest": largest,
        "quality_drop": profile.get("quality_drop"),
        "satisfaction_drop": profile.get("satisfaction_drop"),
        "elapsed_growth": profile.get("elapsed_growth"),
        "problem_focus": profile.get("problem_focus") or "待观察",
        "decision": decision,
        "actions": actions,
        "evidence": "；".join(parts),
        "capacity_profile": profile,
    }


def _agent_scalability_score(summary: dict, scale_evidence: dict) -> float:
    score = 45 + min(25, int(summary.get("equipment_group_count") or 0) / 3)
    if scale_evidence.get("available"):
        score += 15
    if scale_evidence.get("capacity_defined"):
        score += 12
    status = scale_evidence.get("status")
    if status == "容量充足":
        score += 8
    elif status == "需分批规划":
        score += 4
    elif status == "需扩容规则":
        score -= 8
    max_elapsed = float(scale_evidence.get("max_elapsed_ms") or 0)
    threshold = float(scale_evidence.get("interactive_threshold_ms") or 0)
    if max_elapsed and threshold and max_elapsed <= threshold:
        score += 4
    return _bounded_score(score)


def _agent_capacity_batch_plan(visualization: dict, risk_items: list[dict], scale_evidence: dict) -> dict:
    recommended = scale_evidence.get("recommended") or {}
    recommended_units = int(recommended.get("task_unit_count") or 0)
    recommended_groups = int(recommended.get("equipment_group_count") or 0)
    if not scale_evidence.get("capacity_defined") or recommended_units <= 0 or recommended_groups <= 0:
        return {
            "available": False,
            "needed": False,
            "reason": "尚未形成推荐容量边界，无法生成拆批预案。",
            "batches": [],
            "guardrails": ["先运行阶梯压测形成推荐单次规模和最大压力规模。"],
        }

    units = list(visualization.get("task_units") or [])
    groups = list(visualization.get("equipment_groups") or [])
    assignments_by_group = {
        str(item.get("equipment_group_id") or ""): item
        for item in visualization.get("assignments", [])
        if item.get("equipment_group_id")
    }
    pressure_rows = ((visualization.get("summary") or {}).get("bottleneck_analysis") or {}).get("task_unit_pressure") or []
    pressure_by_unit = {item.get("task_unit_id"): item for item in pressure_rows}
    groups_by_unit: dict[str, list[dict]] = defaultdict(list)
    for group in groups:
        groups_by_unit[str(group.get("task_unit_id") or "")].append(group)

    severity_weight = {"高": 3, "中": 2, "低": 1}
    risk_by_unit: dict[str, Counter] = defaultdict(Counter)
    cross_risks = []
    for risk in risk_items:
        units_in_risk = {
            str(risk.get("task_unit_id") or ""),
            str(risk.get("task_unit_a") or ""),
            str(risk.get("task_unit_b") or ""),
        }
        units_in_risk.discard("")
        for unit_id in units_in_risk:
            risk_by_unit[unit_id][str(risk.get("severity") or "中")] += 1
        if risk.get("task_unit_a") and risk.get("task_unit_b") and risk.get("task_unit_a") != risk.get("task_unit_b"):
            cross_risks.append(risk)

    unit_rows = []
    for unit in units:
        unit_id = str(unit.get("task_unit_id") or "")
        unit_groups = groups_by_unit.get(unit_id, [])
        pressure = pressure_by_unit.get(unit_id) or {}
        preferred_bands = _split_csv(unit.get("preferred_band_groups"))
        severity_counter = risk_by_unit.get(unit_id, Counter())
        risk_score = sum(severity_weight.get(level, 1) * count for level, count in severity_counter.items())
        group_count = len(unit_groups)
        sample_count = sum(int(group.get("count") or 0) for group in unit_groups)
        unit_rows.append(
            {
                "task_unit_id": unit_id,
                "name": unit.get("name") or unit_id,
                "unit_type": unit.get("unit_type") or "-",
                "priority": int(unit.get("priority") or 1),
                "preferred_band_group": preferred_bands[0] if preferred_bands else "-",
                "equipment_group_count": group_count,
                "equipment_sample_count": sample_count,
                "pressure_score": float(pressure.get("pressure_score") or 0),
                "satisfaction_ratio_pct": round(float(unit.get("satisfaction_ratio") or 0) * 100, 1),
                "high_risk_count": int(severity_counter.get("高") or 0),
                "medium_risk_count": int(severity_counter.get("中") or 0),
                "risk_weight": risk_score,
                "status": unit.get("status") or "-",
            }
        )

    sorted_units = sorted(
        unit_rows,
        key=lambda item: (
            str(item.get("preferred_band_group") or ""),
            -int(item.get("priority") or 0),
            -float(item.get("pressure_score") or 0),
            -int(item.get("equipment_group_count") or 0),
            str(item.get("task_unit_id") or ""),
        ),
    )
    batches: list[dict] = []
    current: list[dict] = []

    def would_exceed(batch: list[dict], row: dict) -> bool:
        return (
            len(batch) + 1 > recommended_units
            or sum(int(item.get("equipment_group_count") or 0) for item in batch) + int(row.get("equipment_group_count") or 0) > recommended_groups
        )

    def close_batch(batch: list[dict]) -> None:
        if not batch:
            return
        batch_id = f"B{len(batches) + 1:02d}"
        unit_count = len(batch)
        group_count = sum(int(item.get("equipment_group_count") or 0) for item in batch)
        sample_count = sum(int(item.get("equipment_sample_count") or 0) for item in batch)
        high_count = sum(int(item.get("high_risk_count") or 0) for item in batch)
        medium_count = sum(int(item.get("medium_risk_count") or 0) for item in batch)
        pressure = round(sum(float(item.get("pressure_score") or 0) for item in batch), 1)
        unit_utilization = round(unit_count / recommended_units * 100, 1) if recommended_units else 0
        group_utilization = round(group_count / recommended_groups * 100, 1) if recommended_groups else 0
        dominant_band = Counter(str(item.get("preferred_band_group") or "-") for item in batch).most_common(1)[0][0]
        status = "超出建议" if unit_count > recommended_units or group_count > recommended_groups else "建议规模内"
        batches.append(
            {
                "batch_id": batch_id,
                "name": f"批次 {len(batches) + 1}",
                "status": status,
                "task_unit_count": unit_count,
                "equipment_group_count": group_count,
                "equipment_sample_count": sample_count,
                "unit_utilization_pct": unit_utilization,
                "group_utilization_pct": group_utilization,
                "pressure_score": pressure,
                "high_risk_count": high_count,
                "medium_risk_count": medium_count,
                "dominant_band_group": dominant_band,
                "task_units": [
                    {
                        "task_unit_id": item.get("task_unit_id"),
                        "name": item.get("name"),
                        "unit_type": item.get("unit_type"),
                        "priority": item.get("priority"),
                        "equipment_group_count": item.get("equipment_group_count"),
                        "equipment_sample_count": item.get("equipment_sample_count"),
                        "pressure_score": item.get("pressure_score"),
                        "status": item.get("status"),
                    }
                    for item in batch
                ],
                "reason": (
                    f"按主用频段 {dominant_band}、任务优先级和压力分聚合；"
                    f"本批占推荐装备组容量 {group_utilization}%"
                ),
            }
        )

    for row in sorted_units:
        if current and would_exceed(current, row):
            close_batch(current)
            current = []
        current.append(row)
        if int(row.get("equipment_group_count") or 0) > recommended_groups:
            close_batch(current)
            current = []
    close_batch(current)

    unit_to_batch = {
        unit.get("task_unit_id"): batch.get("batch_id")
        for batch in batches
        for unit in batch.get("task_units", [])
    }
    cross_batch_links = []
    for risk in sorted(cross_risks, key=lambda item: float(item.get("score") or 0), reverse=True):
        source = risk.get("task_unit_a")
        target = risk.get("task_unit_b")
        source_batch = unit_to_batch.get(source)
        target_batch = unit_to_batch.get(target)
        if source_batch and target_batch and source_batch != target_batch:
            source_assignment = assignments_by_group.get(str(risk.get("equipment_group_a") or ""))
            target_assignment = assignments_by_group.get(str(risk.get("equipment_group_b") or ""))
            cross_batch_links.append(
                {
                    "source_unit": source,
                    "target_unit": target,
                    "source_equipment_group": risk.get("equipment_group_a"),
                    "target_equipment_group": risk.get("equipment_group_b"),
                    "source_batch": source_batch,
                    "target_batch": target_batch,
                    "source_band_group": (source_assignment or {}).get("band_group"),
                    "target_band_group": (target_assignment or {}).get("band_group"),
                    "source_resource": risk.get("resource_a"),
                    "target_resource": risk.get("resource_b"),
                    "severity": risk.get("severity"),
                    "score": risk.get("score"),
                    "reason": risk.get("reason") or risk.get("risk_type") or "跨批复用风险",
                }
            )
        if len(cross_batch_links) >= 6:
            break

    current_unit_count = len(units)
    current_group_count = len(groups)
    needed = current_unit_count > recommended_units or current_group_count > recommended_groups
    over_limit_count = sum(1 for batch in batches if batch.get("status") == "超出建议")
    max_group_utilization = max((float(batch.get("group_utilization_pct") or 0) for batch in batches), default=0)
    return {
        "available": True,
        "needed": needed,
        "method": "按主用频段、优先级、任务压力和推荐容量边界自动拆批",
        "reason": (
            f"当前 {current_unit_count} 个任务单元/{current_group_count} 个装备组；"
            f"推荐单批不超过 {recommended_units} 个任务单元/{recommended_groups} 个装备组。"
        ),
        "recommended_limits": {
            "task_unit_count": recommended_units,
            "equipment_group_count": recommended_groups,
            "equipment_sample_count": recommended.get("equipment_sample_count"),
        },
        "current": {
            "task_unit_count": current_unit_count,
            "equipment_group_count": current_group_count,
            "equipment_sample_count": sum(int(group.get("count") or 0) for group in groups),
        },
        "batch_count": len(batches),
        "max_group_utilization_pct": round(max_group_utilization, 1),
        "over_limit_count": over_limit_count,
        "cross_batch_risk_count": len(cross_batch_links),
        "batches": batches,
        "cross_batch_links": cross_batch_links,
        "guardrails": [
            "跨批仍需保留保护频率、禁用频率和同频复用距离约束。",
            "雷达、回传和高功率通信装备跨批复用时需复核保护距离。",
            "若单个任务单元已超过推荐装备组容量，应先在该任务内部按装备类型拆分。",
        ],
    }


def _agent_leader_summary(score: float, summary: dict, high_risk: int, medium_risk: int, partial: int, unsatisfied: int) -> str:
    avg = summary.get("task_satisfaction_avg", 0)
    quality = (summary.get("quality_scores") or {}).get("total", "-")
    return (
        f"当前智能体成熟度 {score} 分，处于“{_maturity_level(score)}”。"
        f" 最新方案平均保障率 {avg}%，综合质量 {quality} 分；"
        f"高风险 {high_risk} 个、中风险 {medium_risk} 个、部分满足 {partial} 个、未满足 {unsatisfied} 个。"
    )


def _agent_acceptance_gates(summary: dict, risk_items: list[dict], versions: dict, scores: dict) -> list[dict]:
    avg = float(summary.get("task_satisfaction_avg") or 0)
    quality = float((summary.get("quality_scores") or {}).get("total") or 0)
    unsatisfied = int(summary.get("unsatisfied_group_count") or 0)
    partial = int(summary.get("partial_group_count") or 0)
    high_risk = int(summary.get("high_risk_count") or 0)
    run_count = len(versions.get("runs", []))
    scale_evidence = _agent_scale_evidence(versions)
    capacity_status = scale_evidence.get("status")
    capacity_defined = bool(scale_evidence.get("capacity_defined"))
    return [
        {
            "name": "任务保障率达到可执行阈值",
            "passed": avg >= 95 and unsatisfied == 0,
            "evidence": f"平均保障率 {avg}%，未满足 {unsatisfied} 个",
            "next_step": "对未满足或低保障装备组设置必须完全满足，或增加备用频段后重算。",
        },
        {
            "name": "高风险清零",
            "passed": high_risk == 0,
            "evidence": f"高风险 {high_risk} 个，总风险 {len(risk_items)} 个",
            "next_step": "切换到风险最低权重，优先分离高风险冲突装备组。",
        },
        {
            "name": "降级保障可解释",
            "passed": partial == 0 or scores.get("explainability", 0) >= 80,
            "evidence": f"部分满足 {partial} 个，可解释性 {scores.get('explainability', 0)} 分",
            "next_step": "为部分满足对象补充缺口、备选频段和人工接受理由。",
        },
        {
            "name": "存在可比较版本历史",
            "passed": run_count >= 2,
            "evidence": f"成功规划版本 {run_count} 个",
            "next_step": "至少执行一次受控重规划，形成前后对比。",
        },
        {
            "name": "具备规模压测证据",
            "passed": bool(scale_evidence.get("available")),
            "evidence": str(scale_evidence.get("evidence") or "尚未形成压测证据"),
            "next_step": "运行阶梯压测，记录不同装备规模下的耗时和质量变化。",
        },
        {
            "name": "容量边界可执行",
            "passed": capacity_defined and capacity_status in {"容量充足", "需分批规划", "已有压测"},
            "evidence": (
                f"{capacity_status}；推荐 {_capacity_count_label(scale_evidence.get('recommended'))}；"
                f"最大压测 {_capacity_count_label(scale_evidence.get('largest'))}"
                if capacity_defined
                else "尚未形成推荐规模和最大压力规模"
            ),
            "next_step": str(scale_evidence.get("decision") or "补齐推荐容量边界后再进入大规模动态规划验收。"),
        },
        {
            "name": "综合质量达标",
            "passed": quality >= 80,
            "evidence": f"综合质量 {quality} 分",
            "next_step": "根据瓶颈频段和诊断建议迭代约束，再比较质量分。",
        },
    ]


def _supplement_range_from_pressure_band(band: dict, visualization: dict) -> dict | None:
    band_group = band.get("band_group")
    if not band_group:
        return None
    requested_width = max(
        1.0,
        min(
            20.0,
            max(
                (float(band.get("demand_width_mhz") or 0) - float(band.get("clean_available_width_mhz") or 0)) * 0.35,
                int(band.get("pressure_group_count") or 0) * 0.5,
            ),
        ),
    )
    return _supplement_range_after_band(
        str(band_group),
        visualization,
        requested_width,
        "智能体根据瓶颈频段压力建议补充的模拟备用窗口",
    )


def _supplement_range_for_unmet_assignment(assignments: list[dict], visualization: dict) -> dict | None:
    ranges = _supplement_ranges_for_unmet_assignments(assignments, visualization, limit=1)
    return ranges[0] if ranges else None


def _supplement_ranges_for_unmet_assignments(assignments: list[dict], visualization: dict, limit: int = 3) -> list[dict]:
    rich_by_group = {item.get("equipment_group_id"): item for item in visualization.get("assignments", [])}
    candidates = []
    for assignment in assignments:
        if assignment.get("status") == "完全满足":
            continue
        rich = rich_by_group.get(assignment.get("equipment_group_id")) or assignment
        chain = rich.get("explanation_chain") or {}
        required = chain.get("required_extra_resource") or {}
        estimated_width = float(required.get("estimated_extra_width_mhz") or 0)
        missing_channels = max(0, int(assignment.get("requested_channels") or 0) - int(assignment.get("assigned_channels") or 0))
        bandwidth_mhz = float(rich.get("bandwidth_khz") or 0) / 1000
        width = max(estimated_width, missing_channels * max(0.001, bandwidth_mhz), 1.0)
        band_group = str(assignment.get("band_group") or "").strip()
        if not band_group:
            alternatives = rich.get("alternative_resources") or []
            usable = next((item for item in alternatives if item.get("band_group") and item.get("status") != "不可用"), None)
            band_group = str((usable or {}).get("band_group") or "").strip()
        if not band_group:
            continue
        candidates.append(
            {
                "assignment": assignment,
                "band_group": band_group,
                "width_mhz": width,
                "priority": int(rich.get("priority") or 1),
                "missing_channels": missing_channels,
            }
        )
    if not candidates:
        return []
    by_band: dict[str, dict] = {}
    for item in candidates:
        band_group = item["band_group"]
        group = by_band.setdefault(
            band_group,
            {
                "band_group": band_group,
                "width_mhz": 0.0,
                "priority": 0,
                "missing_channels": 0,
                "equipment_group_ids": [],
            },
        )
        group["width_mhz"] += float(item["width_mhz"] or 0)
        group["priority"] = max(int(group["priority"] or 0), int(item["priority"] or 0))
        group["missing_channels"] += int(item["missing_channels"] or 0)
        group["equipment_group_ids"].append(item["assignment"].get("equipment_group_id"))
    grouped = sorted(
        by_band.values(),
        key=lambda item: (item["priority"], item["missing_channels"], item["width_mhz"]),
        reverse=True,
    )
    ranges = []
    for item in grouped[: max(1, limit)]:
        ids = ", ".join(str(group_id) for group_id in item["equipment_group_ids"] if group_id)
        supplement = _supplement_range_after_band(
            item["band_group"],
            visualization,
            max(1.0, min(60.0, float(item["width_mhz"] or 0) * 1.25)),
            f"智能体根据 {ids} 的未满足/部分满足缺口建议补充的模拟可用窗口",
        )
        if supplement:
            ranges.append(supplement)
    return ranges


def _supplement_range_after_band(band_group: str, visualization: dict, requested_width_mhz: float, reason: str) -> dict | None:
    timeline_rows = [row for row in visualization.get("spectrum_timeline", []) if row.get("band_group") == band_group]
    if not timeline_rows:
        return None
    end_mhz = max(float(row.get("end_mhz") or 0) for row in timeline_rows)
    start_mhz = min(float(row.get("start_mhz") or 0) for row in timeline_rows)
    if end_mhz <= start_mhz:
        return None
    current_width = max(0.001, end_mhz - start_mhz)
    suggested_width = max(1.0, min(60.0, max(requested_width_mhz, current_width * 0.03)))
    gap = max(0.05, min(2.0, current_width * 0.01))
    supplement_start = round(end_mhz + gap, 3)
    supplement_end = round(supplement_start + suggested_width, 3)
    return {
        "band_group": band_group,
        "start_mhz": supplement_start,
        "end_mhz": supplement_end,
        "reason": reason,
    }


def _agent_next_actions(
    summary: dict,
    assignments: list[dict],
    risk_items: list[dict],
    visualization: dict,
    versions: dict,
    scores: dict,
    replan_effect: dict | None = None,
    scale_evidence: dict | None = None,
) -> list[dict]:
    actions = []
    unsatisfied = [item for item in assignments if item.get("status") == "未满足"]
    partial = [item for item in assignments if item.get("status") == "部分满足"]
    high_risks = [item for item in risk_items if item.get("severity") == "高"]
    medium_risks = [item for item in risk_items if item.get("severity") == "中"]
    pressure_bands = ((summary.get("bottleneck_analysis") or {}).get("band_bottlenecks") or [])[:3]
    performance_history = versions.get("performance_history", []) or []
    capacity_profile = (performance_history[0].get("capacity_profile") or {}) if performance_history else {}
    batch_plan = (scale_evidence or {}).get("batch_plan") or {}
    flat_unused_ranges = _flat_replan_unused_added_ranges(replan_effect)
    flat_strategy_stall = _flat_replan_strategy_stall(replan_effect)
    open_plan_issue = bool(unsatisfied or partial or high_risks or medium_risks)
    if unsatisfied:
        targets = [item["equipment_group_id"] for item in unsatisfied[:3]]
        actions.append(
            _agent_action(
                "recover_unsatisfied",
                "高",
                "优先恢复未满足装备组",
                f"{len(unsatisfied)} 个装备组未满足，直接影响任务可执行性。",
                f"要求 {', '.join(targets)} 必须完全满足，允许调整备用频段并重新规划。",
                {"objective": "task_assurance", "required_full_targets": targets, "allow_low_priority_degrade": False},
            )
        )
    if partial:
        targets = [item["equipment_group_id"] for item in sorted(partial, key=lambda row: (row.get("priority") or 0, row.get("requested_channels") or 0), reverse=True)[:3]]
        supplements = _supplement_ranges_for_unmet_assignments(partial, visualization)
        payload = {"objective": "task_assurance", "required_full_targets": targets}
        message = f"优先将 {', '.join(targets)} 设置为必须完全满足；若不可行，保留降级并写明原因。"
        if supplements and not flat_unused_ranges:
            payload["available_ranges"] = supplements
            payload["constraint_weights"] = {"task": 95, "risk": 70, "spectrum": 40, "priority": 80, "switching": 25, "reuse": 25}
            range_text = "；".join(
                f"{item['band_group']} {item['start_mhz']}-{item['end_mhz']} MHz" for item in supplements
            )
            message = (
                f"优先将 {', '.join(targets)} 设置为必须完全满足，并补充 {range_text} "
                "连续可用窗口后重算。"
            )
        elif flat_unused_ranges:
            payload["constraint_weights"] = {"task": 95, "risk": 75, "spectrum": 55, "priority": 85, "switching": 35, "reuse": 35}
            message = (
                f"上一轮新增频段未被采用，先将 {', '.join(targets)} 设置为必须完全满足并复核兼容/目标权重，"
                "本轮不继续追加同类可用窗口。"
            )
        actions.append(
            _agent_action(
                "explain_or_upgrade_partial",
                "高" if not unsatisfied else "中",
                "处理部分满足装备组",
                f"{len(partial)} 个装备组为部分满足，需要决定接受降级还是补资源。",
                message,
                payload,
            )
        )
    if high_risks or medium_risks:
        actions.append(
            _agent_action(
                "risk_first_replan",
                "高" if high_risks else "中",
                "执行风险最低重规划",
                f"当前存在高风险 {len(high_risks)} 个、中风险 {len(medium_risks)} 个。",
                "切换到风险最低策略，优先降低保护频率靠近和复用距离不足。",
                {
                    "objective": "minimize_interference",
                    "strategy_profile": "risk_first",
                    "constraint_weights": {"risk": 95, "task": 65, "spectrum": 45, "priority": 70, "switching": 25, "reuse": 25},
                },
            )
        )
    if pressure_bands and open_plan_issue:
        top = pressure_bands[0]
        supplement = None if flat_unused_ranges else (_supplement_range_for_unmet_assignment(assignments, visualization) or _supplement_range_from_pressure_band(top, visualization))
        payload = {"avoid_band_groups": [top.get("band_group")], "objective": "task_assurance"}
        title = "缓解瓶颈频段池"
        message = f"减少对 {top.get('band_group')} 的依赖，或增加相邻/备用频段窗口后重算。"
        if supplement:
            payload = {
                "objective": "task_assurance",
                "available_ranges": [supplement],
                "constraint_weights": {"task": 90, "risk": 70, "spectrum": 45, "priority": 75, "switching": 35, "reuse": 35},
            }
            title = "补充瓶颈频段资源"
            message = f"为 {top.get('band_group')} 补充 {supplement['start_mhz']}-{supplement['end_mhz']} MHz 备用可用窗口后重算。"
        actions.append(
            _agent_action(
                "relieve_bottleneck_band",
                "中",
                title,
                f"{top.get('band_group')} 压力分 {top.get('pressure_score')}，净可用 {top.get('clean_available_width_mhz')} MHz。",
                message,
                payload,
            )
        )
    if flat_unused_ranges or flat_strategy_stall:
        actions.append(_agent_pivot_action_after_flat_replan(summary, high_risks, medium_risks, replan_effect, capacity_profile))
    if capacity_profile and capacity_profile.get("status") != "容量充足":
        recommended = capacity_profile.get("recommended") or {}
        largest = capacity_profile.get("largest") or {}
        recommended_units = recommended.get("task_unit_count") or "-"
        recommended_groups = recommended.get("equipment_group_count") or "-"
        largest_units = largest.get("task_unit_count") or "-"
        largest_groups = largest.get("equipment_group_count") or "-"
        batch_count = batch_plan.get("batch_count")
        batch_suffix = f"；当前预案为 {batch_count} 个批次" if batch_plan.get("available") and batch_count else ""
        actions.append(
            _agent_action(
                "capacity_boundary_split",
                "中",
                "按容量边界分批规划",
                f"压测显示最大规模 {largest_units} 单元/{largest_groups} 装备组已超出质量边界，瓶颈为{capacity_profile.get('problem_focus', '规模扩展')}。",
                f"将后续大规模任务拆分为不超过 {recommended_units} 个任务单元、{recommended_groups} 个装备组的批次{batch_suffix}，并优先补充连续宽带资源后复测。",
                {"operation": "capacity_batch_planning", "capacity_profile": capacity_profile, "batch_plan": batch_plan},
            )
        )
    if replan_effect and replan_effect.get("status") == "flat":
        actions.append(
            _agent_action(
                "explain_flat_replan",
                "中",
                "定位重规划无明显收益原因",
                replan_effect.get("summary", "上一轮重规划收益不明显，需要继续定位约束。"),
                replan_effect.get("recommendation", "按未满足装备组反推频段和兼容规则后再重算。"),
                {"operation": "preview_replan_from_suggestion"},
            )
        )
    if replan_effect and replan_effect.get("status") == "regressed" and replan_effect.get("base_run_id"):
        actions.append(
            _agent_action(
                "rollback_to_base_run",
                "高",
                "回退查看上一有效版本",
                replan_effect.get("summary", "上一轮重规划导致关键指标下降。"),
                f"先切回运行 #{replan_effect.get('base_run_id')} 作为安全基线，再重新选择约束较弱的策略。",
                {"operation": "select_task_run", "run_id": replan_effect.get("base_run_id")},
            )
        )
        if _replan_used_strategy(replan_effect, {"minimize_bandwidth"}, {"spectrum_saving"}):
            operation_payload = (
                {"operation": "capacity_batch_planning", "capacity_profile": capacity_profile}
                if capacity_profile
                else {"operation": "task_performance_batch"}
            )
            actions.append(
                _agent_action(
                    "capacity_after_spectrum_regression",
                    "中",
                    "频谱节约回归后复测容量边界",
                    "频谱节约策略导致指标下降，说明继续压缩占用可能触碰容量或连续带宽边界。",
                    "先回退到上一有效版本，再运行阶梯压测或按容量画像分批规划，确认可承载规模后再重算。",
                    operation_payload,
                )
            )
    if len(versions.get("runs", [])) < 2:
        actions.append(
            _agent_action(
                "create_version_comparison",
                "中",
                "形成可比较版本",
                "当前成功规划版本不足，无法充分证明动态重规划收益。",
                "执行一次受控重规划，并对比保障率、风险和频段占用变化。",
                {"objective": "minimize_interference"},
            )
        )
    if not versions.get("performance_history"):
        actions.append(
            _agent_action(
                "run_batch_performance",
                "中",
                "运行阶梯压测",
                "缺少规模效能证据，无法判断智能体在大规模装备下是否高效。",
                "运行项目级阶梯压测，记录耗时、质量分和瓶颈变化。",
                {"operation": "task_performance_batch"},
            )
        )
    if scores.get("dynamic_replanning", 0) < 75:
        actions.append(
            _agent_action(
                "strengthen_replanning_loop",
                "中",
                "增强重规划闭环",
                f"动态重规划能力当前 {scores.get('dynamic_replanning')} 分。",
                "把本面板建议转入预览变更清单，形成建议-确认-重算-对比闭环。",
                {"operation": "preview_replan_from_suggestion"},
            )
        )
    if not actions:
        actions.append(
            _agent_action(
                "human_review",
                "低",
                "进入人工复核",
                "当前关键门槛基本满足。",
                "导出 Excel 和 HTML 报告，进行人工审核和归档。",
                {"operation": "export_report"},
            )
        )
    return _rank_agent_actions(actions, summary, replan_effect)[:6]


def _flat_replan_unused_added_ranges(replan_effect: dict | None) -> bool:
    if not replan_effect or replan_effect.get("status") != "flat":
        return False
    if not replan_effect.get("added_ranges"):
        return False
    usage = replan_effect.get("added_range_usage") or []
    used_width = sum(float(item.get("used_width_mhz") or 0) for item in usage)
    used_count = sum(int(item.get("used_assignment_count") or 0) for item in usage)
    return used_width <= 0 and used_count == 0


def _flat_replan_strategy_stall(replan_effect: dict | None) -> bool:
    if not replan_effect or replan_effect.get("status") != "flat":
        return False
    return _replan_used_strategy(replan_effect, {"minimize_interference", "minimize_bandwidth"}, {"risk_first", "spectrum_saving"})


def _replan_used_strategy(replan_effect: dict | None, objectives: set[str], strategies: set[str]) -> bool:
    if not replan_effect:
        return False
    current_values = {
        str(replan_effect.get("current_objective") or ""),
        str(replan_effect.get("current_effective_objective") or ""),
        str(replan_effect.get("current_strategy_profile") or ""),
    }
    return bool(current_values & objectives) or bool(current_values & strategies)


def _agent_pivot_action_after_flat_replan(summary: dict, high_risks: list[dict], medium_risks: list[dict], replan_effect: dict | None, capacity_profile: dict | None = None) -> dict:
    if _replan_used_strategy(replan_effect, {"minimize_interference"}, {"risk_first"}):
        payload = {
            "objective": "minimize_bandwidth",
            "strategy_profile": "spectrum_saving",
            "constraint_weights": {"task": 65, "risk": 55, "spectrum": 95, "priority": 55, "switching": 35, "reuse": 70},
        }
        used_mhz = round(float(summary.get("used_bandwidth_mhz") or 0), 3)
        return _agent_action(
            "pivot_after_flat_replan",
            "高",
            "风险无收益后转向频谱节约",
            "上一轮风险优先重规划收益不明显，继续沿同一风险目标搜索的边际收益较低。",
            f"改用频谱节约策略重算，尝试压缩当前约 {used_mhz} MHz 的占用带宽，并对比风险是否保持可接受。",
            payload,
        )
    if _replan_used_strategy(replan_effect, {"minimize_bandwidth"}, {"spectrum_saving"}):
        payload = (
            {"operation": "capacity_batch_planning", "capacity_profile": capacity_profile}
            if capacity_profile
            else {"operation": "task_performance_batch"}
        )
        return _agent_action(
            "pivot_after_flat_replan",
            "高",
            "频谱节约无收益后复测容量",
            "上一轮频谱节约重规划收益不明显，继续在同一目标下搜索容易陷入低收益循环。",
            "停止在风险/节约目标之间反复切换，先复测容量边界或按容量画像分批规划，再决定是否扩大资源或拆分任务。",
            payload,
        )
    if high_risks or medium_risks:
        payload = {
            "objective": "minimize_interference",
            "strategy_profile": "risk_first",
            "constraint_weights": {"risk": 95, "task": 65, "spectrum": 45, "priority": 70, "switching": 25, "reuse": 25},
        }
        return _agent_action(
            "pivot_after_flat_replan",
            "高",
            "转向风险隔离重规划",
            "上一轮新增可用频段未被采用，继续补同类资源收益较低；当前仍有风险项需要压降。",
            "停止继续追加同类可用窗口，改用风险最低策略重算，优先压降复用距离、保护频率靠近和邻频风险。",
            payload,
        )
    payload = {
        "objective": "minimize_bandwidth",
        "strategy_profile": "spectrum_saving",
        "constraint_weights": {"task": 65, "risk": 55, "spectrum": 95, "priority": 55, "switching": 35, "reuse": 70},
    }
    used_mhz = round(float(summary.get("used_bandwidth_mhz") or 0), 3)
    return _agent_action(
        "pivot_after_flat_replan",
        "高",
        "转向频谱节约重规划",
        "上一轮新增可用频段未被采用，继续补频不会明显改变求解器选择。",
        f"停止继续追加同类可用窗口，改用频谱节约策略重算，尝试压缩当前约 {used_mhz} MHz 的占用带宽。",
        payload,
    )


def _agent_action(action_id: str, priority: str, title: str, why: str, suggested_message: str, payload: dict) -> dict:
    return {
        "action_id": action_id,
        "priority": priority,
        "title": title,
        "why": why,
        "suggested_message": suggested_message,
        "deterministic_payload": payload,
    }


def _rank_agent_actions(actions: list[dict], summary: dict, replan_effect: dict | None = None) -> list[dict]:
    ranked = []
    for action in actions:
        item = dict(action)
        score = _agent_action_rank_score(item, summary, replan_effect)
        item["rank_score"] = round(score, 1)
        item["expected_gain"] = _agent_action_expected_gain(item, summary, replan_effect)
        item["guardrail"] = _agent_action_guardrail(item)
        ranked.append(item)
    return sorted(ranked, key=lambda item: (-float(item.get("rank_score") or 0), _priority_sort_value(item.get("priority")), item.get("action_id", "")))


def _priority_sort_value(priority: str | None) -> int:
    return {"高": 0, "中": 1, "低": 2}.get(str(priority or ""), 9)


def _agent_action_rank_score(action: dict, summary: dict, replan_effect: dict | None = None) -> float:
    score = {"高": 80.0, "中": 55.0, "低": 30.0}.get(action.get("priority"), 40.0)
    action_id = action.get("action_id")
    payload = action.get("deterministic_payload") or {}
    status = (replan_effect or {}).get("status")
    unsatisfied = int(summary.get("unsatisfied_group_count") or 0)
    partial = int(summary.get("partial_group_count") or 0)
    high_risk = int(summary.get("high_risk_count") or 0)

    if status == "regressed":
        if action_id == "rollback_to_base_run":
            score += 40
        elif action_id == "capacity_after_spectrum_regression":
            score += 20
        elif action_id in {"risk_first_replan", "recover_unsatisfied"}:
            score += 8
    elif status == "flat":
        if action_id == "pivot_after_flat_replan":
            score += 25
        if action_id in {"relieve_bottleneck_band", "risk_first_replan", "explain_flat_replan"}:
            score += 12
        if payload.get("available_ranges") and _flat_replan_unused_added_ranges(replan_effect):
            score -= 25
    elif status == "improved":
        if action_id in {"recover_unsatisfied", "relieve_bottleneck_band", "risk_first_replan"}:
            score += 8

    if unsatisfied and action_id == "recover_unsatisfied":
        score += min(18, unsatisfied)
    if partial and action_id == "explain_or_upgrade_partial":
        score += min(10, partial)
    if high_risk and action_id == "risk_first_replan":
        score += min(16, high_risk)
    if payload.get("available_ranges") and (unsatisfied or partial):
        score += 8
    if payload.get("operation") == "task_performance_batch" and not high_risk and not unsatisfied:
        score += 10
    if action_id == "capacity_boundary_split":
        score += 12 if payload.get("capacity_profile") else 0
    return min(130.0, score)


def _agent_action_expected_gain(action: dict, summary: dict, replan_effect: dict | None = None) -> str:
    action_id = action.get("action_id")
    payload = action.get("deterministic_payload") or {}
    if action_id == "rollback_to_base_run":
        return "恢复到上一成功版本作为安全基线，避免继续沿用已变差的方案。"
    if payload.get("available_ranges"):
        width = sum(max(0.0, float(item.get("end_mhz") or 0) - float(item.get("start_mhz") or 0)) for item in payload.get("available_ranges", []))
        return f"预计新增约 {round(width, 3)} MHz 可用窗口，优先缓解未满足或部分满足装备组。"
    if action_id == "recover_unsatisfied":
        return f"预计优先拉升 {min(3, int(summary.get('unsatisfied_group_count') or 0))} 个未满足装备组的保障状态。"
    if action_id == "risk_first_replan":
        return "预计降低保护频率靠近、复用距离不足和高功率近距离风险。"
    if action_id == "pivot_after_flat_replan":
        if payload.get("operation") in {"task_performance_batch", "capacity_batch_planning"}:
            return "预计停止低收益目标循环，转向容量边界复测或分批规划。"
        if payload.get("objective") == "minimize_interference":
            return "预计停止重复补频，转而压降剩余中高风险链路。"
        return "预计停止重复补频，转而压缩已满足方案的频谱占用。"
    if action_id == "capacity_after_spectrum_regression":
        return "预计先回退低收益版本，再用容量边界证据判断是否需要分批规划。"
    if action_id == "explain_or_upgrade_partial":
        return "预计把部分满足对象转为必须满足或形成可审计的降级理由。"
    if action_id == "run_batch_performance":
        return "预计补齐规模效能证据，用于判断大规模任务下的求解稳定性。"
    if action_id == "capacity_boundary_split":
        profile = payload.get("capacity_profile") or {}
        recommended = profile.get("recommended") or {}
        return f"预计把超大规模任务收敛到 {recommended.get('task_unit_count', '-')} 单元/{recommended.get('equipment_group_count', '-')} 装备组以内，降低质量塌陷和连续带宽瓶颈。"
    if action_id == "explain_flat_replan":
        return (replan_effect or {}).get("recommendation", "预计定位上一轮无收益原因并收窄下一步动作。")
    return "预计补齐当前能力面板中的薄弱环节。"


def _agent_action_guardrail(action: dict) -> str:
    payload = action.get("deterministic_payload") or {}
    if action.get("action_id") == "rollback_to_base_run":
        return "只切换当前查看和导出版本，不删除新版本和审计记录。"
    if payload.get("available_ranges"):
        return "新增频段仍通过结构化规则、兼容性和风险复核，不由 LLM 直接决定指配。"
    if payload.get("required_full_targets"):
        return "若必须满足导致不可行，应保留不可行原因并允许人工确认降级。"
    if payload.get("operation") == "task_performance_batch":
        return "压测会生成多次规划版本和审计记录，不改变人工选定的最终方案。"
    if payload.get("operation") == "capacity_batch_planning":
        return "容量边界只给出拆分和复测建议，不直接改变当前频率指配；实际拆分仍需人工确认任务边界。"
    if action.get("action_id") == "pivot_after_flat_replan":
        return "转向动作只改变目标函数和权重，仍需走预览确认和确定性求解复核，不自动接受低收益方案。"
    return "动作执行前进入预览或确定性接口，保留审计记录。"


def _agent_artifact_checklist(run_id: int | None, summary: dict, assignments: list[dict], risk_items: list[dict], visualization: dict, versions: dict) -> list[dict]:
    scale_evidence = _agent_scale_evidence(versions)
    return [
        {
            "item": "最新成功规划版本",
            "covered": run_id is not None,
            "evidence": f"run_id={run_id}" if run_id is not None else "无成功版本",
        },
        {
            "item": "装备组分配结果",
            "covered": bool(assignments),
            "evidence": f"{len(assignments)} 条装备组分配",
        },
        {
            "item": "风险明细",
            "covered": "risk_item_count" in summary,
            "evidence": f"{len(risk_items)} 条风险/部分满足明细",
        },
        {
            "item": "解释链",
            "covered": any(item.get("explanation_chain") for item in visualization.get("assignments", [])),
            "evidence": f"{sum(1 for item in visualization.get('assignments', []) if item.get('explanation_chain'))} 条解释链",
        },
        {
            "item": "瓶颈和频谱损失",
            "covered": bool(summary.get("bottleneck_analysis")) and bool(summary.get("spectrum_contention")),
            "evidence": "已生成瓶颈频段、冲突网络和频谱损失来源" if summary.get("bottleneck_analysis") else "缺少瓶颈分析",
        },
        {
            "item": "版本审计",
            "covered": bool(versions.get("audit_logs")),
            "evidence": f"{len(versions.get('audit_logs', []))} 条审计记录",
        },
        {
            "item": "规模效能证据",
            "covered": bool(scale_evidence.get("available") and scale_evidence.get("capacity_defined")),
            "evidence": str(scale_evidence.get("evidence") or "尚未形成压测证据"),
        },
    ]


def _agent_strategy_history(versions: dict, current_run_id: int | None = None) -> list[dict]:
    rows = []
    for run in sorted(versions.get("runs", []) or [], key=lambda item: int(item.get("run_id") or 0)):
        run_id = int(run.get("run_id") or 0)
        if current_run_id and run_id > int(current_run_id):
            continue
        summary = run.get("summary") or {}
        rows.append(
            {
                "run_id": run_id,
                "objective": summary.get("requested_objective") or run.get("objective") or summary.get("effective_objective"),
                "effective_objective": summary.get("effective_objective"),
                "strategy_profile": summary.get("strategy_profile") or "balanced",
                "task_satisfaction_avg": float(summary.get("task_satisfaction_avg") or 0),
                "quality_total": _summary_quality(summary),
                "high_risk_count": int(summary.get("high_risk_count") or 0),
                "medium_risk_count": int(summary.get("medium_risk_count") or 0),
                "partial_group_count": int(summary.get("partial_group_count") or 0),
                "unsatisfied_group_count": int(summary.get("unsatisfied_group_count") or 0),
                "used_bandwidth_mhz": float(summary.get("used_bandwidth_mhz") or 0),
                "elapsed_ms": int(run.get("elapsed_ms") or 0),
                "created_at": run.get("created_at"),
            }
        )
    history = rows[-8:]
    previous = None
    for item in history:
        if previous is None:
            item["transition_status"] = "baseline"
            item["transition_label"] = "基线"
            item["delta_quality"] = 0.0
            item["delta_satisfaction"] = 0.0
        else:
            delta_quality = round(float(item["quality_total"] or 0) - float(previous["quality_total"] or 0), 3)
            delta_satisfaction = round(float(item["task_satisfaction_avg"] or 0) - float(previous["task_satisfaction_avg"] or 0), 3)
            item["delta_quality"] = delta_quality
            item["delta_satisfaction"] = delta_satisfaction
            if delta_quality > 0.05 or delta_satisfaction > 0.05 or item["unsatisfied_group_count"] < previous["unsatisfied_group_count"] or item["high_risk_count"] < previous["high_risk_count"]:
                item["transition_status"] = "improved"
                item["transition_label"] = "改善"
            elif delta_quality < -0.05 or delta_satisfaction < -0.05 or item["unsatisfied_group_count"] > previous["unsatisfied_group_count"] or item["high_risk_count"] > previous["high_risk_count"]:
                item["transition_status"] = "regressed"
                item["transition_label"] = "回退"
            else:
                item["transition_status"] = "flat"
                item["transition_label"] = "持平"
        previous = item
    return history


def _performance_history_from_logs(session: Session, project_id: int) -> list[dict]:
    logs = session.exec(
        select(AuditLog)
        .where(AuditLog.project_id == project_id, AuditLog.action == "task_performance_batch")
        .order_by(AuditLog.id.desc())
        .limit(8)
    ).all()
    history = []
    for log in logs:
        try:
            payload = json.loads(log.detail or "{}")
        except json.JSONDecodeError:
            payload = {}
        summary = payload.get("summary", {})
        history.append(
            {
                "id": log.id,
                "created_at": log.created_at.isoformat(),
                "scenario_count": summary.get("scenario_count", 0),
                "run_count": summary.get("run_count", 0),
                "max_elapsed_ms": summary.get("max_elapsed_ms", 0),
                "avg_elapsed_ms": summary.get("avg_elapsed_ms", 0),
                "max_equipment_group_count": summary.get("max_equipment_group_count", 0),
                "max_equipment_sample_count": summary.get("max_equipment_sample_count", 0),
                "best_quality_total": summary.get("best_quality_total", 0),
                "leader_summary": payload.get("leader_summary", ""),
                "capacity_profile": payload.get("capacity_profile", {}),
            }
        )
    return history


def _parse_replan_changes(session: Session, project_id: int, payload: dict) -> dict:
    message = str(payload.get("message") or "")
    task_units = db_task_units_to_dicts(session, project_id)
    equipment_groups = db_equipment_groups_to_dicts(session, project_id)
    spectrum_rules = db_spectrum_rules_to_dicts(session, project_id)
    base_context = _replan_base_context(session, project_id, payload.get("base_run_id"))
    text_objective = _objective_from_message(message)
    requested_objective = payload.get("objective") or text_objective or base_context.get("objective") or "task_assurance"
    payload_weights = payload.get("constraint_weights") or {}
    normalized_weights = _normalize_constraint_weights(payload_weights)
    changes = {
        "base_run_id": base_context.get("run_id"),
        "base_objective": base_context.get("objective"),
        "reuse_strategy_from_run_id": _normalized_run_id(payload.get("reuse_strategy_from_run_id")),
        "objective": requested_objective,
        "available_ranges": [dict(item) for item in payload.get("available_ranges", [])],
        "forbidden_ranges": [dict(item) for item in payload.get("forbidden_ranges", [])],
        "priority_updates": [dict(item) for item in payload.get("priority_updates", [])],
        "satisfaction_updates": [dict(item) for item in payload.get("satisfaction_updates", [])],
        "locked_equipment_group_ids": list(payload.get("locked_equipment_group_ids", []) or []),
        "locked_task_unit_ids": list(payload.get("locked_task_unit_ids", []) or []),
        "avoid_band_groups": list(payload.get("avoid_band_groups", []) or []),
        "forced_band_groups": dict(payload.get("forced_band_groups", {}) or {}),
        "required_full_targets": list(payload.get("required_full_targets", []) or []),
        "allow_low_priority_degrade": bool(payload.get("allow_low_priority_degrade", True)),
        "constraint_weights": normalized_weights,
        "strategy_profile": payload.get("strategy_profile") or "balanced",
        "base_strategy_profile": base_context.get("strategy_profile"),
        "trial_context": _sanitize_trial_context(payload.get("trial_context")),
    }
    if text_objective:
        changes["objective"] = text_objective
    changes["available_ranges"].extend(_available_ranges_from_message(message, spectrum_rules))
    changes["forbidden_ranges"].extend(_forbidden_ranges_from_message(message, spectrum_rules))
    changes["priority_updates"].extend(_priority_updates_from_message(message, task_units, equipment_groups))
    changes["satisfaction_updates"].extend(_satisfaction_updates_from_message(message, task_units))
    changes["locked_equipment_group_ids"].extend(_locked_groups_from_message(message, equipment_groups))
    changes["locked_equipment_group_ids"].extend(_group_ids_for_locked_units(changes["locked_task_unit_ids"], task_units, equipment_groups))
    changes["avoid_band_groups"].extend(_avoid_bands_from_message(message, spectrum_rules))
    changes["forced_band_groups"].update(_forced_bands_from_message(message, spectrum_rules, task_units, equipment_groups))
    changes["required_full_targets"].extend(_required_full_targets_from_message(message, task_units, equipment_groups))
    changes["locked_equipment_group_ids"] = _unique_keep_order(changes["locked_equipment_group_ids"])
    changes["locked_task_unit_ids"] = _unique_keep_order(changes["locked_task_unit_ids"])
    changes["avoid_band_groups"] = _unique_keep_order(changes["avoid_band_groups"])
    changes["required_full_targets"] = _unique_keep_order(changes["required_full_targets"])
    changes["available_ranges"] = _unique_frequency_ranges(changes["available_ranges"])
    changes["forbidden_ranges"] = _unique_frequency_ranges(changes["forbidden_ranges"])
    changes["objective_changed"] = _replan_objective_changed(changes["base_objective"], changes["objective"], payload.get("objective") or text_objective)
    changes["constraint_weights_changed"] = _replan_weights_changed(
        base_context.get("constraint_weights"),
        changes["constraint_weights"],
        payload_weights,
        changes.get("base_strategy_profile"),
        changes.get("strategy_profile"),
    )
    return changes


def _replan_base_context(session: Session, project_id: int, base_run_id: object | None) -> dict:
    run = None
    normalized_run_id = _normalized_run_id(base_run_id)
    if normalized_run_id:
        candidate = session.get(PlanningRun, normalized_run_id)
        if candidate and candidate.project_id == project_id and candidate.status == "success":
            run = candidate
    if run is None:
        task_objective_names = [item["objective"] for item in TASK_OBJECTIVES]
        run = session.exec(
            select(PlanningRun)
            .where(PlanningRun.project_id == project_id, PlanningRun.objective.in_(task_objective_names), PlanningRun.status == "success")
            .order_by(PlanningRun.id.desc())
        ).first()
    if run is None:
        return {}
    summary = _json_dict(run.summary_json or "{}")
    return {
        "run_id": run.id,
        "objective": run.objective,
        "constraint_weights": _normalize_constraint_weights(summary.get("constraint_weights") or {}),
        "strategy_profile": summary.get("strategy_profile") or "balanced",
    }


def _replan_base_summary(session: Session, project_id: int, base_run_id: object | None) -> tuple[int | None, dict]:
    context = _replan_base_context(session, project_id, base_run_id)
    run_id = context.get("run_id")
    if not run_id:
        return None, {}
    run = session.get(PlanningRun, int(run_id))
    if not run or run.project_id != project_id or run.status != "success":
        return None, {}
    return run.id, _json_dict(run.summary_json or "{}")


def _normalized_run_id(value: object | None) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _replan_objective_changed(base_objective: object | None, objective: object | None, explicit_objective: object | None) -> bool:
    if base_objective:
        return str(objective or "") != str(base_objective)
    return bool(explicit_objective)


def _replan_weights_changed(
    base_weights: dict | None,
    current_weights: dict,
    raw_payload_weights: object,
    base_strategy_profile: object | None,
    strategy_profile: object | None,
) -> bool:
    has_payload_weights = bool(raw_payload_weights)
    strategy_changed = bool(base_strategy_profile and strategy_profile and str(base_strategy_profile) != str(strategy_profile))
    if not has_payload_weights:
        return strategy_changed
    if not base_weights:
        return True
    return strategy_changed or any(abs(float(current_weights.get(key, 0)) - float(base_weights.get(key, 0))) > 0.001 for key in set(current_weights) | set(base_weights))


def _apply_replan_changes(session: Session, project_id: int, changes: dict) -> dict:
    applied = {
        "available_range_count": 0,
        "forbidden_range_count": 0,
        "priority_update_count": 0,
        "satisfaction_update_count": 0,
    }
    rules = db_spectrum_rules_to_dicts(session, project_id)
    for idx, item in enumerate(changes["available_ranges"]):
        start = float(item.get("start_mhz") or 0)
        end = float(item.get("end_mhz") or 0)
        if end <= start:
            continue
        band_group = item.get("band_group") or _infer_band_group(start, end, rules)
        if not band_group:
            continue
        defaults = _available_rule_defaults_for_band(rules, band_group)
        rule_id = f"SR-USER-AVAIL-{int(time.time() * 1000)}-{idx}"
        data = {
            "rule_id": rule_id,
            "rule_type": "可用",
            "band_group": band_group,
            "spectrum_relation": defaults.get("spectrum_relation", "可复用"),
            "start_mhz": start,
            "end_mhz": end,
            "channel_step_khz": defaults.get("channel_step_khz", 25),
            "max_bandwidth_khz": defaults.get("max_bandwidth_khz", 25),
            "max_power_w": defaults.get("max_power_w", 1),
            "guard_band_khz": defaults.get("guard_band_khz", 0),
            "compatible_unit_types": defaults.get("compatible_unit_types", ""),
            "compatible_equipment_types": defaults.get("compatible_equipment_types", ""),
            "reason": item.get("reason") or "用户补充可用频段",
            "source": "USER_REPLAN",
            "severity": "低",
        }
        session.add(SpectrumRule(project_id=project_id, raw_json=json.dumps(data, ensure_ascii=False), **data))
        applied["available_range_count"] += 1

    for idx, item in enumerate(changes["forbidden_ranges"]):
        start = float(item.get("start_mhz") or 0)
        end = float(item.get("end_mhz") or 0)
        if end <= start:
            continue
        band_group = item.get("band_group") or _infer_band_group(start, end, rules)
        if not band_group:
            continue
        rule_id = f"SR-USER-FORBID-{int(time.time() * 1000)}-{idx}"
        data = {
            "rule_id": rule_id,
            "rule_type": "禁用",
            "band_group": band_group,
            "spectrum_relation": "禁用",
            "start_mhz": start,
            "end_mhz": end,
            "channel_step_khz": 25,
            "max_bandwidth_khz": 0,
            "max_power_w": 0,
            "guard_band_khz": float(item.get("guard_band_khz") or 0),
            "compatible_unit_types": "",
            "compatible_equipment_types": "",
            "reason": item.get("reason") or "用户临时禁用",
            "source": "USER_REPLAN",
            "severity": "高",
        }
        session.add(SpectrumRule(project_id=project_id, raw_json=json.dumps(data, ensure_ascii=False), **data))
        applied["forbidden_range_count"] += 1

    units = session.exec(select(TaskUnit).where(TaskUnit.project_id == project_id)).all()
    groups = session.exec(select(EquipmentGroup).where(EquipmentGroup.project_id == project_id)).all()
    for update in changes["priority_updates"]:
        target = str(update.get("target") or "").strip()
        priority = max(1, min(10, int(update.get("priority") or 1)))
        matched = False
        for unit in units:
            if _target_matches(target, unit.task_unit_id, unit.name, unit.unit_type):
                unit.priority = priority
                unit.raw_json = _refresh_raw(unit)
                session.add(unit)
                matched = True
        for group in groups:
            if _target_matches(target, group.equipment_group_id, group.equipment_type):
                group.priority = priority
                group.raw_json = _refresh_raw(group)
                session.add(group)
                matched = True
        if matched:
            applied["priority_update_count"] += 1

    for update in changes["satisfaction_updates"]:
        target = str(update.get("task_unit_id") or "").strip()
        ratio = max(0.1, min(1.0, float(update.get("min_satisfaction_ratio") or 1.0)))
        for unit in units:
            if _target_matches(target, unit.task_unit_id, unit.name, unit.unit_type):
                unit.min_satisfaction_ratio = ratio
                unit.raw_json = _refresh_raw(unit)
                session.add(unit)
                applied["satisfaction_update_count"] += 1
                break

    if any(applied.values()):
        _touch_project(session, project_id, "task_constraints_updated")
        session.commit()
    return applied


def _locked_assignments_for_run(session: Session, project_id: int, group_ids: list[str], run_id: int | None = None) -> dict[str, dict]:
    if not group_ids:
        return {}
    task_objective_names = [item["objective"] for item in TASK_OBJECTIVES]
    if run_id:
        run = session.get(PlanningRun, run_id)
        if not run or run.project_id != project_id or run.status != "success":
            return {}
    else:
        run = session.exec(
            select(PlanningRun)
            .where(PlanningRun.project_id == project_id, PlanningRun.status == "success", PlanningRun.objective.in_(task_objective_names))
            .order_by(PlanningRun.id.desc())
        ).first()
    if not run:
        return {}
    locked = {}
    for item in task_assignments_for_run(session, project_id, run.id):
        if item["equipment_group_id"] in group_ids:
            locked[item["equipment_group_id"]] = item
    return locked


def _allocation_from_locked(group: dict, unit: dict, locked: dict, objective: str) -> dict:
    requested_count = int(group.get("count") or locked.get("requested_count") or 0)
    requested_channels = max(1, int(group.get("required_channels") or locked.get("requested_channels") or 1))
    assigned_channels = max(0, min(requested_channels, int(locked.get("assigned_channels") or 0)))
    ratio = min(1.0, assigned_channels / requested_channels) if requested_channels else 0
    satisfied_count = math.floor(requested_count * ratio)
    status = "完全满足" if ratio >= 0.999 else "部分满足" if ratio > 0 else "未满足"
    return {
        "task_unit_id": group["task_unit_id"],
        "equipment_group_id": group["equipment_group_id"],
        "equipment_type": group["equipment_type"],
        "assignment_mode": group.get("assignment_mode") or locked.get("assignment_mode") or "离散信道",
        "band_group": locked.get("band_group"),
        "assigned_resource": locked.get("assigned_resource") or "",
        "requested_count": requested_count,
        "satisfied_count": satisfied_count,
        "requested_channels": requested_channels,
        "assigned_channels": assigned_channels,
        "satisfaction_ratio": round(ratio, 4),
        "status": status,
        "risk_score": locked.get("risk_score", 0 if status == "完全满足" else 45),
        "risk_level": locked.get("risk_level", "低" if status == "完全满足" else "中"),
        "reason": locked.get("reason") or "用户锁定上一版指配结果",
        "decision_notes": f"用户锁定该装备组，按“{_objective_label(objective)}”重算时保持原指配",
    }


def _task_unit_summaries(task_units: list[dict], assignments: list[dict]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    by_unit: dict[str, list[dict]] = defaultdict(list)
    for assignment in assignments:
        by_unit[assignment["task_unit_id"]].append(assignment)
    for unit in task_units:
        items = by_unit.get(unit["task_unit_id"], [])
        requested = sum(int(item.get("requested_count") or 0) for item in items)
        satisfied = sum(int(item.get("satisfied_count") or 0) for item in items)
        result[unit["task_unit_id"]] = {
            "requested_count": requested,
            "satisfied_count": satisfied,
            "satisfaction_ratio": round(satisfied / requested, 4) if requested else 0,
        }
    return result


def _task_summary(task_units: list[dict], equipment_groups: list[dict], assignments: list[dict], risk_items: list[dict], unit_summaries: dict[str, dict]) -> dict:
    ratios = [item.get("satisfaction_ratio", 0) for item in unit_summaries.values()]
    used_width = sum(segment.width_mhz for assignment in assignments for segment in _parse_resource_segments(assignment.get("assigned_resource") or ""))
    status_counter = Counter(item["status"] for item in assignments)
    severity_counter = Counter(item["severity"] for item in risk_items)
    return {
        "task_unit_count": len(task_units),
        "equipment_group_count": len(equipment_groups),
        "equipment_sample_count": sum(int(item.get("count") or 0) for item in equipment_groups),
        "task_satisfaction_avg": round((sum(ratios) / len(ratios) * 100) if ratios else 0, 1),
        "full_group_count": status_counter.get("完全满足", 0),
        "partial_group_count": status_counter.get("部分满足", 0),
        "unsatisfied_group_count": status_counter.get("未满足", 0),
        "used_bandwidth_mhz": round(used_width, 3),
        "risk_item_count": len(risk_items),
        "high_risk_count": severity_counter.get("高", 0),
        "medium_risk_count": severity_counter.get("中", 0),
    }


def _normalize_constraint_weights(weights: dict | None) -> dict:
    defaults = next(item["weights"] for item in PLANNING_WEIGHT_TEMPLATES if item["key"] == "balanced")
    result = dict(defaults)
    for key, value in (weights or {}).items():
        if key in result:
            result[key] = max(0, min(100, float(value or 0)))
    return result


def _effective_objective_from_weights(objective: str, weights: dict) -> str:
    if weights.get("risk", 0) >= 90 and weights.get("risk", 0) >= weights.get("task", 0) + 10:
        return "minimize_interference"
    if weights.get("spectrum", 0) >= 90:
        return "minimize_bandwidth"
    if weights.get("switching", 0) >= 90:
        return "minimize_switching"
    if weights.get("reuse", 0) >= 85 and weights.get("spectrum", 0) >= 65:
        return "maximize_reuse_efficiency"
    if weights.get("priority", 0) >= 85 and objective == "task_assurance":
        return "priority_equipment"
    return objective


def _apply_required_full_flag(assignment: dict, group: dict, unit: dict, required_full_targets: set[str], allow_low_priority_degrade: bool) -> None:
    if not required_full_targets:
        return
    matched = any(
        _target_matches(target, group.get("equipment_group_id", ""), group.get("equipment_type", ""), unit.get("task_unit_id", ""), unit.get("name", ""), unit.get("unit_type", ""))
        for target in required_full_targets
    )
    if not matched:
        return
    assignment["required_full"] = True
    if assignment.get("status") == "完全满足":
        assignment["decision_notes"] = f"{assignment.get('decision_notes', '')}；该对象被标记为必须完全满足，当前已满足"
        return
    assignment["risk_score"] = max(float(assignment.get("risk_score") or 0), 120)
    assignment["risk_level"] = "高"
    assignment["reason"] = f"必须完全满足对象当前{assignment.get('status')}：{assignment.get('reason')}"
    if not allow_low_priority_degrade:
        assignment["decision_notes"] = "已禁止低优先级降级保障，建议扩展可用频段或降低该对象带宽/信道需求"


def _bottleneck_analysis(
    task_units: list[dict],
    equipment_groups: list[dict],
    spectrum_rules: list[dict],
    assignments: list[dict],
    risk_items: list[dict],
) -> dict:
    groups_by_id = {item["equipment_group_id"]: item for item in equipment_groups}
    units_by_id = {item["task_unit_id"]: item for item in task_units}
    clean_segments = _available_segments_by_band(spectrum_rules)
    assigned_by_group = {item["equipment_group_id"]: item for item in assignments}

    band_bottlenecks = []
    for band in sorted({rule.get("band_group") for rule in spectrum_rules if rule.get("band_group")}):
        raw_available_width = sum(
            max(0.0, float(rule.get("end_mhz") or 0) - float(rule.get("start_mhz") or 0))
            for rule in spectrum_rules
            if rule.get("band_group") == band and rule.get("rule_type") == "可用"
        )
        clean_width = sum(segment.width_mhz for segment in clean_segments.get(band, []))
        used_segments = [
            segment
            for assignment in assignments
            if assignment.get("band_group") == band
            for segment in _parse_resource_segments(assignment.get("assigned_resource") or "")
        ]
        used_width = sum(segment.width_mhz for segment in used_segments)
        blockers = [rule for rule in spectrum_rules if rule.get("band_group") == band and rule.get("rule_type") in {"禁用", "保护"}]
        blocker_width = sum(max(0.0, float(rule.get("end_mhz") or 0) - float(rule.get("start_mhz") or 0)) for rule in blockers)
        candidate_groups = [
            group
            for group in equipment_groups
            if band in _split_csv(group.get("preferred_band_group"))
            or band in _split_csv(units_by_id.get(group.get("task_unit_id"), {}).get("preferred_band_groups"))
        ]
        pressure_groups = [
            group
            for group in candidate_groups
            if assigned_by_group.get(group["equipment_group_id"], {}).get("status") != "完全满足"
        ]
        demand_width = sum(float(group.get("bandwidth_khz") or 0) / 1000 * max(1, int(group.get("required_channels") or 1)) for group in candidate_groups)
        pressure_score = _band_pressure_score(raw_available_width, clean_width, used_width, demand_width, len(blockers), len(pressure_groups))
        band_bottlenecks.append(
            {
                "band_group": band,
                "raw_available_width_mhz": round(raw_available_width, 3),
                "clean_available_width_mhz": round(clean_width, 3),
                "blocked_width_mhz": round(blocker_width, 3),
                "used_width_mhz": round(used_width, 3),
                "demand_width_mhz": round(demand_width, 3),
                "utilization_pct": round(used_width / clean_width * 100, 1) if clean_width else 0,
                "blocker_count": len(blockers),
                "pressure_group_count": len(pressure_groups),
                "pressure_score": pressure_score,
                "top_blockers": [
                    {
                        "rule_id": rule.get("rule_id"),
                        "rule_type": rule.get("rule_type"),
                        "start_mhz": rule.get("start_mhz"),
                        "end_mhz": rule.get("end_mhz"),
                        "reason": rule.get("reason"),
                        "severity": rule.get("severity"),
                    }
                    for rule in blockers[:4]
                ],
            }
        )

    equipment_gaps = []
    by_type: dict[str, list[dict]] = defaultdict(list)
    for group in equipment_groups:
        by_type[group.get("equipment_type") or "未分类"].append(group)
    for equipment_type, groups in sorted(by_type.items()):
        related = [assigned_by_group.get(group["equipment_group_id"], {}) for group in groups]
        requested = sum(int(group.get("count") or 0) for group in groups)
        satisfied = sum(int(item.get("satisfied_count") or 0) for item in related)
        partial = sum(1 for item in related if item.get("status") == "部分满足")
        unsatisfied = sum(1 for item in related if item.get("status") == "未满足")
        if partial or unsatisfied:
            main_reason = Counter(item.get("reason") for item in related if item.get("status") != "完全满足").most_common(1)
            equipment_gaps.append(
                {
                    "equipment_type": equipment_type,
                    "group_count": len(groups),
                    "requested_count": requested,
                    "satisfied_count": satisfied,
                    "gap_count": max(0, requested - satisfied),
                    "partial_group_count": partial,
                    "unsatisfied_group_count": unsatisfied,
                    "gap_ratio_pct": round((1 - satisfied / requested) * 100, 1) if requested else 0,
                    "main_reason": main_reason[0][0] if main_reason and main_reason[0][0] else "资源不足",
                }
            )

    task_unit_pressure = []
    risks_by_unit: dict[str, list[dict]] = defaultdict(list)
    for risk in risk_items:
        if risk.get("task_unit_a"):
            risks_by_unit[risk["task_unit_a"]].append(risk)
        if risk.get("task_unit_b"):
            risks_by_unit[risk["task_unit_b"]].append(risk)
    by_unit: dict[str, list[dict]] = defaultdict(list)
    for assignment in assignments:
        by_unit[assignment["task_unit_id"]].append(assignment)
    for unit in task_units:
        items = by_unit.get(unit["task_unit_id"], [])
        requested = sum(int(item.get("requested_count") or 0) for item in items)
        satisfied = sum(int(item.get("satisfied_count") or 0) for item in items)
        partial = sum(1 for item in items if item.get("status") == "部分满足")
        unsatisfied = sum(1 for item in items if item.get("status") == "未满足")
        risk_count = len(risks_by_unit.get(unit["task_unit_id"], []))
        pressure = round((partial * 18 + unsatisfied * 35 + risk_count * 5 + max(0, requested - satisfied) * 0.12), 1)
        task_unit_pressure.append(
            {
                "task_unit_id": unit["task_unit_id"],
                "name": unit.get("name"),
                "unit_type": unit.get("unit_type"),
                "priority": unit.get("priority", 1),
                "requested_count": requested,
                "satisfied_count": satisfied,
                "satisfaction_ratio_pct": round(satisfied / requested * 100, 1) if requested else 0,
                "partial_group_count": partial,
                "unsatisfied_group_count": unsatisfied,
                "risk_count": risk_count,
                "pressure_score": pressure,
            }
        )

    conflict_reasons = Counter(item.get("reason") or item.get("risk_type") or "未说明" for item in risk_items)
    contention_links = []
    for item in sorted(risk_items, key=lambda row: float(row.get("score") or 0), reverse=True):
        if not item.get("equipment_group_b"):
            continue
        group_a = groups_by_id.get(item.get("equipment_group_a"), {})
        group_b = groups_by_id.get(item.get("equipment_group_b"), {})
        contention_links.append(
            {
                "source_unit": item.get("task_unit_a"),
                "target_unit": item.get("task_unit_b"),
                "source_group": item.get("equipment_group_a"),
                "target_group": item.get("equipment_group_b"),
                "source_equipment_type": group_a.get("equipment_type"),
                "target_equipment_type": group_b.get("equipment_type"),
                "severity": item.get("severity"),
                "score": item.get("score", 0),
                "reason": item.get("reason"),
                "resource_a": item.get("resource_a"),
                "resource_b": item.get("resource_b"),
            }
        )
        if len(contention_links) >= 10:
            break

    return {
        "band_bottlenecks": sorted(band_bottlenecks, key=lambda item: item["pressure_score"], reverse=True),
        "equipment_gaps": sorted(equipment_gaps, key=lambda item: (item["unsatisfied_group_count"], item["gap_count"], item["partial_group_count"]), reverse=True)[:12],
        "task_unit_pressure": sorted(task_unit_pressure, key=lambda item: item["pressure_score"], reverse=True),
        "conflict_reasons": [{"reason": reason, "count": count} for reason, count in conflict_reasons.most_common(10)],
        "contention_links": contention_links,
    }


def _spectrum_contention_analysis(
    task_units: list[dict],
    equipment_groups: list[dict],
    spectrum_rules: list[dict],
    assignments: list[dict],
    risk_items: list[dict],
) -> dict:
    groups_by_id = {item["equipment_group_id"]: item for item in equipment_groups}
    units_by_id = {item["task_unit_id"]: item for item in task_units}
    rules_by_band = defaultdict(list)
    for rule in spectrum_rules:
        if rule.get("band_group"):
            rules_by_band[rule["band_group"]].append(rule)
    by_band: dict[str, list[dict]] = defaultdict(list)
    for assignment in assignments:
        if assignment.get("band_group"):
            by_band[assignment["band_group"]].append(assignment)
    available_by_band = _available_segments_by_band(spectrum_rules)
    risk_frequencies = [
        _first_frequency_in_text(risk.get("resource_a") or "")
        for risk in risk_items
        if risk.get("resource_a")
    ]
    band_items = []
    for band, items in sorted(by_band.items()):
        equipment_counter = Counter(item.get("equipment_type") for item in items)
        blockers = [rule for rule in rules_by_band.get(band, []) if rule.get("rule_type") in {"禁用", "保护"}]
        band_segments = available_by_band.get(band, [])
        risk_count = sum(1 for frequency in risk_frequencies if any(segment.start <= frequency <= segment.end for segment in band_segments))
        competing_groups = []
        for item in sorted(items, key=lambda row: float(row.get("risk_score") or 0), reverse=True)[:8]:
            group = groups_by_id.get(item["equipment_group_id"], {})
            unit = units_by_id.get(item["task_unit_id"], {})
            competing_groups.append(
                {
                    "task_unit_id": item["task_unit_id"],
                    "task_unit_name": unit.get("name"),
                    "equipment_group_id": item["equipment_group_id"],
                    "equipment_type": item.get("equipment_type"),
                    "assigned_resource": item.get("assigned_resource"),
                    "status": item.get("status"),
                    "risk_score": item.get("risk_score"),
                    "priority": group.get("priority", 1),
                }
            )
        band_items.append(
            {
                "band_group": band,
                "assignment_count": len(items),
                "equipment_types": [{"equipment_type": key, "count": value} for key, value in equipment_counter.most_common()],
                "blocker_count": len(blockers),
                "blockers": [
                    {
                        "rule_id": rule.get("rule_id"),
                        "rule_type": rule.get("rule_type"),
                        "range_mhz": f"{rule.get('start_mhz')}-{rule.get('end_mhz')}",
                        "reason": rule.get("reason"),
                        "severity": rule.get("severity"),
                    }
                    for rule in blockers[:6]
                ],
                "risk_count": risk_count,
                "competing_groups": competing_groups,
            }
        )
    return {
        "bands": sorted(band_items, key=lambda item: (item["blocker_count"], item["risk_count"], item["assignment_count"]), reverse=True),
        "top_loss_sources": _top_spectrum_loss_sources(spectrum_rules, assignments),
    }


def _first_frequency_in_text(value: str) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)", value or "")
    return float(match.group(1)) if match else -1.0


def _top_spectrum_loss_sources(spectrum_rules: list[dict], assignments: list[dict]) -> list[dict]:
    rows = []
    assignment_bands = Counter(item.get("band_group") for item in assignments if item.get("band_group"))
    for rule in spectrum_rules:
        if rule.get("rule_type") not in {"禁用", "保护"}:
            continue
        width = max(0.0, float(rule.get("end_mhz") or 0) - float(rule.get("start_mhz") or 0))
        guard = float(rule.get("guard_band_khz") or 0) / 1000
        rows.append(
            {
                "rule_id": rule.get("rule_id"),
                "rule_type": rule.get("rule_type"),
                "band_group": rule.get("band_group"),
                "loss_width_mhz": round(width + 2 * guard, 3),
                "affected_assignment_count": assignment_bands.get(rule.get("band_group"), 0),
                "reason": rule.get("reason"),
                "severity": rule.get("severity"),
            }
        )
    return sorted(rows, key=lambda item: (item["loss_width_mhz"], item["affected_assignment_count"]), reverse=True)[:10]


def _band_pressure_score(raw_available_width: float, clean_width: float, used_width: float, demand_width: float, blocker_count: int, pressure_group_count: int) -> float:
    if raw_available_width <= 0:
        return 100.0
    clean_loss = max(0.0, (raw_available_width - clean_width) / raw_available_width) * 30
    utilization = (used_width / clean_width * 35) if clean_width > 0 else 35
    demand_pressure = (demand_width / clean_width * 18) if clean_width > 0 else 18
    blocker_pressure = min(12.0, blocker_count * 2.5)
    group_pressure = min(20.0, pressure_group_count * 2.0)
    return round(min(100.0, clean_loss + utilization + demand_pressure + blocker_pressure + group_pressure), 1)


def _split_csv(value: object) -> list[str]:
    return [item.strip() for item in str(value or "").replace("；", ",").replace("，", ",").split(",") if item.strip()]


def _normalize_band_avoid_map(value: object) -> dict[str, set[str]]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, set[str]] = {}
    for key, raw_bands in value.items():
        target = str(key or "").strip()
        if not target:
            continue
        bands: set[str] = set()
        if isinstance(raw_bands, (list, tuple, set)):
            source = raw_bands
        else:
            source = _split_csv(raw_bands)
        for band in source:
            item = str(band or "").strip()
            if item:
                bands.add(item)
        if bands:
            result[target] = bands
    return result


def _hard_avoid_bands_for_group(group: dict, unit: dict, by_unit: dict[str, set[str]], by_group: dict[str, set[str]]) -> set[str]:
    bands = set(by_group.get(str(group.get("equipment_group_id") or ""), set()))
    bands.update(by_unit.get(str(unit.get("task_unit_id") or group.get("task_unit_id") or ""), set()))
    return bands


def _task_plan_score_components(summary: dict) -> list[dict]:
    satisfaction_gap = max(0.0, 100 - float(summary.get("task_satisfaction_avg") or 0)) * 10
    unsatisfied = float(summary.get("unsatisfied_group_count") or 0) * 80
    partial = float(summary.get("partial_group_count") or 0) * 35
    high_risk = float(summary.get("high_risk_count") or 0) * 30
    bandwidth = float(summary.get("used_bandwidth_mhz") or 0) * 0.05
    return [
        {"key": "satisfaction_gap", "label": "保障率缺口", "value": round(satisfaction_gap, 3), "note": "平均保障率低于 100% 的代价"},
        {"key": "unsatisfied_group", "label": "未满足装备组", "value": round(unsatisfied, 3), "note": "未满足装备组的强惩罚"},
        {"key": "partial_group", "label": "部分满足装备组", "value": round(partial, 3), "note": "部分满足带来的业务牺牲"},
        {"key": "high_risk", "label": "高风险项", "value": round(high_risk, 3), "note": "高风险冲突和保护问题"},
        {"key": "used_bandwidth", "label": "频谱占用", "value": round(bandwidth, 3), "note": "总占用带宽的轻量惩罚"},
    ]


def _task_plan_score_explanation(summary: dict) -> dict:
    components = _task_plan_score_components(summary)
    total = round(sum(float(item["value"]) for item in components), 3)
    return {
        "total_score": total,
        "components": components,
        "interpretation": "综合分越低，说明保障缺口、风险和频谱占用的综合代价越小。",
    }


def _quality_scores(summary: dict) -> dict:
    task_assurance = max(0.0, min(100.0, float(summary.get("task_satisfaction_avg") or 0)))
    interference_risk = max(
        0.0,
        100.0
        - float(summary.get("high_risk_count") or 0) * 14
        - float(summary.get("medium_risk_count") or 0) * 6
        - float(summary.get("risk_item_count") or 0) * 1.5,
    )
    spectrum_efficiency = max(0.0, 100.0 - float(summary.get("used_bandwidth_mhz") or 0) * 0.45)
    executability = max(
        0.0,
        100.0
        - float(summary.get("partial_group_count") or 0) * 8
        - float(summary.get("unsatisfied_group_count") or 0) * 22,
    )
    change_cost = 100.0
    total = task_assurance * 0.35 + interference_risk * 0.25 + spectrum_efficiency * 0.15 + executability * 0.2 + change_cost * 0.05
    return {
        "total": round(total, 1),
        "items": [
            {"key": "task_assurance", "label": "任务保障", "score": round(task_assurance, 1), "note": "任务单元平均保障率"},
            {"key": "interference_risk", "label": "干扰风险", "score": round(interference_risk, 1), "note": "高/中风险项越少分值越高"},
            {"key": "spectrum_efficiency", "label": "频谱效率", "score": round(spectrum_efficiency, 1), "note": "占用带宽越低分值越高"},
            {"key": "executability", "label": "可执行性", "score": round(executability, 1), "note": "未满足和部分满足越少分值越高"},
            {"key": "change_cost", "label": "调整代价", "score": round(change_cost, 1), "note": "当前单方案默认无历史切换代价"},
        ],
    }


def _leader_summary(summary: dict) -> str:
    quality = summary.get("quality_scores", {})
    return (
        f"本方案综合质量 {quality.get('total', 0)} 分，平均保障率 {summary.get('task_satisfaction_avg', 0)}%。"
        f"完全满足 {summary.get('full_group_count', 0)} 个装备组，部分满足 {summary.get('partial_group_count', 0)} 个，"
        f"未满足 {summary.get('unsatisfied_group_count', 0)} 个，高风险 {summary.get('high_risk_count', 0)} 项。"
    )


def _technical_summary(summary: dict) -> str:
    recommendations = summary.get("decision_recommendations") or []
    first = recommendations[0] if recommendations else "当前方案可进入人工复核。"
    return (
        f"求解结果占用 {summary.get('used_bandwidth_mhz', 0)} MHz，风险项 {summary.get('risk_item_count', 0)} 条。"
        f"技术处理建议：{first}"
    )


def _task_plan_score(summary: dict) -> float:
    return float(_task_plan_score_explanation(summary)["total_score"])


def _recommendation_reason(summary: dict, label: str) -> str:
    if int(summary.get("unsatisfied_group_count") or 0):
        return f"{label}方案仍有未满足装备组，适合作为约束紧张时的备选。"
    if int(summary.get("partial_group_count") or 0):
        return f"{label}方案保障率较高，但存在部分满足装备组，需要结合任务优先级确认牺牲是否可接受。"
    if int(summary.get("high_risk_count") or 0):
        return f"{label}方案全部满足需求，但仍存在高风险项，建议复核保护距离。"
    return f"{label}方案在当前约束下风险较低，可作为推荐方案。"


def _decision_table_from_plans(plans: list[dict]) -> list[dict]:
    profiles = [
        ("recommended", "综合推荐", None, "默认提交人工审核", "综合分最低，适合作为主方案"),
        ("conservative", "保守低风险", "minimize_interference", "保护频率和复用距离敏感任务", "可能占用更多频谱或降低复用效率"),
        ("reuse", "激进复用", "maximize_reuse_efficiency", "频谱紧张但允许工程复核的任务", "复用链路和邻频风险需要重点复核"),
        ("radar", "雷达优先", "radar_priority", "雷达探测窗口必须优先保障", "通信或回传装备可能被降级"),
        ("communication", "通信优先", "communication_continuity", "指挥通信、中继和数据链连续性优先", "雷达/宽带连续窗口可能出现部分满足"),
        ("minimum_change", "最小改动", "minimize_switching", "已有规划只需局部调整", "不一定获得最低干扰或最高频谱效率"),
    ]
    successful = [plan for plan in plans if plan.get("status") == "success"]
    recommended = min(successful, key=lambda item: float(item.get("objective_score") or 0), default=None)
    rows = []
    for key, profile_name, objective, use_case, tradeoff in profiles:
        if objective:
            plan = next((item for item in successful if item.get("objective") == objective), None)
        else:
            plan = recommended
        if not plan:
            continue
        rows.append(
            {
                "profile": key,
                "profile_name": profile_name,
                "run_id": plan.get("run_id"),
                "objective": plan.get("objective"),
                "objective_label": plan.get("label"),
                "use_case": use_case,
                "tradeoff": tradeoff,
                "task_satisfaction_avg": plan.get("task_satisfaction_avg", 0),
                "full_group_count": plan.get("full_group_count", 0),
                "partial_group_count": plan.get("partial_group_count", 0),
                "unsatisfied_group_count": plan.get("unsatisfied_group_count", 0),
                "high_risk_count": plan.get("high_risk_count", 0),
                "used_bandwidth_mhz": plan.get("used_bandwidth_mhz", 0),
                "objective_score": plan.get("objective_score", 0),
                "decision": _decision_row_action(plan),
            }
        )
    return rows


def _decision_row_action(plan: dict) -> str:
    if int(plan.get("unsatisfied_group_count") or 0):
        return "作为备选，需先处理未满足装备组"
    if int(plan.get("high_risk_count") or 0):
        return "可进入复核，重点检查高风险链路"
    if int(plan.get("partial_group_count") or 0):
        return "可执行但需确认部分满足牺牲"
    return "可作为候选主方案"


def _group_sort_key(group: dict, units_by_id: dict[str, dict], objective: str) -> tuple:
    unit = units_by_id.get(group["task_unit_id"], {})
    unit_priority = int(unit.get("priority") or 1)
    group_priority = int(group.get("priority") or 1)
    bandwidth = float(group.get("bandwidth_khz") or 0)
    protection = float(group.get("protection_distance_km") or 0)
    count = int(group.get("count") or 0)
    power = float(group.get("tx_power_w") or 0)
    text = " ".join(
        str(value or "")
        for value in [
            group.get("equipment_type"),
            group.get("assignment_mode"),
            group.get("preferred_band_group"),
            unit.get("unit_type"),
            unit.get("name"),
            unit.get("spectrum_relation"),
        ]
    )
    if objective == "minimize_bandwidth":
        return (bandwidth, -group_priority, -unit_priority)
    if objective == "minimize_interference":
        return (-protection, -power, -group_priority)
    if objective == "priority_equipment":
        return (-group_priority, -unit_priority, -count)
    if objective == "radar_priority":
        return (0 if _text_has(text, ["雷达", "探测", "跟踪"]) else 1, -bandwidth, -group_priority, -unit_priority)
    if objective == "uav_link_priority":
        return (0 if _text_has(text, ["无人机", "地面控制站", "数传", "遥控", "高清视频"]) else 1, -group_priority, -bandwidth, -unit_priority)
    if objective == "communication_continuity":
        return (0 if _text_has(text, ["通信", "电台", "基站", "中继", "数据链", "自组网"]) else 1, -group_priority, -count, -unit_priority)
    if objective == "ew_isolation_priority":
        return (0 if _text_has(text, ["电子对抗", "电子压制", "诱骗干扰", "EW"]) else 1, -power, -protection, -group_priority)
    if objective == "minimize_switching":
        return (str(group.get("preferred_band_group") or ""), -unit_priority, -group_priority, bandwidth)
    if objective == "maximize_reuse_efficiency":
        reusable = 0 if "可复用" in str(unit.get("spectrum_relation") or "") or _text_has(text, ["共享", "手持", "低功率"]) else 1
        return (reusable, bandwidth, protection, -count, -group_priority)
    return (-unit_priority, -float(unit.get("min_satisfaction_ratio") or 0), -group_priority)


def _text_has(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def _ordered_band_candidates(
    group: dict,
    unit: dict,
    rules_by_band: dict[str, list[Segment]],
    avoid_band_groups: set[str] | None = None,
    forced_band_groups: dict[str, str] | None = None,
) -> list[str]:
    avoid_band_groups = avoid_band_groups or set()
    forced = _forced_band_for_group(group, unit, forced_band_groups or {})
    if forced:
        return [forced] if forced in rules_by_band else []
    values = []
    source_values = []
    if group.get("preferred_band_group"):
        source_values.append(group.get("preferred_band_group"))
    if unit.get("preferred_band_groups"):
        source_values.append(unit.get("preferred_band_groups"))
    for raw in source_values:
        for item in str(raw or "").replace("；", ",").replace("，", ",").split(","):
            item = item.strip()
            if item and item not in values:
                values.append(item)
    valid = [band for band in values if band in rules_by_band]
    return [band for band in valid if band not in avoid_band_groups] + [band for band in valid if band in avoid_band_groups]


def _forced_band_for_group(group: dict, unit: dict, forced_band_groups: dict[str, str]) -> str | None:
    for target, band in forced_band_groups.items():
        if _target_matches(str(target), group.get("equipment_group_id", ""), group.get("equipment_type", ""), unit.get("task_unit_id", ""), unit.get("name", ""), unit.get("unit_type", "")):
            return str(band or "").strip() or None
    return None


def _available_rules_for_band(spectrum_rules: list[dict], band: str) -> list[dict]:
    return [rule for rule in spectrum_rules if rule.get("band_group") == band and rule.get("rule_type") == "可用"]


def _band_constraint_reason(group: dict, unit: dict, band_rules: list[dict], band: str) -> str | None:
    if not band_rules:
        return f"{band} 没有可用频段规则"
    compatible = [rule for rule in band_rules if _rule_matches_unit_and_equipment(rule, unit, group)]
    if not compatible:
        return f"{band} 不匹配任务类型或装备类型"
    bandwidth = float(group.get("bandwidth_khz") or 0)
    max_bandwidth = max(float(rule.get("max_bandwidth_khz") or 0) for rule in compatible)
    if bandwidth > max_bandwidth:
        return f"{band} 最大允许带宽 {max_bandwidth:g} kHz，小于装备需求 {bandwidth:g} kHz"
    power = float(group.get("tx_power_w") or 0)
    max_power = max(float(rule.get("max_power_w") or 0) for rule in compatible)
    if power > max_power:
        return f"{band} 最大发射功率 {max_power:g} W，小于装备需求 {power:g} W"
    return None


def _rule_matches_unit_and_equipment(rule: dict, unit: dict, group: dict) -> bool:
    unit_types = _split_csv(rule.get("compatible_unit_types"))
    equipment_types = _split_csv(rule.get("compatible_equipment_types"))
    unit_ok = not unit_types or any(_text_match(item, unit.get("unit_type", ""), unit.get("name", "")) for item in unit_types)
    equipment_ok = not equipment_types or any(_text_match(item, group.get("equipment_type", "")) for item in equipment_types)
    return unit_ok and equipment_ok


def _alternative_resources_for_assignment(group: dict, unit: dict, spectrum_rules: list[dict], assignment: dict) -> list[dict]:
    if not group:
        return []
    rules_by_band = _available_segments_by_band(spectrum_rules)
    candidates = _ordered_band_candidates(group, unit, rules_by_band)
    current_band = assignment.get("band_group")
    alternatives = []
    for band in candidates:
        if band == current_band:
            continue
        reason = _band_constraint_reason(group, unit, _available_rules_for_band(spectrum_rules, band), band)
        if reason:
            alternatives.append({"band_group": band, "status": "不可用", "resource": "", "reason": reason})
            continue
        allocation = _allocate_in_band(group, unit, band, rules_by_band.get(band, []), "task_assurance")
        if allocation:
            ratio = min(1.0, allocation["assigned_channels"] / max(1, int(group.get("required_channels") or 1)))
            alternatives.append(
                {
                    "band_group": band,
                    "status": "可用" if ratio >= 0.999 else "部分可用",
                    "resource": allocation["resource"],
                    "assigned_channels": allocation["assigned_channels"],
                    "satisfaction_ratio": round(ratio, 4),
                    "reason": "可作为重规划备用资源",
                }
            )
        else:
            alternatives.append({"band_group": band, "status": "不可用", "resource": "", "reason": "连续窗口或离散信道不足"})
        if len(alternatives) >= 4:
            break
    return alternatives


def _assignment_explanation_chain(group: dict, unit: dict, spectrum_rules: list[dict], assignment: dict, alternatives: list[dict]) -> dict:
    if not group:
        return {}
    selected_band = assignment.get("band_group") or ""
    requested_channels = max(1, int(group.get("required_channels") or assignment.get("requested_channels") or 1))
    assigned_channels = int(assignment.get("assigned_channels") or 0)
    missing_channels = max(0, requested_channels - assigned_channels)
    bandwidth_mhz = float(group.get("bandwidth_khz") or 0) / 1000
    guard_mhz = max(float(group.get("guard_band_khz") or 0), float(group.get("min_spacing_khz") or 0)) / 1000
    blocker_rules = [
        rule
        for rule in spectrum_rules
        if rule.get("band_group") == selected_band and rule.get("rule_type") in {"禁用", "保护"}
    ][:4]
    why_selected = []
    if selected_band:
        why_selected.append(f"装备首选/任务候选频段包含 {selected_band}")
        why_selected.append(f"{selected_band} 通过任务类型、装备类型、带宽和功率规则校验")
    if assignment.get("status") == "完全满足":
        why_selected.append("候选窗口可覆盖所需信道数，形成完整指配")
    elif assigned_channels > 0:
        why_selected.append("候选窗口不足以全量覆盖，但允许部分满足，因此保留为降级方案")
    else:
        why_selected.append("当前候选频段无法形成有效指配")
    why_rejected = [
        {
            "band_group": item.get("band_group"),
            "status": item.get("status"),
            "reason": item.get("reason"),
        }
        for item in alternatives
        if item.get("status") != "可用"
    ][:4]
    if not why_rejected and alternatives:
        why_rejected = [{"band_group": item.get("band_group"), "status": item.get("status"), "reason": "未被选中：当前方案优先保留首选频段或目标排序更靠前"} for item in alternatives[:3]]
    required_extra = {
        "missing_channels": missing_channels,
        "estimated_extra_width_mhz": round(missing_channels * max(bandwidth_mhz + guard_mhz, bandwidth_mhz), 3),
        "suggestion": "无需增加资源" if missing_channels == 0 else "增加连续窗口/离散信道，或降低该装备组信道数、带宽、保护间隔后重算",
    }
    return {
        "why_selected": why_selected,
        "why_rejected": why_rejected,
        "blocking_rules": [
            {
                "rule_id": rule.get("rule_id"),
                "rule_type": rule.get("rule_type"),
                "start_mhz": rule.get("start_mhz"),
                "end_mhz": rule.get("end_mhz"),
                "reason": rule.get("reason"),
                "severity": rule.get("severity"),
            }
            for rule in blocker_rules
        ],
        "required_extra_resource": required_extra,
        "audit_hint": _assignment_audit_hint(assignment, required_extra),
    }


def _assignment_audit_hint(assignment: dict, required_extra: dict) -> str:
    if assignment.get("required_full") and assignment.get("status") != "完全满足":
        return "必须完全满足对象未达标，应优先人工处置"
    if assignment.get("status") == "未满足":
        return "未满足对象，需要扩展频段或调整装备需求"
    if assignment.get("status") == "部分满足":
        return f"部分满足对象，预计还需 {required_extra.get('estimated_extra_width_mhz', 0)} MHz 等效资源"
    if assignment.get("risk_level") == "高":
        return "已满足但风险等级高，应复核保护距离和保护频率"
    return "可进入常规审核"


def _split_csv(value: str | None) -> list[str]:
    return [item.strip() for item in str(value or "").replace("；", ",").replace("，", ",").split(",") if item.strip()]


def _text_match(needle: str, *values: str) -> bool:
    return any(needle == value or needle in value or value in needle for value in values if value)


def _segments_after_consumption(segments: list[Segment], consumed: list[Segment]) -> list[Segment]:
    pieces = list(segments)
    for used in consumed:
        next_pieces: list[Segment] = []
        for piece in pieces:
            next_pieces.extend(_subtract_segment(piece, used))
        pieces = next_pieces
    return pieces


def _subtract_segment(segment: Segment, blocker: Segment) -> list[Segment]:
    if blocker.end <= segment.start or blocker.start >= segment.end:
        return [segment]
    pieces = []
    if blocker.start > segment.start:
        pieces.append(Segment(segment.start, min(blocker.start, segment.end)))
    if blocker.end < segment.end:
        pieces.append(Segment(max(blocker.end, segment.start), segment.end))
    return [piece for piece in pieces if piece.width_mhz > 0.0001]


def _parse_resource_segments(resource: str) -> list[Segment]:
    segments: list[Segment] = []
    if not resource:
        return segments
    for part in resource.replace(",", ";").split(";"):
        part = part.strip().replace("MHz", "").strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            try:
                segments.append(Segment(float(left.strip()), float(right.strip())))
            except ValueError:
                continue
        elif "/" in part:
            for freq in part.split("/"):
                try:
                    value = float(freq.strip())
                    segments.append(Segment(value - 0.0005, value + 0.0005))
                except ValueError:
                    continue
        else:
            try:
                value = float(part)
                segments.append(Segment(value - 0.0005, value + 0.0005))
            except ValueError:
                continue
    return segments


def _distribution(values: list[str], levels: list[str]) -> list[dict]:
    counter = Counter(values)
    return [{"label": level, "count": counter.get(level, 0)} for level in levels]


def _build_spectrum_timeline(spectrum_rules: list[dict], assignments: list[dict]) -> list[dict]:
    rows = []
    available_rules = [rule for rule in spectrum_rules if rule.get("rule_type") == "可用"]
    for rule in sorted(available_rules, key=lambda item: (item.get("band_group") or "", float(item.get("start_mhz") or 0))):
        band = rule["band_group"]
        band_start = float(rule.get("start_mhz") or 0)
        band_end = float(rule.get("end_mhz") or 0)
        width = max(0.0001, band_end - band_start)
        markers = []
        for other in spectrum_rules:
            if other.get("band_group") != band or other.get("rule_type") not in {"禁用", "保护"}:
                continue
            markers.append(_timeline_marker(other["rule_type"], other.get("rule_id", ""), other.get("reason", ""), band_start, width, float(other.get("start_mhz") or 0), float(other.get("end_mhz") or 0), other.get("severity", "中")))
        for assignment in assignments:
            if assignment.get("band_group") != band:
                continue
            for idx, segment in enumerate(_parse_resource_segments(assignment.get("assigned_resource") or "")):
                markers.append(
                    _timeline_marker(
                        "指配",
                        f"{assignment.get('equipment_group_id')}-{idx}",
                        f"{assignment.get('task_unit_id')} / {assignment.get('equipment_group_id')} / {assignment.get('status')}",
                        band_start,
                        width,
                        segment.start,
                        segment.end,
                        assignment.get("risk_level", "低"),
                        assignment.get("task_unit_id"),
                        assignment.get("equipment_group_id"),
                    )
                )
        rows.append(
            {
                "band_group": band,
                "start_mhz": band_start,
                "end_mhz": band_end,
                "available_width_mhz": round(width, 3),
                "markers": sorted(markers, key=lambda item: (item["start_pct"], item["end_pct"], item["kind"])),
            }
        )
    return rows


def _timeline_marker(kind: str, marker_id: str, label: str, base: float, width: float, start: float, end: float, severity: str, task_unit_id: str | None = None, equipment_group_id: str | None = None) -> dict:
    left = max(0.0, min(100.0, (start - base) / width * 100))
    right = max(0.0, min(100.0, (end - base) / width * 100))
    if right < left:
        left, right = right, left
    return {
        "kind": kind,
        "id": marker_id,
        "label": label,
        "start_mhz": round(start, 6),
        "end_mhz": round(end, 6),
        "start_pct": round(left, 3),
        "end_pct": round(max(right, left + 0.35), 3),
        "severity": severity,
        "task_unit_id": task_unit_id,
        "equipment_group_id": equipment_group_id,
    }


def _diagnose_task_plan(task_units: list[dict], equipment_groups: list[dict], spectrum_rules: list[dict], assignments: list[dict], risk_items: list[dict]) -> list[dict]:
    diagnostics = []
    groups = {item["equipment_group_id"]: item for item in equipment_groups}
    for assignment in assignments:
        if assignment.get("status") == "完全满足":
            continue
        group = groups.get(assignment["equipment_group_id"], {})
        category = "候选频段不足"
        if "连续" in str(assignment.get("assignment_mode")):
            category = "连续带宽不足"
        if "雷达" in str(group.get("equipment_type", "")):
            category = "雷达宽带窗口不足"
        diagnostics.append(
            {
                "category": category,
                "severity": assignment.get("risk_level", "中"),
                "target": assignment["equipment_group_id"],
                "reason": assignment.get("reason", ""),
                "suggestion": _suggestion_for_assignment(assignment, group),
                "estimated_gain_pct": _estimated_gain(assignment),
            }
        )
    for risk in risk_items:
        if risk.get("risk_type") == "保护频率靠近":
            diagnostics.append(
                {
                    "category": "保护频率避让",
                    "severity": risk.get("severity", "中"),
                    "target": risk.get("equipment_group_a") or risk.get("task_unit_a") or "",
                    "reason": risk.get("reason", ""),
                    "suggestion": "增加保护带、调整连续窗口起点，或把该装备组切换到备用频段池。",
                    "estimated_gain_pct": 5,
                }
            )
        elif risk.get("risk_type") == "跨任务复用距离不足":
            diagnostics.append(
                {
                    "category": "复用距离不足",
                    "severity": risk.get("severity", "中"),
                    "target": f"{risk.get('equipment_group_a')} / {risk.get('equipment_group_b')}",
                    "reason": risk.get("reason", ""),
                    "suggestion": "优先给两个任务单元分离频段，或降低其中一个任务单元复用等级。",
                    "estimated_gain_pct": 3,
                }
            )
    if not diagnostics:
        diagnostics.append(
            {
                "category": "方案可执行",
                "severity": "低",
                "target": "全局",
                "reason": "当前约束下未发现未满足装备组或高等级风险。",
                "suggestion": "可进入人工复核和报告归档。",
                "estimated_gain_pct": 0,
            }
        )
    return diagnostics[:12]


def _suggestion_for_assignment(assignment: dict, group: dict) -> str:
    if assignment.get("status") == "未满足":
        return "增加备用频段池，或降低该装备组所需信道数/带宽后重算。"
    if "雷达" in str(group.get("equipment_type", "")):
        return "增加连续雷达窗口、允许跨频段分段保障，或降低单通道带宽。"
    if "连续" in str(assignment.get("assignment_mode", "")):
        return "优先扩大连续可用窗口，减少保护/禁用频率对可用段的切分。"
    return "减少所需信道数、允许共享信道，或引入备用频段池。"


def _estimated_gain(assignment: dict) -> float:
    return round(max(0.0, 1 - float(assignment.get("satisfaction_ratio") or 0)) * 100, 1)


def _decision_recommendations(assignments: list[dict], risk_items: list[dict]) -> list[str]:
    recommendations = []
    partial = [item for item in assignments if item.get("status") == "部分满足"]
    unsatisfied = [item for item in assignments if item.get("status") == "未满足"]
    if partial:
        recommendations.append(f"优先复核 {len(partial)} 个部分满足装备组，确认是否接受降级保障。")
    if unsatisfied:
        recommendations.append(f"{len(unsatisfied)} 个装备组未满足，建议增加备用频段或降低带宽/信道需求。")
    if any(item.get("risk_type") == "保护频率靠近" for item in risk_items):
        recommendations.append("存在保护频率靠近风险，建议扩大保护带后再次重算。")
    if any(item.get("risk_type") == "跨任务复用距离不足" for item in risk_items):
        recommendations.append("存在跨任务复用距离不足，建议对相邻任务单元分离频段池。")
    if not recommendations:
        recommendations.append("当前方案风险较低，可作为人工审核基准版本。")
    return recommendations


def _report_conclusion(summary: dict) -> str:
    avg = summary.get("task_satisfaction_avg", 0)
    partial = int(summary.get("partial_group_count") or 0)
    unsatisfied = int(summary.get("unsatisfied_group_count") or 0)
    high = int(summary.get("high_risk_count") or 0)
    if unsatisfied:
        return f"当前方案平均保障率 {avg}%，存在 {unsatisfied} 个未满足装备组，应先处理候选频段不足问题。"
    if partial:
        return f"当前方案平均保障率 {avg}%，存在 {partial} 个部分满足装备组，可作为允许降级保障的备选方案。"
    if high:
        return f"当前方案已满足装备组需求，但存在 {high} 个高风险项，需人工复核保护距离和保护频率。"
    return f"当前方案平均保障率 {avg}%，未发现明显高风险项，可进入人工审核。"


def _audit_checklist(summary: dict, assignments: list[dict]) -> list[str]:
    items = []
    if int(summary.get("unsatisfied_group_count") or 0):
        items.append(f"优先处置 {summary.get('unsatisfied_group_count')} 个未满足装备组，确认是否增加频段或降低需求。")
    if int(summary.get("partial_group_count") or 0):
        items.append(f"复核 {summary.get('partial_group_count')} 个部分满足装备组，确认降级保障是否可接受。")
    if int(summary.get("high_risk_count") or 0):
        items.append(f"复核 {summary.get('high_risk_count')} 项高风险，重点检查保护频率和复用距离。")
    required_failed = [item for item in assignments if item.get("required_full") and item.get("status") != "完全满足"]
    if required_failed:
        items.append(f"必须完全满足对象仍有 {len(required_failed)} 个未达标，应阻止直接下发。")
    bottleneck = summary.get("bottleneck_analysis", {})
    top_band = (bottleneck.get("band_bottlenecks") or [{}])[0]
    if top_band.get("pressure_score", 0):
        items.append(f"频段池 {top_band.get('band_group')} 压力最高，建议先检查阻塞窗口和竞争装备组。")
    if not items:
        items.append("当前方案未发现阻塞性问题，可进入常规人工审核。")
    return items


def _replan_explanation(applied: dict, changes: dict, summary: dict) -> str:
    parts = [
        f"已按“{_objective_label(changes['objective'])}”重新规划。",
        f"新增可用频段 {applied.get('available_range_count', 0)} 条，新增禁用频段 {applied['forbidden_range_count']} 条，调整优先级 {applied['priority_update_count']} 项，调整保障率 {applied['satisfaction_update_count']} 项。",
    ]
    if changes["locked_equipment_group_ids"]:
        parts.append(f"锁定装备组：{', '.join(changes['locked_equipment_group_ids'])}。")
    if changes["avoid_band_groups"]:
        parts.append(f"避用频段池：{', '.join(changes['avoid_band_groups'])}。")
    if changes.get("forced_band_groups"):
        forced_text = "、".join(f"{target}->{band}" for target, band in changes["forced_band_groups"].items())
        parts.append(f"强制频段：{forced_text}。")
    if changes.get("required_full_targets"):
        parts.append(f"必须完全满足对象：{', '.join(changes['required_full_targets'])}。")
    parts.append(f"新方案平均保障率 {summary.get('task_satisfaction_avg', 0)}%，部分满足 {summary.get('partial_group_count', 0)} 个，未满足 {summary.get('unsatisfied_group_count', 0)} 个。")
    recommendations = summary.get("decision_recommendations") or []
    if recommendations:
        parts.append("建议：" + recommendations[0])
    return "".join(parts)


def _objective_label(objective: str) -> str:
    return next((item["label"] for item in TASK_OBJECTIVES if item["objective"] == objective), objective)


def _objective_from_message(message: str) -> str | None:
    if any(word in message for word in ["干扰最低", "降低干扰", "少干扰"]):
        return "minimize_interference"
    if any(word in message for word in ["占用带宽最小", "少占带宽", "减少频谱占用", "减少带宽"]):
        return "minimize_bandwidth"
    if any(word in message for word in ["雷达优先", "优先保障雷达", "探测优先", "低空探测"]):
        return "radar_priority"
    if any(word in message for word in ["无人机优先", "优先保障无人机", "数传优先", "遥控链路优先"]):
        return "uav_link_priority"
    if any(word in message for word in ["通信连续", "连续性优先", "中继优先", "数据链连续", "通信保障"]):
        return "communication_continuity"
    if any(word in message for word in ["电子对抗优先", "电子压制优先", "干扰设备隔离", "对抗隔离"]):
        return "ew_isolation_priority"
    if any(word in message for word in ["最少切换", "少切换", "保持原频", "沿用首选频段"]):
        return "minimize_switching"
    if any(word in message for word in ["最大复用", "复用效率", "提高复用", "频率复用"]):
        return "maximize_reuse_efficiency"
    if any(word in message for word in ["高优先级", "优先级装备"]):
        return "priority_equipment"
    if any(word in message for word in ["任务保障", "保障优先"]):
        return "task_assurance"
    return None


def _available_ranges_from_message(message: str, spectrum_rules: list[dict]) -> list[dict]:
    ranges = []
    pattern = re.compile(r"(?:新增可用|补充可用|增加可用|启用|开放)\s*([A-Za-z][A-Za-z0-9-]*)?\s*(\d+(?:\.\d+)?)\s*(?:-|~|至|到)\s*(\d+(?:\.\d+)?)\s*(?:MHz|mhz)?")
    for match in pattern.finditer(message):
        raw_band, start, end = match.groups()
        start_mhz = float(start)
        end_mhz = float(end)
        ranges.append(
            {
                "band_group": raw_band if raw_band and "-" in raw_band else _infer_band_group(start_mhz, end_mhz, spectrum_rules),
                "start_mhz": min(start_mhz, end_mhz),
                "end_mhz": max(start_mhz, end_mhz),
                "reason": "用户聊天补充可用频段",
            }
        )
    return ranges


def _forbidden_ranges_from_message(message: str, spectrum_rules: list[dict]) -> list[dict]:
    ranges = []
    pattern = re.compile(r"(?:禁用|避开|禁止)\s*([A-Za-z][A-Za-z0-9-]*)?\s*(\d+(?:\.\d+)?)\s*(?:-|~|至|到)\s*(\d+(?:\.\d+)?)\s*(?:MHz|mhz)?")
    for match in pattern.finditer(message):
        raw_band, start, end = match.groups()
        start_mhz = float(start)
        end_mhz = float(end)
        ranges.append(
            {
                "band_group": raw_band if raw_band and "-" in raw_band else _infer_band_group(start_mhz, end_mhz, spectrum_rules),
                "start_mhz": min(start_mhz, end_mhz),
                "end_mhz": max(start_mhz, end_mhz),
                "reason": "用户聊天追加禁用",
            }
        )
    return ranges


def _priority_updates_from_message(message: str, task_units: list[dict], equipment_groups: list[dict]) -> list[dict]:
    updates = []
    if "优先级" not in message and "优先保障" not in message:
        return updates
    targets = [(item["task_unit_id"], item.get("name", ""), item.get("unit_type", ""), item.get("priority", 1)) for item in task_units]
    targets.extend((item["equipment_group_id"], item.get("equipment_type", ""), "", item.get("priority", 1)) for item in equipment_groups)
    explicit = re.search(r"(?:优先级|设为)\s*(\d+)", message)
    for target_id, name, unit_type, current in targets:
        if target_id in message or (name and name in message) or (unit_type and unit_type in message):
            priority = int(explicit.group(1)) if explicit else min(10, int(current or 1) + 1)
            updates.append({"target": target_id, "priority": priority})
    return updates


def _satisfaction_updates_from_message(message: str, task_units: list[dict]) -> list[dict]:
    updates = []
    if "保障率" not in message and "部分满足" not in message:
        return updates
    ratio_match = re.search(r"(\d{1,3})\s*%", message)
    ratio = float(ratio_match.group(1)) / 100 if ratio_match else 0.7
    for unit in task_units:
        if unit["task_unit_id"] in message or unit.get("name", "") in message or unit.get("unit_type", "") in message:
            updates.append({"task_unit_id": unit["task_unit_id"], "min_satisfaction_ratio": ratio})
    return updates


def _locked_groups_from_message(message: str, equipment_groups: list[dict]) -> list[str]:
    if "锁定" not in message and "保持" not in message:
        return []
    values = []
    for group in equipment_groups:
        if group["equipment_group_id"] in message or group.get("equipment_type", "") in message:
            values.append(group["equipment_group_id"])
    return values


def _group_ids_for_locked_units(unit_ids: list[str], task_units: list[dict], equipment_groups: list[dict]) -> list[str]:
    if not unit_ids:
        return []
    matched_units = {
        unit["task_unit_id"]
        for unit in task_units
        if any(_target_matches(target, unit.get("task_unit_id", ""), unit.get("name", ""), unit.get("unit_type", "")) for target in unit_ids)
    }
    return [group["equipment_group_id"] for group in equipment_groups if group.get("task_unit_id") in matched_units]


def _avoid_bands_from_message(message: str, spectrum_rules: list[dict]) -> list[str]:
    if not any(word in message for word in ["少用", "尽量少用", "避免使用"]):
        return []
    bands = sorted({rule.get("band_group") for rule in spectrum_rules if rule.get("band_group")})
    return [band for band in bands if band and band in message]


def _forced_bands_from_message(message: str, spectrum_rules: list[dict], task_units: list[dict], equipment_groups: list[dict]) -> dict[str, str]:
    if not any(word in message for word in ["必须用", "指定", "强制"]):
        return {}
    bands = sorted({rule.get("band_group") for rule in spectrum_rules if rule.get("band_group")}, key=len, reverse=True)
    selected_band = next((band for band in bands if band and band in message), None)
    if not selected_band:
        return {}
    targets = []
    for unit in task_units:
        if unit.get("task_unit_id") in message or unit.get("name", "") in message or unit.get("unit_type", "") in message:
            targets.append(unit["task_unit_id"])
    for group in equipment_groups:
        if group.get("equipment_group_id") in message or group.get("equipment_type", "") in message:
            targets.append(group["equipment_group_id"])
    return {target: selected_band for target in _unique_keep_order(targets)}


def _required_full_targets_from_message(message: str, task_units: list[dict], equipment_groups: list[dict]) -> list[str]:
    if not any(word in message for word in ["必须完全满足", "不得部分满足", "不能降级", "不允许降级"]):
        return []
    targets = []
    for unit in task_units:
        if unit.get("task_unit_id") in message or unit.get("name", "") in message or unit.get("unit_type", "") in message:
            targets.append(unit["task_unit_id"])
    for group in equipment_groups:
        if group.get("equipment_group_id") in message or group.get("equipment_type", "") in message:
            targets.append(group["equipment_group_id"])
    return targets


def _infer_band_group(start_mhz: float, end_mhz: float, spectrum_rules: list[dict]) -> str | None:
    for rule in spectrum_rules:
        if rule.get("rule_type") != "可用":
            continue
        if float(rule.get("start_mhz") or 0) <= start_mhz and end_mhz <= float(rule.get("end_mhz") or 0):
            return rule.get("band_group")
    return None


def _available_rule_defaults_for_band(spectrum_rules: list[dict], band_group: str) -> dict:
    rules = [rule for rule in spectrum_rules if rule.get("band_group") == band_group and rule.get("rule_type") == "可用"]
    if not rules:
        return {
            "spectrum_relation": "可复用",
            "channel_step_khz": 25,
            "max_bandwidth_khz": 25,
            "max_power_w": 1,
            "guard_band_khz": 0,
            "compatible_unit_types": "",
            "compatible_equipment_types": "",
        }
    return {
        "spectrum_relation": rules[0].get("spectrum_relation") or "可复用",
        "channel_step_khz": min(float(rule.get("channel_step_khz") or 25) for rule in rules),
        "max_bandwidth_khz": max(float(rule.get("max_bandwidth_khz") or 25) for rule in rules),
        "max_power_w": max(float(rule.get("max_power_w") or 1) for rule in rules),
        "guard_band_khz": max(float(rule.get("guard_band_khz") or 0) for rule in rules),
        "compatible_unit_types": ",".join(_unique_keep_order([str(rule.get("compatible_unit_types") or "") for rule in rules if rule.get("compatible_unit_types")])),
        "compatible_equipment_types": ",".join(_unique_keep_order([str(rule.get("compatible_equipment_types") or "") for rule in rules if rule.get("compatible_equipment_types")])),
    }


def _target_matches(target: str, *candidates: str | None) -> bool:
    if not target:
        return False
    return any(target == str(item or "") or target in str(item or "") for item in candidates)


def _refresh_raw(row) -> str:
    return json.dumps(row.model_dump(exclude={"id", "project_id"}), ensure_ascii=False, default=str)


def _unique_keep_order(values: list[str]) -> list[str]:
    result = []
    for item in values:
        if item and item not in result:
            result.append(item)
    return result


def _unique_frequency_ranges(ranges: list[dict]) -> list[dict]:
    result = []
    seen = set()
    for item in ranges:
        start = round(float(item.get("start_mhz") or 0), 6)
        end = round(float(item.get("end_mhz") or 0), 6)
        if end <= start:
            continue
        key = (item.get("band_group") or "", start, end, item.get("reason") or "")
        if key in seen:
            continue
        seen.add(key)
        result.append({**item, "start_mhz": start, "end_mhz": end})
    return result


def _partial_reason(group: dict, assigned: int, requested: int) -> str:
    if assigned == 0:
        return "禁用/保护频率或连续带宽约束导致无法分配"
    if "雷达" in str(group.get("equipment_type")):
        return "雷达宽带连续频段需求较大，当前频段池只能部分满足"
    if "连续" in str(group.get("assignment_mode")):
        return "连续可用带宽不足，只能分配部分链路"
    return f"可用信道不足，需求 {requested} 个，当前可分配 {assigned} 个"


def _decision_note(group: dict, band: str, objective: str, status: str) -> str:
    objective_text = next((item["label"] for item in TASK_OBJECTIVES if item["objective"] == objective), objective)
    if status == "完全满足":
        return f"按“{objective_text}”目标在 {band} 中完成指配"
    return f"按“{objective_text}”目标优先保障高价值链路，剩余需求建议通过备用频段或降低带宽解决"


def _status_from_ratio(ratio: float, threshold: float) -> str:
    if ratio >= max(0.0, min(1.0, float(threshold or 1.0))):
        return "完全满足"
    if ratio > 0:
        return "部分满足"
    return "未满足"


def _fmt_segment(segment: Segment) -> str:
    return f"{segment.start:.6f}-{segment.end:.6f} MHz"


def _ceil_to_step(value: float, step: float) -> float:
    return math.ceil(value / step - 1e-9) * step


def _overlaps(a: Segment, b: Segment) -> bool:
    return a.start < b.end and b.start < a.end


def _task_unit(task_unit_id: str, name: str, unit_type: str, lat: float, lon: float, radius: float, priority: int, relation: str, bands: str, ratio: float) -> dict:
    data = {
        "task_unit_id": task_unit_id,
        "name": name,
        "unit_type": unit_type,
        "area_center_lat": lat,
        "area_center_lon": lon,
        "area_radius_km": radius,
        "priority": priority,
        "spectrum_relation": relation,
        "preferred_band_groups": bands,
        "min_satisfaction_ratio": ratio,
    }
    return {**data, "raw_json": json.dumps(data, ensure_ascii=False)}


def _group(
    equipment_group_id: str,
    task_unit_id: str,
    equipment_type: str,
    count: int,
    tx_rx_role: str,
    mobility: str,
    bandwidth_khz: float,
    tx_power_w: float,
    antenna_gain_dbi: float,
    antenna_height_m: float,
    receiver_sensitivity_dbm: float,
    modulation: str,
    duplex_mode: str,
    required_channels: int,
    assignment_mode: str,
    preferred_band_group: str,
    priority: int,
    protection_distance_km: float,
    min_spacing_khz: float,
    guard_band_khz: float,
) -> dict:
    data = {
        "equipment_group_id": equipment_group_id,
        "task_unit_id": task_unit_id,
        "equipment_type": equipment_type,
        "count": count,
        "tx_rx_role": tx_rx_role,
        "mobility": mobility,
        "bandwidth_khz": bandwidth_khz,
        "tx_power_w": tx_power_w,
        "antenna_gain_dbi": antenna_gain_dbi,
        "antenna_height_m": antenna_height_m,
        "receiver_sensitivity_dbm": receiver_sensitivity_dbm,
        "modulation": modulation,
        "duplex_mode": duplex_mode,
        "required_channels": required_channels,
        "assignment_mode": assignment_mode,
        "preferred_band_group": preferred_band_group,
        "priority": priority,
        "protection_distance_km": protection_distance_km,
        "min_spacing_khz": min_spacing_khz,
        "guard_band_khz": guard_band_khz,
    }
    return {**data, "raw_json": json.dumps(data, ensure_ascii=False)}


def _rule(
    rule_id: str,
    rule_type: str,
    band_group: str,
    relation: str,
    start: float,
    end: float,
    step: float,
    max_bandwidth: float,
    max_power: float,
    guard: float,
    unit_types: str,
    equipment_types: str,
    reason: str,
    source: str,
    severity: str,
) -> dict:
    data = {
        "rule_id": rule_id,
        "rule_type": rule_type,
        "band_group": band_group,
        "spectrum_relation": relation,
        "start_mhz": start,
        "end_mhz": end,
        "channel_step_khz": step,
        "max_bandwidth_khz": max_bandwidth,
        "max_power_w": max_power,
        "guard_band_khz": guard,
        "compatible_unit_types": unit_types,
        "compatible_equipment_types": equipment_types,
        "reason": reason,
        "source": source,
        "severity": severity,
    }
    return {**data, "raw_json": json.dumps(data, ensure_ascii=False)}


def _touch_project(session: Session, project_id: int, status: str) -> None:
    project = session.get(Project, project_id)
    if not project:
        return
    project.status = status

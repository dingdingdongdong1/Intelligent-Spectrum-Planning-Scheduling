from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from ..models import AuditLog, PlanningRun, PlanningSnapshot, Project
from .equipment_planning import task_assignments_for_run, task_risks_for_run


MANIFEST_SCHEMA = "spectrum-planning-trust-manifest/v1"
ALGORITHM_VERSION = "deterministic-spectrum-planner/1.0"


def build_trust_manifest(session: Session, project_id: int, run_id: int) -> dict[str, Any]:
    project = session.get(Project, project_id)
    run = session.get(PlanningRun, run_id)
    if project is None or run is None or run.project_id != project_id or run.status != "success":
        raise ValueError("规划版本不存在或尚未成功")

    snapshot = session.exec(
        select(PlanningSnapshot).where(PlanningSnapshot.project_id == project_id, PlanningSnapshot.run_id == run_id)
    ).first()
    summary = _json_value(run.summary_json, {})
    input_payload = _json_value(snapshot.input_json, {}) if snapshot else {}
    assignments = [_artifact_row(item) for item in task_assignments_for_run(session, project_id, run_id)]
    risks = [_artifact_row(item) for item in task_risks_for_run(session, project_id, run_id)]
    assignments.sort(key=lambda item: (str(item.get("task_unit_id", "")), str(item.get("equipment_group_id", ""))))
    risks.sort(
        key=lambda item: (
            str(item.get("risk_type", "")),
            str(item.get("equipment_group_a", "")),
            str(item.get("equipment_group_b", "")),
            float(item.get("score") or 0),
        )
    )

    hashes = {
        "input_sha256": _sha256(input_payload) if snapshot else None,
        "summary_sha256": _sha256(summary),
        "assignments_sha256": _sha256(assignments),
        "risks_sha256": _sha256(risks),
    }
    hashes["output_sha256"] = _sha256(
        {"summary": hashes["summary_sha256"], "assignments": hashes["assignments_sha256"], "risks": hashes["risks_sha256"]}
    )
    hashes["artifact_sha256"] = _sha256({"input": hashes["input_sha256"], "output": hashes["output_sha256"]})

    logs = session.exec(select(AuditLog).where(AuditLog.project_id == project_id).order_by(AuditLog.id)).all()
    audit_chain = _audit_hash_chain(logs)
    chain_root = audit_chain[-1]["chain_sha256"] if audit_chain else _sha256([])
    verification_checks = [
        {"name": "输入快照", "passed": snapshot is not None, "evidence": "已保存完整输入快照" if snapshot else "该历史版本没有输入快照"},
        {"name": "规划输出", "passed": bool(assignments), "evidence": f"{len(assignments)} 条装备指配、{len(risks)} 条风险记录"},
        {"name": "审计链", "passed": bool(audit_chain), "evidence": f"{len(audit_chain)} 条日志，链根 {chain_root[:16]}..."},
        {"name": "确定性配置", "passed": True, "evidence": ALGORITHM_VERSION},
    ]

    return {
        "schema": MANIFEST_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": {"project_id": project_id, "name": project.name},
        "run": {
            "run_id": run_id,
            "objective": run.objective,
            "status": run.status,
            "created_at": run.created_at.isoformat(),
            "lifecycle_status": snapshot.lifecycle_status if snapshot else "历史（无快照）",
            "adopted": bool(snapshot.adopted) if snapshot else False,
            "parent_run_id": snapshot.parent_run_id if snapshot else None,
            "rollback_source_run_id": snapshot.rollback_source_run_id if snapshot else None,
        },
        "reproducibility": {
            "deterministic": True,
            "algorithm_version": ALGORITHM_VERSION,
            "requested_objective": summary.get("requested_objective") or run.objective,
            "effective_objective": summary.get("effective_objective") or run.objective,
            "strategy_profile": summary.get("strategy_profile") or "balanced",
            "constraint_weights": summary.get("constraint_weights") or {},
            "input_snapshot_available": snapshot is not None,
        },
        "integrity": {
            **hashes,
            "audit_chain_root_sha256": chain_root,
            "audit_event_count": len(audit_chain),
        },
        "verification": {
            "status": "passed" if all(item["passed"] for item in verification_checks) else "attention",
            "checks": verification_checks,
        },
        "audit_chain": audit_chain,
    }


def verify_trust_root(manifest: dict[str, Any], expected_root: str | None = None) -> dict[str, Any]:
    actual = str((manifest.get("integrity") or {}).get("artifact_sha256") or "")
    expected = str(expected_root or actual).strip().lower()
    return {
        "verified": bool(actual) and actual.lower() == expected,
        "expected_artifact_sha256": expected,
        "actual_artifact_sha256": actual,
        "manifest": manifest,
    }


def _artifact_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in {"id", "project_id", "run_id"}}


def _audit_hash_chain(logs: list[AuditLog]) -> list[dict[str, Any]]:
    previous = "0" * 64
    chain = []
    for log in logs:
        event = {
            "id": log.id,
            "run_id": log.run_id,
            "actor": log.actor,
            "action": log.action,
            "detail": _json_value(log.detail, log.detail),
            "created_at": log.created_at.isoformat(),
        }
        event_hash = _sha256(event)
        chain_hash = _sha256({"previous": previous, "event": event_hash})
        chain.append(
            {
                "audit_id": log.id,
                "run_id": log.run_id,
                "actor": log.actor,
                "action": log.action,
                "created_at": log.created_at.isoformat(),
                "event_sha256": event_hash,
                "previous_chain_sha256": previous,
                "chain_sha256": chain_hash,
            }
        )
        previous = chain_hash
    return chain


def _json_value(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (json.JSONDecodeError, TypeError):
        return fallback


def _sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

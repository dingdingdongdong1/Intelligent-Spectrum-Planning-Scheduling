from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.database import get_session
from backend.app.main import app
from backend.app.models import AuditLog
from backend.app.services.task_intent import parse_task_intent


def test_parse_task_intent_builds_confirmable_replan_payload() -> None:
    result = parse_task_intent(
        "抗扰保通优先，避开 2200-2210 MHz，释放 2300-2310 MHz，"
        "锁定 TU-CMD 和 EG-CMD-VEH；EG-CMD-VEH 必须完全满足，"
        "EG-CMD-VEH 优先级调整为 10，不允许降级"
    )

    payload = result["deterministic_payload"]
    assert result["objective"] == "communication_continuity"
    assert result["requires_confirmation"] is True
    assert payload["forbidden_ranges"][0]["start_mhz"] == 2200
    assert payload["available_ranges"][0]["end_mhz"] == 2310
    assert payload["locked_task_unit_ids"] == ["TU-CMD"]
    assert payload["locked_equipment_group_ids"] == ["EG-CMD-VEH"]
    assert payload["required_full_targets"] == ["EG-CMD-VEH"]
    assert payload["priority_updates"] == [{"target": "EG-CMD-VEH", "priority": 10}]
    assert payload["allow_low_priority_degrade"] is False
    assert set(payload["constraint_weights"]) == {"task", "risk", "spectrum", "priority", "switching", "reuse"}


def test_task_intent_api_audits_sanitized_interpretation() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    try:
        project_id = client.post("/api/projects", json={"name": "Intent Test"}).json()["id"]
        response = client.post(
            f"/api/projects/{project_id}/task-intent",
            json={"message": "风险最低，避开 410-412 MHz，锁定 TU-CMD"},
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["objective"] == "minimize_interference"
        assert result["explanation_source"] in {"deterministic", "deterministic_fallback", "llm_enhanced"}

        with Session(engine) as session:
            audit = session.exec(select(AuditLog).where(AuditLog.action == "task_intent_interpreted")).one()
            detail = json.loads(audit.detail)
            assert detail["objective"] == "minimize_interference"
            assert "message" not in detail
    finally:
        app.dependency_overrides.clear()

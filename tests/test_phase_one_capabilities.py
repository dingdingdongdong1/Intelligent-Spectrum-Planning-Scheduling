from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


def test_phase_one_capability_manifest_is_complete() -> None:
    client = TestClient(app)
    response = client.get("/api/phase-one-capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    capability_ids = {item["id"] for item in data["capabilities"]}
    assert {
        "task_unit_management",
        "equipment_group_management",
        "spectrum_rule_management",
        "spectrum_resource_management",
        "automatic_planning",
        "interference_risk_assessment",
        "visual_overview",
        "dynamic_replanning",
        "multi_plan_comparison",
        "intelligent_decision_assistance",
        "report_export",
        "trust_verification",
    } <= capability_ids
    assert all(item["status"] == "ready" for item in data["capabilities"])
    assert all(item["endpoints"] for item in data["capabilities"])

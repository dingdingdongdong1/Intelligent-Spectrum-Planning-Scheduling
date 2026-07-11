from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from backend.app.database import get_session
from backend.app.main import app
from backend.app.services.equipment_planning import _parse_resource_segments


def _client() -> tuple[TestClient, object]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app), engine


def _project(client: TestClient, name: str) -> int:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 200
    return response.json()["id"]


def _resource(resource_id: str, resource_type: str = "可用频段", start: float = 400, end: float = 420) -> dict:
    return {
        "resource_id": resource_id,
        "name": resource_id,
        "resource_type": resource_type,
        "purpose": "任务通信",
        "region": "区域A",
        "start_mhz": start,
        "end_mhz": end,
        "channel_step_khz": 25,
        "max_bandwidth_khz": 100,
        "max_power_w": 50,
        "guard_band_khz": 25,
        "center_lat": 30,
        "center_lon": 120,
        "coverage_radius_km": 20,
        "status": "启用",
    }


def test_spectrum_resource_crud_and_project_isolation() -> None:
    client, engine = _client()
    try:
        project_a = _project(client, "resource-a")
        project_b = _project(client, "resource-b")
        base_a = f"/api/projects/{project_a}/spectrum-resources"
        created = client.post(base_a, json=_resource("POOL-A"))
        assert created.status_code == 200, created.text
        row = created.json()
        assert client.post(base_a, json=_resource("POOL-A")).status_code == 409
        assert client.get(base_a).json()[0]["resource_id"] == "POOL-A"
        assert client.get(f"/api/projects/{project_b}/spectrum-resources").json() == []

        updated_payload = _resource("POOL-A", "保护频段", 401, 419)
        updated = client.put(f"{base_a}/{row['id']}", json=updated_payload)
        assert updated.status_code == 200
        assert updated.json()["resource_type"] == "保护频段"
        assert client.put(f"/api/projects/{project_b}/spectrum-resources/{row['id']}", json=updated_payload).status_code == 404
        assert client.delete(f"{base_a}/{row['id']}").status_code == 200
        assert client.get(base_a).json() == []
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_resource_validation_rejects_invalid_ranges_and_times() -> None:
    client, engine = _client()
    try:
        project_id = _project(client, "resource-validation")
        base = f"/api/projects/{project_id}/spectrum-resources"
        invalid_range = _resource("BAD", start=420, end=400)
        assert client.post(base, json=invalid_range).status_code == 422
        invalid_type = _resource("BAD-TYPE")
        invalid_type["resource_type"] = "未知"
        assert client.post(base, json=invalid_type).status_code == 422
        invalid_time = _resource("BAD-TIME")
        invalid_time.update({"starts_at": "2026-07-12T12:00:00", "ends_at": "2026-07-11T12:00:00"})
        assert client.post(base, json=invalid_time).status_code == 422
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_heatmap_combines_active_resource_types_and_time_windows() -> None:
    client, engine = _client()
    try:
        project_id = _project(client, "resource-heatmap")
        base = f"/api/projects/{project_id}/spectrum-resources"
        assert client.post(base, json=_resource("AVAILABLE", "可用频段", 400, 420)).status_code == 200
        temporary = _resource("TEMP", "临时占用", 405, 410)
        temporary.update({"starts_at": "2026-07-11T08:00:00", "ends_at": "2026-07-11T18:00:00"})
        assert client.post(base, json=temporary).status_code == 200
        protected = _resource("PROTECT", "保护频段", 415, 418)
        assert client.post(base, json=protected).status_code == 200
        future = _resource("FUTURE", "禁用频段", 410, 412)
        future.update({"starts_at": "2026-07-12T08:00:00", "ends_at": "2026-07-12T18:00:00"})
        assert client.post(base, json=future).status_code == 200

        heatmap = client.get(
            f"/api/projects/{project_id}/spectrum-resource-heatmap",
            params={"at": "2026-07-11T12:00:00", "region": "区域A"},
        )
        assert heatmap.status_code == 200, heatmap.text
        data = heatmap.json()
        assert data["summary"]["active_resource_count"] == 3
        assert any(cell["resource_type"] == "临时占用" and cell["availability_pct"] == 30 for cell in data["cells"])
        assert any(cell["resource_type"] == "保护频段" and cell["availability_pct"] == 10 for cell in data["cells"])
        assert all("FUTURE" not in cell["active_resource_ids"] for cell in data["cells"])
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_active_resource_constraints_participate_in_task_planning() -> None:
    client, engine = _client()
    try:
        project_id = _project(client, "resource-planning")
        generated = client.post(f"/api/projects/{project_id}/generate-task-demo", params={"scenario": "baseline"})
        assert generated.status_code == 200, generated.text

        protected = _resource("LIVE-PROTECT", "保护频段", 410.2, 410.6)
        protected["region"] = "全域"
        created = client.post(f"/api/projects/{project_id}/spectrum-resources", json=protected)
        assert created.status_code == 200, created.text

        future = _resource("FUTURE-FORBID", "禁用频段", 410.7, 410.9)
        future.update({"region": "全域", "starts_at": "2099-01-01T00:00:00", "ends_at": "2099-01-02T00:00:00"})
        assert client.post(f"/api/projects/{project_id}/spectrum-resources", json=future).status_code == 200

        planned = client.post(
            f"/api/projects/{project_id}/task-plan",
            json={"objective": "minimize_interference", "constraint_weights": {}, "strategy_profile": "risk_first"},
        )
        assert planned.status_code == 200, planned.text
        summary = planned.json()["summary"]
        assert summary["spectrum_resource_rule_count"] >= 1

        visualization = client.get(
            f"/api/projects/{project_id}/task-visualization",
            params={"run_id": planned.json()["run_id"]},
        )
        assert visualization.status_code == 200, visualization.text
        timeline_rules = [
            marker["id"]
            for band in visualization.json()["spectrum_timeline"]
            for marker in band["markers"]
            if marker["kind"] in {"保护", "禁用"}
        ]
        assert any("LIVE-PROTECT" in rule_id for rule_id in timeline_rules)
        assert all("FUTURE-FORBID" not in rule_id for rule_id in timeline_rules)
        uhf_assignments = [item for item in visualization.json()["assignments"] if item.get("band_group") == "UHF-SIM-1"]
        assert uhf_assignments
        assert all(
            not (segment.start < 410.6 and 410.2 < segment.end)
            for assignment in uhf_assignments
            for segment in _parse_resource_segments(assignment.get("assigned_resource") or "")
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from backend.app.database import get_session
from backend.app.main import app


def test_plan_adoption_and_rollback_restore_complete_inputs() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    try:
        preflight = client.options(
            "/api/projects",
            headers={"Origin": "http://127.0.0.1:5199", "Access-Control-Request-Method": "GET"},
        )
        assert preflight.headers["access-control-allow-origin"] == "http://127.0.0.1:5199"

        project = client.post("/api/projects", json={"name": "lifecycle"}).json()
        project_id = project["id"]
        assert client.post(f"/api/projects/{project_id}/generate-task-demo", params={"scenario": "baseline"}).status_code == 200

        planned = client.post(
            f"/api/projects/{project_id}/task-plan",
            json={"objective": "task_assurance", "constraint_weights": {"task": 80, "risk": 70}, "strategy_profile": "balanced"},
        )
        assert planned.status_code == 200, planned.text
        source_run_id = planned.json()["run_id"]

        adopted = client.post(f"/api/projects/{project_id}/task-runs/{source_run_id}/adopt")
        assert adopted.status_code == 200, adopted.text
        assert adopted.json()["adopted"] is True

        original = client.get(f"/api/projects/{project_id}/task-data").json()
        original_group_ids = {item["equipment_group_id"] for item in original["equipment_groups"]}
        deleted = original["equipment_groups"][0]
        assert client.delete(f"/api/projects/{project_id}/equipment-groups/{deleted['id']}").status_code == 200

        jammer = {
            "resource_id": "ROLLBACK-JAMMER",
            "name": "回滚测试干扰源",
            "resource_type": "干扰源",
            "purpose": "动态事件",
            "region": "全域",
            "start_mhz": 410,
            "end_mhz": 411,
            "channel_step_khz": 25,
            "max_bandwidth_khz": 100,
            "max_power_w": 500,
            "guard_band_khz": 25,
            "coverage_radius_km": 20,
            "status": "启用",
        }
        assert client.post(f"/api/projects/{project_id}/spectrum-resources", json=jammer).status_code == 200
        changed = client.get(f"/api/projects/{project_id}/task-data").json()
        assert deleted["equipment_group_id"] not in {item["equipment_group_id"] for item in changed["equipment_groups"]}
        assert client.get(f"/api/projects/{project_id}/spectrum-resources").json()

        rolled_back = client.post(f"/api/projects/{project_id}/task-runs/{source_run_id}/rollback")
        assert rolled_back.status_code == 200, rolled_back.text
        restored_run_id = rolled_back.json()["run_id"]
        assert restored_run_id != source_run_id

        restored = client.get(f"/api/projects/{project_id}/task-data").json()
        assert {item["equipment_group_id"] for item in restored["equipment_groups"]} == original_group_ids
        assert client.get(f"/api/projects/{project_id}/spectrum-resources").json() == []

        versions = client.get(f"/api/projects/{project_id}/task-versions").json()["runs"]
        restored_version = next(item for item in versions if item["run_id"] == restored_run_id)
        source_version = next(item for item in versions if item["run_id"] == source_run_id)
        assert restored_version["adopted"] is True
        assert restored_version["rollback_source_run_id"] == source_run_id
        assert restored_version["snapshot_available"] is True
        assert source_version["adopted"] is False
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

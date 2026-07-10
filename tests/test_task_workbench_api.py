from __future__ import annotations

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.database import get_session
from backend.app.main import app
from backend.app.models import AuditLog
from backend.app.services import task_workbench
from backend.app.services.excel_io import EQUIPMENT_GROUP_COLUMNS, SPECTRUM_RULE_COLUMNS, TASK_UNIT_COLUMNS


@pytest.fixture()
def api() -> tuple[TestClient, object]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app, raise_server_exceptions=False)
    try:
        yield client, engine
    finally:
        app.dependency_overrides.clear()


def _project(client: TestClient, name: str) -> int:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _task_unit(task_unit_id: str, name: str | None = None) -> dict:
    return {
        "task_unit_id": task_unit_id,
        "name": name or task_unit_id,
        "unit_type": "command",
        "priority": 3,
        "min_satisfaction_ratio": 0.9,
    }


def _equipment(group_id: str, task_unit_id: str) -> dict:
    return {
        "equipment_group_id": group_id,
        "task_unit_id": task_unit_id,
        "equipment_type": "radio",
        "count": 2,
        "bandwidth_khz": 25,
        "required_channels": 1,
    }


def test_crud_from_empty_project_and_audit(api: tuple[TestClient, object]) -> None:
    client, engine = api
    project_id = _project(client, "workbench-crud")
    base = f"/api/projects/{project_id}"

    assert client.get(f"{base}/task-mission").json() is None
    initial = client.get(f"{base}/task-data").json()
    assert initial["mission"] is None
    assert initial["phases"] == []
    assert initial["links"] == []

    mission = client.put(
        f"{base}/task-mission",
        json={
            "mission_id": "M-1",
            "name": "Mission one",
            "required_assurance": 0.95,
            "starts_at": "2026-07-10T08:00:00",
            "ends_at": "2026-07-10T12:00:00",
        },
    )
    assert mission.status_code == 200, mission.text
    assert mission.json()["project_id"] == project_id
    assert mission.json()["id"] is not None
    invalid_time = client.put(
        f"{base}/task-mission",
        json={"mission_id": "M-1", "name": "Bad", "starts_at": "2026-07-11T12:00:00", "ends_at": "2026-07-10T12:00:00"},
    )
    assert invalid_time.status_code == 422

    phase = client.post(f"{base}/task-phases", json={"phase_id": "P-1", "name": "Phase one", "sequence": 1})
    assert phase.status_code == 200, phase.text
    phase_row = phase.json()
    assert client.post(f"{base}/task-phases", json={"phase_id": "P-1", "name": "Duplicate"}).status_code == 409

    unit_a = client.post(f"{base}/task-units", json=_task_unit("TU-A"))
    unit_b = client.post(f"{base}/task-units", json=_task_unit("TU-B"))
    assert unit_a.status_code == unit_b.status_code == 200
    group = client.post(f"{base}/equipment-groups", json=_equipment("EG-B", "TU-B"))
    assert group.status_code == 200, group.text

    link_payload = {
        "link_id": "L-1",
        "name": "Command link",
        "source_task_unit_id": "TU-A",
        "target_equipment_group_id": "EG-B",
        "active_phase_ids": ["P-1"],
        "required_availability": 0.99,
        "bandwidth_khz": 50,
        "required_channels": 2,
    }
    link = client.post(f"{base}/task-links", json=link_payload)
    assert link.status_code == 200, link.text
    assert link.json()["active_phase_ids"] == ["P-1"]

    assert client.put(f"{base}/task-phases/{phase_row['id']}", json={"phase_id": "P-1", "name": "Updated", "sequence": 2}).status_code == 200
    assert client.put(f"{base}/task-units/{unit_a.json()['id']}", json=_task_unit("TU-A", "Updated unit")).status_code == 200
    assert client.put(f"{base}/equipment-groups/{group.json()['id']}", json=_equipment("EG-B", "TU-B")).status_code == 200
    link_payload["name"] = "Updated link"
    assert client.put(f"{base}/task-links/{link.json()['id']}", json=link_payload).status_code == 200

    data = client.get(f"{base}/task-data").json()
    assert data["mission"]["mission_id"] == "M-1"
    assert [row["phase_id"] for row in data["phases"]] == ["P-1"]
    assert [row["link_id"] for row in data["links"]] == ["L-1"]
    assert client.delete(f"{base}/task-phases/{phase_row['id']}").status_code == 409
    assert client.delete(f"{base}/equipment-groups/{group.json()['id']}").status_code == 409
    assert client.delete(f"{base}/task-links/{link.json()['id']}").status_code == 200
    assert client.delete(f"{base}/equipment-groups/{group.json()['id']}").status_code == 200
    assert client.delete(f"{base}/task-units/{unit_a.json()['id']}").status_code == 200
    assert client.delete(f"{base}/task-units/{unit_b.json()['id']}").status_code == 200
    assert client.delete(f"{base}/task-phases/{phase_row['id']}").status_code == 200

    with Session(engine) as session:
        actions = {row.action for row in session.exec(select(AuditLog).where(AuditLog.project_id == project_id)).all()}
    assert {"create_task_mission", "create_task_phase", "create_task_unit", "create_equipment_group", "create_task_link"} <= actions


def test_invalid_links_and_cross_project_isolation(api: tuple[TestClient, object]) -> None:
    client, _ = api
    project_a = _project(client, "project-a")
    project_b = _project(client, "project-b")
    base_a = f"/api/projects/{project_a}"
    base_b = f"/api/projects/{project_b}"
    unit_a = client.post(f"{base_a}/task-units", json=_task_unit("TU-A")).json()
    unit_b = client.post(f"{base_b}/task-units", json=_task_unit("TU-B")).json()
    group_b = client.post(f"{base_b}/equipment-groups", json=_equipment("EG-B", "TU-B")).json()
    phase_b = client.post(f"{base_b}/task-phases", json={"phase_id": "P-B", "name": "Other phase"}).json()

    assert client.post(f"{base_a}/equipment-groups", json=_equipment("EG-X", "TU-B")).status_code == 422
    assert client.put(f"{base_a}/task-units/{unit_b['id']}", json=_task_unit("TU-X")).status_code == 404
    assert client.delete(f"{base_a}/equipment-groups/{group_b['id']}").status_code == 404
    assert client.delete(f"{base_a}/task-phases/{phase_b['id']}").status_code == 404
    invalid_link = {
        "link_id": "L-X",
        "name": "Invalid",
        "source_task_unit_id": "TU-A",
        "target_equipment_group_id": "EG-B",
        "active_phase_ids": ["P-B"],
    }
    assert client.post(f"{base_a}/task-links", json=invalid_link).status_code == 422
    invalid_link.update({"target_equipment_group_id": None, "target_task_unit_id": "TU-A"})
    assert client.post(f"{base_a}/task-links", json=invalid_link).status_code == 422
    assert client.get(f"{base_a}/task-units").json() == [unit_a]


def _xlsx(columns: list[str], row: dict) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(columns)
    sheet.append([row.get(column) for column in columns])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _package(prefix: str, equipment_task_id: str | None = None) -> dict[str, tuple[str, bytes, str]]:
    task_id = f"TU-{prefix}"
    task_row = {
        "task_unit_id": task_id,
        "name": f"Unit {prefix}",
        "unit_type": "command",
        "area_center_lat": 30,
        "area_center_lon": 120,
        "area_radius_km": 1,
        "priority": 2,
        "spectrum_relation": "exclusive",
        "preferred_band_groups": f"B-{prefix}",
        "min_satisfaction_ratio": 0.9,
    }
    equipment_row = {
        "equipment_group_id": f"EG-{prefix}",
        "task_unit_id": equipment_task_id or task_id,
        "equipment_type": "radio",
        "count": 1,
        "bandwidth_khz": 25,
        "tx_power_w": 5,
        "required_channels": 1,
    }
    rule_row = {
        "rule_id": f"SR-{prefix}",
        "rule_type": "可用",
        "band_group": f"B-{prefix}",
        "spectrum_relation": "可复用",
        "start_mhz": 400,
        "end_mhz": 410,
        "channel_step_khz": 25,
        "max_bandwidth_khz": 25,
        "max_power_w": 10,
    }
    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return {
        "task_units": ("task_units.xlsx", _xlsx(TASK_UNIT_COLUMNS, task_row), content_type),
        "equipment_groups": ("equipment_groups.xlsx", _xlsx(EQUIPMENT_GROUP_COLUMNS, equipment_row), content_type),
        "spectrum_rules": ("spectrum_rules.xlsx", _xlsx(SPECTRUM_RULE_COLUMNS, rule_row), content_type),
    }


def test_task_package_is_atomic_and_replaces_all_data(
    api: tuple[TestClient, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = api
    project_id = _project(client, "package-import")
    base = f"/api/projects/{project_id}"
    assert client.post(f"{base}/import-task-package", files=_package("OLD")).status_code == 200
    before = client.get(f"{base}/task-data").json()

    invalid = client.post(f"{base}/import-task-package", files=_package("BAD", equipment_task_id="TU-MISSING"))
    assert invalid.status_code == 422
    assert client.get(f"{base}/task-data").json() == before

    original_replace = task_workbench._replace_equipment_groups_without_commit
    with monkeypatch.context() as patch:
        def fail_after_staging(session, target_project_id, records):
            original_replace(session, target_project_id, records)
            raise RuntimeError("injected import failure")

        patch.setattr(task_workbench, "_replace_equipment_groups_without_commit", fail_after_staging)
        assert client.post(f"{base}/import-task-package", files=_package("ROLLBACK")).status_code == 500
    assert client.get(f"{base}/task-data").json() == before

    success = client.post(f"{base}/import-task-package", files=_package("NEW"))
    assert success.status_code == 200, success.text
    assert success.json() == {"task_unit_count": 1, "equipment_group_count": 1, "spectrum_rule_count": 1}
    after = client.get(f"{base}/task-data").json()
    assert [row["task_unit_id"] for row in after["task_units"]] == ["TU-NEW"]
    assert [row["equipment_group_id"] for row in after["equipment_groups"]] == ["EG-NEW"]
    assert [row["rule_id"] for row in after["spectrum_rules"]] == ["SR-NEW"]

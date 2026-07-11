from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from backend.app.database import get_session
from backend.app.main import app


def _assert_ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def test_task_planning_api_end_to_end_acceptance_flow() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    try:
        project = _assert_ok(client.post("/api/projects", json={"name": "api-e2e-acceptance"}))
        project_id = project["id"]
        assert project["created_at"]
        assert project["updated_at"]

        projects = _assert_ok(client.get("/api/projects"))
        assert projects[0]["id"] == project_id
        assert projects[0]["name"] == "api-e2e-acceptance"

        demo = _assert_ok(client.post(f"/api/projects/{project_id}/generate-task-demo?scenario=large_joint_exercise"))
        assert demo["task_unit_count"] >= 12
        assert demo["equipment_group_count"] >= 40
        assert demo["mission_count"] == 1
        assert demo["phase_count"] == 3
        assert demo["link_count"] == demo["task_unit_count"] - 1
        assert demo["project_name"].startswith("大型联合演训-用频筹划-")
        assert demo["mission_name"] == "大型联合演训-用频筹划任务"

        task_data = _assert_ok(client.get(f"/api/projects/{project_id}/task-data"))
        assert task_data["mission"]["name"] == demo["mission_name"]
        assert len(task_data["phases"]) == 3
        assert all(item["status"] == "待开始" for item in task_data["phases"])
        assert len(task_data["links"]) == demo["task_unit_count"] - 1
        task_unit_ids = {item["task_unit_id"] for item in task_data["task_units"]}
        assert all(item["source_task_unit_id"] in task_unit_ids for item in task_data["links"])
        assert all(item["target_task_unit_id"] in task_unit_ids for item in task_data["links"])

        validation = _assert_ok(client.post(f"/api/projects/{project_id}/validate-task"))
        assert validation["ok"] is True

        plan = _assert_ok(
            client.post(
                f"/api/projects/{project_id}/task-plan",
                json={
                    "objective": "task_assurance",
                    "constraint_weights": {"task": 80, "risk": 75, "spectrum": 45, "priority": 70, "switching": 20, "reuse": 35},
                    "strategy_profile": "balanced",
                },
            )
        )
        assert plan["status"] == "success"
        base_run_id = plan["run_id"]

        visualization = _assert_ok(client.get(f"/api/projects/{project_id}/task-visualization?run_id={base_run_id}"))
        assert visualization["assignments"]
        assert visualization["task_units"]
        assert visualization["band_usage"]
        assert all(item["available_ranges"] for item in visualization["band_usage"])
        assert all(item["available_ranges"][0]["start_mhz"] < item["available_ranges"][0]["end_mhz"] for item in visualization["band_usage"])
        assert visualization["spectrum_timeline"]
        assert visualization["summary"]["bottleneck_analysis"]["band_bottlenecks"]
        assert any(item["alternative_resources"] for item in visualization["assignments"])
        assert any(item["explanation_chain"] for item in visualization["assignments"])

        strategy_trials = _assert_ok(
            client.post(
                f"/api/projects/{project_id}/task-strategy-trials",
                json={"base_run_id": base_run_id, "objective": "task_assurance", "strategy_profile": "balanced"},
            )
        )
        assert strategy_trials["ok"] is True
        assert strategy_trials["recommended_trial_id"] == strategy_trials["decision_summary"]["recommended_trial_id"]
        assert strategy_trials["decision_summary"]["role_picks"]
        assert strategy_trials["decision_summary"]["pareto_frontier"]
        assert strategy_trials["decision_summary"]["adoption_guardrails"]

        performance = _assert_ok(client.post(f"/api/projects/{project_id}/task-performance-batch"))
        assert performance["summary"]["run_count"] >= 10
        assert performance["analysis"]["capacity_profile"]["status"]

        capacity = _assert_ok(
            client.post(
                f"/api/projects/{project_id}/task-capacity-batches",
                json={"base_run_id": base_run_id, "objective": "task_assurance", "strategy_profile": "balanced"},
            )
        )
        assert capacity["ok"] is True
        assert len(capacity["runs"]) >= 2
        assert capacity["merged_plan"]["run_ids"]
        assert capacity["cross_batch_review"]["cross_batch_risk_count"] > 0

        master_export = client.get(f"/api/projects/{project_id}/task-capacity-master-export.xlsx")
        assert master_export.status_code == 200
        assert master_export.content[:2] == b"PK"

        closure = _assert_ok(
            client.post(
                f"/api/projects/{project_id}/task-capacity-risk-closure",
                json={"objective": "task_assurance", "strategy_profile": "risk_closure"},
            )
        )
        assert closure["ok"] is True
        assert closure["closure"]["applied_rule_count"] > 0
        assert closure["closure"]["before_cross_batch_risk_count"] >= closure["closure"]["after_cross_batch_risk_count"]

        closure_export = client.get(f"/api/projects/{project_id}/task-capacity-risk-closure-export.xlsx")
        assert closure_export.status_code == 200
        assert closure_export.content[:2] == b"PK"

        versions = _assert_ok(client.get(f"/api/projects/{project_id}/task-versions"))
        assert versions["runs"]
        assert versions["audit_logs"]
        assert versions["audit_summary"]["planning_count"] > 0
        assert versions["audit_summary"]["manual_change_count"] > 0
        assert versions["performance_history"]
        assert versions["closure_events"]
        assert versions["closure_events"][0]["applied_rule_count"] == closure["closure"]["applied_rule_count"]

        report = client.get(f"/api/projects/{project_id}/task-report?run={closure['runs'][0]['run_id']}")
        assert report.status_code == 200
        assert "text/html" in report.headers["content-type"]

        pdf_report = client.get(f"/api/projects/{project_id}/task-report.pdf?run={closure['runs'][0]['run_id']}")
        assert pdf_report.status_code == 200
        assert pdf_report.content[:4] == b"%PDF"
        assert "application/pdf" in pdf_report.headers["content-type"]

        export = client.get(f"/api/projects/{project_id}/task-export.xlsx?run={closure['runs'][0]['run_id']}")
        assert export.status_code == 200
        assert export.content[:2] == b"PK"

        audited_exports = _assert_ok(client.get(f"/api/projects/{project_id}/task-versions"))
        assert audited_exports["audit_summary"]["export_count"] >= 3
    finally:
        app.dependency_overrides.clear()

from __future__ import annotations

from collections.abc import Callable

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.models import AuditLog, EquipmentGroup, Project, SpectrumRule, TaskUnit
from backend.app.services import equipment_planning


class TrackingSession(Session):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.commit_calls = 0
        self.rollback_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1
        super().commit()

    def rollback(self) -> None:
        self.rollback_calls += 1
        super().rollback()


def _create_database() -> tuple[object, int]:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        project = Project(name="transaction-test")
        session.add(project)
        session.commit()
        session.refresh(project)
        assert project.id is not None
        return engine, project.id


def _generate_preset(session: Session, project_id: int) -> dict:
    return equipment_planning.generate_demo_scenario(session, project_id, "uav_priority")


def _generate_parametric(session: Session, project_id: int) -> dict:
    return equipment_planning.generate_parametric_demo_scenario(
        session,
        project_id,
        {
            "unit_count": 8,
            "density_multiplier": 1.2,
            "radar_ratio": 20,
            "uav_ratio": 25,
            "protection_density": 1,
            "forbidden_density": 1,
        },
    )


GENERATORS = [
    pytest.param(_generate_preset, "generate_demo_scenario", id="preset"),
    pytest.param(_generate_parametric, "generate_parametric_demo_scenario", id="parametric"),
]


@pytest.mark.parametrize(("generate", "expected_action"), GENERATORS)
def test_demo_generation_commits_all_data_once(
    generate: Callable[[Session, int], dict],
    expected_action: str,
) -> None:
    engine, project_id = _create_database()

    with TrackingSession(engine) as session:
        result = generate(session, project_id)
        assert session.commit_calls == 1
        assert session.rollback_calls == 0

    with Session(engine) as session:
        project = session.get(Project, project_id)
        assert project is not None
        assert project.name == result["project_name"]
        assert len(session.exec(select(TaskUnit).where(TaskUnit.project_id == project_id)).all()) == result["task_unit_count"]
        assert len(session.exec(select(EquipmentGroup).where(EquipmentGroup.project_id == project_id)).all()) == result["equipment_group_count"]
        assert len(session.exec(select(SpectrumRule).where(SpectrumRule.project_id == project_id)).all()) == result["spectrum_rule_count"]
        actions = [
            row.action
            for row in session.exec(select(AuditLog).where(AuditLog.project_id == project_id).order_by(AuditLog.id)).all()
        ]
        assert actions == [
            "upload_task_units",
            "upload_equipment_groups",
            "upload_spectrum_rules",
            expected_action,
        ]


def _project_snapshot(session: Session, project_id: int) -> dict:
    project = session.get(Project, project_id)
    assert project is not None
    return {
        "name": project.name,
        "status": project.status,
        "task_units": [
            row.model_dump()
            for row in session.exec(select(TaskUnit).where(TaskUnit.project_id == project_id).order_by(TaskUnit.id)).all()
        ],
        "equipment_groups": [
            row.model_dump()
            for row in session.exec(select(EquipmentGroup).where(EquipmentGroup.project_id == project_id).order_by(EquipmentGroup.id)).all()
        ],
        "spectrum_rules": [
            row.model_dump()
            for row in session.exec(select(SpectrumRule).where(SpectrumRule.project_id == project_id).order_by(SpectrumRule.id)).all()
        ],
        "audit_logs": [
            row.model_dump()
            for row in session.exec(select(AuditLog).where(AuditLog.project_id == project_id).order_by(AuditLog.id)).all()
        ],
    }


@pytest.mark.parametrize(("generate", "expected_action"), GENERATORS)
def test_demo_generation_rolls_back_every_change_when_a_step_fails(
    monkeypatch: pytest.MonkeyPatch,
    generate: Callable[[Session, int], dict],
    expected_action: str,
) -> None:
    del expected_action
    engine, project_id = _create_database()
    with Session(engine) as session:
        equipment_planning.generate_demo_scenario(session, project_id, "baseline")
        before = _project_snapshot(session, project_id)

    replace_equipment_groups = equipment_planning._replace_equipment_groups_without_commit

    def fail_after_equipment_groups_are_staged(session: Session, target_project_id: int, records: list[dict]) -> None:
        replace_equipment_groups(session, target_project_id, records)
        raise RuntimeError("injected equipment-group failure")

    monkeypatch.setattr(
        equipment_planning,
        "_replace_equipment_groups_without_commit",
        fail_after_equipment_groups_are_staged,
    )

    with TrackingSession(engine) as session:
        with pytest.raises(RuntimeError, match="injected equipment-group failure"):
            generate(session, project_id)
        assert session.commit_calls == 0
        assert session.rollback_calls == 1

    with Session(engine) as session:
        assert _project_snapshot(session, project_id) == before


def test_public_replace_operations_still_commit_successfully() -> None:
    engine, project_id = _create_database()
    task_units, equipment_groups, spectrum_rules = equipment_planning.demo_scenario_records("baseline")

    with TrackingSession(engine) as session:
        equipment_planning.replace_task_units(session, project_id, task_units[:1])
        assert session.commit_calls == 1
        equipment_planning.replace_equipment_groups(session, project_id, equipment_groups[:1])
        assert session.commit_calls == 2
        equipment_planning.replace_spectrum_rules(session, project_id, spectrum_rules[:1])
        assert session.commit_calls == 3

    with Session(engine) as session:
        assert len(session.exec(select(TaskUnit).where(TaskUnit.project_id == project_id)).all()) == 1
        assert len(session.exec(select(EquipmentGroup).where(EquipmentGroup.project_id == project_id)).all()) == 1
        assert len(session.exec(select(SpectrumRule).where(SpectrumRule.project_id == project_id)).all()) == 1

from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..models import AuditLog, EquipmentGroup, MissionTask, Project, SpectrumRule, TaskLink, TaskPhase, TaskUnit
from .equipment_planning import (
    _replace_equipment_groups_without_commit,
    _replace_spectrum_rules_without_commit,
    _replace_task_units_without_commit,
)


def _require_project(session: Session, project_id: int) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _scoped_row(session: Session, model: type[Any], project_id: int, row_id: int, label: str) -> Any:
    row = session.get(model, row_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return row


def _clean_identifier(value: object, field: str) -> str:
    identifier = str(value or "").strip()
    if not identifier:
        raise HTTPException(status_code=422, detail=f"{field} must not be empty")
    return identifier


def _validate_time_range(data: dict[str, Any]) -> None:
    starts_at = data.get("starts_at")
    ends_at = data.get("ends_at")
    if starts_at is not None and ends_at is not None and ends_at < starts_at:
        raise HTTPException(status_code=422, detail="ends_at must be greater than or equal to starts_at")


def _validate_coordinates(data: dict[str, Any], lat_field: str, lon_field: str) -> None:
    latitude = data.get(lat_field)
    longitude = data.get(lon_field)
    if latitude is not None and not -90 <= float(latitude) <= 90:
        raise HTTPException(status_code=422, detail=f"{lat_field} must be between -90 and 90")
    if longitude is not None and not -180 <= float(longitude) <= 180:
        raise HTTPException(status_code=422, detail=f"{lon_field} must be between -180 and 180")


def _require_finite(data: dict[str, Any], fields: tuple[str, ...]) -> None:
    for field in fields:
        value = data.get(field)
        if value is not None and not math.isfinite(float(value)):
            raise HTTPException(status_code=422, detail=f"{field} must be finite")


def _require_unique(
    session: Session,
    model: type[Any],
    project_id: int,
    field: str,
    value: str,
    row_id: int | None = None,
) -> None:
    statement = select(model).where(model.project_id == project_id, getattr(model, field) == value)
    existing = session.exec(statement).first()
    if existing is not None and existing.id != row_id:
        raise HTTPException(status_code=409, detail=f"{field} already exists in this project")


def _audit(session: Session, project_id: int, action: str, detail: object) -> None:
    session.add(
        AuditLog(
            project_id=project_id,
            actor="user",
            action=action,
            detail=json.dumps(detail, ensure_ascii=False, default=str),
        )
    )


def _commit(session: Session, project: Project, action: str, detail: object, row: Any | None = None) -> None:
    project.status = "task_data_updated"
    project.updated_at = datetime.utcnow()
    session.add(project)
    _audit(session, project.id, action, detail)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Conflicting project data") from exc
    if row is not None:
        session.refresh(row)


def get_mission(session: Session, project_id: int) -> dict[str, Any] | None:
    _require_project(session, project_id)
    mission = session.exec(select(MissionTask).where(MissionTask.project_id == project_id)).first()
    return mission.model_dump() if mission is not None else None


def upsert_mission(session: Session, project_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    project = _require_project(session, project_id)
    data = dict(payload)
    data["mission_id"] = _clean_identifier(data.get("mission_id"), "mission_id")
    data["name"] = _clean_identifier(data.get("name"), "name")
    _validate_time_range(data)
    _validate_coordinates(data, "center_lat", "center_lon")
    _require_finite(data, ("required_assurance", "center_lat", "center_lon", "area_radius_km", "mobility_range_km"))
    mission = session.exec(select(MissionTask).where(MissionTask.project_id == project_id)).first()
    action = "create_task_mission" if mission is None else "update_task_mission"
    if mission is None:
        mission = MissionTask(project_id=project_id, **data)
    else:
        for key, value in data.items():
            setattr(mission, key, value)
    session.add(mission)
    _commit(session, project, action, data, mission)
    return mission.model_dump()


def list_phases(session: Session, project_id: int) -> list[dict[str, Any]]:
    _require_project(session, project_id)
    rows = session.exec(
        select(TaskPhase).where(TaskPhase.project_id == project_id).order_by(TaskPhase.sequence, TaskPhase.id)
    ).all()
    return [row.model_dump() for row in rows]


def _validated_phase_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    data["phase_id"] = _clean_identifier(data.get("phase_id"), "phase_id")
    data["name"] = _clean_identifier(data.get("name"), "name")
    _validate_time_range(data)
    _validate_coordinates(data, "area_center_lat", "area_center_lon")
    _require_finite(data, ("area_center_lat", "area_center_lon", "area_radius_km"))
    return data


def create_phase(session: Session, project_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    project = _require_project(session, project_id)
    data = _validated_phase_data(payload)
    _require_unique(session, TaskPhase, project_id, "phase_id", data["phase_id"])
    row = TaskPhase(project_id=project_id, **data)
    session.add(row)
    _commit(session, project, "create_task_phase", data, row)
    return row.model_dump()


def update_phase(session: Session, project_id: int, row_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    project = _require_project(session, project_id)
    row = _scoped_row(session, TaskPhase, project_id, row_id, "Task phase")
    data = _validated_phase_data(payload)
    _require_unique(session, TaskPhase, project_id, "phase_id", data["phase_id"], row_id)
    if row.phase_id != data["phase_id"] and _links_using_phase(session, project_id, row.phase_id):
        raise HTTPException(status_code=409, detail="Task phase is referenced by task links")
    for key, value in data.items():
        setattr(row, key, value)
    session.add(row)
    _commit(session, project, "update_task_phase", data, row)
    return row.model_dump()


def delete_phase(session: Session, project_id: int, row_id: int) -> None:
    project = _require_project(session, project_id)
    row = _scoped_row(session, TaskPhase, project_id, row_id, "Task phase")
    if _links_using_phase(session, project_id, row.phase_id):
        raise HTTPException(status_code=409, detail="Task phase is referenced by task links")
    detail = row.model_dump()
    session.delete(row)
    _commit(session, project, "delete_task_phase", detail)


def _links_using_phase(session: Session, project_id: int, phase_id: str) -> list[TaskLink]:
    links = session.exec(select(TaskLink).where(TaskLink.project_id == project_id)).all()
    return [link for link in links if phase_id in (link.active_phase_ids or [])]


def list_task_units(session: Session, project_id: int) -> list[dict[str, Any]]:
    _require_project(session, project_id)
    rows = session.exec(select(TaskUnit).where(TaskUnit.project_id == project_id).order_by(TaskUnit.id)).all()
    return [row.model_dump() for row in rows]


def _validated_task_unit_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    data["task_unit_id"] = _clean_identifier(data.get("task_unit_id"), "task_unit_id")
    data["name"] = _clean_identifier(data.get("name"), "name")
    data["unit_type"] = _clean_identifier(data.get("unit_type"), "unit_type")
    _validate_coordinates(data, "area_center_lat", "area_center_lon")
    _require_finite(data, ("area_center_lat", "area_center_lon", "area_radius_km", "min_satisfaction_ratio"))
    data["raw_json"] = json.dumps(data, ensure_ascii=False, default=str)
    return data


def create_task_unit(session: Session, project_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    project = _require_project(session, project_id)
    data = _validated_task_unit_data(payload)
    _require_unique(session, TaskUnit, project_id, "task_unit_id", data["task_unit_id"])
    row = TaskUnit(project_id=project_id, **data)
    session.add(row)
    _commit(session, project, "create_task_unit", data, row)
    return row.model_dump()


def update_task_unit(session: Session, project_id: int, row_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    project = _require_project(session, project_id)
    row = _scoped_row(session, TaskUnit, project_id, row_id, "Task unit")
    data = _validated_task_unit_data(payload)
    _require_unique(session, TaskUnit, project_id, "task_unit_id", data["task_unit_id"], row_id)
    if row.task_unit_id != data["task_unit_id"] and _task_unit_is_referenced(session, project_id, row.task_unit_id):
        raise HTTPException(status_code=409, detail="Task unit is referenced by equipment groups or task links")
    for key, value in data.items():
        setattr(row, key, value)
    session.add(row)
    _commit(session, project, "update_task_unit", data, row)
    return row.model_dump()


def delete_task_unit(session: Session, project_id: int, row_id: int) -> None:
    project = _require_project(session, project_id)
    row = _scoped_row(session, TaskUnit, project_id, row_id, "Task unit")
    if _task_unit_is_referenced(session, project_id, row.task_unit_id):
        raise HTTPException(status_code=409, detail="Task unit is referenced by equipment groups or task links")
    detail = row.model_dump()
    session.delete(row)
    _commit(session, project, "delete_task_unit", detail)


def _task_unit_is_referenced(session: Session, project_id: int, task_unit_id: str) -> bool:
    equipment = session.exec(
        select(EquipmentGroup).where(
            EquipmentGroup.project_id == project_id,
            EquipmentGroup.task_unit_id == task_unit_id,
        )
    ).first()
    if equipment is not None:
        return True
    link = session.exec(
        select(TaskLink).where(
            TaskLink.project_id == project_id,
            (TaskLink.source_task_unit_id == task_unit_id) | (TaskLink.target_task_unit_id == task_unit_id),
        )
    ).first()
    return link is not None


def list_equipment_groups(session: Session, project_id: int) -> list[dict[str, Any]]:
    _require_project(session, project_id)
    rows = session.exec(select(EquipmentGroup).where(EquipmentGroup.project_id == project_id).order_by(EquipmentGroup.id)).all()
    return [row.model_dump() for row in rows]


def _validated_equipment_group_data(session: Session, project_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    data["equipment_group_id"] = _clean_identifier(data.get("equipment_group_id"), "equipment_group_id")
    data["task_unit_id"] = _clean_identifier(data.get("task_unit_id"), "task_unit_id")
    data["equipment_type"] = _clean_identifier(data.get("equipment_type"), "equipment_type")
    task_unit = session.exec(
        select(TaskUnit).where(TaskUnit.project_id == project_id, TaskUnit.task_unit_id == data["task_unit_id"])
    ).first()
    if task_unit is None:
        raise HTTPException(status_code=422, detail="task_unit_id does not exist in this project")
    _require_finite(
        data,
        (
            "bandwidth_khz",
            "tx_power_w",
            "antenna_gain_dbi",
            "antenna_height_m",
            "receiver_sensitivity_dbm",
            "protection_distance_km",
            "min_spacing_khz",
            "guard_band_khz",
        ),
    )
    data["raw_json"] = json.dumps(data, ensure_ascii=False, default=str)
    return data


def create_equipment_group(session: Session, project_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    project = _require_project(session, project_id)
    data = _validated_equipment_group_data(session, project_id, payload)
    _require_unique(session, EquipmentGroup, project_id, "equipment_group_id", data["equipment_group_id"])
    row = EquipmentGroup(project_id=project_id, **data)
    session.add(row)
    _commit(session, project, "create_equipment_group", data, row)
    return row.model_dump()


def update_equipment_group(session: Session, project_id: int, row_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    project = _require_project(session, project_id)
    row = _scoped_row(session, EquipmentGroup, project_id, row_id, "Equipment group")
    data = _validated_equipment_group_data(session, project_id, payload)
    _require_unique(session, EquipmentGroup, project_id, "equipment_group_id", data["equipment_group_id"], row_id)
    if row.equipment_group_id != data["equipment_group_id"] and _equipment_group_is_referenced(
        session, project_id, row.equipment_group_id
    ):
        raise HTTPException(status_code=409, detail="Equipment group is referenced by task links")
    for key, value in data.items():
        setattr(row, key, value)
    session.add(row)
    _commit(session, project, "update_equipment_group", data, row)
    return row.model_dump()


def delete_equipment_group(session: Session, project_id: int, row_id: int) -> None:
    project = _require_project(session, project_id)
    row = _scoped_row(session, EquipmentGroup, project_id, row_id, "Equipment group")
    if _equipment_group_is_referenced(session, project_id, row.equipment_group_id):
        raise HTTPException(status_code=409, detail="Equipment group is referenced by task links")
    detail = row.model_dump()
    session.delete(row)
    _commit(session, project, "delete_equipment_group", detail)


def _equipment_group_is_referenced(session: Session, project_id: int, equipment_group_id: str) -> bool:
    link = session.exec(
        select(TaskLink).where(
            TaskLink.project_id == project_id,
            (TaskLink.source_equipment_group_id == equipment_group_id)
            | (TaskLink.target_equipment_group_id == equipment_group_id),
        )
    ).first()
    return link is not None


def list_links(session: Session, project_id: int) -> list[dict[str, Any]]:
    _require_project(session, project_id)
    rows = session.exec(select(TaskLink).where(TaskLink.project_id == project_id).order_by(TaskLink.id)).all()
    return [row.model_dump() for row in rows]


def _validated_link_data(session: Session, project_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    data["link_id"] = _clean_identifier(data.get("link_id"), "link_id")
    data["name"] = _clean_identifier(data.get("name"), "name")
    endpoint_fields = (
        "source_task_unit_id",
        "target_task_unit_id",
        "source_equipment_group_id",
        "target_equipment_group_id",
    )
    for field in endpoint_fields:
        data[field] = str(data.get(field) or "").strip() or None
    if sum(data[field] is not None for field in ("source_task_unit_id", "source_equipment_group_id")) != 1:
        raise HTTPException(status_code=422, detail="Exactly one source endpoint is required")
    if sum(data[field] is not None for field in ("target_task_unit_id", "target_equipment_group_id")) != 1:
        raise HTTPException(status_code=422, detail="Exactly one target endpoint is required")

    task_ids = {
        row.task_unit_id for row in session.exec(select(TaskUnit).where(TaskUnit.project_id == project_id)).all()
    }
    group_ids = {
        row.equipment_group_id
        for row in session.exec(select(EquipmentGroup).where(EquipmentGroup.project_id == project_id)).all()
    }
    for field in ("source_task_unit_id", "target_task_unit_id"):
        if data[field] is not None and data[field] not in task_ids:
            raise HTTPException(status_code=422, detail=f"{field} does not exist in this project")
    for field in ("source_equipment_group_id", "target_equipment_group_id"):
        if data[field] is not None and data[field] not in group_ids:
            raise HTTPException(status_code=422, detail=f"{field} does not exist in this project")

    source = (data["source_task_unit_id"], data["source_equipment_group_id"])
    target = (data["target_task_unit_id"], data["target_equipment_group_id"])
    if source == target:
        raise HTTPException(status_code=422, detail="Source and target endpoints must be different")

    phase_ids = [str(value).strip() for value in data.get("active_phase_ids") or [] if str(value).strip()]
    if len(phase_ids) != len(set(phase_ids)):
        raise HTTPException(status_code=422, detail="active_phase_ids must not contain duplicates")
    known_phase_ids = {
        row.phase_id for row in session.exec(select(TaskPhase).where(TaskPhase.project_id == project_id)).all()
    }
    missing_phase_ids = [phase_id for phase_id in phase_ids if phase_id not in known_phase_ids]
    if missing_phase_ids:
        raise HTTPException(status_code=422, detail={"message": "Unknown active phase ids", "phase_ids": missing_phase_ids})
    data["active_phase_ids"] = phase_ids
    _require_finite(data, ("required_availability", "bandwidth_khz"))
    return data


def create_link(session: Session, project_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    project = _require_project(session, project_id)
    data = _validated_link_data(session, project_id, payload)
    _require_unique(session, TaskLink, project_id, "link_id", data["link_id"])
    row = TaskLink(project_id=project_id, **data)
    session.add(row)
    _commit(session, project, "create_task_link", data, row)
    return row.model_dump()


def update_link(session: Session, project_id: int, row_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    project = _require_project(session, project_id)
    row = _scoped_row(session, TaskLink, project_id, row_id, "Task link")
    data = _validated_link_data(session, project_id, payload)
    _require_unique(session, TaskLink, project_id, "link_id", data["link_id"], row_id)
    for key, value in data.items():
        setattr(row, key, value)
    session.add(row)
    _commit(session, project, "update_task_link", data, row)
    return row.model_dump()


def delete_link(session: Session, project_id: int, row_id: int) -> None:
    project = _require_project(session, project_id)
    row = _scoped_row(session, TaskLink, project_id, row_id, "Task link")
    detail = row.model_dump()
    session.delete(row)
    _commit(session, project, "delete_task_link", detail)


def _duplicate_values(records: list[dict[str, Any]], field: str) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for record in records:
        value = str(record.get(field) or "").strip()
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(value for value in duplicates if value)


def validate_task_package_records(
    session: Session,
    project_id: int,
    task_units: list[dict[str, Any]],
    equipment_groups: list[dict[str, Any]],
    spectrum_rules: list[dict[str, Any]],
) -> None:
    _require_project(session, project_id)
    errors: list[str] = []
    for records, field in (
        (task_units, "task_unit_id"),
        (equipment_groups, "equipment_group_id"),
        (spectrum_rules, "rule_id"),
    ):
        duplicates = _duplicate_values(records, field)
        if duplicates:
            errors.append(f"Duplicate {field}: {', '.join(duplicates)}")

    task_ids = {str(row.get("task_unit_id") or "").strip() for row in task_units}
    group_ids = {str(row.get("equipment_group_id") or "").strip() for row in equipment_groups}
    for group in equipment_groups:
        task_unit_id = str(group.get("task_unit_id") or "").strip()
        if task_unit_id not in task_ids:
            errors.append(
                f"Equipment group {group.get('equipment_group_id') or '-'} references unknown task unit {task_unit_id or '-'}"
            )

    for link in session.exec(select(TaskLink).where(TaskLink.project_id == project_id)).all():
        for field in ("source_task_unit_id", "target_task_unit_id"):
            value = getattr(link, field)
            if value and value not in task_ids:
                errors.append(f"Existing task link {link.link_id} would reference missing task unit {value}")
        for field in ("source_equipment_group_id", "target_equipment_group_id"):
            value = getattr(link, field)
            if value and value not in group_ids:
                errors.append(f"Existing task link {link.link_id} would reference missing equipment group {value}")

    if errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "Task package cross-table validation failed; existing data was not changed", "errors": errors[:20]},
        )


def replace_task_package(
    session: Session,
    project_id: int,
    task_units: list[dict[str, Any]],
    equipment_groups: list[dict[str, Any]],
    spectrum_rules: list[dict[str, Any]],
) -> dict[str, int]:
    validate_task_package_records(session, project_id, task_units, equipment_groups, spectrum_rules)
    try:
        _replace_task_units_without_commit(session, project_id, task_units)
        _replace_equipment_groups_without_commit(session, project_id, equipment_groups)
        _replace_spectrum_rules_without_commit(session, project_id, spectrum_rules)
        _audit(
            session,
            project_id,
            "import_task_package",
            {
                "task_unit_count": len(task_units),
                "equipment_group_count": len(equipment_groups),
                "spectrum_rule_count": len(spectrum_rules),
            },
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {
        "task_unit_count": len(task_units),
        "equipment_group_count": len(equipment_groups),
        "spectrum_rule_count": len(spectrum_rules),
    }

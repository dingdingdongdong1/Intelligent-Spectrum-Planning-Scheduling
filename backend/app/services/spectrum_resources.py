from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..models import AuditLog, Project, SpectrumResource


RESOURCE_TYPES = ("可用频段", "固定占用", "临时占用", "保护频段", "禁用频段", "干扰源")
TYPE_SCORE = {"可用频段": 1.0, "临时占用": 0.3, "固定占用": 0.15, "保护频段": 0.1, "禁用频段": 0.0, "干扰源": 0.0}
TYPE_PRIORITY = {"可用频段": 0, "临时占用": 1, "固定占用": 2, "保护频段": 3, "禁用频段": 4, "干扰源": 5}


def _project(session: Session, project_id: int) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def _row(session: Session, project_id: int, row_id: int) -> SpectrumResource:
    row = session.get(SpectrumResource, row_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="频谱资源不存在")
    return row


def _validated(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    data["resource_id"] = str(data.get("resource_id") or "").strip()
    data["name"] = str(data.get("name") or "").strip()
    data["region"] = str(data.get("region") or "全域").strip()
    if not data["resource_id"] or not data["name"]:
        raise HTTPException(status_code=422, detail="资源编号和名称不能为空")
    if data.get("resource_type") not in RESOURCE_TYPES:
        raise HTTPException(status_code=422, detail=f"资源类型必须为：{', '.join(RESOURCE_TYPES)}")
    if float(data.get("end_mhz") or 0) <= float(data.get("start_mhz") or 0):
        raise HTTPException(status_code=422, detail="终止频率必须大于起始频率")
    if data.get("starts_at") and data.get("ends_at") and data["ends_at"] < data["starts_at"]:
        raise HTTPException(status_code=422, detail="结束时间必须晚于开始时间")
    return data


def _unique(session: Session, project_id: int, resource_id: str, row_id: int | None = None) -> None:
    existing = session.exec(
        select(SpectrumResource).where(
            SpectrumResource.project_id == project_id,
            SpectrumResource.resource_id == resource_id,
        )
    ).first()
    if existing is not None and existing.id != row_id:
        raise HTTPException(status_code=409, detail="项目内资源编号已存在")


def _commit(session: Session, project: Project, action: str, detail: object, row: SpectrumResource | None = None) -> None:
    project.status = "spectrum_resources_updated"
    project.updated_at = datetime.utcnow()
    session.add(project)
    session.add(AuditLog(project_id=project.id, actor="user", action=action, detail=json.dumps(detail, ensure_ascii=False, default=str)))
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="频谱资源数据冲突") from exc
    if row is not None:
        session.refresh(row)


def list_resources(session: Session, project_id: int) -> list[dict[str, Any]]:
    _project(session, project_id)
    rows = session.exec(
        select(SpectrumResource)
        .where(SpectrumResource.project_id == project_id)
        .order_by(SpectrumResource.start_mhz, SpectrumResource.id)
    ).all()
    return [row.model_dump() for row in rows]


def create_resource(session: Session, project_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    project = _project(session, project_id)
    data = _validated(payload)
    _unique(session, project_id, data["resource_id"])
    row = SpectrumResource(project_id=project_id, **data)
    session.add(row)
    _commit(session, project, "create_spectrum_resource", data, row)
    return row.model_dump()


def update_resource(session: Session, project_id: int, row_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    project = _project(session, project_id)
    row = _row(session, project_id, row_id)
    data = _validated(payload)
    _unique(session, project_id, data["resource_id"], row_id)
    for key, value in data.items():
        setattr(row, key, value)
    session.add(row)
    _commit(session, project, "update_spectrum_resource", data, row)
    return row.model_dump()


def delete_resource(session: Session, project_id: int, row_id: int) -> None:
    project = _project(session, project_id)
    row = _row(session, project_id, row_id)
    detail = row.model_dump()
    session.delete(row)
    _commit(session, project, "delete_spectrum_resource", detail)


def _active(row: SpectrumResource, at: datetime) -> bool:
    if row.status != "启用":
        return False
    if row.starts_at is not None and at < row.starts_at:
        return False
    if row.ends_at is not None and at > row.ends_at:
        return False
    return True


def resource_heatmap(session: Session, project_id: int, at: datetime | None = None, region: str | None = None) -> dict[str, Any]:
    _project(session, project_id)
    target_time = at or datetime.utcnow()
    rows = session.exec(select(SpectrumResource).where(SpectrumResource.project_id == project_id)).all()
    active = [row for row in rows if _active(row, target_time) and (not region or row.region in {region, "全域"})]
    boundaries = sorted({value for row in active for value in (row.start_mhz, row.end_mhz)})
    cells: list[dict[str, Any]] = []
    for start, end in zip(boundaries, boundaries[1:]):
        if end <= start:
            continue
        overlaps = [row for row in active if row.start_mhz < end and row.end_mhz > start]
        if not overlaps:
            continue
        dominant = max(overlaps, key=lambda row: TYPE_PRIORITY[row.resource_type])
        score = min(TYPE_SCORE[row.resource_type] for row in overlaps)
        cells.append(
            {
                "start_mhz": round(start, 6),
                "end_mhz": round(end, 6),
                "width_mhz": round(end - start, 6),
                "resource_type": dominant.resource_type,
                "availability_score": score,
                "availability_pct": round(score * 100, 1),
                "region": region or dominant.region,
                "purpose": dominant.purpose,
                "active_resource_ids": sorted(row.resource_id for row in overlaps),
            }
        )
    total_width = sum(cell["width_mhz"] for cell in cells)
    weighted = sum(cell["width_mhz"] * cell["availability_score"] for cell in cells)
    type_counts = {resource_type: sum(1 for row in active if row.resource_type == resource_type) for resource_type in RESOURCE_TYPES}
    return {
        "at": target_time.isoformat(),
        "region": region or "全部区域",
        "summary": {
            "resource_count": len(rows),
            "active_resource_count": len(active),
            "cell_count": len(cells),
            "covered_bandwidth_mhz": round(total_width, 6),
            "average_availability_pct": round((weighted / total_width * 100) if total_width else 0, 1),
            "type_counts": type_counts,
        },
        "cells": cells,
    }

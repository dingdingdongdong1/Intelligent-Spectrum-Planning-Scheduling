from __future__ import annotations

import json
from io import BytesIO

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlmodel import Session, select

from .database import get_session, init_db
from .models import AuditLog, FrequencyRule, PlanningRun, Project
from .schemas import (
    EquipmentLibraryItemResponse,
    ChatRequest,
    ChatResponse,
    PlanRequest,
    PlanResponse,
    ParametricTaskDemoRequest,
    ProjectCreate,
    ProjectRead,
    RulePayload,
    SpectrumRulePayload,
    TaskCapacityBatchRequest,
    TaskCapacityRiskClosureRequest,
    TaskObjectiveResponse,
    TaskReplanRequest,
    TaskSampleCatalogResponse,
    TaskScenarioResponse,
    ValidationResponse,
)
from .services.chat import parse_chat_instruction
from .services.comparison import compare_plans
from .services.equipment_planning import (
    build_task_export_xlsx,
    build_task_report,
    build_task_visualization_data,
    compare_task_plans,
    create_spectrum_rule,
    delete_spectrum_rule,
    db_equipment_groups_to_dicts,
    db_spectrum_rules_to_dicts,
    db_task_units_to_dicts,
    equipment_parameter_library,
    execute_capacity_batch_planning,
    execute_capacity_batch_risk_closure,
    generate_demo_scenario,
    generate_parametric_demo_scenario,
    latest_capacity_batch_closure_export_xlsx,
    latest_capacity_batch_export_xlsx,
    list_spectrum_rules,
    preview_task_replan,
    preview_task_strategy_trials,
    replan_task_project,
    replace_equipment_groups,
    replace_spectrum_rules,
    replace_task_units,
    run_task_planning,
    task_scenario_library,
    task_sample_catalog,
    task_planning_batch_performance_test,
    task_project_batch_performance_test,
    task_agent_capability_assessment,
    task_assignments_for_run,
    task_planning_performance_test,
    task_risks_for_run,
    task_versions_and_audit,
    update_spectrum_rule,
    validate_task_inputs,
)
from .services.task_catalog import TASK_OBJECTIVES
from .services.excel_io import (
    build_equipment_group_template,
    build_rule_template,
    build_spectrum_rule_template,
    build_station_template,
    build_task_unit_template,
    parse_equipment_group_excel,
    parse_rule_excel,
    parse_spectrum_rule_excel,
    parse_station_excel,
    parse_task_unit_excel,
)
from .services.llm import LLMClient
from .services.planning import (
    add_forbidden_frequencies,
    apply_priority_updates,
    assignments_for_run,
    db_rules_to_dicts,
    db_stations_to_dicts,
    latest_successful_run,
    replace_rules,
    replace_stations,
    risks_for_run,
    run_planning,
)
from .services.report import build_export_xlsx, generate_report
from .services.validation import validate_inputs
from .services.visualization import build_visualization_data


app = FastAPI(title="战场智能用频筹划平台", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:5175",
        "http://localhost:5175",
        "http://127.0.0.1:5176",
        "http://localhost:5176",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/phase-one-capabilities")
def phase_one_capabilities() -> dict:
    return {
        "phase": "第一阶段",
        "status": "ready",
        "goal": "形成任务输入、资源建模、自动规划、风险评估、动态重筹、方案对比和报告留痕的完整闭环。",
        "capabilities": [
            {
                "id": "task_unit_management",
                "name": "任务单元管理",
                "status": "ready",
                "evidence": ["任务样例生成", "任务单元 Excel 导入", "任务单元模板下载"],
                "endpoints": [
                    "POST /api/projects/{id}/generate-task-demo",
                    "POST /api/projects/{id}/upload-task-units",
                    "GET /api/templates/task-units.xlsx",
                ],
            },
            {
                "id": "equipment_group_management",
                "name": "装备组管理",
                "status": "ready",
                "evidence": ["装备组 Excel 导入", "装备参数库", "装备组模板下载"],
                "endpoints": [
                    "POST /api/projects/{id}/upload-equipment-groups",
                    "GET /api/equipment-library",
                    "GET /api/templates/equipment-groups.xlsx",
                ],
            },
            {
                "id": "spectrum_rule_management",
                "name": "频谱规则管理",
                "status": "ready",
                "evidence": ["频段池规则增删改查", "保护/禁用/可用规则", "规则模板下载"],
                "endpoints": [
                    "GET /api/projects/{id}/spectrum-rules",
                    "POST /api/projects/{id}/spectrum-rules",
                    "GET /api/templates/spectrum-rules.xlsx",
                ],
            },
            {
                "id": "automatic_planning",
                "name": "自动用频规划",
                "status": "ready",
                "evidence": ["多目标权重", "策略模板", "任务保障率输出"],
                "endpoints": ["POST /api/projects/{id}/task-plan", "GET /api/task-objectives"],
            },
            {
                "id": "interference_risk_assessment",
                "name": "干扰风险评估",
                "status": "ready",
                "evidence": ["同频/邻频风险", "瓶颈分析", "冲突理由排序"],
                "endpoints": ["GET /api/projects/{id}/task-visualization"],
            },
            {
                "id": "visual_overview",
                "name": "可视化总览",
                "status": "ready",
                "evidence": ["保障矩阵", "频段占用全景", "空间态势联动"],
                "endpoints": ["GET /api/projects/{id}/task-visualization"],
            },
            {
                "id": "dynamic_replanning",
                "name": "动态重规划",
                "status": "ready",
                "evidence": ["变更预览", "多策略试算", "执行重筹与效果对齐"],
                "endpoints": [
                    "POST /api/projects/{id}/task-replan-preview",
                    "POST /api/projects/{id}/task-strategy-trials",
                    "POST /api/projects/{id}/task-replan",
                ],
            },
            {
                "id": "multi_plan_comparison",
                "name": "多方案对比",
                "status": "ready",
                "evidence": ["多目标批量求解", "推荐方案", "决策表"],
                "endpoints": ["POST /api/projects/{id}/task-compare"],
            },
            {
                "id": "report_export",
                "name": "报表导出与留痕",
                "status": "ready",
                "evidence": ["HTML 报告", "Excel 导出", "版本审计"],
                "endpoints": [
                    "GET /api/projects/{id}/task-report",
                    "GET /api/projects/{id}/task-export.xlsx",
                    "GET /api/projects/{id}/task-versions",
                ],
            },
        ],
    }


@app.post("/api/projects", response_model=ProjectRead)
def create_project(payload: ProjectCreate, session: Session = Depends(get_session)) -> Project:
    project = Project(name=payload.name)
    session.add(project)
    session.commit()
    session.refresh(project)
    session.add(AuditLog(project_id=project.id, actor="user", action="create_project", detail=project.name))
    session.commit()
    return project


@app.get("/api/projects", response_model=list[ProjectRead])
def list_projects(session: Session = Depends(get_session)) -> list[Project]:
    return session.exec(select(Project).order_by(Project.id.desc())).all()


@app.get("/api/task-objectives", response_model=list[TaskObjectiveResponse])
def task_objectives() -> list[dict]:
    return TASK_OBJECTIVES


@app.get("/api/equipment-library", response_model=list[EquipmentLibraryItemResponse])
def equipment_library() -> list[dict]:
    return equipment_parameter_library()


@app.get("/api/task-scenarios", response_model=list[TaskScenarioResponse])
def task_scenarios() -> list[dict]:
    return task_scenario_library()


@app.get(
    "/api/task-sample-catalog",
    response_model=TaskSampleCatalogResponse,
    response_model_exclude_none=True,
)
def task_samples() -> dict:
    return task_sample_catalog()


@app.post("/api/task-performance-test")
def task_performance_test() -> dict:
    return task_planning_performance_test()


@app.post("/api/task-performance-batch")
def task_performance_batch() -> dict:
    return task_planning_batch_performance_test()


@app.post("/api/projects/{project_id}/upload-stations")
async def upload_stations(project_id: int, file: UploadFile = File(...), session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    parsed = parse_station_excel(await file.read())
    replace_stations(session, project_id, parsed.records)
    return {
        "count": len(parsed.records),
        "missing_columns": parsed.missing_columns,
        "extra_columns": parsed.extra_columns,
    }


@app.post("/api/projects/{project_id}/upload-rules")
async def upload_rules(project_id: int, file: UploadFile = File(...), session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    parsed = parse_rule_excel(await file.read())
    replace_rules(session, project_id, parsed.records)
    return {
        "count": len(parsed.records),
        "missing_columns": parsed.missing_columns,
        "extra_columns": parsed.extra_columns,
    }


@app.post("/api/projects/{project_id}/generate-task-demo")
def generate_task_demo(
    project_id: int,
    scenario: str = Query(default="baseline"),
    session: Session = Depends(get_session),
) -> dict:
    _require_project(session, project_id)
    return generate_demo_scenario(session, project_id, scenario)


@app.post("/api/projects/{project_id}/generate-parametric-task-demo")
def generate_parametric_task_demo(
    project_id: int,
    payload: ParametricTaskDemoRequest,
    session: Session = Depends(get_session),
) -> dict:
    _require_project(session, project_id)
    return generate_parametric_demo_scenario(session, project_id, payload.model_dump())


@app.post("/api/projects/{project_id}/upload-task-units")
async def upload_task_units(project_id: int, file: UploadFile = File(...), session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    parsed = parse_task_unit_excel(await file.read())
    replace_task_units(session, project_id, parsed.records)
    return {
        "count": len(parsed.records),
        "missing_columns": parsed.missing_columns,
        "extra_columns": parsed.extra_columns,
    }


@app.post("/api/projects/{project_id}/upload-equipment-groups")
async def upload_equipment_groups(project_id: int, file: UploadFile = File(...), session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    parsed = parse_equipment_group_excel(await file.read())
    replace_equipment_groups(session, project_id, parsed.records)
    return {
        "count": len(parsed.records),
        "missing_columns": parsed.missing_columns,
        "extra_columns": parsed.extra_columns,
    }


@app.post("/api/projects/{project_id}/upload-spectrum-rules")
async def upload_spectrum_rules(project_id: int, file: UploadFile = File(...), session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    parsed = parse_spectrum_rule_excel(await file.read())
    replace_spectrum_rules(session, project_id, parsed.records)
    return {
        "count": len(parsed.records),
        "missing_columns": parsed.missing_columns,
        "extra_columns": parsed.extra_columns,
    }


@app.get("/api/projects/{project_id}/task-data")
def task_data(project_id: int, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    return {
        "task_units": db_task_units_to_dicts(session, project_id),
        "equipment_groups": db_equipment_groups_to_dicts(session, project_id),
        "spectrum_rules": db_spectrum_rules_to_dicts(session, project_id),
    }


@app.get("/api/projects/{project_id}/spectrum-rules")
def task_spectrum_rules(project_id: int, session: Session = Depends(get_session)) -> list[dict]:
    _require_project(session, project_id)
    return list_spectrum_rules(session, project_id)


@app.post("/api/projects/{project_id}/spectrum-rules")
def task_spectrum_rule_create(project_id: int, payload: SpectrumRulePayload, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    return create_spectrum_rule(session, project_id, payload.model_dump())


@app.put("/api/projects/{project_id}/spectrum-rules/{row_id}")
def task_spectrum_rule_update(project_id: int, row_id: int, payload: SpectrumRulePayload, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    rule = update_spectrum_rule(session, project_id, row_id, payload.model_dump())
    if rule is None:
        raise HTTPException(status_code=404, detail="Spectrum rule not found")
    return rule


@app.delete("/api/projects/{project_id}/spectrum-rules/{row_id}")
def task_spectrum_rule_delete(project_id: int, row_id: int, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    if not delete_spectrum_rule(session, project_id, row_id):
        raise HTTPException(status_code=404, detail="Spectrum rule not found")
    return {"ok": True}


@app.get("/api/projects/{project_id}/rules")
def list_rules(project_id: int, session: Session = Depends(get_session)) -> list[dict]:
    _require_project(session, project_id)
    rules = session.exec(select(FrequencyRule).where(FrequencyRule.project_id == project_id).order_by(FrequencyRule.id)).all()
    return [rule.model_dump() for rule in rules]


@app.post("/api/projects/{project_id}/rules")
def create_rule(project_id: int, payload: RulePayload, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    data = payload.model_dump()
    rule = FrequencyRule(project_id=project_id, raw_json=json.dumps(data, ensure_ascii=False), **data)
    session.add(rule)
    session.commit()
    session.refresh(rule)
    session.add(AuditLog(project_id=project_id, action="create_rule", detail=json.dumps(rule.model_dump(), ensure_ascii=False, default=str)))
    session.commit()
    return rule.model_dump()


@app.put("/api/projects/{project_id}/rules/{rule_id}")
def update_rule(project_id: int, rule_id: int, payload: RulePayload, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    rule = session.get(FrequencyRule, rule_id)
    if not rule or rule.project_id != project_id:
        raise HTTPException(status_code=404, detail="Rule not found")
    data = payload.model_dump()
    for key, value in data.items():
        setattr(rule, key, value)
    rule.raw_json = json.dumps(data, ensure_ascii=False)
    session.add(rule)
    session.add(AuditLog(project_id=project_id, action="update_rule", detail=json.dumps(rule.model_dump(), ensure_ascii=False, default=str)))
    session.commit()
    session.refresh(rule)
    return rule.model_dump()


@app.delete("/api/projects/{project_id}/rules/{rule_id}")
def delete_rule(project_id: int, rule_id: int, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    rule = session.get(FrequencyRule, rule_id)
    if not rule or rule.project_id != project_id:
        raise HTTPException(status_code=404, detail="Rule not found")
    session.delete(rule)
    session.add(AuditLog(project_id=project_id, action="delete_rule", detail=str(rule_id)))
    session.commit()
    return {"ok": True}


@app.post("/api/projects/{project_id}/validate", response_model=ValidationResponse)
async def validate_project(project_id: int, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    result = validate_inputs(db_stations_to_dicts(session, project_id), db_rules_to_dicts(session, project_id))
    result["missing_questions"] = await LLMClient().explain_validation(result)
    session.add(AuditLog(project_id=project_id, action="validate", detail=json.dumps(result["summary"], ensure_ascii=False)))
    session.commit()
    return result


@app.post("/api/projects/{project_id}/plan", response_model=PlanResponse)
def plan_project(project_id: int, payload: PlanRequest, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    validation = validate_inputs(db_stations_to_dicts(session, project_id), db_rules_to_dicts(session, project_id))
    if not validation["ok"]:
        raise HTTPException(status_code=422, detail=validation)
    run = run_planning(session, project_id, payload.objective)
    return _run_response(run)


@app.post("/api/projects/{project_id}/compare")
def compare_project(project_id: int, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    validation = validate_inputs(db_stations_to_dicts(session, project_id), db_rules_to_dicts(session, project_id))
    if not validation["ok"]:
        raise HTTPException(status_code=422, detail=validation)
    result = compare_plans(session, project_id)
    session.add(AuditLog(project_id=project_id, action="compare_plans", detail=json.dumps(result.get("recommended_run_id"), ensure_ascii=False)))
    session.commit()
    return result


@app.post("/api/projects/{project_id}/validate-task")
def validate_task_project(project_id: int, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    result = validate_task_inputs(
        db_task_units_to_dicts(session, project_id),
        db_equipment_groups_to_dicts(session, project_id),
        db_spectrum_rules_to_dicts(session, project_id),
    )
    session.add(AuditLog(project_id=project_id, action="validate_task", detail=json.dumps(result["summary"], ensure_ascii=False)))
    session.commit()
    return result


@app.post("/api/projects/{project_id}/task-plan", response_model=PlanResponse)
def task_plan_project(project_id: int, payload: PlanRequest, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    validation = validate_task_inputs(
        db_task_units_to_dicts(session, project_id),
        db_equipment_groups_to_dicts(session, project_id),
        db_spectrum_rules_to_dicts(session, project_id),
    )
    if not validation["ok"]:
        raise HTTPException(status_code=422, detail=validation)
    run = run_task_planning(
        session,
        project_id,
        payload.objective,
        constraints={"weights": payload.constraint_weights, "strategy_profile": payload.strategy_profile},
    )
    return _run_response(run)


@app.post("/api/projects/{project_id}/task-compare")
def task_compare_project(project_id: int, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    validation = validate_task_inputs(
        db_task_units_to_dicts(session, project_id),
        db_equipment_groups_to_dicts(session, project_id),
        db_spectrum_rules_to_dicts(session, project_id),
    )
    if not validation["ok"]:
        raise HTTPException(status_code=422, detail=validation)
    result = compare_task_plans(session, project_id)
    session.add(AuditLog(project_id=project_id, action="task_compare", detail=json.dumps(result.get("recommended_run_id"), ensure_ascii=False)))
    session.commit()
    return result


@app.post("/api/projects/{project_id}/task-replan-preview")
def task_replan_preview(project_id: int, payload: TaskReplanRequest, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    return preview_task_replan(session, project_id, payload.model_dump())


@app.post("/api/projects/{project_id}/task-strategy-trials")
def task_strategy_trials(project_id: int, payload: TaskReplanRequest, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    validation = validate_task_inputs(
        db_task_units_to_dicts(session, project_id),
        db_equipment_groups_to_dicts(session, project_id),
        db_spectrum_rules_to_dicts(session, project_id),
    )
    if not validation["ok"]:
        raise HTTPException(status_code=422, detail=validation)
    return preview_task_strategy_trials(session, project_id, payload.model_dump())


@app.post("/api/projects/{project_id}/task-replan", response_model=ChatResponse)
def task_replan_project(project_id: int, payload: TaskReplanRequest, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    validation = validate_task_inputs(
        db_task_units_to_dicts(session, project_id),
        db_equipment_groups_to_dicts(session, project_id),
        db_spectrum_rules_to_dicts(session, project_id),
    )
    if not validation["ok"]:
        raise HTTPException(status_code=422, detail=validation)
    return replan_task_project(session, project_id, payload.model_dump())


@app.post("/api/projects/{project_id}/task-performance-batch")
def task_project_performance_batch(project_id: int, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    return task_project_batch_performance_test(session, project_id)


@app.post("/api/projects/{project_id}/task-capacity-batches")
def task_capacity_batches(project_id: int, payload: TaskCapacityBatchRequest, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    return execute_capacity_batch_planning(session, project_id, payload.model_dump())


@app.post("/api/projects/{project_id}/task-capacity-risk-closure")
def task_capacity_risk_closure(project_id: int, payload: TaskCapacityRiskClosureRequest, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    return execute_capacity_batch_risk_closure(session, project_id, payload.model_dump())


@app.get("/api/projects/{project_id}/task-versions")
def task_versions(project_id: int, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    return task_versions_and_audit(session, project_id)


@app.get("/api/projects/{project_id}/task-agent-assessment")
def task_agent_assessment(
    project_id: int,
    run_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict:
    _require_project(session, project_id)
    return task_agent_capability_assessment(session, project_id, run_id)


@app.get("/api/projects/{project_id}/task-visualization")
def task_visualization(
    project_id: int,
    run_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict:
    _require_project(session, project_id)
    run = _resolve_task_run(session, project_id, run_id)
    assignments = task_assignments_for_run(session, project_id, run.id)
    risks = task_risks_for_run(session, project_id, run.id)
    summary = json.loads(run.summary_json or "{}")
    return build_task_visualization_data(
        task_units=db_task_units_to_dicts(session, project_id),
        equipment_groups=db_equipment_groups_to_dicts(session, project_id),
        spectrum_rules=db_spectrum_rules_to_dicts(session, project_id),
        assignments=assignments,
        risk_items=risks,
        summary=summary,
    )


@app.post("/api/projects/{project_id}/chat", response_model=ChatResponse)
async def chat(project_id: int, payload: ChatRequest, session: Session = Depends(get_session)) -> dict:
    _require_project(session, project_id)
    instruction = parse_chat_instruction(payload.message)
    forbidden_count = add_forbidden_frequencies(session, project_id, instruction["forbidden_frequencies"])
    priority_count = apply_priority_updates(session, project_id, instruction["priority_updates"])
    objective = instruction["objective"] or payload.objective

    validation = validate_inputs(db_stations_to_dicts(session, project_id), db_rules_to_dicts(session, project_id))
    if not validation["ok"]:
        questions = await LLMClient().explain_validation(validation)
        return {
            "reply": "当前数据还不能重新规划：" + "；".join(questions[:5]),
            "run_id": None,
            "summary": validation["summary"],
        }

    run = run_planning(session, project_id, objective)
    assignments = assignments_for_run(session, project_id, run.id) if run.status == "success" else []
    risks = risks_for_run(session, project_id, run.id) if run.status == "success" else []
    summary = json.loads(run.summary_json or "{}")
    explanation = await LLMClient().explain_plan(summary, risks)
    changed_text = f"已应用：新增禁用频点规则 {forbidden_count} 条，调整优先级 {priority_count} 个台站。"
    return {"reply": f"{changed_text}{explanation}", "run_id": run.id, "summary": {**summary, **_run_response(run)["summary"]}}


@app.get("/api/projects/{project_id}/visualization")
def visualization(
    project_id: int,
    run_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict:
    _require_project(session, project_id)
    run = _resolve_run(session, project_id, run_id)
    return build_visualization_data(
        stations=db_stations_to_dicts(session, project_id),
        rules=db_rules_to_dicts(session, project_id),
        assignments=assignments_for_run(session, project_id, run.id),
        risks=risks_for_run(session, project_id, run.id),
    )


@app.get("/api/projects/{project_id}/report", response_class=HTMLResponse)
def report(
    project_id: int,
    run_id: int | None = Query(default=None, alias="run"),
    session: Session = Depends(get_session),
) -> str:
    project = _require_project(session, project_id)
    run = _resolve_run(session, project_id, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="还没有成功的规划运行")
    assignments = assignments_for_run(session, project_id, run.id)
    risks = risks_for_run(session, project_id, run.id)
    return generate_report(
        project=project.model_dump(),
        run=run.model_dump(),
        assignments=assignments,
        risk_items=risks,
        summary=json.loads(run.summary_json or "{}"),
    )


@app.get("/api/projects/{project_id}/task-report", response_class=HTMLResponse)
def task_report(
    project_id: int,
    run_id: int | None = Query(default=None, alias="run"),
    session: Session = Depends(get_session),
) -> str:
    project = _require_project(session, project_id)
    run = _resolve_task_run(session, project_id, run_id)
    assignments = task_assignments_for_run(session, project_id, run.id)
    risks = task_risks_for_run(session, project_id, run.id)
    summary = json.loads(run.summary_json or "{}")
    visualization_data = build_task_visualization_data(
        task_units=db_task_units_to_dicts(session, project_id),
        equipment_groups=db_equipment_groups_to_dicts(session, project_id),
        spectrum_rules=db_spectrum_rules_to_dicts(session, project_id),
        assignments=assignments,
        risk_items=risks,
        summary=summary,
    )
    return build_task_report(
        project=project.model_dump(),
        run=run.model_dump(),
        assignments=assignments,
        risks=risks,
        summary=summary,
        visualization=visualization_data,
    )


@app.get("/api/projects/{project_id}/export.xlsx")
def export(
    project_id: int,
    run_id: int | None = Query(default=None, alias="run"),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    _require_project(session, project_id)
    run = _resolve_run(session, project_id, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="还没有成功的规划运行")
    content = build_export_xlsx(
        assignments=assignments_for_run(session, project_id, run.id),
        risk_items=risks_for_run(session, project_id, run.id),
        summary=json.loads(run.summary_json or "{}"),
    )
    return _xlsx_response(content, f"planning_result_project_{project_id}_run_{run.id}.xlsx")


@app.get("/api/projects/{project_id}/task-export.xlsx")
def task_export(
    project_id: int,
    run_id: int | None = Query(default=None, alias="run"),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    _require_project(session, project_id)
    run = _resolve_task_run(session, project_id, run_id)
    assignments = task_assignments_for_run(session, project_id, run.id)
    risks = task_risks_for_run(session, project_id, run.id)
    summary = json.loads(run.summary_json or "{}")
    visualization_data = build_task_visualization_data(
        task_units=db_task_units_to_dicts(session, project_id),
        equipment_groups=db_equipment_groups_to_dicts(session, project_id),
        spectrum_rules=db_spectrum_rules_to_dicts(session, project_id),
        assignments=assignments,
        risk_items=risks,
        summary=summary,
    )
    content = build_task_export_xlsx(assignments=assignments, risks=risks, summary=summary, visualization=visualization_data)
    return _xlsx_response(content, f"task_planning_project_{project_id}_run_{run.id}.xlsx")


@app.get("/api/projects/{project_id}/task-capacity-master-export.xlsx")
def task_capacity_master_export(project_id: int, session: Session = Depends(get_session)) -> StreamingResponse:
    _require_project(session, project_id)
    try:
        content, audit_id = latest_capacity_batch_export_xlsx(session, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _xlsx_response(content, f"task_capacity_master_project_{project_id}_audit_{audit_id}.xlsx")


@app.get("/api/projects/{project_id}/task-capacity-risk-closure-export.xlsx")
def task_capacity_risk_closure_export(project_id: int, session: Session = Depends(get_session)) -> StreamingResponse:
    _require_project(session, project_id)
    try:
        content, audit_id = latest_capacity_batch_closure_export_xlsx(session, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _xlsx_response(content, f"task_capacity_risk_closure_project_{project_id}_audit_{audit_id}.xlsx")


@app.get("/api/templates/stations.xlsx")
def station_template() -> StreamingResponse:
    return _xlsx_response(build_station_template(), "stations_template.xlsx")


@app.get("/api/templates/rules.xlsx")
def rule_template() -> StreamingResponse:
    return _xlsx_response(build_rule_template(), "rules_template.xlsx")


@app.get("/api/templates/task-units.xlsx")
def task_unit_template() -> StreamingResponse:
    return _xlsx_response(build_task_unit_template(), "task_units_template.xlsx")


@app.get("/api/templates/equipment-groups.xlsx")
def equipment_group_template() -> StreamingResponse:
    return _xlsx_response(build_equipment_group_template(), "equipment_groups_template.xlsx")


@app.get("/api/templates/spectrum-rules.xlsx")
def spectrum_rule_template() -> StreamingResponse:
    return _xlsx_response(build_spectrum_rule_template(), "spectrum_rules_template.xlsx")


def _require_project(session: Session, project_id: int) -> Project:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def _resolve_run(session: Session, project_id: int, run_id: int | None) -> PlanningRun:
    if run_id is not None:
        run = session.get(PlanningRun, run_id)
        if run and run.project_id == project_id and run.status == "success":
            return run
        raise HTTPException(status_code=404, detail="Planning run not found or not successful")
    run = latest_successful_run(session, project_id)
    if not run:
        raise HTTPException(status_code=404, detail="No successful planning run yet")
    return run


def _resolve_task_run(session: Session, project_id: int, run_id: int | None) -> PlanningRun:
    task_objective_names = [item["objective"] for item in TASK_OBJECTIVES]
    if run_id is not None:
        run = session.get(PlanningRun, run_id)
        if run and run.project_id == project_id and run.status == "success" and run.objective in task_objective_names:
            return run
        raise HTTPException(status_code=404, detail="Task planning run not found or not successful")
    run = session.exec(
        select(PlanningRun)
        .where(
            PlanningRun.project_id == project_id,
            PlanningRun.status == "success",
            PlanningRun.objective.in_(task_objective_names),
        )
        .order_by(PlanningRun.id.desc())
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="No successful task planning run yet")
    return run


def _run_response(run: PlanningRun) -> dict:
    return {
        "run_id": run.id,
        "status": run.status,
        "message": run.message,
        "summary": json.loads(run.summary_json or "{}"),
    }


def _xlsx_response(content: bytes, filename: str) -> StreamingResponse:
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )

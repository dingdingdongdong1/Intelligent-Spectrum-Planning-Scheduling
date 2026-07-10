from typing import Any

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = "未命名战场用频筹划项目"


class ProjectRead(BaseModel):
    id: int
    name: str
    status: str


class TaskObjectiveResponse(BaseModel):
    objective: str
    label: str
    description: str


class EquipmentLibraryItemResponse(BaseModel):
    equipment_type: str
    default_assignment_mode: str
    reasonable_bandwidth_khz: str
    reasonable_power_w: str
    typical_mobility: str
    planning_notes: str


class TaskScenarioResponse(BaseModel):
    key: str
    name: str
    description: str


class TaskSamplePresetResponse(BaseModel):
    key: str
    name: str
    scenario: str
    task_unit_count: int
    density_multiplier: float
    spectrum_pressure: str
    description: str


class TaskUnitProfileResponse(BaseModel):
    code: str
    name: str
    unit_type: str
    spectrum_relation: str
    preferred_band_groups: str
    default_priority: int
    min_satisfaction_ratio: float
    equipment_group_count: int
    equipment_types: list[str]


class BatchPerformanceScaleResponse(BaseModel):
    key: str
    name: str
    scenario: str | None = None
    prefix: str | None = None
    unit_count: int
    density_multiplier: float


class PlanningWeightsResponse(BaseModel):
    task: int
    risk: int
    spectrum: int
    priority: int
    switching: int
    reuse: int


class PlanningWeightTemplateResponse(BaseModel):
    key: str
    name: str
    weights: PlanningWeightsResponse
    description: str


class ParametricSampleDefaultsResponse(BaseModel):
    unit_count: int
    density_multiplier: float
    radar_ratio: int
    uav_ratio: int
    protection_density: int
    forbidden_density: int


class TaskSampleCatalogResponse(BaseModel):
    presets: list[TaskSamplePresetResponse]
    task_unit_profiles: list[TaskUnitProfileResponse]
    equipment_types: list[EquipmentLibraryItemResponse]
    batch_scales: list[BatchPerformanceScaleResponse]
    weight_templates: list[PlanningWeightTemplateResponse]
    parametric_defaults: ParametricSampleDefaultsResponse
    objective_count: int


class ValidationResponse(BaseModel):
    ok: bool
    errors: list[str]
    warnings: list[str]
    missing_questions: list[str]
    summary: dict


class PlanRequest(BaseModel):
    objective: str = "minimize_interference"
    constraint_weights: dict[str, float] = Field(default_factory=dict)
    strategy_profile: str = "balanced"


class PlanResponse(BaseModel):
    run_id: int
    status: str
    message: str
    summary: dict


class ChatRequest(BaseModel):
    message: str
    objective: str = "minimize_interference"


class ChatResponse(BaseModel):
    reply: str
    run_id: int | None = None
    summary: dict = {}
    replan_effect: dict | None = None


class FrequencyRangePayload(BaseModel):
    band_group: str | None = None
    start_mhz: float
    end_mhz: float
    reason: str = "用户临时禁用"


class PriorityUpdatePayload(BaseModel):
    target: str
    priority: int


class SatisfactionUpdatePayload(BaseModel):
    task_unit_id: str
    min_satisfaction_ratio: float


class TaskReplanRequest(BaseModel):
    message: str = ""
    objective: str = "task_assurance"
    base_run_id: int | None = None
    reuse_strategy_from_run_id: int | None = None
    locked_equipment_group_ids: list[str] = Field(default_factory=list)
    locked_task_unit_ids: list[str] = Field(default_factory=list)
    available_ranges: list[FrequencyRangePayload] = Field(default_factory=list)
    forbidden_ranges: list[FrequencyRangePayload] = Field(default_factory=list)
    priority_updates: list[PriorityUpdatePayload] = Field(default_factory=list)
    satisfaction_updates: list[SatisfactionUpdatePayload] = Field(default_factory=list)
    avoid_band_groups: list[str] = Field(default_factory=list)
    forced_band_groups: dict[str, str] = Field(default_factory=dict)
    required_full_targets: list[str] = Field(default_factory=list)
    allow_low_priority_degrade: bool = True
    constraint_weights: dict[str, float] = Field(default_factory=dict)
    strategy_profile: str = "balanced"
    trial_context: dict[str, Any] = Field(default_factory=dict)


class TaskCapacityBatchRequest(BaseModel):
    base_run_id: int | None = None
    objective: str | None = None
    batch_ids: list[str] = Field(default_factory=list)
    constraint_weights: dict[str, float] = Field(default_factory=dict)
    strategy_profile: str | None = None


class TaskCapacityRiskClosureRequest(BaseModel):
    objective: str | None = None
    constraint_weights: dict[str, float] = Field(default_factory=dict)
    strategy_profile: str | None = None


class ParametricTaskDemoRequest(BaseModel):
    unit_count: int = 24
    density_multiplier: float = 1.8
    radar_ratio: int = 18
    uav_ratio: int = 18
    protection_density: int = 2
    forbidden_density: int = 2


class SpectrumRulePayload(BaseModel):
    rule_id: str = ""
    rule_type: str = "可用"
    band_group: str
    spectrum_relation: str = "可复用"
    start_mhz: float
    end_mhz: float
    channel_step_khz: float = 25
    max_bandwidth_khz: float = 25
    max_power_w: float = 1
    guard_band_khz: float = 0
    compatible_unit_types: str = ""
    compatible_equipment_types: str = ""
    reason: str = ""
    source: str = "USER_UI"
    severity: str = "中"


class RulePayload(BaseModel):
    band_group: str
    service_type: str
    region: str = "default"
    start_mhz: float
    end_mhz: float
    channel_step_khz: float
    max_bandwidth_khz: float
    max_power_w: float
    guard_band_khz: float = 0
    min_spacing_khz: float = 0
    forbidden_frequency_mhz: float | None = None
    protection_distance_km: float = 0

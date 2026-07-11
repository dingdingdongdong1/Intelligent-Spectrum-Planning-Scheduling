from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = "未命名战场用频筹划项目"


class ProjectRead(BaseModel):
    id: int
    name: str
    status: str
    created_at: datetime
    updated_at: datetime


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


class TaskIntentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


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


class EquipmentEventPayload(BaseModel):
    action: str
    equipment_group_id: str
    template_group_id: str | None = None
    task_unit_id: str | None = None
    equipment_type: str | None = None
    count: int = Field(default=1, ge=1)
    reason: str = "动态装备事件"


class UnitPositionUpdatePayload(BaseModel):
    task_unit_id: str
    area_center_lat: float = Field(ge=-90, le=90)
    area_center_lon: float = Field(ge=-180, le=180)
    area_radius_km: float = Field(default=0, ge=0)
    reason: str = "任务单元机动"


class InterferenceSourceEventPayload(BaseModel):
    source_id: str
    start_mhz: float = Field(ge=0)
    end_mhz: float = Field(gt=0)
    max_power_w: float = Field(default=1, ge=0)
    center_lat: float | None = Field(default=None, ge=-90, le=90)
    center_lon: float | None = Field(default=None, ge=-180, le=180)
    coverage_radius_km: float = Field(default=0, ge=0)
    region: str = "全域"
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    reason: str = "新增动态干扰源"


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
    equipment_events: list[EquipmentEventPayload] = Field(default_factory=list)
    unit_position_updates: list[UnitPositionUpdatePayload] = Field(default_factory=list)
    interference_sources: list[InterferenceSourceEventPayload] = Field(default_factory=list)
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


class SpectrumResourcePayload(BaseModel):
    resource_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    resource_type: str
    purpose: str = ""
    region: str = "全域"
    start_mhz: float = Field(ge=0)
    end_mhz: float = Field(gt=0)
    channel_step_khz: float = Field(default=25, gt=0)
    max_bandwidth_khz: float = Field(default=25, gt=0)
    max_power_w: float = Field(default=1, ge=0)
    guard_band_khz: float = Field(default=0, ge=0)
    center_lat: float | None = Field(default=None, ge=-90, le=90)
    center_lon: float | None = Field(default=None, ge=-180, le=180)
    coverage_radius_km: float = Field(default=0, ge=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    compatible_equipment_types: str = ""
    status: str = "启用"
    source: str = "USER_UI"
    notes: str = ""


class MissionTaskPayload(BaseModel):
    mission_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    mission_type: str = ""
    description: str = ""
    priority: int = Field(default=1, ge=1)
    required_assurance: float = Field(default=1.0, ge=0, le=1)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    region_name: str = ""
    center_lat: float | None = Field(default=None, ge=-90, le=90)
    center_lon: float | None = Field(default=None, ge=-180, le=180)
    area_radius_km: float = Field(default=0, ge=0)
    mobility_range_km: float = Field(default=0, ge=0)
    commander_intent: str = ""
    status: str = "draft"


class TaskPhasePayload(BaseModel):
    phase_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    sequence: int = Field(default=0, ge=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: str = "draft"
    area_center_lat: float | None = Field(default=None, ge=-90, le=90)
    area_center_lon: float | None = Field(default=None, ge=-180, le=180)
    area_radius_km: float = Field(default=0, ge=0)
    notes: str = ""


class TaskUnitPayload(BaseModel):
    task_unit_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    unit_type: str = Field(min_length=1)
    area_center_lat: float | None = Field(default=None, ge=-90, le=90)
    area_center_lon: float | None = Field(default=None, ge=-180, le=180)
    area_radius_km: float = Field(default=0, ge=0)
    priority: int = Field(default=1, ge=1)
    spectrum_relation: str = "exclusive"
    preferred_band_groups: str = ""
    min_satisfaction_ratio: float = Field(default=1.0, gt=0, le=1)


class EquipmentGroupPayload(BaseModel):
    equipment_group_id: str = Field(min_length=1)
    task_unit_id: str = Field(min_length=1)
    equipment_type: str = Field(min_length=1)
    count: int = Field(default=1, gt=0)
    tx_rx_role: str = "duplex"
    mobility: str = "fixed"
    bandwidth_khz: float = Field(default=25, gt=0)
    tx_power_w: float = Field(default=1, ge=0)
    antenna_gain_dbi: float = 0
    antenna_height_m: float = Field(default=1, ge=0)
    receiver_sensitivity_dbm: float = -100
    modulation: str = ""
    duplex_mode: str = "simplex"
    required_channels: int = Field(default=1, gt=0)
    assignment_mode: str = "discrete_channels"
    preferred_band_group: str = ""
    priority: int = Field(default=1, ge=1)
    protection_distance_km: float = Field(default=0, ge=0)
    min_spacing_khz: float = Field(default=0, ge=0)
    guard_band_khz: float = Field(default=0, ge=0)


class TaskLinkPayload(BaseModel):
    link_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    link_type: str = "communication"
    source_task_unit_id: str | None = None
    target_task_unit_id: str | None = None
    source_equipment_group_id: str | None = None
    target_equipment_group_id: str | None = None
    direction: str = "bidirectional"
    priority: int = Field(default=1, ge=1)
    required_availability: float = Field(default=1.0, ge=0, le=1)
    bandwidth_khz: float = Field(default=25, gt=0)
    required_channels: int = Field(default=1, gt=0)
    primary_band_group: str = ""
    backup_band_group: str = ""
    active_phase_ids: list[str] = Field(default_factory=list)
    notes: str = ""


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

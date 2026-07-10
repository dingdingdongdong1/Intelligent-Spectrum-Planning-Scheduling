from typing import Any

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = "未命名战场用频筹划项目"


class ProjectRead(BaseModel):
    id: int
    name: str
    status: str


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

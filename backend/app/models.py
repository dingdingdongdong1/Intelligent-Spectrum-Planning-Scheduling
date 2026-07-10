from datetime import datetime

from sqlmodel import Field, SQLModel


class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    status: str = "created"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Station(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    station_id: str = Field(index=True)
    name: str
    latitude: float | None = None
    longitude: float | None = None
    service_type: str | None = None
    bandwidth_khz: float | None = None
    tx_power_w: float | None = None
    antenna_height_m: float | None = None
    antenna_gain_dbi: float | None = None
    available_band_group: str | None = None
    protection_distance_km: float | None = None
    priority: int = 1
    existing_frequency_mhz: float | None = None
    forbidden_frequencies_mhz: str | None = None
    raw_json: str


class FrequencyRule(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    band_group: str = Field(index=True)
    service_type: str = Field(index=True)
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
    raw_json: str


class PlanningRun(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    objective: str = "minimize_interference"
    status: str = "created"
    message: str = ""
    elapsed_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    summary_json: str = "{}"


class Assignment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    run_id: int = Field(index=True)
    station_id: str = Field(index=True)
    assigned_frequency_mhz: float | None = None
    alternative_frequencies_mhz: str = ""
    risk_score: float = 0
    risk_level: str = "低"
    notes: str = ""


class RiskItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    run_id: int = Field(index=True)
    station_a: str
    station_b: str | None = None
    frequency_a_mhz: float | None = None
    frequency_b_mhz: float | None = None
    risk_type: str
    severity: str
    score: float
    reason: str


class AuditLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    run_id: int | None = None
    actor: str = "system"
    action: str
    detail: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskUnit(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    task_unit_id: str = Field(index=True)
    name: str
    unit_type: str = Field(index=True)
    area_center_lat: float | None = None
    area_center_lon: float | None = None
    area_radius_km: float = 0
    priority: int = 1
    spectrum_relation: str = "独占"
    preferred_band_groups: str = ""
    min_satisfaction_ratio: float = 1.0
    raw_json: str


class EquipmentGroup(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    equipment_group_id: str = Field(index=True)
    task_unit_id: str = Field(index=True)
    equipment_type: str = Field(index=True)
    count: int = 1
    tx_rx_role: str = "双工"
    mobility: str = "固定"
    bandwidth_khz: float = 25
    tx_power_w: float = 1
    antenna_gain_dbi: float = 0
    antenna_height_m: float = 1
    receiver_sensitivity_dbm: float = -100
    modulation: str = ""
    duplex_mode: str = "单工"
    required_channels: int = 1
    assignment_mode: str = "离散信道"
    preferred_band_group: str = ""
    priority: int = 1
    protection_distance_km: float = 0
    min_spacing_khz: float = 0
    guard_band_khz: float = 0
    raw_json: str


class SpectrumRule(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    rule_id: str = Field(index=True)
    rule_type: str = Field(index=True)
    band_group: str = Field(index=True)
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
    source: str = ""
    severity: str = "中"
    raw_json: str


class EquipmentAssignment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    run_id: int = Field(index=True)
    task_unit_id: str = Field(index=True)
    equipment_group_id: str = Field(index=True)
    equipment_type: str
    assignment_mode: str
    band_group: str | None = None
    assigned_resource: str = ""
    requested_count: int = 0
    satisfied_count: int = 0
    requested_channels: int = 0
    assigned_channels: int = 0
    satisfaction_ratio: float = 0
    status: str = "未满足"
    risk_score: float = 0
    risk_level: str = "低"
    reason: str = ""
    decision_notes: str = ""


class TaskRiskItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    run_id: int = Field(index=True)
    risk_type: str
    severity: str
    task_unit_a: str | None = None
    equipment_group_a: str | None = None
    task_unit_b: str | None = None
    equipment_group_b: str | None = None
    resource_a: str | None = None
    resource_b: str | None = None
    score: float = 0
    reason: str = ""

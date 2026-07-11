const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000';

export type Project = {
  id: number;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type TaskProjectData = {
  mission: MissionTaskRecord | null;
  phases: TaskPhaseRecord[];
  links: TaskLinkRecord[];
  task_units: TaskUnitRecord[];
  equipment_groups: EquipmentGroupRecord[];
  spectrum_rules: TaskSpectrumRuleRecord[];
};

export type SpectrumResourcePayload = {
  resource_id: string;
  name: string;
  resource_type: string;
  purpose: string;
  region: string;
  start_mhz: number;
  end_mhz: number;
  channel_step_khz: number;
  max_bandwidth_khz: number;
  max_power_w: number;
  guard_band_khz: number;
  center_lat: number | null;
  center_lon: number | null;
  coverage_radius_km: number;
  starts_at: string | null;
  ends_at: string | null;
  compatible_equipment_types: string;
  status: string;
  source: string;
  notes: string;
};

export type SpectrumResourceRecord = SpectrumResourcePayload & { id: number; project_id: number };

export type SpectrumResourceHeatmap = {
  at: string;
  region: string;
  summary: {
    resource_count: number;
    active_resource_count: number;
    cell_count: number;
    covered_bandwidth_mhz: number;
    average_availability_pct: number;
    type_counts: Record<string, number>;
  };
  cells: Array<{
    start_mhz: number;
    end_mhz: number;
    width_mhz: number;
    resource_type: string;
    availability_score: number;
    availability_pct: number;
    region: string;
    purpose: string;
    active_resource_ids: string[];
  }>;
};

export type MissionTaskPayload = {
  mission_id: string;
  name: string;
  mission_type: string;
  description: string;
  priority: number;
  required_assurance: number;
  starts_at: string | null;
  ends_at: string | null;
  region_name: string;
  center_lat: number | null;
  center_lon: number | null;
  area_radius_km: number;
  mobility_range_km: number;
  commander_intent: string;
  status: string;
};

export type MissionTaskRecord = MissionTaskPayload & { id: number; project_id: number };

export type TaskPhasePayload = {
  phase_id: string;
  name: string;
  sequence: number;
  starts_at: string | null;
  ends_at: string | null;
  status: string;
  area_center_lat: number | null;
  area_center_lon: number | null;
  area_radius_km: number;
  notes: string;
};

export type TaskPhaseRecord = TaskPhasePayload & { id: number; project_id: number };

export type TaskUnitPayload = {
  task_unit_id: string;
  name: string;
  unit_type: string;
  area_center_lat: number | null;
  area_center_lon: number | null;
  area_radius_km: number;
  priority: number;
  spectrum_relation: string;
  preferred_band_groups: string;
  min_satisfaction_ratio: number;
};

export type TaskUnitRecord = TaskUnitPayload & { id: number; project_id: number; raw_json?: string };

export type EquipmentGroupPayload = {
  equipment_group_id: string;
  task_unit_id: string;
  equipment_type: string;
  count: number;
  tx_rx_role: string;
  mobility: string;
  bandwidth_khz: number;
  tx_power_w: number;
  antenna_gain_dbi: number;
  antenna_height_m: number;
  receiver_sensitivity_dbm: number;
  modulation: string;
  duplex_mode: string;
  required_channels: number;
  assignment_mode: string;
  preferred_band_group: string;
  priority: number;
  protection_distance_km: number;
  min_spacing_khz: number;
  guard_band_khz: number;
};

export type EquipmentGroupRecord = EquipmentGroupPayload & { id: number; project_id: number; raw_json?: string };

export type TaskLinkPayload = {
  link_id: string;
  name: string;
  link_type: string;
  source_task_unit_id: string | null;
  target_task_unit_id: string | null;
  source_equipment_group_id: string | null;
  target_equipment_group_id: string | null;
  direction: string;
  priority: number;
  required_availability: number;
  bandwidth_khz: number;
  required_channels: number;
  primary_band_group: string;
  backup_band_group: string;
  active_phase_ids: string[];
  notes: string;
};

export type TaskLinkRecord = TaskLinkPayload & { id: number; project_id: number };

export type ValidationResult = {
  ok: boolean;
  errors: string[];
  warnings: string[];
  missing_questions: string[];
  summary: Record<string, unknown>;
};

export type PlanResult = {
  run_id: number;
  status: string;
  message: string;
  summary: Record<string, unknown>;
};

export type ReplanEffect = {
  base_run_id: number;
  current_run_id: number;
  base_objective?: string | null;
  current_objective?: string | null;
  base_effective_objective?: string | null;
  current_effective_objective?: string | null;
  base_strategy_profile?: string | null;
  current_strategy_profile?: string | null;
  status: string;
  status_label: string;
  summary: string;
  deltas: Record<string, number>;
  assignment_delta: {
    changed_assignment_count: number;
    improved_group_count: number;
    worsened_group_count: number;
    top_changes: Array<{
      equipment_group_id: string;
      before_status: string;
      after_status: string;
      ratio_delta: number;
      resource_changed: boolean;
    }>;
  };
  added_ranges: Array<{ band_group?: string; start_mhz: number; end_mhz: number; reason?: string }>;
  added_range_usage: Array<{
    band_group: string;
    start_mhz: number;
    end_mhz: number;
    width_mhz: number;
    used_width_mhz: number;
    used_assignment_count: number;
  }>;
  trial_context?: {
    trial_id?: string;
    label?: string;
    objective?: string;
    objective_label?: string;
    strategy_profile?: string;
    constraint_variant?: string;
    constraint_label?: string;
    decision?: string;
    reason?: string;
    tradeoff?: string;
    recommendation_score?: number;
    expected_metrics?: Record<string, number>;
    expected_deltas?: Record<string, number>;
    constraint_changes?: string[];
  };
  prediction_alignment?: {
    matched_count: number;
    total_count: number;
    summary: string;
    rows: Array<{
      key: string;
      label: string;
      expected_delta: number;
      actual_delta: number;
      direction_matched: boolean;
    }>;
  };
  reasons: string[];
  recommendation: string;
};

export type ChatResult = {
  reply: string;
  run_id: number | null;
  summary: Record<string, unknown>;
  replan_effect?: ReplanEffect | null;
};

export type VisualizationStation = {
  station_id: string;
  name: string;
  latitude: number | null;
  longitude: number | null;
  service_type: string | null;
  band_group: string | null;
  priority: number;
  frequency_mhz: number | null;
  risk_score: number;
  risk_level: string;
};

export type VisualizationRiskLink = {
  station_a: string;
  station_b: string;
  frequency_a_mhz: number | null;
  frequency_b_mhz: number | null;
  risk_type: string;
  severity: string;
  score: number;
  reason: string;
};

export type VisualizationSpectrumBand = {
  band_group: string;
  service_type: string;
  start_mhz: number | null;
  end_mhz: number | null;
  candidate_channel_count: number;
  used_channel_count: number;
  utilization_pct: number;
  assignments: Array<{
    station_id: string;
    frequency_mhz: number;
    risk_level: string;
  }>;
};

export type VisualizationData = {
  summary: Record<string, unknown>;
  stations: VisualizationStation[];
  risk_links: VisualizationRiskLink[];
  spectrum: VisualizationSpectrumBand[];
  risk_distribution: Array<{ level: string; count: number }>;
  station_risk_distribution: Array<{ level: string; count: number }>;
  service_distribution: Array<{ service_type: string; count: number }>;
};

export type ComparisonPlan = {
  run_id: number;
  objective: string;
  label: string;
  description: string;
  status: string;
  message: string;
  recommended: boolean;
  station_count: number;
  assigned_count: number;
  used_frequency_count: number;
  risk_item_count: number;
  high_risk_count: number;
  medium_risk_count: number;
  average_station_risk: number;
  max_station_risk: number;
  change_count: number;
  objective_value: number | null;
  elapsed_ms: number;
};

export type ComparisonResult = {
  plans: ComparisonPlan[];
  recommended_run_id: number | null;
  objectives: Array<{ objective: string; label: string; description: string }>;
};

export type RuleRecord = {
  id: number;
  project_id: number;
  band_group: string;
  service_type: string;
  region: string;
  start_mhz: number;
  end_mhz: number;
  channel_step_khz: number;
  max_bandwidth_khz: number;
  max_power_w: number;
  guard_band_khz: number;
  min_spacing_khz: number;
  forbidden_frequency_mhz: number | null;
  protection_distance_km: number;
};

export type RulePayload = Omit<RuleRecord, 'id' | 'project_id'>;

export type TaskObjective = {
  objective: string;
  label: string;
  description: string;
};

export type TaskScenario = {
  key: string;
  name: string;
  description: string;
};

export type TaskValidationResult = {
  ok: boolean;
  errors: string[];
  warnings: string[];
  summary: Record<string, unknown>;
};

export type TaskComparisonPlan = {
  run_id: number;
  objective: string;
  label: string;
  description: string;
  status: string;
  message: string;
  task_satisfaction_avg: number;
  full_group_count: number;
  partial_group_count: number;
  unsatisfied_group_count: number;
  used_bandwidth_mhz: number;
  risk_item_count: number;
  high_risk_count: number;
  objective_score: number;
  weighted_score?: number;
  weighted_components?: Array<{ key: string; score: number; weight: number; contribution: number }>;
  score_explanation?: ScoreExplanation;
  recommendation_reason?: string;
  recommended: boolean;
  elapsed_ms: number;
};

export type TaskDecisionRow = {
  profile: string;
  plan_label: string;
  decision: string;
  main_gain: string;
  tradeoff: string;
  suitable_when: string;
  risk: string;
};

export type TaskComparisonResult = {
  plans: TaskComparisonPlan[];
  recommended_run_id: number | null;
  objectives: TaskObjective[];
  decision_table?: TaskDecisionRow[];
  decision_weights?: Partial<ConstraintWeights>;
};

export type TaskUnitView = {
  task_unit_id: string;
  name: string;
  unit_type: string;
  area_center_lat: number | null;
  area_center_lon: number | null;
  area_radius_km: number;
  priority: number;
  spectrum_relation: string;
  preferred_band_groups: string;
  min_satisfaction_ratio: number;
  satisfaction_ratio: number;
  satisfied_count: number;
  requested_count: number;
  status: string;
};

export type EquipmentAssignmentView = {
  task_unit_id: string;
  equipment_group_id: string;
  equipment_type: string;
  assignment_mode: string;
  band_group: string | null;
  assigned_resource: string;
  requested_count: number;
  satisfied_count: number;
  requested_channels: number;
  assigned_channels: number;
  satisfaction_ratio: number;
  status: string;
  risk_score: number;
  risk_level: string;
  reason: string;
  decision_notes: string;
  count?: number;
  priority?: number;
  mobility?: string;
  bandwidth_khz?: number;
  required_full?: boolean;
  alternative_resources?: Array<{
    band_group: string;
    status: string;
    resource: string;
    assigned_channels?: number;
    satisfaction_ratio?: number;
    reason: string;
  }>;
  explanation_chain?: {
    why_selected: string[];
    why_rejected: Array<{ band_group: string; status: string; reason: string }>;
    blocking_rules: Array<{
      rule_id: string;
      rule_type: string;
      start_mhz: number;
      end_mhz: number;
      reason: string;
      severity: string;
    }>;
    required_extra_resource: {
      missing_channels: number;
      estimated_extra_width_mhz: number;
      suggestion: string;
    };
    audit_hint: string;
  };
};

export type BandUsageView = {
  band_group: string;
  available_width_mhz: number;
  used_width_mhz: number;
  utilization_pct: number;
  assignment_count: number;
  rules: Array<{
    rule_id: string;
    rule_type: string;
    start_mhz: number;
    end_mhz: number;
    reason: string;
    source: string;
    severity: string;
  }>;
};

export type SpectrumTimelineMarker = {
  kind: string;
  id: string;
  label: string;
  start_mhz: number;
  end_mhz: number;
  start_pct: number;
  end_pct: number;
  severity: string;
  task_unit_id?: string | null;
  equipment_group_id?: string | null;
};

export type SpectrumTimelineBand = {
  band_group: string;
  start_mhz: number;
  end_mhz: number;
  available_width_mhz: number;
  markers: SpectrumTimelineMarker[];
};

export type TaskRiskItemView = {
  risk_type: string;
  severity: string;
  task_unit_a: string | null;
  equipment_group_a: string | null;
  task_unit_b: string | null;
  equipment_group_b: string | null;
  resource_a: string | null;
  resource_b: string | null;
  score: number;
  reason: string;
};

export type BottleneckAnalysis = {
  band_bottlenecks: Array<{
    band_group: string;
    raw_available_width_mhz: number;
    clean_available_width_mhz: number;
    blocked_width_mhz: number;
    used_width_mhz: number;
    demand_width_mhz: number;
    utilization_pct: number;
    blocker_count: number;
    pressure_group_count: number;
    pressure_score: number;
    top_blockers: Array<{
      rule_id: string;
      rule_type: string;
      start_mhz: number;
      end_mhz: number;
      reason: string;
      severity: string;
    }>;
  }>;
  equipment_gaps: Array<{
    equipment_type: string;
    group_count: number;
    requested_count: number;
    satisfied_count: number;
    gap_count: number;
    partial_group_count: number;
    unsatisfied_group_count: number;
    gap_ratio_pct: number;
    main_reason: string;
  }>;
  task_unit_pressure: Array<{
    task_unit_id: string;
    name: string;
    unit_type: string;
    priority: number;
    requested_count: number;
    satisfied_count: number;
    satisfaction_ratio_pct: number;
    partial_group_count: number;
    unsatisfied_group_count: number;
    risk_count: number;
    pressure_score: number;
  }>;
  conflict_reasons: Array<{ reason: string; count: number }>;
  contention_links: Array<{
    source_unit: string;
    target_unit: string;
    source_group: string;
    target_group: string;
    source_equipment_type: string;
    target_equipment_type: string;
    severity: string;
    score: number;
    reason: string;
    resource_a: string;
    resource_b: string;
  }>;
};

export type SpectrumContention = {
  bands: Array<{
    band_group: string;
    available_width_mhz: number;
    used_width_mhz: number;
    demand_width_mhz: number;
    oversubscription_mhz: number;
    utilization_pct: number;
    pressure_score: number;
    risk_count: number;
  }>;
  top_loss_sources: Array<{
    band_group: string;
    rule_id: string;
    rule_type: string;
    start_mhz: number;
    end_mhz: number;
    width_mhz: number;
    reason: string;
    severity: string;
  }>;
};

export type TaskVisualizationData = {
  summary: Record<string, unknown>;
  task_units: TaskUnitView[];
  assignments: EquipmentAssignmentView[];
  band_usage: BandUsageView[];
  spectrum_timeline: SpectrumTimelineBand[];
  risk_items: TaskRiskItemView[];
  satisfaction_distribution: Array<{ label: string; count: number }>;
  assignment_status_distribution: Array<{ label: string; count: number }>;
  risk_reason_rank: Array<{ reason: string; count: number }>;
  partial_reason_rank: Array<{ reason: string; count: number }>;
};

export type ScoreExplanation = {
  total_score: number;
  interpretation: string;
  components: Array<{ key: string; label: string; value: number; note: string }>;
};

export type DiagnosticItem = {
  category: string;
  severity: string;
  target: string;
  reason: string;
  suggestion: string;
  estimated_gain_pct: number;
};

export type EquipmentLibraryItem = {
  equipment_type: string;
  default_assignment_mode: string;
  reasonable_bandwidth_khz: string;
  reasonable_power_w: string;
  typical_mobility: string;
  planning_notes: string;
};

export type ConstraintWeights = {
  task: number;
  risk: number;
  spectrum: number;
  priority: number;
  switching: number;
  reuse: number;
};

export type WeightTemplate = {
  key: string;
  name: string;
  weights: ConstraintWeights;
  description: string;
};

export type ParametricTaskDemoPayload = {
  unit_count: number;
  density_multiplier: number;
  radar_ratio: number;
  uav_ratio: number;
  protection_density: number;
  forbidden_density: number;
};

export type TaskSampleCatalog = {
  presets: Array<{
    key: string;
    name: string;
    scenario: string;
    task_unit_count: number;
    density_multiplier: number;
    spectrum_pressure: string;
    description: string;
  }>;
  task_unit_profiles: Array<{
    code: string;
    name: string;
    unit_type: string;
    spectrum_relation: string;
    preferred_band_groups: string;
    default_priority: number;
    min_satisfaction_ratio: number;
    equipment_group_count: number;
    equipment_types: string[];
  }>;
  equipment_types: EquipmentLibraryItem[];
  batch_scales: Array<{
    key: string;
    name: string;
    scenario?: string;
    prefix?: string;
    unit_count: number;
    density_multiplier: number;
  }>;
  weight_templates: WeightTemplate[];
  parametric_defaults: ParametricTaskDemoPayload;
  objective_count: number;
};

export type TaskReplanPayload = {
  message: string;
  objective: string;
  base_run_id?: number | null;
  reuse_strategy_from_run_id?: number | null;
  locked_equipment_group_ids: string[];
  available_ranges: Array<{ band_group?: string; start_mhz: number; end_mhz: number; reason?: string }>;
  forbidden_ranges: Array<{ band_group?: string; start_mhz: number; end_mhz: number; reason?: string }>;
  priority_updates: Array<{ target: string; priority: number }>;
  satisfaction_updates: Array<{ task_unit_id: string; min_satisfaction_ratio: number }>;
  equipment_events?: Array<{ action: '损毁' | '新增'; equipment_group_id: string; template_group_id?: string; task_unit_id?: string; equipment_type?: string; count: number; reason?: string }>;
  unit_position_updates?: Array<{ task_unit_id: string; area_center_lat: number; area_center_lon: number; area_radius_km: number; reason?: string }>;
  interference_sources?: Array<{ source_id: string; start_mhz: number; end_mhz: number; max_power_w: number; center_lat?: number | null; center_lon?: number | null; coverage_radius_km?: number; region?: string; starts_at?: string | null; ends_at?: string | null; reason?: string }>;
  avoid_band_groups: string[];
  locked_task_unit_ids?: string[];
  forced_band_groups?: Record<string, string>;
  required_full_targets?: string[];
  allow_low_priority_degrade?: boolean;
  constraint_weights?: Partial<ConstraintWeights>;
  strategy_profile?: string;
  trial_context?: ReplanEffect['trial_context'];
};

export type TaskReplanPreview = {
  objective: string;
  objective_label: string;
  requires_confirmation: boolean;
  change_items: Array<{ type: string; target: string; detail: string }>;
  changes: Record<string, unknown>;
};

export type TaskStrategyTrial = {
  trial_id: string;
  label: string;
  objective: string;
  objective_label: string;
  strategy_profile: string;
  constraint_variant: string;
  constraint_label: string;
  constraint_changes: string[];
  constraint_weights: Partial<ConstraintWeights>;
  reason: string;
  tradeoff: string;
  status: string;
  message: string;
  task_satisfaction_avg: number;
  quality_total: number;
  high_risk_count: number;
  medium_risk_count: number;
  partial_group_count: number;
  unsatisfied_group_count: number;
  used_bandwidth_mhz: number;
  objective_score: number;
  recommendation_score: number;
  deltas: {
    task_satisfaction_avg: number;
    quality_total: number;
    high_risk_count: number;
    medium_risk_count: number;
    partial_group_count: number;
    unsatisfied_group_count: number;
    used_bandwidth_mhz: number;
  };
  decision: string;
  suggested_message: string;
  apply_payload: Partial<TaskReplanPayload>;
  recommended?: boolean;
};

export type TaskStrategyTrialsResult = {
  ok: boolean;
  base_run_id: number | null;
  base_metrics: {
    task_satisfaction_avg: number;
    quality_total: number;
    high_risk_count: number;
    medium_risk_count: number;
    partial_group_count: number;
    unsatisfied_group_count: number;
    used_bandwidth_mhz: number;
  };
  recommended_trial_id: string | null;
  candidates: TaskStrategyTrial[];
  decision_summary?: {
    recommended_trial_id: string | null;
    baseline: {
      task_satisfaction_avg: number;
      quality_total: number;
      high_risk_count: number;
      medium_risk_count: number;
      partial_group_count: number;
      unsatisfied_group_count: number;
      used_bandwidth_mhz: number;
    };
    role_picks: Array<{
      role: string;
      label: string;
      trial_id: string;
      trial_label: string;
      objective?: string;
      objective_label?: string;
      strategy_profile?: string;
      constraint_variant?: string;
      constraint_label?: string;
      metric_key: string;
      metric_value: number | string | null;
      deltas: TaskStrategyTrial['deltas'];
      decision: string;
    }>;
    pareto_frontier: Array<{
      trial_id: string;
      label: string;
      objective_label: string;
      constraint_label: string;
      task_satisfaction_avg: number;
      quality_total: number;
      high_risk_count: number;
      unsatisfied_group_count: number;
      used_bandwidth_mhz: number;
      recommendation_score: number;
    }>;
    tradeoff_notes: string[];
    adoption_guardrails: string[];
  };
  diagnostics: string[];
};

export type TaskSpectrumRuleRecord = {
  id: number;
  project_id: number;
  rule_id: string;
  rule_type: string;
  band_group: string;
  spectrum_relation: string;
  start_mhz: number;
  end_mhz: number;
  channel_step_khz: number;
  max_bandwidth_khz: number;
  max_power_w: number;
  guard_band_khz: number;
  compatible_unit_types: string;
  compatible_equipment_types: string;
  reason: string;
  source: string;
  severity: string;
};

export type TaskSpectrumRulePayload = Omit<TaskSpectrumRuleRecord, 'id' | 'project_id'>;

export type QualityScores = {
  total: number;
  items: Array<{ key: string; label: string; score: number; note: string }>;
};

export type TaskPerformanceRow = {
  scenario: string;
  scenario_name: string;
  scale_key?: string;
  scale_name?: string;
  density_multiplier?: number;
  objective: string;
  objective_label: string;
  status: string;
  message: string;
  task_unit_count: number;
  equipment_group_count: number;
  equipment_sample_count: number;
  spectrum_rule_count: number;
  elapsed_ms: number;
  groups_per_second: number;
  task_satisfaction_avg: number;
  full_group_count: number;
  partial_group_count: number;
  unsatisfied_group_count: number;
  risk_item_count: number;
  high_risk_count: number;
  used_bandwidth_mhz: number;
  quality_total: number;
};

export type TaskCapacityProfile = {
  status: string;
  decision: string;
  interactive_threshold_ms: number;
  quality_floor: number;
  recommended: Partial<TaskPerformanceRow>;
  largest: Partial<TaskPerformanceRow>;
  slowest?: Partial<TaskPerformanceRow>;
  quality_drop: number;
  satisfaction_drop: number;
  elapsed_growth: number;
  problem_focus: string;
  actions: string[];
};

export type TaskScaleEvidence = {
  available: boolean;
  capacity_defined: boolean;
  status: string;
  history_count: number;
  scenario_count?: number;
  run_count?: number;
  max_elapsed_ms?: number;
  avg_elapsed_ms?: number;
  best_quality_total?: number;
  interactive_threshold_ms?: number | null;
  quality_floor?: number | null;
  recommended: Partial<TaskPerformanceRow>;
  largest: Partial<TaskPerformanceRow>;
  quality_drop?: number | null;
  satisfaction_drop?: number | null;
  elapsed_growth?: number | null;
  problem_focus?: string;
  decision: string;
  actions: string[];
  evidence: string;
  capacity_profile?: Partial<TaskCapacityProfile>;
  batch_plan?: TaskCapacityBatchPlan;
};

export type TaskCapacityBatchPlan = {
  available: boolean;
  needed: boolean;
  method?: string;
  reason: string;
  recommended_limits?: {
    task_unit_count?: number;
    equipment_group_count?: number;
    equipment_sample_count?: number | null;
  };
  current?: {
    task_unit_count?: number;
    equipment_group_count?: number;
    equipment_sample_count?: number;
  };
  batch_count?: number;
  max_group_utilization_pct?: number;
  over_limit_count?: number;
  cross_batch_risk_count?: number;
  batches: Array<{
    batch_id: string;
    name: string;
    status: string;
    task_unit_count: number;
    equipment_group_count: number;
    equipment_sample_count: number;
    unit_utilization_pct: number;
    group_utilization_pct: number;
    pressure_score: number;
    high_risk_count: number;
    medium_risk_count: number;
    dominant_band_group: string;
    reason: string;
    task_units: Array<{
      task_unit_id: string;
      name: string;
      unit_type: string;
      priority: number;
      equipment_group_count: number;
      equipment_sample_count: number;
      pressure_score: number;
      status: string;
    }>;
  }>;
  cross_batch_links?: Array<{
    source_unit: string;
    target_unit: string;
    source_batch: string;
    target_batch: string;
    source_equipment_group?: string;
    target_equipment_group?: string;
    source_band_group?: string;
    target_band_group?: string;
    source_resource?: string;
    target_resource?: string;
    severity: string;
    score: number;
    reason: string;
  }>;
  guardrails?: string[];
};

export type TaskCapacityBatchExecutionResult = {
  ok: boolean;
  message: string;
  base_run_id?: number;
  objective?: string;
  strategy_profile?: string;
  batch_plan?: TaskCapacityBatchPlan;
  runs: Array<{
    run_id: number;
    batch_id: string;
    batch_name: string;
    status: string;
    message: string;
    elapsed_ms: number;
    task_unit_count: number;
    equipment_group_count: number;
    equipment_sample_count: number;
    task_satisfaction_avg: number;
    full_group_count: number;
    partial_group_count: number;
    unsatisfied_group_count: number;
    high_risk_count: number;
    medium_risk_count: number;
    used_bandwidth_mhz: number;
    quality_total: number;
    summary: Record<string, unknown>;
  }>;
  cross_batch_review?: {
    status: string;
    summary: string;
    cross_batch_risk_count: number;
    high_risk_count: number;
    medium_risk_count: number;
    affected_batches: string[];
    top_links: Array<{
      source_unit: string;
      target_unit: string;
      source_batch: string;
      target_batch: string;
      source_equipment_group?: string;
      target_equipment_group?: string;
      source_band_group?: string;
      target_band_group?: string;
      source_resource?: string;
      target_resource?: string;
      severity: string;
      score: number;
      reason: string;
    }>;
    guardrails: string[];
    recommendation: string;
  };
  merged_plan?: {
    status: string;
    status_label: string;
    summary: string;
    base_run_id: number;
    objective: string;
    strategy_profile: string;
    run_ids: number[];
    batch_count: number;
    task_unit_count: number;
    equipment_group_count: number;
    equipment_sample_count: number;
    full_group_count: number;
    partial_group_count: number;
    unsatisfied_group_count: number;
    high_risk_count: number;
    medium_risk_count: number;
    cross_batch_risk_count: number;
    cross_batch_high_count: number;
    used_bandwidth_mhz: number;
    total_elapsed_ms: number;
    task_satisfaction_avg: number;
    quality_total: number;
    unresolved_count: number;
    batch_summaries: Array<{
      run_id: number;
      batch_id: string;
      batch_name: string;
      task_unit_count: number;
      equipment_group_count: number;
      task_satisfaction_avg: number;
      quality_total: number;
      unsatisfied_group_count: number;
      partial_group_count: number;
      high_risk_count: number;
      decision: string;
    }>;
    audit_items: string[];
    recommendation: string;
  };
  closure?: {
    source_audit_id?: number;
    applied_rule_count: number;
    skipped_link_count: number;
    before_cross_batch_risk_count: number;
    after_cross_batch_risk_count: number;
    before_high_risk_count?: number;
    after_high_risk_count?: number;
    before_medium_risk_count?: number;
    after_medium_risk_count?: number;
    before_affected_batch_count?: number;
    after_affected_batch_count?: number;
    delta_cross_batch_risk_count?: number;
    resolved_cross_batch_risk_count?: number;
    improved: boolean;
    summary: string;
    rules: Array<{
      batch_id: string;
      task_unit_id: string;
      avoid_band_group: string;
      protected_task_unit_id: string;
      reason: string;
    }>;
    by_batch: Record<string, Record<string, string[]>>;
  };
};

export type TaskPerformanceResult = {
  rows: TaskPerformanceRow[];
  summary: {
    scenario_count: number;
    run_count: number;
    max_elapsed_ms: number;
    avg_elapsed_ms: number;
    max_equipment_group_count: number;
    max_equipment_sample_count: number;
    best_quality_total: number;
  };
  analysis: {
    leader_summary: string;
    scale_curve: Array<{
      scenario: string;
      scenario_name: string;
      task_unit_count: number;
      equipment_group_count: number;
      equipment_sample_count: number;
      avg_elapsed_ms: number;
      max_elapsed_ms: number;
      best_quality_total: number;
      best_satisfaction_avg: number;
      fastest_objective_label: string;
    }>;
    objective_rankings: Array<{
      scenario: string;
      scenario_name: string;
      recommended_objective: string;
      recommended_label: string;
      quality_total: number;
      task_satisfaction_avg: number;
      elapsed_ms: number;
      reason: string;
    }>;
    diagnostics: Array<{
      severity: string;
      title: string;
      detail: string;
      suggestion: string;
    }>;
    capacity_profile?: TaskCapacityProfile;
    fastest_case?: TaskPerformanceRow | null;
    slowest_case?: TaskPerformanceRow | null;
  };
  scales?: TaskSampleCatalog['batch_scales'];
  history?: Array<{
    id?: number;
    created_at: string;
    scenario_count?: number;
    run_count: number;
    max_elapsed_ms: number;
    avg_elapsed_ms: number;
    max_equipment_group_count: number;
    max_equipment_sample_count?: number;
    best_quality_total?: number;
    leader_summary: string;
    capacity_profile?: TaskCapacityProfile;
  }>;
};

export type TaskVersionRun = {
  run_id: number;
  objective: string;
  status: string;
  message: string;
  elapsed_ms: number;
  created_at: string;
  summary: Record<string, unknown>;
  replan_effect?: ReplanEffect | null;
  lifecycle_status: string;
  adopted: boolean;
  parent_run_id: number | null;
  rollback_source_run_id: number | null;
  snapshot_available: boolean;
};

export type TaskAuditLog = {
  id: number;
  run_id: number | null;
  actor: string;
  action: string;
  detail: string;
  created_at: string;
};

export type TaskVersionsResult = {
  runs: TaskVersionRun[];
  audit_logs: TaskAuditLog[];
  audit_summary?: {
    total_count: number;
    planning_count: number;
    replan_count: number;
    manual_change_count: number;
    export_count: number;
    actor_counts: Record<string, number>;
    action_counts: Record<string, number>;
    last_activity_at: string | null;
  };
  closure_events?: Array<{
    id: number;
    run_id: number | null;
    source_audit_id?: number | null;
    created_at: string;
    summary: string;
    improved: boolean;
    applied_rule_count: number;
    skipped_link_count: number;
    before_cross_batch_risk_count: number;
    after_cross_batch_risk_count: number;
    before_high_risk_count: number;
    after_high_risk_count: number;
    resolved_cross_batch_risk_count: number;
    affected_batches: string[];
    run_ids: number[];
    rules: Array<{
      batch_id: string;
      task_unit_id: string;
      avoid_band_group: string;
      protected_task_unit_id: string;
      reason: string;
    }>;
  }>;
  performance_history?: TaskPerformanceResult['history'];
};

export type TaskAgentAssessment = {
  status: string;
  run_id: number | null;
  maturity_score: number;
  maturity_level: string;
  leader_summary: string;
  replan_effect?: ReplanEffect | null;
  strategy_history?: Array<{
    run_id: number;
    objective?: string | null;
    effective_objective?: string | null;
    strategy_profile?: string | null;
    task_satisfaction_avg: number;
    quality_total: number;
    high_risk_count: number;
    medium_risk_count: number;
    partial_group_count: number;
    unsatisfied_group_count: number;
    used_bandwidth_mhz: number;
    elapsed_ms: number;
    created_at?: string | null;
    transition_status: string;
    transition_label: string;
    delta_quality: number;
    delta_satisfaction: number;
  }>;
  scale_evidence?: TaskScaleEvidence;
  capability_items: Array<{
    key: string;
    label: string;
    score: number;
    status: string;
    evidence: string;
    next_step: string;
  }>;
  acceptance_gates: Array<{
    name: string;
    passed: boolean;
    evidence: string;
    next_step: string;
  }>;
  next_actions: Array<{
    action_id: string;
    priority: string;
    title: string;
    why: string;
    suggested_message: string;
    rank_score?: number;
    expected_gain?: string;
    guardrail?: string;
    deterministic_payload: Record<string, unknown>;
  }>;
  artifact_checklist: Array<{
    item: string;
    covered: boolean;
    evidence: string;
  }>;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    let message = response.statusText;
    try {
      const data = await response.json();
      message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail ?? data);
    } catch {
      message = await response.text();
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export async function createProject(name: string): Promise<Project> {
  return request<Project>('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
}

export async function listProjects(): Promise<Project[]> {
  return request<Project[]>('/api/projects');
}

export async function getTaskProjectData(projectId: number): Promise<TaskProjectData> {
  return request<TaskProjectData>(`/api/projects/${projectId}/task-data`);
}

export async function listSpectrumResources(projectId: number): Promise<SpectrumResourceRecord[]> {
  return request<SpectrumResourceRecord[]>(`/api/projects/${projectId}/spectrum-resources`);
}

export async function createSpectrumResource(projectId: number, payload: SpectrumResourcePayload): Promise<SpectrumResourceRecord> {
  return request<SpectrumResourceRecord>(`/api/projects/${projectId}/spectrum-resources`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
}

export async function updateSpectrumResource(
  projectId: number,
  rowId: number,
  payload: SpectrumResourcePayload,
): Promise<SpectrumResourceRecord> {
  return request<SpectrumResourceRecord>(`/api/projects/${projectId}/spectrum-resources/${rowId}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
}

export async function deleteSpectrumResource(projectId: number, rowId: number): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/api/projects/${projectId}/spectrum-resources/${rowId}`, { method: 'DELETE' });
}

export async function getSpectrumResourceHeatmap(
  projectId: number,
  at?: string,
  region?: string,
): Promise<SpectrumResourceHeatmap> {
  const query = new URLSearchParams();
  if (at) query.set('at', at);
  if (region) query.set('region', region);
  const suffix = query.size ? `?${query.toString()}` : '';
  return request<SpectrumResourceHeatmap>(`/api/projects/${projectId}/spectrum-resource-heatmap${suffix}`);
}

export async function saveMissionTask(projectId: number, payload: MissionTaskPayload): Promise<MissionTaskRecord> {
  return request<MissionTaskRecord>(`/api/projects/${projectId}/task-mission`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function createTaskPhase(projectId: number, payload: TaskPhasePayload): Promise<TaskPhaseRecord> {
  return request<TaskPhaseRecord>(`/api/projects/${projectId}/task-phases`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
}

export async function updateTaskPhase(projectId: number, rowId: number, payload: TaskPhasePayload): Promise<TaskPhaseRecord> {
  return request<TaskPhaseRecord>(`/api/projects/${projectId}/task-phases/${rowId}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
}

export async function deleteTaskPhase(projectId: number, rowId: number): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/api/projects/${projectId}/task-phases/${rowId}`, { method: 'DELETE' });
}

export async function createTaskUnit(projectId: number, payload: TaskUnitPayload): Promise<TaskUnitRecord> {
  return request<TaskUnitRecord>(`/api/projects/${projectId}/task-units`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
}

export async function updateTaskUnit(projectId: number, rowId: number, payload: TaskUnitPayload): Promise<TaskUnitRecord> {
  return request<TaskUnitRecord>(`/api/projects/${projectId}/task-units/${rowId}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
}

export async function deleteTaskUnit(projectId: number, rowId: number): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/api/projects/${projectId}/task-units/${rowId}`, { method: 'DELETE' });
}

export async function createEquipmentGroup(projectId: number, payload: EquipmentGroupPayload): Promise<EquipmentGroupRecord> {
  return request<EquipmentGroupRecord>(`/api/projects/${projectId}/equipment-groups`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
}

export async function updateEquipmentGroup(
  projectId: number,
  rowId: number,
  payload: EquipmentGroupPayload,
): Promise<EquipmentGroupRecord> {
  return request<EquipmentGroupRecord>(`/api/projects/${projectId}/equipment-groups/${rowId}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
}

export async function deleteEquipmentGroup(projectId: number, rowId: number): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/api/projects/${projectId}/equipment-groups/${rowId}`, { method: 'DELETE' });
}

export async function createTaskLink(projectId: number, payload: TaskLinkPayload): Promise<TaskLinkRecord> {
  return request<TaskLinkRecord>(`/api/projects/${projectId}/task-links`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
}

export async function updateTaskLink(projectId: number, rowId: number, payload: TaskLinkPayload): Promise<TaskLinkRecord> {
  return request<TaskLinkRecord>(`/api/projects/${projectId}/task-links/${rowId}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
}

export async function deleteTaskLink(projectId: number, rowId: number): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/api/projects/${projectId}/task-links/${rowId}`, { method: 'DELETE' });
}

export async function importTaskPackage(
  projectId: number,
  taskUnits: File,
  equipmentGroups: File,
  spectrumRules: File,
): Promise<Record<string, unknown>> {
  const form = new FormData();
  form.append('task_units', taskUnits);
  form.append('equipment_groups', equipmentGroups);
  form.append('spectrum_rules', spectrumRules);
  return request<Record<string, unknown>>(`/api/projects/${projectId}/import-task-package`, { method: 'POST', body: form });
}

export async function uploadFile(projectId: number, kind: 'stations' | 'rules', file: File): Promise<Record<string, unknown>> {
  const form = new FormData();
  form.append('file', file);
  const path = kind === 'stations' ? 'upload-stations' : 'upload-rules';
  return request<Record<string, unknown>>(`/api/projects/${projectId}/${path}`, {
    method: 'POST',
    body: form,
  });
}

export async function validateProject(projectId: number): Promise<ValidationResult> {
  return request<ValidationResult>(`/api/projects/${projectId}/validate`, { method: 'POST' });
}

export async function planProject(projectId: number, objective: string): Promise<PlanResult> {
  return request<PlanResult>(`/api/projects/${projectId}/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ objective }),
  });
}

export async function chat(projectId: number, message: string, objective: string): Promise<ChatResult> {
  return request<ChatResult>(`/api/projects/${projectId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, objective }),
  });
}

export async function getVisualization(projectId: number, runId: number): Promise<VisualizationData> {
  return request<VisualizationData>(`/api/projects/${projectId}/visualization?run_id=${runId}`);
}

export async function comparePlans(projectId: number): Promise<ComparisonResult> {
  return request<ComparisonResult>(`/api/projects/${projectId}/compare`, { method: 'POST' });
}

export async function listRules(projectId: number): Promise<RuleRecord[]> {
  return request<RuleRecord[]>(`/api/projects/${projectId}/rules`);
}

export async function createRule(projectId: number, payload: RulePayload): Promise<RuleRecord> {
  return request<RuleRecord>(`/api/projects/${projectId}/rules`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function updateRule(projectId: number, ruleId: number, payload: RulePayload): Promise<RuleRecord> {
  return request<RuleRecord>(`/api/projects/${projectId}/rules/${ruleId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function deleteRule(projectId: number, ruleId: number): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/api/projects/${projectId}/rules/${ruleId}`, { method: 'DELETE' });
}

export async function getTaskObjectives(): Promise<TaskObjective[]> {
  return request<TaskObjective[]>('/api/task-objectives');
}

export async function getEquipmentLibrary(): Promise<EquipmentLibraryItem[]> {
  return request<EquipmentLibraryItem[]>('/api/equipment-library');
}

export async function getTaskScenarios(): Promise<TaskScenario[]> {
  return request<TaskScenario[]>('/api/task-scenarios');
}

export async function getTaskSampleCatalog(): Promise<TaskSampleCatalog> {
  return request<TaskSampleCatalog>('/api/task-sample-catalog');
}

export async function runTaskPerformanceTest(): Promise<TaskPerformanceResult> {
  return request<TaskPerformanceResult>('/api/task-performance-test', { method: 'POST' });
}

export async function runTaskBatchPerformanceTest(): Promise<TaskPerformanceResult> {
  return request<TaskPerformanceResult>('/api/task-performance-batch', { method: 'POST' });
}

export async function generateTaskDemo(projectId: number, scenario = 'baseline'): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/api/projects/${projectId}/generate-task-demo?scenario=${encodeURIComponent(scenario)}`, {
    method: 'POST',
  });
}

export async function generateParametricTaskDemo(
  projectId: number,
  payload: ParametricTaskDemoPayload,
): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/api/projects/${projectId}/generate-parametric-task-demo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function uploadTaskFile(
  projectId: number,
  kind: 'task-units' | 'equipment-groups' | 'spectrum-rules',
  file: File,
): Promise<Record<string, unknown>> {
  const form = new FormData();
  form.append('file', file);
  const path =
    kind === 'task-units' ? 'upload-task-units' : kind === 'equipment-groups' ? 'upload-equipment-groups' : 'upload-spectrum-rules';
  return request<Record<string, unknown>>(`/api/projects/${projectId}/${path}`, {
    method: 'POST',
    body: form,
  });
}

export async function validateTaskProject(projectId: number): Promise<TaskValidationResult> {
  return request<TaskValidationResult>(`/api/projects/${projectId}/validate-task`, { method: 'POST' });
}

export async function planTaskProject(
  projectId: number,
  objective: string,
  constraintWeights: Partial<ConstraintWeights> = {},
  strategyProfile = 'balanced',
): Promise<PlanResult> {
  return request<PlanResult>(`/api/projects/${projectId}/task-plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ objective, constraint_weights: constraintWeights, strategy_profile: strategyProfile }),
  });
}

export async function compareTaskPlans(projectId: number, constraintWeights: Partial<ConstraintWeights> = {}, strategyProfile = 'balanced'): Promise<TaskComparisonResult> {
  return request<TaskComparisonResult>(`/api/projects/${projectId}/task-compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ objective: 'multi_objective', constraint_weights: constraintWeights, strategy_profile: strategyProfile }),
  });
}

export async function getTaskVisualization(projectId: number, runId: number): Promise<TaskVisualizationData> {
  return request<TaskVisualizationData>(`/api/projects/${projectId}/task-visualization?run_id=${runId}`);
}

export async function replanTaskProject(projectId: number, payload: TaskReplanPayload): Promise<ChatResult> {
  return request<ChatResult>(`/api/projects/${projectId}/task-replan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function previewTaskReplan(projectId: number, payload: TaskReplanPayload): Promise<TaskReplanPreview> {
  return request<TaskReplanPreview>(`/api/projects/${projectId}/task-replan-preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function previewTaskStrategyTrials(projectId: number, payload: TaskReplanPayload): Promise<TaskStrategyTrialsResult> {
  return request<TaskStrategyTrialsResult>(`/api/projects/${projectId}/task-strategy-trials`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function getTaskVersions(projectId: number): Promise<TaskVersionsResult> {
  return request<TaskVersionsResult>(`/api/projects/${projectId}/task-versions`);
}

export async function adoptTaskPlan(projectId: number, runId: number): Promise<{ ok: boolean; run_id: number; lifecycle_status: string; adopted: boolean }> {
  return request(`/api/projects/${projectId}/task-runs/${runId}/adopt`, { method: 'POST' });
}

export async function rollbackTaskPlan(projectId: number, runId: number): Promise<PlanResult> {
  return request<PlanResult>(`/api/projects/${projectId}/task-runs/${runId}/rollback`, { method: 'POST' });
}

export async function getTaskAgentAssessment(projectId: number, runId?: number | null): Promise<TaskAgentAssessment> {
  const query = runId ? `?run_id=${runId}` : '';
  return request<TaskAgentAssessment>(`/api/projects/${projectId}/task-agent-assessment${query}`);
}

export async function runProjectTaskBatchPerformanceTest(projectId: number): Promise<TaskPerformanceResult> {
  return request<TaskPerformanceResult>(`/api/projects/${projectId}/task-performance-batch`, { method: 'POST' });
}

export async function executeTaskCapacityBatches(
  projectId: number,
  payload: {
    base_run_id?: number | null;
    objective?: string | null;
    batch_ids?: string[];
    constraint_weights?: Partial<ConstraintWeights>;
    strategy_profile?: string | null;
  },
): Promise<TaskCapacityBatchExecutionResult> {
  return request<TaskCapacityBatchExecutionResult>(`/api/projects/${projectId}/task-capacity-batches`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function executeTaskCapacityRiskClosure(
  projectId: number,
  payload: {
    objective?: string | null;
    constraint_weights?: Partial<ConstraintWeights>;
    strategy_profile?: string | null;
  } = {},
): Promise<TaskCapacityBatchExecutionResult> {
  return request<TaskCapacityBatchExecutionResult>(`/api/projects/${projectId}/task-capacity-risk-closure`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function listTaskSpectrumRules(projectId: number): Promise<TaskSpectrumRuleRecord[]> {
  return request<TaskSpectrumRuleRecord[]>(`/api/projects/${projectId}/spectrum-rules`);
}

export async function createTaskSpectrumRule(projectId: number, payload: TaskSpectrumRulePayload): Promise<TaskSpectrumRuleRecord> {
  return request<TaskSpectrumRuleRecord>(`/api/projects/${projectId}/spectrum-rules`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function updateTaskSpectrumRule(projectId: number, rowId: number, payload: TaskSpectrumRulePayload): Promise<TaskSpectrumRuleRecord> {
  return request<TaskSpectrumRuleRecord>(`/api/projects/${projectId}/spectrum-rules/${rowId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function deleteTaskSpectrumRule(projectId: number, rowId: number): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/api/projects/${projectId}/spectrum-rules/${rowId}`, { method: 'DELETE' });
}

export function url(path: string): string {
  return `${API_BASE}${path}`;
}

import { ChangeEvent, CSSProperties, ReactNode, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  BarChart3,
  Bell,
  Bot,
  CheckCircle2,
  ClipboardList,
  Clock3,
  Download,
  Eye,
  FileCheck2,
  Gauge,
  HelpCircle,
  Layers3,
  Lock,
  Mail,
  Menu,
  MessageSquare,
  MousePointer2,
  Plus,
  Play,
  RadioTower,
  RefreshCw,
  RotateCcw,
  Save,
  ShieldAlert,
  SlidersHorizontal,
  Trash2,
  Upload,
  WandSparkles,
} from 'lucide-react';
import {
  BottleneckAnalysis,
  ConstraintWeights,
  DiagnosticItem,
  EquipmentLibraryItem,
  MissionTaskRecord,
  ParametricTaskDemoPayload,
  PlanResult,
  Project,
  QualityScores,
  ReplanEffect,
  SpectrumContention,
  TaskAuditLog,
  TaskCapacityBatchExecutionResult,
  TaskComparisonPlan,
  TaskComparisonResult,
  TaskAgentAssessment,
  TaskObjective,
  TaskPerformanceResult,
  TaskProjectData,
  TaskReplanPreview,
  TaskReplanPayload,
  TaskSampleCatalog,
  TaskScenario,
  TaskStrategyTrial,
  TaskStrategyTrialsResult,
  TaskSpectrumRulePayload,
  TaskSpectrumRuleRecord,
  TaskValidationResult,
  TaskVersionRun,
  TaskVersionsResult,
  TaskVisualizationData,
  compareTaskPlans,
  createTaskSpectrumRule,
  createProject,
  deleteTaskSpectrumRule,
  executeTaskCapacityBatches,
  executeTaskCapacityRiskClosure,
  generateParametricTaskDemo,
  generateTaskDemo,
  getEquipmentLibrary,
  getTaskObjectives,
  getTaskProjectData,
  getTaskAgentAssessment,
  getTaskSampleCatalog,
  getTaskScenarios,
  getTaskVersions,
  getTaskVisualization,
  listTaskSpectrumRules,
  listProjects,
  planTaskProject,
  previewTaskReplan,
  previewTaskStrategyTrials,
  replanTaskProject,
  runTaskBatchPerformanceTest,
  runProjectTaskBatchPerformanceTest,
  runTaskPerformanceTest,
  updateTaskSpectrumRule,
  uploadTaskFile,
  url,
  validateTaskProject,
  adoptTaskPlan,
  rollbackTaskPlan,
} from './api';
import TaskWorkbench from './TaskWorkbench';
import SpectrumResourcePanel from './SpectrumResourcePanel';
import { InterferenceAnalysisPanel } from './InterferenceAnalysisPanel';
import { PlanningResultPanel } from './PlanningResultPanel';
import { DynamicEventPanel, DynamicEvents } from './DynamicEventPanel';
type Notice = {
  type: 'info' | 'error' | 'success';
  text: string;
};

type AgentSuggestedAction = TaskAgentAssessment['next_actions'][number];

const defaultObjectives: TaskObjective[] = [
  { objective: 'task_assurance', label: '任务保障优先', description: '优先满足任务单元最低保障率。' },
  { objective: 'minimize_interference', label: '干扰最低', description: '降低保护频率和复用风险。' },
  { objective: 'minimize_bandwidth', label: '占用带宽最小', description: '压缩总占用带宽。' },
  { objective: 'priority_equipment', label: '高优先级装备优先', description: '优先保障高优先级装备组。' },
  { objective: 'radar_priority', label: '雷达优先保障', description: '优先保障雷达连续宽带窗口。' },
  { objective: 'uav_link_priority', label: '无人机链路优先', description: '优先满足无人机遥控和数传链路。' },
  { objective: 'communication_continuity', label: '通信连续性优先', description: '优先保证通信、中继和数据链连续可用。' },
  { objective: 'ew_isolation_priority', label: '电子对抗隔离优先', description: '优先隔离高功率电子对抗装备。' },
  { objective: 'minimize_switching', label: '最少频段切换', description: '优先沿用装备首选频段。' },
  { objective: 'maximize_reuse_efficiency', label: '最大复用效率', description: '优先复用低功率和共享型资源。' },
];

const defaultConstraintWeights: ConstraintWeights = {
  task: 70,
  risk: 70,
  spectrum: 55,
  priority: 65,
  switching: 35,
  reuse: 45,
};

const defaultParametricPayload: ParametricTaskDemoPayload = {
  unit_count: 24,
  density_multiplier: 1.8,
  radar_ratio: 18,
  uav_ratio: 18,
  protection_density: 2,
  forbidden_density: 2,
};

type DashboardModuleKey =
  | 'overview'
  | 'tasks'
  | 'spectrumResources'
  | 'plan'
  | 'spectrum'
  | 'interference'
  | 'risk'
  | 'replan'
  | 'decision'
  | 'assurance'
  | 'report'
  | 'system';

const dashboardModuleTitles: Record<DashboardModuleKey, string> = {
  overview: '项目总览',
  tasks: '任务管理',
  spectrumResources: '频谱资源',
  plan: '规划方案',
  spectrum: '频谱占用',
  interference: '干扰分析',
  risk: '风险管理',
  replan: '动态重规划',
  decision: '多策略决策',
  assurance: '任务保障率',
  report: '报表中心',
  system: '验收留痕',
};

export default function TaskPlanningApp() {
  const [projectName, setProjectName] = useState('战场联合任务用频筹划');
  const [project, setProject] = useState<Project | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [taskDataSummary, setTaskDataSummary] = useState({ taskUnits: 0, equipmentGroups: 0, spectrumRules: 0, phases: 0, links: 0 });
  const [taskMission, setTaskMission] = useState<MissionTaskRecord | null>(null);
  const [taskDataRevision, setTaskDataRevision] = useState(0);
  const [activeModule, setActiveModule] = useState<DashboardModuleKey>('overview');
  const [objectives, setObjectives] = useState<TaskObjective[]>(defaultObjectives);
  const [objective, setObjective] = useState('task_assurance');
  const [constraintWeights, setConstraintWeights] = useState<ConstraintWeights>(defaultConstraintWeights);
  const [strategyProfile, setStrategyProfile] = useState('balanced');
  const [parametricPayload, setParametricPayload] = useState<ParametricTaskDemoPayload>(defaultParametricPayload);
  const [scenarios, setScenarios] = useState<TaskScenario[]>([]);
  const [scenario, setScenario] = useState('baseline');
  const [taskUnitFile, setTaskUnitFile] = useState<File | null>(null);
  const [equipmentFile, setEquipmentFile] = useState<File | null>(null);
  const [spectrumFile, setSpectrumFile] = useState<File | null>(null);
  const [validation, setValidation] = useState<TaskValidationResult | null>(null);
  const [comparison, setComparison] = useState<TaskComparisonResult | null>(null);
  const [plan, setPlan] = useState<PlanResult | null>(null);
  const [performance, setPerformance] = useState<TaskPerformanceResult | null>(null);
  const [capacityBatchExecution, setCapacityBatchExecution] = useState<TaskCapacityBatchExecutionResult | null>(null);
  const [visualization, setVisualization] = useState<TaskVisualizationData | null>(null);
  const [previousVisualization, setPreviousVisualization] = useState<TaskVisualizationData | null>(null);
  const [agentAssessment, setAgentAssessment] = useState<TaskAgentAssessment | null>(null);
  const [visualizationRunId, setVisualizationRunId] = useState<number | null>(null);
  const [equipmentLibrary, setEquipmentLibrary] = useState<EquipmentLibraryItem[]>([]);
  const [sampleCatalog, setSampleCatalog] = useState<TaskSampleCatalog | null>(null);
  const [versions, setVersions] = useState<TaskVersionsResult | null>(null);
  const [spectrumRules, setSpectrumRules] = useState<TaskSpectrumRuleRecord[]>([]);
  const [replanPreview, setReplanPreview] = useState<TaskReplanPreview | null>(null);
  const [strategyTrials, setStrategyTrials] = useState<TaskStrategyTrialsResult | null>(null);
  const [replanConfirmed, setReplanConfirmed] = useState(false);
  const [replanMessage, setReplanMessage] = useState('禁用 2210-2215 MHz，雷达探测单元优先级提高，尽量少用 C-SIM-1');
  const [lockedGroupIds, setLockedGroupIds] = useState<string[]>([]);
  const [lockedTaskUnitIds, setLockedTaskUnitIds] = useState<string[]>([]);
  const [forbidBand, setForbidBand] = useState('');
  const [forbidStart, setForbidStart] = useState('');
  const [forbidEnd, setForbidEnd] = useState('');
  const [availableBand, setAvailableBand] = useState('');
  const [availableStart, setAvailableStart] = useState('');
  const [availableEnd, setAvailableEnd] = useState('');
  const [priorityTarget, setPriorityTarget] = useState('');
  const [priorityValue, setPriorityValue] = useState('9');
  const [satisfactionUnit, setSatisfactionUnit] = useState('');
  const [satisfactionValue, setSatisfactionValue] = useState('70');
  const [avoidBand, setAvoidBand] = useState('');
  const [forcedTarget, setForcedTarget] = useState('');
  const [forcedBand, setForcedBand] = useState('');
  const [requiredFullTarget, setRequiredFullTarget] = useState('');
  const [allowLowPriorityDegrade, setAllowLowPriorityDegrade] = useState(true);
  const [dynamicEvents, setDynamicEvents] = useState<DynamicEvents>({ equipment_events: [], unit_position_updates: [], interference_sources: [] });
  const [suggestedPayloadOverride, setSuggestedPayloadOverride] = useState<Partial<TaskReplanPayload> | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState(false);

  const reportUrl = useMemo(
    () => (project && plan?.status === 'success' ? url(`/api/projects/${project.id}/task-report?run=${plan.run_id}`) : ''),
    [project, plan],
  );

  useEffect(() => {
    void getTaskObjectives()
      .then(setObjectives)
      .catch(() => setObjectives(defaultObjectives));
    void getTaskScenarios()
      .then(setScenarios)
      .catch(() => setScenarios([]));
    void getEquipmentLibrary()
      .then(setEquipmentLibrary)
      .catch(() => setEquipmentLibrary([]));
    void getTaskSampleCatalog()
      .then((catalog) => {
        setSampleCatalog(catalog);
        const balanced = catalog.weight_templates.find((item) => item.key === 'balanced') ?? catalog.weight_templates[0];
        if (balanced) {
          setConstraintWeights(balanced.weights);
          setStrategyProfile(balanced.key);
        }
        setParametricPayload(catalog.parametric_defaults);
      })
      .catch(() => setSampleCatalog(null));
    void listProjects()
      .then((items) => {
        setProjects(items);
        if (!items.length) return;
        const savedProjectId = Number(window.localStorage.getItem('spectrum-planning-project-id'));
        const selected = items.find((item) => item.id === savedProjectId) ?? items[0];
        void openProject(selected, false);
      })
      .catch(() => setProjects([]));
  }, []);

  async function runAction<T>(action: () => Promise<T>, success: string): Promise<T | null> {
    setBusy(true);
    setNotice(null);
    try {
      const result = await action();
      setNotice({ type: 'success', text: success });
      return result;
    } catch (error) {
      setNotice({ type: 'error', text: error instanceof Error ? error.message : '操作失败' });
      return null;
    } finally {
      setBusy(false);
    }
  }

  function clearPlanningState() {
    setValidation(null);
    setComparison(null);
    setPlan(null);
    setVisualization(null);
    setPreviousVisualization(null);
    setAgentAssessment(null);
    setCapacityBatchExecution(null);
    setVisualizationRunId(null);
    setVersions(null);
    setReplanPreview(null);
    setReplanConfirmed(false);
    setSuggestedPayloadOverride(null);
    setLockedGroupIds([]);
    setLockedTaskUnitIds([]);
    setAvailableBand('');
    setAvailableStart('');
    setAvailableEnd('');
    setDynamicEvents({ equipment_events: [], unit_position_updates: [], interference_sources: [] });
  }

  async function loadVisualization(projectId: number, runId: number) {
    const result = await getTaskVisualization(projectId, runId);
    if (visualization && visualizationRunId !== runId) {
      setPreviousVisualization(visualization);
    }
    setVisualization(result);
    setVisualizationRunId(runId);
    await refreshAgentAssessment(projectId, runId);
    await refreshVersions(projectId);
    return result;
  }

  async function refreshAgentAssessment(projectId: number, runId?: number | null) {
    try {
      const result = await getTaskAgentAssessment(projectId, runId ?? plan?.run_id ?? null);
      setAgentAssessment(result);
    } catch {
      setAgentAssessment(null);
    }
  }

  async function refreshVersions(projectId: number) {
    try {
      const result = await getTaskVersions(projectId);
      setVersions(result);
    } catch {
      setVersions(null);
    }
  }

  async function refreshSpectrumRules(projectId: number) {
    try {
      const result = await listTaskSpectrumRules(projectId);
      setSpectrumRules(result);
    } catch {
      setSpectrumRules([]);
    }
  }

  function applyTaskDataSummary(data: TaskProjectData) {
    setTaskMission(data.mission ?? null);
    setTaskDataSummary({
      taskUnits: data.task_units.length,
      equipmentGroups: data.equipment_groups.length,
      spectrumRules: data.spectrum_rules.length,
      phases: data.phases?.length ?? 0,
      links: data.links?.length ?? 0,
    });
  }

  async function refreshTaskDataSummary(projectId: number) {
    try {
      applyTaskDataSummary(await getTaskProjectData(projectId));
    } catch {
      setTaskMission(null);
      setTaskDataSummary({ taskUnits: 0, equipmentGroups: 0, spectrumRules: 0, phases: 0, links: 0 });
    }
  }

  async function openProject(selected: Project, announce = true) {
    setBusy(true);
    setNotice(null);
    setProject(selected);
    setProjectName(selected.name);
    clearPlanningState();
    window.localStorage.setItem('spectrum-planning-project-id', String(selected.id));
    try {
      const [data, projectVersions, rules] = await Promise.all([
        getTaskProjectData(selected.id),
        getTaskVersions(selected.id),
        listTaskSpectrumRules(selected.id),
      ]);
      applyTaskDataSummary(data);
      setVersions(projectVersions);
      setSpectrumRules(rules);

      const latestRun = projectVersions.runs[0];
      if (latestRun) {
        const [latestVisualization, assessment] = await Promise.all([
          getTaskVisualization(selected.id, latestRun.run_id),
          getTaskAgentAssessment(selected.id, latestRun.run_id).catch(() => null),
        ]);
        setPlan({
          run_id: latestRun.run_id,
          status: latestRun.status,
          message: latestRun.message,
          summary: latestVisualization.summary,
        });
        setVisualization(latestVisualization);
        setVisualizationRunId(latestRun.run_id);
        setAgentAssessment(assessment);
      }
      if (announce) setNotice({ type: 'success', text: `已打开项目“${selected.name}”` });
    } catch (error) {
      setNotice({ type: 'error', text: error instanceof Error ? error.message : '项目加载失败' });
    } finally {
      setBusy(false);
    }
  }

  async function refreshProjectList() {
    const result = await runAction(listProjects, '项目列表已刷新');
    if (result) setProjects(result);
  }

  async function handleCreateProject() {
    const name = projectName.trim();
    if (!name) {
      setNotice({ type: 'error', text: '请输入项目名称' });
      return;
    }
    const created = await runAction(() => createProject(name), '项目已创建');
    if (created) {
      setProject(created);
      setProjects((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      clearPlanningState();
      setSpectrumRules([]);
      setTaskMission(null);
      setTaskDataSummary({ taskUnits: 0, equipmentGroups: 0, spectrumRules: 0, phases: 0, links: 0 });
      window.localStorage.setItem('spectrum-planning-project-id', String(created.id));
    }
  }

  async function handleGenerateDemo() {
    if (!project) {
      setNotice({ type: 'error', text: '请先创建项目' });
      return;
    }
    const result = await runAction(() => generateTaskDemo(project.id, scenario), '已生成任务场景样例');
    if (result) {
      clearPlanningState();
      await refreshSpectrumRules(project.id);
      await refreshTaskDataSummary(project.id);
      setTaskDataRevision((current) => current + 1);
    }
  }

  async function handleGenerateParametricDemo() {
    if (!project) {
      setNotice({ type: 'error', text: '请先创建项目' });
      return;
    }
    const result = await runAction(() => generateParametricTaskDemo(project.id, parametricPayload), '已生成参数化任务场景');
    if (result) {
      clearPlanningState();
      await refreshSpectrumRules(project.id);
      await refreshTaskDataSummary(project.id);
      setTaskDataRevision((current) => current + 1);
    }
  }

  async function handleUpload(kind: 'task-units' | 'equipment-groups' | 'spectrum-rules') {
    if (!project) {
      setNotice({ type: 'error', text: '请先创建项目' });
      return;
    }
    const file = kind === 'task-units' ? taskUnitFile : kind === 'equipment-groups' ? equipmentFile : spectrumFile;
    if (!file) {
      setNotice({ type: 'error', text: '请选择对应 Excel 文件' });
      return;
    }
    const result = await runAction(() => uploadTaskFile(project.id, kind, file), '数据已上传');
    if (result) {
      clearPlanningState();
      if (kind === 'spectrum-rules') await refreshSpectrumRules(project.id);
      await refreshTaskDataSummary(project.id);
      setTaskDataRevision((current) => current + 1);
    }
  }

  async function handleValidate() {
    if (!project) return;
    const result = await runAction(() => validateTaskProject(project.id), '校验完成');
    if (result) setValidation(result);
  }

  async function handlePlan() {
    if (!project) return;
    const result = await runAction(() => planTaskProject(project.id, objective, constraintWeights, strategyProfile), '任务单元规划完成');
    if (result) {
      setPlan(result);
      if (result.status === 'success') {
        await loadVisualization(project.id, result.run_id);
      }
    }
  }

  async function handleCompare() {
    if (!project) return;
    const result = await runAction(() => compareTaskPlans(project.id), '多方案对比完成');
    if (result) {
      setComparison(result);
      const selected = result.plans.find((item) => item.recommended) ?? result.plans.find((item) => item.status === 'success');
      if (selected) await selectPlan(selected);
    }
  }

  async function handlePerformanceTest() {
    const result = await runAction(() => runTaskPerformanceTest(), '规划效能测试完成');
    if (result) setPerformance(result);
  }

  async function handleBatchPerformanceTest() {
    const action = project ? () => runProjectTaskBatchPerformanceTest(project.id) : () => runTaskBatchPerformanceTest();
    const result = await runAction(action, '阶梯压测完成');
    if (result) {
      setPerformance(result);
      if (project) {
        await refreshVersions(project.id);
        await refreshAgentAssessment(project.id, plan?.run_id ?? visualizationRunId);
      }
    }
  }

  async function handlePreviewReplan() {
    if (!project) return;
    const payload = buildReplanPayload(suggestedPayloadOverride ?? undefined);
    const result = await runAction(() => previewTaskReplan(project.id, payload), '已生成变更清单');
    if (result) {
      setReplanPreview(result);
      setReplanConfirmed(false);
    }
  }

  async function handlePreviewStrategyTrials() {
    if (!project) return;
    const payload = buildReplanPayload(suggestedPayloadOverride ?? undefined);
    const result = await runAction(() => previewTaskStrategyTrials(project.id, payload), '已完成多策略试算');
    if (result) {
      setStrategyTrials(result);
      setReplanConfirmed(false);
    }
  }

  async function handleApplyStrategyTrial(trial: TaskStrategyTrial) {
    if (!project) return;
    const overrides: Partial<TaskReplanPayload> = {
      ...(trial.apply_payload ?? {}),
      trial_context: {
        trial_id: trial.trial_id,
        label: trial.label,
        objective: trial.objective,
        objective_label: trial.objective_label,
        strategy_profile: trial.strategy_profile,
        constraint_variant: trial.constraint_variant,
        constraint_label: trial.constraint_label,
        decision: trial.decision,
        reason: trial.reason,
        tradeoff: trial.tradeoff,
        recommendation_score: trial.recommendation_score,
        expected_metrics: {
          task_satisfaction_avg: trial.task_satisfaction_avg,
          quality_total: trial.quality_total,
          high_risk_count: trial.high_risk_count,
          medium_risk_count: trial.medium_risk_count,
          partial_group_count: trial.partial_group_count,
          unsatisfied_group_count: trial.unsatisfied_group_count,
          used_bandwidth_mhz: trial.used_bandwidth_mhz,
        },
        expected_deltas: trial.deltas,
        constraint_changes: trial.constraint_changes,
      },
    };
    const message = trial.suggested_message || `采用“${trial.label}”试算策略重新规划。`;
    applyReplanOverridesToForm(overrides, message);
    setSuggestedPayloadOverride(overrides);
    const result = await runAction(() => previewTaskReplan(project.id, buildReplanPayload(overrides, message)), `已采用“${trial.label}”生成变更清单`);
    if (result) {
      setReplanPreview(result);
      setReplanConfirmed(false);
      document.getElementById('task-replan-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  async function selectPlan(selected: TaskComparisonPlan) {
    if (!project || selected.status !== 'success') return;
    setPlan({
      run_id: selected.run_id,
      status: selected.status,
      message: selected.message,
      summary: {
        task_satisfaction_avg: selected.task_satisfaction_avg,
        full_group_count: selected.full_group_count,
        partial_group_count: selected.partial_group_count,
        unsatisfied_group_count: selected.unsatisfied_group_count,
        used_bandwidth_mhz: selected.used_bandwidth_mhz,
      },
    });
    await loadVisualization(project.id, selected.run_id);
  }

  async function handleSelectVersion(run: TaskVersionRun) {
    if (!project) return;
    const selected = await runAction(() => loadVisualization(project.id, run.run_id), `已切换到规划版本 #${run.run_id}`);
    if (selected) {
      setPlan({
        run_id: run.run_id,
        status: 'success',
        message: run.message,
        summary: selected.summary,
      });
    }
  }

  async function selectCapacityBatchRun(run: TaskCapacityBatchExecutionResult['runs'][number]) {
    if (!project || !run.run_id) return;
    const selected = await runAction(() => loadVisualization(project.id, run.run_id), `已切换到${run.batch_name || '批次'}子规划 #${run.run_id}`);
    if (selected) {
      setPlan({
        run_id: run.run_id,
        status: run.status,
        message: run.message,
        summary: selected.summary,
      });
    }
  }

  async function handleCapacityRiskClosure() {
    if (!project) return;
    const result = await runAction(
      () =>
        executeTaskCapacityRiskClosure(project.id, {
          objective,
          constraint_weights: constraintWeights,
          strategy_profile: strategyProfile,
        }),
      '已完成跨批风险闭环重算',
    );
    if (!result) return;
    setCapacityBatchExecution(result);
    setNotice({ type: result.ok ? 'success' : 'info', text: result.closure?.summary || result.message });
    await refreshVersions(project.id);
    const firstRun = result.runs.find((item) => item.status === 'success') ?? result.runs[0];
    if (firstRun?.run_id) {
      setPlan({
        run_id: firstRun.run_id,
        status: firstRun.status,
        message: firstRun.message,
        summary: firstRun.summary,
      });
      await loadVisualization(project.id, firstRun.run_id);
    }
    document.querySelector('.capacity-batch-execution-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  async function handleReuseVersionStrategy(run: TaskVersionRun) {
    if (!project) return;
    const summary = run.summary ?? {};
    const reusedObjective = stringValue(summary.requested_objective) || stringValue(summary.effective_objective) || run.objective;
    const reusedWeights = constraintWeightsValue(summary.constraint_weights);
    const reusedStrategy = stringValue(summary.strategy_profile) || strategyProfile;
    const message = `复用版本 #${run.run_id} 的${objectiveLabel(reusedObjective)}策略作为基线继续重规划`;
    const overrides: Partial<TaskReplanPayload> = {
      message,
      objective: reusedObjective,
      base_run_id: run.run_id,
      reuse_strategy_from_run_id: run.run_id,
      strategy_profile: reusedStrategy,
    };
    if (Object.keys(reusedWeights).length) {
      overrides.constraint_weights = reusedWeights;
      setConstraintWeights((current) => ({ ...current, ...reusedWeights }));
    }
    setObjective(reusedObjective);
    setStrategyProfile(reusedStrategy);
    applyReplanOverridesToForm(overrides, message);
    setSuggestedPayloadOverride(overrides);
    const result = await runAction(async () => {
      await loadVisualization(project.id, run.run_id);
      return previewTaskReplan(project.id, buildReplanPayload(overrides, message));
    }, `已复用版本 #${run.run_id} 策略`);
    if (result) {
      setPlan({
        run_id: run.run_id,
        status: 'success',
        message: run.message,
        summary: run.summary,
      });
      setReplanPreview(result);
      setReplanConfirmed(false);
      document.getElementById('task-replan-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  async function handleAdoptVersion(run: TaskVersionRun) {
    if (!project) return;
    const result = await runAction(() => adoptTaskPlan(project.id, run.run_id), `已正式采纳规划版本 #${run.run_id}`);
    if (!result) return;
    await refreshVersions(project.id);
    await handleSelectVersion(run);
  }

  async function handleRollbackVersion(run: TaskVersionRun) {
    if (!project || !run.snapshot_available) return;
    if (!window.confirm(`确认恢复版本 #${run.run_id} 的完整任务、装备、链路、规则和频谱资源输入？系统将生成新的回滚版本。`)) return;
    const result = await runAction(() => rollbackTaskPlan(project.id, run.run_id), `已恢复版本 #${run.run_id} 并生成新方案`);
    if (!result?.run_id) return;
    setPlan(result);
    await Promise.all([refreshTaskDataSummary(project.id), refreshSpectrumRules(project.id)]);
    setTaskDataRevision((current) => current + 1);
    await loadVisualization(project.id, result.run_id);
  }

  async function handleReplan() {
    if (!project) return;
    if (!replanConfirmed) {
      setNotice({ type: 'info', text: '请先预览变更清单，确认后再执行重规划。' });
      return;
    }
    const payload = buildReplanPayload(suggestedPayloadOverride ?? undefined);
    const result = await runAction(() => replanTaskProject(project.id, payload), '已按新要求重算');
    if (result?.run_id) {
      setReplanPreview(null);
      setStrategyTrials(null);
      setReplanConfirmed(false);
      setSuggestedPayloadOverride(null);
      setPlan({
        run_id: result.run_id,
        status: 'success',
        message: result.reply,
        summary: result.summary,
      });
      await loadVisualization(project.id, result.run_id);
      await refreshSpectrumRules(project.id);
    }
  }

  function resetReplanPreview() {
    setReplanPreview(null);
    setStrategyTrials(null);
    setReplanConfirmed(false);
    setSuggestedPayloadOverride(null);
  }

  async function handleApplyAgentAction(action: AgentSuggestedAction) {
    if (!project) return;
    const operation = stringValue(action.deterministic_payload.operation);
    if (operation === 'task_performance_batch') {
      await handleBatchPerformanceTest();
      return;
    }
    if (operation === 'capacity_batch_planning') {
      document.querySelector('.scale-evidence-card')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      const profile = recordValue(action.deterministic_payload.capacity_profile);
      const batchPlan = recordValue(action.deterministic_payload.batch_plan);
      if (batchPlan.available && numberValue(batchPlan.batch_count)) {
        const result = await runAction(
          () =>
            executeTaskCapacityBatches(project.id, {
              base_run_id: agentAssessment?.run_id ?? plan?.run_id ?? null,
              objective: stringValue(action.deterministic_payload.objective) || stringValue(plan?.summary?.requested_objective) || objective,
              constraint_weights: constraintWeights,
              strategy_profile: strategyProfile,
            }),
          '已生成容量子规划版本',
        );
        if (result) {
          setCapacityBatchExecution(result);
          await refreshVersions(project.id);
          const firstRun = result.runs.find((item) => item.status === 'success') ?? result.runs[0];
          if (firstRun?.run_id) {
            setPlan({
              run_id: firstRun.run_id,
              status: firstRun.status,
              message: firstRun.message,
              summary: firstRun.summary,
            });
            await loadVisualization(project.id, firstRun.run_id);
          }
          document.querySelector('.capacity-batch-execution-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        return;
      }
      const recommended = recordValue(profile.recommended);
      const units = numberValue(recommended.task_unit_count);
      const groups = numberValue(recommended.equipment_group_count);
      const batchCount = numberValue(batchPlan.batch_count);
      setNotice({
        type: 'info',
        text:
          batchCount
            ? `已生成 ${batchCount} 个容量拆批预案，建议按批次复核跨批保护约束`
            : units && groups
            ? `建议将大规模任务拆为不超过 ${units} 个任务单元、${groups} 个装备组的批次后复测`
            : '已定位到容量边界画像，请按任务区域或频段池分批规划后复测',
      });
      return;
    }
    if (operation === 'export_report') {
      if (reportUrl) {
        window.open(reportUrl, '_blank', 'noopener,noreferrer');
        setNotice({ type: 'success', text: '已打开当前规划报告' });
      } else {
        setNotice({ type: 'info', text: '请先完成一次成功规划后再打开报告' });
      }
      return;
    }
    if (operation === 'preview_replan_from_suggestion') {
      document.getElementById('task-replan-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setNotice({ type: 'info', text: '请选择上方具体建议动作，或在重规划区手动调整约束后预览' });
      return;
    }
    if (operation === 'select_task_run') {
      const runId = numberValue(action.deterministic_payload.run_id);
      if (!runId) {
        setNotice({ type: 'error', text: '建议动作缺少可切换的规划版本' });
        return;
      }
      const selected = await runAction(() => loadVisualization(project.id, runId), `已切换到规划版本 #${runId}`);
      if (selected) {
        setPlan({
          run_id: runId,
          status: 'success',
          message: action.suggested_message,
          summary: selected.summary,
        });
      }
      return;
    }

    const overrides = replanOverridesFromAction(action);
    applyReplanOverridesToForm(overrides, action.suggested_message);
    const payload = buildReplanPayload(overrides, action.suggested_message);
    setSuggestedPayloadOverride(overrides);
    const result = await runAction(() => previewTaskReplan(project.id, payload), '已按建议生成变更清单');
    if (result) {
      setReplanPreview(result);
      setReplanConfirmed(false);
      document.getElementById('task-replan-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  function applyReplanOverridesToForm(overrides: Partial<TaskReplanPayload>, message: string) {
    setReplanMessage(message);
    if (overrides.objective) setObjective(overrides.objective);
    if (overrides.strategy_profile) setStrategyProfile(overrides.strategy_profile);
    if (overrides.constraint_weights) setConstraintWeights((current) => ({ ...current, ...overrides.constraint_weights }));
    if (overrides.required_full_targets?.length) setRequiredFullTarget(overrides.required_full_targets.join(', '));
    if (overrides.avoid_band_groups?.length) setAvoidBand(overrides.avoid_band_groups[0]);
    if (typeof overrides.allow_low_priority_degrade === 'boolean') setAllowLowPriorityDegrade(overrides.allow_low_priority_degrade);
    const forcedEntries = Object.entries(overrides.forced_band_groups ?? {});
    if (forcedEntries.length) {
      setForcedTarget(forcedEntries[0][0]);
      setForcedBand(forcedEntries[0][1]);
    }
    const firstForbidden = overrides.forbidden_ranges?.[0];
    if (firstForbidden) {
      setForbidBand(firstForbidden.band_group ?? '');
      setForbidStart(String(firstForbidden.start_mhz));
      setForbidEnd(String(firstForbidden.end_mhz));
    }
    const firstAvailable = overrides.available_ranges?.[0];
    if (firstAvailable) {
      setAvailableBand(firstAvailable.band_group ?? '');
      setAvailableStart(String(firstAvailable.start_mhz));
      setAvailableEnd(String(firstAvailable.end_mhz));
    }
    const firstPriority = overrides.priority_updates?.[0];
    if (firstPriority) {
      setPriorityTarget(firstPriority.target);
      setPriorityValue(String(firstPriority.priority));
    }
    const firstSatisfaction = overrides.satisfaction_updates?.[0];
    if (firstSatisfaction) {
      setSatisfactionUnit(firstSatisfaction.task_unit_id);
      setSatisfactionValue(String(Math.round(firstSatisfaction.min_satisfaction_ratio * 100)));
    }
  }

  function buildReplanPayload(overrides: Partial<TaskReplanPayload> = {}, messageOverride?: string): TaskReplanPayload {
    const forbidden =
      Number(forbidStart) && Number(forbidEnd)
        ? [{ band_group: forbidBand || undefined, start_mhz: Number(forbidStart), end_mhz: Number(forbidEnd), reason: '界面追加禁用' }]
        : [];
    const available =
      Number(availableStart) && Number(availableEnd)
        ? [{ band_group: availableBand || undefined, start_mhz: Number(availableStart), end_mhz: Number(availableEnd), reason: '界面补充可用频段' }]
        : [];
    const priority_updates = priorityTarget.trim() ? [{ target: priorityTarget.trim(), priority: Number(priorityValue) || 8 }] : [];
    const satisfaction_updates = satisfactionUnit.trim()
      ? [{ task_unit_id: satisfactionUnit.trim(), min_satisfaction_ratio: Math.max(10, Math.min(100, Number(satisfactionValue) || 70)) / 100 }]
      : [];
    const basePayload: TaskReplanPayload = {
      message: messageOverride ?? replanMessage,
      objective,
      base_run_id: plan?.run_id ?? null,
      reuse_strategy_from_run_id: null,
      locked_equipment_group_ids: lockedGroupIds,
      locked_task_unit_ids: lockedTaskUnitIds,
      available_ranges: available,
      forbidden_ranges: forbidden,
      priority_updates,
      satisfaction_updates,
      equipment_events: dynamicEvents.equipment_events,
      unit_position_updates: dynamicEvents.unit_position_updates,
      interference_sources: dynamicEvents.interference_sources,
      avoid_band_groups: avoidBand ? [avoidBand] : [],
      forced_band_groups: forcedTarget.trim() && forcedBand ? { [forcedTarget.trim()]: forcedBand } : {},
      required_full_targets: splitList(requiredFullTarget),
      allow_low_priority_degrade: allowLowPriorityDegrade,
      constraint_weights: constraintWeights,
      strategy_profile: strategyProfile,
    };
    return {
      ...basePayload,
      ...overrides,
      message: messageOverride ?? overrides.message ?? basePayload.message,
      objective: overrides.objective ?? basePayload.objective,
      base_run_id: overrides.base_run_id ?? basePayload.base_run_id,
      reuse_strategy_from_run_id: overrides.reuse_strategy_from_run_id ?? basePayload.reuse_strategy_from_run_id,
      locked_equipment_group_ids: overrides.locked_equipment_group_ids ?? basePayload.locked_equipment_group_ids,
      locked_task_unit_ids: overrides.locked_task_unit_ids ?? basePayload.locked_task_unit_ids,
      available_ranges: overrides.available_ranges ?? basePayload.available_ranges,
      forbidden_ranges: overrides.forbidden_ranges ?? basePayload.forbidden_ranges,
      priority_updates: overrides.priority_updates ?? basePayload.priority_updates,
      satisfaction_updates: overrides.satisfaction_updates ?? basePayload.satisfaction_updates,
      equipment_events: overrides.equipment_events ?? basePayload.equipment_events,
      unit_position_updates: overrides.unit_position_updates ?? basePayload.unit_position_updates,
      interference_sources: overrides.interference_sources ?? basePayload.interference_sources,
      avoid_band_groups: overrides.avoid_band_groups ?? basePayload.avoid_band_groups,
      forced_band_groups: overrides.forced_band_groups ?? basePayload.forced_band_groups,
      required_full_targets: overrides.required_full_targets ?? basePayload.required_full_targets,
      allow_low_priority_degrade: overrides.allow_low_priority_degrade ?? basePayload.allow_low_priority_degrade,
      constraint_weights: { ...basePayload.constraint_weights, ...(overrides.constraint_weights ?? {}) },
      strategy_profile: overrides.strategy_profile ?? basePayload.strategy_profile,
      trial_context: overrides.trial_context ?? basePayload.trial_context,
    };
  }

  function toggleLockedGroup(groupId: string) {
    setLockedGroupIds((current) => (current.includes(groupId) ? current.filter((item) => item !== groupId) : [...current, groupId]));
    resetReplanPreview();
  }

  function toggleLockedTaskUnit(unitId: string) {
    setLockedTaskUnitIds((current) => (current.includes(unitId) ? current.filter((item) => item !== unitId) : [...current, unitId]));
    resetReplanPreview();
  }

  function updateParametricPayload(key: keyof ParametricTaskDemoPayload, value: number) {
    setParametricPayload((current) => ({ ...current, [key]: value }));
  }

  const activeModuleTitle = dashboardModuleTitles[activeModule];
  const pageRiskItems = visualization?.risk_items ?? [];
  const pageSummary = visualization?.summary ?? plan?.summary ?? {};
  const pageTaskUnitCount = dashboardFirstNumber(
    numberValue(pageSummary.task_unit_count),
    visualization?.task_units.length,
    numberValue(validation?.summary.task_unit_count),
  );
  const pageTopBands = [...(visualization?.band_usage ?? [])].sort((left, right) => right.utilization_pct - left.utilization_pct).slice(0, 4);

  return (
    <main className="shell task-shell dashboard-shell">
      <div className="dashboard-frame">
        <DashboardSideRail
          project={project}
          plan={plan}
          visualization={visualization}
          agentAssessment={agentAssessment}
          reportUrl={reportUrl}
          activeModule={activeModule}
          onModuleChange={setActiveModule}
        />
        <div className="dashboard-main-stack">
          <ReferenceTopBar project={project} plan={plan} reportUrl={reportUrl} title={activeModuleTitle} />
          <ReferenceProjectBar
            project={project}
            mission={taskMission}
            taskUnitCount={taskDataSummary.taskUnits}
            plan={plan}
            validation={validation}
            onCompare={handleCompare}
            busy={busy}
          />

          {notice && <div className={`notice ${notice.type}`}>{notice.text}</div>}

          <div className="dashboard-page-shell" aria-label={activeModuleTitle}>
            {activeModule === 'overview' && (
              <TaskDashboardOverview
                project={project}
                validation={validation}
                plan={plan}
                visualization={visualization}
                agentAssessment={agentAssessment}
                performance={performance}
                versions={versions}
                busy={busy}
                reportUrl={reportUrl}
                onValidate={handleValidate}
                onPlan={handlePlan}
                onCompare={handleCompare}
                onRunBatch={handleBatchPerformanceTest}
              />
            )}

            {activeModule === 'tasks' && (
              <section id="dashboard-data" className="workflow task-workflow dashboard-section">
        <TaskWorkbench
          projectId={project?.id ?? null}
          busy={busy}
          revision={taskDataRevision}
          onDataChange={applyTaskDataSummary}
        />
        <div className="panel setup">
          <div className="panel-title">
            <WandSparkles size={18} />
            <h2>项目与仿真数据</h2>
          </div>
          <div className="row">
            <input
              id="project-name"
              aria-label="项目名称"
              name="project_name"
              value={projectName}
              onChange={(event) => setProjectName(event.target.value)}
            />
            <button onClick={handleCreateProject} disabled={busy}>
              <Play size={16} />
              创建
            </button>
          </div>
          <div className="project-switcher">
            <label htmlFor="existing-project">已有项目</label>
            <div className="project-switcher-row">
              <select
                id="existing-project"
                name="existing_project"
                value={project?.id ?? ''}
                onChange={(event) => {
                  const selected = projects.find((item) => item.id === Number(event.target.value));
                  if (selected) void openProject(selected);
                }}
                disabled={busy || projects.length === 0}
              >
                <option value="">{projects.length ? '选择项目' : '暂无已有项目'}</option>
                {projects.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
              <button type="button" className="icon-button" onClick={refreshProjectList} disabled={busy} title="刷新项目列表" aria-label="刷新项目列表">
                <RefreshCw size={16} />
              </button>
            </div>
            {project && (
              <div className="project-data-summary" aria-label="当前项目数据概况">
                <span>任务单元 <strong>{taskDataSummary.taskUnits}</strong></span>
                <span>装备组 <strong>{taskDataSummary.equipmentGroups}</strong></span>
                <span>任务阶段 <strong>{taskDataSummary.phases}</strong></span>
                <span>任务链路 <strong>{taskDataSummary.links}</strong></span>
                <span>频谱规则 <strong>{taskDataSummary.spectrumRules}</strong></span>
                <span>创建时间 <strong>{formatProjectDate(project.created_at)}</strong></span>
              </div>
            )}
          </div>
          <label className="field-label" htmlFor="task-scenario">
            样例任务场景
          </label>
          <select id="task-scenario" name="task_scenario" value={scenario} onChange={(event) => setScenario(event.target.value)}>
            {(scenarios.length ? scenarios : [{ key: 'baseline', name: '高密度联合作战基线', description: '' }]).map((item) => (
              <option key={item.key} value={item.key}>
                {item.name}
              </option>
            ))}
          </select>
          <p className="objective-help">{scenarios.find((item) => item.key === scenario)?.description}</p>
          <button className="wide secondary" onClick={handleGenerateDemo} disabled={busy || !project}>
            <WandSparkles size={16} />
            生成样例场景
          </button>
          <div className="parametric-sample">
            <div className="parametric-head">
              <strong>参数化扩展样例</strong>
              <span>按任务数量、雷达/无人机占比和禁用保护密度生成</span>
            </div>
            <div className="mini-grid">
              <NumberField
                name="parametric_unit_count"
                label="任务单元"
                value={parametricPayload.unit_count}
                min={6}
                max={72}
                step={1}
                onChange={(value) => updateParametricPayload('unit_count', value)}
              />
              <NumberField
                name="parametric_density_multiplier"
                label="装备密度"
                value={parametricPayload.density_multiplier}
                min={0.8}
                max={3.5}
                step={0.1}
                onChange={(value) => updateParametricPayload('density_multiplier', value)}
              />
              <NumberField
                name="parametric_radar_ratio"
                label="雷达占比%"
                value={parametricPayload.radar_ratio}
                min={0}
                max={45}
                step={1}
                onChange={(value) => updateParametricPayload('radar_ratio', value)}
              />
              <NumberField
                name="parametric_uav_ratio"
                label="无人机占比%"
                value={parametricPayload.uav_ratio}
                min={0}
                max={45}
                step={1}
                onChange={(value) => updateParametricPayload('uav_ratio', value)}
              />
              <NumberField
                name="parametric_protection_density"
                label="保护密度"
                value={parametricPayload.protection_density}
                min={0}
                max={5}
                step={1}
                onChange={(value) => updateParametricPayload('protection_density', value)}
              />
              <NumberField
                name="parametric_forbidden_density"
                label="禁用密度"
                value={parametricPayload.forbidden_density}
                min={0}
                max={5}
                step={1}
                onChange={(value) => updateParametricPayload('forbidden_density', value)}
              />
            </div>
            <button className="wide" onClick={handleGenerateParametricDemo} disabled={busy || !project}>
              <WandSparkles size={16} />
              生成参数化样例
            </button>
          </div>
          <div className="template-links">
            <a href={url('/api/templates/task-units.xlsx')}>
              <Download size={15} />
              任务单元模板
            </a>
            <a href={url('/api/templates/equipment-groups.xlsx')}>
              <Download size={15} />
              装备组模板
            </a>
            <a href={url('/api/templates/spectrum-rules.xlsx')}>
              <Download size={15} />
              频段规则模板
            </a>
          </div>
        </div>

        <div className="panel">
          <div className="panel-title">
            <Upload size={18} />
            <h2>上传数据</h2>
          </div>
          <FilePicker name="task_units_excel" label="任务单元 Excel" file={taskUnitFile} onChange={setTaskUnitFile} />
          <button className="wide" onClick={() => handleUpload('task-units')} disabled={busy || !project}>
            上传任务单元
          </button>
          <FilePicker name="equipment_groups_excel" label="装备组 Excel" file={equipmentFile} onChange={setEquipmentFile} />
          <button className="wide" onClick={() => handleUpload('equipment-groups')} disabled={busy || !project}>
            上传装备组
          </button>
          <FilePicker name="spectrum_rules_excel" label="频段规则 Excel" file={spectrumFile} onChange={setSpectrumFile} />
          <button className="wide" onClick={() => handleUpload('spectrum-rules')} disabled={busy || !project}>
            上传频段规则
          </button>
        </div>

        <div className="panel">
          <div className="panel-title">
            <FileCheck2 size={18} />
            <h2>规划目标</h2>
          </div>
          <label className="field-label" htmlFor="task-objective">
            目标函数
          </label>
          <select id="task-objective" name="task_objective" value={objective} onChange={(event) => setObjective(event.target.value)}>
            {objectives.map((item) => (
              <option key={item.objective} value={item.objective}>
                {item.label}
              </option>
            ))}
          </select>
          <p className="objective-help">{objectives.find((item) => item.objective === objective)?.description}</p>
          <WeightControlPanel
            templates={sampleCatalog?.weight_templates ?? []}
            strategyProfile={strategyProfile}
            weights={constraintWeights}
            onTemplateChange={(template) => {
              setStrategyProfile(template.key);
              setConstraintWeights(template.weights);
              resetReplanPreview();
            }}
            onWeightChange={(key, value) => {
              setConstraintWeights((current) => ({ ...current, [key]: value }));
              resetReplanPreview();
            }}
          />
          <div className="button-grid">
            <button onClick={handleValidate} disabled={busy || !project}>
              <FileCheck2 size={16} />
              校验
            </button>
            <button onClick={handlePlan} disabled={busy || !project}>
              <RefreshCw size={16} />
              规划
            </button>
            <button onClick={handleCompare} disabled={busy || !project}>
              <BarChart3 size={16} />
              多方案
            </button>
          </div>
          {project && plan?.status === 'success' && (
            <a className="export" href={url(`/api/projects/${project.id}/task-export.xlsx?run=${plan.run_id}`)}>
              <Download size={15} />
              导出结果
            </a>
          )}
        </div>
      </section>
            )}

            {activeModule === 'spectrumResources' && (
              <div id="dashboard-rules" className="dashboard-section spectrum-resource-stack">
                <SpectrumResourcePanel projectId={project?.id ?? null} busy={busy} />
                <SpectrumRuleManagerPanel
                  busy={busy}
                  projectId={project?.id ?? null}
                  rules={spectrumRules}
                  bands={visualization?.band_usage.map((item) => item.band_group) ?? []}
                  onRulesChange={() => project && refreshSpectrumRules(project.id)}
                  runAction={runAction}
                />
              </div>
            )}

            {activeModule === 'plan' && (
              <section id="dashboard-plan" className="content-grid task-content-grid dashboard-section">
                <PlanningResultPanel data={visualization} />
                <ValidationPanel data={validation} />
                <TaskComparisonPanel data={comparison} projectId={project?.id ?? null} onSelect={selectPlan} />
              </section>
            )}

            {activeModule === 'spectrum' && (
              <div id="dashboard-spectrum" className="dashboard-section dashboard-page-wide">
                <ReferenceSpectrumPanorama bands={visualization?.spectrum_timeline ?? []} assignments={visualization?.assignments ?? []} riskCount={pageRiskItems.length} />
              </div>
            )}

            {activeModule === 'interference' && (
              <div id="dashboard-interference" className="dashboard-section dashboard-page-wide">
                <InterferenceAnalysisPanel risks={pageRiskItems} bands={pageTopBands} />
              </div>
            )}

            {activeModule === 'risk' && (
              <div id="dashboard-agent" className="dashboard-section">
                <TaskAgentAssessmentPanel
                  data={agentAssessment}
                  busy={busy}
                  planReady={Boolean(plan?.run_id)}
                  projectReady={Boolean(project)}
                  onRefresh={() => project && refreshAgentAssessment(project.id, plan?.run_id ?? visualizationRunId)}
                  onApplyAction={handleApplyAgentAction}
                />
              </div>
            )}

            {activeModule === 'replan' && (
              <section id="dashboard-replan" className="content-grid task-content-grid dashboard-section">
                <DynamicEventPanel value={dynamicEvents} onChange={(value) => { setDynamicEvents(value); resetReplanPreview(); }} busy={busy} />
                <ReplanPanel
                  busy={busy}
                  projectReady={Boolean(project)}
                  visualization={visualization}
                  lockedGroupIds={lockedGroupIds}
                  lockedTaskUnitIds={lockedTaskUnitIds}
                  preview={replanPreview}
                  strategyTrials={strategyTrials}
                  confirmed={replanConfirmed}
                  replanMessage={replanMessage}
                  forbidBand={forbidBand}
                  forbidStart={forbidStart}
                  forbidEnd={forbidEnd}
                  availableBand={availableBand}
                  availableStart={availableStart}
                  availableEnd={availableEnd}
                  priorityTarget={priorityTarget}
                  priorityValue={priorityValue}
                  satisfactionUnit={satisfactionUnit}
                  satisfactionValue={satisfactionValue}
                  avoidBand={avoidBand}
                  forcedTarget={forcedTarget}
                  forcedBand={forcedBand}
                  requiredFullTarget={requiredFullTarget}
                  allowLowPriorityDegrade={allowLowPriorityDegrade}
                  onMessageChange={(value) => {
                    setReplanMessage(value);
                    resetReplanPreview();
                  }}
                  onForbidBandChange={(value) => {
                    setForbidBand(value);
                    resetReplanPreview();
                  }}
                  onForbidStartChange={(value) => {
                    setForbidStart(value);
                    resetReplanPreview();
                  }}
                  onForbidEndChange={(value) => {
                    setForbidEnd(value);
                    resetReplanPreview();
                  }}
                  onAvailableBandChange={(value) => {
                    setAvailableBand(value);
                    resetReplanPreview();
                  }}
                  onAvailableStartChange={(value) => {
                    setAvailableStart(value);
                    resetReplanPreview();
                  }}
                  onAvailableEndChange={(value) => {
                    setAvailableEnd(value);
                    resetReplanPreview();
                  }}
                  onPriorityTargetChange={(value) => {
                    setPriorityTarget(value);
                    resetReplanPreview();
                  }}
                  onPriorityValueChange={(value) => {
                    setPriorityValue(value);
                    resetReplanPreview();
                  }}
                  onSatisfactionUnitChange={(value) => {
                    setSatisfactionUnit(value);
                    resetReplanPreview();
                  }}
                  onSatisfactionValueChange={(value) => {
                    setSatisfactionValue(value);
                    resetReplanPreview();
                  }}
                  onAvoidBandChange={(value) => {
                    setAvoidBand(value);
                    resetReplanPreview();
                  }}
                  onForcedTargetChange={(value) => {
                    setForcedTarget(value);
                    resetReplanPreview();
                  }}
                  onForcedBandChange={(value) => {
                    setForcedBand(value);
                    resetReplanPreview();
                  }}
                  onRequiredFullTargetChange={(value) => {
                    setRequiredFullTarget(value);
                    resetReplanPreview();
                  }}
                  onAllowLowPriorityDegradeChange={(value) => {
                    setAllowLowPriorityDegrade(value);
                    resetReplanPreview();
                  }}
                  onToggleLocked={toggleLockedGroup}
                  onToggleLockedTaskUnit={toggleLockedTaskUnit}
                  onPreview={handlePreviewReplan}
                  onPreviewStrategies={handlePreviewStrategyTrials}
                  onApplyStrategyTrial={handleApplyStrategyTrial}
                  onConfirmChange={setReplanConfirmed}
                  onReplan={handleReplan}
                />
                <EquipmentLibraryPanel items={equipmentLibrary} />
              </section>
            )}

            {activeModule === 'decision' && (
              <section id="dashboard-decision" className="content-grid task-content-grid dashboard-section dashboard-decision-page">
                <TaskComparisonPanel data={comparison} projectId={project?.id ?? null} onSelect={selectPlan} />
                <DecisionAssistantPanel
                  project={project}
                  plan={plan}
                  visualization={visualization}
                  agentAssessment={agentAssessment}
                  comparison={comparison}
                  reportUrl={reportUrl}
                  busy={busy}
                  onPlan={handlePlan}
                  onCompare={handleCompare}
                  onSelectPlan={selectPlan}
                  onRunBatch={handleBatchPerformanceTest}
                  onApplyAction={handleApplyAgentAction}
                />
              </section>
            )}

            {activeModule === 'assurance' && (
              <div id="dashboard-assurance" className="dashboard-section">
                <ReferenceTaskMatrix assignments={visualization?.assignments ?? []} taskUnitCount={pageTaskUnitCount} />
              </div>
            )}

            {activeModule === 'report' && (
              <section id="dashboard-report" className="panel report-panel dashboard-section">
                <div className="report-header">
                  <h2>任务规划报告</h2>
                  {plan && <span>{plan.message}</span>}
                </div>
                {reportUrl ? <iframe title="任务规划报告" src={reportUrl} /> : <div className="empty">等待成功规划结果</div>}
              </section>
            )}

            {activeModule === 'system' && (
              <div id="dashboard-audit" className="dashboard-section dashboard-system-page">
                <VersionAuditPanel
                  data={versions}
                  activeRunId={visualizationRunId ?? plan?.run_id ?? null}
                  onRefresh={() => project && refreshVersions(project.id)}
                  onSelectRun={handleSelectVersion}
                  onReuseRun={handleReuseVersionStrategy}
                  onAdoptRun={handleAdoptVersion}
                  onRollbackRun={handleRollbackVersion}
                />
                <PlanningPerformancePanel busy={busy} data={performance} onRun={handlePerformanceTest} onRunBatch={handleBatchPerformanceTest} />
                <CapacityBatchExecutionPanel
                  data={capacityBatchExecution}
                  projectId={project?.id ?? null}
                  busy={busy}
                  onSelectRun={selectCapacityBatchRun}
                  onRiskClosure={handleCapacityRiskClosure}
                />
                <SampleCatalogPanel catalog={sampleCatalog} />
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}

function ReferenceTopBar({ project, plan, reportUrl, title }: { project: Project | null; plan: PlanResult | null; reportUrl: string; title: string }) {
  const clock = new Date().toLocaleString('zh-CN', {
    hour12: false,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
  const runStatus = plan?.status === 'success' ? '系统运行正常' : project ? '项目待规划' : '等待创建项目';
  return (
    <header className="reference-topbar" aria-label="顶部运行状态栏">
      <div className="reference-title">
        <button className="icon-button ghost" type="button" aria-label="展开导航">
          <Menu size={20} />
        </button>
        <strong>{title}</strong>
      </div>
      <div className="reference-utility">
        <span className={`system-health ${plan?.status === 'success' ? 'online' : 'pending'}`}>
          <i />
          {runStatus}
        </span>
        <span className="utility-time">
          <Clock3 size={16} />
          {clock}
        </span>
        <button className="icon-button ghost has-badge" type="button" aria-label="通知">
          <Bell size={18} />
          <em>{plan?.status === 'success' ? '8' : '0'}</em>
        </button>
        <button className="icon-button ghost has-badge" type="button" aria-label="消息">
          <Mail size={18} />
          <em>{reportUrl ? '3' : '0'}</em>
        </button>
        <button className="icon-button ghost" type="button" aria-label="帮助">
          <HelpCircle size={18} />
        </button>
        <span className="logout-link">退出</span>
      </div>
    </header>
  );
}

function ReferenceProjectBar({
  project,
  mission,
  taskUnitCount,
  plan,
  validation,
  busy,
  onCompare,
}: {
  project: Project | null;
  mission: MissionTaskRecord | null;
  taskUnitCount: number;
  plan: PlanResult | null;
  validation: TaskValidationResult | null;
  busy: boolean;
  onCompare: () => void;
}) {
  const validatedUnits = numberValue(validation?.summary.task_unit_count) ?? (taskUnitCount || null);
  const missionRange = mission?.starts_at || mission?.ends_at
    ? `${formatMissionTime(mission.starts_at)} ～ ${formatMissionTime(mission.ends_at)}`
    : '未设置';
  const statusText = plan?.status === 'success'
    ? '规划进行中'
    : validation
      ? '数据已校验'
      : mission || taskUnitCount
        ? '任务筹划中'
        : project
          ? '待接入数据'
          : '未创建项目';
  const tone = plan?.status === 'success' ? 'running' : validation || mission || taskUnitCount ? 'ready' : 'pending';
  return (
    <section className="reference-project-bar" aria-label="项目状态摘要">
      <div className="project-meta">
        <span>项目名称：</span>
        <strong>{project?.name ?? '演训-东部战区-2025A'}</strong>
      </div>
      <span className={`project-pill ${tone}`}>{statusText}</span>
      <div className="project-meta">
        <span>时间范围：</span>
        <strong>{missionRange}</strong>
      </div>
      <div className="project-meta compact">
        <span>任务单元：</span>
        <strong>{validatedUnits ?? '待生成'}</strong>
      </div>
      <div className="project-meta compact">
        <span>方案版本：</span>
        <strong>{plan?.run_id ? `v${plan.run_id}.0` : '未生成'}</strong>
      </div>
      <button className="outline-action" type="button" onClick={onCompare} disabled={busy || !project}>
        方案对比
      </button>
    </section>
  );
}

function DecisionAssistantPanel({
  project,
  plan,
  visualization,
  agentAssessment,
  comparison,
  reportUrl,
  busy,
  onPlan,
  onCompare,
  onSelectPlan,
  onRunBatch,
  onApplyAction,
}: {
  project: Project | null;
  plan: PlanResult | null;
  visualization: TaskVisualizationData | null;
  agentAssessment: TaskAgentAssessment | null;
  comparison: TaskComparisonResult | null;
  reportUrl: string;
  busy: boolean;
  onPlan: () => void;
  onCompare: () => void;
  onSelectPlan: (plan: TaskComparisonPlan) => void;
  onRunBatch: () => void;
  onApplyAction: (action: AgentSuggestedAction) => void;
}) {
  const [activeTab, setActiveTab] = useState<'replan' | 'decision' | 'risk'>('replan');
  const summary = visualization?.summary ?? plan?.summary ?? {};
  const riskItems = visualization?.risk_items ?? [];
  const highRiskCount = riskItems.filter((item) => isHighRiskSeverity(item.severity)).length;
  const mediumRiskCount = riskItems.filter((item) => isMediumRiskSeverity(item.severity)).length;
  const plans = comparison?.plans ?? [];
  const actions = agentAssessment?.next_actions ?? [];
  const recommendationCards = plans.length
    ? plans.slice(0, 3)
    : [
        {
          run_id: plan?.run_id ?? 0,
          label: '当前方案',
          description: plan?.message ?? '完成规划后显示当前方案指标。',
          task_satisfaction_avg: numberValue(summary.task_satisfaction_avg) ?? 0,
          high_risk_count: numberValue(summary.high_risk_count) ?? highRiskCount,
          used_bandwidth_mhz: numberValue(summary.used_bandwidth_mhz) ?? 0,
          recommendation_reason: stringValue(summary.leader_summary) || '以当前目标函数生成的基线方案。',
          recommended: true,
        } as TaskComparisonPlan,
      ];

  return (
    <aside className="decision-assistant-panel" aria-label="智能决策助手">
      <div className="assistant-header">
        <div>
          <Bot size={20} />
          <strong>智能决策助手</strong>
        </div>
        <button className="icon-button ghost" type="button" aria-label="收起助手">
          <ChevronGlyph />
        </button>
      </div>
      <div className="assistant-tabs" role="tablist" aria-label="助手视图">
        <button className={activeTab === 'replan' ? 'active' : ''} type="button" onClick={() => setActiveTab('replan')}>
          动态重规划
        </button>
        <button className={activeTab === 'decision' ? 'active' : ''} type="button" onClick={() => setActiveTab('decision')}>
          多策略决策
        </button>
        <button className={activeTab === 'risk' ? 'active' : ''} type="button" onClick={() => setActiveTab('risk')}>
          风险闭环
        </button>
      </div>

      {activeTab === 'replan' && (
        <div className="assistant-section-stack">
          <section className="assistant-card current">
            <span className="section-marker" />
            <h3>当前态势</h3>
            <p>
              检测到 <b>{highRiskCount}</b> 个高风险项，涉及 <b>{riskItems.length || '待生成'}</b> 条风险记录；
              平均保障率 {dashboardMetricValue(numberValue(summary.task_satisfaction_avg), '%', 1)}。
            </p>
            <button type="button" onClick={onPlan} disabled={busy || !project}>
              执行重算
            </button>
          </section>
          <section className="assistant-card">
            <h3>推荐动作</h3>
            {actions.length ? (
              actions.slice(0, 4).map((action) => (
                <article className="assistant-action" key={action.action_id}>
                  <strong>{action.title}</strong>
                  <p>{action.why}</p>
                  <button type="button" onClick={() => onApplyAction(action)} disabled={busy || !project}>
                    转为预案
                  </button>
                </article>
              ))
            ) : (
              <div className="empty small">完成规划和智能体评估后生成动作建议。</div>
            )}
          </section>
        </div>
      )}

      {activeTab === 'decision' && (
        <div className="assistant-section-stack">
          <div className="assistant-toolbar">
            <span>推荐方案</span>
            <button type="button" onClick={onCompare} disabled={busy || !project}>
              生成对比
            </button>
          </div>
          {recommendationCards.map((item, index) => (
            <article className={`decision-plan-card ${item.recommended ? 'recommended' : ''}`} key={`${item.run_id}-${item.label}-${index}`}>
              <div className="plan-card-title">
                <strong>{index === 0 ? `方案A：${item.label}` : `方案${String.fromCharCode(65 + index)}：${item.label}`}</strong>
                {item.recommended && <span>推荐</span>}
              </div>
              <div className="assistant-plan-metrics">
                <Metric label="保障率" value={`${item.task_satisfaction_avg}%`} />
                <Metric label="冲突数" value={item.high_risk_count} />
                <Metric label="带宽占用" value={`${item.used_bandwidth_mhz} MHz`} />
              </div>
              <p>{item.recommendation_reason || item.description}</p>
              <button type="button" onClick={() => (plans.length ? onSelectPlan(item) : onCompare())} disabled={busy || !project}>
                {plans.length ? '应用方案' : '先做对比'}
              </button>
            </article>
          ))}
          <button className="secondary wide" type="button" onClick={onRunBatch} disabled={busy}>
            规模压测
          </button>
        </div>
      )}

      {activeTab === 'risk' && (
        <div className="assistant-section-stack">
          <section className="assistant-card">
            <h3>风险闭环建议</h3>
            {riskItems.length ? (
              riskItems.slice(0, 6).map((risk, index) => (
                <article className={`risk-closure-line ${riskTone(risk.severity)}`} key={`${risk.risk_type}-${index}`}>
                  <div>
                    <strong>{risk.severity}风险</strong>
                    <span>{risk.risk_type}</span>
                    <p>{risk.reason}</p>
                  </div>
                  <button type="button" onClick={onPlan} disabled={busy || !project}>
                    处理
                  </button>
                </article>
              ))
            ) : (
              <div className="empty small">暂无风险项，或等待规划结果。</div>
            )}
            <p className="assistant-footnote">中风险 {mediumRiskCount} 项；建议优先处理高风险和未满足装备组。</p>
          </section>
          {reportUrl && (
            <a className="assistant-report-link" href={reportUrl}>
              <Download size={15} />
              查看完整报告
            </a>
          )}
        </div>
      )}
    </aside>
  );
}

function ChevronGlyph() {
  return (
    <svg aria-hidden="true" viewBox="0 0 16 16" width="16" height="16">
      <path d="M4 10l4-4 4 4" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
    </svg>
  );
}

function DashboardSideRail({
  project,
  plan,
  visualization,
  agentAssessment,
  reportUrl,
  activeModule,
  onModuleChange,
}: {
  project: Project | null;
  plan: PlanResult | null;
  visualization: TaskVisualizationData | null;
  agentAssessment: TaskAgentAssessment | null;
  reportUrl: string;
  activeModule: DashboardModuleKey;
  onModuleChange: (module: DashboardModuleKey) => void;
}) {
  const summary = visualization?.summary ?? plan?.summary ?? {};
  const satisfaction = numberValue(summary.task_satisfaction_avg);
  const highRiskCount = numberValue(summary.high_risk_count) ?? 0;
  const quality = dashboardFirstNumber(numberValue(recordValue(summary.quality_scores).total), numberValue(summary.quality_total));
  const navItems = [
    { module: 'overview' as const, label: '项目总览', icon: <Layers3 size={16} /> },
    { module: 'tasks' as const, label: '任务管理', icon: <ClipboardList size={16} /> },
    { module: 'spectrumResources' as const, label: '频谱资源', icon: <RadioTower size={16} /> },
    { module: 'plan' as const, label: '规划方案', icon: <FileCheck2 size={16} /> },
    { module: 'spectrum' as const, label: '频谱占用', icon: <BarChart3 size={16} /> },
    { module: 'interference' as const, label: '干扰分析', icon: <ShieldAlert size={16} /> },
    { module: 'risk' as const, label: '风险管理', icon: <Gauge size={16} /> },
    { module: 'replan' as const, label: '动态重规划', icon: <RefreshCw size={16} /> },
    { module: 'decision' as const, label: '多策略决策', icon: <SlidersHorizontal size={16} /> },
    { module: 'assurance' as const, label: '任务保障率', icon: <Activity size={16} /> },
    { module: 'report' as const, label: '报表中心', icon: <Download size={16} /> },
    { module: 'system' as const, label: '验收留痕', icon: <Save size={16} /> },
  ];

  return (
    <aside className="dashboard-side-rail" aria-label="战场智能用频筹划平台模块栏">
      <div className="side-rail-brand">
        <span>
          <ShieldAlert size={20} />
        </span>
        <div>
          <strong>战场智能用频筹划平台</strong>
          <em>任务保障与动态重筹中枢</em>
        </div>
      </div>
      <nav className="side-rail-nav">
        {navItems.map((item) => (
          <button
            className={activeModule === item.module ? 'active' : ''}
            key={item.label}
            type="button"
            onClick={() => onModuleChange(item.module)}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="side-rail-status">
        <span>当前项目</span>
        <strong>{project?.name ?? '演训-东部战区-2026A'}</strong>
        <p>{plan?.status === 'success' ? `方案 #${plan.run_id}` : '等待规划方案'}</p>
        <div>
          <Metric label="保障" value={satisfaction !== null ? `${satisfaction.toFixed(1)}%` : '待生成'} />
          <Metric label="质量" value={quality !== null ? quality.toFixed(1) : '待生成'} />
          <Metric label="高风险" value={highRiskCount} />
          <Metric label="成熟度" value={agentAssessment ? agentAssessment.maturity_score : '待评估'} />
        </div>
      </div>
      <div className="side-rail-user">
        <span>用户</span>
        <strong>筹划值班员</strong>
        <em>用频筹划席</em>
      </div>
      {reportUrl ? (
        <a className="side-rail-report" href={reportUrl}>
          <Download size={15} />
          打开报告
        </a>
      ) : (
        <span className="side-rail-report disabled">报告待生成</span>
      )}
    </aside>
  );
}

function TaskDashboardOverview({
  project,
  validation,
  plan,
  visualization,
  agentAssessment,
  performance,
  versions,
  busy,
  reportUrl,
  onValidate,
  onPlan,
  onCompare,
  onRunBatch,
}: {
  project: Project | null;
  validation: TaskValidationResult | null;
  plan: PlanResult | null;
  visualization: TaskVisualizationData | null;
  agentAssessment: TaskAgentAssessment | null;
  performance: TaskPerformanceResult | null;
  versions: TaskVersionsResult | null;
  busy: boolean;
  reportUrl: string;
  onValidate: () => void;
  onPlan: () => void;
  onCompare: () => void;
  onRunBatch: () => void;
}) {
  const summary = visualization?.summary ?? plan?.summary ?? {};
  const quality = recordValue(summary.quality_scores);
  const riskItems = visualization?.risk_items ?? [];
  const taskUnitCount = dashboardFirstNumber(
    numberValue(summary.task_unit_count),
    visualization?.task_units.length,
    numberValue(validation?.summary.task_unit_count),
  );
  const equipmentGroupCount = dashboardFirstNumber(
    numberValue(summary.equipment_group_count),
    visualization?.assignments.length,
    numberValue(validation?.summary.equipment_group_count),
  );
  const satisfaction = numberValue(summary.task_satisfaction_avg);
  const usedBandwidth = numberValue(summary.used_bandwidth_mhz);
  const totalBandwidth = dashboardFirstNumber(
    numberValue(summary.available_bandwidth_mhz),
    visualization?.band_usage.reduce((total, item) => total + item.available_width_mhz, 0),
  );
  const qualityTotal = dashboardFirstNumber(numberValue(quality.total), numberValue(summary.quality_total), numberValue(summary.objective_score));
  const highRiskCount = dashboardFirstNumber(
    numberValue(summary.high_risk_count),
    riskItems.filter((item) => isHighRiskSeverity(item.severity)).length,
  );
  const mediumRiskCount = dashboardFirstNumber(
    numberValue(summary.medium_risk_count),
    riskItems.filter((item) => isMediumRiskSeverity(item.severity)).length,
  );
  const fullGroupCount = dashboardFirstNumber(
    numberValue(summary.full_group_count),
    visualization?.assignments.filter((item) => item.status === '完全满足').length,
  );
  const unsatisfiedCount = dashboardFirstNumber(
    numberValue(summary.unsatisfied_group_count),
    visualization?.assignments.filter((item) => item.status === '未满足').length,
  );
  const activeVersionCount = versions?.runs.length ?? 0;
  const auditCount = versions?.audit_logs.length ?? 0;
  const maxElapsedMs = dashboardFirstNumber(agentAssessment?.scale_evidence?.max_elapsed_ms, performance?.summary.max_elapsed_ms);
  const topBands = [...(visualization?.band_usage ?? [])].sort((left, right) => right.utilization_pct - left.utilization_pct).slice(0, 4);
  const blockedGates = agentAssessment?.acceptance_gates.filter((gate) => !gate.passed).length ?? null;
  const status = dashboardReadinessStatus(project, validation, plan, visualization, highRiskCount ?? 0);
  const leaderSummary =
    agentAssessment?.leader_summary ||
    stringValue(summary.leader_summary) ||
    (plan?.message ? plan.message : project ? '已进入任务单元规划工作台，可执行校验、规划、对比和重规划。' : '创建项目后接入样例或 Excel 数据。');
  const assuranceNote =
    fullGroupCount !== null && equipmentGroupCount !== null
      ? `保障装备组 ${fullGroupCount} / ${equipmentGroupCount}`
      : '等待任务保障矩阵';
  const bandwidthNote =
    totalBandwidth !== null && usedBandwidth !== null ? `总可用 ${totalBandwidth.toFixed(1)} MHz` : '跨频段资源占用';

  return (
    <section id="dashboard-overview" className="dashboard-overview reference-dashboard-canvas" aria-label="战场智能用频筹划驾驶舱总览">
      <div className="dashboard-command">
        <div className="dashboard-brand">
          <span className="brand-mark">
            <RadioTower size={23} />
          </span>
          <div>
            <strong>{project?.name ?? '战场用频筹划项目'}</strong>
            <p>{leaderSummary}</p>
          </div>
        </div>
        <div className={`readiness-pill ${status.tone}`}>
          <span>{status.label}</span>
          <strong>{status.detail}</strong>
        </div>
      </div>

      <div className="dashboard-kpi-grid reference-kpi-row">
        <DashboardMetric icon={<Activity size={18} />} label="任务保障率" value={dashboardMetricValue(satisfaction, '%', 1)} note={assuranceNote} tone="blue" />
        <DashboardMetric icon={<ShieldAlert size={18} />} label="高风险" value={dashboardMetricValue(highRiskCount)} note={`中风险 ${dashboardMetricValue(mediumRiskCount)}`} tone={highRiskCount ? 'red' : 'green'} />
        <DashboardMetric icon={<ClipboardList size={18} />} label="未满足装备" value={dashboardMetricValue(unsatisfiedCount)} note={`装备组 ${dashboardMetricValue(equipmentGroupCount)}`} tone={unsatisfiedCount ? 'amber' : 'teal'} />
        <DashboardMetric icon={<RadioTower size={18} />} label="占用带宽" value={dashboardMetricValue(usedBandwidth, ' MHz', 1)} note={bandwidthNote} tone="violet" />
      </div>

      <div className="dashboard-action-bar">
        <button onClick={onValidate} disabled={busy || !project}>
          <FileCheck2 size={16} />
          数据校验
        </button>
        <button onClick={onPlan} disabled={busy || !project}>
          <RefreshCw size={16} />
          执行规划
        </button>
        <button onClick={onCompare} disabled={busy || !project}>
          <BarChart3 size={16} />
          多策略对比
        </button>
        <button className="secondary" onClick={onRunBatch} disabled={busy}>
          <SlidersHorizontal size={16} />
          规模压测
        </button>
        {reportUrl && (
          <a className="export" href={reportUrl}>
            <Download size={15} />
            查看报告
          </a>
        )}
      </div>
    </section>
  );
}

function DashboardMetric({
  icon,
  label,
  value,
  note,
  tone,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  note: string;
  tone: 'blue' | 'teal' | 'green' | 'amber' | 'red' | 'violet';
}) {
  return (
    <article className={`dashboard-metric-card ${tone}`}>
      <span className="metric-icon">{icon}</span>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <em>{note}</em>
      </div>
    </article>
  );
}

function ReferenceSpectrumPanorama({
  bands,
  assignments,
  riskCount,
}: {
  bands: TaskVisualizationData['spectrum_timeline'];
  assignments: TaskVisualizationData['assignments'];
  riskCount: number;
}) {
  const visibleBands = useMemo(() => [...bands].sort((left, right) => left.start_mhz - right.start_mhz || left.end_mhz - right.end_mhz), [bands]);
  const assignmentByGroup = useMemo(() => new Map(assignments.map((item) => [item.equipment_group_id, item])), [assignments]);
  const equipmentTypes = useMemo(() => {
    const names = new Set<string>();
    bands.forEach((band) => {
      band.markers.forEach((marker) => {
        const equipmentType = equipmentTypeForMarker(marker, assignmentByGroup);
        if (equipmentType) names.add(equipmentType);
      });
    });
    return [...names].sort((left, right) => left.localeCompare(right, 'zh-Hans-CN'));
  }, [assignmentByGroup, bands]);
  const equipmentColorByType = useMemo(() => new Map(equipmentTypes.map((type, index) => [type, EQUIPMENT_TYPE_COLORS[index % EQUIPMENT_TYPE_COLORS.length]])), [equipmentTypes]);
  const markerItems = useMemo(
    () => visibleBands.flatMap((band) => band.markers.map((marker) => ({ band, marker }))),
    [visibleBands],
  );
  const rankedSpatialNodes = useMemo(
    () =>
      [...markerItems].sort(
        (left, right) =>
          spatialPriority(right.marker) - spatialPriority(left.marker) ||
          right.marker.end_pct - right.marker.start_pct - (left.marker.end_pct - left.marker.start_pct),
      ),
    [markerItems],
  );
  const defaultMarkerId =
    markerItems.find(({ marker }) => marker.severity === '高' || marker.kind === '禁用')?.marker.id ?? markerItems[0]?.marker.id ?? null;
  const [selectedMarkerId, setSelectedMarkerId] = useState<string | null>(defaultMarkerId);

  useEffect(() => {
    const selectedStillExists = selectedMarkerId ? markerItems.some(({ marker }) => marker.id === selectedMarkerId) : false;
    if (!selectedStillExists) setSelectedMarkerId(defaultMarkerId);
  }, [defaultMarkerId, markerItems, selectedMarkerId]);

  const selectedItem = markerItems.find(({ marker }) => marker.id === selectedMarkerId) ?? markerItems.find(({ marker }) => marker.id === defaultMarkerId) ?? null;
  const spatialNodes = useMemo(() => {
    const baseNodes = rankedSpatialNodes.slice(0, 12);
    if (!selectedItem || baseNodes.some(({ marker }) => marker.id === selectedItem.marker.id)) return baseNodes;
    return [selectedItem, ...baseNodes.slice(0, 11)];
  }, [rankedSpatialNodes, selectedItem]);
  const spatialNodeItems = useMemo(
    () => spatialNodes.map((item, index) => ({ ...item, position: spatialNodePosition(index, item.marker) })),
    [spatialNodes],
  );
  const activeSpatialNode = selectedItem ? spatialNodeItems.find(({ marker }) => marker.id === selectedItem.marker.id) ?? null : null;
  const linkedSpatialNodes = activeSpatialNode
    ? spatialNodeItems.filter(({ band, marker }) => band.band_group === activeSpatialNode.band.band_group && marker.id !== activeSpatialNode.marker.id).slice(0, 4)
    : [];
  const selectedBandPeers = selectedItem ? selectedItem.band.markers.filter((marker) => marker.id !== selectedItem.marker.id).slice(0, 4) : [];
  const statusLegendItems = useMemo(() => {
    const markerClasses = new Set(markerItems.map(({ marker }) => markerClass(marker.kind, marker.severity)));
    return [
      { className: 'legend-risk', label: '风险指配', visible: markerClasses.has('marker-risk') },
      { className: 'legend-forbid', label: '禁用频段', visible: markerClasses.has('marker-forbid') },
      { className: 'legend-protect', label: '保护频段', visible: markerClasses.has('marker-protect') },
      { className: 'legend-idle', label: '可用未占用', visible: true },
    ].filter((item) => item.visible);
  }, [markerItems]);

  return (
    <section className="reference-spectrum-panel">
      <div className="reference-panel-head">
        <div>
          <h2>频谱占用全景 · 装备类型联动</h2>
          <span>每行代表一个实际频段池，横向位置为该频段内占用比例，颜色区分装备类型</span>
        </div>
        <div className="current-time-pin neutral">联动视图</div>
      </div>
      {bands.length ? (
        <div className="spectrum-25d-layout">
          <div className="spectrum-25d-main">
            <div className="spectrum-frequency-scale">
              <span>频段范围 (MHz)</span>
              <span>频段内占用位置</span>
            </div>
            <div className="spectrum-25d-stage">
              <div className="spectrum-frequency-axis" aria-hidden="true">
                {visibleBands.map((band) => (
                  <strong key={`${band.band_group}-${band.start_mhz}`}>{band.start_mhz}-{band.end_mhz}</strong>
                ))}
              </div>
              <div className="spectrum-25d-plane" role="grid" aria-label="频率占用条带图">
                {visibleBands.map((band, rowIndex) => (
                  <div className="spectrum-frequency-lane" key={`${band.band_group}-${band.start_mhz}`} style={{ '--lane-index': rowIndex } as CSSProperties}>
                    <span className="spectrum-lane-width" />
                    {band.markers.map((marker) => {
                      const isActive = selectedItem?.marker.id === marker.id;
                      const equipmentType = equipmentTypeForMarker(marker, assignmentByGroup);
                      const markerColor = markerColorForMarker(marker, equipmentColorByType, equipmentType);
                      return (
                        <button
                          className={`spectrum-25d-marker ${markerClass(marker.kind, marker.severity)} ${isActive ? 'active' : ''}`}
                          key={marker.id}
                          onClick={() => setSelectedMarkerId(marker.id)}
                          style={
                            {
                              left: `${marker.start_pct}%`,
                              width: `${Math.max(1.6, marker.end_pct - marker.start_pct)}%`,
                              '--marker-rise': `${markerRise(marker.kind, marker.severity)}px`,
                              '--equipment-color': markerColor,
                            } as CSSProperties
                          }
                          title={`${marker.kind} ${marker.start_mhz}-${marker.end_mhz} MHz · ${equipmentType ? `${equipmentType} · ` : ''}${marker.label}`}
                        >
                          <span>{marker.kind}</span>
                        </button>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
            <div className="reference-spectrum-legend spectrum-25d-legend">
              {equipmentTypes.map((type) => (
                <span className="legend-equipment-type" key={type} style={{ '--legend-color': equipmentColorByType.get(type) } as CSSProperties}>
                  {type}
                </span>
              ))}
              {statusLegendItems.map((item) => (
                <span className={item.className} key={item.className}>
                  {item.label}
                </span>
              ))}
              <b>干扰告警 {riskCount}</b>
            </div>
          </div>

          <aside className="spectrum-spatial-panel" aria-label="空间态势联动">
            <div className="spectrum-spatial-head">
              <strong>空间态势联动</strong>
              <span>同频对象与影响关系</span>
            </div>
            <div className="spectrum-site-map" role="list">
              <span className="site-grid-line horizontal" />
              <span className="site-grid-line vertical" />
              <span className="site-zone site-zone-command">指挥通信</span>
              <span className="site-zone site-zone-radar">雷达观测</span>
              <span className="site-zone site-zone-uav">无人平台</span>
              <span className="site-zone site-zone-ew">干扰/保护</span>
              {activeSpatialNode ? (
                <svg className="site-link-layer" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                  {linkedSpatialNodes.map(({ marker, position }) => (
                    <line
                      key={marker.id}
                      x1={activeSpatialNode.position.left}
                      y1={activeSpatialNode.position.top}
                      x2={position.left}
                      y2={position.top}
                    />
                  ))}
                </svg>
              ) : null}
              {spatialNodeItems.map(({ band, marker, position }) => {
                const isActive = selectedItem?.marker.id === marker.id;
                const isLinked = linkedSpatialNodes.some((item) => item.marker.id === marker.id);
                const equipmentType = equipmentTypeForMarker(marker, assignmentByGroup);
                return (
                  <button
                    className={`spectrum-site-node ${markerClass(marker.kind, marker.severity)} ${isActive ? 'active' : ''} ${isLinked ? 'linked' : ''}`}
                    key={`${band.band_group}-${marker.id}`}
                    onClick={() => setSelectedMarkerId(marker.id)}
                    style={
                      {
                        left: `${position.left}%`,
                        top: `${position.top}%`,
                        '--equipment-color': markerColorForMarker(marker, equipmentColorByType, equipmentType),
                      } as CSSProperties
                    }
                    title={`${nodeLabel(marker)} · ${equipmentType || marker.kind} · ${marker.start_mhz}-${marker.end_mhz} MHz`}
                  >
                    <RadioTower size={13} />
                    <span>{shorten(nodeLabel(marker), 8)}</span>
                  </button>
                );
              })}
            </div>
            <div className="spectrum-selection-card">
              {selectedItem ? (
                <>
                  <span className={severityClass(selectedItem.marker.severity)}>{selectedItem.marker.severity || '低'}风险</span>
                  <strong>{selectedItem.marker.label}</strong>
                  <dl>
                    <div>
                      <dt>频段池</dt>
                      <dd>{selectedItem.band.band_group}</dd>
                    </div>
                    <div>
                      <dt>频段</dt>
                      <dd>
                        {selectedItem.marker.start_mhz}-{selectedItem.marker.end_mhz}
                      </dd>
                    </div>
                    <div>
                      <dt>宽度</dt>
                      <dd>{Math.max(0, selectedItem.marker.end_mhz - selectedItem.marker.start_mhz).toFixed(3)}</dd>
                    </div>
                    <div>
                      <dt>对象</dt>
                      <dd>{nodeLabel(selectedItem.marker)}</dd>
                    </div>
                    <div>
                      <dt>装备类型</dt>
                      <dd>{equipmentTypeForMarker(selectedItem.marker, assignmentByGroup) || selectedItem.marker.kind}</dd>
                    </div>
                  </dl>
                  <div className="spectrum-impact-list">
                    <span>同频对象</span>
                    {selectedBandPeers.length ? (
                      selectedBandPeers.map((marker) => (
                        <button key={marker.id} type="button" onClick={() => setSelectedMarkerId(marker.id)}>
                          <i className={markerClass(marker.kind, marker.severity)} />
                          <strong>{shorten(nodeLabel(marker), 14)}</strong>
                          <em>{marker.kind}</em>
                        </button>
                      ))
                    ) : (
                      <em>当前频段池暂无其他关联对象</em>
                    )}
                  </div>
                </>
              ) : (
                <div className="empty small">点击热力块或空间节点查看联动详情</div>
              )}
            </div>
          </aside>
        </div>
      ) : (
        <div className="empty visual-empty">完成规划后显示频谱占用全景、保护频率和干扰片段。</div>
      )}
    </section>
  );
}

function ReferenceInterferenceAlerts({
  risks,
  bands,
}: {
  risks: TaskVisualizationData['risk_items'];
  bands: TaskVisualizationData['band_usage'];
}) {
  const highRisks = risks.filter((item) => isHighRiskSeverity(item.severity)).slice(0, 3);
  const visibleRisks = (highRisks.length ? highRisks : risks).slice(0, 4);
  return (
    <aside className="reference-alert-panel" aria-label="干扰告警">
      <div className="reference-panel-head compact">
        <div>
          <h2>干扰告警</h2>
          <span>{risks.length ? `${risks.length} 条风险记录` : '等待规划结果'}</span>
        </div>
        <ShieldAlert size={18} />
      </div>
      <div className="reference-alert-list">
        {visibleRisks.length ? (
          visibleRisks.map((risk, index) => (
            <article className={riskTone(risk.severity)} key={`${risk.risk_type}-${risk.reason}-${index}`}>
              <span>{risk.severity}风险</span>
              <strong>{risk.risk_type}</strong>
              <p>{risk.reason}</p>
              <em>
                {risk.task_unit_a || risk.equipment_group_a || '任务单元'} {risk.task_unit_b ? `→ ${risk.task_unit_b}` : ''}
              </em>
            </article>
          ))
        ) : (
          <div className="empty small">完成规划后显示同频、邻频、保护距离和高功率近距告警。</div>
        )}
      </div>
      <div className="reference-band-pressure">
        <strong>频段压力</strong>
        {bands.length ? (
          bands.slice(0, 3).map((band) => (
            <div className="band-pressure-line" key={band.band_group}>
              <span>{band.band_group}</span>
              <b>
                <i style={{ width: `${Math.min(100, Math.max(2, band.utilization_pct))}%` }} />
              </b>
              <em>{Math.round(band.utilization_pct)}%</em>
            </div>
          ))
        ) : (
          <p>等待频段占用统计</p>
        )}
      </div>
    </aside>
  );
}

function ReferenceTaskMatrix({
  assignments,
  taskUnitCount,
}: {
  assignments: TaskVisualizationData['assignments'];
  taskUnitCount: number | null;
}) {
  const rows = assignments.slice(0, 5);
  return (
    <section className="reference-matrix-panel">
      <div className="reference-panel-head">
        <div>
          <h2>任务单元保障矩阵</h2>
          <span>频率可用、干扰可控、同频兼容、跨域协同与保障率联动核查</span>
        </div>
        <div className="matrix-filter-row">
          <span>任务单元 {taskUnitCount ?? '待生成'}</span>
          <span>全部任务状态</span>
          <span>搜索任务/装备名称</span>
        </div>
      </div>
      {rows.length ? (
        <div className="reference-table-wrap">
          <table className="reference-matrix-table">
            <thead>
              <tr>
                <th>任务单元</th>
                <th>设备/系统</th>
                <th>频段需求</th>
                <th>重要级别</th>
                <th>频率可用</th>
                <th>干扰可控</th>
                <th>同频兼容</th>
                <th>跨域协同</th>
                <th>保障率</th>
                <th>风险等级</th>
                <th>方案备注</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((item) => {
                const ratio = Math.round(Number(item.satisfaction_ratio ?? 0) * 100);
                const risk = item.status === '未满足' ? '高' : item.status === '部分满足' ? '中' : '低';
                return (
                  <tr key={`${item.task_unit_id}-${item.equipment_group_id}`}>
                    <td>{item.task_unit_id}</td>
                    <td>{item.equipment_type}</td>
                    <td>{item.band_group || '-'}</td>
                    <td className={risk === '高' ? 'risk-high' : risk === '中' ? 'risk-medium' : 'risk-low'}>{risk === '低' ? '中' : risk}</td>
                    <td>
                      <CheckCircle2 size={15} />
                    </td>
                    <td>
                      <CheckCircle2 size={15} />
                    </td>
                    <td>{risk === '高' ? '×' : <CheckCircle2 size={15} />}</td>
                    <td>{risk === '高' ? '×' : <CheckCircle2 size={15} />}</td>
                    <td>{ratio}%</td>
                    <td className={risk === '高' ? 'risk-high' : risk === '中' ? 'risk-medium' : 'risk-low'}>{risk}</td>
                    <td>{item.decision_notes || item.reason || item.status}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty visual-empty">完成规划后显示任务单元、装备组、频段池和保障状态。</div>
      )}
    </section>
  );
}

function ReferenceVersionAuditStrip({
  versions,
  qualityTotal,
  blockedGates,
  maxElapsedMs,
  nextAction,
  activeVersionCount,
  auditCount,
}: {
  versions: TaskVersionsResult | null;
  qualityTotal: number | null;
  blockedGates: number | null;
  maxElapsedMs: number | null;
  nextAction: string;
  activeVersionCount: number;
  auditCount: number;
}) {
  const runs = versions?.runs.slice(0, 3) ?? [];
  const audits = versions?.audit_logs.slice(0, 2) ?? [];
  return (
    <section className="reference-audit-panel" aria-label="版本审计">
      <div className="reference-panel-head compact">
        <div>
          <h2>版本审计</h2>
          <span>
            方案 {activeVersionCount} 个 · 审计 {auditCount} 条
          </span>
        </div>
        <div className="audit-health-strip">
          <Metric label="质量" value={qualityTotal !== null ? qualityTotal.toFixed(1) : '待生成'} />
          <Metric label="未过门槛" value={blockedGates ?? '待评估'} />
          <Metric label="最大耗时" value={maxElapsedMs ? `${maxElapsedMs} ms` : '待压测'} />
          <Metric label="下一动作" value={nextAction || '等待规划'} />
        </div>
      </div>
      {runs.length ? (
        <div className="reference-audit-grid">
          <table className="reference-audit-table">
            <thead>
              <tr>
                <th>版本号</th>
                <th>目标</th>
                <th>关键指标</th>
                <th>变更说明</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run, index) => {
                const runSummary = recordValue(run.summary);
                const assurance = numberValue(runSummary.task_satisfaction_avg);
                const highRisk = numberValue(runSummary.high_risk_count);
                const bandwidth = numberValue(runSummary.used_bandwidth_mhz);
                return (
                  <tr key={run.run_id}>
                    <td>{index === 0 ? `v${run.run_id}.0 当前` : `v${run.run_id}.0`}</td>
                    <td>{run.objective}</td>
                    <td>
                      {assurance !== null ? `${assurance.toFixed(1)}%` : '待生成'} / {highRisk ?? '-'} /{' '}
                      {bandwidth !== null ? `${bandwidth.toFixed(1)} MHz` : '-'}
                    </td>
                    <td>{run.replan_effect?.summary || run.message || run.status}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="audit-log-strip">
            {audits.length ? audits.map((audit) => <span key={audit.id}>{audit.action}：{shorten(audit.detail, 34)}</span>) : <span>暂无审计记录</span>}
          </div>
        </div>
      ) : (
        <div className="empty small">执行规划后显示版本、关键指标、变更说明和审计记录。</div>
      )}
    </section>
  );
}

function FilePicker({
  name,
  label,
  file,
  onChange,
}: {
  name: string;
  label: string;
  file: File | null;
  onChange: (file: File | null) => void;
}) {
  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    onChange(event.target.files?.[0] ?? null);
  }
  const inputId = `${name}-input`;
  return (
    <label className="file-picker" htmlFor={inputId}>
      <span>{label}</span>
      <input id={inputId} aria-label={label} name={name} type="file" accept=".xlsx,.xls" onChange={handleChange} />
      <em>{file?.name ?? '未选择'}</em>
    </label>
  );
}

function NumberField({
  name,
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  name: string;
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
}) {
  const inputId = `${name}-input`;
  return (
    <label htmlFor={inputId}>
      <span>{label}</span>
      <input
        id={inputId}
        name={name}
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(event) => onChange(Math.max(min, Math.min(max, Number(event.target.value) || min)))}
      />
    </label>
  );
}

function WeightControlPanel({
  templates,
  strategyProfile,
  weights,
  onTemplateChange,
  onWeightChange,
}: {
  templates: TaskSampleCatalog['weight_templates'];
  strategyProfile: string;
  weights: ConstraintWeights;
  onTemplateChange: (template: TaskSampleCatalog['weight_templates'][number]) => void;
  onWeightChange: (key: keyof ConstraintWeights, value: number) => void;
}) {
  const weightLabels: Record<keyof ConstraintWeights, string> = {
    task: '任务保障',
    risk: '风险抑制',
    spectrum: '频谱节约',
    priority: '优先级',
    switching: '少切换',
    reuse: '复用效率',
  };
  const activeTemplate = templates.find((item) => item.key === strategyProfile);
  return (
    <div className="weight-panel">
      <div className="weight-head">
        <label htmlFor="weight-template">
          <span>策略模板</span>
          <select
            id="weight-template"
            name="weight_template"
            value={strategyProfile}
            onChange={(event) => {
              const selected = templates.find((item) => item.key === event.target.value);
              if (selected) onTemplateChange(selected);
            }}
          >
            {templates.length ? (
              templates.map((item) => (
                <option key={item.key} value={item.key}>
                  {item.name}
                </option>
              ))
            ) : (
              <option value="balanced">均衡</option>
            )}
          </select>
        </label>
        <p>{activeTemplate?.description ?? '按当前权重折中任务保障、风险和频谱占用。'}</p>
      </div>
      <div className="weight-grid">
        {(Object.keys(weightLabels) as Array<keyof ConstraintWeights>).map((key) => (
          <label key={key} htmlFor={`constraint-weight-${key}`}>
            <span>
              {weightLabels[key]}
              <b>{weights[key]}</b>
            </span>
            <input
              id={`constraint-weight-${key}`}
              name={`constraint_weight_${key}`}
              type="range"
              min={0}
              max={100}
              step={5}
              value={weights[key]}
              onChange={(event) => onWeightChange(key, Number(event.target.value))}
            />
          </label>
        ))}
      </div>
    </div>
  );
}

function ValidationPanel({ data }: { data: TaskValidationResult | null }) {
  return (
    <section className="panel">
      <div className="panel-title">
        <ShieldAlert size={18} />
        <h2>输入校验</h2>
      </div>
      <SummaryBlock data={data?.summary} />
      <IssueList title="错误" items={data?.errors ?? []} type="error" />
      <IssueList title="提醒" items={data?.warnings ?? []} type="warning" />
    </section>
  );
}

function TaskComparisonPanel({
  data,
  projectId,
  onSelect,
}: {
  data: TaskComparisonResult | null;
  projectId: number | null;
  onSelect: (plan: TaskComparisonPlan) => void;
}) {
  if (!data) {
    return (
      <section className="panel">
        <div className="panel-title">
          <BarChart3 size={18} />
          <h2>多方案对比</h2>
        </div>
        <div className="empty small">点击“多方案”后生成多目标用频决策。</div>
      </section>
    );
  }
  return (
    <section className="panel">
      <div className="panel-title">
        <BarChart3 size={18} />
        <h2>多方案对比</h2>
      </div>
      <div className="task-plan-grid">
        {data.plans.map((plan) => (
          <article className={`task-plan-card ${plan.recommended ? 'recommended' : ''}`} key={plan.run_id}>
            <div className="plan-card-head">
              <div>
                <h3>{plan.label}</h3>
                <p>{plan.description}</p>
              </div>
              {plan.recommended && <span className="recommend-badge">推荐</span>}
            </div>
            <div className="plan-metrics">
              <Metric label="保障率" value={`${plan.task_satisfaction_avg}%`} />
              <Metric label="完全满足" value={plan.full_group_count} />
              <Metric label="部分满足" value={plan.partial_group_count} />
              <Metric label="未满足" value={plan.unsatisfied_group_count} />
              <Metric label="占用 MHz" value={plan.used_bandwidth_mhz} />
              <Metric label="高风险" value={plan.high_risk_count} />
              <Metric label="综合分" value={plan.objective_score} />
            </div>
            {plan.recommendation_reason && <p className="plan-reason">{plan.recommendation_reason}</p>}
            <div className="plan-actions">
              <button onClick={() => onSelect(plan)}>查看</button>
              {projectId && plan.status === 'success' && <a href={url(`/api/projects/${projectId}/task-export.xlsx?run=${plan.run_id}`)}>导出</a>}
            </div>
          </article>
        ))}
      </div>
      <DecisionTable rows={data.decision_table ?? []} />
    </section>
  );
}

function DecisionTable({ rows }: { rows: NonNullable<TaskComparisonResult['decision_table']> }) {
  if (!rows.length) return null;
  return (
    <div className="decision-table-wrap">
      <h3>多方案决策参谋表</h3>
      <table className="decision-table">
        <thead>
          <tr>
            <th>策略</th>
            <th>建议</th>
            <th>主要收益</th>
            <th>代价</th>
            <th>适用情况</th>
            <th>风险</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.profile}-${row.plan_label}`}>
              <td>
                <strong>{row.profile}</strong>
                <span>{row.plan_label}</span>
              </td>
              <td>{row.decision}</td>
              <td>{row.main_gain}</td>
              <td>{row.tradeoff}</td>
              <td>{row.suitable_when}</td>
              <td>{row.risk}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SampleCatalogPanel({ catalog }: { catalog: TaskSampleCatalog | null }) {
  if (!catalog) return null;
  const profileCount = catalog.task_unit_profiles.length;
  const equipmentTypeCount = catalog.equipment_types.length;
  const maxScale = catalog.batch_scales[catalog.batch_scales.length - 1];
  return (
    <section className="panel sample-catalog-panel">
      <div className="report-header">
        <div className="panel-title">
          <Layers3 size={18} />
          <h2>样例库与装备谱系</h2>
        </div>
        <span>
          {profileCount} 类任务单元 · {equipmentTypeCount} 类装备 · {catalog.objective_count} 类目标
        </span>
      </div>
      <div className="sample-catalog-grid">
        <div>
          <h3>生成预设</h3>
          <div className="sample-preset-list">
            {catalog.presets.map((item) => (
              <article key={item.key}>
                <strong>{item.name}</strong>
                <span>
                  {item.task_unit_count} 单元 · 压力 {item.spectrum_pressure}
                </span>
                <p>{item.description}</p>
              </article>
            ))}
          </div>
        </div>
        <div>
          <h3>任务单元模板</h3>
          <div className="profile-chip-list">
            {catalog.task_unit_profiles.map((item) => (
              <span key={item.code} title={`${item.preferred_band_groups} · ${item.equipment_types.join('、')}`}>
                {item.name} · {item.equipment_group_count} 组
              </span>
            ))}
          </div>
        </div>
        <div>
          <h3>阶梯压测规模</h3>
          <div className="scale-chip-list">
            {catalog.batch_scales.map((item) => (
              <span key={item.key}>
                {item.name} · {item.unit_count} 单元 · {item.density_multiplier}x
              </span>
            ))}
          </div>
          <p className="objective-help">
            最大压测规模为 {maxScale?.unit_count ?? '-'} 个任务单元，适合观察装备增多后的求解耗时和瓶颈变化。
          </p>
        </div>
        <div>
          <h3>权重模板</h3>
          <div className="scale-chip-list">
            {catalog.weight_templates.map((item) => (
              <span key={item.key} title={item.description}>
                {item.name} · 风险 {item.weights.risk} · 任务 {item.weights.task}
              </span>
            ))}
          </div>
          <p className="objective-help">
            参数化默认：{catalog.parametric_defaults.unit_count} 单元 · 装备密度 {catalog.parametric_defaults.density_multiplier}x · 雷达{' '}
            {catalog.parametric_defaults.radar_ratio}% · 无人机 {catalog.parametric_defaults.uav_ratio}%
          </p>
        </div>
      </div>
    </section>
  );
}

function PlanningPerformancePanel({
  busy,
  data,
  onRun,
  onRunBatch,
}: {
  busy: boolean;
  data: TaskPerformanceResult | null;
  onRun: () => void;
  onRunBatch: () => void;
}) {
  const largestScenario =
    data && data.analysis.scale_curve.length
      ? data.analysis.scale_curve.reduce((best, item) => (item.equipment_group_count > best.equipment_group_count ? item : best), data.analysis.scale_curve[0])
      : null;
  const largestRows = data?.rows.filter((row) => row.scenario === (largestScenario?.scenario ?? 'stress_performance')) ?? [];
  const bestStress = largestRows.length ? largestRows.reduce((best, row) => (row.quality_total > best.quality_total ? row : best), largestRows[0]) : null;
  const maxElapsed = Math.max(...(data?.analysis.scale_curve.map((item) => item.max_elapsed_ms) ?? [1]), 1);
  const maxGroups = Math.max(...(data?.analysis.scale_curve.map((item) => item.equipment_group_count) ?? [1]), 1);
  const objectiveCount = data ? new Set(data.rows.map((row) => row.objective)).size : defaultObjectives.length;
  const capacityProfile = data?.analysis.capacity_profile;
  return (
    <section className="panel performance-panel">
      <div className="report-header">
        <div className="panel-title">
          <BarChart3 size={18} />
          <h2>规划效能测试</h2>
        </div>
        <div className="inline-actions">
          <button onClick={onRun} disabled={busy}>
            <RefreshCw size={16} />
            快速测试
          </button>
          <button className="secondary" onClick={onRunBatch} disabled={busy}>
            <BarChart3 size={16} />
            阶梯压测
          </button>
        </div>
      </div>
      <p className="objective-help">对 {objectiveCount} 类规划目标执行求解，统计耗时、保障率、风险和质量分；阶梯压测会按任务单元规模递增生成样例。</p>
      {data ? (
        <>
          <div className="performance-summary">
            <Metric label="测试场景" value={data.summary.scenario_count} />
            <Metric label="求解次数" value={data.summary.run_count} />
            <Metric label="最大耗时" value={`${data.summary.max_elapsed_ms} ms`} />
            <Metric label="平均耗时" value={`${data.summary.avg_elapsed_ms} ms`} />
            <Metric label="最大装备组" value={data.summary.max_equipment_group_count} />
            <Metric label="最大台套数" value={data.summary.max_equipment_sample_count} />
            <Metric label="最佳质量" value={data.summary.best_quality_total} />
            <Metric label="压力推荐" value={bestStress?.objective_label ?? '-'} />
          </div>
          <div className="performance-insights">
            <article className="performance-leader">
              <strong>效能结论</strong>
              <p>{data.analysis.leader_summary}</p>
            </article>
            <div className="performance-diagnostics">
              {data.analysis.diagnostics.map((item) => (
                <article key={`${item.title}-${item.detail}`}>
                  <div>
                    <strong>{item.title}</strong>
                    <span className={severityClass(item.severity)}>{item.severity}</span>
                  </div>
                  <p>{item.detail}</p>
                  <em>{item.suggestion}</em>
                </article>
              ))}
            </div>
          </div>
          {capacityProfile && (
            <div className="capacity-profile">
              <article className="capacity-main">
                <div>
                  <strong>容量边界画像</strong>
                  <span className={severityClass(capacityProfile.status === '容量充足' ? '低' : capacityProfile.status === '需分批规划' ? '中' : '高')}>
                    {capacityProfile.status}
                  </span>
                </div>
                <p>{capacityProfile.decision}</p>
                <div className="capacity-metrics">
                  <Metric
                    label="推荐单次规模"
                    value={`${capacityProfile.recommended.task_unit_count ?? '-'} 单元 / ${capacityProfile.recommended.equipment_group_count ?? '-'} 组`}
                  />
                  <Metric
                    label="最大压测规模"
                    value={`${capacityProfile.largest.task_unit_count ?? '-'} 单元 / ${capacityProfile.largest.equipment_group_count ?? '-'} 组`}
                  />
                  <Metric label="质量下降" value={capacityProfile.quality_drop} />
                  <Metric label="耗时增长" value={`${capacityProfile.elapsed_growth}x`} />
                  <Metric label="瓶颈焦点" value={capacityProfile.problem_focus} />
                </div>
              </article>
              <div className="capacity-actions">
                {capacityProfile.actions.map((item) => (
                  <span key={item}>{item}</span>
                ))}
              </div>
            </div>
          )}
          <PerformanceHistory history={data.history ?? []} />
          <div className="performance-trends">
            <div>
              <h3>规模与耗时趋势</h3>
              <div className="trend-list">
                {data.analysis.scale_curve.map((item) => (
                  <article key={item.scenario}>
                    <div>
                      <strong>{item.scenario_name}</strong>
                      <span>
                        {item.equipment_group_count} 组 / {item.equipment_sample_count} 台套
                      </span>
                    </div>
                    <b>
                      <i style={{ width: `${Math.max(4, (item.max_elapsed_ms / maxElapsed) * 100)}%` }} />
                    </b>
                    <em>{item.max_elapsed_ms} ms</em>
                    <small style={{ width: `${Math.max(4, (item.equipment_group_count / maxGroups) * 100)}%` }} />
                  </article>
                ))}
              </div>
            </div>
            <div>
              <h3>场景推荐目标</h3>
              <div className="ranking-list">
                {data.analysis.objective_rankings.map((item) => (
                  <article key={item.scenario}>
                    <div>
                      <strong>{item.scenario_name}</strong>
                      <span>{item.recommended_label}</span>
                    </div>
                    <p>
                      质量 {item.quality_total} · 保障率 {item.task_satisfaction_avg}% · {item.elapsed_ms} ms
                    </p>
                    <em>{item.reason}</em>
                  </article>
                ))}
              </div>
            </div>
          </div>
          <div className="performance-table-wrap">
            <table className="performance-table">
              <thead>
                <tr>
                  <th>场景</th>
                  <th>目标</th>
                  <th>规模</th>
                  <th>耗时</th>
                  <th>效率</th>
                  <th>保障率</th>
                  <th>满足情况</th>
                  <th>风险</th>
                  <th>占用</th>
                  <th>质量</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row) => (
                  <tr key={`${row.scenario}-${row.objective}`}>
                    <td>
                      <strong>{row.scenario_name}</strong>
                      <span>{row.spectrum_rule_count} 条规则</span>
                    </td>
                    <td>{row.objective_label}</td>
                    <td>
                      {row.task_unit_count} 单元 / {row.equipment_group_count} 组
                      <br />
                      {row.equipment_sample_count} 台套
                    </td>
                    <td>{row.elapsed_ms} ms</td>
                    <td>{row.groups_per_second} 组/秒</td>
                    <td>{row.task_satisfaction_avg}%</td>
                    <td>
                      完全 {row.full_group_count} · 部分 {row.partial_group_count} · 未满足 {row.unsatisfied_group_count}
                    </td>
                    <td>
                      高 {row.high_risk_count} / 总 {row.risk_item_count}
                    </td>
                    <td>{row.used_bandwidth_mhz} MHz</td>
                    <td>{row.quality_total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="empty small">点击按钮后生成大规模样例并执行效能测试。</div>
      )}
    </section>
  );
}

function PerformanceHistory({ history }: { history: NonNullable<TaskPerformanceResult['history']> }) {
  if (!history.length) return null;
  const maxElapsed = Math.max(...history.map((item) => item.max_elapsed_ms), 1);
  return (
    <div className="performance-history">
      <h3>项目压测历史</h3>
      <div className="history-bars">
        {history.map((item) => (
          <article key={`${item.created_at}-${item.run_count}`}>
            <div>
              <strong>{new Date(item.created_at).toLocaleString()}</strong>
              <span>{item.run_count} 次求解 · {item.max_equipment_group_count} 装备组</span>
            </div>
            <b>
              <i style={{ width: `${Math.max(4, (item.max_elapsed_ms / maxElapsed) * 100)}%` }} />
            </b>
            <em>{item.max_elapsed_ms} ms</em>
            <p>{item.leader_summary}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

function TaskAgentAssessmentPanel({
  data,
  busy,
  planReady,
  projectReady,
  onRefresh,
  onApplyAction,
}: {
  data: TaskAgentAssessment | null;
  busy: boolean;
  planReady: boolean;
  projectReady: boolean;
  onRefresh: () => void;
  onApplyAction: (action: AgentSuggestedAction) => void;
}) {
  const maxCapability = Math.max(...(data?.capability_items.map((item) => item.score) ?? [100]), 1);
  return (
    <section className="panel agent-assessment-panel">
      <div className="report-header">
        <div className="panel-title">
          <SlidersHorizontal size={18} />
          <h2>动态规划智能体能力基线</h2>
        </div>
        <button className="small-button" onClick={onRefresh} disabled={!projectReady}>
          刷新
        </button>
      </div>
      {!data ? (
        <div className="empty small">完成一次任务规划后生成智能体成熟度、验收门槛和下一轮迭代建议。</div>
      ) : data.status === 'needs_plan' ? (
        <div className="agent-empty">
          <strong>{data.maturity_level}</strong>
          <p>{data.leader_summary}</p>
          <ActionList actions={data.next_actions} busy={busy} canApply={planReady} onApplyAction={onApplyAction} />
        </div>
      ) : (
        <>
          <div className="agent-summary">
            <div className="agent-score">
              <span>成熟度</span>
              <strong>{data.maturity_score}</strong>
              <em>{data.maturity_level}</em>
            </div>
            <p>{data.leader_summary}</p>
          </div>
          <div className="agent-grid">
            <div className="agent-card">
              <h3>能力项</h3>
              <div className="capability-list">
                {data.capability_items.map((item) => (
                  <article key={item.key}>
                    <div>
                      <strong>{item.label}</strong>
                      <span className={scoreClass(item.score)}>{item.status}</span>
                    </div>
                    <b>
                      <i style={{ width: `${Math.max(4, (item.score / maxCapability) * 100)}%` }} />
                    </b>
                    <em>{item.score} 分 · {item.evidence}</em>
                    <p>{item.next_step}</p>
                  </article>
                ))}
              </div>
            </div>
            <div className="agent-card">
              <h3>验收门槛</h3>
              <div className="gate-list">
                {data.acceptance_gates.map((gate) => (
                  <article key={gate.name} className={gate.passed ? 'passed' : 'blocked'}>
                    <div>
                      <strong>{gate.name}</strong>
                      <span>{gate.passed ? '通过' : '未达标'}</span>
                    </div>
                    <p>{gate.evidence}</p>
                    {!gate.passed && <em>{gate.next_step}</em>}
                  </article>
                ))}
              </div>
            </div>
            <ScaleEvidenceCard evidence={data.scale_evidence} />
            <div className="agent-card">
              <h3>下一轮动作</h3>
              <ActionList actions={data.next_actions} busy={busy} canApply={planReady} onApplyAction={onApplyAction} />
            </div>
            <ReplanEffectCard effect={data.replan_effect} />
            <StrategyTransitionCard
              effect={data.replan_effect}
              actions={data.next_actions}
              history={data.strategy_history ?? []}
              busy={busy}
              canApply={planReady}
              onApplyAction={onApplyAction}
            />
            <div className="agent-card">
              <h3>证据清单</h3>
              <div className="artifact-list">
                {data.artifact_checklist.map((item) => (
                  <article key={item.item} className={item.covered ? 'passed' : 'blocked'}>
                    <strong>{item.item}</strong>
                    <span>{item.covered ? '已覆盖' : '缺失'}</span>
                    <p>{item.evidence}</p>
                  </article>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
}

function ScaleEvidenceCard({ evidence }: { evidence?: TaskAgentAssessment['scale_evidence'] }) {
  if (!evidence) return null;
  const tone = evidence.status === '容量充足' ? 'low' : evidence.status === '需分批规划' ? 'medium' : evidence.available ? 'high' : 'missing';
  return (
    <div className={`agent-card scale-evidence-card ${tone}`}>
      <div className="effect-title">
        <h3>规模效能证据</h3>
        <span>{evidence.status}</span>
      </div>
      <p>{evidence.evidence}</p>
      <div className="capacity-metrics">
        <Metric label="推荐单次规模" value={capacityScaleLabel(evidence.recommended)} />
        <Metric label="最大压测规模" value={capacityScaleLabel(evidence.largest)} />
        <Metric label="最大耗时" value={evidence.max_elapsed_ms ? `${evidence.max_elapsed_ms} ms` : '-'} />
        <Metric label="最佳质量" value={evidence.best_quality_total ?? '-'} />
        <Metric label="质量下降" value={evidence.quality_drop ?? '-'} />
        <Metric label="耗时增长" value={evidence.elapsed_growth ? `${evidence.elapsed_growth}x` : '-'} />
      </div>
      <div className="scale-decision">
        <strong>处置建议</strong>
        <p>{evidence.decision}</p>
      </div>
      {evidence.actions?.length ? (
        <div className="capacity-actions">
          {evidence.actions.slice(0, 4).map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
      ) : null}
      <CapacityBatchPlanView plan={evidence.batch_plan} />
    </div>
  );
}

function CapacityBatchPlanView({ plan }: { plan?: NonNullable<TaskAgentAssessment['scale_evidence']>['batch_plan'] }) {
  if (!plan?.available) return null;
  const maxGroupUtilization = Math.max(...plan.batches.map((item) => item.group_utilization_pct || 0), 1);
  return (
    <div className="batch-plan-view">
      <div className="batch-plan-head">
        <div>
          <strong>容量拆批预案</strong>
          <span>{plan.needed ? `${plan.batch_count ?? plan.batches.length} 个批次` : '当前可单批规划'}</span>
        </div>
        <p>{plan.reason}</p>
      </div>
      <div className="batch-plan-metrics">
        <Metric label="当前规模" value={`${plan.current?.task_unit_count ?? '-'} 单元 / ${plan.current?.equipment_group_count ?? '-'} 组`} />
        <Metric label="推荐边界" value={`${plan.recommended_limits?.task_unit_count ?? '-'} 单元 / ${plan.recommended_limits?.equipment_group_count ?? '-'} 组`} />
        <Metric label="最高占用" value={`${plan.max_group_utilization_pct ?? '-'}%`} />
        <Metric label="跨批风险" value={plan.cross_batch_risk_count ?? 0} />
      </div>
      <div className="batch-list">
        {plan.batches.map((batch) => (
          <article key={batch.batch_id} className={batch.status === '超出建议' ? 'blocked' : 'passed'}>
            <div>
              <strong>{batch.name}</strong>
              <span>{batch.status}</span>
            </div>
            <b>
              <i style={{ width: `${Math.max(4, ((batch.group_utilization_pct || 0) / maxGroupUtilization) * 100)}%` }} />
            </b>
            <em>
              {batch.task_unit_count} 单元 · {batch.equipment_group_count} 组 · {batch.equipment_sample_count} 台套 · {batch.dominant_band_group}
            </em>
            <p>{batch.task_units.slice(0, 4).map((unit) => unit.name || unit.task_unit_id).join('、')}</p>
            <small>{batch.reason}</small>
          </article>
        ))}
      </div>
      {plan.cross_batch_links?.length ? (
        <div className="cross-batch-links">
          <strong>跨批复核</strong>
          {plan.cross_batch_links.slice(0, 3).map((item) => (
            <span key={`${item.source_unit}-${item.target_unit}-${item.reason}`}>
              {item.source_batch}-{item.target_batch} · {item.reason}
            </span>
          ))}
        </div>
      ) : null}
      {plan.guardrails?.length ? (
        <div className="capacity-actions">
          {plan.guardrails.slice(0, 3).map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function CapacityBatchExecutionPanel({
  data,
  projectId,
  busy,
  onSelectRun,
  onRiskClosure,
}: {
  data: TaskCapacityBatchExecutionResult | null;
  projectId: number | null;
  busy: boolean;
  onSelectRun: (run: TaskCapacityBatchExecutionResult['runs'][number]) => void;
  onRiskClosure: () => void;
}) {
  if (!data) return null;
  const review = data.cross_batch_review;
  const merged = data.merged_plan;
  const canCloseRisks = Boolean(projectId && data.ok && (review?.cross_batch_risk_count ?? 0) > 0);
  const closureTrend = data.closure
    ? [
        { label: '跨批风险', before: data.closure.before_cross_batch_risk_count, after: data.closure.after_cross_batch_risk_count },
        { label: '高风险', before: data.closure.before_high_risk_count ?? 0, after: data.closure.after_high_risk_count ?? 0 },
        { label: '中风险', before: data.closure.before_medium_risk_count ?? 0, after: data.closure.after_medium_risk_count ?? 0 },
        { label: '影响批次', before: data.closure.before_affected_batch_count ?? 0, after: data.closure.after_affected_batch_count ?? 0 },
      ]
    : [];
  const maxClosureValue = Math.max(...closureTrend.flatMap((item) => [Number(item.before || 0), Number(item.after || 0)]), 1);
  const maxQuality = Math.max(...data.runs.map((item) => Number(item.quality_total || 0)), 1);
  return (
    <section className={`panel capacity-batch-execution-panel ${data.ok ? 'ready' : 'blocked'}`}>
      <div className="report-header">
        <div className="panel-title">
          <Layers3 size={18} />
          <h2>容量子规划版本</h2>
        </div>
        <span>{data.message}</span>
      </div>
      <div className="batch-execution-summary">
        <Metric label="基线版本" value={data.base_run_id ? `#${data.base_run_id}` : '-'} />
        <Metric label="子规划数" value={data.runs.length} />
        <Metric label="跨批风险" value={review?.cross_batch_risk_count ?? 0} />
        <Metric label="复核状态" value={review?.status ?? '-'} />
      </div>
      {merged && (
        <div className={`merged-master-plan ${merged.status}`}>
          <div>
            <strong>合并总方案</strong>
            <span>{merged.status_label}</span>
          </div>
          <p>{merged.summary}</p>
          <div className="master-plan-metrics">
            <Metric label="总任务单元" value={merged.task_unit_count} />
            <Metric label="总装备组" value={merged.equipment_group_count} />
            <Metric label="平均保障率" value={`${Number(merged.task_satisfaction_avg || 0).toFixed(1)}%`} />
            <Metric label="遗留问题" value={merged.unresolved_count} />
          </div>
          <em>{merged.recommendation}</em>
          <div className="master-plan-actions">
            {projectId && data.ok ? (
              <a className="master-export" href={url(`/api/projects/${projectId}/task-capacity-master-export.xlsx`)}>
                导出总方案 Excel
              </a>
            ) : null}
            {canCloseRisks ? (
              <button className="master-secondary-action" disabled={busy} onClick={onRiskClosure}>
                风险闭环重算
              </button>
            ) : null}
          </div>
          {merged.audit_items?.length ? (
            <ul>
              {merged.audit_items.slice(0, 4).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : null}
        </div>
      )}
      {data.closure ? (
        <div className={`risk-closure-result ${data.closure.improved ? 'passed' : 'blocked'}`}>
          <strong>闭环重算结果</strong>
          <p>{data.closure.summary}</p>
          <span>
            {`硬约束 ${data.closure.applied_rule_count} 条 · 跳过 ${data.closure.skipped_link_count} 条 · 风险 ${data.closure.before_cross_batch_risk_count} -> ${data.closure.after_cross_batch_risk_count}`}
          </span>
          <div className="risk-closure-bars">
            {closureTrend.map((item) => (
              <div key={item.label} className="closure-bar-row">
                <div>
                  <b>{item.label}</b>
                  <span>{`${item.before} -> ${item.after}`}</span>
                </div>
                <p>
                  <i className="before" style={{ width: `${Math.max(4, (Number(item.before || 0) / maxClosureValue) * 100)}%` }} />
                  <i className="after" style={{ width: `${Math.max(4, (Number(item.after || 0) / maxClosureValue) * 100)}%` }} />
                </p>
              </div>
            ))}
          </div>
          <div className="master-plan-actions">
            {projectId && data.ok ? (
              <a className="closure-export" href={url(`/api/projects/${projectId}/task-capacity-risk-closure-export.xlsx`)}>
                导出闭环报告 Excel
              </a>
            ) : null}
          </div>
          {data.closure.rules?.length ? (
            <div className="closure-rule-list">
              {data.closure.rules.slice(0, 6).map((rule) => (
                <span key={`${rule.batch_id}-${rule.task_unit_id}-${rule.avoid_band_group}-${rule.protected_task_unit_id}`}>
                  {rule.batch_id} · {rule.task_unit_id} 避用 {rule.avoid_band_group}，保护 {rule.protected_task_unit_id}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
      {review && (
        <div className={`cross-batch-review ${review.status === '通过' ? 'passed' : 'blocked'}`}>
          <strong>跨批保护复核</strong>
          <p>{review.summary}</p>
          <em>{review.recommendation}</em>
          {canCloseRisks && !merged ? (
            <button className="master-secondary-action" disabled={busy} onClick={onRiskClosure}>
              风险闭环重算
            </button>
          ) : null}
          {review.top_links?.length ? (
            <div className="review-link-list">
              {review.top_links.slice(0, 4).map((item) => (
                <span key={`${item.source_unit}-${item.target_unit}-${item.reason}`}>
                  {item.source_batch}-{item.target_batch} · {item.reason}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      )}
      <div className="sub-run-grid">
        {data.runs.map((run) => (
          <article key={run.run_id} className={run.unsatisfied_group_count || run.high_risk_count ? 'blocked' : 'passed'}>
            <div>
              <strong>{run.batch_name || run.batch_id}</strong>
              <span>#{run.run_id}</span>
            </div>
            <b>
              <i style={{ width: `${Math.max(4, (Number(run.quality_total || 0) / maxQuality) * 100)}%` }} />
            </b>
            <em>
              {run.task_unit_count} 单元 · {run.equipment_group_count} 组 · 质量 {Number(run.quality_total || 0).toFixed(1)}
            </em>
            <p>
              保障 {Number(run.task_satisfaction_avg || 0).toFixed(1)}% · 未满足 {run.unsatisfied_group_count} · 高风险 {run.high_risk_count}
            </p>
            <div className="sub-run-actions">
              <button className="small-button" disabled={busy || !projectId} onClick={() => onSelectRun(run)}>
                查看批次
              </button>
              {projectId && run.status === 'success' && (
                <a href={url(`/api/projects/${projectId}/task-export.xlsx?run=${run.run_id}`)}>导出</a>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function capacityScaleLabel(row?: NonNullable<TaskAgentAssessment['scale_evidence']>['recommended']) {
  if (!row || (!row.task_unit_count && !row.equipment_group_count)) return '-';
  const samples = row.equipment_sample_count ? ` / ${row.equipment_sample_count} 台套` : '';
  return `${row.task_unit_count ?? '-'} 单元 / ${row.equipment_group_count ?? '-'} 组${samples}`;
}

function StrategyTransitionCard({
  effect,
  actions,
  history,
  busy,
  canApply,
  onApplyAction,
}: {
  effect?: ReplanEffect | null;
  actions: TaskAgentAssessment['next_actions'];
  history: NonNullable<TaskAgentAssessment['strategy_history']>;
  busy?: boolean;
  canApply?: boolean;
  onApplyAction?: (action: AgentSuggestedAction) => void;
}) {
  const pivotAction =
    actions.find((item) => item.action_id === 'pivot_after_flat_replan') ??
    actions.find((item) => item.action_id === 'capacity_after_spectrum_regression') ??
    actions.find((item) => item.action_id === 'rollback_to_base_run') ??
    actions[0];
  const baseLabel = effect ? strategyNodeLabel(effect.base_objective, effect.base_strategy_profile) : '待形成基线';
  const currentLabel = effect ? strategyNodeLabel(effect.current_objective, effect.current_strategy_profile) : '等待重规划';
  const nextLabel = pivotAction ? strategyActionLabel(pivotAction) : '人工复核';
  const status = effect?.status ?? 'pending';
  return (
    <div className={`agent-card strategy-chain-card ${status}`}>
      <div className="effect-title">
        <h3>策略转移链</h3>
        <span>{effect?.status_label ?? '未对比'}</span>
      </div>
      <div className="strategy-chain">
        <article>
          <span>上一版</span>
          <strong>{baseLabel}</strong>
        </article>
        <i />
        <article>
          <span>当前版</span>
          <strong>{currentLabel}</strong>
        </article>
        <i />
        <article>
          <span>下一跳</span>
          <strong>{nextLabel}</strong>
        </article>
      </div>
      <div className="strategy-details">
        {effect?.reasons?.[0] && <p>{effect.reasons[0]}</p>}
        {pivotAction?.expected_gain && <p>预计收益：{pivotAction.expected_gain}</p>}
        {pivotAction?.guardrail && <em>{pivotAction.guardrail}</em>}
      </div>
      {history.length ? (
        <div className="strategy-history">
          {history.slice(-5).map((item) => (
            <button
              key={item.run_id}
              type="button"
              className={item.transition_status}
              disabled={busy || !canApply || !onApplyAction}
              onClick={() => onApplyAction?.(historySelectAction(item))}
            >
              <div>
                <strong>#{item.run_id}</strong>
                <span>{item.transition_label}</span>
              </div>
              <p>{strategyNodeLabel(item.objective, item.strategy_profile)}</p>
              <em>
                保障 {Number(item.task_satisfaction_avg || 0).toFixed(1)}% · 质量 {Number(item.quality_total || 0).toFixed(1)} · 风险 {item.high_risk_count}/{item.medium_risk_count}
              </em>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function historySelectAction(item: NonNullable<TaskAgentAssessment['strategy_history']>[number]): AgentSuggestedAction {
  return {
    action_id: 'history_select_run',
    priority: '中',
    title: `切换到版本 #${item.run_id}`,
    why: `查看 ${strategyNodeLabel(item.objective, item.strategy_profile)} 的历史结果。`,
    suggested_message: `已切换到策略历史版本 #${item.run_id}`,
    deterministic_payload: { operation: 'select_task_run', run_id: item.run_id },
  };
}

function strategyNodeLabel(objective?: string | null, strategy?: string | null): string {
  const objectiveText = objectiveLabel(objective);
  const strategyText = strategyLabel(strategy);
  if (objectiveText && strategyText && strategyText !== '均衡') return `${objectiveText} · ${strategyText}`;
  return objectiveText || strategyText || '未记录';
}

function strategyActionLabel(action: AgentSuggestedAction): string {
  const operation = stringValue(action.deterministic_payload.operation);
  if (operation === 'capacity_batch_planning') return '容量分批';
  if (operation === 'task_performance_batch') return '容量复测';
  if (operation === 'select_task_run') return '回退版本';
  const objective = objectiveLabel(stringValue(action.deterministic_payload.objective));
  return objective || action.title;
}

function objectiveLabel(value?: string | null): string {
  const labels: Record<string, string> = {
    task_assurance: '任务保障',
    minimize_interference: '风险隔离',
    minimize_bandwidth: '频谱节约',
    priority_equipment: '优先级保障',
    radar_priority: '雷达优先',
    uav_link_priority: '无人机优先',
    communication_continuity: '通信连续',
    ew_isolation_priority: '对抗隔离',
    minimize_switching: '少切换',
    maximize_reuse_efficiency: '复用效率',
  };
  return labels[String(value ?? '')] ?? '';
}

function strategyLabel(value?: string | null): string {
  const labels: Record<string, string> = {
    balanced: '均衡',
    risk_first: '风险最低',
    task_first: '任务保障',
    spectrum_saving: '频谱节约',
    minimum_change: '最小调整',
  };
  return labels[String(value ?? '')] ?? '';
}

function ReplanEffectCard({ effect }: { effect?: ReplanEffect | null }) {
  if (!effect) {
    return (
      <div className="agent-card replan-effect-card">
        <h3>最近重规划收益</h3>
        <div className="empty small">暂无可比较的重规划收益，完成至少两次规划后显示。</div>
      </div>
    );
  }
  const delta = effect.deltas ?? {};
  const usage = effect.added_range_usage ?? [];
  return (
    <div className={`agent-card replan-effect-card ${effect.status}`}>
      <div className="effect-title">
        <h3>最近重规划收益</h3>
        <span>{effect.status_label}</span>
      </div>
      <p>{effect.summary}</p>
      <div className="effect-metrics">
        <Metric label="保障率" value={`${formatSigned(Number(delta.task_satisfaction_avg ?? 0))}%`} />
        <Metric label="质量分" value={formatSigned(Number(delta.quality_total ?? 0))} />
        <Metric label="未满足" value={formatSigned(Number(delta.unsatisfied_group_count ?? 0))} />
        <Metric label="高风险" value={formatSigned(Number(delta.high_risk_count ?? 0))} />
      </div>
      {usage.length ? (
        <div className="effect-usage">
          {usage.slice(0, 3).map((item) => (
            <article key={`${item.band_group}-${item.start_mhz}-${item.end_mhz}`}>
              <strong>{item.band_group || '自动频段'}</strong>
              <span>
                {item.start_mhz}-{item.end_mhz} MHz
              </span>
              <em>已用 {item.used_width_mhz} / {item.width_mhz} MHz，关联 {item.used_assignment_count} 个装备组</em>
            </article>
          ))}
        </div>
      ) : null}
      <ol className="effect-reasons">
        {(effect.reasons ?? []).slice(0, 3).map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ol>
      <em className="effect-recommendation">{effect.recommendation}</em>
    </div>
  );
}

function ActionList({
  actions,
  busy = false,
  canApply = false,
  onApplyAction,
}: {
  actions: TaskAgentAssessment['next_actions'];
  busy?: boolean;
  canApply?: boolean;
  onApplyAction?: (action: AgentSuggestedAction) => void;
}) {
  if (!actions.length) return <div className="empty small">暂无下一步建议</div>;
  return (
    <div className="action-list">
      {actions.map((action) => (
        <article key={action.action_id}>
          <div>
            <strong>{action.title}</strong>
            <span className={priorityClass(action.priority)}>{action.priority}</span>
          </div>
          {typeof action.rank_score === 'number' && (
            <small className="action-rank">排序分 {action.rank_score}</small>
          )}
          <p>{action.why}</p>
          {action.expected_gain && <p className="action-gain">预计收益：{action.expected_gain}</p>}
          {action.guardrail && <p className="action-guardrail">保护约束：{action.guardrail}</p>}
          <em>{action.suggested_message}</em>
          {onApplyAction && (
            <button className="small-button action-apply" onClick={() => onApplyAction(action)} disabled={busy || !canApply}>
              {agentActionButtonLabel(action)}
            </button>
          )}
        </article>
      ))}
    </div>
  );
}

function ReplanPanel({
  busy,
  projectReady,
  visualization,
  lockedGroupIds,
  lockedTaskUnitIds,
  preview,
  strategyTrials,
  confirmed,
  replanMessage,
  forbidBand,
  forbidStart,
  forbidEnd,
  availableBand,
  availableStart,
  availableEnd,
  priorityTarget,
  priorityValue,
  satisfactionUnit,
  satisfactionValue,
  avoidBand,
  forcedTarget,
  forcedBand,
  requiredFullTarget,
  allowLowPriorityDegrade,
  onMessageChange,
  onForbidBandChange,
  onForbidStartChange,
  onForbidEndChange,
  onAvailableBandChange,
  onAvailableStartChange,
  onAvailableEndChange,
  onPriorityTargetChange,
  onPriorityValueChange,
  onSatisfactionUnitChange,
  onSatisfactionValueChange,
  onAvoidBandChange,
  onForcedTargetChange,
  onForcedBandChange,
  onRequiredFullTargetChange,
  onAllowLowPriorityDegradeChange,
  onToggleLocked,
  onToggleLockedTaskUnit,
  onPreview,
  onPreviewStrategies,
  onApplyStrategyTrial,
  onConfirmChange,
  onReplan,
}: {
  busy: boolean;
  projectReady: boolean;
  visualization: TaskVisualizationData | null;
  lockedGroupIds: string[];
  lockedTaskUnitIds: string[];
  preview: TaskReplanPreview | null;
  strategyTrials: TaskStrategyTrialsResult | null;
  confirmed: boolean;
  replanMessage: string;
  forbidBand: string;
  forbidStart: string;
  forbidEnd: string;
  availableBand: string;
  availableStart: string;
  availableEnd: string;
  priorityTarget: string;
  priorityValue: string;
  satisfactionUnit: string;
  satisfactionValue: string;
  avoidBand: string;
  forcedTarget: string;
  forcedBand: string;
  requiredFullTarget: string;
  allowLowPriorityDegrade: boolean;
  onMessageChange: (value: string) => void;
  onForbidBandChange: (value: string) => void;
  onForbidStartChange: (value: string) => void;
  onForbidEndChange: (value: string) => void;
  onAvailableBandChange: (value: string) => void;
  onAvailableStartChange: (value: string) => void;
  onAvailableEndChange: (value: string) => void;
  onPriorityTargetChange: (value: string) => void;
  onPriorityValueChange: (value: string) => void;
  onSatisfactionUnitChange: (value: string) => void;
  onSatisfactionValueChange: (value: string) => void;
  onAvoidBandChange: (value: string) => void;
  onForcedTargetChange: (value: string) => void;
  onForcedBandChange: (value: string) => void;
  onRequiredFullTargetChange: (value: string) => void;
  onAllowLowPriorityDegradeChange: (value: boolean) => void;
  onToggleLocked: (groupId: string) => void;
  onToggleLockedTaskUnit: (unitId: string) => void;
  onPreview: () => void;
  onPreviewStrategies: () => void;
  onApplyStrategyTrial: (trial: TaskStrategyTrial) => void;
  onConfirmChange: (value: boolean) => void;
  onReplan: () => void;
}) {
  const bands = visualization?.band_usage.map((item) => item.band_group) ?? [];
  const taskUnits = visualization?.task_units ?? [];
  const assignments = visualization?.assignments ?? [];
  return (
    <section className="panel replan-panel" id="task-replan-panel">
      <div className="panel-title">
        <MessageSquare size={18} />
        <h2>交互式重规划</h2>
      </div>
      <label className="field-label" htmlFor="replan-message">
        自然语言要求
      </label>
      <textarea id="replan-message" name="replan_message" value={replanMessage} onChange={(event) => onMessageChange(event.target.value)} />
      <div className="replan-grid">
        <label htmlFor="replan-available-band">
          <span>补充可用频段池</span>
          <select id="replan-available-band" name="replan_available_band" value={availableBand} onChange={(event) => onAvailableBandChange(event.target.value)}>
            <option value="">自动判断</option>
            {bands.map((band) => (
              <option key={band} value={band}>
                {band}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor="replan-available-start">
          <span>可用起点 MHz</span>
          <input id="replan-available-start" name="replan_available_start_mhz" value={availableStart} onChange={(event) => onAvailableStartChange(event.target.value)} placeholder="2220" />
        </label>
        <label htmlFor="replan-available-end">
          <span>可用终点 MHz</span>
          <input id="replan-available-end" name="replan_available_end_mhz" value={availableEnd} onChange={(event) => onAvailableEndChange(event.target.value)} placeholder="2230" />
        </label>
        <label htmlFor="replan-forbid-band">
          <span>禁用频段池</span>
          <select id="replan-forbid-band" name="replan_forbid_band" value={forbidBand} onChange={(event) => onForbidBandChange(event.target.value)}>
            <option value="">自动判断</option>
            {bands.map((band) => (
              <option key={band} value={band}>
                {band}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor="replan-forbid-start">
          <span>禁用起点 MHz</span>
          <input id="replan-forbid-start" name="replan_forbid_start_mhz" value={forbidStart} onChange={(event) => onForbidStartChange(event.target.value)} placeholder="2210" />
        </label>
        <label htmlFor="replan-forbid-end">
          <span>禁用终点 MHz</span>
          <input id="replan-forbid-end" name="replan_forbid_end_mhz" value={forbidEnd} onChange={(event) => onForbidEndChange(event.target.value)} placeholder="2215" />
        </label>
        <label htmlFor="replan-avoid-band">
          <span>避用频段池</span>
          <select id="replan-avoid-band" name="replan_avoid_band" value={avoidBand} onChange={(event) => onAvoidBandChange(event.target.value)}>
            <option value="">不指定</option>
            {bands.map((band) => (
              <option key={band} value={band}>
                {band}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor="replan-forced-target">
          <span>强制对象</span>
          <input id="replan-forced-target" name="replan_forced_target" value={forcedTarget} onChange={(event) => onForcedTargetChange(event.target.value)} placeholder="EG-UAV-DATA 或 TU-UAV" />
        </label>
        <label htmlFor="replan-forced-band">
          <span>强制频段池</span>
          <select id="replan-forced-band" name="replan_forced_band" value={forcedBand} onChange={(event) => onForcedBandChange(event.target.value)}>
            <option value="">不指定</option>
            {bands.map((band) => (
              <option key={band} value={band}>
                {band}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor="replan-required-full-target">
          <span>必须完全满足</span>
          <input id="replan-required-full-target" name="replan_required_full_target" value={requiredFullTarget} onChange={(event) => onRequiredFullTargetChange(event.target.value)} placeholder="任务单元或装备组" />
        </label>
        <label className="checkbox-field" htmlFor="replan-allow-low-priority-degrade">
          <span>低优先级降级</span>
          <input id="replan-allow-low-priority-degrade" name="replan_allow_low_priority_degrade" type="checkbox" checked={allowLowPriorityDegrade} onChange={(event) => onAllowLowPriorityDegradeChange(event.target.checked)} />
        </label>
        <label htmlFor="replan-priority-target">
          <span>优先级对象</span>
          <input id="replan-priority-target" name="replan_priority_target" value={priorityTarget} onChange={(event) => onPriorityTargetChange(event.target.value)} placeholder="TU-RAD 或 雷达探测单元" />
        </label>
        <label htmlFor="replan-priority-value">
          <span>优先级</span>
          <input id="replan-priority-value" name="replan_priority_value" value={priorityValue} onChange={(event) => onPriorityValueChange(event.target.value)} placeholder="9" />
        </label>
        <label htmlFor="replan-satisfaction-unit">
          <span>保障率任务单元</span>
          <select id="replan-satisfaction-unit" name="replan_satisfaction_unit" value={satisfactionUnit} onChange={(event) => onSatisfactionUnitChange(event.target.value)}>
            <option value="">不调整</option>
            {taskUnits.map((unit) => (
              <option key={unit.task_unit_id} value={unit.task_unit_id}>
                {unit.name}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor="replan-satisfaction-value">
          <span>最低保障率 %</span>
          <input id="replan-satisfaction-value" name="replan_satisfaction_value" value={satisfactionValue} onChange={(event) => onSatisfactionValueChange(event.target.value)} placeholder="70" />
        </label>
      </div>
      <div className="lock-list">
        <div>
          <Lock size={16} />
          <strong>锁定任务单元 / 装备组</strong>
        </div>
        {assignments.length || taskUnits.length ? (
          <>
            <div className="lock-chips">
              {taskUnits.slice(0, 8).map((item) => (
                <button
                  className={lockedTaskUnitIds.includes(item.task_unit_id) ? 'chip active' : 'chip'}
                  key={item.task_unit_id}
                  onClick={() => onToggleLockedTaskUnit(item.task_unit_id)}
                >
                  {item.name}
                </button>
              ))}
            </div>
            <div className="lock-chips">
              {assignments.slice(0, 12).map((item) => (
                <button
                  className={lockedGroupIds.includes(item.equipment_group_id) ? 'chip active' : 'chip'}
                  key={item.equipment_group_id}
                  onClick={() => onToggleLocked(item.equipment_group_id)}
                >
                  {item.equipment_group_id}
                </button>
              ))}
            </div>
          </>
        ) : (
          <p>完成一次规划后可锁定任务单元或装备组。</p>
        )}
      </div>
      <div className="replan-confirm">
        <div className="replan-actions">
          <button className="wide secondary" onClick={onPreview} disabled={busy || !projectReady}>
            <MousePointer2 size={16} />
            预览变更清单
          </button>
          <button className="wide secondary" onClick={onPreviewStrategies} disabled={busy || !projectReady}>
            <BarChart3 size={16} />
            多策略试算
          </button>
        </div>
        {strategyTrials && (
          <StrategyTrialsPanel data={strategyTrials} busy={busy} onApply={onApplyStrategyTrial} />
        )}
        {preview ? (
          <div className="change-preview">
            <div>
              <strong>{preview.requires_confirmation ? `将按“${preview.objective_label}”重算` : '未发现有效约束变更'}</strong>
              <span>{preview.change_items.length} 项变更</span>
            </div>
            {preview.change_items.length ? (
              <ul>
                {preview.change_items.slice(0, 8).map((item, index) => (
                  <li key={`${item.type}-${item.target}-${index}`}>
                    <b>{item.type}</b>
                    <span>{item.target}</span>
                    <em>{item.detail}</em>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty small">当前输入与基线版本一致，无需生成新的规划版本。</div>
            )}
            {preview.requires_confirmation && (
              <label className="confirm-line" htmlFor="replan-confirmed">
                <input id="replan-confirmed" name="replan_confirmed" type="checkbox" checked={confirmed} onChange={(event) => onConfirmChange(event.target.checked)} />
                <span>确认以上约束变更，并生成新规划版本</span>
              </label>
            )}
          </div>
        ) : (
          <div className="empty small">先预览变更，再执行重规划。</div>
        )}
        <button className="wide" onClick={onReplan} disabled={busy || !projectReady || !preview?.requires_confirmation || !confirmed}>
          <SlidersHorizontal size={16} />
          确认执行重规划
        </button>
      </div>
    </section>
  );
}

function StrategyTrialsPanel({
  data,
  busy,
  onApply,
}: {
  data: TaskStrategyTrialsResult;
  busy: boolean;
  onApply: (trial: TaskStrategyTrial) => void;
}) {
  const [constraintFilter, setConstraintFilter] = useState('all');
  const [objectiveFilter, setObjectiveFilter] = useState('all');
  const [sortMode, setSortMode] = useState('recommended');
  const [showAll, setShowAll] = useState(false);
  const candidates = data.candidates ?? [];
  const constraintOptions = useMemo(
    () =>
      Array.from(
        new Map(candidates.map((item) => [item.constraint_variant || 'current_constraints', item.constraint_label || '当前约束'])),
      ).map(([value, label]) => ({ value, label })),
    [candidates],
  );
  const objectiveOptions = useMemo(
    () => Array.from(new Map(candidates.map((item) => [item.objective || 'task_assurance', item.objective_label || item.objective]))).map(([value, label]) => ({ value, label })),
    [candidates],
  );
  const filteredCandidates = useMemo(() => {
    const rows = candidates
      .filter((item) => constraintFilter === 'all' || item.constraint_variant === constraintFilter)
      .filter((item) => objectiveFilter === 'all' || item.objective === objectiveFilter);
    return [...rows].sort((a, b) => {
      if (sortMode === 'quality') return b.quality_total - a.quality_total || b.recommendation_score - a.recommendation_score;
      if (sortMode === 'risk') return a.high_risk_count - b.high_risk_count || a.medium_risk_count - b.medium_risk_count || b.recommendation_score - a.recommendation_score;
      if (sortMode === 'bandwidth') return a.used_bandwidth_mhz - b.used_bandwidth_mhz || b.recommendation_score - a.recommendation_score;
      if (sortMode === 'satisfaction') return b.task_satisfaction_avg - a.task_satisfaction_avg || b.recommendation_score - a.recommendation_score;
      return b.recommendation_score - a.recommendation_score || a.objective_score - b.objective_score;
    });
  }, [candidates, constraintFilter, objectiveFilter, sortMode]);
  const visibleCandidates = showAll ? filteredCandidates : filteredCandidates.slice(0, 6);

  useEffect(() => {
    setConstraintFilter('all');
    setObjectiveFilter('all');
    setSortMode('recommended');
    setShowAll(false);
  }, [data.base_run_id, data.recommended_trial_id]);

  if (!data.ok) {
    return (
      <div className="strategy-trials">
        <div className="strategy-trials-head">
          <strong>多策略试算</strong>
          <span>无法生成候选</span>
        </div>
        {(data.diagnostics ?? []).map((item, index) => (
          <p key={`${item}-${index}`} className="trial-diagnostic">
            {item}
          </p>
        ))}
      </div>
    );
  }
  return (
    <div className="strategy-trials">
      <div className="strategy-trials-head">
        <strong>多策略试算</strong>
        <span>{data.base_run_id ? `基线 #${data.base_run_id}` : '无基线'}</span>
      </div>
      <div className="trial-summary">
        <span>{candidates.length} 个候选</span>
        <span>{constraintOptions.length} 类约束</span>
        <span>{objectiveOptions.length} 类目标</span>
        <span>{filteredCandidates.length} 个当前可见</span>
      </div>
      <StrategyDecisionSummary summary={data.decision_summary} />
      <div className="trial-toolbar">
        <label htmlFor="strategy-trial-constraint-filter">
          约束
          <select id="strategy-trial-constraint-filter" name="strategy_trial_constraint_filter" value={constraintFilter} onChange={(event) => setConstraintFilter(event.target.value)}>
            <option value="all">全部约束</option>
            {constraintOptions.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor="strategy-trial-objective-filter">
          目标
          <select id="strategy-trial-objective-filter" name="strategy_trial_objective_filter" value={objectiveFilter} onChange={(event) => setObjectiveFilter(event.target.value)}>
            <option value="all">全部目标</option>
            {objectiveOptions.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor="strategy-trial-sort-mode">
          排序
          <select id="strategy-trial-sort-mode" name="strategy_trial_sort_mode" value={sortMode} onChange={(event) => setSortMode(event.target.value)}>
            <option value="recommended">推荐优先</option>
            <option value="quality">质量最高</option>
            <option value="satisfaction">保障率最高</option>
            <option value="risk">风险最低</option>
            <option value="bandwidth">占用最少</option>
          </select>
        </label>
      </div>
      {data.diagnostics?.length ? (
        <div className="trial-diagnostics">
          {data.diagnostics.slice(0, 2).map((item, index) => (
            <p key={`${item}-${index}`}>{item}</p>
          ))}
        </div>
      ) : null}
      <div className="strategy-trial-list">
        {visibleCandidates.map((trial) => (
          <article className={trial.recommended ? 'recommended' : ''} key={trial.trial_id}>
            <div className="trial-card-head">
              <div>
                <strong>{trial.label}</strong>
                <span>
                  {trial.objective_label} / {trial.strategy_profile} · {trial.constraint_label}
                </span>
              </div>
              {trial.recommended && <em>推荐</em>}
            </div>
            <div className="trial-metrics">
              <span>
                质量
                <b>{formatTrialNumber(trial.quality_total)}</b>
                <em className={trialDeltaClass(trial.deltas.quality_total)}>{formatTrialDelta(trial.deltas.quality_total)}</em>
              </span>
              <span>
                保障率
                <b>{formatTrialNumber(trial.task_satisfaction_avg)}%</b>
                <em className={trialDeltaClass(trial.deltas.task_satisfaction_avg)}>{formatTrialDelta(trial.deltas.task_satisfaction_avg, '%')}</em>
              </span>
              <span>
                高风险
                <b>{trial.high_risk_count}</b>
                <em className={trialDeltaClass(trial.deltas.high_risk_count, true)}>{formatTrialDelta(trial.deltas.high_risk_count)}</em>
              </span>
              <span>
                未满足
                <b>{trial.unsatisfied_group_count}</b>
                <em className={trialDeltaClass(trial.deltas.unsatisfied_group_count, true)}>{formatTrialDelta(trial.deltas.unsatisfied_group_count)}</em>
              </span>
              <span>
                占用
                <b>{formatTrialNumber(trial.used_bandwidth_mhz)} MHz</b>
                <em className={trialDeltaClass(trial.deltas.used_bandwidth_mhz, true)}>{formatTrialDelta(trial.deltas.used_bandwidth_mhz, ' MHz')}</em>
              </span>
            </div>
            {trial.constraint_changes?.length ? (
              <div className="trial-constraints">
                {trial.constraint_changes.slice(0, 3).map((item, index) => (
                  <span key={`${trial.trial_id}-constraint-${index}`}>{item}</span>
                ))}
              </div>
            ) : null}
            <p>{trial.reason}</p>
            <p>{trial.tradeoff}</p>
            <div className="trial-decision">
              <span>{trial.decision}</span>
              <button onClick={() => onApply(trial)} disabled={busy}>
                <RotateCcw size={14} />
                采用策略
              </button>
            </div>
          </article>
        ))}
      </div>
      {!filteredCandidates.length ? <p className="trial-empty">当前筛选下没有候选方案。</p> : null}
      {filteredCandidates.length > 6 ? (
        <button className="trial-more" onClick={() => setShowAll((value) => !value)} type="button">
          {showAll ? '收起候选' : `显示全部 ${filteredCandidates.length} 个候选`}
        </button>
      ) : null}
    </div>
  );
}

function StrategyDecisionSummary({ summary }: { summary?: TaskStrategyTrialsResult['decision_summary'] }) {
  if (!summary) return null;
  const rolePicks = summary.role_picks ?? [];
  const frontier = summary.pareto_frontier ?? [];
  return (
    <div className="strategy-decision-summary">
      <div className="decision-summary-head">
        <div>
          <strong>策略决策摘要</strong>
          <span>{summary.recommended_trial_id ? `推荐 ${summary.recommended_trial_id}` : '等待候选方案'}</span>
        </div>
        <div className="decision-baseline">
          <span>基线质量 {formatTrialNumber(summary.baseline?.quality_total)}</span>
          <span>基线保障 {formatTrialNumber(summary.baseline?.task_satisfaction_avg)}%</span>
          <span>高风险 {summary.baseline?.high_risk_count ?? 0}</span>
        </div>
      </div>
      {rolePicks.length ? (
        <div className="decision-role-grid">
          {rolePicks.slice(0, 5).map((item) => (
            <article key={`${item.role}-${item.trial_id}`}>
              <span>{item.label}</span>
              <strong>{item.trial_label}</strong>
              <em>{item.constraint_label}</em>
              <b>{strategyMetricLabel(item.metric_key)}：{formatStrategyMetric(item.metric_key, item.metric_value)}</b>
            </article>
          ))}
        </div>
      ) : null}
      {frontier.length ? (
        <div className="pareto-frontier">
          <strong>折中前沿</strong>
          <div>
            {frontier.slice(0, 5).map((item) => (
              <span key={item.trial_id}>
                {item.label} · 保障 {formatTrialNumber(item.task_satisfaction_avg)}% · 风险 {item.high_risk_count} · 占频 {formatTrialNumber(item.used_bandwidth_mhz)} MHz
              </span>
            ))}
          </div>
        </div>
      ) : null}
      <div className="decision-note-grid">
        <div>
          <strong>取舍说明</strong>
          {(summary.tradeoff_notes ?? []).slice(0, 3).map((item, index) => (
            <p key={`tradeoff-${index}`}>{item}</p>
          ))}
        </div>
        <div>
          <strong>采用护栏</strong>
          {(summary.adoption_guardrails ?? []).slice(0, 3).map((item, index) => (
            <p key={`guardrail-${index}`}>{item}</p>
          ))}
        </div>
      </div>
    </div>
  );
}

function strategyMetricLabel(key?: string): string {
  if (key === 'recommendation_score') return '推荐分';
  if (key === 'high_risk_count') return '高风险';
  if (key === 'task_satisfaction_avg') return '保障率';
  if (key === 'used_bandwidth_mhz') return '占频';
  if (key === 'quality_total') return '质量';
  return '指标';
}

function formatStrategyMetric(key: string | undefined, value: number | string | null | undefined): string {
  if (typeof value === 'string') return value;
  const formatted = formatTrialNumber(value);
  if (key === 'task_satisfaction_avg') return `${formatted}%`;
  if (key === 'used_bandwidth_mhz') return `${formatted} MHz`;
  return formatted;
}

function formatTrialNumber(value: number | null | undefined): string {
  const numeric = Number(value ?? 0);
  return Number.isInteger(numeric) ? String(numeric) : numeric.toFixed(1);
}

function formatTrialDelta(value: number | null | undefined, suffix = ''): string {
  const numeric = Number(value ?? 0);
  if (Math.abs(numeric) < 0.001) return `0${suffix}`;
  const formatted = Number.isInteger(numeric) ? String(numeric) : numeric.toFixed(1);
  return `${numeric > 0 ? '+' : ''}${formatted}${suffix}`;
}

function trialDeltaClass(value: number | null | undefined, lowerIsBetter = false): string {
  const numeric = Number(value ?? 0);
  if (Math.abs(numeric) < 0.001) return 'flat';
  const good = lowerIsBetter ? numeric < 0 : numeric > 0;
  return good ? 'good' : 'bad';
}

function EquipmentLibraryPanel({ items }: { items: EquipmentLibraryItem[] }) {
  return (
    <section className="panel equipment-library">
      <div className="panel-title">
        <ClipboardList size={18} />
        <h2>装备参数库</h2>
      </div>
      <div className="library-list">
        {items.slice(0, 20).map((item) => (
          <article key={item.equipment_type}>
            <div>
              <strong>{item.equipment_type}</strong>
              <span>{item.default_assignment_mode}</span>
            </div>
            <p>
              带宽 {item.reasonable_bandwidth_khz} kHz · 功率 {item.reasonable_power_w} W · {item.typical_mobility}
            </p>
            <em>{item.planning_notes}</em>
          </article>
        ))}
      </div>
    </section>
  );
}

function SpectrumRuleManagerPanel({
  busy,
  projectId,
  rules,
  bands,
  onRulesChange,
  runAction,
}: {
  busy: boolean;
  projectId: number | null;
  rules: TaskSpectrumRuleRecord[];
  bands: string[];
  onRulesChange: () => void;
  runAction: <T>(action: () => Promise<T>, success: string) => Promise<T | null>;
}) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<TaskSpectrumRulePayload>(() => defaultSpectrumRulePayload(bands));

  useEffect(() => {
    if (!form.band_group && bands[0]) {
      setForm((current) => ({ ...current, band_group: bands[0] }));
    }
  }, [bands, form.band_group]);

  function editRule(rule: TaskSpectrumRuleRecord) {
    setEditingId(rule.id);
    setForm({
      rule_id: rule.rule_id,
      rule_type: rule.rule_type,
      band_group: rule.band_group,
      spectrum_relation: rule.spectrum_relation,
      start_mhz: rule.start_mhz,
      end_mhz: rule.end_mhz,
      channel_step_khz: rule.channel_step_khz,
      max_bandwidth_khz: rule.max_bandwidth_khz,
      max_power_w: rule.max_power_w,
      guard_band_khz: rule.guard_band_khz,
      compatible_unit_types: rule.compatible_unit_types,
      compatible_equipment_types: rule.compatible_equipment_types,
      reason: rule.reason,
      source: rule.source,
      severity: rule.severity,
    });
  }

  async function saveRule() {
    if (!projectId) return;
    const action = editingId
      ? () => updateTaskSpectrumRule(projectId, editingId, form)
      : () => createTaskSpectrumRule(projectId, { ...form, rule_id: form.rule_id || `SR-UI-${Date.now()}` });
    const result = await runAction(action, editingId ? '频段规则已更新' : '频段规则已新增');
    if (result) {
      setEditingId(null);
      setForm(defaultSpectrumRulePayload(bands));
      onRulesChange();
    }
  }

  async function removeRule(ruleId: number) {
    if (!projectId) return;
    const result = await runAction(() => deleteTaskSpectrumRule(projectId, ruleId), '频段规则已删除');
    if (result) onRulesChange();
  }

  return (
    <section className="panel rules-panel task-rules-panel">
      <div className="report-header">
        <div className="panel-title">
          <RadioTower size={18} />
          <h2>任务频段规则管理</h2>
        </div>
        <button className="small-button" onClick={onRulesChange} disabled={!projectId || busy}>
          <RefreshCw size={15} />
          刷新
        </button>
      </div>
      {!projectId ? (
        <div className="empty small">创建项目后可维护可用、禁用和保护频率。</div>
      ) : (
        <div className="rules-layout">
          <div className="rules-table-wrap">
            <table className="rules-table task-rules-table">
              <thead>
                <tr>
                  <th>规则</th>
                  <th>类型</th>
                  <th>频段池</th>
                  <th>范围 MHz</th>
                  <th>带宽/功率</th>
                  <th>兼容对象</th>
                  <th>原因</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {rules.slice(0, 80).map((rule) => (
                  <tr key={rule.id}>
                    <td>{rule.rule_id}</td>
                    <td className={rule.rule_type === '禁用' ? 'risk-high' : rule.rule_type === '保护' ? 'risk-medium' : 'risk-low'}>
                      {rule.rule_type}
                    </td>
                    <td>{rule.band_group}</td>
                    <td>
                      {rule.start_mhz}-{rule.end_mhz}
                    </td>
                    <td>
                      {rule.max_bandwidth_khz} kHz / {rule.max_power_w} W
                    </td>
                    <td>
                      {shorten(rule.compatible_unit_types || '-', 36)}
                      <br />
                      {shorten(rule.compatible_equipment_types || '-', 36)}
                    </td>
                    <td>{shorten(rule.reason || '-', 50)}</td>
                    <td>
                      <button className="small-button" onClick={() => editRule(rule)} disabled={busy}>
                        <Save size={14} />
                      </button>
                      <button className="icon-danger" onClick={() => removeRule(rule.id)} disabled={busy}>
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="rule-form">
            <h3>{editingId ? '编辑规则' : '新增规则'}</h3>
            <div className="rule-form-grid">
              <label htmlFor="rule-form-rule-id">
                <span>规则编号</span>
                <input id="rule-form-rule-id" name="rule_id" value={form.rule_id} onChange={(event) => setForm({ ...form, rule_id: event.target.value })} placeholder="SR-UI-FORBID-1" />
              </label>
              <label htmlFor="rule-form-rule-type">
                <span>规则类型</span>
                <select
                  id="rule-form-rule-type"
                  name="rule_type"
                  value={form.rule_type}
                  onChange={(event) => setForm({ ...form, rule_type: event.target.value, spectrum_relation: event.target.value })}
                >
                  <option value="可用">可用</option>
                  <option value="保护">保护</option>
                  <option value="禁用">禁用</option>
                </select>
              </label>
              <label htmlFor="rule-form-band-group">
                <span>频段池</span>
                <input id="rule-form-band-group" name="band_group" value={form.band_group} onChange={(event) => setForm({ ...form, band_group: event.target.value })} placeholder={bands[0] ?? 'S-SIM-1'} />
              </label>
              <label htmlFor="rule-form-severity">
                <span>严重度</span>
                <select id="rule-form-severity" name="severity" value={form.severity} onChange={(event) => setForm({ ...form, severity: event.target.value })}>
                  <option value="低">低</option>
                  <option value="中">中</option>
                  <option value="高">高</option>
                </select>
              </label>
              <label htmlFor="rule-form-start-mhz">
                <span>起点 MHz</span>
                <input id="rule-form-start-mhz" name="start_mhz" type="number" value={form.start_mhz} onChange={(event) => setForm({ ...form, start_mhz: Number(event.target.value) })} />
              </label>
              <label htmlFor="rule-form-end-mhz">
                <span>终点 MHz</span>
                <input id="rule-form-end-mhz" name="end_mhz" type="number" value={form.end_mhz} onChange={(event) => setForm({ ...form, end_mhz: Number(event.target.value) })} />
              </label>
              <label htmlFor="rule-form-channel-step-khz">
                <span>步进 kHz</span>
                <input id="rule-form-channel-step-khz" name="channel_step_khz" type="number" value={form.channel_step_khz} onChange={(event) => setForm({ ...form, channel_step_khz: Number(event.target.value) })} />
              </label>
              <label htmlFor="rule-form-guard-band-khz">
                <span>保护带 kHz</span>
                <input id="rule-form-guard-band-khz" name="guard_band_khz" type="number" value={form.guard_band_khz} onChange={(event) => setForm({ ...form, guard_band_khz: Number(event.target.value) })} />
              </label>
              <label htmlFor="rule-form-max-bandwidth-khz">
                <span>最大带宽 kHz</span>
                <input id="rule-form-max-bandwidth-khz" name="max_bandwidth_khz" type="number" value={form.max_bandwidth_khz} onChange={(event) => setForm({ ...form, max_bandwidth_khz: Number(event.target.value) })} />
              </label>
              <label htmlFor="rule-form-max-power-w">
                <span>最大功率 W</span>
                <input id="rule-form-max-power-w" name="max_power_w" type="number" value={form.max_power_w} onChange={(event) => setForm({ ...form, max_power_w: Number(event.target.value) })} />
              </label>
            </div>
            <label htmlFor="rule-form-compatible-unit-types">
              <span>兼容任务类型</span>
              <input id="rule-form-compatible-unit-types" name="compatible_unit_types" value={form.compatible_unit_types} onChange={(event) => setForm({ ...form, compatible_unit_types: event.target.value })} placeholder="雷达探测单元,无人机侦察单元" />
            </label>
            <label htmlFor="rule-form-compatible-equipment-types">
              <span>兼容装备类型</span>
              <input id="rule-form-compatible-equipment-types" name="compatible_equipment_types" value={form.compatible_equipment_types} onChange={(event) => setForm({ ...form, compatible_equipment_types: event.target.value })} placeholder="低空探测雷达,无人机数传链路" />
            </label>
            <label htmlFor="rule-form-reason">
              <span>原因/依据</span>
              <textarea id="rule-form-reason" name="reason" value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} />
            </label>
            <div className="rule-form-actions">
              <button onClick={saveRule} disabled={busy || !form.band_group || form.end_mhz <= form.start_mhz}>
                <Plus size={16} />
                {editingId ? '保存规则' : '新增规则'}
              </button>
              {editingId && (
                <button
                  className="secondary"
                  onClick={() => {
                    setEditingId(null);
                    setForm(defaultSpectrumRulePayload(bands));
                  }}
                >
                  取消
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function TaskVisualizationPanel({
  data,
  previousData,
}: {
  data: TaskVisualizationData | null;
  previousData: TaskVisualizationData | null;
}) {
  if (!data) {
    return (
      <section className="visual-board">
        <div className="visual-header">
          <div>
            <p className="eyebrow">任务单元可视化</p>
            <h2>等待规划结果</h2>
          </div>
        </div>
        <div className="empty visual-empty">完成规划后显示保障率、频段池、装备组指配和部分满足原因。</div>
      </section>
    );
  }
  const diff = buildTaskDiff(previousData, data);
  return (
    <section className="visual-board">
      <div className="visual-header">
        <div>
          <p className="eyebrow">任务单元可视化</p>
          <h2>任务保障率、频段池与装备组指配</h2>
        </div>
        <div className="visual-metrics">
          <Metric label="任务单元" value={data.summary.task_unit_count} />
          <Metric label="装备组" value={data.summary.equipment_group_count} />
          <Metric label="平均保障率" value={`${data.summary.task_satisfaction_avg ?? 0}%`} />
          <Metric label="占用带宽" value={`${data.summary.used_bandwidth_mhz ?? 0} MHz`} />
          <Metric label="综合质量" value={`${(data.summary.quality_scores as QualityScores | undefined)?.total ?? '-'} 分`} />
        </div>
      </div>
      <ExplanationSummary summary={data.summary} />
      <div className="task-visual-grid">
        <div className="chart-block">
          <div className="chart-title">
            <Layers3 size={17} />
            <span>任务单元保障率</span>
          </div>
          <TaskUnitBars units={data.task_units} />
        </div>
        <div className="chart-block">
          <div className="chart-title">
            <RadioTower size={17} />
            <span>频段池占用</span>
          </div>
          <BandUsage bands={data.band_usage} />
        </div>
        <div className="chart-block wide-chart">
          <div className="chart-title">
            <RadioTower size={17} />
            <span>频谱条带图</span>
          </div>
          <SpectrumTimeline bands={data.spectrum_timeline} />
        </div>
        <div className="chart-block wide-chart">
          <div className="chart-title">
            <ShieldAlert size={17} />
            <span>瓶颈定位与冲突网络</span>
          </div>
          <BottleneckPanel analysis={data.summary.bottleneck_analysis as BottleneckAnalysis | undefined} />
        </div>
        <div className="chart-block wide-chart">
          <div className="chart-title">
            <RadioTower size={17} />
            <span>频谱损失与冲突细分</span>
          </div>
          <SpectrumContentionPanel analysis={data.summary.spectrum_contention as SpectrumContention | undefined} />
        </div>
        <div className="chart-block wide-chart">
          <div className="chart-title">
            <BarChart3 size={17} />
            <span>装备组分配矩阵</span>
          </div>
          <AssignmentMatrix assignments={data.assignments} />
        </div>
        <div className="chart-block wide-chart">
          <div className="chart-title">
            <FileCheck2 size={17} />
            <span>装备组解释链</span>
          </div>
          <AssignmentExplanationPanel assignments={data.assignments} />
        </div>
        <div className="chart-block">
          <div className="chart-title">
            <ShieldAlert size={17} />
            <span>部分满足原因排行</span>
          </div>
          <ReasonRank items={data.partial_reason_rank.length ? data.partial_reason_rank : data.risk_reason_rank} />
        </div>
        <div className="chart-block">
          <div className="chart-title">
            <ShieldAlert size={17} />
            <span>诊断建议</span>
          </div>
          <DiagnosticList items={(data.summary.diagnostics as DiagnosticItem[]) ?? []} />
        </div>
        <div className="chart-block">
          <div className="chart-title">
            <BarChart3 size={17} />
            <span>质量看板</span>
          </div>
          <QualityDashboard quality={data.summary.quality_scores as QualityScores | undefined} />
        </div>
        <div className="chart-block">
          <div className="chart-title">
            <BarChart3 size={17} />
            <span>评分解释</span>
          </div>
          <ScoreExplanationPanel score={data.summary.score_explanation as TaskComparisonPlan['score_explanation']} />
        </div>
        <div className="chart-block">
          <div className="chart-title">
            <RefreshCw size={17} />
            <span>方案差异</span>
          </div>
          {diff ? (
            <div className="diff-panel">
              <div className="diff-metrics">
                <Metric label="保障率变化" value={`${formatSigned(diff.avgDelta)}%`} />
                <Metric label="指配变化" value={diff.changedAssignments} />
                <Metric label="改善装备组" value={diff.improved} />
                <Metric label="下降装备组" value={diff.worsened} />
              </div>
              <ol className="diff-list">
                {diff.rows.slice(0, 8).map((row) => (
                  <li key={row.groupId}>
                    <strong>{row.groupId}</strong>
                    <span>
                      {row.beforeStatus} → {row.afterStatus}
                    </span>
                    <em>{formatSigned(row.ratioDelta * 100)}%</em>
                  </li>
                ))}
              </ol>
            </div>
          ) : (
            <div className="empty small">暂无上一版方案可对比</div>
          )}
        </div>
      </div>
    </section>
  );
}

function ExplanationSummary({ summary }: { summary: Record<string, unknown> }) {
  const leader = String(summary.leader_summary ?? '');
  const technical = String(summary.technical_summary ?? '');
  const weights = summary.constraint_weights as Partial<ConstraintWeights> | undefined;
  if (!leader && !technical && !weights) return null;
  return (
    <div className="explanation-summary">
      <article>
        <strong>决策摘要</strong>
        <p>{leader}</p>
      </article>
      <article>
        <strong>技术复核</strong>
        <p>{technical}</p>
      </article>
      <article>
        <strong>策略与权重</strong>
        <p>
          请求目标 {String(summary.requested_objective ?? summary.objective ?? '-')}，实际策略 {String(summary.effective_objective ?? '-')}；
          模板 {String(summary.strategy_profile ?? '-')}；任务 {weights?.task ?? '-'}，风险 {weights?.risk ?? '-'}，频谱 {weights?.spectrum ?? '-'}。
        </p>
      </article>
    </div>
  );
}

function QualityDashboard({ quality }: { quality?: QualityScores }) {
  if (!quality) return <div className="empty small">暂无质量评分</div>;
  return (
    <div className="quality-dashboard">
      <div className="quality-total">
        <span>综合质量</span>
        <strong>{quality.total}</strong>
      </div>
      {quality.items.map((item) => (
        <div className="quality-row" key={item.key}>
          <div>
            <strong>{item.label}</strong>
            <span>{item.note}</span>
          </div>
          <b>
            <i style={{ width: `${Math.max(0, Math.min(100, item.score))}%` }} />
          </b>
          <em>{item.score}</em>
        </div>
      ))}
    </div>
  );
}

function TaskUnitBars({ units }: { units: TaskVisualizationData['task_units'] }) {
  return (
    <div className="task-bars">
      {units.map((unit) => (
        <div className="task-bar-row" key={unit.task_unit_id}>
          <div>
            <strong>{unit.name}</strong>
            <span>
              {unit.satisfied_count}/{unit.requested_count} · {unit.status}
            </span>
          </div>
          <b>
            <i className={statusClass(unit.status)} style={{ width: `${Math.min(100, unit.satisfaction_ratio * 100)}%` }} />
          </b>
          <em>{Math.round(unit.satisfaction_ratio * 100)}%</em>
        </div>
      ))}
    </div>
  );
}

function BandUsage({ bands }: { bands: TaskVisualizationData['band_usage'] }) {
  return (
    <div className="band-usage">
      {bands.map((band) => (
        <article key={band.band_group}>
          <div>
            <strong>{band.band_group}</strong>
            <span>
              {band.used_width_mhz}/{band.available_width_mhz} MHz
            </span>
          </div>
          <b>
            <i style={{ width: `${Math.min(100, band.utilization_pct)}%` }} />
          </b>
          <ul>
            {band.rules.map((rule) => (
              <li key={rule.rule_id} className={rule.rule_type === '禁用' ? 'risk-high' : 'risk-medium'}>
                {rule.rule_type} {rule.start_mhz}-{rule.end_mhz} MHz · {rule.reason}
              </li>
            ))}
          </ul>
        </article>
      ))}
    </div>
  );
}

function SpectrumTimeline({ bands }: { bands: TaskVisualizationData['spectrum_timeline'] }) {
  const [selected, setSelected] = useState<{
    band: string;
    marker: TaskVisualizationData['spectrum_timeline'][number]['markers'][number];
  } | null>(null);
  if (!bands.length) return <div className="empty small">暂无频谱条带数据</div>;
  return (
    <div className="timeline-layout">
      <div className="timeline-list">
        {bands.map((band) => (
          <article key={`${band.band_group}-${band.start_mhz}`}>
            <div className="timeline-head">
              <strong>{band.band_group}</strong>
              <span>
                {band.start_mhz}-{band.end_mhz} MHz
              </span>
            </div>
            <div className="timeline-track">
              {band.markers.map((marker) => (
                <button
                  className={`timeline-marker ${markerClass(marker.kind, marker.severity)} ${
                    selected?.band === band.band_group && selected.marker.id === marker.id ? 'active' : ''
                  }`}
                  key={marker.id}
                  style={{ left: `${marker.start_pct}%`, width: `${Math.max(0.8, marker.end_pct - marker.start_pct)}%` }}
                  title={`${marker.kind} ${marker.start_mhz}-${marker.end_mhz} MHz · ${marker.label}`}
                  onClick={() => setSelected({ band: band.band_group, marker })}
                />
              ))}
            </div>
            <div className="timeline-legend">
              <span className="legend-assign">指配</span>
              <span className="legend-protect">保护</span>
              <span className="legend-forbid">禁用</span>
            </div>
          </article>
        ))}
      </div>
      <aside className="timeline-detail">
        {selected ? (
          <>
            <strong>{selected.band}</strong>
            <span>
              {selected.marker.kind} · {selected.marker.severity}
            </span>
            <p>
              {selected.marker.start_mhz}-{selected.marker.end_mhz} MHz
            </p>
            <em>{selected.marker.label}</em>
            {selected.marker.equipment_group_id && <b>{selected.marker.equipment_group_id}</b>}
          </>
        ) : (
          <div className="empty small">点击条带片段查看详情</div>
        )}
      </aside>
    </div>
  );
}

function BottleneckPanel({ analysis }: { analysis?: BottleneckAnalysis }) {
  if (!analysis) return <div className="empty small">暂无瓶颈分析数据</div>;
  const maxBandPressure = Math.max(...analysis.band_bottlenecks.map((item) => item.pressure_score), 1);
  const maxTaskPressure = Math.max(...analysis.task_unit_pressure.map((item) => item.pressure_score), 1);
  return (
    <div className="bottleneck-layout">
      <div className="bottleneck-card">
        <h3>频段压力</h3>
        <div className="bottleneck-list">
          {analysis.band_bottlenecks.slice(0, 8).map((item) => (
            <article key={item.band_group}>
              <div>
                <strong>{item.band_group}</strong>
                <span>
                  可用 {item.clean_available_width_mhz} MHz · 阻塞 {item.blocked_width_mhz} MHz
                </span>
              </div>
              <b>
                <i style={{ width: `${Math.max(4, (item.pressure_score / maxBandPressure) * 100)}%` }} />
              </b>
              <em>{item.pressure_score}</em>
              {item.top_blockers[0] && <p>{item.top_blockers[0].rule_type}：{item.top_blockers[0].reason}</p>}
            </article>
          ))}
        </div>
      </div>
      <div className="bottleneck-card">
        <h3>装备缺口</h3>
        <div className="gap-list">
          {analysis.equipment_gaps.length ? (
            analysis.equipment_gaps.slice(0, 8).map((item) => (
              <article key={item.equipment_type}>
                <strong>{item.equipment_type}</strong>
                <span>
                  缺口 {item.gap_count} 台套 · 部分 {item.partial_group_count} · 未满足 {item.unsatisfied_group_count}
                </span>
                <p>{item.main_reason}</p>
              </article>
            ))
          ) : (
            <div className="empty small">暂无装备缺口</div>
          )}
        </div>
      </div>
      <div className="bottleneck-card">
        <h3>任务压力</h3>
        <div className="task-pressure-list">
          {analysis.task_unit_pressure.slice(0, 8).map((item) => (
            <article key={item.task_unit_id}>
              <div>
                <strong>{item.name}</strong>
                <span>{item.satisfaction_ratio_pct}%</span>
              </div>
              <b>
                <i style={{ width: `${Math.max(4, (item.pressure_score / maxTaskPressure) * 100)}%` }} />
              </b>
              <em>
                部分 {item.partial_group_count} · 未满足 {item.unsatisfied_group_count} · 风险 {item.risk_count}
              </em>
            </article>
          ))}
        </div>
      </div>
      <div className="bottleneck-card conflict-card">
        <h3>冲突网络</h3>
        <ConflictNetwork analysis={analysis} />
      </div>
    </div>
  );
}

function ConflictNetwork({ analysis }: { analysis: BottleneckAnalysis }) {
  const links = analysis.contention_links.slice(0, 10);
  if (!links.length) {
    return <div className="empty small">暂无跨任务冲突链路</div>;
  }
  const unitNames = new Map(analysis.task_unit_pressure.map((item) => [item.task_unit_id, item.name]));
  const nodes = Array.from(new Set(links.flatMap((item) => [item.source_unit, item.target_unit]).filter(Boolean)));
  const width = 720;
  const height = 260;
  const cx = width / 2;
  const cy = height / 2;
  const rx = Math.max(160, width / 2 - 90);
  const ry = 88;
  const positions = new Map(
    nodes.map((node, index) => {
      const angle = (Math.PI * 2 * index) / Math.max(nodes.length, 1) - Math.PI / 2;
      return [node, { x: cx + Math.cos(angle) * rx, y: cy + Math.sin(angle) * ry }];
    }),
  );
  return (
    <div className="conflict-network">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="冲突网络">
        {links.map((link, index) => {
          const source = positions.get(link.source_unit);
          const target = positions.get(link.target_unit);
          if (!source || !target) return null;
          return (
            <line
              className={`network-link ${severityClass(link.severity)}`}
              key={`${link.source_group}-${link.target_group}-${index}`}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              strokeWidth={Math.max(1.5, Math.min(8, Number(link.score) / 14))}
            />
          );
        })}
        {nodes.map((node) => {
          const pos = positions.get(node);
          if (!pos) return null;
          const label = unitNames.get(node) ?? node;
          return (
            <g key={node}>
              <circle cx={pos.x} cy={pos.y} r="24" />
              <text x={pos.x} y={pos.y + 4} textAnchor="middle">
                {node.replace(/^TU-/, '').slice(0, 8)}
              </text>
              <title>{label}</title>
            </g>
          );
        })}
      </svg>
      <ol>
        {links.slice(0, 5).map((link, index) => (
          <li key={`${link.source_group}-${link.target_group}-${index}`}>
            <strong>
              {link.source_group} ↔ {link.target_group}
            </strong>
            <span className={severityClass(link.severity)}>{link.severity}</span>
            <p>{link.reason}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}

function SpectrumContentionPanel({ analysis }: { analysis?: SpectrumContention }) {
  if (!analysis) return <div className="empty small">暂无频谱冲突细分数据</div>;
  const maxPressure = Math.max(...analysis.bands.map((item) => item.pressure_score), 1);
  return (
    <div className="contention-layout">
      <div className="contention-bands">
        <h3>频段压力</h3>
        {analysis.bands.slice(0, 10).map((item) => (
          <article key={item.band_group}>
            <div>
              <strong>{item.band_group}</strong>
              <span>
                需求 {item.demand_width_mhz} MHz · 可用 {item.available_width_mhz} MHz · 超订 {item.oversubscription_mhz} MHz
              </span>
            </div>
            <b>
              <i style={{ width: `${Math.max(4, (item.pressure_score / maxPressure) * 100)}%` }} />
            </b>
            <em>
              压力 {item.pressure_score} · 风险 {item.risk_count}
            </em>
          </article>
        ))}
      </div>
      <div className="loss-source-list">
        <h3>频谱损失来源</h3>
        {analysis.top_loss_sources.length ? (
          analysis.top_loss_sources.slice(0, 8).map((item) => (
            <article key={`${item.rule_id}-${item.band_group}-${item.start_mhz}`}>
              <div>
                <strong>{item.band_group}</strong>
                <span className={severityClass(item.severity)}>{item.rule_type}</span>
              </div>
              <p>
                {item.start_mhz}-{item.end_mhz} MHz · 损失 {item.width_mhz} MHz
              </p>
              <em>{item.reason}</em>
            </article>
          ))
        ) : (
          <div className="empty small">暂无明显禁用/保护损失来源</div>
        )}
      </div>
    </div>
  );
}

function AssignmentMatrix({ assignments }: { assignments: TaskVisualizationData['assignments'] }) {
  return (
    <div className="assignment-table-wrap">
      <table className="assignment-table">
        <thead>
          <tr>
            <th>任务单元</th>
            <th>装备组</th>
            <th>类型</th>
            <th>模式</th>
            <th>频段池</th>
            <th>指配资源</th>
            <th>满足</th>
            <th>状态</th>
            <th>原因</th>
            <th>审核提示</th>
            <th>备选资源</th>
          </tr>
        </thead>
        <tbody>
          {assignments.map((item) => (
            <tr key={item.equipment_group_id}>
              <td>{item.task_unit_id}</td>
              <td>{item.equipment_group_id}</td>
              <td>{item.equipment_type}</td>
              <td>{item.assignment_mode}</td>
              <td>{item.band_group ?? '-'}</td>
              <td>{item.assigned_resource || '-'}</td>
              <td>
                {item.satisfied_count}/{item.requested_count}
              </td>
              <td className={statusClass(item.status)}>{item.status}</td>
              <td>{item.reason}</td>
              <td>{item.explanation_chain?.audit_hint ?? '-'}</td>
              <td>
                <AlternativeList items={item.alternative_resources ?? []} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AssignmentExplanationPanel({ assignments }: { assignments: TaskVisualizationData['assignments'] }) {
  const rows = assignments
    .filter((item) => item.explanation_chain)
    .sort((a, b) => {
      const aScore = (a.status === '完全满足' ? 0 : 100) + a.risk_score;
      const bScore = (b.status === '完全满足' ? 0 : 100) + b.risk_score;
      return bScore - aScore;
    })
    .slice(0, 10);
  if (!rows.length) return <div className="empty small">暂无装备组解释链</div>;
  return (
    <div className="explain-chain-list">
      {rows.map((item) => {
        const chain = item.explanation_chain;
        return (
          <article key={item.equipment_group_id}>
            <div className="explain-chain-head">
              <strong>{item.equipment_group_id}</strong>
              <span className={statusClass(item.status)}>{item.status}</span>
              {item.required_full && <em>必须完全满足</em>}
            </div>
            <p>{chain?.why_selected.join('；') || item.reason}</p>
            <div className="explain-chain-columns">
              <div>
                <b>未选原因</b>
                {(chain?.why_rejected ?? []).slice(0, 3).map((row) => (
                  <span key={`${item.equipment_group_id}-${row.band_group}`}>
                    {row.band_group}：{row.reason}
                  </span>
                ))}
              </div>
              <div>
                <b>阻断规则</b>
                {(chain?.blocking_rules ?? []).slice(0, 3).map((rule) => (
                  <span key={`${item.equipment_group_id}-${rule.rule_id}`}>
                    {rule.rule_type} {rule.start_mhz}-{rule.end_mhz} MHz
                  </span>
                ))}
                {!(chain?.blocking_rules ?? []).length && <span>无明显规则阻断</span>}
              </div>
              <div>
                <b>资源缺口</b>
                <span>
                  缺 {chain?.required_extra_resource.missing_channels ?? 0} 个信道，约{' '}
                  {chain?.required_extra_resource.estimated_extra_width_mhz ?? 0} MHz
                </span>
                <span>{chain?.required_extra_resource.suggestion ?? '暂无额外建议'}</span>
              </div>
            </div>
            <em>{chain?.audit_hint}</em>
          </article>
        );
      })}
    </div>
  );
}

function AlternativeList({
  items,
}: {
  items: NonNullable<TaskVisualizationData['assignments'][number]['alternative_resources']>;
}) {
  if (!items.length) return <span className="muted">无</span>;
  return (
    <div className="alternative-list">
      {items.slice(0, 3).map((item) => (
        <article key={`${item.band_group}-${item.resource}-${item.reason}`}>
          <strong>{item.band_group}</strong>
          <span className={item.status === '可用' ? 'risk-low' : item.status === '部分可用' ? 'risk-medium' : 'risk-high'}>{item.status}</span>
          <em>{item.resource || item.reason}</em>
        </article>
      ))}
    </div>
  );
}

function DiagnosticList({ items }: { items: DiagnosticItem[] }) {
  if (!items.length) return <div className="empty small">暂无诊断建议</div>;
  return (
    <div className="diagnostic-list">
      {items.slice(0, 8).map((item) => (
        <article key={`${item.category}-${item.target}-${item.reason}`}>
          <div>
            <strong>{item.category}</strong>
            <span className={severityClass(item.severity)}>{item.severity}</span>
          </div>
          <p>{item.reason}</p>
          <em>{item.suggestion}</em>
        </article>
      ))}
    </div>
  );
}

function ScoreExplanationPanel({ score }: { score: TaskComparisonPlan['score_explanation'] }) {
  if (!score) return <div className="empty small">暂无评分解释</div>;
  const max = Math.max(...score.components.map((item) => item.value), 1);
  return (
    <div className="score-panel">
      <div className="score-total">
        <span>综合分</span>
        <strong>{score.total_score}</strong>
      </div>
      {score.components.map((item) => (
        <div className="score-row" key={item.key}>
          <span>{item.label}</span>
          <b>
            <i style={{ width: `${(item.value / max) * 100}%` }} />
          </b>
          <em>{item.value}</em>
        </div>
      ))}
    </div>
  );
}

function ReasonRank({ items }: { items: Array<{ reason: string; count: number }> }) {
  if (!items.length) return <div className="empty small">暂无部分满足或风险原因</div>;
  const max = Math.max(...items.map((item) => item.count), 1);
  return (
    <div className="reason-rank">
      {items.slice(0, 8).map((item) => (
        <div key={item.reason}>
          <span>{item.reason}</span>
          <b>
            <i style={{ width: `${(item.count / max) * 100}%` }} />
          </b>
          <em>{item.count}</em>
        </div>
      ))}
    </div>
  );
}

function SummaryBlock({ data }: { data?: Record<string, unknown> }) {
  if (!data) return <div className="empty small">暂无数据</div>;
  return (
    <div className="summary-grid">
      {Object.entries(data).map(([key, value]) => (
        <div key={key}>
          <span>{key}</span>
          <strong>{Array.isArray(value) ? value.join('、') : String(value)}</strong>
        </div>
      ))}
    </div>
  );
}

function IssueList({ title, items, type }: { title: string; items: string[]; type: 'error' | 'warning' }) {
  if (!items.length) return null;
  return (
    <div className={`issues ${type}`}>
      <h3>{title}</h3>
      <ul>
        {items.slice(0, 10).map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: unknown }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{String(value ?? '-')}</strong>
    </div>
  );
}

function VersionAuditPanel({
  data,
  activeRunId,
  onRefresh,
  onSelectRun,
  onReuseRun,
  onAdoptRun,
  onRollbackRun,
}: {
  data: TaskVersionsResult | null;
  activeRunId?: number | null;
  onRefresh: () => void;
  onSelectRun: (run: TaskVersionRun) => void;
  onReuseRun: (run: TaskVersionRun) => void;
  onAdoptRun: (run: TaskVersionRun) => void;
  onRollbackRun: (run: TaskVersionRun) => void;
}) {
  const activeRun = activeRunId ? data?.runs.find((run) => run.run_id === activeRunId) ?? null : null;
  const comparison = data && activeRun ? buildRunComparison(data.runs, activeRun.run_id) : null;
  return (
    <section className="panel version-panel">
      <div className="report-header">
        <div className="panel-title">
          <RefreshCw size={18} />
          <h2>版本与审计</h2>
        </div>
        <button className="small-button" onClick={onRefresh}>
          刷新
        </button>
      </div>
      {!data ? (
        <div className="empty small">完成规划后显示版本和审计记录</div>
      ) : (
        <div className="version-grid">
          <div>
            <h3>规划版本</h3>
            <div className="version-list">
              {data.runs.slice(0, 8).map((run) => {
                const trialContext = run.replan_effect?.trial_context;
                return (
                  <article key={run.run_id} className={run.run_id === activeRunId ? 'active' : ''}>
                    <div className="version-head">
                      <div>
                        <strong>#{run.run_id}</strong>
                        <span>{objectiveLabel(String(run.summary.requested_objective ?? run.objective)) || run.objective}</span>
                        <span className={`version-lifecycle ${run.adopted ? 'adopted' : ''}`}>{run.lifecycle_status}</span>
                      </div>
                      <em>{new Date(run.created_at).toLocaleString()}</em>
                    </div>
                    <em>
                      保障 {String(run.summary.task_satisfaction_avg ?? '-')}% · 质量 {formatRunMetric(run, 'quality')} · 风险 {String(run.summary.high_risk_count ?? 0)}/
                      {String(run.summary.medium_risk_count ?? 0)}
                    </em>
                    {trialContext?.label && (
                      <em className="version-trial">
                        试算 {trialContext.label} · {run.replan_effect?.prediction_alignment?.summary ?? run.replan_effect?.status_label ?? '已执行'}
                      </em>
                    )}
                    <div className="version-actions">
                      <button type="button" onClick={() => onSelectRun(run)}>
                        <Eye size={14} />
                        查看
                      </button>
                      <button type="button" onClick={() => onReuseRun(run)}>
                        <RotateCcw size={14} />
                        复用策略
                      </button>
                      {!run.adopted && run.snapshot_available && (
                        <button type="button" onClick={() => onAdoptRun(run)}>
                          <Save size={14} />
                          正式采纳
                        </button>
                      )}
                      {run.snapshot_available && (
                        <button type="button" className="rollback" onClick={() => onRollbackRun(run)}>
                          <RotateCcw size={14} />
                          恢复输入
                        </button>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
          <div>
            <h3>版本对比</h3>
            {comparison ? (
              <div className="version-compare">
                <div>
                  <strong>当前 #{comparison.current.run_id}</strong>
                  <span>对比 #{comparison.previous.run_id}</span>
                </div>
                <VersionDelta label="保障率" value={comparison.satisfactionDelta} suffix="%" />
                <VersionDelta label="质量分" value={comparison.qualityDelta} />
                <VersionDelta label="高风险" value={comparison.highRiskDelta} inverse />
                <VersionDelta label="未满足" value={comparison.unsatisfiedDelta} inverse />
                <VersionDelta label="已用带宽" value={comparison.bandwidthDelta} suffix=" MHz" inverse />
                {comparison.current.replan_effect && <VersionEffectSummary effect={comparison.current.replan_effect} />}
              </div>
            ) : (
              <div className="empty small">选择有上一版本的规划后显示对比</div>
            )}
          </div>
          <ClosureEventPanel events={data.closure_events ?? []} />
          <div>
            <h3>审计记录</h3>
            <div className="audit-list">
              {data.audit_logs.slice(0, 10).map((log) => (
                <article key={log.id}>
                  <strong>{auditActionLabel(log.action)}</strong>
                  <span>{log.run_id ? `运行 #${log.run_id}` : '项目级'}</span>
                  <em>{auditLogSummary(log)}</em>
                </article>
              ))}
            </div>
          </div>
          <div>
            <h3>压测历史</h3>
            <div className="audit-list">
              {(data.performance_history ?? []).slice(0, 6).map((item) => (
                <article key={`${item.created_at}-${item.run_count}`}>
                  <strong>{item.run_count} 次求解 · {item.capacity_profile?.status ?? '未形成容量画像'}</strong>
                  <span>{new Date(item.created_at).toLocaleString()}</span>
                  <em>
                    推荐 {capacityScaleLabel(item.capacity_profile?.recommended)} · 最大 {capacityScaleLabel(item.capacity_profile?.largest)} · 耗时 {item.max_elapsed_ms} ms
                  </em>
                  {item.capacity_profile?.problem_focus && <em>瓶颈：{item.capacity_profile.problem_focus}</em>}
                </article>
              ))}
              {!(data.performance_history ?? []).length && <div className="empty small">暂无项目压测历史</div>}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function ClosureEventPanel({ events }: { events: NonNullable<TaskVersionsResult['closure_events']> }) {
  return (
    <div>
      <h3>闭环审计</h3>
      {events.length ? (
        <div className="closure-event-list">
          {events.slice(0, 6).map((event) => {
            const maxRisk = Math.max(event.before_cross_batch_risk_count, event.after_cross_batch_risk_count, 1);
            return (
              <article key={event.id} className={event.improved ? 'improved' : 'flat'}>
                <div className="closure-event-head">
                  <strong>闭环 #{event.id}</strong>
                  <span>{new Date(event.created_at).toLocaleString()}</span>
                </div>
                <p>{event.summary || `跨批风险 ${event.before_cross_batch_risk_count} -> ${event.after_cross_batch_risk_count}`}</p>
                <div className="closure-event-metrics">
                  <span>硬约束 {event.applied_rule_count}</span>
                  <span>已解决 {event.resolved_cross_batch_risk_count}</span>
                  <span>关联版本 {event.run_ids.map((item) => `#${item}`).join(', ') || '-'}</span>
                </div>
                <div className="closure-event-bars">
                  <i className="before" style={{ width: `${Math.max(5, (event.before_cross_batch_risk_count / maxRisk) * 100)}%` }} />
                  <i className="after" style={{ width: `${Math.max(5, (event.after_cross_batch_risk_count / maxRisk) * 100)}%` }} />
                </div>
                {event.rules.length ? (
                  <div className="closure-event-rules">
                    {event.rules.slice(0, 3).map((rule) => (
                      <span key={`${event.id}-${rule.batch_id}-${rule.task_unit_id}-${rule.avoid_band_group}`}>
                        {rule.batch_id} · {rule.task_unit_id} 避用 {rule.avoid_band_group}
                      </span>
                    ))}
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      ) : (
        <div className="empty small">暂无闭环重算审计</div>
      )}
    </div>
  );
}

function VersionDelta({ label, value, suffix = '', inverse = false }: { label: string; value: number; suffix?: string; inverse?: boolean }) {
  const rounded = Math.round(value * 10) / 10;
  const improved = inverse ? rounded < 0 : rounded > 0;
  const worsened = inverse ? rounded > 0 : rounded < 0;
  return (
    <article className={improved ? 'up' : worsened ? 'down' : 'flat'}>
      <span>{label}</span>
      <strong>
        {rounded > 0 ? '+' : ''}
        {rounded}
        {suffix}
      </strong>
    </article>
  );
}

function VersionEffectSummary({ effect }: { effect: ReplanEffect }) {
  const trialContext = effect.trial_context;
  const alignment = effect.prediction_alignment;
  return (
    <div className="version-effect-note">
      <strong>{trialContext?.label ? `采用试算：${trialContext.label}` : effect.status_label}</strong>
      <span>{effect.summary}</span>
      {trialContext?.decision && <em>{trialContext.decision}</em>}
      {alignment?.total_count ? <em>{alignment.summary}</em> : null}
    </div>
  );
}

function buildRunComparison(runs: TaskVersionRun[], currentRunId: number) {
  const ordered = [...runs].sort((a, b) => a.run_id - b.run_id);
  const currentIndex = ordered.findIndex((run) => run.run_id === currentRunId);
  if (currentIndex <= 0) return null;
  const previous = ordered[currentIndex - 1];
  const current = ordered[currentIndex];
  return {
    previous,
    current,
    satisfactionDelta: numberMetric(current.summary.task_satisfaction_avg) - numberMetric(previous.summary.task_satisfaction_avg),
    qualityDelta: runQuality(current) - runQuality(previous),
    highRiskDelta: numberMetric(current.summary.high_risk_count) - numberMetric(previous.summary.high_risk_count),
    unsatisfiedDelta: numberMetric(current.summary.unsatisfied_group_count) - numberMetric(previous.summary.unsatisfied_group_count),
    bandwidthDelta: numberMetric(current.summary.used_bandwidth_mhz) - numberMetric(previous.summary.used_bandwidth_mhz),
  };
}

function auditActionLabel(action: string): string {
  const labels: Record<string, string> = {
    task_strategy_trials: '多策略试算',
    task_replan_preview: '重规划预览',
    task_replan: '执行重规划',
    task_plan_success: '规划成功',
    task_plan_failed: '规划失败',
    task_compare: '目标对比',
    task_plan_adopted: '正式采纳方案',
    task_plan_rollback_restore: '恢复方案输入',
    task_plan_rollback_completed: '完成方案回滚',
  };
  return labels[action] ?? action;
}

function auditLogSummary(log: TaskAuditLog): string {
  const detail = safeJsonRecord(log.detail);
  if (!Object.keys(detail).length) return shorten(log.detail, 120);
  if (log.action === 'task_strategy_trials') {
    const count = numberValue(detail.candidate_count);
    const variantCount = numberValue(detail.constraint_variant_count);
    const recommended = stringValue(detail.recommended_trial_id);
    return shorten(`生成 ${count ?? 0} 个候选、${variantCount ?? 0} 类约束变体；推荐 ${recommended || '-'}`, 140);
  }
  if (log.action === 'task_replan' || log.action === 'task_replan_preview') {
    const trial = recordValue(detail.trial_context);
    const trialLabel = stringValue(trial.label);
    const objective = objectiveLabel(stringValue(detail.objective)) || stringValue(detail.objective) || '当前目标';
    const baseRunId = numberValue(detail.base_run_id);
    const changeCount = numberValue(detail.change_count);
    const parts = [
      trialLabel ? `采用试算“${trialLabel}”` : '',
      baseRunId ? `基线 #${baseRunId}` : '',
      objective,
      typeof changeCount === 'number' ? `${changeCount} 项变更` : '',
    ].filter(Boolean);
    return shorten(parts.join('；') || log.detail, 140);
  }
  if (typeof detail.message === 'string') return shorten(detail.message, 140);
  return shorten(JSON.stringify(detail), 140);
}

function formatRunMetric(run: TaskVersionRun, key: 'quality') {
  if (key === 'quality') return runQuality(run).toFixed(1);
  return '-';
}

function runQuality(run: TaskVersionRun): number {
  return numberMetric(recordValue(run.summary.quality_scores).total);
}

function formatProjectDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return '--';
  return parsed.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function formatMissionTime(value: string | null): string {
  if (!value) return '未设置';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value.replace('T', ' ').slice(0, 16);
  return parsed.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

function numberMetric(value: unknown): number {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function buildTaskDiff(previous: TaskVisualizationData | null, current: TaskVisualizationData) {
  if (!previous) return null;
  const before = new Map(previous.assignments.map((item) => [item.equipment_group_id, item]));
  const after = new Map(current.assignments.map((item) => [item.equipment_group_id, item]));
  const groupIds = Array.from(new Set([...before.keys(), ...after.keys()])).sort();
  const rows = groupIds
    .map((groupId) => {
      const oldItem = before.get(groupId);
      const newItem = after.get(groupId);
      const ratioDelta = (newItem?.satisfaction_ratio ?? 0) - (oldItem?.satisfaction_ratio ?? 0);
      const resourceChanged = (oldItem?.assigned_resource ?? '') !== (newItem?.assigned_resource ?? '');
      if (!resourceChanged && Math.abs(ratioDelta) < 0.0001) return null;
      return {
        groupId,
        beforeStatus: oldItem?.status ?? '-',
        afterStatus: newItem?.status ?? '-',
        ratioDelta,
        resourceChanged,
      };
    })
    .filter((item): item is NonNullable<typeof item> => item !== null)
    .sort((a, b) => Math.abs(b.ratioDelta) - Math.abs(a.ratioDelta));
  return {
    rows,
    changedAssignments: rows.filter((row) => row.resourceChanged).length,
    improved: rows.filter((row) => row.ratioDelta > 0).length,
    worsened: rows.filter((row) => row.ratioDelta < 0).length,
    avgDelta: Number(current.summary.task_satisfaction_avg ?? 0) - Number(previous.summary.task_satisfaction_avg ?? 0),
  };
}

function replanOverridesFromAction(action: AgentSuggestedAction): Partial<TaskReplanPayload> {
  const payload = action.deterministic_payload ?? {};
  const overrides: Partial<TaskReplanPayload> = { message: action.suggested_message };
  const baseRunId = numberValue(payload.base_run_id);
  if (baseRunId) overrides.base_run_id = baseRunId;
  const reuseStrategyFromRunId = numberValue(payload.reuse_strategy_from_run_id);
  if (reuseStrategyFromRunId) overrides.reuse_strategy_from_run_id = reuseStrategyFromRunId;
  const objective = stringValue(payload.objective);
  if (objective) overrides.objective = objective;
  const strategyProfile = stringValue(payload.strategy_profile);
  if (strategyProfile) overrides.strategy_profile = strategyProfile;
  const requiredFullTargets = stringArrayValue(payload.required_full_targets);
  if (requiredFullTargets.length) overrides.required_full_targets = requiredFullTargets;
  const avoidBandGroups = stringArrayValue(payload.avoid_band_groups);
  if (avoidBandGroups.length) overrides.avoid_band_groups = avoidBandGroups;
  const lockedGroups = stringArrayValue(payload.locked_equipment_group_ids);
  if (lockedGroups.length) overrides.locked_equipment_group_ids = lockedGroups;
  const lockedUnits = stringArrayValue(payload.locked_task_unit_ids);
  if (lockedUnits.length) overrides.locked_task_unit_ids = lockedUnits;
  const forcedBandGroups = stringRecordValue(payload.forced_band_groups);
  if (Object.keys(forcedBandGroups).length) overrides.forced_band_groups = forcedBandGroups;
  const constraintWeights = constraintWeightsValue(payload.constraint_weights);
  if (Object.keys(constraintWeights).length) overrides.constraint_weights = constraintWeights;
  const availableRanges = availableRangesValue(payload.available_ranges);
  if (availableRanges.length) overrides.available_ranges = availableRanges;
  const forbiddenRanges = forbiddenRangesValue(payload.forbidden_ranges);
  if (forbiddenRanges.length) overrides.forbidden_ranges = forbiddenRanges;
  const priorityUpdates = priorityUpdatesValue(payload.priority_updates);
  if (priorityUpdates.length) overrides.priority_updates = priorityUpdates;
  const satisfactionUpdates = satisfactionUpdatesValue(payload.satisfaction_updates);
  if (satisfactionUpdates.length) overrides.satisfaction_updates = satisfactionUpdates;
  if (typeof payload.allow_low_priority_degrade === 'boolean') {
    overrides.allow_low_priority_degrade = payload.allow_low_priority_degrade;
  }
  return overrides;
}

function agentActionButtonLabel(action: AgentSuggestedAction): string {
  const operation = stringValue(action.deterministic_payload.operation);
  if (operation === 'task_performance_batch') return '运行压测';
  if (operation === 'capacity_batch_planning') {
    return recordValue(action.deterministic_payload.batch_plan).available ? '生成子规划' : '查看容量边界';
  }
  if (operation === 'export_report') return '打开报告';
  if (operation === 'select_task_run') return '切回版本';
  if (operation === 'preview_replan_from_suggestion') return '查看重规划区';
  if (action.action_id === 'pivot_after_flat_replan') return '转向策略';
  if (availableRangesValue(action.deterministic_payload.available_ranges).length) return '补充频段';
  return '转入重规划';
}

function stringValue(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function splitList(value: string): string[] {
  return value
    .split(/[,\s，、;；]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function stringArrayValue(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((item) => String(item).trim()).filter(Boolean);
  if (typeof value === 'string') return splitList(value);
  return [];
}

function numberValue(value: unknown): number | null {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function dashboardFirstNumber(...values: Array<number | null | undefined>): number | null {
  for (const value of values) {
    if (typeof value === 'number' && Number.isFinite(value)) return value;
  }
  return null;
}

function dashboardMetricValue(value: number | null | undefined, suffix = '', decimals = 0): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '待生成';
  const formatted = Number.isInteger(value) && decimals === 0 ? String(value) : value.toFixed(decimals);
  return `${formatted}${suffix}`;
}

function dashboardReadinessStatus(
  project: Project | null,
  validation: TaskValidationResult | null,
  plan: PlanResult | null,
  visualization: TaskVisualizationData | null,
  highRiskCount: number,
): { label: string; detail: string; tone: 'ready' | 'pending' | 'warning' | 'danger' } {
  if (!project) return { label: '待创建', detail: '先创建规划项目', tone: 'pending' };
  if (plan?.status === 'success' && visualization && highRiskCount > 0) return { label: '需复核', detail: `${highRiskCount} 条高风险`, tone: 'danger' };
  if (plan?.status === 'success' && visualization) return { label: '可交付', detail: `方案 #${plan.run_id}`, tone: 'ready' };
  if (validation && !validation.ok) return { label: '待修正', detail: `${validation.errors.length} 个错误`, tone: 'danger' };
  if (validation?.ok) return { label: '可规划', detail: '输入校验通过', tone: 'ready' };
  return { label: '待校验', detail: '接入数据后校验', tone: 'warning' };
}

function isHighRiskSeverity(severity: string): boolean {
  const normalized = severity.toLowerCase();
  return severity.includes('高') || normalized.includes('high');
}

function isMediumRiskSeverity(severity: string): boolean {
  const normalized = severity.toLowerCase();
  return severity.includes('中') || normalized.includes('medium');
}

function riskTone(severity: string): string {
  if (isHighRiskSeverity(severity)) return 'high';
  if (isMediumRiskSeverity(severity)) return 'medium';
  return 'low';
}

function recordValue(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  return value as Record<string, unknown>;
}

function safeJsonRecord(value: string): Record<string, unknown> {
  try {
    return recordValue(JSON.parse(value));
  } catch {
    return {};
  }
}

function stringRecordValue(value: unknown): Record<string, string> {
  const record = recordValue(value);
  return Object.fromEntries(
    Object.entries(record)
      .map(([key, item]) => [key.trim(), String(item).trim()])
      .filter(([key, item]) => key && item),
  );
}

function constraintWeightsValue(value: unknown): Partial<ConstraintWeights> {
  const record = recordValue(value);
  const result: Partial<ConstraintWeights> = {};
  (['task', 'risk', 'spectrum', 'priority', 'switching', 'reuse'] as const).forEach((key) => {
    const number = numberValue(record[key]);
    if (number !== null) result[key] = Math.max(0, Math.min(100, number));
  });
  return result;
}

function availableRangesValue(value: unknown): TaskReplanPayload['available_ranges'] {
  return frequencyRangesValue(value, '建议动作补充可用频段');
}

function forbiddenRangesValue(value: unknown): TaskReplanPayload['forbidden_ranges'] {
  return frequencyRangesValue(value, '建议动作追加禁用');
}

function frequencyRangesValue(
  value: unknown,
  fallbackReason: string,
): Array<{ band_group?: string; start_mhz: number; end_mhz: number; reason?: string }> {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    const record = recordValue(item);
    const start = numberValue(record.start_mhz);
    const end = numberValue(record.end_mhz);
    if (start === null || end === null || end <= start) return [];
    return [
      {
        band_group: stringValue(record.band_group) || undefined,
        start_mhz: start,
        end_mhz: end,
        reason: stringValue(record.reason) || fallbackReason,
      },
    ];
  });
}

function priorityUpdatesValue(value: unknown): TaskReplanPayload['priority_updates'] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    const record = recordValue(item);
    const target = stringValue(record.target);
    const priority = numberValue(record.priority);
    if (!target || priority === null) return [];
    return [{ target, priority: Math.max(1, Math.min(10, Math.round(priority))) }];
  });
}

function satisfactionUpdatesValue(value: unknown): TaskReplanPayload['satisfaction_updates'] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    const record = recordValue(item);
    const taskUnitId = stringValue(record.task_unit_id);
    const ratio = numberValue(record.min_satisfaction_ratio);
    if (!taskUnitId || ratio === null) return [];
    return [{ task_unit_id: taskUnitId, min_satisfaction_ratio: Math.max(0.1, Math.min(1, ratio)) }];
  });
}

const EQUIPMENT_TYPE_COLORS = [
  '#2563eb',
  '#059669',
  '#d97706',
  '#7c3aed',
  '#dc2626',
  '#0891b2',
  '#65a30d',
  '#c2410c',
  '#4f46e5',
  '#be185d',
  '#0f766e',
  '#9333ea',
];

function equipmentTypeForMarker(
  marker: TaskVisualizationData['spectrum_timeline'][number]['markers'][number],
  assignmentByGroup: Map<string, TaskVisualizationData['assignments'][number]>,
): string {
  if (marker.kind !== '指配' || !marker.equipment_group_id) return '';
  return assignmentByGroup.get(marker.equipment_group_id)?.equipment_type ?? '';
}

function markerColorForMarker(
  marker: TaskVisualizationData['spectrum_timeline'][number]['markers'][number],
  equipmentColorByType: Map<string, string>,
  equipmentType: string,
): string {
  if (marker.kind === '禁用') return '#d92d20';
  if (marker.kind === '保护') return '#f79009';
  return equipmentColorByType.get(equipmentType) ?? '#2563eb';
}

function markerClass(kind: string, severity: string): string {
  if (kind === '禁用') return 'marker-forbid';
  if (kind === '保护') return 'marker-protect';
  if (severity === '高') return 'marker-risk';
  return 'marker-assign';
}

function markerRise(kind: string, severity: string): number {
  if (kind === '禁用') return 22;
  if (severity === '高') return 20;
  if (severity === '中') return 15;
  if (kind === '保护') return 12;
  return 8;
}

function spatialPriority(marker: TaskVisualizationData['spectrum_timeline'][number]['markers'][number]): number {
  if (marker.severity === '高') return 5;
  if (marker.kind === '禁用') return 4;
  if (marker.severity === '中') return 3;
  if (marker.kind === '保护') return 2;
  return 1;
}

function spatialNodePosition(index: number, marker: TaskVisualizationData['spectrum_timeline'][number]['markers'][number]): { left: number; top: number } {
  const label = nodeLabel(marker).toUpperCase();
  let anchor = { left: 40, top: 46 };
  if (label.includes('RAD')) anchor = { left: 76, top: 30 };
  else if (label.includes('UAV')) anchor = { left: 74, top: 68 };
  else if (label.includes('COM') || label.includes('SIM')) anchor = { left: 32, top: 42 };
  else if (label.includes('EW') || marker.kind === '禁用' || marker.kind === '保护') anchor = { left: 47, top: 74 };
  const offsets = [
    { left: 0, top: 0 },
    { left: -8, top: 8 },
    { left: 8, top: 7 },
    { left: -11, top: -8 },
    { left: 11, top: -8 },
  ];
  const offset = offsets[index % offsets.length];
  const spread = Math.floor(index / offsets.length) * 3;
  return {
    left: Math.max(10, Math.min(90, anchor.left + offset.left + spread)),
    top: Math.max(18, Math.min(86, anchor.top + offset.top)),
  };
}

function nodeLabel(marker: TaskVisualizationData['spectrum_timeline'][number]['markers'][number]): string {
  return marker.equipment_group_id || marker.task_unit_id || marker.label || marker.kind;
}

function severityClass(severity: string): string {
  if (severity === '高') return 'risk-high';
  if (severity === '中') return 'risk-medium';
  return 'risk-low';
}

function priorityClass(priority: string): string {
  if (priority === '高') return 'risk-high';
  if (priority === '中') return 'risk-medium';
  return 'risk-low';
}

function scoreClass(score: number): string {
  if (score >= 90) return 'risk-low';
  if (score >= 75) return 'status-full';
  if (score >= 60) return 'risk-medium';
  return 'risk-high';
}

function statusClass(status: string): string {
  if (status === '完全满足') return 'status-full';
  if (status === '部分满足') return 'status-partial';
  return 'status-none';
}

function shorten(value: string, length: number): string {
  if (!value) return '-';
  return value.length > length ? `${value.slice(0, length)}...` : value;
}

function formatSigned(value: number): string {
  if (Math.abs(value) < 0.001) return '0';
  return `${value > 0 ? '+' : ''}${value.toFixed(1)}`;
}

function defaultSpectrumRulePayload(bands: string[]): TaskSpectrumRulePayload {
  return {
    rule_id: '',
    rule_type: '禁用',
    band_group: bands[0] ?? 'S-SIM-1',
    spectrum_relation: '禁用',
    start_mhz: 2210,
    end_mhz: 2215,
    channel_step_khz: 25,
    max_bandwidth_khz: 0,
    max_power_w: 0,
    guard_band_khz: 100,
    compatible_unit_types: '',
    compatible_equipment_types: '',
    reason: '界面新增约束',
    source: 'USER_UI',
    severity: '高',
  };
}

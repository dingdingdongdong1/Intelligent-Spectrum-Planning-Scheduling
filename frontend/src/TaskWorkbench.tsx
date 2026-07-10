import { useEffect, useMemo, useState } from 'react';
import { Boxes, Cable, ClipboardList, Pencil, Plus, RefreshCw, Save, Timer, Trash2, Upload } from 'lucide-react';
import {
  EquipmentGroupPayload,
  MissionTaskPayload,
  TaskLinkPayload,
  TaskPhasePayload,
  TaskProjectData,
  TaskUnitPayload,
  createEquipmentGroup,
  createTaskLink,
  createTaskPhase,
  createTaskUnit,
  deleteEquipmentGroup,
  deleteTaskLink,
  deleteTaskPhase,
  deleteTaskUnit,
  getTaskProjectData,
  importTaskPackage,
  saveMissionTask,
  updateEquipmentGroup,
  updateTaskLink,
  updateTaskPhase,
  updateTaskUnit,
} from './api';

type WorkbenchTab = 'mission' | 'phases' | 'units' | 'equipment' | 'links' | 'import';

type Props = {
  projectId: number | null;
  busy: boolean;
  revision: number;
  onDataChange: (data: TaskProjectData) => void;
};

const emptyData: TaskProjectData = {
  mission: null,
  phases: [],
  links: [],
  task_units: [],
  equipment_groups: [],
  spectrum_rules: [],
};

const defaultMission: MissionTaskPayload = {
  mission_id: 'MISSION-001',
  name: '新建任务',
  mission_type: '作战任务',
  description: '',
  priority: 8,
  required_assurance: 0.9,
  starts_at: null,
  ends_at: null,
  region_name: '',
  center_lat: null,
  center_lon: null,
  area_radius_km: 20,
  mobility_range_km: 10,
  commander_intent: '',
  status: '筹划中',
};

const defaultPhase: TaskPhasePayload = {
  phase_id: 'PHASE-01',
  name: '任务准备',
  sequence: 1,
  starts_at: null,
  ends_at: null,
  status: '待开始',
  area_center_lat: null,
  area_center_lon: null,
  area_radius_km: 20,
  notes: '',
};

const defaultUnit: TaskUnitPayload = {
  task_unit_id: 'TU-001',
  name: '任务单元',
  unit_type: '通信保障单元',
  area_center_lat: null,
  area_center_lon: null,
  area_radius_km: 10,
  priority: 7,
  spectrum_relation: '可复用',
  preferred_band_groups: '',
  min_satisfaction_ratio: 0.9,
};

const defaultEquipment: EquipmentGroupPayload = {
  equipment_group_id: 'EG-001',
  task_unit_id: '',
  equipment_type: '战术通信电台',
  count: 1,
  tx_rx_role: '双工',
  mobility: '机动',
  bandwidth_khz: 25,
  tx_power_w: 20,
  antenna_gain_dbi: 3,
  antenna_height_m: 2,
  receiver_sensitivity_dbm: -100,
  modulation: 'FM',
  duplex_mode: '单工',
  required_channels: 1,
  assignment_mode: '离散信道',
  preferred_band_group: '',
  priority: 7,
  protection_distance_km: 3,
  min_spacing_khz: 25,
  guard_band_khz: 25,
};

const defaultLink: TaskLinkPayload = {
  link_id: 'LINK-001',
  name: '任务链路',
  link_type: '通信链路',
  source_task_unit_id: '',
  target_task_unit_id: '',
  source_equipment_group_id: '',
  target_equipment_group_id: '',
  direction: '双向',
  priority: 8,
  required_availability: 0.95,
  bandwidth_khz: 25,
  required_channels: 1,
  primary_band_group: '',
  backup_band_group: '',
  active_phase_ids: [],
  notes: '',
};

export default function TaskWorkbench({ projectId, busy, revision, onDataChange }: Props) {
  const [tab, setTab] = useState<WorkbenchTab>('mission');
  const [data, setData] = useState<TaskProjectData>(emptyData);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [mission, setMission] = useState<MissionTaskPayload>(defaultMission);
  const [phase, setPhase] = useState<TaskPhasePayload>(defaultPhase);
  const [unit, setUnit] = useState<TaskUnitPayload>(defaultUnit);
  const [equipment, setEquipment] = useState<EquipmentGroupPayload>(defaultEquipment);
  const [link, setLink] = useState<TaskLinkPayload>(defaultLink);
  const [editingPhase, setEditingPhase] = useState<number | null>(null);
  const [editingUnit, setEditingUnit] = useState<number | null>(null);
  const [editingEquipment, setEditingEquipment] = useState<number | null>(null);
  const [editingLink, setEditingLink] = useState<number | null>(null);
  const [taskUnitsFile, setTaskUnitsFile] = useState<File | null>(null);
  const [equipmentFile, setEquipmentFile] = useState<File | null>(null);
  const [rulesFile, setRulesFile] = useState<File | null>(null);

  const unavailable = busy || loading || !projectId;
  const unitOptions = useMemo(() => data.task_units.map((item) => item.task_unit_id), [data.task_units]);

  async function load() {
    if (!projectId) {
      setData(emptyData);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const result = await getTaskProjectData(projectId);
      const normalized: TaskProjectData = {
        mission: result.mission ?? null,
        phases: result.phases ?? [],
        links: result.links ?? [],
        task_units: result.task_units ?? [],
        equipment_groups: result.equipment_groups ?? [],
        spectrum_rules: result.spectrum_rules ?? [],
      };
      setData(normalized);
      if (normalized.mission) setMission(stripRecord(normalized.mission));
      onDataChange(normalized);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '任务数据读取失败');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [projectId, revision]);

  useEffect(() => {
    if (!unitOptions.length) return;
    setEquipment((current) => ({
      ...current,
      task_unit_id: unitOptions.includes(current.task_unit_id) ? current.task_unit_id : unitOptions[0],
    }));
    setLink((current) => ({
      ...current,
      source_task_unit_id: current.source_task_unit_id && unitOptions.includes(current.source_task_unit_id)
        ? current.source_task_unit_id
        : unitOptions[0],
      target_task_unit_id: current.target_task_unit_id && unitOptions.includes(current.target_task_unit_id)
        ? current.target_task_unit_id
        : unitOptions[1] ?? unitOptions[0],
    }));
  }, [unitOptions.join('|')]);

  async function commit(action: () => Promise<unknown>, success: string) {
    if (!projectId) return;
    setLoading(true);
    setMessage('');
    setError('');
    try {
      await action();
      setMessage(success);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '操作失败');
      setLoading(false);
    }
  }

  function resetPhase() {
    setEditingPhase(null);
    setPhase({ ...defaultPhase, sequence: data.phases.length + 1, phase_id: `PHASE-${String(data.phases.length + 1).padStart(2, '0')}` });
  }

  function resetUnit() {
    setEditingUnit(null);
    setUnit({ ...defaultUnit, task_unit_id: `TU-${String(data.task_units.length + 1).padStart(3, '0')}` });
  }

  function resetEquipment() {
    setEditingEquipment(null);
    setEquipment({
      ...defaultEquipment,
      equipment_group_id: `EG-${String(data.equipment_groups.length + 1).padStart(3, '0')}`,
      task_unit_id: unitOptions[0] ?? '',
    });
  }

  function resetLink() {
    setEditingLink(null);
    setLink({
      ...defaultLink,
      link_id: `LINK-${String(data.links.length + 1).padStart(3, '0')}`,
      source_task_unit_id: unitOptions[0] ?? '',
      target_task_unit_id: unitOptions[1] ?? unitOptions[0] ?? '',
    });
  }

  const tabs: Array<{ key: WorkbenchTab; label: string }> = [
    { key: 'mission', label: '任务' },
    { key: 'phases', label: `阶段 ${data.phases.length}` },
    { key: 'units', label: `单元 ${data.task_units.length}` },
    { key: 'equipment', label: `装备 ${data.equipment_groups.length}` },
    { key: 'links', label: `链路 ${data.links.length}` },
    { key: 'import', label: '整体导入' },
  ];

  return (
    <section className="panel task-workbench">
      <div className="workbench-head">
        <div className="panel-title">
          <ClipboardList size={18} />
          <h2>任务筹划工作台</h2>
        </div>
        <button className="icon-button" type="button" onClick={() => void load()} disabled={unavailable} title="刷新" aria-label="刷新">
          <RefreshCw size={16} />
        </button>
      </div>
      <div className="workbench-tabs" role="tablist" aria-label="任务数据类型">
        {tabs.map((item) => (
          <button key={item.key} type="button" className={tab === item.key ? 'active' : ''} onClick={() => setTab(item.key)}>
            {item.label}
          </button>
        ))}
      </div>
      {message && <div className="workbench-message success">{message}</div>}
      {error && <div className="workbench-message error">{error}</div>}
      {!projectId && <div className="workbench-empty">请先创建或打开项目</div>}

      {projectId && tab === 'mission' && (
        <form className="workbench-form" onSubmit={(event) => { event.preventDefault(); void commit(() => saveMissionTask(projectId, mission), '任务信息已保存'); }}>
          <div className="workbench-section-title"><ClipboardList size={16} /><strong>任务信息</strong></div>
          <div className="workbench-form-grid">
            <TextField label="任务编号" value={mission.mission_id} onChange={(value) => setMission({ ...mission, mission_id: value })} />
            <TextField label="任务名称" value={mission.name} onChange={(value) => setMission({ ...mission, name: value })} />
            <SelectField label="任务类型" value={mission.mission_type} options={['作战任务', '演训任务', '应急任务', '保障任务']} onChange={(value) => setMission({ ...mission, mission_type: value })} />
            <NumberInput label="优先级" value={mission.priority} min={1} max={10} onChange={(value) => setMission({ ...mission, priority: value ?? 1 })} />
            <NumberInput label="最低保障率" value={mission.required_assurance} min={0.1} max={1} step={0.05} onChange={(value) => setMission({ ...mission, required_assurance: value ?? 1 })} />
            <SelectField label="状态" value={mission.status} options={['筹划中', '待执行', '执行中', '已结束']} onChange={(value) => setMission({ ...mission, status: value })} />
            <DateTimeField label="开始时间" value={mission.starts_at} onChange={(value) => setMission({ ...mission, starts_at: value })} />
            <DateTimeField label="结束时间" value={mission.ends_at} onChange={(value) => setMission({ ...mission, ends_at: value })} />
            <TextField label="地域" value={mission.region_name} onChange={(value) => setMission({ ...mission, region_name: value })} />
            <NumberInput label="中心纬度" value={mission.center_lat} step={0.0001} onChange={(value) => setMission({ ...mission, center_lat: value })} />
            <NumberInput label="中心经度" value={mission.center_lon} step={0.0001} onChange={(value) => setMission({ ...mission, center_lon: value })} />
            <NumberInput label="区域半径 km" value={mission.area_radius_km} min={0} step={1} onChange={(value) => setMission({ ...mission, area_radius_km: value ?? 0 })} />
            <NumberInput label="机动范围 km" value={mission.mobility_range_km} min={0} step={1} onChange={(value) => setMission({ ...mission, mobility_range_km: value ?? 0 })} />
          </div>
          <TextArea label="任务描述" value={mission.description} onChange={(value) => setMission({ ...mission, description: value })} />
          <TextArea label="指挥意图" value={mission.commander_intent} onChange={(value) => setMission({ ...mission, commander_intent: value })} />
          <FormActions editing onReset={() => setMission(data.mission ? stripRecord(data.mission) : defaultMission)} disabled={unavailable} />
        </form>
      )}

      {projectId && tab === 'phases' && (
        <EntityEditor icon={<Timer size={16} />} title="任务阶段" onSubmit={() => commit(
          () => editingPhase ? updateTaskPhase(projectId, editingPhase, phase) : createTaskPhase(projectId, phase),
          editingPhase ? '阶段已更新' : '阶段已创建',
        )} editing={editingPhase !== null} onReset={resetPhase} disabled={unavailable} table={
          <EntityTable headers={['顺序', '阶段', '时段', '状态', '操作']} rows={data.phases.map((item) => [
            item.sequence,
            <strong>{item.name}<small>{item.phase_id}</small></strong>,
            `${formatDateTime(item.starts_at)} - ${formatDateTime(item.ends_at)}`,
            item.status,
            <RowActions onEdit={() => { setEditingPhase(item.id); setPhase(stripRecord(item)); }} onDelete={() => confirmDelete(() => commit(() => deleteTaskPhase(projectId, item.id), '阶段已删除'))} />,
          ])} />
        }>
          <div className="workbench-form-grid">
            <TextField label="阶段编号" value={phase.phase_id} onChange={(value) => setPhase({ ...phase, phase_id: value })} />
            <TextField label="阶段名称" value={phase.name} onChange={(value) => setPhase({ ...phase, name: value })} />
            <NumberInput label="顺序" value={phase.sequence} min={1} onChange={(value) => setPhase({ ...phase, sequence: value ?? 1 })} />
            <SelectField label="状态" value={phase.status} options={['待开始', '执行中', '已结束']} onChange={(value) => setPhase({ ...phase, status: value })} />
            <DateTimeField label="开始时间" value={phase.starts_at} onChange={(value) => setPhase({ ...phase, starts_at: value })} />
            <DateTimeField label="结束时间" value={phase.ends_at} onChange={(value) => setPhase({ ...phase, ends_at: value })} />
            <NumberInput label="中心纬度" value={phase.area_center_lat} step={0.0001} onChange={(value) => setPhase({ ...phase, area_center_lat: value })} />
            <NumberInput label="中心经度" value={phase.area_center_lon} step={0.0001} onChange={(value) => setPhase({ ...phase, area_center_lon: value })} />
            <NumberInput label="区域半径 km" value={phase.area_radius_km} min={0} onChange={(value) => setPhase({ ...phase, area_radius_km: value ?? 0 })} />
          </div>
          <TextArea label="阶段备注" value={phase.notes} onChange={(value) => setPhase({ ...phase, notes: value })} />
        </EntityEditor>
      )}

      {projectId && tab === 'units' && (
        <EntityEditor icon={<Boxes size={16} />} title="任务单元" onSubmit={() => commit(
          () => editingUnit ? updateTaskUnit(projectId, editingUnit, unit) : createTaskUnit(projectId, unit),
          editingUnit ? '任务单元已更新' : '任务单元已创建',
        )} editing={editingUnit !== null} onReset={resetUnit} disabled={unavailable} table={
          <EntityTable headers={['任务单元', '类型', '优先级', '地域', '操作']} rows={data.task_units.map((item) => [
            <strong>{item.name}<small>{item.task_unit_id}</small></strong>, item.unit_type, item.priority,
            `${formatCoordinate(item.area_center_lat)}, ${formatCoordinate(item.area_center_lon)} / ${item.area_radius_km}km`,
            <RowActions onEdit={() => { setEditingUnit(item.id); setUnit(stripRecord(item)); }} onDelete={() => confirmDelete(() => commit(() => deleteTaskUnit(projectId, item.id), '任务单元已删除'))} />,
          ])} />
        }>
          <div className="workbench-form-grid">
            <TextField label="单元编号" value={unit.task_unit_id} onChange={(value) => setUnit({ ...unit, task_unit_id: value })} />
            <TextField label="单元名称" value={unit.name} onChange={(value) => setUnit({ ...unit, name: value })} />
            <TextField label="单元类型" value={unit.unit_type} onChange={(value) => setUnit({ ...unit, unit_type: value })} />
            <NumberInput label="优先级" value={unit.priority} min={1} max={10} onChange={(value) => setUnit({ ...unit, priority: value ?? 1 })} />
            <SelectField label="频谱关系" value={unit.spectrum_relation} options={['独占', '可复用', '共享']} onChange={(value) => setUnit({ ...unit, spectrum_relation: value })} />
            <NumberInput label="最低保障率" value={unit.min_satisfaction_ratio} min={0.1} max={1} step={0.05} onChange={(value) => setUnit({ ...unit, min_satisfaction_ratio: value ?? 1 })} />
            <TextField label="首选频段组" value={unit.preferred_band_groups} onChange={(value) => setUnit({ ...unit, preferred_band_groups: value })} />
            <NumberInput label="中心纬度" value={unit.area_center_lat} step={0.0001} onChange={(value) => setUnit({ ...unit, area_center_lat: value })} />
            <NumberInput label="中心经度" value={unit.area_center_lon} step={0.0001} onChange={(value) => setUnit({ ...unit, area_center_lon: value })} />
            <NumberInput label="区域半径 km" value={unit.area_radius_km} min={0} onChange={(value) => setUnit({ ...unit, area_radius_km: value ?? 0 })} />
          </div>
        </EntityEditor>
      )}

      {projectId && tab === 'equipment' && (
        <EntityEditor icon={<Boxes size={16} />} title="装备组" onSubmit={() => commit(
          () => editingEquipment ? updateEquipmentGroup(projectId, editingEquipment, equipment) : createEquipmentGroup(projectId, equipment),
          editingEquipment ? '装备组已更新' : '装备组已创建',
        )} editing={editingEquipment !== null} onReset={resetEquipment} disabled={unavailable} table={
          <EntityTable headers={['装备组', '任务单元', '数量', '带宽/功率', '频段', '操作']} rows={data.equipment_groups.map((item) => [
            <strong>{item.equipment_type}<small>{item.equipment_group_id}</small></strong>, item.task_unit_id, item.count,
            `${item.bandwidth_khz}kHz / ${item.tx_power_w}W`, item.preferred_band_group || '-',
            <RowActions onEdit={() => { setEditingEquipment(item.id); setEquipment(stripRecord(item)); }} onDelete={() => confirmDelete(() => commit(() => deleteEquipmentGroup(projectId, item.id), '装备组已删除'))} />,
          ])} />
        }>
          <div className="workbench-form-grid">
            <TextField label="装备组编号" value={equipment.equipment_group_id} onChange={(value) => setEquipment({ ...equipment, equipment_group_id: value })} />
            <SelectField label="任务单元" value={equipment.task_unit_id} options={unitOptions} onChange={(value) => setEquipment({ ...equipment, task_unit_id: value })} />
            <TextField label="装备类型" value={equipment.equipment_type} onChange={(value) => setEquipment({ ...equipment, equipment_type: value })} />
            <NumberInput label="数量" value={equipment.count} min={1} onChange={(value) => setEquipment({ ...equipment, count: value ?? 1 })} />
            <SelectField label="收发角色" value={equipment.tx_rx_role} options={['发射', '接收', '双工']} onChange={(value) => setEquipment({ ...equipment, tx_rx_role: value })} />
            <SelectField label="机动属性" value={equipment.mobility} options={['固定', '机动', '空中机动', '海上机动']} onChange={(value) => setEquipment({ ...equipment, mobility: value })} />
            <NumberInput label="带宽 kHz" value={equipment.bandwidth_khz} min={0.1} step={0.1} onChange={(value) => setEquipment({ ...equipment, bandwidth_khz: value ?? 25 })} />
            <NumberInput label="功率 W" value={equipment.tx_power_w} min={0} onChange={(value) => setEquipment({ ...equipment, tx_power_w: value ?? 0 })} />
            <NumberInput label="所需信道" value={equipment.required_channels} min={1} onChange={(value) => setEquipment({ ...equipment, required_channels: value ?? 1 })} />
            <TextField label="首选频段" value={equipment.preferred_band_group} onChange={(value) => setEquipment({ ...equipment, preferred_band_group: value })} />
            <NumberInput label="优先级" value={equipment.priority} min={1} max={10} onChange={(value) => setEquipment({ ...equipment, priority: value ?? 1 })} />
            <NumberInput label="保护距离 km" value={equipment.protection_distance_km} min={0} onChange={(value) => setEquipment({ ...equipment, protection_distance_km: value ?? 0 })} />
            <NumberInput label="最小间隔 kHz" value={equipment.min_spacing_khz} min={0} onChange={(value) => setEquipment({ ...equipment, min_spacing_khz: value ?? 0 })} />
            <NumberInput label="保护带 kHz" value={equipment.guard_band_khz} min={0} onChange={(value) => setEquipment({ ...equipment, guard_band_khz: value ?? 0 })} />
            <TextField label="调制方式" value={equipment.modulation} onChange={(value) => setEquipment({ ...equipment, modulation: value })} />
            <SelectField label="双工模式" value={equipment.duplex_mode} options={['单工', '半双工', '双工']} onChange={(value) => setEquipment({ ...equipment, duplex_mode: value })} />
            <SelectField label="指配方式" value={equipment.assignment_mode} options={['离散信道', '连续频段']} onChange={(value) => setEquipment({ ...equipment, assignment_mode: value })} />
            <NumberInput label="天线增益 dBi" value={equipment.antenna_gain_dbi} onChange={(value) => setEquipment({ ...equipment, antenna_gain_dbi: value ?? 0 })} />
            <NumberInput label="天线高度 m" value={equipment.antenna_height_m} min={0} onChange={(value) => setEquipment({ ...equipment, antenna_height_m: value ?? 0 })} />
            <NumberInput label="接收灵敏度 dBm" value={equipment.receiver_sensitivity_dbm} onChange={(value) => setEquipment({ ...equipment, receiver_sensitivity_dbm: value ?? -100 })} />
          </div>
        </EntityEditor>
      )}

      {projectId && tab === 'links' && (
        <EntityEditor icon={<Cable size={16} />} title="任务链路" onSubmit={() => commit(
          () => editingLink ? updateTaskLink(projectId, editingLink, link) : createTaskLink(projectId, link),
          editingLink ? '链路已更新' : '链路已创建',
        )} editing={editingLink !== null} onReset={resetLink} disabled={unavailable} table={
          <EntityTable headers={['链路', '端点', '类型', '保障率', '主/备频段', '操作']} rows={data.links.map((item) => [
            <strong>{item.name}<small>{item.link_id}</small></strong>, `${item.source_task_unit_id} → ${item.target_task_unit_id}`,
            item.link_type, `${Math.round(item.required_availability * 100)}%`, `${item.primary_band_group || '-'} / ${item.backup_band_group || '-'}`,
            <RowActions onEdit={() => { setEditingLink(item.id); setLink(stripRecord(item)); }} onDelete={() => confirmDelete(() => commit(() => deleteTaskLink(projectId, item.id), '链路已删除'))} />,
          ])} />
        }>
          <div className="workbench-form-grid">
            <TextField label="链路编号" value={link.link_id} onChange={(value) => setLink({ ...link, link_id: value })} />
            <TextField label="链路名称" value={link.name} onChange={(value) => setLink({ ...link, name: value })} />
            <SelectField label="链路类型" value={link.link_type} options={['通信链路', '数据链路', '无人机控制链路', '无人机数传链路', '雷达协同链路', '回传链路']} onChange={(value) => setLink({ ...link, link_type: value })} />
            <SelectField label="方向" value={link.direction} options={['单向', '双向']} onChange={(value) => setLink({ ...link, direction: value })} />
            <SelectField label="源任务单元" value={link.source_task_unit_id ?? ''} options={unitOptions} onChange={(value) => setLink({ ...link, source_task_unit_id: value || null })} />
            <SelectField label="目标任务单元" value={link.target_task_unit_id ?? ''} options={unitOptions} onChange={(value) => setLink({ ...link, target_task_unit_id: value || null })} />
            <SelectField label="源装备组" value={link.source_equipment_group_id ?? ''} options={['', ...data.equipment_groups.filter((item) => item.task_unit_id === link.source_task_unit_id).map((item) => item.equipment_group_id)]} onChange={(value) => setLink({ ...link, source_equipment_group_id: value || null })} />
            <SelectField label="目标装备组" value={link.target_equipment_group_id ?? ''} options={['', ...data.equipment_groups.filter((item) => item.task_unit_id === link.target_task_unit_id).map((item) => item.equipment_group_id)]} onChange={(value) => setLink({ ...link, target_equipment_group_id: value || null })} />
            <NumberInput label="优先级" value={link.priority} min={1} max={10} onChange={(value) => setLink({ ...link, priority: value ?? 1 })} />
            <NumberInput label="最低可用率" value={link.required_availability} min={0.1} max={1} step={0.05} onChange={(value) => setLink({ ...link, required_availability: value ?? 1 })} />
            <NumberInput label="带宽 kHz" value={link.bandwidth_khz} min={0.1} step={0.1} onChange={(value) => setLink({ ...link, bandwidth_khz: value ?? 25 })} />
            <NumberInput label="所需信道" value={link.required_channels} min={1} onChange={(value) => setLink({ ...link, required_channels: value ?? 1 })} />
            <TextField label="主用频段" value={link.primary_band_group} onChange={(value) => setLink({ ...link, primary_band_group: value })} />
            <TextField label="备用频段" value={link.backup_band_group} onChange={(value) => setLink({ ...link, backup_band_group: value })} />
            <TextField label="生效阶段" value={link.active_phase_ids.join(',')} onChange={(value) => setLink({ ...link, active_phase_ids: value.split(',').map((item) => item.trim()).filter(Boolean) })} />
          </div>
          <TextArea label="链路备注" value={link.notes} onChange={(value) => setLink({ ...link, notes: value })} />
        </EntityEditor>
      )}

      {projectId && tab === 'import' && (
        <form className="workbench-form" onSubmit={(event) => {
          event.preventDefault();
          if (!taskUnitsFile || !equipmentFile || !rulesFile) { setError('请选择三份 Excel 文件'); return; }
          void commit(() => importTaskPackage(projectId, taskUnitsFile, equipmentFile, rulesFile), '任务数据已整体导入');
        }}>
          <div className="workbench-section-title"><Upload size={16} /><strong>任务数据整体导入</strong></div>
          <div className="workbench-import-grid">
            <FileField label="任务单元" onChange={setTaskUnitsFile} />
            <FileField label="装备组" onChange={setEquipmentFile} />
            <FileField label="频谱规则" onChange={setRulesFile} />
          </div>
          <button type="submit" disabled={unavailable || !taskUnitsFile || !equipmentFile || !rulesFile}><Upload size={16} />整体导入</button>
        </form>
      )}
    </section>
  );
}

function EntityEditor({ icon, title, children, table, onSubmit, editing, onReset, disabled }: {
  icon: React.ReactNode; title: string; children: React.ReactNode; table: React.ReactNode;
  onSubmit: () => void; editing: boolean; onReset: () => void; disabled: boolean;
}) {
  return <div className="workbench-entity-layout">
    <form className="workbench-form" onSubmit={(event) => { event.preventDefault(); onSubmit(); }}>
      <div className="workbench-section-title">{icon}<strong>{title}</strong></div>
      {children}
      <FormActions editing={editing} onReset={onReset} disabled={disabled} />
    </form>
    {table}
  </div>;
}

function FormActions({ editing, onReset, disabled }: { editing: boolean; onReset: () => void; disabled: boolean }) {
  return <div className="workbench-actions">
    <button type="submit" disabled={disabled}>{editing ? <Save size={16} /> : <Plus size={16} />}{editing ? '保存' : '新增'}</button>
    <button type="button" className="secondary" onClick={onReset} disabled={disabled}><RefreshCw size={16} />重置</button>
  </div>;
}

function EntityTable({ headers, rows }: { headers: string[]; rows: React.ReactNode[][] }) {
  if (!rows.length) return <div className="workbench-empty">暂无记录</div>;
  return <div className="workbench-table-wrap"><table className="workbench-table"><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead>
    <tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, index) => <td key={index}>{cell}</td>)}</tr>)}</tbody></table></div>;
}

function RowActions({ onEdit, onDelete }: { onEdit: () => void; onDelete: () => void }) {
  return <div className="row-actions">
    <button type="button" className="icon-button" onClick={onEdit} title="编辑" aria-label="编辑"><Pencil size={15} /></button>
    <button type="button" className="icon-button danger" onClick={onDelete} title="删除" aria-label="删除"><Trash2 size={15} /></button>
  </div>;
}

function TextField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label><span>{label}</span><input value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function TextArea({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="workbench-textarea"><span>{label}</span><textarea value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return <label><span>{label}</span><select value={value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => <option key={option || '__empty'} value={option}>{option || '不指定'}</option>)}</select></label>;
}

function NumberInput({ label, value, min, max, step = 1, onChange }: {
  label: string; value: number | null; min?: number; max?: number; step?: number; onChange: (value: number | null) => void;
}) {
  return <label><span>{label}</span><input type="number" value={value ?? ''} min={min} max={max} step={step} onChange={(event) => onChange(event.target.value === '' ? null : Number(event.target.value))} /></label>;
}

function DateTimeField({ label, value, onChange }: { label: string; value: string | null; onChange: (value: string | null) => void }) {
  return <label><span>{label}</span><input type="datetime-local" value={value ? value.slice(0, 16) : ''} onChange={(event) => onChange(event.target.value || null)} /></label>;
}

function FileField({ label, onChange }: { label: string; onChange: (file: File | null) => void }) {
  return <label className="workbench-file"><span>{label}</span><input type="file" accept=".xlsx" onChange={(event) => onChange(event.target.files?.[0] ?? null)} /></label>;
}

function stripRecord<T extends Record<string, unknown>>(record: T): Omit<T, 'id' | 'project_id' | 'raw_json'> {
  const { id: _id, project_id: _projectId, raw_json: _rawJson, ...payload } = record;
  return payload;
}

function formatDateTime(value: string | null) {
  return value ? value.replace('T', ' ').slice(0, 16) : '-';
}

function formatCoordinate(value: number | null) {
  return value === null ? '-' : value.toFixed(4);
}

function confirmDelete(action: () => void) {
  if (window.confirm('确认删除这条记录？')) action();
}

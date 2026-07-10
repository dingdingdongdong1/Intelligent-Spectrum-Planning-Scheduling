import { useEffect, useMemo, useState } from 'react';
import { Grid3X3, Pencil, Plus, RadioTower, RefreshCw, Save, Trash2 } from 'lucide-react';
import {
  SpectrumResourceHeatmap,
  SpectrumResourcePayload,
  SpectrumResourceRecord,
  createSpectrumResource,
  deleteSpectrumResource,
  getSpectrumResourceHeatmap,
  listSpectrumResources,
  updateSpectrumResource,
} from './api';

const defaultResource: SpectrumResourcePayload = {
  resource_id: 'RES-001',
  name: '任务可用频段池',
  resource_type: '可用频段',
  purpose: '任务通信',
  region: '全域',
  start_mhz: 400,
  end_mhz: 420,
  channel_step_khz: 25,
  max_bandwidth_khz: 100,
  max_power_w: 50,
  guard_band_khz: 25,
  center_lat: null,
  center_lon: null,
  coverage_radius_km: 0,
  starts_at: null,
  ends_at: null,
  compatible_equipment_types: '',
  status: '启用',
  source: 'USER_UI',
  notes: '',
};

export default function SpectrumResourcePanel({ projectId, busy }: { projectId: number | null; busy: boolean }) {
  const [resources, setResources] = useState<SpectrumResourceRecord[]>([]);
  const [heatmap, setHeatmap] = useState<SpectrumResourceHeatmap | null>(null);
  const [form, setForm] = useState<SpectrumResourcePayload>(defaultResource);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [at, setAt] = useState('');
  const [region, setRegion] = useState('');
  const disabled = busy || loading || !projectId;
  const regions = useMemo(() => Array.from(new Set(resources.map((item) => item.region))).sort(), [resources]);

  async function load() {
    if (!projectId) {
      setResources([]);
      setHeatmap(null);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const [resourceRows, map] = await Promise.all([
        listSpectrumResources(projectId),
        getSpectrumResourceHeatmap(projectId, at || undefined, region || undefined),
      ]);
      setResources(resourceRows);
      setHeatmap(map);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '频谱资源读取失败');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [projectId]);

  async function save() {
    if (!projectId) return;
    setLoading(true);
    setError('');
    setMessage('');
    try {
      if (editingId) await updateSpectrumResource(projectId, editingId, form);
      else await createSpectrumResource(projectId, form);
      setMessage(editingId ? '频谱资源已更新' : '频谱资源已创建');
      setEditingId(null);
      setForm({ ...defaultResource, resource_id: `RES-${String(resources.length + 2).padStart(3, '0')}` });
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '保存失败');
      setLoading(false);
    }
  }

  async function remove(rowId: number) {
    if (!projectId || !window.confirm('确认删除这条频谱资源？')) return;
    setLoading(true);
    setError('');
    try {
      await deleteSpectrumResource(projectId, rowId);
      setMessage('频谱资源已删除');
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '删除失败');
      setLoading(false);
    }
  }

  function edit(row: SpectrumResourceRecord) {
    const { id: _id, project_id: _projectId, ...payload } = row;
    setEditingId(row.id);
    setForm(payload);
  }

  return (
    <section className="panel spectrum-resource-panel">
      <div className="resource-panel-head">
        <div className="panel-title"><RadioTower size={18} /><h2>频谱资源管理</h2></div>
        <button type="button" className="icon-button" onClick={() => void load()} disabled={disabled} title="刷新" aria-label="刷新频谱资源"><RefreshCw size={16} /></button>
      </div>
      {message && <div className="resource-message success">{message}</div>}
      {error && <div className="resource-message error">{error}</div>}
      {!projectId ? <div className="empty small">请先创建或打开项目</div> : <>
        <div className="resource-layout">
          <form className="resource-form" onSubmit={(event) => { event.preventDefault(); void save(); }}>
            <div className="resource-form-grid">
              <TextField label="资源编号" value={form.resource_id} onChange={(value) => setForm({ ...form, resource_id: value })} />
              <TextField label="资源名称" value={form.name} onChange={(value) => setForm({ ...form, name: value })} />
              <SelectField label="资源类型" value={form.resource_type} options={['可用频段', '固定占用', '临时占用', '保护频段', '禁用频段']} onChange={(value) => setForm({ ...form, resource_type: value })} />
              <SelectField label="状态" value={form.status} options={['启用', '停用']} onChange={(value) => setForm({ ...form, status: value })} />
              <TextField label="用途" value={form.purpose} onChange={(value) => setForm({ ...form, purpose: value })} />
              <TextField label="区域" value={form.region} onChange={(value) => setForm({ ...form, region: value })} />
              <NumberField label="起点 MHz" value={form.start_mhz} min={0} onChange={(value) => setForm({ ...form, start_mhz: value ?? 0 })} />
              <NumberField label="终点 MHz" value={form.end_mhz} min={0} onChange={(value) => setForm({ ...form, end_mhz: value ?? 0 })} />
              <NumberField label="步进 kHz" value={form.channel_step_khz} min={0.1} step={0.1} onChange={(value) => setForm({ ...form, channel_step_khz: value ?? 25 })} />
              <NumberField label="最大带宽 kHz" value={form.max_bandwidth_khz} min={0.1} step={0.1} onChange={(value) => setForm({ ...form, max_bandwidth_khz: value ?? 25 })} />
              <NumberField label="最大功率 W" value={form.max_power_w} min={0} step={0.1} onChange={(value) => setForm({ ...form, max_power_w: value ?? 0 })} />
              <NumberField label="保护带 kHz" value={form.guard_band_khz} min={0} step={0.1} onChange={(value) => setForm({ ...form, guard_band_khz: value ?? 0 })} />
              <DateTimeField label="生效时间" value={form.starts_at} onChange={(value) => setForm({ ...form, starts_at: value })} />
              <DateTimeField label="失效时间" value={form.ends_at} onChange={(value) => setForm({ ...form, ends_at: value })} />
              <NumberField label="中心纬度" value={form.center_lat} step={0.0001} nullable onChange={(value) => setForm({ ...form, center_lat: value })} />
              <NumberField label="中心经度" value={form.center_lon} step={0.0001} nullable onChange={(value) => setForm({ ...form, center_lon: value })} />
              <NumberField label="覆盖半径 km" value={form.coverage_radius_km} min={0} step={0.1} onChange={(value) => setForm({ ...form, coverage_radius_km: value ?? 0 })} />
              <TextField label="兼容装备" value={form.compatible_equipment_types} onChange={(value) => setForm({ ...form, compatible_equipment_types: value })} />
            </div>
            <label><span>备注</span><textarea value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></label>
            <div className="resource-actions">
              <button type="submit" disabled={disabled || !form.resource_id || !form.name || form.end_mhz <= form.start_mhz}>{editingId ? <Save size={16} /> : <Plus size={16} />}{editingId ? '保存' : '新增'}</button>
              <button type="button" className="secondary" onClick={() => { setEditingId(null); setForm(defaultResource); }} disabled={disabled}><RefreshCw size={16} />重置</button>
            </div>
          </form>
          <div className="resource-table-wrap">
            <table className="resource-table"><thead><tr><th>资源</th><th>类型</th><th>区域/用途</th><th>范围 MHz</th><th>有效时段</th><th>操作</th></tr></thead>
              <tbody>{resources.map((row) => <tr key={row.id}>
                <td><strong>{row.name}</strong><small>{row.resource_id}</small></td>
                <td><span className={`resource-type ${resourceTone(row.resource_type)}`}>{row.resource_type}</span></td>
                <td>{row.region}<small>{row.purpose || '-'}</small></td>
                <td>{row.start_mhz} - {row.end_mhz}</td>
                <td>{formatTime(row.starts_at)}<br />{formatTime(row.ends_at)}</td>
                <td><div className="resource-row-actions">
                  <button type="button" className="icon-button" onClick={() => edit(row)} title="编辑" aria-label="编辑资源"><Pencil size={15} /></button>
                  <button type="button" className="icon-button danger" onClick={() => void remove(row.id)} title="删除" aria-label="删除资源"><Trash2 size={15} /></button>
                </div></td>
              </tr>)}</tbody>
            </table>
          </div>
        </div>
        <div className="heatmap-head">
          <div className="panel-title"><Grid3X3 size={17} /><h3>频谱可用性热力图</h3></div>
          <div className="heatmap-filters">
            <input aria-label="热力图时间" type="datetime-local" value={at} onChange={(event) => setAt(event.target.value)} />
            <select aria-label="热力图区域" value={region} onChange={(event) => setRegion(event.target.value)}><option value="">全部区域</option>{regions.map((item) => <option key={item}>{item}</option>)}</select>
            <button type="button" onClick={() => void load()} disabled={disabled}><RefreshCw size={15} />扫描</button>
          </div>
        </div>
        {heatmap && <>
          <div className="heatmap-summary">
            <span>活动资源 <strong>{heatmap.summary.active_resource_count}</strong></span>
            <span>覆盖带宽 <strong>{heatmap.summary.covered_bandwidth_mhz} MHz</strong></span>
            <span>平均可用率 <strong>{heatmap.summary.average_availability_pct}%</strong></span>
          </div>
          <div className="heatmap-strip">{heatmap.cells.map((cell, index) => <div key={`${cell.start_mhz}-${index}`} className={`heat-cell ${heatTone(cell.availability_pct)}`} style={{ flexGrow: Math.max(1, cell.width_mhz) }} title={`${cell.start_mhz}-${cell.end_mhz} MHz · ${cell.resource_type} · ${cell.availability_pct}%`}><span>{cell.start_mhz}-{cell.end_mhz}</span><strong>{cell.availability_pct}%</strong></div>)}</div>
          <div className="heatmap-table-wrap"><table className="heatmap-table"><thead><tr><th>频率范围 MHz</th><th>状态</th><th>可用率</th><th>区域</th><th>资源依据</th></tr></thead><tbody>{heatmap.cells.map((cell, index) => <tr key={`${cell.start_mhz}-${cell.end_mhz}-${index}`}><td>{cell.start_mhz} - {cell.end_mhz}</td><td>{cell.resource_type}</td><td><strong>{cell.availability_pct}%</strong></td><td>{cell.region}</td><td>{cell.active_resource_ids.join(', ')}</td></tr>)}</tbody></table></div>
        </>}
      </>}
    </section>
  );
}

function TextField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label><span>{label}</span><input value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return <label><span>{label}</span><select value={value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => <option key={option}>{option}</option>)}</select></label>;
}

function NumberField({ label, value, min, step = 1, nullable = false, onChange }: { label: string; value: number | null; min?: number; step?: number; nullable?: boolean; onChange: (value: number | null) => void }) {
  return <label><span>{label}</span><input type="number" value={value ?? ''} min={min} step={step} onChange={(event) => onChange(event.target.value === '' && nullable ? null : Number(event.target.value))} /></label>;
}

function DateTimeField({ label, value, onChange }: { label: string; value: string | null; onChange: (value: string | null) => void }) {
  return <label><span>{label}</span><input type="datetime-local" value={value?.slice(0, 16) ?? ''} onChange={(event) => onChange(event.target.value || null)} /></label>;
}

function formatTime(value: string | null) { return value ? value.replace('T', ' ').slice(0, 16) : '持续有效'; }
function resourceTone(type: string) { return type === '禁用频段' ? 'blocked' : type === '保护频段' || type.includes('占用') ? 'limited' : 'available'; }
function heatTone(value: number) { return value <= 10 ? 'blocked' : value < 70 ? 'limited' : 'available'; }

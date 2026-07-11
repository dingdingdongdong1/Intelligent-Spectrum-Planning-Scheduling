import { ReactNode, useState } from 'react';
import { MapPin, Plus, RadioTower, Trash2 } from 'lucide-react';

import type { TaskReplanPayload } from './api';

export type DynamicEvents = {
  equipment_events: NonNullable<TaskReplanPayload['equipment_events']>;
  unit_position_updates: NonNullable<TaskReplanPayload['unit_position_updates']>;
  interference_sources: NonNullable<TaskReplanPayload['interference_sources']>;
};

export function DynamicEventPanel({ value, onChange, busy }: { value: DynamicEvents; onChange: (value: DynamicEvents) => void; busy: boolean }) {
  const [equipment, setEquipment] = useState({ action: '损毁' as '损毁' | '新增', equipment_group_id: '', template_group_id: '', task_unit_id: '', equipment_type: '', count: 1, reason: '' });
  const [position, setPosition] = useState({ task_unit_id: '', area_center_lat: '', area_center_lon: '', area_radius_km: '', reason: '' });
  const [jammer, setJammer] = useState({ source_id: '', start_mhz: '', end_mhz: '', max_power_w: '', center_lat: '', center_lon: '', coverage_radius_km: '', region: '全域', reason: '' });

  return (
    <section className="panel dynamic-event-panel">
      <div className="panel-title"><RadioTower size={18} /><h2>战场变化事件</h2></div>
      <div className="dynamic-event-grid">
        <EventForm title="装备损毁 / 新增">
          <select aria-label="装备事件类型" value={equipment.action} onChange={(event) => setEquipment({ ...equipment, action: event.target.value as '损毁' | '新增' })}><option>损毁</option><option>新增</option></select>
          <input aria-label="装备组编号" placeholder="装备组编号" value={equipment.equipment_group_id} onChange={(event) => setEquipment({ ...equipment, equipment_group_id: event.target.value })} />
          {equipment.action === '新增' && <><input aria-label="模板装备组" placeholder="模板装备组（可选）" value={equipment.template_group_id} onChange={(event) => setEquipment({ ...equipment, template_group_id: event.target.value })} /><input aria-label="归属任务单元" placeholder="归属任务单元" value={equipment.task_unit_id} onChange={(event) => setEquipment({ ...equipment, task_unit_id: event.target.value })} /><input aria-label="装备类型" placeholder="装备类型" value={equipment.equipment_type} onChange={(event) => setEquipment({ ...equipment, equipment_type: event.target.value })} /></>}
          <input aria-label="装备数量" type="number" min={1} value={equipment.count} onChange={(event) => setEquipment({ ...equipment, count: Number(event.target.value) || 1 })} />
          <input aria-label="装备事件原因" placeholder="原因" value={equipment.reason} onChange={(event) => setEquipment({ ...equipment, reason: event.target.value })} />
          <button type="button" disabled={busy || !equipment.equipment_group_id.trim()} onClick={() => { onChange({ ...value, equipment_events: [...value.equipment_events, { ...equipment, equipment_group_id: equipment.equipment_group_id.trim() }] }); setEquipment({ ...equipment, equipment_group_id: '', reason: '' }); }}><Plus size={15} />加入事件</button>
        </EventForm>
        <EventForm title="任务单元机动">
          <input aria-label="机动任务单元" placeholder="任务单元编号" value={position.task_unit_id} onChange={(event) => setPosition({ ...position, task_unit_id: event.target.value })} />
          <div className="event-inline"><input aria-label="新纬度" type="number" placeholder="纬度" value={position.area_center_lat} onChange={(event) => setPosition({ ...position, area_center_lat: event.target.value })} /><input aria-label="新经度" type="number" placeholder="经度" value={position.area_center_lon} onChange={(event) => setPosition({ ...position, area_center_lon: event.target.value })} /></div>
          <input aria-label="机动半径" type="number" min={0} placeholder="区域半径 km" value={position.area_radius_km} onChange={(event) => setPosition({ ...position, area_radius_km: event.target.value })} />
          <input aria-label="机动原因" placeholder="原因" value={position.reason} onChange={(event) => setPosition({ ...position, reason: event.target.value })} />
          <button type="button" disabled={busy || !position.task_unit_id || position.area_center_lat === '' || position.area_center_lon === ''} onClick={() => { onChange({ ...value, unit_position_updates: [...value.unit_position_updates, { task_unit_id: position.task_unit_id.trim(), area_center_lat: Number(position.area_center_lat), area_center_lon: Number(position.area_center_lon), area_radius_km: Number(position.area_radius_km) || 0, reason: position.reason }] }); setPosition({ ...position, task_unit_id: '', reason: '' }); }}><MapPin size={15} />加入事件</button>
        </EventForm>
        <EventForm title="新增干扰源">
          <input aria-label="干扰源编号" placeholder="干扰源编号" value={jammer.source_id} onChange={(event) => setJammer({ ...jammer, source_id: event.target.value })} />
          <div className="event-inline"><input aria-label="干扰起点" type="number" placeholder="起点 MHz" value={jammer.start_mhz} onChange={(event) => setJammer({ ...jammer, start_mhz: event.target.value })} /><input aria-label="干扰终点" type="number" placeholder="终点 MHz" value={jammer.end_mhz} onChange={(event) => setJammer({ ...jammer, end_mhz: event.target.value })} /></div>
          <div className="event-inline"><input aria-label="干扰功率" type="number" min={0} placeholder="功率 W" value={jammer.max_power_w} onChange={(event) => setJammer({ ...jammer, max_power_w: event.target.value })} /><input aria-label="干扰覆盖半径" type="number" min={0} placeholder="半径 km" value={jammer.coverage_radius_km} onChange={(event) => setJammer({ ...jammer, coverage_radius_km: event.target.value })} /></div>
          <div className="event-inline"><input aria-label="干扰源纬度" type="number" placeholder="纬度（可选）" value={jammer.center_lat} onChange={(event) => setJammer({ ...jammer, center_lat: event.target.value })} /><input aria-label="干扰源经度" type="number" placeholder="经度（可选）" value={jammer.center_lon} onChange={(event) => setJammer({ ...jammer, center_lon: event.target.value })} /></div>
          <input aria-label="干扰源原因" placeholder="发现依据 / 原因" value={jammer.reason} onChange={(event) => setJammer({ ...jammer, reason: event.target.value })} />
          <button type="button" disabled={busy || !jammer.source_id || !Number(jammer.start_mhz) || Number(jammer.end_mhz) <= Number(jammer.start_mhz)} onClick={() => { onChange({ ...value, interference_sources: [...value.interference_sources, { source_id: jammer.source_id.trim(), start_mhz: Number(jammer.start_mhz), end_mhz: Number(jammer.end_mhz), max_power_w: Number(jammer.max_power_w) || 0, center_lat: jammer.center_lat === '' ? null : Number(jammer.center_lat), center_lon: jammer.center_lon === '' ? null : Number(jammer.center_lon), coverage_radius_km: Number(jammer.coverage_radius_km) || 0, region: jammer.region, reason: jammer.reason }] }); setJammer({ ...jammer, source_id: '', reason: '' }); }}><RadioTower size={15} />加入事件</button>
        </EventForm>
      </div>
      <div className="dynamic-event-queue">
        {[...value.equipment_events.map((item, index) => ({ key: `e-${index}`, label: `装备${item.action}：${item.equipment_group_id} × ${item.count}`, remove: () => onChange({ ...value, equipment_events: value.equipment_events.filter((_, row) => row !== index) }) })), ...value.unit_position_updates.map((item, index) => ({ key: `p-${index}`, label: `机动：${item.task_unit_id} → ${item.area_center_lat}, ${item.area_center_lon}`, remove: () => onChange({ ...value, unit_position_updates: value.unit_position_updates.filter((_, row) => row !== index) }) })), ...value.interference_sources.map((item, index) => ({ key: `j-${index}`, label: `干扰源：${item.source_id} / ${item.start_mhz}-${item.end_mhz} MHz`, remove: () => onChange({ ...value, interference_sources: value.interference_sources.filter((_, row) => row !== index) }) }))].map((item) => <span key={item.key}>{item.label}<button type="button" title="移除事件" onClick={item.remove}><Trash2 size={13} /></button></span>)}
      </div>
    </section>
  );
}

function EventForm({ title, children }: { title: string; children: ReactNode }) { return <div className="dynamic-event-form"><h3>{title}</h3>{children}</div>; }

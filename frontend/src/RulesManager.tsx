import { useEffect, useMemo, useState } from 'react';
import { Plus, RefreshCw, Save, Settings2, Trash2 } from 'lucide-react';
import { RulePayload, RuleRecord, createRule, deleteRule, listRules, updateRule } from './api';

type Props = {
  projectId: number | null;
  refreshKey: number;
  onChanged: () => void;
};

const emptyRule: RulePayload = {
  band_group: 'UHF-A',
  service_type: '专网语音',
  region: 'default',
  start_mhz: 410,
  end_mhz: 412,
  channel_step_khz: 25,
  max_bandwidth_khz: 25,
  max_power_w: 50,
  guard_band_khz: 25,
  min_spacing_khz: 50,
  forbidden_frequency_mhz: null,
  protection_distance_km: 5,
};

export default function RulesManager({ projectId, refreshKey, onChanged }: Props) {
  const [rules, setRules] = useState<RuleRecord[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<RulePayload>(emptyRule);
  const [message, setMessage] = useState('');

  const editingRule = useMemo(() => rules.find((rule) => rule.id === editingId), [editingId, rules]);

  useEffect(() => {
    if (!projectId) {
      setRules([]);
      return;
    }
    void refresh();
  }, [projectId, refreshKey]);

  useEffect(() => {
    if (editingRule) {
      setDraft(toPayload(editingRule));
    }
  }, [editingRule]);

  async function refresh() {
    if (!projectId) return;
    setRules(await listRules(projectId));
  }

  async function save() {
    if (!projectId) return;
    if (editingId) {
      await updateRule(projectId, editingId, draft);
      setMessage('规则已更新');
    } else {
      await createRule(projectId, draft);
      setMessage('规则已新增');
    }
    setEditingId(null);
    setDraft(emptyRule);
    await refresh();
    onChanged();
  }

  async function remove(ruleId: number) {
    if (!projectId) return;
    await deleteRule(projectId, ruleId);
    setMessage('规则已删除');
    await refresh();
    onChanged();
  }

  return (
    <section className="panel rules-panel">
      <div className="panel-title">
        <Settings2 size={18} />
        <h2>规则管理</h2>
      </div>
      {message && <div className="inline-message">{message}</div>}
      <div className="rules-layout">
        <div className="rules-table-wrap">
          <div className="rules-toolbar">
            <button onClick={refresh} disabled={!projectId}>
              <RefreshCw size={15} />
              刷新
            </button>
            <button
              onClick={() => {
                setEditingId(null);
                setDraft(emptyRule);
              }}
              disabled={!projectId}
            >
              <Plus size={15} />
              新增
            </button>
          </div>
          <table className="rules-table">
            <thead>
              <tr>
                <th>频段组</th>
                <th>业务</th>
                <th>范围 MHz</th>
                <th>步进 kHz</th>
                <th>功率 W</th>
                <th>保护 km</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.id}>
                  <td>{rule.band_group}</td>
                  <td>{rule.service_type}</td>
                  <td>
                    {rule.start_mhz}-{rule.end_mhz}
                  </td>
                  <td>{rule.channel_step_khz}</td>
                  <td>{rule.max_power_w}</td>
                  <td>{rule.protection_distance_km}</td>
                  <td>
                    <button className="small-button" onClick={() => setEditingId(rule.id)}>
                      编辑
                    </button>
                    <button className="icon-danger" onClick={() => remove(rule.id)}>
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
          <RuleInput label="频段组" value={draft.band_group} onChange={(value) => setDraft({ ...draft, band_group: value })} />
          <RuleInput label="业务类型" value={draft.service_type} onChange={(value) => setDraft({ ...draft, service_type: value })} />
          <RuleInput label="地区" value={draft.region} onChange={(value) => setDraft({ ...draft, region: value })} />
          <RuleNumber label="起始 MHz" value={draft.start_mhz} onChange={(value) => setDraft({ ...draft, start_mhz: value })} />
          <RuleNumber label="终止 MHz" value={draft.end_mhz} onChange={(value) => setDraft({ ...draft, end_mhz: value })} />
          <RuleNumber label="步进 kHz" value={draft.channel_step_khz} onChange={(value) => setDraft({ ...draft, channel_step_khz: value })} />
          <RuleNumber label="最大带宽 kHz" value={draft.max_bandwidth_khz} onChange={(value) => setDraft({ ...draft, max_bandwidth_khz: value })} />
          <RuleNumber label="最大功率 W" value={draft.max_power_w} onChange={(value) => setDraft({ ...draft, max_power_w: value })} />
          <RuleNumber label="保护距离 km" value={draft.protection_distance_km} onChange={(value) => setDraft({ ...draft, protection_distance_km: value })} />
          <RuleNumber label="最小间隔 kHz" value={draft.min_spacing_khz} onChange={(value) => setDraft({ ...draft, min_spacing_khz: value })} />
          <RuleNumber label="保护带 kHz" value={draft.guard_band_khz} onChange={(value) => setDraft({ ...draft, guard_band_khz: value })} />
          <RuleNumber
            label="禁用频点 MHz"
            value={draft.forbidden_frequency_mhz ?? ''}
            onChange={(value) => setDraft({ ...draft, forbidden_frequency_mhz: Number.isFinite(value) ? value : null })}
          />
          <button className="wide" onClick={save} disabled={!projectId}>
            <Save size={15} />
            保存规则
          </button>
        </div>
      </div>
    </section>
  );
}

function RuleInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label>
      <span>{label}</span>
      <input aria-label={label} name={label} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function RuleNumber({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number | '';
  onChange: (value: number) => void;
}) {
  return (
    <label>
      <span>{label}</span>
      <input
        aria-label={label}
        name={label}
        type="number"
        value={value}
        onChange={(event) => onChange(event.target.value === '' ? Number.NaN : Number(event.target.value))}
      />
    </label>
  );
}

function toPayload(rule: RuleRecord): RulePayload {
  return {
    band_group: rule.band_group,
    service_type: rule.service_type,
    region: rule.region,
    start_mhz: rule.start_mhz,
    end_mhz: rule.end_mhz,
    channel_step_khz: rule.channel_step_khz,
    max_bandwidth_khz: rule.max_bandwidth_khz,
    max_power_w: rule.max_power_w,
    guard_band_khz: rule.guard_band_khz,
    min_spacing_khz: rule.min_spacing_khz,
    forbidden_frequency_mhz: rule.forbidden_frequency_mhz,
    protection_distance_km: rule.protection_distance_km,
  };
}

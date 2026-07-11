import { CheckCircle2, RadioTower, ShieldAlert } from 'lucide-react';

import type { TaskVisualizationData } from './api';

export function PlanningResultPanel({ data }: { data: TaskVisualizationData | null }) {
  const assignments = data?.assignments ?? [];
  const summary = data?.summary ?? {};
  return (
    <section className="planning-result-panel">
      <header>
        <div>
          <span>确定性优化结果</span>
          <h2>装备组主备频率方案</h2>
          <p>{String(summary.leader_summary || '执行规划后生成主用资源、备份资源和保障状态。')}</p>
        </div>
        <RadioTower size={23} />
      </header>
      {assignments.length ? (
        <>
          <div className="planning-result-metrics">
            <Metric label="装备组" value={assignments.length} />
            <Metric label="完全满足" value={assignments.filter((item) => item.status === '完全满足').length} />
            <Metric label="部分满足" value={assignments.filter((item) => item.status === '部分满足').length} />
            <Metric label="未满足" value={assignments.filter((item) => item.status === '未满足').length} />
            <Metric label="资源约束" value={Number(summary.spectrum_resource_rule_count || 0)} />
          </div>
          <div className="planning-result-table-wrap">
            <table className="planning-result-table">
              <thead><tr><th>任务 / 装备组</th><th>主用资源</th><th>首选备份</th><th>信道满足</th><th>保障状态</th><th>风险</th><th>决策依据</th></tr></thead>
              <tbody>
                {assignments.map((item) => {
                  const backup = item.alternative_resources?.find((candidate) => candidate.status === '可用') ?? item.alternative_resources?.[0];
                  return (
                    <tr key={`${item.task_unit_id}-${item.equipment_group_id}`}>
                      <td><strong>{item.equipment_group_id}</strong><span>{item.task_unit_id} · {item.equipment_type}</span></td>
                      <td><strong>{item.band_group || '未分配'}</strong><span>{item.assigned_resource || '无主用资源'}</span></td>
                      <td><strong>{backup?.band_group || '无可用备份'}</strong><span>{backup?.resource || backup?.reason || '-'}</span></td>
                      <td>{item.assigned_channels} / {item.requested_channels}</td>
                      <td><Status value={item.status} /></td>
                      <td><span className={riskTone(item.risk_level)}>{item.risk_level} · {Number(item.risk_score || 0).toFixed(1)}</span></td>
                      <td><span>{item.decision_notes || item.reason}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="empty visual-empty"><ShieldAlert size={20} />先执行数据校验和智能规划，再查看各装备组主备资源。</div>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}

function Status({ value }: { value: string }) {
  return <span className={`planning-status ${value === '完全满足' ? 'full' : value === '部分满足' ? 'partial' : 'unmet'}`}><CheckCircle2 size={14} />{value}</span>;
}

function riskTone(level: string): string {
  if (level === '高') return 'risk-high';
  if (level === '中') return 'risk-medium';
  return 'risk-low';
}

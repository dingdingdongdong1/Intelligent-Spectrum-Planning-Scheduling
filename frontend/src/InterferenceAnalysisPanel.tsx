import { useMemo, useState } from 'react';
import { Filter, Network, ShieldAlert } from 'lucide-react';

import type { BandUsageView, TaskRiskItemView } from './api';

type Props = {
  risks: TaskRiskItemView[];
  bands: BandUsageView[];
};

const levels = ['全部', '高', '中', '低'] as const;

export function InterferenceAnalysisPanel({ risks, bands }: Props) {
  const [level, setLevel] = useState<(typeof levels)[number]>('全部');
  const [riskType, setRiskType] = useState('全部');
  const [page, setPage] = useState(1);
  const riskTypes = useMemo(() => Array.from(new Set(risks.map((item) => item.risk_type))).sort(), [risks]);
  const visible = useMemo(
    () => risks.filter((item) => (level === '全部' || item.severity === level) && (riskType === '全部' || item.risk_type === riskType)),
    [level, riskType, risks],
  );
  const affectedUnits = new Set(risks.flatMap((item) => [item.task_unit_a, item.task_unit_b]).filter(Boolean)).size;
  const pageSize = 12;
  const pageCount = Math.max(1, Math.ceil(visible.length / pageSize));
  const currentPage = Math.min(page, pageCount);
  const pageRows = visible.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <section className="interference-workbench" aria-label="干扰与冲突评估">
      <header className="interference-header">
        <div>
          <span>确定性风险模型</span>
          <h2>干扰与冲突评估</h2>
          <p>综合频谱重叠、信道间隔、功率、距离、保护要求和任务优先级生成风险解释链。</p>
        </div>
        <ShieldAlert size={24} />
      </header>

      <div className="interference-metrics">
        <RiskMetric label="风险总数" value={risks.length} />
        <RiskMetric label="高风险" value={risks.filter((item) => item.severity === '高').length} tone="high" />
        <RiskMetric label="中风险" value={risks.filter((item) => item.severity === '中').length} tone="medium" />
        <RiskMetric label="影响单元" value={affectedUnits} />
        <RiskMetric label="风险类型" value={riskTypes.length} />
      </div>

      <div className="interference-toolbar">
        <Filter size={16} />
        <div className="segmented-control" aria-label="风险等级筛选">
          {levels.map((item) => (
            <button type="button" className={level === item ? 'active' : ''} key={item} onClick={() => { setLevel(item); setPage(1); }}>
              {item}
            </button>
          ))}
        </div>
        <select aria-label="风险类型筛选" value={riskType} onChange={(event) => { setRiskType(event.target.value); setPage(1); }}>
          <option value="全部">全部风险类型</option>
          {riskTypes.map((item) => <option key={item}>{item}</option>)}
        </select>
        <span>{visible.length} 条结果</span>
      </div>

      <div className="interference-grid">
        <article className="conflict-network-panel">
          <div className="interference-panel-title"><Network size={17} /><strong>冲突链路图</strong></div>
          <RiskNetwork risks={visible} />
        </article>
        <article className="band-risk-panel">
          <div className="interference-panel-title"><ShieldAlert size={17} /><strong>频段竞争压力</strong></div>
          {bands.length ? bands.slice(0, 8).map((band) => (
            <div className="interference-band-row" key={band.band_group}>
              <div><strong>{band.band_group}</strong><span>{band.assignment_count} 个分配对象</span></div>
              <b><i style={{ width: `${Math.min(100, Math.max(2, band.utilization_pct))}%` }} /></b>
              <em>{Math.round(band.utilization_pct)}%</em>
            </div>
          )) : <Empty text="等待规划后生成频段竞争压力" />}
        </article>
      </div>

      <div className="risk-explanation-list">
        {pageRows.length ? pageRows.map((risk, index) => (
          <article className={`risk-explanation-card ${tone(risk.severity)}`} key={`${risk.risk_type}-${risk.reason}-${index}`}>
            <div className="risk-explanation-head">
              <div><span>{risk.severity}风险</span><strong>{risk.risk_type}</strong></div>
              <b>{Number(risk.score).toFixed(1)}</b>
            </div>
            <div className="risk-parties">
              <strong>{risk.equipment_group_a || risk.task_unit_a || '资源规则'}</strong>
              <span>关联</span>
              <strong>{risk.equipment_group_b || risk.task_unit_b || risk.resource_b || '频谱约束'}</strong>
            </div>
            <ol className="explanation-chain">
              <li><span>1</span><div><strong>资源关系</strong><p>{risk.resource_a || '未分配'} / {risk.resource_b || '规则约束'}</p></div></li>
              <li><span>2</span><div><strong>风险计算</strong><p>{risk.reason}</p></div></li>
              <li><span>3</span><div><strong>处置建议</strong><p>{recommendation(risk.risk_type)}</p></div></li>
            </ol>
          </article>
        )) : <Empty text={risks.length ? '当前筛选条件下无风险' : '完成用频规划后生成冲突链路和风险解释链'} />}
      </div>
      {visible.length > pageSize && (
        <div className="risk-pagination" aria-label="风险分页">
          <button type="button" disabled={currentPage <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>上一页</button>
          <span>第 {currentPage} / {pageCount} 页</span>
          <button type="button" disabled={currentPage >= pageCount} onClick={() => setPage((value) => Math.min(pageCount, value + 1))}>下一页</button>
        </div>
      )}
    </section>
  );
}

function RiskMetric({ label, value, tone: metricTone = '' }: { label: string; value: number; tone?: string }) {
  return <div className={metricTone}><span>{label}</span><strong>{value}</strong></div>;
}

function RiskNetwork({ risks }: { risks: TaskRiskItemView[] }) {
  const links = risks.filter((item) => item.task_unit_a && item.task_unit_b).slice(0, 14);
  const nodes = Array.from(new Set(links.flatMap((item) => [item.task_unit_a, item.task_unit_b]).filter(Boolean))) as string[];
  if (!links.length) return <Empty text="当前无任务单元间冲突链路" />;
  const width = 720;
  const height = 310;
  const positions = new Map(nodes.map((node, index) => {
    const angle = Math.PI * 2 * index / Math.max(nodes.length, 1) - Math.PI / 2;
    return [node, { x: width / 2 + Math.cos(angle) * 250, y: height / 2 + Math.sin(angle) * 105 }] as const;
  }));
  return (
    <svg className="interference-network" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="任务单元冲突链路图">
      {links.map((link, index) => {
        const source = positions.get(link.task_unit_a as string);
        const target = positions.get(link.task_unit_b as string);
        if (!source || !target) return null;
        return <line key={`${link.risk_type}-${index}`} x1={source.x} y1={source.y} x2={target.x} y2={target.y} className={tone(link.severity)} strokeWidth={Math.max(2, Number(link.score) / 16)}><title>{link.risk_type}: {link.reason}</title></line>;
      })}
      {nodes.map((node) => {
        const position = positions.get(node)!;
        return <g key={node}><circle cx={position.x} cy={position.y} r="27" /><text x={position.x} y={position.y + 4} textAnchor="middle">{node.replace(/^TU-/, '').slice(0, 8)}</text><title>{node}</title></g>;
      })}
    </svg>
  );
}

function recommendation(type: string): string {
  if (type.includes('互调')) return '调整三组频点组合，增加收发隔离，并复核发射机非线性指标。';
  if (type.includes('同频') || type.includes('竞争')) return '拆分同频资源、扩大复用距离，或优先保障高优先级任务。';
  if (type.includes('邻频') || type.includes('间隔')) return '增加信道或保护带间隔，必要时降低占用带宽。';
  if (type.includes('功率') || type.includes('距离')) return '降低发射功率、调整部署位置，或增加天线隔离。';
  if (type.includes('保护') || type.includes('禁用')) return '避让受保护或禁用频段，并重新计算主备频点。';
  return '复核任务优先级、资源约束和备份频点后执行局部重筹。';
}

function tone(level: string): string {
  if (level === '高') return 'risk-high';
  if (level === '中') return 'risk-medium';
  return 'risk-low';
}

function Empty({ text }: { text: string }) {
  return <div className="empty small">{text}</div>;
}

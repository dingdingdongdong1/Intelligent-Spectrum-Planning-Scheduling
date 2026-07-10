import { BarChart3, CheckCircle2, Download, Eye } from 'lucide-react';
import { ComparisonResult, ComparisonPlan, url } from './api';

type Props = {
  data: ComparisonResult | null;
  projectId: number | null;
  onSelect: (plan: ComparisonPlan) => void;
};

export default function ComparisonPanel({ data, projectId, onSelect }: Props) {
  if (!data) {
    return (
      <section className="panel comparison-panel">
        <div className="panel-title">
          <BarChart3 size={18} />
          <h2>方案对比</h2>
        </div>
        <div className="empty small">点击“方案对比”后生成多套规划方案并并排比较。</div>
      </section>
    );
  }

  return (
    <section className="panel comparison-panel">
      <div className="panel-title">
        <BarChart3 size={18} />
        <h2>方案对比</h2>
      </div>
      <div className="comparison-grid">
        {data.plans.map((plan) => (
          <article className={`plan-card ${plan.recommended ? 'recommended' : ''}`} key={plan.run_id}>
            <div className="plan-card-head">
              <div>
                <h3>{plan.label}</h3>
                <p>{plan.description}</p>
              </div>
              {plan.recommended && (
                <span className="recommend-badge">
                  <CheckCircle2 size={14} />
                  推荐
                </span>
              )}
            </div>
            <div className="plan-metrics">
              <Metric label="运行" value={`#${plan.run_id}`} />
              <Metric label="高风险" value={plan.high_risk_count} />
              <Metric label="中风险" value={plan.medium_risk_count} />
              <Metric label="风险项" value={plan.risk_item_count} />
              <Metric label="使用频点" value={plan.used_frequency_count} />
              <Metric label="最大台站风险" value={plan.max_station_risk} />
            </div>
            <div className="plan-actions">
              <button onClick={() => onSelect(plan)}>
                <Eye size={15} />
                查看
              </button>
              {projectId && plan.status === 'success' && (
                <a href={url(`/api/projects/${projectId}/export.xlsx?run=${plan.run_id}`)}>
                  <Download size={15} />
                  导出
                </a>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value ?? '-'}</strong>
    </div>
  );
}

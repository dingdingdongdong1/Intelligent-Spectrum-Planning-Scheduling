import { Activity, BarChart3, Lightbulb, MapPinned, RadioTower, RefreshCw } from 'lucide-react';
import { useMemo, useState } from 'react';
import { VisualizationData, VisualizationRiskLink, VisualizationSpectrumBand } from './api';
import LeafletMap from './LeafletMap';

const riskColor: Record<string, string> = {
  高: '#d92d20',
  中: '#dc6803',
  低: '#078658',
};

type RiskFilter = '全部' | '高' | '中' | '低';

export default function VisualizationPanel({
  data,
  previousData,
}: {
  data: VisualizationData | null;
  previousData: VisualizationData | null;
}) {
  const [riskFilter, setRiskFilter] = useState<RiskFilter>('全部');
  const [serviceFilter, setServiceFilter] = useState('全部');
  const [selectedLinkKey, setSelectedLinkKey] = useState<string | null>(null);

  const serviceOptions = useMemo(() => {
    if (!data) return ['全部'];
    return ['全部', ...Array.from(new Set(data.stations.map((station) => station.service_type ?? '未分类'))).sort()];
  }, [data]);

  const filtered = useMemo(() => {
    if (!data) return { stations: [], links: [] };
    const stations =
      serviceFilter === '全部'
        ? data.stations
        : data.stations.filter((station) => (station.service_type ?? '未分类') === serviceFilter);
    const stationIds = new Set(stations.map((station) => station.station_id));
    const links = data.risk_links.filter((link) => {
      const riskOk = riskFilter === '全部' || link.severity === riskFilter;
      return riskOk && stationIds.has(link.station_a) && stationIds.has(link.station_b);
    });
    return { stations, links };
  }, [data, riskFilter, serviceFilter]);

  if (!data) {
    return (
      <section className="visual-board">
        <div className="visual-header">
          <div>
            <p className="eyebrow">可视化看板</p>
            <h2>等待规划结果</h2>
          </div>
        </div>
        <div className="empty visual-empty">完成规划后显示频段占用、台站分布和风险链路。</div>
      </section>
    );
  }

  const activeLink = filtered.links.find((link) => linkKey(link) === selectedLinkKey) ?? null;

  return (
    <section className="visual-board">
      <div className="visual-header">
        <div>
          <p className="eyebrow">可视化看板</p>
          <h2>频谱占用、台站分布与风险链路</h2>
        </div>
        <div className="visual-metrics">
          <Metric label="台站" value={data.summary.station_count} />
          <Metric label="已分配" value={data.summary.assigned_count} />
          <Metric label="风险链路" value={data.summary.risk_link_count} />
          <Metric label="频段组" value={data.summary.band_count} />
        </div>
      </div>

      <div className="map-filterbar">
        <label>
          <span>风险等级</span>
          <select
            aria-label="风险等级"
            name="risk_filter"
            value={riskFilter}
            onChange={(event) => setRiskFilter(event.target.value as RiskFilter)}
          >
            <option value="全部">全部</option>
            <option value="高">高</option>
            <option value="中">中</option>
            <option value="低">低</option>
          </select>
        </label>
        <label>
          <span>业务类型</span>
          <select
            aria-label="业务类型"
            name="service_filter"
            value={serviceFilter}
            onChange={(event) => setServiceFilter(event.target.value)}
          >
            {serviceOptions.map((service) => (
              <option value={service} key={service}>
                {service}
              </option>
            ))}
          </select>
        </label>
        {activeLink && (
          <div className="selected-link">
            <strong>
              {activeLink.station_a} - {activeLink.station_b}
            </strong>
            <span>{activeLink.reason}</span>
          </div>
        )}
      </div>

      <div className="visual-grid">
        <div className="chart-block map-block">
          <div className="chart-title">
            <MapPinned size={17} />
            <span>真实地图与风险链路</span>
          </div>
          <LeafletMap
            stations={filtered.stations}
            links={filtered.links}
            selectedLinkKey={selectedLinkKey}
            onLinkSelect={setSelectedLinkKey}
          />
        </div>

        <div className="chart-block">
          <div className="chart-title">
            <RadioTower size={17} />
            <span>频段占用</span>
          </div>
          <SpectrumBands bands={data.spectrum} />
        </div>

        <div className="chart-block">
          <div className="chart-title">
            <BarChart3 size={17} />
            <span>风险统计</span>
          </div>
          <Distribution title="链路风险" items={data.risk_distribution.map((item) => ({ label: item.level, value: item.count }))} />
          <Distribution title="台站风险" items={data.station_risk_distribution.map((item) => ({ label: item.level, value: item.count }))} />
          <Distribution title="业务类型" items={data.service_distribution.map((item) => ({ label: item.service_type, value: item.count }))} />
        </div>

        <div className="chart-block">
          <div className="chart-title">
            <Activity size={17} />
            <span>重点风险链路</span>
          </div>
          <RiskList links={filtered.links} selectedKey={selectedLinkKey} onSelect={setSelectedLinkKey} />
        </div>

        <div className="chart-block insight-block">
          <div className="chart-title">
            <Lightbulb size={17} />
            <span>风险解释与处置</span>
          </div>
          <RiskInsights links={data.risk_links} />
        </div>

        <div className="chart-block insight-block">
          <div className="chart-title">
            <RefreshCw size={17} />
            <span>方案差异</span>
          </div>
          <PlanDiff previous={previousData} current={data} />
        </div>
      </div>
    </section>
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

function SpectrumBands({ bands }: { bands: VisualizationSpectrumBand[] }) {
  if (!bands.length) return <div className="empty small">暂无频段数据</div>;
  return (
    <div className="spectrum-list">
      {bands.map((band) => (
        <div className="spectrum-row" key={`${band.band_group}-${band.service_type}`}>
          <div className="spectrum-meta">
            <strong>{band.band_group}</strong>
            <span>{band.service_type}</span>
            <em>{formatRange(band.start_mhz, band.end_mhz)}</em>
          </div>
          <div className="spectrum-track">
            <div className="spectrum-fill" style={{ width: `${Math.min(100, band.utilization_pct)}%` }} />
            {band.assignments.map((assignment) => {
              const left = frequencyLeft(assignment.frequency_mhz, band.start_mhz, band.end_mhz);
              return (
                <i
                  key={`${assignment.station_id}-${assignment.frequency_mhz}`}
                  className={`freq-marker ${riskClass(assignment.risk_level)}`}
                  style={{ left: `${left}%` }}
                >
                  <span>{assignment.station_id}</span>
                </i>
              );
            })}
          </div>
          <div className="spectrum-count">
            {band.used_channel_count}/{band.candidate_channel_count}
          </div>
        </div>
      ))}
    </div>
  );
}

function Distribution({ title, items }: { title: string; items: Array<{ label: string; value: number }> }) {
  const max = Math.max(...items.map((item) => item.value), 1);
  return (
    <div className="distribution">
      <h3>{title}</h3>
      {items.map((item) => (
        <div className="dist-row" key={`${title}-${item.label}`}>
          <span>{item.label}</span>
          <b>
            <i style={{ width: `${(item.value / max) * 100}%`, background: riskColor[item.label] ?? '#356ac3' }} />
          </b>
          <em>{item.value}</em>
        </div>
      ))}
    </div>
  );
}

function RiskList({
  links,
  selectedKey,
  onSelect,
}: {
  links: VisualizationRiskLink[];
  selectedKey: string | null;
  onSelect: (key: string) => void;
}) {
  if (!links.length) return <div className="empty small">暂无明显风险链路</div>;
  return (
    <ol className="risk-list">
      {links.slice(0, 10).map((link) => {
        const key = linkKey(link);
        return (
          <li key={key} className={selectedKey === key ? 'active' : ''}>
            <button type="button" onClick={() => onSelect(key)}>
              <div>
                <strong>
                  {link.station_a} - {link.station_b}
                </strong>
                <span className={riskClass(link.severity)}>{link.severity}</span>
              </div>
              <p>{link.reason}</p>
            </button>
          </li>
        );
      })}
    </ol>
  );
}

function RiskInsights({ links }: { links: VisualizationRiskLink[] }) {
  if (!links.length) return <div className="empty small">暂无明显风险项</div>;
  const grouped = Array.from(
    links.reduce((map, link) => {
      const key = link.risk_type || '其他风险';
      const item = map.get(key) ?? { riskType: key, count: 0, high: 0, medium: 0, maxScore: 0, example: link };
      item.count += 1;
      item.high += link.severity === '高' ? 1 : 0;
      item.medium += link.severity === '中' ? 1 : 0;
      if (link.score > item.maxScore) {
        item.maxScore = link.score;
        item.example = link;
      }
      map.set(key, item);
      return map;
    }, new Map<string, { riskType: string; count: number; high: number; medium: number; maxScore: number; example: VisualizationRiskLink }>()),
  ).map(([, item]) => item);
  grouped.sort((a, b) => b.high - a.high || b.medium - a.medium || b.maxScore - a.maxScore);

  return (
    <div className="insight-list">
      {grouped.slice(0, 4).map((item) => (
        <article key={item.riskType}>
          <div>
            <strong>{item.riskType}</strong>
            <span>
              {item.count} 项，最高 {formatNumber(item.maxScore)}
            </span>
          </div>
          <p>{item.example.reason}</p>
          <em>{suggestionFor(item.riskType)}</em>
        </article>
      ))}
    </div>
  );
}

function PlanDiff({ previous, current }: { previous: VisualizationData | null; current: VisualizationData }) {
  const diff = useMemo(() => buildPlanDiff(previous, current), [previous, current]);
  if (!diff) return <div className="empty small">暂无上一版方案可对比</div>;

  return (
    <div className="diff-panel">
      <div className="diff-metrics">
        <Metric label="频点变更" value={diff.frequencyChanged} />
        <Metric label="风险下降" value={diff.improved} />
        <Metric label="风险上升" value={diff.worsened} />
        <Metric label="总风险变化" value={formatSigned(diff.totalRiskDelta)} />
      </div>
      {diff.changes.length ? (
        <ol className="diff-list">
          {diff.changes.slice(0, 8).map((change) => (
            <li key={change.stationId}>
              <strong>{change.stationId}</strong>
              <span>
                {formatFrequency(change.previousFrequency)} → {formatFrequency(change.currentFrequency)}
              </span>
              <em className={change.scoreDelta > 0 ? 'risk-high' : change.scoreDelta < 0 ? 'risk-low' : ''}>
                {change.previousRiskLevel} → {change.currentRiskLevel}，{formatSigned(change.scoreDelta)}
              </em>
            </li>
          ))}
        </ol>
      ) : (
        <div className="empty small">与上一版没有台站级变化</div>
      )}
    </div>
  );
}

function buildPlanDiff(previous: VisualizationData | null, current: VisualizationData) {
  if (!previous) return null;
  const before = new Map(previous.stations.map((station) => [station.station_id, station]));
  const after = new Map(current.stations.map((station) => [station.station_id, station]));
  const stationIds = Array.from(new Set([...before.keys(), ...after.keys()])).sort();
  const changes = stationIds
    .map((stationId) => {
      const oldStation = before.get(stationId);
      const newStation = after.get(stationId);
      const previousFrequency = oldStation?.frequency_mhz ?? null;
      const currentFrequency = newStation?.frequency_mhz ?? null;
      const previousRiskScore = oldStation?.risk_score ?? 0;
      const currentRiskScore = newStation?.risk_score ?? 0;
      const frequencyChanged = Math.abs((previousFrequency ?? -1) - (currentFrequency ?? -1)) > 0.000001;
      const scoreDelta = currentRiskScore - previousRiskScore;
      const riskChanged = (oldStation?.risk_level ?? '-') !== (newStation?.risk_level ?? '-') || Math.abs(scoreDelta) > 0.000001;
      if (!frequencyChanged && !riskChanged) return null;
      return {
        stationId,
        previousFrequency,
        currentFrequency,
        previousRiskLevel: oldStation?.risk_level ?? '-',
        currentRiskLevel: newStation?.risk_level ?? '-',
        previousRiskScore,
        currentRiskScore,
        scoreDelta,
        frequencyChanged,
      };
    })
    .filter((item): item is NonNullable<typeof item> => item !== null)
    .sort((a, b) => Math.abs(b.scoreDelta) - Math.abs(a.scoreDelta));

  return {
    changes,
    frequencyChanged: changes.filter((item) => item.frequencyChanged).length,
    improved: changes.filter((item) => item.scoreDelta < 0).length,
    worsened: changes.filter((item) => item.scoreDelta > 0).length,
    totalRiskDelta: sumRisk(current) - sumRisk(previous),
  };
}

function sumRisk(data: VisualizationData): number {
  return data.stations.reduce((total, station) => total + (Number(station.risk_score) || 0), 0);
}

function suggestionFor(type: string): string {
  if (type.includes('同频')) return '建议优先拆分同频台站，或扩大同频复用距离。';
  if (type.includes('邻频')) return '建议增大相邻信道间隔，或调整保护带与候选频点。';
  if (type.includes('近距离') || type.includes('高功率')) return '建议降低发射功率、调整天线参数，或为近距离台站分配更分散的频点。';
  return '建议复核规则表中的保护距离、最小间隔和禁用频点约束。';
}

function frequencyLeft(frequency: number, start: number | null, end: number | null): number {
  if (start === null || end === null || end <= start) return 0;
  return Math.max(0, Math.min(100, ((frequency - start) / (end - start)) * 100));
}

function formatRange(start: number | null, end: number | null): string {
  if (start === null || end === null) return '-';
  return `${start.toFixed(3)}-${end.toFixed(3)} MHz`;
}

function formatFrequency(value: number | null): string {
  return value === null ? '-' : `${value.toFixed(3)} MHz`;
}

function formatNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function formatSigned(value: number): string {
  if (Math.abs(value) < 0.000001) return '0';
  return `${value > 0 ? '+' : ''}${formatNumber(value)}`;
}

function linkKey(link: VisualizationRiskLink): string {
  return `${link.station_a}-${link.station_b}-${link.risk_type}-${link.frequency_a_mhz ?? '-'}-${link.frequency_b_mhz ?? '-'}`;
}

function riskClass(level: string | null | undefined): string {
  if (level === '高') return 'risk-high';
  if (level === '中') return 'risk-medium';
  return 'risk-low';
}

"use client";

import { CSSProperties, ReactNode, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Crosshair,
  Download,
  Gauge,
  Layers3,
  Lock,
  RadioTower,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Target,
  Zap,
} from "lucide-react";

type ScenarioKey = "joint" | "lowAltitude" | "contested";
type MarkerTone = "planned" | "fixed" | "temporary" | "jammed" | "protected" | "reserved";

type SpectrumMarker = {
  left: number;
  width: number;
  label: string;
  tone: MarkerTone;
};

type SpectrumLane = {
  range: string;
  service: string;
  utilization: number;
  markers: SpectrumMarker[];
};

type Scenario = {
  label: string;
  subtitle: string;
  command: string;
  baseSatisfaction: number;
  baseRisk: number;
  bandwidth: number;
  latency: number;
  lanes: SpectrumLane[];
  risks: Array<{ title: string; detail: string; severity: "高" | "中" | "低" }>;
  actions: Array<{ title: string; detail: string; score: number }>;
};

const scenarios: Record<ScenarioKey, Scenario> = {
  joint: {
    label: "联合任务保障",
    subtitle: "陆空协同、雷达观测、数据链与电子对抗混合用频",
    command: "东部战区演训 · 2026A",
    baseSatisfaction: 92.7,
    baseRisk: 7,
    bandwidth: 1.28,
    latency: 42,
    lanes: [
      {
        range: "30-88",
        service: "短波/超短波指挥",
        utilization: 68,
        markers: [
          { left: 8, width: 42, label: "主用通信", tone: "planned" },
          { left: 64, width: 18, label: "预留链路", tone: "reserved" },
        ],
      },
      {
        range: "225-400",
        service: "航空数据链",
        utilization: 61,
        markers: [
          { left: 14, width: 18, label: "无人机遥测", tone: "fixed" },
          { left: 42, width: 22, label: "战术数据链", tone: "planned" },
          { left: 77, width: 12, label: "保护窗口", tone: "protected" },
        ],
      },
      {
        range: "960-1240",
        service: "雷达/导航",
        utilization: 76,
        markers: [
          { left: 6, width: 29, label: "雷达主瓣", tone: "planned" },
          { left: 43, width: 20, label: "同步干扰", tone: "jammed" },
          { left: 72, width: 17, label: "备用频点", tone: "temporary" },
        ],
      },
      {
        range: "2.0-2.7G",
        service: "宽带侦察",
        utilization: 53,
        markers: [
          { left: 20, width: 24, label: "电子侦察", tone: "fixed" },
          { left: 58, width: 16, label: "临时占用", tone: "temporary" },
        ],
      },
    ],
    risks: [
      { title: "雷达与无人机遥测邻频", detail: "影响 3 个高优先级任务单元", severity: "高" },
      { title: "宽带侦察窗口被压缩", detail: "2.2-2.4 GHz 可用余量不足", severity: "中" },
      { title: "固定台站复用密度上升", detail: "建议重算保护间隔", severity: "中" },
    ],
    actions: [
      { title: "优先保障关键任务", detail: "提高雷达与数据链权重，允许低优先级任务降级", score: 95 },
      { title: "均衡优化", detail: "维持保障率并压低冲突数，适合常态值守", score: 91 },
      { title: "最小带宽占用", detail: "压缩临时占用，保留更多应急窗口", score: 86 },
    ],
  },
  lowAltitude: {
    label: "低空无人集群",
    subtitle: "密集无人平台、测控链路和中继节点快速入网",
    command: "低空空域保障 · 2026B",
    baseSatisfaction: 88.4,
    baseRisk: 11,
    bandwidth: 1.46,
    latency: 35,
    lanes: [
      {
        range: "136-174",
        service: "地面引导",
        utilization: 58,
        markers: [
          { left: 10, width: 22, label: "引导链路", tone: "planned" },
          { left: 48, width: 18, label: "临时测控", tone: "temporary" },
        ],
      },
      {
        range: "400-960",
        service: "低空遥控",
        utilization: 82,
        markers: [
          { left: 4, width: 35, label: "集群遥控", tone: "planned" },
          { left: 43, width: 18, label: "同步干扰", tone: "jammed" },
          { left: 72, width: 19, label: "备用中继", tone: "reserved" },
        ],
      },
      {
        range: "1240-2000",
        service: "图传回传",
        utilization: 71,
        markers: [
          { left: 18, width: 26, label: "宽带图传", tone: "fixed" },
          { left: 52, width: 17, label: "保护窗口", tone: "protected" },
        ],
      },
      {
        range: "5.2-5.8G",
        service: "近距高速链路",
        utilization: 49,
        markers: [
          { left: 28, width: 18, label: "高速回传", tone: "planned" },
          { left: 62, width: 15, label: "保留", tone: "reserved" },
        ],
      },
    ],
    risks: [
      { title: "无人机测控拥塞", detail: "400-450 MHz 竞争密度高", severity: "高" },
      { title: "图传与中继同频", detail: "影响 5 个机动节点", severity: "高" },
      { title: "备用窗口偏少", detail: "建议释放 5.8 GHz 近距链路", severity: "中" },
    ],
    actions: [
      { title: "释放近距高速链路", detail: "将非关键图传迁移到 5.2-5.8 GHz", score: 93 },
      { title: "测控链路分层", detail: "按任务高度和半径分配主备频点", score: 89 },
      { title: "压缩低优先级回传", detail: "牺牲部分码率换取干扰余量", score: 84 },
    ],
  },
  contested: {
    label: "强对抗保通",
    subtitle: "干扰压制、保护频段和应急通信链路并行筹划",
    command: "复杂电磁环境 · 2026C",
    baseSatisfaction: 84.9,
    baseRisk: 14,
    bandwidth: 1.62,
    latency: 51,
    lanes: [
      {
        range: "30-88",
        service: "应急指挥",
        utilization: 74,
        markers: [
          { left: 8, width: 24, label: "应急网", tone: "planned" },
          { left: 38, width: 18, label: "干扰源", tone: "jammed" },
          { left: 68, width: 16, label: "保护", tone: "protected" },
        ],
      },
      {
        range: "225-400",
        service: "抗扰数据链",
        utilization: 86,
        markers: [
          { left: 5, width: 34, label: "跳频数据链", tone: "fixed" },
          { left: 46, width: 24, label: "压制干扰", tone: "jammed" },
          { left: 78, width: 12, label: "备用", tone: "reserved" },
        ],
      },
      {
        range: "960-1240",
        service: "侦测/识别",
        utilization: 64,
        markers: [
          { left: 16, width: 24, label: "侦测窗口", tone: "planned" },
          { left: 58, width: 18, label: "临时禁用", tone: "jammed" },
        ],
      },
      {
        range: "2.7-6G",
        service: "电子对抗",
        utilization: 59,
        markers: [
          { left: 12, width: 20, label: "电子压制", tone: "temporary" },
          { left: 48, width: 26, label: "保护走廊", tone: "protected" },
        ],
      },
    ],
    risks: [
      { title: "压制干扰覆盖主用链路", detail: "225-400 MHz 需立即迁移", severity: "高" },
      { title: "应急指挥保护不足", detail: "低频段保护间隔不足", severity: "高" },
      { title: "侦测窗口碎片化", detail: "建议合并临时频点", severity: "中" },
    ],
    actions: [
      { title: "启动抗扰优先模板", detail: "锁定应急指挥，迁移数据链到备用走廊", score: 97 },
      { title: "合并保护窗口", detail: "牺牲部分电子压制带宽，提高通信连续性", score: 92 },
      { title: "按区域分批重筹", detail: "先保障前沿任务，再回收后方冗余占用", score: 88 },
    ],
  },
};

const missionRows = [
  { unit: "任务单元-01", system: "卫通终端", need: "5925-6425", priority: "高", state: "完全保障", rate: 100 },
  { unit: "任务单元-02", system: "无人机链路", need: "940-980", priority: "高", state: "部分保障", rate: 82 },
  { unit: "任务单元-03", system: "战术数据链", need: "225-400", priority: "高", state: "完全保障", rate: 96 },
  { unit: "任务单元-04", system: "通信电台", need: "136-174", priority: "中", state: "部分保障", rate: 74 },
  { unit: "任务单元-05", system: "电子侦察", need: "2-6 GHz", priority: "中", state: "待复核", rate: 68 },
];

const navItems = ["态势总览", "频段资源", "冲突评估", "动态重筹", "方案留痕"];

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

export default function Home() {
  const [scenarioKey, setScenarioKey] = useState<ScenarioKey>("joint");
  const [taskWeight, setTaskWeight] = useState(72);
  const [riskWeight, setRiskWeight] = useState(68);
  const [reuseWeight, setReuseWeight] = useState(45);
  const [showInterference, setShowInterference] = useState(true);
  const [emergencyMode, setEmergencyMode] = useState(false);
  const scenario = scenarios[scenarioKey];

  const computed = useMemo(() => {
    const satisfaction = clamp(
      scenario.baseSatisfaction + (taskWeight - 65) * 0.09 + (riskWeight - 60) * 0.04 - (emergencyMode ? 1.2 : 0),
      70,
      99.2,
    );
    const risk = clamp(Math.round(scenario.baseRisk - (riskWeight - 60) * 0.08 + (reuseWeight - 45) * 0.06 + (emergencyMode ? 2 : 0)), 2, 18);
    const bandwidth = clamp(scenario.bandwidth + (taskWeight - 70) * 0.006 - (reuseWeight - 45) * 0.004 + (emergencyMode ? 0.08 : 0), 0.9, 1.9);
    const quality = clamp(Math.round(satisfaction * 0.58 + (100 - risk * 4) * 0.24 + (100 - bandwidth * 28) * 0.18), 60, 98);
    return { satisfaction, risk, bandwidth, quality };
  }, [emergencyMode, reuseWeight, riskWeight, scenario, taskWeight]);

  return (
    <main className="ops-shell">
      <aside className="side-rail" aria-label="战场智能频谱筹划导航">
        <div className="brand-lockup">
          <span className="brand-mark">
            <ShieldAlert size={21} />
          </span>
          <div>
            <strong>战场智能频谱筹划</strong>
            <em>电磁态势与动态重筹</em>
          </div>
        </div>
        <nav className="rail-nav">
          {navItems.map((item, index) => (
            <button className={index === 0 ? "active" : ""} key={item} type="button">
              {index === 0 && <Layers3 size={16} />}
              {index === 1 && <RadioTower size={16} />}
              {index === 2 && <ShieldCheck size={16} />}
              {index === 3 && <RefreshCw size={16} />}
              {index === 4 && <Clock3 size={16} />}
              <span>{item}</span>
            </button>
          ))}
        </nav>
        <div className="rail-status">
          <span>当前筹划任务</span>
          <strong>{scenario.command}</strong>
          <p>频谱态势实时汇聚，智能体建议已同步。</p>
          <div>
            <Metric label="保障" value={`${computed.satisfaction.toFixed(1)}%`} />
            <Metric label="风险" value={computed.risk} />
          </div>
        </div>
        <div className="security-note">
          <Lock size={15} />
          <span>脱敏摘要模式</span>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">BATTLEFIELD SPECTRUM PLANNING</span>
            <h1>战场智能频谱筹划平台</h1>
          </div>
          <div className="topbar-actions">
            <span className="health-dot">
              <i />
              系统运行正常
            </span>
            <button type="button" className="icon-command" aria-label="导出筹划摘要" onClick={() => window.print()}>
              <Download size={17} />
            </button>
          </div>
        </header>

        <section className="mission-strip" aria-label="任务模式">
          {(Object.entries(scenarios) as Array<[ScenarioKey, Scenario]>).map(([key, item]) => (
            <button className={scenarioKey === key ? "active" : ""} key={key} type="button" onClick={() => setScenarioKey(key)}>
              <strong>{item.label}</strong>
              <span>{item.subtitle}</span>
            </button>
          ))}
        </section>

        <section className="command-grid" aria-label="筹划驾驶舱">
          <div className="command-panel">
            <div className="section-head">
              <div>
                <span className="eyebrow">任务态势</span>
                <h2>{scenario.label}</h2>
              </div>
              <span className="status-pill">规划进行中</span>
            </div>
            <p className="leader-copy">
              面向{scenario.subtitle}，将任务优先级、频段规则、保护窗口和干扰告警统一进入筹划闭环，生成可解释的频谱分配方案。
            </p>
            <div className="kpi-grid">
              <KpiCard icon={<Activity size={18} />} label="任务保障率" value={`${computed.satisfaction.toFixed(1)}%`} note="关键链路优先满足" tone="blue" />
              <KpiCard icon={<AlertTriangle size={18} />} label="高风险告警" value={computed.risk} note="需复核冲突" tone={computed.risk > 9 ? "red" : "amber"} />
              <KpiCard icon={<RadioTower size={18} />} label="占用带宽" value={`${computed.bandwidth.toFixed(2)} GHz`} note="含保护与备用窗口" tone="green" />
              <KpiCard icon={<Gauge size={18} />} label="综合质量" value={computed.quality} note={`${scenario.latency} ms 级重筹反馈`} tone="violet" />
            </div>
            <PlanningControls
              taskWeight={taskWeight}
              riskWeight={riskWeight}
              reuseWeight={reuseWeight}
              showInterference={showInterference}
              emergencyMode={emergencyMode}
              onTaskWeight={setTaskWeight}
              onRiskWeight={setRiskWeight}
              onReuseWeight={setReuseWeight}
              onShowInterference={setShowInterference}
              onEmergencyMode={setEmergencyMode}
            />
          </div>

          <div className="visual-panel">
            <div className="visual-map">
              <span className="map-grid horizontal" />
              <span className="map-grid vertical" />
              <MapNode className="command" label="指挥所" icon={<Target size={14} />} />
              <MapNode className="radar" label="雷达阵地" icon={<RadioTower size={14} />} />
              <MapNode className="uav" label="无人平台" icon={<Crosshair size={14} />} />
              <MapNode className="ew" label="电子对抗" icon={<Zap size={14} />} />
              <svg className="link-layer" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                <line x1="24" y1="48" x2="74" y2="27" />
                <line x1="24" y1="48" x2="74" y2="68" />
                <line x1="74" y1="27" x2="50" y2="77" />
              </svg>
            </div>
            <div className="asset-preview">
              <img src="/dashboard-concept.png" alt="项目原型中的智能频谱规划助手仪表盘" />
            </div>
          </div>
        </section>

        <section className="lower-grid">
          <SpectrumBoard lanes={scenario.lanes} showInterference={showInterference} />
          <RecommendationPanel actions={scenario.actions} risks={scenario.risks} />
        </section>

        <section className="matrix-panel" aria-label="任务单元保障矩阵">
          <div className="section-head">
            <div>
              <span className="eyebrow">保障矩阵</span>
              <h2>任务单元、装备组与频段池指配</h2>
            </div>
            <span className="status-pill neutral">5 个高价值任务</span>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>任务单元</th>
                  <th>装备/系统</th>
                  <th>频段需求 MHz</th>
                  <th>重要级别</th>
                  <th>当前状态</th>
                  <th>保障率</th>
                </tr>
              </thead>
              <tbody>
                {missionRows.map((row) => (
                  <tr key={row.unit}>
                    <td>{row.unit}</td>
                    <td>{row.system}</td>
                    <td>{row.need}</td>
                    <td>
                      <span className={`priority ${row.priority === "高" ? "high" : "medium"}`}>{row.priority}</span>
                    </td>
                    <td>{row.state}</td>
                    <td>
                      <span className="rate-bar">
                        <i style={{ width: `${row.rate}%` }} />
                      </span>
                      {row.rate}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function KpiCard({
  icon,
  label,
  value,
  note,
  tone,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  note: string;
  tone: "blue" | "green" | "amber" | "red" | "violet";
}) {
  return (
    <article className={`kpi-card ${tone}`}>
      <span>{icon}</span>
      <div>
        <em>{label}</em>
        <strong>{value}</strong>
        <small>{note}</small>
      </div>
    </article>
  );
}

function PlanningControls({
  taskWeight,
  riskWeight,
  reuseWeight,
  showInterference,
  emergencyMode,
  onTaskWeight,
  onRiskWeight,
  onReuseWeight,
  onShowInterference,
  onEmergencyMode,
}: {
  taskWeight: number;
  riskWeight: number;
  reuseWeight: number;
  showInterference: boolean;
  emergencyMode: boolean;
  onTaskWeight: (value: number) => void;
  onRiskWeight: (value: number) => void;
  onReuseWeight: (value: number) => void;
  onShowInterference: (value: boolean) => void;
  onEmergencyMode: (value: boolean) => void;
}) {
  return (
    <div className="planning-controls" aria-label="筹划参数">
      <div className="control-head">
        <SlidersHorizontal size={17} />
        <strong>筹划权重</strong>
      </div>
      <RangeControl label="任务保障" value={taskWeight} onChange={onTaskWeight} />
      <RangeControl label="风险压制" value={riskWeight} onChange={onRiskWeight} />
      <RangeControl label="复用效率" value={reuseWeight} onChange={onReuseWeight} />
      <div className="toggle-row">
        <label>
          <input type="checkbox" checked={showInterference} onChange={(event) => onShowInterference(event.target.checked)} />
          <span>显示干扰源</span>
        </label>
        <label>
          <input type="checkbox" checked={emergencyMode} onChange={(event) => onEmergencyMode(event.target.checked)} />
          <span>应急抢占</span>
        </label>
      </div>
    </div>
  );
}

function RangeControl({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return (
    <label className="range-control">
      <span>{label}</span>
      <input type="range" min="20" max="100" value={value} onChange={(event) => onChange(Number(event.target.value))} />
      <strong>{value}</strong>
    </label>
  );
}

function MapNode({ className, label, icon }: { className: string; label: string; icon: ReactNode }) {
  return (
    <span className={`map-node ${className}`}>
      {icon}
      <strong>{label}</strong>
    </span>
  );
}

function SpectrumBoard({ lanes, showInterference }: { lanes: SpectrumLane[]; showInterference: boolean }) {
  return (
    <section className="spectrum-panel" aria-label="频谱占用全景">
      <div className="section-head">
        <div>
          <span className="eyebrow">频谱占用</span>
          <h2>跨频段占用全景</h2>
        </div>
        <span className="status-pill neutral">MHz 视图</span>
      </div>
      <div className="spectrum-axis">
        <span>频段池</span>
        <span>0%</span>
        <span>25%</span>
        <span>50%</span>
        <span>75%</span>
        <span>100%</span>
      </div>
      <div className="spectrum-lanes">
        {lanes.map((lane) => (
          <article key={lane.range}>
            <div className="lane-label">
              <strong>{lane.range}</strong>
              <span>{lane.service}</span>
            </div>
            <div className="lane-track">
              <span className="lane-utilization" style={{ width: `${lane.utilization}%` }} />
              {lane.markers
                .filter((marker) => showInterference || marker.tone !== "jammed")
                .map((marker) => (
                  <button
                    className={`lane-marker ${marker.tone}`}
                    key={`${lane.range}-${marker.label}`}
                    type="button"
                    style={{ left: `${marker.left}%`, width: `${marker.width}%` } as CSSProperties}
                    title={marker.label}
                    aria-label={`${lane.range} ${marker.label}`}
                  >
                    <span>{marker.label}</span>
                  </button>
                ))}
            </div>
            <em>{lane.utilization}%</em>
          </article>
        ))}
      </div>
      <div className="legend-row">
        <span className="planned">已规划</span>
        <span className="fixed">固定占用</span>
        <span className="temporary">临时占用</span>
        <span className="jammed">干扰源</span>
        <span className="protected">保护频段</span>
        <span className="reserved">预留</span>
      </div>
    </section>
  );
}

function RecommendationPanel({
  actions,
  risks,
}: {
  actions: Scenario["actions"];
  risks: Scenario["risks"];
}) {
  return (
    <aside className="decision-panel" aria-label="智能决策建议">
      <div className="section-head compact">
        <div>
          <span className="eyebrow">智能体建议</span>
          <h2>风险闭环与重筹动作</h2>
        </div>
        <Sparkles size={18} />
      </div>
      <div className="risk-list">
        {risks.map((risk) => (
          <article className={`risk-card ${risk.severity === "高" ? "high" : risk.severity === "中" ? "medium" : "low"}`} key={risk.title}>
            <strong>{risk.title}</strong>
            <span>{risk.detail}</span>
            <em>{risk.severity}风险</em>
          </article>
        ))}
      </div>
      <div className="action-list">
        {actions.map((action, index) => (
          <article key={action.title}>
            <span>方案 {String.fromCharCode(65 + index)}</span>
            <strong>{action.title}</strong>
            <p>{action.detail}</p>
            <button type="button">
              <CheckCircle2 size={15} />
              应用方案
            </button>
            <em>{action.score}</em>
          </article>
        ))}
      </div>
    </aside>
  );
}

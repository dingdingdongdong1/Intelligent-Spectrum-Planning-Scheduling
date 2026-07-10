from __future__ import annotations

import io
from html import escape

import pandas as pd


def generate_report(project: dict, run: dict, assignments: list[dict], risk_items: list[dict], summary: dict) -> str:
    assignment_rows = "\n".join(
        f"""
        <tr>
          <td>{escape(str(item.get("station_id", "")))}</td>
          <td>{_fmt_freq(item.get("assigned_frequency_mhz"))}</td>
          <td>{escape(str(item.get("alternative_frequencies_mhz", "")))}</td>
          <td><span class="level {escape(str(item.get("risk_level", "")))}">{escape(str(item.get("risk_level", "")))}</span></td>
          <td>{escape(str(item.get("risk_score", 0)))}</td>
          <td>{escape(str(item.get("notes", "")))}</td>
        </tr>
        """
        for item in assignments
    )
    risk_rows = "\n".join(
        f"""
        <tr>
          <td>{escape(str(item.get("risk_type", "")))}</td>
          <td>{escape(str(item.get("severity", "")))}</td>
          <td>{escape(str(item.get("station_a", "")))}</td>
          <td>{escape(str(item.get("station_b", "")))}</td>
          <td>{_fmt_freq(item.get("frequency_a_mhz"))}</td>
          <td>{_fmt_freq(item.get("frequency_b_mhz"))}</td>
          <td>{escape(str(item.get("score", "")))}</td>
          <td>{escape(str(item.get("reason", "")))}</td>
        </tr>
        """
        for item in risk_items
    )
    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>频谱规划报告 - {escape(project.get("name", ""))}</title>
  <style>
    body {{ font-family: Arial, "Microsoft YaHei", sans-serif; margin: 32px; color: #172033; }}
    h1, h2 {{ margin: 0 0 16px; }}
    section {{ margin: 28px 0; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border: 1px solid #d8dde8; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f6fb; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 12px; }}
    .metric {{ border: 1px solid #d8dde8; padding: 12px; border-radius: 6px; background: #fbfcff; }}
    .metric strong {{ display: block; font-size: 22px; margin-top: 4px; }}
    .level {{ font-weight: 700; }}
    .高 {{ color: #b42318; }}
    .中 {{ color: #b54708; }}
    .低 {{ color: #067647; }}
  </style>
</head>
<body>
  <h1>频谱规划报告</h1>
  <p>项目：{escape(project.get("name", ""))}｜运行编号：{escape(str(run.get("id", "")))}｜状态：{escape(run.get("status", ""))}</p>

  <section class="summary">
    <div class="metric">台站数量<strong>{escape(str(summary.get("station_count", len(assignments))))}</strong></div>
    <div class="metric">候选频点数<strong>{escape(str(summary.get("candidate_count", "-")))}</strong></div>
    <div class="metric">风险项<strong>{escape(str(summary.get("risk_item_count", len(risk_items))))}</strong></div>
    <div class="metric">高风险项<strong>{escape(str(summary.get("high_risk_count", 0)))}</strong></div>
  </section>

  <section>
    <h2>推荐频率分配</h2>
    <table>
      <thead>
        <tr><th>台站编号</th><th>推荐频率 MHz</th><th>备选频率 MHz</th><th>风险等级</th><th>风险分</th><th>说明</th></tr>
      </thead>
      <tbody>{assignment_rows}</tbody>
    </table>
  </section>

  <section>
    <h2>干扰风险明细</h2>
    <table>
      <thead>
        <tr><th>类型</th><th>等级</th><th>台站 A</th><th>台站 B</th><th>频率 A</th><th>频率 B</th><th>分值</th><th>原因</th></tr>
      </thead>
      <tbody>{risk_rows or '<tr><td colspan="8">未发现明显同频、邻频或近距离高功率风险。</td></tr>'}</tbody>
    </table>
  </section>
</body>
</html>
"""


def build_export_xlsx(assignments: list[dict], risk_items: list[dict], summary: dict) -> bytes:
    buffer = io.BytesIO()
    assignment_df = pd.DataFrame(assignments)
    risk_df = pd.DataFrame(risk_items)
    summary_df = pd.DataFrame([summary])
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        assignment_df.to_excel(writer, index=False, sheet_name="规划结果")
        risk_df.to_excel(writer, index=False, sheet_name="风险明细")
        summary_df.to_excel(writer, index=False, sheet_name="汇总")
    return buffer.getvalue()


def _fmt_freq(value: object) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.6f}"
    except (TypeError, ValueError):
        return escape(str(value))

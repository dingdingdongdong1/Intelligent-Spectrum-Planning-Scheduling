"""Synthetic case-derived scenarios for task spectrum planning.

All coordinates, frequencies, powers, bandwidths, and equipment counts in this
module are simulation assumptions. Public battle-case research supplies only the
mission structure and failure modes.
"""

from __future__ import annotations

import json
from collections.abc import Callable


SIM_SCENARIO_MANIFESTS = {
    "sim_mosul_urban": {
        "scenario_id": "SIM-MOSUL-URBAN-01",
        "name": "摩苏尔城市频谱拥塞仿真",
        "reference_case_id": "CASE-MOSUL-2016-17",
        "case_type": "combat_operation_reference",
        "source_ids": ["SRC-25"],
        "factual_basis": ["城市频谱拥塞", "UAS/C-UAS并行运用", "友军系统兼容风险", "能力快速机动接入"],
        "simulation_assumptions": ["全部坐标为合成网格", "全部SIM频段与功率为算法测试值", "不复原历史行动编组和电子战配置"],
        "dynamic_events": ["新增低空目标", "C-UAS保护窗口扩大", "城区中继节点失联", "火力任务优先级上调"],
        "recommended_objectives": ["minimize_interference", "uav_link_priority", "communication_continuity"],
    },
    "sim_kabul_airlift": {
        "scenario_id": "SIM-KABUL-AIRLIFT-01",
        "name": "机场高密度撤离通信仿真",
        "reference_case_id": "CASE-OAR-2021",
        "case_type": "noncombatant_evacuation_reference",
        "source_ids": ["SRC-28", "SRC-29"],
        "factual_basis": ["昼夜连续空运", "机场空中交通管制", "多国与商业航空协同", "节点和航班快速增长"],
        "simulation_assumptions": ["不使用历史航班表", "机场位置和通信参数均为合成值", "AIR-SIM仅用于软件测试"],
        "dynamic_events": ["航班批次激增", "医疗后送任务插入", "跑道通信节点失效", "伙伴网关临时接入"],
        "recommended_objectives": ["task_assurance", "communication_continuity", "minimize_switching"],
    },
    "sim_oir_cuas": {
        "scenario_id": "SIM-OIR-CUAS-01",
        "name": "基地多传感器反无人机仿真",
        "reference_case_id": "CASE-OIR-CUAS-2023-24",
        "case_type": "combat_operation_reference",
        "source_ids": ["SRC-44"],
        "factual_basis": ["Q-50/Q-53/Q-64多传感器", "FAAD C2融合", "近实时联合态势共享", "专业人员和节点容量约束"],
        "simulation_assumptions": ["雷达名称只表示任务角色", "探测和链路参数为合成值", "不包含真实目标轨迹和交战规则"],
        "dynamic_events": ["传感器离线", "多目标突发", "融合节点负荷上升", "机动防护单元加入"],
        "recommended_objectives": ["radar_priority", "task_assurance", "minimize_interference"],
    },
    "sim_red_sea_defense": {
        "scenario_id": "SIM-RED-SEA-DEFENSE-01",
        "name": "海上多目标防空协同仿真",
        "reference_case_id": "CASE-OPG-2023-24",
        "case_type": "combat_operation_reference",
        "source_ids": ["SRC-30", "SRC-31", "SRC-32"],
        "factual_basis": ["狭窄航道持续护航", "多目标空中威胁", "多国协同", "商船双向通信"],
        "simulation_assumptions": ["舰船和航道坐标为合成网格", "不对应任何参战舰艇配置", "雷达、数据链和卫星频段均为SIM资源"],
        "dynamic_events": ["多目标告警", "联盟节点加入", "商船流量上升", "卫星回传窗口受限"],
        "recommended_objectives": ["radar_priority", "communication_continuity", "priority_equipment"],
    },
}

SIM_SCENARIO_KEYS = frozenset(SIM_SCENARIO_MANIFESTS)


def sim_scenario_records(scenario: str) -> tuple[list[dict], list[dict], list[dict]]:
    builders: dict[str, Callable[[], tuple[list[dict], list[dict], list[dict]]]] = {
        "sim_mosul_urban": _mosul_records,
        "sim_kabul_airlift": _kabul_records,
        "sim_oir_cuas": _oir_cuas_records,
        "sim_red_sea_defense": _red_sea_records,
    }
    try:
        return builders[scenario]()
    except KeyError as exc:
        raise ValueError(f"Unknown SIM scenario: {scenario}") from exc


def _with_raw(data: dict) -> dict:
    return {**data, "raw_json": json.dumps(data, ensure_ascii=False)}


def _task(
    task_id: str,
    name: str,
    unit_type: str,
    lat: float,
    lon: float,
    radius: float,
    priority: int,
    relation: str,
    bands: str,
    ratio: float,
) -> dict:
    return _with_raw(
        {
            "task_unit_id": task_id,
            "name": name,
            "unit_type": unit_type,
            "area_center_lat": lat,
            "area_center_lon": lon,
            "area_radius_km": radius,
            "priority": priority,
            "spectrum_relation": relation,
            "preferred_band_groups": bands,
            "min_satisfaction_ratio": ratio,
        }
    )


def _group(
    group_id: str,
    task_id: str,
    equipment_type: str,
    count: int,
    role: str,
    mobility: str,
    bandwidth: float,
    power: float,
    gain: float,
    height: float,
    sensitivity: float,
    modulation: str,
    duplex: str,
    channels: int,
    mode: str,
    band: str,
    priority: int,
    protection: float,
    spacing: float,
    guard: float,
) -> dict:
    return _with_raw(
        {
            "equipment_group_id": group_id,
            "task_unit_id": task_id,
            "equipment_type": equipment_type,
            "count": count,
            "tx_rx_role": role,
            "mobility": mobility,
            "bandwidth_khz": bandwidth,
            "tx_power_w": power,
            "antenna_gain_dbi": gain,
            "antenna_height_m": height,
            "receiver_sensitivity_dbm": sensitivity,
            "modulation": modulation,
            "duplex_mode": duplex,
            "required_channels": channels,
            "assignment_mode": mode,
            "preferred_band_group": band,
            "priority": priority,
            "protection_distance_km": protection,
            "min_spacing_khz": spacing,
            "guard_band_khz": guard,
        }
    )


def _rule(
    rule_id: str,
    rule_type: str,
    band: str,
    relation: str,
    start: float,
    end: float,
    step: float,
    max_bandwidth: float,
    max_power: float,
    guard: float,
    unit_types: str,
    equipment_types: str,
    reason: str,
    severity: str = "低",
) -> dict:
    return _with_raw(
        {
            "rule_id": rule_id,
            "rule_type": rule_type,
            "band_group": band,
            "spectrum_relation": relation,
            "start_mhz": start,
            "end_mhz": end,
            "channel_step_khz": step,
            "max_bandwidth_khz": max_bandwidth,
            "max_power_w": max_power,
            "guard_band_khz": guard,
            "compatible_unit_types": unit_types,
            "compatible_equipment_types": equipment_types,
            "reason": reason,
            "source": "SIM_CASE_TEMPLATE",
            "severity": severity,
        }
    )


def _mosul_records() -> tuple[list[dict], list[dict], list[dict]]:
    tasks = [
        _task("SIM-MOS-TU-C2", "城市联合指挥", "指挥通信单元", 0.00, 0.00, 8, 10, "独占", "UHF-SIM-MOS,VHF-SIM-MOS", 0.98),
        _task("SIM-MOS-TU-EAST", "东部机动分队", "机动通信单元", 0.08, 0.05, 10, 8, "可复用", "VHF-SIM-MOS,UHF-SIM-MOS", 0.88),
        _task("SIM-MOS-TU-WEST", "西部机动分队", "机动通信单元", -0.06, -0.08, 10, 8, "可复用", "VHF-SIM-MOS,UHF-SIM-MOS", 0.88),
        _task("SIM-MOS-TU-UAV", "城市无人机侦察", "无人机侦察单元", 0.04, 0.12, 14, 9, "独占", "L-SIM-MOS,S-SIM-MOS", 0.95),
        _task("SIM-MOS-TU-CUAS", "反无人机防护", "雷达探测单元", -0.03, 0.09, 12, 10, "独占", "S-SIM-MOS,C-SIM-MOS", 0.98),
        _task("SIM-MOS-TU-BH", "城市回传保障", "回传保障单元", -0.10, 0.02, 16, 8, "可复用", "C-SIM-MOS,Ku-SIM-MOS", 0.90),
    ]
    groups = [
        _group("SIM-MOS-EG-C2", "SIM-MOS-TU-C2", "固定基站", 3, "双工", "固定", 25, 30, 6, 20, -108, "数字窄带", "双工", 4, "离散信道", "UHF-SIM-MOS", 10, 6, 50, 25),
        _group("SIM-MOS-EG-C2-RELAY", "SIM-MOS-TU-C2", "中继设备", 2, "双工", "机动", 25, 25, 5, 8, -108, "数字窄带", "双工", 2, "收发频点对", "UHF-SIM-MOS", 9, 8, 100, 50),
        _group("SIM-MOS-EG-EAST", "SIM-MOS-TU-EAST", "车载电台", 16, "双工", "机动", 25, 20, 3, 3, -105, "数字窄带", "单工", 8, "离散信道", "VHF-SIM-MOS", 8, 4, 50, 25),
        _group("SIM-MOS-EG-WEST", "SIM-MOS-TU-WEST", "手持终端", 32, "双工", "便携", 12.5, 4, 0, 1.5, -103, "数字窄带", "单工", 10, "共享信道", "VHF-SIM-MOS", 8, 2, 12.5, 12.5),
        _group("SIM-MOS-EG-UAV-CTRL", "SIM-MOS-TU-UAV", "无人机遥控链路", 8, "双工", "空中机动", 250, 5, 5, 2, -100, "扩频", "双工", 6, "离散信道", "L-SIM-MOS", 9, 8, 250, 100),
        _group("SIM-MOS-EG-UAV-DATA", "SIM-MOS-TU-UAV", "无人机数传链路", 6, "双工", "空中机动", 1500, 8, 7, 1, -94, "OFDM", "双工", 4, "连续频段", "S-SIM-MOS", 9, 10, 1000, 500),
        _group("SIM-MOS-EG-CUAS-RAD", "SIM-MOS-TU-CUAS", "近程警戒雷达", 3, "发射", "机动", 6000, 900, 24, 10, -82, "仿真脉冲", "单工", 2, "宽带连续频段", "C-SIM-MOS", 10, 20, 2000, 1000),
        _group("SIM-MOS-EG-CUAS-MON", "SIM-MOS-TU-CUAS", "频谱侦察接收机", 3, "接收", "机动", 2000, 0.5, 8, 5, -112, "宽带监测", "单工", 2, "连续频段", "S-SIM-MOS", 9, 12, 500, 250),
        _group("SIM-MOS-EG-BH", "SIM-MOS-TU-BH", "微波回传链路", 4, "双工", "固定", 4000, 3, 18, 16, -88, "QAM", "双工", 3, "连续频段", "C-SIM-MOS", 8, 12, 2000, 1000),
        _group("SIM-MOS-EG-SAT", "SIM-MOS-TU-BH", "卫星通信终端", 2, "双工", "机动", 3000, 4, 15, 3, -90, "仿真卫星波形", "双工", 2, "连续频段", "Ku-SIM-MOS", 8, 10, 1000, 1000),
    ]
    rules = [
        _rule("SIM-MOS-SR-VHF", "可用", "VHF-SIM-MOS", "可复用", 180, 186, 12.5, 25, 30, 12.5, "指挥通信单元,机动通信单元", "手持终端,车载电台", "合成城市窄带资源"),
        _rule("SIM-MOS-SR-UHF", "可用", "UHF-SIM-MOS", "可复用", 540, 560, 25, 50, 50, 25, "指挥通信单元,机动通信单元", "固定基站,中继设备,车载电台", "合成城市指挥资源"),
        _rule("SIM-MOS-SR-L", "可用", "L-SIM-MOS", "独占", 1700, 1730, 100, 1000, 30, 100, "无人机侦察单元", "无人机遥控链路", "合成无人机控制资源"),
        _rule("SIM-MOS-SR-S", "可用", "S-SIM-MOS", "独占", 2350, 2400, 500, 5000, 200, 500, "无人机侦察单元,雷达探测单元", "无人机数传链路,频谱侦察接收机", "合成UAS/C-UAS共享资源"),
        _rule("SIM-MOS-SR-C", "可用", "C-SIM-MOS", "独占", 4750, 4850, 1000, 10000, 1200, 1000, "雷达探测单元,回传保障单元", "近程警戒雷达,微波回传链路", "合成雷达与回传资源"),
        _rule("SIM-MOS-SR-KU", "可用", "Ku-SIM-MOS", "可复用", 15200, 15280, 1000, 5000, 20, 1000, "回传保障单元", "卫星通信终端", "合成卫星回传资源"),
        _rule("SIM-MOS-SR-S-PROTECT", "保护", "S-SIM-MOS", "保护", 2370, 2375, 500, 500, 5, 1000, "", "", "反无人机作业保护窗口仿真", "高"),
        _rule("SIM-MOS-SR-UHF-FORBID", "禁用", "UHF-SIM-MOS", "禁用", 550, 551, 25, 25, 0, 50, "", "", "城区临时禁用窗口仿真", "高"),
    ]
    return tasks, groups, rules


def _kabul_records() -> tuple[list[dict], list[dict], list[dict]]:
    tasks = [
        _task("SIM-KBL-TU-ATC", "机场管制核心", "指挥通信单元", 2.00, 2.00, 6, 10, "独占", "AIR-SIM-KBL,UHF-SIM-KBL", 1.00),
        _task("SIM-KBL-TU-RAMP", "停机坪调度", "机动通信单元", 2.03, 2.02, 4, 9, "独占", "UHF-SIM-KBL,VHF-SIM-KBL", 0.95),
        _task("SIM-KBL-TU-AIRLIFT", "战略空运协调", "数据链协同单元", 2.06, 2.04, 12, 10, "独占", "AIR-SIM-KBL,L-SIM-KBL", 0.98),
        _task("SIM-KBL-TU-COAL", "伙伴协调网关", "回传保障单元", 1.97, 2.06, 10, 8, "可复用", "C-SIM-KBL,Ku-SIM-KBL", 0.90),
        _task("SIM-KBL-TU-MED", "医疗后送通信", "机动通信单元", 1.96, 1.98, 5, 9, "独占", "VHF-SIM-KBL,UHF-SIM-KBL", 0.95),
        _task("SIM-KBL-TU-SEC", "机场安全通信", "机动通信单元", 2.02, 1.94, 8, 8, "可复用", "VHF-SIM-KBL,UHF-SIM-KBL", 0.88),
    ]
    groups = [
        _group("SIM-KBL-EG-ATC", "SIM-KBL-TU-ATC", "固定基站", 3, "双工", "固定", 25, 30, 8, 25, -110, "仿真航空话音", "双工", 6, "离散信道", "AIR-SIM-KBL", 10, 8, 50, 25),
        _group("SIM-KBL-EG-RAMP", "SIM-KBL-TU-RAMP", "车载电台", 18, "双工", "机动", 25, 20, 3, 3, -106, "数字窄带", "单工", 10, "离散信道", "UHF-SIM-KBL", 9, 4, 50, 25),
        _group("SIM-KBL-EG-AIR-DATA", "SIM-KBL-TU-AIRLIFT", "战术数据链终端", 12, "双工", "机动/空中", 1000, 15, 8, 2, -98, "仿真数据链", "双工", 8, "连续频段", "L-SIM-KBL", 10, 10, 500, 250),
        _group("SIM-KBL-EG-AIR-VOICE", "SIM-KBL-TU-AIRLIFT", "指挥车", 6, "双工", "机动", 25, 25, 5, 6, -108, "仿真航空话音", "双工", 6, "离散信道", "AIR-SIM-KBL", 10, 8, 50, 25),
        _group("SIM-KBL-EG-COAL", "SIM-KBL-TU-COAL", "宽带自组网节点", 6, "双工", "机动", 3000, 10, 10, 5, -92, "OFDM", "双工", 4, "连续频段", "C-SIM-KBL", 8, 10, 1000, 500),
        _group("SIM-KBL-EG-SAT", "SIM-KBL-TU-COAL", "卫星通信终端", 3, "双工", "固定/机动", 4000, 5, 16, 3, -90, "仿真卫星波形", "双工", 3, "连续频段", "Ku-SIM-KBL", 8, 10, 1000, 1000),
        _group("SIM-KBL-EG-MED", "SIM-KBL-TU-MED", "手持终端", 24, "双工", "便携", 12.5, 4, 0, 1.5, -104, "数字窄带", "单工", 8, "共享信道", "VHF-SIM-KBL", 9, 2, 12.5, 12.5),
        _group("SIM-KBL-EG-SEC", "SIM-KBL-TU-SEC", "手持终端", 40, "双工", "便携", 12.5, 4, 0, 1.5, -104, "数字窄带", "单工", 12, "共享信道", "VHF-SIM-KBL", 8, 2, 12.5, 12.5),
        _group("SIM-KBL-EG-RELAY", "SIM-KBL-TU-RAMP", "中继设备", 3, "双工", "机动", 25, 25, 5, 8, -108, "数字窄带", "双工", 3, "收发频点对", "UHF-SIM-KBL", 9, 8, 100, 50),
    ]
    rules = [
        _rule("SIM-KBL-SR-AIR", "可用", "AIR-SIM-KBL", "独占", 620, 640, 25, 50, 50, 25, "指挥通信单元,数据链协同单元", "固定基站,指挥车", "合成航空协调频段池"),
        _rule("SIM-KBL-SR-VHF", "可用", "VHF-SIM-KBL", "可复用", 188, 194, 12.5, 25, 20, 12.5, "机动通信单元", "手持终端", "合成机场地面窄带池"),
        _rule("SIM-KBL-SR-UHF", "可用", "UHF-SIM-KBL", "可复用", 565, 585, 25, 50, 50, 25, "机动通信单元,指挥通信单元", "车载电台,中继设备,固定基站", "合成机场调度频段池"),
        _rule("SIM-KBL-SR-L", "可用", "L-SIM-KBL", "独占", 1740, 1770, 250, 2000, 50, 250, "数据链协同单元", "战术数据链终端", "合成空运数据链频段池"),
        _rule("SIM-KBL-SR-C", "可用", "C-SIM-KBL", "可复用", 4860, 4930, 1000, 5000, 30, 1000, "回传保障单元", "宽带自组网节点", "合成伙伴网关资源"),
        _rule("SIM-KBL-SR-KU", "可用", "Ku-SIM-KBL", "可复用", 15300, 15380, 1000, 5000, 20, 1000, "回传保障单元", "卫星通信终端", "合成跨洲回传资源"),
        _rule("SIM-KBL-SR-AIR-PROTECT", "保护", "AIR-SIM-KBL", "保护", 628, 629, 25, 25, 5, 100, "", "", "机场安全关键保护窗口仿真", "高"),
        _rule("SIM-KBL-SR-KU-FORBID", "禁用", "Ku-SIM-KBL", "禁用", 15332, 15340, 1000, 1000, 0, 1000, "", "", "卫星窗口临时受限仿真", "高"),
    ]
    return tasks, groups, rules


def _oir_cuas_records() -> tuple[list[dict], list[dict], list[dict]]:
    tasks = [
        _task("SIM-OIR-TU-Q50", "近程传感器扇区", "雷达探测单元", 4.00, 4.00, 10, 9, "独占", "L-SIM-OIR,S-SIM-OIR", 0.95),
        _task("SIM-OIR-TU-Q53", "中程传感器扇区", "雷达探测单元", 4.10, 4.04, 18, 10, "独占", "S-SIM-OIR,C-SIM-OIR", 0.98),
        _task("SIM-OIR-TU-Q64", "低空监视扇区", "雷达探测单元", 3.94, 4.12, 22, 10, "独占", "C-SIM-OIR,S-SIM-OIR", 0.98),
        _task("SIM-OIR-TU-FUSION", "基地防空融合节点", "指挥通信单元", 4.02, 4.06, 12, 10, "独占", "UHF-SIM-OIR,C-SIM-OIR", 1.00),
        _task("SIM-OIR-TU-MOBILE", "机动防护分队", "机动通信单元", 4.16, 3.96, 14, 8, "可复用", "VHF-SIM-OIR,UHF-SIM-OIR", 0.88),
        _task("SIM-OIR-TU-BH", "联合态势回传", "回传保障单元", 3.90, 3.94, 20, 9, "可复用", "C-SIM-OIR,Ku-SIM-OIR", 0.92),
    ]
    groups = [
        _group("SIM-OIR-EG-Q50", "SIM-OIR-TU-Q50", "近程警戒雷达", 3, "发射", "机动", 5000, 700, 22, 8, -82, "仿真脉冲", "单工", 2, "宽带连续频段", "L-SIM-OIR", 9, 18, 2000, 1000),
        _group("SIM-OIR-EG-Q53", "SIM-OIR-TU-Q53", "低空探测雷达", 2, "发射", "机动", 10000, 1500, 30, 12, -84, "仿真脉冲", "单工", 2, "宽带连续频段", "S-SIM-OIR", 10, 28, 3000, 1500),
        _group("SIM-OIR-EG-Q64", "SIM-OIR-TU-Q64", "跟踪类雷达仿真装备", 2, "发射", "固定", 12000, 1800, 32, 15, -86, "仿真脉冲多普勒", "单工", 2, "宽带连续频段", "C-SIM-OIR", 10, 32, 3000, 1500),
        _group("SIM-OIR-EG-FUSION", "SIM-OIR-TU-FUSION", "固定基站", 3, "双工", "固定", 50, 35, 8, 25, -110, "数字窄带", "双工", 4, "离散信道", "UHF-SIM-OIR", 10, 8, 100, 50),
        _group("SIM-OIR-EG-JDN", "SIM-OIR-TU-FUSION", "战术数据链终端", 8, "双工", "固定/机动", 1500, 20, 10, 8, -98, "仿真联合数据网", "双工", 6, "连续频段", "C-SIM-OIR", 10, 12, 1000, 500),
        _group("SIM-OIR-EG-MOBILE", "SIM-OIR-TU-MOBILE", "车载电台", 16, "双工", "机动", 25, 20, 3, 3, -106, "数字窄带", "单工", 8, "离散信道", "VHF-SIM-OIR", 8, 4, 50, 25),
        _group("SIM-OIR-EG-MOBILE-DATA", "SIM-OIR-TU-MOBILE", "宽带自组网节点", 6, "双工", "机动", 2000, 10, 8, 4, -94, "OFDM", "双工", 4, "连续频段", "S-SIM-OIR", 8, 8, 500, 250),
        _group("SIM-OIR-EG-BH", "SIM-OIR-TU-BH", "微波回传链路", 4, "双工", "固定", 5000, 3, 20, 18, -88, "QAM", "双工", 4, "连续频段", "C-SIM-OIR", 9, 14, 2000, 1000),
        _group("SIM-OIR-EG-SAT", "SIM-OIR-TU-BH", "卫星通信终端", 2, "双工", "固定/机动", 3500, 5, 16, 3, -90, "仿真卫星波形", "双工", 2, "连续频段", "Ku-SIM-OIR", 8, 10, 1000, 1000),
        _group("SIM-OIR-EG-MON", "SIM-OIR-TU-FUSION", "频谱侦察接收机", 4, "接收", "固定/机动", 2500, 0.5, 8, 6, -114, "宽带监测", "单工", 2, "连续频段", "S-SIM-OIR", 9, 12, 500, 250),
    ]
    rules = [
        _rule("SIM-OIR-SR-VHF", "可用", "VHF-SIM-OIR", "可复用", 196, 202, 12.5, 25, 30, 12.5, "机动通信单元", "车载电台", "合成机动防护窄带资源"),
        _rule("SIM-OIR-SR-UHF", "可用", "UHF-SIM-OIR", "独占", 590, 610, 25, 50, 50, 25, "指挥通信单元,机动通信单元", "固定基站,车载电台", "合成基地指挥资源"),
        _rule("SIM-OIR-SR-L", "可用", "L-SIM-OIR", "独占", 1780, 1810, 500, 8000, 1000, 500, "雷达探测单元", "近程警戒雷达", "合成近程传感器资源"),
        _rule("SIM-OIR-SR-S", "可用", "S-SIM-OIR", "独占", 2410, 2470, 500, 15000, 1800, 1000, "雷达探测单元,机动通信单元,指挥通信单元", "低空探测雷达,宽带自组网节点,频谱侦察接收机", "合成中程传感器与监测资源"),
        _rule("SIM-OIR-SR-C", "可用", "C-SIM-OIR", "独占", 4940, 5060, 1000, 20000, 2200, 1000, "雷达探测单元,指挥通信单元,回传保障单元", "跟踪类雷达仿真装备,战术数据链终端,微波回传链路", "合成跟踪、融合与回传资源"),
        _rule("SIM-OIR-SR-KU", "可用", "Ku-SIM-OIR", "可复用", 15400, 15480, 1000, 5000, 20, 1000, "回传保障单元", "卫星通信终端", "合成超视距回传资源"),
        _rule("SIM-OIR-SR-S-PROTECT", "保护", "S-SIM-OIR", "保护", 2430, 2436, 500, 500, 10, 1000, "", "", "友军传感器保护窗口仿真", "高"),
        _rule("SIM-OIR-SR-C-FORBID", "禁用", "C-SIM-OIR", "禁用", 5000, 5010, 1000, 1000, 0, 1000, "", "", "融合链路临时禁用窗口仿真", "高"),
    ]
    return tasks, groups, rules


def _red_sea_records() -> tuple[list[dict], list[dict], list[dict]]:
    tasks = [
        _task("SIM-RS-TU-RADAR", "舰载综合探测", "雷达探测单元", 6.00, 6.00, 35, 10, "独占", "S-SIM-RS,C-SIM-RS", 1.00),
        _task("SIM-RS-TU-C2", "海上防空指挥", "指挥通信单元", 6.04, 6.02, 20, 10, "独占", "UHF-SIM-RS,L-SIM-RS", 1.00),
        _task("SIM-RS-TU-COAL", "联盟数据交换", "数据链协同单元", 6.12, 6.08, 40, 9, "可复用", "L-SIM-RS,C-SIM-RS", 0.95),
        _task("SIM-RS-TU-MERCHANT", "商船协调通信", "机动通信单元", 5.94, 6.16, 45, 8, "可复用", "VHF-SIM-RS,UHF-SIM-RS", 0.90),
        _task("SIM-RS-TU-SAT", "远程回传保障", "回传保障单元", 6.18, 5.94, 50, 9, "可复用", "C-SIM-RS,Ku-SIM-RS", 0.95),
        _task("SIM-RS-TU-LOG", "海上持续保障", "机动通信单元", 5.88, 5.92, 35, 7, "可复用", "VHF-SIM-RS,UHF-SIM-RS", 0.82),
    ]
    groups = [
        _group("SIM-RS-EG-SEARCH", "SIM-RS-TU-RADAR", "低空探测雷达", 2, "发射", "舰载", 15000, 1800, 34, 20, -86, "仿真多任务雷达", "单工", 2, "宽带连续频段", "S-SIM-RS", 10, 35, 3000, 1500),
        _group("SIM-RS-EG-TRACK", "SIM-RS-TU-RADAR", "跟踪类雷达仿真装备", 2, "发射", "舰载", 12000, 1600, 32, 18, -85, "仿真跟踪波形", "单工", 2, "宽带连续频段", "C-SIM-RS", 10, 30, 3000, 1500),
        _group("SIM-RS-EG-C2", "SIM-RS-TU-C2", "固定基站", 3, "双工", "舰载", 50, 35, 8, 20, -110, "数字窄带", "双工", 4, "离散信道", "UHF-SIM-RS", 10, 10, 100, 50),
        _group("SIM-RS-EG-C2-DATA", "SIM-RS-TU-C2", "战术数据链终端", 8, "双工", "舰载/空中", 1500, 20, 10, 8, -98, "仿真联合数据链", "双工", 6, "连续频段", "L-SIM-RS", 10, 14, 1000, 500),
        _group("SIM-RS-EG-COAL", "SIM-RS-TU-COAL", "战术数据链终端", 10, "双工", "舰载/空中", 1000, 15, 9, 6, -98, "仿真联盟数据链", "双工", 8, "连续频段", "L-SIM-RS", 9, 16, 500, 250),
        _group("SIM-RS-EG-GW", "SIM-RS-TU-COAL", "宽带自组网节点", 5, "双工", "舰载", 3000, 10, 12, 12, -92, "OFDM", "双工", 4, "连续频段", "C-SIM-RS", 9, 14, 1000, 500),
        _group("SIM-RS-EG-MERCHANT", "SIM-RS-TU-MERCHANT", "车载电台", 24, "双工", "舰载", 25, 15, 3, 8, -105, "仿真海事话音", "单工", 12, "共享信道", "VHF-SIM-RS", 8, 8, 50, 25),
        _group("SIM-RS-EG-SAT", "SIM-RS-TU-SAT", "卫星通信终端", 4, "双工", "舰载", 5000, 8, 20, 12, -90, "仿真卫星波形", "双工", 4, "连续频段", "Ku-SIM-RS", 9, 14, 2000, 1000),
        _group("SIM-RS-EG-BH", "SIM-RS-TU-SAT", "微波回传链路", 4, "双工", "舰载", 4000, 4, 18, 14, -88, "QAM", "双工", 3, "连续频段", "C-SIM-RS", 8, 12, 2000, 1000),
        _group("SIM-RS-EG-LOG", "SIM-RS-TU-LOG", "手持终端", 30, "双工", "便携", 12.5, 4, 0, 1.5, -104, "数字窄带", "单工", 10, "共享信道", "UHF-SIM-RS", 7, 3, 25, 12.5),
    ]
    rules = [
        _rule("SIM-RS-SR-VHF", "可用", "VHF-SIM-RS", "可复用", 204, 210, 12.5, 25, 30, 12.5, "机动通信单元", "车载电台", "合成商船协调资源"),
        _rule("SIM-RS-SR-UHF", "可用", "UHF-SIM-RS", "可复用", 640, 662, 25, 50, 50, 25, "指挥通信单元,机动通信单元", "固定基站,手持终端", "合成舰内与保障资源"),
        _rule("SIM-RS-SR-L", "可用", "L-SIM-RS", "独占", 1820, 1860, 250, 3000, 50, 250, "指挥通信单元,数据链协同单元", "战术数据链终端", "合成联合数据交换资源"),
        _rule("SIM-RS-SR-S", "可用", "S-SIM-RS", "独占", 2480, 2550, 1000, 20000, 2200, 1500, "雷达探测单元", "低空探测雷达", "合成舰载搜索资源"),
        _rule("SIM-RS-SR-C", "可用", "C-SIM-RS", "独占", 5080, 5210, 1000, 20000, 2200, 1000, "雷达探测单元,数据链协同单元,回传保障单元", "跟踪类雷达仿真装备,宽带自组网节点,微波回传链路", "合成跟踪、网关和回传资源"),
        _rule("SIM-RS-SR-KU", "可用", "Ku-SIM-RS", "可复用", 15500, 15600, 1000, 6000, 25, 1000, "回传保障单元", "卫星通信终端", "合成远程卫星回传资源"),
        _rule("SIM-RS-SR-C-PROTECT", "保护", "C-SIM-RS", "保护", 5140, 5148, 1000, 1000, 10, 2000, "", "", "联盟传感器保护窗口仿真", "高"),
        _rule("SIM-RS-SR-KU-FORBID", "禁用", "Ku-SIM-RS", "禁用", 15545, 15555, 1000, 1000, 0, 1000, "", "", "远程回传窗口受限仿真", "高"),
    ]
    return tasks, groups, rules

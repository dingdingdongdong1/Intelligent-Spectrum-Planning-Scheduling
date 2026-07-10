"""Static catalog data for task and equipment planning."""

from __future__ import annotations

TASK_OBJECTIVES = [
    {
        "objective": "task_assurance",
        "label": "任务保障优先",
        "description": "优先满足任务单元最低保障率，高优先级任务先分配。",
    },
    {
        "objective": "minimize_interference",
        "label": "干扰最低",
        "description": "优先降低同频复用、保护频率靠近和高功率近距离风险。",
    },
    {
        "objective": "minimize_bandwidth",
        "label": "占用带宽最小",
        "description": "优先压缩连续频段和离散信道数量。",
    },
    {
        "objective": "priority_equipment",
        "label": "高优先级装备优先",
        "description": "高优先级装备组优先获得完整指配。",
    },
    {
        "objective": "radar_priority",
        "label": "雷达优先保障",
        "description": "优先保障近程警戒、低空探测和跟踪类雷达的连续宽带窗口。",
    },
    {
        "objective": "uav_link_priority",
        "label": "无人机链路优先",
        "description": "优先满足无人机遥控、数传和高清视频链路。",
    },
    {
        "objective": "communication_continuity",
        "label": "通信连续性优先",
        "description": "优先保证指挥通信、机动通信、中继和数据链的连续可用。",
    },
    {
        "objective": "ew_isolation_priority",
        "label": "电子对抗隔离优先",
        "description": "优先隔离电子压制、诱骗干扰和高功率发射装备。",
    },
    {
        "objective": "minimize_switching",
        "label": "最少频段切换",
        "description": "优先沿用装备首选频段和锁定资源，降低重规划切换代价。",
    },
    {
        "objective": "maximize_reuse_efficiency",
        "label": "最大复用效率",
        "description": "优先复用低功率、共享型和可复用任务单元资源，提高频谱利用率。",
    },
]

TRIAL_METRIC_KEYS = (
    "task_satisfaction_avg",
    "quality_total",
    "risk_item_count",
    "high_risk_count",
    "medium_risk_count",
    "partial_group_count",
    "unsatisfied_group_count",
    "used_bandwidth_mhz",
)

TRIAL_METRIC_LABELS = {
    "task_satisfaction_avg": "保障率",
    "quality_total": "质量分",
    "risk_item_count": "风险总数",
    "high_risk_count": "高风险",
    "medium_risk_count": "中风险",
    "partial_group_count": "部分满足",
    "unsatisfied_group_count": "未满足",
    "used_bandwidth_mhz": "占用带宽",
}


EQUIPMENT_LIBRARY = [
    {
        "equipment_type": "手持终端",
        "default_assignment_mode": "共享信道",
        "reasonable_bandwidth_khz": "12.5-25",
        "reasonable_power_w": "2-5",
        "typical_mobility": "便携",
        "planning_notes": "适合共享窄带信道，优先保证覆盖和复用距离。",
    },
    {
        "equipment_type": "车载电台",
        "default_assignment_mode": "离散信道",
        "reasonable_bandwidth_khz": "25-50",
        "reasonable_power_w": "20-50",
        "typical_mobility": "机动",
        "planning_notes": "适合按任务单元分配离散信道，高功率近距离复用需加保护距离。",
    },
    {
        "equipment_type": "固定基站",
        "default_assignment_mode": "离散信道",
        "reasonable_bandwidth_khz": "25-50",
        "reasonable_power_w": "30-80",
        "typical_mobility": "固定",
        "planning_notes": "优先稳定指配，可作为锁定频点对象。",
    },
    {
        "equipment_type": "中继设备",
        "default_assignment_mode": "收发频点对",
        "reasonable_bandwidth_khz": "25-50",
        "reasonable_power_w": "25-60",
        "typical_mobility": "固定/机动",
        "planning_notes": "需要成对频点，收发间隔和保护距离优先级高。",
    },
    {
        "equipment_type": "无人机遥控链路",
        "default_assignment_mode": "离散信道",
        "reasonable_bandwidth_khz": "100-500",
        "reasonable_power_w": "2-10",
        "typical_mobility": "空中机动",
        "planning_notes": "优先保障链路连续性，避免靠近保护频率。",
    },
    {
        "equipment_type": "无人机数传链路",
        "default_assignment_mode": "连续频段",
        "reasonable_bandwidth_khz": "500-2000",
        "reasonable_power_w": "5-20",
        "typical_mobility": "空中机动",
        "planning_notes": "需要连续带宽，保护频率会显著切分可用窗口。",
    },
    {
        "equipment_type": "微波回传链路",
        "default_assignment_mode": "连续频段",
        "reasonable_bandwidth_khz": "2000-10000",
        "reasonable_power_w": "1-10",
        "typical_mobility": "固定",
        "planning_notes": "以连续带宽和链路稳定为主，可在多方案中压缩总占用。",
    },
    {
        "equipment_type": "卫星通信终端",
        "default_assignment_mode": "连续频段",
        "reasonable_bandwidth_khz": "1000-5000",
        "reasonable_power_w": "2-20",
        "typical_mobility": "机动/固定",
        "planning_notes": "适合独立频段池，需避开保护窗口。",
    },
    {
        "equipment_type": "近程警戒雷达",
        "default_assignment_mode": "宽带连续频段",
        "reasonable_bandwidth_khz": "5000-15000",
        "reasonable_power_w": "500-2000",
        "typical_mobility": "固定/机动",
        "planning_notes": "宽带连续需求强，允许部分满足时应给出牺牲理由。",
    },
    {
        "equipment_type": "低空探测雷达",
        "default_assignment_mode": "宽带连续频段",
        "reasonable_bandwidth_khz": "10000-30000",
        "reasonable_power_w": "1000-3000",
        "typical_mobility": "固定",
        "planning_notes": "优先检查连续窗口是否被保护/禁用频率切断。",
    },
    {
        "equipment_type": "战术数据链终端",
        "default_assignment_mode": "连续频段",
        "reasonable_bandwidth_khz": "500-1500",
        "reasonable_power_w": "10-40",
        "typical_mobility": "机动/空中",
        "planning_notes": "适合按任务单元保障连续窄宽带窗口，需控制与无人机链路的邻频关系。",
    },
    {
        "equipment_type": "宽带自组网节点",
        "default_assignment_mode": "连续频段",
        "reasonable_bandwidth_khz": "1000-5000",
        "reasonable_power_w": "5-30",
        "typical_mobility": "机动",
        "planning_notes": "适合应急宽带接入和移动中继，优先使用 L/S 备用频段池。",
    },
    {
        "equipment_type": "导航授时终端",
        "default_assignment_mode": "离散信道",
        "reasonable_bandwidth_khz": "50-200",
        "reasonable_power_w": "1-5",
        "typical_mobility": "便携/车载",
        "planning_notes": "低功率、窄带、保护优先级高，规划时应避开保护窗口并保证冗余信道。",
    },
    {
        "equipment_type": "频谱侦察接收机",
        "default_assignment_mode": "连续频段",
        "reasonable_bandwidth_khz": "1000-5000",
        "reasonable_power_w": "0.1-1",
        "typical_mobility": "固定/机动",
        "planning_notes": "以接收监视窗口为主，可复用但需避免被高功率发射装备近距离压制。",
    },
    {
        "equipment_type": "被动测向站",
        "default_assignment_mode": "连续频段",
        "reasonable_bandwidth_khz": "500-3000",
        "reasonable_power_w": "0.1-1",
        "typical_mobility": "固定",
        "planning_notes": "通常成组部署，适合与侦察接收频段合并规划，重点看保护距离和覆盖分布。",
    },
    {
        "equipment_type": "电子压制设备",
        "default_assignment_mode": "连续频段",
        "reasonable_bandwidth_khz": "1000-5000",
        "reasonable_power_w": "50-250",
        "typical_mobility": "机动",
        "planning_notes": "高功率连续窗口需求明显，必须与通信、导航和无人机链路保持明确隔离。",
    },
    {
        "equipment_type": "诱骗干扰设备",
        "default_assignment_mode": "离散信道",
        "reasonable_bandwidth_khz": "200-1000",
        "reasonable_power_w": "20-100",
        "typical_mobility": "机动",
        "planning_notes": "适合离散频点或窄连续窗口，规划时应给出与保护频率的隔离说明。",
    },
]


TASK_SCENARIOS = [
    {
        "key": "baseline",
        "name": "高密度联合作战基线",
        "description": "通信、无人机、雷达、回传、导航授时和电磁仿真任务并发，突出频谱资源紧缺和智能规划增效。",
    },
    {
        "key": "urban_dense",
        "name": "城区密集机动",
        "description": "手持和车载装备数量增加，VHF/UHF 复用压力更高。",
    },
    {
        "key": "uav_priority",
        "name": "无人机侦察优先",
        "description": "无人机控制和数传链路优先级提升，并加入高清视频链路需求。",
    },
    {
        "key": "radar_priority",
        "name": "雷达探测优先",
        "description": "雷达任务保障率和优先级提升，连续宽带窗口约束更紧。",
    },
    {
        "key": "backhaul_limited",
        "name": "回传频段受限",
        "description": "C/Ku 回传频段加入额外禁用和保护窗口，验证不可行解释。",
    },
    {
        "key": "high_protection_density",
        "name": "保护频率密集",
        "description": "多个频段加入额外保护窗口，突出避让和重规划能力。",
    },
    {
        "key": "large_joint_exercise",
        "name": "大型联合演训",
        "description": "18 个任务单元、70 余个装备组、1500 余台套仿真装备，用于验证中等规模规划效果。",
    },
    {
        "key": "stress_performance",
        "name": "压力效能测试",
        "description": "36 个任务单元、150 余个装备组、3500 余台套仿真装备，用于观察求解耗时和瓶颈。",
    },
]

SAMPLE_GENERATOR_PRESETS = [
    {
        "key": "compact",
        "name": "高密度默认",
        "scenario": "baseline",
        "task_unit_count": 12,
        "density_multiplier": 1.6,
        "spectrum_pressure": "高",
        "description": "用于默认加载高密度联合作战输入，观察频谱紧缺下的保障率、冲突和带宽占用变化。",
    },
    {
        "key": "joint_large",
        "name": "联合演训",
        "scenario": "large_joint_exercise",
        "task_unit_count": 18,
        "density_multiplier": 1.85,
        "spectrum_pressure": "中",
        "description": "覆盖通信、无人机、回传、雷达、数据链、导航授时、侦察和电子对抗。",
    },
    {
        "key": "stress_36",
        "name": "压力 36 单元",
        "scenario": "stress_performance",
        "task_unit_count": 36,
        "density_multiplier": 2.4,
        "spectrum_pressure": "高",
        "description": "用于观察高密度装备和保护/禁用窗口叠加后的规划效能。",
    },
]

BATCH_PERFORMANCE_SCALES = [
    {"key": "s12", "name": "12 单元默认", "scenario": "baseline", "unit_count": 12, "density_multiplier": 1.6},
    {"key": "s18", "name": "18 单元", "prefix": "B18", "unit_count": 18, "density_multiplier": 1.85},
    {"key": "s24", "name": "24 单元", "prefix": "B24", "unit_count": 24, "density_multiplier": 2.05},
    {"key": "s36", "name": "36 单元", "prefix": "B36", "unit_count": 36, "density_multiplier": 2.4},
]

PLANNING_WEIGHT_TEMPLATES = [
    {
        "key": "balanced",
        "name": "均衡权重",
        "weights": {"task": 85, "risk": 75, "spectrum": 65, "priority": 80, "switching": 35, "reuse": 70},
        "description": "面向高密度联合作战默认输入，优先保障关键任务，同时压缩频谱占用并提升复用效率。",
    },
    {
        "key": "risk_first",
        "name": "风险最低",
        "weights": {"task": 65, "risk": 95, "spectrum": 45, "priority": 60, "switching": 25, "reuse": 30},
        "description": "保护频率、复用距离和高功率干扰权重最高。",
    },
    {
        "key": "task_first",
        "name": "任务保障",
        "weights": {"task": 95, "risk": 65, "spectrum": 35, "priority": 85, "switching": 30, "reuse": 35},
        "description": "优先保证高优先级任务和装备组满足率。",
    },
    {
        "key": "spectrum_saving",
        "name": "频谱节约",
        "weights": {"task": 65, "risk": 55, "spectrum": 95, "priority": 55, "switching": 35, "reuse": 70},
        "description": "减少总占用带宽并提高可复用资源利用。",
    },
    {
        "key": "minimum_change",
        "name": "最小调整",
        "weights": {"task": 70, "risk": 60, "spectrum": 45, "priority": 60, "switching": 95, "reuse": 35},
        "description": "尽量沿用首选频段和已锁定资源，适合重规划。",
    },
]

PARAMETRIC_SAMPLE_DEFAULTS = {
    "unit_count": 24,
    "density_multiplier": 2.1,
    "radar_ratio": 22,
    "uav_ratio": 24,
    "protection_density": 3,
    "forbidden_density": 3,
}

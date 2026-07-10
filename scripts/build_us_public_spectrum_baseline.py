from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo


OUTPUT = Path("docs/research/us_public_battle_spectrum_baseline.xlsx")


BATTLE_CASES = [
    {
        "case_id": "CASE-DS-1991",
        "operation": "Operation Desert Shield / Desert Storm",
        "year_range": "1990-1991",
        "mission_type": "联合地面机动、航空支援、指挥控制、火力协同",
        "spectrum_dependent_tasks": "地面战斗网话音；航空空空/空地通信；跨网指挥；抗干扰通信",
        "public_systems": "SINCGARS；安全FM；UHF航空通信；VHF/FM航空通信",
        "observed_issue_or_result": "SINCGARS公开资料称在西南亚环境表现良好；Apache事件调查显示空地无线电域存在互通边界。",
        "planning_requirements": "多频段装备建模；空地兼容性；跨网网关；备用链路；距离与优先级约束",
        "parameter_disclosure": "系统级参数公开；行动实际频道未公开",
        "confidence": "高",
        "source_org": "U.S. Army / GAO",
        "source_title": "1992 Weapon Systems Handbook; Operation Desert Storm: Apache Helicopter Fratricide Incident",
        "source_url": "https://asc.army.mil/docs/wsh2/1992-wsh.pdf | https://www.gao.gov/assets/osi-93-4.pdf",
        "evidence_note": "不能将调查中披露的无线电类别解释为事故唯一原因。",
    },
    {
        "case_id": "CASE-OAF-1999",
        "operation": "Operation Allied Force / Task Force Hawk",
        "year_range": "1999",
        "mission_type": "Apache深袭特遣部队支援联合空中战役",
        "spectrum_dependent_tasks": "陆空协同；C4I互操作；共同态势信息交换",
        "public_systems": "报告未在公开摘要中披露具体电台和频道",
        "observed_issue_or_result": "GAO确认陆军和空军在联合作战及C4I装备互操作方面存在显著问题。",
        "planning_requirements": "通信链路实体；跨军种网关；互操作覆盖率；共同态势数据可达性",
        "parameter_disclosure": "任务与问题公开；频率参数未公开",
        "confidence": "高",
        "source_org": "GAO",
        "source_title": "GAO-01-401 Kosovo Air Operations",
        "source_url": "https://www.gao.gov/products/gao-01-401",
        "evidence_note": "不得用Link 16等系统通用频段冒充Task Force Hawk实际频道。",
    },
    {
        "case_id": "CASE-OEF-2001",
        "operation": "Operation Enduring Freedom",
        "year_range": "2001起",
        "mission_type": "山地远距离作战、分散节点指挥、ISR与超视距通信",
        "spectrum_dependent_tasks": "超视距指挥；战术卫星通信；地面视距通信；ISR数据传输",
        "public_systems": "UHF TACSAT；MSE/JNN/WIN-T演进背景",
        "observed_issue_or_result": "山地环境限制视距FM通信；OEF推动超视距网络需求。",
        "planning_requirements": "视距可达性；地形遮挡等级；卫星/HF备用链路；关键任务多链路保障",
        "parameter_disclosure": "业务频段类别公开；行动频道未公开",
        "confidence": "中高",
        "source_org": "U.S. Army",
        "source_title": "WIN-T: It's real, it's here and it works; High-Frequency Communications",
        "source_url": "https://www.army.mil/article/25076/warfighter_information_network_tactical_its_real_its_here_and_it_works | https://www.lineofdeparture.army.mil/Journals/Field-Artillery/Field-Artillery-Archive/Field-Artillery-2025-E-Edition/High-Frequency-Communications/",
        "evidence_note": "UHF在公开文章中仅按300 MHz-3 GHz类别描述，不等于具体TACSAT频道。",
    },
    {
        "case_id": "CASE-OIF-2003",
        "operation": "Operation Iraqi Freedom",
        "year_range": "2003起",
        "mission_type": "高速地面推进、机动指挥、宽带态势共享",
        "spectrum_dependent_tasks": "超视距骨干；指挥所宽带；行进间通信；共同态势图",
        "public_systems": "MSE；JNN；WIN-T；卫星与地面网络",
        "observed_issue_or_result": "进攻速度超过原MSE视距网络通信能力，推动JNN/WIN-T超视距网络。",
        "planning_requirements": "作战阶段与时段；机动速度；建链/撤收时间；行进间能力；链路切换代价",
        "parameter_disclosure": "架构和能力公开；行动频道未公开",
        "confidence": "高",
        "source_org": "U.S. Army / GAO",
        "source_title": "WIN-T: It's real, it's here and it works; GAO-04-547 Military Operations",
        "source_url": "https://www.army.mil/article/25076/warfighter_information_network_tactical_its_real_its_here_and_it_works | https://www.gao.gov/products/gao-04-547",
        "evidence_note": "公开证据支持能力缺口，不提供战术网络初始化数据。",
    },
    {
        "case_id": "CASE-UAS-2001-07",
        "operation": "Iraq/Afghanistan UAS Operations",
        "year_range": "2001-2007",
        "mission_type": "无人机飞控、ISR载荷数据回传、实时视频、时敏目标支持",
        "spectrum_dependent_tasks": "飞行控制链路；载荷数据链路；卫星/视距回传；空域协同",
        "public_systems": "多型UAS使用C band或Ku band；Common Data Link改进方向",
        "observed_issue_or_result": "频谱拥塞、互操作和带宽约束导致部分任务延迟；载荷数据需求高于飞控。",
        "planning_requirements": "飞控与载荷链路拆分；带宽需求；同时在线数量；频段重构；拥塞事件动态重筹",
        "parameter_disclosure": "频段类别公开；行动具体频率未公开",
        "confidence": "高",
        "source_org": "GAO",
        "source_title": "GAO-06-49; GAO-07-836 Unmanned Aircraft Systems",
        "source_url": "https://www.gao.gov/products/gao-06-49 | https://www.gao.gov/products/gao-07-836",
        "evidence_note": "数值频率保持为空；不使用IEEE通用波段边界替代战例事实。",
    },
]


PUBLIC_PARAMETERS = [
    {
        "parameter_id": "PAR-SINCGARS",
        "system_or_service": "SINCGARS",
        "mission_role": "地面战斗网指挥控制",
        "case_links": "CASE-DS-1991",
        "frequency_start_mhz": 30.0,
        "frequency_end_mhz": 87.975,
        "center_frequency_mhz": None,
        "channel_step_khz": 25.0,
        "occupied_bandwidth_khz": None,
        "power_w": None,
        "channel_count": 2320,
        "range_km": "8-35",
        "waveform_or_access": "单信道/跳频能力；ECCM",
        "mobility": "背负、车载、机载",
        "assignment_mode": "离散频道",
        "planning_relation": "战斗网；按任务和网系分配",
        "parameter_status": "公开精确范围",
        "confidence": "高",
        "source_org": "U.S. Army",
        "source_title": "1992 Weapon Systems Handbook",
        "source_url": "https://asc.army.mil/docs/wsh2/1992-wsh.pdf",
        "evidence_note": "25 kHz步进与公开端点及2320个等间隔频道一致；不同型号功率未统一。",
        "usage_boundary": "系统调谐范围，不是行动实际频道，不得直接标记为可用频段。",
    },
    {
        "parameter_id": "PAR-MIL-AIR-VOICE",
        "system_or_service": "军用航空空地话音参考",
        "mission_role": "军机空地/空空话音和空管协调",
        "case_links": "CASE-DS-1991; CASE-OAF-1999",
        "frequency_start_mhz": 225.0,
        "frequency_end_mhz": 399.9,
        "center_frequency_mhz": None,
        "channel_step_khz": 25.0,
        "occupied_bandwidth_khz": 6.0,
        "power_w": "10-50",
        "channel_count": 471,
        "range_km": None,
        "waveform_or_access": "公开规划资料未统一给出；按航空话音业务建模",
        "mobility": "机载/地面站",
        "assignment_mode": "离散频道",
        "planning_relation": "航空业务，需空地互操作",
        "parameter_status": "公开业务规划范围",
        "confidence": "中高",
        "source_org": "U.S. Department of Transportation / NTIA",
        "source_title": "Transportation Strategic Spectrum Plan",
        "source_url": "https://www.ntia.gov/sites/default/files/publications/transportation_strategic_spectrum_plan_nov2007_0.pdf",
        "evidence_note": "公开资料说明排除326.6-335.4 MHz；471频道是ATS规划口径。",
        "usage_boundary": "美国境内规划资料，不代表海外战例授权。",
    },
    {
        "parameter_id": "PAR-EPLRS",
        "system_or_service": "EPLRS/AEPLRS",
        "mission_role": "战术位置报告、数据分发、态势感知",
        "case_links": "CASE-OAF-1999; CASE-OIF-2003",
        "frequency_start_mhz": 420.0,
        "frequency_end_mhz": 450.0,
        "center_frequency_mhz": None,
        "channel_step_khz": None,
        "occupied_bandwidth_khz": None,
        "power_w": None,
        "channel_count": None,
        "range_km": "公开报告仅称支持短程和长程",
        "waveform_or_access": "TDMA；跳频扩频；多跳",
        "mobility": "地面、舰载、机载",
        "assignment_mode": "网络化跳频资源",
        "planning_relation": "位置报告和战术数据网络",
        "parameter_status": "公开精确范围",
        "confidence": "高",
        "source_org": "NTIA",
        "source_title": "420-450 MHz Federal Spectrum Use Report",
        "source_url": "https://www.ntia.gov/files/ntia/publications/compendium/0420.00-0450.00_01MAY15.pdf",
        "evidence_note": "报告明确EPLRS/AEPLRS用途和波形类别。",
        "usage_boundary": "公共系统频段，实际网络参数和跳频表未公开。",
    },
    {
        "parameter_id": "PAR-LINK16",
        "system_or_service": "JTIDS/MIDS / Link 16",
        "mission_role": "联合战术数据、语音和态势感知",
        "case_links": "CASE-OAF-1999; CASE-OIF-2003",
        "frequency_start_mhz": 960.0,
        "frequency_end_mhz": 1164.0,
        "center_frequency_mhz": None,
        "channel_step_khz": None,
        "occupied_bandwidth_khz": None,
        "power_w": None,
        "channel_count": 51,
        "range_km": "视距",
        "waveform_or_access": "扩频跳频；TDMA类多址；内部加密",
        "mobility": "机载、舰载、地面",
        "assignment_mode": "51个离散频率上的网络化时隙",
        "planning_relation": "联合数据链，需与航空导航业务协调",
        "parameter_status": "公开精确范围",
        "confidence": "高",
        "source_org": "NTIA / U.S. Army",
        "source_title": "1164-1215 MHz Federal Spectrum Use Report; FM 3-01",
        "source_url": "https://www.ntia.gov/files/ntia/publications/compendium/1164.00-1215.00_01MAR14.pdf | https://rdl.train.army.mil/catalog-ws/view/100.ATSC/C01CC9C1-DA1C-4D5E-A6EB-5FCFAE218DCD-1398170439966/fm3_01.pdf",
        "evidence_note": "FM 3-01公开数据率超过50 kbit/s和51个离散频率；NTIA明确960-1164 MHz边界。",
        "usage_boundary": "不收录网络号、时隙分配、密钥或脉冲去冲突参数。",
    },
    {
        "parameter_id": "PAR-GPS-L5",
        "system_or_service": "GPS L5",
        "mission_role": "定位、导航和授时保护对象",
        "case_links": "CASE-OEF-2001; CASE-OIF-2003",
        "frequency_start_mhz": None,
        "frequency_end_mhz": None,
        "center_frequency_mhz": 1176.45,
        "channel_step_khz": None,
        "occupied_bandwidth_khz": 24000,
        "power_w": None,
        "channel_count": None,
        "range_km": "全球覆盖（接收）",
        "waveform_or_access": "RNSS接收信号",
        "mobility": "各类接收平台",
        "assignment_mode": "中心频率保护",
        "planning_relation": "保护频率/敏感接收业务",
        "parameter_status": "公开中心频率",
        "confidence": "高",
        "source_org": "NTIA",
        "source_title": "1164-1215 MHz Federal Spectrum Use Report",
        "source_url": "https://www.ntia.gov/files/ntia/publications/compendium/1164.00-1215.00_01MAR14.pdf",
        "evidence_note": "NTIA说明L5位于1176.45±12 MHz。",
        "usage_boundary": "用于仿真保护窗口，不代表接收机抗干扰门限。",
    },
    {
        "parameter_id": "PAR-GPS-L2",
        "system_or_service": "GPS L2",
        "mission_role": "定位、导航和授时保护对象",
        "case_links": "CASE-OEF-2001; CASE-OIF-2003",
        "frequency_start_mhz": None,
        "frequency_end_mhz": None,
        "center_frequency_mhz": 1227.60,
        "channel_step_khz": None,
        "occupied_bandwidth_khz": None,
        "power_w": None,
        "channel_count": None,
        "range_km": "全球覆盖（接收）",
        "waveform_or_access": "RNSS接收信号",
        "mobility": "各类接收平台",
        "assignment_mode": "中心频率保护",
        "planning_relation": "保护频率/敏感接收业务",
        "parameter_status": "公开中心频率",
        "confidence": "高",
        "source_org": "NTIA",
        "source_title": "1164-1215 MHz Federal Spectrum Use Report",
        "source_url": "https://www.ntia.gov/files/ntia/publications/compendium/1164.00-1215.00_01MAR14.pdf",
        "evidence_note": "NTIA公开L2中心频率。",
        "usage_boundary": "不得推定军用码型、功率或抗干扰参数。",
    },
    {
        "parameter_id": "PAR-GPS-L1",
        "system_or_service": "GPS L1",
        "mission_role": "定位、导航和授时保护对象",
        "case_links": "CASE-OEF-2001; CASE-OIF-2003",
        "frequency_start_mhz": None,
        "frequency_end_mhz": None,
        "center_frequency_mhz": 1575.42,
        "channel_step_khz": None,
        "occupied_bandwidth_khz": None,
        "power_w": None,
        "channel_count": None,
        "range_km": "全球覆盖（接收）",
        "waveform_or_access": "RNSS接收信号",
        "mobility": "各类接收平台",
        "assignment_mode": "中心频率保护",
        "planning_relation": "保护频率/敏感接收业务",
        "parameter_status": "公开中心频率",
        "confidence": "高",
        "source_org": "NTIA",
        "source_title": "1164-1215 MHz Federal Spectrum Use Report",
        "source_url": "https://www.ntia.gov/files/ntia/publications/compendium/1164.00-1215.00_01MAR14.pdf",
        "evidence_note": "NTIA公开L1中心频率。",
        "usage_boundary": "不得推定军用码型、功率或抗干扰参数。",
    },
    {
        "parameter_id": "PAR-UAS-C-KU",
        "system_or_service": "UAS飞控/载荷链路（公开类别）",
        "mission_role": "无人机飞控、传感器数据和视频回传",
        "case_links": "CASE-UAS-2001-07",
        "frequency_start_mhz": None,
        "frequency_end_mhz": None,
        "center_frequency_mhz": None,
        "channel_step_khz": None,
        "occupied_bandwidth_khz": None,
        "power_w": None,
        "channel_count": None,
        "range_km": None,
        "waveform_or_access": "C band / Ku band；具体波形未在GAO摘要公开",
        "mobility": "空中平台/地面控制站",
        "assignment_mode": "飞控与载荷链路分开规划",
        "planning_relation": "高带宽载荷链路与高可靠飞控链路竞争资源",
        "parameter_status": "仅公开频段类别",
        "confidence": "高",
        "source_org": "GAO",
        "source_title": "GAO-06-49 Unmanned Aircraft Systems",
        "source_url": "https://www.gao.gov/products/gao-06-49",
        "evidence_note": "GAO统计12类UAS中C/Ku频段使用情况，并记录拥塞导致任务延迟。",
        "usage_boundary": "数值频率必须保持为空，不能用通用波段定义替代行动数据。",
    },
    {
        "parameter_id": "PAR-TRR-4400",
        "system_or_service": "战术无线电中继研究参考",
        "mission_role": "战术中继、固定/可搬移数据链",
        "case_links": "CASE-OIF-2003",
        "frequency_start_mhz": 4400.0,
        "frequency_end_mhz": 4940.0,
        "center_frequency_mhz": None,
        "channel_step_khz": None,
        "occupied_bandwidth_khz": None,
        "power_w": None,
        "channel_count": None,
        "range_km": None,
        "waveform_or_access": "公开评估未给统一波形",
        "mobility": "可搬移/固定中继",
        "assignment_mode": "连续频段/中继链路",
        "planning_relation": "与CEC、雷达及其他系统共存研究",
        "parameter_status": "公开评估范围",
        "confidence": "中",
        "source_org": "DoD / NTIA",
        "source_title": "DoD 4400-4940 MHz Band Assessment",
        "source_url": "https://www.ntia.gov/sites/default/files/publications/dodassessment_0.pdf",
        "evidence_note": "属于频谱迁移和共存评估，不证明某次战役实际使用该范围。",
        "usage_boundary": "仅供冲突研究，不得直接转成可用规则。",
    },
    {
        "parameter_id": "PAR-RADAR-TPQ53",
        "system_or_service": "AN/TPQ-53反炮兵雷达",
        "mission_role": "迫击炮、火炮和火箭弹探测、分类及发射点定位",
        "case_links": "",
        "frequency_start_mhz": 2000.0,
        "frequency_end_mhz": 4000.0,
        "center_frequency_mhz": None,
        "channel_step_khz": None,
        "occupied_bandwidth_khz": None,
        "power_w": None,
        "channel_count": None,
        "range_km": "90度模式：火箭60、火炮34、迫击炮20；360度模式：20",
        "waveform_or_access": "S波段有源相控阵；具体波形未公开",
        "mobility": "高机动、可部署雷达",
        "assignment_mode": "雷达调谐范围/时段占用",
        "planning_relation": "高优先级雷达发射；需要时空保护和同址兼容",
        "parameter_status": "公开波段与能力范围",
        "confidence": "中高",
        "source_org": "U.S. Army ODIN",
        "source_title": "AN/TPQ-53 Counterfire Target Acquisition Radar",
        "source_url": "https://odin.t2com.army.mil/WEG/Asset/6ea3c7edc1d7b3bab022f375761f3ee6",
        "evidence_note": "ODIN公开2-4 GHz和不同工作模式的最大覆盖距离；未将60 kW电源功率误作射频发射功率。",
        "usage_boundary": "宽波段装备能力记录，不代表战时调谐点、脉冲参数或部署位置。",
    },
    {
        "parameter_id": "PAR-RADAR-SENTINEL",
        "system_or_service": "AN/MPQ-64 Sentinel",
        "mission_role": "低空空情、无人机、巡航导弹及固定/旋翼机监视",
        "case_links": "",
        "frequency_start_mhz": None,
        "frequency_end_mhz": None,
        "center_frequency_mhz": None,
        "channel_step_khz": None,
        "occupied_bandwidth_khz": None,
        "power_w": None,
        "channel_count": None,
        "range_km": "75",
        "waveform_or_access": "三维X波段相控阵；具体频率和波形未公开",
        "mobility": "车载/拖车式、两人操作",
        "assignment_mode": "雷达波段/时段占用",
        "planning_relation": "持续空情监视；与数据链和防空指挥系统协同",
        "parameter_status": "仅公开频段类别和覆盖距离",
        "confidence": "高",
        "source_org": "U.S. Army Acquisition",
        "source_title": "U.S. Army Acquisition Program Portfolio 2024; Acquisition partnership to roll out new improved Sentinel Radar",
        "source_url": "https://api.army.mil/e2/c/downloads/2024/07/19/ab2038a9/u-s-army-portfolio-2024.pdf | https://asc.army.mil/web/access-acquisition-partnership-to-roll-out-new-improved-sentinel-radar/",
        "evidence_note": "陆军公开资料明确X波段、三维、360度和75 km；数值调谐范围保持为空。75 km和360度由陆军采办文章直接支持。",
        "usage_boundary": "不得用通用X波段边界替代具体授权范围。",
    },
    {
        "parameter_id": "PAR-RADAR-SURVEILLANCE-2700",
        "system_or_service": "联邦/军用监视雷达参考",
        "mission_role": "机场监视、天气与军用监视雷达共存",
        "case_links": "",
        "frequency_start_mhz": 2700.0,
        "frequency_end_mhz": 2900.0,
        "center_frequency_mhz": None,
        "channel_step_khz": None,
        "occupied_bandwidth_khz": None,
        "power_w": None,
        "channel_count": None,
        "range_km": None,
        "waveform_or_access": "脉冲雷达；具体系统参数依RSEC和单台指配",
        "mobility": "固定、移动或可搬移",
        "assignment_mode": "单台雷达频率与保护区",
        "planning_relation": "高功率雷达之间需频率-距离协调和杂散保护",
        "parameter_status": "公开业务频段",
        "confidence": "高",
        "source_org": "NTIA",
        "source_title": "2700-2900 MHz Federal Spectrum Use Report",
        "source_url": "https://www.ntia.gov/files/ntia/publications/compendium/2700.00-2900.00_01MAR14.pdf",
        "evidence_note": "NTIA强调该频段雷达需谨慎协调并符合Radar Spectrum Engineering Criteria。",
        "usage_boundary": "业务共存参考，不代表平台可在整个频段自由分配。",
    },
    {
        "parameter_id": "PAR-RADAR-MARITIME-2900",
        "system_or_service": "军用/海上搜索雷达参考",
        "mission_role": "海上导航、搜索、跟踪和训练",
        "case_links": "",
        "frequency_start_mhz": 2900.0,
        "frequency_end_mhz": 3100.0,
        "center_frequency_mhz": None,
        "channel_step_khz": None,
        "occupied_bandwidth_khz": None,
        "power_w": None,
        "channel_count": None,
        "range_km": None,
        "waveform_or_access": "脉冲/线性调频雷达类别",
        "mobility": "舰载、岸基、可搬移",
        "assignment_mode": "雷达频率与保护区",
        "planning_relation": "需评估接收机前端过载、带外发射和频率-距离隔离",
        "parameter_status": "公开业务频段",
        "confidence": "高",
        "source_org": "NTIA",
        "source_title": "2900-3100 MHz Federal Spectrum Use Report",
        "source_url": "https://www.ntia.gov/files/ntia/publications/compendium/2900.00-3100.00_01MAY15.pdf",
        "evidence_note": "NTIA公开该频段的军用和海上雷达用途，并说明线性调频等技术。",
        "usage_boundary": "不包含单台雷达峰值功率、脉宽、PRF或部署参数。",
    },
    {
        "parameter_id": "PAR-UHF-SATCOM-DOWN",
        "system_or_service": "FLTSATCOM/UHF移动卫星下行参考",
        "mission_role": "战术和战略窄带卫星通信下行",
        "case_links": "CASE-OEF-2001; CASE-OIF-2003",
        "frequency_start_mhz": 243.855,
        "frequency_end_mhz": 269.95,
        "center_frequency_mhz": None,
        "channel_step_khz": None,
        "occupied_bandwidth_khz": None,
        "power_w": None,
        "channel_count": None,
        "range_km": "卫星覆盖",
        "waveform_or_access": "窄带移动卫星；具体频道和接入计划未公开",
        "mobility": "背负、车载、舰载、机载终端",
        "assignment_mode": "卫星下行频道/网络资源",
        "planning_relation": "超视距关键链路；下行与地面/航空业务共存",
        "parameter_status": "公开精确历史范围",
        "confidence": "高",
        "source_org": "NTIA",
        "source_title": "225-328.6 MHz Federal Spectrum Use Report",
        "source_url": "https://www.ntia.gov/files/ntia/publications/compendium/0225.00-0328.60_01MAR14.pdf",
        "evidence_note": "NTIA公开FLTSATCOM历史下行范围。",
        "usage_boundary": "历史系统范围，不收录当前卫星频道计划或实际任务网络。",
    },
    {
        "parameter_id": "PAR-UHF-SATCOM-UP",
        "system_or_service": "FLTSATCOM/UHF移动卫星上行参考",
        "mission_role": "战术和战略窄带卫星通信上行",
        "case_links": "CASE-OEF-2001; CASE-OIF-2003",
        "frequency_start_mhz": 292.85,
        "frequency_end_mhz": 317.325,
        "center_frequency_mhz": None,
        "channel_step_khz": None,
        "occupied_bandwidth_khz": None,
        "power_w": None,
        "channel_count": None,
        "range_km": "卫星覆盖",
        "waveform_or_access": "窄带移动卫星；具体频道和接入计划未公开",
        "mobility": "背负、车载、舰载、机载终端",
        "assignment_mode": "卫星上行频道/网络资源",
        "planning_relation": "超视距关键链路；上行发射需区域和时段授权",
        "parameter_status": "公开精确历史范围",
        "confidence": "高",
        "source_org": "NTIA",
        "source_title": "225-328.6 MHz Federal Spectrum Use Report",
        "source_url": "https://www.ntia.gov/files/ntia/publications/compendium/0225.00-0328.60_01MAR14.pdf",
        "evidence_note": "NTIA公开FLTSATCOM历史上行范围。",
        "usage_boundary": "历史系统范围，不收录当前卫星频道计划或实际任务网络。",
    },
    {
        "parameter_id": "PAR-WGS-X",
        "system_or_service": "WGS X-band业务类别",
        "mission_role": "全球高容量军事卫星通信",
        "case_links": "",
        "frequency_start_mhz": None,
        "frequency_end_mhz": None,
        "center_frequency_mhz": None,
        "channel_step_khz": None,
        "occupied_bandwidth_khz": None,
        "power_w": None,
        "channel_count": None,
        "range_km": "全球覆盖",
        "waveform_or_access": "WGS提供X-band服务；具体转发器参数未公开",
        "mobility": "固定、可搬移、地面/空中/舰载终端",
        "assignment_mode": "卫星带宽/波束资源",
        "planning_relation": "高容量骨干链路；需带宽、波束和终端能力联合规划",
        "parameter_status": "公开频段类别边界",
        "confidence": "中高",
        "source_org": "U.S. Space Force / U.S. Army",
        "source_title": "Wideband Global SATCOM Fact Sheet; D3SOE Handbook",
        "source_url": "https://www.spaceforce.mil/about-us/fact-sheets/article/2197740/wideband-global-satcom-satellite/ | https://api.army.mil/e2/c/downloads/2023/01/19/7f7281ee/18-28-operating-in-a-denied-degraded-and-disrupted-space-operational-environment-handbook-jun-18-public.pdf",
        "evidence_note": "Space Force确认WGS提供X/Ka业务；8-12 GHz来自陆军公开波段定义，不是WGS具体转发器范围。",
        "usage_boundary": "不得把整个X波段直接转成WGS可用规则。",
    },
    {
        "parameter_id": "PAR-WGS-KA",
        "system_or_service": "WGS Ka-band业务类别",
        "mission_role": "全球高容量军事卫星通信",
        "case_links": "",
        "frequency_start_mhz": None,
        "frequency_end_mhz": None,
        "center_frequency_mhz": None,
        "channel_step_khz": None,
        "occupied_bandwidth_khz": None,
        "power_w": None,
        "channel_count": None,
        "range_km": "全球覆盖",
        "waveform_or_access": "WGS提供Ka-band服务；具体转发器参数未公开",
        "mobility": "固定、可搬移、地面/空中/舰载终端",
        "assignment_mode": "卫星带宽/波束资源",
        "planning_relation": "高容量骨干和广播；需考虑雨衰及终端口径",
        "parameter_status": "公开频段类别边界",
        "confidence": "中高",
        "source_org": "U.S. Space Force / U.S. Army",
        "source_title": "Wideband Global SATCOM Fact Sheet; D3SOE Handbook",
        "source_url": "https://www.spaceforce.mil/about-us/fact-sheets/article/2197740/wideband-global-satcom-satellite/ | https://api.army.mil/e2/c/downloads/2023/01/19/7f7281ee/18-28-operating-in-a-denied-degraded-and-disrupted-space-operational-environment-handbook-jun-18-public.pdf",
        "evidence_note": "27-40 GHz是公开Ka波段定义，不是WGS具体上下行或转发器范围。",
        "usage_boundary": "不得把整个Ka波段直接转成WGS可用规则。",
    },
    {
        "parameter_id": "PAR-UAS-CNPC-5030",
        "system_or_service": "UAS CNPC公共规划参考",
        "mission_role": "非隔离空域无人机安全控制与非载荷通信",
        "case_links": "",
        "frequency_start_mhz": 5030.0,
        "frequency_end_mhz": 5091.0,
        "center_frequency_mhz": None,
        "channel_step_khz": None,
        "occupied_bandwidth_khz": None,
        "power_w": None,
        "channel_count": None,
        "range_km": "地面视距链路",
        "waveform_or_access": "高完整性CNPC；具体标准参数另行建模",
        "mobility": "无人机/远程控制中心",
        "assignment_mode": "安全控制链路",
        "planning_relation": "飞控高可靠链路，应与载荷数据分离并设置最高保障级",
        "parameter_status": "公开规划频段",
        "confidence": "高",
        "source_org": "NTIA / FAA",
        "source_title": "5030-5250 MHz Spectrum Compendium; UAS NAS Integration Roadmap",
        "source_url": "https://www.ntia.gov/files/ntia/publications/compendium/5030.00-5250.00-02092021.pdf | https://www.faa.gov/sites/faa.gov/files/uas/resources/policy_library/Second_Edition_Integration_of_Civil_UAS_NAS_Roadmap_July%25202018.pdf",
        "evidence_note": "5030-5091 MHz是CNPC公共规划频段，不是伊拉克/阿富汗战例频率。",
        "usage_boundary": "仅作未来控制链路和数据模型参考。",
    },
    {
        "parameter_id": "PAR-UAS-TELEMETRY-2200",
        "system_or_service": "航空/UAS试验遥测参考",
        "mission_role": "飞行试验遥测、高分辨率视频和无人飞行器测试",
        "case_links": "",
        "frequency_start_mhz": 2200.0,
        "frequency_end_mhz": 2290.0,
        "center_frequency_mhz": None,
        "channel_step_khz": None,
        "occupied_bandwidth_khz": None,
        "power_w": None,
        "channel_count": None,
        "range_km": None,
        "waveform_or_access": "航空遥测；高分辨率视频需求",
        "mobility": "试验航空器/UAS与地面站",
        "assignment_mode": "遥测频道/连续带宽",
        "planning_relation": "试验任务时段化占用；需与空间业务协调",
        "parameter_status": "公开业务频段",
        "confidence": "高",
        "source_org": "NTIA",
        "source_title": "2200-2290 MHz Federal Spectrum Use Report",
        "source_url": "https://www.ntia.gov/files/ntia/publications/compendium/2200.00-2290.00_01MAY15.pdf",
        "evidence_note": "NTIA明确DoD和商业飞行试验、高分辨率视频及无人飞行器测试需求。",
        "usage_boundary": "试验遥测频段，不代表作战UAS实际控制或载荷链路。",
    },
]


PARAMETER_METADATA = {
    "PAR-SINCGARS": ("equipment_range", "SRC-01", "海湾战争地面战斗网装备基线"),
    "PAR-MIL-AIR-VOICE": ("service_plan", "SRC-11", "军用航空话音业务规划参考"),
    "PAR-EPLRS": ("system_band", "SRC-08", "战术位置报告与数据分发系统基线"),
    "PAR-LINK16": ("system_band", "SRC-09; SRC-10", "联合战术数据链系统基线"),
    "PAR-GPS-L5": ("protected_center", "SRC-09", "PNT敏感接收业务保护对象"),
    "PAR-GPS-L2": ("protected_center", "SRC-09", "PNT敏感接收业务保护对象"),
    "PAR-GPS-L1": ("protected_center", "SRC-09", "PNT敏感接收业务保护对象"),
    "PAR-UAS-C-KU": ("category_only", "SRC-05", "伊拉克/阿富汗无人系统公开类别"),
    "PAR-TRR-4400": ("coexistence_study_band", "SRC-23", "频谱迁移与共存评估参考"),
    "PAR-RADAR-TPQ53": ("equipment_range", "SRC-13", "伊拉克/阿富汗时期后段反炮兵雷达能力参考"),
    "PAR-RADAR-SENTINEL": ("category_only", "SRC-14; SRC-24", "后伊拉克战争时期防空雷达能力参考"),
    "PAR-RADAR-SURVEILLANCE-2700": ("service_allocation", "SRC-15", "通用雷达共存基线"),
    "PAR-RADAR-MARITIME-2900": ("service_allocation", "SRC-16", "通用海上雷达共存基线"),
    "PAR-UHF-SATCOM-DOWN": ("historical_system_range", "SRC-17", "OEF/OIF超视距通信需求背景"),
    "PAR-UHF-SATCOM-UP": ("historical_system_range", "SRC-17", "OEF/OIF超视距通信需求背景"),
    "PAR-WGS-X": ("category_only", "SRC-18; SRC-19", "后OEF/OIF宽带卫星通信能力参考"),
    "PAR-WGS-KA": ("category_only", "SRC-18; SRC-19", "后OEF/OIF宽带卫星通信能力参考"),
    "PAR-UAS-CNPC-5030": ("planned_service_allocation", "SRC-20; SRC-22", "未来无人机安全控制链路参考"),
    "PAR-UAS-TELEMETRY-2200": ("service_allocation", "SRC-21", "无人机试验与鉴定业务参考"),
}

for parameter in PUBLIC_PARAMETERS:
    frequency_scope, source_ids, baseline_context = PARAMETER_METADATA[parameter["parameter_id"]]
    parameter["frequency_scope"] = frequency_scope
    parameter["source_ids"] = source_ids
    parameter["baseline_context"] = baseline_context


FIELD_DICTIONARY = [
    ("case_id / parameter_id", "稳定记录编号", "用于来源追踪和后续增量更新"),
    ("operation / case_links", "战例及关联", "参数关联到需求背景，不代表战例实际使用了系统全部调谐范围"),
    ("frequency_start_mhz / frequency_end_mhz", "公开数值范围", "仅在来源明确给出时填写；必须结合frequency_scope解释"),
    ("center_frequency_mhz", "公开中心频率", "适用于GPS等保护对象"),
    ("channel_step_khz", "频道间隔或规划步进", "来源未明确时留空；不得用设备带宽替代"),
    ("occupied_bandwidth_khz", "单项占用带宽", "来源未明确时留空"),
    ("power_w", "公开功率或范围", "型号差异明显或未公开时留空"),
    ("frequency_scope", "频率数值语义", "equipment_range / system_band / service_allocation / service_plan / protected_center / category_only / historical_system_range / planned_service_allocation / coexistence_study_band"),
    ("parameter_status", "披露粒度", "公开精确范围 / 公开业务规划范围 / 仅公开频段类别"),
    ("source_ids", "来源目录编号", "一个或多个SRC-*编号；必须能在来源目录中解析"),
    ("baseline_context", "参考背景", "用于保存非战例外键的时代、能力或共存背景"),
    ("usage_boundary", "使用边界", "防止把工作范围误当授权或实际行动频道"),
    ("confidence", "证据置信度", "高=政府原始资料直接支持；中=政府资料中的评估或汇总"),
]


SOURCES = [
    ("SRC-01", "U.S. Army", "1992 Weapon Systems Handbook", "SINCGARS参数与西南亚表现", "https://asc.army.mil/docs/wsh2/1992-wsh.pdf", "政府原始资料"),
    ("SRC-02", "GAO", "Operation Desert Storm: Apache Helicopter Fratricide Incident", "海湾战争航空无线电类别", "https://www.gao.gov/assets/osi-93-4.pdf", "政府调查"),
    ("SRC-03", "GAO", "GAO-01-401 Kosovo Air Operations", "Task Force Hawk联合互操作问题", "https://www.gao.gov/products/gao-01-401", "政府审计"),
    ("SRC-04", "GAO", "GAO-04-547 Military Operations", "Kosovo/Afghanistan/Iraq网络化作战与互操作", "https://www.gao.gov/products/gao-04-547", "政府审计"),
    ("SRC-05", "GAO", "GAO-06-49 Unmanned Aircraft Systems", "UAS C/Ku频段类别、拥塞和任务延迟", "https://www.gao.gov/products/gao-06-49", "政府审计"),
    ("SRC-06", "GAO", "GAO-07-836 Unmanned Aircraft Systems", "Iraq/Afghanistan UAS带宽和协调问题", "https://www.gao.gov/products/gao-07-836", "政府审计"),
    ("SRC-07", "U.S. Army", "WIN-T: It is real, it is here and it works", "OEF/OIF超视距网络需求", "https://www.army.mil/article/25076/warfighter_information_network_tactical_its_real_its_here_and_it_works", "军方官方文章"),
    ("SRC-08", "NTIA", "420-450 MHz Federal Spectrum Use Report", "EPLRS/AEPLRS与频段用途", "https://www.ntia.gov/files/ntia/publications/compendium/0420.00-0450.00_01MAY15.pdf", "政府频谱报告"),
    ("SRC-09", "NTIA", "1164-1215 MHz Federal Spectrum Use Report", "Link 16授权范围和GPS中心频率", "https://www.ntia.gov/files/ntia/publications/compendium/1164.00-1215.00_01MAR14.pdf", "政府频谱报告"),
    ("SRC-10", "U.S. Army", "FM 3-01 Air and Missile Defense Operations", "Link 16离散频率数和公开速率", "https://rdl.train.army.mil/catalog-ws/view/100.ATSC/C01CC9C1-DA1C-4D5E-A6EB-5FCFAE218DCD-1398170439966/fm3_01.pdf", "公开条令"),
    ("SRC-11", "U.S. DOT / NTIA", "Transportation Strategic Spectrum Plan", "军用航空空地业务规划参数", "https://www.ntia.gov/sites/default/files/publications/transportation_strategic_spectrum_plan_nov2007_0.pdf", "政府规划资料"),
    ("SRC-12", "GAO", "GAO-26-107873 Spectrum Management", "频率申请数据包含地点、时间、频段和持续时长", "https://files.gao.gov/reports/GAO-26-107873/index.html", "政府审计"),
    ("SRC-13", "U.S. Army ODIN", "AN/TPQ-53 Counterfire Radar", "Q-53 S波段和公开覆盖距离", "https://odin.t2com.army.mil/WEG/Asset/6ea3c7edc1d7b3bab022f375761f3ee6", "军方公开数据库"),
    ("SRC-14", "U.S. Army Acquisition", "Program Portfolio 2024", "Sentinel项目与X波段能力背景", "https://api.army.mil/e2/c/downloads/2024/07/19/ab2038a9/u-s-army-portfolio-2024.pdf", "军方项目资料"),
    ("SRC-15", "NTIA", "2700-2900 MHz Federal Spectrum Use Report", "监视雷达和频率协调", "https://www.ntia.gov/files/ntia/publications/compendium/2700.00-2900.00_01MAR14.pdf", "政府频谱报告"),
    ("SRC-16", "NTIA", "2900-3100 MHz Federal Spectrum Use Report", "海上和军用雷达用途", "https://www.ntia.gov/files/ntia/publications/compendium/2900.00-3100.00_01MAY15.pdf", "政府频谱报告"),
    ("SRC-17", "NTIA", "225-328.6 MHz Federal Spectrum Use Report", "FLTSATCOM历史上下行范围", "https://www.ntia.gov/files/ntia/publications/compendium/0225.00-0328.60_01MAR14.pdf", "政府频谱报告"),
    ("SRC-18", "U.S. Space Force", "Wideband Global SATCOM Fact Sheet", "WGS X/Ka波段业务", "https://www.spaceforce.mil/about-us/fact-sheets/article/2197740/wideband-global-satcom-satellite/", "军方事实页"),
    ("SRC-19", "U.S. Army", "D3SOE Handbook", "公开通信波段边界与典型系统", "https://api.army.mil/e2/c/downloads/2023/01/19/7f7281ee/18-28-operating-in-a-denied-degraded-and-disrupted-space-operational-environment-handbook-jun-18-public.pdf", "公开手册"),
    ("SRC-20", "NTIA / FAA", "5030-5250 MHz Spectrum Compendium", "UAS CNPC 5030-5091 MHz", "https://www.ntia.gov/files/ntia/publications/compendium/5030.00-5250.00-02092021.pdf", "政府频谱报告"),
    ("SRC-21", "NTIA", "2200-2290 MHz Federal Spectrum Use Report", "航空/UAS试验遥测", "https://www.ntia.gov/files/ntia/publications/compendium/2200.00-2290.00_01MAY15.pdf", "政府频谱报告"),
    ("SRC-22", "FAA", "Integration of Civil UAS in the National Airspace System Roadmap", "UAS CNPC安全关键用途与5030-5091 MHz规划", "https://www.faa.gov/sites/faa.gov/files/uas/resources/policy_library/Second_Edition_Integration_of_Civil_UAS_NAS_Roadmap_July%25202018.pdf", "政府路线图"),
    ("SRC-23", "U.S. Department of Defense / NTIA", "DoD 4400-4940 MHz Band Assessment", "战术中继与其他系统的迁移和共存评估", "https://www.ntia.gov/sites/default/files/publications/dodassessment_0.pdf", "政府频谱评估"),
    ("SRC-24", "U.S. Army Acquisition Support Center", "Acquisition partnership to roll out new improved Sentinel Radar", "AN/MPQ-64A3三维X波段、360度和75 km", "https://asc.army.mil/web/access-acquisition-partnership-to-roll-out-new-improved-sentinel-radar/", "军方采办文章"),
]


def style_sheet(sheet, table_name=None):
    thin = Side(style="thin", color="C7D2E2")
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    sheet.row_dimensions[1].height = 28
    for cell in sheet[1]:
        cell.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="17365D")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(bottom=thin)
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="Arial", size=9, color="1F2937")
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(bottom=thin)
        if row[0].row % 2 == 0:
            for cell in row:
                cell.fill = PatternFill("solid", fgColor="F6F8FB")
    for column_index, column in enumerate(sheet.columns, start=1):
        header = str(sheet.cell(1, column_index).value or "")
        values = [str(cell.value or "") for cell in list(column)[:80]]
        width = min(55, max(12, max((len(value) for value in values), default=10) + 2))
        if "url" in header.lower():
            width = 48
        elif header in {"observed_issue_or_result", "planning_requirements", "evidence_note", "usage_boundary", "source_title"}:
            width = 42
        elif header in {"spectrum_dependent_tasks", "public_systems", "waveform_or_access"}:
            width = 32
        sheet.column_dimensions[get_column_letter(column_index)].width = width
    if table_name and sheet.max_row >= 2:
        table = Table(displayName=table_name, ref=sheet.dimensions)
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        sheet.add_table(table)


def add_sheet(workbook, name, rows, headers=None, table_name=None):
    sheet = workbook.create_sheet(name)
    if headers is None:
        headers = list(rows[0].keys()) if rows else []
        data_rows = [[row.get(header) for header in headers] for row in rows]
    else:
        data_rows = rows
    sheet.append(headers)
    for row in data_rows:
        sheet.append(row)
    style_sheet(sheet, table_name)
    return sheet


def validate_records():
    case_ids = {record["case_id"] for record in BATTLE_CASES}
    parameter_ids = {record["parameter_id"] for record in PUBLIC_PARAMETERS}
    source_by_id = {record[0]: record[4] for record in SOURCES}
    allowed_scopes = {
        "equipment_range",
        "system_band",
        "service_allocation",
        "service_plan",
        "protected_center",
        "category_only",
        "historical_system_range",
        "planned_service_allocation",
        "coexistence_study_band",
    }

    assert len(case_ids) == len(BATTLE_CASES), "Duplicate case_id"
    assert len(parameter_ids) == len(PUBLIC_PARAMETERS), "Duplicate parameter_id"
    assert len(source_by_id) == len(SOURCES), "Duplicate source_id"
    assert parameter_ids == set(PARAMETER_METADATA), "Parameter metadata coverage mismatch"

    for parameter in PUBLIC_PARAMETERS:
        linked_cases = {value.strip() for value in parameter["case_links"].split(";") if value.strip()}
        assert linked_cases <= case_ids, f"Unknown case link: {parameter['parameter_id']}"
        assert parameter["frequency_scope"] in allowed_scopes, f"Unknown frequency scope: {parameter['parameter_id']}"
        if parameter["frequency_scope"] == "category_only":
            assert parameter["frequency_start_mhz"] is None and parameter["frequency_end_mhz"] is None, (
                f"Category-only record has numeric range: {parameter['parameter_id']}"
            )
        linked_sources = {value.strip() for value in parameter["source_ids"].split(";") if value.strip()}
        assert linked_sources and linked_sources <= set(source_by_id), f"Unknown source link: {parameter['parameter_id']}"
        for source_id in linked_sources:
            assert source_by_id[source_id] in parameter["source_url"], (
                f"Source URL mismatch: {parameter['parameter_id']} -> {source_id}"
            )


def build_workbook(output=OUTPUT):
    validate_records()
    workbook = Workbook()
    workbook.remove(workbook.active)

    boundary = workbook.create_sheet("数据边界")
    notes = [
        ("项目", "美军公开战例与用频参数基线（第一、二批）"),
        ("更新日期", "2026-07-10"),
        ("用途", "需求建模、算法测试、仿真样例设计"),
        ("禁止解释", "系统调谐范围不等于战例实际频道；公开频段不等于本项目获得使用授权"),
        ("不收录", "具体频道、呼号、密钥、跳频表、网络初始化数据和部署坐标"),
        ("缺失处理", "来源没有公开的精确频率、功率、带宽保持为空，不用推测值补齐"),
        ("平台导入", "本工作簿不是spectrum_rules导入模板；应另行构造SIM-*仿真规则并标明假设"),
        ("证据优先级", "政府/军方原始资料 > 政府审计 > 政府汇总；不以商业宣传页作为首要证据"),
    ]
    for row in notes:
        boundary.append(row)
    boundary.column_dimensions["A"].width = 18
    boundary.column_dimensions["B"].width = 110
    for row in boundary.iter_rows():
        row[0].font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        row[0].fill = PatternFill("solid", fgColor="17365D")
        row[1].font = Font(name="Arial", size=10)
        row[0].alignment = row[1].alignment = Alignment(vertical="top", wrap_text=True)
        row[0].border = row[1].border = Border(bottom=Side(style="thin", color="C7D2E2"))
        boundary.row_dimensions[row[0].row].height = 34

    add_sheet(workbook, "战例基线", BATTLE_CASES, table_name="BattleCases")
    add_sheet(workbook, "公开用频参数", PUBLIC_PARAMETERS, table_name="SpectrumParameters")
    add_sheet(workbook, "字段字典", FIELD_DICTIONARY, headers=["字段", "含义", "使用规则"], table_name="FieldDictionary")
    add_sheet(
        workbook,
        "来源目录",
        SOURCES,
        headers=["source_id", "source_org", "source_title", "evidence_scope", "source_url", "source_type"],
        table_name="SourceCatalog",
    )

    for sheet in workbook.worksheets:
        sheet.sheet_view.showGridLines = False

    output.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output)

    check = load_workbook(output, read_only=False, data_only=False)
    assert check.sheetnames == ["数据边界", "战例基线", "公开用频参数", "字段字典", "来源目录"]
    assert check["战例基线"].max_row == len(BATTLE_CASES) + 1
    assert check["公开用频参数"].max_row == len(PUBLIC_PARAMETERS) + 1
    assert check["来源目录"].max_row == len(SOURCES) + 1
    return output


if __name__ == "__main__":
    path = build_workbook()
    print(f"{path} | cases={len(BATTLE_CASES)} | parameters={len(PUBLIC_PARAMETERS)} | sources={len(SOURCES)}")

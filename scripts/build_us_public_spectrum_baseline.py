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
]


FIELD_DICTIONARY = [
    ("case_id / parameter_id", "稳定记录编号", "用于来源追踪和后续增量更新"),
    ("operation / case_links", "战例及关联", "参数关联到需求背景，不代表战例实际使用了系统全部调谐范围"),
    ("frequency_start_mhz / frequency_end_mhz", "公开工作范围", "仅在来源明确给出时填写"),
    ("center_frequency_mhz", "公开中心频率", "适用于GPS等保护对象"),
    ("channel_step_khz", "频道间隔或规划步进", "来源未明确时留空；不得用设备带宽替代"),
    ("occupied_bandwidth_khz", "单项占用带宽", "来源未明确时留空"),
    ("power_w", "公开功率或范围", "型号差异明显或未公开时留空"),
    ("parameter_status", "披露粒度", "公开精确范围 / 公开业务规划范围 / 仅公开频段类别"),
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


def build_workbook(output=OUTPUT):
    workbook = Workbook()
    workbook.remove(workbook.active)

    boundary = workbook.create_sheet("数据边界")
    notes = [
        ("项目", "美军公开战例与用频参数基线（第一批）"),
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
    return output


if __name__ == "__main__":
    path = build_workbook()
    print(f"{path} | cases={len(BATTLE_CASES)} | parameters={len(PUBLIC_PARAMETERS)} | sources={len(SOURCES)}")

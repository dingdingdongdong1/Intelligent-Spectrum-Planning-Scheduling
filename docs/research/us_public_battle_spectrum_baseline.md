# 美军公开战例与用频参数基线（第一批）

更新日期：2026-07-10

## 使用边界

本资料只收录美国政府、美军官方或已公开政府审计材料能够核验的信息，用于需求建模、算法测试和仿真样例设计。

- “系统工作频段”不等于某次行动的实际频道，也不等于本项目可直接使用的授权频段。
- 不收录现役部队具体频道、呼号、密钥、跳频表、网络初始化数据和部署坐标。
- 来源没有公开精确频率、功率或带宽时保持为空，不用推测值补齐。
- 平台生成样例时应使用独立的 `SIM-*` 仿真频段，不应把本表直接转成“可用”规则。

## 战例基线

### 1. 沙漠盾牌/沙漠风暴行动（1990-1991）

**任务背景**：大规模联合地面机动、航空兵支援、指挥控制和火力协同。

**公开证据**：

- 美国陆军 1992 年《Weapon Systems Handbook》记录 SINCGARS 的任务是提供战斗网指挥控制和抗电子战能力，公开参数为 30.000-87.975 MHz、2320 个频道、典型通信距离 8-35 km，并称其在西南亚作战环境中表现良好。
- GAO 对海湾战争 Apache 误击事件的调查披露了安全 FM、UHF 空空和 VHF/FM 等不同无线电域，说明空地协同需要跨无线电域的互操作或网关保障；该报告不能被解读为无线电问题是事故的唯一原因。

**对平台的需求映射**：

- 任务单元需要区分地面指挥、航空兵、火力和保障节点。
- 装备组需要支持 VHF 战斗网、UHF 航空通信和跨网互联关系。
- 规划约束需要包含通信距离、任务优先级、空地兼容性、备用通信手段和抗干扰策略。

### 2. 联盟力量行动 / Task Force Hawk（1999）

**任务背景**：陆军 Apache 特遣部队支援以空中行动为主的联合战役。

**公开证据**：GAO-01-401 认定陆军和空军在联合作战以及 C4I 装备互操作方面存在显著问题。公开摘要没有给出行动实际频道。

**对平台的需求映射**：

- 规划对象不能只有“电台”，还应有通信链路、数据链和跨军种网关。
- 方案评价需要增加互操作覆盖率、跨域链路可达性和共同态势数据可用性。
- 数据缺失时应保留“频率未公开”，不能用装备通用频段冒充战例频道。

### 3. 持久自由行动（2001 起）

**任务背景**：山地远距离作战、分散节点指挥、情报侦察和超视距通信。

**公开证据**：美国陆军材料将 OEF 与超视距通信需求直接关联；公开陆军文章还指出阿富汗山地对视距 FM 通信不利，UHF 战术卫星通信被频繁使用。

**对平台的需求映射**：

- 地域模型至少需要地形/遮挡等级、视距可达性和超视距需求。
- 同一关键任务应同时规划地面 VHF/UHF、卫星或 HF 备用链路。
- 保障率不能只按“分到频率”计算，还应考虑链路模式是否适应地域和机动条件。

### 4. 伊拉克自由行动（2003 起）

**任务背景**：高速地面推进、机动指挥、宽带态势共享和跨军种协同。

**公开证据**：美国陆军称进攻巴格达期间部队推进速度超过原有 MSE 视距网络的通信能力，从而推动 JNN/WIN-T 超视距网络；GAO-04-547 同时指出 Kosovo、Afghanistan 和 Iraq 的网络化作战提高了信息共享速度，但标准化和互操作不足仍是主要障碍。

**对平台的需求映射**：

- 任务应具备时段、阶段、机动速度和通信建立/撤收时间。
- 规划应区分静止建立、短停建立和行进间通信能力。
- 方案代价应纳入链路切换、节点重构和卫星/地面资源占用。

### 5. 伊拉克/阿富汗无人系统联合运用（2001-2007）

**任务背景**：无人机飞行控制、ISR 传感器数据回传、实时视频和时敏目标支持。

**公开证据**：GAO-06-49 和 GAO-07-836 记录 C/Ku 频段拥塞、互操作不足和带宽受限曾导致部分无人机任务延迟；报告还指出传感器数据通常比飞行控制需要更高带宽。报告只公开频段类别，没有公开行动频道。

**对平台的需求映射**：

- 必须把“飞行控制链路”和“载荷数据链路”拆成不同装备组和不同保障率。
- 规划器需要带宽、频段可重构能力、链路优先级和同时在线数量约束。
- 动态重筹应支持频段拥塞、任务延迟、带宽降级和 C/Ku 备选切换事件。

## 第一批公开参数

| 系统/业务 | 公开频率信息 | 公开的其他参数 | 适用说明 |
| --- | --- | --- | --- |
| SINCGARS | 30.000-87.975 MHz | 2320 频道；8-35 km；地面/车载/机载构型 | 系统工作范围，不是行动频道 |
| 军用航空空地话音 | 225.000-399.900 MHz（排除 326.6-335.4 MHz） | 25 kHz 间隔；6 kHz 指配带宽；10-50 W；471 频道 | 美国境内频谱规划资料，不代表海外行动授权 |
| EPLRS/AEPLRS | 420-450 MHz | TDMA、跳频扩频、位置报告和多跳数据 | 公共系统频段 |
| JTIDS/MIDS / Link 16 | 960-1164 MHz | 51 个离散频率；扩频跳频；数据率超过 50 kbit/s | 需与航空导航业务兼容协调 |
| GPS L5 | 1176.45 MHz | NTIA 公开 L5 中心频率 | 接收型 PNT 保护对象 |
| GPS L2 | 1227.60 MHz | NTIA 公开 L2 中心频率 | 接收型 PNT 保护对象 |
| GPS L1 | 1575.42 MHz | NTIA 公开 L1 中心频率 | 接收型 PNT 保护对象 |
| UAS 控制/载荷链路 | C band / Ku band | 12 类 UAS 中多型依赖 C 或 Ku；多数当时不能跨频段重构 | GAO 未公开行动具体频率，数值保持空缺 |
| 战术无线电中继参考 | 4400-4940 MHz | NTIA/DoD 公开评估中的候选或共存研究频段 | 仅用于冲突研究，不作为授权频段 |

详细字段、来源 URL 和证据等级见 `us_public_battle_spectrum_baseline.xlsx`。

## 主要公开来源

1. U.S. Army, *1992 Weapon Systems Handbook*: https://asc.army.mil/docs/wsh2/1992-wsh.pdf
2. GAO, *Operation Desert Storm: Apache Helicopter Fratricide Incident*: https://www.gao.gov/assets/osi-93-4.pdf
3. GAO-01-401, *Kosovo Air Operations*: https://www.gao.gov/products/gao-01-401
4. GAO-04-547, *Military Operations: Recent Campaigns Benefited from Improved Communications and Technology*: https://www.gao.gov/products/gao-04-547
5. GAO-06-49, *Unmanned Aircraft Systems*: https://www.gao.gov/products/gao-06-49
6. GAO-07-836, *Unmanned Aircraft Systems: Advance Coordination and Increased Visibility Needed*: https://www.gao.gov/products/gao-07-836
7. U.S. Army, *WIN-T: It's real, it's here and it works*: https://www.army.mil/article/25076/warfighter_information_network_tactical_its_real_its_here_and_it_works
8. NTIA, *420-450 MHz Federal Spectrum Use Report*: https://www.ntia.gov/files/ntia/publications/compendium/0420.00-0450.00_01MAY15.pdf
9. NTIA, *1164-1215 MHz Federal Spectrum Use Report*: https://www.ntia.gov/files/ntia/publications/compendium/1164.00-1215.00_01MAR14.pdf
10. U.S. Army FM 3-01, *Air and Missile Defense Operations*: https://rdl.train.army.mil/catalog-ws/view/100.ATSC/C01CC9C1-DA1C-4D5E-A6EB-5FCFAE218DCD-1398170439966/fm3_01.pdf
11. U.S. Department of Transportation, *Transportation Strategic Spectrum Plan*: https://www.ntia.gov/sites/default/files/publications/transportation_strategic_spectrum_plan_nov2007_0.pdf
12. GAO-26-107873, *Spectrum Management*: https://files.gao.gov/reports/GAO-26-107873/index.html

## 下一批需要补充

- 海湾战争和伊拉克战争的任务阶段、节点规模、保障优先级和链路关系。
- 公开资料中的雷达、卫星通信、无人机控制/载荷链路参数及其证据等级。
- 面向平台的数据字典：任务时段、通信链路、频率授权、地理范围和机动事件。
- 将公开系统参数转成独立的仿真参数库，而不是直接转成行动用频规则。

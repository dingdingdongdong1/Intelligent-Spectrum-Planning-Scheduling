# 美军公开战例与用频参数基线（第一至三批）

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

## 第二批公开参数：雷达、卫星通信与无人机链路

| 系统/业务 | 公开频率信息 | 公开的其他参数 | 证据边界与平台用途 |
| --- | --- | --- | --- |
| AN/TPQ-53 反炮兵雷达 | 2-4 GHz（S 波段） | 90 度模式：火箭 60 km、火炮 34 km、迫击炮 20 km；360 度模式：20 km | 装备能力范围；未公开实际调谐点、脉冲参数和射频功率，用于建立雷达时空保护对象 |
| AN/MPQ-64 Sentinel | 仅公开 X 波段，数值范围留空 | 三维相控阵、360 度、75 km | 不用通用 X 波段边界替代具体授权范围，用于建立持续空情监视任务 |
| 联邦/军用监视雷达参考 | 2700-2900 MHz | 机场、天气和军用监视雷达共存 | 业务频段参考，用于频率-距离协调、保护区和杂散约束建模 |
| 军用/海上搜索雷达参考 | 2900-3100 MHz | 脉冲及线性调频雷达类别 | 用于接收机前端过载、带外发射和频率-距离隔离评估 |
| FLTSATCOM/UHF 卫星下行 | 243.855-269.950 MHz | 窄带移动卫星通信 | 历史系统范围；不包含当前频道计划和实际任务网络 |
| FLTSATCOM/UHF 卫星上行 | 292.850-317.325 MHz | 窄带移动卫星通信 | 上、下行分别建模；不把中间空段合并为连续可用频段 |
| WGS X-band 业务类别 | 8-12 GHz 仅作为通用 X 波段文本定义；数值字段留空 | WGS 支持固定、可搬移、地面、空中和舰载终端 | 仅表示业务类别，不是 WGS 转发器或上下行实际范围 |
| WGS Ka-band 业务类别 | 27-40 GHz 仅作为通用 Ka 波段文本定义；数值字段留空 | 高容量骨干及广播业务 | 仅表示业务类别；规划模型还需考虑雨衰、波束和终端能力 |
| UAS CNPC 公共规划参考 | 5030-5091 MHz | 非隔离空域安全控制与非载荷通信 | 面向未来的公共规划频段，不是伊拉克/阿富汗作战频率 |
| 航空/UAS 试验遥测参考 | 2200-2290 MHz | 飞行试验遥测、高分辨率视频和无人飞行器测试 | 试验业务频段，不代表作战无人机飞控或载荷链路 |

### 第二批对平台数据模型的直接影响

- 雷达必须作为“高功率发射任务 + 接收保护对象”建模，字段至少包括工作时段、搜索扇区、覆盖距离、保护区、机动性和证据状态。
- 卫星链路必须拆分上行、下行、波束和带宽资源；系统支持某频段类别，不等于该频段整体可分配。
- 无人机必须拆分安全飞控链路、载荷数据链路和试验遥测，三者的保障等级、带宽和失效影响不同。
- 每条参数需保留 `frequency_scope`、`source_ids`、披露状态和证据等级；规划器只能把经过授权或人工确认的记录转换为可用规则。
- `case_links` 只允许填写现有 `CASE-*` 编号；时代背景、能力背景和共存背景统一放入 `baseline_context`，避免形成虚假战例关联。

## 第三批：2016-2026 近十年战例与演训样例

| 战例/样例 | 类型 | 公开事实与主要问题 | 对平台的需求映射 |
| --- | --- | --- | --- |
| 摩苏尔战役 / Operation Eagle Strike（2016-2017） | 实战行动 | 城市频谱拥塞且持续变化；UAS/C-UAS快速演进；部分C-UAS能力会同时影响友军和对手系统 | 城市遮挡、高密度发射源、友军干扰、UAS/C-UAS联动、保护区和阶段化重筹 |
| OIR叙利亚受干扰环境（2018） | 实战行动 | 空军执行通信对抗任务；公开审计材料指出通信链路曾在强电子干扰环境下反复受影响 | PACE多链路、链路失效事件、任务降级、恢复时间、重传和连续性 |
| 喀布尔撤离 / Operation Allies Refuge（2021） | 非战斗人员撤离 | 美军接管机场空管并组织17天昼夜空运；高峰期约每34分钟一架军机离场，多国和商业航空同时参与 | 高密度时隙、机场局部拥塞、航空链路优先级、节点突增、威胁与医疗事件重筹 |
| 红海防空与护航 / Operation Prosperity Guardian（2023-2024公开资料截点） | 实战行动 | 狭窄繁忙航道中的多国护航、商船持续双向通信以及无人机/导弹/无人艇威胁；行动建立前的USS Carney先导交战持续约10小时 | 舰船机动、传感器覆盖重叠、多目标突发、多国互操作、商军通信隔离和防空优先级 |
| OIR基地反无人机部署（2023-2024） | 实战行动 | Q-50/Q-53/Q-64与FAAD C2、联合数据网形成多传感器态势；专业人员、承包保障和操作员数量构成约束 | 传感器覆盖、融合节点容量、近实时数据、操作员负荷、固定/机动防护和序列威胁 |
| Project Convergence Capstone 4（2024） | 联合实验，非实战 | 超过4000名参与者使用现役、实验和商业通信方法组成混合网络，验证跨军种和多国数据交换 | 异构网络、带宽受限、伙伴接入、数据优先级、节点失联和传感器-效应器动态匹配 |

第三批在工作簿中新增 `case_type`、`phase_model`、`dynamic_events` 和战例级 `source_ids`。其中任务阶段用于生成仿真骨架，不等同于历史行动时间表；演训事件必须标记为 `joint_experiment`。

## 第三批公开参数

| 系统/业务 | 公开频率信息 | 其他公开参数 | 数据边界 |
| --- | --- | --- | --- |
| AN/PRC-158 | 数值调谐范围未公开 | 双通道；窄带最高10 W、SATCOM/宽带最高20 W；UHF SATCOM支持5/25 kHz频道类别 | 只保存能力和公开上限，不保存网络预置、跳频或任务频道 |
| MUOS频段A | 243.525-270.050 MHz | WCDMA与传统UHF兼容 | 与频段B分条保存；不推定上下行方向和频道计划 |
| MUOS频段B | 280-320 MHz | GAO称系统容量可较传统系统提高约10倍 | 不能与频段A合并成连续范围；10倍不是单用户保证速率 |
| AN/TPQ-50 | 仅公开L波段类别，数值字段留空 | 360度；条令定位范围0.5-10 km；ODIN称最高约15 km取决于目标和轨迹 | ODIN的1200 W是供电需求，不是射频功率 |
| KuRFS | 仅公开Ku波段类别，数值字段留空 | 360度；固定、半固定或车载；支持C-UAS探测与效应器引导 | 不写入通用Ku波段边界、探测门限和电子攻击参数 |
| AN/SPY-6(V)1 | 仅公开S波段类别，数值字段留空 | 四阵面、每阵37个RMA；公开相对灵敏度SPY+16 dB | 相对能力不是绝对接收门限，不与特定红海参战舰艇绑定 |
| DoD混合SATCOM | 无统一频率范围 | 终端、地面站、卫星、网络和用户的多路径组合 | 用于资源编排模型，不代表容量或频段已经获得授权 |
| AN/PRC-160 | 1.6-60 MHz | 宽带HF；公开最高数据率120 kbit/s | 速率是能力上限；实际链路取决于传播、时段和天线条件 |

当前工作簿共包含 **11个战例/演训样例、27条公开参数和46个来源**。所有新增参数均具有 `frequency_scope`，只有设备范围或公开系统范围可保存数值；`category_only` 记录强制保持起止频率为空。

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
13. U.S. Army ODIN, *AN/TPQ-53 Counterfire Target Acquisition Radar*: https://odin.t2com.army.mil/WEG/Asset/6ea3c7edc1d7b3bab022f375761f3ee6
14. U.S. Army Acquisition, *U.S. Army Acquisition Program Portfolio 2024*: https://api.army.mil/e2/c/downloads/2024/07/19/ab2038a9/u-s-army-portfolio-2024.pdf
15. NTIA, *2700-2900 MHz Federal Spectrum Use Report*: https://www.ntia.gov/files/ntia/publications/compendium/2700.00-2900.00_01MAR14.pdf
16. NTIA, *2900-3100 MHz Federal Spectrum Use Report*: https://www.ntia.gov/files/ntia/publications/compendium/2900.00-3100.00_01MAY15.pdf
17. NTIA, *225-328.6 MHz Federal Spectrum Use Report*: https://www.ntia.gov/files/ntia/publications/compendium/0225.00-0328.60_01MAR14.pdf
18. U.S. Space Force, *Wideband Global SATCOM Satellite Fact Sheet*: https://www.spaceforce.mil/about-us/fact-sheets/article/2197740/wideband-global-satcom-satellite/
19. U.S. Army, *Operating in a Denied, Degraded, and Disrupted Space Operational Environment Handbook*: https://api.army.mil/e2/c/downloads/2023/01/19/7f7281ee/18-28-operating-in-a-denied-degraded-and-disrupted-space-operational-environment-handbook-jun-18-public.pdf
20. NTIA, *5030-5250 MHz Spectrum Compendium*: https://www.ntia.gov/files/ntia/publications/compendium/5030.00-5250.00-02092021.pdf
21. FAA, *Integration of Civil UAS in the National Airspace System Roadmap*: https://www.faa.gov/sites/faa.gov/files/uas/resources/policy_library/Second_Edition_Integration_of_Civil_UAS_NAS_Roadmap_July%25202018.pdf
22. NTIA, *2200-2290 MHz Federal Spectrum Use Report*: https://www.ntia.gov/files/ntia/publications/compendium/2200.00-2290.00_01MAY15.pdf
23. U.S. Department of Defense / NTIA, *DoD 4400-4940 MHz Band Assessment*: https://www.ntia.gov/sites/default/files/publications/dodassessment_0.pdf
24. U.S. Army Acquisition Support Center, *Acquisition partnership to roll out new improved Sentinel Radar*: https://asc.army.mil/web/access-acquisition-partnership-to-roll-out-new-improved-sentinel-radar/
25. U.S. Army TRADOC, *Mosul Study Group: What the Battle for Mosul Teaches the Force*: https://api.army.mil/e2/c/downloads/2023/01/19/e9325e8b/17-24u-mosul-study-group-what-the-battle-for-mosul-teaches-the-force-sep-17-public.pdf
26. U.S. Air Force, *Compass Call dominates OIR with electronic warfare*: https://www.af.mil/News/Features/Article/1295655/compass-call-dominates-oir-with-electronic-warfare/
27. GAO-21-64, *Electromagnetic Spectrum Operations*: https://www.gao.gov/assets/gao-21-64.pdf
28. U.S. Department of Defense / USTRANSCOM, *Transportation Command Aids in Historic Evacuation*: https://www.defense.gov/News/News-Stories/Article/Article/2764916/transportation-command-aids-in-historic-evacuation/
29. U.S. Department of State / Department of Defense, *Joint Statement on Afghanistan*: https://www.defense.gov/News/Releases/Release/Article/2732053/joint-statement-from-the-department-of-state-and-department-of-defense-update-o/
30. U.S. Department of Defense / NAVCENT, *Press Briefing on Operation Prosperity Guardian*: https://www.defense.gov/News/Transcripts/Transcript/Article/3631484/navcent-commander-vice-admiral-brad-cooper-holds-an-off-camera-on-the-record-pr/
31. U.S. Department of Defense / U.S. Navy, *Navy's Top Officer Credits Training and Logistics With Meeting Red Sea Mission*: https://www.defense.gov/News/News-Stories/Article/Article/3723681/navys-top-officer-credits-training-logistics-with-meeting-red-sea-mission/
32. U.S. Navy, *USS Carney: a Destroyer at War*: https://www.navy.mil/Press-Office/News-Stories/display-news/Article/3984206/uss-carney-a-destroyer-at-war/
33. U.S. Department of Defense / U.S. Army, *Network Capability Provides Successful Start to Project Convergence Capstone 4*: https://www.defense.gov/News/News-Stories/Article/Article/3692858/network-capability-provides-successful-start-to-project-convergence-capstone-4/
34. U.S. Army CPE C2IN, *Handheld, Manpack and Small Form Fit*: https://peoc3n.army.mil/Organizations/PM-Tactical-Radios/Handheld-Manpack-and-Small-Form-Fit/
35. U.S. Army, *ATP 6-02.53 Techniques for Tactical Radio Operations*: https://rdl.train.army.mil/catalog-ws/view/100.ATSC/0C45D378-25E0-438E-8881-749EF51DE080-1452191121290/atp6_02x53.pdf
36. NTIA, *225-328.6 MHz Federal Spectrum Use Report*: https://www.ntia.gov/files/ntia/publications/compendium/0225.00-0328.60_21NOV14.pdf
37. GAO-21-105283, *Satellite Communications*: https://www.gao.gov/products/gao-21-105283
38. U.S. Army ODIN, *AN/TPQ-50 American Counterfire Radar System*: https://odin.t2com.army.mil/WEG/Asset/c57802f406c1c9733314e686c6be00ea
39. U.S. Army, *PB 2023 Firefinder RDT&E Justification*: https://www.asafm.army.mil/Portals/72/Documents/BudgetMaterial/2023/Base%20Budget/rdte/vol_2-Budget_Activity_5C.pdf
40. U.S. Army Military Review, *Advancing the U.S. Army's Counter-UAS Mission Command Systems*: https://www.armyupress.army.mil/Journals/Military-Review/English-Edition-Archives/May-June-2024/MJ-24-Modern-Warfare/
41. U.S. Navy, *Air and Missile Defense Radar Fact File*: https://www.navy.mil/Resources/Fact-Files/Display-FactFiles/Article/2166758/air-and-missile-defense-radar-amdr/
42. U.S. Navy, *FY 2018 Shipbuilding and Conversion Budget*: https://www.secnav.navy.mil/fmc/fmb/Documents/18pres/SCN_Book.pdf
43. GAO-25-107034, *DOD Satellite Communications*: https://files.gao.gov/reports/GAO-25-107034/index.html
44. U.S. Army Military Review, *C-UAS Operations*: https://www.armyupress.army.mil/Portals/7/military-review/Archives/English/JA-24/C-UAS%20Operations/C-UAS-Operations-UA.pdf
45. U.S. Army Armor, *Adapting to Multi-Domain Battlefield: Developing Emissions Control SOP*: https://www.lineofdeparture.army.mil/Journals/Armor/Armor-Archive/Spring-2025-Edition/Adapting-to-the-Multi-Domain-Battlefield/
46. U.S. Army CPE C2IN, *Helicopter and Multi-Mission Radios*: https://peoc3n.army.mil/Organizations/PM-Tactical-Radios/Helicopter-and-Multi-Mission-Radios/

## 下一批需要补充

- 将摩苏尔、喀布尔撤离、OIR基地反无人机和红海护航转换为可导入的任务模板，使用合成节点和 `SIM-*` 频率。
- 增加 Northern Edge 23-2、Valiant Shield 24 和 RIMPAC 24 演训样例，重点验证真实公开的链路中断、空中中继和多阶段资源竞争。
- 补充公开的接收机抗干扰、频率-距离隔离和保护区规则，形成确定性冲突评估输入。
- 为每个模板建立“公开事实字段”和“仿真假设字段”双层结构，禁止算法将能力范围直接当作授权资源。

# 战场智能用频筹划平台

这是一个本地 Web 版“任务驱动 + 规则约束 + 确定性规划 + 智能决策辅助”的战场用频筹划平台。

第一阶段目标是先形成完整闭环：任务输入、频谱资源建模、规则校验、自动规划、干扰风险评估、动态重筹、多方案对比、报告导出和版本留痕。

## 第一阶段功能

- 任务筹划工作台：从零维护任务信息、任务阶段、时段地域、任务单元、装备组和任务链路。
- 任务单元管理：支持逐项增删改、作战/演训样例生成、参数化样例和 Excel 导入。
- 装备组管理：维护装备类型、数量、带宽、功率、优先级、机动属性和任务归属。
- 数据整体导入：任务单元、装备组和频谱规则三表跨表校验并在单个事务中提交。
- 频谱规则管理：维护可用、禁用、保护、固定占用等频段规则。
- 频谱资源管理：维护可用频段、固定占用、临时占用、保护频段和禁用频段，支持用途、区域、时段、步进、功率和兼容设备约束。
- 资源可用性热力图：按查询时刻和区域计算频段覆盖、主导占用类型与可用率，为规划和重筹提供资源底图。
- 自动用频规划：按任务保障、干扰最低、带宽节约、高优先级装备优先等目标生成方案。
- 干扰风险评估：输出同频、邻频、保护间隔、高功率近距、任务竞争和三阶互调风险，并提供冲突链路图、筛选、风险评分与三步解释链。
- 可视化总览：展示任务保障率、频段占用、空间态势联动、任务保障矩阵。
- 动态重规划：支持禁用频段、补充可用频段、提高优先级、锁定任务或装备后重筹。
- 多方案对比：批量试算不同目标与约束模板，给出推荐方案和取舍理由。
- 报表与留痕：导出 HTML 报告、Excel 结果，保留规划版本、审计日志和能力验收状态。

## 快速启动

后端：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

访问：

```text
http://127.0.0.1:5173
```

## 第一阶段验收

能力清单接口：

```text
GET http://127.0.0.1:8000/api/phase-one-capabilities
```

端到端验收测试：

```powershell
.\.venv\Scripts\python -m pytest
```

核心验收链路：

1. 创建项目。
2. 生成样例任务场景。
3. 校验任务单元、装备组和频谱规则。
4. 执行自动用频规划。
5. 查看频谱占用、任务保障矩阵和干扰风险。
6. 执行多策略对比。
7. 执行动态重规划或多策略试算。
8. 导出报告和 Excel。
9. 查看版本审计与能力基线。

## 主要接口

- `POST /api/projects`
- `GET /api/phase-one-capabilities`
- `GET /api/task-objectives`
- `GET /api/task-scenarios`
- `POST /api/projects/{id}/generate-task-demo`
- `GET|PUT /api/projects/{id}/task-mission`
- `GET|POST /api/projects/{id}/task-phases`
- `GET|POST /api/projects/{id}/task-units`
- `GET|POST /api/projects/{id}/equipment-groups`
- `GET|POST /api/projects/{id}/task-links`
- `POST /api/projects/{id}/import-task-package`
- `POST /api/projects/{id}/upload-task-units`
- `POST /api/projects/{id}/upload-equipment-groups`
- `POST /api/projects/{id}/upload-spectrum-rules`
- `GET|POST /api/projects/{id}/spectrum-resources`
- `PUT|DELETE /api/projects/{id}/spectrum-resources/{row_id}`
- `GET /api/projects/{id}/spectrum-resource-heatmap`
- `POST /api/projects/{id}/validate-task`
- `POST /api/projects/{id}/task-plan`
- `GET /api/projects/{id}/task-visualization`
- `POST /api/projects/{id}/task-compare`
- `POST /api/projects/{id}/task-strategy-trials`
- `POST /api/projects/{id}/task-replan-preview`
- `POST /api/projects/{id}/task-replan`
- `GET /api/projects/{id}/task-report`
- `GET /api/projects/{id}/task-export.xlsx`
- `GET /api/projects/{id}/task-versions`
- `GET /api/projects/{id}/task-agent-assessment`

## LLM 配置

默认没有配置模型时，系统使用本地模板解释器，仍可完成完整规划闭环。

如需接入 OpenAI 兼容接口，可设置：

```powershell
$env:OPENAI_COMPAT_API_KEY="..."
$env:OPENAI_COMPAT_BASE_URL="https://api.openai.com/v1"
$env:OPENAI_COMPAT_MODEL="gpt-4o-mini"
```

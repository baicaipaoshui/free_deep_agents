# IAV AI Safety Platform — FuSa 多智能体编排器

> 基于 DeepAgents 的 ISO 26262 功能安全分析平台
> 技术栈：Python + FastAPI + DeepAgents/LangGraph + Dify(RAG) + Next.js

## 架构概览

```
用户请求
  └─ Next.js 前端 (port 3000)
       └─ FastAPI 后端 (port 8000)
            └─ 编排器 [create_deep_agent]
                 ├─ SkillsMiddleware  → skills/common/
                 ├─ MemoryMiddleware  → AGENTS.md
                 ├─ SubAgentMiddleware
                 │    ├─ hara_analyst  → skills/hara/
                 │    ├─ fmea_analyst  → skills/fmea/
                 │    └─ fta_analyst   → skills/fta/
                 └─ FilesystemMiddleware → CompositeBackend
                      ├─ StateBackend (临时)
                      └─ StoreBackend /reports/ (持久化)
```

## 快速开始

### 1. 启动基础设施

```bash
cd iav-fusa-platform
cp backend/.env.example backend/.env
# 编辑 .env，填入 ANTHROPIC_API_KEY 等必要配置

docker-compose up -d postgres redis minio dify
```

### 2. 启动后端

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000 → 项目列表页面。

## 目录结构

```
iav-fusa-platform/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 环境变量配置
│   │   ├── api/                 # REST + WebSocket 路由
│   │   │   ├── projects.py      # 项目 CRUD
│   │   │   ├── analysis.py      # 分析会话 + WebSocket 流
│   │   │   └── approval.py      # 人工审批门
│   │   ├── agent/
│   │   │   ├── orchestrator.py  # create_deep_agent() 编排器
│   │   │   ├── subagents.py     # HARA/FMEA/FTA SubAgent 定义 + Tools
│   │   │   └── graphs/          # LangGraph CompiledSubAgent 流水线
│   │   │       ├── hara_pipeline.py   # 6 阶段 + ASIL 审批门
│   │   │       ├── fmea_pipeline.py   # 4 阶段 + RPN 审批门
│   │   │       └── fta_pipeline.py    # 4 阶段 + 逻辑校验循环
│   │   ├── hooks/
│   │   │   └── safety_hooks.py  # asil_gate, rpn_gate, fta_xref
│   │   ├── models/
│   │   │   └── schemas.py       # Pydantic 数据模型
│   │   └── router/
│   │       └── intent.py        # 两级意图路由
│   ├── skills/                  # SkillsMiddleware 加载的 SKILL.md
│   │   ├── common/              # 通用 FuSa 技能
│   │   ├── hara/                # HARA 专用技能 (6 个)
│   │   ├── fmea/                # FMEA 专用技能 (4 个)
│   │   └── fta/                 # FTA 专用技能 (3 个)
│   ├── knowledge-base/          # 导入 Dify 的原始文档
│   ├── AGENTS.md                # MemoryMiddleware 项目记忆
│   └── pyproject.toml
├── frontend/
│   ├── app/
│   │   ├── projects/            # 项目列表页
│   │   ├── analysis/[id]/       # 分析工作台
│   │   ├── approval/            # 人工审批队列
│   │   └── knowledge/           # 知识库管理
│   ├── components/
│   │   ├── AgentPanel.tsx       # WebSocket 实时流输出
│   │   ├── PipelineProgress.tsx # 流水线阶段可视化
│   │   └── ApprovalDialog.tsx   # 人工审批对话框
│   └── lib/api.ts               # API 客户端
└── docker-compose.yml           # PostgreSQL + Redis + MinIO + Dify
```

## 关键设计决策

| 决策 | 原则 |
|------|------|
| 不 fork DeepAgents | 只通过公开 API 扩展，零侵入 |
| RAG 用 `@tool` | Agent 自主决定何时检索，比 Middleware 注入更灵活 |
| Skills 用原生 SKILL.md | 与 `SkillsMiddleware` 格式完全对齐 |
| 安全门 = LangGraph 条件边 | `awaiting_approval` 状态字段 + 条件路由 |
| CompiledSubAgent = 严格流程 | 6/4 阶段顺序不可跳过，适用 HARA/FMEA/FTA |

## 人工审批门

| 门类型 | 触发条件 | 处理方式 |
|--------|---------|---------|
| `asil_gate` | S/E/C/O 评估完成 | 人工确认 ASIL 定级后继续 |
| `rpn_gate` | RPN > 阈值（默认 100） | 人工审核高风险失效模式 |
| `fta_logic_check` | AND/OR 门子节点 < 2 | 自动重跑分解阶段（最多 3 次） |
| `fta_xref_fmea` | 底事件无 FMEA 对应 | 告警，不阻塞流程 |

## 环境变量

参考 `backend/.env.example`。核心变量：

- `DEEPAGENTS_MODEL`: LLM 模型（默认 `anthropic:claude-sonnet-4-6`）
- `ANTHROPIC_API_KEY`: Anthropic API Key
- `DIFY_API_URL` / `DIFY_API_KEY`: Dify RAG 服务
- `LANGSMITH_API_KEY`: LangSmith 审计追踪
- `RPN_THRESHOLD`: FMEA RPN 人工审批阈值（默认 100）

# FuSa DeepAgents Workspace

该仓库已按 [设计架构文档](./设计架构文档.md) 收敛，只保留与 `IAV AI Safety Platform` 实现直接相关的内容。

## 保留结构

```txt
.
├── apps/
│   └── iav-fusa-platform/   # FuSa 多智能体应用（FastAPI + Next.js）
├── libs/
│   ├── deepagents/          # DeepAgents SDK 源码
│   └── cli/                 # 设计文档中引用的 Hooks / Skills 参考实现
├── AGENTS.md
└── 设计架构文档.md
```

## 目录说明

- `apps/iav-fusa-platform`：设计文档中的目标应用，实现 HARA / FMEA / FTA 编排、技能、Hooks 和前后端页面。
- `libs/deepagents`：应用依赖的本地 DeepAgents SDK。
- `libs/cli`：设计文档中提到的 CLI Hooks、内置 Skills 和相关参考实现。

## 说明

已移除与该设计实现无直接关系的示例项目、ACP、评测套件、合作方集成以及发布流水线配置。

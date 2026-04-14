# IAV AI Safety Platform — FuSa 多智能体编排器

## 项目背景
- **项目名称**: IAV AI Safety Platform
- **系统**: 功能安全分析多智能体平台（HARA / FMEA / FTA）
- **适用标准**: ISO 26262:2018 2nd Edition
- **范围**: 面向整车功能安全开发全生命周期的 AI 辅助分析

## 架构约束
- 所有安全分析必须基于 DeepAgents 的 SubAgentMiddleware + SkillsMiddleware
- RAG 检索通过 Dify Knowledge API 封装为标准 `@tool`，不使用 Middleware
- 关键节点（ASIL 定级、高 RPN 失效模式）必须经过人工审批门
- 全链路审计通过 LangSmith tracing 实现

## 子代理清单
- **hara_analyst**: HARA 危害分析与风险评估（ISO 26262 Part 3）
- **fmea_analyst**: FMEA 失效模式与影响分析（ISO 26262 Part 5 + AIAG-VDA）
- **fta_analyst**: FTA 故障树分析（ISO 26262 Part 9 + IEC 61025）

## 开发原则
- 不 fork DeepAgents 核心代码，只通过公开 API 扩展
- SubAgent 各自加载专属 SKILL.md，skills/ 目录是领域知识的唯一来源
- 安全门通过 hooks/safety_hooks.py + LangGraph 条件边实现

## 审批流程
1. ASIL 定级前：人工确认 S/E/C/O 评估（asil_gate_hook）
2. RPN > 阈值时：人工审核高风险失效模式（rpn_gate_hook）
3. FTA 逻辑错误时：自动重跑分解阶段（fta_logic_check_hook）
4. 底事件未映射 FMEA 时：告警通知工程师（fta_xref_fmea_hook）

---
name: safety-case
description: "Safety Case 构建：GSN 论证结构、证据收集、审计追踪"
---

# Safety Case 构建

## 触发条件
当用户讨论 Safety Case、GSN（Goal Structuring Notation）、安全论证、证据管理时激活。

## 方法论

### GSN 元素
- **目标（Goal）**: 需要论证的安全声明
- **战略（Strategy）**: 如何分解目标
- **解决方案（Solution）**: 具体证据项
- **背景（Context）**: 适用约束条件
- **假设（Assumption）**: 未验证前提

### Safety Case 结构模板
```
G1: [系统名称] 在 [工况范围] 内满足 ISO 26262 ASIL-X 要求
  S1: 通过 HARA → 安全目标 → 功能安全概念分解论证
    G2: HARA 已识别所有相关危害
      Sn1: HARA 报告 v{版本}
    G3: 安全目标覆盖所有 ASIL-X 危害
      Sn2: 安全目标清单 v{版本}
```

### 审计追踪要求
每个证据项必须包含：
- 文档 ID、版本号、创建日期
- 作者与审核人员
- 关联的危害/安全需求 ID
- LangSmith trace ID（AI 辅助生成的内容）

## 参考标准
ISO 26262-2:2018, Clause 6; ISO/IEC 15026-2

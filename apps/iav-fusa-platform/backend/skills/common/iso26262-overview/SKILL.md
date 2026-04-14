---
name: iso26262-overview
description: "ISO 26262 全生命周期概览：功能安全开发流程、关键术语、文档要求"
---

# ISO 26262 全生命周期概览

## 触发条件
当用户提到 ISO 26262、功能安全、FuSa、安全开发流程，或询问标准概述时激活。

## 方法论

### 标准结构
ISO 26262:2018 共 12 个部分：
- **Part 1**: 词汇
- **Part 2**: 功能安全管理
- **Part 3**: 概念阶段（HARA、安全目标、FSC）
- **Part 4**: 产品开发：系统级
- **Part 5**: 产品开发：硬件级
- **Part 6**: 产品开发：软件级
- **Part 7**: 生产与运营
- **Part 8**: 支持过程
- **Part 9**: ASIL 面向方法与安全分析
- **Part 10**: 指南
- **Part 11**: 半导体
- **Part 12**: 摩托车

### 开发 V 模型
```
Item Definition
    └─ HARA → Safety Goals → FSC
           └─ System Design
                  ├─ HW Design → HW Integration Test
                  └─ SW Architecture → SW Unit Test → SW Integration Test
                         └─ System Integration Test
                                └─ Validation
```

### ASIL 等级
QM < ASIL-A < ASIL-B < ASIL-C < ASIL-D（最高安全完整性要求）

## 参考标准
ISO 26262:2018 全部 12 部分

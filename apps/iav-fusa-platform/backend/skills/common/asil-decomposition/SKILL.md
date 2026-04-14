---
name: asil-decomposition
description: "ASIL 分解规则：将高 ASIL 要求分解到独立冗余通道"
---

# ASIL 分解

## 触发条件
当用户讨论 ASIL 分解、冗余设计、独立通道、ASIL-D(ASIL-B+ASIL-B) 时激活。

## 方法论

### 分解规则
ASIL 分解将单一 ASIL-X 要求分配给两个独立、充分独立的元素：

| 原始 ASIL | 分解方案 A     | 分解方案 B     |
|-----------|----------------|----------------|
| ASIL-D    | ASIL-C + ASIL-A | ASIL-B + ASIL-B |
| ASIL-C    | ASIL-B + ASIL-A | ASIL-A + ASIL-B |
| ASIL-B    | ASIL-A + ASIL-A | ASIL-A + QM     |
| ASIL-A    | QM + QM        | —              |

### 独立性要求
分解成立的前提：两个元素必须满足**充分独立性**（sufficient independence）：
1. **空间独立性**：不共用相同硬件资源
2. **时间独立性**：不相互影响执行时序
3. **共因失效（CCF）分析**：需证明 β 因子满足要求

### 分解标注
分解后，每个元素的 ASIL 标注为 `ASIL-X(d)`，括号中的 `d` 表示已分解。

## 参考标准
ISO 26262-9:2018, Clause 5

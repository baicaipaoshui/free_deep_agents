---
name: fta-top-event
description: "Stage 1：顶事件定义——从 HARA 安全目标或用户描述中提取顶事件，填充 FTAState.top_event 和根节点 FaultTreeNode"
---

# Stage 1 — `define_top_event`

## 职责

从 HARA 安全目标（或用户指定的危险场景）中确定故障树的顶事件（Undesired Top-Level Event）。
填充 `FTAState.top_event`（字符串）和 `FTAResult.top_event`，并生成根节点 `FaultTreeNode`（`node_type="top_event"`）。

## 顶事件选择准则

**来源优先级：**
1. **HARA 安全目标违反（推荐）**：选取 ASIL-C 或 ASIL-D 的安全目标作为顶事件
   - 安全目标描述"不得发生"的事件即为顶事件
   - 示例：SG-EPS-001 "EPS 不得意外施加反向力矩" → 顶事件 = "EPS 意外施加反向力矩"
2. **HARA 危险事件**：直接使用 `HARAState.hazards` 中的危险事件描述
3. **用户指定**：用户直接描述的不希望发生的系统级事件

**顶事件命名格式：**
```
[系统名称] 在 [工况/前提条件] 下 [发生什么不希望的行为]
```

**示例：**
- `EPS 在车辆行驶时意外施加与驾驶员意图相反的转向力矩`
- `AEB 在无障碍物情况下意外触发紧急制动`
- `发动机油门控制系统在驾驶员松开油门后持续维持高油门状态`

## 必须明确的边界条件

在顶事件描述中或附注中明确：

| 边界要素 | 说明 | 示例 |
|---------|------|------|
| **系统前提状态** | 分析成立的系统状态 | 点火ON、车速>20 km/h、EPS功能激活 |
| **时间窗口** | 对应 HARA 的 FTTI | 在 150 ms 内发生 |
| **分析范围** | 包含和排除的组件 | 包含 EPS 电控部分；排除方向盘机械结构 |
| **环境条件** | 适用的工况 | 正常行驶工况，不含电磁极端干扰 |

## 与 HARA 安全目标的对应关系表

| HARA 安全目标 | FTA 顶事件 | ASIL |
|-------------|-----------|------|
| SG-EPS-001：EPS 不得意外施加反向力矩 | EPS 意外施加反向转向力矩 | ASIL-D |
| SG-EPS-002：EPS 不得因辅助失效导致方向失控 | EPS 转向辅助完全丧失且持续超过 FTTI | ASIL-C |
| SG-AEB-001：AEB 不得误激活 | AEB 在无制动需求场景触发制动 | ASIL-B |

## 根节点 FaultTreeNode 格式

```json
{
  "id": "TE-001",
  "label": "EPS意外施加反向转向力矩",
  "description": "在车辆正常行驶（车速>20 km/h，点火ON）时，EPS 向转向系统施加与驾驶员意图相反的力矩，持续时间超过 100 ms（FTTI）。分析范围：EPS 电控系统（传感器→ECU→电机驱动器），不含机械转向机。",
  "node_type": "top_event",
  "children": [],
  "probability": null,
  "fmea_ref": null
}
```

**注意：** 根节点的 `children` 在 Stage 2 逻辑门分解完成后填充（通常为第一层 OR 门或 AND 门节点的 ID）。

## FTAResult.top_event 字段

填写顶事件的简洁字符串描述（对应 `FTAResult.top_event` 字段）：
```
"EPS 在驾驶员正常行驶时意外施加与驾驶意图相反的转向力矩，导致车辆偏航"
```

## 多顶事件处理

若需分析多个安全目标（如完整系统 FTA），每个安全目标对应独立的故障树（各自有独立的 TE ID 和完整树结构）。优先分析 ASIL 最高的安全目标。

## 完成标志

回复中标注 `[FTA Stage 1 完成]`，输出根节点 FaultTreeNode JSON 和 FTAResult.top_event 字符串，以及边界条件说明。

## 参考标准

IEC 61025:2006, Clause 5（Top event definition）；ISO 26262-9:2018, Clause 8.4.1

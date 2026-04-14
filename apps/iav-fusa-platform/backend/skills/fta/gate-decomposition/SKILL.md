---
name: fta-gate-decomposition
description: "Stage 2：AND/OR 逻辑门递归分解——构建 FaultTreeNode 层次树，满足校验规则（每门≥2子节点），支持重迭代修正"
---

# Stage 2 — `decompose_gates`（支持重迭代）

## 职责

从顶事件出发，自顶向下递归分解，使用 AND/OR 逻辑门构建完整故障树。
填充 `FTAState.fault_tree`（dict） 和 `FTAResult.fault_tree`（list）。

**重要：** 若 Stage 4 逻辑校验发现错误（`needs_rework=True`），本阶段将重新执行。
迭代计数在 `FTAState.rework_iterations` 中记录，最多 3 次迭代。
每次迭代开始时标注 `[FTA Stage 2 第N次迭代]`。

## 门类型选择决策树

```
问：若子事件A失效，在没有子事件B失效的情况下，顶事件/父事件是否会发生？
  ├─ 是 → 使用 OR 门（串联，单点即可触发）
  └─ 否 → 问：只有当A和B同时失效时，父事件才会发生吗？
               ├─ 是 → 使用 AND 门（并联/冗余，需要多点同时失效）
               └─ 否 → 重新审视系统架构，可能需要拆分中间事件
```

## AND 门详解（`"node_type": "and_gate"`）

**适用场景：** 系统具有冗余保护，单一失效不足以导致父事件。

典型模式：
- **1oo2 冗余**：主传感器失效 AND 备用传感器失效
- **诊断屏蔽**：硬件失效 AND 诊断功能失效（无法检测）
- **时序条件**：失效发生 AND 发生在 FTTI 内（时间窗口）
- **Lockstep 失效**：Core 0 失效 AND Core 1 失效（双核互检系统）

示例节点：
```json
{
  "id": "AND-001",
  "label": "AND门：双传感器同时失效",
  "description": "主扭矩传感器（TAS-A）失效 AND 冗余扭矩传感器（TAS-B）失效，2oo2 表决逻辑无法检测",
  "node_type": "and_gate",
  "children": ["BE-001", "BE-002"],
  "probability": null,
  "fmea_ref": null
}
```

## OR 门详解（`"node_type": "or_gate"`）

**适用场景：** 任一失效路径独立导致父事件，无冗余保护。

典型模式：
- **串联系统**：组件 A 失效 OR 组件 B 失效 OR 组件 C 失效
- **多失效原因**：同一失效模式的不同根本原因
- **软件 + 硬件路径**：软件错误 OR 硬件失效（各自独立触发）

示例节点：
```json
{
  "id": "OR-001",
  "label": "OR门：力矩命令来源异常",
  "description": "以下任一原因均可导致 ECU 输出异常力矩命令",
  "node_type": "or_gate",
  "children": ["IE-001", "IE-002", "BE-008"],
  "probability": null,
  "fmea_ref": null
}
```

## 中间事件（`"node_type": "intermediate_event"`）

可进一步分解的系统/子系统级失效，连接上下层门节点。

```json
{
  "id": "IE-001",
  "label": "传感模块信号异常",
  "description": "传感器模块向 ECU 提供错误的驾驶员力矩信号",
  "node_type": "intermediate_event",
  "children": ["OR-002"],
  "probability": null,
  "fmea_ref": null
}
```

## 底事件（`"node_type": "basic_event"`）

叶节点，不可继续分解。`fmea_ref` 在 Stage 3 填充。

```json
{
  "id": "BE-003",
  "label": "CAN总线消息超时",
  "description": "传感器 CAN 报文连续 3 个周期（30ms）未到达 ECU",
  "node_type": "basic_event",
  "children": [],
  "probability": null,
  "fmea_ref": null
}
```

## 分解深度指南

| 层级 | 典型对象 | 处理方式 |
|------|---------|---------|
| 0（顶事件）| EPS 意外施加反向力矩 | 根节点，连接第一层门 |
| 1（子系统级）| 力矩命令错误 / 传感信号异常 | 中间事件 |
| 2（功能级）| 传感器信号卡死 / ECU 计算错误 | 中间事件或底事件 |
| 3（组件/函数级）| ASIC 芯片失效 / 特定软件函数错误 | 底事件（停止分解）|

## 一致性校验前置自查（防止 Stage 4 触发重迭代）

在完成分解后，**自行检查以下规则**（与 `_check_gate_consistency` 函数一致）：

- [ ] 每个 `and_gate` 节点的 `children` 列表长度 ≥ 2
- [ ] 每个 `or_gate` 节点的 `children` 列表长度 ≥ 2
- [ ] 所有 `children` 中的 ID 在 `fault_tree` 中存在对应节点
- [ ] 无循环引用（任何节点不以自身或其祖先为子节点）
- [ ] 顶事件节点唯一（只有一个 `node_type="top_event"` 节点）

若发现问题，在标注完成前自行修正。

## 故障树 JSON 完整示例（简化）

```json
{
  "TE-001": {
    "id": "TE-001", "label": "EPS意外反向力矩", "node_type": "top_event",
    "children": ["OR-001"], "description": "...", "probability": null, "fmea_ref": null
  },
  "OR-001": {
    "id": "OR-001", "label": "OR门：力矩命令异常原因", "node_type": "or_gate",
    "children": ["IE-001", "IE-002"], "description": "...", "probability": null, "fmea_ref": null
  },
  "IE-001": {
    "id": "IE-001", "label": "传感器信号异常", "node_type": "intermediate_event",
    "children": ["OR-002"], "description": "...", "probability": null, "fmea_ref": null
  },
  "OR-002": {
    "id": "OR-002", "label": "OR门：传感器失效原因", "node_type": "or_gate",
    "children": ["BE-001", "BE-002", "BE-003"], "description": "...", "probability": null, "fmea_ref": null
  },
  "BE-001": {
    "id": "BE-001", "label": "TAS-A信号卡死低端", "node_type": "basic_event",
    "children": [], "description": "...", "probability": null, "fmea_ref": null
  }
}
```

## 完成标志

回复中标注 `[FTA Stage 2 完成]`（或 `[FTA Stage 2 第N次迭代完成]`），
输出完整 fault_tree dict（用于状态填充）和 FaultTreeNode list（用于 FTAResult）。

## 参考标准

IEC 61025:2006, Clause 6（Gate logic）；ISO 26262-9:2018, Clause 8.4.2（Fault tree construction）

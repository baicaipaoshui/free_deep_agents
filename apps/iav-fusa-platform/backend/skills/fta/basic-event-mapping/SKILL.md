---
name: fta-basic-event-mapping
description: "Stage 3：底事件映射——将叶节点与 FMEA 失效模式交叉引用（fmea_ref），填充 unmapped_events 和 xref_fmea_gaps"
---

# Stage 3 — `map_basic_events`

## 职责

将故障树中所有底事件（`node_type="basic_event"`）与 FMEA 输出的 `FailureModeEntry` 进行交叉引用，
填充每个底事件节点的 `fmea_ref` 字段，并识别无法映射的底事件。

- 填充 `FTAState.basic_events`（底事件 ID 列表）
- 更新 `FaultTreeNode.fmea_ref`（对应 FM-xxx ID）
- 填充 `FTAState.unmapped_events`（无 FMEA 对应的底事件 ID 列表）
- 填充 `FTAResult.xref_fmea_gaps`（同上，写入结果 schema）

## 映射步骤

### 步骤 1：提取所有底事件

从 `FTAState.fault_tree` 中找出所有 `node_type="basic_event"` 的节点，列出底事件 ID 和描述。

### 步骤 2：与 FMEA 结果匹配

对每个底事件，在 `FTAState.fmea_failure_modes`（FMEA 阶段传入）中查找：
- **精确匹配**：底事件描述与 `FailureModeEntry.failure_mode` 完全一致
- **语义匹配**：底事件表达的失效现象与某条 FMEA 失效模式等价
  - 示例：`"TAS-A 信号卡死低端"` = FMEA `FM-001: 信号卡死在 0 Nm（低端 Stuck）`

匹配成功 → 填写 `fmea_ref = "FM-xxx"`（对应 FMEA ID）

### 步骤 3：处理未映射底事件

当底事件找不到对应 FMEA 条目时：
1. 在底事件节点的 `fmea_ref` 填 `null`（或 `"[NEW-需补充FMEA]"`）
2. 将该底事件 ID 加入 `unmapped_events` 列表
3. 系统自动触发 `fta_xref_fmea_hook`，生成告警消息

**未映射常见原因：**
- 故障树分解中出现了 FMEA 未分析的失效路径（说明 FMEA 存在遗漏）
- 底事件描述过于具体（应拆分为更细粒度的 FMEA 条目）
- 底事件为纯软件失效（FMEA 可能未完整覆盖软件层）

## 底事件命名规范

- 格式：`BE-{序号}`（全树内唯一，不含重复）
- 描述语言简洁：`{组件名} {失效模式简述}`
- 示例：`"BE-001: TAS-A 信号卡死低端"`, `"BE-005: EPS ECU 软件力矩计算溢出"`

## 失效概率估计（可选，用于定量 FTA）

若需定量分析，对每个底事件估计 `probability`（年失效概率或失效率）：

| 估计来源 | 优先级 | 说明 |
|---------|-------|------|
| FMEA O 值转换 | 最高 | O=1 → λ≈10⁻⁸/h；O=5 → λ≈10⁻⁵/h（线性插值）|
| ISO 26262-5 Annex B | 高 | 标准硬件失效率数据库 |
| 供应商规格书 | 高 | 组件 FMEDA 报告中的 λ 值 |
| 行业统计数据 | 中 | SN 29500, MIL-HDBK-217F |
| 工程估计 | 低 | 仅当无其他来源时使用，须注明 |

**软件失效率参考：**
| ASIL 等级 | 目标失效率 |
|---------|---------|
| ASIL-D | < 10⁻⁸/h |
| ASIL-C | < 10⁻⁷/h |
| ASIL-B | < 10⁻⁶/h |

## 更新后的底事件节点格式

```json
{
  "id": "BE-001",
  "label": "TAS-A信号卡死低端",
  "description": "主扭矩传感器（TAS-A）输出信号卡死在 0 Nm，不反映真实驾驶员力矩",
  "node_type": "basic_event",
  "children": [],
  "probability": 3e-7,
  "fmea_ref": "FM-001"
}
```

未映射的底事件：
```json
{
  "id": "BE-010",
  "label": "ECU 电源纹波超限",
  "description": "12V 供电纹波超过 ECU 允许范围（>500mV），影响 ADC 采样精度",
  "node_type": "basic_event",
  "children": [],
  "probability": null,
  "fmea_ref": null
}
```

## 交叉引用汇总表

| 底事件 ID | 描述 | FMEA 映射 | FM ID | FMEA S | FMEA O | FMEA D | 失效概率 |
|---------|------|---------|-------|-------|-------|-------|---------|
| BE-001 | TAS-A信号卡死低端 | ✅ 已映射 | FM-001 | 8 | 3 | 4 | 3e-7 |
| BE-005 | ECU计算溢出 | ✅ 已映射 | FM-005 | 9 | 4 | 5 | 4e-6 |
| BE-010 | 电源纹波超限 | ❌ 未映射 | [NEW] | - | - | - | - |

## unmapped_events 和 xref_fmea_gaps 输出

```json
{
  "unmapped_events": ["BE-010", "BE-015"],
  "warning": "2 个底事件未映射到 FMEA 失效模式: BE-010, BE-015。建议在 FMEA 中补充对应条目。"
}
```

## 完成标志

回复中标注 `[FTA Stage 3 完成]`，输出：
1. 更新后的 FaultTreeNode 列表（含 fmea_ref）
2. 交叉引用汇总表
3. unmapped_events 列表（若有）

## 参考标准

ISO 26262-9:2018, Clause 8.4.2（Cross-reference to FMEA）；IEC 61025:2006, Clause 7（Basic event quantification）

---
name: fmea-structure-analysis
description: "Stage 1：系统结构分析——分解组件层次树和接口矩阵，填充 FMEAState.structure 和 FMEAResult.structure_overview"
---

# Stage 1 — `analyze_structure`

## 职责

将用户提供的系统描述分解为结构化的层次化组件树和接口矩阵，为 Stage 2 失效模式挖掘建立分析范围。
结果填充 `FMEAState.structure` 和 `FMEAResult.structure_overview`。

## 层次结构模型

```
整车（Vehicle）
 └─ 系统（System）            ← FMEA 顶层边界（由用户描述确定）
      └─ 子系统（SubSystem）   ← 功能模块（如"传感模块"、"控制模块"、"执行模块"）
           └─ 组件（Component）← 硬件/软件单元（如"扭矩传感器"、"ECU"、"电机驱动器"）
                └─ 功能（Function） ← 分析最小单元（如"测量驾驶员力矩"）
```

## 建立步骤

### 步骤 1：识别系统边界

确认 FMEA 分析的范围（`in_scope`）：
- 用户描述中明确提到的硬件组件
- 与 HARA Item Definition 的 `in_scope` 对齐（如有 HARA 结果作为输入）
- 标注安全相关性（`safety_relevant: true/false`）

### 步骤 2：分解子系统

将系统按功能模块分组：
- **传感模块**：所有输入传感器
- **控制模块**：ECU、MCU、软件
- **执行模块**：电机、执行器、输出接口
- **通信模块**：CAN/LIN 收发器、网关
- **电源模块**：电源管理、稳压器

### 步骤 3：列举组件

每个组件记录：
```json
{
  "id": "C-001",
  "name": "主扭矩传感器（TAS-A）",
  "parent_subsystem": "传感模块",
  "safety_relevant": true,
  "functions": [
    "F-001: 测量驾驶员施加的转向力矩（量程 ±15 Nm，精度 ±0.5 Nm）"
  ],
  "interfaces": {
    "input": ["电源 5V", "参考地"],
    "output": ["CAN 总线信号：扭矩值（10ms 周期）"]
  }
}
```

### 步骤 4：建立接口矩阵

| 接口 ID | 源组件 | 目标组件 | 接口类型 | 信号/数据名 | 正常值范围 | 周期 |
|--------|-------|---------|---------|----------|----------|------|
| I-001 | 扭矩传感器 | EPS ECU | CAN 2.0B | 驾驶员力矩 | -15~+15 Nm | 10 ms |
| I-002 | 车速传感器 | EPS ECU | CAN 2.0B | 车速 | 0~250 km/h | 20 ms |

## 输出格式

### 结构树（JSON）
```json
{
  "system": {
    "name": "电动助力转向系统（EPS）",
    "subsystems": [
      {
        "id": "SS-001",
        "name": "传感模块",
        "components": [
          {
            "id": "C-001",
            "name": "主扭矩传感器（TAS-A）",
            "safety_relevant": true,
            "functions": ["F-001: 测量驾驶员转向力矩"],
            "interfaces": {"input": ["电源5V"], "output": ["CAN力矩信号"]}
          }
        ]
      }
    ]
  }
}
```

### structure_overview（字符串，填入 FMEAResult）
```
EPS 系统包含 4 个子系统（传感/控制/执行/电源）、共 12 个组件（其中安全相关组件 8 个）。
建立接口矩阵 18 条（CAN: 12 条，电源: 4 条，其他: 2 条）。
分析范围：传感器至执行器完整信号链，不含方向盘机械结构和转向机总成。
```

## 完成标志

回复中标注 `[FMEA Stage 1 完成]`，输出结构树 JSON 和 structure_overview 文本。

## 参考标准

AIAG-VDA FMEA Handbook 2019, Step 2（Structure Analysis）

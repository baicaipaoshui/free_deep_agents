---
name: hara-item-definition
description: "Stage 1：Item Definition 解析——从用户输入提取系统边界、功能清单、工况范围，填充 HARAState.item_definition"
---

# Stage 1 — `parse_item_definition`

## 职责

从用户自然语言描述中提取结构化系统信息，为后续 5 个阶段建立分析基础。
结果填充到 `HARAState.item_definition`。

## 提取步骤

### 步骤 1：识别系统名称与版本
从输入中提取明确的系统/子系统名称，如"电动助力转向系统（EPS）V2.1"。
若用户未提供版本号，记录为"版本待确认"。

### 步骤 2：定义系统边界
明确三类边界要素：
- **in_scope**：系统内部受控组件和软件（如 ECU、传感器、执行器、嵌入式软件）
- **interfaces**：系统外部接口（传感器信号输入、总线通信 CAN/LIN/以太网、电源）
- **out_of_scope**：不在分析范围内的上下游组件

### 步骤 3：枚举安全相关功能
列举所有安全相关功能，每条记录：
- `id`：功能 ID，格式 F-001、F-002…（项目内唯一）
- `description`：动词+宾语格式（如"提供转向辅助力矩"）
- `conditions`：激活条件（如["点火ON", "车速 < 200 km/h"]）
- `requirements`：性能指标（如["响应时间 < 50 ms", "力矩精度 ±2%"]）

### 步骤 4：确定工况范围

| 工况类别 | 常见示例 |
|---------|---------|
| 正常行驶 | 直线 / 转弯 / 超车 / 跟车 |
| 特殊工况 | 湿滑路面 / 紧急制动 / 爆胎 / 山路 |
| 停车操作 | 平行泊车 / 垂直泊车 / 低速挪车 |
| 启动 / 关机 | 点火过渡 / 熄火过渡 / 系统自检 |

## 输出格式（JSON，嵌入回复）

```json
{
  "system_name": "电动助力转向系统（EPS）V2.1",
  "system_boundary": {
    "in_scope": ["扭矩传感器", "转向角传感器", "EPS ECU", "无刷电机驱动器"],
    "interfaces": ["CAN总线（接收车速/横摆角速度）", "LIN总线（方向盘角度）", "电源12V/48V"],
    "out_of_scope": ["方向盘机械结构", "转向机总成", "悬架系统"]
  },
  "functions": [
    {
      "id": "F-001",
      "description": "提供与驾驶员意图一致的转向辅助力矩",
      "conditions": ["点火ON", "车速 < 200 km/h", "系统自检通过"],
      "requirements": ["响应时间 < 50 ms", "力矩误差 < ±2% 额定值"]
    },
    {
      "id": "F-002",
      "description": "检测系统故障并切换到安全降级模式",
      "conditions": ["任意系统故障触发"],
      "requirements": ["诊断时间 < 10 ms", "降级响应 < 100 ms"]
    }
  ],
  "operational_situations": ["正常行驶", "低速泊车", "紧急制动", "湿滑路面", "系统启动/关机"]
}
```

## 完成标志

回复中标注 `[HARA Stage 1 完成]`，并输出上述 JSON 内容。

## 参考标准

ISO 26262-3:2018, Clause 5（Item definition）

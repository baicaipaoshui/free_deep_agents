---
name: fmea-failure-mining
description: "Stage 2：失效模式挖掘——对每个组件/功能识别失效模式，分析三层影响链，调用 search_knowledge_base，输出 FailureModeEntry 列表"
---

# Stage 2 — `mine_failure_modes`

## 职责

对 Stage 1 输出的每个组件和功能，系统性识别失效模式，并分析局部→子系统→系统三层影响链。
结果填充 `FMEAState.failure_modes`，格式对应 `FailureModeEntry` schema（S/O/D 暂填初始估计，Stage 3 精确计算 RPN）。

## 标准失效模式类别

对每个组件，按所属类别从下表中选取适用的失效模式：

### 传感器类
| 失效模式 | 含义 |
|---------|------|
| 信号超出范围（High Stuck / Low Stuck） | 输出值超过正常范围上限或卡在下限 |
| 信号漂移（Signal Drift） | 信号缓慢偏离真实值，难以即时检测 |
| 信号间歇中断（Intermittent Signal Loss） | 随机性信号丢失 |
| 信号延迟（Latency）| 信号到达时间超过规定周期 |
| 噪声过大（Excessive Noise） | 信号抖动超出允许范围 |
| 两点故障（Dual-Sensor Divergence）| 冗余传感器两路输出差异过大 |

### 执行器类
| 失效模式 | 含义 |
|---------|------|
| 无响应（No Response） | 完全不执行指令 |
| 过度响应（Over-response） | 输出幅值远超指令值 |
| 响应迟滞（Sluggish Response） | 响应时间超出规定 |
| 方向反转（Reversed Output） | 输出方向与指令相反 |
| 卡死在当前位置（Stuck at Current State） | 无法从当前状态转移 |

### MCU/ECU/软件类
| 失效模式 | 含义 |
|---------|------|
| 计算错误（Computation Error） | 输出与输入不符（位翻转/溢出/精度损失）|
| 内存错误（Memory Corruption） | RAM 位错误，数据被篡改 |
| 时序错误（Timing Violation） | 计算或通信超出截止时间 |
| 软件崩溃（Software Crash/Hang） | 程序异常终止或死循环 |
| 通信丢失（Communication Lost） | CAN/LIN 消息超时未到达 |

### 电源类
| 失效模式 | 含义 |
|---------|------|
| 欠压（Under-voltage） | 供电电压低于最低工作电压 |
| 过压（Over-voltage） | 供电电压超过最大允许电压 |
| 短路（Short Circuit） | 电源线对地短路，过流保护动作 |
| 开路（Open Circuit） | 电源线断路，组件断电 |

### 机械/结构类
| 失效模式 | 含义 |
|---------|------|
| 过度磨损（Excessive Wear） | 机械接触面磨损超限 |
| 断裂（Fracture/Break） | 结构件断裂 |
| 卡死（Mechanical Jam） | 运动部件无法运动 |
| 泄漏（Leakage） | 液压/气压系统泄漏 |

## 知识库检索

每个组件处理后调用：
```
search_knowledge_base(query="<组件名> <系统类型> 典型失效模式", collection="failure_modes")
```

对于有历史案例的关键组件（如 MCU、传感器），额外检索：
```
search_knowledge_base(query="<系统名称> <组件名> 故障案例", collection="historical_cases")
```

## 三层影响链分析

每条失效模式必须分析三层影响（内部推理过程），`failure_effect` 字段填写**系统级最终影响**：

```
失效模式: 扭矩传感器信号卡死在 0 Nm
  ↓ 局部影响: 传感器输出恒定为 0，不反映真实驾驶员力矩
  ↓ 子系统影响: EPS ECU 接收到错误力矩信号，计算出接近 0 的辅助电流
  ↓ 系统级影响（写入 failure_effect）: 转向辅助完全丧失，驾驶员需增加数倍力气转向，高速行驶时危险
```

## 失效原因（failure_cause）

填写**直接技术原因**（可能有多个，用分号分隔）：
- 硬件原因：芯片老化 / 工艺缺陷 / ESD 损伤 / 焊点虚焊
- 软件原因：数组越界 / 整数溢出 / 竞争条件
- 环境原因：温度超限 / 振动冲击 / 电磁干扰（EMC）

## 现有控制措施（current_controls）

必须填写，若无则填 `["无现有控制措施，需在 Stage 4 补充"]`。
来源：已实现的诊断功能、硬件冗余、软件校验。

## 每条记录格式（`FailureModeEntry` schema）

```json
{
  "id": "FM-001",
  "component": "主扭矩传感器（TAS-A）",
  "failure_mode": "信号卡死在 0 Nm（低端 Stuck）",
  "failure_effect": "EPS 转向辅助完全丧失，驾驶员需大力转向，高速行驶时存在失控风险",
  "failure_cause": "传感器内部 ASIC 芯片失效；电源 5V 欠压导致传感器工作异常",
  "severity": 8,
  "occurrence": 3,
  "detectability": 4,
  "rpn": 96,
  "current_controls": ["ECU 力矩合理性校验（范围检查±15Nm）", "CAN 报文超时检测（100ms）"]
}
```

**注意：** `rpn` 字段在此阶段填入初步估计，Stage 3 会依据完整评分标准重新计算确认。

## 输出汇总表

| FM ID | 组件 | 失效模式 | 系统级影响 | 失效原因 | 初步 S | 初步 O | 初步 D | 初步 RPN |
|-------|------|---------|----------|---------|-------|-------|-------|---------|
| FM-001 | 扭矩传感器 | 信号卡死0Nm | 辅助丧失，失控风险 | ASIC芯片失效 | 8 | 3 | 4 | 96 |

## 完成标志

回复中标注 `[FMEA Stage 2 完成]`，输出 FailureModeEntry JSON 列表及汇总表。

## 参考标准

AIAG-VDA FMEA Handbook 2019, Step 3（Function Analysis）+ Step 4（Failure Analysis）；ISO 26262-5:2018, Annex B（Hardware failure rates）

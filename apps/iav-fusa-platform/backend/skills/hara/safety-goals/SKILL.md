---
name: hara-safety-goals
description: "Stage 6：安全目标生成——对每个 ASIL≥A 的危险事件生成 SafetyGoal，含 id/description/asil/associated_hazard/safe_state/ftti"
---

# Stage 6 — `generate_safety_goals`

## 职责

对 Stage 5 输出的所有 ASIL ≥ A（ASIL-A/B/C/D）危险事件，每个生成一条安全目标。
结果填充到 `HARAState.safety_goals`，格式严格对应 `SafetyGoal` schema。

**数量规则：** 安全目标数量 = ASIL ≥ A 的危险事件数量（1:1 对应）
**ASIL = QM 的危险事件**：不生成安全目标，记录"无需安全目标"即可。

## SafetyGoal Schema 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | str | 安全目标 ID，格式 `SG-{项目代号}-{序号}` |
| `description` | str | 规范性安全目标陈述 |
| `asil` | ASILLevel | ASIL-A / ASIL-B / ASIL-C / ASIL-D |
| `associated_hazard` | str | 对应危害 ID（如 H-001）|
| `safe_state` | str | 失效后要求的安全状态或降级模式 |
| `ftti` | str | 容错时间间隔（如 "150 ms"）|

## 安全目标写作规范

### 五项必须

1. **否定形式**：使用"不得"/"避免"/"防止"等否定词
2. **功能级描述**：描述系统行为要求，不涉及具体技术实现（如"冗余传感器"、"CRC校验"等不应出现）
3. **1:1 关联**：每个安全目标必须有 `associated_hazard` 字段指向对应危害 ID
4. **安全状态明确**：`safe_state` 描述系统进入安全状态的方式（降级模式 + 驾驶员通知）
5. **FTTI 量化**：给出容错时间间隔数值

### 语句模板

```
SG-{项目代号}-{序号}：
[系统名称] 的 [功能描述] 不得在 [工况] 下因 [失效类型] 导致 [危险后果]。
```

**示例：**
```
SG-EPS-001：
EPS 不得在车辆行驶时因转向辅助功能失效导致驾驶员无法控制车辆转向方向。
```

## FTTI 参考值

| 系统类型 | 典型 FTTI |
|---------|----------|
| 制动系统（制动踏板）| 50~100 ms |
| 转向系统（EPS/EHPS）| 100~200 ms |
| ADAS 功能（LKA/AEB）| 200~500 ms |
| 动力总成（加速/油门）| 500 ms~2 s |
| 灯光/仪表（非运动控制）| 2~10 s |

**确定 FTTI 原则：** 从危险事件发生到驾驶员必须做出响应的最大可用时间。

## 安全状态描述规范

安全状态必须包含两个要素：
1. **系统行为**：系统进入的降级状态（如"断电"/"限速"/"提供最低限度辅助"/"纯机械模式"）
2. **驾驶员通知**：告知驾驶员的方式（如"仪表故障灯"/"声音报警"/"触觉提示"）

**示例：**
- `"系统切换到纯机械转向模式（0辅助力矩），同时触发仪表盘 EPS 故障警告灯和声音报警"`
- `"ADAS 功能立即退出，系统发出声音告警并在 HMI 显示'请接管'"`

## 完整输出示例（对应 `SafetyGoal` schema）

```json
[
  {
    "id": "SG-EPS-001",
    "description": "EPS 不得在车辆行驶时因转向辅助功能完全失效导致驾驶员无法维持车辆方向控制",
    "asil": "ASIL-C",
    "associated_hazard": "H-001",
    "safe_state": "系统切换到纯机械转向模式，触发仪表盘 EPS 故障灯（橙色）及持续声音报警（≥85dB）",
    "ftti": "150 ms"
  },
  {
    "id": "SG-EPS-002",
    "description": "EPS 不得在驾驶员未施加转向输入时对转向系统施加意外力矩",
    "asil": "ASIL-D",
    "associated_hazard": "H-003",
    "safe_state": "立即切断电机驱动输出，系统进入纯机械转向，触发 EPS 故障报警",
    "ftti": "100 ms"
  }
]
```

## 输出汇总表

| SG ID | 安全目标描述（摘要）| ASIL | 关联危害 | 安全状态（摘要）| FTTI |
|-------|------------------|------|---------|--------------|------|
| SG-EPS-001 | EPS 不得因辅助失效导致方向失控 | ASIL-C | H-001 | 纯机械模式+故障报警 | 150 ms |

## 完成标志

回复中标注 `[HARA Stage 6 完成]`，输出安全目标 JSON 列表及汇总表。

## 参考标准

ISO 26262-3:2018, Clause 8（Functional safety concept and safety goals）

---
name: fmea-corrective-actions
description: "Stage 4：纠正措施——对 high_rpn_modes 进行根本原因分析并生成 CorrectiveAction，填写 revised_rpn 验证改善效果"
---

# Stage 4 — `recommend_actions`

## 职责

对 Stage 3 识别的所有高 RPN 失效模式（`high_rpn_modes`），在工程师审批通过后，
生成具体可执行的纠正措施，填充 `FMEAState.corrective_actions`，对应 `CorrectiveAction` schema。

## CorrectiveAction Schema 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `failure_mode_id` | str | 对应 FM ID（如 FM-005）|
| `action` | str | 具体措施描述（可执行，明确技术方案）|
| `responsible_party` | str | 负责人或部门（默认 "TBD"）|
| `target_date` | str | 目标完成日期（默认 "TBD"）|
| `revised_severity` | int\|None | 措施后修订 S（1-10）|
| `revised_occurrence` | int\|None | 措施后修订 O（1-10）|
| `revised_detectability` | int\|None | 措施后修订 D（1-10）|
| `revised_rpn` | int\|None | 措施后预计 RPN = revised_S × revised_O × revised_D |

## 根本原因分析（必须在提出措施前完成）

### 5-Why 分析
```
为什么 EPS ECU 软件产生错误计算结果？
  → 为什么力矩控制算法出错？
    → 为什么输入数据超出算法预期范围？
      → 为什么没有对输入数据做范围校验？
        → 根本原因：软件需求中未明确输入数据范围约束，开发阶段未验证边界条件
```

### 4M 鱼骨图分类
- **Man（人）**：操作错误、培训不足
- **Machine（机器/硬件）**：组件老化、制造缺陷、EMC 干扰
- **Material（材料/软件）**：代码缺陷、算法错误、配置错误
- **Method（方法/流程）**：测试覆盖不足、需求缺失、验证方法不当

## 措施优先级原则

按以下优先级从根本上解决问题（避免仅靠检测弥补设计缺陷）：

| 优先级 | 措施类型 | 目标 | 示例 |
|-------|---------|------|------|
| **1（最高）** | 消除失效原因（降 O）| 从设计源头防止失效发生 | 切换到经认证的安全级芯片；增加看门狗电路 |
| **2** | 提高检测能力（降 D）| 在失效影响用户之前检测到 | 增加传感器合理性校验；添加 CRC 通信校验 |
| **3** | 降低失效影响（降 S）| 减少失效发生时对用户的影响 | 增加冗余通道；设计安全降级模式 |

## 措施描述规范

措施描述必须：
1. **具体可执行**：明确技术方案（如"增加冗余传感器"而非"改进传感器"）
2. **量化改善效果**：说明预计 O/D 如何变化
3. **指明实施阶段**：硬件设计阶段 / 软件开发阶段 / 测试验证阶段

## 每条记录格式（`CorrectiveAction` schema）

```json
{
  "failure_mode_id": "FM-005",
  "action": "在 EPS ECU 软件中增加输入数据范围校验（力矩：-20~+20 Nm；车速：0~300 km/h），超范围时触发错误处理并切换安全状态",
  "responsible_party": "EPS 软件安全工程师",
  "target_date": "2026-06-30",
  "revised_severity": 9,
  "revised_occurrence": 2,
  "revised_detectability": 2,
  "revised_rpn": 36
}
```

## 有效性验证规则

1. `revised_rpn = revised_severity × revised_occurrence × revised_detectability`（必须精确计算）
2. `revised_rpn` 必须 ≤ `RPN_THRESHOLD`（否则需要追加措施）
3. 若 `revised_severity` ≥ 9，即使 RPN 达标，仍需额外说明安全论证

## 常见措施示例

| 问题类型 | 推荐措施 | 降低目标 |
|---------|---------|---------|
| 传感器单点失效 | 增加冗余传感器（2oo2 表决）| O: 5→2，D: 6→2 |
| ECU 计算错误 | 增加双核 Lockstep 处理器 | D: 7→1 |
| 通信丢失 | CAN 报文超时检测 + 冗余总线 | D: 6→2，O: 4→2 |
| 软件算法缺陷 | 形式化验证 + MC/DC 覆盖测试 | D: 8→2 |
| 电源欠压 | 增加欠压监控（UVLO）+ 双电源冗余 | D: 7→1，O: 4→2 |

## 输出汇总表

| CA ID | 针对 FM | 措施描述（摘要）| 类型 | 负责人 | 日期 | 修订 S | 修订 O | 修订 D | 修订 RPN |
|-------|--------|----------------|------|-------|------|-------|-------|-------|---------|
| CA-FM005-01 | FM-005 | 增加输入范围校验+安全状态切换 | 检测+降S | SW Engineer | 2026-06-30 | 9 | 2 | 2 | 36 |

## 完成标志

回复中标注 `[FMEA Stage 4 完成]`，输出 CorrectiveAction JSON 列表、汇总表，以及 `FMEAResult.summary` 统计。

## 参考标准

AIAG-VDA FMEA Handbook 2019, Step 6（Optimization）；ISO 26262-5:2018, Clause 9（Evaluation of the hardware architectural metrics）

---
name: hara-failure-modes
description: "Stage 2：失效模式识别——对每个功能应用 4 关键词模板，调用 search_knowledge_base 补充，填充 HARAState.failure_modes"
---

# Stage 2 — `identify_failure_modes`

## 职责

对 Stage 1 输出的每个功能，系统性应用 4 关键词失效模式模板，并通过知识库检索补充领域特定失效模式。
结果填充到 `HARAState.failure_modes`。

## 4 关键词模板

| 关键词 | 含义 | EPS 功能 F-001 示例 |
|--------|------|-------------------|
| **Loss of function** | 功能完全丧失（0%） | 转向辅助完全失效，无力矩输出 |
| **Degradation of function** | 功能性能显著下降 | 转向辅助力矩不足（< 50% 额定值）|
| **Unintended activation** | 不应激活时启动 | 停车熄火后意外施加转向力矩 |
| **Incorrect output** | 输出错误方向、幅值或时序 | 施加与驾驶员意图相反的力矩 |

对每个功能的每个关键词**至少生成 1 条**失效模式记录。

## 知识库检索

每个功能处理完后，调用：
```
search_knowledge_base(query="<系统名称> <功能描述> 失效模式", collection="failure_modes")
```
将检索结果中的领域特定失效模式补充到列表（去重）。

亦可检索历史案例：
```
search_knowledge_base(query="<系统名称> 历史故障事故", collection="historical_cases")
```

## 安全相关性初判

对每条失效模式判断：
- `safety_relevant`：是否可能导致人员伤亡或影响驾驶控制（布尔值）
- `preliminary_severity`：S0/S1/S2/S3 初步估计（Stage 4 会精确评估）

**初判规则：**
- 影响车辆方向控制 → 至少 S2
- 影响制动能力 → 至少 S2
- 仅影响舒适性 → S1 或 S0

## 每条记录格式

```json
{
  "id": "FM-001",
  "function_id": "F-001",
  "keyword": "Loss of function",
  "description": "转向辅助完全失效，驾驶员需全力转向",
  "safety_relevant": true,
  "preliminary_severity": "S2",
  "source": "4-keyword-template"
}
```

`source` 可选值：`"4-keyword-template"` / `"knowledge_base"` / `"historical_case"`

## 输出汇总表

| FM ID | 功能 | 失效模式 | 关键词类别 | 安全相关 | 初步 S | 来源 |
|-------|------|---------|-----------|---------|--------|------|
| FM-001 | F-001: 提供辅助力矩 | 转向辅助完全失效 | Loss | 是 | S2 | 4-keyword |
| FM-002 | F-001: 提供辅助力矩 | 辅助力矩不足 | Degradation | 是 | S1 | 4-keyword |

## 完成标志

回复中标注 `[HARA Stage 2 完成]`，输出失效模式 JSON 列表及汇总表。

## 参考标准

ISO 26262-3:2018, Clause 7.4（Hazard identification）

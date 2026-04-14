"""Two-level intent router for classifying user analysis requests.

Level 1 — determines the primary analysis type:
    HARA / FMEA / FTA / FULL

Level 2 — for HARA requests, determines the specific pipeline stage:
    item_definition / failure_modes / hazard_derivation /
    seco_estimation / asil_classification / safety_goals
"""

from __future__ import annotations

import re
from typing import Literal

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

AnalysisType = Literal["hara", "fmea", "fta", "full"]
HARAStage = Literal[
    "item_definition",
    "failure_modes",
    "hazard_derivation",
    "seco_estimation",
    "asil_classification",
    "safety_goals",
    "unknown",
]

# ---------------------------------------------------------------------------
# Keyword maps for rule-based classification (fast path)
# ---------------------------------------------------------------------------

_HARA_KEYWORDS = {
    "hara", "危害分析", "风险评估", "hazard", "asil", "安全完整性",
    "安全目标", "safety goal", "seco", "s/e/c",
}

_FMEA_KEYWORDS = {
    "fmea", "失效模式", "failure mode", "rpn", "风险优先", "纠正措施",
    "corrective action", "severity", "occurrence", "detectability",
}

_FTA_KEYWORDS = {
    "fta", "故障树", "fault tree", "顶事件", "top event", "and gate",
    "or gate", "底事件", "basic event", "cut set", "最小割集",
}

_HARA_STAGE_KEYWORDS: dict[HARAStage, set[str]] = {
    "item_definition": {"item definition", "系统定义", "边界", "功能描述", "工况"},
    "failure_modes": {"失效模式", "failure mode", "loss of function", "degradation", "unintended"},
    "hazard_derivation": {"危害", "hazard", "危险事件", "hazardous event"},
    "seco_estimation": {"severity", "exposure", "controllability", "严酷度", "暴露概率", "可控性"},
    "asil_classification": {"asil", "定级", "classification", "asil-a", "asil-b", "asil-c", "asil-d"},
    "safety_goals": {"safety goal", "安全目标", "ftti", "safe state", "安全状态"},
}


def classify_analysis_type(text: str) -> AnalysisType:
    """Classify a user request into a primary analysis type.

    Uses keyword matching for speed; falls back to 'full' when ambiguous.

    Args:
        text: Free-text user input (Chinese or English).

    Returns:
        One of 'hara', 'fmea', 'fta', or 'full'.
    """
    lower = text.lower()

    # Full-pipeline trigger words
    if any(kw in lower for kw in ("全流程", "complete analysis", "all analysis", "full pipeline")):
        return "full"

    hits: dict[AnalysisType, int] = {
        "hara": sum(1 for kw in _HARA_KEYWORDS if kw in lower),
        "fmea": sum(1 for kw in _FMEA_KEYWORDS if kw in lower),
        "fta": sum(1 for kw in _FTA_KEYWORDS if kw in lower),
    }

    max_hits = max(hits.values())
    if max_hits == 0:
        return "full"

    # If there's a clear winner, return it
    winners = [k for k, v in hits.items() if v == max_hits]
    if len(winners) == 1:
        return winners[0]

    # Multiple types match — run full pipeline
    return "full"


def classify_hara_stage(text: str) -> HARAStage:
    """Classify which HARA pipeline stage a request targets.

    Args:
        text: Free-text user input.

    Returns:
        A `HARAStage` literal or 'unknown'.
    """
    lower = text.lower()
    hits: dict[HARAStage, int] = {
        stage: sum(1 for kw in keywords if kw in lower)
        for stage, keywords in _HARA_STAGE_KEYWORDS.items()
    }

    max_hits = max(hits.values())
    if max_hits == 0:
        return "unknown"

    winners = [k for k, v in hits.items() if v == max_hits]
    return winners[0] if len(winners) == 1 else "unknown"


def route_request(text: str) -> dict[str, str]:
    """Route a user request to the appropriate agent and stage.

    Args:
        text: Free-text user input.

    Returns:
        Dict with keys 'analysis_type' and optionally 'hara_stage'.
    """
    analysis_type = classify_analysis_type(text)
    result: dict[str, str] = {"analysis_type": analysis_type}

    if analysis_type == "hara":
        result["hara_stage"] = classify_hara_stage(text)

    return result

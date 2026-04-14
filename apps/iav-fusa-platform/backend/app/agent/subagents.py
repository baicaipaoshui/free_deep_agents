"""SubAgent definitions and shared tools for the IAV FuSa Platform.

Provides three analysis SubAgents (HARA, FMEA, FTA) plus two shared tools:
- `search_knowledge_base`: retrieves relevant passages from Dify RAG datasets
- `asil_lookup`: ISO 26262 ASIL classification table lookup

All SubAgents follow the DeepAgents `SubAgent` TypedDict contract and use the
new API (each spec includes `model` and `tools`).
"""

from __future__ import annotations

from pathlib import Path

import httpx
from langchain_core.tools import tool

from app.agent import stream_bus
from app.config import (
    COLLECTION_MAP,
    DIFY_API_KEY,
    DIFY_API_URL,
    MODEL,
    OPENAI_API_BASE,
    OPENAI_API_KEY,
    SKILLS_FMEA_DIR,
    SKILLS_FTA_DIR,
    SKILLS_HARA_DIR,
)


def _subagent_model():
    """Same logic as orchestrator: use ChatOpenAI when custom endpoint is set."""
    if OPENAI_API_BASE:
        from langchain_openai import ChatOpenAI  # noqa: PLC0415
        return ChatOpenAI(
            model=MODEL,
            api_key=OPENAI_API_KEY or "placeholder",
            base_url=OPENAI_API_BASE,
            temperature=0.2,
        )
    return MODEL

# ---------------------------------------------------------------------------
# Shared tools
# ---------------------------------------------------------------------------

_ASIL_TABLE: dict[tuple[int, int, int], str] = {
    # (Severity, Exposure, Controllability) → ASIL
    (1, 1, 1): "QM", (1, 1, 2): "QM", (1, 1, 3): "QM",
    (1, 2, 1): "QM", (1, 2, 2): "QM", (1, 2, 3): "QM",
    (1, 3, 1): "QM", (1, 3, 2): "QM", (1, 3, 3): "QM",
    (1, 4, 1): "QM", (1, 4, 2): "QM", (1, 4, 3): "QM",
    (2, 1, 1): "QM", (2, 1, 2): "QM", (2, 1, 3): "QM",
    (2, 2, 1): "QM", (2, 2, 2): "QM", (2, 2, 3): "ASIL-A",
    (2, 3, 1): "QM", (2, 3, 2): "ASIL-A", (2, 3, 3): "ASIL-B",
    (2, 4, 1): "QM", (2, 4, 2): "ASIL-A", (2, 4, 3): "ASIL-B",
    (3, 1, 1): "QM", (3, 1, 2): "QM", (3, 1, 3): "ASIL-A",
    (3, 2, 1): "QM", (3, 2, 2): "ASIL-A", (3, 2, 3): "ASIL-B",
    (3, 3, 1): "ASIL-A", (3, 3, 2): "ASIL-B", (3, 3, 3): "ASIL-C",
    (3, 4, 1): "ASIL-A", (3, 4, 2): "ASIL-B", (3, 4, 3): "ASIL-C",
}


@tool
def search_knowledge_base(query: str, collection: str = "iso26262_hara") -> str:
    """Retrieve relevant passages from the Dify knowledge base.

    Args:
        query: Free-text search query describing the information needed.
        collection: Dataset identifier.  Valid values:
            iso26262_hara, iso26262_fmea, iso26262_fta,
            failure_modes, historical_cases, company_standards.

    Returns:
        Concatenated relevant passages (up to 5 results), separated by '---'.
        Returns an error message if the API call fails.
    """
    dataset_id = COLLECTION_MAP.get(collection)
    if not dataset_id:
        return f"[知识库] 集合 '{collection}' 未配置 dataset_id，请检查环境变量。"

    stream_bus.emit_current({
        "type": "tool_start",
        "tool": "search_knowledge_base",
        "message": f"📚 检索知识库 [{collection}]: {query[:80]}",
        "input": {"query": query, "collection": collection},
    })

    try:
        resp = httpx.post(
            f"{DIFY_API_URL}/v1/datasets/{dataset_id}/retrieve",
            json={"query": query, "top_k": 5},
            headers={"Authorization": f"Bearer {DIFY_API_KEY}"},
            timeout=15.0,
        )
        resp.raise_for_status()
        records = resp.json().get("records", [])
        result = (
            "\n---\n".join(r.get("content", "") for r in records[:5])
            if records
            else "[知识库] 未找到相关文档。"
        )
    except httpx.HTTPError as exc:
        result = f"[知识库] API 调用失败: {exc}"

    stream_bus.emit_current({"type": "tool_end", "tool": "search_knowledge_base"})
    return result


@tool
def asil_lookup(severity: int, exposure: int, controllability: int) -> str:
    """Look up the ISO 26262 ASIL rating from S / E / C parameters.

    Args:
        severity: Severity class S1-S3 (use 1-3; S0 maps to QM automatically).
        exposure: Exposure class E1-E4 (use 1-4).
        controllability: Controllability class C1-C3 (use 1-3).

    Returns:
        ASIL rating string: one of 'QM', 'ASIL-A', 'ASIL-B', 'ASIL-C', 'ASIL-D'.
    """
    stream_bus.emit_current({
        "type": "tool_start",
        "tool": "asil_lookup",
        "message": f"🔢 ASIL 查表: S={severity} / E={exposure} / C={controllability}",
        "input": {"severity": severity, "exposure": exposure, "controllability": controllability},
    })
    if severity == 0 or exposure == 0 or controllability == 0:
        result = "QM"
    else:
        key = (severity, exposure, controllability)
        result = _ASIL_TABLE.get(key, "QM")
    stream_bus.emit_current({"type": "tool_end", "tool": "asil_lookup", "result": result})
    return result


# ---------------------------------------------------------------------------
# SKILL.md loaders
# ---------------------------------------------------------------------------


def _load_skill(path: str) -> str:
    """Return the content of the primary SKILL.md for a given skills directory.

    Args:
        path: Absolute path to the skill directory (e.g. skills/hara/).

    Returns:
        File content as a string, or an empty string if not found.
    """
    skill_file = Path(path) / "SKILL.md"
    if skill_file.is_file():
        return skill_file.read_text(encoding="utf-8")
    return ""


# ---------------------------------------------------------------------------
# SubAgent definitions (DeepAgents new API — must include `model` and `tools`)
# ---------------------------------------------------------------------------

hara_subagent = {
    "name": "hara_analyst",
    "description": (
        "执行 HARA（危害分析与风险评估）。包括：Item Definition 解析、"
        "失效模式识别、车辆级危害推导、S/E/C/O 估计、ASIL 定级、安全目标生成。"
        "严格按照 ISO 26262 Part 3 流程执行。"
    ),
    "system_prompt": _load_skill(SKILLS_HARA_DIR),
    "model": _subagent_model(),
    "tools": [search_knowledge_base, asil_lookup],
    "skills": [SKILLS_HARA_DIR],
}

fmea_subagent = {
    "name": "fmea_analyst",
    "description": (
        "执行 FMEA（失效模式与影响分析）。包括：系统结构分解、失效模式挖掘、"
        "RPN 风险评估（S×O×D）、纠正措施建议。支持 Dify RAG 知识增强检索。"
    ),
    "system_prompt": _load_skill(SKILLS_FMEA_DIR),
    "model": _subagent_model(),
    "tools": [search_knowledge_base],
    "skills": [SKILLS_FMEA_DIR],
}

fta_subagent = {
    "name": "fta_analyst",
    "description": (
        "执行 FTA（故障树分析）。包括：顶事件定义、AND/OR 逻辑门递归分解、"
        "底事件映射（关联 FMEA 结果）、逻辑一致性校验、可选定量分析。"
    ),
    "system_prompt": _load_skill(SKILLS_FTA_DIR),
    "model": _subagent_model(),
    "tools": [search_knowledge_base],
    "skills": [SKILLS_FTA_DIR],
}

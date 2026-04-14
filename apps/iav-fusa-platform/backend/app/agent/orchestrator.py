"""Orchestrator agent for the IAV FuSa Platform.

Uses `create_deep_agent()` native `subagents`, `skills`, `memory`, and `backend`
parameters to wire up the top-level analysis orchestrator.

Model selection
---------------
- If ``OPENAI_API_BASE`` is set, uses ``langchain_openai.ChatOpenAI`` pointing
  to that endpoint (supports MiniMax, local Ollama, any OpenAI-compatible API).
- Otherwise falls back to the ``DEEPAGENTS_MODEL`` string (e.g.
  ``anthropic:claude-sonnet-4-6``).
"""

from __future__ import annotations

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend

from app.agent.subagents import fmea_subagent, fta_subagent, hara_subagent
from app.config import AGENTS_MD_PATH, MODEL, OPENAI_API_BASE, OPENAI_API_KEY, SKILLS_COMMON_DIR

_ORCHESTRATOR_SYSTEM_PROMPT = (
    "你是 IAV AI Safety Platform 的安全分析编排器。\n"
    "根据用户请求，识别所需的分析类型（HARA / FMEA / FTA / 全流程），"
    "然后调用对应的安全分析子代理执行分析任务。\n\n"
    "重要原则：\n"
    "- 所有分析必须严格遵循 ISO 26262:2018\n"
    "- 关键节点（ASIL 定级、高 RPN 失效模式）需等待人工审批后方可继续\n"
    "- 最终向用户提供清晰的分析摘要和可追溯的结论\n"
)


def _build_model():
    """Return a LangChain chat model or a model-name string for DeepAgents.

    When OPENAI_API_BASE is configured (MiniMax / proxy), returns a
    ``ChatOpenAI`` instance so DeepAgents can use any OpenAI-compatible endpoint.
    """
    if OPENAI_API_BASE:
        from langchain_openai import ChatOpenAI  # noqa: PLC0415
        return ChatOpenAI(
            model=MODEL,
            api_key=OPENAI_API_KEY or "placeholder",
            base_url=OPENAI_API_BASE,
            temperature=0.2,
        )
    return MODEL


_orchestrator = None  # singleton — compiled once, reused across requests


def get_orchestrator():
    """Return the orchestrator agent, creating it once on first call."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = create_deep_agent(
            model=_build_model(),
            system_prompt=_ORCHESTRATOR_SYSTEM_PROMPT,
            subagents=[hara_subagent, fmea_subagent, fta_subagent],
            skills=[SKILLS_COMMON_DIR],
            memory=[AGENTS_MD_PATH],
            backend=LocalShellBackend(),
        )
    return _orchestrator

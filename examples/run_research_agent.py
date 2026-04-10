"""Runnable Deep Agents research example with Tavily + custom base URL."""

import os
from typing import Literal

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from tavily import TavilyClient

from _env import load_project_dotenv

load_project_dotenv()

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
) -> dict:
    """Run web search via Tavily."""
    return tavily_client.search(
        query=query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )


def main() -> None:
    """Build and run a deep research agent once."""
    model = init_chat_model(
        "openai:claude-sonnet-4-5-20250929",
        api_key=os.environ["ANTHROPIC_API_KEY"],
        base_url="https://z.apiyihe.org/v1",
        temperature=0,
    )

    research_instructions = """You are an expert researcher.
Use internet_search as your primary tool for finding up-to-date information.
Return a concise but informative final answer with key points and sources."""

    agent = create_deep_agent(
        model=model,
        tools=[internet_search],
        system_prompt=research_instructions,
    )

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "什么是 langgraph？"}]}
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()

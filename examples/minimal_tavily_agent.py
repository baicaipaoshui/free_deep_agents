"""Minimal Deep Agents example with Tavily web search."""

import os

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from tavily import TavilyClient

from _env import load_project_dotenv

load_project_dotenv()

_tavily_client = TavilyClient()


@tool
def tavily_search(query: str) -> str:
    """Search the web with Tavily and return a compact text summary.

    Args:
        query: Search query to execute.

    Returns:
        A plain-text summary of the top search results.
    """
    response = _tavily_client.search(query=query, max_results=3, topic="general")
    results = response.get("results", [])
    if not results:
        return "No results found."

    lines: list[str] = []
    for item in results:
        title = item.get("title", "Untitled")
        url = item.get("url", "")
        content = item.get("content", "")
        lines.append(f"- {title}\n  {url}\n  {content}")
    return "\n".join(lines)


def main() -> None:
    """Run a minimal Deep Agent with Tavily search."""
    model = init_chat_model(
        "openai:claude-sonnet-4-5-20250929",
        api_key=os.environ["ANTHROPIC_API_KEY"],
        base_url="https://z.apiyihe.org/v1",
        temperature=0,
    )
    agent = create_deep_agent(
        model=model,
        tools=[tavily_search],
        system_prompt=(
            "You are a concise research assistant. "
            "Use `tavily_search` when current web information would help."
        ),
    )

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Please research the latest Deep Agents Python package and summarize what it is.",
                }
            ]
        }
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()

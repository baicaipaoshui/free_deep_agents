import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.chat_models import init_chat_model

EXAMPLE_DIR = Path(__file__).parent
DEFAULT_MODEL = "openai:gpt-4.1"
DEFAULT_MODEL_API_KEY_ENV = "OPENAI_API_KEY"

load_dotenv(EXAMPLE_DIR.parents[1] / ".env", override=False)


def _resolve_model_name() -> str:
    """Resolve the model name for the automotive example.

    Returns:
        The configured model specification in `provider:model` format.

    Raises:
        RuntimeError: If the example falls back to the default model without the
            required API key being configured.
    """
    model_name = os.environ.get("AUTOMOTIVE_AGENT_MODEL")
    if model_name:
        return model_name

    if os.environ.get(DEFAULT_MODEL_API_KEY_ENV):
        return DEFAULT_MODEL

    msg = (
        f"{DEFAULT_MODEL_API_KEY_ENV} is not set. "
        f"Set {DEFAULT_MODEL_API_KEY_ENV} to use the default model "
        f"({DEFAULT_MODEL}), or set AUTOMOTIVE_AGENT_MODEL to another "
        "provider:model value and configure that provider's credentials."
    )
    raise RuntimeError(msg)


def create_automotive_agent():
    model_name = _resolve_model_name()
    provider, _, _ = model_name.partition(":")
    model_kwargs: dict[str, object] = {"temperature": 0}

    # OpenAI-compatible gateways often require explicit base URL wiring.
    if provider == "openai":
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            model_kwargs["api_key"] = openai_key

        openai_base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get(
            "OPENAI_API_BASE"
        )
        if openai_base_url:
            model_kwargs["base_url"] = openai_base_url

    model = init_chat_model(model_name, **model_kwargs)

    return create_deep_agent(
        model=model,
        skills=["./skills"],
        backend=FilesystemBackend(root_dir=EXAMPLE_DIR, virtual_mode=True),
    )


def main():
    parser = argparse.ArgumentParser(description="Automotive Deep Agent")
    parser.add_argument("question", type=str, help="Question for the automotive agent")
    args = parser.parse_args()

    agent = create_automotive_agent()

    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": args.question}]}
        )
        print(result["messages"][-1].content)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

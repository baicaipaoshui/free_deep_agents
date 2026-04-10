"""Tests for the automotive agent example."""

import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

from deepagents.backends import FilesystemBackend
from deepagents.middleware.skills import _list_skills


def _load_automotive_agent_module() -> ModuleType:
    """Load the automotive agent example as a module."""
    module_path = (
        Path(__file__).resolve().parents[4] / "examples" / "automotive-agent" / "agent.py"
    )
    spec = importlib.util.spec_from_file_location("automotive_agent_example", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_create_automotive_agent_uses_openai_default_model() -> None:
    """The example should default to an OpenAI model and virtual filesystem mode."""
    module = _load_automotive_agent_module()

    with (
        patch.dict(
            module.os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "OPENAI_BASE_URL": "https://example.com/v1",
            },
            clear=True,
        ),
        patch.object(module, "init_chat_model") as init_chat_model_mock,
        patch.object(module, "create_deep_agent") as create_deep_agent_mock,
        patch.object(module, "FilesystemBackend") as filesystem_backend_mock,
    ):
        init_chat_model_mock.return_value = MagicMock(name="model")
        filesystem_backend_mock.return_value = MagicMock(name="backend")
        create_deep_agent_mock.return_value = MagicMock(name="agent")

        module.create_automotive_agent()

    init_chat_model_mock.assert_called_once_with(
        "openai:gpt-4.1",
        temperature=0,
        api_key="test-key",
        base_url="https://example.com/v1",
    )
    filesystem_backend_mock.assert_called_once_with(
        root_dir=module.EXAMPLE_DIR,
        virtual_mode=True,
    )
    create_deep_agent_mock.assert_called_once()


def test_create_automotive_agent_requires_default_model_credentials() -> None:
    """The example should fail early with a clear error when no credentials exist."""
    module = _load_automotive_agent_module()

    with patch.dict(module.os.environ, {}, clear=True):
        try:
            module.create_automotive_agent()
        except RuntimeError as exc:
            message = str(exc)
        else:
            raise AssertionError("Expected create_automotive_agent() to fail")

    assert "OPENAI_API_KEY is not set" in message
    assert "AUTOMOTIVE_AGENT_MODEL" in message


def test_create_automotive_agent_uses_explicit_model_without_openai_key() -> None:
    """An explicit model selection should bypass the default OpenAI credential check."""
    module = _load_automotive_agent_module()

    with (
        patch.dict(
            module.os.environ,
            {"AUTOMOTIVE_AGENT_MODEL": "anthropic:claude-sonnet-4-6"},
            clear=True,
        ),
        patch.object(module, "init_chat_model") as init_chat_model_mock,
        patch.object(module, "create_deep_agent") as create_deep_agent_mock,
        patch.object(module, "FilesystemBackend") as filesystem_backend_mock,
    ):
        init_chat_model_mock.return_value = MagicMock(name="model")
        filesystem_backend_mock.return_value = MagicMock(name="backend")
        create_deep_agent_mock.return_value = MagicMock(name="agent")

        module.create_automotive_agent()

    init_chat_model_mock.assert_called_once_with(
        "anthropic:claude-sonnet-4-6",
        temperature=0,
    )


def test_openai_model_uses_openai_api_base_when_base_url_missing() -> None:
    """OpenAI models should fall back to OPENAI_API_BASE for gateway routing."""
    module = _load_automotive_agent_module()

    with (
        patch.dict(
            module.os.environ,
            {
                "AUTOMOTIVE_AGENT_MODEL": "openai:claude-sonnet-4-5-20250929",
                "OPENAI_API_KEY": "test-key",
                "OPENAI_API_BASE": "https://example.com/api",
            },
            clear=True,
        ),
        patch.object(module, "init_chat_model") as init_chat_model_mock,
        patch.object(module, "create_deep_agent") as create_deep_agent_mock,
        patch.object(module, "FilesystemBackend") as filesystem_backend_mock,
    ):
        init_chat_model_mock.return_value = MagicMock(name="model")
        filesystem_backend_mock.return_value = MagicMock(name="backend")
        create_deep_agent_mock.return_value = MagicMock(name="agent")

        module.create_automotive_agent()

    init_chat_model_mock.assert_called_once_with(
        "openai:claude-sonnet-4-5-20250929",
        temperature=0,
        api_key="test-key",
        base_url="https://example.com/api",
    )


def test_automotive_skills_are_discoverable_from_skills_source() -> None:
    """The automotive example should expose directory-based skills to middleware."""
    module = _load_automotive_agent_module()
    backend = FilesystemBackend(root_dir=module.EXAMPLE_DIR, virtual_mode=True)

    discovered = _list_skills(backend, "./skills")
    names = {skill["name"] for skill in discovered}

    assert "automotive-adas" in names
    assert "automotive-functional-safety-analysis" in names

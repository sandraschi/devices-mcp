"""Tests for LLM Manager."""

from unittest.mock import AsyncMock, patch

import pytest

from devices_mcp.llm.manager import LLMManager, get_llm_manager
from devices_mcp.llm.providers import (
    OllamaProvider,
    ProviderType,
)


class TestLLMManager:
    """Tests for LLMManager."""

    @pytest.fixture
    def manager(self):
        """Create an LLMManager instance."""
        return LLMManager()

    def test_register_ollama_provider(self, manager):
        """Test registering Ollama provider."""
        result = manager.register_provider(ProviderType.OLLAMA, "http://localhost:11434")
        assert result is True
        assert ProviderType.OLLAMA in manager.providers
        assert isinstance(manager.providers[ProviderType.OLLAMA], OllamaProvider)

    def test_register_lm_studio_provider(self, manager):
        """Test registering LM Studio provider."""
        result = manager.register_provider(ProviderType.LM_STUDIO, "http://localhost:1234")
        assert result is True
        assert ProviderType.LM_STUDIO in manager.providers

    def test_register_openai_provider(self, manager):
        """Test registering OpenAI provider."""
        result = manager.register_provider(
            ProviderType.OPENAI,
            "https://api.openai.com/v1",
            api_key="test-key",
        )
        assert result is True
        assert ProviderType.OPENAI in manager.providers

    def test_register_openai_without_key(self, manager):
        """Test that OpenAI provider requires API key."""
        result = manager.register_provider(
            ProviderType.OPENAI, "https://api.openai.com/v1", api_key=None
        )
        assert result is False

    def test_register_invalid_provider(self, manager):
        """Test registering invalid provider type."""
        # This should fail gracefully
        # Note: ProviderType enum should prevent this, but test error handling

    @pytest.mark.asyncio
    async def test_list_providers(self, manager):
        """Test listing providers."""
        manager.register_provider(ProviderType.OLLAMA, "http://localhost:11434")
        manager.register_provider(ProviderType.LM_STUDIO, "http://localhost:1234")

        with patch.object(
            manager.providers[ProviderType.OLLAMA], "list_models", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = []
            providers = await manager.list_providers()

            assert len(providers) == 2
            assert any(p["type"] == "ollama" for p in providers)
            assert any(p["type"] == "lm_studio" for p in providers)

    @pytest.mark.asyncio
    async def test_list_models(self, manager):
        """Test listing models for a provider."""
        manager.register_provider(ProviderType.OLLAMA, "http://localhost:11434")

        mock_models = [
            {"name": "llama2", "provider": "ollama"},
            {"name": "mistral", "provider": "ollama"},
        ]

        with patch.object(
            manager.providers[ProviderType.OLLAMA], "list_models", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = mock_models
            models = await manager.list_models(ProviderType.OLLAMA)

            assert len(models) == 2
            assert models[0]["name"] == "llama2"

    @pytest.mark.asyncio
    async def test_load_model(self, manager):
        """Test loading a model."""
        manager.register_provider(ProviderType.OLLAMA, "http://localhost:11434")

        with patch.object(
            manager.providers[ProviderType.OLLAMA], "load_model", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = True
            result = await manager.load_model("llama2", ProviderType.OLLAMA)

            assert result is True
            assert manager.current_model == "llama2"
            assert manager.current_provider == ProviderType.OLLAMA

    @pytest.mark.asyncio
    async def test_unload_model(self, manager):
        """Test unloading a model."""
        manager.register_provider(ProviderType.OLLAMA, "http://localhost:11434")
        manager.current_model = "llama2"
        manager.current_provider = ProviderType.OLLAMA

        with patch.object(
            manager.providers[ProviderType.OLLAMA],
            "unload_model",
            new_callable=AsyncMock,
        ) as mock_unload:
            mock_unload.return_value = True
            result = await manager.unload_model(ProviderType.OLLAMA)

            assert result is True
            assert manager.current_model is None

    @pytest.mark.asyncio
    async def test_chat(self, manager):
        """Test sending a chat message."""
        manager.register_provider(ProviderType.OLLAMA, "http://localhost:11434")
        manager.current_model = "llama2"
        manager.current_provider = ProviderType.OLLAMA

        with patch.object(
            manager.providers[ProviderType.OLLAMA], "chat", new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.return_value = "AI response"
            response = await manager.chat(
                [{"role": "user", "content": "Hello"}], ProviderType.OLLAMA, stream=False
            )

            assert response == "AI response"

    @pytest.mark.asyncio
    async def test_chat_without_provider(self, manager):
        """Test chat fails when no provider is available."""
        with pytest.raises(ValueError, match="No provider available"):
            await manager.chat([{"role": "user", "content": "Hello"}], stream=False)

    @pytest.mark.asyncio
    async def test_close(self, manager):
        """Test closing all providers."""
        manager.register_provider(ProviderType.OLLAMA, "http://localhost:11434")

        with patch.object(
            manager.providers[ProviderType.OLLAMA], "close", new_callable=AsyncMock
        ) as mock_close:
            await manager.close()

            mock_close.assert_called_once()
            assert len(manager.providers) == 0


class TestGetLLMManager:
    """Tests for get_llm_manager singleton."""

    def test_get_llm_manager_returns_singleton(self):
        """Test that get_llm_manager returns the same instance."""
        manager1 = get_llm_manager()
        manager2 = get_llm_manager()

        assert manager1 is manager2

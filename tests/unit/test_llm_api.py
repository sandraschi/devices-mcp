"""Tests for LLM API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from backend.server import WebServer
from fastapi.testclient import TestClient

from devices_mcp.llm.manager import get_llm_manager
from devices_mcp.llm.providers import ProviderType


@pytest.fixture
def client():
    """Create a test client."""
    server = WebServer()
    return TestClient(server.app)


@pytest.fixture
def mock_manager():
    """Create a mock LLM manager."""
    manager = get_llm_manager()
    # Clear any existing providers
    manager.providers.clear()
    return manager


class TestLLMProvidersAPI:
    """Tests for provider management endpoints."""

    @pytest.mark.asyncio
    async def test_list_providers_empty(self, client, mock_manager):
        """Test listing providers when none are registered."""
        response = client.get("/api/llm/providers")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["providers"] == []

    @pytest.mark.asyncio
    async def test_register_ollama_provider(self, client, mock_manager):
        """Test registering Ollama provider."""
        response = client.post(
            "/api/llm/providers/register",
            json={
                "type": "ollama",
                "base_url": "http://localhost:11434",
                "api_key": None,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "registered" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_register_openai_provider(self, client, mock_manager):
        """Test registering OpenAI provider."""
        response = client.post(
            "/api/llm/providers/register",
            json={
                "type": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "test-key",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_register_invalid_provider(self, client, mock_manager):
        """Test registering invalid provider type."""
        response = client.post(
            "/api/llm/providers/register",
            json={
                "type": "invalid",
                "base_url": "http://localhost:9999",
                "api_key": None,
            },
        )
        assert response.status_code == 400


class TestLLMModelsAPI:
    """Tests for model management endpoints."""

    @pytest.mark.asyncio
    async def test_list_models_no_provider(self, client, mock_manager):
        """Test listing models when no provider is registered."""
        response = client.get("/api/llm/models")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["models"] == []

    @pytest.mark.asyncio
    async def test_list_models_with_provider(self, client, mock_manager):
        """Test listing models for a provider."""
        # Register provider first
        mock_manager.register_provider(ProviderType.OLLAMA, "http://localhost:11434")

        mock_models = [
            {"name": "llama2", "provider": "ollama"},
            {"name": "mistral", "provider": "ollama"},
        ]

        with patch.object(
            mock_manager.providers[ProviderType.OLLAMA],
            "list_models",
            new_callable=AsyncMock,
        ) as mock_list:
            mock_list.return_value = mock_models
            response = client.get("/api/llm/models?provider=ollama")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["models"]) == 2

    @pytest.mark.asyncio
    async def test_load_model(self, client, mock_manager):
        """Test loading a model."""
        mock_manager.register_provider(ProviderType.OLLAMA, "http://localhost:11434")

        with patch.object(
            mock_manager.providers[ProviderType.OLLAMA],
            "load_model",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = True
            response = client.post(
                "/api/llm/models/load",
                json={"model_name": "llama2", "provider": "ollama"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_unload_model(self, client, mock_manager):
        """Test unloading a model."""
        mock_manager.register_provider(ProviderType.OLLAMA, "http://localhost:11434")

        with patch.object(
            mock_manager.providers[ProviderType.OLLAMA],
            "unload_model",
            new_callable=AsyncMock,
        ) as mock_unload:
            mock_unload.return_value = True
            response = client.post("/api/llm/models/unload", json={"provider": "ollama"})
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestLLMChatAPI:
    """Tests for chat endpoints."""

    @pytest.mark.asyncio
    async def test_chat_no_provider(self, client, mock_manager):
        """Test chat when no provider is available."""
        response = client.post(
            "/api/llm/chat",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "provider": None,
                "stream": False,
            },
        )
        # Returns 400 (Bad Request) when no provider is available, which is correct
        assert response.status_code in (400, 500)

    @pytest.mark.asyncio
    async def test_chat_with_provider(self, client, mock_manager):
        """Test chat with a provider."""
        mock_manager.register_provider(ProviderType.OLLAMA, "http://localhost:11434")
        mock_manager.current_model = "llama2"
        mock_manager.current_provider = ProviderType.OLLAMA

        with patch.object(mock_manager.providers[ProviderType.OLLAMA], "chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "AI response text"
            response = client.post(
                "/api/llm/chat",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "provider": "ollama",
                    "stream": False,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["response"] == "AI response text"

    @pytest.mark.asyncio
    async def test_chat_with_explicit_model(self, client, mock_manager):
        """Test chat passes an explicit model name to the provider."""
        mock_manager.register_provider(ProviderType.OLLAMA, "http://localhost:11434")

        with patch.object(mock_manager.providers[ProviderType.OLLAMA], "chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "AI response text"
            response = client.post(
                "/api/llm/chat",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "provider": "ollama",
                    "model": "mistral",
                    "stream": False,
                },
            )
            assert response.status_code == 200
            mock_chat.assert_awaited_once()
            assert mock_chat.await_args.kwargs.get("model_name") == "mistral"

    @pytest.mark.asyncio
    async def test_list_models_returns_object_shape(self, client, mock_manager):
        """Frontend contract: models are objects with a name field."""
        mock_manager.register_provider(ProviderType.OLLAMA, "http://localhost:11434")

        mock_models = [
            {"name": "llama2", "provider": "ollama", "size": 123},
            {"name": "mistral", "provider": "ollama"},
        ]

        with patch.object(
            mock_manager.providers[ProviderType.OLLAMA],
            "list_models",
            new_callable=AsyncMock,
        ) as mock_list:
            mock_list.return_value = mock_models
            response = client.get("/api/llm/models?provider=ollama")
            assert response.status_code == 200
            data = response.json()
            assert data["models"][0]["name"] == "llama2"
            assert isinstance(data["models"][0], dict)

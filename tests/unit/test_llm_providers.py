"""Tests for LLM provider implementations."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devices_mcp.llm.providers import (
    LMStudioProvider,
    OllamaProvider,
    OpenAIProvider,
)


class TestOllamaProvider:
    """Tests for OllamaProvider."""

    @pytest.fixture
    def provider(self):
        """Create an OllamaProvider instance."""
        return OllamaProvider(base_url="http://localhost:11434")

    @pytest.mark.asyncio
    async def test_list_models_success(self, provider):
        """Test successful model listing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama2", "size": 1000000, "modified_at": "2024-01-01"},
                {"name": "mistral", "size": 2000000, "modified_at": "2024-01-02"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            models = await provider.list_models()

            assert len(models) == 2
            assert models[0]["name"] == "llama2"
            assert models[0]["provider"] == "ollama"
            assert models[1]["name"] == "mistral"

    @pytest.mark.asyncio
    async def test_list_models_failure(self, provider):
        """Test model listing failure."""
        with patch.object(provider._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection error")
            models = await provider.list_models()

            assert models == []

    @pytest.mark.asyncio
    async def test_load_model_success(self, provider):
        """Test successful model loading."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await provider.load_model("llama2")

            assert result is True
            assert provider._current_model == "llama2"

    @pytest.mark.asyncio
    async def test_load_model_failure(self, provider):
        """Test model loading failure."""
        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Model not found")
            result = await provider.load_model("nonexistent")

            assert result is False

    @pytest.mark.asyncio
    async def test_get_current_model(self, provider):
        """Test getting current model."""
        provider._current_model = "llama2"
        assert await provider.get_current_model() == "llama2"

    @pytest.mark.asyncio
    async def test_chat_non_streaming(self, provider):
        """Test non-streaming chat."""
        provider._current_model = "llama2"
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Hello, how can I help?"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            response = await provider.chat([{"role": "user", "content": "Hello"}], stream=False)

            assert response == "Hello, how can I help?"

    @pytest.mark.asyncio
    async def test_unload_model(self, provider):
        """Test model unloading."""
        with patch.object(provider._client, "post", new_callable=AsyncMock):
            result = await provider.unload_model()
            assert result is True


class TestLMStudioProvider:
    """Tests for LMStudioProvider."""

    @pytest.fixture
    def provider(self):
        """Create an LMStudioProvider instance."""
        return LMStudioProvider(base_url="http://localhost:1234")

    @pytest.mark.asyncio
    async def test_list_models_success(self, provider):
        """Test successful model listing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"id": "model1", "object": "model"},
                {"id": "model2", "object": "model"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            models = await provider.list_models()

            assert len(models) == 2
            assert models[0]["name"] == "model1"
            assert models[0]["provider"] == "lm_studio"

    @pytest.mark.asyncio
    async def test_load_model_success(self, provider):
        """Test successful model loading."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await provider.load_model("model1")

            assert result is True

    @pytest.mark.asyncio
    async def test_chat_non_streaming(self, provider):
        """Test non-streaming chat."""
        mock_models_response = MagicMock()
        mock_models_response.json.return_value = {"data": [{"id": "model1"}]}
        mock_models_response.raise_for_status = MagicMock()

        mock_chat_response = MagicMock()
        mock_chat_response.json.return_value = {"choices": [{"message": {"content": "Response text"}}]}
        mock_chat_response.raise_for_status = MagicMock()

        with patch.object(provider._client, "get", new_callable=AsyncMock) as mock_get:
            with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
                mock_get.return_value = mock_models_response
                mock_post.return_value = mock_chat_response

                response = await provider.chat([{"role": "user", "content": "Hello"}], stream=False)

                assert response == "Response text"

    @pytest.mark.asyncio
    async def test_unload_model(self, provider):
        """Test model unloading."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await provider.unload_model()

            assert result is True


class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    @pytest.fixture
    def provider(self):
        """Create an OpenAIProvider instance."""
        return OpenAIProvider(base_url="https://api.openai.com/v1", api_key="test-key")

    def test_init_requires_api_key(self):
        """Test that OpenAI provider requires API key."""
        with pytest.raises(ValueError, match="API key"):
            OpenAIProvider(base_url="https://api.openai.com/v1", api_key=None)

    @pytest.mark.asyncio
    async def test_list_models_success(self, provider):
        """Test successful model listing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"id": "gpt-4", "object": "model"},
                {"id": "gpt-3.5-turbo", "object": "model"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            models = await provider.list_models()

            assert len(models) == 2
            assert models[0]["name"] == "gpt-4"
            assert models[0]["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_load_model_success(self, provider):
        """Test successful model loading."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "gpt-4", "object": "model"}]}
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await provider.load_model("gpt-4")

            assert result is True

    @pytest.mark.asyncio
    async def test_chat_non_streaming(self, provider):
        """Test non-streaming chat."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "AI response"}}]}
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            response = await provider.chat([{"role": "user", "content": "Hello"}], stream=False)

            assert response == "AI response"

    @pytest.mark.asyncio
    async def test_unload_model(self, provider):
        """Test model unloading (always succeeds for OpenAI)."""
        result = await provider.unload_model()
        assert result is True

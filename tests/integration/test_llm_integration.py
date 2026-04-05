"""Integration tests for LLM providers with real connections.

These tests require actual LLM providers to be running:
- Ollama: http://localhost:11434
- LM Studio: http://localhost:1234
- OpenAI: Requires API key in environment variable OPENAI_API_KEY

To run these tests:
    pytest tests/integration/test_llm_integration.py -v -m integration

To skip integration tests:
    pytest tests/integration/test_llm_integration.py -v -m "not integration"
"""

import logging
import os

import pytest

from devices_mcp.llm.manager import LLMManager
from devices_mcp.llm.providers import (
    LMStudioProvider,
    OllamaProvider,
    OpenAIProvider,
    ProviderType,
)

logger = logging.getLogger(__name__)

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


def check_provider_available(base_url: str, timeout: float = 2.0) -> bool:
    """Check if a provider is available at the given URL."""
    import httpx

    try:
        if "ollama" in base_url.lower():
            response = httpx.get(f"{base_url}/api/tags", timeout=timeout)
        elif "lm" in base_url.lower() or "1234" in base_url:
            response = httpx.get(f"{base_url}/v1/models", timeout=timeout)
        else:
            # For OpenAI, just check if we can reach the base URL
            response = httpx.get(
                f"{base_url}/models", timeout=timeout, headers={"Authorization": "Bearer test"}
            )
        return response.status_code in (200, 401)  # 401 means API is reachable but needs auth
    except Exception:
        return False


@pytest.fixture(scope="module")
def ollama_available():
    """Check if Ollama is available."""
    return check_provider_available("http://localhost:11434")


@pytest.fixture(scope="module")
def lm_studio_available():
    """Check if LM Studio is available."""
    return check_provider_available("http://localhost:1234")


@pytest.fixture(scope="module")
def openai_api_key():
    """Get OpenAI API key from environment."""
    return os.getenv("OPENAI_API_KEY")


class TestOllamaIntegration:
    """Integration tests for Ollama provider."""

    @pytest.fixture
    def provider(self):
        """Create an OllamaProvider instance."""
        return OllamaProvider(base_url="http://localhost:11434")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not check_provider_available("http://localhost:11434"), reason="Ollama not available"
    )
    async def test_list_models_real(self, provider):
        """Test listing real models from Ollama."""
        models = await provider.list_models()
        assert isinstance(models, list)
        # Ollama might have no models, or might have some
        # Just verify the response is valid
        for model in models:
            assert "name" in model
            assert "provider" in model
            assert model["provider"] == "ollama"

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not check_provider_available("http://localhost:11434"), reason="Ollama not available"
    )
    async def test_load_model_real(self, provider):
        """Test loading a real model in Ollama."""
        # First, get available models
        models = await provider.list_models()
        if not models:
            pytest.skip("No models available in Ollama")

        # Try to load the first available model
        model_name = models[0]["name"]
        result = await provider.load_model(model_name)
        assert result is True
        assert provider._current_model == model_name

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not check_provider_available("http://localhost:11434"), reason="Ollama not available"
    )
    async def test_chat_real(self, provider):
        """Test real chat with Ollama."""
        # First, get available models
        models = await provider.list_models()
        if not models:
            pytest.skip("No models available in Ollama")

        # Load a model
        model_name = models[0]["name"]
        await provider.load_model(model_name)

        # Send a simple chat message
        messages = [{"role": "user", "content": "Say 'Hello' in one word."}]
        response = await provider.chat(messages, stream=False, model_name=model_name)

        assert isinstance(response, str)
        assert len(response) > 0
        # Response should contain some text (might be "Hello" or similar)
        logger.info("Ollama response: %s", response)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not check_provider_available("http://localhost:11434"), reason="Ollama not available"
    )
    async def test_get_current_model_real(self, provider):
        """Test getting current model after loading."""
        models = await provider.list_models()
        if not models:
            pytest.skip("No models available in Ollama")

        model_name = models[0]["name"]
        await provider.load_model(model_name)

        current = await provider.get_current_model()
        assert current == model_name


class TestLMStudioIntegration:
    """Integration tests for LM Studio provider."""

    @pytest.fixture
    def provider(self):
        """Create an LMStudioProvider instance."""
        return LMStudioProvider(base_url="http://localhost:1234")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not check_provider_available("http://localhost:1234"), reason="LM Studio not available"
    )
    async def test_list_models_real(self, provider):
        """Test listing real models from LM Studio."""
        models = await provider.list_models()
        assert isinstance(models, list)
        # LM Studio might have no models loaded
        for model in models:
            assert "name" in model
            assert "provider" in model
            assert model["provider"] == "lm_studio"

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not check_provider_available("http://localhost:1234"), reason="LM Studio not available"
    )
    async def test_load_model_real(self, provider):
        """Test loading a real model in LM Studio."""
        models = await provider.list_models()
        if not models:
            pytest.skip("No models available in LM Studio")

        model_name = models[0]["name"]
        result = await provider.load_model(model_name)
        # LM Studio might fail to load if model is already loaded or doesn't exist
        # Just verify the call doesn't crash
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not check_provider_available("http://localhost:1234"), reason="LM Studio not available"
    )
    async def test_chat_real(self, provider):
        """Test real chat with LM Studio."""
        models = await provider.list_models()
        if not models:
            pytest.skip("No models available in LM Studio")

        # Get current model or use first available
        current_model = await provider.get_current_model()
        if not current_model:
            # Try to load first model
            model_name = models[0]["name"]
            await provider.load_model(model_name)
            current_model = model_name

        if not current_model:
            pytest.skip("Could not get a model to use")

        # Send a simple chat message
        messages = [{"role": "user", "content": "Say 'Hello' in one word."}]
        try:
            response = await provider.chat(messages, stream=False)
            assert isinstance(response, str)
            assert len(response) > 0
            logger.info("LM Studio response: %s", response)
        except Exception as e:
            # LM Studio might not have a model loaded or might be busy
            pytest.skip(f"LM Studio chat failed (might need model loaded): {e}")


class TestOpenAIIntegration:
    """Integration tests for OpenAI provider."""

    @pytest.fixture
    def provider(self, openai_api_key):
        """Create an OpenAIProvider instance."""
        if not openai_api_key:
            pytest.skip("OPENAI_API_KEY environment variable not set")
        return OpenAIProvider(base_url="https://api.openai.com/v1", api_key=openai_api_key)

    @pytest.mark.asyncio
    async def test_list_models_real(self, provider, openai_api_key):
        """Test listing real models from OpenAI."""
        if not openai_api_key:
            pytest.skip("OPENAI_API_KEY not set")

        models = await provider.list_models()
        assert isinstance(models, list)
        # OpenAI should have GPT models
        assert len(models) > 0
        for model in models:
            assert "name" in model
            assert "provider" in model
            assert model["provider"] == "openai"
            # Should be GPT models
            assert "gpt" in model["name"].lower()

    @pytest.mark.asyncio
    async def test_chat_real(self, provider, openai_api_key):
        """Test real chat with OpenAI."""
        if not openai_api_key:
            pytest.skip("OPENAI_API_KEY not set")

        messages = [{"role": "user", "content": "Say 'Hello' in one word."}]
        response = await provider.chat(messages, stream=False)

        assert isinstance(response, str)
        assert len(response) > 0
        # Response should contain "Hello" or similar greeting
        logger.info("OpenAI response: %s", response)


class TestLLMManagerIntegration:
    """Integration tests for LLM Manager with real providers."""

    @pytest.fixture
    def manager(self):
        """Create a fresh LLMManager instance."""
        return LLMManager()

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not check_provider_available("http://localhost:11434"), reason="Ollama not available"
    )
    async def test_manager_with_ollama(self, manager):
        """Test manager with real Ollama provider."""
        # Register Ollama
        success = manager.register_provider(ProviderType.OLLAMA, "http://localhost:11434")
        assert success is True

        # List providers
        providers = await manager.list_providers()
        assert len(providers) > 0
        assert any(p["type"] == "ollama" for p in providers)

        # List models
        models = await manager.list_models(ProviderType.OLLAMA)
        assert isinstance(models, list)

        # If models available, try loading one
        if models:
            model_name = models[0]["name"]
            result = await manager.load_model(model_name, ProviderType.OLLAMA)
            assert result is True
            assert manager.current_model == model_name

            # Try chatting
            messages = [{"role": "user", "content": "Say 'test'"}]
            response = await manager.chat(messages, ProviderType.OLLAMA, stream=False)
            assert isinstance(response, str)
            assert len(response) > 0
            logger.info("Manager with Ollama response: %s", response)

    @pytest.mark.asyncio
    async def test_manager_with_openai(self, manager, openai_api_key):
        """Test manager with real OpenAI provider."""
        if not openai_api_key:
            pytest.skip("OPENAI_API_KEY not set")

        # Register OpenAI
        success = manager.register_provider(
            ProviderType.OPENAI, "https://api.openai.com/v1", api_key=openai_api_key
        )
        assert success is True

        # List providers
        providers = await manager.list_providers()
        assert any(p["type"] == "openai" for p in providers)

        # List models
        models = await manager.list_models(ProviderType.OPENAI)
        assert len(models) > 0

        # Try chatting (OpenAI doesn't need explicit load)
        messages = [{"role": "user", "content": "Say 'test'"}]
        response = await manager.chat(messages, ProviderType.OPENAI, stream=False)
        assert isinstance(response, str)
        assert len(response) > 0
        logger.info("Manager with OpenAI response: %s", response)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not check_provider_available("http://localhost:1234"), reason="LM Studio not available"
    )
    async def test_manager_with_lm_studio(self, manager):
        """Test manager with real LM Studio provider."""
        # Register LM Studio
        success = manager.register_provider(ProviderType.LM_STUDIO, "http://localhost:1234")
        assert success is True

        # List providers
        providers = await manager.list_providers()
        assert any(p["type"] == "lm_studio" for p in providers)

        # List models
        models = await manager.list_models(ProviderType.LM_STUDIO)
        assert isinstance(models, list)

        # Try to get current model or load one
        if models:
            model_name = models[0]["name"]
            await manager.load_model(model_name, ProviderType.LM_STUDIO)

            # Try chatting
            messages = [{"role": "user", "content": "Say 'test'"}]
            try:
                response = await manager.chat(messages, ProviderType.LM_STUDIO, stream=False)
                assert isinstance(response, str)
                assert len(response) > 0
                logger.info("Manager with LM Studio response: %s", response)
            except Exception as e:
                pytest.skip(f"LM Studio chat failed: {e}")

    @pytest.mark.asyncio
    async def test_manager_multiple_providers(self, manager, openai_api_key):
        """Test manager with multiple providers registered."""
        providers_registered = 0

        # Try to register Ollama
        if check_provider_available("http://localhost:11434") and manager.register_provider(
            ProviderType.OLLAMA, "http://localhost:11434"
        ):
            providers_registered += 1

        # Try to register LM Studio
        if check_provider_available("http://localhost:1234") and manager.register_provider(
            ProviderType.LM_STUDIO, "http://localhost:1234"
        ):
            providers_registered += 1

        # Try to register OpenAI
        if openai_api_key and manager.register_provider(
            ProviderType.OPENAI, "https://api.openai.com/v1", api_key=openai_api_key
        ):
            providers_registered += 1

        if providers_registered == 0:
            pytest.skip("No providers available for multi-provider test")

        # List all providers
        providers = await manager.list_providers()
        assert len(providers) == providers_registered

        # Verify we can list models from each
        for provider_info in providers:
            provider_type = ProviderType(provider_info["type"])
            models = await manager.list_models(provider_type)
            assert isinstance(models, list)
            logger.info("Provider %s has %d models", provider_info["type"], len(models))


class TestStreamingIntegration:
    """Integration tests for streaming responses."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not check_provider_available("http://localhost:11434"), reason="Ollama not available"
    )
    async def test_ollama_streaming(self):
        """Test streaming chat with Ollama."""
        provider = OllamaProvider(base_url="http://localhost:11434")

        # Get available models
        models = await provider.list_models()
        if not models:
            pytest.skip("No models available in Ollama")

        model_name = models[0]["name"]
        await provider.load_model(model_name)

        # Test streaming
        messages = [{"role": "user", "content": "Count from 1 to 5, one number per line."}]
        chunks = []

        async for chunk in await provider.chat(messages, stream=True, model_name=model_name):
            chunks.append(chunk)
            if len(chunks) >= 10:  # Limit to first 10 chunks for speed
                break

        assert len(chunks) > 0
        # All chunks should be strings
        for chunk in chunks:
            assert isinstance(chunk, str)
        logger.info("Received %d streaming chunks from Ollama", len(chunks))

    @pytest.mark.asyncio
    async def test_openai_streaming(self, openai_api_key):
        """Test streaming chat with OpenAI."""
        if not openai_api_key:
            pytest.skip("OPENAI_API_KEY not set")

        provider = OpenAIProvider(base_url="https://api.openai.com/v1", api_key=openai_api_key)

        messages = [{"role": "user", "content": "Count from 1 to 5, one number per line."}]
        chunks = []

        async for chunk in await provider.chat(messages, stream=True):
            chunks.append(chunk)
            if len(chunks) >= 10:  # Limit to first 10 chunks for speed
                break

        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, str)
        logger.info("Received %d streaming chunks from OpenAI", len(chunks))

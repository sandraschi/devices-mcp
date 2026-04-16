"""LLM Manager for handling multiple providers."""

import logging
import os

# Import for type checking
from typing import Any

import httpx

from .providers import (
    LLMProvider,
    LMStudioProvider,
    OllamaProvider,
    OpenAIProvider,
    ProviderType,
)

logger = logging.getLogger(__name__)


class LLMManager:
    """Manager for LLM providers and models."""

    def __init__(self):
        """Initialize the LLM manager."""
        self.providers: dict[ProviderType, LLMProvider] = {}
        self.current_provider: ProviderType | None = None
        self.current_model: str | None = None

    def register_provider(
        self,
        provider_type: ProviderType,
        base_url: str,
        api_key: str | None = None,
    ) -> bool:
        """Register a provider.

        Args:
            provider_type: Type of provider
            base_url: Base URL for the provider
            api_key: Optional API key

        Returns:
            True if registration successful
        """
        try:
            if provider_type == ProviderType.OLLAMA:
                provider = OllamaProvider(base_url)
            elif provider_type == ProviderType.LM_STUDIO:
                provider = LMStudioProvider(base_url)
            elif provider_type == ProviderType.OPENAI:
                if not api_key:
                    logger.error("OpenAI provider requires an API key")
                    return False
                provider = OpenAIProvider(base_url, api_key)
            else:
                logger.error(f"Unknown provider type: {provider_type}")
                return False

            self.providers[provider_type] = provider
            logger.info(f"Registered {provider_type.value} provider at {base_url}")
            return True
        except Exception:
            logger.exception("Failed to register %s provider", provider_type.value)
            return False

    async def list_providers(self) -> list[dict[str, Any]]:
        """List all registered providers."""
        providers = []
        for provider_type, provider in self.providers.items():
            try:
                models = await provider.list_models()
                current_model = await provider.get_current_model()
                providers.append(
                    {
                        "type": provider_type.value,
                        "base_url": provider.base_url,
                        "model_count": len(models),
                        "current_model": current_model,
                        "available": True,
                    }
                )
            except Exception:
                providers.append(
                    {
                        "type": provider_type.value,
                        "base_url": provider.base_url,
                        "model_count": 0,
                        "current_model": None,
                        "available": False,
                    }
                )
        return providers

    async def list_models(self, provider_type: ProviderType | None = None) -> list[dict[str, Any]]:
        """List models for a provider.

        Args:
            provider_type: Provider type, or None for current provider

        Returns:
            List of available models
        """
        provider = self._get_provider(provider_type)
        if not provider:
            return []

        try:
            return await provider.list_models()
        except Exception:
            logger.exception("Failed to list models")
            return []

    async def load_model(self, model_name: str, provider_type: ProviderType | None = None) -> bool:
        """Load a model.

        Args:
            model_name: Name of the model to load
            provider_type: Provider type, or None for current provider

        Returns:
            True if model loaded successfully
        """
        provider = self._get_provider(provider_type)
        if not provider:
            return False

        try:
            success = await provider.load_model(model_name)
            if success:
                self.current_model = model_name
                if provider_type:
                    self.current_provider = provider_type
                logger.info(f"Loaded model {model_name} on {provider_type or self.current_provider}")
            return success
        except Exception:
            logger.exception("Failed to load model %s", model_name)
            return False

    async def unload_model(self, provider_type: ProviderType | None = None) -> bool:
        """Unload the current model.

        Args:
            provider_type: Provider type, or None for current provider

        Returns:
            True if model unloaded successfully
        """
        provider = self._get_provider(provider_type)
        if not provider:
            return False

        try:
            success = await provider.unload_model()
            if success:
                self.current_model = None
                logger.info(f"Unloaded model on {provider_type or self.current_provider}")
            return success
        except Exception:
            logger.exception("Failed to unload model")
            return False

    async def chat(
        self,
        messages: list[dict[str, str]],
        provider_type: ProviderType | None = None,
        stream: bool = False,
        model_name: str | None = None,
    ) -> Any:
        """Send a chat message.

        Args:
            messages: List of message dicts with 'role' and 'content'
            provider_type: Provider type, or None for current provider
            stream: Whether to stream the response
            model_name: Optional model name to use

        Returns:
            Response from the model
        """
        provider = self._get_provider(provider_type)
        if not provider:
            raise ValueError("No provider available")

        # Use current model if not specified
        use_model = model_name or self.current_model

        # For Ollama, pass model_name to chat method
        if isinstance(provider, OllamaProvider):
            return await provider.chat(messages, stream=stream, model_name=use_model)
        return await provider.chat(messages, stream=stream)

    def _get_provider(self, provider_type: ProviderType | None = None) -> LLMProvider | None:
        """Get a provider instance.

        Args:
            provider_type: Provider type, or None for current provider

        Returns:
            Provider instance or None
        """
        if provider_type:
            return self.providers.get(provider_type)
        if self.current_provider:
            return self.providers.get(self.current_provider)
        if self.providers:
            # Use first available provider
            return next(iter(self.providers.values()))
        return None

    async def close(self):
        """Close all providers."""
        for provider in self.providers.values():
            await provider.close()
        self.providers.clear()

    async def glom_local_providers_if_up(self) -> None:
        """Fleet SOTA: auto-register Ollama (11434) and LM Studio (1234) when reachable.

        Disable with DEVICES_MCP_LLM_GLOM=0.
        """
        if os.getenv("DEVICES_MCP_LLM_GLOM", "1").strip().lower() in ("0", "false", "no", "off"):
            return
        timeout = httpx.Timeout(2.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            if ProviderType.OLLAMA not in self.providers:
                try:
                    r = await client.get("http://127.0.0.1:11434/api/tags")
                    if r.status_code == 200:
                        if self.register_provider(ProviderType.OLLAMA, "http://127.0.0.1:11434"):
                            logger.info("LLM glom: registered Ollama at 127.0.0.1:11434")
                except Exception:
                    logger.debug("LLM glom: Ollama not reachable", exc_info=True)
            if ProviderType.LM_STUDIO not in self.providers:
                try:
                    r = await client.get("http://127.0.0.1:1234/v1/models")
                    if r.status_code == 200:
                        if self.register_provider(ProviderType.LM_STUDIO, "http://127.0.0.1:1234"):
                            logger.info("LLM glom: registered LM Studio at 127.0.0.1:1234")
                except Exception:
                    logger.debug("LLM glom: LM Studio not reachable", exc_info=True)


# Global manager instance
_llm_manager: LLMManager | None = None


def get_llm_manager() -> LLMManager:
    """Get the global LLM manager instance."""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager

"""LLM provider implementations for Ollama, LM Studio, and OpenAI."""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    OLLAMA = "ollama"
    LM_STUDIO = "lm_studio"
    OPENAI = "openai"


class LLMProvider(ABC):
    """Base class for LLM providers."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """Initialize the provider.

        Args:
            base_url: Base URL for the provider API
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=60.0)

    @abstractmethod
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""

    @abstractmethod
    async def load_model(self, model_name: str) -> bool:
        """Load a model."""

    @abstractmethod
    async def unload_model(self) -> bool:
        """Unload the current model."""

    @abstractmethod
    async def get_current_model(self) -> Optional[str]:
        """Get the currently loaded model name."""

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], stream: bool = False) -> Any:
        """Send a chat message."""

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


class OllamaProvider(LLMProvider):
    """Ollama provider implementation."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        """Initialize Ollama provider."""
        super().__init__(base_url)
        self._current_model: Optional[str] = None

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available Ollama models."""
        try:
            response = await self._client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            models = []
            for model in data.get("models", []):
                models.append(
                    {
                        "name": model.get("name", ""),
                        "size": model.get("size", 0),
                        "modified_at": model.get("modified_at", ""),
                        "provider": "ollama",
                    }
                )
            return models
        except Exception:
            logger.exception("Failed to list Ollama models")
            return []

    async def load_model(self, model_name: str) -> bool:
        """Load an Ollama model."""
        try:
            # Ollama loads models on first use, so we just verify it exists
            response = await self._client.post(
                f"{self.base_url}/api/show",
                json={"name": model_name},
            )
            response.raise_for_status()
            self._current_model = model_name
            return True
        except Exception:
            logger.exception("Failed to load Ollama model %s", model_name)
            return False

    async def unload_model(self) -> bool:
        """Unload current Ollama model."""
        try:
            # Ollama doesn't have explicit unload, but we can free memory
            await self._client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": "",
                    "prompt": "",
                    "stream": False,
                },
            )
            # This is a workaround - Ollama doesn't have explicit unload
            return True
        except Exception:
            return True  # Ignore errors for unload

    async def get_current_model(self) -> Optional[str]:
        """Get current Ollama model."""
        return self._current_model

    async def chat(
        self, messages: List[Dict[str, str]], stream: bool = False, model_name: Optional[str] = None
    ) -> Any:
        """Send chat message to Ollama."""
        # Use provided model or current model
        use_model = model_name or self._current_model or "llama2"

        # Convert messages to Ollama format
        prompt = ""
        for msg in messages:
            if msg.get("role") == "system":
                prompt += f"System: {msg.get('content')}\n\n"
            elif msg.get("role") == "user":
                prompt += f"User: {msg.get('content')}\n\n"
            elif msg.get("role") == "assistant":
                prompt += f"Assistant: {msg.get('content')}\n\n"

        if stream:

            async def generate():
                async with self._client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json={
                        "model": use_model,
                        "prompt": prompt,
                        "stream": True,
                    },
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            import json

                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                            except json.JSONDecodeError:
                                pass

            return generate()
        response = await self._client.post(
            f"{self.base_url}/api/generate",
            json={
                "model": use_model,
                "prompt": prompt,
                "stream": False,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")


class LMStudioProvider(LLMProvider):
    """LM Studio provider implementation (OpenAI-compatible API)."""

    def __init__(self, base_url: str = "http://localhost:1234"):
        """Initialize LM Studio provider."""
        super().__init__(base_url)

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available LM Studio models."""
        try:
            response = await self._client.get(f"{self.base_url}/v1/models")
            response.raise_for_status()
            data = response.json()
            models = []
            for model in data.get("data", []):
                models.append(
                    {
                        "name": model.get("id", ""),
                        "provider": "lm_studio",
                        "object": model.get("object", "model"),
                    }
                )
            return models
        except Exception:
            logger.exception("Failed to list LM Studio models")
            return []

    async def load_model(self, model_name: str) -> bool:
        """Load an LM Studio model."""
        try:
            # LM Studio loads models via the OpenAI-compatible API
            response = await self._client.post(
                f"{self.base_url}/v1/models/load",
                json={"model": model_name},
            )
            response.raise_for_status()
            return True
        except Exception:
            logger.exception("Failed to load LM Studio model %s", model_name)
            return False

    async def unload_model(self) -> bool:
        """Unload current LM Studio model."""
        try:
            response = await self._client.post(f"{self.base_url}/v1/models/unload")
            response.raise_for_status()
            return True
        except Exception:
            logger.exception("Failed to unload LM Studio model")
            return False

    async def get_current_model(self) -> Optional[str]:
        """Get current LM Studio model."""
        try:
            response = await self._client.get(f"{self.base_url}/v1/models")
            response.raise_for_status()
            data = response.json()
            # LM Studio typically has one active model
            models = data.get("data", [])
            if models:
                return models[0].get("id")
            return None
        except Exception:
            return None

    async def chat(self, messages: List[Dict[str, str]], stream: bool = False) -> Any:
        """Send chat message to LM Studio (OpenAI-compatible)."""
        try:
            response = await self._client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": await self.get_current_model() or "local-model",
                    "messages": messages,
                    "stream": stream,
                },
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
            )
            response.raise_for_status()

            if stream:

                async def generate():
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            import json

                            try:
                                data = json.loads(line[6:])
                                if data.get("choices"):
                                    delta = data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                pass

                return generate()
            data = response.json()
            if data.get("choices"):
                return data["choices"][0]["message"]["content"]
            return ""
        except Exception:
            logger.exception("Failed to chat with LM Studio")
            raise


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""

    def __init__(self, base_url: str = "https://api.openai.com/v1", api_key: Optional[str] = None):
        """Initialize OpenAI provider."""
        super().__init__(base_url, api_key)
        if not api_key:
            raise ValueError("OpenAI provider requires an API key")

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available OpenAI models."""
        try:
            response = await self._client.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            data = response.json()
            models = []
            for model in data.get("data", []):
                if model.get("id", "").startswith("gpt-"):
                    models.append(
                        {
                            "name": model.get("id", ""),
                            "provider": "openai",
                            "object": model.get("object", "model"),
                        }
                    )
            return models
        except Exception:
            logger.exception("Failed to list OpenAI models")
            return []

    async def load_model(self, model_name: str) -> bool:
        """OpenAI doesn't require explicit model loading."""
        # OpenAI models are always available, just verify it exists
        models = await self.list_models()
        return any(m["name"] == model_name for m in models)

    async def unload_model(self) -> bool:
        """OpenAI doesn't require explicit model unloading."""
        return True

    async def get_current_model(self) -> Optional[str]:
        """OpenAI doesn't have a concept of 'current' model."""
        return None

    async def chat(self, messages: List[Dict[str, str]], stream: bool = False) -> Any:
        """Send chat message to OpenAI."""
        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": "gpt-4",  # Default, should be configurable
                    "messages": messages,
                    "stream": stream,
                },
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()

            if stream:

                async def generate():
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            if line == "data: [DONE]":
                                break
                            import json

                            try:
                                data = json.loads(line[6:])
                                if data.get("choices"):
                                    delta = data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                pass

                return generate()
            data = response.json()
            if data.get("choices"):
                return data["choices"][0]["message"]["content"]
            return ""
        except Exception:
            logger.exception("Failed to chat with OpenAI")
            raise

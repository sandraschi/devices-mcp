"""LLM API endpoints for model management and chat."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from devices_mcp.llm.manager import get_llm_manager
from devices_mcp.llm.providers import ProviderType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["llm"])


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat request model."""

    messages: list[ChatMessage] = Field(..., description="List of chat messages")
    provider: str | None = Field(None, description="Provider type (ollama, lm_studio, openai)")
    model: str | None = Field(None, description="Model name to use for this chat")
    stream: bool = Field(False, description="Whether to stream the response")
    include_device_context: bool = Field(
        True,
        description="Inject live home device inventory as system prompt (devices-mcp skill)",
    )


class ProviderConfig(BaseModel):
    """Provider configuration model."""

    type: str = Field(..., description="Provider type")
    base_url: str = Field(..., description="Base URL for the provider")
    api_key: str | None = Field(None, description="API key (for OpenAI)")


@router.get("/providers", summary="List all registered providers")
async def list_providers() -> dict[str, Any]:
    """List all registered LLM providers."""
    try:
        manager = get_llm_manager()
        providers = await manager.list_providers()
        return {"success": True, "providers": providers}
    except Exception as e:
        logger.exception("Failed to list providers")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/providers/register", summary="Register a new provider")
async def register_provider(config: ProviderConfig) -> dict[str, Any]:
    """Register a new LLM provider."""
    try:
        manager = get_llm_manager()
        provider_type = ProviderType(config.type)
        success = manager.register_provider(
            provider_type,
            config.base_url,
            config.api_key,
        )
        if success:
            return {"success": True, "message": f"Provider {config.type} registered"}
        raise HTTPException(status_code=400, detail=f"Failed to register provider {config.type}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to register provider")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/models", summary="List available models")
async def list_models(provider: str | None = None) -> dict[str, Any]:
    """List available models for a provider."""
    try:
        manager = get_llm_manager()
        provider_type = ProviderType(provider) if provider else None
        models = await manager.list_models(provider_type)
        return {"success": True, "models": models, "count": len(models)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to list models")
        raise HTTPException(status_code=500, detail=str(e)) from e


class LoadModelRequest(BaseModel):
    """Load model request model."""

    model_name: str = Field(..., description="Name of the model to load")
    provider: str | None = Field(None, description="Provider type")


class UnloadModelRequest(BaseModel):
    """Unload model request model."""

    provider: str | None = Field(None, description="Provider type")


@router.post("/models/load", summary="Load a model")
async def load_model(request: LoadModelRequest) -> dict[str, Any]:
    """Load a model on a provider."""
    try:
        manager = get_llm_manager()
        provider_type = ProviderType(request.provider) if request.provider else None
        success = await manager.load_model(request.model_name, provider_type)
        if success:
            return {"success": True, "message": f"Model {request.model_name} loaded"}
        raise HTTPException(status_code=400, detail=f"Failed to load model {request.model_name}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to load model")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/models/unload", summary="Unload current model")
async def unload_model(request: UnloadModelRequest) -> dict[str, Any]:
    """Unload the current model."""
    try:
        manager = get_llm_manager()
        provider_type = ProviderType(request.provider) if request.provider else None
        success = await manager.unload_model(provider_type)
        if success:
            return {"success": True, "message": "Model unloaded"}
        raise HTTPException(status_code=400, detail="Failed to unload model")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to unload model")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/device-context", summary="Live device inventory for chat preprompt")
async def get_device_context() -> dict[str, Any]:
    """Return the device snapshot injected into chat system messages."""
    try:
        from devices_mcp.chat.device_context import build_device_context_snapshot

        text = await build_device_context_snapshot()
        return {"success": True, "context": text, "chars": len(text)}
    except Exception as e:
        logger.exception("Failed to build device context")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/chat", summary="Send a chat message")
async def chat(request: ChatRequest) -> dict[str, Any]:
    """Send a chat message to the LLM."""
    try:
        manager = get_llm_manager()
        provider_type = ProviderType(request.provider) if request.provider else None

        # Convert Pydantic models to dicts
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        if request.include_device_context:
            from devices_mcp.chat.device_context import (
                build_device_context_snapshot,
                merge_device_context_into_messages,
            )

            context = await build_device_context_snapshot()
            messages = merge_device_context_into_messages(messages, context)

        if request.stream:
            from fastapi.responses import StreamingResponse

            async def generate():
                async for chunk in await manager.chat(
                    messages,
                    provider_type,
                    stream=True,
                    model_name=request.model,
                ):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(generate(), media_type="text/event-stream")
        response = await manager.chat(
            messages,
            provider_type,
            stream=False,
            model_name=request.model,
        )
        return {"success": True, "response": response}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to chat")
        raise HTTPException(status_code=500, detail=str(e)) from e

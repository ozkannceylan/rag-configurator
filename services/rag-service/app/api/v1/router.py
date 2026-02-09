"""API v1 router aggregating all endpoints."""

from fastapi import APIRouter

from app.api.v1 import query, chat, stream

router = APIRouter()

# Include sub-routers
router.include_router(query.router, prefix="/query", tags=["query"])
router.include_router(chat.router, tags=["chat"])
router.include_router(stream.router, tags=["stream"])


@router.get("/", tags=["root"])
async def root():
    """API v1 root endpoint."""
    return {
        "message": "RAG Service API v1",
        "version": "1.0.0",
        "endpoints": {
            "query": "/api/v1/query",
            "chat": "/api/v1/chat",
            "agents": "/api/v1/agents",
        },
    }


@router.get("/providers", tags=["providers"])
async def list_providers():
    """List available LLM providers."""
    from app.core.settings import settings

    providers = []

    # OpenAI
    if settings.openai_api_key:
        providers.append({
            "id": "openai",
            "name": "OpenAI",
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            "available": True,
        })
    else:
        providers.append({
            "id": "openai",
            "name": "OpenAI",
            "available": False,
            "reason": "API key not configured",
        })

    # Anthropic
    if settings.anthropic_api_key:
        providers.append({
            "id": "anthropic",
            "name": "Anthropic",
            "models": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
            "available": True,
        })
    else:
        providers.append({
            "id": "anthropic",
            "name": "Anthropic",
            "available": False,
            "reason": "API key not configured",
        })

    # Ollama (always available if URL is set)
    providers.append({
        "id": "ollama",
        "name": "Ollama (Local)",
        "base_url": settings.ollama_base_url,
        "default_model": settings.ollama_default_model,
        "available": True,
    })

    # vLLM
    if settings.vllm_base_url:
        providers.append({
            "id": "vllm",
            "name": "vLLM (Self-hosted)",
            "base_url": settings.vllm_base_url,
            "available": True,
        })

    return {
        "providers": providers,
        "default_provider": settings.default_llm_provider,
        "default_model": settings.default_llm_model,
    }

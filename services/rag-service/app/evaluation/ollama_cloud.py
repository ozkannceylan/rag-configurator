"""Ollama Cloud (OpenAI-compatible) client for the live LLM-as-judge baseline.

Hermes uses Ollama Cloud, not OpenAI/Anthropic direct. Native local Ollama is
``POST {host}/api/chat`` with no auth (see ``app.llm.ollama.OllamaLLM``). Cloud
chat completions are ``https://ollama.com/v1`` (NOT ``/api/v1``) with
``Authorization: Bearer $OLLAMA_API_KEY``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse, urlunparse

from app.llm.base import BaseLLM, LLMConfig
from app.llm.openai import OpenAILLM

DEFAULT_OLLAMA_CLOUD_OPENAI_BASE = "https://ollama.com/v1"
DEFAULT_OLLAMA_CLOUD_MODEL = "gpt-oss:20b"

_LOCAL_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "host.docker.internal",
    }
)


def is_local_ollama_url(url: str | None) -> bool:
    """True for native local Ollama hosts (localhost / :11434), not Ollama Cloud."""
    if url is None or not str(url).strip():
        return True
    parsed = urlparse(str(url).strip())
    host = (parsed.hostname or "").lower()
    if host in _LOCAL_HOSTS:
        return True
    if parsed.port == 11434:
        return True
    return False


def normalize_openai_compat_base(url: str) -> str:
    """Map an Ollama host URL to the OpenAI-compatible ``/v1`` base.

    Ollama Cloud chat completions live at ``https://ollama.com/v1``. Native
    ``/api`` and the mistaken ``/api/v1`` suffix are rewritten to ``/v1``.
    """
    raw = url.strip().rstrip("/")
    if "://" not in raw:
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    path = (parsed.path or "").rstrip("/")
    if path in {"", "/"}:
        path = "/v1"
    elif path in {"/api", "/api/v1"}:
        path = "/v1"
    elif path.endswith("/api"):
        path = f"{path[: -len('/api')]}/v1"
    elif path.endswith("/api/v1"):
        path = f"{path[: -len('/api/v1')]}/v1"
    elif not path.endswith("/v1"):
        path = f"{path}/v1"
    scheme = parsed.scheme or "https"
    return urlunparse((scheme, parsed.netloc, path, "", "", "")).rstrip("/")


def resolve_ollama_cloud_openai_base(
    *,
    api_key: str | None,
    ollama_base_url: str | None = None,
    openai_compat_base: str | None = None,
    override_base: str | None = None,
) -> str | None:
    """Return the OpenAI-compat base URL when an Ollama Cloud API key is set.

    Preference: ``JEV_EVAL_LLM_BASE_URL`` / ``OLLAMA_OPENAI_BASE_URL`` overrides,
    then a non-local ``OLLAMA_BASE_URL``, else ``https://ollama.com/v1``.
    Local ``:11434`` URLs are ignored so a typical Hermes ``.env`` still hits
    Ollama Cloud for the live judge.
    """
    if not (api_key or "").strip():
        return None
    for candidate in (override_base, openai_compat_base):
        if candidate and str(candidate).strip():
            return normalize_openai_compat_base(str(candidate).strip())
    if (
        ollama_base_url
        and str(ollama_base_url).strip()
        and not is_local_ollama_url(ollama_base_url)
    ):
        return normalize_openai_compat_base(str(ollama_base_url).strip())
    return DEFAULT_OLLAMA_CLOUD_OPENAI_BASE


def resolve_ollama_cloud_model(env: Mapping[str, str] | None = None) -> str:
    source = env if env is not None else os.environ
    for name in ("JEV_EVAL_LLM_MODEL", "OLLAMA_CLOUD_MODEL"):
        raw = source.get(name)
        if raw and str(raw).strip():
            return str(raw).strip()
    return DEFAULT_OLLAMA_CLOUD_MODEL


def _env_get(env: Mapping[str, Any], name: str) -> str | None:
    raw = env.get(name)
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def build_ollama_cloud_llm(
    env: Mapping[str, str] | None = None,
    *,
    temperature: float = 0.0,
    max_tokens: int = 256,
) -> BaseLLM | None:
    """OpenAI-compatible client pointed at Ollama Cloud, or None if no API key."""
    source = env if env is not None else os.environ
    api_key = _env_get(source, "OLLAMA_API_KEY")
    base = resolve_ollama_cloud_openai_base(
        api_key=api_key,
        ollama_base_url=_env_get(source, "OLLAMA_BASE_URL"),
        openai_compat_base=_env_get(source, "OLLAMA_OPENAI_BASE_URL"),
        override_base=_env_get(source, "JEV_EVAL_LLM_BASE_URL"),
    )
    if api_key is None or base is None:
        return None
    model = resolve_ollama_cloud_model(source)
    return OpenAILLM(
        config=LLMConfig(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            base_url=base,
        )
    )


def build_ollama_cloud_quality_judge(
    env: Mapping[str, str] | None = None,
    *,
    temperature: float = 0.0,
    max_tokens: int = 256,
    judge_name: str = "llm",
):
    """QualityJudge backed by Ollama Cloud, or None if ``OLLAMA_API_KEY`` is unset."""
    from app.evaluation.quality_judge import QualityJudge

    llm = build_ollama_cloud_llm(env, temperature=temperature, max_tokens=max_tokens)
    if llm is None:
        return None
    return QualityJudge(llm=llm, judge_name=judge_name)

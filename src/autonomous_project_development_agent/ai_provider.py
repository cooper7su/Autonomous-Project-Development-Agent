"""Provider abstraction for AI-Phase2.

This module keeps provider selection, configuration, and response normalization
separate from task execution. The current implementation stays local and safe:

- `LocalTemplateProvider` returns deterministic placeholder content.
- `OpenAIProvider` is a configuration-aware placeholder and does not perform
  live network calls unless a later phase explicitly enables that behavior.

Future phases can extend these classes with approval-aware live requests,
response parsing, caching, and richer error handling.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import Any


def utc_now() -> str:
    """Return an ISO 8601 timestamp in UTC."""

    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _env_flag(name: str, default: bool = False) -> bool:
    """Read a boolean environment flag using common truthy values."""

    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AIProviderConfig:
    """Runtime provider configuration resolved from CLI and environment."""

    provider_name: str
    timeout_seconds: float = 30.0
    max_retries: int = 1
    allow_live_calls: bool = False
    openai_model: str = "gpt-4.1-mini"
    has_openai_api_key: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize provider configuration for logs and state output."""

        return asdict(self)


@dataclass(frozen=True)
class AIProviderRequest:
    """Normalized provider request shared across all AI provider types."""

    provider_name: str
    task_id: str
    goal_id: str
    phase: str
    prompt: str
    system_prompt: str
    target_project_dir: str
    task_title: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the provider request for debugging and persistence."""

        return asdict(self)


@dataclass(frozen=True)
class AIProviderResponse:
    """Normalized provider response for placeholder and future live providers."""

    provider_name: str
    model_name: str
    success: bool
    mode: str
    content: str
    started_at: str
    finished_at: str
    latency_seconds: float
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the provider response for logs and reports."""

        return asdict(self)


class BaseAIProvider:
    """Base contract for AI providers used by AIExecutor."""

    provider_name = "base"

    def __init__(self, config: AIProviderConfig) -> None:
        self.config = config

    def generate(self, request: AIProviderRequest) -> AIProviderResponse:
        """Generate content for an AI task."""

        raise NotImplementedError


class LocalTemplateProvider(BaseAIProvider):
    """Return deterministic local template output for AI-enabled tasks."""

    provider_name = "local_placeholder"

    def generate(self, request: AIProviderRequest) -> AIProviderResponse:
        started_at = utc_now()
        started_clock = perf_counter()
        content = (
            "Local template provider response.\n"
            f"Phase: {request.phase}\n"
            f"Task: {request.task_id}\n"
            f"Goal: {request.goal_id}\n"
            f"Target: {request.target_project_dir}\n"
            "Mode: read-only placeholder generation.\n"
            "Next step: keep results as preview artifacts until a later phase enables reviewed live provider calls."
        )
        latency_seconds = round(perf_counter() - started_clock, 4)
        return AIProviderResponse(
            provider_name=self.provider_name,
            model_name="local-template-v1",
            success=True,
            mode="local_template",
            content=content,
            started_at=started_at,
            finished_at=utc_now(),
            latency_seconds=latency_seconds,
            metadata={
                "request_prompt_length": len(request.prompt),
                "system_prompt_length": len(request.system_prompt),
                "allow_live_calls": self.config.allow_live_calls,
            },
        )


class OpenAIProvider(BaseAIProvider):
    """Configuration-aware placeholder for a future OpenAI-backed provider.

    AI-Phase2 keeps this provider non-networked. It reports whether a future
    live configuration is present, but it still returns deterministic local
    content so the workflow remains safe and fully runnable offline.
    """

    provider_name = "openai"

    def generate(self, request: AIProviderRequest) -> AIProviderResponse:
        started_at = utc_now()
        started_clock = perf_counter()
        live_call_ready = self.config.allow_live_calls and self.config.has_openai_api_key
        if live_call_ready:
            mode = "openai_live_disabled_by_phase"
            content = (
                "OpenAI provider is configured, but AI-Phase2 keeps live calls disabled. "
                "Use this response as a placeholder until a later phase introduces approved network execution."
            )
        elif self.config.has_openai_api_key:
            mode = "openai_configured_placeholder"
            content = (
                "OpenAI API key is present, but live calls are not enabled. "
                "Returning deterministic placeholder content."
            )
        else:
            mode = "openai_unconfigured_placeholder"
            content = (
                "OpenAI provider selected without API credentials. "
                "Returning deterministic placeholder content and keeping the workflow local."
            )

        latency_seconds = round(perf_counter() - started_clock, 4)
        return AIProviderResponse(
            provider_name=self.provider_name,
            model_name=self.config.openai_model,
            success=True,
            mode=mode,
            content=content,
            started_at=started_at,
            finished_at=utc_now(),
            latency_seconds=latency_seconds,
            metadata={
                "has_openai_api_key": self.config.has_openai_api_key,
                "allow_live_calls": self.config.allow_live_calls,
                "timeout_seconds": self.config.timeout_seconds,
                "max_retries": self.config.max_retries,
            },
        )


def load_ai_provider_config(provider_name: str | None = None) -> AIProviderConfig:
    """Resolve provider configuration from CLI preference and environment."""

    resolved_name = (provider_name or os.getenv("APDA_AI_PROVIDER") or "local_placeholder").strip().lower()
    timeout_seconds = float(os.getenv("APDA_AI_TIMEOUT_SECONDS", "30"))
    max_retries = int(os.getenv("APDA_AI_MAX_RETRIES", "1"))
    allow_live_calls = _env_flag("APDA_AI_ALLOW_LIVE_CALLS", default=False)
    openai_model = os.getenv("APDA_OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
    has_openai_api_key = bool(os.getenv("OPENAI_API_KEY"))
    return AIProviderConfig(
        provider_name=resolved_name,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        allow_live_calls=allow_live_calls,
        openai_model=openai_model,
        has_openai_api_key=has_openai_api_key,
    )


def provider_status_snapshot(config: AIProviderConfig) -> dict[str, Any]:
    """Build a CLI- and dashboard-friendly provider status snapshot."""

    return {
        "provider_name": config.provider_name,
        "timeout_seconds": config.timeout_seconds,
        "max_retries": config.max_retries,
        "allow_live_calls": config.allow_live_calls,
        "openai_model": config.openai_model,
        "has_openai_api_key": config.has_openai_api_key,
        "available_providers": ["local_placeholder", "mock", "openai"],
    }


def resolve_ai_provider(provider_name: str | None = None) -> BaseAIProvider:
    """Resolve a provider implementation from configuration or explicit name."""

    config = load_ai_provider_config(provider_name)
    if config.provider_name in {"local_placeholder", "local_template", "mock"}:
        return LocalTemplateProvider(config)
    if config.provider_name == "openai":
        return OpenAIProvider(config)
    return LocalTemplateProvider(
        AIProviderConfig(
            provider_name="local_placeholder",
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
            allow_live_calls=False,
            openai_model=config.openai_model,
            has_openai_api_key=config.has_openai_api_key,
        )
    )

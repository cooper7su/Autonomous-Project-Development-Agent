"""Provider abstraction for AI-Phase2.

This module keeps provider selection, configuration, and response normalization
separate from task execution. The current implementation stays local and safe:

- `LocalTemplateProvider` returns deterministic placeholder content.
- `OpenAIProvider` is a configuration-aware placeholder and does not perform
  live network calls unless a later phase explicitly enables that behavior.

Future phases can extend these classes with approval-aware live requests,
response parsing, caching, and richer error handling. AI-Phase4 extends the
same interface with preview-only candidate code and patch-summary responses so
the workflow can create engineering artifacts without mutating the repository.
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


def _candidate_symbol_name(task_id: str, target_file: str) -> str:
    """Derive a stable Python symbol name for preview-only candidate code."""

    stem = target_file.rsplit("/", 1)[-1].split(".", 1)[0] if target_file else task_id
    tokens = [token for token in stem.replace("-", "_").split("_") if token]
    if not tokens:
        tokens = [token for token in task_id.replace("-", "_").split("_") if token]
    return "".join(token[:1].upper() + token[1:] for token in tokens) or "CandidatePreview"


def _build_candidate_preview_payload(
    request: AIProviderRequest,
    *,
    provider_label: str,
    guidance_note: str,
) -> tuple[str, dict[str, Any]]:
    """Build a deterministic preview-only candidate payload."""

    target_file = str(
        request.metadata.get("candidate_target_file")
        or "src/autonomous_project_development_agent/preview_candidate.py"
    )
    change_type = str(request.metadata.get("candidate_change_type", "add_preview_module"))
    preview_only = bool(request.metadata.get("preview_only", True))
    not_applied = bool(request.metadata.get("not_applied", True))
    requires_review = bool(request.metadata.get("requires_review", True))
    risk_level = str(request.metadata.get("risk_level", "low"))
    symbol_name = _candidate_symbol_name(request.task_id, target_file)

    candidate_code = "\n".join(
        [
            f'"""Preview-only candidate generated for {request.task_id}.',
            "",
            "This file is not applied automatically by the workflow.",
            '"""',
            "",
            f"class {symbol_name}:",
            '    """Preview helper proposed by the AI-Phase4 code-assist pipeline."""',
            "",
            "    def summarize(self) -> dict[str, object]:",
            "        return {",
            f'            "goal_id": "{request.goal_id}",',
            f'            "phase": "{request.phase}",',
            f'            "task_id": "{request.task_id}",',
            f'            "target_file": "{target_file}",',
            f'            "provider": "{provider_label}",',
            f'            "preview_only": {preview_only},',
            "        }",
            "",
            "",
            "def build_candidate_preview() -> dict[str, object]:",
            f"    return {symbol_name}().summarize()",
        ]
    )

    patch_summary = [
        {
            "target_file": target_file,
            "change_type": change_type,
            "summary": (
                "Add a preview-only helper module that packages scan metrics, memory context, "
                "and safe next-step recommendations behind one reusable Python object."
            ),
            "preview_only": preview_only,
            "not_applied": not_applied,
            "requires_review": requires_review,
            "risk_level": risk_level,
        }
    ]
    rationale = (
        "The candidate stays read-only and artifact-only so developers can review a concrete "
        "implementation direction before any repository mutation is considered."
    )
    labels = ["preview_only", "not_applied", "requires_review", "ai_phase4"]

    content = "\n".join(
        [
            f"{provider_label} code-assist response.",
            f"Phase: {request.phase}",
            f"Task: {request.task_id}",
            f"Target file: {target_file}",
            f"Guidance: {guidance_note}",
            "Preview labels: preview_only, not_applied, requires_review",
        ]
    )
    metadata = {
        "request_kind": str(request.metadata.get("request_kind", "code_assist")),
        "candidate_code": candidate_code,
        "candidate_patch_summary": patch_summary,
        "target_file": target_file,
        "rationale": rationale,
        "risk_level": risk_level,
        "preview_only": preview_only,
        "not_applied": not_applied,
        "requires_review": requires_review,
        "labels": labels,
        "candidate_change_type": change_type,
        "guidance_note": guidance_note,
        "request_prompt_length": len(request.prompt),
        "system_prompt_length": len(request.system_prompt),
    }
    return content, metadata


class LocalTemplateProvider(BaseAIProvider):
    """Return deterministic local template output for AI-enabled tasks."""

    provider_name = "local_placeholder"

    def generate(self, request: AIProviderRequest) -> AIProviderResponse:
        started_at = utc_now()
        started_clock = perf_counter()
        request_kind = str(request.metadata.get("request_kind", "task_execution"))
        if request_kind == "task_planning":
            recommended_adjustments = [
                "Prioritize safe project-scan tasks before review-oriented tasks.",
                "Increase retry budget for AI-capable tasks by one attempt.",
                "Keep read-only local scan tasks eligible for parallel grouping where dependencies allow it.",
            ]
            content = "\n".join(
                [
                    "Local template provider planning response.",
                    f"Phase: {request.phase}",
                    f"Goal: {request.goal_id}",
                    "Planning strategy: scan first, then synthesize, then review.",
                    "Recommended adjustments:",
                    *[f"- {item}" for item in recommended_adjustments],
                ]
            )
            metadata = {
                "request_kind": request_kind,
                "planning_strategy": "scan_first_parallel_then_review",
                "recommended_parallel_batch": "project_scan",
                "recommended_adjustments": recommended_adjustments,
                "boost_ai_tasks": True,
                "boost_memory_tasks": True,
                "allow_live_calls": self.config.allow_live_calls,
                "request_prompt_length": len(request.prompt),
                "system_prompt_length": len(request.system_prompt),
            }
        elif request_kind in {"code_assist", "patch_preview"}:
            content, metadata = _build_candidate_preview_payload(
                request,
                provider_label="Local template provider",
                guidance_note="Keep all candidate code as preview artifacts until explicit approval exists.",
            )
            metadata["allow_live_calls"] = self.config.allow_live_calls
        else:
            content = (
                "Local template provider response.\n"
                f"Phase: {request.phase}\n"
                f"Task: {request.task_id}\n"
                f"Goal: {request.goal_id}\n"
                f"Target: {request.target_project_dir}\n"
                "Mode: read-only placeholder generation.\n"
                "Next step: keep results as preview artifacts until a later phase enables reviewed live provider calls."
            )
            metadata = {
                "request_kind": request_kind,
                "request_prompt_length": len(request.prompt),
                "system_prompt_length": len(request.system_prompt),
                "allow_live_calls": self.config.allow_live_calls,
            }
        latency_seconds = round(perf_counter() - started_clock, 4)
        return AIProviderResponse(
            provider_name=self.provider_name,
            model_name="local-template-v1",
            success=True,
            mode=(
                "local_template_planning"
                if request_kind == "task_planning"
                else "local_template_code_assist"
                if request_kind in {"code_assist", "patch_preview"}
                else "local_template"
            ),
            content=content,
            started_at=started_at,
            finished_at=utc_now(),
            latency_seconds=latency_seconds,
            metadata=metadata,
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
        request_kind = str(request.metadata.get("request_kind", "task_execution"))
        live_call_ready = self.config.allow_live_calls and self.config.has_openai_api_key
        if request_kind == "task_planning":
            if live_call_ready:
                mode = "openai_planning_live_disabled_by_phase"
                content = (
                    "OpenAI planning provider is configured, but AI-Phase3 keeps live planning calls disabled. "
                    "Use this provider response as a safe placeholder."
                )
            elif self.config.has_openai_api_key:
                mode = "openai_planning_configured_placeholder"
                content = (
                    "OpenAI planning provider is configured with credentials, but live calls remain disabled. "
                    "Returning deterministic planning guidance."
                )
            else:
                mode = "openai_planning_unconfigured_placeholder"
                content = (
                    "OpenAI planning provider selected without API credentials. "
                    "Returning deterministic planning guidance and keeping the workflow local."
                )
            recommended_adjustments = [
                "Group independent scan tasks for earlier feedback.",
                "Promote AI-capable synthesis and review tasks after local artifact generation.",
                "Record provider planning rationale in the persisted plan for auditability.",
            ]
            metadata = {
                "request_kind": request_kind,
                "planning_strategy": "provider_guided_placeholder",
                "recommended_parallel_batch": "project_scan",
                "recommended_adjustments": recommended_adjustments,
                "boost_ai_tasks": True,
                "boost_memory_tasks": True,
                "has_openai_api_key": self.config.has_openai_api_key,
                "allow_live_calls": self.config.allow_live_calls,
                "timeout_seconds": self.config.timeout_seconds,
                "max_retries": self.config.max_retries,
            }
        elif request_kind in {"code_assist", "patch_preview"}:
            if live_call_ready:
                mode = "openai_code_assist_live_disabled_by_phase"
                guidance_note = "OpenAI is configured, but AI-Phase4 keeps code-assist in preview-only placeholder mode."
            elif self.config.has_openai_api_key:
                mode = "openai_code_assist_configured_placeholder"
                guidance_note = "OpenAI credentials are present, but live candidate generation remains disabled."
            else:
                mode = "openai_code_assist_unconfigured_placeholder"
                guidance_note = "OpenAI was selected without credentials, so deterministic local preview content is returned."
            content, metadata = _build_candidate_preview_payload(
                request,
                provider_label="OpenAI placeholder provider",
                guidance_note=guidance_note,
            )
            metadata.update(
                {
                    "has_openai_api_key": self.config.has_openai_api_key,
                    "allow_live_calls": self.config.allow_live_calls,
                    "timeout_seconds": self.config.timeout_seconds,
                    "max_retries": self.config.max_retries,
                }
            )
        elif live_call_ready:
            mode = "openai_live_disabled_by_phase"
            content = (
                "OpenAI provider is configured, but AI-Phase2 keeps live calls disabled. "
                "Use this response as a placeholder until a later phase introduces approved network execution."
            )
            metadata = {
                "request_kind": request_kind,
                "has_openai_api_key": self.config.has_openai_api_key,
                "allow_live_calls": self.config.allow_live_calls,
                "timeout_seconds": self.config.timeout_seconds,
                "max_retries": self.config.max_retries,
            }
        elif self.config.has_openai_api_key:
            mode = "openai_configured_placeholder"
            content = (
                "OpenAI API key is present, but live calls are not enabled. "
                "Returning deterministic placeholder content."
            )
            metadata = {
                "request_kind": request_kind,
                "has_openai_api_key": self.config.has_openai_api_key,
                "allow_live_calls": self.config.allow_live_calls,
                "timeout_seconds": self.config.timeout_seconds,
                "max_retries": self.config.max_retries,
            }
        else:
            mode = "openai_unconfigured_placeholder"
            content = (
                "OpenAI provider selected without API credentials. "
                "Returning deterministic placeholder content and keeping the workflow local."
            )
            metadata = {
                "request_kind": request_kind,
                "has_openai_api_key": self.config.has_openai_api_key,
                "allow_live_calls": self.config.allow_live_calls,
                "timeout_seconds": self.config.timeout_seconds,
                "max_retries": self.config.max_retries,
            }

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
            metadata=metadata,
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

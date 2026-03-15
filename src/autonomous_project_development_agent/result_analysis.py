"""Result analysis and historical scoring for the Phase2 to Phase5 workflows.

Phase5 extends the analysis layer with:
- local task history and workflow history persistence,
- task success/failure/retry statistics,
- lightweight heuristic support for later scheduling adjustments,
- richer visualization payloads for Streamlit.

Future phases can replace these deterministic checks with stronger evaluation,
policy-aware scoring, and richer observability pipelines.
AI-Phase1 extends reporting with task-level AI routing metadata.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .executor import ExecutionContext, TaskResult
from .task_planning import PlannedTask


def utc_now() -> str:
    """Return an ISO 8601 timestamp in UTC."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _read_json_file(path: Path) -> dict[str, Any] | None:
    """Read a JSON file if it exists and contains valid content."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    """Write deterministic JSON content to disk."""
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def task_history_path(state_dir: str | Path) -> Path:
    """Return the task-history state file path."""
    return Path(state_dir) / "task_history.json"


def workflow_history_path(state_dir: str | Path) -> Path:
    """Return the workflow-history state file path."""
    return Path(state_dir) / "workflow_history.json"


def load_task_history(state_dir: str | Path) -> dict[str, Any]:
    """Load aggregated task execution history."""
    payload = _read_json_file(task_history_path(state_dir)) or {
        "updated_at": None,
        "task_profile_count": 0,
        "task_profiles": {},
        "recent_runs": [],
    }
    payload["task_profile_count"] = len(payload.get("task_profiles", {}))
    return payload


def load_workflow_history(state_dir: str | Path) -> dict[str, Any]:
    """Load summarized workflow run history."""
    return _read_json_file(workflow_history_path(state_dir)) or {
        "updated_at": None,
        "run_count": 0,
        "recent_runs": [],
    }


@dataclass(frozen=True)
class AnalysisReport:
    """Structured evaluation for one task result."""

    task_id: str
    status: str
    summary: str
    recommended_action: str
    human_intervention_required: bool
    review_required: bool = False
    preview_status: str | None = None
    verification_checks: dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0
    visualization_payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report into JSON-friendly data."""
        return asdict(self)


def analyze_task_result(
    task: PlannedTask,
    result: TaskResult,
    context: ExecutionContext,
) -> AnalysisReport:
    """Classify one task result."""
    checks: dict[str, Any] = {
        "returncode": result.returncode,
        "success_flag": result.success,
        "artifact_exists": bool(result.artifact_path and Path(result.artifact_path).exists()),
        "target_project_dir": context.target_project_dir,
        "executor_type": task.executor_type,
        "actual_executor_type": result.executor_type,
        "requested_executor_type": result.requested_executor_type or task.executor_type,
        "task_use_ai": task.use_ai,
        "ai_enabled": context.enable_ai,
        "duration_seconds": result.duration_seconds,
    }
    operation = task.metadata.get("operation")
    is_code_assist_task = str(task.metadata.get("ai_request_kind", "")).strip().lower() in {"code_assist", "patch_preview"}

    if is_code_assist_task and context.enable_ai:
        candidate_preview = result.output.get("candidate_preview", {})
        candidate_verification = result.output.get("candidate_verification", {})
        summary_markdown = result.output.get("summary_markdown", "")
        checks["summary_present"] = bool(summary_markdown.strip())
        checks["candidate_preview_present"] = bool(candidate_preview)
        checks["candidate_code_present"] = bool(str(result.output.get("candidate_code", "")).strip())
        checks["patch_summary_count"] = len(result.output.get("candidate_patch_summary", []))
        checks["preview_status"] = result.output.get("preview_status")
        checks["preview_only"] = bool(result.output.get("preview_only", False))
        checks["not_applied"] = bool(result.output.get("not_applied", False))
        checks["review_required"] = bool(result.output.get("requires_review", False))
        checks["verification_present"] = bool(candidate_verification)
        checks["verification_passed"] = bool(candidate_verification.get("verification_passed", False))
        checks["path_safety_check"] = bool(candidate_verification.get("path_safety_check", False))
        checks["syntax_validation"] = bool(candidate_verification.get("syntax_validation", False))
        checks["target_within_project"] = bool(candidate_verification.get("target_within_project", False))
        checks["candidate_preview_artifact_exists"] = bool(
            result.output.get("candidate_preview_artifact")
            and Path(str(result.output.get("candidate_preview_artifact"))).exists()
        )
        checks["candidate_code_artifact_exists"] = bool(
            result.output.get("candidate_code_artifact")
            and Path(str(result.output.get("candidate_code_artifact"))).exists()
        )
        checks["candidate_verification_artifact_exists"] = bool(
            result.output.get("candidate_verification_artifact")
            and Path(str(result.output.get("candidate_verification_artifact"))).exists()
        )
        passed = (
            result.success
            and checks["summary_present"]
            and checks["candidate_preview_present"]
            and checks["candidate_code_present"]
            and checks["patch_summary_count"] >= 1
            and checks["verification_passed"]
            and checks["candidate_preview_artifact_exists"]
            and checks["candidate_code_artifact_exists"]
            and checks["candidate_verification_artifact_exists"]
        )
        review_required = bool(checks["review_required"])
        preview_status = str(checks["preview_status"] or "unknown")
        visualization_payload = {
            "task_id": task.task_id,
            "status": "passed" if passed else "failed",
            "executor_type": task.executor_type,
            "actual_executor_type": result.executor_type,
            "priority": task.priority,
            "execution_mode": task.execution_mode,
            "parallel_group": task.parallel_group,
            "use_ai": task.use_ai,
            "ai_enabled": context.enable_ai,
            "ai_provider": context.ai_provider,
            "duration_seconds": result.duration_seconds,
            "attempt": result.attempt,
            "preview_status": preview_status,
            "review_required": review_required,
            "target_file": result.output.get("target_file"),
            "risk_level": result.output.get("risk_level"),
            "metrics": {
                "verification_passed": checks["verification_passed"],
                "patch_summary_count": checks["patch_summary_count"],
            },
        }
        if passed:
            return AnalysisReport(
                task_id=task.task_id,
                status="passed",
                summary=f"Task '{task.task_id}' completed preview-only candidate generation and local verification.",
                recommended_action="continue",
                human_intervention_required=False,
                review_required=review_required,
                preview_status=preview_status,
                verification_checks=checks,
                confidence_score=0.9,
                visualization_payload=visualization_payload,
            )
        if checks["candidate_preview_present"] and not checks["verification_passed"]:
            return AnalysisReport(
                task_id=task.task_id,
                status="failed",
                summary=f"Task '{task.task_id}' generated a candidate preview, but local verification failed and review is required.",
                recommended_action="review_candidate",
                human_intervention_required=True,
                review_required=True,
                preview_status=preview_status,
                verification_checks=checks,
                confidence_score=0.12,
                visualization_payload=visualization_payload,
            )
        return AnalysisReport(
            task_id=task.task_id,
            status="retryable",
            summary=f"Task '{task.task_id}' did not produce a complete candidate preview package yet.",
            recommended_action="retry",
            human_intervention_required=False,
            review_required=review_required,
            preview_status=preview_status,
            verification_checks=checks,
            confidence_score=0.3,
            visualization_payload=visualization_payload,
        )

    if task.task_id == "inspect_project_directory":
        checks["entry_count"] = result.output.get("top_level_entry_count", -1)
        passed = result.success and checks["entry_count"] >= 0
    elif task.task_id == "generate_module_list":
        checks["module_count"] = result.output.get("module_count", -1)
        checks["python_file_count"] = result.output.get("python_file_count", -1)
        passed = result.success and checks["module_count"] >= 0
    elif task.task_id == "count_python_files":
        checks["python_file_count"] = result.output.get("python_file_count", -1)
        checks["total_python_lines"] = result.output.get("total_python_lines", -1)
        passed = result.success and checks["python_file_count"] >= 0 and checks["total_python_lines"] >= 0
    elif task.task_id == "draft_preliminary_analysis":
        summary_markdown = result.output.get("summary_markdown", "")
        checks["summary_present"] = bool(summary_markdown.strip())
        checks["mentions_target_dir"] = context.target_project_dir in summary_markdown
        passed = result.success and checks["summary_present"] and checks["mentions_target_dir"]
    elif task.task_id == "retrieve_memory_context":
        checks["goal_count"] = result.output.get("goal_count", -1)
        checks["vector_count"] = result.output.get("vector_count", -1)
        checks["retrieved_goal_count"] = result.output.get("retrieved_goal_count", -1)
        passed = result.success and checks["goal_count"] >= 0 and checks["retrieved_goal_count"] >= 0
    elif operation == "summarize_project_artifacts":
        checks["total_tracked_files"] = result.output.get("total_tracked_files", -1)
        checks["suffix_count"] = len(result.output.get("suffix_counts", {}))
        passed = result.success and checks["total_tracked_files"] >= 0 and checks["suffix_count"] >= 0
    elif task.task_id == "execute_sample_python_task":
        checks["dataset_count"] = result.output.get("dataset_count", -1)
        checks["mean"] = result.output.get("mean", -1)
        checks["script_preview_present"] = bool(result.output.get("script_preview", "").strip())
        passed = result.success and checks["dataset_count"] > 0 and checks["mean"] >= 0 and checks["script_preview_present"]
    elif task.task_id == "compile_phase5_task_tree":
        summary_markdown = result.output.get("summary_markdown", "")
        checks["summary_present"] = bool(summary_markdown.strip())
        checks["suggested_subtask_count"] = len(result.output.get("suggested_subtasks", []))
        passed = result.success and checks["summary_present"] and checks["suggested_subtask_count"] >= 1
    elif task.task_id in {"propose_autonomous_stub", "propose_phase4_actions", "propose_phase5_actions"}:
        summary_markdown = result.output.get("summary_markdown", "")
        code_preview = result.output.get("generated_code_preview", "")
        code_artifact = result.output.get("generated_code_artifact")
        checks["summary_present"] = bool(summary_markdown.strip())
        checks["code_preview_present"] = bool(code_preview.strip())
        checks["code_artifact_exists"] = bool(code_artifact and Path(code_artifact).exists())
        checks["suggested_action_count"] = len(result.output.get("suggested_actions", []))
        passed = (
            result.success
            and checks["summary_present"]
            and checks["code_preview_present"]
            and checks["code_artifact_exists"]
            and checks["suggested_action_count"] >= 1
        )
    elif task.task_id == "draft_iteration_review":
        summary_markdown = result.output.get("summary_markdown", "")
        checks["summary_present"] = bool(summary_markdown.strip())
        checks["recommended_next_action_count"] = len(result.output.get("recommended_next_actions", []))
        checks["mentions_phase5"] = "Phase5" in summary_markdown
        passed = (
            result.success
            and checks["summary_present"]
            and checks["recommended_next_action_count"] >= 1
            and checks["mentions_phase5"]
        )
    elif task.task_id == "draft_self_optimization_review":
        summary_markdown = result.output.get("summary_markdown", "")
        checks["summary_present"] = bool(summary_markdown.strip())
        checks["recommended_next_action_count"] = len(result.output.get("recommended_next_actions", []))
        checks["mentions_local_optimization"] = "optimization" in summary_markdown.lower()
        passed = (
            result.success
            and checks["summary_present"]
            and checks["recommended_next_action_count"] >= 1
            and checks["mentions_local_optimization"]
        )
    else:
        passed = result.success

    if task.use_ai and context.enable_ai:
        checks["ai_metadata_present"] = bool(result.ai_metadata or result.output.get("ai_execution"))
        passed = passed and checks["ai_metadata_present"]

    truthy_checks = sum(
        1
        for key, value in checks.items()
        if key not in {"returncode", "duration_seconds"} and bool(value if not isinstance(value, int | float) else value >= 0)
    )
    confidence_score = round(min(0.99, 0.2 + (truthy_checks / max(len(checks), 1)) * 0.75), 2) if passed else 0.35
    status = "passed" if passed else "retryable" if result.returncode != 0 or not checks.get("artifact_exists", False) else "failed"
    visualization_payload = {
        "task_id": task.task_id,
        "status": status,
        "executor_type": task.executor_type,
        "actual_executor_type": result.executor_type,
        "priority": task.priority,
        "execution_mode": task.execution_mode,
        "parallel_group": task.parallel_group,
        "use_ai": task.use_ai,
        "ai_enabled": context.enable_ai,
        "ai_provider": context.ai_provider,
        "duration_seconds": result.duration_seconds,
        "attempt": result.attempt,
        "metrics": {
            "python_file_count": result.output.get("python_file_count"),
            "module_count": result.output.get("module_count"),
            "top_level_entry_count": result.output.get("top_level_entry_count"),
            "retrieved_goal_count": result.output.get("retrieved_goal_count"),
            "total_tracked_files": result.output.get("total_tracked_files"),
            "dataset_count": result.output.get("dataset_count"),
        },
    }

    if passed:
        return AnalysisReport(
            task_id=task.task_id,
            status="passed",
            summary=f"Task '{task.task_id}' satisfied the {context.phase} verification checks.",
            recommended_action="continue",
            human_intervention_required=False,
            review_required=False,
            preview_status=result.output.get("preview_status"),
            verification_checks=checks,
            confidence_score=confidence_score,
            visualization_payload=visualization_payload,
        )

    retryable = status == "retryable"
    return AnalysisReport(
        task_id=task.task_id,
        status=status,
        summary=f"Task '{task.task_id}' did not satisfy the {context.phase} verification checks.",
        recommended_action="retry" if retryable else "human_intervention",
        human_intervention_required=not retryable,
        review_required=False,
        preview_status=result.output.get("preview_status"),
        verification_checks=checks,
        confidence_score=0.35 if retryable else 0.1,
        visualization_payload=visualization_payload,
    )


def update_task_history(
    state_dir: str | Path,
    goal_payload: dict[str, Any],
    task: PlannedTask,
    result: TaskResult,
    analysis: AnalysisReport,
) -> dict[str, Any]:
    """Update aggregated task execution history after one task attempt."""
    path = Path(state_dir)
    path.mkdir(parents=True, exist_ok=True)
    payload = load_task_history(path)
    profiles = dict(payload.get("task_profiles", {}))
    profile = dict(
        profiles.get(
            task.task_id,
            {
                "task_id": task.task_id,
                "title": task.title,
                "module_name": task.module_name,
                "executor_type": task.executor_type,
                "runs": 0,
                "passed": 0,
                "failed": 0,
                "retryable": 0,
                "total_retries": 0,
                "total_duration_seconds": 0.0,
                "average_duration_seconds": 0.0,
                "average_confidence_score": 0.0,
                "success_rate": 0.0,
                "failure_rate": 0.0,
                "retry_rate": 0.0,
                "use_ai": bool(task.use_ai),
                "last_provider": None,
                "last_status": None,
                "last_run_at": None,
                "last_actual_executor_type": None,
                "last_requested_executor_type": None,
            },
        )
    )

    profile["runs"] = int(profile.get("runs", 0)) + 1
    if analysis.status == "passed":
        profile["passed"] = int(profile.get("passed", 0)) + 1
    elif analysis.status == "retryable":
        profile["retryable"] = int(profile.get("retryable", 0)) + 1
    else:
        profile["failed"] = int(profile.get("failed", 0)) + 1

    if result.attempt > 1:
        profile["total_retries"] = int(profile.get("total_retries", 0)) + 1

    profile["total_duration_seconds"] = round(
        float(profile.get("total_duration_seconds", 0.0)) + float(result.duration_seconds),
        4,
    )
    profile["average_duration_seconds"] = round(
        profile["total_duration_seconds"] / max(profile["runs"], 1),
        4,
    )
    profile["average_confidence_score"] = round(
        (
            float(profile.get("average_confidence_score", 0.0)) * (profile["runs"] - 1)
            + float(analysis.confidence_score)
        )
        / max(profile["runs"], 1),
        3,
    )
    profile["success_rate"] = round(profile["passed"] / max(profile["runs"], 1), 3)
    profile["failure_rate"] = round(profile["failed"] / max(profile["runs"], 1), 3)
    profile["retry_rate"] = round(profile["retryable"] / max(profile["runs"], 1), 3)
    profile["last_status"] = analysis.status
    profile["last_run_at"] = analysis.created_at
    profile["last_goal_id"] = goal_payload.get("goal_id")
    profile["last_phase"] = goal_payload.get("phase")
    profile["use_ai"] = bool(task.use_ai)
    profile["last_provider"] = result.ai_metadata.get("provider")
    profile["last_actual_executor_type"] = result.executor_type
    profile["last_requested_executor_type"] = result.requested_executor_type or task.executor_type

    profiles[task.task_id] = profile
    recent_runs = list(payload.get("recent_runs", []))
    recent_runs.insert(
        0,
        {
            "task_id": task.task_id,
            "goal_id": goal_payload.get("goal_id"),
            "phase": goal_payload.get("phase"),
            "status": analysis.status,
            "attempt": result.attempt,
            "confidence_score": analysis.confidence_score,
            "duration_seconds": result.duration_seconds,
            "timestamp": analysis.created_at,
        },
    )

    updated_payload = {
        "updated_at": utc_now(),
        "task_profile_count": len(profiles),
        "task_profiles": profiles,
        "recent_runs": recent_runs[:250],
    }
    _write_json_file(task_history_path(path), updated_payload)
    return updated_payload


def query_task_history(
    state_dir: str | Path,
    query_text: str | None = None,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """Query local task history using deterministic text matching."""
    payload = load_task_history(state_dir)
    normalized_query = " ".join((query_text or "").strip().split()).lower()
    profiles = list(payload.get("task_profiles", {}).values())

    if not normalized_query:
        ordered_profiles = sorted(
            profiles,
            key=lambda entry: (-(entry.get("runs", 0)), entry.get("task_id", "")),
        )
        matches = ordered_profiles[:limit]
    else:
        matches = []
        for entry in profiles:
            haystack = " ".join(
                [
                    str(entry.get("task_id", "")),
                    str(entry.get("title", "")),
                    str(entry.get("module_name", "")),
                    str(entry.get("executor_type", "")),
                ]
            ).lower()
            if normalized_query in haystack:
                matches.append(entry)
        matches.sort(key=lambda entry: (-(entry.get("runs", 0)), entry.get("task_id", "")))
        matches = matches[:limit]

    return {
        "query": normalized_query or None,
        "match_count": len(matches),
        "matches": matches,
        "task_profile_count": payload.get("task_profile_count", 0),
    }


def update_workflow_history(state_dir: str | Path, final_report: dict[str, Any]) -> dict[str, Any]:
    """Update workflow-run history after one autonomous run."""
    path = Path(state_dir)
    path.mkdir(parents=True, exist_ok=True)
    payload = load_workflow_history(path)
    recent_runs = list(payload.get("recent_runs", []))
    recent_runs.insert(
        0,
        {
            "goal_id": final_report.get("goal", {}).get("goal_id"),
            "phase": final_report.get("phase"),
            "goal_version": final_report.get("goal", {}).get("goal_version", 1),
            "overall_status": final_report.get("summary", {}).get("overall_status"),
            "task_count": final_report.get("summary", {}).get("task_count", 0),
            "passed_tasks": final_report.get("summary", {}).get("passed_tasks", 0),
            "retryable_tasks": final_report.get("summary", {}).get("retryable_tasks", 0),
            "total_duration_seconds": final_report.get("summary", {}).get("total_duration_seconds", 0.0),
            "generated_at": final_report.get("generated_at"),
        },
    )
    updated_payload = {
        "updated_at": utc_now(),
        "run_count": len(recent_runs),
        "recent_runs": recent_runs[:200],
    }
    _write_json_file(workflow_history_path(path), updated_payload)
    return updated_payload


def query_workflow_history(
    state_dir: str | Path,
    query_text: str | None = None,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """Query workflow run history using deterministic text matching."""
    payload = load_workflow_history(state_dir)
    normalized_query = " ".join((query_text or "").strip().split()).lower()
    recent_runs = list(payload.get("recent_runs", []))

    if not normalized_query:
        matches = recent_runs[:limit]
    else:
        matches = []
        for entry in recent_runs:
            haystack = " ".join(
                [
                    str(entry.get("goal_id", "")),
                    str(entry.get("phase", "")),
                    str(entry.get("overall_status", "")),
                ]
            ).lower()
            if normalized_query in haystack:
                matches.append(entry)
        matches = matches[:limit]

    return {
        "query": normalized_query or None,
        "match_count": len(matches),
        "matches": matches,
        "run_count": payload.get("run_count", 0),
    }


def build_final_report(
    goal_payload: dict[str, Any],
    plan_payload: dict[str, Any],
    loop_state_payload: dict[str, Any],
    task_records: list[dict[str, Any]],
    *,
    phase: str = "Phase2",
    memory_state: dict[str, Any] | None = None,
    task_history_state: dict[str, Any] | None = None,
    workflow_history_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create the final structured report for the current workflow phase."""
    memory_state = memory_state or {}
    task_history_state = task_history_state or {}
    workflow_history_state = workflow_history_state or {}

    passed_tasks = sum(1 for record in task_records if record["analysis"]["status"] == "passed")
    failed_tasks = sum(1 for record in task_records if record["analysis"]["status"] == "failed")
    retryable_tasks = sum(1 for record in task_records if record["analysis"]["status"] == "retryable")
    total_duration = round(sum(float(record["result"].get("duration_seconds", 0.0)) for record in task_records), 4)
    average_confidence = round(
        sum(float(record["analysis"].get("confidence_score", 0.0)) for record in task_records) / max(len(task_records), 1),
        2,
    )

    executor_breakdown: dict[str, int] = {}
    actual_executor_breakdown: dict[str, int] = {}
    provider_breakdown: dict[str, int] = {}
    candidate_preview_count = 0
    preview_completed_count = 0
    review_required_count = 0
    verification_failed_count = 0
    candidate_previews: list[dict[str, Any]] = []
    duration_series: list[dict[str, Any]] = []
    retry_series: list[dict[str, Any]] = []
    ai_task_count = 0
    ai_executed_task_count = 0
    for record in task_records:
        executor_type = record["task"].get("executor_type", "unknown")
        executor_breakdown[executor_type] = executor_breakdown.get(executor_type, 0) + 1
        actual_executor_type = record["result"].get("executor_type", executor_type)
        actual_executor_breakdown[actual_executor_type] = actual_executor_breakdown.get(actual_executor_type, 0) + 1
        provider_name = record["result"].get("ai_metadata", {}).get("provider")
        if provider_name:
            provider_breakdown[provider_name] = provider_breakdown.get(provider_name, 0) + 1
        if record["task"].get("use_ai"):
            ai_task_count += 1
        if actual_executor_type == "ai_executor":
            ai_executed_task_count += 1
        candidate_preview = record["result"].get("output", {}).get("candidate_preview")
        candidate_verification = record["result"].get("output", {}).get("candidate_verification", {})
        if candidate_preview:
            candidate_preview_count += 1
            preview_completed = record["result"].get("output", {}).get("preview_status") == "preview_complete"
            if preview_completed:
                preview_completed_count += 1
            if record["analysis"].get("review_required", False):
                review_required_count += 1
            if not candidate_verification.get("verification_passed", False):
                verification_failed_count += 1
            candidate_previews.append(
                {
                    "task_id": record["task"].get("task_id"),
                    "preview_status": record["result"].get("output", {}).get("preview_status"),
                    "review_required": record["analysis"].get("review_required", False),
                    "target_file": candidate_preview.get("target_file"),
                    "risk_level": candidate_preview.get("risk_level"),
                    "provider": candidate_preview.get("provider"),
                    "candidate_preview_artifact": record["result"].get("output", {}).get("candidate_preview_artifact"),
                    "candidate_code_artifact": record["result"].get("output", {}).get("candidate_code_artifact"),
                    "candidate_verification_artifact": record["result"].get("output", {}).get("candidate_verification_artifact"),
                    "verification_passed": candidate_verification.get("verification_passed", False),
                }
            )
        duration_series.append(
            {
                "task_id": record["task"].get("task_id"),
                "duration_seconds": record["result"].get("duration_seconds", 0.0),
                "status": record["analysis"].get("status"),
            }
        )
        retry_series.append(
            {
                "task_id": record["task"].get("task_id"),
                "attempt": record["result"].get("attempt", 1),
                "status": record["analysis"].get("status"),
            }
        )

    task_success_rates = [
        {
            "task_id": profile.get("task_id"),
            "success_rate": profile.get("success_rate", 0.0),
            "retry_rate": profile.get("retry_rate", 0.0),
            "runs": profile.get("runs", 0),
        }
        for profile in task_history_state.get("task_profiles", {}).values()
    ]
    task_success_rates.sort(key=lambda entry: (-float(entry.get("runs", 0)), entry.get("task_id", "")))

    self_optimization = {
        "heuristic_adjustments": plan_payload.get("heuristic_adjustments", []),
        "attention_tasks": [
            profile
            for profile in task_history_state.get("task_profiles", {}).values()
            if float(profile.get("success_rate", 1.0)) < 0.8 or float(profile.get("retry_rate", 0.0)) > 0.2
        ][:10],
    }

    visualization = {
        "task_statuses": [
            {
                "task_id": record["task"]["task_id"],
                "status": record["analysis"]["status"],
                "executor_type": record["task"]["executor_type"],
                "actual_executor_type": record["result"].get("executor_type"),
                "priority": record["task"].get("priority"),
                "parallel_group": record["task"].get("parallel_group"),
                "use_ai": record["task"].get("use_ai", False),
            }
            for record in task_records
        ],
        "summary_counts": {
            "passed": passed_tasks,
            "failed": failed_tasks,
            "retryable": retryable_tasks,
        },
        "ai_summary": {
            "goal_use_ai": bool(goal_payload.get("use_ai", False)),
            "ai_task_count": ai_task_count,
            "ai_executed_task_count": ai_executed_task_count,
            "provider_breakdown": provider_breakdown,
        },
        "candidate_summary": {
            "candidate_preview_count": candidate_preview_count,
            "preview_completed_count": preview_completed_count,
            "review_required_count": review_required_count,
            "verification_failed_count": verification_failed_count,
        },
        "candidate_previews": candidate_previews,
        "review_required_items": [entry for entry in candidate_previews if entry.get("review_required")],
        "dependency_edges": plan_payload.get("dependency_edges", []),
        "duration_series": duration_series,
        "retry_series": retry_series,
        "executor_breakdown": executor_breakdown,
        "actual_executor_breakdown": actual_executor_breakdown,
        "provider_breakdown": provider_breakdown,
        "memory_overview": {
            "goal_count": memory_state.get("goal_count", 0),
            "vector_count": memory_state.get("vector_count", 0),
            "retrieved_goal_count": memory_state.get("retrieved_goal_count", 0),
            "task_profile_count": task_history_state.get("task_profile_count", 0),
            "workflow_run_count": workflow_history_state.get("run_count", 0),
        },
        "task_success_rates": task_success_rates[:15],
    }

    return {
        "generated_at": utc_now(),
        "phase": phase,
        "goal": goal_payload,
        "plan": {
            "goal_id": plan_payload.get("goal_id"),
            "goal_version": plan_payload.get("goal_version", goal_payload.get("goal_version", 1)),
            "task_count": plan_payload.get("task_count", 0),
            "parallel_task_count": plan_payload.get("parallel_task_count", 0),
            "candidate_task_count": plan_payload.get("candidate_task_count", 0),
            "preview_only_task_count": plan_payload.get("preview_only_task_count", 0),
            "review_required_task_count": plan_payload.get("review_required_task_count", 0),
            "executor_breakdown": plan_payload.get("executor_breakdown", {}),
            "heuristic_adjustments": plan_payload.get("heuristic_adjustments", []),
            "planning": plan_payload.get("planning", {}),
        },
        "summary": {
            "overall_status": loop_state_payload.get("overall_status", "unknown"),
            "task_count": len(task_records),
            "passed_tasks": passed_tasks,
            "failed_tasks": failed_tasks,
            "retryable_tasks": retryable_tasks,
            "human_intervention_required": loop_state_payload.get("human_intervention_required", False),
            "goal_use_ai": bool(goal_payload.get("use_ai", False)),
            "ai_task_count": ai_task_count,
            "ai_executed_task_count": ai_executed_task_count,
            "candidate_preview_count": candidate_preview_count,
            "preview_completed_count": preview_completed_count,
            "review_required_count": review_required_count,
            "verification_failed_count": verification_failed_count,
            "total_duration_seconds": total_duration,
            "average_confidence_score": average_confidence,
        },
        "statistics": {
            "total_duration_seconds": total_duration,
            "average_confidence_score": average_confidence,
            "executor_breakdown": executor_breakdown,
            "actual_executor_breakdown": actual_executor_breakdown,
            "provider_breakdown": provider_breakdown,
            "completed_batches": loop_state_payload.get("completed_batches", 0),
            "parallel_task_count": plan_payload.get("parallel_task_count", 0),
            "ai_task_count": ai_task_count,
            "ai_executed_task_count": ai_executed_task_count,
            "candidate_preview_count": candidate_preview_count,
            "preview_completed_count": preview_completed_count,
            "review_required_count": review_required_count,
            "verification_failed_count": verification_failed_count,
            "task_profile_count": task_history_state.get("task_profile_count", 0),
            "workflow_run_count": workflow_history_state.get("run_count", 0),
        },
        "memory_state": memory_state,
        "task_history": {
            "task_profile_count": task_history_state.get("task_profile_count", 0),
            "recent_runs": task_history_state.get("recent_runs", [])[:20],
        },
        "workflow_history": {
            "run_count": workflow_history_state.get("run_count", 0),
            "recent_runs": workflow_history_state.get("recent_runs", [])[:20],
        },
        "self_optimization": self_optimization,
        "candidate_previews": candidate_previews,
        "tasks": task_records,
        "loop_state": loop_state_payload,
        "visualization": visualization,
    }

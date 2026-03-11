"""Result analysis for the Phase2 to Phase4 workflows.

Phase4 extends the analysis layer with:
- richer task-specific checks,
- aggregate scoring and statistics,
- visualization payloads for Streamlit,
- explicit support for memory-aware autonomous review tasks.

Phase5 can replace these lightweight checks with stronger quality gates,
retrieval-augmented evaluation, and richer observability.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .executor import ExecutionContext, TaskResult
from .task_planning import PlannedTask


def utc_now() -> str:
    """Return an ISO 8601 timestamp in UTC."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class AnalysisReport:
    """Structured evaluation for one task result."""

    task_id: str
    status: str
    summary: str
    recommended_action: str
    human_intervention_required: bool
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
        "duration_seconds": result.duration_seconds,
    }
    operation = task.metadata.get("operation")

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
    elif task.task_id in {"propose_autonomous_stub", "propose_phase4_actions"}:
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
    else:
        passed = result.success

    truthy_checks = sum(
        1
        for key, value in checks.items()
        if key not in {"returncode", "duration_seconds"} and bool(value if not isinstance(value, int) else value >= 0)
    )
    confidence_score = round(min(0.99, 0.2 + (truthy_checks / max(len(checks), 1)) * 0.75), 2) if passed else 0.35
    status = "passed" if passed else "retryable" if result.returncode != 0 or not checks.get("artifact_exists", False) else "failed"
    visualization_payload = {
        "task_id": task.task_id,
        "status": status,
        "executor_type": task.executor_type,
        "priority": task.priority,
        "execution_mode": task.execution_mode,
        "parallel_group": task.parallel_group,
        "duration_seconds": result.duration_seconds,
        "metrics": {
            "python_file_count": result.output.get("python_file_count"),
            "module_count": result.output.get("module_count"),
            "top_level_entry_count": result.output.get("top_level_entry_count"),
            "retrieved_goal_count": result.output.get("retrieved_goal_count"),
            "total_tracked_files": result.output.get("total_tracked_files"),
        },
    }

    if passed:
        return AnalysisReport(
            task_id=task.task_id,
            status="passed",
            summary=f"Task '{task.task_id}' satisfied the {context.phase} verification checks.",
            recommended_action="continue",
            human_intervention_required=False,
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
        verification_checks=checks,
        confidence_score=0.35 if retryable else 0.1,
        visualization_payload=visualization_payload,
    )


def build_final_report(
    goal_payload: dict[str, Any],
    plan_payload: dict[str, Any],
    loop_state_payload: dict[str, Any],
    task_records: list[dict[str, Any]],
    *,
    phase: str = "Phase2",
    memory_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create the final structured report for the current workflow phase."""
    memory_state = memory_state or {}
    passed_tasks = sum(1 for record in task_records if record["analysis"]["status"] == "passed")
    failed_tasks = sum(1 for record in task_records if record["analysis"]["status"] == "failed")
    retryable_tasks = sum(1 for record in task_records if record["analysis"]["status"] == "retryable")
    total_duration = round(sum(float(record["result"].get("duration_seconds", 0.0)) for record in task_records), 4)
    average_confidence = round(
        sum(float(record["analysis"].get("confidence_score", 0.0)) for record in task_records) / max(len(task_records), 1),
        2,
    )

    executor_breakdown: dict[str, int] = {}
    duration_series: list[dict[str, Any]] = []
    for record in task_records:
        executor_type = record["task"].get("executor_type", "unknown")
        executor_breakdown[executor_type] = executor_breakdown.get(executor_type, 0) + 1
        duration_series.append(
            {
                "task_id": record["task"].get("task_id"),
                "duration_seconds": record["result"].get("duration_seconds", 0.0),
                "status": record["analysis"].get("status"),
            }
        )

    visualization = {
        "task_statuses": [
            {
                "task_id": record["task"]["task_id"],
                "status": record["analysis"]["status"],
                "executor_type": record["task"]["executor_type"],
                "priority": record["task"].get("priority"),
                "parallel_group": record["task"].get("parallel_group"),
            }
            for record in task_records
        ],
        "summary_counts": {
            "passed": passed_tasks,
            "failed": failed_tasks,
            "retryable": retryable_tasks,
        },
        "dependency_edges": plan_payload.get("dependency_edges", []),
        "duration_series": duration_series,
        "executor_breakdown": executor_breakdown,
        "memory_overview": {
            "goal_count": memory_state.get("goal_count", 0),
            "vector_count": memory_state.get("vector_count", 0),
            "retrieved_goal_count": memory_state.get("retrieved_goal_count", 0),
        },
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
            "executor_breakdown": plan_payload.get("executor_breakdown", {}),
        },
        "summary": {
            "overall_status": loop_state_payload.get("overall_status", "unknown"),
            "task_count": len(task_records),
            "passed_tasks": passed_tasks,
            "failed_tasks": failed_tasks,
            "retryable_tasks": retryable_tasks,
            "human_intervention_required": loop_state_payload.get("human_intervention_required", False),
            "total_duration_seconds": total_duration,
            "average_confidence_score": average_confidence,
        },
        "statistics": {
            "total_duration_seconds": total_duration,
            "average_confidence_score": average_confidence,
            "executor_breakdown": executor_breakdown,
            "completed_batches": loop_state_payload.get("completed_batches", 0),
            "parallel_task_count": plan_payload.get("parallel_task_count", 0),
        },
        "memory_state": memory_state,
        "tasks": task_records,
        "loop_state": loop_state_payload,
        "visualization": visualization,
    }

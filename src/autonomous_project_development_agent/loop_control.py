"""Loop control for the Phase2 to Phase5 workflows.

Phase5 extends the loop controller with:
- local heuristic-aware scheduling,
- richer retry and stop accounting,
- decision traces for historical browsing,
- lightweight adaptive prioritization support.

Future phases can add replanning, approvals, and stronger policy controls.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from .result_analysis import AnalysisReport
from .task_planning import PlannedTask


def utc_now() -> str:
    """Return an ISO 8601 timestamp in UTC."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass
class LoopState:
    """Loop state for Phase2 to Phase5 task orchestration."""

    goal_id: str
    total_tasks: int
    phase: str = "Phase2"
    current_task_index: int = 0
    iteration: int = 0
    max_iterations: int = 24
    completed_batches: int = 0
    completed_task_ids: list[str] = field(default_factory=list)
    failed_task_ids: list[str] = field(default_factory=list)
    retry_counts: dict[str, int] = field(default_factory=dict)
    ready_queue: list[str] = field(default_factory=list)
    running_task_ids: list[str] = field(default_factory=list)
    completed_parallel_groups: list[str] = field(default_factory=list)
    overall_status: str = "pending"
    next_action: str = "next_task"
    stop_reason: str | None = None
    human_intervention_required: bool = False
    history: list[dict[str, Any]] = field(default_factory=list)
    decision_trace: list[dict[str, Any]] = field(default_factory=list)
    statistics: dict[str, Any] = field(
        default_factory=lambda: {
            "passed_tasks": 0,
            "failed_tasks": 0,
            "retryable_events": 0,
            "parallel_batches": 0,
            "total_retries": 0,
            "adaptive_priority_tasks": 0,
            "preview_completed_tasks": 0,
            "review_required_events": 0,
            "verification_failed_tasks": 0,
        }
    )
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the loop state into JSON-friendly data."""
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LoopState":
        """Rebuild loop state from persisted JSON data."""
        return cls(
            goal_id=payload["goal_id"],
            total_tasks=int(payload["total_tasks"]),
            phase=payload.get("phase", "Phase2"),
            current_task_index=int(payload.get("current_task_index", 0)),
            iteration=int(payload.get("iteration", 0)),
            max_iterations=int(payload.get("max_iterations", 24)),
            completed_batches=int(payload.get("completed_batches", 0)),
            completed_task_ids=list(payload.get("completed_task_ids", [])),
            failed_task_ids=list(payload.get("failed_task_ids", [])),
            retry_counts=dict(payload.get("retry_counts", {})),
            ready_queue=list(payload.get("ready_queue", [])),
            running_task_ids=list(payload.get("running_task_ids", [])),
            completed_parallel_groups=list(payload.get("completed_parallel_groups", [])),
            overall_status=payload.get("overall_status", "pending"),
            next_action=payload.get("next_action", "next_task"),
            stop_reason=payload.get("stop_reason"),
            human_intervention_required=bool(payload.get("human_intervention_required", False)),
            history=list(payload.get("history", [])),
            decision_trace=list(payload.get("decision_trace", [])),
            statistics=dict(
                payload.get(
                    "statistics",
                    {
                        "passed_tasks": 0,
                        "failed_tasks": 0,
                        "retryable_events": 0,
                        "parallel_batches": 0,
                        "total_retries": 0,
                        "adaptive_priority_tasks": 0,
                        "preview_completed_tasks": 0,
                        "review_required_events": 0,
                        "verification_failed_tasks": 0,
                    },
                )
            ),
            updated_at=payload.get("updated_at", utc_now()),
        )


def initialize_loop_state(goal_id: str, total_tasks: int, phase: str = "Phase2") -> LoopState:
    """Create the initial loop state for a new run."""
    max_iterations = max(12, total_tasks * (5 if phase == "Phase5" else 4))
    return LoopState(
        goal_id=goal_id,
        total_tasks=total_tasks,
        phase=phase,
        max_iterations=max_iterations,
        overall_status="running" if total_tasks else "passed",
        next_action="next_task" if total_tasks else "stop",
        stop_reason=None if total_tasks else "no_tasks_generated",
    )


def select_ready_tasks(loop_state: LoopState, tasks: list[PlannedTask]) -> list[PlannedTask]:
    """Select the next ready task batch using dependency and priority rules."""
    if loop_state.iteration >= loop_state.max_iterations and len(loop_state.completed_task_ids) < loop_state.total_tasks:
        loop_state.running_task_ids = []
        loop_state.overall_status = "needs_human_intervention"
        loop_state.next_action = "human_intervention"
        loop_state.stop_reason = "max_iterations_reached"
        loop_state.human_intervention_required = True
        loop_state.updated_at = utc_now()
        return []

    completed = set(loop_state.completed_task_ids)
    failed = set(loop_state.failed_task_ids)
    pending = [
        task
        for task in tasks
        if task.task_id not in completed
        and task.task_id not in failed
        and all(dependency in completed for dependency in task.depends_on)
    ]
    pending.sort(
        key=lambda task: (
            -task.priority,
            -min(loop_state.retry_counts.get(task.task_id, 0), 1),
            task.order,
        )
    )
    loop_state.ready_queue = [task.task_id for task in pending]

    if not pending:
        loop_state.running_task_ids = []
        loop_state.current_task_index = len(loop_state.completed_task_ids) + len(loop_state.failed_task_ids)
        if len(loop_state.completed_task_ids) >= loop_state.total_tasks:
            loop_state.overall_status = "passed"
            loop_state.next_action = "stop"
            loop_state.stop_reason = "all_tasks_completed"
        elif loop_state.human_intervention_required:
            loop_state.overall_status = "needs_human_intervention"
            loop_state.next_action = "human_intervention"
        else:
            loop_state.overall_status = "blocked"
            loop_state.next_action = "human_intervention"
            loop_state.human_intervention_required = True
            loop_state.stop_reason = "no_ready_tasks"
        loop_state.updated_at = utc_now()
        return []

    top_task = pending[0]
    if top_task.parallel_group:
        batch = [task for task in pending if task.parallel_group == top_task.parallel_group]
        batch.sort(key=lambda task: task.order)
    else:
        batch = [top_task]

    loop_state.running_task_ids = [task.task_id for task in batch]
    loop_state.overall_status = "running"
    loop_state.next_action = "execute_batch"
    loop_state.updated_at = utc_now()
    loop_state.decision_trace.append(
        {
            "timestamp": loop_state.updated_at,
            "event": "batch_selected",
            "task_ids": loop_state.running_task_ids,
            "phase": loop_state.phase,
            "ready_queue": list(loop_state.ready_queue),
        }
    )
    if any(task.metadata.get("historical_heuristic") for task in batch):
        loop_state.statistics["adaptive_priority_tasks"] = loop_state.statistics.get("adaptive_priority_tasks", 0) + len(batch)
    return batch


def apply_analysis_to_loop(
    loop_state: LoopState,
    task: PlannedTask,
    analysis: AnalysisReport,
) -> LoopState:
    """Advance or stop the loop based on one analysis result."""
    return apply_batch_to_loop(loop_state, [task], [analysis])


def apply_batch_to_loop(
    loop_state: LoopState,
    tasks: list[PlannedTask],
    analyses: list[AnalysisReport],
) -> LoopState:
    """Advance or stop the loop based on a task batch result."""
    loop_state.iteration += 1
    loop_state.completed_batches += 1
    loop_state.updated_at = utc_now()

    if len(tasks) > 1 or any(task.parallel_group for task in tasks):
        loop_state.statistics["parallel_batches"] = loop_state.statistics.get("parallel_batches", 0) + 1

    retryable_task_ids: list[str] = []
    hard_failure_task_ids: list[str] = []

    for task, analysis in zip(tasks, analyses):
        loop_state.history.append(
            {
                "task_id": task.task_id,
                "analysis_status": analysis.status,
                "recommended_action": analysis.recommended_action,
                "review_required": analysis.review_required,
                "preview_status": analysis.preview_status,
                "parallel_group": task.parallel_group,
                "timestamp": loop_state.updated_at,
            }
        )
        if analysis.review_required:
            loop_state.statistics["review_required_events"] = loop_state.statistics.get("review_required_events", 0) + 1
        if analysis.preview_status == "preview_complete":
            loop_state.statistics["preview_completed_tasks"] = loop_state.statistics.get("preview_completed_tasks", 0) + 1

        if analysis.status == "passed":
            if task.task_id not in loop_state.completed_task_ids:
                loop_state.completed_task_ids.append(task.task_id)
                loop_state.statistics["passed_tasks"] = loop_state.statistics.get("passed_tasks", 0) + 1
            if task.parallel_group and task.parallel_group not in loop_state.completed_parallel_groups:
                sibling_ids = {item.task_id for item in tasks if item.parallel_group == task.parallel_group}
                if sibling_ids.issubset(set(loop_state.completed_task_ids) | {task.task_id}):
                    loop_state.completed_parallel_groups.append(task.parallel_group)
            continue

        if analysis.status == "retryable":
            retry_count = loop_state.retry_counts.get(task.task_id, 0) + 1
            loop_state.retry_counts[task.task_id] = retry_count
            loop_state.statistics["retryable_events"] = loop_state.statistics.get("retryable_events", 0) + 1
            loop_state.statistics["total_retries"] = loop_state.statistics.get("total_retries", 0) + 1
            if retry_count <= task.max_retries:
                retryable_task_ids.append(task.task_id)
            else:
                hard_failure_task_ids.append(task.task_id)
                if task.task_id not in loop_state.failed_task_ids:
                    loop_state.failed_task_ids.append(task.task_id)
                    loop_state.statistics["failed_tasks"] = loop_state.statistics.get("failed_tasks", 0) + 1
                loop_state.human_intervention_required = True
            continue

        hard_failure_task_ids.append(task.task_id)
        if task.task_id not in loop_state.failed_task_ids:
            loop_state.failed_task_ids.append(task.task_id)
            loop_state.statistics["failed_tasks"] = loop_state.statistics.get("failed_tasks", 0) + 1
        if analysis.preview_status == "verification_failed":
            loop_state.statistics["verification_failed_tasks"] = loop_state.statistics.get("verification_failed_tasks", 0) + 1
        loop_state.human_intervention_required = True

    loop_state.running_task_ids = []
    loop_state.current_task_index = len(loop_state.completed_task_ids) + len(loop_state.failed_task_ids)
    loop_state.decision_trace.append(
        {
            "timestamp": loop_state.updated_at,
            "event": "batch_completed",
            "task_ids": [task.task_id for task in tasks],
            "statuses": {task.task_id: analysis.status for task, analysis in zip(tasks, analyses)},
            "next_action": loop_state.next_action,
            "statistics": dict(loop_state.statistics),
        }
    )

    if hard_failure_task_ids:
        loop_state.overall_status = "needs_human_intervention"
        loop_state.next_action = "human_intervention"
        if any(analysis.recommended_action == "review_candidate" for analysis in analyses):
            loop_state.stop_reason = f"review_required:{','.join(hard_failure_task_ids)}"
        else:
            loop_state.stop_reason = f"task_failure:{','.join(hard_failure_task_ids)}"
        return loop_state

    if retryable_task_ids:
        loop_state.overall_status = "running"
        loop_state.next_action = "retry"
        loop_state.stop_reason = f"retrying:{','.join(retryable_task_ids)}"
        return loop_state

    if len(loop_state.completed_task_ids) >= loop_state.total_tasks:
        loop_state.overall_status = "passed"
        loop_state.next_action = "stop"
        loop_state.stop_reason = "all_tasks_completed"
        return loop_state

    loop_state.overall_status = "running"
    loop_state.next_action = "next_task"
    loop_state.stop_reason = None
    return loop_state

"""Task planning for the Phase2 to Phase4 workflows.

Phase4 extends the earlier plan layer with:
- multi-task trees,
- explicit dependency edges,
- parallel execution groups,
- richer prompt templates for placeholder Codex/GPT routing.

Phase5 can replace these deterministic templates with adaptive planning,
tool selection, replanning, and policy-aware execution routing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .goal_framework import ProjectGoal, utc_now


@dataclass(frozen=True)
class PlannedTask:
    """A single planned task for the autonomous workflow prototype."""

    task_id: str
    order: int
    module_name: str
    executor_type: str
    title: str
    description: str
    prompt_template: str
    expected_output: str
    verification_hint: str
    max_retries: int = 1
    priority: int = 50
    execution_mode: str = "sequential"
    parallel_group: str | None = None
    depends_on: list[str] = field(default_factory=list)
    callback_channel: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the task into JSON-friendly data."""
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlannedTask":
        """Rebuild a task from persisted JSON data."""
        return cls(
            task_id=payload["task_id"],
            order=int(payload["order"]),
            module_name=payload["module_name"],
            executor_type=payload["executor_type"],
            title=payload["title"],
            description=payload["description"],
            prompt_template=payload["prompt_template"],
            expected_output=payload["expected_output"],
            verification_hint=payload["verification_hint"],
            max_retries=int(payload.get("max_retries", 1)),
            priority=int(payload.get("priority", 50)),
            execution_mode=payload.get("execution_mode", "sequential"),
            parallel_group=payload.get("parallel_group"),
            depends_on=list(payload.get("depends_on", [])),
            callback_channel=payload.get("callback_channel"),
            metadata=dict(payload.get("metadata", {})),
        )


def render_task_prompt(task: PlannedTask, goal: ProjectGoal, memory_status: dict[str, Any] | None = None) -> str:
    """Render a dynamic prompt template for placeholder agent executors."""
    memory_status = memory_status or {}
    return task.prompt_template.format(
        goal=goal.normalized_goal,
        target_dir=goal.target_project_dir,
        phase=goal.phase,
        priority=goal.priority,
        goal_version=goal.goal_version,
        parent_goal_id=goal.parent_goal_id or "none",
        dependency_count=len(task.depends_on),
        memory_goal_count=memory_status.get("goal_count", 0),
        memory_vector_count=memory_status.get("vector_count", 0),
        memory_match_count=memory_status.get("retrieved_goal_count", len(memory_status.get("matches", []))),
    )


def generate_task_plan(goal: ProjectGoal, phase: str | None = None) -> list[PlannedTask]:
    """Generate a deterministic task plan for the requested workflow phase."""
    resolved_phase = phase or goal.phase
    if resolved_phase == "Phase4":
        return _generate_phase4_task_plan(goal)
    if resolved_phase == "Phase3":
        return _generate_phase3_task_plan(goal)
    return _generate_phase2_task_plan(goal)


def _generate_phase2_task_plan(goal: ProjectGoal) -> list[PlannedTask]:
    target_dir = goal.target_project_dir

    return [
        PlannedTask(
            task_id="inspect_project_directory",
            order=1,
            module_name="goal_framework",
            executor_type="local_python",
            title="Inspect target directory",
            description="Read the target project directory and capture a top-level snapshot.",
            prompt_template=(
                "Inspect the local project directory at '{target_dir}' for goal '{goal}'. "
                "Return a safe summary of files and folders without modifying the project."
            ),
            expected_output="A JSON summary of the target path and its top-level entries.",
            verification_hint="The target path must exist and the snapshot must include entry counts.",
            priority=100,
            execution_mode="sequential",
            metadata={
                "operation": "inspect_directory",
                "artifact_name": "directory_snapshot.json",
                "target_dir": target_dir,
            },
        ),
        PlannedTask(
            task_id="generate_module_list",
            order=2,
            module_name="task_planning",
            executor_type="local_python",
            title="Generate module list",
            description="Collect Python source files and derive import-style module names.",
            prompt_template=(
                "Inventory Python files under '{target_dir}' for goal '{goal}'. "
                "Produce module-style names and relative paths."
            ),
            expected_output="A JSON artifact listing Python files and module names.",
            verification_hint="The artifact must contain a file list and module count.",
            priority=90,
            execution_mode="sequential",
            depends_on=["inspect_project_directory"],
            metadata={
                "operation": "list_python_modules",
                "artifact_name": "module_inventory.json",
                "target_dir": target_dir,
            },
        ),
        PlannedTask(
            task_id="count_python_files",
            order=3,
            module_name="executor",
            executor_type="local_python",
            title="Count Python files",
            description="Count Python files and estimate total line volume for a basic project metric.",
            prompt_template=(
                "Count Python files under '{target_dir}' for goal '{goal}'. "
                "Return a small metrics summary suitable for further analysis."
            ),
            expected_output="A JSON artifact containing file count, line count, and representative paths.",
            verification_hint="The metrics artifact must include a non-negative Python file count.",
            priority=80,
            execution_mode="sequential",
            depends_on=["generate_module_list"],
            metadata={
                "operation": "count_python_files",
                "artifact_name": "python_file_metrics.json",
                "target_dir": target_dir,
            },
        ),
        PlannedTask(
            task_id="draft_preliminary_analysis",
            order=4,
            module_name="result_analysis",
            executor_type="placeholder_agent",
            title="Draft preliminary analysis",
            description="Simulate a future agent summary using only the safe local artifacts from prior tasks.",
            prompt_template=(
                "Using the collected directory snapshot, module inventory, and Python metrics for goal "
                "'{goal}', write a preliminary analysis report and recommend a safe next step."
            ),
            expected_output="A markdown-style analysis summary derived from previous task outputs.",
            verification_hint="The summary must mention the target path, module inventory, and file metrics.",
            priority=70,
            execution_mode="sequential",
            depends_on=["count_python_files"],
            metadata={
                "operation": "draft_analysis",
                "artifact_name": "preliminary_analysis.md",
                "target_dir": target_dir,
            },
        ),
    ]


def _generate_phase3_task_plan(goal: ProjectGoal) -> list[PlannedTask]:
    target_dir = goal.target_project_dir

    return [
        PlannedTask(
            task_id="inspect_project_directory",
            order=1,
            module_name="goal_framework",
            executor_type="local_python",
            title="Inspect target directory",
            description="Read the target project directory and capture a top-level snapshot.",
            prompt_template=(
                "Inspect '{target_dir}' for Phase3 goal '{goal}'. Summarize the local project layout "
                "and keep the workflow safe and read-only."
            ),
            expected_output="A JSON summary of the target path and its top-level entries.",
            verification_hint="The target path must exist and the snapshot must include entry counts.",
            priority=100,
            execution_mode="sequential",
            metadata={
                "operation": "inspect_directory",
                "artifact_name": "directory_snapshot.json",
                "target_dir": target_dir,
            },
        ),
        PlannedTask(
            task_id="generate_module_list",
            order=2,
            module_name="task_planning",
            executor_type="local_python",
            title="Generate module list",
            description="Collect Python source files and derive import-style module names.",
            prompt_template=(
                "Inventory Python files under '{target_dir}' for Phase3 goal '{goal}'. "
                "Use memory context count={memory_goal_count} to keep naming stable."
            ),
            expected_output="A JSON artifact listing Python files and module names.",
            verification_hint="The artifact must contain a file list and module count.",
            priority=90,
            execution_mode="parallel",
            parallel_group="project_scan",
            depends_on=["inspect_project_directory"],
            callback_channel="artifact_ready",
            metadata={
                "operation": "list_python_modules",
                "artifact_name": "module_inventory.json",
                "target_dir": target_dir,
            },
        ),
        PlannedTask(
            task_id="count_python_files",
            order=3,
            module_name="executor",
            executor_type="local_python",
            title="Count Python files",
            description="Count Python files and estimate total line volume for a basic project metric.",
            prompt_template=(
                "Count Python files under '{target_dir}' for Phase3 goal '{goal}'. "
                "Prepare metrics for a later autonomous implementation suggestion."
            ),
            expected_output="A JSON artifact containing file count, line count, and representative paths.",
            verification_hint="The metrics artifact must include a non-negative Python file count.",
            priority=90,
            execution_mode="parallel",
            parallel_group="project_scan",
            depends_on=["inspect_project_directory"],
            callback_channel="artifact_ready",
            metadata={
                "operation": "count_python_files",
                "artifact_name": "python_file_metrics.json",
                "target_dir": target_dir,
            },
        ),
        PlannedTask(
            task_id="propose_autonomous_stub",
            order=4,
            module_name="result_analysis",
            executor_type="codex_placeholder",
            title="Propose autonomous stub",
            description="Simulate a Codex/GPT-generated implementation suggestion using local artifacts and memory context.",
            prompt_template=(
                "For goal '{goal}' on '{target_dir}', synthesize a safe implementation stub. "
                "Dependencies={dependency_count}, memory_goals={memory_goal_count}, memory_vectors={memory_vector_count}."
            ),
            expected_output="A markdown summary and Python stub preview derived from prior task outputs.",
            verification_hint="The result must include a generated code preview and reference local metrics.",
            priority=70,
            execution_mode="sequential",
            depends_on=["generate_module_list", "count_python_files"],
            metadata={
                "operation": "codex_stub",
                "artifact_name": "autonomous_stub_suggestion.json",
                "code_artifact_name": "autonomous_stub_preview.py",
                "target_dir": target_dir,
            },
        ),
    ]


def _generate_phase4_task_plan(goal: ProjectGoal) -> list[PlannedTask]:
    target_dir = goal.target_project_dir

    return [
        PlannedTask(
            task_id="inspect_project_directory",
            order=1,
            module_name="goal_framework",
            executor_type="local_python",
            title="Inspect target directory",
            description="Capture a safe top-level snapshot before any memory-aware planning begins.",
            prompt_template=(
                "Inspect '{target_dir}' for Phase4 goal '{goal}'. Goal version={goal_version}. "
                "Keep the workflow read-only and summarize the local layout."
            ),
            expected_output="A JSON summary of the target path and its top-level entries.",
            verification_hint="The target path must exist and the snapshot must include entry counts.",
            priority=130,
            execution_mode="sequential",
            callback_channel="scan_started",
            metadata={
                "operation": "inspect_directory",
                "artifact_name": "directory_snapshot.json",
                "target_dir": target_dir,
            },
        ),
        PlannedTask(
            task_id="retrieve_memory_context",
            order=2,
            module_name="goal_framework",
            executor_type="local_python",
            title="Retrieve memory context",
            description="Load historical goal memory and compute the lightweight similarity context for Phase4 decisions.",
            prompt_template=(
                "Retrieve local memory context for goal '{goal}' with version={goal_version}. "
                "Parent goal={parent_goal_id}, stored goals={memory_goal_count}, matches={memory_match_count}."
            ),
            expected_output="A JSON artifact describing stored goals, vector placeholders, and retrieved goal matches.",
            verification_hint="The artifact must contain goal and vector counts, plus a retrieved match count.",
            priority=120,
            execution_mode="sequential",
            callback_channel="memory_ready",
            metadata={
                "operation": "retrieve_memory_context",
                "artifact_name": "memory_context.json",
                "target_dir": target_dir,
            },
        ),
        PlannedTask(
            task_id="generate_module_list",
            order=3,
            module_name="task_planning",
            executor_type="local_python",
            title="Generate module list",
            description="Collect Python source files and derive module-style names for the project scan.",
            prompt_template=(
                "Inventory Python files under '{target_dir}' for Phase4 goal '{goal}'. "
                "Use retrieved memory matches={memory_match_count} to keep the summary reusable."
            ),
            expected_output="A JSON artifact listing Python files and module names.",
            verification_hint="The artifact must contain a file list and module count.",
            priority=110,
            execution_mode="parallel",
            parallel_group="project_scan",
            depends_on=["inspect_project_directory"],
            callback_channel="artifact_ready",
            metadata={
                "operation": "list_python_modules",
                "artifact_name": "module_inventory.json",
                "target_dir": target_dir,
            },
        ),
        PlannedTask(
            task_id="count_python_files",
            order=4,
            module_name="executor",
            executor_type="local_python",
            title="Count Python files",
            description="Count Python files and estimate project line volume for safe autonomous reporting.",
            prompt_template=(
                "Count Python files under '{target_dir}' for Phase4 goal '{goal}'. "
                "Prepare metrics for autonomous review and retry-free reporting."
            ),
            expected_output="A JSON artifact containing file count, line count, and representative paths.",
            verification_hint="The metrics artifact must include a non-negative Python file count.",
            priority=110,
            execution_mode="parallel",
            parallel_group="project_scan",
            depends_on=["inspect_project_directory"],
            callback_channel="artifact_ready",
            metadata={
                "operation": "count_python_files",
                "artifact_name": "python_file_metrics.json",
                "target_dir": target_dir,
            },
        ),
        PlannedTask(
            task_id="summarize_project_artifacts",
            order=5,
            module_name="result_analysis",
            executor_type="local_python",
            title="Summarize project artifacts",
            description="Build a safe summary of file suffixes and top directories for the Phase4 task tree.",
            prompt_template=(
                "Summarize tracked project artifacts under '{target_dir}' for goal '{goal}'. "
                "Return file suffix counts and top directories for dashboard visualization."
            ),
            expected_output="A JSON artifact containing tracked file counts, suffix breakdown, and top directories.",
            verification_hint="The artifact must contain tracked file counts and a suffix histogram.",
            priority=105,
            execution_mode="parallel",
            parallel_group="project_scan",
            depends_on=["inspect_project_directory"],
            callback_channel="artifact_ready",
            metadata={
                "operation": "summarize_project_artifacts",
                "artifact_name": "project_artifact_summary.json",
                "target_dir": target_dir,
            },
        ),
        PlannedTask(
            task_id="propose_phase4_actions",
            order=6,
            module_name="executor",
            executor_type="codex_placeholder",
            title="Propose Phase4 actions",
            description="Simulate a code-generation agent that prepares safe implementation suggestions from local artifacts.",
            prompt_template=(
                "For Phase4 goal '{goal}' on '{target_dir}', build a safe autonomous suggestion package. "
                "Goal version={goal_version}, dependencies={dependency_count}, memory matches={memory_match_count}."
            ),
            expected_output="A structured suggestion package plus a Python preview derived from local artifacts.",
            verification_hint="The result must include a summary, suggested actions, and a generated code preview.",
            priority=90,
            execution_mode="sequential",
            depends_on=[
                "retrieve_memory_context",
                "generate_module_list",
                "count_python_files",
                "summarize_project_artifacts",
            ],
            callback_channel="suggestion_ready",
            metadata={
                "operation": "phase4_change_suggestion",
                "artifact_name": "phase4_change_suggestion.json",
                "code_artifact_name": "phase4_autonomous_preview.py",
                "target_dir": target_dir,
            },
        ),
        PlannedTask(
            task_id="draft_iteration_review",
            order=7,
            module_name="loop_control",
            executor_type="gpt_placeholder",
            title="Draft iteration review",
            description="Simulate a review-oriented GPT step that turns prior outputs into a structured iteration brief.",
            prompt_template=(
                "Create a Phase4 iteration review for goal '{goal}' on '{target_dir}'. "
                "Summarize task tree outcomes, highlight retry needs, and recommend the next safe loop decision."
            ),
            expected_output="A markdown-style review with next actions, risks, and Phase5 handoff notes.",
            verification_hint="The review must contain summary text and recommended next actions.",
            priority=80,
            execution_mode="sequential",
            depends_on=["propose_phase4_actions"],
            callback_channel="review_ready",
            metadata={
                "operation": "phase4_iteration_review",
                "artifact_name": "phase4_iteration_review.md",
                "target_dir": target_dir,
            },
        ),
    ]


def build_plan_payload(goal: ProjectGoal, tasks: list[PlannedTask], phase: str | None = None) -> dict[str, Any]:
    """Serialize the current plan for persistence and CLI display."""
    resolved_phase = phase or goal.phase
    parallel_task_count = sum(1 for task in tasks if task.execution_mode == "parallel")

    executor_breakdown: dict[str, int] = {}
    parallel_groups: dict[str, list[str]] = {}
    dependency_edges: list[dict[str, str]] = []
    for task in tasks:
        executor_breakdown[task.executor_type] = executor_breakdown.get(task.executor_type, 0) + 1
        if task.parallel_group:
            parallel_groups.setdefault(task.parallel_group, []).append(task.task_id)
        for dependency in task.depends_on:
            dependency_edges.append({"from": dependency, "to": task.task_id})

    return {
        "generated_at": utc_now(),
        "phase": resolved_phase,
        "goal_id": goal.goal_id,
        "goal_version": goal.goal_version,
        "target_project_dir": goal.target_project_dir,
        "task_count": len(tasks),
        "parallel_task_count": parallel_task_count,
        "sequential_task_count": len(tasks) - parallel_task_count,
        "max_parallel_tasks": max(len(task_ids) for task_ids in parallel_groups.values()) if parallel_groups else 1,
        "executor_breakdown": executor_breakdown,
        "parallel_groups": parallel_groups,
        "dependency_edges": dependency_edges,
        "tasks": [task.to_dict() for task in tasks],
    }


def load_tasks(payload: dict[str, Any]) -> list[PlannedTask]:
    """Rebuild a persisted task list."""
    return [PlannedTask.from_dict(task_payload) for task_payload in payload.get("tasks", [])]

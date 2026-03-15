"""Task planning for the Phase2 to Phase5 workflows.

Phase5 extends the earlier planning layer with:
- rule-based multi-task tree generation,
- local heuristic priority and retry tuning,
- sequential plus parallel task grouping,
- local templates for placeholder AI-style tasks without external APIs.

Future phases can replace these deterministic templates with adaptive
replanning, approval-aware routing, and richer project-specific planners.
AI-Phase1 adds task-level AI flags and prompt-template placeholders.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .goal_framework import ProjectGoal, render_goal_ai_prompt, utc_now


AI_EXECUTOR_TYPES = {"placeholder_agent", "codex_placeholder", "gpt_placeholder"}


def is_ai_executor_type(executor_type: str) -> bool:
    """Return True when an executor type represents an AI-capable route."""

    return executor_type in AI_EXECUTOR_TYPES


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
    use_ai: bool = False
    ai_prompt_template: str | None = None
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
            use_ai=bool(payload.get("use_ai", is_ai_executor_type(payload["executor_type"]))),
            title=payload["title"],
            description=payload["description"],
            prompt_template=payload["prompt_template"],
            ai_prompt_template=payload.get("ai_prompt_template"),
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
    rendered_prompt = (task.ai_prompt_template or task.prompt_template).format(
        goal=goal.normalized_goal,
        target_dir=goal.target_project_dir,
        phase=goal.phase,
        priority=goal.priority,
        use_ai=goal.use_ai,
        ai_provider=goal.ai_provider,
        goal_version=goal.goal_version,
        parent_goal_id=goal.parent_goal_id or "none",
        complexity_level=goal.complexity_level,
        dependency_count=len(task.depends_on),
        memory_goal_count=memory_status.get("goal_count", 0),
        memory_vector_count=memory_status.get("vector_count", 0),
        memory_match_count=memory_status.get("retrieved_goal_count", len(memory_status.get("matches", []))),
        task_profile_count=memory_status.get("task_profile_count", 0),
    )
    if task.use_ai:
        return (
            f"{render_goal_ai_prompt(goal)}\n"
            f"ai_task={task.task_id}; ai_enabled={goal.use_ai}; ai_provider={goal.ai_provider}\n"
            f"{rendered_prompt}"
        )
    return rendered_prompt


def generate_task_plan(
    goal: ProjectGoal,
    phase: str | None = None,
    task_history: dict[str, Any] | None = None,
) -> list[PlannedTask]:
    """Generate a deterministic task plan for the requested workflow phase."""
    resolved_phase = phase or goal.phase
    if resolved_phase == "Phase5":
        tasks = _generate_phase5_task_plan(goal)
    elif resolved_phase == "Phase4":
        tasks = _generate_phase4_task_plan(goal)
    elif resolved_phase == "Phase3":
        tasks = _generate_phase3_task_plan(goal)
    else:
        tasks = _generate_phase2_task_plan(goal)
    tasks = _apply_historical_task_heuristics(tasks, task_history or {}, phase=resolved_phase)
    return _apply_ai_task_defaults(tasks)


def _apply_ai_task_defaults(tasks: list[PlannedTask]) -> list[PlannedTask]:
    """Ensure AI-capable tasks carry explicit AI metadata."""

    adapted_tasks: list[PlannedTask] = []
    for task in tasks:
        cloned_payload = task.to_dict()
        cloned_payload["use_ai"] = bool(cloned_payload.get("use_ai", False) or is_ai_executor_type(task.executor_type))
        if cloned_payload["use_ai"] and not cloned_payload.get("ai_prompt_template"):
            cloned_payload["ai_prompt_template"] = (
                f"{cloned_payload['prompt_template']} "
                "Use ai_provider={ai_provider} in safe placeholder mode and do not mutate project files."
            )
        adapted_tasks.append(PlannedTask.from_dict(cloned_payload))
    return adapted_tasks


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


def _generate_phase5_task_plan(goal: ProjectGoal) -> list[PlannedTask]:
    target_dir = goal.target_project_dir
    include_artifact_summary = goal.complexity_level != "simple"
    parallel_scan_tasks = [
        PlannedTask(
            task_id="generate_module_list",
            order=3,
            module_name="task_planning",
            executor_type="local_python",
            title="Generate module list",
            description="Collect Python source files and derive module-style names for the local project scan.",
            prompt_template=(
                "Inventory Python files under '{target_dir}' for Phase5 goal '{goal}'. "
                "Use historical task profiles={task_profile_count} and memory matches={memory_match_count}."
            ),
            expected_output="A JSON artifact listing Python files and module names.",
            verification_hint="The artifact must contain a file list and module count.",
            priority=118,
            execution_mode="parallel",
            parallel_group="project_scan",
            depends_on=["inspect_project_directory"],
            callback_channel="artifact_ready",
            metadata={
                "operation": "list_python_modules",
                "artifact_name": "module_inventory.json",
                "target_dir": target_dir,
                "phase5_category": "scan",
            },
        ),
        PlannedTask(
            task_id="count_python_files",
            order=4,
            module_name="executor",
            executor_type="local_python",
            title="Count Python files",
            description="Count Python files and estimate project line volume for local autonomy metrics.",
            prompt_template=(
                "Count Python files under '{target_dir}' for Phase5 goal '{goal}'. "
                "Prepare safe metrics for scheduling and optimization."
            ),
            expected_output="A JSON artifact containing file count, line count, and representative paths.",
            verification_hint="The metrics artifact must include a non-negative Python file count.",
            priority=116,
            execution_mode="parallel",
            parallel_group="project_scan",
            depends_on=["inspect_project_directory"],
            callback_channel="artifact_ready",
            metadata={
                "operation": "count_python_files",
                "artifact_name": "python_file_metrics.json",
                "target_dir": target_dir,
                "phase5_category": "scan",
            },
        ),
    ]
    if include_artifact_summary:
        parallel_scan_tasks.append(
            PlannedTask(
                task_id="summarize_project_artifacts",
                order=5,
                module_name="result_analysis",
                executor_type="local_python",
                title="Summarize project artifacts",
                description="Build a safe summary of file suffixes and top directories for the Phase5 task tree.",
                prompt_template=(
                    "Summarize tracked project artifacts under '{target_dir}' for goal '{goal}'. "
                    "Return file suffix counts and top directories for dashboard visualization."
                ),
                expected_output="A JSON artifact containing tracked file counts, suffix breakdown, and top directories.",
                verification_hint="The artifact must contain tracked file counts and a suffix histogram.",
                priority=114,
                execution_mode="parallel",
                parallel_group="project_scan",
                depends_on=["inspect_project_directory"],
                callback_channel="artifact_ready",
                metadata={
                    "operation": "summarize_project_artifacts",
                    "artifact_name": "project_artifact_summary.json",
                    "target_dir": target_dir,
                    "phase5_category": "scan",
                },
            )
        )

    summary_dependencies = [
        "retrieve_memory_context",
        "generate_module_list",
        "count_python_files",
        "execute_sample_python_task",
    ]
    if include_artifact_summary:
        summary_dependencies.append("summarize_project_artifacts")

    tasks = [
        PlannedTask(
            task_id="inspect_project_directory",
            order=1,
            module_name="goal_framework",
            executor_type="local_python",
            title="Inspect target directory",
            description="Capture a safe top-level snapshot before Phase5 planning begins.",
            prompt_template=(
                "Inspect '{target_dir}' for Phase5 goal '{goal}'. Goal version={goal_version}, "
                "complexity={complexity_level}. Keep the workflow read-only."
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
                "phase5_category": "scan",
            },
        ),
        PlannedTask(
            task_id="retrieve_memory_context",
            order=2,
            module_name="goal_framework",
            executor_type="local_python",
            title="Retrieve memory context",
            description="Load historical goal memory and retrieve matching goals for the current Phase5 workflow.",
            prompt_template=(
                "Retrieve local memory context for goal '{goal}' with version={goal_version}. "
                "Stored goals={memory_goal_count}, vectors={memory_vector_count}, matches={memory_match_count}."
            ),
            expected_output="A JSON artifact describing stored goals, vector placeholders, and retrieved goal matches.",
            verification_hint="The artifact must contain goal and vector counts, plus a retrieved match count.",
            priority=124,
            execution_mode="sequential",
            callback_channel="memory_ready",
            metadata={
                "operation": "retrieve_memory_context",
                "artifact_name": "memory_context.json",
                "target_dir": target_dir,
                "phase5_category": "memory",
            },
        ),
    ]
    tasks.extend(parallel_scan_tasks)
    tasks.append(
        PlannedTask(
            task_id="execute_sample_python_task",
            order=6 if include_artifact_summary else 5,
            module_name="executor",
            executor_type="local_python",
            title="Execute sample Python task",
            description="Run a safe local Python function to generate baseline execution statistics for Phase5.",
            prompt_template=(
                "Execute a safe local Python task for goal '{goal}' on '{target_dir}'. "
                "Return deterministic metrics that can be reused for self-optimization."
            ),
            expected_output="A JSON artifact containing deterministic sample execution metrics.",
            verification_hint="The result must include sample counts, totals, and a generated preview.",
            priority=112,
            execution_mode="sequential",
            depends_on=["inspect_project_directory"],
            callback_channel="sample_ready",
            metadata={
                "operation": "execute_sample_python_task",
                "artifact_name": "sample_python_execution.json",
                "target_dir": target_dir,
                "phase5_category": "execution",
            },
        )
    )
    tasks.append(
        PlannedTask(
            task_id="compile_phase5_task_tree",
            order=7 if include_artifact_summary else 6,
            module_name="task_planning",
            executor_type="placeholder_agent",
            title="Compile Phase5 task tree",
            description="Simulate an AI-style planning pass using only local templates, memory, and prior artifacts.",
            prompt_template=(
                "Compile a Phase5 task-tree summary for goal '{goal}' on '{target_dir}'. "
                "Memory matches={memory_match_count}, task profiles={task_profile_count}, complexity={complexity_level}."
            ),
            expected_output="A markdown summary plus structured subtask recommendations derived from local artifacts.",
            verification_hint="The result must include a summary and at least one suggested subtask.",
            priority=98,
            execution_mode="sequential",
            depends_on=summary_dependencies,
            callback_channel="task_tree_ready",
            metadata={
                "operation": "compile_phase5_task_tree",
                "artifact_name": "phase5_task_tree.md",
                "target_dir": target_dir,
                "phase5_category": "planning",
            },
        )
    )
    tasks.append(
        PlannedTask(
            task_id="propose_phase5_actions",
            order=8 if include_artifact_summary else 7,
            module_name="executor",
            executor_type="codex_placeholder",
            title="Propose Phase5 actions",
            description="Generate a safe local autonomy suggestion package without external AI APIs.",
            prompt_template=(
                "For Phase5 goal '{goal}' on '{target_dir}', build a local automation suggestion package. "
                "Goal version={goal_version}, matches={memory_match_count}, task profiles={task_profile_count}."
            ),
            expected_output="A structured suggestion package plus a Python preview derived from local artifacts.",
            verification_hint="The result must include a summary, suggested actions, and a generated code preview.",
            priority=90,
            execution_mode="sequential",
            depends_on=["compile_phase5_task_tree"],
            callback_channel="suggestion_ready",
            metadata={
                "operation": "phase5_local_automation_suggestion",
                "artifact_name": "phase5_local_automation_suggestion.json",
                "code_artifact_name": "phase5_local_automation_preview.py",
                "target_dir": target_dir,
                "phase5_category": "optimization",
            },
        )
    )
    tasks.append(
        PlannedTask(
            task_id="draft_self_optimization_review",
            order=9 if include_artifact_summary else 8,
            module_name="loop_control",
            executor_type="gpt_placeholder",
            title="Draft self-optimization review",
            description="Produce a local review of task outcomes, retry posture, and future scheduling improvements.",
            prompt_template=(
                "Create a Phase5 self-optimization review for goal '{goal}' on '{target_dir}'. "
                "Summarize local task outcomes, retries, and safe next-step improvements."
            ),
            expected_output="A markdown-style review with next actions, heuristic notes, and future enhancement hooks.",
            verification_hint="The review must contain summary text and recommended local optimization actions.",
            priority=84,
            execution_mode="sequential",
            depends_on=["propose_phase5_actions"],
            callback_channel="review_ready",
            metadata={
                "operation": "phase5_self_optimization_review",
                "artifact_name": "phase5_self_optimization_review.md",
                "target_dir": target_dir,
                "phase5_category": "optimization",
            },
        )
    )
    return tasks


def _apply_historical_task_heuristics(
    tasks: list[PlannedTask],
    task_history: dict[str, Any],
    *,
    phase: str,
) -> list[PlannedTask]:
    """Adjust task priority and retry counts using local historical outcomes."""
    profiles = dict(task_history.get("task_profiles", {}))
    adapted_tasks: list[PlannedTask] = []

    for task in tasks:
        profile = profiles.get(task.task_id, {})
        if not profile:
            adapted_tasks.append(task)
            continue

        success_rate = float(profile.get("success_rate", 1.0))
        retry_rate = float(profile.get("retry_rate", 0.0))
        failure_rate = float(profile.get("failure_rate", 0.0))
        priority_delta = 0
        retry_delta = 0
        heuristic_notes: list[str] = []

        if success_rate < 0.8:
            priority_delta += 10
            retry_delta += 1
            heuristic_notes.append("priority_boost_low_success_rate")
        elif success_rate > 0.97:
            priority_delta -= 2
            heuristic_notes.append("priority_relaxed_high_success_rate")

        if retry_rate > 0.15:
            priority_delta += 4
            retry_delta += 1
            heuristic_notes.append("retry_budget_boost_high_retry_rate")

        if failure_rate > 0.2:
            priority_delta += 6
            heuristic_notes.append("priority_boost_failure_rate")

        if not heuristic_notes:
            adapted_tasks.append(task)
            continue

        cloned_payload = task.to_dict()
        cloned_payload["priority"] = max(10, min(200, task.priority + priority_delta))
        cloned_payload["max_retries"] = max(1, min(4, task.max_retries + retry_delta))
        metadata = dict(task.metadata)
        metadata["historical_profile"] = {
            "success_rate": round(success_rate, 3),
            "retry_rate": round(retry_rate, 3),
            "failure_rate": round(failure_rate, 3),
            "runs": int(profile.get("runs", 0)),
            "phase_applied": phase,
        }
        metadata["historical_heuristic"] = heuristic_notes
        cloned_payload["metadata"] = metadata
        adapted_tasks.append(PlannedTask.from_dict(cloned_payload))

    return adapted_tasks


def build_plan_payload(goal: ProjectGoal, tasks: list[PlannedTask], phase: str | None = None) -> dict[str, Any]:
    """Serialize the current plan for persistence and CLI display."""
    resolved_phase = phase or goal.phase
    parallel_task_count = sum(1 for task in tasks if task.execution_mode == "parallel")
    ai_task_count = sum(1 for task in tasks if task.use_ai)

    executor_breakdown: dict[str, int] = {}
    ai_executor_breakdown: dict[str, int] = {}
    parallel_groups: dict[str, list[str]] = {}
    dependency_edges: list[dict[str, str]] = []
    heuristic_adjustments: list[dict[str, Any]] = []
    for task in tasks:
        executor_breakdown[task.executor_type] = executor_breakdown.get(task.executor_type, 0) + 1
        if task.use_ai:
            ai_executor_breakdown[task.executor_type] = ai_executor_breakdown.get(task.executor_type, 0) + 1
        if task.parallel_group:
            parallel_groups.setdefault(task.parallel_group, []).append(task.task_id)
        for dependency in task.depends_on:
            dependency_edges.append({"from": dependency, "to": task.task_id})
        if task.metadata.get("historical_heuristic"):
            heuristic_adjustments.append(
                {
                    "task_id": task.task_id,
                    "priority": task.priority,
                    "max_retries": task.max_retries,
                    "heuristics": task.metadata.get("historical_heuristic", []),
                    "historical_profile": task.metadata.get("historical_profile", {}),
                }
            )

    return {
        "generated_at": utc_now(),
        "phase": resolved_phase,
        "goal_id": goal.goal_id,
        "goal_version": goal.goal_version,
        "complexity_level": goal.complexity_level,
        "target_project_dir": goal.target_project_dir,
        "use_ai": goal.use_ai,
        "ai_provider": goal.ai_provider,
        "task_count": len(tasks),
        "ai_task_count": ai_task_count,
        "parallel_task_count": parallel_task_count,
        "sequential_task_count": len(tasks) - parallel_task_count,
        "retry_budget_total": sum(task.max_retries for task in tasks),
        "max_parallel_tasks": max(len(task_ids) for task_ids in parallel_groups.values()) if parallel_groups else 1,
        "executor_breakdown": executor_breakdown,
        "ai_executor_breakdown": ai_executor_breakdown,
        "parallel_groups": parallel_groups,
        "dependency_edges": dependency_edges,
        "heuristic_adjustments": heuristic_adjustments,
        "tasks": [task.to_dict() for task in tasks],
    }


def load_tasks(payload: dict[str, Any]) -> list[PlannedTask]:
    """Rebuild a persisted task list."""
    return [PlannedTask.from_dict(task_payload) for task_payload in payload.get("tasks", [])]

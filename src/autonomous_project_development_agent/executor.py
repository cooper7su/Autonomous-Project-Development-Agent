"""Execution interfaces for the Phase2 to Phase4 workflows.

Phase4 extends the earlier executor layer with:
- callback-aware batched execution,
- placeholder Codex/GPT routes for autonomous suggestions,
- safe local memory/context tasks,
- richer runtime statistics for reporting and visualization.

Phase5 can replace these placeholders with real model calls, stronger
isolation, approval-aware policies, and tool-specific execution sandboxes.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from .task_planning import PlannedTask


def utc_now() -> str:
    """Return an ISO 8601 timestamp in UTC."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass
class ExecutionContext:
    """Runtime context shared across task execution."""

    base_dir: str
    runtime_root: str
    target_project_dir: str
    goal_id: str
    goal_text: str
    phase: str
    iteration: int
    run_id: str
    state_dir: str
    logs_dir: str
    artifacts_dir: str
    goal_version: int = 1
    prior_results: list[dict[str, Any]] = field(default_factory=list)
    memory_state: dict[str, Any] = field(default_factory=dict)
    plan_summary: dict[str, Any] = field(default_factory=dict)
    max_parallel_tasks: int = 2

    def to_dict(self) -> dict[str, Any]:
        """Serialize the execution context for persistence or debugging."""
        return asdict(self)


@dataclass
class TaskResult:
    """Structured execution output for one task attempt."""

    task_id: str
    module_name: str
    title: str
    executor_type: str
    attempt: int
    success: bool
    returncode: int
    started_at: str
    finished_at: str
    duration_seconds: float
    output: dict[str, Any]
    output_text: str
    artifact_path: str | None = None
    error: str | None = None
    statistics: dict[str, Any] = field(default_factory=dict)
    visualization_data: dict[str, Any] = field(default_factory=dict)
    callback_events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the result into JSON-friendly data."""
        return asdict(self)


class BaseExecutor:
    """Base executor contract for prototype tasks."""

    executor_type = "base"

    def execute(self, task: PlannedTask, context: ExecutionContext, attempt: int = 1) -> TaskResult:
        """Execute a planned task and return a structured result."""
        raise NotImplementedError


class LocalPythonExecutor(BaseExecutor):
    """Run safe local Python tasks without external network or shell usage."""

    executor_type = "local_python"

    def execute(self, task: PlannedTask, context: ExecutionContext, attempt: int = 1) -> TaskResult:
        started_at = utc_now()
        started_clock = perf_counter()
        target_dir = Path(task.metadata.get("target_dir", context.target_project_dir)).resolve()
        artifact_name = task.metadata.get("artifact_name", f"{task.task_id}.json")
        artifact_path = Path(context.artifacts_dir) / artifact_name
        callback_events: list[dict[str, Any]] = []

        try:
            operation = task.metadata.get("operation")
            if operation == "inspect_directory":
                output, artifact_payload = self._inspect_directory(target_dir)
            elif operation == "list_python_modules":
                output, artifact_payload = self._list_python_modules(target_dir)
            elif operation == "count_python_files":
                output, artifact_payload = self._count_python_files(target_dir)
            elif operation == "retrieve_memory_context":
                output, artifact_payload = self._retrieve_memory_context(context)
            elif operation == "summarize_project_artifacts":
                output, artifact_payload = self._summarize_project_artifacts(target_dir)
            else:
                raise ValueError(f"Unsupported local operation: {operation}")

            artifact_path.write_text(
                json.dumps(artifact_payload, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )
            callback_events.append(
                {
                    "event": task.callback_channel or "artifact_ready",
                    "artifact_path": str(artifact_path),
                    "task_id": task.task_id,
                }
            )
            success = True
            returncode = 0
            error = None
        except Exception as exc:
            output = {
                "task_id": task.task_id,
                "message": "Local task execution failed.",
                "error": str(exc),
            }
            success = False
            returncode = 1
            error = str(exc)
            artifact_path = None

        duration_seconds = round(perf_counter() - started_clock, 4)
        statistics = {
            "duration_seconds": duration_seconds,
            "artifact_written": bool(artifact_path),
        }
        statistics.update(output.get("statistics", {}))
        visualization_data = {
            "task_id": task.task_id,
            "executor_type": self.executor_type,
            "duration_seconds": duration_seconds,
            "execution_mode": task.execution_mode,
            "parallel_group": task.parallel_group,
        }

        return TaskResult(
            task_id=task.task_id,
            module_name=task.module_name,
            title=task.title,
            executor_type=self.executor_type,
            attempt=attempt,
            success=success,
            returncode=returncode,
            started_at=started_at,
            finished_at=utc_now(),
            duration_seconds=duration_seconds,
            output=output,
            output_text=json.dumps(output, ensure_ascii=True),
            artifact_path=str(artifact_path) if artifact_path else None,
            error=error,
            statistics=statistics,
            visualization_data=visualization_data,
            callback_events=callback_events,
        )

    def _inspect_directory(self, target_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
        if not target_dir.exists() or not target_dir.is_dir():
            raise FileNotFoundError(f"Target project directory is not readable: {target_dir}")

        entries = sorted(child.name for child in target_dir.iterdir())
        payload = {
            "task_id": "inspect_project_directory",
            "target_project_dir": str(target_dir),
            "top_level_entries": entries,
            "top_level_entry_count": len(entries),
            "contains_src_dir": (target_dir / "src").exists(),
            "contains_docs_dir": (target_dir / "docs").exists(),
        }
        return payload, payload

    def _list_python_modules(self, target_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
        python_files = self._iter_python_files(target_dir)
        modules = [
            {
                "path": str(path.relative_to(target_dir)),
                "module_name": self._module_name(target_dir, path),
            }
            for path in python_files
        ]
        artifact_payload = {
            "task_id": "generate_module_list",
            "target_project_dir": str(target_dir),
            "python_file_count": len(python_files),
            "modules": modules,
            "module_count": len(modules),
            "statistics": {"module_count": len(modules)},
        }
        output = {
            "task_id": "generate_module_list",
            "target_project_dir": str(target_dir),
            "python_file_count": len(python_files),
            "module_count": len(modules),
            "modules_sample": modules[:20],
            "statistics": {"module_count": len(modules)},
        }
        return output, artifact_payload

    def _count_python_files(self, target_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
        python_files = self._iter_python_files(target_dir)
        line_count = sum(self._line_count(path) for path in python_files)
        relative_paths = [str(path.relative_to(target_dir)) for path in python_files]
        payload = {
            "task_id": "count_python_files",
            "target_project_dir": str(target_dir),
            "python_file_count": len(python_files),
            "total_python_lines": line_count,
            "sample_paths": relative_paths[:10],
            "statistics": {
                "python_file_count": len(python_files),
                "total_python_lines": line_count,
            },
        }
        return payload, payload

    def _retrieve_memory_context(self, context: ExecutionContext) -> tuple[dict[str, Any], dict[str, Any]]:
        matches = list(context.memory_state.get("matches", []))[:5]
        payload = {
            "task_id": "retrieve_memory_context",
            "goal_id": context.goal_id,
            "goal_version": context.goal_version,
            "goal_count": context.memory_state.get("goal_count", 0),
            "vector_count": context.memory_state.get("vector_count", 0),
            "retrieved_goal_count": len(matches),
            "matches": matches,
            "phase_breakdown": context.memory_state.get("phase_breakdown", {}),
            "memory_scope": context.memory_state.get("memory_scope", "local_placeholder"),
            "statistics": {
                "retrieved_goal_count": len(matches),
                "goal_count": context.memory_state.get("goal_count", 0),
            },
        }
        return payload, payload

    def _summarize_project_artifacts(self, target_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
        ignored_parts = self._ignored_parts()
        suffix_counts: dict[str, int] = {}
        top_directory_counts: dict[str, int] = {}
        tracked_files = 0

        for path in sorted(target_dir.rglob("*")):
            if not path.is_file():
                continue
            if any(part in ignored_parts for part in path.parts):
                continue

            tracked_files += 1
            suffix = path.suffix or "<no_suffix>"
            suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1
            relative = path.relative_to(target_dir)
            top_directory = relative.parts[0] if len(relative.parts) > 1 else "."
            top_directory_counts[top_directory] = top_directory_counts.get(top_directory, 0) + 1

        ordered_suffixes = dict(sorted(suffix_counts.items(), key=lambda item: (-item[1], item[0])))
        top_directories = [
            {"directory": name, "file_count": count}
            for name, count in sorted(
                top_directory_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[:10]
        ]
        payload = {
            "task_id": "summarize_project_artifacts",
            "target_project_dir": str(target_dir),
            "total_tracked_files": tracked_files,
            "suffix_counts": ordered_suffixes,
            "top_directories": top_directories,
            "statistics": {
                "total_tracked_files": tracked_files,
                "distinct_suffixes": len(ordered_suffixes),
            },
        }
        return payload, payload

    def _ignored_parts(self) -> set[str]:
        return {
            ".git",
            ".venv",
            "venv",
            "__pycache__",
            "phase1_runtime",
            "build",
            "dist",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
        }

    def _iter_python_files(self, target_dir: Path) -> list[Path]:
        ignored_parts = self._ignored_parts()
        python_files: list[Path] = []
        for path in sorted(target_dir.rglob("*.py")):
            if any(part in ignored_parts for part in path.parts):
                continue
            python_files.append(path)
        return python_files

    def _module_name(self, target_dir: Path, file_path: Path) -> str:
        relative = file_path.relative_to(target_dir)
        if relative.name == "__init__.py":
            return ".".join(relative.parent.parts) or "__init__"
        return ".".join(relative.with_suffix("").parts)

    def _line_count(self, file_path: Path) -> int:
        with file_path.open("r", encoding="utf-8") as handle:
            return sum(1 for _ in handle)


class PlaceholderAgentExecutor(BaseExecutor):
    """Simulate a future coding-agent call using only local task artifacts."""

    executor_type = "placeholder_agent"

    def execute(self, task: PlannedTask, context: ExecutionContext, attempt: int = 1) -> TaskResult:
        started_at = utc_now()
        started_clock = perf_counter()
        artifact_name = task.metadata.get("artifact_name", "placeholder_output.md")
        artifact_path = Path(context.artifacts_dir) / artifact_name
        callback_events: list[dict[str, Any]] = []

        try:
            output = self._draft_analysis(task, context)
            artifact_path.write_text(output["summary_markdown"] + "\n", encoding="utf-8")
            callback_events.append(
                {
                    "event": task.callback_channel or "analysis_ready",
                    "artifact_path": str(artifact_path),
                    "task_id": task.task_id,
                }
            )
            success = True
            returncode = 0
            error = None
        except Exception as exc:
            output = {
                "task_id": task.task_id,
                "message": "Placeholder agent execution failed.",
                "error": str(exc),
            }
            success = False
            returncode = 1
            error = str(exc)
            artifact_path = None

        duration_seconds = round(perf_counter() - started_clock, 4)
        return TaskResult(
            task_id=task.task_id,
            module_name=task.module_name,
            title=task.title,
            executor_type=self.executor_type,
            attempt=attempt,
            success=success,
            returncode=returncode,
            started_at=started_at,
            finished_at=utc_now(),
            duration_seconds=duration_seconds,
            output=output,
            output_text=output.get("summary_markdown", json.dumps(output, ensure_ascii=True)),
            artifact_path=str(artifact_path) if artifact_path else None,
            error=error,
            statistics={"duration_seconds": duration_seconds, "artifact_written": bool(artifact_path)},
            visualization_data={
                "task_id": task.task_id,
                "executor_type": self.executor_type,
                "duration_seconds": duration_seconds,
            },
            callback_events=callback_events,
        )

    def _draft_analysis(self, task: PlannedTask, context: ExecutionContext) -> dict[str, Any]:
        results_by_task = {result["task_id"]: result for result in context.prior_results}
        directory_snapshot = results_by_task.get("inspect_project_directory", {}).get("output", {})
        module_inventory = results_by_task.get("generate_module_list", {}).get("output", {})
        python_metrics = results_by_task.get("count_python_files", {}).get("output", {})

        summary_lines = [
            "# Preliminary Project Analysis",
            "",
            f"- Goal: {context.goal_text}",
            f"- Target directory: {context.target_project_dir}",
            f"- Top-level entries: {directory_snapshot.get('top_level_entry_count', 0)}",
            f"- Python files discovered: {python_metrics.get('python_file_count', 0)}",
            f"- Total Python lines: {python_metrics.get('total_python_lines', 0)}",
            f"- Module inventory size: {module_inventory.get('module_count', 0)}",
            "",
            "## Observations",
            "- The workflow completed a safe local inspection only.",
            "- The current analysis is deterministic and does not call external agent services.",
            "- The executor boundary remains ready for future Codex/OpenAI or MATLAB integrations.",
            "",
            "## Suggested Next Step",
            "- Extend task planning with richer dependency reasoning in later phases.",
        ]

        return {
            "task_id": task.task_id,
            "summary_markdown": "\n".join(summary_lines),
            "highlights": {
                "top_level_entries": directory_snapshot.get("top_level_entry_count", 0),
                "module_count": module_inventory.get("module_count", 0),
                "python_file_count": python_metrics.get("python_file_count", 0),
            },
        }


class CodexExecutor(BaseExecutor):
    """Generate a safe implementation suggestion as a placeholder for Codex/GPT."""

    executor_type = "codex_placeholder"

    def execute(self, task: PlannedTask, context: ExecutionContext, attempt: int = 1) -> TaskResult:
        started_at = utc_now()
        started_clock = perf_counter()
        artifact_name = task.metadata.get("artifact_name", "codex_placeholder_output.json")
        artifact_path = Path(context.artifacts_dir) / artifact_name
        callback_events: list[dict[str, Any]] = []

        try:
            operation = task.metadata.get("operation")
            if operation == "phase4_change_suggestion":
                output = self._build_phase4_suggestion(task, context)
            else:
                output = self._build_phase3_stub(task, context)

            artifact_path.write_text(json.dumps(output, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

            code_artifact_name = task.metadata.get("code_artifact_name", "codex_placeholder_preview.py")
            code_artifact_path = Path(context.artifacts_dir) / code_artifact_name
            code_artifact_path.write_text(output["generated_code_preview"] + "\n", encoding="utf-8")

            output["generated_code_artifact"] = str(code_artifact_path)
            callback_events.append(
                {
                    "event": task.callback_channel or "suggestion_ready",
                    "artifact_path": str(artifact_path),
                    "code_artifact_path": str(code_artifact_path),
                    "task_id": task.task_id,
                }
            )
            success = True
            returncode = 0
            error = None
        except Exception as exc:
            output = {
                "task_id": task.task_id,
                "message": "Codex placeholder execution failed.",
                "error": str(exc),
            }
            success = False
            returncode = 1
            error = str(exc)
            artifact_path = None

        duration_seconds = round(perf_counter() - started_clock, 4)
        return TaskResult(
            task_id=task.task_id,
            module_name=task.module_name,
            title=task.title,
            executor_type=self.executor_type,
            attempt=attempt,
            success=success,
            returncode=returncode,
            started_at=started_at,
            finished_at=utc_now(),
            duration_seconds=duration_seconds,
            output=output,
            output_text=output.get("summary_markdown", json.dumps(output, ensure_ascii=True)),
            artifact_path=str(artifact_path) if artifact_path else None,
            error=error,
            statistics={
                "duration_seconds": duration_seconds,
                "artifact_written": bool(artifact_path),
                "suggested_action_count": len(output.get("suggested_actions", [])),
            },
            visualization_data={
                "task_id": task.task_id,
                "executor_type": self.executor_type,
                "duration_seconds": duration_seconds,
                "suggested_action_count": len(output.get("suggested_actions", [])),
            },
            callback_events=callback_events,
        )

    def _build_phase3_stub(self, task: PlannedTask, context: ExecutionContext) -> dict[str, Any]:
        results_by_task = {result["task_id"]: result for result in context.prior_results}
        module_inventory = results_by_task.get("generate_module_list", {}).get("output", {})
        python_metrics = results_by_task.get("count_python_files", {}).get("output", {})
        memory_goal_count = context.memory_state.get("goal_count", 0)

        class_name = "Phase3SuggestedWorkflow"
        code_preview = "\n".join(
            [
                '"""Safe placeholder generated by the Phase3 Codex executor."""',
                "",
                f"class {class_name}:",
                '    """Preview of a future autonomous workflow helper."""',
                "",
                "    def summarize(self) -> dict[str, int]:",
                "        return {",
                f'            "module_count": {module_inventory.get("module_count", 0)},',
                f'            "python_file_count": {python_metrics.get("python_file_count", 0)},',
                "        }",
            ]
        )

        summary_lines = [
            "# Autonomous Stub Suggestion",
            "",
            f"- Goal: {context.goal_text}",
            f"- Target directory: {context.target_project_dir}",
            f"- Memory goals available: {memory_goal_count}",
            f"- Module inventory size: {module_inventory.get('module_count', 0)}",
            f"- Python file count: {python_metrics.get('python_file_count', 0)}",
            "",
            "## Proposed Safe Next Step",
            "- Start by encapsulating project scan summaries behind a reusable helper class.",
            "- Keep external model execution disabled until policy and approval controls are added.",
        ]

        return {
            "task_id": task.task_id,
            "summary_markdown": "\n".join(summary_lines),
            "generated_code_preview": code_preview,
            "suggested_files": ["phase3_autonomous_stub.py"],
            "memory_goal_count": memory_goal_count,
            "suggested_actions": [
                "Encapsulate project scan summaries in a helper class.",
                "Keep external model execution disabled in prototype mode.",
            ],
        }

    def _build_phase4_suggestion(self, task: PlannedTask, context: ExecutionContext) -> dict[str, Any]:
        results_by_task = {result["task_id"]: result for result in context.prior_results}
        memory_context = results_by_task.get("retrieve_memory_context", {}).get("output", {})
        module_inventory = results_by_task.get("generate_module_list", {}).get("output", {})
        python_metrics = results_by_task.get("count_python_files", {}).get("output", {})
        artifact_summary = results_by_task.get("summarize_project_artifacts", {}).get("output", {})

        class_name = "Phase4TaskBundle"
        code_preview = "\n".join(
            [
                '"""Safe placeholder generated by the Phase4 Codex executor."""',
                "",
                f"class {class_name}:",
                '    """Preview of a future memory-aware autonomous helper."""',
                "",
                "    def build_summary(self) -> dict[str, object]:",
                "        return {",
                f'            "goal_version": {context.goal_version},',
                f'            "module_count": {module_inventory.get("module_count", 0)},',
                f'            "python_file_count": {python_metrics.get("python_file_count", 0)},',
                f'            "retrieved_goal_count": {memory_context.get("retrieved_goal_count", 0)},',
                f'            "tracked_file_count": {artifact_summary.get("total_tracked_files", 0)},',
                "        }",
            ]
        )

        suggested_actions = [
            {
                "action_id": "encapsulate_scan_outputs",
                "title": "Encapsulate scan outputs",
                "safe": True,
                "reason": "Unify module, file-count, and artifact summaries behind one reusable data object.",
            },
            {
                "action_id": "persist_iteration_statistics",
                "title": "Persist iteration statistics",
                "safe": True,
                "reason": "Keep loop-state and dashboard reporting aligned as the prototype grows.",
            },
            {
                "action_id": "prepare_phase5_tool_policies",
                "title": "Prepare Phase5 tool policies",
                "safe": True,
                "reason": "Future real model execution needs approval and mutation guardrails before activation.",
            },
        ]

        summary_lines = [
            "# Phase4 Autonomous Suggestion Package",
            "",
            f"- Goal: {context.goal_text}",
            f"- Goal version: {context.goal_version}",
            f"- Target directory: {context.target_project_dir}",
            f"- Retrieved memory matches: {memory_context.get('retrieved_goal_count', 0)}",
            f"- Module inventory size: {module_inventory.get('module_count', 0)}",
            f"- Python file count: {python_metrics.get('python_file_count', 0)}",
            f"- Tracked file count: {artifact_summary.get('total_tracked_files', 0)}",
            "",
            "## Safe Suggested Actions",
            "- Encapsulate scan outputs into a reusable summary object.",
            "- Persist execution statistics for dashboard and loop control reuse.",
            "- Keep code generation placeholder-only until Phase5 approval policies exist.",
        ]

        return {
            "task_id": task.task_id,
            "summary_markdown": "\n".join(summary_lines),
            "generated_code_preview": code_preview,
            "suggested_files": ["phase4_autonomous_bundle.py"],
            "suggested_actions": suggested_actions,
            "retrieved_goal_count": memory_context.get("retrieved_goal_count", 0),
            "module_count": module_inventory.get("module_count", 0),
            "python_file_count": python_metrics.get("python_file_count", 0),
            "tracked_file_count": artifact_summary.get("total_tracked_files", 0),
        }


class GPTExecutor(BaseExecutor):
    """Simulate a review-oriented GPT execution path for later autonomous phases."""

    executor_type = "gpt_placeholder"

    def execute(self, task: PlannedTask, context: ExecutionContext, attempt: int = 1) -> TaskResult:
        started_at = utc_now()
        started_clock = perf_counter()
        artifact_name = task.metadata.get("artifact_name", "gpt_placeholder_output.md")
        artifact_path = Path(context.artifacts_dir) / artifact_name
        callback_events: list[dict[str, Any]] = []

        try:
            output = self._build_iteration_review(task, context)
            if artifact_path.suffix.lower() == ".md":
                artifact_path.write_text(output["summary_markdown"] + "\n", encoding="utf-8")
            else:
                artifact_path.write_text(json.dumps(output, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
            callback_events.append(
                {
                    "event": task.callback_channel or "review_ready",
                    "artifact_path": str(artifact_path),
                    "task_id": task.task_id,
                }
            )
            success = True
            returncode = 0
            error = None
        except Exception as exc:
            output = {
                "task_id": task.task_id,
                "message": "GPT placeholder execution failed.",
                "error": str(exc),
            }
            success = False
            returncode = 1
            error = str(exc)
            artifact_path = None

        duration_seconds = round(perf_counter() - started_clock, 4)
        return TaskResult(
            task_id=task.task_id,
            module_name=task.module_name,
            title=task.title,
            executor_type=self.executor_type,
            attempt=attempt,
            success=success,
            returncode=returncode,
            started_at=started_at,
            finished_at=utc_now(),
            duration_seconds=duration_seconds,
            output=output,
            output_text=output.get("summary_markdown", json.dumps(output, ensure_ascii=True)),
            artifact_path=str(artifact_path) if artifact_path else None,
            error=error,
            statistics={
                "duration_seconds": duration_seconds,
                "artifact_written": bool(artifact_path),
                "recommended_next_action_count": len(output.get("recommended_next_actions", [])),
            },
            visualization_data={
                "task_id": task.task_id,
                "executor_type": self.executor_type,
                "duration_seconds": duration_seconds,
                "recommended_next_action_count": len(output.get("recommended_next_actions", [])),
            },
            callback_events=callback_events,
        )

    def _build_iteration_review(self, task: PlannedTask, context: ExecutionContext) -> dict[str, Any]:
        results_by_task = {result["task_id"]: result for result in context.prior_results}
        suggestion = results_by_task.get("propose_phase4_actions", {}).get("output", {})
        memory_context = results_by_task.get("retrieve_memory_context", {}).get("output", {})

        recommended_next_actions = [
            "Keep the current run read-only and archive its artifacts for later comparison.",
            "Promote reusable scan helpers before enabling real code mutation.",
            "Add approval-aware executor routing in Phase5 before turning on live model calls.",
        ]
        summary_lines = [
            "# Phase4 Iteration Review",
            "",
            f"- Goal: {context.goal_text}",
            f"- Goal version: {context.goal_version}",
            f"- Target directory: {context.target_project_dir}",
            f"- Retrieved memory matches: {memory_context.get('retrieved_goal_count', 0)}",
            f"- Suggested action count: {len(suggestion.get('suggested_actions', []))}",
            "",
            "## Review Summary",
            "- The prototype completed a safe autonomous loop using local inspection and placeholder agents only.",
            "- Parallel scan tasks produced reusable metrics for later autonomous planning.",
            "- The next phase should focus on approval policies, memory ranking, and controlled mutation boundaries.",
            "",
            "## Recommended Next Actions",
        ]
        summary_lines.extend(f"- {item}" for item in recommended_next_actions)
        summary_lines.extend(
            [
                "",
                "## Phase5 Handoff",
                "- Replace placeholder model execution with approval-aware live integrations.",
                "- Add stronger memory retrieval and task replanning logic.",
            ]
        )

        return {
            "task_id": task.task_id,
            "summary_markdown": "\n".join(summary_lines),
            "recommended_next_actions": recommended_next_actions,
            "risk_notes": [
                "Real code mutation remains disabled.",
                "Memory similarity is placeholder-only and not vector-search based.",
            ],
        }


def build_executor(executor_type: str) -> BaseExecutor:
    """Return the executor implementation for a planned task."""
    if executor_type == "local_python":
        return LocalPythonExecutor()
    if executor_type == "placeholder_agent":
        return PlaceholderAgentExecutor()
    if executor_type == "codex_placeholder":
        return CodexExecutor()
    if executor_type == "gpt_placeholder":
        return GPTExecutor()
    raise ValueError(f"Unsupported executor type: {executor_type}")


def execute_task_batch(
    tasks: list[PlannedTask],
    context: ExecutionContext,
    attempt_map: dict[str, int] | None = None,
    result_callback: Callable[[TaskResult], None] | None = None,
) -> list[TaskResult]:
    """Execute a task batch, parallelizing only when the plan asks for it."""
    attempt_map = attempt_map or {}
    if not tasks:
        return []

    ordered_tasks = sorted(tasks, key=lambda task: task.order)
    if len(ordered_tasks) == 1 or all(task.execution_mode != "parallel" for task in ordered_tasks):
        results: list[TaskResult] = []
        for task in ordered_tasks:
            result = build_executor(task.executor_type).execute(
                task,
                context,
                attempt=attempt_map.get(task.task_id, 1),
            )
            if result_callback is not None:
                result_callback(result)
            results.append(result)
        return results

    results: dict[str, TaskResult] = {}
    with ThreadPoolExecutor(max_workers=min(context.max_parallel_tasks, len(ordered_tasks))) as pool:
        future_map = {
            pool.submit(
                build_executor(task.executor_type).execute,
                task,
                context,
                attempt_map.get(task.task_id, 1),
            ): task
            for task in ordered_tasks
        }
        for future in as_completed(future_map):
            task = future_map[future]
            result = future.result()
            results[task.task_id] = result
            if result_callback is not None:
                result_callback(result)

    return [results[task.task_id] for task in ordered_tasks]

#!/usr/bin/env python3
"""Generate a Phase1 scaffold for the AI branch of the project.

This script creates a clean, pip-installable Python project that mirrors the
Phase1 foundation of the Autonomous Project Development Agent while adding
safe AI integration placeholders.

The generated scaffold is intentionally conservative:
- It does not call external AI APIs.
- It keeps a LocalPythonExecutor for immediate local execution.
- It adds an AIExecutor that returns deterministic, safe template output.
- It includes CLI and Streamlit placeholders for future expansion.

Phase2 and later can extend the generated files rather than replacing them.
"""

from __future__ import annotations

import argparse
import shutil
import textwrap
from pathlib import Path


PROJECT_NAME = "Autonomous Project Development Agent"
DEFAULT_TARGET_NAME = "Autonomous-Project-Development-Agent-AI"


def dedent(value: str) -> str:
    """Normalize generated file content and keep a trailing newline."""

    return textwrap.dedent(value).strip() + "\n"


def write_file(path: Path, content: str) -> None:
    """Write a text file, creating parent directories when needed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_clean_target(target_dir: Path, overwrite: bool) -> None:
    """Validate or prepare the target directory before generation."""

    if target_dir.exists() and any(target_dir.iterdir()):
        if not overwrite:
            raise SystemExit(
                f"Target directory '{target_dir}' already exists and is not empty. "
                "Use --overwrite to replace it or choose a different --target-dir."
            )
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)


def build_readme() -> str:
    """Return README.md content for the generated scaffold."""

    return dedent(
        f"""
        # {PROJECT_NAME} - AI Branch Phase1

        This repository contains a Phase1 scaffold for an AI-enabled branch of the
        Autonomous Project Development Agent. The scaffold is Python-centric and
        immediately runnable, while keeping all AI behavior in safe local placeholders.

        ## Phase1 Objectives

        - Define the project structure for future autonomous development workflows.
        - Provide package modules for goal modeling, task planning, execution,
          result analysis, and loop control.
        - Add an `AIExecutor` placeholder that can be enabled from the CLI without
          calling any external API.
        - Preserve local execution through `LocalPythonExecutor`.
        - Expose a simple CLI and Streamlit placeholder for Phase1 validation.

        ## Project Structure

        ```text
        .
        |- docs/
        |- src/autonomous_project_development_agent/
        |  |- __init__.py
        |  |- __main__.py
        |  |- main.py
        |  |- goal_framework.py
        |  |- task_planning.py
        |  |- executor.py
        |  |- result_analysis.py
        |  |- loop_control.py
        |- tests/
        |- requirements.txt
        |- pyproject.toml
        ```

        ## Installation

        Option 1: editable install

        ```bash
        python3 -m venv venv
        source venv/bin/activate
        pip install -e .
        ```

        Option 2: requirements install

        ```bash
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        ```

        ## Phase1 CLI Usage

        Show scaffold status:

        ```bash
        python -m autonomous_project_development_agent --status
        ```

        Initialize runtime state:

        ```bash
        python -m autonomous_project_development_agent --init
        ```

        Run Phase1 locally:

        ```bash
        python -m autonomous_project_development_agent --run-phase1
        ```

        Run Phase1 with AI placeholder enabled:

        ```bash
        python -m autonomous_project_development_agent --run-phase1 --enable-ai
        ```

        Provide a custom goal:

        ```bash
        python -m autonomous_project_development_agent --goal "Inspect a local project and draft an AI placeholder summary." --run-phase1 --enable-ai
        ```

        ## Streamlit Placeholder

        ```bash
        streamlit run src/autonomous_project_development_agent/main.py -- --visualize
        ```

        The dashboard only visualizes the Phase1 state. Real AI calls, multi-agent
        execution, long-term vector memory, and complex orchestration are intentionally
        deferred to later phases.

        ## Future Extension Notes

        - `AIExecutor` is the designated boundary for future OpenAI or other AI API integration.
        - Prompt rendering helpers are already separated in `goal_framework.py` and `task_planning.py`.
        - Runtime state is stored under `phase1_runtime/` to make future phases composable.
        """
    )


def build_project_overview() -> str:
    """Return docs/project_overview.md content."""

    return dedent(
        """
        # Project Overview

        Autonomous Project Development Agent is a Python-based prototype for an
        autonomous software workflow. The system is designed to transform a user
        goal into a structured task tree, run safe local actions, analyze outputs,
        and expose the current state through CLI and Streamlit interfaces.

        ## Phase1 Scope

        Phase1 establishes the engineering baseline:

        - Package layout and installation metadata
        - Goal and task data models
        - Safe local execution
        - AI execution placeholders
        - Runtime status, logs, and reports
        - Streamlit visualization placeholder

        ## AI Branch Intent

        This branch introduces AI-facing integration points without depending on
        external APIs. It provides:

        - `use_ai` flags on goals and tasks
        - Prompt template placeholders
        - `AIExecutor` for safe simulated AI output
        - Visualization of AI-enabled execution state

        ## Future Direction

        Later phases can integrate:

        - Real API-backed code generation
        - Memory retrieval and ranking
        - Multi-task scheduling
        - Self-checking and retry policies
        - MATLAB or other toolchain adapters
        """
    )


def build_development_plan() -> str:
    """Return docs/development_plan.md content."""

    return dedent(
        """
        # Development Plan

        ## Phase1 Tasks

        | Task | Module Boundary | Purpose |
        | --- | --- | --- |
        | Goal normalization | `goal_framework.py` | Build a structured `ProjectGoal` with `use_ai` support |
        | Task generation | `task_planning.py` | Produce a small safe Phase1 task tree |
        | Safe execution | `executor.py` | Execute local tasks and AI placeholder tasks |
        | Result checking | `result_analysis.py` | Convert raw task outputs into simple analysis reports |
        | Loop and status tracking | `loop_control.py` | Maintain progress, counters, and final status |
        | CLI and Streamlit | `main.py` | Run Phase1 and visualize current runtime state |

        ## Phase1 Deliverables

        - Installable Python package
        - Placeholder runtime under `phase1_runtime/`
        - CLI commands: `--init`, `--status`, `--run-phase1`, `--enable-ai`
        - Streamlit placeholder showing goal, tasks, memory, and AI execution state

        ## Phase2 High-Level Plan

        - Expand planning into a richer task tree
        - Introduce structured prompt strategies
        - Add stronger result scoring and retry logic

        ## Phase3 High-Level Plan

        - Add long-term memory retrieval placeholders
        - Support mixed sequential and parallel tasks
        - Improve local autonomous orchestration

        ## Phase4 High-Level Plan

        - Add history browsing, better visualization, and richer loop control
        - Prepare external tool adapters while preserving safe local defaults
        """
    )


def build_gitignore() -> str:
    """Return .gitignore content for the generated project."""

    return dedent(
        """
        __pycache__/
        *.py[cod]
        *.egg-info/
        .pytest_cache/
        .mypy_cache/
        .venv/
        venv/
        .DS_Store
        phase1_runtime/
        build/
        dist/
        """
    )


def build_requirements() -> str:
    """Return requirements.txt content."""

    return dedent(
        """
        openai
        pandas
        numpy
        matplotlib
        faiss-cpu
        streamlit
        """
    )


def build_pyproject() -> str:
    """Return pyproject.toml content."""

    return dedent(
        """
        [build-system]
        requires = ["setuptools>=68", "wheel"]
        build-backend = "setuptools.build_meta"

        [project]
        name = "autonomous-project-development-agent"
        version = "0.1.0"
        description = "Phase1 AI branch scaffold for an autonomous project development workflow."
        readme = "README.md"
        requires-python = ">=3.10"
        license = { text = "MIT" }
        authors = [
          { name = "Codex Generated Scaffold" }
        ]
        dependencies = [
          "openai",
          "pandas",
          "numpy",
          "matplotlib",
          "faiss-cpu",
          "streamlit",
        ]

        [project.scripts]
        apda-phase1 = "autonomous_project_development_agent.main:cli_main"

        [tool.setuptools]
        package-dir = { "" = "src" }

        [tool.setuptools.packages.find]
        where = ["src"]
        """
    )


def build_init_py() -> str:
    """Return package __init__.py content."""

    return dedent(
        '''
        """Autonomous Project Development Agent Phase1 AI scaffold."""

        from __future__ import annotations

        APP_NAME = "Autonomous Project Development Agent"
        PACKAGE_NAME = "autonomous_project_development_agent"
        PHASE_LABEL = "Phase1 AI"
        RUNTIME_DIRNAME = "phase1_runtime"
        MODULE_MAP = {
            "goal_framework": "Goal definition and AI prompt boundary",
            "task_planning": "Task generation with local and AI placeholder modes",
            "executor": "Local and AI placeholder execution adapters",
            "result_analysis": "Task result checking and reporting",
            "loop_control": "Phase1 loop state and status tracking",
            "main": "CLI and Streamlit placeholder entry point",
        }

        __all__ = [
            "APP_NAME",
            "PACKAGE_NAME",
            "PHASE_LABEL",
            "RUNTIME_DIRNAME",
            "MODULE_MAP",
        ]

        __version__ = "0.1.0"
        '''
    )


def build_main_module() -> str:
    """Return package __main__.py content."""

    return dedent(
        '''
        """Allow `python -m autonomous_project_development_agent`."""

        from .main import cli_main


        if __name__ == "__main__":
            raise SystemExit(cli_main())
        '''
    )


def build_goal_framework() -> str:
    """Return goal_framework.py content."""

    return dedent(
        '''
        """Goal modeling utilities for the Phase1 AI scaffold.

        Future phases can replace the prompt renderers with real AI prompt builders
        while keeping the ProjectGoal data contract stable.
        """

        from __future__ import annotations

        from dataclasses import asdict, dataclass, field
        from datetime import datetime, timezone
        from typing import Any
        from uuid import uuid4


        DEFAULT_GOAL_TEXT = (
            "Inspect a local project directory, summarize the Python package layout, "
            "and produce a safe AI placeholder recommendation."
        )


        @dataclass(slots=True)
        class ProjectGoal:
            """Structured representation of a Phase1 goal.

            Attributes:
                goal_id: Stable identifier for runtime state and logs.
                text: Raw user goal.
                use_ai: Whether the workflow may route AI-marked tasks to AIExecutor.
                project_dir: Directory that local safe tasks should inspect.
                priority: Simple Phase1 priority placeholder for later scheduling work.
                metadata: Extra room for memory, prompt, or integration hints.
                created_at: UTC timestamp for runtime persistence.
            """

            goal_id: str
            text: str
            use_ai: bool
            project_dir: str
            priority: int = 1
            metadata: dict[str, Any] = field(default_factory=dict)
            created_at: str = field(
                default_factory=lambda: datetime.now(timezone.utc).isoformat()
            )

            def to_dict(self) -> dict[str, Any]:
                """Convert the goal to a JSON-serializable dictionary."""

                return asdict(self)


        def build_project_goal(
            goal_text: str | None,
            project_dir: str,
            use_ai: bool = False,
            priority: int = 1,
        ) -> ProjectGoal:
            """Create a normalized Phase1 goal.

            Phase2 can expand this helper into richer validation, dependencies, and
            memory-aware normalization without changing the CLI contract.
            """

            text = (goal_text or DEFAULT_GOAL_TEXT).strip()
            metadata = {
                "phase": "phase1_ai",
                "prompt_template": "goal_summary_v1",
                "supports_future_external_ai": True,
            }
            return ProjectGoal(
                goal_id=f"goal-{uuid4().hex[:12]}",
                text=text,
                use_ai=use_ai,
                project_dir=project_dir,
                priority=priority,
                metadata=metadata,
            )


        def render_ai_goal_prompt(goal: ProjectGoal) -> str:
            """Build a safe prompt preview for future AI integration.

            This function deliberately returns plain text only. A real AI API client
            can consume the rendered prompt in later phases.
            """

            return (
                "You are preparing a safe Phase1 planning response. "
                f"Goal: {goal.text} "
                f"Project directory: {goal.project_dir} "
                "Output a concise analysis and a small set of next-step suggestions."
            )
        '''
    )


def build_task_planning() -> str:
    """Return task_planning.py content."""

    return dedent(
        '''
        """Task planning helpers for the Phase1 AI scaffold.

        The planner uses deterministic local rules in Phase1. Future phases can add
        dependency graphs, richer prompt templates, and dynamic planning strategies.
        """

        from __future__ import annotations

        from dataclasses import asdict, dataclass, field
        from typing import Any

        from .goal_framework import ProjectGoal, render_ai_goal_prompt


        @dataclass(slots=True)
        class PlannedTask:
            """Represents a single safe task in the Phase1 workflow."""

            task_id: str
            name: str
            description: str
            action: str
            use_ai: bool = False
            prompt_template: str | None = None
            metadata: dict[str, Any] = field(default_factory=dict)

            def to_dict(self) -> dict[str, Any]:
                """Convert the task to a JSON-serializable dictionary."""

                return asdict(self)


        def render_task_prompt(task: PlannedTask, goal: ProjectGoal) -> str:
            """Return a safe prompt preview for AI-enabled tasks."""

            goal_prompt = render_ai_goal_prompt(goal)
            return (
                f"{goal_prompt}\\n"
                f"Task name: {task.name}\\n"
                f"Task description: {task.description}\\n"
                "Return a minimal safe template response."
            )


        def build_phase1_tasks(goal: ProjectGoal) -> list[PlannedTask]:
            """Create a deterministic Phase1 task list.

            The planner keeps the workflow intentionally small and safe:
            1. Verify package placeholders exist.
            2. Inspect the target directory.
            3. Count Python files.
            4. Produce an AI placeholder summary when enabled.
            """

            tasks = [
                PlannedTask(
                    task_id="task-verify-modules",
                    name="verify_modules",
                    description="Check that core package placeholder modules exist.",
                    action="verify_modules",
                    metadata={"expected_modules": [
                        "goal_framework.py",
                        "task_planning.py",
                        "executor.py",
                        "result_analysis.py",
                        "loop_control.py",
                        "main.py",
                    ]},
                ),
                PlannedTask(
                    task_id="task-inspect-project",
                    name="inspect_project_directory",
                    description="Inspect the project directory and list top-level entries.",
                    action="inspect_project_directory",
                    metadata={"limit": 20},
                ),
                PlannedTask(
                    task_id="task-count-python",
                    name="count_python_files",
                    description="Count Python files beneath the project directory.",
                    action="count_python_files",
                ),
                PlannedTask(
                    task_id="task-ai-summary",
                    name="draft_ai_placeholder_output",
                    description=(
                        "Produce a safe AI placeholder summary and template code preview."
                    ),
                    action="draft_ai_placeholder_output",
                    use_ai=goal.use_ai,
                    prompt_template="phase1_ai_task_summary_v1",
                ),
            ]
            return tasks
        '''
    )


def build_executor() -> str:
    """Return executor.py content."""

    return dedent(
        '''
        """Execution adapters for the Phase1 AI scaffold.

        Phase1 uses only safe local logic. The AIExecutor is a placeholder boundary
        where future API-backed logic can be introduced without changing task shapes.
        """

        from __future__ import annotations

        import json
        from dataclasses import asdict, dataclass, field
        from datetime import datetime, timezone
        from pathlib import Path
        from typing import Any

        from .goal_framework import ProjectGoal, render_ai_goal_prompt
        from .task_planning import PlannedTask, render_task_prompt


        @dataclass(slots=True)
        class ExecutionContext:
            """Runtime paths and current goal for task execution."""

            project_root: str
            package_dir: str
            artifacts_dir: str
            goal: ProjectGoal
            enable_ai: bool = False

            def to_dict(self) -> dict[str, Any]:
                """Convert the execution context to a JSON-serializable dictionary."""

                data = asdict(self)
                data["goal"] = self.goal.to_dict()
                return data


        @dataclass(slots=True)
        class TaskResult:
            """Structured output from a local or AI placeholder task execution."""

            task_id: str
            executor_name: str
            status: str
            summary: str
            output: dict[str, Any] = field(default_factory=dict)
            logs: list[str] = field(default_factory=list)
            started_at: str = field(
                default_factory=lambda: datetime.now(timezone.utc).isoformat()
            )
            finished_at: str | None = None

            def to_dict(self) -> dict[str, Any]:
                """Convert the task result to a JSON-serializable dictionary."""

                return asdict(self)


        class BaseExecutor:
            """Shared interface for all Phase1 executors."""

            name = "base"

            def execute(self, task: PlannedTask, context: ExecutionContext) -> TaskResult:
                """Execute a task and return a structured result."""

                raise NotImplementedError


        class LocalPythonExecutor(BaseExecutor):
            """Run safe deterministic local tasks using only standard Python."""

            name = "local_python"

            def execute(self, task: PlannedTask, context: ExecutionContext) -> TaskResult:
                project_root = Path(context.project_root)
                package_dir = Path(context.package_dir)
                artifacts_dir = Path(context.artifacts_dir)
                artifacts_dir.mkdir(parents=True, exist_ok=True)

                if task.action == "verify_modules":
                    expected = task.metadata.get("expected_modules", [])
                    existing = []
                    missing = []
                    for module_name in expected:
                        module_path = package_dir / module_name
                        if module_path.exists():
                            existing.append(module_name)
                        else:
                            missing.append(module_name)
                    status = "passed" if not missing else "failed"
                    summary = (
                        "All placeholder modules are present."
                        if status == "passed"
                        else "Missing expected placeholder modules."
                    )
                    result = TaskResult(
                        task_id=task.task_id,
                        executor_name=self.name,
                        status=status,
                        summary=summary,
                        output={"existing_modules": existing, "missing_modules": missing},
                        logs=[f"Checked {len(expected)} expected module files."],
                    )
                elif task.action == "inspect_project_directory":
                    entries = sorted(item.name for item in project_root.iterdir())
                    limit = int(task.metadata.get("limit", 20))
                    result = TaskResult(
                        task_id=task.task_id,
                        executor_name=self.name,
                        status="passed",
                        summary="Collected project directory inventory.",
                        output={
                            "entry_count": len(entries),
                            "entries_preview": entries[:limit],
                        },
                        logs=[f"Scanned project root: {project_root}"],
                    )
                elif task.action == "count_python_files":
                    python_files = sorted(
                        str(path.relative_to(project_root))
                        for path in project_root.rglob("*.py")
                    )
                    result = TaskResult(
                        task_id=task.task_id,
                        executor_name=self.name,
                        status="passed",
                        summary="Counted Python files in the project directory.",
                        output={
                            "python_file_count": len(python_files),
                            "python_files_preview": python_files[:25],
                        },
                        logs=[f"Discovered {len(python_files)} Python files."],
                    )
                elif task.action == "draft_ai_placeholder_output":
                    artifact_path = artifacts_dir / "local_ai_fallback_summary.json"
                    payload = {
                        "mode": "local_fallback",
                        "goal": context.goal.text,
                        "recommendation": (
                            "AI is disabled. Keep using LocalPythonExecutor until "
                            "a real provider is integrated."
                        ),
                    }
                    artifact_path.write_text(
                        json.dumps(payload, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    result = TaskResult(
                        task_id=task.task_id,
                        executor_name=self.name,
                        status="passed",
                        summary="Produced a local fallback summary for the AI task.",
                        output={"artifact": str(artifact_path), "payload": payload},
                        logs=["AI flag disabled; returned a deterministic local fallback."],
                    )
                else:
                    result = TaskResult(
                        task_id=task.task_id,
                        executor_name=self.name,
                        status="failed",
                        summary=f"Unsupported local action: {task.action}",
                        output={"action": task.action},
                        logs=["The task action is not implemented in LocalPythonExecutor."],
                    )

                result.finished_at = datetime.now(timezone.utc).isoformat()
                return result


        class AIExecutor(BaseExecutor):
            """Return safe template output that simulates future AI execution.

            A real implementation can later replace this class with API-backed code
            generation or editing logic while preserving the same TaskResult shape.
            """

            name = "ai_placeholder"

            def execute(self, task: PlannedTask, context: ExecutionContext) -> TaskResult:
                artifacts_dir = Path(context.artifacts_dir)
                artifacts_dir.mkdir(parents=True, exist_ok=True)

                prompt = render_task_prompt(task, context.goal)
                goal_prompt = render_ai_goal_prompt(context.goal)
                artifact_path = artifacts_dir / "ai_placeholder_preview.py"
                template_code = (
                    "# AI placeholder preview generated locally\\n"
                    "def phase1_ai_placeholder():\\n"
                    "    return {\\n"
                    f"        'task_id': '{task.task_id}',\\n"
                    "        'message': 'Replace this deterministic template with a real AI executor in a later phase.'\\n"
                    "    }\\n"
                )
                artifact_path.write_text(template_code, encoding="utf-8")

                result = TaskResult(
                    task_id=task.task_id,
                    executor_name=self.name,
                    status="passed",
                    summary="Generated a safe AI placeholder response and code preview.",
                    output={
                        "artifact": str(artifact_path),
                        "ai_prompt_preview": prompt,
                        "goal_prompt_preview": goal_prompt,
                        "template_code": template_code,
                    },
                    logs=[
                        "AIExecutor returned deterministic local content.",
                        "No external API call was made.",
                    ],
                )
                result.finished_at = datetime.now(timezone.utc).isoformat()
                return result


        def build_executor(task: PlannedTask, enable_ai: bool) -> BaseExecutor:
            """Select the appropriate executor for a task."""

            if task.use_ai and enable_ai:
                return AIExecutor()
            return LocalPythonExecutor()
        '''
    )


def build_result_analysis() -> str:
    """Return result_analysis.py content."""

    return dedent(
        '''
        """Result analysis helpers for the Phase1 AI scaffold.

        The current analysis is intentionally simple. Future phases can add richer
        scoring, retry guidance, and memory-driven optimization here.
        """

        from __future__ import annotations

        from dataclasses import asdict, dataclass, field
        from typing import Any

        from .executor import TaskResult
        from .task_planning import PlannedTask


        @dataclass(slots=True)
        class AnalysisReport:
            """Structured assessment for a single task result or final run summary."""

            subject: str
            outcome: str
            score: float
            notes: list[str] = field(default_factory=list)
            details: dict[str, Any] = field(default_factory=dict)

            def to_dict(self) -> dict[str, Any]:
                """Convert the report to a JSON-serializable dictionary."""

                return asdict(self)


        def analyze_task_result(task: PlannedTask, result: TaskResult) -> AnalysisReport:
            """Evaluate whether a task passed and record a simple score."""

            notes = [result.summary]
            if result.status == "passed":
                score = 1.0
                outcome = "passed"
            elif result.status == "retryable":
                score = 0.5
                outcome = "retryable"
            else:
                score = 0.0
                outcome = "failed"

            if task.use_ai:
                notes.append(
                    "Task supports AI execution. In Phase1 this remains a safe placeholder."
                )

            return AnalysisReport(
                subject=task.task_id,
                outcome=outcome,
                score=score,
                notes=notes,
                details={"task": task.to_dict(), "result": result.to_dict()},
            )


        def build_phase1_report(
            analyses: list[AnalysisReport],
            task_results: list[TaskResult],
        ) -> AnalysisReport:
            """Build the final Phase1 summary report."""

            passed = sum(1 for report in analyses if report.outcome == "passed")
            retryable = sum(1 for report in analyses if report.outcome == "retryable")
            failed = sum(1 for report in analyses if report.outcome == "failed")
            total = len(analyses)
            final_outcome = "passed" if failed == 0 else "failed"
            average_score = sum(report.score for report in analyses) / total if total else 0.0

            return AnalysisReport(
                subject="phase1_run",
                outcome=final_outcome,
                score=average_score,
                notes=[
                    f"Completed {total} tasks.",
                    f"Passed: {passed}",
                    f"Retryable: {retryable}",
                    f"Failed: {failed}",
                ],
                details={
                    "task_results": [result.to_dict() for result in task_results],
                    "analyses": [report.to_dict() for report in analyses],
                },
            )


        def build_visualization_data(analyses: list[AnalysisReport]) -> dict[str, Any]:
            """Create simple chart-ready values for the Streamlit placeholder."""

            return {
                "labels": [report.subject for report in analyses],
                "scores": [report.score for report in analyses],
                "outcomes": [report.outcome for report in analyses],
            }
        '''
    )


def build_loop_control() -> str:
    """Return loop_control.py content."""

    return dedent(
        '''
        """Loop control helpers for the Phase1 AI scaffold.

        Phase1 only needs minimal counters and stop conditions. Later phases can add
        retries, priorities, dependencies, and human intervention hooks here.
        """

        from __future__ import annotations

        from dataclasses import asdict, dataclass, field
        from datetime import datetime, timezone
        from typing import Any

        from .result_analysis import AnalysisReport
        from .task_planning import PlannedTask


        @dataclass(slots=True)
        class LoopState:
            """Track the current Phase1 run progression."""

            phase: str
            current_task_id: str | None
            completed_tasks: list[str] = field(default_factory=list)
            failed_tasks: list[str] = field(default_factory=list)
            iteration_count: int = 0
            final_status: str = "not_started"
            updated_at: str = field(
                default_factory=lambda: datetime.now(timezone.utc).isoformat()
            )

            def to_dict(self) -> dict[str, Any]:
                """Convert the loop state to a JSON-serializable dictionary."""

                return asdict(self)


        def initialize_loop_state(tasks: list[PlannedTask]) -> LoopState:
            """Create the starting loop state for Phase1."""

            current_task_id = tasks[0].task_id if tasks else None
            return LoopState(phase="phase1_ai", current_task_id=current_task_id)


        def advance_loop(
            state: LoopState,
            task: PlannedTask,
            analysis: AnalysisReport,
            remaining_tasks: list[PlannedTask],
        ) -> LoopState:
            """Update the loop state after a task finishes."""

            state.iteration_count += 1
            state.updated_at = datetime.now(timezone.utc).isoformat()

            if analysis.outcome == "passed":
                state.completed_tasks.append(task.task_id)
            else:
                state.failed_tasks.append(task.task_id)

            if analysis.outcome == "failed":
                state.final_status = "failed"
                state.current_task_id = None
                return state

            if remaining_tasks:
                state.current_task_id = remaining_tasks[0].task_id
                state.final_status = "running"
            else:
                state.current_task_id = None
                state.final_status = "passed"
            return state
        '''
    )


def build_main_py() -> str:
    """Return main.py content."""

    return dedent(
        '''
        """CLI and Streamlit placeholder entry point for the Phase1 AI scaffold."""

        from __future__ import annotations

        import argparse
        import json
        import sys
        from datetime import datetime, timezone
        from pathlib import Path
        from typing import Any

        from . import APP_NAME, MODULE_MAP, PHASE_LABEL, RUNTIME_DIRNAME, __version__
        from .executor import ExecutionContext, TaskResult, build_executor
        from .goal_framework import DEFAULT_GOAL_TEXT, ProjectGoal, build_project_goal
        from .loop_control import LoopState, advance_loop, initialize_loop_state
        from .result_analysis import (
            AnalysisReport,
            analyze_task_result,
            build_phase1_report,
            build_visualization_data,
        )
        from .task_planning import PlannedTask, build_phase1_tasks


        def now_utc() -> str:
            """Return an ISO-formatted UTC timestamp."""

            return datetime.now(timezone.utc).isoformat()


        def package_dir() -> Path:
            """Return the installed package directory."""

            return Path(__file__).resolve().parent


        def project_root(base_dir: str | None = None) -> Path:
            """Return the project root for runtime output."""

            if base_dir:
                return Path(base_dir).resolve()
            return package_dir().parents[2]


        def runtime_root(base_dir: str | None = None) -> Path:
            """Return the Phase1 runtime directory."""

            return project_root(base_dir) / RUNTIME_DIRNAME


        def state_dir(base_dir: str | None = None) -> Path:
            """Return the state directory inside the runtime tree."""

            return runtime_root(base_dir) / "state"


        def logs_dir(base_dir: str | None = None) -> Path:
            """Return the logs directory inside the runtime tree."""

            return runtime_root(base_dir) / "logs"


        def artifacts_dir(base_dir: str | None = None) -> Path:
            """Return the artifacts directory inside the runtime tree."""

            return runtime_root(base_dir) / "artifacts"


        def ensure_runtime_tree(base_dir: str | None = None) -> None:
            """Create the runtime directories expected by the CLI and Streamlit views."""

            for directory in (
                runtime_root(base_dir),
                state_dir(base_dir),
                logs_dir(base_dir),
                artifacts_dir(base_dir),
            ):
                directory.mkdir(parents=True, exist_ok=True)


        def write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
            """Persist JSON with stable formatting."""

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )


        def read_json(path: Path, default: Any) -> Any:
            """Read JSON if it exists, otherwise return a default value."""

            if not path.exists():
                return default
            return json.loads(path.read_text(encoding="utf-8"))


        def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
            """Append a line-delimited JSON event."""

            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\\n")


        def state_file(name: str, base_dir: str | None = None) -> Path:
            """Return a named state file path."""

            return state_dir(base_dir) / name


        def initialize_memory(goal: ProjectGoal, base_dir: str | None = None) -> dict[str, Any]:
            """Store the current goal in a simple Phase1 memory placeholder."""

            memory_path = state_file("memory_store.json", base_dir)
            memory = read_json(memory_path, {"goals": []})
            memory["goals"].append(
                {
                    "goal_id": goal.goal_id,
                    "text": goal.text,
                    "use_ai": goal.use_ai,
                    "created_at": goal.created_at,
                    "project_dir": goal.project_dir,
                }
            )
            write_json(memory_path, memory)
            return memory


        def initialize_goal(
            goal_text: str | None,
            project_dir_value: str,
            enable_ai: bool,
            base_dir: str | None = None,
        ) -> ProjectGoal:
            """Create and persist the current Phase1 goal."""

            goal = build_project_goal(
                goal_text=goal_text,
                project_dir=project_dir_value,
                use_ai=enable_ai,
            )
            write_json(state_file("goal.json", base_dir), goal.to_dict())
            return goal


        def initialize_manifest(
            goal: ProjectGoal,
            base_dir: str | None = None,
        ) -> list[PlannedTask]:
            """Build and persist the Phase1 task list."""

            tasks = build_phase1_tasks(goal)
            write_json(
                state_file("task_manifest.json", base_dir),
                {
                    "goal_id": goal.goal_id,
                    "phase": "phase1_ai",
                    "tasks": [task.to_dict() for task in tasks],
                },
            )
            return tasks


        def initialize_status(goal: ProjectGoal, tasks: list[PlannedTask], base_dir: str | None) -> None:
            """Write the starting status snapshot for the run."""

            status_payload = {
                "app_name": APP_NAME,
                "phase": PHASE_LABEL,
                "status": "initialized",
                "goal_id": goal.goal_id,
                "goal_text": goal.text,
                "use_ai": goal.use_ai,
                "task_count": len(tasks),
                "updated_at": now_utc(),
            }
            write_json(state_file("phase1_status.json", base_dir), status_payload)


        def build_context(
            goal: ProjectGoal,
            base_dir: str | None,
            project_dir_value: str,
            enable_ai: bool,
        ) -> ExecutionContext:
            """Create the runtime execution context."""

            return ExecutionContext(
                project_root=str(Path(project_dir_value).resolve()),
                package_dir=str(package_dir()),
                artifacts_dir=str(artifacts_dir(base_dir)),
                goal=goal,
                enable_ai=enable_ai,
            )


        def run_phase1(
            goal_text: str | None,
            project_dir_value: str,
            enable_ai: bool,
            base_dir: str | None = None,
        ) -> AnalysisReport:
            """Execute the full Phase1 safe workflow."""

            ensure_runtime_tree(base_dir)
            goal = initialize_goal(goal_text, project_dir_value, enable_ai, base_dir)
            tasks = initialize_manifest(goal, base_dir)
            initialize_status(goal, tasks, base_dir)
            memory = initialize_memory(goal, base_dir)

            ai_state = {
                "enabled": enable_ai,
                "executor_mode": "AIExecutor" if enable_ai else "LocalPythonExecutor",
                "goal_id": goal.goal_id,
                "updated_at": now_utc(),
            }
            write_json(state_file("ai_execution_state.json", base_dir), ai_state)

            context = build_context(goal, base_dir, project_dir_value, enable_ai)
            loop_state = initialize_loop_state(tasks)
            write_json(state_file("loop_state.json", base_dir), loop_state.to_dict())

            task_results: list[TaskResult] = []
            analyses: list[AnalysisReport] = []

            for index, task in enumerate(tasks):
                executor = build_executor(task, enable_ai)
                result = executor.execute(task, context)
                analysis = analyze_task_result(task, result)
                remaining = tasks[index + 1 :]
                loop_state = advance_loop(loop_state, task, analysis, remaining)

                task_results.append(result)
                analyses.append(analysis)

                append_jsonl(
                    logs_dir(base_dir) / "execution_log.jsonl",
                    {
                        "timestamp": now_utc(),
                        "goal_id": goal.goal_id,
                        "task": task.to_dict(),
                        "result": result.to_dict(),
                        "analysis": analysis.to_dict(),
                    },
                )
                write_json(state_file("loop_state.json", base_dir), loop_state.to_dict())

            final_report = build_phase1_report(analyses, task_results)
            visualization = build_visualization_data(analyses)
            write_json(state_file("final_report.json", base_dir), final_report.to_dict())
            write_json(state_file("visualization_data.json", base_dir), visualization)
            write_json(
                state_file("phase1_status.json", base_dir),
                {
                    "app_name": APP_NAME,
                    "phase": PHASE_LABEL,
                    "status": final_report.outcome,
                    "goal_id": goal.goal_id,
                    "goal_text": goal.text,
                    "use_ai": goal.use_ai,
                    "task_count": len(tasks),
                    "completed_tasks": [report.subject for report in analyses if report.outcome == "passed"],
                    "failed_tasks": [report.subject for report in analyses if report.outcome == "failed"],
                    "memory_goal_count": len(memory.get("goals", [])),
                    "updated_at": now_utc(),
                },
            )
            return final_report


        def initialize_only(
            goal_text: str | None,
            project_dir_value: str,
            enable_ai: bool,
            base_dir: str | None = None,
        ) -> None:
            """Create runtime files without executing tasks."""

            ensure_runtime_tree(base_dir)
            goal = initialize_goal(goal_text, project_dir_value, enable_ai, base_dir)
            tasks = initialize_manifest(goal, base_dir)
            initialize_memory(goal, base_dir)
            initialize_status(goal, tasks, base_dir)
            write_json(
                state_file("ai_execution_state.json", base_dir),
                {
                    "enabled": enable_ai,
                    "executor_mode": "AIExecutor" if enable_ai else "LocalPythonExecutor",
                    "goal_id": goal.goal_id,
                    "updated_at": now_utc(),
                },
            )
            write_json(
                state_file("loop_state.json", base_dir),
                initialize_loop_state(tasks).to_dict(),
            )


        def print_status(base_dir: str | None = None) -> int:
            """Print a concise CLI status overview."""

            ensure_runtime_tree(base_dir)
            status = read_json(
                state_file("phase1_status.json", base_dir),
                {
                    "app_name": APP_NAME,
                    "phase": PHASE_LABEL,
                    "status": "not_initialized",
                    "goal_text": DEFAULT_GOAL_TEXT,
                    "use_ai": False,
                    "task_count": 0,
                },
            )
            memory = read_json(state_file("memory_store.json", base_dir), {"goals": []})
            manifest = read_json(state_file("task_manifest.json", base_dir), {"tasks": []})
            ai_state = read_json(
                state_file("ai_execution_state.json", base_dir),
                {"enabled": False, "executor_mode": "LocalPythonExecutor"},
            )

            print(f"{APP_NAME} | {PHASE_LABEL}")
            print(f"Version: {__version__}")
            print(f"Status: {status.get('status')}")
            print(f"Goal: {status.get('goal_text')}")
            print(f"AI enabled: {ai_state.get('enabled')}")
            print(f"Executor mode: {ai_state.get('executor_mode')}")
            print(f"Task count: {len(manifest.get('tasks', []))}")
            print(f"Stored goals: {len(memory.get('goals', []))}")
            print("Modules:")
            for name, description in MODULE_MAP.items():
                print(f"  - {name}: {description}")
            return 0


        def print_report(base_dir: str | None = None) -> int:
            """Print the latest final report if available."""

            report = read_json(state_file("final_report.json", base_dir), None)
            if report is None:
                print("No Phase1 report found. Run --run-phase1 first.")
                return 1
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0


        def render_streamlit_placeholder(base_dir: str | None = None) -> None:
            """Render a simple Streamlit dashboard for the current runtime state."""

            import streamlit as st

            ensure_runtime_tree(base_dir)
            st.set_page_config(page_title="APDA Phase1 AI", layout="wide")
            st.title("Autonomous Project Development Agent")
            st.caption("Phase1 AI scaffold dashboard")

            goal = read_json(state_file("goal.json", base_dir), {})
            manifest = read_json(state_file("task_manifest.json", base_dir), {"tasks": []})
            memory = read_json(state_file("memory_store.json", base_dir), {"goals": []})
            ai_state = read_json(state_file("ai_execution_state.json", base_dir), {})
            loop_state = read_json(state_file("loop_state.json", base_dir), {})
            report = read_json(state_file("final_report.json", base_dir), {})
            visualization = read_json(state_file("visualization_data.json", base_dir), {})
            log_path = logs_dir(base_dir) / "execution_log.jsonl"

            left, right = st.columns([2, 1])
            with left:
                st.subheader("Current Goal")
                st.json(goal or {"message": "No goal initialized yet."})

                st.subheader("Task List")
                st.json(manifest)

                st.subheader("Final Report")
                st.json(report or {"message": "No report generated yet."})

            with right:
                st.subheader("AI Execution State")
                st.json(ai_state or {"enabled": False})

                st.subheader("Loop State")
                st.json(loop_state or {"status": "not_started"})

                st.subheader("Memory")
                st.json(memory)

            st.subheader("Visualization Data")
            st.json(visualization)

            st.subheader("Execution Log")
            if log_path.exists():
                log_lines = log_path.read_text(encoding="utf-8").splitlines()
                st.code("\\n".join(log_lines[-20:]), language="json")
            else:
                st.info("No execution log found. Run the Phase1 workflow first.")

            st.info(
                "This dashboard is Phase1-only. Future phases can add richer charts, "
                "historical browsing, and real AI-backed execution."
            )


        def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
            """Build the CLI parser for the Phase1 AI scaffold."""

            parser = argparse.ArgumentParser(description=APP_NAME)
            parser.add_argument("--goal", help="Goal text for the Phase1 run.")
            parser.add_argument(
                "--project-dir",
                default=".",
                help="Project directory to inspect for safe local tasks.",
            )
            parser.add_argument(
                "--base-dir",
                help="Optional project root override for runtime output.",
            )
            parser.add_argument(
                "--enable-ai",
                action="store_true",
                help="Enable the safe AIExecutor placeholder for AI-marked tasks.",
            )
            parser.add_argument("--init", action="store_true", help="Initialize runtime state.")
            parser.add_argument("--status", action="store_true", help="Print current Phase1 status.")
            parser.add_argument(
                "--run-phase1",
                action="store_true",
                help="Execute the Phase1 task tree using safe local logic.",
            )
            parser.add_argument("--report", action="store_true", help="Print the latest final report.")
            parser.add_argument(
                "--visualize",
                action="store_true",
                help="Render the Streamlit placeholder dashboard.",
            )
            return parser.parse_args(argv)


        def cli_main(argv: list[str] | None = None) -> int:
            """Primary CLI entry point."""

            args = parse_args(argv)
            base_dir = args.base_dir
            project_dir_value = str(Path(args.project_dir).resolve())

            if args.visualize:
                render_streamlit_placeholder(base_dir)
                return 0

            if args.init:
                initialize_only(args.goal, project_dir_value, args.enable_ai, base_dir)
                print("Phase1 AI runtime initialized.")
                return 0

            if args.run_phase1:
                report = run_phase1(args.goal, project_dir_value, args.enable_ai, base_dir)
                print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
                return 0 if report.outcome == "passed" else 1

            if args.report:
                return print_report(base_dir)

            if args.status or not any(
                [args.init, args.run_phase1, args.report, args.visualize]
            ):
                return print_status(base_dir)

            return 0


        if __name__ == "__main__":
            raise SystemExit(cli_main(sys.argv[1:]))
        '''
    )


def build_tests_gitkeep() -> str:
    """Return the placeholder content for tests/.gitkeep."""

    return "\n"


def generated_files() -> dict[str, str]:
    """Build the complete generated file map."""

    return {
        "README.md": build_readme(),
        "docs/project_overview.md": build_project_overview(),
        "docs/development_plan.md": build_development_plan(),
        ".gitignore": build_gitignore(),
        "requirements.txt": build_requirements(),
        "pyproject.toml": build_pyproject(),
        "tests/.gitkeep": build_tests_gitkeep(),
        "src/autonomous_project_development_agent/__init__.py": build_init_py(),
        "src/autonomous_project_development_agent/__main__.py": build_main_module(),
        "src/autonomous_project_development_agent/main.py": build_main_py(),
        "src/autonomous_project_development_agent/goal_framework.py": build_goal_framework(),
        "src/autonomous_project_development_agent/task_planning.py": build_task_planning(),
        "src/autonomous_project_development_agent/executor.py": build_executor(),
        "src/autonomous_project_development_agent/result_analysis.py": build_result_analysis(),
        "src/autonomous_project_development_agent/loop_control.py": build_loop_control(),
    }


def generate_project(target_dir: Path) -> None:
    """Write the scaffold to disk."""

    for relative_path, content in generated_files().items():
        write_file(target_dir / relative_path, content)


def parse_args() -> argparse.Namespace:
    """Parse script arguments."""

    parser = argparse.ArgumentParser(
        description="Generate a Phase1 AI scaffold for the Autonomous Project Development Agent."
    )
    parser.add_argument(
        "--target-dir",
        default=DEFAULT_TARGET_NAME,
        help=(
            "Directory where the scaffold should be generated. Defaults to "
            f"'{DEFAULT_TARGET_NAME}' relative to the current working directory."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the target directory if it already exists and is not empty.",
    )
    return parser.parse_args()


def main() -> int:
    """Generate the scaffold and print a concise summary."""

    args = parse_args()
    target_dir = Path(args.target_dir).expanduser().resolve()
    ensure_clean_target(target_dir, args.overwrite)
    generate_project(target_dir)

    print(f"Generated Phase1 AI scaffold at: {target_dir}")
    print("Next steps:")
    print(f"  cd {target_dir}")
    print("  python3 -m venv venv")
    print("  source venv/bin/activate")
    print("  pip install -e .")
    print("  python -m autonomous_project_development_agent --run-phase1 --enable-ai")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""CLI and Streamlit entry point for Phase1 to Phase5 workflows."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable


if __package__ in {None, ""}:
    SRC_ROOT = Path(__file__).resolve().parents[1]
    if str(SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(SRC_ROOT))

    from autonomous_project_development_agent import (  # type: ignore
        APP_NAME,
        DEFAULT_PHASE2_GOAL,
        DEFAULT_PHASE3_GOAL,
        DEFAULT_PHASE4_GOAL,
        DEFAULT_PHASE5_GOAL,
        PACKAGE_NAME,
        PHASE1_MODULE_MAP,
        PHASE1_RUNTIME_DIRNAME,
        PHASE1_TASK_BLUEPRINTS,
        PLACEHOLDER_LOGS,
        __version__,
    )
    from autonomous_project_development_agent.ai_provider import (  # type: ignore
        load_ai_provider_config,
        provider_status_snapshot,
    )
    from autonomous_project_development_agent.executor import (  # type: ignore
        ExecutionContext,
        TaskResult as WorkflowTaskResult,
        execute_task_batch,
    )
    from autonomous_project_development_agent.goal_framework import (  # type: ignore
        ProjectGoal,
        build_project_goal,
        load_memory_status,
        persist_goal_memory,
        query_goal_memory,
        render_goal_ai_prompt,
        retrieve_memory_context,
    )
    from autonomous_project_development_agent.loop_control import (  # type: ignore
        LoopState,
        apply_batch_to_loop,
        initialize_loop_state,
        select_ready_tasks,
    )
    from autonomous_project_development_agent.result_analysis import (  # type: ignore
        AnalysisReport,
        analyze_task_result,
        build_final_report,
        load_task_history,
        load_workflow_history,
        query_task_history,
        query_workflow_history,
        update_task_history,
        update_workflow_history,
    )
    from autonomous_project_development_agent.task_planning import (  # type: ignore
        PlannedTask,
        build_plan_payload,
        generate_task_plan,
        render_task_prompt,
    )
else:
    from . import (
        APP_NAME,
        DEFAULT_PHASE2_GOAL,
        DEFAULT_PHASE3_GOAL,
        DEFAULT_PHASE4_GOAL,
        DEFAULT_PHASE5_GOAL,
        PACKAGE_NAME,
        PHASE1_MODULE_MAP,
        PHASE1_RUNTIME_DIRNAME,
        PHASE1_TASK_BLUEPRINTS,
        PLACEHOLDER_LOGS,
        __version__,
    )
    from .ai_provider import load_ai_provider_config, provider_status_snapshot
    from .executor import ExecutionContext, TaskResult as WorkflowTaskResult, execute_task_batch
    from .goal_framework import (
        ProjectGoal,
        build_project_goal,
        load_memory_status,
        persist_goal_memory,
        query_goal_memory,
        render_goal_ai_prompt,
        retrieve_memory_context,
    )
    from .loop_control import LoopState, apply_batch_to_loop, initialize_loop_state, select_ready_tasks
    from .result_analysis import (
        AnalysisReport,
        analyze_task_result,
        build_final_report,
        load_task_history,
        load_workflow_history,
        query_task_history,
        query_workflow_history,
        update_task_history,
        update_workflow_history,
    )
    from .task_planning import PlannedTask, build_plan_payload, generate_task_plan, render_task_prompt


@dataclass(frozen=True)
class ValidationResult:
    """Container for a single Phase1 validation check."""

    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class TaskSpec:
    """Definition for a safe, runnable Phase1 placeholder task."""

    module_name: str
    task_id: str
    title: str
    description: str
    script_name: str


@dataclass(frozen=True)
class Phase1TaskRunResult:
    """Captured result for one executed Phase1 task."""

    module_name: str
    task_id: str
    title: str
    status: str
    returncode: int
    verification: str
    duration_seconds: float
    output: str
    artifact_path: str | None
    details: dict[str, Any]


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for Phase1 to Phase5 workflows."""
    parser = argparse.ArgumentParser(
        description="CLI for the Autonomous Project Development Agent prototype."
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--init",
        action="store_true",
        help="Initialize the Phase1 runtime task tree in the current directory.",
    )
    actions.add_argument(
        "--status",
        action="store_true",
        help="Print the latest Phase1 to Phase5 status summaries.",
    )
    actions.add_argument(
        "--run-phase1",
        action="store_true",
        help="Run the safe Phase1 placeholder task set.",
    )
    actions.add_argument(
        "--plan",
        action="store_true",
        help="Generate and persist the Phase2 sequential task plan.",
    )
    actions.add_argument(
        "--run-phase2",
        action="store_true",
        help="Execute the minimal Phase2 closed-loop workflow.",
    )
    actions.add_argument(
        "--run-phase3",
        action="store_true",
        help="Execute the Phase3 autonomous workflow with memory and batched task handling.",
    )
    actions.add_argument(
        "--run-phase4",
        action="store_true",
        help="Execute the Phase4 autonomous workflow with memory, task trees, and review packaging.",
    )
    actions.add_argument(
        "--run-phase5",
        action="store_true",
        help="Execute the Phase5 autonomous workflow with local memory, heuristic planning, and self-optimization.",
    )
    actions.add_argument(
        "--report",
        action="store_true",
        help="Show the latest persisted workflow final report.",
    )
    actions.add_argument(
        "--memory-status",
        action="store_true",
        help="Show the stored memory state and vector-store placeholder entries.",
    )
    actions.add_argument(
        "--memory-query",
        action="store_true",
        help="Query historical goal, task, and workflow memory using local matching rules.",
    )
    actions.add_argument(
        "--visualize",
        action="store_true",
        help="Launch the Streamlit dashboard for goals, tasks, logs, and reports.",
    )
    parser.add_argument(
        "--goal",
        dest="goal_text",
        help="Simple project goal. If omitted, the latest saved goal or the phase default is used.",
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Local project directory that the workflow should inspect safely.",
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Base directory for runtime state such as logs, plans, reports, and memory placeholders.",
    )
    parser.add_argument(
        "--enable-ai",
        action="store_true",
        help="Enable AIExecutor for AI-capable placeholder tasks while keeping execution local and safe.",
    )
    parser.add_argument(
        "--ai-provider",
        default=None,
        help="AI provider route to use when --enable-ai is active. Defaults to APDA_AI_PROVIDER or local_placeholder.",
    )
    return parser


def utc_now() -> str:
    """Return an ISO 8601 timestamp in UTC."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def module_names() -> list[str]:
    """Return the ordered list of scaffold module names."""
    return [module_name for module_name, _ in PHASE1_MODULE_MAP]


def build_task_specs() -> list[TaskSpec]:
    """Build the Phase1 task tree from the static blueprint."""
    return [
        TaskSpec(
            module_name=module_name,
            task_id=task_id,
            title=title,
            description=description,
            script_name=script_name,
        )
        for module_name, task_id, title, description, script_name in PHASE1_TASK_BLUEPRINTS
    ]


def format_module_map() -> str:
    """Return the module map as human-readable text."""
    lines = [f"{APP_NAME} v{__version__}", "Module map:"]
    for module_name, description in PHASE1_MODULE_MAP:
        lines.append(f"- {module_name}: {description}")
    return "\n".join(lines)


def runtime_root(base_dir: Path | str) -> Path:
    """Resolve the shared runtime directory from a user-supplied base path."""
    return Path(base_dir).resolve() / PHASE1_RUNTIME_DIRNAME


def logs_dir(base_dir: Path | str) -> Path:
    """Return the log directory inside the runtime tree."""
    return runtime_root(base_dir) / "logs"


def state_dir(base_dir: Path | str) -> Path:
    """Return the state directory inside the runtime tree."""
    return runtime_root(base_dir) / "state"


def task_tree_dir(base_dir: Path | str) -> Path:
    """Return the task tree directory inside the runtime tree."""
    return runtime_root(base_dir) / "task_tree"


def artifacts_dir(base_dir: Path | str) -> Path:
    """Return the artifacts directory inside the runtime tree."""
    return runtime_root(base_dir) / "artifacts"


def phase1_status_path(base_dir: Path | str) -> Path:
    """Return the Phase1 status file path."""
    return state_dir(base_dir) / "phase1_status.json"


def phase1_manifest_path(base_dir: Path | str) -> Path:
    """Return the Phase1 task manifest path."""
    return state_dir(base_dir) / "task_manifest.json"


def goal_path(base_dir: Path | str) -> Path:
    """Return the persisted workflow goal path."""
    return state_dir(base_dir) / "goal.json"


def plan_path(base_dir: Path | str) -> Path:
    """Return the persisted workflow plan path."""
    return state_dir(base_dir) / "plan.json"


def loop_state_path(base_dir: Path | str) -> Path:
    """Return the persisted workflow loop state path."""
    return state_dir(base_dir) / "loop_state.json"


def final_report_path(base_dir: Path | str) -> Path:
    """Return the persisted workflow final report path."""
    return state_dir(base_dir) / "final_report.json"


def execution_log_path(base_dir: Path | str) -> Path:
    """Return the shared append-only execution log path."""
    return logs_dir(base_dir) / "execution_log.jsonl"


def memory_store_path(base_dir: Path | str) -> Path:
    """Return the persisted long-term memory store path."""
    return state_dir(base_dir) / "memory_store.json"


def vector_store_placeholder_path(base_dir: Path | str) -> Path:
    """Return the placeholder vector-store path."""
    return state_dir(base_dir) / "vector_store_placeholder.json"


def ai_execution_state_path(base_dir: Path | str) -> Path:
    """Return the persisted AI execution state path."""

    return state_dir(base_dir) / "ai_execution_state.json"


def read_json_file(path: Path) -> dict[str, Any] | None:
    """Read a JSON file if it exists and is valid."""
    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_json_file(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON payload using deterministic formatting."""
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def append_json_line(path: Path, payload: dict[str, Any]) -> None:
    """Append a structured JSON log record."""
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def read_recent_logs(base_dir: Path | str, limit: int = 20) -> list[dict[str, Any]]:
    """Load recent structured log records for CLI and Streamlit display."""
    records: list[dict[str, Any]] = []
    path = execution_log_path(base_dir)
    if not path.exists():
        return records

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records[-limit:]


def load_ai_execution_state(base_dir: Path | str) -> dict[str, Any]:
    """Load the persisted AI execution state or return a safe default."""

    return read_json_file(ai_execution_state_path(base_dir)) or {
        "updated_at": None,
        "phase": None,
        "enabled": False,
        "ai_provider": "disabled",
        "goal_id": None,
        "goal_use_ai": False,
        "ai_task_count": 0,
        "actual_ai_executor_runs": 0,
        "available_routes": [],
    }


def persist_ai_execution_state(
    base_dir: Path | str,
    *,
    phase: str,
    enabled: bool,
    goal: ProjectGoal | None = None,
    tasks: list[PlannedTask] | None = None,
    ai_provider: str | None = None,
    actual_ai_executor_runs: int = 0,
) -> dict[str, Any]:
    """Persist a structured AI execution state snapshot for CLI and Streamlit."""

    tasks = tasks or []
    provider_name = goal.ai_provider if goal else (ai_provider or ("local_placeholder" if enabled else "disabled"))
    provider_config = load_ai_provider_config(provider_name if enabled else "local_placeholder")
    provider_status = provider_status_snapshot(provider_config)
    if not enabled:
        provider_status["provider_name"] = "disabled"
        provider_status["allow_live_calls"] = False

    payload = {
        "updated_at": utc_now(),
        "phase": phase,
        "enabled": enabled,
        "ai_provider": provider_name if enabled else "disabled",
        "goal_id": goal.goal_id if goal else None,
        "goal_use_ai": bool(goal.use_ai) if goal else enabled,
        "goal_prompt_preview": render_goal_ai_prompt(goal) if goal else None,
        "ai_task_count": sum(1 for task in tasks if task.use_ai),
        "planned_ai_routes": sorted({task.executor_type for task in tasks if task.use_ai}),
        "actual_ai_executor_runs": actual_ai_executor_runs,
        "available_routes": [
            "AIExecutor",
            "LocalPythonExecutor",
            "PlaceholderAgentExecutor",
            "CodexExecutor",
            "GPTExecutor",
        ],
        "provider_status": provider_status,
    }
    write_json_file(ai_execution_state_path(base_dir), payload)
    return payload


def collect_project_state() -> dict[str, Any]:
    """Read the current scaffold state from the package modules."""
    modules: list[dict[str, str]] = []
    for module_name, description in PHASE1_MODULE_MAP:
        module = import_module(f"{PACKAGE_NAME}.{module_name}")
        docstring = (module.__doc__ or "").strip()
        modules.append(
            {
                "module_name": module_name,
                "description": description,
                "docstring_summary": docstring.splitlines()[0] if docstring else description,
            }
        )

    return {
        "package_name": PACKAGE_NAME,
        "app_name": APP_NAME,
        "version": __version__,
        "module_count": len(modules),
        "modules": modules,
    }


def ensure_runtime_tree(base_dir: Path | str) -> list[Path]:
    """Create the shared runtime directory structure."""
    directories = [
        runtime_root(base_dir),
        logs_dir(base_dir),
        state_dir(base_dir),
        task_tree_dir(base_dir),
        artifacts_dir(base_dir),
    ]

    created: list[Path] = []
    for directory in directories:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created.append(directory)
        else:
            directory.mkdir(parents=True, exist_ok=True)
    execution_log_path(base_dir).touch(exist_ok=True)
    return created


def task_directory(base_dir: Path | str, task_index: int, module_name: str) -> Path:
    """Return a numbered task directory for a Phase1 module boundary."""
    return task_tree_dir(base_dir) / f"{task_index:02d}_{module_name}"


def initialize_phase1_tree(base_dir: Path | str) -> list[Path]:
    """Create the placeholder runtime directory structure for Phase1."""
    created = ensure_runtime_tree(base_dir)
    for index, (module_name, _) in enumerate(PHASE1_MODULE_MAP, start=1):
        directory = task_directory(base_dir, index, module_name)
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created.append(directory)
    return created


def build_task_manifest(base_dir: Path | str) -> dict[str, Any]:
    """Create the Phase1 task manifest structure."""
    return {
        "generated_at": utc_now(),
        "runtime_root": str(runtime_root(base_dir)),
        "tasks": [
            {
                "order": index,
                "module_name": spec.module_name,
                "task_id": spec.task_id,
                "title": spec.title,
                "description": spec.description,
                "use_ai": False,
                "script_path": str(task_directory(base_dir, index, spec.module_name) / spec.script_name),
            }
            for index, spec in enumerate(build_task_specs(), start=1)
        ],
    }


def task_script_source(spec: TaskSpec) -> str:
    """Generate a safe Python script for one Phase1 placeholder task."""
    module_names_literal = repr(module_names())
    package_name_literal = repr(PACKAGE_NAME)
    source_root_literal = repr(str(Path(__file__).resolve().parents[1]))

    shared_header = textwrap.dedent(
        f"""
        import json
        import sys
        from pathlib import Path

        RUNTIME_ROOT = Path(__file__).resolve().parents[2]
        SRC_ROOT = Path({source_root_literal})
        if str(SRC_ROOT) not in sys.path:
            sys.path.insert(0, str(SRC_ROOT))

        STATE_DIR = RUNTIME_ROOT / "state"
        TASK_TREE_DIR = RUNTIME_ROOT / "task_tree"
        PACKAGE_NAME = {package_name_literal}
        MODULE_NAMES = {module_names_literal}
        """
    ).strip()

    if spec.task_id == "module_verification":
        body = """
from importlib import import_module

checks = []
for module_name in MODULE_NAMES:
    module = import_module(f"{PACKAGE_NAME}.{module_name}")
    docstring = (module.__doc__ or "").strip()
    checks.append(
        {
            "module_name": module_name,
            "has_docstring": bool(docstring),
            "summary": docstring.splitlines()[0] if docstring else "",
        }
    )

payload = {
    "task_id": "module_verification",
    "success": all(item["has_docstring"] for item in checks),
    "verification": f"Verified {len(checks)} Phase1 modules with docstrings.",
    "details": {"modules": checks},
}
print(json.dumps(payload))
"""
    elif spec.task_id == "task_tree_snapshot":
        body = """
directories = sorted(path.name for path in TASK_TREE_DIR.iterdir() if path.is_dir())
payload = {
    "task_id": "task_tree_snapshot",
    "success": len(directories) >= len(MODULE_NAMES),
    "verification": f"Detected {len(directories)} task directories in the Phase1 task tree.",
    "details": {
        "task_directory_count": len(directories),
        "task_directories": directories,
    },
}
print(json.dumps(payload))
"""
    elif spec.task_id == "placeholder_execution":
        body = """
artifact_path = STATE_DIR / "executor_placeholder_output.json"
payload_data = {
    "message": "Executor placeholder ran safely.",
    "python_executable": sys.executable,
    "runtime_root": str(RUNTIME_ROOT),
}
artifact_path.write_text(json.dumps(payload_data, indent=2) + "\\n", encoding="utf-8")
payload = {
    "task_id": "placeholder_execution",
    "success": artifact_path.exists(),
    "verification": "Executor placeholder artifact created successfully.",
    "artifact_path": str(artifact_path),
    "details": payload_data,
}
print(json.dumps(payload))
"""
    elif spec.task_id == "dummy_data_processing":
        body = """
from statistics import mean

dataset = [2, 4, 6, 8, 10]
summary = {
    "count": len(dataset),
    "total": sum(dataset),
    "mean": mean(dataset),
    "minimum": min(dataset),
    "maximum": max(dataset),
}
artifact_path = STATE_DIR / "dummy_data_summary.json"
artifact_path.write_text(json.dumps(summary, indent=2) + "\\n", encoding="utf-8")
payload = {
    "task_id": "dummy_data_processing",
    "success": summary["total"] == 30 and summary["mean"] == 6,
    "verification": "Dummy data processing completed with the expected summary values.",
    "artifact_path": str(artifact_path),
    "details": summary,
}
print(json.dumps(payload))
"""
    elif spec.task_id == "initial_logging":
        body = """
artifacts = sorted(path.name for path in STATE_DIR.glob("*.json"))
artifact_path = STATE_DIR / "loop_control_checkpoint.json"
checkpoint = {
    "observed_artifacts": artifacts,
    "artifact_count": len(artifacts),
    "status": "ready_for_phase1_report" if len(artifacts) >= 2 else "incomplete",
}
artifact_path.write_text(json.dumps(checkpoint, indent=2) + "\\n", encoding="utf-8")
payload = {
    "task_id": "initial_logging",
    "success": checkpoint["artifact_count"] >= 2,
    "verification": f"Loop control checkpoint recorded {checkpoint['artifact_count']} artifacts.",
    "artifact_path": str(artifact_path),
    "details": checkpoint,
}
print(json.dumps(payload))
"""
    else:
        raise ValueError(f"Unsupported Phase1 task: {spec.task_id}")

    return textwrap.dedent(f"{shared_header}\n\n{body}").strip() + "\n"


def write_task_scripts(base_dir: Path | str) -> list[Path]:
    """Generate the runnable Phase1 task scripts under the task tree."""
    written: list[Path] = []
    for index, spec in enumerate(build_task_specs(), start=1):
        script_path = task_directory(base_dir, index, spec.module_name) / spec.script_name
        contents = task_script_source(spec)
        if not script_path.exists() or script_path.read_text(encoding="utf-8") != contents:
            script_path.write_text(contents, encoding="utf-8")
            written.append(script_path)
    return written


def initialize_phase1_status(base_dir: Path | str, *, enable_ai: bool = False) -> dict[str, Any]:
    """Create an initial pending Phase1 status file."""
    manifest = build_task_manifest(base_dir)
    status = {
        "phase": "Phase1",
        "generated_at": utc_now(),
        "last_run_at": None,
        "overall_status": "pending",
        "ai_enabled": enable_ai,
        "ai_execution_mode": "AIExecutor" if enable_ai else "LocalPythonExecutor",
        "summary": {
            "total_tasks": len(manifest["tasks"]),
            "completed_tasks": 0,
            "passed_tasks": 0,
            "failed_tasks": 0,
        },
        "project_state": collect_project_state(),
        "tasks": [
            {
                "module_name": task["module_name"],
                "task_id": task["task_id"],
                "title": task["title"],
                "status": "pending",
                "verification": "Not executed yet.",
                "artifact_path": None,
                "use_ai": False,
            }
            for task in manifest["tasks"]
        ],
    }
    write_json_file(phase1_manifest_path(base_dir), manifest)
    write_json_file(phase1_status_path(base_dir), status)
    append_json_line(
        execution_log_path(base_dir),
        {
            "timestamp": utc_now(),
            "phase": "Phase1",
            "event": "phase1_initialized",
            "runtime_root": str(runtime_root(base_dir)),
            "task_count": len(manifest["tasks"]),
            "ai_enabled": enable_ai,
        },
    )
    return status


def parse_phase1_task_output(output: str) -> dict[str, Any]:
    """Extract the JSON payload from a Phase1 task stdout stream."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return {"success": False, "verification": "Task produced no output.", "details": {}}

    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return {
            "success": False,
            "verification": "Task output was not valid JSON.",
            "details": {"raw_output": output},
        }


def verify_phase1_task_payload(spec: TaskSpec, payload: dict[str, Any]) -> tuple[bool, str]:
    """Perform a lightweight verification of the Phase1 task payload."""
    success = bool(payload.get("success"))
    artifact_path_value = payload.get("artifact_path")
    artifact_exists = True
    if artifact_path_value:
        artifact_exists = Path(artifact_path_value).exists()

    if spec.task_id == "module_verification":
        modules = payload.get("details", {}).get("modules", [])
        success = success and len(modules) == len(module_names())
    elif spec.task_id == "task_tree_snapshot":
        directory_count = payload.get("details", {}).get("task_directory_count", 0)
        success = success and directory_count >= len(build_task_specs())
    elif spec.task_id == "placeholder_execution":
        success = success and artifact_exists
    elif spec.task_id == "dummy_data_processing":
        details = payload.get("details", {})
        success = success and details.get("total") == 30 and details.get("mean") == 6
    elif spec.task_id == "initial_logging":
        artifact_count = payload.get("details", {}).get("artifact_count", 0)
        success = success and artifact_exists and artifact_count >= 2

    verification = payload.get("verification", "Verification completed.")
    if not artifact_exists:
        verification = f"{verification} Missing artifact: {artifact_path_value}"
    return success, verification


def run_phase1_task_script(base_dir: Path | str, task_index: int, spec: TaskSpec) -> Phase1TaskRunResult:
    """Execute one generated Phase1 task script and capture its result."""
    script_path = task_directory(base_dir, task_index, spec.module_name) / spec.script_name
    start = perf_counter()
    completed = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(runtime_root(base_dir).parent),
        capture_output=True,
        text=True,
        check=False,
    )
    duration = perf_counter() - start
    combined_output = completed.stdout.strip()
    if completed.stderr.strip():
        combined_output = f"{combined_output}\n{completed.stderr.strip()}".strip()

    payload = parse_phase1_task_output(completed.stdout)
    verified, verification = verify_phase1_task_payload(spec, payload)
    status = "passed" if completed.returncode == 0 and verified else "failed"

    return Phase1TaskRunResult(
        module_name=spec.module_name,
        task_id=spec.task_id,
        title=spec.title,
        status=status,
        returncode=completed.returncode,
        verification=verification,
        duration_seconds=round(duration, 4),
        output=combined_output or "(no output)",
        artifact_path=payload.get("artifact_path"),
        details=payload.get("details", {}),
    )


def save_phase1_run(base_dir: Path | str, results: list[Phase1TaskRunResult]) -> dict[str, Any]:
    """Persist the latest Phase1 run status and append task logs."""
    existing = read_json_file(phase1_status_path(base_dir))
    passed_tasks = sum(1 for result in results if result.status == "passed")
    failed_tasks = len(results) - passed_tasks
    status = {
        "phase": "Phase1",
        "generated_at": existing.get("generated_at") if existing else utc_now(),
        "last_run_at": utc_now(),
        "overall_status": "passed" if failed_tasks == 0 else "failed",
        "ai_enabled": bool(existing.get("ai_enabled", False)) if existing else False,
        "ai_execution_mode": existing.get("ai_execution_mode", "LocalPythonExecutor") if existing else "LocalPythonExecutor",
        "summary": {
            "total_tasks": len(results),
            "completed_tasks": len(results),
            "passed_tasks": passed_tasks,
            "failed_tasks": failed_tasks,
        },
        "project_state": collect_project_state(),
        "tasks": [
            {
                "module_name": result.module_name,
                "task_id": result.task_id,
                "title": result.title,
                "status": result.status,
                "returncode": result.returncode,
                "duration_seconds": result.duration_seconds,
                "verification": result.verification,
                "artifact_path": result.artifact_path,
                "details": result.details,
                "output": result.output,
                "use_ai": False,
            }
            for result in results
        ],
    }

    write_json_file(phase1_status_path(base_dir), status)
    for result in results:
        append_json_line(
            execution_log_path(base_dir),
            {
                "timestamp": utc_now(),
                "phase": "Phase1",
                "event": "phase1_task_run",
                "module_name": result.module_name,
                "task_id": result.task_id,
                "status": result.status,
                "returncode": result.returncode,
                "duration_seconds": result.duration_seconds,
                "verification": result.verification,
                "artifact_path": result.artifact_path,
            },
        )
    append_json_line(
        execution_log_path(base_dir),
        {
            "timestamp": utc_now(),
            "phase": "Phase1",
            "event": "phase1_run_complete",
            "overall_status": status["overall_status"],
            "summary": status["summary"],
        },
    )
    return status


def print_phase1_report(status: dict[str, Any]) -> None:
    """Print a compact Phase1 execution report."""
    summary = status["summary"]
    print(f"{APP_NAME} Phase1 report")
    print(f"- Overall status: {status['overall_status']}")
    print(f"- Last run at: {status['last_run_at']}")
    print(f"- AI enabled: {status.get('ai_enabled', False)}")
    print(
        "- Tasks: "
        f"{summary['completed_tasks']}/{summary['total_tasks']} completed, "
        f"{summary['passed_tasks']} passed, {summary['failed_tasks']} failed"
    )

    print("\nTask results:")
    for task in status["tasks"]:
        print(
            f"- [{task.get('status', 'unknown').upper()}] {task['task_id']} "
            f"({task['module_name']}): {task.get('verification', 'No verification available.')}"
        )
        print(f"  output: {task.get('output', 'not executed yet')}")
        if task.get("artifact_path"):
            print(f"  artifact: {task['artifact_path']}")


def iter_validation_results() -> Iterable[ValidationResult]:
    """Validate that all package modules import correctly and remain documented."""
    for module_name, description in PHASE1_MODULE_MAP:
        module = import_module(f"{PACKAGE_NAME}.{module_name}")
        docstring = (module.__doc__ or "").strip()
        ok = bool(docstring)
        detail = docstring.splitlines()[0] if docstring else description
        yield ValidationResult(module_name, ok, detail)


def resolve_goal(
    base_dir: Path | str,
    goal_text: str | None,
    project_dir: str | Path,
    *,
    phase: str,
    enable_ai: bool = False,
    ai_provider: str | None = None,
) -> ProjectGoal:
    """Load an existing goal or create a new one for the requested phase."""
    ensure_runtime_tree(base_dir)
    existing = read_json_file(goal_path(base_dir))
    default_goal = {
        "Phase2": DEFAULT_PHASE2_GOAL,
        "Phase3": DEFAULT_PHASE3_GOAL,
        "Phase4": DEFAULT_PHASE4_GOAL,
        "Phase5": DEFAULT_PHASE5_GOAL,
    }.get(phase, DEFAULT_PHASE2_GOAL)
    priority = {
        "Phase2": "medium",
        "Phase3": "high",
        "Phase4": "critical",
        "Phase5": "critical",
    }.get(phase, "medium")
    enable_memory = phase in {"Phase3", "Phase4", "Phase5"}

    if goal_text:
        goal = build_project_goal(
            goal_text,
            project_dir,
            phase=phase,
            priority=priority,
            enable_ai=enable_ai,
            ai_provider=ai_provider,
            enable_memory=enable_memory,
            state_dir=state_dir(base_dir),
        )
    elif existing and existing.get("phase") == phase:
        goal = ProjectGoal.from_dict(existing)
        requested_provider = ai_provider or ("local_placeholder" if enable_ai else "disabled")
        if (
            goal.use_ai != enable_ai
            or goal.ai_provider != requested_provider
            or Path(goal.target_project_dir).resolve() != Path(project_dir).resolve()
        ):
            goal = build_project_goal(
                goal.raw_goal,
                project_dir,
                phase=phase,
                priority=priority,
                enable_ai=enable_ai,
                ai_provider=ai_provider,
                enable_memory=enable_memory,
                state_dir=state_dir(base_dir),
            )
    else:
        goal = build_project_goal(
            default_goal,
            project_dir,
            phase=phase,
            priority=priority,
            enable_ai=enable_ai,
            ai_provider=ai_provider,
            enable_memory=enable_memory,
            state_dir=state_dir(base_dir),
        )

    write_json_file(goal_path(base_dir), goal.to_dict())
    append_json_line(
        execution_log_path(base_dir),
        {
            "timestamp": utc_now(),
            "phase": phase,
            "event": "goal_resolved",
            "goal_id": goal.goal_id,
            "target_project_dir": goal.target_project_dir,
            "memory_enabled": goal.memory_enabled,
            "goal_version": goal.goal_version,
            "use_ai": goal.use_ai,
            "ai_provider": goal.ai_provider,
        },
    )
    return goal


def save_plan(base_dir: Path | str, goal: ProjectGoal, tasks: list[PlannedTask], *, phase: str) -> dict[str, Any]:
    """Persist the generated task plan."""
    payload = build_plan_payload(goal, tasks, phase=phase)
    write_json_file(plan_path(base_dir), payload)
    append_json_line(
        execution_log_path(base_dir),
        {
            "timestamp": utc_now(),
            "phase": phase,
            "event": "plan_generated",
            "goal_id": goal.goal_id,
            "task_count": len(tasks),
            "parallel_task_count": payload.get("parallel_task_count", 0),
            "ai_task_count": payload.get("ai_task_count", 0),
            "use_ai": goal.use_ai,
        },
    )
    return payload


def build_execution_context(
    base_dir: Path | str,
    goal: ProjectGoal,
    loop_state: LoopState,
    task_records: list[dict[str, Any]],
    *,
    phase: str,
    enable_ai: bool,
    memory_state: dict[str, Any] | None,
    task_history: dict[str, Any] | None,
    plan_payload: dict[str, Any],
) -> ExecutionContext:
    """Create the runtime execution context for one workflow batch."""
    prior_results = [record["result"] for record in task_records]
    return ExecutionContext(
        base_dir=str(Path(base_dir).resolve()),
        runtime_root=str(runtime_root(base_dir)),
        target_project_dir=goal.target_project_dir,
        goal_id=goal.goal_id,
        goal_text=goal.normalized_goal,
        phase=phase,
        iteration=loop_state.iteration + 1,
        run_id=f"{goal.goal_id}-iter-{loop_state.iteration + 1}",
        state_dir=str(state_dir(base_dir)),
        logs_dir=str(logs_dir(base_dir)),
        artifacts_dir=str(artifacts_dir(base_dir)),
        goal_version=goal.goal_version,
        goal_payload=goal.to_dict(),
        enable_ai=enable_ai,
        ai_provider=goal.ai_provider,
        ai_provider_config=load_ai_provider_config(goal.ai_provider).to_dict(),
        prior_results=prior_results,
        memory_state=memory_state or {},
        task_history=task_history or {},
        plan_summary=plan_payload,
        ai_execution_state=load_ai_execution_state(base_dir),
        max_parallel_tasks=int(plan_payload.get("max_parallel_tasks", 2)),
    )


def print_goal_summary(goal: ProjectGoal) -> None:
    """Print a compact goal summary."""
    print(f"{goal.phase} goal")
    print(f"- Goal ID: {goal.goal_id}")
    print(f"- Goal version: {goal.goal_version}")
    print(f"- Parent goal: {goal.parent_goal_id or 'none'}")
    print(f"- Raw goal: {goal.raw_goal}")
    print(f"- Target project dir: {goal.target_project_dir}")
    print(f"- Priority: {goal.priority}")
    print(f"- AI enabled: {goal.use_ai}")
    print(f"- AI provider: {goal.ai_provider}")
    print(f"- Memory enabled: {goal.memory_enabled}")
    print(f"- Success criteria: {len(goal.success_criteria)}")


def print_task_plan(goal: ProjectGoal, tasks: list[PlannedTask], memory_state: dict[str, Any] | None = None) -> None:
    """Print the workflow task plan."""
    print_goal_summary(goal)
    print(f"\n{goal.phase} plan")
    for task in tasks:
        print(
            f"- [{task.order}] {task.task_id} ({task.module_name}, {task.executor_type}, "
            f"{task.execution_mode}): {task.title}"
        )
        print(f"  use_ai: {task.use_ai}")
        if task.parallel_group:
            print(f"  parallel_group: {task.parallel_group}")
        if task.depends_on:
            print(f"  depends_on: {', '.join(task.depends_on)}")
        if task.callback_channel:
            print(f"  callback_channel: {task.callback_channel}")
        print(f"  description: {task.description}")
        print(f"  expected: {task.expected_output}")
        print(f"  prompt: {render_task_prompt(task, goal, memory_state)}")


def print_workflow_report(report: dict[str, Any]) -> None:
    """Print the latest workflow final report."""
    def shorten(text: str, limit: int = 600) -> str:
        cleaned = " ".join(text.split())
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 3] + "..."

    phase = report.get("phase", "Workflow")
    summary = report.get("summary", {})
    print(f"{APP_NAME} {phase} report")
    print(f"- Overall status: {summary.get('overall_status', 'unknown')}")
    print(f"- Generated at: {report.get('generated_at', 'unknown')}")
    print(
        "- Tasks: "
        f"{summary.get('task_count', 0)} total, "
        f"{summary.get('passed_tasks', 0)} passed, "
        f"{summary.get('failed_tasks', 0)} failed, "
        f"{summary.get('retryable_tasks', 0)} retryable"
    )
    print(f"- AI enabled: {summary.get('goal_use_ai', False)}")
    print(f"- AI-capable tasks: {summary.get('ai_task_count', 0)}")
    print(f"- AIExecutor runs: {summary.get('ai_executed_task_count', 0)}")
    print(f"- Human intervention required: {summary.get('human_intervention_required', False)}")
    print(f"- Total duration (s): {summary.get('total_duration_seconds', 0.0)}")
    print(f"- Average confidence: {summary.get('average_confidence_score', 0.0)}")

    memory_state = report.get("memory_state") or {}
    if memory_state:
        print(f"- Memory goals: {memory_state.get('goal_count', 0)}")
        print(f"- Memory vectors: {memory_state.get('vector_count', 0)}")
        if memory_state.get("retrieved_goal_count") is not None:
            print(f"- Memory matches: {memory_state.get('retrieved_goal_count', 0)}")

    statistics = report.get("statistics") or {}
    if statistics:
        print(f"- Completed batches: {statistics.get('completed_batches', 0)}")
        print(f"- Parallel task count: {statistics.get('parallel_task_count', 0)}")
        print(f"- Provider breakdown: {statistics.get('provider_breakdown', {})}")
        print(f"- Task profiles: {statistics.get('task_profile_count', 0)}")
        print(f"- Workflow runs: {statistics.get('workflow_run_count', 0)}")

    print("\nTask records:")
    for record in report.get("tasks", []):
        task = record.get("task", {})
        result = record.get("result", {})
        analysis = record.get("analysis", {})
        print(
            f"- [{analysis.get('status', 'unknown').upper()}] {task.get('task_id', 'unknown')} "
            f"({task.get('module_name', 'unknown')} / planned={task.get('executor_type', 'unknown')} / "
            f"actual={result.get('executor_type', 'unknown')})"
        )
        print(f"  summary: {analysis.get('summary', 'No summary available.')}")
        print(f"  duration_seconds: {result.get('duration_seconds', 0.0)}")
        print(f"  output: {shorten(result.get('output_text', 'No output available.'))}")
        if result.get("artifact_path"):
            print(f"  artifact: {result['artifact_path']}")


def print_memory_status(memory_status: dict[str, Any]) -> None:
    """Print the stored memory placeholder state."""
    print("Workflow memory status")
    print(f"- Updated at: {memory_status.get('updated_at')}")
    print(f"- Stored goals: {memory_status.get('goal_count', 0)}")
    print(f"- Vector placeholders: {memory_status.get('vector_count', 0)}")
    print(f"- Phase breakdown: {memory_status.get('phase_breakdown', {})}")
    print(f"- Complexity breakdown: {memory_status.get('complexity_breakdown', {})}")
    print(f"- Goal relationships: {memory_status.get('relationship_count', 0)}")
    print(f"- AI-enabled goals: {memory_status.get('ai_goal_count', 0)}")
    print(f"- AI provider breakdown: {memory_status.get('ai_provider_breakdown', {})}")
    print(f"- Task profiles: {memory_status.get('task_profile_count', 0)}")
    print(f"- Workflow runs: {memory_status.get('workflow_run_count', 0)}")
    print(f"- Retrieved matches: {memory_status.get('retrieved_goal_count', 0)}")
    print("\nRecent goals:")
    recent_goals = memory_status.get("recent_goals", [])
    if not recent_goals:
        print("- none")
    for entry in recent_goals:
        print(
            f"- {entry.get('goal_id')} [{entry.get('phase')}] "
            f"v{entry.get('goal_version', 1)} {entry.get('priority')} -> {entry.get('normalized_goal')}"
        )


def print_status_overview(base_dir: Path | str) -> None:
    """Print the current module map plus the latest Phase1 to Phase5 runtime state."""
    print(format_module_map())
    print("\nScope:")
    print("- Phase1 runs safe placeholder tasks and stores structured status/log files.")
    print("- Phase2 runs a minimal local closed-loop with planning, execution, analysis, and loop control.")
    print("- Phase3 adds memory placeholders, priority scheduling, batched parallel tasks, and Codex/GPT placeholders.")
    print("- Phase4 adds versioned goals, richer task trees, callback-aware execution, and review packaging.")
    print("- Phase5 adds local task history, heuristic planning, self-optimization, and richer dashboard analytics.")
    print("- Streamlit visualizes goals, plans, reports, memory, task history, and historical runtime artifacts.")

    print(f"\nRuntime root: {runtime_root(base_dir)}")

    phase1_manifest = read_json_file(phase1_manifest_path(base_dir))
    phase1_status = read_json_file(phase1_status_path(base_dir))
    current_goal = read_json_file(goal_path(base_dir))
    current_plan = read_json_file(plan_path(base_dir))
    current_report = read_json_file(final_report_path(base_dir))
    current_loop_state = read_json_file(loop_state_path(base_dir))
    current_memory = load_memory_status(state_dir(base_dir))
    current_task_history = load_task_history(state_dir(base_dir))
    current_workflow_history = load_workflow_history(state_dir(base_dir))
    current_ai_state = load_ai_execution_state(base_dir)

    print("\nPhase1 status:")
    if phase1_manifest:
        print(f"- Planned tasks: {len(phase1_manifest.get('tasks', []))}")
    else:
        print("- Planned tasks: not initialized")
    if phase1_status:
        print(f"- Overall status: {phase1_status.get('overall_status', 'unknown')}")
        print(f"- Last run: {phase1_status.get('last_run_at', 'unknown')}")
        print(f"- AI enabled: {phase1_status.get('ai_enabled', False)}")
    else:
        print("- Overall status: no Phase1 run recorded")

    print("\nWorkflow status (latest Phase2/Phase5 run):")
    if current_goal:
        print(f"- Goal phase: {current_goal.get('phase', 'unknown')}")
        print(f"- Goal version: {current_goal.get('goal_version', 1)}")
        print(f"- Goal: {current_goal.get('normalized_goal', current_goal.get('raw_goal', 'unknown'))}")
        print(f"- Target dir: {current_goal.get('target_project_dir', 'unknown')}")
        print(f"- Goal use_ai: {current_goal.get('use_ai', False)}")
        print(f"- AI provider: {current_goal.get('ai_provider', 'disabled')}")
    else:
        print("- Goal: not set")
    if current_plan:
        print(f"- Planned tasks: {current_plan.get('task_count', 0)}")
        print(f"- Parallel tasks: {current_plan.get('parallel_task_count', 0)}")
        print(f"- AI tasks: {current_plan.get('ai_task_count', 0)}")
    else:
        print("- Planned tasks: not generated")
    if current_loop_state:
        print(f"- Loop state: {current_loop_state.get('overall_status', 'unknown')}")
        print(f"- Next action: {current_loop_state.get('next_action', 'unknown')}")
    else:
        print("- Loop state: not initialized")
    if current_report:
        print(f"- Final report phase: {current_report.get('phase', 'unknown')}")
        print(f"- Final report status: {current_report.get('summary', {}).get('overall_status', 'unknown')}")
        print(f"- Final report generated at: {current_report.get('generated_at', 'unknown')}")
    else:
        print("- Final report: not available")

    print("\nMemory status:")
    print(f"- Stored goals: {current_memory.get('goal_count', 0)}")
    print(f"- Vector placeholders: {current_memory.get('vector_count', 0)}")
    print(f"- AI-enabled goals: {current_memory.get('ai_goal_count', 0)}")
    print(f"- Phase breakdown: {current_memory.get('phase_breakdown', {})}")
    print(f"- Task profiles: {current_task_history.get('task_profile_count', 0)}")
    print(f"- Workflow runs: {current_workflow_history.get('run_count', 0)}")
    print("\nAI execution state:")
    print(f"- Enabled: {current_ai_state.get('enabled', False)}")
    print(f"- Provider: {current_ai_state.get('ai_provider', 'disabled')}")
    print(f"- Goal use_ai: {current_ai_state.get('goal_use_ai', False)}")
    print(f"- AI tasks in latest plan: {current_ai_state.get('ai_task_count', 0)}")
    print(f"- AIExecutor runs in latest workflow: {current_ai_state.get('actual_ai_executor_runs', 0)}")
    print(f"- Provider status: {current_ai_state.get('provider_status', {})}")


def run_phase1(base_dir: Path | str, *, enable_ai: bool = False, ai_provider: str | None = None) -> int:
    """Run the full safe Phase1 task set without adding later-phase behavior."""
    created = initialize_phase1_tree(base_dir)
    root = runtime_root(base_dir)
    write_task_scripts(base_dir)
    initialize_phase1_status(base_dir, enable_ai=enable_ai)
    persist_ai_execution_state(base_dir, phase="Phase1", enabled=enable_ai, tasks=[], ai_provider=ai_provider)

    validation_results = list(iter_validation_results())
    if not all(result.ok for result in validation_results):
        print(f"{APP_NAME} Phase1 validation")
        print(f"Runtime tree: {root}")
        print("Validation failed before task execution.")
        for result in validation_results:
            status = "OK" if result.ok else "FAILED"
            print(f"- [{status}] {result.name}: {result.detail}")
        return 1

    task_results = [
        run_phase1_task_script(base_dir, index, spec)
        for index, spec in enumerate(build_task_specs(), start=1)
    ]
    status = save_phase1_run(base_dir, task_results)

    print(f"{APP_NAME} Phase1 execution")
    print(f"Runtime tree: {root}")
    if created:
        print(f"Initialized {len(created)} runtime directories.")
    else:
        print("Runtime tree already existed; reusing existing directories.")

    print("\nProject state:")
    project_state = status["project_state"]
    print(
        f"- Package: {project_state['package_name']} v{project_state['version']} "
        f"with {project_state['module_count']} modules"
    )

    print("")
    print_phase1_report(status)

    print("\nStatic placeholder notes:")
    for entry in PLACEHOLDER_LOGS:
        print(f"- {entry}")
    if enable_ai:
        print("- AI-Phase1 flag is enabled, but Phase1 static task scripts remain local and read-only.")

    return 0 if status["overall_status"] == "passed" else 1


def plan_workflow(
    base_dir: Path | str,
    goal_text: str | None,
    project_dir: str | Path,
    *,
    phase: str,
    enable_ai: bool = False,
    ai_provider: str | None = None,
) -> tuple[ProjectGoal, list[PlannedTask], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Resolve a workflow goal, update local memory, and generate a task plan."""
    ensure_runtime_tree(base_dir)
    goal = resolve_goal(
        base_dir,
        goal_text,
        project_dir,
        phase=phase,
        enable_ai=enable_ai,
        ai_provider=ai_provider,
    )

    memory_state = load_memory_status(state_dir(base_dir))
    if phase in {"Phase3", "Phase4", "Phase5"} and goal.memory_enabled:
        persisted_memory = persist_goal_memory(state_dir(base_dir), goal)
        append_json_line(
            execution_log_path(base_dir),
            {
                "timestamp": utc_now(),
                "phase": phase,
                "event": "memory_updated",
                "goal_id": goal.goal_id,
                "goal_version": goal.goal_version,
                "goal_count": persisted_memory.get("memory_store", {}).get("goal_count", 0),
                "vector_count": persisted_memory.get("vector_store_placeholder", {}).get("vector_count", 0),
            },
        )
        memory_state = load_memory_status(state_dir(base_dir))
        if phase in {"Phase4", "Phase5"}:
            memory_state = retrieve_memory_context(state_dir(base_dir), goal, limit=8)
            append_json_line(
                execution_log_path(base_dir),
                {
                    "timestamp": utc_now(),
                    "phase": phase,
                    "event": "memory_retrieved",
                    "goal_id": goal.goal_id,
                    "retrieved_goal_count": memory_state.get("retrieved_goal_count", 0),
                    "top_match_goal_id": memory_state.get("top_match_goal_id"),
                },
            )

    task_history = load_task_history(state_dir(base_dir))
    memory_state = {
        **memory_state,
        "task_profile_count": task_history.get("task_profile_count", 0),
        "goal_use_ai": goal.use_ai,
    }
    tasks = generate_task_plan(goal, phase=phase, task_history=task_history)
    memory_state["ai_task_count"] = sum(1 for task in tasks if task.use_ai)
    payload = save_plan(base_dir, goal, tasks, phase=phase)
    persist_ai_execution_state(base_dir, phase=phase, enabled=enable_ai, goal=goal, tasks=tasks)
    return goal, tasks, payload, memory_state, task_history


def run_autonomous_phase(
    base_dir: Path | str,
    goal_text: str | None,
    project_dir: str | Path,
    *,
    phase: str,
    enable_ai: bool = False,
    ai_provider: str | None = None,
) -> int:
    """Execute the Phase2, Phase3, Phase4, or Phase5 autonomous workflow."""
    goal, tasks, plan_payload, memory_state, task_history_state = plan_workflow(
        base_dir,
        goal_text,
        project_dir,
        phase=phase,
        enable_ai=enable_ai,
        ai_provider=ai_provider,
    )
    loop_state = initialize_loop_state(goal.goal_id, len(tasks), phase=phase)
    write_json_file(loop_state_path(base_dir), loop_state.to_dict())

    task_records: list[dict[str, Any]] = []

    def log_result_callback(result: WorkflowTaskResult) -> None:
        for callback_event in result.callback_events:
            append_json_line(
                execution_log_path(base_dir),
                {
                    "timestamp": utc_now(),
                    "phase": phase,
                    "event": "executor_callback",
                    "task_id": result.task_id,
                    "executor_type": result.executor_type,
                    "callback": callback_event,
                },
            )

    while True:
        ready_tasks = select_ready_tasks(loop_state, tasks)
        write_json_file(loop_state_path(base_dir), loop_state.to_dict())
        if not ready_tasks:
            break

        attempt_map = {
            task.task_id: loop_state.retry_counts.get(task.task_id, 0) + 1
            for task in ready_tasks
        }
        context = build_execution_context(
            base_dir,
            goal,
            loop_state,
            task_records,
            phase=phase,
            enable_ai=enable_ai,
            memory_state=memory_state,
            task_history=task_history_state,
            plan_payload=plan_payload,
        )
        results = execute_task_batch(ready_tasks, context, attempt_map, result_callback=log_result_callback)
        analyses = [analyze_task_result(task, result, context) for task, result in zip(ready_tasks, results)]

        for task, result, analysis in zip(ready_tasks, results, analyses):
            task_records.append(
                {
                    "task": task.to_dict(),
                    "result": result.to_dict(),
                    "analysis": analysis.to_dict(),
                }
            )
            append_json_line(
                execution_log_path(base_dir),
                {
                    "timestamp": utc_now(),
                    "phase": phase,
                    "event": "task_executed",
                    "task_id": task.task_id,
                    "planned_executor_type": task.executor_type,
                    "actual_executor_type": result.executor_type,
                    "use_ai": task.use_ai,
                    "execution_mode": task.execution_mode,
                    "parallel_group": task.parallel_group,
                    "attempt": result.attempt,
                    "duration_seconds": result.duration_seconds,
                    "analysis_status": analysis.status,
                    "recommended_action": analysis.recommended_action,
                    "artifact_path": result.artifact_path,
                },
            )
            task_history_state = update_task_history(
                state_dir(base_dir),
                goal.to_dict(),
                task,
                result,
                analysis,
            )

        loop_state = apply_batch_to_loop(loop_state, ready_tasks, analyses)
        write_json_file(loop_state_path(base_dir), loop_state.to_dict())

        if loop_state.next_action in {"stop", "human_intervention"}:
            break

    workflow_history_state = load_workflow_history(state_dir(base_dir))
    final_report = build_final_report(
        goal_payload=goal.to_dict(),
        plan_payload=plan_payload,
        loop_state_payload=loop_state.to_dict(),
        task_records=task_records,
        phase=phase,
        memory_state=memory_state,
        task_history_state=task_history_state,
        workflow_history_state=workflow_history_state,
    )
    write_json_file(final_report_path(base_dir), final_report)
    workflow_history_state = update_workflow_history(state_dir(base_dir), final_report)
    final_report = build_final_report(
        goal_payload=goal.to_dict(),
        plan_payload=plan_payload,
        loop_state_payload=loop_state.to_dict(),
        task_records=task_records,
        phase=phase,
        memory_state=memory_state,
        task_history_state=task_history_state,
        workflow_history_state=workflow_history_state,
    )
    write_json_file(final_report_path(base_dir), final_report)
    persist_ai_execution_state(
        base_dir,
        phase=phase,
        enabled=enable_ai,
        goal=goal,
        tasks=tasks,
        actual_ai_executor_runs=sum(
            1 for record in final_report.get("tasks", [])
            if record.get("result", {}).get("executor_type") == "ai_executor"
        ),
    )
    append_json_line(
        execution_log_path(base_dir),
        {
            "timestamp": utc_now(),
            "phase": phase,
            "event": "run_complete",
            "overall_status": final_report["summary"]["overall_status"],
            "task_count": final_report["summary"]["task_count"],
            "ai_enabled": enable_ai,
            "ai_executor_runs": final_report["summary"].get("ai_executed_task_count", 0),
            "human_intervention_required": final_report["summary"]["human_intervention_required"],
        },
    )

    print_goal_summary(goal)
    print("")
    print_workflow_report(final_report)
    return 0 if final_report["summary"]["overall_status"] == "passed" else 1


def show_latest_report(base_dir: Path | str) -> int:
    """Load and print the latest persisted workflow final report."""
    report = read_json_file(final_report_path(base_dir))
    if not report:
        print("Workflow final report not found. Run `--run-phase2`, `--run-phase3`, `--run-phase4`, or `--run-phase5` first.")
        return 1
    print_workflow_report(report)
    return 0


def show_memory_status(base_dir: Path | str) -> int:
    """Load and print the current memory placeholder state."""
    memory_status = {
        **load_memory_status(state_dir(base_dir)),
        "task_profile_count": load_task_history(state_dir(base_dir)).get("task_profile_count", 0),
        "workflow_run_count": load_workflow_history(state_dir(base_dir)).get("run_count", 0),
    }
    print_memory_status(memory_status)
    return 0


def show_memory_query(base_dir: Path | str, query_text: str | None) -> int:
    """Query historical goal, task, and workflow memory using local matching rules."""
    goal_matches = query_goal_memory(state_dir(base_dir), query_text, limit=10)
    task_matches = query_task_history(state_dir(base_dir), query_text, limit=10)
    workflow_matches = query_workflow_history(state_dir(base_dir), query_text, limit=10)

    print("Workflow memory query")
    print(f"- Query: {goal_matches.get('query') or '(recent items)'}")
    print(f"- Goal matches: {goal_matches.get('match_count', 0)}")
    print(f"- Task matches: {task_matches.get('match_count', 0)}")
    print(f"- Workflow matches: {workflow_matches.get('match_count', 0)}")

    print("\nGoal memory:")
    if not goal_matches.get("matches"):
        print("- none")
    for entry in goal_matches.get("matches", []):
        print(
            f"- {entry.get('goal_id')} [{entry.get('phase')}] "
            f"v{entry.get('goal_version', 1)} {entry.get('priority', 'unknown')} -> {entry.get('normalized_goal', '')}"
        )

    print("\nTask memory:")
    if not task_matches.get("matches"):
        print("- none")
    for entry in task_matches.get("matches", []):
        print(
            f"- {entry.get('task_id')} ({entry.get('module_name')}/{entry.get('executor_type')}): "
            f"runs={entry.get('runs', 0)}, success_rate={entry.get('success_rate', 0.0)}, retry_rate={entry.get('retry_rate', 0.0)}"
        )

    print("\nWorkflow history:")
    if not workflow_matches.get("matches"):
        print("- none")
    for entry in workflow_matches.get("matches", []):
        print(
            f"- {entry.get('goal_id')} [{entry.get('phase')}] {entry.get('overall_status')} "
            f"tasks={entry.get('task_count', 0)} duration={entry.get('total_duration_seconds', 0.0)}"
        )
    return 0


def streamlit_base_dir() -> str:
    """Resolve an optional base directory passed through Streamlit script args."""
    argv = sys.argv[1:]
    if "--base-dir" in argv:
        index = argv.index("--base-dir")
        if index + 1 < len(argv):
            return argv[index + 1]
    return "."


def render_streamlit_placeholder() -> None:
    """Render the visualization-oriented Streamlit view for runtime data."""
    import streamlit as st

    base_dir = streamlit_base_dir()
    st.set_page_config(page_title=APP_NAME, layout="wide")
    st.title(APP_NAME)
    st.caption("Phase1 + Phase2 + Phase3 + Phase4 + Phase5 prototype dashboard")
    st.info(
        "This UI visualizes the current local runtime state only. "
        "Interactive controls are limited to browsing historical runtime data and reports."
    )

    st.subheader("Module Map")
    st.table(
        [
            {"Module": module_name, "Role": description}
            for module_name, description in PHASE1_MODULE_MAP
        ]
    )

    phase1_status = read_json_file(phase1_status_path(base_dir))
    phase1_manifest = read_json_file(phase1_manifest_path(base_dir))
    current_goal = read_json_file(goal_path(base_dir))
    current_plan = read_json_file(plan_path(base_dir))
    current_loop_state = read_json_file(loop_state_path(base_dir))
    current_report = read_json_file(final_report_path(base_dir))
    current_memory = {
        **load_memory_status(state_dir(base_dir)),
        "task_profile_count": load_task_history(state_dir(base_dir)).get("task_profile_count", 0),
        "workflow_run_count": load_workflow_history(state_dir(base_dir)).get("run_count", 0),
    }
    current_ai_state = load_ai_execution_state(base_dir)
    current_task_history = load_task_history(state_dir(base_dir))
    current_workflow_history = load_workflow_history(state_dir(base_dir))
    recent_logs = read_recent_logs(base_dir)

    st.subheader("Phase1")
    if phase1_manifest:
        st.write("Task tree")
        st.table(phase1_manifest.get("tasks", []))
    else:
        st.warning("Phase1 task tree has not been initialized yet.")
    if phase1_status:
        st.write("Latest Phase1 status")
        st.json(
            {
                "overall_status": phase1_status.get("overall_status"),
                "last_run_at": phase1_status.get("last_run_at"),
                "ai_enabled": phase1_status.get("ai_enabled", False),
                "ai_execution_mode": phase1_status.get("ai_execution_mode", "LocalPythonExecutor"),
                "summary": phase1_status.get("summary"),
            }
        )
        st.table(phase1_status.get("tasks", []))
    else:
        st.warning("No Phase1 execution status is available yet.")

    st.subheader("Latest Autonomous Workflow")
    if current_goal:
        st.write("Goal")
        st.json(current_goal)
    else:
        st.warning("No Phase2 to Phase5 goal is stored yet.")

    if current_plan:
        st.write("Plan")
        st.table(current_plan.get("tasks", []))
        if current_plan.get("dependency_edges"):
            st.write("Dependency edges")
            st.table(current_plan.get("dependency_edges", []))
    else:
        st.warning("No workflow plan is available yet.")

    if current_loop_state:
        st.write("Loop state")
        st.json(current_loop_state)
    else:
        st.warning("No workflow loop state is available yet.")

    if current_report:
        st.write("Final report")
        st.json(
            {
                "phase": current_report.get("phase"),
                "generated_at": current_report.get("generated_at"),
                "summary": current_report.get("summary"),
                "statistics": current_report.get("statistics"),
                "visualization": current_report.get("visualization"),
            }
        )
        task_records = current_report.get("tasks", [])
        if task_records:
            task_options = [record.get("task", {}).get("task_id", "unknown") for record in task_records]
            selected_task_id = st.selectbox("View latest task record", task_options, key="latest-task-record")
            selected_task_record = next(
                (
                    record
                    for record in task_records
                    if record.get("task", {}).get("task_id") == selected_task_id
                ),
                task_records[0],
            )
            st.json(selected_task_record)

            task_status_rows = current_report.get("visualization", {}).get("task_statuses", [])
            if task_status_rows:
                st.write("Task status table")
                st.table(task_status_rows)

            duration_series = current_report.get("visualization", {}).get("duration_series", [])
            if duration_series:
                st.write("Task duration chart")
                st.bar_chart(
                    {
                        row["task_id"]: row.get("duration_seconds", 0.0)
                        for row in duration_series
                    }
                )
            retry_series = current_report.get("visualization", {}).get("retry_series", [])
            if retry_series:
                st.write("Task retry/attempt chart")
                st.bar_chart(
                    {
                        row["task_id"]: row.get("attempt", 1)
                        for row in retry_series
                    }
                )
    else:
        st.warning("No final report is available yet.")

    st.subheader("Memory")
    st.json(current_memory)
    historical_goals = current_memory.get("recent_goals", [])
    if historical_goals:
        goal_labels = [
            f"{entry.get('goal_id')} | {entry.get('phase')} | v{entry.get('goal_version', 1)}"
            for entry in historical_goals
        ]
        selected_goal_label = st.selectbox("View historical goal", goal_labels, key="historical-goal")
        selected_goal_index = goal_labels.index(selected_goal_label)
        st.json(historical_goals[selected_goal_index])
    if current_memory.get("phase_breakdown"):
        st.write("Memory phase breakdown")
        st.bar_chart(current_memory.get("phase_breakdown", {}))
    if current_memory.get("complexity_breakdown"):
        st.write("Memory complexity breakdown")
        st.bar_chart(current_memory.get("complexity_breakdown", {}))

    st.subheader("AI Execution State")
    st.json(current_ai_state)
    if current_report and current_report.get("visualization", {}).get("ai_summary"):
        st.write("AI summary")
        st.json(current_report.get("visualization", {}).get("ai_summary"))

    st.subheader("Task History")
    task_profiles = list(current_task_history.get("task_profiles", {}).values())
    if task_profiles:
        st.table(task_profiles)
        task_profile_labels = [
            f"{entry.get('task_id')} | runs={entry.get('runs', 0)}"
            for entry in task_profiles
        ]
        selected_task_profile = st.selectbox("View historical task profile", task_profile_labels, key="historical-task-profile")
        selected_task_profile_index = task_profile_labels.index(selected_task_profile)
        st.json(task_profiles[selected_task_profile_index])
        st.write("Task success rates")
        st.bar_chart(
            {
                entry.get("task_id"): float(entry.get("success_rate", 0.0))
                for entry in task_profiles[:15]
            }
        )
        st.write("Task retry rates")
        st.bar_chart(
            {
                entry.get("task_id"): float(entry.get("retry_rate", 0.0))
                for entry in task_profiles[:15]
            }
        )
    else:
        st.warning("No task history is available yet.")

    st.subheader("Workflow History")
    workflow_runs = current_workflow_history.get("recent_runs", [])
    if workflow_runs:
        st.table(workflow_runs)
        workflow_labels = [
            f"{entry.get('goal_id')} | {entry.get('phase')} | {entry.get('overall_status')}"
            for entry in workflow_runs
        ]
        selected_workflow = st.selectbox("View historical workflow run", workflow_labels, key="historical-workflow")
        selected_workflow_index = workflow_labels.index(selected_workflow)
        st.json(workflow_runs[selected_workflow_index])
    else:
        st.warning("No workflow history is available yet.")

    st.subheader("Usage Metrics")
    st.bar_chart(
        {
            "stored_goals": current_memory.get("goal_count", 0),
            "vector_placeholders": current_memory.get("vector_count", 0),
            "task_profiles": current_task_history.get("task_profile_count", 0),
            "workflow_runs": current_workflow_history.get("run_count", 0),
        }
    )

    st.subheader("Recent logs")
    if recent_logs:
        st.table(recent_logs)
    else:
        for entry in PLACEHOLDER_LOGS:
            st.code(entry, language="text")

    st.subheader("CLI Commands")
    st.markdown(
        "\n".join(
            [
                "- `python -m autonomous_project_development_agent --init`",
                "- `python -m autonomous_project_development_agent --run-phase1`",
                "- `python -m autonomous_project_development_agent --run-phase1 --enable-ai`",
                "- `python -m autonomous_project_development_agent --goal \"Read a local project directory, generate a module list, count Python files, and output a preliminary analysis report.\" --run-phase2`",
                "- `python -m autonomous_project_development_agent --goal \"Read a local project directory, generate a module list, count Python files, and output a preliminary analysis report.\" --run-phase2 --enable-ai`",
                "- `python -m autonomous_project_development_agent --goal \"Inspect a local project, build a reusable module inventory, compute Python file metrics, and generate a safe autonomous implementation suggestion.\" --run-phase3`",
                "- `python -m autonomous_project_development_agent --goal \"Inspect a local project, recover relevant historical context, generate a dependency-aware task tree, prepare safe autonomous implementation suggestions, and produce an iteration review package.\" --run-phase4`",
                "- `python -m autonomous_project_development_agent --goal \"Inspect a local project, reuse historical memory, generate a self-optimizing task tree, execute safe local analysis tasks, and produce a local autonomy review without external AI APIs.\" --run-phase5`",
                "- `python -m autonomous_project_development_agent --memory-status`",
                "- `python -m autonomous_project_development_agent --memory-query --goal \"phase5\"`",
                "- `python -m autonomous_project_development_agent --visualize`",
                "- `python -m autonomous_project_development_agent --report`",
            ]
        )
    )


def launch_visualization(base_dir: Path | str) -> int:
    """Launch the Streamlit dashboard for the current runtime base directory."""
    try:
        import streamlit  # noqa: F401
    except Exception as exc:
        print(f"Streamlit is not available in the current Python environment: {exc}")
        return 1

    script_path = Path(__file__).resolve()
    command = [sys.executable, "-m", "streamlit", "run", str(script_path), "--", "--base-dir", str(base_dir)]
    process = subprocess.Popen(
        command,
        cwd=str(Path(base_dir).resolve()),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print("Streamlit dashboard launched.")
    print(f"- PID: {process.pid}")
    print("- URL: http://localhost:8501")
    print(f"- Base dir: {Path(base_dir).resolve()}")
    return 0


def in_streamlit_context() -> bool:
    """Return True when the module is being executed by Streamlit."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except Exception:
        return False

    return get_script_run_ctx() is not None


def cli_main(argv: list[str] | None = None) -> int:
    """Run the command-line interface."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.init:
        created = initialize_phase1_tree(args.base_dir)
        manifest = build_task_manifest(args.base_dir)
        scripts = write_task_scripts(args.base_dir)
        initialize_phase1_status(args.base_dir, enable_ai=args.enable_ai)
        persist_ai_execution_state(
            args.base_dir,
            phase="Phase1",
            enabled=args.enable_ai,
            tasks=[],
            ai_provider=args.ai_provider,
        )
        print(f"Phase1 task tree ready at: {runtime_root(args.base_dir)}")
        if created:
            for path in created:
                print(f"- created {path}")
        else:
            print("- no new directories were needed")
        print(f"- task manifest written: {phase1_manifest_path(args.base_dir)}")
        print(f"- generated {len(manifest['tasks'])} task entries")
        print(f"- generated {len(scripts)} runnable task scripts")
        return 0

    if args.status:
        print_status_overview(args.base_dir)
        return 0

    if args.run_phase1:
        return run_phase1(args.base_dir, enable_ai=args.enable_ai, ai_provider=args.ai_provider)

    if args.plan:
        goal, tasks, _, memory_state, _ = plan_workflow(
            args.base_dir,
            args.goal_text,
            args.project_dir,
            phase="Phase2",
            enable_ai=args.enable_ai,
            ai_provider=args.ai_provider,
        )
        print_task_plan(goal, tasks, memory_state)
        return 0

    if args.run_phase2:
        return run_autonomous_phase(
            args.base_dir,
            args.goal_text,
            args.project_dir,
            phase="Phase2",
            enable_ai=args.enable_ai,
            ai_provider=args.ai_provider,
        )

    if args.run_phase3:
        return run_autonomous_phase(
            args.base_dir,
            args.goal_text,
            args.project_dir,
            phase="Phase3",
            enable_ai=args.enable_ai,
            ai_provider=args.ai_provider,
        )

    if args.run_phase4:
        return run_autonomous_phase(
            args.base_dir,
            args.goal_text,
            args.project_dir,
            phase="Phase4",
            enable_ai=args.enable_ai,
            ai_provider=args.ai_provider,
        )

    if args.run_phase5:
        return run_autonomous_phase(
            args.base_dir,
            args.goal_text,
            args.project_dir,
            phase="Phase5",
            enable_ai=args.enable_ai,
            ai_provider=args.ai_provider,
        )

    if args.report:
        return show_latest_report(args.base_dir)

    if args.memory_status:
        return show_memory_status(args.base_dir)

    if args.memory_query:
        return show_memory_query(args.base_dir, args.goal_text)

    if args.visualize:
        return launch_visualization(args.base_dir)

    if args.goal_text:
        if args.goal_text == DEFAULT_PHASE4_GOAL:
            target_phase = "Phase4"
        elif args.goal_text == DEFAULT_PHASE5_GOAL:
            target_phase = "Phase5"
        elif args.goal_text == DEFAULT_PHASE3_GOAL:
            target_phase = "Phase3"
        else:
            target_phase = "Phase2"
        goal = resolve_goal(
            args.base_dir,
            args.goal_text,
            args.project_dir,
            phase=target_phase,
            enable_ai=args.enable_ai,
            ai_provider=args.ai_provider,
        )
        persist_ai_execution_state(
            args.base_dir,
            phase=target_phase,
            enabled=args.enable_ai,
            goal=goal,
            tasks=[],
            ai_provider=args.ai_provider,
        )
        print_goal_summary(goal)
        print("\nTip: use `--plan`, `--run-phase2`, `--run-phase3`, `--run-phase4`, or `--run-phase5` to continue.")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    if in_streamlit_context():
        render_streamlit_placeholder()
    else:
        raise SystemExit(cli_main())

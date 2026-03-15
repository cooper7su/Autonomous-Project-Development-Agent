"""Package metadata and shared constants for Phase1 to Phase5 plus AI-Phase1."""

APP_NAME = "Autonomous Project Development Agent"
PACKAGE_NAME = "autonomous_project_development_agent"
PHASE1_RUNTIME_DIRNAME = "phase1_runtime"
DEFAULT_PHASE2_GOAL = (
    "Read a local project directory, generate a module list, count Python files, "
    "and output a preliminary analysis report."
)
DEFAULT_PHASE3_GOAL = (
    "Inspect a local project, build a reusable module inventory, compute Python "
    "file metrics, and generate a safe autonomous implementation suggestion."
)
DEFAULT_PHASE4_GOAL = (
    "Inspect a local project, recover relevant historical context, generate a "
    "dependency-aware task tree, prepare safe autonomous implementation "
    "suggestions, and produce an iteration review package."
)
DEFAULT_PHASE5_GOAL = (
    "Inspect a local project, reuse historical memory, generate a self-optimizing "
    "task tree, execute safe local analysis tasks, and produce a local autonomy "
    "review without external AI APIs."
)
__version__ = "0.6.0"

PHASE1_MODULE_MAP = [
    (
        "goal_framework",
        "Capture project goals, constraints, assumptions, and success criteria.",
    ),
    (
        "task_planning",
        "Reserve task decomposition and prompt generation responsibilities.",
    ),
    (
        "executor",
        "Reserve execution routing for Codex, Python tooling, MATLAB, and shell integrations.",
    ),
    (
        "result_analysis",
        "Reserve output inspection, self-checks, and completion assessment.",
    ),
    (
        "loop_control",
        "Reserve iteration control, stop conditions, retries, and escalation rules.",
    ),
]

PLACEHOLDER_LOGS = [
    "Goal framework placeholder loaded: no live goal model is active yet.",
    "Task planning placeholder loaded: no prompt synthesis or task graph exists yet.",
    "Executor placeholder loaded: no Codex, OpenAI, MATLAB, or shell dispatch is active yet.",
    "Result analysis placeholder loaded: no scoring or regression checks are active yet.",
    "Loop control placeholder loaded: no autonomous retry policy is active yet.",
    "AI-Phase1 adds a safe AIExecutor boundary that can be enabled with --enable-ai.",
]

PHASE1_TASK_BLUEPRINTS = [
    (
        "goal_framework",
        "module_verification",
        "Verify Phase1 modules",
        "Import the current Phase1 scaffold modules and confirm their docstrings are present.",
        "module_verification.py",
    ),
    (
        "task_planning",
        "task_tree_snapshot",
        "Snapshot task tree",
        "Capture the generated Phase1 task tree and confirm the planned tasks exist.",
        "task_tree_snapshot.py",
    ),
    (
        "executor",
        "placeholder_execution",
        "Run placeholder executor",
        "Execute a safe placeholder task and persist a small runtime artifact.",
        "placeholder_execution.py",
    ),
    (
        "result_analysis",
        "dummy_data_processing",
        "Process dummy data",
        "Run a small standard-library data processing task and verify the summary.",
        "dummy_data_processing.py",
    ),
    (
        "loop_control",
        "initial_logging",
        "Write initial checkpoint",
        "Verify artifacts from prior tasks and write the initial Phase1 checkpoint.",
        "initial_logging.py",
    ),
]

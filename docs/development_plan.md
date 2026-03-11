# Development Plan

## Phase1: Direct Prototype Foundation

| Task | Description | Responsible Module Or File | Deliverable |
| --- | --- | --- | --- |
| Repository layout | Create the installable Python project skeleton and documentation folders. | `pyproject.toml`, `requirements.txt`, `README.md` | Pip-compatible project foundation |
| CLI entry point | Expose `--init`, `--status`, and `--run-phase1` commands. | `main.py` | Runnable prototype control surface |
| Streamlit placeholder | Show module map and placeholder logs in a lightweight UI. | `main.py` | Read-only prototype dashboard |
| Goal module placeholder | Reserve ownership of objectives, constraints, and success criteria. | `goal_framework.py` | Documented extension point |
| Planning module placeholder | Reserve task decomposition and prompt generation responsibilities. | `task_planning.py` | Documented extension point |
| Executor placeholder | Reserve tool-routing responsibilities for Codex, Python, MATLAB, and shell execution. | `executor.py` | Documented extension point |
| Analysis placeholder | Reserve self-check and output review responsibilities. | `result_analysis.py` | Documented extension point |
| Loop control placeholder | Reserve orchestration, stop conditions, and iteration policy. | `loop_control.py` | Documented extension point |
| Runtime tree initialization | Create a Phase1 runtime directory for logs, state, and task staging. | `main.py --init` | Placeholder workspace tree |

## Phase2: Minimal Closed-Loop Workflow

| Task | Description | Responsible Module | Deliverable |
| --- | --- | --- | --- |
| Goal modeling | Normalize a simple user goal into a structured data object. | `goal_framework.py` | `ProjectGoal` and `goal.json` |
| Sequential planning | Generate 2 to 4 deterministic safe tasks with prompt templates. | `task_planning.py` | `PlannedTask` list and `plan.json` |
| Safe local execution | Run local filesystem inspection tasks and deterministic placeholder-agent summaries. | `executor.py` | `ExecutionContext`, `TaskResult`, artifacts |
| Result analysis | Classify task runs as `passed`, `failed`, or `retryable`. | `result_analysis.py` | `AnalysisReport` records |
| Loop control | Advance, retry, stop, or request human intervention. | `loop_control.py` | `LoopState` and `loop_state.json` |
| Report persistence | Assemble a final structured execution report. | `main.py`, `result_analysis.py` | `final_report.json`, `execution_log.jsonl` |
| Visualization | Display current goal, plan, task states, logs, and report in Streamlit. | `main.py` | Read-only runtime dashboard |

## Phase3: Memory And Batched Autonomous Workflow

| Task | Description | Responsible Module | Deliverable |
| --- | --- | --- | --- |
| Goal memory | Persist goals into a local memory store and vector-store placeholder. | `goal_framework.py` | `memory_store.json`, `vector_store_placeholder.json` |
| Parallel-safe planning | Generate a dependency-aware plan with one batched parallel scan stage. | `task_planning.py` | Parallel-capable `PlannedTask` list |
| Placeholder model execution | Add Codex/GPT-style placeholder executors for safe suggestion generation. | `executor.py` | `codex_placeholder`, `gpt_placeholder` |
| Batched execution | Execute ready tasks in parallel when the plan allows it. | `executor.py`, `main.py` | Safe local parallel execution path |
| Enhanced analysis | Add confidence scores, visualization payloads, and richer verification. | `result_analysis.py` | Extended `AnalysisReport` |
| Priority loop control | Schedule ready tasks by dependency and priority with bounded retries. | `loop_control.py` | Extended `LoopState` |
| Memory and status UI | Display memory, report summaries, and logs in Streamlit. | `main.py` | Read-only Phase3 dashboard |

## Phase4: Managed Autonomous Review Loop

| Task | Description | Responsible Module | Deliverable |
| --- | --- | --- | --- |
| Versioned goals | Track goal version, parent linkage, and richer memory metadata. | `goal_framework.py` | Extended `ProjectGoal`, enriched memory store |
| Memory retrieval | Recover lightweight historical context from local placeholder memory. | `goal_framework.py`, `main.py` | Retrieved memory context in runtime state |
| Task-tree planning | Generate a larger dependency-aware task tree with sequential and parallel stages. | `task_planning.py` | Phase4 `PlannedTask` tree and dependency edges |
| Callback-aware execution | Emit callback events for local and placeholder agent executors. | `executor.py`, `main.py` | Callback logs and richer task artifacts |
| Advanced reporting | Add statistics, duration summaries, and visualization payloads. | `result_analysis.py` | Extended `final_report.json` |
| Managed loop control | Track decision traces, batch execution, retry events, and stop reasons. | `loop_control.py` | Extended `LoopState` |
| Dashboard browsing | Visualize historical goals, task tree details, and latest task records. | `main.py` | Interactive browsing in Streamlit |

## Phase5: Local Autonomy And Self-Optimization

| Task | Description | Responsible Module | Deliverable |
| --- | --- | --- | --- |
| Goal memory enrichment | Extend local goal memory with complexity, parent/child tracking, and query interfaces. | `goal_framework.py` | Richer `memory_store.json` and memory queries |
| Historical task memory | Persist task success, failure, retry, and duration statistics. | `result_analysis.py` | `task_history.json` |
| Workflow history | Record summarized historical runs for later browsing. | `result_analysis.py`, `main.py` | `workflow_history.json` |
| Heuristic task planning | Adjust task priorities and retry budgets using local task history. | `task_planning.py` | Phase5 heuristic task tree |
| Sample local execution | Add deterministic safe Python task execution for Phase5 validation. | `executor.py` | Local sample execution artifact |
| Placeholder local AI tasks | Simulate planning and review tasks without external APIs. | `executor.py` | Local placeholder planning/review artifacts |
| Self-optimization loop | Track retry events, adaptive priorities, and richer scheduling decisions. | `loop_control.py` | Extended `LoopState` statistics |
| Enhanced dashboard | Visualize memory usage, task success rates, retries, and historical runs. | `main.py` | Phase5 dashboard view |

## Completed Milestones

1. Created a clean source layout under `src/`.
2. Made the package installable with editable pip support.
3. Documented the architecture and roadmap.
4. Added Phase1 validation and safe placeholder execution.
5. Implemented a minimal Phase2 closed-loop workflow with structured persistence.
6. Implemented a Phase3 memory-aware workflow with batched task execution and placeholder Codex/GPT routing.
7. Implemented a Phase4 memory-aware review loop with versioned goals, task trees, and richer dashboard reporting.
8. Implemented a Phase5 local-only autonomy workflow with task history, workflow history, heuristic planning, and self-optimization.

## Future Phases

### Phase6: Managed Autonomy And Tool Expansion

- Add richer scoring, self-check heuristics, and regression-style validation.
- Add longer multi-step orchestration flows and policy controls.
- Introduce approval gates, escalation paths, and recovery logic.
- Replace placeholder memory with real retrieval and ranking support.
- Expand executor integrations for MATLAB, notebooks, shell scripts, and other tools.
- Improve the Streamlit app into a lightweight operational console.
- Improve observability, auditability, and deployment readiness.
- Support reuse across multiple project templates and domains.

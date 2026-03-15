# Autonomous Project Development Agent

Autonomous Project Development Agent is a Python-first prototype for an
autonomous project workflow. The repository now includes:

- Phase1: repository scaffolding, placeholder modules, and safe validation tasks
- Phase2: a minimal runnable closed-loop workflow for goal intake, planning,
  local execution, result analysis, loop control, and report persistence
- Phase3: memory placeholders, batched parallel-safe tasks, placeholder
  Codex/GPT execution, and richer autonomous loop state management
- Phase4: versioned goals, memory-aware task trees, callback-aware execution,
  richer analysis, and a review-oriented autonomous reporting loop
- Phase5: local task history, heuristic planning, self-optimization, richer
  memory browsing, and local-only autonomous execution without external AI APIs
- AI-Phase1: a switchable `AIExecutor`, `use_ai` goal/task flags, and AI-aware
  CLI and dashboard state
- AI-Phase2: provider abstraction through local placeholder and OpenAI-ready
  provider interfaces without enabling live network execution

The current implementation remains intentionally conservative:

- only safe local filesystem analysis is performed,
- external agent behavior is simulated by a placeholder executor,
- long-term memory is implemented as a local placeholder store only,
- no multi-agent coordination or production networking is enabled.

## Current Objectives

- Maintain a reusable project structure under `Autonomous-Project-Development-Agent`
- Provide installable Python packaging through `requirements.txt` and `pyproject.toml`
- Expose CLI and Streamlit entry points for Phase1 through Phase5
- Persist goals, plans, loop state, reports, and logs in a structured runtime tree

## Repository Layout

```text
.
|-- README.md
|-- pyproject.toml
|-- requirements.txt
|-- docs/
|   |-- development_plan.md
|   `-- project_overview.md
|-- src/
|   `-- autonomous_project_development_agent/
|       |-- __init__.py
|       |-- __main__.py
|       |-- main.py
|       |-- goal_framework.py
|       |-- task_planning.py
|       |-- executor.py
|       |-- result_analysis.py
|       `-- loop_control.py
`-- tests/
    `-- .gitkeep
```

## Installation

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies using either workflow:

```bash
pip install -r requirements.txt
```

or:

```bash
pip install -e .
```

If you are working in a restricted or offline environment, use:

```bash
pip install -e . --no-build-isolation
```

If editable install fails because `setuptools` is missing in a fresh Python 3.12
environment, install it first:

```bash
pip install setuptools
```

The dependency list is Python-centric for Phase1, but the `executor.py`
boundary is reserved for future integrations with Codex, MATLAB, shell tools,
or other external runtimes.

## CLI Usage

After `pip install -e .`, use either console script:

```bash
apda --status
apda-phase1 --status
```

Equivalent module-based usage:

```bash
python -m autonomous_project_development_agent --status
```

Available commands:

- `--init`: create the placeholder Phase1 runtime task tree in the current directory.
- `--status`: print the module map and current prototype scope.
- `--run-phase1`: validate placeholder imports and print placeholder execution logs.
- `--goal "..."`: persist a simple Phase2 goal.
- `--plan`: generate the Phase2 sequential task list.
- `--run-phase2`: execute the full minimal Phase2 closed-loop workflow.
- `--run-phase3`: execute the Phase3 autonomous workflow with memory and batched task handling.
- `--run-phase4`: execute the Phase4 autonomous workflow with versioned goals, task trees, and review packaging.
- `--run-phase5`: execute the Phase5 autonomous workflow with local memory, heuristic planning, and self-optimization.
- `--memory-status`: show stored goal memory and vector-store placeholder state.
- `--memory-query`: query historical goal, task, and workflow memory using local matching rules.
- `--enable-ai`: route AI-capable tasks through `AIExecutor` using safe local placeholder behavior.
- `--ai-provider`: choose the provider route for `--enable-ai`, such as `local_placeholder` or `openai`.
- `--visualize`: launch the Streamlit dashboard.
- `--report`: show the latest Phase2, Phase3, Phase4, or Phase5 execution report.

Examples:

```bash
python -m autonomous_project_development_agent --init
python -m autonomous_project_development_agent --status
python -m autonomous_project_development_agent --run-phase1
python -m autonomous_project_development_agent --run-phase1 --enable-ai --ai-provider local_placeholder
python -m autonomous_project_development_agent --goal "Read a local project directory, generate a module list, count Python files, and output a preliminary analysis report." --plan
python -m autonomous_project_development_agent --goal "Read a local project directory, generate a module list, count Python files, and output a preliminary analysis report." --run-phase2
python -m autonomous_project_development_agent --goal "Read a local project directory, generate a module list, count Python files, and output a preliminary analysis report." --run-phase2 --enable-ai --ai-provider openai
python -m autonomous_project_development_agent --goal "Inspect a local project, build a reusable module inventory, compute Python file metrics, and generate a safe autonomous implementation suggestion." --run-phase3
python -m autonomous_project_development_agent --goal "Inspect a local project, recover relevant historical context, generate a dependency-aware task tree, prepare safe autonomous implementation suggestions, and produce an iteration review package." --run-phase4
python -m autonomous_project_development_agent --goal "Inspect a local project, reuse historical memory, generate a self-optimizing task tree, execute safe local analysis tasks, and produce a local autonomy review without external AI APIs." --run-phase5
python -m autonomous_project_development_agent --goal "Inspect a local project, reuse historical memory, generate a self-optimizing task tree, execute safe local analysis tasks, and produce a local autonomy review with AI placeholder routing." --run-phase5 --enable-ai --ai-provider local_placeholder
python -m autonomous_project_development_agent --memory-status
python -m autonomous_project_development_agent --memory-query --goal "phase5"
python -m autonomous_project_development_agent --visualize
python -m autonomous_project_development_agent --report
```

## Streamlit Placeholder

Launch the runtime dashboard:

```bash
streamlit run src/autonomous_project_development_agent/main.py
```

The Streamlit view displays:

- module map
- Phase1 task tree and latest Phase1 status
- latest Phase2 to Phase5 goal, plan, loop state, logs, and final report
- AI execution state, provider status, and AI-capable task routing
- memory placeholder state, historical goal browsing, task history, workflow history, and visualization summary payloads

It remains lightweight, but now supports simple browsing interactions for
historical goals, task profiles, workflow runs, and latest task records.

## Runtime Files

When Phase2 through Phase5 runs, the following files are written under `phase1_runtime/state/`:

- `goal.json`
- `plan.json`
- `loop_state.json`
- `final_report.json`
- `memory_store.json`
- `vector_store_placeholder.json`
- `task_history.json`
- `workflow_history.json`

The shared log stream is written to `phase1_runtime/logs/execution_log.jsonl`.

## Documentation

- Overview: [docs/project_overview.md](docs/project_overview.md)
- Development plan: [docs/development_plan.md](docs/development_plan.md)

## GitHub Publish

```bash
git add .
git commit -m "Implement Phase5 local autonomy workflow"
git push -u origin main
```

# AI Branch Development Plan

## Overview

The `codex/AI` branch is the dedicated line of development for adding safe,
observable, and extensible AI-assisted capabilities to the Autonomous Project
Development Agent.

This branch is intentionally separated from the main local-autonomy workflow so
that AI-related planning, execution, memory, and review logic can evolve
without destabilizing the main branch.

The branch goal is not simply to connect an external API. The goal is to build
a full AI-assisted agent loop:

`goal input -> goal modeling -> task generation -> local/AI mixed execution -> result analysis -> retry or stop -> memory update -> visualization`

## Branch Principles

- Keep all AI behavior switchable and observable.
- Preserve safe local execution as the default fallback.
- Avoid hard-coupling the architecture to a single provider.
- Record prompts, outputs, status, and decisions in structured runtime state.
- Add AI features incrementally without breaking existing Phase1-Phase5 flows.

## AI-Phase1: AI Integration Skeleton

### Goal

Introduce AI-ready data structures, execution boundaries, and CLI controls while
keeping all AI behavior local and deterministic.

### Scope

- Add `use_ai` to goal and task models.
- Add safe AI prompt template placeholders.
- Add `AIExecutor` as a non-networked placeholder executor.
- Add `--enable-ai` to the CLI.
- Add AI execution state to runtime status and Streamlit visualization.

### Key Modules

- `src/autonomous_project_development_agent/goal_framework.py`
- `src/autonomous_project_development_agent/task_planning.py`
- `src/autonomous_project_development_agent/executor.py`
- `src/autonomous_project_development_agent/main.py`

### Deliverables

- AI-aware `ProjectGoal` and `PlannedTask`
- `AIExecutor` placeholder
- AI status persistence
- Streamlit placeholder showing AI mode

### Acceptance Criteria

- `--enable-ai` changes execution routing for AI-enabled tasks.
- No external AI API call is made.
- Existing non-AI workflows remain functional.

## AI-Phase2: Provider Abstraction Layer

### Goal

Create a clean provider interface so the project can later support real AI
services without rewriting the execution pipeline.

### Scope

- Add `BaseAIProvider` abstraction.
- Add `MockAIProvider` and `OpenAIProvider` placeholders.
- Standardize prompt request and response structures.
- Read provider configuration from environment variables.
- Add timeout, retry, and response logging boundaries.

### Deliverables

- Provider abstraction layer
- Mock and real-provider interfaces
- Standardized AI request/response objects

### Acceptance Criteria

- The executor can switch providers without changing task structures.
- Failures can fall back to local safe execution.
- Responses and errors are persisted for later analysis.

## AI-Phase3: AI-Assisted Task Planning

### Goal

Allow AI to participate in goal decomposition and task generation while
retaining deterministic local planning as a fallback.

### Scope

- Extend planning from fixed templates to structured AI-assisted planning.
- Support sequential and parallel tasks.
- Add task priority, dependency, and risk metadata.
- Persist planning rationale and prompt previews.

### Deliverables

- AI-assisted planning mode
- Richer task tree representation
- Stored planning prompts and plan rationale

### Acceptance Criteria

- A simple goal can produce a structured 3-8 task plan.
- The system can fall back to local rule-based planning.
- Plans are persisted in a reusable structured format.

## AI-Phase4: AI-Assisted Code Generation and Patch Proposals

### Goal

Use AI to propose code, edits, or patches while keeping verification local and
safe.

### Scope

- Add AI task types for code generation and code modification.
- Produce candidate patches or file drafts instead of uncontrolled direct edits.
- Run local syntax checks, tests, and verification after generation.
- Keep human review points for higher-risk changes.

### Deliverables

- Patch proposal workflow
- Local validation after AI generation
- Structured review artifacts and change summaries

### Acceptance Criteria

- The system can generate a candidate code change safely.
- Validation runs automatically after generation.
- Failing outputs are rejected or flagged for intervention.

## AI-Phase5: Memory and Self-Optimization

### Goal

Use historical outcomes to improve planning, task routing, and retry behavior.

### Scope

- Expand memory to include prompts, task results, and failure reasons.
- Add simple retrieval and ranking for similar goals or tasks.
- Track per-task and per-template success rates.
- Adjust scheduling and retry limits using local heuristics.

### Deliverables

- Richer memory records
- Queryable goal/task history
- Basic self-optimization heuristics

### Acceptance Criteria

- The system can retrieve prior related runs.
- Planning and execution decisions can use past results.
- Retry and scheduling behavior improves based on recorded history.

## AI-Phase6: Full AI Branch Workflow

### Goal

Deliver a complete AI-assisted branch that can be demonstrated end-to-end
through CLI and Streamlit.

### Scope

- Strengthen loop control with retry, stop, and human intervention rules.
- Improve multi-task orchestration and batch execution.
- Visualize prompts, task tree, execution state, memory, diffs, and reports.
- Add better packaging, tests, and developer documentation.

### Deliverables

- End-to-end AI-assisted workflow
- Better dashboard and reporting
- Developer-ready packaging and documentation

### Acceptance Criteria

- A user can provide a goal and observe the full workflow from planning through
  execution, analysis, memory update, and reporting.
- AI-generated outputs are validated locally before acceptance.
- The dashboard exposes enough information for debugging and human oversight.

## Module Responsibilities

### `goal_framework.py`

- Goal normalization
- AI execution flags
- Memory entry creation
- Goal metadata, versions, and dependencies

### `task_planning.py`

- Task tree generation
- Priority and dependency assignment
- Prompt template rendering
- Local and AI-assisted planning modes

### `executor.py`

- Local executor
- AI executor
- Provider abstraction
- Patch proposal and execution routing

### `result_analysis.py`

- Task scoring
- Failure classification
- Retryability analysis
- Visualization-ready summary data

### `loop_control.py`

- Scheduling
- Retry policy
- Stop conditions
- Human intervention triggers

### `main.py`

- CLI entry points
- Workflow orchestration
- Runtime state persistence
- Streamlit integration

## Runtime and Data Evolution

The AI branch should continue to use structured runtime state so each phase can
build on the previous one.

Expected runtime artifacts include:

- `goal.json`
- `plan.json`
- `loop_state.json`
- `final_report.json`
- `memory_store.json`
- `vector_store_placeholder.json`
- `execution_log.jsonl`
- prompt and patch artifacts under `phase1_runtime/artifacts/`

## Risks

- Tight coupling between executor logic and a single AI provider
- Uncontrolled AI output without verification
- Prompt and result storage becoming inconsistent across phases
- Regressions to existing non-AI workflows
- Poor observability when AI behavior fails silently

## Mitigations

- Keep provider boundaries explicit
- Maintain a local fallback for all AI-enabled flows
- Persist every major decision and result in structured files
- Add regression checks for existing Phase1-Phase5 commands
- Treat AI-generated code as candidate output until verified

## Recommended Implementation Order

1. Complete AI-Phase1 in the live codebase.
2. Add provider abstraction in AI-Phase2.
3. Extend planning in AI-Phase3.
4. Add code generation and validation in AI-Phase4.
5. Add memory-driven optimization in AI-Phase5.
6. Consolidate the full workflow and developer experience in AI-Phase6.

## Final Target State

The final AI branch should behave as a controlled AI-assisted development
workflow:

- A user submits a project goal.
- The system retrieves relevant memory and builds a task tree.
- Tasks are routed between local execution and AI-assisted execution.
- Generated outputs are validated locally.
- The loop decides whether to continue, retry, stop, or request human input.
- Results, prompts, reports, and memory updates are persisted automatically.
- CLI and Streamlit provide a full view of the workflow state.

At that point, the AI branch becomes a serious experimental platform for
AI-assisted project development rather than a simple executor placeholder.

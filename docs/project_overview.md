# Project Overview

## Introduction

The Autonomous Project Development Agent is intended to become a structured
software-development loop that can interpret high-level goals, create plans,
delegate implementation tasks to coding tools, assess results, and decide on
the next iteration. The long-term goal is not just code generation, but
project-level orchestration with explicit checkpoints and review stages.

## Phase1 Objectives

Phase1 establishes the minimum professional foundation for that system:

- an installable Python package,
- clear module boundaries for orchestration responsibilities,
- a CLI for basic prototype interaction,
- a Streamlit placeholder for lightweight inspection,
- documentation that describes scope and future direction.

## Phase2 Objectives

Phase2 adds the first minimal runnable closed loop:

- accept one simple project goal,
- generate a short sequential task plan,
- execute safe local tasks plus one placeholder-agent summary step,
- analyze each task result and persist loop state,
- produce a structured final report for CLI and Streamlit display.

## Phase3 Objectives

Phase3 extends the prototype with a slightly more autonomous orchestration layer:

- store goals in a local long-term memory placeholder,
- support dependency-aware planning with a small parallel task batch,
- add placeholder Codex/GPT execution pathways,
- enrich analysis outputs with confidence and visualization payloads,
- improve loop control with priority and retry-aware scheduling.

## Phase4 Objectives

Phase4 expands the prototype into a richer managed-autonomy loop:

- store versioned goals in the local memory placeholder,
- retrieve lightweight historical context for current planning,
- generate a larger task tree with sequential and parallel stages,
- add callback-aware placeholder Codex/GPT execution,
- produce richer reports, statistics, and dashboard visualization data,
- keep the workflow safe, local, and non-mutating.

## Phase5 Objectives

Phase5 adds a local-only autonomy layer with historical learning:

- persist goals with versioning and parent/child tracking in local memory,
- maintain task execution history and workflow history for later reuse,
- generate multi-task trees using deterministic rules and templates,
- support local self-optimization through task-priority and retry heuristics,
- enhance the dashboard with memory, success-rate, retry, and history views,
- keep the entire workflow local and free of external AI API calls.

## High-Level Architecture

### Goal Framework

Owns the project objective, constraints, assumptions, acceptance criteria,
and the structured context that downstream modules should consume.

### Task Planning

Will eventually transform the goal into an execution plan, prompt payloads,
task sequencing rules for coding agents or other backends. In Phase4 it now
builds a lightweight dependency-aware task tree with parallel scan batches.
Phase5 further adjusts priorities and retry budgets using local historical
task outcomes.

### Executor

Acts as the integration boundary for safe local Python execution in Phase2,
Phase3 placeholder Codex/GPT execution, and Phase4 callback-aware suggestion
and review packaging. Phase5 adds local-only sample execution and more
deterministic placeholder AI-style tasks. It remains the future attachment
point for real Codex, OpenAI APIs, shell tools, MATLAB workflows, notebooks,
and other implementation channels.

### Result Analysis

Will compare outputs against the original objective, run self-checks, and
produce a verdict that informs the next iteration.

### Loop Control

Owns iteration budgets, stop conditions, retries, and future human-approval
checkpoints. Phase4 also tracks decisions, batch execution, and review state
for the dashboard. Phase5 adds local heuristic scheduling signals and richer
retry statistics.

## What The Current Prototype Deliberately Does Not Include

- no real multi-agent orchestration,
- no live external API execution,
- no real vector retrieval beyond a placeholder embedding store,
- no production-grade UI or networking,
- no MATLAB execution logic beyond a documented future integration point.

## Definition Of Done

The current prototype is useful when a contributor can install the package
locally, run the CLI, launch the Streamlit placeholder, execute the minimal
Phase2 to Phase5 loops, inspect stored memory and reports, and identify where
future Phase6 capabilities should be added.

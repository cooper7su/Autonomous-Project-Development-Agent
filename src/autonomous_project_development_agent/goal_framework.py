"""Goal modeling and local memory helpers for the Phase2 to Phase5 workflows.

Phase5 extends the earlier scaffold with:
- richer local memory management,
- goal versioning plus parent/child tracking,
- lightweight complexity assessment,
- local memory querying for historical goal retrieval.
- AI-Phase1 adds goal-level AI flags and prompt-template placeholders.

Future phases can replace these deterministic placeholders with stronger
retrieval, clustering, policy-aware ranking, and cross-project memory sharing.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


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

PRIORITY_SCORES = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def utc_now() -> str:
    """Return an ISO 8601 timestamp in UTC."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _goal_slug(goal_text: str) -> str:
    """Build a filesystem-safe slug from free-form goal text."""
    slug = "".join(character.lower() if character.isalnum() else "-" for character in goal_text)
    collapsed = "-".join(part for part in slug.split("-") if part)
    return collapsed[:24] or "autonomous-goal"


def _tokenize(text: str) -> set[str]:
    """Tokenize a text snippet for lightweight local similarity checks."""
    cleaned = "".join(character.lower() if character.isalnum() else " " for character in text)
    return {token for token in cleaned.split() if len(token) >= 3}


def infer_goal_complexity(goal_text: str) -> str:
    """Infer a lightweight goal complexity label from local heuristics."""
    tokens = goal_text.split()
    connective_count = sum(goal_text.count(marker) for marker in [",", " and ", " then ", " while "])
    if len(tokens) <= 10 and connective_count <= 1:
        return "simple"
    if len(tokens) <= 22 and connective_count <= 3:
        return "moderate"
    return "complex"


@dataclass(frozen=True)
class ProjectGoal:
    """Structured representation of a project goal across prototype phases."""

    goal_id: str
    phase: str
    raw_goal: str
    normalized_goal: str
    target_project_dir: str
    success_criteria: list[str]
    constraints: list[str]
    created_at: str
    priority: str = "medium"
    use_ai: bool = False
    ai_provider: str = "disabled"
    ai_prompt_template: str | None = None
    dependencies: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    memory_enabled: bool = False
    memory_keys: list[str] = field(default_factory=list)
    vector_store_ref: str | None = None
    goal_version: int = 1
    parent_goal_id: str | None = None
    child_goal_ids: list[str] = field(default_factory=list)
    retrieval_notes: list[str] = field(default_factory=list)
    complexity_level: str = "moderate"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the goal into JSON-friendly data."""
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProjectGoal":
        """Rebuild a goal from persisted JSON data."""
        return cls(
            goal_id=payload["goal_id"],
            phase=payload.get("phase", "Phase2"),
            raw_goal=payload["raw_goal"],
            normalized_goal=payload["normalized_goal"],
            target_project_dir=payload["target_project_dir"],
            success_criteria=list(payload.get("success_criteria", [])),
            constraints=list(payload.get("constraints", [])),
            created_at=payload["created_at"],
            priority=payload.get("priority", "medium"),
            use_ai=bool(payload.get("use_ai", False)),
            ai_provider=payload.get("ai_provider", "disabled"),
            ai_prompt_template=payload.get("ai_prompt_template"),
            dependencies=list(payload.get("dependencies", [])),
            notes=list(payload.get("notes", [])),
            tags=list(payload.get("tags", [])),
            memory_enabled=bool(payload.get("memory_enabled", False)),
            memory_keys=list(payload.get("memory_keys", [])),
            vector_store_ref=payload.get("vector_store_ref"),
            goal_version=int(payload.get("goal_version", 1)),
            parent_goal_id=payload.get("parent_goal_id"),
            child_goal_ids=list(payload.get("child_goal_ids", [])),
            retrieval_notes=list(payload.get("retrieval_notes", [])),
            complexity_level=payload.get("complexity_level", "moderate"),
        )

    @property
    def target_path(self) -> Path:
        """Return the resolved target directory for local analysis."""
        return Path(self.target_project_dir)


def memory_store_path(state_dir: str | Path) -> Path:
    """Return the persisted goal-memory file path."""
    return Path(state_dir) / "memory_store.json"


def vector_store_placeholder_path(state_dir: str | Path) -> Path:
    """Return the placeholder vector-store file path."""
    return Path(state_dir) / "vector_store_placeholder.json"


def read_json_file(path: Path) -> dict[str, Any] | None:
    """Read a JSON file if it exists and contains valid JSON."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_json_file(path: Path, payload: dict[str, Any]) -> None:
    """Write deterministic JSON content to disk."""
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def infer_goal_lineage(state_dir: str | Path, normalized_goal: str) -> dict[str, Any]:
    """Infer goal version and parent linkage from the memory placeholder store."""
    payload = read_json_file(memory_store_path(state_dir)) or {
        "goal_count": 0,
        "goals": [],
    }
    matching_goals = [
        entry
        for entry in payload.get("goals", [])
        if entry.get("normalized_goal") == normalized_goal
    ]
    if not matching_goals:
        return {
            "goal_version": 1,
            "parent_goal_id": None,
            "retrieval_notes": [],
            "child_goal_ids": [],
        }

    latest_match = matching_goals[0]
    latest_version = max(int(entry.get("goal_version", 1)) for entry in matching_goals)
    return {
        "goal_version": latest_version + 1,
        "parent_goal_id": latest_match.get("goal_id"),
        "retrieval_notes": [
            f"Historical memory contains {len(matching_goals)} earlier goal versions with the same normalized text.",
            f"Latest related goal: {latest_match.get('goal_id')}",
        ],
        "child_goal_ids": list(latest_match.get("child_goal_ids", [])),
    }


def build_project_goal(
    raw_goal: str | None,
    target_project_dir: str | Path,
    *,
    phase: str = "Phase2",
    priority: str = "medium",
    enable_ai: bool = False,
    ai_provider: str | None = None,
    dependencies: list[str] | None = None,
    enable_memory: bool | None = None,
    state_dir: str | Path | None = None,
) -> ProjectGoal:
    """Create a safe local-analysis goal for the current workflow phase."""
    default_goal = {
        "Phase2": DEFAULT_PHASE2_GOAL,
        "Phase3": DEFAULT_PHASE3_GOAL,
        "Phase4": DEFAULT_PHASE4_GOAL,
        "Phase5": DEFAULT_PHASE5_GOAL,
    }.get(phase, DEFAULT_PHASE2_GOAL)
    normalized_goal = " ".join((raw_goal or default_goal).strip().split())
    complexity_level = infer_goal_complexity(normalized_goal)
    target_path = Path(target_project_dir).resolve()
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    memory_enabled = phase in {"Phase3", "Phase4", "Phase5"} if enable_memory is None else enable_memory
    lineage = (
        infer_goal_lineage(state_dir, normalized_goal)
        if state_dir is not None and memory_enabled
        else {
            "goal_version": 1,
            "parent_goal_id": None,
            "retrieval_notes": [],
            "child_goal_ids": [],
        }
    )

    success_criteria = [
        "The target project directory can be read locally.",
        "A safe task plan is generated for the current workflow phase.",
        "Project inspection artifacts are created without mutating source files.",
        "A structured report is produced without external network calls.",
    ]
    if phase in {"Phase3", "Phase4", "Phase5"}:
        success_criteria.append("Historical goal memory is updated with a local vector-store placeholder entry.")
    if phase == "Phase4":
        success_criteria.extend(
            [
                "A dependency-aware task tree is generated with sequential and parallel tasks.",
                "The workflow produces a review package with safe autonomous suggestions and iteration notes.",
            ]
        )
    if phase == "Phase5":
        success_criteria.extend(
            [
                "A local self-optimization heuristic adjusts task scheduling or retry policy.",
                "Task history and workflow history are updated for later runs.",
            ]
        )

    constraints = [
        "Only safe local filesystem inspection is allowed.",
        "No production Codex, GPT, or OpenAI API execution is enabled by default.",
        "MATLAB and other external toolchains remain documented integration points only.",
    ]
    if phase in {"Phase4", "Phase5"}:
        constraints.append("Autonomous code generation remains a placeholder and must not mutate project files.")
    if phase == "Phase5":
        constraints.append("All optimization logic must be local, deterministic, and safe to rerun.")
    if enable_ai:
        constraints.append("AI mode uses only local placeholder execution in AI-Phase1 through AI-Phase4.")
        constraints.append("AI-Phase4 candidate code stays preview-only and must not be applied automatically.")

    notes = [
        f"This goal is configured for the {phase} prototype workflow.",
        "Placeholder agent executors may simulate reasoning, but they do not mutate project code.",
        f"Goal version: {lineage['goal_version']}.",
        f"Complexity level: {complexity_level}.",
    ]
    if enable_ai:
        notes.append("AI-Phase1 is enabled: AIExecutor routes AI-capable tasks through safe local placeholders.")
        notes.append("AI-Phase2 provider abstraction is active: provider routing is configurable without changing task structures.")
        notes.append("AI-Phase4 keeps code assistance in preview-only mode with local verification and explicit review gating.")
    notes.extend(lineage["retrieval_notes"])

    tags = ["python", "local-analysis", phase.lower(), complexity_level]
    if enable_ai:
        tags.extend(["ai-enabled", "ai-placeholder"])
    if phase == "Phase4":
        tags.extend(["memory-aware", "task-tree", "autonomous-review"])
    if phase == "Phase5":
        tags.extend(["self-optimization", "historical-memory", "local-autonomy"])

    memory_keys = [f"{phase.lower()}::{_goal_slug(normalized_goal)}"] if memory_enabled else []
    vector_store_ref = f"vector::{phase.lower()}::{timestamp}" if memory_enabled else None

    return ProjectGoal(
        goal_id=f"goal-{_goal_slug(normalized_goal)}-{timestamp}",
        phase=phase,
        raw_goal=raw_goal or default_goal,
        normalized_goal=normalized_goal,
        target_project_dir=str(target_path),
        success_criteria=success_criteria,
        constraints=constraints,
        created_at=utc_now(),
        priority=priority if priority in PRIORITY_SCORES else "medium",
        use_ai=enable_ai,
        ai_provider=(ai_provider or "local_placeholder") if enable_ai else "disabled",
        ai_prompt_template="ai_phase1_goal_prompt_v1" if enable_ai else None,
        dependencies=list(dependencies or []),
        notes=notes,
        tags=tags,
        memory_enabled=memory_enabled,
        memory_keys=memory_keys,
        vector_store_ref=vector_store_ref,
        goal_version=int(lineage["goal_version"]),
        parent_goal_id=lineage["parent_goal_id"],
        child_goal_ids=list(lineage["child_goal_ids"]),
        retrieval_notes=list(lineage["retrieval_notes"]),
        complexity_level=complexity_level,
    )


def render_goal_ai_prompt(goal: ProjectGoal) -> str:
    """Render a safe AI prompt preview for the current goal.

    The returned text is for logging, visualization, and future provider
    integration boundaries only. AI-Phase1 does not send it to external APIs.
    """

    return (
        f"[{goal.phase}] Goal={goal.normalized_goal}; "
        f"target_dir={goal.target_project_dir}; "
        f"priority={goal.priority}; "
        f"goal_version={goal.goal_version}; "
        f"use_ai={goal.use_ai}; "
        "instruction=produce a safe read-only planning, candidate code, or patch-preview suggestion."
    )


def _rebuild_goal_children(goals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rebuild child-goal references from parent-goal links."""
    child_map: dict[str, list[str]] = {}
    for entry in goals:
        parent_goal_id = entry.get("parent_goal_id")
        if parent_goal_id:
            child_map.setdefault(parent_goal_id, []).append(entry.get("goal_id"))

    rebuilt: list[dict[str, Any]] = []
    for entry in goals:
        cloned = dict(entry)
        cloned["child_goal_ids"] = child_map.get(entry.get("goal_id"), [])
        cloned["complexity_level"] = cloned.get("complexity_level") or infer_goal_complexity(
            str(cloned.get("normalized_goal", ""))
        )
        cloned["goal_version"] = int(cloned.get("goal_version", 1))
        rebuilt.append(cloned)
    return rebuilt


def persist_goal_memory(state_dir: str | Path, goal: ProjectGoal) -> dict[str, Any]:
    """Persist the current goal in a simple long-term memory placeholder."""
    state_path = Path(state_dir)
    state_path.mkdir(parents=True, exist_ok=True)

    memory_payload = read_json_file(memory_store_path(state_path)) or {
        "updated_at": utc_now(),
        "goal_count": 0,
        "goals": [],
    }
    vector_payload = read_json_file(vector_store_placeholder_path(state_path)) or {
        "updated_at": utc_now(),
        "vector_count": 0,
        "vectors": [],
    }

    memory_entry = {
        "goal_id": goal.goal_id,
        "phase": goal.phase,
        "normalized_goal": goal.normalized_goal,
        "target_project_dir": goal.target_project_dir,
        "priority": goal.priority,
        "use_ai": goal.use_ai,
        "ai_provider": goal.ai_provider,
        "dependencies": goal.dependencies,
        "created_at": goal.created_at,
        "memory_keys": goal.memory_keys,
        "goal_version": goal.goal_version,
        "parent_goal_id": goal.parent_goal_id,
        "child_goal_ids": list(goal.child_goal_ids),
        "tags": goal.tags,
        "complexity_level": goal.complexity_level,
    }
    vector_entry = {
        "goal_id": goal.goal_id,
        "memory_keys": goal.memory_keys,
        "embedding_stub": [
            len(goal.normalized_goal.split()),
            len(goal.normalized_goal),
            PRIORITY_SCORES.get(goal.priority, 2),
            len(goal.success_criteria),
            goal.goal_version,
        ],
        "created_at": goal.created_at,
        "phase": goal.phase,
        "complexity_level": goal.complexity_level,
        "use_ai": goal.use_ai,
    }

    goals = [entry for entry in memory_payload.get("goals", []) if entry.get("goal_id") != goal.goal_id]
    goals.insert(0, memory_entry)
    goals = _rebuild_goal_children(goals)

    vectors = [
        entry
        for entry in vector_payload.get("vectors", [])
        if entry.get("goal_id") != goal.goal_id
    ]
    vectors.insert(0, vector_entry)

    memory_payload = {
        "updated_at": utc_now(),
        "goal_count": len(goals),
        "goals": goals[:150],
    }
    vector_payload = {
        "updated_at": utc_now(),
        "vector_count": len(vectors),
        "vectors": vectors[:150],
    }

    write_json_file(memory_store_path(state_path), memory_payload)
    write_json_file(vector_store_placeholder_path(state_path), vector_payload)

    return {
        "memory_store": memory_payload,
        "vector_store_placeholder": vector_payload,
    }


def load_memory_status(state_dir: str | Path) -> dict[str, Any]:
    """Return a combined view of the stored goal-memory placeholders."""
    state_path = Path(state_dir)
    memory_payload = read_json_file(memory_store_path(state_path)) or {
        "updated_at": None,
        "goal_count": 0,
        "goals": [],
    }
    vector_payload = read_json_file(vector_store_placeholder_path(state_path)) or {
        "updated_at": None,
        "vector_count": 0,
        "vectors": [],
    }

    phase_breakdown: dict[str, int] = {}
    complexity_breakdown: dict[str, int] = {}
    ai_provider_breakdown: dict[str, int] = {}
    relationship_count = 0
    ai_goal_count = 0
    for entry in memory_payload.get("goals", []):
        phase = entry.get("phase", "unknown")
        complexity = entry.get("complexity_level", "unknown")
        phase_breakdown[phase] = phase_breakdown.get(phase, 0) + 1
        complexity_breakdown[complexity] = complexity_breakdown.get(complexity, 0) + 1
        if entry.get("parent_goal_id"):
            relationship_count += 1
        if entry.get("use_ai"):
            ai_goal_count += 1
            provider = entry.get("ai_provider", "unknown")
            ai_provider_breakdown[provider] = ai_provider_breakdown.get(provider, 0) + 1

    return {
        "updated_at": max(
            filter(
                None,
                [
                    memory_payload.get("updated_at"),
                    vector_payload.get("updated_at"),
                ],
            ),
            default=None,
        ),
        "goal_count": memory_payload.get("goal_count", 0),
        "vector_count": vector_payload.get("vector_count", 0),
        "recent_goals": memory_payload.get("goals", [])[:10],
        "recent_vectors": vector_payload.get("vectors", [])[:10],
        "phase_breakdown": phase_breakdown,
        "complexity_breakdown": complexity_breakdown,
        "relationship_count": relationship_count,
        "ai_goal_count": ai_goal_count,
        "ai_provider_breakdown": ai_provider_breakdown,
    }


def retrieve_memory_context(
    state_dir: str | Path,
    goal: ProjectGoal,
    *,
    limit: int = 5,
) -> dict[str, Any]:
    """Retrieve a lightweight local memory context for the current goal."""
    state_path = Path(state_dir)
    status = load_memory_status(state_path)
    payload = read_json_file(memory_store_path(state_path)) or {"goals": []}
    goal_tokens = _tokenize(goal.normalized_goal)

    matches: list[dict[str, Any]] = []
    for entry in payload.get("goals", []):
        if entry.get("goal_id") == goal.goal_id:
            continue

        entry_goal = entry.get("normalized_goal", "")
        overlap_score = len(goal_tokens & _tokenize(entry_goal))
        phase_bonus = 1 if entry.get("phase") == goal.phase else 0
        priority_bonus = 1 if entry.get("priority") == goal.priority else 0
        complexity_bonus = 1 if entry.get("complexity_level") == goal.complexity_level else 0
        total_score = overlap_score + phase_bonus + priority_bonus + complexity_bonus
        if total_score <= 0:
            continue

        matches.append(
            {
                "goal_id": entry.get("goal_id"),
                "phase": entry.get("phase"),
                "priority": entry.get("priority"),
                "goal_version": entry.get("goal_version", 1),
                "parent_goal_id": entry.get("parent_goal_id"),
                "child_goal_ids": list(entry.get("child_goal_ids", [])),
                "normalized_goal": entry_goal,
                "complexity_level": entry.get("complexity_level", "unknown"),
                "similarity_score": total_score,
                "created_at": entry.get("created_at"),
                "use_ai": bool(entry.get("use_ai", False)),
            }
        )

    matches.sort(
        key=lambda entry: (
            -int(entry.get("similarity_score", 0)),
            entry.get("created_at") or "",
        )
    )
    limited_matches = matches[:limit]

    return {
        **status,
        "goal_id": goal.goal_id,
        "goal_version": goal.goal_version,
        "parent_goal_id": goal.parent_goal_id,
        "child_goal_ids": goal.child_goal_ids,
        "complexity_level": goal.complexity_level,
        "matches": limited_matches,
        "retrieved_goal_count": len(limited_matches),
        "top_match_goal_id": limited_matches[0]["goal_id"] if limited_matches else None,
        "memory_scope": "local_placeholder",
        "ai_goal_count": status.get("ai_goal_count", 0),
    }


def query_goal_memory(
    state_dir: str | Path,
    query_text: str | None = None,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """Query local goal memory using deterministic token overlap heuristics."""
    state_path = Path(state_dir)
    status = load_memory_status(state_path)
    payload = read_json_file(memory_store_path(state_path)) or {"goals": []}
    normalized_query = " ".join((query_text or "").strip().split())
    query_tokens = _tokenize(normalized_query)

    results: list[dict[str, Any]] = []
    for entry in payload.get("goals", []):
        normalized_goal = entry.get("normalized_goal", "")
        score = 0
        if normalized_query:
            score += len(query_tokens & _tokenize(normalized_goal))
            if normalized_query.lower() in normalized_goal.lower():
                score += 3
            if normalized_query.lower() in str(entry.get("goal_id", "")).lower():
                score += 2
            if normalized_query.lower() == str(entry.get("phase", "")).lower():
                score += 1
            if score <= 0:
                continue
        results.append(
            {
                "goal_id": entry.get("goal_id"),
                "phase": entry.get("phase"),
                "priority": entry.get("priority"),
                "goal_version": entry.get("goal_version", 1),
                "parent_goal_id": entry.get("parent_goal_id"),
                "child_goal_ids": list(entry.get("child_goal_ids", [])),
                "complexity_level": entry.get("complexity_level", "unknown"),
                "normalized_goal": normalized_goal,
                "created_at": entry.get("created_at"),
                "score": score,
            }
        )

    results.sort(key=lambda entry: (-int(entry.get("score", 0)), entry.get("created_at") or ""), reverse=False)
    if normalized_query:
        results = sorted(results, key=lambda entry: (-int(entry.get("score", 0)), entry.get("created_at") or ""))
    else:
        results = status.get("recent_goals", [])

    return {
        "query": normalized_query or None,
        "match_count": len(results[:limit]),
        "matches": results[:limit],
        "memory_status": status,
    }

# Data Model: Phase 4 Closeout — Host-Surface Breadth and Trail Follow-On

**Mission**: `phase-4-closeout-host-surfaces-and-trail-01KPWA5X`
**Phase**: 1 (Design)

This document is the typed data model for every new or extended entity the mission introduces. All types are Python 3.11+ with PEP-604 union syntax and `from __future__ import annotations` for the source files. `mypy --strict` must pass (NFR-005).

## 1. `ModeOfWork` enum

Location: new module `src/specify_cli/invocation/modes.py`.

```python
class ModeOfWork(str, Enum):
    ADVISORY = "advisory"
    TASK_EXECUTION = "task_execution"
    MISSION_STEP = "mission_step"
    QUERY = "query"
```

`str`-valued so the enum round-trips cleanly through JSONL (`json.dumps(ModeOfWork.ADVISORY) == '"advisory"'`).

### Derivation

```python
_ENTRY_COMMAND_MODE: dict[str, ModeOfWork] = {
    "advise": ModeOfWork.ADVISORY,
    "ask": ModeOfWork.TASK_EXECUTION,
    "do": ModeOfWork.TASK_EXECUTION,
    "profile-invocation.complete": ModeOfWork.TASK_EXECUTION,
    "next.specify": ModeOfWork.MISSION_STEP,
    "next.plan": ModeOfWork.MISSION_STEP,
    "next.tasks": ModeOfWork.MISSION_STEP,
    "next.implement": ModeOfWork.MISSION_STEP,
    "next.review": ModeOfWork.MISSION_STEP,
    "next.merge": ModeOfWork.MISSION_STEP,
    "next.accept": ModeOfWork.MISSION_STEP,
    "profiles.list": ModeOfWork.QUERY,
    "invocations.list": ModeOfWork.QUERY,
}

def derive_mode(entry_command: str) -> ModeOfWork:
    """Deterministic derivation. Raises KeyError on unknown command."""
    return _ENTRY_COMMAND_MODE[entry_command]
```

Unknown `entry_command` raises `KeyError` at the CLI layer (not inside the executor) so that the CLI can present a clear error before a malformed invocation is opened. The executor accepts `mode_of_work: ModeOfWork | None` and only rejects at enforcement time.

## 2. `InvocationRecord` (extended)

Location: existing module `src/specify_cli/invocation/record.py`.

New optional field on the `started` shape only:

```python
@dataclass(frozen=True)
class InvocationRecord:
    # existing fields ...
    event: Literal["started", "completed"]
    invocation_id: str
    profile_id: str
    action: str
    request_text: str | None = None
    governance_context_hash: str | None = None
    governance_context_available: bool | None = None
    actor: str | None = None
    router_confidence: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    outcome: Literal["done", "failed", "abandoned"] | None = None
    evidence_ref: str | None = None

    # NEW (additive, started-event only):
    mode_of_work: str | None = None  # one of ModeOfWork values; None for pre-mission records
```

- Serialisation: `model_dump()` unchanged; a `None` `mode_of_work` is omitted from JSON output (existing `exclude_none=True` behaviour if using pydantic, or explicit filter if dataclass + json).
- Read path: every consumer must treat `mode_of_work` as `str | None` and tolerate `None` (NFR existing-record compatibility).

## 3. Correlation events (new)

Two new event shapes, appended to the same invocation JSONL file. They are **events**, not `InvocationRecord` mutations, to keep `InvocationRecord` focused on started/completed.

### 3.1 `artifact_link` event

```json
{
  "event": "artifact_link",
  "invocation_id": "01HXYZ...",
  "kind": "artifact",
  "ref": "kitty-specs/042-foo/tasks/WP03.md",
  "at": "2026-04-23T04:45:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `event` | `"artifact_link"` | Event discriminator. |
| `invocation_id` | `str` (ULID) | Must match the file's invocation_id. |
| `kind` | `str` | Free-form classifier for the artifact kind (e.g., `"artifact"`, `"mission_artifact"`, `"test_report"`). Default `"artifact"` at CLI layer. |
| `ref` | `str` | The persisted reference. Repo-relative if the resolved absolute path is under `repo_root`; absolute otherwise (see §6 below). |
| `at` | `str` (ISO-8601 UTC) | Append timestamp. |

### 3.2 `commit_link` event

```json
{
  "event": "commit_link",
  "invocation_id": "01HXYZ...",
  "sha": "a1b2c3d4e5f6...",
  "at": "2026-04-23T04:45:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `event` | `"commit_link"` | Event discriminator. |
| `invocation_id` | `str` (ULID) | Must match the file's invocation_id. |
| `sha` | `str` | Git SHA, recorded verbatim. No validation against `git cat-file`; the trail is observational. |
| `at` | `str` (ISO-8601 UTC) | Append timestamp. |

### 3.3 Invariants for both correlation events

- Appended via a new `InvocationWriter.append_correlation_link(...)` method in append mode (`"a"`).
- The invocation file must already exist (a `started` event was written). The method raises `InvocationError` if not.
- No existing line is mutated. Multiple `artifact_link` events are expected; multiple `commit_link` events are legal but the CLI surface records one per `complete` call (singular `--commit`).
- Readers that do not recognise these event types must skip the line — the same invariant as `glossary_checked` (`writer.py:142-168`).
- Not serialisable as `InvocationRecord`; use `dict[str, object]` + `json.dumps(sort_keys=False)`.

## 4. `EventKind` enum

Location: `src/specify_cli/invocation/projection_policy.py` (re-exports `ModeOfWork` from `modes.py`).

```python
class EventKind(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    ARTIFACT_LINK = "artifact_link"
    COMMIT_LINK = "commit_link"
```

`glossary_checked` is intentionally **not** in `EventKind`: it is a diagnostic / local-only observation and is already handled by the existing chokepoint path, which does not route through `_propagate_one`.

## 5. `ProjectionRule` + `POLICY_TABLE`

Location: `src/specify_cli/invocation/projection_policy.py`.

```python
@dataclass(frozen=True)
class ProjectionRule:
    project: bool
    include_request_text: bool
    include_evidence_ref: bool

POLICY_TABLE: dict[tuple[ModeOfWork, EventKind], ProjectionRule] = {
    (ModeOfWork.ADVISORY, EventKind.STARTED):        ProjectionRule(True,  False, False),
    (ModeOfWork.ADVISORY, EventKind.COMPLETED):      ProjectionRule(True,  False, False),
    (ModeOfWork.ADVISORY, EventKind.ARTIFACT_LINK):  ProjectionRule(False, False, False),
    (ModeOfWork.ADVISORY, EventKind.COMMIT_LINK):    ProjectionRule(False, False, False),

    (ModeOfWork.TASK_EXECUTION, EventKind.STARTED):       ProjectionRule(True, True,  False),
    (ModeOfWork.TASK_EXECUTION, EventKind.COMPLETED):     ProjectionRule(True, True,  True),
    (ModeOfWork.TASK_EXECUTION, EventKind.ARTIFACT_LINK): ProjectionRule(True, False, False),
    (ModeOfWork.TASK_EXECUTION, EventKind.COMMIT_LINK):   ProjectionRule(True, False, False),

    (ModeOfWork.MISSION_STEP, EventKind.STARTED):       ProjectionRule(True, True,  False),
    (ModeOfWork.MISSION_STEP, EventKind.COMPLETED):     ProjectionRule(True, True,  True),
    (ModeOfWork.MISSION_STEP, EventKind.ARTIFACT_LINK): ProjectionRule(True, False, False),
    (ModeOfWork.MISSION_STEP, EventKind.COMMIT_LINK):   ProjectionRule(True, False, False),

    (ModeOfWork.QUERY, EventKind.STARTED):       ProjectionRule(False, False, False),
    (ModeOfWork.QUERY, EventKind.COMPLETED):     ProjectionRule(False, False, False),
    (ModeOfWork.QUERY, EventKind.ARTIFACT_LINK): ProjectionRule(False, False, False),
    (ModeOfWork.QUERY, EventKind.COMMIT_LINK):   ProjectionRule(False, False, False),
}

_DEFAULT_RULE = ProjectionRule(project=True, include_request_text=True, include_evidence_ref=True)

def resolve_projection(mode: ModeOfWork | None, event: EventKind) -> ProjectionRule:
    """Return the projection rule for (mode, event).

    None mode (pre-mission records) is treated as TASK_EXECUTION to preserve
    existing projection behaviour for legacy records.
    """
    effective_mode = mode if mode is not None else ModeOfWork.TASK_EXECUTION
    return POLICY_TABLE.get((effective_mode, event), _DEFAULT_RULE)
```

Table is exhaustive for `(ModeOfWork, EventKind)` ∈ {4 × 4}. `resolve_projection` falls back to `_DEFAULT_RULE` only for entries that a future `EventKind` extension would add before the table is updated — defensive, never hit in testing today.

## 6. Ref-normalisation algorithm (for `--artifact` and `--evidence`)

Shared helper, used by `complete_invocation` for `--evidence` and by the new `append_correlation_link` for `--artifact`:

```python
def normalise_ref(ref: str, repo_root: Path) -> str:
    """Repo-relative when the resolved path is under repo_root; absolute otherwise.

    The input ref is treated as a filesystem path. Ref values that do not look
    like paths (for example, inline URIs or verbatim strings) are returned
    as-is — this is the current behaviour for evidence refs that cannot be
    resolved (see executor.complete_invocation:247-253).
    """
    try:
        resolved = Path(ref).resolve()
    except (OSError, RuntimeError):
        return ref
    root = repo_root.resolve()
    try:
        return str(resolved.relative_to(root))
    except ValueError:
        # Resolved path is outside the checkout. Absolute fallback.
        return str(resolved)
```

### Behaviour by input

| Input `ref` | Under `repo_root`? | Persisted |
|-------------|--------------------|-----------|
| `kitty-specs/042/spec.md` | yes | `"kitty-specs/042/spec.md"` |
| `./build/out.log` | yes | `"build/out.log"` |
| `/tmp/something.log` | no | `"/tmp/something.log"` |
| `/absolute/inside/repo/file.md` | yes | `"<relpath>"` |
| `not-a-valid-path\0x00` | n/a (raises on resolve) | `"not-a-valid-path\x00"` (verbatim) |

Worktrees (`.worktrees/<slug>-lane-a/…`) resolve to paths inside `repo_root` and are recorded repo-relative; this is intentional for correlation purposes.

## 7. `InvalidModeForEvidenceError`

Location: `src/specify_cli/invocation/errors.py` (existing module, add new class).

```python
class InvalidModeForEvidenceError(InvocationError):
    """Raised when --evidence is supplied on an invocation whose mode_of_work
    disallows Tier 2 promotion (advisory or query)."""

    def __init__(self, invocation_id: str, mode: ModeOfWork) -> None:
        self.invocation_id = invocation_id
        self.mode = mode
        super().__init__(
            f"Cannot promote evidence on invocation {invocation_id}: "
            f"mode is {mode.value}; Tier 2 evidence is only allowed on "
            f"task_execution or mission_step invocations."
        )
```

CLI exit code: inherits from `InvocationError` (existing mapping — typically exit 2). The CLI layer prints a red error via `rich` and a one-line hint suggesting the operator rerun `complete` without `--evidence`.

## 8. `HostSurfaceInventoryRow`

Location: `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/host-surface-inventory.md` — a markdown table, not a Python type. The contract at `contracts/host-surface-inventory.md` pins the column order.

Logical schema:

| Field | Type | Allowed values |
|-------|------|----------------|
| `surface_key` | `str` | Canonical agent key per `AGENT_DIRS` (e.g. `claude`, `codex`, `vibe`, `copilot`, `cursor`, `gemini`, `qwen`, `opencode`, `windsurf`, `kilocode`, `auggie`, `roo`, `q`, `kiro`, `agent`) |
| `directory` | `str` | Filesystem path from repo root |
| `kind` | `str` | `slash_command` or `agent_skill` |
| `has_advise_guidance` | `bool` | yes / no |
| `has_governance_injection` | `bool` | yes / no |
| `has_completion_guidance` | `bool` | yes / no |
| `guidance_style` | `str` | `inline` (content lives in the surface) or `pointer` (surface points at canonical skill pack) |
| `parity_status` | `str` | `at_parity`, `partial`, or `missing` |
| `notes` | `str` | Free text — used to capture per-surface rationale for `pointer` style (FR-006). |

The matrix is the concrete acceptance surface for FR-001 / NFR-003.

## 9. Relationship to existing data model

- `InvocationRecord` is the only existing type touched; the change is additive (`mode_of_work: str | None` with default `None`).
- Correlation events are new event shapes on an existing file; no existing event shape changes.
- `ProjectionRule` / `POLICY_TABLE` are new; they do not replace or shadow any existing type.
- `_get_saas_client` / `_propagate_one` signatures do not change; `_propagate_one`'s behaviour changes by consulting `POLICY_TABLE` after the existing sync-gate.
- The invocation index at `.kittify/events/invocation-index.jsonl` is **not** extended — correlation links are discovered by reading the invocation file itself, not by index lookup. This preserves NFR-002 (O(limit) reverse-scan).

## 10. Non-goals explicitly preserved from the spec

Types and fields NOT introduced by this mission:

- No new invocation kinds beyond `started`, `completed`, `artifact_link`, `commit_link`, `glossary_checked`.
- No mutation of existing JSONL lines (C-004).
- No new top-level dashboard data type — wording changes do not alter API response shapes.
- No `spec-kitty explain` data model (C-005).
- No SaaS projection of Tier 2 evidence bodies (D5).
- No operator-configurable YAML for projection policy (D4).

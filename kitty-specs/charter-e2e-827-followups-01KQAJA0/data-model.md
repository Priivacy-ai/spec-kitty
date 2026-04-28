# Data Model — Charter E2E #827 Follow-ups (Tranche A)

This is a behavior-tightening mission, not a schema mission. No new persistent entities are introduced. The "data model" here is a set of **invariants** layered on top of existing structures. Each invariant maps to one or more FRs from [spec.md](spec.md).

## Existing entities affected

### `RuntimeDecision` (from `src/specify_cli/next/decision.py`)

Already-existing dataclass with at least these fields (current shape, abbreviated):

```python
@dataclass
class RuntimeDecision:
    kind: Literal["step", "blocked", "complete", "..."]
    prompt_file: str | None = None
    # ... other fields
```

Wire format (current, from `to_dict()`):
- `kind`: string
- `prompt_file`: string | null  ← **invariant tightened by this mission**
- `prompt_path`: string | null  (alias; same tightening applies whichever field is populated)

#### New invariants (#844)

| ID | Invariant | Enforced where |
|---|---|---|
| INV-844-1 | If `kind == "step"`, then `prompt_file` (or `prompt_path` alias) MUST be a non-empty string. | Envelope construction in `decision.py` and `runtime_bridge.py`; validation guard before serialization. |
| INV-844-2 | If `kind == "step"`, then the path emitted by INV-844-1 MUST resolve to an existing on-disk file at the time of envelope construction. | Same. Falls back to `kind=blocked` with reason if it cannot. |
| INV-844-3 | A non-actionable runtime state MUST use a non-`step` kind (typically `kind=blocked`) with a `reason`. `kind=step` with `prompt_file=null` is illegal. | Same. |

State transitions: none. The `kind` enum already exists; this mission only enforces correct use of existing values.

### `MissionDossierSnapshot` (from `src/specify_cli/dossier/snapshot.py`)

Already-existing pydantic model. Persisted to `<feature_dir>/.kittify/dossiers/<mission_slug>/snapshot-latest.json` by `save_snapshot()`.

#### New invariants (#845)

| ID | Invariant | Enforced where |
|---|---|---|
| INV-845-1 | The snapshot file path `*/.kittify/dossiers/*/snapshot-latest.json` MUST be ignored by `.gitignore`. | Root `.gitignore` entry. |
| INV-845-2 | Any worktree dirty-state pre-flight used by `agent tasks move-task` (and related transitions) MUST treat paths matching INV-845-1's pattern as not-dirty for the purposes of the transition gate. | Pre-flight code path in `src/specify_cli/cli/commands/agent/tasks.py` and helpers in `src/specify_cli/status/`. |
| INV-845-3 | The pre-flight MUST continue to fail on **other** worktree dirty state (i.e., real uncommitted edits unrelated to the snapshot). | Same. Verified by regression test. |

### `Mission` setup-plan / setup-specify auto-commit decision

Already-existing code path in `src/specify_cli/cli/commands/agent/mission.py` that auto-commits scaffolded `spec.md` / `plan.md` to the target branch.

#### New invariants (#846)

| ID | Invariant | Enforced where |
|---|---|---|
| INV-846-1 | The auto-commit step MUST consult `_is_substantive(file_path, kind)` before committing. | `mission.py` at the auto-commit branch. |
| INV-846-2 | If `_is_substantive(...)` returns false, the workflow MUST NOT auto-commit. It MUST emit a documented "needs substantive content" status and skip the commit. | Same. |
| INV-846-3 | Workflow status JSON MUST report a non-substantive-but-scaffolded state as **incomplete**, not "ready". | Status emission paths reachable from `setup-plan --json` and the specify equivalent. |

#### `_is_substantive(file_path: Path, kind: Literal["spec", "plan"]) -> bool`

New helper. Definition (operational):

```
_is_substantive(file_path, kind) returns True iff EITHER:
  (a) byte_length(file_path) > byte_length(canonical_scaffold(kind)) + SUBSTANTIVE_DELTA  // default 256
  OR
  (b) required_sections_present(file_path, kind)  // spec: ≥1 FR row; plan: non-empty Technical Context
```

`canonical_scaffold(kind)` returns the bytes of whatever the create command writes by default for that artifact kind. Computed once at module load and cached.

Both checks are pure functions of file content. No side effects. Deterministic.

## Pin-drift detection (#848)

No persistent entity. The check is a procedure, not a data structure. Inputs:
- `uv.lock` (TOML at repo root)
- `importlib.metadata.version(<package>)` for each governed shared package

Outputs (in test failure path):
- list of offending packages with their `(uv.lock_version, installed_version)` tuples
- the documented sync command, embedded in the failure message

Governed packages (initial scope, derived from `pyproject.toml` `[project.dependencies]` plus this mission's spec):
- `spec-kitty-events` — required by FR-001 explicitly
- `spec-kitty-tracker` — same pin contract; included for parity (the architectural-shape tests already cover both)

The list of governed packages is centralized in the new test (`GOVERNED_PACKAGES = ["spec-kitty-events", "spec-kitty-tracker"]`). Adding a future package is a one-line edit.

## Removed text (doctrine / inline comments)

This mission deletes the following text patterns wherever they appear:

- "advance mode populates this" (in inline comments around prompt-file fields).
- Any host-facing guidance under `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` that legitimizes a null prompt for `kind=step`.

Replacement guidance: "null is only legal for non-`step` kinds; a `kind=step` envelope without a resolvable prompt is a runtime invariant violation".

## What this mission does NOT touch

Per Constraint C-003 / C-004 and the broader "no redesign" thesis:

- No changes to: `pyproject.toml` `[project.dependencies]` shape; `uv.lock` semantics; `[tool.uv.sources]`; the shared-package boundary contract.
- No changes to: lane state machine, status event log schema, merge engine, worktree layout.
- No changes to: the kind enum in `RuntimeDecision`, the wire-format keys, mission/charter doctrine beyond the surgical scrub for #844.

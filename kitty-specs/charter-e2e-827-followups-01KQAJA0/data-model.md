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

Wire format (current, from `to_dict()` in `decision.py:93`):
- `kind`: string
- `prompt_file`: string | null  ← **only producer-side prompt field; invariant tightened by this mission**

`prompt_path` is **not** a wire field on `RuntimeDecision` / `Decision`. It is a local variable in `prompt_builder.py` and `runtime_bridge.py`. The current charter E2E (`tests/e2e/test_charter_epic_golden_path.py:570`) accepts either key as a defensive consumer-side fallback — that fallback is preserved by this mission for backward compatibility, but **producer code in this mission writes `prompt_file` only**. This mission does NOT introduce a `prompt_path` wire field.

#### New invariants (#844)

| ID | Invariant | Enforced where |
|---|---|---|
| INV-844-1 | If `kind == "step"`, then `prompt_file` MUST be a non-empty string. | Envelope construction (`__post_init__` on `RuntimeDecision` in `decision.py`); call-site fallback to `kind=blocked` in `runtime_bridge.py` when validation fails. |
| INV-844-2 | If `kind == "step"`, then the path emitted by INV-844-1 MUST resolve to an existing on-disk file at the time of envelope construction. | Same. |
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

### `Mission` create / setup-plan auto-commit decisions

Two existing code paths in `src/specify_cli/cli/commands/agent/mission.py`:

1. **`mission create`** auto-commits the empty `spec.md` scaffold + `meta.json` at create time. *This is the primary defect surface for #846.*
2. **`setup-plan`** writes `plan.md` from the slash-template flow and calls `_commit_to_branch(plan_file, …)` to commit it.

The `/spec-kitty.specify` slash-template instructs the agent to commit substantive `spec.md` content separately; that commit happens outside Python.

#### New invariants (#846)

| ID | Invariant | Enforced where |
|---|---|---|
| INV-846-1 | `mission create` MUST NOT auto-commit `spec.md`. The empty scaffold remains untracked at create time; the agent commits the populated content after writing substantive requirements. | `mission.py` — modify the create-time `safe_commit` call to omit `spec.md` from `files_to_commit`. |
| INV-846-2 | `setup-plan` MUST verify, at entry, that `spec.md` is **both** committed (tracked + present in HEAD) **and** substantive. If either fails, emit `phase_complete=False` with a `blocked_reason` and return without writing or committing `plan.md`. | `mission.py` `setup-plan` entry path. |
| INV-846-3 | The existing `_commit_to_branch(plan_file, …)` call in `setup-plan` MUST be gated on `is_substantive(plan_path, "plan")`. If false, emit `phase_complete=False / blocked_reason` and skip the commit. | `mission.py` `setup-plan` exit path (around line 973). |
| INV-846-4 | Workflow status JSON MUST report any non-substantive or uncommitted-substantive state as **incomplete**, not "ready". | Status emission paths reachable from `setup-plan --json` and any peer status command. |

#### `is_substantive(file_path: Path, kind: Literal["spec", "plan"]) -> bool`

New helper. Definition (operational, **revised — section-presence only**):

```
is_substantive(file_path, kind) returns True iff:
  required_sections_present(file_path, kind)
```

Required-section heuristics:
- **spec**: at least one row with an `FR-\d{3}` ID followed by non-empty description content. The row must not consist entirely of template placeholders (`[NEEDS CLARIFICATION …]`, `[e.g., …]`).
- **plan**: a populated `Technical Context` section where the `Language/Version`, `Primary Dependencies`, etc. fields contain real values, not template placeholders like `[e.g., Python 3.11 …]` or `[NEEDS CLARIFICATION …]`.

The earlier "byte-length OR section-presence" formulation was rejected (research R7, revised) because byte-length-only could pass scaffold + 300 bytes of arbitrary prose, recreating the failure mode.

The check is a pure function of file content. No side effects. Deterministic.

#### `is_committed(file_path: Path, repo_root: Path) -> bool`

New helper. Returns True iff `git ls-files --error-unmatch <file_path>` succeeds AND the file is present at HEAD (`git cat-file -e HEAD:<rel_path>`). Used by INV-846-2.

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

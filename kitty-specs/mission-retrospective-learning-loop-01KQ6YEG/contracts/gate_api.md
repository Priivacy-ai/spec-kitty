# Contract: Lifecycle Gate Python API

**Status**: pinned for this tranche.
**Source of truth**: `specify_cli.retrospective.gate`.
**ADR**: `architecture/2.x/adr/2026-04-27-1-retrospective-gate-shared-module.md` (drafted in WP for sub-problem 3).

The gate is the single source of truth (AD-001, Q1-C). Both `specify_cli.next` and any status-transition surface that ever needs mission-level mode policy MUST consult it through this API. Mission-level policy MUST NOT be re-implemented in WP-level status code.

---

## Public API

```python
# specify_cli.retrospective.gate

def is_completion_allowed(
    mission_id: MissionId,
    *,
    feature_dir: Path,
    repo_root: Path,
    mode_override: Mode | None = None,
) -> GateDecision: ...
```

### Inputs

| Argument | Type | Notes |
|---|---|---|
| `mission_id` | `MissionId` (ULID) | Canonical identity. |
| `feature_dir` | `Path` | Path to `kitty-specs/<slug>/`; used to read the mission event log. |
| `repo_root` | `Path` | Used to find `.kittify/missions/<mission_id>/retrospective.yaml`. |
| `mode_override` | `Mode \| None` | Test-only injection. Production callers pass `None` and let the gate resolve via `mode.detect()`. |

### Output

```python
class GateDecision(BaseModel):
    allow_completion: bool
    mode: Mode
    reason: GateReason
```

(See [../data-model.md](../data-model.md) for `GateReason`.)

The decision is **deterministic**: same event log + same mode signals → same `GateDecision`. (NFR-008.)

---

## Decision matrix

| Mode | Latest retrospective event for mission | Decision |
|---|---|---|
| `autonomous` | none | block, `missing_completion_autonomous` |
| `autonomous` | `retrospective.completed` | allow, `completed_present` |
| `autonomous` | `retrospective.skipped` | block, `silent_skip_attempted` |
| `autonomous` | `retrospective.failed` | block, `facilitator_failure` |
| `autonomous` | only `requested`/`started` | block, `missing_completion_autonomous` |
| `human_in_command` | none | block, `silent_auto_run_attempted` if a `next`-driven completion is being attempted; otherwise the gate returns `allow=False` and the runtime offers the retrospective to the operator. |
| `human_in_command` | `retrospective.completed` | allow, `completed_present_hic` |
| `human_in_command` | `retrospective.skipped` | allow, `skipped_permitted` |
| `human_in_command` | `retrospective.failed` | block, `facilitator_failure` |

**Charter override**: in autonomous mode, if the charter clause permits operator-authorized skip and a `retrospective.skipped` event carries an `actor` whose authorization matches the clause, the gate allows completion. The decision's `reason.code = "skipped_permitted"` and `reason.charter_clause_ref` is set. Without a permissive clause, autonomous + skipped is always `silent_skip_attempted`.

**Silent auto-run detection** (HiC): if a `retrospective.completed` event exists in HiC mode but the upstream `requested` event was emitted by `actor.kind == "runtime"` (not by an operator), the gate treats the completion as silent and returns `silent_auto_run_attempted` blocking. This is the operational predicate for "silent" called out in CHK005.

---

## Performance

NFR-007: when `retrospective.completed` is already present, `is_completion_allowed` MUST return in < 500 ms (warm interpreter, SSD; a 200-mission corpus is not relevant — this is per-mission). Implementation-wise the gate reads at most:

1. `meta.json` (small).
2. `kitty-specs/<slug>/status.events.jsonl` filtered to retrospective events (constant-bounded for any single mission).
3. `.kittify/missions/<mission_id>/retrospective.yaml` (only if a `completed` event references it for hash verification).

No filesystem walk of the project is required. No network IO.

---

## Determinism

The same (event log content, charter content, env vars, parent-process metadata, `mode_override`) MUST produce the same `GateDecision`. Tests assert this by replaying the same fixture twice in a process and comparing.

---

## Caller patterns

### From `next` (canonical control loop)

```python
from specify_cli.retrospective import gate as retro_gate

decision = retro_gate.is_completion_allowed(
    mission_id=meta.mission_id,
    feature_dir=feature_dir,
    repo_root=repo_root,
)
if not decision.allow_completion:
    raise MissionCompletionBlocked(decision)
```

### From a status-transition surface

```python
from specify_cli.retrospective import gate as retro_gate

decision = retro_gate.is_completion_allowed(
    mission_id=mission_id,
    feature_dir=feature_dir,
    repo_root=repo_root,
)
if not decision.allow_completion and intends_mission_completion(transition):
    return TransitionRejected(reason=decision.reason)
```

Mission-level policy never lives inside `specify_cli.status.transitions` itself. WP-level transitions remain governed by the existing per-WP transition matrix.

---

## Error contract

Errors raised by the gate are typed:

```python
class GateError(Exception): ...
class MissionIdentityMissing(GateError): ...
class EventLogUnreadable(GateError): ...
class ModeResolutionError(GateError): ...
```

Errors are **not** silently converted to `allow_completion=True`. They propagate to the caller, which surfaces them as structured runtime errors. (FR-011, CHK005, CHK006.)

---

## Fakes for tests

`specify_cli.retrospective.gate` exposes a `tests` namespace (or a sibling `tests/retrospective/_fakes.py`) with:

- a fake event-log builder that takes a list of envelope dicts and writes a JSONL file;
- a fake charter override loader that returns a `Mode` value without touching disk;
- a clock fixture so timestamps are deterministic.

Tests for the gate exercise every row in the decision matrix above.

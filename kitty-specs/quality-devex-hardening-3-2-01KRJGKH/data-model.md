# Data Model — Quality and DevEx Hardening 3.2

**Mission**: `quality-devex-hardening-3-2-01KRJGKH`
**Plan**: [plan.md](plan.md)

This document describes the **value objects** introduced or modified by the mission. The mission is infrastructure-hygiene work, so there are no business entities — the data model is small and consists of pure value objects passed between modules.

Entities are presented per WP grouping. All entities are frozen dataclasses (or `typing.Protocol` for behavioral contracts). No mutation, no inheritance beyond `dataclass(frozen=True)`.

---

## 1. Canonicalization Rule Pipeline — FR-011 / WP03

### `CanonicalRule` (Protocol)

Per-step contract for the Transformer-flavor rule pipeline that lifts `_canonicalize_status_row` and its analogues onto a typed surface. Codified by the `chain-of-responsibility-rule-pipeline` tactic (Transformer flavor, see tactic notes).

**Location**: `src/specify_cli/migration/canonicalization.py`

**Shape**:

```python
from typing import Protocol, TypeVar

State = TypeVar("State")

class CanonicalRule(Protocol[State]):
    """Per-step contract: check applicability, optionally act, return result."""
    def __call__(self, state: State, ctx: "MigrationContext") -> "CanonicalStepResult[State]":
        ...
```

**Invariants**:

- The function MUST be pure (no I/O, no globals, no in-place mutation of `state` beyond the returned value).
- A rule that does not apply returns `CanonicalStepResult.passthrough(state)` — the runner sees a no-op result and continues.
- A rule that detects a hard error returns `CanonicalStepResult(state=state, actions=(...), error=<reason>)` — the runner short-circuits.
- The actions tuple is a part of the contract: callers (e.g. migration manifest rendering) consume it.

**Composition**:

```python
def apply_rules(
    rules: Sequence[CanonicalRule[State]],
    state: State,
    ctx: MigrationContext,
) -> CanonicalPipelineResult[State]:
    """Runner: thread state through rules; short-circuit on error."""
```

### `CanonicalStepResult[State]` (frozen dataclass)

Output of a single rule application.

**Shape**:

```python
@dataclass(frozen=True)
class CanonicalStepResult(Generic[State]):
    state: State
    actions: tuple[str, ...] = ()
    error: str | None = None

    @classmethod
    def passthrough(cls, state: State) -> "CanonicalStepResult[State]":
        """A rule that did not apply."""
        return cls(state=state, actions=(), error=None)
```

**Invariants**:

- `error is not None` ⇒ runner short-circuits, returning `CanonicalPipelineResult(error=...)`.
- `error is None` and `actions == ()` is the passthrough idiom — runner continues with unchanged state.
- `actions` is a tuple (not list) — immutable; safe to thread across rule boundaries without defensive copying.

### `CanonicalPipelineResult[State]` (frozen dataclass)

Output of the runner.

**Shape**:

```python
@dataclass(frozen=True)
class CanonicalPipelineResult(Generic[State]):
    state: State | None       # None when error is set
    actions: tuple[str, ...]  # accumulated across all rules
    error: str | None         # short-circuit reason; None on success
```

**Invariants**:

- `error is None` ⇒ `state is not None`; the pipeline completed.
- `error is not None` ⇒ `state is None`; `actions` includes whatever rules ran before the short-circuit.

### `MigrationContext` (frozen dataclass)

Per-pipeline context. Generic across migration shapes (status events, frontmatter, sync envelopes).

**Shape**:

```python
@dataclass(frozen=True)
class MigrationContext:
    mission_slug: str
    mission_id: str
    line_number: int             # for log / quarantine attribution
    generated_ids: list[str] | None = None  # accumulator for minted ids
```

**Invariants**:

- The mission identity fields are required and immutable.
- `generated_ids` is the one mutable element on the context — by design, rules append minted IDs here so the caller can see them. Documented exception; safe because the caller owns the list and the rules use `.append()` only.

### Bootstrap of `_canonicalize_status_row` onto the Protocol

Pre-extraction (current code shape):

```python
def _canonicalize_status_row(data, *, mission_slug, mission_id, line_number, generated_ids=None) -> _CanonicalRowResult:
    # ~80 lines of sequential rules: aliases → strip-legacy → stamp-identity → mint-id → defaults → require-fields → normalize-lanes
```

Post-extraction:

```python
_RULES: tuple[CanonicalRule[Row], ...] = (
    _rule_reject_non_status_event,
    _rule_apply_aliases,
    _rule_strip_legacy_keys,
    _rule_stamp_identity,
    _rule_mint_event_id,
    _rule_default_at,
    _rule_default_from_lane,
    _rule_require_to_lane,
    _rule_require_wp_id,
    _rule_normalize_lanes,
)

def _canonicalize_status_row(data, *, mission_slug, mission_id, line_number, generated_ids=None) -> _CanonicalRowResult:
    ctx = MigrationContext(mission_slug=mission_slug, mission_id=mission_id, line_number=line_number, generated_ids=generated_ids)
    result = apply_rules(_RULES, dict(data), ctx)
    return _CanonicalRowResult.from_pipeline(result)
```

Same shape lifts `rebuild_state.py` rules; the WP03 prompt documents the lift.

---

## 2. Upgrade Probe and Notifier — FR-007 / WP09

### `UpgradeProbeResult` (frozen dataclass)

Output of the PyPI probe.

**Location**: `src/specify_cli/core/upgrade_probe.py`

**Shape**:

```python
@dataclass(frozen=True)
class UpgradeProbeResult:
    installed_version: str       # what get_cli_version() returned
    latest_pypi_version: str | None  # None if PyPI returned no usable response
    channel: UpgradeChannel
    probed_at: datetime          # UTC, ISO-8601 serialized in cache
    error: str | None = None     # populated when channel == UNKNOWN
```

### `UpgradeChannel` (StrEnum)

```python
class UpgradeChannel(StrEnum):
    ALREADY_CURRENT = "already_current"
    AHEAD_OF_PYPI = "ahead_of_pypi"
    NO_UPGRADE_PATH = "no_upgrade_path"
    UPGRADE_AVAILABLE = "upgrade_available"
    UNKNOWN = "unknown"
```

**Channel rules** (from research §5):

| Condition | Channel |
|---|---|
| HTTP 200, installed version equals latest PyPI release | `ALREADY_CURRENT` |
| HTTP 200, installed version > latest PyPI release (e.g. RC / dev build) | `AHEAD_OF_PYPI` |
| HTTP 200, installed version not in PyPI `releases` table | `NO_UPGRADE_PATH` |
| HTTP 200, installed version is in PyPI `releases` table but older than latest | `UPGRADE_AVAILABLE` |
| HTTP error, network failure, or timeout | `UNKNOWN` (with `error` populated) |

### Cache schema

**Path**: `~/.cache/spec-kitty/upgrade-check.json` (POSIX) / `%LOCALAPPDATA%\spec-kitty\upgrade-check.json` (Windows).

**Schema**:

```json
{
  "installed_version": "3.2.0rc7",
  "latest_pypi_version": "3.2.0rc7",
  "channel": "already_current",
  "probed_at": "2026-05-14T05:50:00+00:00",
  "error": null,
  "ttl_seconds": 86400
}
```

**TTL rules**:

- Successful probe (`channel ∈ {ALREADY_CURRENT, AHEAD_OF_PYPI, NO_UPGRADE_PATH, UPGRADE_AVAILABLE}`): `ttl_seconds=86400` (24 h).
- Failed probe (`channel == UNKNOWN`): `ttl_seconds=3600` (1 h). Shorter retry window prevents users from being stuck without notices during a transient PyPI outage.

**Invariants**:

- The cache file is best-effort. A read failure (corrupted file, missing parent dir) treats the entry as expired and the probe runs again.
- The cache is per-user, not per-project.

### `UpgradeNotifier` (callable)

**Location**: `src/specify_cli/core/upgrade_notifier.py`

**Contract**:

```python
def maybe_emit_upgrade_notice(
    cli_version: str,
    *,
    console: Console | None = None,
    now: datetime | None = None,
    cache_path: Path | None = None,
) -> bool:
    """
    Returns True if a notice was emitted, False otherwise.

    Behavior:
      1. If SPEC_KITTY_NO_UPGRADE_CHECK=1 is set → return False (no probe, no notice).
      2. Load cache; if entry valid (within TTL), use it. Otherwise probe PyPI.
      3. Emit a one-line notice on console matching the channel.
      4. Cache the result. Refresh probed_at + ttl on every successful read.
      5. Suppress identical-channel notices within the TTL window.

    Never blocks longer than 100ms on the hot path (NFR-004).
    """
```

**Invariants**:

- Probe failures are swallowed silently (`channel = UNKNOWN`, no exception bubbling).
- No notice when `channel == ALREADY_CURRENT` AND the previous cache entry was also `ALREADY_CURRENT` within the TTL window (suppress identical repeats, AC #4).
- No notice when `channel == UPGRADE_AVAILABLE`; the existing upgrade nag owns that path.
- Cold-cache budget: up to 300 ms allowed once per 24 h (NFR-004 carve-out).

---

## 3. Auto-Rebase Conflict Classification — FR-006 / WP08

### `ConflictClassification` (frozen dataclass)

Output of the file-pattern classifier.

**Location**: `src/specify_cli/merge/conflict_classifier.py`

**Shape**:

```python
@dataclass(frozen=True)
class ConflictClassification:
    file_path: Path
    hunk_text: str            # the conflict region as git emitted it
    resolution: Resolution
```

### `Resolution` (sealed union via `dataclass`)

```python
@dataclass(frozen=True)
class Auto:
    """Auto-resolve: return the merged text. The classifier emits this."""
    merged_text: str
    rule_id: str  # which classifier rule produced this; for audit log

@dataclass(frozen=True)
class Manual:
    """Halt and surface to operator. Default for any unmatched pattern."""
    reason: str

Resolution = Auto | Manual
```

**Invariants**:

- Any input not matching an explicit classifier rule resolves to `Manual` with a reason citing the unmatched pattern. This is the **fail-safe default** (NFR-005).
- `Auto` carries a `rule_id` so the audit log can trace which rule fired.
- `merged_text` in `Auto` is the complete merged file region — the auto-rebase orchestrator writes it back atomically.

### Classifier rules (from research §3)

The ADR draft in `contracts/stale-lane-auto-rebase-classifier-policy.md` enumerates each rule with examples and counter-examples. Summary:

| Rule ID | File pattern | Conflict shape | Resolution |
|---|---|---|---|
| `R-PYPROJECT-DEPS-UNION` | `pyproject.toml` `[project.dependencies]` or `[dependency-groups.*]` | Both sides added distinct entries | `Auto(union of entries, dedup by name)` |
| `R-UVLOCK-REGENERATE` | `uv.lock` | Any conflict | (post-merge step: `uv lock --no-upgrade` under file lock; not classified as `Auto`/`Manual` because the file is regenerated, not merged) |
| `R-INIT-IMPORTS-UNION` | `*/__init__.py` import block | Both sides added distinct `from X import Y` lines | `Auto(union of imports, ruff-canonical order)` |
| `R-URLS-LIST-UNION` | `urls.py` (or analogous `_URLS = [...]` constant) | Both sides added distinct list entries | `Auto(union of entries, preserve original sort order)` |
| `R-DEFAULT-MANUAL` | (any unmatched file) | (any) | `Manual(reason="no classifier rule matched")` |

**Invariants**:

- Rules are ordered; first match wins. `R-DEFAULT-MANUAL` is always last.
- `R-UVLOCK-REGENERATE` is special — it does not emit a `Resolution`; it triggers a post-merge regeneration step in the orchestrator that holds a global `specify_cli.core.file_lock`.

### `AutoRebaseReport` (frozen dataclass)

Output of the orchestrator for a single mission's merge.

**Location**: `src/specify_cli/lanes/auto_rebase.py`

**Shape**:

```python
@dataclass(frozen=True)
class AutoRebaseReport:
    lane_id: str
    attempted: bool                        # False if lane wasn't stale to begin with
    succeeded: bool                        # True iff every conflict resolved to Auto
    classifications: tuple[ConflictClassification, ...]
    halt_reason: str | None                # set when succeeded=False; cites the first Manual
```

**Invariants**:

- `succeeded == True` ⇒ every `classifications[i].resolution` is `Auto`.
- `succeeded == False` ⇒ exactly one or more `classifications[i].resolution` is `Manual`; `halt_reason` cites the first `Manual.reason`.
- `attempted == False` ⇒ `classifications == ()` and `succeeded == True` (the lane was not stale; nothing to rebase).

---

## Validation rules summary

| Invariant | Where enforced |
|---|---|
| `CanonicalRule` returns no error ⇒ pipeline continues; error ⇒ pipeline halts | Runner in `migration/canonicalization.py::apply_rules` |
| `CanonicalStepResult.actions` is a tuple, never a list | Type system + `dataclass(frozen=True)` |
| `UpgradeChannel == UNKNOWN` ⇔ `error is not None` | `UpgradeProbeResult.__post_init__` validation |
| `UpgradeNotifier` swallows all probe exceptions | `maybe_emit_upgrade_notice` body |
| `ConflictClassification.resolution` defaults to `Manual` on unmatched pattern | Classifier `R-DEFAULT-MANUAL` rule always last |
| `AutoRebaseReport.halt_reason` is set iff `succeeded == False` | `__post_init__` validation |

## State transitions

The mission introduces no state machines. The Transformer pipeline runs once per row; the upgrade probe runs once per cache miss; the auto-rebase orchestrator runs once per stale lane and produces a one-shot report.

The existing status-event state machine in `src/specify_cli/status/transitions.py` is **not modified** by this mission — the canonicalization refactor preserves the existing transition contract (FR-009, NFR-003).

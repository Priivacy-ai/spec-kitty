# Contract — Canonicalization Rule Pipeline

**Mission**: `quality-devex-hardening-3-2-01KRJGKH`
**Requirement**: FR-011
**Module**: `src/specify_cli/migration/canonicalization.py` (new)
**Tactic**: [`chain-of-responsibility-rule-pipeline`](../../../src/doctrine/tactics/shipped/code-patterns/chain-of-responsibility-rule-pipeline.tactic.yaml) — Transformer flavor

## Purpose

Lift the implicit Transformer pipeline that currently lives flattened in `_canonicalize_status_row` onto a typed Protocol so that:

1. Each rule is independently testable as a pure function.
2. Rule ordering becomes explicit and auditable.
3. A second consumer (`rebuild_state.py` rule sequence) reuses the same Protocol — the two-consumer bar for an abstraction is met.
4. Future migration code (frontmatter migration, sync envelope canonicalization) has an opinionated shape to follow.

## Public surface

```python
# src/specify_cli/migration/canonicalization.py

from typing import Protocol, TypeVar, Generic, Sequence
from dataclasses import dataclass

State = TypeVar("State")


@dataclass(frozen=True)
class MigrationContext:
    mission_slug: str
    mission_id: str
    line_number: int
    generated_ids: list[str] | None = None


@dataclass(frozen=True)
class CanonicalStepResult(Generic[State]):
    state: State
    actions: tuple[str, ...] = ()
    error: str | None = None

    @classmethod
    def passthrough(cls, state: State) -> "CanonicalStepResult[State]":
        return cls(state=state, actions=(), error=None)


@dataclass(frozen=True)
class CanonicalPipelineResult(Generic[State]):
    state: State | None
    actions: tuple[str, ...]
    error: str | None


class CanonicalRule(Protocol[State]):
    def __call__(self, state: State, ctx: MigrationContext) -> CanonicalStepResult[State]:
        ...


def apply_rules(
    rules: Sequence[CanonicalRule[State]],
    state: State,
    ctx: MigrationContext,
) -> CanonicalPipelineResult[State]:
    """Thread state through rules; short-circuit on the first error."""
    accumulated_actions: list[str] = []
    current = state
    for rule in rules:
        result = rule(current, ctx)
        accumulated_actions.extend(result.actions)
        if result.error is not None:
            return CanonicalPipelineResult(
                state=None,
                actions=tuple(accumulated_actions),
                error=result.error,
            )
        current = result.state
    return CanonicalPipelineResult(
        state=current,
        actions=tuple(accumulated_actions),
        error=None,
    )
```

## Invariants

- A rule is a **pure function**: no I/O, no globals, no in-place mutation of `state` beyond the returned value.
- A rule that does not apply MUST return `CanonicalStepResult.passthrough(state)`. It does not raise to signal "not applicable".
- A rule that detects a hard error MUST return `CanonicalStepResult(state=state, actions=..., error=<reason>)`. The runner short-circuits.
- The `actions` tuple is part of the contract — callers consume it for migration manifests / audit trails.
- `MigrationContext.generated_ids` is the **one** mutable element on the context, by design: rules append minted IDs so the caller observes them. Documented exception.

## Composition rules

- Rules are declared as an ordered `tuple[CanonicalRule[State], ...]` at module scope. Tuple, not list, to signal immutability.
- Order is **part of the contract**: early-exit / sanity rules first, then renames / normalizations, then defaults, then validation.
- Adding or removing a rule is a localized change: only the rule body and the tuple entry. No re-reading of the whole pipeline.

## Testing contract

Per `function-over-form-testing` + `tdd-red-green-refactor`:

1. **Characterization tests first** (before the refactor commit). Fixture rows drawn from `.kittify/migrations/mission-state/` capture today's canonicalization output for the monolithic `_canonicalize_status_row`. The refactor commit MUST leave those tests green.
2. **Per-rule unit tests** (`tests/unit/migration/test_canonicalization_rules.py`). Parametrized `(input_state, ctx, expected_result)` triples per rule. Pure value-transformer tests — no structural assertions.
3. **End-to-end pipeline tests** (`tests/integration/migration/test_canonicalization_pipeline.py`). Realistic input fixtures; assert on final `CanonicalPipelineResult.state` and `actions` tuple.
4. **No tests on the runner** beyond the obvious short-circuit assertion. The runner is a 10-line function; testing rule interaction is the integration layer's job.

## Migration of `_canonicalize_status_row`

Pre-refactor body (motivating example, ~80 lines):

```python
def _canonicalize_status_row(data, *, mission_slug, mission_id, line_number, generated_ids=None):
    if "event_type" in data or "event_name" in data:
        return _CanonicalRowResult(row=None, actions=("quarantined_non_status_event",))
    row = dict(data)
    actions = []
    for old, new in STATUS_ROW_ALIASES.items():
        ...
    for key in sorted(FORBIDDEN_LEGACY_KEYS - {"feature_slug"}):
        ...
    row["mission_slug"] = ...
    row["mission_id"] = ...
    if not _valid_event_id(row.get("event_id")):
        ...
    if not row.get("at"):
        ...
    if row.get("from_lane") is None:
        ...
    if not row.get("to_lane"):
        return _CanonicalRowResult(row=None, actions=tuple(actions), error="missing required to_lane")
    if not row.get("wp_id"):
        return _CanonicalRowResult(row=None, actions=tuple(actions), error="missing required wp_id")
    for key in ("from_lane", "to_lane"):
        ...
    return _CanonicalRowResult(row=row, actions=tuple(actions))
```

Post-refactor:

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
    ctx = MigrationContext(
        mission_slug=mission_slug,
        mission_id=mission_id,
        line_number=line_number,
        generated_ids=generated_ids,
    )
    result = apply_rules(_RULES, dict(data), ctx)
    return _CanonicalRowResult.from_pipeline(result)
```

Each `_rule_*` function is ~5–10 lines, pure, individually testable.

## Reuse in `rebuild_state.py`

`migration/rebuild_state.py` contains an analogous rule sequence (different state shape — frontmatter dict instead of status-event row). The same Protocol covers it because `State` is generic. The two-consumer bar is met; the abstraction is justified per the `rule-pipeline-pattern-survey.md` recommendation.

## Architectural catalog update

When this contract lands, the WP that introduces `migration/canonicalization.py` updates `architecture/2.x/04_implementation_mapping/code-patterns.md` entry 1 to cite the new module as the canonical Transformer-flavor implementation. The existing catalog entry already names this module as the **planned** canonical implementation; the update flips "planned" to "in-tree".

## Out of scope for this contract

- **Validator-flavor pipelines** (existing in `audit/`, `charter_lint/`). They use a different return type (`list[Finding]`) and a different runner. The unifying tactic notes describe both flavors; the Protocols stay distinct.
- **Scorer-flavor pipelines** (existing in `agent_profiles/repository.py`). One consumer only; not abstracted.
- **Generalization of the runner** to a generic `RuleEngine` covering all three flavors. Rejected in `work/findings/rule-pipeline-pattern-survey.md` — the shapes are different abstractions, not one.

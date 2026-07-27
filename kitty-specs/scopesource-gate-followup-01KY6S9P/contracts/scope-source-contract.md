# Contract: `ScopeSource` predicates, factory port, and breakdown mixin

**Traces**: FR-003, FR-005, FR-006, FR-007, NFR-005
**Home**: `src/specify_cli/review/scope_source.py` · **Consumers**: `pre_review_gate.py`,
`tasks_move_task.py`, `baseline.py`

This contract replaces the single welded `isinstance(scope_source, ScopeBreakdownSource)` decision
(two sites: `pre_review_gate.py:881` and `:1013`) with two independently-evaluable predicates, hoists
the source factory to one shared home, and makes `file_to_scope` a default projection over
`scope_breakdown` via an ABC/mixin.

## Two independent predicates (FR-005)

Each predicate reads a **different signal**, so a source may satisfy one without the other.

| Predicate | Signature | Backing signal | `GateCoverageScopeSource` | `DeclaredCommandScopeSource` | Synthetic split |
|-----------|-----------|----------------|---------------------------|------------------------------|-----------------|
| `exposes_scope_breakdown` | `(source: ScopeSource) -> bool` | `isinstance(source, ScopeBreakdownSource)` (has `scope_breakdown`) | `True` | `False` | may be `True` while policy `False` |
| `empty_scope_is_coverage_gap` | `(source: ScopeSource) -> bool` | `getattr(source, "treats_empty_scope_as_coverage_gap", False)` (ClassVar marker) | `True` | `False` | may be `True` while capability `False` |

**Invariant (weld removed, not renamed).** The two predicates MUST NOT share a signal. A test
constructs a synthetic source that satisfies exactly one (US3 AS3) and asserts each predicate returns
its declared value independently.

**Consumer rewrite:**

```python
# round-trip: skip: illustrative call-site rewrite — executable behaviour in tests/review/test_pre_review_gate_engine.py
# pre_review_gate.py:881  (policy site — empty derived scope ⇒ NO_COVERAGE)
if empty_scope_is_coverage_gap(scope_source) and scope.is_empty:
    return GateVerdict(outcome=GateOutcome.NO_COVERAGE, scope=scope, reason=scope.describe_empty_reason())

# pre_review_gate.py:1013  (capability site — build the full breakdown metadata)
if exposes_scope_breakdown(scope_source):
    return _scope_result_from_breakdown(scope_source, changed_files)
```

**Behaviour preservation (FR-005/FR-007).** For the two shipped sources the verdict is byte-identical
to the pre-split `isinstance` behaviour: `GateCoverageScopeSource` → both `True`;
`DeclaredCommandScopeSource` → both `False`.

## `file_to_scope` as a default projection (FR-006)

An ABC/mixin (proposed `ScopeBreakdownMixin`) — NOT a `Protocol` default, which never reaches a
structural implementer:

```python
# round-trip: skip: illustrative mixin shape — executable behaviour in tests/review/test_scope_source.py
class ScopeBreakdownMixin(abc.ABC):
    treats_empty_scope_as_coverage_gap: ClassVar[bool] = True

    @abc.abstractmethod
    def scope_breakdown(self, path: str) -> FileScopeBreakdown: ...

    def file_to_scope(self, path: str) -> tuple[str, ...]:
        return self.scope_breakdown(path).test_targets
```

| Class | Inherits mixin | Defines `scope_breakdown` | Defines `file_to_scope` | `treats_empty_scope_as_coverage_gap` |
|-------|----------------|---------------------------|-------------------------|--------------------------------------|
| `GateCoverageScopeSource` | yes | yes | inherited (drops hand-written `:355-362`) | `True` |
| `DeclaredCommandScopeSource` | no (structural `ScopeSource`) | no | `() ` always (`:508-516`) | `False` (default) |

**Obligation.** `GateCoverageScopeSource` still satisfies both `ScopeSource` and
`ScopeBreakdownSource` structurally; `DeclaredCommandScopeSource` still satisfies `ScopeSource`
structurally with no `scope_breakdown`. `@runtime_checkable isinstance` checks are unchanged.

## Shared factory port (FR-003 / NFR-005)

```python
# round-trip: skip: illustrative factory signature — executable behaviour in tests/review/test_scope_source_factory.py
def resolve_scope_source(
    repo_root: Path,
    *,
    filter_groups_override: Mapping[str, tuple[str, ...]] | None = None,
    composite_routing_override: Mapping[str, _CompositeRoute] | None = None,
) -> ScopeSource:
    """The single authority both baseline capture and the head hook resolve through."""
    return GateCoverageScopeSource(
        repo_root=repo_root,
        filter_groups_override=filter_groups_override,
        composite_routing_override=composite_routing_override,
    )
```

| Caller | Home | Override args | Result |
|--------|------|---------------|--------|
| `_mt_resolve_scope_source` (head hook) | `tasks_move_task.py:1250` | `_pre_review_gate_filter_groups()` / `_pre_review_gate_composite_routing()` (both `None` in prod) | wrapper threads the test seams; no import back into `tasks_move_task` |
| `implement_capture_baseline` (baseline) | `workflow_executor.py:1153` | none (prod → `None`) | `capture_baseline(..., scope_source=resolve_scope_source(main_repo_root))` |

**No-import-cycle obligation (FR-003).** `resolve_scope_source` lives in `scope_source.py`, already
imported by both `baseline.py:30` and `pre_review_gate.py:65-71`; it MUST NOT import
`tasks_move_task`. The seams are passed as parameters, never imported into the factory.

**Equivalence obligation (NFR-005).** For the same `repo_root` and config, the source resolved at
implement-time (baseline) and at `for_review` (head) is **equivalent** = equal `test_command()` output
AND equal parse-mode/identity (`scope_source_identity`, see `baseline-identity-contract.md`). A test
pins this so the baseline↔head split cannot re-open.

## What this contract does NOT change

- The `ScopeSource` / `ScopeBreakdownSource` port shapes (`scope_source.py:85-165`) — only
  `file_to_scope`'s *provenance* on `GateCoverageScopeSource` moves to the mixin.
- The private census derivation inside `scope_source.py` (`:195-411`) — it is the live derivation,
  untouched (C-002).
- `RawRunResult` / `FileScopeBreakdown` dataclasses (`:66-83`, `:126-145`).
</content>

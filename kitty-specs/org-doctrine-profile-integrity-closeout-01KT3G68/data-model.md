# Data Model — Org Doctrine Profile Integrity Close-Out

No new persistent entities. This mission touches the *semantics* of two existing surfaces and adds one facade. Documented for traceability.

## Touched value objects / contracts

### `DoctrineHealthReport` / `PackHealth` (existing — `src/specify_cli/cli/commands/_doctrine_health.py`)
- **Invariant restored (FR-001):** `report.healthy` is true **iff** every discovered profile across every layer loaded validly AND there are zero invalid/skipped profiles. An empty report (no profiles collected because loading raised) MUST NOT be `healthy=True`.
- **Surfacing rule:** an inline-ref-rejected profile appears in the report's invalid/skipped set with `{path, id, error_summary}` (same shape as a schema-invalid profile), so `doctor doctrine` shows it.

### `InlineReferenceRejectedError` contract (existing — `src/doctrine/agent_profiles/repository.py`)
- **State:** load-layer behavior unchanged (propagates / fail-closed for general callers — R1).
- **Consumer rule (FR-001/FR-003):** the doctor health collector catches it specifically and degrades the affected `PackHealth` to `healthy=False`; `diagnostics.py` documentation is reconciled to describe this propagate-then-surface flow (no contradiction).

### `SkippedProfile` (existing — `src/doctrine/agent_profiles/diagnostics.py`)
- Unchanged shape; its docstring's enumeration of failure reasons is corrected for consistency with the load contract (FR-003).

## New module (facade only — no model)

### `charter.template_catalog` (NEW — `src/charter/template_catalog.py`)
- Pure re-export ACL: `discover_templates`, `TemplateRef`, `TierRoot` from `doctrine.template_catalog`; declares `__all__`. No behavior, no new types (identity preserved, mirroring `charter.profiles`).

## Dead-symbol surface (FR-009)
- `events.py` drops `SignificanceEvaluatedPayload` / `TimeoutExpiredPayload` from `__all__` (canonical home: `…_internal_runtime/significance.py`); `_SYMBOL_ALLOWLIST` loses the two stale entries; `JsonlEventLog` stays (no `src/` caller, rationale retained).

## Boundary allowlist (FR-007)
- `tests/architectural/_baselines.yaml::test_runtime_charter_doctrine_boundary.baseline_allowlist`: 2 → 0.
- `_BASELINE_ALLOWLIST` in the boundary test: `{activate.py, list_cmd.py}` → `{}` (empty).

## No state transitions / no externally visible events introduced.

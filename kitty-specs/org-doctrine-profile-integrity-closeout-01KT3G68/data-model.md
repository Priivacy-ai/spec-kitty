# Data Model — Org Doctrine Profile Integrity Close-Out

No new persistent entities. This mission touches the *semantics* of two existing surfaces and adds one facade. Documented for traceability.

## Touched value objects / contracts

### `DoctrineHealthReport` / `PackHealth` (existing — `src/specify_cli/cli/commands/_doctrine_health.py`)
- **Invariant restored (FR-001):** `report.healthy` is true **iff** every discovered profile across every layer loaded validly AND there are zero invalid/skipped profiles. An empty report (no profiles collected because loading raised) MUST NOT be `healthy=True`.
- **Surfacing rule:** an inline-ref-rejected profile appears in the report's invalid/skipped set with `{path, id, error_summary}` (same shape as a schema-invalid profile), so `doctor doctrine` shows it.

### `InlineReferenceRejectedError` contract (existing — `src/doctrine/agent_profiles/repository.py`)
- **State (REVISED — R1/A1/DD-1):** the **load layer** (`repository._load_layer`) catches it and calls `_record_skip`, so it becomes a recoverable, surfaced skip; valid sibling profiles still load (loading is eager/all-or-nothing, so a consumer-only catch cannot keep valid profiles visible). The exception's fields (`file_path`, `forbidden_field`, `artifact_kind`, `migration_hint`) plus the in-hand YAML give the `SkippedProfile` its `{layer, path, profile_id, error_summary}`.
- **Consumer rule (FR-001):** with the load-layer skip, `_collect_profile_health` sees a non-empty skipped set → reports `healthy=False` and surfaces the profile; no change to its broad-except is required, but the FR-001 edit target is the **load layer**, not just `doctor.py`.
- **Contract reconciliation (FR-003/I-9):** `diagnostics.py` (already calls it a skip) and the `repository.py` comment (currently "must propagate") are reconciled to "surfaced skip."
- **NOTE:** `PackHealth` is defined in **both** `_doctrine_health.py` and `diagnostics.py`; the FR-001 health invariant (`all([]) == True` green-on-empty) is at `_doctrine_health.py:112`. Tasks must target the correct definition.

### `SkippedProfile` (existing — `src/doctrine/agent_profiles/diagnostics.py`)
- Unchanged shape; its docstring's enumeration of failure reasons is corrected for consistency with the load contract (FR-003).

## New module (facade only — no model)

### `charter.template_catalog` (NEW — `src/charter/template_catalog.py`)
- Pure re-export ACL: `discover_templates`, `TemplateRef`, `TierRoot` from `doctrine.template_catalog`; declares `__all__`. No behavior, no new types (identity preserved, mirroring `charter.profiles`).

## Dead-symbol surface (FR-009)
- `events.py` drops `SignificanceEvaluatedPayload` / `TimeoutExpiredPayload` from `__all__` (canonical home: `…_internal_runtime/significance.py`); `_SYMBOL_ALLOWLIST` loses the two stale entries; `JsonlEventLog` stays (no `src/` caller, rationale retained).
- **KEEP the `import` lines** (A6): both symbols are used as type annotations in `events.py` (~lines 81/83/114/117) — only the `__all__` membership is removed, not the import.

## Boundary allowlist (FR-007)
- `tests/architectural/_baselines.yaml::test_runtime_charter_doctrine_boundary.baseline_allowlist`: 2 → 0.
- `_BASELINE_ALLOWLIST` in the boundary test: `{activate.py, list_cmd.py}` → `{}` (empty).

## No state transitions / no externally visible events introduced.

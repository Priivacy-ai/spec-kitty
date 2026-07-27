# Data Model — Workflow Parity Fixes 988/989/991

## New Types

### `ClaimablePreview` (in `src/specify_cli/next/`)

A frozen dataclass returned by a side-effect-free claim-discovery helper used by `next --json`.

| Field | Type | Description | Invariant |
|-------|------|-------------|-----------|
| `wp_id` | `str \| None` | The WP that `agent action implement` would claim, or `None` when no candidate can be selected. | If `None`, `selection_reason` MUST be non-`None`. |
| `selection_reason` | `str \| None` | A short stable token identifying why selection was suppressed. Examples: `"no_planned_wps"`, `"all_wps_in_progress"`, `"dependencies_unsatisfied"`, `"baseline_violation"`. | When `wp_id` is non-`None`, this field is `None`. |
| `candidates` | `tuple[str, ...]` | Ordered list of WP IDs the claim algorithm would have considered. | Deterministic by lane/order; identical to the order `start_implementation_status()` would have walked. |

Lifetime: per-invocation only; never persisted.

## New Diagnostic Codes

### `LIGHTWEIGHT_REVIEW_MISSING_BASELINE` (in `src/specify_cli/cli/commands/review/_diagnostics.py`)

Emitted by `scan_dead_code()` when called from the lightweight review path for a **modern** mission (one whose `meta.json` has a populated `mission_id`) whose `baseline_merge_commit` is `null`.

| Payload field | Type | Description |
|---------------|------|-------------|
| `code` | `str` | Always `"LIGHTWEIGHT_REVIEW_MISSING_BASELINE"`. |
| `mission_id` | `str` | The mission's canonical ULID. |
| `mission_slug` | `str` | The mission's human slug. |
| `remediation` | `str` | Stable hint string; for tests, the substring `"baseline_merge_commit"` MUST appear. |

### `LEGACY_MISSION_DEAD_CODE_SKIP` (optional, in `_diagnostics.py`)

Emitted in the **legacy** path so that the silent-skip behavior remains greppable. The lightweight review still returns a passing verdict on legacy missions but tags the verdict with this code so it cannot be confused with a true clean pass.

## Reused Types (no schema change)

- `MissionMeta` — read-only consumers are the only change point; the `mission_id` field already exists.
- `MissionReviewMode` (`src/specify_cli/cli/commands/review/_mode.py`) — unchanged.
- `WorkPackageClaimConflict` (`src/specify_cli/status/work_package_lifecycle.py`) — unchanged; the new helper does not raise this because it does not attempt to claim.
- `find_rejected_review_artifact_conflicts(...)` return shape — unchanged; just called from a new caller (dry-run).
- `REJECTED_REVIEW_ARTIFACT_CONFLICT` constant — unchanged.

## State Transitions

No new lane transitions are introduced. The 9-lane state machine (`planned → claimed → in_progress → for_review → in_review → approved → done`, plus `blocked`/`canceled`) is unchanged. The claim-discovery helper performs **no transition** — it computes the same candidate set `start_implementation_status()` would have used, then returns it.

## Invariants

- **I-001**: `ClaimablePreview.wp_id is None XOR selection_reason is None` — exactly one is set.
- **I-002**: `LIGHTWEIGHT_REVIEW_MISSING_BASELINE` is emitted only when `mission_id` is present in `meta.json` and `baseline_merge_commit` is `null`.
- **I-003**: `merge --dry-run` invokes `find_rejected_review_artifact_conflicts()` exactly once per dry-run invocation, before any merge preview output is emitted.

# Data Model — Planning-artifact WPs Own kitty-specs Paths

No datastore. The "entities" are the work-package ownership fields (WP frontmatter YAML) and the
derived ownership manifest that finalize-tasks reasons over.

## Entities

### Work Package (frontmatter)
| Field | Type | Role in this mission |
|-------|------|----------------------|
| `execution_mode` | `planning_artifact` \| `code_change` \| (unset→inferred) | The **decision key** for the exemption. `planning_artifact` → repo-root/planning lane; `code_change` → `.worktrees/` execution lane. |
| `owned_files` | list[str] (globs/paths) | Declared deliverables. Under `kitty-specs/<mission>/` for planning deliverables. |
| `authoritative_surface` | str | Must prefix at least one `owned_files` entry (unchanged hard-check); inference normally sets it consistently. |
| `create_intent` | list[str] | Suppresses zero-match errors for not-yet-existing declared deliverables. |

### Ownership Manifest (derived)
- Built by `build_wp_manifests` from frontmatter **iff** `execution_mode` and `owned_files` are both truthy.
- Consumed by `compute_lanes` to route the WP: `planning_artifact` → `lane-planning` (repo-root); `code_change` → execution lane.

## The exemption condition (refined post-plan, finding R-1)

The kitty-specs ban is lifted for a work package **iff BOTH**:
1. `execution_mode == planning_artifact` (compared against `ExecutionMode.PLANNING_ARTIFACT.value` / normalized — finding R-3), **and**
2. every `owned_files` entry is under a planning prefix — `_PLANNING_PREFIXES` (`kitty-specs/`, `docs/`), imported from `ownership.validation` (single authority, not re-derived).

Condition 2 is the **confinement guard**: a `planning_artifact` WP that *also* owns `src/`/`tests/` (or any non-planning path) is **not** exempted, so the kitty-specs path still trips the ban and the WP is rejected. This closes the mislabel hole where a planning-labelled WP could own code with only a warning.

## Ownership verdict — decision table (the behavior this mission defines)

| `execution_mode` | `owned_files` shape | Current | After fix |
|------------------|---------------------|---------|-----------|
| `planning_artifact` | kitty-specs only (or +`docs/`) | **REJECT** (`INVALID_WP_OWNED_FILES_KITTY_SPECS`) | **ACCEPT** → planning lane |
| `planning_artifact` | `docs/` only (no kitty-specs) | ACCEPT | ACCEPT (unchanged) |
| `planning_artifact` | kitty-specs **+ `src/`/`tests/`** | REJECT | **REJECT** (confinement — not exempted; INV-4) |
| `planning_artifact` | kitty-specs + other non-planning (`scripts/`) | REJECT | REJECT (not fully confined → not exempted; also WARN) |
| unset → inferred `planning_artifact` | kitty-specs only | REJECT | **ACCEPT** → planning lane (inference sets mode; row added post-plan, finding A-2) |
| `code_change` | owns any kitty-specs path | REJECT | **REJECT** (unchanged, fail-closed) |
| unset → inferred `code_change` (has a code signal) | owns any kitty-specs path | REJECT | **REJECT** (unchanged, fail-closed) |
| two `planning_artifact` WPs, overlapping kitty-specs scopes, no dep edge | — | REJECT (ban) | **REJECT** (`validate_no_overlap`, downstream; finding A-1) |
| any | no kitty-specs path | ACCEPT | ACCEPT (unchanged) |

## Invariants
- **INV-1 (fail-closed)**: a `code_change` work package owning any `kitty-specs/` path is always rejected.
- **INV-2 (mode-keyed exemption, path-shaped inference)**: the *predicate* grants the exemption on `execution_mode == planning_artifact` (plus the INV-4 confinement), never on the raw path prefix at the predicate boundary. For a WP with *unset* mode, ownership inference may use path signals to derive the mode — but any code signal (`src/`/`tests/`/`.py`) forces `code_change`, so a path-shaped inference can only ever move a WP toward the fail-closed side.
- **INV-3 (no silent placement change)**: an accepted planning work package routes to the planning lane (repo-root; `wp_id in compute_lanes(...).planning_artifact_wps`), never a `.worktrees/` branch.
- **INV-4 (confinement)**: the exemption applies only when every `owned_files` entry is under `_PLANNING_PREFIXES`; a `planning_artifact` WP owning any non-planning path is not exempted.

## Deliverable durability (finding D-2, filename-scoped)

A legitimized `kitty-specs/` deliverable survives lane merge / `auto_rebase` **only when** `kind_for_mission_file(path) is None`. `auto_rebase` take-theirs manages `{WORK_PACKAGE_TASK, LANE_STATE, ANALYSIS_REPORT}` kinds, so a planning deliverable named `analysis-report.md` or `tasks/WP*.md` **is** reconciled (clobbered) — the durability guarantee (C-003) is scoped to non-managed filenames and this carve-out is asserted by a negative test rather than left implicit.

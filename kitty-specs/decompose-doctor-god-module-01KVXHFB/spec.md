# Mission Specification — Decompose `doctor.py` God-Module (Residual)

**Mission type:** software-dev · **Branch (planning = merge base):** `prog/2059-doctor` (non-protected program branch; lands on `main`).

## Overview

`src/specify_cli/cli/commands/doctor.py` is a **3434-LOC god module** hosting the `spec-kitty doctor` CLI group: a `typer.Typer(name="doctor", ...)` app, **16 subcommands**, and eleven cohesive clusters of helper functions. It already carries a tracked god-module pointer comment (`doctor.py:1-7`) referencing this ticket (**#2059**) and the prior partial extraction that landed in closed **#1623**.

#1623 extracted exactly two sibling modules and stopped: `_doctrine_health.py` (health MODEL: `PackHealth`, `DoctrineHealthReport`, `build_pack_health_by_layer`) and `_profile_health_render.py` (doctrine RENDER helpers + the shared `console` singleton). It deliberately left the **doctrine-health DATA COLLECTORS** (`_collect_profile_health`, `_attach_pack_health`, `_build_pack_entries`, `_collect_org_layer_data`, `_collect_doctrine_collisions`, `_build_selection_block`, etc.) behind in `doctor.py` — an incomplete seam.

This mission decomposes the **residual** into cohesive, independently-testable sibling modules plus a thin orchestration surface, **completing the doctrine-health collector seam #1623 left behind** and **mirroring the `_doctrine_health.py` sibling-module precedent**. The public `spec-kitty doctor` CLI surface — all 16 subcommand names, every flag, help text, and exit-code contract — must remain **byte-for-byte identical** before vs after. This is a behavior-preserving refactor: no command, flag, name, or output changes.

Two named circular-import hazards (from research §6) gate the design:

- **H1 — shared console/guards home.** `console` (and `_json_output_guard`/`_json_error`) must have exactly one canonical home that every sibling and the orchestrator import from. A per-module `Console()` breaks `--json` stdout cleanliness and the byte-pinned doctrine-selections snapshot.
- **H2 — `merge` cross-import.** `_check_tracked_worktrees_content` imports `specify_cli.cli.commands.merge.path_is_under_worktrees` *inside the function body*. That import must stay **function-local** in the extracted coordination sibling or a `doctor↔merge` module-load cycle reappears.

## User Scenarios & Testing

- **CLI surface is unchanged (operator).** An operator runs any of the 16 `spec-kitty doctor <subcommand> [--flags]` commands before and after the refactor. Success: identical subcommand set, identical flags, identical `--help` text, identical exit codes for every documented path (e.g. `doctor skills` 0/1/2, `doctor restart-daemon` 0/1/2/3, `doctor ops --threshold` without `--close-stale` raises `BadParameter`, `doctor mission-state` mode-exclusivity). A golden characterization harness captured FIRST (WP01) proves this byte-for-byte.

- **Tests keep importing private symbols from `doctor` (maintainer).** The existing 58 test files that `from specify_cli.cli.commands.doctor import ...` continue to resolve `app`, `SlashCommandGap`, and the 11 test-facing private symbols. Success: every symbol re-exports from the `doctor` shim (mirroring the `_profile_health_render` re-export precedent); the full suite stays green with no test-import edits required.

- **Cross-module CLI coupling survives (maintainer).** `compat/safety_modes.py:186-194` keys safety predicates on the command-path tuples `("doctor",)`, `("doctor","skills")`, `("doctor","sparse-checkout")`; `__init__.py` argv fast-paths (`_is_doctor_skills_invocation`, `_is_doctor_restart_daemon_invocation`) key on the `doctor skills` / `doctor restart-daemon` name strings. Success: because subcommand names are preserved byte-for-byte, these continue to fire; the golden harness explicitly covers those three names.

- **Doctrine-health collector seam is completed (maintainer).** The doctrine-health DATA COLLECTORS #1623 left in `doctor.py` move into a sibling collector module (`_doctrine_collect.py`), beside the existing `_doctrine_health.py` (MODEL) and `_profile_health_render.py` (RENDER). Success: the model/render/collect triad is cohesive; the byte-pinned doctrine snapshot tests stay green.

- **Mega-functions reach the complexity ceiling (maintainer).** The six >15-CC functions (`skills` CC20, `identity` 19, `sparse_checkout` 19, `_check_lane_sparse_checkout_drift` 19, `state_roots` 17, `_repair_command_skill_state` 16) are decomposed into ≤15-CC sub-helpers *as part of* their cluster extraction (not merely relocated oversized), each new helper carrying focused tests.

### Edge cases

- A sibling must not re-instantiate `Console()`; importing from anywhere but the canonical `_doctor_shared` home is a regression (H1).
- Hoisting the `merge.path_is_under_worktrees` import to module scope in the coordination sibling reintroduces the `doctor↔merge` cycle (H2) — keep it function-local.
- A mega-function relocated at >15 CC (without decomposition) fails the complexity gate even though tests pass — decomposition is mandatory, not optional.
- Moving a test-facing private symbol without re-exporting it from `doctor` breaks existing test imports — re-export is required (the lower-risk path vs editing 58 test files).
- The `mission_state` command carries an explicit `# noqa: C901` but is already dispatch-thin; the suppression may be dropped once its helpers move with it — do not add new suppressions anywhere.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | **Frozen CLI surface.** The public `spec-kitty doctor` CLI surface — all 16 subcommands (`command-files`, `skills`, `tool-surfaces`, `state-roots`, `workspaces`, `identity`, `topology`, `sparse-checkout`, `shim-registry`, `invocation-pairing`, `ops`, `orphan-daemons`, `restart-daemon`, `mission-state`, `doctrine`, `coordination`) with every flag/arg and the documented exit-code contract — stays **byte-identical** before vs after. Proven by a golden characterization harness (WP01). | Approved |
| FR-002 | **Pointer comment.** The top-of-file god-module pointer comment references **#2059** (research confirms it already does at `doctor.py:1-7`). Verify and preserve it; do not add new responsibilities to `doctor.py` while it remains tracked. | Approved |
| FR-003 | **Extract research-resolved siblings + complete the doctrine seam.** Extract the research-resolved sibling modules — `_doctrine_collect`, `_identity_audit`, `_command_surface_doctor`, `_mission_state_doctor`, `_coordination_doctor`, `_sparse_checkout_doctor`, `_workspace_husk_doctor`, `_daemon_doctor`, and `_doctor_shared` (canonical console/guards/constants home). `_doctrine_collect` **completes the doctrine-health collector seam #1623 left in `doctor.py`**. Do **NOT** re-extract `_doctrine_health.py` / `_profile_health_render.py` (already done by #1623). | Approved |
| FR-004 | **Focused sibling tests.** Each new sibling module carries focused tests achieving **≥90%** line coverage of the extracted code, executing the new branches/helpers directly (not only via broad integration). | Approved |
| FR-005 | **Decompose >15-CC functions.** Internally decompose every function above the complexity ceiling — `skills` (CC20), `identity` (19), `sparse_checkout` (19), `_check_lane_sparse_checkout_drift` (19), `state_roots` (17), `_repair_command_skill_state` (16) — into ≤15-CC sub-helpers, extracting render/scan/repair subroutines and adding focused tests for each. Relocating a function oversized is a defect. | Approved |
| FR-006 | **Re-export contract + name preservation.** Re-export the 11 test-imported private symbols (`SlashCommandGap`, `_load_slash_command_state`, `_repair_slash_command_state`, `_collect_profile_health`, `_collect_org_layer_data`, `_build_pack_entries`, `_count_pack_artifacts`, `_resolve_pack_version`, `_render_org_layer_section`, `_print_overdue_details`) plus `app` from the `doctor` shim (mirror the `_profile_health_render` `from ._x import _y as _y` precedent). Preserve every subcommand-name string — `compat/safety_modes.py:186-194` and the `__init__.py` argv fast-paths key on them. | Approved |
| FR-007 | **Avoid circular imports.** A single canonical `console`/guards/constants home in `_doctor_shared` (or `console` re-exported through it) imported by every sibling + the orchestrator — never a per-module `Console()` (H1). Keep `merge.path_is_under_worktrees` import **function-local** in `_coordination_doctor` to avoid the `doctor↔merge` cycle (H2). Import direction stays one-way: orchestrator → sibling → `_doctor_shared` → external packages; no sibling↔sibling or sibling→orchestrator imports. | Approved |

## Non-Functional Requirements

- **NFR-001 — complexity ceiling.** Every function post-extraction is `maxCC ≤ 15` (Ruff `C901` / Sonar `S3776`). No function relocated or created above the ceiling.
- **NFR-002 — coverage.** Each new sibling module is `≥ 90%` line-covered by focused tests landing in the same WP as the extraction.
- **NFR-003 — clean gates, no new suppressions.** New/touched code passes `ruff` and `mypy --strict` with zero issues and zero warnings; **no new `# noqa`, `# type: ignore`, or per-file ignores**. Existing `# noqa: C901` on `mission_state` may be dropped if its helpers move with it; nothing new added.
- **NFR-004 — behavior-preserving.** No change to command names, flags, help text, output bytes, or exit codes. The byte-pinned doctrine-selections snapshot and `doctor skills --json` schema baseline stay green.

## Constraints

- **C-001 — no command/flag/name changes.** No subcommand renamed/added/removed; no flag added/removed/renamed; no help-text or output-byte drift. The 16-subcommand frozen contract (FR-001) is absolute.
- **C-002 — mirror the `_doctrine_health.py` sibling precedent.** Extraction topology follows the #1623 sibling-module + re-export style already established beside `doctor.py`. Do not invent a new packaging convention; do not create a `_misc` catch-all (it re-creates a mini-god-module).
- **C-003 — behavior-preserving refactor.** Logic moves, it does not change. Each extraction is validated against the WP01 golden harness (byte-identical pre/post) before the WP closes.
- **C-004 — no new suppressions.** Per NFR-003: fix complexity by decomposition, not by suppressing `C901`/`S3776`.
- **C-005 — golden harness FIRST.** The golden `spec-kitty doctor` CLI characterization test (all 16 subcommands' names/flags/help/exit-codes) is captured in **WP01, before any extraction**, so every later extraction has an objective byte-identical proof.

## Success Criteria

- **SC-001:** All 16 `spec-kitty doctor` subcommands enumerate with identical names, flags, `--help`, and exit-code behavior pre vs post (golden harness green at HEAD and after the final WP).
- **SC-002:** `doctor.py` is reduced to a thin orchestration surface (`app` + 16 thin command shells + re-export block + shared-infra import; target ≤ ~400 LOC); all extracted logic lives in cohesive siblings.
- **SC-003:** The nine new sibling modules exist beside `doctor.py`, each ≥90% covered; `_doctrine_collect` completes the doctrine MODEL/RENDER/COLLECT triad.
- **SC-004:** Every function in `doctor.py` and the siblings is ≤15 CC (`ruff check --select C901` clean); the six named mega-functions are decomposed, not relocated oversized.
- **SC-005:** The 11 private symbols + `app` + `SlashCommandGap` resolve via `from specify_cli.cli.commands.doctor import ...`; the full existing test suite stays green with no test-import edits.
- **SC-006:** Import-graph stays one-way (no sibling↔sibling, no sibling→orchestrator, no `doctor↔merge` cycle); exactly one `Console()` instance across the doctor surface.
- **SC-007:** `ruff` + `mypy --strict` clean with zero new suppressions; safety-predicate and argv-fast-path tests (`tests/cli_gate/test_doctor_modes.py`, `test_safe_commands.py`) green.

## Key Entities

- **Orchestration surface (`doctor.py`):** `app = typer.Typer(name="doctor", ...)`, the 16 `@app.command` thin shells (resolve repo_root/flags → delegate to a sibling entrypoint → preserve `raise typer.Exit(code)`), the re-export block, and the shared-infra import.
- **`_doctor_shared.py` (NEW):** canonical home for `console`, `_json_output_guard`, `_json_error`, `_is_interactive_environment`, and constants (`_CI_ENV_VARS`, `_STARTED_AT_COLUMN`, `_NOT_IN_PROJECT_MESSAGE`). Resolves H1.
- **`_doctrine_collect.py` (NEW):** doctrine-health DATA COLLECTORS (Cluster J) — completes the seam beside `_doctrine_health.py` (MODEL) + `_profile_health_render.py` (RENDER).
- **`_identity_audit.py` (NEW):** identity + topology cluster (D).
- **`_command_surface_doctor.py` (NEW):** tool-surface + command-skill + slash-command cluster (A); the `skills` command fuses command-skills + slash-commands → one sibling.
- **`_mission_state_doctor.py` (NEW):** mission-state audit/repair/teamspace-dry-run cluster (H).
- **`_coordination_doctor.py` (NEW):** git-version + worktree/sparse-drift health cluster (K); keeps `merge.path_is_under_worktrees` function-local (H2).
- **`_sparse_checkout_doctor.py` (NEW):** sparse-checkout remediation render/flow cluster (E).
- **`_workspace_husk_doctor.py` (NEW):** workspace-husk cluster (C).
- **`_daemon_doctor.py` (NEW):** orphan-daemons + restart-daemon bodies cluster (I).
- **Existing siblings (UNCHANGED):** `_doctrine_health.py`, `_profile_health_render.py`.

## Assumptions

- Small clusters already thin-delegating to external packages (B state-roots → `state.doctor`; F shim-registry → `compat`; G ops/invocation → `doctor.ops`) keep their thin command shells in `doctor.py`; only their private render helpers (`_print_overdue_details`, `_run_ops_sweep`) move if a cohesive sibling owns them, or stay if relocation adds no cohesion. Plan-phase decision (research OQ2).
- The doctrine-health render helpers are already extracted to `_profile_health_render.py`; this mission only moves the *collectors* (OQ resolved: collectors → `_doctrine_collect`).
- `_auth_doctor.py` (backs `auth doctor`, not the `doctor` group) is out of scope.
- The deferred `doctor.py` god-module split is the doctrine-health-collector follow-up tracked by #1623 / this ticket; this mission is its residual closeout, not a new feature.

## Research Outcomes

- Live `doctor.py` is **3434 LOC** (issue text says 3328/3300; the live file governs).
- #1623 extracted only MODEL + RENDER; collectors remain — confirmed the seam to complete.
- Deferred function-local imports are the dominant pattern, making each cluster's domain deps self-contained → extraction is low-risk.
- Import feasibility is one-way and GOOD; no cluster calls another cluster's helpers.
- The single highest-value pre-extraction artifact is the **golden CLI characterization test** (none exists today) — it lands FIRST (WP01).
- Recommended topology: **thin command shells stay in `doctor.py`; per-cluster logic moves to siblings** (lowest CLI-surface risk; mirrors the existing `mission_state` dispatch-thin pattern).

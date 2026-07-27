# Mission Spec — Decompose `agent/mission.py` god-module (remainder) (#2056)

**Mission:** `decompose-mission-god-module-01KVXHF8`
**Mission type:** software-dev
**Target file:** `src/specify_cli/cli/commands/agent/mission.py` — 4125 LOC, 62 top-level defs, 8 `@app.command`s.
**Base:** worktree `sk-2056` on `origin/main` (`c3814ec5a`). This base does **NOT** include sibling mission #2058.

---

## Overview

`agent/mission.py` is the `agent mission` CLI command module. It has grown into a god-module:
**4125 LOC across 62 top-level definitions** (61 `def` + 1 `class`), exposing **8 subcommands**
(`branch-context`, `create`, `check-prerequisites`, `record-analysis`, `setup-plan`, `accept`,
`merge`, `finalize-tasks`). Three command functions are themselves mega-functions far over the
complexity ceiling: `finalize_tasks` (1227 LOC), `setup_plan` (507 LOC), `create_mission` (281 LOC).

The planning-commit *pipeline* was already extracted into `coordination/commit_router.py` by a prior
slice (mission `01KVMBD6` — `commit_for_mission` + materialise/stage/route helpers). **This mission
decomposes the REMAINDER**: the command surface, the shared resolution/parsing/validation helpers,
and the internal complexity of the three mega-functions — into cohesive, independently-testable seams
behind a thin command-registration shim, **preserving the public `agent mission` CLI surface
byte-for-byte**.

This is a behavior-preserving refactor (semantic compression, profile `randy-reducer`): no command,
flag, JSON envelope, exit code, or on-disk behavior changes. The only observable effect is a smaller,
saner module topology, a complexity ceiling that holds, and a frozen, machine-checkable CLI contract.

### What is in scope

- Decompose the remainder of `mission.py` into the 4 research-resolved seams.
- Internally decompose the 3 mega-functions into `<=15`-complexity phase helpers, each with focused tests.
- Make `mission.py` a thin shim that registers the 8 commands and **re-exports every previously
  importable / test-patched symbol** (~100 names) so existing import edges and `@patch("...mission.<name>")`
  targets keep resolving with zero test churn.
- Relocate the planning-commit residue (`_planning_commit_worktree`, `_resolve_planning_placement`,
  `_stage_finalize_artifacts_in_coord_worktree`) into `coordination/commit_router.py` and repoint
  `tasks.py`'s import — these symbols are **LIVE on this base** (see Critical base-version constraint).

### What is out of scope

- Any change to command names, flag names/defaults, positional args, JSON envelope keys, or exit codes.
- Re-extracting the already-extracted planning-commit pipeline (`commit_for_mission` & friends).
- Touching the `agent tasks` god-module (#2058, a sibling mission).
- New functionality of any kind.

---

## ⚠️ Critical base-version constraint (LIVE planning-commit residue)

This worktree branches from `origin/main` (`c3814ec5a`), which does **NOT** contain the #2058 mission.
On this base:

- `tasks.py` **still imports** `_planning_commit_worktree` from `mission.py`
  (verified: `src/specify_cli/cli/commands/agent/tasks.py:3928` and `:3936` call it; `:3704` imports
  `_resolve_planning_placement`).
- Therefore `_planning_commit_worktree` and `_resolve_planning_placement` are **LIVE**, not dead code.

**Disposition decision (binding for this mission):** **RELOCATE**, never delete.

- Move `_planning_commit_worktree`, `_resolve_planning_placement`, and the helper they depend on,
  `_stage_finalize_artifacts_in_coord_worktree`, into `coordination/commit_router.py` — the canonical
  home of the planning-commit pipeline that the prior slice (`01KVMBD6`) established.
- Reconcile `_stage_finalize_artifacts_in_coord_worktree` against commit_router's existing near-duplicate
  `_stage_artifacts_in_coord_worktree` (`commit_router.py:366`, whose docstring already names the mission.py
  version as its mirror) — collapse the duplication rather than forking a second copy.
- Repoint `tasks.py`'s single function-local import of `_planning_commit_worktree` /
  `_resolve_planning_placement` to the new `commit_router` home.

This completes the commit-pipeline consolidation that `01KVMBD6` started. The spec is explicit:
**the planning-commit residue is LIVE and must be relocated + repointed, never deleted.** (If #2058 were
already on this base, those symbols would be dead and deletable — but they are not, so relocation is the
only correct disposition here.)

---

## User Scenarios & Testing

Primary "users" of this module are: (a) the agent/operator invoking `spec-kitty agent mission <cmd>`,
(b) downstream Python callers (`lifecycle.py`, `tasks.py`), and (c) the ~50 test files that import or patch
`mission.<symbol>`.

### Scenario 1 — Operator invokes any `agent mission` subcommand (byte-for-byte preserved)
- **Given** the decomposition is complete,
- **When** an operator runs `spec-kitty agent mission <subcommand> [flags]` (or `--json`),
- **Then** the command name, flags, defaults, behavior, exit code, and JSON envelope are identical to
  the pre-decomposition base — verified by a golden CLI characterization test captured FIRST.

### Scenario 2 — Existing test patches keep working (zero churn)
- **Given** ~50 test files patch `@patch("specify_cli.cli.commands.agent.mission.<name>")`
  (e.g. `locate_project_root` patched 76×, `_find_feature_directory` 39×, `_show_branch_context` 22×),
- **When** the symbols physically move into seam modules,
- **Then** every such patch target still resolves because `mission.py` re-exports the name — the existing
  test suite passes unchanged with no patch-target rewrites.

### Scenario 3 — `lifecycle.py` and `tasks.py` import edges hold
- **Given** `lifecycle.py` imports `create_mission`, `setup_plan`, `finalize_tasks`,
  `_build_setup_plan_detection_error` as `agent_feature.<name>`, and `tasks.py` imports
  `_parse_requirement_refs_from_tasks_md`, `_resolve_planning_placement`, `_planning_commit_worktree`,
- **When** symbols move,
- **Then** `lifecycle.py`'s edges resolve via shim re-export; `tasks.py`'s planning-commit imports are
  repointed to `commit_router`; the parsing-helper import resolves via shim re-export or its seam.

### Scenario 4 — `finalize-tasks --validate-only` mutates zero bytes
- **Given** the `finalize_tasks` mega-function is internally decomposed into phase helpers,
- **When** `finalize-tasks --validate-only` runs,
- **Then** it mutates ZERO bytes on disk (in-memory bootstrap only) — invariant preserved through
  decomposition and pinned by the existing readonly regression test.

### Scenario 5 — Complexity ceiling holds
- **Given** the 3 mega-functions are decomposed,
- **When** ruff `C901` / Sonar `S3776` run,
- **Then** every function (including all new phase helpers) reports complexity `<=15`, with zero new
  suppressions.

---

## Functional Requirements

All FRs are **Status: Approved**.

- **FR-001 — Frozen CLI surface.** The public `agent mission` CLI surface — all 8 subcommands
  (`branch-context`, `create`, `check-prerequisites`, `record-analysis`, `setup-plan`, `accept`, `merge`,
  `finalize-tasks`) with their exact positional args, option flags, defaults, exit codes, and JSON
  envelope shapes — MUST remain byte-identical to the base. The full flag set per command is enumerated
  in research §1 and frozen in `contracts/cli-surface-contract.md`.

- **FR-002 — Decomposition pointer comment.** `mission.py` MUST carry a top-of-file pointer comment
  referencing **#2056** (matching the #1623 / existing god-module-pointer convention already present in
  this repo) that documents the shim role and the seam map, so future maintainers route new responsibilities
  to the seams, not the shim.

- **FR-003 — Decompose into the 4 research-resolved seams.** The remainder MUST be decomposed into:
  1. **feature-dir-resolution** (Seam D) — `_find_feature_directory` & friends
     (`_resolve_mission_dir_name_primary_anchored`, `_primary_anchored_feature_dir`,
     `_list_feature_spec_candidates`, `_sole_mission_slug_or_none`, `_build_setup_plan_detection_error`,
     `_safe_load_meta`, `_read_feature_meta`).
  2. **parsing/validation** (Seam C) — tasks.md/spec.md parsers
     (`_parse_wp_sections_from_tasks_md`, `_parse_dependencies_from_tasks_md`,
     `_parse_requirement_refs_from_tasks_md`, `_parse_requirement_refs_from_wp_files`,
     `_parse_requirement_ids_from_spec_md`, `_extract_wp_ids_from_task_files`), owned-files validation
     (`_normalize_owned_file_path`, `_is_mission_specs_owned_file`,
     `_owned_files_yaml_is_explicit_empty_list`, `_raw_frontmatter_has_field`,
     `_invalid_mission_specs_owned_files`), JSON emit shims
     (`_emit_json`, `_with_cli_version`, `_with_mission_aliases`, `_emit_console_or_json_error`,
     `_utc_now_iso`).
  3. **record-analysis** (Seam A) — `record_analysis` + `_enforce_analysis_report_write_preflight` +
     `_resolve_record_analysis_placement_ref`.
  4. **lifecycle-subcommands split per command-family** (Seam B) — `branch_context`, `create_mission`,
     `check_prerequisites`, `setup_plan`, `accept_feature`, `merge_feature`, `finalize_tasks` and their
     dedicated helpers, split into per-family modules (not one mega-module).

  Seam D is extracted first so the other seams import a stable resolution surface rather than each other.
  One-way imports only: seams import lower layers (`core`/`status`/`coordination`/`mission_runtime`),
  never the shim.

- **FR-004 — Per-seam focused tests (≥90%).** Each seam MUST carry focused tests achieving **≥90%
  coverage** of the seam's code. Pure parsers and resolvers MUST get **direct** unit tests (not only
  indirect coverage through the command path), closing the current gap where Seam C parsers are exercised
  only via `finalize_tasks`.

- **FR-005 — Internal decomposition of the 3 mega-functions.** `finalize_tasks` (1227 LOC), `setup_plan`
  (507 LOC), and `create_mission` (281 LOC) MUST be internally decomposed into phase helpers each with
  complexity `<=15`, and each phase helper MUST have a focused test executing its branches directly.
  Recommended phase boundaries are documented in research §2 (finalize_tasks: preflight → feature-dir
  resolution → branch resolution → conflict detection → charter-activation gate → dependency resolution →
  8-field bootstrap-mutation loop → manifest build/ownership validation → commit → SaaS emit; setup_plan:
  preflight → resolution → branch-contract injection → plan commit → coord commits; create_mission:
  scaffold → meta write → coordination-branch creation → branch-contract injection → event emit).

- **FR-006 — Shim re-exports every test-patched name (~100).** `mission.py` MUST re-export EVERY symbol
  currently importable or patchable as `mission.<name>` so that `@patch("...mission.<name>")` targets and
  `from ...mission import <name>` edges keep working with zero churn. This explicitly includes the heavily
  patched names (`locate_project_root` 76×, `_find_feature_directory` 39×, `_show_branch_context` 22×,
  `run_command`, `get_emitter`, `is_saas_sync_enabled`, `validate_feature_structure`), the exported class
  `CommitToBranchResult`, the `app` Typer object, and all 8 command functions.

- **FR-007 — Relocate (not delete) the planning-commit residue.** `_planning_commit_worktree`,
  `_resolve_planning_placement`, and `_stage_finalize_artifacts_in_coord_worktree` MUST be RELOCATED into
  `coordination/commit_router.py` (the canonical planning-commit pipeline home), reconciling
  `_stage_finalize_artifacts_in_coord_worktree` against commit_router's existing near-duplicate
  `_stage_artifacts_in_coord_worktree`. `tasks.py`'s import of `_planning_commit_worktree` /
  `_resolve_planning_placement` MUST be repointed to the new `commit_router` home. These symbols are
  **LIVE on this base** (`tasks.py` calls `_planning_commit_worktree`) and MUST NOT be deleted as dead code.

---

## Non-Functional Requirements

- **NFR-001 — Complexity ceiling.** Every function (shim, seams, phase helpers) reports max cyclomatic
  complexity `<=15` under ruff `C901` (aligned with Sonar `S3776`). No function left at 16+.
- **NFR-002 — Coverage.** ≥90% coverage per new seam module and per new phase helper; new branches/helpers
  ship with tests in the same WP (Sonar new-code gate).
- **NFR-003 — Static analysis clean.** `ruff check` and `mypy --strict` (the project's configured strict
  profile) pass with zero issues and zero warnings on all touched files.
- **NFR-004 — No new suppressions.** No new `# noqa`, `# type: ignore`, Sonar suppression, or per-file
  ignore additions. Fix the code, don't silence the checker.
- **NFR-005 — No import cycles.** Seam modules import lower layers only; `commit_router` never imports
  from `mission`/seams; `commit_for_mission` / `CoordinationWorkspace` imports stay function-local where
  they already are.

---

## Constraints

- **C-001 — No command/flag changes.** Zero changes to command names, flag names, flag defaults,
  positional args, JSON envelope keys, or exit codes.
- **C-002 — Use canonical commit_router.** The relocated planning-commit residue lands in
  `coordination/commit_router.py`; do not create a parallel pipeline or improvise a new home.
- **C-003 — Behavior preserving.** This is a pure refactor. No observable runtime behavior may change.
- **C-004 — No new suppressions.** (See NFR-004.)
- **C-005 — Golden characterization test FIRST.** A golden `agent mission` CLI characterization test
  (CliRunner-based: `--help` for `app` lists all 8 commands; each subcommand's `--help` lists exact flags;
  representative success + error JSON envelopes) MUST be captured in **WP01, before any extraction**, as the
  safety net for "byte-for-byte preserved."

---

## Success Criteria

- SC-1: `mission.py` is a thin shim with no business logic; all command bodies and helpers live in seams.
- SC-2: The golden CLI characterization test passes against both base and decomposed code (the contract is
  byte-identical).
- SC-3: The full existing test suite (≈50 mission-touching files) passes with **zero patch-target rewrites**.
- SC-4: `mission.py`, every seam module, and every phase helper report complexity `<=15` under ruff `C901`.
- SC-5: Each new seam and phase helper has focused tests; new-code coverage ≥90%.
- SC-6: `ruff` + `mypy --strict` clean on all touched files; zero new suppressions.
- SC-7: `_planning_commit_worktree` / `_resolve_planning_placement` /
  `_stage_finalize_artifacts_in_coord_worktree` live in `commit_router.py`; `tasks.py` imports them from
  there; `tasks.py` behavior unchanged (its tests pass).
- SC-8: `finalize-tasks --validate-only` mutates zero bytes (readonly regression test green).

---

## Key Entities

- **`mission.py` (shim)** — `app = typer.Typer(name="mission", ...)`; registers the 8 commands; re-exports
  ~100 symbols. No logic.
- **Seam modules** — `cmd_record_analysis.py` (Seam A), `parsing.py` (Seam C), `feature_resolution.py`
  (Seam D), and per-family lifecycle command modules (`cmd_branch_context.py`, `cmd_create.py`,
  `cmd_check_prerequisites.py`, `cmd_setup_plan.py`, `cmd_finalize_tasks.py`, `cmd_accept_merge.py`) for
  Seam B. (Module-file-vs-package layout is a plan-phase decision; either preserves the
  `specify_cli.cli.commands.agent.mission` import path.)
- **`coordination/commit_router.py`** — canonical planning-commit pipeline; receives the relocated
  `_planning_commit_worktree` / `_resolve_planning_placement` / `_stage_finalize_artifacts_in_coord_worktree`.
- **`CommitToBranchResult`** — exported dataclass imported by tests; must remain importable from `mission.<name>`.
- **Golden CLI contract** — `contracts/cli-surface-contract.md` + the characterization test pinning it.

---

## Assumptions

- A-1: #2058 is NOT on this base; the `tasks.py → _planning_commit_worktree` edge is live (verified).
- A-2: Shim re-exports are the chosen mitigation for patch-target churn (zero test rewrites) rather than a
  bulk patch-target rewrite.
- A-3: `accept` / `merge` are already thin delegators to `top_level_accept` / `top_level_merge` and can
  move to a `cmd_accept_merge` seam without re-importing the full accept/merge graph at module top level.
- A-4: The module-vs-package layout decision is deferred to the plan; both preserve the import path.
- A-5: Existing dedicated tests (finalize_tasks ×6+ files, create_mission, `_commit_to_branch`,
  `_kind_for_artifact`, record-analysis, JSON envelope) remain the baseline safety net and are extended,
  not replaced.

---

## Research outcomes (resolved decisions)

- **Seam set resolved to 4** (research §3): feature-dir-resolution (D, extracted first),
  parsing/validation (C), record-analysis (A), lifecycle-subcommands split per command-family (B).
- **3 mega-functions confirmed** needing internal decomposition: `finalize_tasks` (1227 LOC, ~8× ceiling),
  `setup_plan` (507), `create_mission` (281). Internal phase extraction is the bulk of the effort, not the
  file split.
- **~100 patch-target re-export requirement** confirmed from the ~50-test patch survey
  (`locate_project_root` 76×, `_find_feature_directory` 39×, `_show_branch_context` 22×, etc.). Shim
  re-export = zero churn.
- **Planning-commit residue: LIVE → RELOCATE** (research §0/§3/§6 O-1, O-2). On this base the symbols are
  live (`tasks.py` calls them), so the resolved disposition is relocate-into-`commit_router` +
  repoint-`tasks.py`, reconciling against commit_router's existing `_stage_artifacts_in_coord_worktree`.
  Deletion is explicitly rejected for this base.
- **Golden characterization test required FIRST** (research §5): no single test currently pins the full
  8-command × all-flags + JSON-envelope contract; WP01 captures it before any extraction.

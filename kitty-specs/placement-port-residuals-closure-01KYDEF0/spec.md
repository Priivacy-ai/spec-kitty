# Mission Specification: Placement-Port Residuals Closure

**Mission Branch**: `placement-port-residuals`
**Created**: 2026-07-25
**Status**: Draft
**Input**: Close the five placement-port residuals deferred from merged PR #2920 (`coord-write-placement-closure`), grounded in that PR's 4-lens post-merge review squad (architect F2/F3/F4, renata F2, debbie F4, paula F2/F3) and GitHub issues #2923 (Part A) + #2924 (Part B). Extended (Part C) to green the six gate/contract reds PR #2920 merged red into `upstream/main` (incl. #2926, the guard-capability red at the same coord-seed call site as FR-008).

## Context & Motivation

PR #2920 closed the coordination write+read placement port so that mission
artifacts land on the correct partition (PRIMARY for stable planning/metadata,
COORD for lifecycle surfaces). Its post-merge review squad found five residual
weaknesses that were too risky to fold into the PR — each touches the sole
`status_phase` writer, the FR-007 backfill corpus path, or a best-effort
degrade surface, and each needs corpus-wide validation. They were deferred to
issues **#2923** (Part A — birth-cutover placement-port hardening, higher risk)
and **#2924** (Part B — degrade-path + best-effort-read hygiene, low risk).

This mission closes all five as one cohesive unit so the placement-port
guarantees are **enforced by the port**, not merely true by caller discipline.

**Part C (added post-merge):** PR #2920 was merged with several gate/contract
tests red — a mix of a fold-induced regression and PR-body reds the merge
accepted as honest-red-main. Because they are placement-port write-side /
path-construction / merge-committed-set gate reds (the exact gate family
Part A hardens), they are folded here rather than into a redundant follow-up
PR. Part C returns `upstream/main`'s arch + integration gates to green.

## Domain Language *(load-bearing — the `primary`/`merge` footgun)*

| Term | Canonical sense in this mission | Do NOT confuse with |
|------|--------------------------------|---------------------|
| **PRIMARY partition** | The stable planning/metadata home (`PRIMARY_METADATA` artifact kind → `resolve_artifact_surface(...).path`). Where `meta.json` / `status_phase` must be written. | The Primary Branch (`main`). A PRIMARY-partition verdict is NOT a "write to `main`" instruction. |
| **COORD partition / leg** | The lifecycle surface (status, notes, trace, issue-matrix), routed via the coordination branch under `coord` topology. | The PRIMARY partition. `tasks/` residue on the COORD leg may be stale or absent. |
| **Placement port** | The single authority resolving where an artifact kind lives: `resolve_artifact_surface`, `resolve_placement_only`, `placement_seam(...).read_dir(kind)` in `src/mission_runtime/`. | Direct filesystem helpers like `canonicalize_feature_dir` + `write_meta`, which bypass the port. |
| **`resolve_placement_only(kind)`** | Returns a **branch `CommitTarget`** (a ref), not a directory. | `resolve_artifact_surface(...).path`, which returns the on-disk **directory** home. The A1 fix needs the directory home. |
| **`_flip_phase`** | The **sole** writer of `status_phase` in the codebase (`runtime_state_cutover.py`). | The read/seed/verify phases, which currently anchor on a different leg (the A3 residual). |

## User Scenarios & Testing *(mandatory)*

Primary actor throughout: the **mission maintainer / operator** running merges,
migrations (`spec-kitty merge`, `spec-kitty migrate backfill-runtime-state`),
and retrospectives, plus **future contributors** who add writers under the
migration subtree. The value is safety: correct-by-construction partition
routing and no silent data loss.

### User Story 1 - Enforce PRIMARY-correctness of the sole `status_phase` writer (Priority: P1)

The birth-cutover and the corpus backfill both drive `_flip_phase`, the only
code that writes `status_phase`. Today it writes `meta.json` via
`canonicalize_feature_dir(feature_dir)` + `write_meta(validate=False)`,
bypassing the placement port; it is PRIMARY-correct only because every current
caller happens to pass a PRIMARY dir. A future caller passing a non-PRIMARY dir
would silently write `status_phase` off-partition with no gate to catch it.

**Why this priority**: This is the load-bearing safety invariant — the sole
writer of the phase key that gates the entire status model. Coincidental
correctness on the single most important writer is the highest-value residual
to convert into enforced correctness.

**Independent Test**: Drive `cutover_mission(feature_dir, status_feature_dir=…)`
with a synthetic caller passing a non-PRIMARY directory; assert the operation
fails closed (raises) rather than writing off-partition. With a PRIMARY dir the
flip still succeeds.

**Acceptance Scenarios**:

1. **Given** a caller passing a genuine PRIMARY `feature_dir`, **When** `_flip_phase` runs, **Then** the write target is resolved via `resolve_artifact_surface(repo_root, feature_dir.name, PRIMARY_METADATA).path` and the flip succeeds unchanged.
2. **Given** a caller passing a directory whose resolved PRIMARY home ≠ the passed dir, **When** `_flip_phase` runs, **Then** it fails closed (raises) and writes nothing — PRIMARY-correctness is enforced, not assumed.
3. **Given** the full FR-007 dogfood backfill corpus of genuinely-legacy missions, **When** the corpus cutover runs, **Then** every mission flips exactly as before (no regression).

---

### User Story 2 - No silent PRIMARY-runtime loss during legacy cutover under coord topology (Priority: P1)

The two-target `cutover_mission` reads legacy `tasks/` frontmatter from the
**COORD** leg (`status_feature_dir`) during seed/verify while `_flip_phase`
writes the **PRIMARY** leg. This is sound only because IC-07 (WP04/WP05) means
no mission reaching the merge hook still carries genuine frontmatter runtime —
a temporal-coupling argument enforced by nothing at runtime. A genuine pre-IC-07
cold-upgrade mission carried across the boundary and merged under coord topology
could have its real PRIMARY-`tasks/` runtime bypassed while the flip proceeds:
**silent data loss**.

**Why this priority**: Silent data loss on a real (if rare) upgrade path is a
correctness defect, not hygiene. Chosen remedy (operator-confirmed): make
seed/verify **read the frontmatter from the PRIMARY leg** so read and write
share a partition and the cutover heals rather than aborts.

**Independent Test**: Drive `cutover_mission` with a PRIMARY dir whose
`tasks/*.md` carry `has_evictable_state() == True` and an absent/stale COORD
`tasks/`; assert the evictable PRIMARY runtime is not silently discarded.

**Acceptance Scenarios**:

1. **Given** a pre-IC-07 cold-upgrade coord mission with evictable PRIMARY frontmatter runtime and no/stale COORD `tasks/`, **When** `cutover_mission` runs, **Then** seed/verify read the PRIMARY leg and the flip proceeds without evicting genuine runtime (no data loss).
2. **Given** a normal post-IC-07 mission with no evictable runtime, **When** `cutover_mission` runs, **Then** behavior is unchanged from today.

---

### User Story 3 - Narrow the `migration/` whole-tree gate carve-out (Priority: P2)

The whole-tree write gate still excludes the entire `src/specify_cli/migration/`
subtree (16 modules, including the real `runtime_state_cutover` writer) via a
directory-prefix carve-out. A bypass added under it would not red the gate, so
SC-002/NFR-001's "any module" guarantee is scoped there (documented deferred in
the merged spec at `kitty-specs/coord-write-placement-closure-01KYCF83/spec.md`
lines 108/136). Once User Story 1 routes the writer through the port, this
prefix can be converted to per-file, individually justified entries.

**Why this priority**: Restores the gate's "any module" guarantee for the
migration subtree. **Hard-depends on User Story 1** — dropping the prefix reds
`test_no_write_side_rederivation.py` on `_flip_phase` until A1 makes its write
seam-derived.

**Independent Test**: With A1 landed, drop `src/specify_cli/migration/` from
`BOUNDARY_SANCTIONED_PREFIXES`; the whole-tree scan reds on a synthetic bypass
added to any previously-carved-out migration module and stays green on the
legitimately-sanctioned per-file entries.

**Acceptance Scenarios**:

1. **Given** A1 has landed, **When** the `migration/` prefix is converted to per-file `BOUNDARY_SANCTIONED_MODULES` entries, **Then** each retained entry carries an individual rationale and every non-primitive migration module is back in scope.
2. **Given** the converted gate, **When** a synthetic write-side rederivation is added to a previously-carved-out migration module, **Then** the whole-tree gate reds.
3. **Given** the closure, **When** the SC-002/NFR-001 guarantee wording is read, **Then** it reads "any module **in the `migration/` subtree**" and the merged deferral note (cited by anchor) is reconciled to "closed for `migration/`; `upgrade/migrations/` retained per C-002" — the claim is precise, not falsely un-qualified.

---

### User Story 4 - One canonical write-target degrade idiom (Priority: P2)

`_mission_meta_exists` was cloned **verbatim** into
`events/decision_log.py` and `git/bookkeeping_commit.py`, each wrapping a
"resolve via port, else degrade" helper — while
`coordination/status_transition.py::_resolve_write_target` degrades differently
(through `get_feature_target_branch`, with no `_mission_meta_exists` pre-gate).
Three divergent implementations of the single decision "how do I resolve a write
target when the mission isn't fully bootstrapped?"

**Why this priority**: Whack-a-field debt — the next placement change must be
made in three places or it drifts again. Consolidating to one kind-parameterized
helper removes the divergence.

**Independent Test**: Assert all three public write paths degrade through **one
shared kind-parameterized helper** in the bootstrap window — coord kinds
(e.g. `STATUS_STATE`) resolve to the coord ref, primary kinds to the primary
home. (NOT "identically" — a uniform ref would flatten coord onto primary, the
C-004-forbidden change.)

**Acceptance Scenarios**:

1. **Given** a mission whose `meta.json` does not yet exist, **When** any of the three write paths resolves its target, **Then** all three degrade via the same shared `resolve_write_target_or_degrade(repo_root, mission_slug, kind, *, degrade_ref)` helper.
2. **Given** the unified helper, **When** it resolves `STATUS_STATE`, **Then** it still routes to the COORD ref under coord topology (kind-parameterized, never hardcoded to PRIMARY).
3. **Given** the consolidation, **When** the codebase is searched, **Then** zero verbatim `_mission_meta_exists` clones remain.

---

### User Story 5 - Deleted-coord retrospective degrades instead of crashing (Priority: P3)

WP07 correctly re-routed `retrospective/generator.py::_load_traces` through the
fail-loud authority (`placement_seam(...).read_dir(TRACER_FILE)`). But `read_dir`
for a COORD kind can raise `CoordinationBranchDeleted`, whereas `_load_traces`
is best-effort (returns `[]` on missing/unreadable). The call is unwrapped, so a
deleted-coord retrospective would crash instead of degrading.

**Why this priority**: Lowest-risk, single-call-site hygiene. Chosen remedy
(operator-confirmed): preserve best-effort — wrap and degrade to `[]`.

**Independent Test**: Drive `generate_retrospective(...)` on a coord mission
whose `coordination_branch` no longer exists; assert it returns without raising
and produces a retrospective with no traces.

**Acceptance Scenarios**:

1. **Given** a coord mission whose coordination branch was deleted, **When** `generate_retrospective` calls `_load_traces`, **Then** the read degrades to `[]` and generation completes (no crash).
2. **Given** a normal coord mission, **When** `_load_traces` runs, **Then** traces load exactly as before.

---

### User Story 6 - Return `main`'s gate/contract suites to green (Part C) (Priority: P2)

PR #2920 merged with six reproducible reds now sitting in `upstream/main`:
a fold-induced write-side-rederivation offender (`executor.py:1056`), a
guard-capability offender at the SAME coord-seed call site (`executor.py:1059`
`MERGE_BOOKKEEPING`, #2926), a raw-mission-spec-path offender
(`mission_repair.py:65`), a mission-CLI golden-contract drift (the new `repair`
command is a 9th, frozen contract says 8), and two merge tests expecting
`status.events.jsonl` in the committed file-set. Each red is judged per the
failing-test remediation framework: fix
the PRODUCT where the test encodes a real invariant; re-pin the TEST where the
contract legitimately moved (e.g. `repair` is a sanctioned new command).

**Why this priority**: Green gates are the shared safety net every later WP in
this mission relies on; leaving arch gates red on `main` masks regressions
(including this mission's own A1/A2 work on `test_no_write_side_rederivation`).
P2 (not P1) because they do not corrupt data — they are gate/contract debt.

**Independent Test**: The five named tests, red on the merge-base, are green
after Part C; the full `tests/architectural/` + affected integration suites pass.

**Acceptance Scenarios**:

1. **Given** `executor.py:1056`'s coord-seed `CommitTarget`, **When** the write-side gate runs, **Then** it is green because the call is seam-routed OR carries a tracked, rationale-bearing allow-list entry (MERGE_BOOKKEEPING coord reconciliation).
2. **Given** `mission_repair.py:65`'s mission-dir construction, **When** the raw-path gate runs, **Then** it is green via the canonical constructor OR a rationale-bearing constructor-file allow-list entry.
3. **Given** the `agent mission repair` command is a sanctioned addition, **When** the golden-contract test runs, **Then** `_EXPECTED_COMMANDS` and the `cli-surface-contract.md` frozen doc include `repair` and the set matches exactly.
4. **Given** a planning-artifact / mark-done merge, **When** the committed file-set is asserted, **Then** `status.events.jsonl` is committed alongside `meta.json`/`status.json` (both merge tests green).
5. **Given** the coord-seed `safe_commit` at `executor.py:1059`, **When** the guard-capability gate runs, **Then** it is green because `MERGE_BOOKKEEPING`'s allowlist includes `merge/executor.py` with a dated rationale (the same call site FR-008 covers, resolved with one coherent rationale across both gates).

### Edge Cases

- **Non-PRIMARY dir at the flip** (A1): resolved home ≠ passed dir → fail closed, write nothing.
- **COORD `tasks/` absent while PRIMARY `tasks/` present** (A3): read must anchor on PRIMARY so genuine runtime is seen.
- **A2 applied before A1**: the gate reds on `_flip_phase` — the mission must sequence A1 first (C-001), never ship A2 alone.
- **Unified helper flips a coord kind to PRIMARY** (B1): forbidden — `STATUS_STATE` and other coord kinds must keep degrading to the coord ref.
- **`_load_traces` raise other than `CoordinationBranchDeleted`** (B2): only the deleted-coord / `StatusReadPathNotFound` family degrades to `[]`; genuinely unexpected errors are not swallowed silently.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Route `_flip_phase` write-target through the placement port with a fail-closed home-equality assert (`resolve_artifact_surface(repo_root, feature_dir.name, PRIMARY_METADATA).path == canonicalize_feature_dir(feature_dir)`). Pre-decisions: (a) `repo_root` is the CWD-invariant main-repo root derived from `feature_dir` (never `Path.cwd()`, per the module's own rule); (b) a resolver **raise** on a well-formed legacy corpus mission MUST NOT abort the cutover — only an **equality mismatch** fail-closes; (c) the flip is enforced by this runtime assert, not by a static gate (`write_meta` is invisible to the write-side gate). | As a maintainer, I want the sole `status_phase` writer's PRIMARY-correctness enforced by a runtime fail-closed check so a future off-partition caller fails instead of corrupting state silently. | High | Open |
| FR-002 | Close the A3 COORD-read/PRIMARY-write residual by moving ONLY the `tasks/` frontmatter **read** (`_seed_phase`/`_verify_phase`) to the PRIMARY leg; the seed-event **write** (`status.events.jsonl` = STATUS_STATE) stays on the COORD leg and the `status_phase` flip stays on PRIMARY. This decouples `backfill_runtime_state`'s read/write coupling (read-dir vs write-dir) — an owned-scope expansion the WP must carry. NOT a leg swap: "read and write share a partition" is wrong for the event write. | As a maintainer, I want the legacy cutover to see genuine PRIMARY `tasks/` runtime so a pre-IC-07 cold-upgrade coord mission is cut over without silent data loss, while the event log still lands on its canonical COORD partition. | High | Open |
| FR-003 | Convert the `src/specify_cli/migration/` whole-tree gate prefix to per-file `BOUNDARY_SANCTIONED_MODULES` entries with individual rationales; drop non-primitive modules back into scope | As a contributor, I want the whole-tree gate to red on a bypass in any migration module so the "any module" guarantee holds for that subtree. | Medium | Open |
| FR-004 | Reconcile the SC-002/NFR-001 guarantee to "any module **in the `migration/` subtree**" (NOT un-qualified) and update the merged-spec deferral note (cite by heading/anchor, not stale line numbers) to "closed for `migration/`; `upgrade/migrations/` prefix retained per C-002". The un-qualified "any module" claim stays false while `upgrade/migrations/` remains a prefix. | As a maintainer, I want the gate's documented guarantee to precisely match the code once the `migration/` carve-out is narrowed. | Medium | Open |
| FR-005 | Extract one shared kind-parameterized `resolve_write_target_or_degrade(repo_root, mission_slug, kind, *, degrade_ref)` in `src/mission_runtime/` and route all three write surfaces through it; delete the two verbatim `_mission_meta_exists` clones | As a maintainer, I want one canonical write-target degrade decision so placement changes are made once, not three times. | Medium | Open |
| FR-006 | Guard `_load_traces` by wrapping the `read_dir(TRACER_FILE)` call in try/except for `CoordinationBranchDeleted`/`StatusReadPathNotFound` and degrading to `[]` | As a maintainer, I want deleted-coord retrospectives to degrade gracefully instead of crashing. | Low | Open |
| FR-007 | Tracker shape: mint a parent epic and native-link the currently-orphaned #2923 + #2924 + #2926 (all `parent: null`) under it. Per-FR→one-issue terminal matrix (12 FR rows / 4 child issues): **#2923**←FR-001/002/003/004; **#2924**←FR-005/006; **#2926**←FR-008+FR-012 (same call site — FR-008 rides under #2926, NO separate issue); **new Part-C issue**←FR-009/010/011 (do NOT ride under #2923, whose body covers A1/A2/A3 only); FR-007 itself is planning | As an operator, I want the deferred follow-ups and the Part C reds tracked under one parented epic with a terminal per-FR 1:1 issue-matrix. | Medium | Open |
| FR-008 | Green `test_no_write_side_rederivation` on `executor.py:1056` via a tracked, rationale-bearing **allow-list** entry (pre-decided over seam-routing): the coord-seed commits `status.events.jsonl` (STATUS_STATE→COORD) onto the captured `pre_target_coord_ref` from the COORD worktree — partition-correct — on a best-effort merge path that must never abort; seam-routing would add merge-window resolvability coupling (`ActionContextError`) the captured-ref path avoids. Fold-induced regression from `e99444df5`. | As a maintainer, I want the write-side gate green on `main` without destabilizing the best-effort merge path. | High | Open |
| FR-009 | Green `test_no_raw_mission_spec_paths` on `mission_repair.py:65` — route through the canonical mission-dir constructor OR add a rationale-bearing constructor-file allow-list entry | As a maintainer, I want the raw-mission-spec-path gate green on `main`. | Medium | Open |
| FR-010 | Reconcile the mission-CLI golden contract for the sanctioned `agent mission repair` command — update `_EXPECTED_COMMANDS` (8→9), add `_EXPECTED_FLAGS["repair"]` and any `_EXPECTED_POSITIONALS["repair"]` (so repair's `--mission`/flag surface is contract-pinned, not just its name), rename the `test_app_exposes_exactly_eight_frozen_commands` test + its "exactly 8" docstring to the new count, and add the `repair` row to `cli-surface-contract.md`. Pure CLI-surface-contract hygiene, folded for co-location with FR-009. | As an operator, I want the mission CLI surface contract to match the shipped command set including repair's flag surface. | Medium | Open |
| FR-011 | Reconcile the merge committed-file set so `status.events.jsonl` is committed alongside `meta.json`/`status.json` — greening `test_safe_commit_is_called_with_correct_files` and `test_planning_artifact_only_merge_does_not_require_mission_branch` | As a maintainer, I want merges to durably commit the status event log, not drop it. | High | Open |
| FR-012 | Green `test_guard_capability_call_sites[MERGE_BOOKKEEPING]` (#2926, fold-induced from `e99444df5`) at the SAME coord-seed call site as FR-008 (`executor.py:1059`, `capability=GuardCapability.MERGE_BOOKKEEPING`) — extend `_PROTECTED_FLOW_ALLOWLISTS["MERGE_BOOKKEEPING"]` to include `merge/executor.py` with a dated rationale naming the merge coord-seed flow. Pre-decided over asserting STANDARD: STANDARD would refuse the protected coord destination the best-effort seed legitimately writes to (consistent with FR-008's allow-list adjudication). | As a maintainer, I want the guard-capability gate green on `main` without weakening the coord-seed commit's authority. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Red-first proof per fix | Each of the 5 fixes (FR-001, FR-002, FR-003, FR-005, FR-006) ships ≥1 test that is demonstrably RED before the fix and GREEN after, driven through the PRE-EXISTING public entry point (`cutover_mission`, the three write paths, `generate_retrospective`, the whole-tree scan). Target: 5/5. | Reliability | High | Open |
| NFR-002 | Corpus-wide validation for A1/A3 | FR-001 and FR-002 are validated across the entire FR-007 dogfood backfill corpus, not a single mission: 0 genuinely-legacy missions fail to flip; 0 PRIMARY-runtime evictions. | Reliability | High | Open |
| NFR-003 | Zero new lint/type debt | New/changed code passes `ruff check` and `mypy --strict` with 0 new issues/warnings; no new blanket `# noqa`/`# type: ignore`; every touched function stays at cyclomatic complexity ≤ 15. | Maintainability | High | Open |
| NFR-004 | Gate/contract suites end green (incl. the Part C reds) | The full `tests/architectural/` suite (incl. `test_no_write_side_rederivation.py`, `test_guard_capability_call_sites.py`, `test_no_raw_mission_spec_paths.py`, `_placement_whole_tree_scan.py`, `test_no_legacy_terminology.py`, golden-contract) AND the affected integration/merge tests are green after the change — the six reds PR #2920 merged red are closed, none reintroduced. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Gate greenness depends on FR-008, NOT on an A1→A2 sequence (corrected post-squad) | The write-side gate flags only `CommitTarget(...)`/`safe_commit(...)` constructs; the entire `src/specify_cli/migration/` subtree contains **zero** such calls, so FR-003 (dropping its prefix) reds nothing and is **not** gated on FR-001. `_flip_phase` writes via `write_meta(<dir>)` — invisible to the gate — so FR-001's PRIMARY-correctness is enforced by a **runtime fail-closed assert**, not a static gate. `test_no_write_side_rederivation` is red today solely from `executor.py:1056` (FR-008); therefore NFR-004/SC-007/SC-008 (full arch green) require **FR-008**, not an A1-before-A2 order. | Technical | High | Open |
| C-002 | Keep the `src/mission_runtime/` AND `src/specify_cli/upgrade/migrations/` prefixes | The whole-tree gate retains `src/mission_runtime/` (the port cannot scan its own authority) and `src/specify_cli/upgrade/migrations/` (sanctioned version-migration drivers). The merged NFR-001 deferred narrowing **both** `migration*` subtrees; this mission narrows only `src/specify_cli/migration/` (FR-003) and leaves `upgrade/migrations/` a documented, justified prefix. | Technical | High | Open |
| C-007 | Shared-file lane cohesion (planning input) | FR-001/FR-002/FR-008/FR-012/FR-011/FR-003/FR-004 all touch `migration/runtime_state_cutover.py`, `merge/executor.py`, or the write-side gate test — /plan MUST group them in one serial lane for file-ownership safety in the shared tree (FR-008 + FR-012 are the SAME `executor.py` coord-seed call site across two gates → same WP). FR-005/FR-006/FR-009/FR-010 are the genuinely-parallel split-candidate lanes. This is a decomposition constraint, not a correctness sequence. | Technical | Medium | Open |
| C-003 | B2 scoped to the single call site | FR-006 touches only the `_load_traces` `read_dir` call. It MUST NOT expand into #2922's ~50-module read-side whack-a-read set (avoid collision with that separate mission). | Technical | Medium | Open |
| C-004 | Kind-parameterized degrade, coord stays coord | The unified helper (FR-005) MUST remain kind-parameterized; `STATUS_STATE` and other COORD kinds must keep degrading to the coord ref, never flip to PRIMARY. Adding the pre-gate to `status_transition._resolve_write_target` is a real behavior change and must be covered by tests. | Technical | High | Open |
| C-005 | No version/patch number in scope | This mission does not assign a release/patch number; the product owner superimposes versioning at release time. | Business | Medium | Open |
| C-006 | Terminology canon | No forbidden/legacy terminology introduced; canonical `Mission` (not `feature`), correct PRIMARY-partition vs Primary-Branch usage per the Domain Language table. | Technical | Medium | Open |

### Key Surfaces *(reference — not new data entities)*

- **`_flip_phase`** (`src/specify_cli/migration/runtime_state_cutover.py`) — sole `status_phase` writer (FR-001).
- **`cutover_mission`** (same module) — two-target seed/verify/flip driver (FR-002).
- **`backfill_runtime_state` / `verify_backfill`** (`src/specify_cli/migration/backfill_runtime_state.py`, incl. `has_evictable_state`) — FR-002 must decouple its read-dir (→PRIMARY `tasks/`) from its event write-dir (→COORD `status.events.jsonl`); also the standalone `spec-kitty migrate backfill-runtime-state` corpus path (NFR-002).
- **Placement port** (`src/mission_runtime/`: `resolve_artifact_surface`, `resolve_placement_only`, `placement_seam`, `MissionArtifactKind.PRIMARY_METADATA`) — the authority FR-001/FR-005 route through.
- **Whole-tree gate** (`tests/architectural/_placement_whole_tree_scan.py`: `BOUNDARY_SANCTIONED_PREFIXES`, `BOUNDARY_SANCTIONED_MODULES`) — FR-003/FR-004.
- **Write surfaces** (`events/decision_log.py`, `git/bookkeeping_commit.py`, `coordination/status_transition.py`) — FR-005 consolidation targets.
- **`_load_traces`** (`src/specify_cli/retrospective/generator.py`) + `CoordinationBranchDeleted` (`coordination/surface_resolver.py`) — FR-006.
- **Part C gate surfaces**: `merge/executor.py:1056` coord-seed `CommitTarget` (FR-008) + `:1059` `MERGE_BOOKKEEPING` capability with `tests/architectural/test_guard_capability_call_sites.py::_PROTECTED_FLOW_ALLOWLISTS` (FR-012, #2926 — same call site); `cli/commands/agent/mission_repair.py:65` (FR-009); `test_mission_cli_golden_contract.py::_EXPECTED_COMMANDS`/`_EXPECTED_FLAGS` + `kitty-specs/decompose-mission-god-module-01KVXHF8/contracts/cli-surface-contract.md` (FR-010); the merge committed-file set asserted by `test_merge_status_commit.py` / `test_merge_lane_planning_data_loss.py` (FR-011).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of `_flip_phase` write-target resolution goes through the placement port; a synthetic non-PRIMARY caller fails closed (proven by a red-first test).
- **SC-002**: 0 `src/specify_cli/migration/` modules remain covered only by a whole-subtree carve-out **in the placement-enforcement scan** (`_placement_whole_tree_scan.BOUNDARY_SANCTIONED_PREFIXES`); every retained sanctioned module (there + the still-prefixed `mission_runtime/`, `upgrade/migrations/`) carries a documented rationale; the whole-tree gate reds on a synthetic `CommitTarget`/`safe_commit` bypass in any previously-carved-out `migration/` module. (The C-004 `_MIGRATION_WALKER_DIR_PREFIXES` blanket in `test_mission_resolver_walker_gate.py` is a SEPARATE, intentional, permanent carve-out — explicitly out of scope.)
- **SC-003**: 0 silent PRIMARY-runtime evictions — a pre-IC-07 cold-upgrade coord mission with evictable PRIMARY frontmatter is cut over without data loss (proven by a red-first repro).
- **SC-004**: exactly 1 canonical write-target-degrade implementation remains (down from 3); 0 verbatim `_mission_meta_exists` clones remain.
- **SC-005**: deleted-coord retrospective generation degrades to `[]` traces with 0 crashes (proven by a red-first repro).
- **SC-006**: the full FR-007 dogfood corpus cutover is regression-free (all missions flip as before; no evictions).
- **SC-007**: full `tests/architectural/` suite green; `ruff`/`mypy --strict` clean on the diff.
- **SC-008**: the six gate/contract reds PR #2920 merged red (`test_no_write_side_rederivation` @ `executor.py:1056`, `test_guard_capability_call_sites[MERGE_BOOKKEEPING]` @ `executor.py:1059` [#2926], `test_no_raw_mission_spec_paths` @ `mission_repair.py:65`, the mission-CLI golden-contract count test [renamed 8→9 by FR-010], `test_safe_commit_is_called_with_correct_files`, `test_planning_artifact_only_merge_does_not_require_mission_branch`) are all green; the previously-failing CI jobs (`arch-adversarial`, `integration-tests-cli`, `integration-tests-core-misc`) pass.

## Assumptions

- The chosen A3 remedy is **read the `tasks/` frontmatter from the PRIMARY leg** (operator-confirmed), not a fail-closed abort guard — but ONLY the read moves: the seed-event write stays COORD and the flip stays PRIMARY (decoupling `backfill_runtime_state`'s read/write coupling). The red-first test must assert both that evictable PRIMARY runtime is seen (`seeded_count > 0`) AND that the event log lands on the COORD leg.
- FR-001's red-first fixture needs a canonical-primary dir present + a divergent `feature_dir` for the same slug + a verify-passing `status_feature_dir` (else the test dies at verify before reaching the assert). A resolver-raise on a well-formed legacy mission is handled distinctly from an equality mismatch (only the mismatch fail-closes).
- The chosen B2 remedy is **degrade to `[]`** (operator-confirmed), preserving `_load_traces`' best-effort contract, not making the raise explicit.
- The shared degrade helper's home is `src/mission_runtime/`; if plan finds a stronger seam it may relocate, but it must stay import-legal for all three call sites.
- Issue #2922 (read-side whack-a-read) is a **separate** mission; B2 is deliberately scoped narrow to avoid collision.
- Restoring SC-002/NFR-001 wording means reconciling the documented deferral note; the merged mission's spec is a historical artifact and only its deferral note is updated to reflect closure.
- **Part C reds are already red** on the merge-base, so they satisfy red-first inherently; each is judged per the failing-test remediation framework (fix PRODUCT where the test encodes a real invariant — FR-008/FR-009/FR-011; re-pin the TEST where the contract legitimately moved — FR-010, `repair` is a sanctioned command). Never retry-to-green.
- `test_repair_command_registered_on_mission_app` **passed locally** (repair is registered in source) but failed on CI — treated as verify-on-CI (possible ordering/isolation), not assumed a firm product defect; FR-010 confirms it lands green on CI.
- `executor.py:1056` is the only FR-008 offender confirmed; if narrowing surfaces sibling coord-seed writers, they are folded under FR-008 (same MERGE_BOOKKEEPING rationale), not a new requirement.

## Out of Scope

- The broader #2922 read-side whack-a-read remediation (~50 modules).
- The `repair_lane_mismatch` frontmatter-corruption fix (#2921) unless it is a trivial campsite in a file already opened.
- Any release/versioning action (C-005).
- New event-sourcing or status-model changes beyond the five residuals.

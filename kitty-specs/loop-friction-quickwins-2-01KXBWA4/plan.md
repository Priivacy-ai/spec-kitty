# Implementation Plan: Implement-Loop Friction Quick-Wins II

**Branch**: `feat/loop-friction-quickwins-2` | **Date**: 2026-07-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/loop-friction-quickwins-2-01KXBWA4/spec.md`

## Summary

Clear the highest-friction, lowest-risk points in the implement→review loop where lifecycle guards
trip on their own runtime writes or the pre-review gate returns inconclusive verdicts that force a
`--force`. Approach: small, seam-local fixes — each mirrors existing prior art where it exists
(`_drop_vcs_lock_only_meta` for the allocator, `_manifest_source_path` for the manifest, `_normalize_tasks_md`
for freshness), each pinned by a red-first regression proving the guard's true-positive still fires
(NFR-005). Seven concerns (post-squad re-split) map to ~7 WPs; the only cross-concern coordination is IC-07's
adjacency to the coord-authority line (C-002), now de-risked since that line already merged into base.
Successor to the **merged** `loop-friction-fastfollow` (complements #2573, does not re-touch its
shipped surfaces).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest (test-only extra), mypy, ruff; `uv` toolchain; git via `GitPort`
**Storage**: filesystem artifacts (`kitty-specs/<mission>/`, `.kittify/agent_profiles_manifest.json`), JSONL status event log, git
**Testing**: `uv run pytest` (parallel `-n auto --dist loadfile`; real-port/daemon tests serial `-n0`); red-first regressions per WP; `ruff` + `mypy` zero-issue
**Target Platform**: Linux/macOS developer + CI (GitHub Actions)
**Project Type**: single (Python CLI package — `src/specify_cli/` + `src/doctrine/` + `tests/`)
**Performance Goals**: no new hot path; pre-review gate interpreter resolution adds ≤1 `shutil.which`/subprocess probe per gate run
**Constraints**: cyclomatic complexity ≤15 (ruff C901 / Sonar S3776); no `# noqa`/`# type: ignore` to pass gates; repeated literals (≥3) hoisted to constants; every new branch/helper tested in-WP; loopback/localhost semantics untouched
**Scale/Scope**: 10 issues across 5 concerns; ~8–10 source files touched, each with a focused test; net-new LOC modest (mostly guards/serialization seams + doctrine doc)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present (`.kittify/charter/charter.md`); governance loaded via `charter context --action plan` (mode: compact; template set `software-dev-default`; tools git/mypy/pytest/ruff/spec-kitty).

- **Single canonical authority / no improvisation** — PASS. Every fix reuses the canonical seam (mirror `_drop_vcs_lock_only_meta`, `_manifest_source_path`, `_normalize_tasks_md`); no older-mission copying.
- **ATDD-first / red-first remediation** — PASS by construction. NFR-005 + C-001 require a red-first regression per guard fix proving the true-positive still fires; C-004 requires the pytest-lacking-interpreter regression (existing tests mask #2570.3).
- **Tiered rigour (core vs glue)** — PASS. Guard/gate cores are DDD-core-tier (pure functions with DI `GitPort`); serialization/doc are glue-tier.
- **Terminology adherence** — PASS. New prose (doctrine sub-agent contract doc, spec/plan) runs `tests/architectural/test_no_legacy_terminology.py` before push.
- **Campsite / no guard-weakening** — PASS. C-001: remove false positives only; never relax a guard to pass.
- **Coord-authority alignment (C-002)** — CONDITIONAL. WP-E shares surface with merged #168 + draft `implement-loop-coord-authority-completion`; must not alter STATUS_STATE placement. Tracked as a Complexity/Coordination note, not a violation.

No unjustified violations. Proceed to Phase 0.

## Project Structure

### Documentation (this mission)

```
kitty-specs/loop-friction-quickwins-2-01KXBWA4/
├── plan.md                 # This file
├── spec.md                 # Committed spec
├── research-synthesis.md   # 4-lens pre-spec squad synthesis (committed)
├── research.md             # Phase 0 output (this command)
├── data-model.md           # Phase 1 output (this command)
├── quickstart.md           # Phase 1 output (this command)
├── contracts/              # Phase 1 output (this command)
├── checklists/requirements.md
└── tasks.md                # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

Tracer files (#2095 experiment) live on the **coordination branch** (coord topology), not here:
`traces/tooling-friction-trace.md`, `traces/approach-trace.md`, `traces/design-trace.md`.

### Source Code (repository root)

```
src/specify_cli/
├── cli/commands/
│   ├── implement.py                    # WP-A: allocator uncommitted-artifact check + shell_pid write
│   ├── implement_cores.py              # WP-A: resolve_planning_artifact_staging (+ _drop_* seam)
│   └── agent/
│       ├── mission_setup_plan.py       # WP-D: scaffold + substantive block + result emit
│       ├── mission_create.py           # WP-D: specify-side twin gate
│       ├── tasks_parsing_validation.py # WP-C: issue-matrix approval blocker message
│       └── tasks_materialization.py    # WP-A: pipe-table [D]/[P] writers (reference)
├── analysis_report.py                  # WP-A: _normalize_tasks_md freshness normalizer
├── review/
│   ├── pre_review_gate.py              # WP-B: run_scoped_tests_at_head interpreter + timeout
│   └── _issue_matrix.py                # WP-C: MANDATORY_COLUMNS / SCHEMA_DRIFT early-return
├── tool_surface/profiles/
│   ├── manifest.py                     # WP-C: _entry_to_json / _entry_from_json (output_path)
│   └── projection.py                   # WP-C: _manifest_source_path prior art (relative)
├── bulk_edit/inference.py              # WP-C: keyword weights / INFERENCE_THRESHOLD
├── policy/commit_guard.py              # WP-E: block_mission_specs protected-path guard
└── missions/_substantive.py           # WP-D: is_substantive (unchanged; read-only reference)

src/doctrine/                           # WP-B: sub-agent long-gate contract (skill/doc)
tests/                                  # per-WP red-first regressions (mirrors each surface)
```

**Structure Decision**: Single Python CLI package. Each concern is a seam-local change in one or two
modules plus a focused test; no new package or architectural layer is introduced.

## Post-Plan Squad Remediations (2026-07-12)

A 4-lens profile-loaded adversarial squad (reviewer-renata dedup / planner-priti sizing /
architect-alphonso coord-adjacency / doctrine-daphne canonical) reviewed this plan against live code.
Verdict: include/exclude boundary **sound** (no wrong-inclusion/exclusion); canonical seams verified real.
Applied refinements (see the updated IC map + spec below):

- **Coord premise was stale (alphonso F1):** both coord missions this plan feared — `implement-loop-coord-authority-completion` (#2194, merged 2026-06-27) and `coord-authority-trio-degod` (#2545, merged 2026-07-11) — are already in this mission's base. C-002 reframed from "sequence with in-flight" to "do not regress the now-shipped partition-lock #168 invariants." Include of IC-05 is de-risked, not weakened.
- **IC-05 narrowed (alphonso F3/F5, priti F12):** WP-file commits already route to **primary** via `commit_router`, so no lane commit of `kitty-specs/` is needed. Drop the `commit_guard.block_mission_specs` exemption; route staging through the authority path and reuse `resolve_planning_artifact_staging` (the seam IC-01 hardens) — no duplicate "should this diff block?" decision.
- **Re-split ~5→7 concerns (priti F5/F8/F3/F9-11):** FR-006 (manifest) is **M** (threads `project_root` through reader+writer, keying-invariant risk) → own concern; IC-02 is **M** (async-vs-sync lock + lock-wait-vs-timeout); IC-04's specify twin is already shipped (`mission_create` `scaffold_only: success`) → plan side only + name real consumers.
- **Folds/links (daphne F6/F7/F8):** fold #2580 (4th `shell_pid` writer, `_mt_persist_wp_file`) into IC-01; add #1862 (FR-002 umbrella) to matrix; explicitly exclude #2583; note #2596/#2598/#2300 in C-002.
- **Correctness pins (renata F10, priti F1/F13):** FR-008 add single-HIGH-phrase true-positive regression (threshold 4 guard); FR-001 assert WP body byte-unchanged + source field set from canonical `frontmatter.py` `WP_FIELD_ORDER`.

## Post-Tasks Squad Remediations (2026-07-12)

A 4-lens post-tasks squad (renata executability / pedro Sonar-campsite / priti completeness / alphonso SSOT)
reviewed the 7 WP files against live code. Verdict: 6/7 executable as written; folded refinements:

- **WP06 reworked (renata HIGH + alphonso D2):** the setup-plan `result` does NOT flow through `next --result`'s fixed `_VALID_RESULTS` (`next_cmd.py:43`). Mirror the shipped specify twin — emit `result: success` + `scaffold_only: true` (ONE token, extract `_resolve_plan_result_state`), consumer = source prompt only. Dropped `engine.py` from ownership.
- **WP05 complexity (pedro):** `_issue_matrix_approval_blocker` is at 13 — route the drift `detail` through the existing `_issue_matrix_diagnostic_lines` helper + hoist the 3× ERROR literals (S1192) to stay ≤15; add the "rows-parsed still lists Missing rows" preservation test.
- **WP04 SSOT (alphonso D1):** reuse ONE `relativize_under_root` helper shared with `_manifest_source_path`; add the out-of-tree absolute-fallback test (G1).
- **WP03 SSOT (alphonso D3 + G2/G4):** the `uv run` executor is net-new → canonical `review/_interpreter.py` (drop the phantom "align with compat" steer); add the uv-present/no-pyproject test; FR-005 is doc-only (C-B2) + agent-copy-regen note.
- **WP07 (pedro + G3):** staging lands in `_mt_write_and_commit_wp_file` (~5), not `_mt_commit_wp_file` (11); #2580 routed through canonical `write_shell_pid_claim`; fold the 3× fallback-write helper.
- **WP08 added (#2533, operator "Both"):** consequence-only surface_resolver fix; derivation revisit + `next_step`/`_mt_commit_wp_file` de-gods filed as follow-ups.
- **Traceability (G5/G6):** WP07 refs FR-001; WP03 refs NFR-005. SC-003 0-diff proof + SC-006 epic-linking are mission-wrap/PR-body items.

## Complexity Tracking

| Violation / Coordination note | Why Needed | Simpler Alternative Rejected Because |
|-------------------------------|------------|--------------------------------------|
| IC-07 routes move-task staging through the authority path; shared surface with the now-MERGED partition-lock #168 + gate-registration refactors #2596/#2598 (C-002) | The recovery-cascade residual (#2555.1) is unowned and high-frequency (0-diff WP → 6 attempts) | Deferring leaves a real unowned friction; operator elected to include. Narrowed to the staging/router leg — NOT a `commit_guard` exemption (that would weaken partition-lock #168 for no benefit) |
| IC-04 (manifest) threads `project_root` through `_entry_to_json`/`_entry_from_json`/`_read`/`save` | On-disk relative + in-memory absolute keying (NFR-004) requires reconstruction at read time | Mirroring `_manifest_source_path` verbatim is only half the pattern — `output_path` is the manifest KEY and must `.exists()`-resolve, unlike the never-reconstructed `source_path` |
| IC-03 gives the contention lock its own acquire-timeout, decoupled from the 300s subprocess timeout | Canonical `MachineFileLock` is async-only; the gate runner is sync — and a lock-wait charged against the subprocess timeout would re-create the false `no_coverage` FR-004 removes | A bare `fcntl.flock` improvises past the canonical lock; charging the wait to the existing timeout reintroduces the bug |
| IC-02 adds an interpreter-resolution helper (net-new ~15 lines) | No `uv run` execution helper exists in `src/` today (verified); the gate must find the test-only `pytest` extra | Reusing `sys.executable` is exactly the bug (#2570.3); bare `python` is worse |

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

> Post-squad decomposition: 7 concerns (was 5). Sizing re-verified against live code.

### IC-01 — Allocator + move-task no-op-stable against their own runtime frontmatter writes

- **Purpose**: Stop the allocator (and the sibling `_mt_persist_wp_file` writer) from blocking on the runtime WP frontmatter the loop itself just wrote; close the `shell_pid`/`base_*` self-writer set by construction.
- **Relevant requirements**: FR-001; NFR-001, NFR-005. **Folds #2580** (4th `shell_pid` writer).
- **Affected surfaces**: `implement.py` (uncommitted-artifact check ~1345; shell_pid write ~1400), `implement_cores.py` (`resolve_planning_artifact_staging`, beside `_drop_vcs_lock_only_meta` @244), `implement_support.py` (`base_*` write), `tasks_move_task.py::_mt_persist_wp_file` (#2580 writer); canonical field list `frontmatter.py::WP_FIELD_ORDER` (@49).
- **Sequencing/depends-on**: none. IC-07 reuses this same staging seam (coordinate, do not fork).
- **Risks (priti F1/F13)**: the new `_drop_runtime_frontmatter_only_wp` must parse frontmatter AND assert the markdown **body is byte-unchanged** (a body edit riding alongside a `shell_pid` write must still block — red-first test). Source the runtime field set from the ONE canonical `WP_FIELD_ORDER`, not a fresh inline tuple (avoid a 4th divergent definition). Byte-identical no-op when `auto_commit=True`.

### IC-02 — Analysis-report freshness normalizes pipe-table status cells

- **Purpose**: Stop `mark-status`'s pipe-table `[D]`/`[P]` cell churn from re-staling the analysis-report.
- **Relevant requirements**: FR-002; NFR-002, NFR-005. **Add #1862** (open umbrella) to linkage.
- **Affected surfaces**: `analysis_report.py::_normalize_tasks_md` (@147; extend `_CHECKBOX_RE` @144), `tasks_materialization.py` (pipe-table writers @223/231, reference).
- **Sequencing/depends-on**: none.
- **Risks**: one carefully-anchored added regex; keep the bullet-checkbox behavior; substantive row-text change must still stale (red-first). S.

### IC-03 — Pre-review gate runner: interpreter + contention (M)

- **Purpose**: Make the gate find the runner (`uv run`) and return a real verdict under contention, never a spurious `no_coverage`/`--force`.
- **Relevant requirements**: FR-003, FR-004; NFR-003; C-004.
- **Affected surfaces**: `review/pre_review_gate.py::run_scoped_tests_at_head` (interpreter cmd @379-386; `_DEFAULT_HEAD_RUN_TIMEOUT` @109; `subprocess.run` @388), `tasks_move_task.py::_mt_run_pre_review_gate` caller.
- **Sequencing/depends-on**: **FR-003 + FR-004 are NON-SPLITTABLE** — both wrap the same `subprocess.run`.
- **Risks (priti F3/F4, C-004)**: canonical `MachineFileLock` (`core/file_lock.py:311`) is **async-only** while the runner is sync — name the lock mechanism (async bridge vs scoped `fcntl.flock`) explicitly; give lock-acquire its OWN timeout + fallback-to-run, **decoupled** from the 300s subprocess timeout (else the lock-wait re-creates the false `no_coverage`). MUST add a pytest-lacking-interpreter regression (existing real-subprocess tests run under a pytest-equipped interpreter and MASK #2570.3) and update those two masking tests.

### IC-04 — Manifest `output_path` repo-relative (M)

- **Purpose**: Make the committed profile manifest cross-machine deterministic.
- **Relevant requirements**: FR-006; NFR-004.
- **Affected surfaces**: `tool_surface/profiles/manifest.py` (`_entry_to_json` @101, `_entry_from_json` @139, `_read` @63, `save`; internal key `str(output_path)` @69/73/77/86); prior art `projection.py::_manifest_source_path` @52-59.
- **Sequencing/depends-on**: none.
- **Risks (priti F5)**: NOT a papercut — thread `project_root` through reader+writer while keeping in-memory `output_path`/key ABSOLUTE; relativize only on disk; reconstruct absolute on read; both-forms tolerant (legacy absolute loads with zero migration). Add a keying-invariant regression (relative-store must not break `get_hash`/`.exists()`), plus regenerate the committed manifest once.

### IC-05 — Diagnostics papercuts: issue-matrix error + bulk-edit inference (S)

- **Purpose**: Make the issue-matrix error name the schema-drift column; stop bulk-edit inference blocking on ordinary refactor verbs.
- **Relevant requirements**: FR-007, FR-008; NFR-006, NFR-005.
- **Affected surfaces**: `agent/tasks_parsing_validation.py::_issue_matrix_approval_blocker` (@202-216) + `review/_issue_matrix.py` (SCHEMA_DRIFT detail @262-287); `bulk_edit/inference.py` (weights @21/44, `INFERENCE_THRESHOLD=4` @51, sum @119).
- **Sequencing/depends-on**: none.
- **Risks (renata F10)**: FR-008 true-positive hazard — with threshold 4, dropping the low-weight `+1` lets a **single-HIGH-phrase** bulk edit (score 3) escape. MUST add a single-HIGH-phrase red-first regression that still trips; if it can't pass at threshold 4, adopt the R-08 fallback (require a HIGH or scale qualifier co-occurrence) rather than lowering detection.

### IC-06 — plan/specify scaffold-block ergonomics (M)

- **Purpose**: Make the first happy-path scaffold write return a distinct non-error state instead of `blocked`.
- **Relevant requirements**: FR-009; NFR-005.
- **Affected surfaces**: `agent/mission_setup_plan.py::_emit_setup_plan_result` (@646) + `_commit_plan_if_substantive`; NEW pristine-vs-insufficient predicate near `missions/_substantive.py` (`is_substantive` @237). Consumers to update (priti F11): source prompts `src/doctrine/missions/mission-steps/software-dev/plan/prompt.md` (+ specify prompt), agent-copy regeneration via `spec-kitty upgrade`, and the `next` engine result-switch `runtime/next/_internal_runtime/engine.py:287-292` (an unhandled `scaffolded` must not fall through).
- **Sequencing/depends-on**: none.
- **Risks (priti F9/F10)**: needs a NET-NEW template-pristine predicate (not a string flip). The specify **twin is already shipped** — `mission_create` returns `scaffold_only: success` and there is no `setup-specify` command — so do NOT budget a specify implementation; only align the plan side + named consumers. Populated-but-insufficient must still return `blocked`.

### IC-07 — move-task coord-lane recovery via the authority path (coordination-aware)

- **Purpose**: Replace the manual `git restore` + guard-blocked-commit agent recovery with code-side routing so no manual restore is ever needed.
- **Relevant requirements**: FR-010; C-002.
- **Affected surfaces**: `tasks_move_task.py` staging/commit leg (WORK_PACKAGE_TASK routing via `coordination/commit_router.py`; `skip_target_commit` pre-gate @~1379-1409; reuse `resolve_planning_artifact_staging`). **NOT `commit_guard.block_mission_specs`** (alphonso F3 — dropped).
- **Sequencing/depends-on**: reuse IC-01's `resolve_planning_artifact_staging` seam (avoid a duplicate block-decision). Coordinate with now-MERGED partition-lock #168 + gate-registration refactors #2596/#2598; cross-ref #2300.
- **Risks (alphonso F3/F4/F5/F7)**: MUST NOT add a `block_mission_specs` exemption (WP-file commits already route to primary — no lane `kitty-specs/` commit needed). MUST NOT touch `_mt_resolve_status_placement_ref`/`_collect_status_artifacts`/`_primary_bundle_status_artifacts` (would perturb STATUS_STATE placement). Pin with a DUAL regression: STATUS_STATE ref/event byte-unchanged AND zero `kitty-specs/` entries committed on the lane branch. Re-verify line-anchors at task authoring (plan's `:299`/`:1302-1390` are pre-degod). Staging call lands in `_mt_write_and_commit_wp_file` (~5), NOT `_mt_commit_wp_file` (11). #2580 writer routed through canonical `write_shell_pid_claim`.

### IC-08 — Solo PR-bound coord mission routes empty-coord surface cleanly to primary (#2533, consequence-only)

- **Purpose**: A solo PR-bound `--start-branch` mission whose coord worktree is legitimately empty must resolve its status surface cleanly to PRIMARY (no split-brain warning / manual flatten), read surface proven == write placement.
- **Relevant requirements**: FR-011; C-002; NFR-005.
- **Affected surfaces**: `coordination/surface_resolver.py` — `resolve_status_surface_with_anchor` (@603) `CoordState.EMPTY` arm (@796-804), reusing `probe_coord_state`/`_effective_surface_topology` (@544)/`_husk_is_authoritative_surface` (@508); `_COORD_EMPTY_FALLBACK_WARNING` (@112).
- **Sequencing/depends-on**: none (disjoint files from WP07). Semantic boundary with WP07 (C-002 WP07↔WP08).
- **Scope decision (operator, #2533 latest comment)**: fix the CONSEQUENCE only; the `if pr_bound: return COORD` derivation (#2581, pinned test) STAYS — a separate follow-up revisits it.
- **Risks (alphonso D4)**: MUST extend the resolver's existing coord-state/lanes signals, NOT add a parallel `pr_bound`-sniffing branch (2nd authority). MUST prove read surface == write placement == PRIMARY (kill split-brain by construction; do not merely mute the warning). A coord mission WITH lanes but empty coord STILL warns (true-positive).

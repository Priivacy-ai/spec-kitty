# Implementation Plan: Runtime-State Corpus Cutover

**Branch**: `feat/runtime-state-corpus-cutover` | **Date**: 2026-07-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/runtime-state-corpus-cutover-01KXZ0AX/spec.md`

## Summary

Complete the deferred #2684 corpus cutover: make the reduced event-log snapshot the **unconditional**
authority for work-package runtime state and remove the phase-1 dual-write toggle, following the strict
migration contract `backfill → verify(FAIL-CLOSED) → flip reader+writer → delete fallbacks → reduce`.

Technical approach: the WP03 backfill library (`specify_cli.migration.backfill_runtime_state`) already
implements seed backfill + a fail-closed count+value verify (hardened in #2817). This mission **wires**
that library into two callers — an operator CLI (`spec-kitty migrate backfill-runtime-state`) and an
auto-discovered upgrade migration — through **one shared cutover orchestration helper** (backfill →
verify → atomic per-mission `status_phase` flip), then removes the flag branch across all 12 call
sites, deletes the predicate and the T037 fallbacks, routes the two remaining bypass readers onto the
snapshot seam, and hardens the #2093 invariant to forbid any frontmatter authority read. The deferred
#2684 inert-field reduction (this mission's IC-06) is an optional post-cutover tail. Then (operator
decision) IC-07/IC-08/IC-09 add the resolved-binding record + reconstruction.

The load-bearing invariant is **fail-closed atomicity**: a mission's `status_phase` is flipped **only**
after its backfill+verify passes; a verify failure aborts before any flip and leaves the deployment on
a consistent, non-partially-flipped state.

**Scope generalization (operator decision 2026-07-20):** the mission also makes the WP/dashboard reader
reconstruct a WP's **resolved final-state from the event log** (one canonical reader replacing three
hand-rolled gates), and generalizes the eviction to the WP's runtime **identity** — the *actual*
`role`/`agent_profile`/`model` are event-sourced (recorded at each pick-up, latest-wins), distinct from
the *authored* recommendation in frontmatter, because the actual identity shifts across the lifecycle.
This is the "record + reconstruct" half of #2093's ruling (IC-07/08/09, with a field-authority ADR); the
full fail-closed #2399 *enforcement* stays out of scope. SaaS delivery rides the existing structured
`actor` on the claim transition — no shared-package change on the preferred path.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `typer` (CLI surface); existing `specify_cli.status` (reducer/emit/store facade),
`specify_cli.migration.backfill_runtime_state` (backfill + fail-closed verify), `specify_cli.upgrade`
(auto-discovered migration registry); `pytest` / `mypy` / `ruff`
**Storage**: append-only event log (`status.events.jsonl`) as authority; `meta.json` `status_phase` as the
per-mission cutover marker. No database; no network I/O.
**Testing**: `pytest` — unit (CLI + orchestration helper), fault-injection (verify abort paths),
architectural (`test_2093_authority_invariant`, `test_no_dead_symbols`), and the `status` suite. Run
architectural tests **per-file with a timeout**, never the whole directory (it hangs). Use
`uv run --extra test python -m pytest -p no:cacheprovider <FILE>` (bare `python` resolves a sibling
checkout → false greens).
**Target Platform**: Linux / macOS / Windows CLI (developer tool)
**Project Type**: single project (Python CLI package under `src/specify_cli/`)
**Performance Goals**: backfill+verify is linear in mission count, a few seconds per mission on the
dogfood corpus; no network calls; idempotent re-runs seed nothing.
**Constraints**: fail-closed with **zero** tolerated parity mismatches; WP-file byte-stability after
cutover; `ruff` + `mypy` clean with **no** new `# noqa` / `# type: ignore` / per-file ignores; all
event-writing paths resolve via `canonicalize_feature_dir` (never `Path.cwd()`; #2815/#2647 class).
**Scale/Scope**: remove the flag branch at **12 call sites across 11 files**; delete 1 predicate + its
facade alias/`__all__` entry; delete 2 legacy fallback blocks (1 shared with a bypass reader); route 2
bypass readers; empty 1 arch-test tolerated set + rewrite 1 vacuous test arm; un-pin a 15-symbol
dead-symbol frozenset; add 1 CLI command + 1 upgrade migration. **Eleven implementation concerns** (IC-01,
IC-01b, IC-02–IC-06 cutover; IC-07/IC-08/IC-09 resolved-binding record+reconstruct + the IC-08a ADR;
IC-10 subtask event-sourcing + checkbox removal). IC-08's dispatch→claim linkage and IC-10's
doctrine-template breadth are the scope-growth risks (operator-accepted).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present (`software-dev-default`, DIR-001..013). Relevant gates and this plan's posture:

- **Single canonical authority** (governing principle) — this mission *is* the enforcement: one
  authority (the reduced snapshot), predicate deleted, invariant hardened to forbid any frontmatter
  authority read. ✅ aligned (the whole point).
- **DIR-005 tests for new functionality / ATDD-first (C-011)** — every new branch/helper (CLI command,
  orchestration helper, upgrade migration, bypass-reader reroute) gets focused tests in the same WP,
  including fault-injection for the verify-abort and flip-refusal paths. ✅
- **DIR-006 mypy --strict / Code Quality (no suppression)** — no new blanket ignores; complexity ≤15;
  repeated literals hoisted (Sonar S1192). ✅ (planned as a code-shaping constraint, not cleanup).
- **Git workflow — no direct pushes to origin/main** — mission lands on `feat/runtime-state-corpus-cutover`,
  PR-bound; local `spec-kitty merge` only; operator publishes. ✅
- **Regression Vigilance / Pre-existing Failure Reporting** — the known-P0 reds and the phantom
  `SYNC_DISABLE_ENV_VARS` arch-adversarial red (pre-existing on main, CI-runner artifact) are NOT this
  mission's to fix; attribute before folding. ✅ (recorded in research.md risks).
- **Canonical sources (no improvise)** — reuse the WP03 library and the auto-discovery migration
  registry; do not hand-roll a parallel backfill or a manual migration sequence. ✅

No charter violations requiring Complexity Tracking.

## Project Structure

### Documentation (this mission)

```
kitty-specs/runtime-state-corpus-cutover-01KXZ0AX/
├── plan.md              # This file
├── research.md          # Phase 0 — design decisions + risks
├── data-model.md        # Phase 1 — entities/state (event, snapshot, status_phase marker)
├── quickstart.md        # Phase 1 — operator + upgrade runbook
├── contracts/
│   ├── cutover-cli.md        # Phase 1 — CLI + upgrade-migration behavioural contract
│   └── resolved-binding.md   # Phase 1 — reconstruction reader + vocabulary + SaaS fan-out contract
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── migration/
│   ├── backfill_runtime_state.py       # WP03 library (exists) — backfill + fail-closed verify
│   └── runtime_state_cutover.py        # NEW — shared orchestration: backfill→verify→atomic flip
├── cli/commands/
│   ├── migrate_cmd.py                  # EDIT — add `@app.command("backfill-runtime-state")`
│   ├── implement.py                    # EDIT — remove flag branch (1 site)
│   └── agent/
│       ├── tasks_transition_core.py    # EDIT — remove flag branch
│       ├── tasks_shared.py             # EDIT — remove flag branch
│       ├── tasks_move_task.py          # EDIT — remove flag branch + route ownership bypass reader
│       ├── tasks_mark_status.py        # EDIT — remove flag branch
│       ├── tasks_status_cmd.py         # EDIT — remove flag branch (missed by the brief)
│       ├── workflow_executor.py        # EDIT — remove flag branch
│       └── workflow_cores.py           # EDIT — delete verdict fallback + route review bypass reader (ONE block)
├── status/
│   ├── emit.py                         # EDIT — delete `_phase1_snapshot_authority_active`; keep `_legacy_lane_mirror_enabled`; remove 1 flag branch
│   ├── __init__.py                     # EDIT — drop facade alias + `__all__` entry
│   └── wp_metadata.py                  # EDIT — remove flag branch; (IC-08) reduce inert fields
├── core/
│   └── stale_detection.py              # EDIT — remove flag branch
├── task_utils/
│   └── support.py                      # EDIT — remove flag branch (TWO sites)
├── merge/
│   └── done_bookkeeping.py             # EDIT — build snapshot done-evidence, then delete frontmatter synthesis
├── dashboard/
│   └── scanner.py                      # EDIT — route agent/assignee/subtask reads to snapshot (MISSED bypass reader)
├── frontmatter.py                      # EDIT — stop the shell_pid frontmatter WRITER (byte-stability)
├── task_metadata_validation.py         # EDIT — stop baking shell_pid into WP templates
└── upgrade/migrations/
    └── m_<version>_runtime_state_backfill.py   # NEW — auto-discovered fail-closed upgrade migration

tests/
├── architectural/
│   ├── test_2093_authority_invariant.py   # EDIT — `_SANCTIONED_READER_MODULES` → frozenset(); rewrite vacuous gate-identity arm
│   └── test_no_dead_symbols.py            # EDIT — remove 15-symbol `_CATEGORY_C_DEFERRED_RUNTIME_STATE_BACKFILL_CUTOVER`
├── (status suite)                          # EDIT — reconcile flag-ON/flag-OFF split; delete/re-point dual-write tests
└── (new)                                   # NEW — CLI command, orchestration helper, upgrade migration, #2815 repo-root-write guard

# Resolved-binding scope (IC-07/08/09, operator decision):
src/specify_cli/status/wp_view.py            # NEW (IC-07) — canonical reconstruct_wp_view; 3 gates → 1
src/specify_cli/status/models.py             # EDIT (IC-08) — WPInnerStateDelta: +role/agent_profile(+version)/model/provider
src/specify_cli/status/reducer.py            # EDIT (IC-08) — _RUNTIME_SLOTS + _apply_annotation_delta: resolved-binding slots
src/specify_cli/cli/commands/agent/workflow_executor.py  # EDIT (IC-08) — resolve seam at claim/review-claim
src/specify_cli/invocation/executor.py       # READ/EDIT (IC-08) — thread resolved model (RoutingRecommendation, advisory today)
src/specify_cli/status/emit.py               # EDIT (IC-09) — enrich structured actor on claim StatusEvent + fan-out
docs/adr/3.x/2026-07-19-1-*.md               # EDIT (IC-08a) — field-authority addendum (C-009)
docs/context/identity.md                     # EDIT (IC-08a) — add authored-intent / resolved-binding terms
```

**Structure Decision**: Single-project Python CLI. Net-new modules: `migration/runtime_state_cutover.py`
— a thin **shared orchestration seam** (backfill → fail-closed verify → atomic per-mission `status_phase`
flip) consumed by *both* the operator CLI and the upgrade migration, so the fail-closed atomicity lives
in one place (avoids two callers re-implementing verify-then-flip); and `status/wp_view.py` — the single
**WP-view reconstruction reader** (IC-07) that collapses the three hand-rolled snapshot gates. The
resolved-binding vocabulary (IC-08) extends `status/models.py`/`reducer.py`; everything else is edits.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs. The **contract order**
> (C-001) is the hard sequencing spine: IC-01 (wire) → **IC-01b (RUN the backfill on this repo's own
> corpus + commit the seeds)** → IC-03 (unconditional flip) → IC-04 (wire snapshot done-evidence, then
> delete fallbacks). IC-05 hardens the end-state; IC-06 is an optional tail.
>
> **⚠️ Merge-unit atomicity (post-planning review, BLOCKER-fix):** IC-01b, IC-03, and IC-04 must land in
> **one merge unit** (the mission PR) with the dependency edges below enforced during WP-by-WP merge to
> local main. If IC-03 (unconditional readers) reaches local main before IC-01b has committed this
> repo's seed events, **every dogfood mission reads an empty snapshot** and the suite goes red instantly
> — this is the exact contract-step-ownership gap the mission's own field report documents. The plan
> owns the backfill *execution*, not just the *tool*.
>
> **Scope generalization (operator decision 2026-07-20):** IC-07/IC-08/IC-09 add the resolved-binding
> "record + reconstruct" slice — the WP/dashboard reader reconstructs resolved final-state from the event
> log, and the actual `role`/`agent_profile`/`model` are event-sourced (distinct from authored intent).
> These build on the cutover (depend on IC-03/IC-04) and carry their own ADR (IC-08a). The full
> fail-closed *enforcement* (#2399) stays out of scope. **Closeout correction:** the C-009 ADR forbids
> historical authored-to-resolved seeding. IC-07 therefore intentionally shows empty resolved slots for
> legacy WPs until a genuine resolver-backed pick-up records an actual binding.

### IC-01 — Cutover orchestration + operator CLI (backfill → verify → atomic flip)

- **Purpose**: Give the corpus cutover an invocable, fail-closed entry point that seeds runtime state
  as events, verifies count+value parity against the old reader, and flips `status_phase` **only** for
  missions that pass — the load-bearing safety mechanism.
- **Relevant requirements**: FR-001 (dry-run CLI), FR-002 (wire the library's fail-closed verify),
  FR-003 (atomic verify-then-flip; sole `status_phase` writer), NFR-001, NFR-002, NFR-006, C-003.
- **Affected surfaces**: NEW `migration/runtime_state_cutover.py` (orchestration helper);
  `cli/commands/migrate_cmd.py` (new `backfill-runtime-state` command with `--dry-run`,
  `--mission`, whole-corpus default); consumes `backfill_runtime_state_repo` / `run_backfill_and_verify`.
  **Removes** the 15-symbol `_CATEGORY_C_DEFERRED_RUNTIME_STATE_BACKFILL_CUTOVER` frozenset from
  `tests/architectural/test_no_dead_symbols.py` (this WP is the first real caller — un-pin is mandatory
  here or the ratchet trips).
- **Sequencing/depends-on**: none (library exists). This is the spine's first step.
- **Risks**: `status_phase` has no existing writer — this helper is the *only* writer; guard against a
  hand-flip of an unverified mission (refuse-to-flip on non-`ok` verify). Dead-symbol un-pin must land
  in the same WP that adds the caller. `#2815` class: write target via `canonicalize_feature_dir` only.

### IC-01b — Execute the dogfood corpus backfill + commit the seeds (BLOCKER-fix)

- **Purpose**: RUN `migrate backfill-runtime-state` over **this repo's own `kitty-specs/`** and **commit**
  the resulting seed events + `status_phase` flips, so that when IC-03 makes readers unconditional, every
  dogfood mission already has its runtime state in the event log. Without this, the contract's
  *backfill-execution* step has no owner in the merge unit (the #2684 field-report failure mode).
- **Relevant requirements**: FR-001/FR-002/FR-003 applied to *this* corpus; C-001 (order); NFR-001.
- **Affected surfaces**: `kitty-specs/**/status.events.jsonl` (seed-event deltas — data, not code),
  `kitty-specs/**/meta.json` (`status_phase` flips). No source edits.
- **Sequencing/depends-on**: **depends-on IC-01**; **blocks IC-03 and IC-04**; lands in the same merge unit.
- **Risks**: currently **all 299 dogfood missions are `status_phase=0`** and their runtime slots live in
  frontmatter only (no events) — the seed diff is large but is exactly the migration payload. Acceptance:
  post-run, `wp_snapshot_state` is non-empty for every mission that carries runtime state, corpus-wide
  `verify_backfill` is `ok`, and a sampled done mission's `_infer_subtasks_complete` returns the correct
  value **with the predicate deleted** (dry-run IC-03 locally to prove it). Re-runnable/idempotent.

### IC-02 — Upgrade-path migration (existing deployments)

- **Purpose**: Ensure existing deployments migrate their corpus on `spec-kitty upgrade` so the
  unconditional cutover does not strand un-migrated on-disk WP state; fresh installs no-op.
- **Relevant requirements**: FR-010, NFR-002 (idempotent), NFR-005 (abort safety), C-003.
- **Affected surfaces**: NEW `upgrade/migrations/m_<version>_runtime_state_backfill.py` (self-registers
  via `@MigrationRegistry.register`; version-key ordered to sort **after** the charter folds); reuses
  the IC-01 orchestration helper. NEW `#2815` regression test (no `status.events.jsonl` at repo root).
- **Sequencing/depends-on**: IC-01 (reuses the shared orchestration helper; do not fork verify-then-flip).
- **Risks**: a verify failure must abort the migration step with an operator-actionable message and
  leave no partial flip (NFR-005). Auto-discovery ordering is name-encoded — pick a version prefix that
  sorts after the charter-fold migrations.

### IC-03 — Unconditional reader/writer cutover (flip the flag, delete the predicate)

- **Purpose**: Make the snapshot the authority everywhere by removing the flag-OFF branch and deleting
  the predicate, so runtime writes are event-only and WP files are byte-stable.
- **Relevant requirements**: FR-004 (12 sites / 11 files), FR-005 (delete predicate + facade export),
  NFR-003 (WP-file byte-stability), C-002 (predicate deleted, not defaulted), C-004 (keep
  `_legacy_lane_mirror_enabled`).
- **Affected surfaces**: the 12 call sites in 11 files (see Project Structure); `status/emit.py` (delete
  `_phase1_snapshot_authority_active`, keep `_legacy_lane_mirror_enabled`); `status/__init__.py` (drop
  alias + `__all__`); remove each paired local `from specify_cli.status import …` import.
- **Sequencing/depends-on**: **IC-01b** (C-001: this repo's corpus must be backfilled + committed before
  readers go unconditional) — transitively IC-01. Same merge unit.
- **Risks**: undersizing — the brief said "~10"; the real surface is 12/11 incl. `tasks_status_cmd.py`
  and the double site in `support.py`. Each site collapses *differently* (not a mechanical rename → not
  a bulk edit). **Must NOT touch `_legacy_lane_mirror_enabled`** — it is KEPT (C-004) and **still reads
  `status_phase`**, so the flip has a live consequence: flipping a mission to `status_phase=1` **activates
  the lane mirror** for it (today all missions are `status_phase=0` → mirror OFF). Add a regression
  asserting lane behaviour is unchanged by the mirror activation; if activation is problematic, decoupling
  the lane mirror from `status_phase` is a **follow-up** (still C-004 out-of-scope here). **Byte-stability
  (NFR-003) requires the writer cutover too** — the `shell_pid` frontmatter **writer**
  (`frontmatter.py:write_shell_pid_claim`) and the template emitter (`task_metadata_validation.py`) must
  stop writing runtime fields to `tasks/WP##.md`, or the file is not byte-stable even with readers cut
  over (see IC-04 surface sweep).

### IC-04 — Wire snapshot done-evidence, then delete T037 legacy fallbacks + route bypass readers

- **Purpose**: Move done-evidence / verdict / ownership reads onto the snapshot seam and remove the
  frontmatter fallbacks — **including building the event-sourced done-evidence read that does not yet
  exist** (post-planning review: the "replacement" is a gap, not a given).
- **Relevant requirements**: FR-006 (delete fallbacks + build snapshot done-evidence), FR-007 (route
  bypass readers), C-001 (order).
- **Affected surfaces**:
  - `merge/done_bookkeeping.py` — **NEW scope**: `_extract_done_evidence` (95-113) AND the `:295-304`
    fallback both read frontmatter (`meta.review_status`/`reviewed_by`/`metadata.agent`); **neither reads
    the snapshot `review` slot** where the backfill puts the evidence. Wire `_mark_wp_merged_done` /
    `_extract_done_evidence` onto the snapshot `review` slot **first**, then delete the frontmatter
    synthesis. This is real implementation, not "delete + verify".
  - `cli/commands/agent/workflow_cores.py` — `resolve_review_feedback_context`: the verdict fallback
    (FR-006a) and the `review_status`/`review_feedback` bypass reader (FR-007) are the **same block** →
    ONE edit that deletes the fallback and resolves via the snapshot.
  - `cli/commands/agent/tasks_move_task.py` — route the `agent`/`current_agent` ownership read onto the
    snapshot accessor.
  - **`dashboard/scanner.py` — MISSED BYPASS READER (found by the dashboard-path review).**
    `_process_wp_file` reads runtime `agent` (:937), `assignee` (:978), and subtask completion (:954-965,
    checkbox-counting) via `read_wp_frontmatter(...).<attr>` — **attribute access on typed `WPMetadata`,
    not `extract_scalar`** — so it escaped the pre-planning #2093-debt list AND the arch invariant. Route
    the **runtime** fields (`agent`, `assignee`, subtask completion) onto the snapshot. For
    `role`/`agent_profile`/`model`: keep the **AUTHORED** recommendation frontmatter-sourced, but the
    **RESOLVED actual** is event-sourced and reconstructed via IC-07/IC-08 (FR-012/FR-013) — do NOT leave
    the resolved value frontmatter-read. The lane already comes from the event log (`get_wp_lane`, :918).
  - **Reader/writer surface sweep (found by the events-boundary review — confirm at `/tasks`)**:
    `core/stale_detection.py:231` (`_is_claiming_process_alive` — verify it fully sources `shell_pid`
    from the snapshot post-cutover, not a partial/conditional read); `frontmatter.py:321`
    (`write_shell_pid_claim` — the dual-write **WRITER** that still writes `shell_pid` to `tasks/WP##.md`;
    must stop for NFR-003 byte-stability); `task_metadata_validation.py:86,141` (bakes `shell_pid` into
    generated WP frontmatter templates); `ownership/frontmatter_source.py` and `context/resolver.py`
    (targeted check for `assignee`/`agent` reads).
- **Sequencing/depends-on**: IC-03 (fallbacks safe to delete only after the flip; C-001) and **IC-01b**
  (backfill has seeded the approvals/review as events in this corpus). Same merge unit.
- **Risks**: `done_bookkeeping` feeds the **merge** gate — deleting synthesis before the snapshot read is
  wired drops event-only missions to the lane-approved fallback with degraded reviewer attribution
  (`metadata.agent` → `"unknown"` once `agent` is snapshot-sourced). **Acceptance test**: an event-only
  mission with NO frontmatter review produces correct `DoneEvidence` through the merge path. FR-006a and
  FR-007-workflow_cores are one block — do not decompose into two edits to the same lines.

### IC-05 — Authority-invariant hardening (#2093) + test-suite reconciliation

- **Purpose**: Lock the single-authority end-state so no frontmatter authority read can regress, and
  reconcile the flag-ON/flag-OFF split test suite to the single end-state.
- **Relevant requirements**: FR-008 (empty tolerated set + rewrite vacuous arm), FR-009 (reconcile
  split suite), C-006 (arch-gate updated not suppressed), SC-003, SC-004, SC-006.
- **Affected surfaces** (post-planning review: **~33 test files, not "the status suite"** — the union of
  `status_phase`/`_phase1` refs (~25 files) and `dual-write` refs (~17 files) spans `cli/commands/agent`,
  `core`, `sync`, `orchestrator_api`, `integration`, `regression`, `upgrade`):
  - `tests/architectural/test_2093_authority_invariant.py` — `_SANCTIONED_READER_MODULES` → `frozenset()`;
    rewrite the now-vacuous canonical-gate-identity arm (imports the deleted predicate) into a "zero
    frontmatter-authority reads" assertion. **CRITICAL COVERAGE GAP (found by the dashboard review):**
    the detector `_reads_dynamic_field_via_extract_scalar` (:312) only matches `extract_scalar(…, "<field>")`
    calls — it is **blind to attribute-access reads** (`read_wp_frontmatter(...).agent`, `WPMetadata.<runtime>`,
    `WorkPackage.<runtime>`). Emptying the tolerated set is a **false green** until the invariant also
    detects the attribute-read class. IC-05 must **extend the detector** to catch runtime-field attribute
    reads on the typed frontmatter/metadata objects, then confirm it flags the dashboard scanner **red
    before** IC-04 reroutes it (non-vacuous proof).
  - the explicit **flag-ON/flag-OFF pair** `test_move_task_rollback_clears_claim.py` +
    `..._flag_off.py` — delete the flag-OFF twin; make the flag-ON assertions unconditional.
  - `test_tasks_compat_surface.py` — asserts the facade seam IC-03 removes → reconcile (breaks on the
    alias drop otherwise).
  - `tests/architectural/baselines/fast-tests-core-misc-nodeids.txt` (and the gate-coverage baselines) —
    **regenerate**; deleted/renamed test node IDs trip both baselines (`--update-baseline` /
    `--freeze-baselines`).
  - Add the NFR-003 byte-stability regression and the #2815 repo-root-write guard if not already added
    in IC-01/IC-02.
- **Sequencing/depends-on**: IC-03 and IC-04 (the invariant/tests must reflect the end-state). Own WP;
  enumerate the full ~33-file set at `/tasks`.
- **Risks**: the arm rewrite is more than a set edit — the test currently asserts the *identity* of the
  canonical gate symbol, which no longer exists. Keep the guard **non-vacuous** (a reintroduced
  frontmatter read must still fail it). Undersizing IC-05 is the plan's second-biggest risk after IC-01b.

### IC-06 — IC-08 inert-field reduction (optional tail; the deferred #2684 IC-08)

- **Purpose**: Remove the now-inert `wp_metadata` fields and cosmetic `WP_FIELD_ORDER` slots that fed
  the retired legacy path — pure hygiene, safe only post-cutover.
- **Relevant requirements**: FR-011 (Low / optional / deferrable).
- **Affected surfaces**: `status/wp_metadata.py` (inert field definitions), `WP_FIELD_ORDER` slots; the
  `wp_snapshot_state` accessor dedup already shipped in #2817 so this is field/slot removal only.
- **Sequencing/depends-on**: IC-03 (post-cutover). **Deferrable** — does not gate mission DoD; may split
  to a fresh follow-up issue (then the PR uses `Contributes to #2816`, not `Closes`).
- **Risks**: **`status_phase` is OUT OF BOUNDS for IC-06** (post-planning correction) — the kept
  `_legacy_lane_mirror_enabled` still reads it (C-004), so retiring the field would silently disable the
  lane mirror. Scope IC-06 to `wp_metadata` runtime fields only. Otherwise non-behavioural; keep the full
  suite green; confirm zero live readers before removal (`assert_zero_readers` proof).

### IC-07 — Canonical WP-view reconstruction reader (collapse 3 gates → 1)

- **Purpose**: Replace the three independently hand-rolled snapshot-authority gates with ONE reader that
  reconstructs a WP's resolved final-state from the event log/snapshot for all dynamic fields, and
  surfaces the authored/recommended assignment from frontmatter **distinctly** — so the dashboard, the
  CLI status board, and `WorkPackage` can never disagree.
- **Relevant requirements**: FR-012, C-008 (authored vs resolved never conflated), SC-007, SC-008.
- **Affected surfaces**: NEW `status/wp_view.py::reconstruct_wp_view(feature_dir, wp_id)` (or extend
  `status/wp_metadata.py::_resolve_runtime_fields_from_snapshot`); force the three readers onto it —
  `dashboard/scanner.py::_process_wp_file`, `cli/commands/agent/tasks_status_cmd.py` (the `agent tasks
  status` board — a **third missed reader**, reads `agent_profile` via `extract_scalar` at :289 and feeds
  the human-in-charge sentinel `_get_hic_marker`), `task_utils/support.py::WorkPackage` (no
  `model`/`role`/`agent_profile` property today; third copy of the gate). **Scope the reader to
  identity/runtime fields ONLY** (adversarial finding): the dashboard also produces presentation fields
  (`title` regex'd from the prompt body, `prompt_markdown`, `prompt_path`) NOT in the reader's contract —
  keep those consumer-side or the reroute reads as a regression. The **subtasks** authority is resolved by
  IC-10 (snapshot slot, checkboxes removed) — the reader reads the slot, not `tasks.md` counting.
- **Sequencing/depends-on**: IC-03/IC-04 (reads the post-cutover snapshot) and IC-08 (needs the resolved
  `role`/`profile`/`model` slots to reconstruct them).
- **Risks**: the three gates encode subtly different fallback behaviour; unify carefully and keep a test
  per consumer proving parity (SC-007). `prompt_builder.py` reads authored `agent_profile` for governance
  rendering — that is authored intent (correctly frontmatter); do not reroute it. **Tolerate-absent
  (historical absence):** IC-07 MUST handle a WP with no resolved-binding slots (never reclaimed, or predating
  resolver-backed binding capture) by showing the authored recommendation + an empty/None resolved actual — never a
  crash or a silent fall-back to reading the authored value *as* the resolved one (that would re-introduce
  the split-brain). Add this to SC-008/INV-8's coverage.

### IC-08 — Resolved-binding vocabulary + dispatch→claim linkage (operator: full model-actual now)

- **Purpose**: Record the **actual** resolved `role`/`agent_profile`(+version)/`model`/`provider` on the
  event log at each pick-up, folded latest-wins into the snapshot, so the reconstruction reader (IC-07)
  has a source. Net-new eviction (NOT in the event vocabulary today).
- **Relevant requirements**: FR-013 (vocabulary), FR-014 (dispatch→claim linkage), C-007 (never re-read
  frontmatter), C-009 (ADR), C-011 (no authored-to-resolved historical fabrication), SC-008.
- **Affected surfaces**:
  - **Vocabulary**: extend `WPInnerStateDelta` (`status/models.py` + `to_dict`/`from_dict`/`is_empty`) —
    **data-drive the field list** (tidy-first) so 5 new slots don't triple-enumerate. Reducer
    `status/reducer.py`: add `role`/`agent_profile`/`agent_profile_version`/`model`/`provider` to
    `_RUNTIME_SLOTS` + `_apply_annotation_delta` — **first extract the flat if-chain into a data-driven
    replace-slot table** (tidy-first: `_apply_annotation_delta` is cx 13 and these slots push it >15).
  - **Dispatch→claim linkage (operator decision Q1 — the real work)**: the genuine model + profile are
    resolved only on the dispatch/Op path (`invocation/executor.py` `RoutingRecommendation.model` +
    `registry.resolve`; recorded in `invocation/record.py`, keyed by `invocation_id`) — the claim seam has
    only the bare `--agent` string + frontmatter-coerced values (C-007-forbidden to record). **Thread the
    resolved model+profile(+`invocation_id`) into the implement/review commands** (`cli/commands/agent/workflow.py`
    — new `--model`/`--profile`/`--invocation-id` options or a sanctioned side-channel), consumed at the
    claim seams (`workflow_executor.py` implement-claim + review-claim) and the `tasks_move_task.py` reassign.
    This is a **cross-layer addition** (dispatch/invocation + command surface + claim seams).
  - **Emit shape (annotation + actor, reconciled)**: emit the binding as an **`InnerStateChanged`
    annotation** (latest-wins at BOTH implement-claim and review-claim — the claim `policy_metadata` fold
    fires only on `planned→claimed`, so review-claim would be missed), AND enrich the transition's
    structured `actor` for the IC-09 fan-out. Both, not either.
  - **Historical binding non-seed + corpus correction (C-011)**: the backfill MUST NOT copy authored
    `role`/`agent_profile`/`model` into resolved-actual slots. Legacy WPs remain explicitly unresolved
    until a genuine resolver-backed runtime event exists. Remove any earlier deterministic
    `_seed_id(…, "resolved_binding")` rows by exact seed identity and preserve all non-seed annotations.
    Acceptance proves authored-only legacy WPs remain empty in the resolved group.
  - **IC-08a — ADR (C-009)**: author the field-authority ADR (addendum to `2026-07-19-1`, model-election
    blocker B4): resolved `role`/`agent_profile`/`model` → dynamic/event; authored → static/frontmatter.
    Add `authored intent`/`resolved binding` to `docs/context/identity.md`.
- **Sequencing/depends-on**: IC-01b/IC-03 (post-cutover snapshot is authority); IC-08a ADR precedes the
  vocabulary change. Feeds IC-07 and IC-09.
- **Risks**: the dispatch→claim linkage is the scope-growth risk — it touches the invocation layer and the
  command surface; keep the resolved values flowing from the resolver (C-007), and where a genuine model is
  still unavailable for a given path, record it **explicitly absent**, never fabricated/frontmatter-copied.
  Historical authored-to-resolved fabrication (C-011) is a provenance violation if retained.

### IC-09 — SaaS fan-out of the resolved binding

- **Purpose**: Deliver the resolved binding across the package boundary to the SaaS consumer (already
  aware), preferentially with zero shared-package change.
- **Relevant requirements**: FR-015.
- **Affected surfaces**: **Preferred** — enrich the structured `actor` (`{role, profile, tool, model}`) on
  the claim/review `StatusEvent` and its existing lane fan-out (`_saas_fan_out`, `emit.py:954-1008`);
  `spec_kitty_events` 6.1.0 `StatusTransitionPayload.actor` is already `Union[str, Dict]` → no shared-package
  change. **⚠️ LOCAL PLUMBING REQUIRED (adversarial finding):** the local emit path is `str`-typed
  end-to-end — `StatusEvent.actor: str` (`status/models.py:258`), `build_status_event(actor: str)`
  (`emit.py:145`), `emit_status_transition(actor: str|None)` (`emit.py:512`), and `from_dict` does
  `str(data["actor"])` (`models.py:360,:506`) which would **corrupt a dict actor on round-trip**. IC-09
  must widen `actor` to `str | dict` across those signatures, guard the `str(...)` coercions so a dict
  survives JSONL round-trip, and audit every reducer/consumer doing string ops on `actor`. So FR-015 is
  **"zero *shared-package* change, non-trivial *local* type-surface change"** — size it accordingly.
  **Fallback** — a new `WPResolvedBindingChanged` shared event + a fan-out added to
  `emit_inner_state_changed` (none today, `emit.py:941-949`), version-gated like the genesis-lane gate
  (`emit.py:82-94`).
- **Sequencing/depends-on**: IC-08 (the resolved actuals must exist to fan out). Coordinate the final
  contract with the SaaS team.
- **Risks**: the local `actor` type-surface change touches mypy-strict signatures across the emit chain —
  bigger than "pass the dict through". Cross-repo: the fallback off-axis event needs a `spec_kitty_events`
  release; the version gate lets #2816 land locally now and enable fan-out when the package ships (never
  block-on-shared). Feature-detect the structured-dict actor defensively before sending.

### IC-10 — Subtask completion fully event-sourced; markdown checkboxes removed (operator decision Q2)

- **Purpose**: Make the snapshot `subtasks` slot the **sole** authority for subtask completion, remove the
  `- [ ] T###` markdown checkboxes (the incoherent proxy the WP view must stop reading), and redirect
  agents to `mark-status`.
- **Relevant requirements**: FR-016, C-010 (removal ordered after seed), NFR-003.
- **Affected surfaces**:
  - **Reader reroute**: dashboard (`dashboard/scanner.py:954-965` checkbox counting) and any subtask-count
    reader → snapshot `subtasks` slot (via IC-07's reader).
  - **Lane-transition guard**: `core/subtask_rows.py` (`iter_wp_section_subtask_rows` /
    `count_wp_section_subtask_rows`) is the guard's blocking source — reroute the guard onto the snapshot
    `subtasks` slot, then retire the checkbox parsing.
  - **Checkbox removal**: strip `- [ ] T###` rows from `tasks.md`/WP templates — **only after** the
    backfill has seeded historical completion from them (C-010). The backfill's `_subtasks_from_tasks_md`
    reads them, so backfill-then-remove ordering is mandatory.
  - **Doctrine prompt templates (breadth risk)**: `src/doctrine/missions/mission-steps/…` + tasks
    templates that instruct checkbox ticking → direct agents to `spec-kitty agent tasks mark-status`.
    Propagates to all agent copies via `spec-kitty upgrade` (do NOT hand-edit agent dirs). Run the
    terminology guard + docs-freshness after prose edits.
- **Sequencing/depends-on**: IC-01b (backfill seeds subtask completion from checkboxes first), IC-07
  (reader reads the slot). Checkbox removal lands after the seed (C-010).
- **Risks**: **large doctrine/template surface** (13 agents' prompt families + the lane guard); the guard
  reroute is behaviour-sensitive (it blocks lane transitions on incomplete subtasks). Add a regression
  proving the guard blocks/*un*blocks correctly off the snapshot. Historical missions whose checkboxes are
  removed must already be seeded (C-010) or their completion is lost.

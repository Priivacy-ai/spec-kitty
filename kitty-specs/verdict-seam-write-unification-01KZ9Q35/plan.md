# Implementation Plan: Verdict-Seam Write-Side Unification

**Branch**: `feat/verdict-seam-write-unification` | **Date**: 2026-08-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/verdict-seam-write-unification-01KZ9Q35/spec.md`

## Summary

Complete the review-cycle verdict-seam write-side unification (PR #3211 / epic #3044 follow-up).
The **primary requirement**: a work package's current verdict has exactly one authority — the
event-sourced reducer snapshot — read identically by every gate, the dashboard, and fix-mode.

**Technical approach — the load-bearing ordering decision.** The post-spec squad proved that the
naive "flip the `.md` write seam + its safety reader atomically" framing (spec FR-001) is neither
the only safe order nor the simplest. Instead the plan sequences **collapse-first**:

1. Harden the census predicate (so it can *prove* reader retirement).
2. Populate + serialize the event authority (backfill historical `.md` verdicts; route durability
   to the event log).
3. **Repoint every verdict reader to the event snapshot** and delete the frontmatter readers.
4. **Only then** relocate the now-prose-only `.md` write to the COORD partition.

Once step 3 lands, no consumer reads the `.md` for a verdict, so step 4's write-partition flip is
**no longer safety-critical** — it is a prose relocation. This *dissolves* FR-001's commit-atomicity
requirement via ordering while still meeting its guarantee (no partial-order fail-open), and it is
the only order that satisfies the two blocker findings (authority must be populated before readers
flip; the un-migrated cohort must be backfilled first). The `#2804`/`#2404` gate-artifact fix is an
independent, parallel-safe track.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `typer`, `ruamel.yaml`; internal — `specify_cli.status` (reducer/emit/store),
`specify_cli.coordination.commit_router`, `mission_runtime.placement_seam`, `spec_kitty_events`
**Storage**: git — event log `status.events.jsonl` (coord branch, union-merge-driver protected);
`review-cycle-N.md` prose files; `acceptance-matrix.json` / `issue-matrix.json` (COORD partition)
**Testing**: `pytest` targeted per-WP surface. Key gates: `tests/architectural/test_verdict_seam_census.py`,
`tests/architectural/test_2093_authority_invariant.py`, `tests/coordination/test_analysis_report_rehome.py`,
`tests/regression/test_issue_2804_merge_resets_gate_artifacts.py`,
`tests/integration/test_review_durability_matrix.py` (50×2 processes, serial `-n0`),
`tests/review/test_cycle.py`. `PWHEADLESS=1` for any UI; real-port/daemon tests run `-n0`.
**Target Platform**: Linux / macOS / Windows CLI
**Project Type**: single (existing `specify_cli` package)
**Performance Goals**: verdict recording (incl. durable persistence) < 2 s (NFR-005); exactly one
authoritative durability call per verdict (NFR-004)
**Constraints**: NFR-001 no inter-process lock across a `git` subprocess; census reds on shrinkage
(retirements land same-change); canonical sources only; change_mode `normal` (no renames)
**Scale/Scope**: repo-wide seam — ~20–24 source files across 6 implementation concerns; ~10 test
surfaces; 47-row census fixture rewritten to the post-flip derived set

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter principle | Status | Note |
|---|---|---|
| Single canonical authority | ✅ core intent | The mission *is* the collapse to one verdict authority; SC-007 makes it structural (artifact carries no verdict field) |
| ATDD-first / red-first | ✅ | Two carry-red pins already exist (`p#3044/C-005`); every new behaviour lands failing-first through a pre-existing entry point |
| DDD + tiered rigour | ✅ | Verdict authority is core domain → highest rigour; the `.md` prose relocation and matrix write-surface are glue → standard rigour |
| Canonical sources / no improvise | ✅ | Reuses `emit_status_transition`, `event_sourced_review_result`, the owner resolver, existing merge drivers + `clear_coordination_metadata` |
| Terminology canon | ✅ | Mission-not-Feature; run `test_no_legacy_terminology.py` pre-push (doctrine/prose untouched, but census/CLI text is) |
| Architectural gate discipline | ✅ | Non-vacuous gates: census (shrinkage-red), `test_2093` derived ratchet, SC-007 no-verdict-field check |
| PRs only / operator merges | ✅ | Feature branch → PR → `main`; operator merges |

**No charter violations.** Complexity Tracking below is empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/verdict-seam-write-unification-01KZ9Q35/
├── plan.md              # This file
├── research.md          # Phase 0 — plan-phase decisions (this command)
├── data-model.md        # Phase 1 — entities/invariants/state
├── quickstart.md        # Phase 1 — how to run the gates
├── contracts/           # Phase 1 — seam contracts
│   ├── verdict-authority-read.md
│   ├── verdict-durability-write.md
│   ├── vocabulary-bridge.md
│   ├── census-predicate.md
│   ├── provenance-backfill.md
│   └── gate-artifact-write-surface.md
├── research/
│   └── pre-spec-research.md   # the 5-stream pre-spec investigation
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── review/
│   ├── cycle.py                    # write seam _review_cycle_wp_dir; durability demote (FR-001/003/008)
│   ├── artifacts.py                # verdict-parser family retire; .md written w/o verdict field (FR-003/SC-007)
│   └── arbiter.py                  # persist_arbiter_decision root threading (FR-016)
├── status/
│   ├── reducer.py                  # event_sourced_review_result (authority); backfill reduce (FR-012)
│   ├── emit.py                     # emit_status_transition durability path (FR-008)
│   └── models.py                   # canonical vocabulary bridge surface (FR-005)
├── agent_utils/status.py           # dashboard/kanban readers → snapshot (FR-004)
├── cli/commands/agent/
│   ├── tasks_verdict_persistence.py    # resolve_review_verdict_facts → snapshot (FR-002)
│   ├── tasks_parsing_validation.py     # delete _get_latest_review_cycle_verdict (FR-005)
│   ├── workflow*.py                    # has_prior_rejection / fix-mode raw joins re-home (FR-001/006)
├── post_merge/review_artifact_consistency.py   # merge gate → pure-event (FR-013)
├── migration/
│   ├── backfill_runtime_state.py       # census .from_dict gap example (FR-010)
│   └── <new> verdict_provenance_backfill.py    # FR-012 backfill + provenance gate
├── merge/executor.py                   # accept→COORD write surface; driver registration (FR-009)
├── cli/commands/merge_driver.py        # review-cycle driver relax; matrix drivers (FR-009/014)
└── cli/commands/init.py                # .gitattributes driver registration / seed-drift fix (FR-009)

tests/
├── architectural/{verdict_seam_census.yaml, test_verdict_seam_census.py, test_2093_authority_invariant.py}
├── coordination/test_analysis_report_rehome.py     # re-pin physical path (FR-001)
├── regression/test_issue_2804_merge_resets_gate_artifacts.py   # green existing pin (FR-009)
├── integration/test_review_durability_matrix.py    # SC-003 concurrency
├── review/test_cycle.py                            # NFR-005 perf
└── status/test_reducer.py                          # WP07 hermetic re-pin; backfill tests
```

**Structure Decision**: single existing package (`specify_cli`), in-place seam unification. No new
top-level packages; one new migration module (`verdict_provenance_backfill.py`) for FR-012.

## Complexity Tracking

*No Charter Check violations — table intentionally empty.*

## Implementation Concern Map (revised — post-plan squad, D-PLAN-9..16)

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs. The **Sequencing**
> lines are load-bearing (spec C-008). **Shared-file serialization**:
> `{verdict_seam_census.yaml, verdict_seam_IC01.yaml}` bind IC-01/02/02b/03/04;
> `{merge_driver.py, init.py}` bind IC-04/06b. Only **IC-06a** is a genuinely parallel lane.
> File-count re-baselined to **~35** (named-only floor was 20-24). Before `/tasks`, every census row
> is mapped to an owning IC (`orchestrator_api::_parse_review_result_json` parses injected JSON, not
> frontmatter → stays a reader-of-JSON, but its inline vocab is swept by IC-02b).

### IC-01 — Census predicate hardening (lands FIRST)

- **Purpose**: Extend the census AST derivation to classify `.from_dict`/factory-constructed records
  (real missed site: `status/models.py:570`; `backfill_runtime_state::_runtime_repair_delta` uses a
  *direct* ctor already matched — verify before claiming it as the gap), with named
  `_EXCLUDED_MODULE_REASONS` for event-authority deserializers **and** the new backfill migration.
  Lands first so the census can *prove* reader retirement during the collapse.
- **Relevant requirements**: FR-010; NFR-002; SC-006.
- **Affected surfaces**: `test_verdict_seam_census.py` (`_derive_census`, `_RECORD_CTOR_CALL_RE`,
  `_contains_ctor`, `_EXCLUDED_MODULE_REASONS`); `verdict_seam_census.yaml`; `verdict_seam_IC01.yaml`.
- **Sequencing/depends-on**: none. **Precedes IC-02b/03/04.** Red anchor: a synthetic `.from_dict`
  poison test (**to-write**, red-first — no `.from_dict` reference in the census today).
- **Risks**: over-match — mitigated by named exclusions.

### IC-02 — Event-authority foundation: backfill + durability-add (lands SECOND)

- **Purpose**: Populate + serialize the event authority for *every* mission before any reader flips,
  **without** demoting the `.md` yet. (a) FR-012: a migration reducing each existing **terminal** `.md`
  verdict into `status.events.jsonl` via `append_events_atomic_verified` (NOT `emit_status_transition`
  — D-PLAN-10), with the event's `at` = the **historical** verdict timestamp, "terminal" defined,
  supersession handled, temporal idempotency key; plus a **new provenance predicate** ("terminal `.md`
  verdict + no event slot") distinct from the doctor's location classes. (b) FR-008: add
  `emit_status_transition` as the authoritative durability write — **but keep the `.md` commit
  hard-error here** (demote deferred to IC-03, D-PLAN-11).
- **Relevant requirements**: FR-008 (add), FR-012; NFR-001/004/005; SC-003, SC-008.
- **Affected surfaces**: new `migration/verdict_provenance_backfill.py`; `status/reducer.py`,
  `status/emit.py`, `status/store.py` (append helper); the provenance-gate surface; `test_reducer.py`
  (WP07 hermetic re-pin + backfill ordering test); `verdict_seam_census.yaml` (backfill-module row).
- **Sequencing/depends-on**: IC-01. **Precedes IC-03 (hard edge to the FIRST IC-03 commit — D-PLAN-15).**
  Red anchors: SC-008 hermetic pin (pre-event `.md`-only rejection still refuses after backfill);
  a reducer ordering test (historical `.md` rejection + later approval → `approved`).
- **Risks**: temporal correctness of `at`; idempotency across re-runs.

### IC-02b — Vocabulary bridge + arch-guard (lands after IC-01; before/with IC-03)

- **Purpose**: One canonical bridge surface beside `status/models.py`, scoped to `{approved, rejected}`
  for `review_result` emission. `arbiter_override` / `approved_after_orchestrator_fix` are **not**
  verdict-bridge inputs to a `review_result` event (D-PLAN-14) — they resolve via `ReviewOverride`
  / orchestrator-fix records; the bridge output feeding an emitted `review_result` is forbidden.
  Enumerate all **9** inline `rejected`↔`changes_requested` sites (`sync/emitter.py`, `status/models.py`,
  `status/reducer.py`, `post_merge/review_artifact_consistency.py`, `review/cycle.py:794`,
  `retrospective/generator.py`, `proof/events.py`, `orchestrator_api/commands.py`,
  `tasks_move_task.py`); mark true-equivalence vs single-value; sweep + the non-vacuous guard land in
  **one WP's `owned_files`** (guard is vacuous until the sweep completes).
- **Relevant requirements**: FR-005.
- **Affected surfaces**: new `status/verdict_vocab.py`; the 9 modules above; a new arch-guard test.
- **Sequencing/depends-on**: IC-01. Adopt-in-place (behaviour-preserving); guard lands last.
- **Risks**: guard-red-with-no-owner if the 9 sites aren't all in the sweep WP.

### IC-03 — Reader collapse: ALL verdict readers die atomically (safety-critical)

- **Purpose**: Repoint **every** verdict reader to `event_sourced_review_result` — approval guard
  `resolve_review_verdict_facts`, the **approval-write probe** (`tasks_verdict_persistence.py:535`,
  D-PLAN-9), merge gate → pure-event (artifact leg retired), dashboard/board, status display,
  fix-mode, **arbiter reader** (`arbiter.py:461`) — **and retire the entire `review/artifacts.py`
  verdict-parser family** (`latest_review_artifact_verdict`, `rejected_review_artifact_for_terminal_lane`,
  `ReviewCycleArtifact.latest`) + delete the two frontmatter readers. **Demote the `.md` commit to
  best-effort HERE** (D-PLAN-11). Extend `test_2093` (derived ratchet); re-point the SC-003/NFR-004
  durability anchors to count **event** records (D-PLAN-13). Reader-row + merge-gate-leg census shrink.
- **Relevant requirements**: FR-002, FR-004, FR-013; FR-003 (parser retirement); FR-006 (reader rows);
  FR-008 (demote); SC-002, SC-003, SC-004.
- **Affected surfaces**: `tasks_verdict_persistence.py`, `tasks_parsing_validation.py`,
  `agent_utils/status.py`, `post_merge/review_artifact_consistency.py`, `review/artifacts.py`
  (parser family), `review/cycle.py` (demote), `workflow*`, `test_2093_authority_invariant.py`,
  `test_review_durability_matrix.py` (re-point), census yaml.
- **Sequencing/depends-on**: **IC-02 (authority populated) + IC-02b (bridge) — hard gate.** The
  reader repoints are ONE atomic WP (splitting reopens the fail-open). Shares census yaml → serial.
- **Risks**: the durability anchor re-point must count events, not `.md` files (renata F1/F2).

### IC-04 — Artifact schema change + census resolver retirements (lands with IC-03's PR)

- **Purpose**: **Remove the `verdict` field** from `ReviewCycleArtifact` (dataclass + `to_dict` +
  `from_dict`/`validate_review_artifact` validation) so the `.md` physically cannot carry a verdict
  (D-PLAN-12) — a schema change, with a **new serialized-artifact assertion** (parse the written `.md`,
  assert no `verdict` key; NOT the census). Retire the 5 census resolver retire rows + 3 unrouted
  sites + 2 raw-join re-homes (name the modules). Reconcile the `cycle.py:70-77` docstring (FR-011)
  and the FR-007 wording (`_review_cycle_wp_dir` is `status: retire` → the fallback is **relocated**
  into the canonical placement resolver, not "verbatim"). **The physical write-partition "flip" is
  largely subsumed** — the commit is already COORD (per-file classifier); `test_analysis_report_rehome`
  is already green. Whether to additionally relocate the physical write (re-pinning that test) is a
  narrow `/tasks` call, not a mission guarantee.
- **Relevant requirements**: FR-003 (SC-007), FR-006 (resolver rows), FR-007, FR-011; SC-001, SC-007.
- **Affected surfaces**: `review/artifacts.py` (schema), `review/cycle.py`, `test_analysis_report_rehome.py`
  (only if a physical move is chosen), `test_review_durability_matrix.py` (field-removal re-pins),
  census yaml. **Also `_guard_feedback_source_provenance` (`cycle.py:380`)** re-expressed without a
  verdict read-back (D-PLAN-5) — name it in the WP.
- **Sequencing/depends-on**: **IC-03 (parser family gone first, else `from_dict` breaks).** Shares
  census yaml → serial after IC-03.
- **Risks**: field removal reds the durability matrix's `.verdict` reads — enumerate those re-pins.

### IC-05 — Arbiter root threading (with IC-03/04 PR)

- **Purpose**: Thread the caller-resolved `main_repo_root` into `persist_arbiter_decision` (retire the
  `feature_dir.parent.parent` self-inference) so an arbiter override under coord topology resolves the
  correct COORD root.
- **Relevant requirements**: FR-016.
- **Affected surfaces**: `review/arbiter.py`, `_run_arbiter_override` (`tasks_move_task.py`).
- **Sequencing/depends-on**: logic-independent; lands same PR as IC-03/04 (serial writer module). Own
  red-first coord-topology test.
- **Risks**: resolved root availability at the call site.

### IC-06a — Gate-artifact WRITE surface de-husk (#2804 + #2404; PARALLEL lane)

- **Purpose**: Single write surface for `acceptance-matrix.json`: `accept` writes COORD, **and suppress
  the PRIMARY husk producer** `mission_finalize._scaffold_acceptance_matrix_if_lane_based:1315` /
  `acceptance/matrix.py::scaffold_acceptance_matrix` under coord topology (D-PLAN-16 / auth F3). A
  write-side check greps **every** `write_acceptance_matrix` call site (not just `accept`). Retire
  `issue-matrix.md`.
- **Relevant requirements**: FR-009 (write surface); SC-005.
- **Affected surfaces**: `merge/executor.py`, `mission_finalize.py`, `acceptance/matrix.py`,
  `acceptance/gates_core.py`, `m_3_2_6_*` migrations.
- **Sequencing/depends-on**: **genuinely parallel — touches no IC-01..05 file, no census yaml.**
  Red anchor: green `test_issue_2804` + the write-side no-PRIMARY-husk check.
- **Risks**: the husk producer runs at finalize time when coord is UNMATERIALIZED (→ PRIMARY).

### IC-06b — Gate-artifact merge DRIVERS (serial with IC-04)

- **Purpose**: Guarantee the row-aware matrix drivers are registered/active before the squash; fix the
  `.md`→`.json` driver seed drift.
- **Relevant requirements**: FR-009 (driver registration).
- **Affected surfaces**: `merge_driver.py` (matrix drivers), `init.py` (`.gitattributes` / `required_entries`),
  `m_3_2_6_*` migrations. **Shares `merge_driver.py`/`init.py` with IC-04's FR-014 review-cycle driver
  relax + `test_merge_reconciliation_class_guard.py` + `verdict_seam_IC04.yaml` +
  `test_review_cycle_merge_driver.py`.**
- **Sequencing/depends-on**: **serial with IC-04** (shared `merge_driver.py`/`init.py`); FR-014's relax
  is semantically gated on IC-03 (the `.md` must be non-authoritative first).
- **Risks**: driver registration on the real merge repo (the pin's bare `git init` harness lacks
  `.gitattributes`).

### FR-014 — Review-cycle merge driver relax (folded into the IC-04/06b PR)

Downgrade the `spec-kitty-review-cycle` fail-closed driver to non-aborting now the `.md` is
non-authoritative; touches `merge_driver.py` + `test_merge_reconciliation_class_guard.py` +
`test_review_cycle_merge_driver.py` + `verdict_seam_IC04.yaml`. Gated on IC-03.

### IC-07 — Canonical `flatten_coordination_metadata` primitive (#3219; operator-added)

- **Purpose**: Extract one `flatten_coordination_metadata(feature_dir)` in `mission_metadata.py`
  doing all three mutations in a single load→mutate→`write_meta(validate=False)` (also closing the
  executor's double-write / mid-flatten-crash window), importing the `topology`/`flattened` key
  constants from `backfill_topology.py`. Converge the three call sites; **correct the
  `mission close --discard` partial-flatten latent bug** (pops `topology`, not just
  `coordination_branch`). Verify the `--push` origin-divergence note (`_phase_push` phase 11 runs
  before cleanup phase 12, so the flatten bookkeeping commit lands local-only on a `--push` merge).
- **Relevant requirements**: FR-015; SC-009.
- **Affected surfaces**: `mission_metadata.py` (new primitive; `clear_coordination_metadata` is the
  1-of-3 today), `merge/executor.py` (`_flatten_coordination_metadata_after_branch_delete`, from
  #3218), `cli/commands/_coordination_doctor.py:816-826`, `cli/commands/mission_type.py`
  (`_flatten_discarded_mission`), `migration/backfill_topology.py` (key owners); a new
  single-source arch-guard + a `mission close --discard` regression.
- **Sequencing/depends-on**: **assumes PR #3218 has landed on the base** (it converges the executor
  site #3218 adds — if #3218 is not yet on `main` at rebase time, this IC waits). **Shares
  `merge/executor.py` with IC-06a** → serialize with (or same lane as) IC-06a; independent of the
  verdict-seam ICs otherwise. Red anchor: the single-source arch-guard (co-occurring three-mutation
  set outside the primitive) + a discarded-coord-mission `CoordinationBranchDeleted` regression.
- **Risks**: this is the 4th touch of the field-set (#2069→#2120→#2614→#3086) — the arch-guard must
  be non-vacuous so a future 5th re-inline reds. Coordination-metadata domain, adjacent to the
  verdict seam — folded for the shared canonical-source-unification pattern, not a verdict dependency.

### Sequencing summary (the critical path)

```
IC-01 (census predicate) ──┬─────────────────────────────────┐
                           ▼                                  ▼
IC-02 (backfill + durability-ADD; .md still hard-error)   IC-02b (vocab bridge + guard)
                           └───────────────┬──────────────────┘
                                           ▼
IC-03 (ALL verdict readers die + .md demote; safety-critical)   ← SC-008 pin gates the first commit
                                           ▼
IC-04 (artifact schema: remove verdict field; resolver retirements) + IC-05 (arbiter) + FR-014/IC-06b
                                           │  (same PR; serial on merge_driver.py/init.py + census)

IC-06a (gate-artifact WRITE surface #2804/#2404) ── parallel, independent lane ──►
```

Hard rule (C-008): IC-01 → IC-02/02b → IC-03 → IC-04 is a serial chain (census-hardened before
collapse; authority populated before readers flip; `.md` demote never precedes the reader flip;
parser family gone before the schema field removal; shared census + `merge_driver.py`/`init.py`).
**IC-06a is the only genuinely parallel lane.**

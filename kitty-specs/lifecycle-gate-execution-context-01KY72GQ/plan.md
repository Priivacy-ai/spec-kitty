# Implementation Plan: Lifecycle Gate Execution Context and Tool-Artifact Ownership

**Branch**: `remediation/coord-lifecycle-gates` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/lifecycle-gate-execution-context-01KY72GQ/spec.md`
**Base**: `upstream/main` `6d9ed490d` (contains PR #2832, #2835, #2818, and sibling #2888)

## Summary

Two seams, delivered strangler-style.

**Seam 1 — Gate Execution Context.** Gates stop inferring their evaluation surface from ambient state and start being handed a `(tree, ref, phase)` triple they cannot derive. A gate whose subject cannot exist in the given surface returns a distinguishable *cannot-evaluate* outcome instead of a verdict. This discharges #1834's live leg (pending negative invariants judged against the pre-consolidation primary tree) and #2885 (the readiness preview handing one directory to a gate that needs two partitions).

**Seam 2 — Tool-Artifact Owner.** The existing `coordination/transaction.py::BookkeepingTransaction` is generalised from *"the owner of writes targeting the coordination branch"* to *"the owner of bytes spec-kitty generates, on any surface"*. It already has the primitives — policy pre-flight, byte-snapshot `write_artifact`, `stage_path`, `commit_idempotent`, surgical `_rollback`. It lacks a non-coord destination, a way to enrol a subprocess's byproducts, and adoption by the merge executor. Once it owns them, every mechanism on the exemption registry (≥11, derived by rule — no count is normative) is retired one at a time, and a ratchet, landed early, prevents a new one.

A key resolver-shape decision underpins both: **resolvers become total, not fallback-based.** Today `_acceptance_matrix_read_dir` returns `coord_read_dir_for(...) or feature_dir`, which conflates *"flat topology, so the primary dir is the correct home"* with *"coord home declared but not materialised, so read primary anyway"*. The first is legitimate; the second is the silent degradation NFR-001 forbids. Making the resolver return the declared home affirmatively for every topology collapses `None` to a single meaning — *declared coord home unresolvable* — which then raises.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest, mypy, ruff; `spec_kitty_events` / `spec_kitty_tracker` (external, public imports only); git via subprocess
**Storage**: Filesystem mission artifacts (JSON / JSONL / Markdown) under `kitty-specs/<mission_slug>/`, with git as the durable store; no database
**Testing**: pytest, ATDD-first (acceptance criteria drive tests outside-in). Parallel local runs use `-n auto --dist loadfile`; daemon/real-port tests run serially at `-n0`. Architectural suite under `tests/architectural/` is the structural safety net.
**Target Platform**: Cross-platform CLI — Linux, macOS, Windows 10+
**Project Type**: single (CLI toolkit + internal runtime packages)
**Performance Goals**: No gate touched by this mission adds >5s to an interactive command (NFR-005). Post-consolidation invariant verification is explicitly non-interactive and exempt.
**Constraints**: mypy strict clean; ruff clean; zero new suppressions; per-function complexity ≤15 (C901 / S3776 aligned); no new filename-based gate exemptions; no new dependence on the `flattened` metadata flag
**Scale/Scope**: **≥26 production modules** (measured — an earlier ≥17 figure counted declaring modules only; the ≥26 count includes the exemption *consumer* modules IC-07 must edit, and is the number to size against) across `acceptance/`, `coordination/`, `merge/`, `mission_runtime/`, `status/`, `cli/commands/`; every registry exemption mechanism retired (≥11, rule-derived); 4 tracker items discharged (#1834, #2885, #2795, #2882)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| **Single canonical authority** | ✅ Directly served | The mission's entire thesis. One owner for generated artifacts, one declared home per artifact kind, one churn classifier (FR-012). |
| **Architectural alignment** | ✅ Pass | Extends the placement seam and `BookkeepingTransaction` established by #2874 rather than opening a parallel mechanism. Explicitly rejects building a third compensator alongside `merge/bookkeeping_projection.py`. |
| **DDD + tiered rigour** | ✅ Pass | Gate Execution Context and Tool-Artifact Owner are core-domain concepts and get full rigour; the exemption retirements are mechanical glue and get proportionate treatment. |
| **ATDD-first** | ✅ Pass | Every FR carries an observable acceptance signal in the spec; tests are written from those signals outside-in. NFR-008 forbids shape-scanning tests. |
| **Terminology adherence** | ✅ Pass | The spec's Domain Language section pins *surface*, *primary*, *merge*, *deferred*. `Mission` canon observed. |
| **Model discipline** | ✅ Pass | Analytical/adversarial/review work routed to the strongest model; mechanical retirements to a mid tier. |
| **Delegate to preserve context** | ✅ Pass | Per-WP implementation dispatched to profile-loaded subagents. |
| **Quality & tech-debt standing orders** | ⚠️ Attention | Campsite-first applies: `merge/executor.py` (1433 LOC) and `coordination/transaction.py` (1345 LOC) are already large. Generalising the latter must not push it past ~1500 LOC — split its acquire/legacy-resolution helpers out first. Tracked as a risk, not a violation. |

**No violations requiring justification.** The Complexity Tracking table below is therefore empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/lifecycle-gate-execution-context-01KY72GQ/
├── plan.md                              # This file
├── spec.md                              # Committed
├── research.md                          # Phase 0 output
├── data-model.md                        # Phase 1 output
├── quickstart.md                        # Phase 1 output
├── contracts/                           # Phase 1 output
│   ├── gate-execution-context.md
│   ├── negative-invariant-provenance.md
│   └── tool-artifact-owner.md
├── checklists/requirements.md           # Committed
├── research/sibling-mission-coordination.md   # Committed
└── tasks.md                             # /spec-kitty.tasks output — NOT created here
```

### Source Code (repository root)

```
src/
├── specify_cli/
│   ├── acceptance/
│   │   ├── matrix.py                 # NI schema + provenance + defer semantics
│   │   ├── gates_core.py             # total read resolver; hand the gate its context
│   │   └── post_consolidation.py     # NEW — Op-dispatched; reads only, no merge/ coupling
│   ├── coordination/
│   │   ├── transaction.py            # generalised into the tool-artifact owner
│   │   ├── commit_router.py          # residue factory + silent-swallow ref advance
│   │   └── coherence.py
│   ├── merge/
│   │   ├── executor.py               # IC-06/IC-07 only — IC-04 has ZERO footprint here
│   │   ├── forecast.py               # #2885 — resolve each partition by kind
│   │   ├── preflight.py              # churn-classifier consumer
│   │   └── bookkeeping_projection.py # duplicate compensator — collapse onto owner
│   ├── cli/commands/
│   │   ├── implement.py              # VCS-lock write site (#2795)
│   │   ├── implement_cores.py        # _drop_vcs_lock_only_meta (exemption 5)
│   │   └── agent/tasks_move_task.py  # exemption 7 (_TransitionGateInputs :1172, dirty_before :1182 post-#2888)
│   ├── status/__init__.py            # COORD_OWNED_STATUS_FILES (exemption 3/4)
│   ├── bulk_edit/diff_check.py       # RUNTIME_STATE_ALLOWLIST (exemption 8)
│   └── git/ref_advance.py            # dirty-entry scan; owner-aware
├── mission_runtime/
│   └── artifacts.py                  # is_self_bookkeeping_path (exemption 1/2)
└── specify_cli/post_merge/
    └── review_artifact_consistency.py # #2885 partition split (+ silent-degradation branch)

tests/
├── acceptance/          # NI provenance, deferral, post-consolidation verification
├── integration/         # coord + flat topology fixtures, preview-vs-merge agreement
├── regression/          # #1834, #2885, #2795 red-first repros
├── architectural/       # anti-ninth-exemption ratchet; total-resolver invariant
└── merge/               # preflight + churn classifier
```

**Structure Decision**: Single-project CLI layout, unchanged. The one new module is
`src/specify_cli/acceptance/post_consolidation.py`, created so that the WP delivering
post-consolidation verification and the WP retiring `merge/`-package exemptions own disjoint
files (decision `01KY7AKXNJZCB2J2W411YM3B9F`). No new package boundary is introduced;
the shared-package boundary rules are untouched.

## Complexity Tracking

*No Charter Check violations. Table intentionally empty.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these
> into executable WPs — one concern may become several WPs, and small concerns may merge.

### IC-01 — Claim-time merge blocker, established by live reproduction

- **Purpose**: Reproduce the real mechanism that blocks merge after a claim, because the reported one (dirty coord `meta.json`) is refuted — the VCS-lock write targets the PRIMARY-partition dir via `placement_seam(...).read_dir(SPEC)`.
- **Relevant requirements**: FR-011, C-002
- **Affected surfaces**: `cli/commands/implement.py`, `cli/commands/implement_cores.py`, `merge/preflight.py`, `git/ref_advance.py`
- **Also captures the NFR-005 baseline** (`spec-kitty accept --diagnose` timing on the coord and flat fixtures) as its very first action, before any WP mutates the tree — nobody else can, since every later WP has already changed the surface.
- **Sequencing/depends-on**: none — **must be first**. Under coord topology this mission cannot merge itself until this is understood and fixed.
- **Risks**: The repro may show the blocker is on the primary checkout, not coord, which changes the fix. Timeboxed: if no repro, the concern converts to a documented finding and the fix is descoped. **The C-002 fallback is then explicit**: the mission cannot rely on a claim-time fix it could not reproduce, so it either (a) pins `auto_commit=True` for its own run — the path on which the reported blocker is a no-op — or (b) flattens its own topology for closeout. One of the two is chosen and recorded at that point; the mission does not proceed on coord topology against an unexplained blocker.

### IC-11 — Surface→filesystem translation seam (consolidating, not additive)

- **Purpose**: Build the ONE total `TopologySurface` → path translation, consuming the **existing**
  `probe_coord_state` / `CoordState` classifier (`missions/_read_path_resolver.py:256`) rather than
  writing a new one beside it. Declare `LANE` / `CONSOLIDATED` / `TEMP` **with** the seam, so no
  member exists that a caller cannot resolve. The operator's resolvability test — every member
  resolves to a real location — is its acceptance signal.
- **Relevant requirements**: FR-001, NFR-001, NFR-003, C-004; unblocks C6's `CONSOLIDATED`
- **Affected surfaces**: `mission_runtime/artifacts.py`, `mission_runtime/resolution.py`,
  `missions/_read_path_resolver.py`, plus every translator on the acceptance / merge / preview
  routes (`acceptance/gates_core.py::_acceptance_matrix_read_dir`, `cli/commands/accept.py::_coord_worktree_root`,
  `post_merge/review_artifact_consistency.py::_resolve_review_cycle_read_dir`, `merge/forecast.py::feature_dir_for_preview`)
- **Sequencing/depends-on**: none — this is the true schema root, ahead of IC-02
- **Risks**: **This is the concern most likely to fail by becoming additive.** ~12 translators exist;
  a seam that adds a thirteenth while twelve survive has made the problem worse, because the next
  contributor gains a precedent rather than losing one. **Decided 2026-07-23: build it and repoint
  or demolish every translator it touches in the same pass**, registering any survivor in the
  ratchet registry so it is visible and shrinking. Prior art for the failure mode:
  `_resolve_review_cycle_read_dir` was itself added by a consolidation-shaped fix (#2646/#2275) and
  directly produced #2885.

### IC-02 — Gate Execution Context

- **Purpose**: Introduce the `(tree, ref, phase)` value a gate is handed and cannot derive, plus the *cannot-evaluate* outcome, and make the resolvers it consumes total rather than fallback-based.
- **Relevant requirements**: FR-001, NFR-001, NFR-003, C-004
- **Affected surfaces**: `acceptance/gates_core.py`, `mission_runtime/artifacts.py` (resolver totality only)
- **Sequencing/depends-on**: IC-11 (the translation seam). IC-02 is the *gate-context* root for IC-03/04/05, built on IC-11's resolved-surface seam — IC-11 is the single true schema root (see Sequencing Constraints).
- **Risks**: Must not be named or shaped around coordination topology (C-004), or the flat case stays broken. Must not add new dependence on `flattened`; the resolver returns each topology's declared home affirmatively.

### IC-03 — Negative-invariant provenance and defer semantics

- **Purpose**: Every recorded judgement states the surface and ref it was established against; a pending invariant that cannot hold in the current surface records `deferred_to_consolidation` with a reason instead of a false `still_present`.
- **Relevant requirements**: FR-002, FR-003, **FR-010** (absorbed from IC-09), **FR-014** (the provenance schema AND its one-time backfill migration), NFR-003
- **Affected surfaces**: `acceptance/matrix.py`, `acceptance/gates_core.py`, and a one-time migration under `cli/commands/migrate/` (or the established migration surface) that walks existing on-disk matrices and writes `provenance_origin: legacy_unrecorded` for the 40 pre-schema results. **The migration's own 153-file write is enrolled in the tool-artifact owner** (it is a toolchain-generated write like any other; the mission's thesis forbids it being an exception) — which sequences this part of IC-03 after IC-06, or, if the migration must precede the owner, it runs under an explicit one-off transaction with the same commit-or-revert guarantee. **Oracle**: a migration test over a fixture matrix corpus asserting every non-`pending` result ends with a valid `provenance_origin`, and that `validate_matrix_evidence` passes on the migrated corpus (currently 153 matrices, 40 non-`pending`, 0 with provenance).
- **Sequencing/depends-on**: IC-02
- **Risks**: `pending` is the scaffolded default, so this path is the common one, not the edge. Schema additions must round-trip through `to_dict`/`from_dict` and be enforced by `validate_matrix_evidence`.

### IC-04 — Post-consolidation verification seam

- **Purpose**: Judge `deferred_to_consolidation` invariants against the consolidated mission tree and write the outcome back with `verified_surface_kind: CONSOLIDATED`; a genuine violation fails **its Op**, not the consolidation.
- **Relevant requirements**: FR-004, FR-005
- **Affected surfaces**: `acceptance/post_consolidation.py` (new) — **and nothing else**. **Decided 2026-07-23: zero `merge/` footprint.** No new CLI verb and no call-in from `merge/executor.py`. The verification is dispatched as an ordinary governed Op through the canonical surface (`spec-kitty dispatch`, closed with `profile-invocation complete`); it reads the consolidated tree and the matrix and writes back outcomes. Because enforcement is an external CI check (FR-016), consolidation does not need to know the Op exists. This supersedes the earlier "narrow call-in from `merge/executor.py`" shape recorded in decision `DM-01KY7AKXNJZCB2J2W411YM3B9F` and in `tracers/design-decisions.md` — both are historical logs and are left unedited. **Consequence:** IC-04's `owned_files` are now genuinely disjoint from IC-06's and IC-07's `merge/`-package work, which is what makes lane-B parallelism real rather than asserted.
- **Sequencing/depends-on**: IC-03 (schema)
- **Risks**: Because the Op runs after consolidation, it does NOT add an abort path inside the consolidation transaction and does NOT interact with the rollback machinery IC-06 is collapsing — that decoupling is deliberate and must be preserved. **The enforcer question is CLOSED (operator, 2026-07-23): enforcement is external, not a loop guardrail.** A CI consistency check at the front of the quality run fails any PR carrying a dangling `deferred_to_consolidation` invariant (FR-016), and the deferral is disclosed to the operator at assignment time so downstream repos know they need their own gate (FR-017). The earlier recommendation — blocking on a non-terminal matrix verdict — was withdrawn as unimplementable: the matrix has exactly one reader and it runs pre-consolidation.

### IC-05 — Two-partition preview gate

- **Purpose**: The readiness preview resolves lane-state and review-cycle from their own declared homes rather than trusting one caller-supplied directory, so preview and real merge agree.
- **Relevant requirements**: FR-006, SC-002
- **Affected surfaces**: `merge/forecast.py`, `post_merge/review_artifact_consistency.py`
- **Sequencing/depends-on**: IC-02
- **Risks**: Harvest the two coord integration tests from PR #2834 **with attribution to @rayjohnson** (C-007) rather than rewriting them.

### IC-12 — Campsite: split `transaction.py` before the owner opens it

- **Purpose**: Behaviour-free extraction, so the owner generalisation lands in a module that has
  room for it. Measured clusters, all pure or import-only: confined-atomic-write (~170 LOC),
  legacy-mission resolution (~189, folding 3 redundant `load_meta` reads on the same path into 1),
  the error hierarchy (~67), and a dead `threading.local()` sentinel with zero repo-wide
  references (~5). Net **1345 → ~914 LOC**.
- **Relevant requirements**: NFR-007; owner contract C10
- **Affected surfaces**: `coordination/transaction.py` (+ new sibling modules)
- **Sequencing/depends-on**: none — **must precede IC-06**
- **Risks**: Low by construction — no behaviour change, and `tests/specify_cli/coordination/test_transaction.py`
  (1046 LOC) is an existing oracle covering acquire/rollback/lock. Keep it a separate work package
  from IC-06: a behaviour-free refactor inside a behaviour-changing diff is unreviewable. Do **not**
  opportunistically remove the 6 `flattened` references here (separate track, R-005).

### IC-06 — Tool-artifact owner

- **Purpose**: Generalise `BookkeepingTransaction` to any surface, add subprocess-byproduct enrolment, and adopt it in the merge executor — collapsing the duplicate compensator in `merge/bookkeeping_projection.py`.
- **Relevant requirements**: FR-007, FR-008, NFR-002
- **Affected surfaces**: `coordination/transaction.py`, `merge/bookkeeping_projection.py`, `merge/executor.py`, `coordination/coherence.py`
- **Sequencing/depends-on**: IC-01 (its findings inform what must be enrolled)
- **Risks**: Highest-LOC surface in the mission. Campsite-first: split `transaction.py`'s acquire/legacy-resolution helpers out before growing it. Do not open `merge/executor.py` until the owner has a non-coord destination, or the mission maintains three compensators instead of two.

### IC-07 — Exemption retirement (strangler; six forced work packages)

- **Purpose**: Retire **every row on the enumerated registry** (IC-08) — the ≥11 mechanisms R-012/R-014 found, not the original eight — migrating each one's behaviour to the
  owner. Behaviour an exemption got right must be preserved (C-010) — a retirement that
  reintroduces a false block is a regression.
- **Relevant requirements**: FR-009, FR-012, NFR-006, C-010
- **Slicing is FORCED by shared consumers, not chosen** (decided 2026-07-23). Six work packages:

  | WP | Group | Why it cannot be split further |
  |----|-------|-------------------------------|
  | a | `is_self_bookkeeping_path` | shares 3 consumer files with (b) — sequential, same lane |
  | b | `is_coordination_artifact_residue_path` | 7 consumers incl. `lanes/auto_rebase.py`, which aborts a rebase on unrecognised dirt |
  | c | `COORD_OWNED_STATUS_FILES` + `advance_branch_ref` param + coord-staging skip | ONE mechanism, 8 consumer sites; retiring one consumer leaves the set alive |
  | d | `_drop_vcs_lock_only_meta` + `_drop_runtime_frontmatter_only_wp` (+ `_exclude_coord_owned`) | applied on the same two call lines; **deduplicate into one `_drop_if(paths, predicate)`**, do not retire sequentially |
  | e | `RUNTIME_STATE_ALLOWLIST` / `_runtime_state_exemption` | single file, fully isolated |
  | f | `new_checkout_paths` | single file; sibling-gate CLEARED (#2888 published) |
  | g | the four R-014 additions — `ACCEPT_OWNED_PATHS` (`acceptance/__init__.py`), the `dirty_classifier` bundle, `_exclude_coord_owned`, and the dead `ignores_primary_coord_residue` field | discovered after the original eight-symbol slice; `ACCEPT_OWNED_PATHS` is in `acceptance/`, which IC-03 already opens |

  **Group (g) — the mechanisms the registry found but the original slice missed.** R-012/R-014
  raised the census from 8 to ≥11; the six-group slice above covers the original eight symbols
  only. Group (g) closes the gap so no registry row is orphaned: `ACCEPT_OWNED_PATHS` (the
  research's "most on-thesis instance — the accept gate ignoring the accept pipeline's own
  writes") and `_exclude_coord_owned` retire against the owner like any other; the
  `dirty_classifier` bundle retires with the review-handoff path; `ignores_primary_coord_residue`
  is dead (zero external consumers) and is simply deleted. **Nothing is declared a permanent
  survivor** — the registry (IC-08) reaches zero rows, which is what TAO-4 and SC-004 require. If
  implementation finds a genuine must-keep, it becomes an explicit, justified registry row, never
  a silent survivor.

  (a) and (b) were one group until measurement showed 9 files — not one-pass reviewable — so they
  split into two sequential WPs sharing a lane.

- **Affected surfaces — DECLARING modules**: `mission_runtime/artifacts.py`, `status/__init__.py`,
  `cli/commands/implement_cores.py`, `bulk_edit/diff_check.py`, `cli/commands/agent/tasks_move_task.py`
- **Affected surfaces — CONSUMER modules (corrected 2026-07-23; previously omitted, causing a ~2× under-size)**:
  `merge/git_probes.py`, `review/dirty_classifier.py`, `cli/commands/agent/mission_record_analysis.py`,
  `acceptance/__init__.py`, `merge/ordering.py`, `lanes/merge.py`, `coordination/coherence.py`,
  `coordination/commit_router.py`, `cli/commands/implement.py`, `lanes/auto_rebase.py`, `git/ref_advance.py`
- **Sequencing/depends-on**: IC-06 (owner) and IC-08 (registry, landing early so each WP has a
  pre-existing red to turn green). WP (f) was sibling-gated; the sibling **published (#2888)** and the branch is rebased, so it is now unblocked — re-confirm `_TransitionGateInputs` line numbers at implement time.
- **Risks**: `merge/ordering.py` and `lanes/merge.py` are **`merge/`-package** files inside group (c),
  which cannot be split — so the "`merge/`-package retirements last" rule is unsatisfiable for that
  group as literally written and must be read as "group (c) is scheduled late", not "split it".

### IC-08 — Exemption registry + anti-ninth ratchet (lands EARLY)

- **Purpose**: A negative structural scan over the derivation rule from R-014 — *every frozenset,
  tuple, or compiled regex of filenames, basenames, suffixes, or path prefixes consulted by a
  dirty-state or churn-classification predicate* — asserting that no such mechanism exists outside
  an explicit registry, and that the registry only ever shrinks.
- **Relevant requirements**: FR-013, NFR-006, NFR-008 (as amended)
- **Affected surfaces**: `tests/architectural/` (new file — register with the shard map, C-006)
- **Sequencing/depends-on**: **IC-06 only.** Lands immediately after the owner and **before the
  first retirement** — reversing the original "ratchet last" ordering.
- **Mode**: **enumerated registry rows, NOT a golden count.** The registry is pre-populated with
  every known mechanism, initially expected-present; each retirement work package deletes its own
  one-line row. Golden-count mode was explicitly rejected: it reinstates the hand-derived oracle
  R-012 repudiated, makes all six retirement WPs co-own one file, and collides with the
  golden-count ban gate.
- **Why early (the mission's primary risk countermeasure)**: this plan is back-loaded and largely
  serial. The named failure mode is not producing something wrong but producing two thirds of
  something right and stopping — which, under "ratchet last", leaves the owner PLUS the surviving
  exemptions PLUS the ones nobody counted: one more compensating mechanism than we started with,
  arrived at by executing the plan faithfully. Landing the ratchet second closes the door from
  week one, gives the registry an oracle so the census stops being hand-derived, and gives every
  retirement WP a pre-existing red to turn green (red-first discipline, which the original
  ordering denied them). A stall at any point then leaves the codebase strictly better than it
  was found.
- **Risks**: This is deliberately a *structural* test, which NFR-008 forbids by default — the NFR
  is amended to permit negative, registry-backed structural invariants for properties that are
  inherently structural. Keep it negative (absence outside the registry); never a positive literal
  count.

### IC-10 — External enforcement, disclosure, and documentation of the deferral contract

- **Purpose**: Update the operator-facing guides so the post-consolidation contract is
  discoverable before an operator meets it. Primary target: `docs/guides/accept-and-merge.md`
  (the guide that currently describes acceptance and merge without any notion of deferral).
- **Relevant requirements**: FR-016 (the CI consistency check), FR-017 (assignment-time disclosure), FR-018 (guides)
- **Affected surfaces**: the CI quality-run configuration (a consistency check at the front of the run that fails any PR carrying a dangling `deferred_to_consolidation` element — FR-016); the status-assignment code path that must emit the disclosure when it writes `deferred_to_consolidation` (FR-017); `docs/guides/accept-and-merge.md`; cross-links from
  `docs/context/orchestration.md` (post-consolidation / `CONSOLIDATED` are already governed
  there); the generated docs indexes must be refreshed (`scripts/docs/freshen_adr_inventory.py`
  then `scripts/docs/docs_index.py --write`, both needing `PYTHONPATH=.` — see #2887).
- **Sequencing/depends-on**: IC-03 (the schema must be settled before it is documented)
- **Risks**: Docs written ahead of behaviour go stale silently. Write this AFTER the deferral
  semantics land, not alongside. Run `tests/architectural/test_no_legacy_terminology.py` and
  `check_docs_freshness --ci` before considering it done — both are CI-only gates that pass a
  local doctrine run.

### IC-09 — FOLDED INTO IC-03 (2026-07-23)

Retained as a heading so the numbering stays stable across artifacts and audits.

The acceptance-matrix write-side single home (FR-010 / #2882) is **not a separate concern**. It
owns `acceptance/matrix.py` — the same file as IC-03 — and the plan's own risk note already
argued the case: *"if these land far apart, the two copies diverge on the new fields in the
interval."* That is an argument for co-landing, not for a dependency edge. Two independent audits
reached the same conclusion.

Its requirement, surfaces (`acceptance/matrix.py`, the `finalize-tasks` scaffolder) and risk are
absorbed by IC-03, which now discharges FR-002, FR-003 **and** FR-010.

## File Ownership (B4 — resolved 2026-07-23)

`/spec-kitty.tasks` derives `owned_files` from concern surfaces and cannot resolve overlaps
itself. Eight files are legitimately touched by more than one concern. Resolution: **no two
concurrent work packages share a file**; every overlap below is *sequential within one lane*, and
carries rationale-backed leeway rather than an artificial file split.

| File | Concerns | Resolution |
|---|---|---|
| `cli/commands/implement.py` | IC-01, IC-07 (a/c/d) | Sequential, lane A. IC-01 first — and if its fix commits the VCS lock rather than dropping it, it has pre-empted part of IC-07(d); re-check before slicing that WP. |
| `cli/commands/implement_cores.py` | IC-01, IC-07 (a/c/d) | Sequential, lane A. IC-07(d) deduplicates all three `_drop_*` siblings in one pass. |
| `coordination/transaction.py` | IC-12, IC-06 | Sequential by construction — campsite extraction, then generalisation. Never concurrent. |
| `coordination/commit_router.py` | IC-07 (a/c) | Sequential within IC-07. |
| `coordination/coherence.py` | IC-06, IC-07(c) | Sequential, lane A. |
| `mission_runtime/artifacts.py` | IC-11, IC-07(a) | Sequential — the seam lands first, the exemption retires against it. |
| `git/ref_advance.py` | IC-01, IC-07(c) | Sequential. IC-01's repro lives here (the cross-gate `meta.json` disagreement). |
| `merge/executor.py` | IC-06, IC-07(c) | Sequential, lane A. **IC-04 no longer appears here** — its zero-`merge/`-footprint decision is what removed the three-way claim. |

**Genuinely parallel** (file-disjoint from the main chain): IC-08 (tests only), IC-07(e)
(`bulk_edit/diff_check.py`), IC-07(f) (`tasks_move_task.py`, sibling-gated), and IC-05 —
*conditional on one check*: whether its fix changes the signature of
`run_review_artifact_consistency_preflight`, which would pull in `merge/preflight.py` and collide
with IC-01. **Verify that before assuming lane B exists.**

Honest note on parallelism: the file graph is one large connected component. Lane A carries most
of the work and every long-pole file, because the exemption consumers are the same modules the
owner and the claim-blocker fix open. Assume roughly serial until the IC-05 check resolves.

### IC-13 — Mission archiving

- **Purpose**: A first-class lifecycle operation that archives a terminal mission as an immutable,
  explicitly-legacy snapshot excluded from live validation but kept enumerable (FR-015 / US6). It
  is orthogonal to both seams — it shares no surface with IC-01..IC-12.
- **Relevant requirements**: FR-015
- **Affected surfaces**: a new archive command/verb and its `ArchivedMission` record; the
  validation path that must exclude archived missions from live checks while keeping them
  enumerable (e.g. `doctor`). The `AM-1..AM-4` invariants and the C10 clause in
  `contracts/negative-invariant-provenance.md` are its acceptance signal.
- **Sequencing/depends-on**: none functionally, but **must not** be reachable from the FR-014
  migration's failure path (AM-4). Can land last, or be cut — it is the one concern with no
  dependency into the mission's critical path (see the split-fallback note below).
- **Risks**: An ungoverned archive is a one-command escape from any acceptance failure; the four
  `AM` invariants exist precisely to prevent that. If mission scope must shrink, this is the first
  concern to cut — it is orthogonal and P3.

## Sequencing Constraints (binding)

1. **IC-01 first.** Coord topology + an unfixed claim-time merge blocker means the mission cannot merge itself otherwise (C-002).
2. **IC-11 before IC-02 before IC-03/04/05.** IC-11 (the translation seam) is the true schema root; IC-02 (gate execution context) builds on it. Everything downstream reads the resolved surface IC-11 provides. (The Technical Context's older "IC-02 = schema root" phrasing is superseded by this.)
3. **IC-12 before IC-06 before IC-08 before IC-07.** The campsite split precedes the owner; Retiring an exemption before an owner exists leaves the
   behaviour homeless; retiring one before the *registry* exists means the class stays open to new
   additions for the whole mission. Ratchet second is the stop-line safety net (operator decision,
   2026-07-23: keep this as ONE mission, with ratchet-first as the countermeasure to the
   stall-mid-strangler failure mode).
4. **Merge-surface work is rebased onto `8074107d7` or later.** C-001 is DISCHARGED — #2832/#2835 are merged and the branch is rebased. Re-fetch before starting any `merge/`-package WP regardless, since upstream moves.
5. **Exemption 7 is unblocked** — sibling published (#2888), branch rebased onto `6d9ed490d`. See `research/sibling-mission-coordination.md` for the completed re-diff. `review/pre_review_gate.py` remains out of scope entirely.
6. **This mission's own negative invariants** are recorded non-`pending` from the lane surface during per-WP review, so the already-landed preserve guard (`b918e66df`) protects them — the mission self-hosts on the half of #1834 that already shipped, and on its own fix from IC-03 onward.

## Fallback Split — pre-agreed contingency (IC-05 / IC-06 fault line)

**Default is ONE mission.** This section is the escape hatch, agreed in calm (operator, 2026-07-23)
so it is a decision rather than a mid-mission scramble.

**Trigger**: if IC-07(f)'s sibling-mission dependency, or the C-001 ↔ IC-07(c) `merge/`-package
tension, causes real delay to the retirement half.

**The cut** (confirmed a clean cut by architecture review — no half-1 concern depends on a half-2
concern; half 1 is dependency-closed and self-consolidates via IC-01):

- **Ship half 1** — Seam 1: IC-01, IC-11, IC-02, IC-03, IC-04, IC-05, IC-10. This lands the gate
  execution context, the translation seam, and the three live defects (#1834, #2885, #2882) plus
  the schema, migration, and deferral contract.
- **Defer half 2 to a follow-on** — Seam 2: IC-12, IC-06, IC-08, IC-07 (owner + campsite +
  ratchet + retirements), and IC-13 (archiving). Every half-2 dependency is satisfied by landed
  half-1 work, so the follow-on rebases cleanly.

**Ratchet-first survives the cut**: IC-08 depends on IC-06, both in half 2, so the ratchet-first
ordering is simply re-instantiated inside the follow-on, unchanged.

**Accepted cost of taking the split** (so it is chosen with eyes open, not defaulted into):
1. Half 1 lands the new translation seam (IC-11) **without the ratchet backstop** (IC-08, half 2),
   so a surviving/13th translator would not be flagged until the follow-on — IC-11's own
   most-likely failure mode.
2. The exemption class stays **open** in the interval — a contributor can add another exemption
   until the follow-on ships US5/FR-013/C9.
3. US3 is only half-discharged: IC-01's specific claim-blocker fix lands; the general owner-fix
   (IC-06, "any toolchain write committed or reverted") waits. Not broken — the exemption status
   quo covers it — but not closed.

**If scope must shrink without a full split**: IC-13 (archiving) is the first concern to cut — it
is orthogonal to both seams, P3, and has no dependency into the critical path.

## Baseline health (VERIFIED — an earlier claim in this file was FALSE)

**There are no known baseline reds.** On base `8074107d7`,
`tests/architectural/test_no_dead_symbols.py` (24 passed) and the `golden_count_ban` selection
(9 passed) are **green** — verified by running them. #2825 was fixed upstream; the base commit is
literally *"landing fold: annotate cardinality site to satisfy golden-count ban"*.

Two earlier revisions of this plan told implementers both were red and not to attribute failures
to their diff. That was carried from the original brief and never verified, and the first
correction missed this second copy — the same fold-at-the-point-of-the-finding failure the audits
named, committed while fixing it.

**Standing rule for this mission:** if an architectural test goes red, it is yours until proven
otherwise **on the current base**. Do not treat any test as pre-broken without re-running it on
`upstream/main` first. A stale known-reds list is a licence to green-wash a real regression.

# Implementation Plan: Worktree-Aware Root Resolution & Verdict Parity

**Branch**: `fix/worktree-root-resolution` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/worktree-root-resolution-01M0B59R/spec.md`
**Mission ID**: `01M0B59R1GMN6N33GSGJFVNBP9` · **Base**: `upstream/main` (re-verify tip at implement time; squad ran `30cffb08b3`) · **Topology**: coord

## Summary

Fix the confirmed members of the **write-path invoking-location** defect class (`docs/plans/investigations/write-path-topology-root-cause.md`, spike #3129) so that a command invoked from a foreign lane worktree fails closed (refuses, naming the target checkout) instead of silently acting on the primary — and closes the false-green guards and the review-verdict CLI-parity gaps that ride the same seam.

**Technical approach**: Introduce one shared **checkout-identity guard** (invocation owns the target checkout vs a foreign lane worktree), carrying **read/write intent** so deliberate primary reads are not flipped. In-scope writing commands consult it and adopt the **#3128 fail-closed refusal** (the accepted remediation for this class) — the message names the checkout it would otherwise have acted on. Fix the two false-green guards (`setup-plan` branch match reads primary HEAD; `backfill` cutover verifies the same redirected path it wrote). Preserve the deliberate primary anchors (#2320 status-home, #3328 primary-reads) behind a documented **must-not-flip inventory** with green characterization tests. On the verdict side, hoist `_parse_review_result_json` (→ `status`) and the `for_review` gate (→ a `lanes`-side leaf with a **surface-neutral error contract**) so both `agent status emit` and `orchestrator-api transition` share one topology-aware invariant, and add `--review-result-json` to `emit`. Finish the audit residuals with a **new `status_event_row`-scoped** registration test (the existing drift test is `meta.json`-scoped), a **value-equality** round-trip property with a non-vacuous generator, and the coordination-key writer as a separately-sized WP.

**Reframe note (post-plan adversarial squad, 2026-08-18)**: an empirical resolver run refuted the brief's "standalone clone re-anchored to primary" framing — clones already resolve to self; the clone/primary split is undecidable and moot (spec C-005). The decidable defect is the linked-worktree/nested-clone **invoking location**. The worktree→primary re-anchor is often **deliberate** (#2320/#3328) and must be preserved. `#3449 --owned-checkout` is dropped as already-correct (recommend wontfix). The `review_result` projection (`407ea376c4`) and repair preservation (`bec7c25273`) are verified already-fixed (C-001/C-002) — built upon, not re-opened; each gets a green sentinel (NFR-004).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml (existing); `spec_kitty_events` / `spec_kitty_tracker` public imports only (no vendored copies); no new third-party dependency is introduced by this mission.
**Storage**: filesystem — git checkouts/worktrees, `.kittify/` state, append-only `status.events.jsonl` event log, `meta.json` mission identity. No database.
**Testing**: pytest (`-n auto --dist loadfile` parallel; real-port/daemon tests serial with `-n0`); `@pytest.mark.regression` for issue-pinned red-first reproductions, authored-and-shown-failing on base; `tests/architectural/` gates (terminology + shared-package + NFR-003 single-channel refusal).
**Target Platform**: Linux/macOS developer CLI (Spec Kitty CLI); no runtime service.
**Project Type**: single project (Python CLI package under `src/specify_cli/` + `src/doctrine/` + `src/runtime/`).
**Performance Goals**: No regression to CLI command latency; the identity guard adds only bounded filesystem stat/`.git` reads already performed today (no new process spawns on the hot path).
**Constraints**: New/changed code passes `ruff` + `mypy` with zero issues/warnings; complexity ≤15 (C901/S3776); no new blanket suppressions; canonical terminology (`Mission`, not `feature`); no direct pushes to origin/main; base `upstream/main` (re-verify tip at implement time).
**Scale/Scope**: 6 confirmed write-path commands + 4 verdict/audit surfaces; 18 FRs; the change is one new identity guard + two hoisted verdict units + targeted per-command adoption/guard fixes. The `get_main_repo_root` primitive (~130 callers) is deliberately NOT globally flipped.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present at `.kittify/charter/charter.md`. Governing-principle gates:

| Charter principle | Compliance in this plan |
|-------------------|--------------------------|
| **Single canonical authority** | One checkout-identity guard owns the invocation-ownership decision; one shared `_parse_review_result_json` + one `for_review` gate own verdict validation. Refusals single-channel through the guard (NFR-003 architectural test). No parallel/duplicate resolvers. |
| **Architectural alignment** | Verified: the shared-package boundary forbids only retired external imports — the verdict-seam hoist is intra-`specify_cli` and does not touch it. Parser → `status`; gate → a `lanes`-side leaf (avoids tightening the existing `status`↔`lanes` deferred-import cycle) with a surface-neutral error contract. |
| **DDD + tiered rigour** | The invoking-location seam is bounded by the identity guard (a small unit with read/write intent). Commands depend on the guard, not raw `.git` walking. Deliberate primary anchors (#2320/#3328) are an explicit must-not-flip inventory, not incidental behavior. |
| **ATDD-first** | Each invariant (SC-001…SC-006) is driven outside-in; red-first per release-blocking slice, **authored and shown failing on base** (NFR-001) — refusal/absence-of-false-green for the fail-closed slices; green sentinels for already-fixed code (NFR-004). |
| **Terminology adherence** | `Mission`/`primary`/`worktree` per glossary; `primary` sense disambiguated (repository-root checkout vs Primary Branch); no clone-vs-primary behavioral vocabulary (C-005). Run `tests/architectural/test_no_legacy_terminology.py` pre-push. |
| **Locality of change + smallest viable diff** | The identity guard is additive; call sites adopt it one command at a time. Read-seam consolidation (#3043/#3065/#3462) is explicitly fenced (C-008) — the guard MUST NOT tidy read paths. Campsite folds (#3323, #3548) only when already editing that file. |

**No unjustified violations.** Complexity Tracking is empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/worktree-root-resolution-01M0B59R/
- plan.md              # This file
- research.md          # Phase 0 — code-grounded decisions + squad reframe grounding
- data-model.md        # Phase 1 — CheckoutIdentity, ForReviewGate, ReviewResult entities + invariants
- quickstart.md        # Phase 1 — red-first repro per invariant (authored tests, not -k globs)
- contracts/           # Phase 1 — resolver-identity + verdict-CLI + audit contracts
- tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
- core/
  - paths.py                     # find_repo_root nested-clone boundary align w/ resolve_canonical_root (FR-007);
                                 #   HOME of get_main_repo_root primitive (~130 callers) — NOT globally flipped
  - checkout_identity.py         # NEW: checkout-identity guard (owns-vs-foreign) + read/write intent (FR-001)
  - mission_creation.py          # is_worktree_context prior art (used at :483) — reused, not moved
- task_utils/support.py          # find_repo_root wrapper (FR-007)
- cli/commands/
  - agent/status.py              # emit: add --review-result-json, fix --help (FR-010,012,013)
  - agent/mission_setup_plan.py  # branch_matches_target from invoking checkout, not primary HEAD (FR-006)
  - intake.py                    # fail-closed identity check before shared-slot write (FR-002)
  - _command_surface_doctor.py   # tool-surfaces --fix: fail-closed refusal from a lane (FR-003)
  - _mission_state_doctor.py     # mission-state: preserve #2320 + identity awareness + manifest honesty (FR-004,009)
- migration/
  - backfill_runtime_state.py    # cutover guard invoking-checkout-aware (FR-005)
  - runtime_state_cutover.py     # verify_backfill false-green fix (FR-005)
  - mission_state.py             # _build_canonical_row preserved (C-002); manifest honesty (FR-009)
  - review/cycle.py              # write-side kind-flip (FR-017)
- orchestrator_api/commands.py   # _parse_review_result_json (-> hoist to status), _enforce_for_review_commit_gate
                                 #   (-> hoist to lanes-side leaf, surface-neutral) (FR-010,011,013)
- status/
  - reducer.py                   # projection ALREADY fixed (C-001) — untouched; green sentinel added (NFR-004)
  - review_result_parse.py       # NEW home for hoisted _parse_review_result_json (co-located w/ ReviewResult)
  - audit/shape_registry.py      # register review_result in status_event_row + coordination-key (FR-014,016,018)
- lanes/for_review_gate.py       # NEW leaf: hoisted topology-aware gate, surface-neutral (FR-011)
- cli/commands/agent/tasks_verdict_persistence.py  # resolve_review_verdict_facts migrate (FR-017)

# Deliberate primary-read anchors — MUST-NOT-FLIP inventory (FR-008, characterization tests only):
#   core/paths.py: get_feature_target_branch, resolve_merge_target_branch
#   mission_runtime/resolution.py closures; merge/*; coordination/write_seam.py

tests/
- architectural/                 # terminology + shared-package + NFR-003 single-channel refusal gate
- <must-not-flip characterization>  # pin #2320/#3328 GREEN (FR-008, SC-003)
- <green sentinels>              # pin 407ea376c4 / bec7c25273 GREEN (NFR-004)
- <issue-pinned regressions>     # @pytest.mark.regression, authored-red-on-base (NFR-001)
```

**Structure Decision**: Single-project Python CLI. Net-new units: `core/checkout_identity.py` (identity guard), `status/review_result_parse.py` (hoisted parser), `lanes/for_review_gate.py` (hoisted gate). Everything else is a call-site adoption plus targeted guard fixes. The `get_main_repo_root` primitive (~130 callers) is NOT globally flipped — only named commands adopt the identity guard; the must-not-flip inventory is preserved with characterization tests (FR-008).

## Parallel Work Analysis

### Dependency Graph

```
WP-A  checkout-identity guard (owns-vs-foreign, read/write intent) + unit tests
      + must-not-flip characterization tests pinning #2320/#3328 GREEN (FR-001, FR-008, SC-003)
   |
   +-- Wave 1 — fail-closed adopters (red-on-base = refusal / absence-of-false-green), depend on WP-A:
   |     WP-B  intake fail-closed identity check (#3540, FR-002)
   |     WP-C  doctor tool-surfaces --fix fail-closed refusal (#2613, FR-003)   <- cleanest confirmed defect
   |     WP-D  doctor mission-state: preserve #2320 + identity awareness + manifest honesty (#3051/#3541, FR-004/009)
   |     WP-E  backfill cutover guard false-green fix (#3049, FR-005)
   |     WP-F  setup-plan branch-match from invoking checkout (#3124, FR-006)
   |     WP-G  find_repo_root nested-clone boundary align (#2610, FR-007)  <- core/paths.py, sequence AFTER WP-A
   |
   +-- Wave 1' — verdict seam (independent of WP-A, starts immediately):
   |     WP-H  hoist parser->status + for_review gate->lanes leaf, surface-neutral, both gate directions (#3547/#1734, FR-011)
   |     WP-I  emit --review-result-json + --help fix + in_review->approved (#3547/#1734, FR-010/012/013)  [dep WP-H]
   |     WP-J  status_event_row register review_result + NEW artifact-scoped drift test + value-equality round-trip (#3543/#3461-registry, FR-014/015/016)
   |     WP-K  review/cycle narrow kind opt-in + reader read-tolerance verification + rehome stays green (#3563 narrowed, FR-017)

Integration: full-suite parallel run + architectural gates (incl. NFR-003 single-channel) + spk-analyze.
```

> **Post-tasks squad drop (2026-08-18):** the former WP-L (coordination-key writer, FR-018/#3461-writer) is **dropped** — already fixed by #2696. WP-K (#3563) is **narrowed** to the safe kind opt-in; the full write-side default flip is deferred (disclosed physical-write rework).

**Dependency edges (squad-corrected):** WP-B…WP-G depend on WP-A (identity guard). WP-G edits `core/paths.py` (WP-A's own file) -> **hard-sequence after WP-A, not parallel**. WP-I depends on WP-H (consumes the hoisted parser/gate). WP-H…WP-K are independent of WP-A. The FR-011 clone-topology half lives inside WP-H's gate hoist (self-contained; does not need WP-A). WP-A's identity guard parses `.git` **directly** (not via `locate_project_root`), keeping it independent of WP-G.

### Work Distribution

- **Sequential**: WP-A first (guard + must-not-flip characterization); WP-G's `core/paths.py` edit sequences after WP-A.
- **Parallel streams**: fail-closed adopters (B–F) after WP-A; verdict-seam (H–K) immediately.
- **Red-first authoring starts immediately** for every slice (behavior is red on base regardless of the guard) — a pre-WP-A parallel stream.
- **DIR-012**: each WP assigns its backing issue to the HiC at implement start.

### Coordination Points

- **Sync**: rebase each lane onto the coord branch after WP-A; re-run terminology + single-channel-refusal architectural gates before each push.
- **Integration**: the six SC invariants each carry a regression test; `spec-kitty analyze` runs before consolidation.

## Complexity Tracking

*No Constitution Check violations — table intentionally empty.*

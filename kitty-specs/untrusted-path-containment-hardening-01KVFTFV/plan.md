# Implementation Plan: Untrusted-Path Containment Hardening

**Branch**: `automation/sonar-security-20260619` (stacked on PR #2036) | **Date**: 2026-06-19 | **Spec**: [spec.md](./spec.md)
**Input**: Mission specification from `kitty-specs/untrusted-path-containment-hardening-01KVFTFV/spec.md`

## Summary

Close the untrusted-path → filesystem-sink vulnerability class across the CLI. An
untrusted path segment (`mission_slug`/`feature_slug`/`wp_id`, read from
`status.events.jsonl`, `meta.json`, or frontmatter) must pass a single canonical
containment seam before any read/write/`mkdir`. PR #2036 landed the first
increment (merge bookkeeping capture-time validation, wrapper `0755→0700`,
`store.py` segment guard, `safe_mission_slug`, reducer-seam chokepoint). This plan
covers the forward work: `resolve()`-containment for the two slug resolvers, a
codebase-wide sink audit that fixes reachable sinks and documents the rest, a
regression guard against new ad-hoc joins, and a documented loopback-only
rationale for `core/loopback_http.py`.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: stdlib `pathlib`; canonical guards `core/paths.py` (`assert_safe_path_segment`, `safe_mission_slug`) and `core/utils.py` (`ensure_within_any`); typer CLI; pytest
**Storage**: filesystem — `kitty-specs/`, `.kittify/derived/`, `.worktrees/`, merge-state; `status.events.jsonl` event log
**Testing**: pytest unit + `tests/architectural/` regression guard; every guard carries a mutation-killing negative test (fails when the guard is removed), incl. a symlink-escape case
**Target Platform**: cross-platform CLI (Linux, macOS, Windows 10+)
**Project Type**: single (CLI library under `src/specify_cli`)
**Performance Goals**: no measurable regression in `status materialize`; validation is O(segment length)
**Constraints**: `ruff` + `mypy` zero issues on changed code (no new `# noqa`/`# type: ignore`); fail-closed semantics; reuse canonical seam (no parallel mechanism); MUST NOT force HTTPS on loopback URLs
**Scale/Scope**: `src/specify_cli` (the CLI surface); shared runtime/external packages out of scope unless the audit surfaces a reachable sink

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present (compact mode). Relevant gates and disposition:

- **Tests for new functionality (DIR-005) / ATDD-First (C-011)**: satisfied — each guard ships with a mutation-killing negative test (FR-008).
- **Code Quality / Quality Gates (ruff+mypy zero, complexity ≤ 15)**: satisfied — NFR-001; helpers stay small.
- **Identifier Safety Rules**: directly advanced — this mission *is* identifier/path safety.
- **Terminology Canon (Mission vs Feature)**: honored — spec/plan use Mission; `feature_slug` referenced only as the legacy on-disk field name being validated.
- **Loopback/local-only HTTP special case**: honored — C-001 forbids forcing HTTPS on loopback; FR-006 documents rationale + keeps regression tests.
- **Pre-existing Failure Reporting**: the pre-existing `test_store.py` `os` mypy note (config-suppressed) is recorded, not silently fixed.

No charter violations → no Complexity Tracking entries required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/untrusted-path-containment-hardening-01KVFTFV/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (guard behavioural contract)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── core/
│   ├── paths.py          # assert_safe_path_segment, safe_mission_slug (canonical segment seam)
│   └── utils.py          # ensure_within_any (resolve()-containment seam)
├── status/
│   ├── store.py          # _SlugResolver.resolve — add resolve()-containment (IC-01)
│   ├── aggregate.py       # sibling resolver — parity resolve()-containment (IC-01)
│   ├── reducer.py         # safe_mission_slug chokepoint (landed in #2036)
│   ├── progress.py        # derived-view write sink (covered via reducer seam, #2036)
│   ├── lifecycle.py       # derived-view write sink (covered, #2036)
│   └── views.py           # derived-view write sink (covered, #2036)
├── cli/commands/merge.py  # bookkeeping capture-time validation (landed, #2036)
└── core/loopback_http.py  # loopback-only rationale + hotspot record (IC-04)

tests/
├── status/                # resolver + derived-view containment tests
├── specify_cli/cli/commands/test_merge.py  # bookkeeping seam tests (landed)
├── core/test_loopback_http.py              # loopback regression tests (retain)
└── architectural/         # NEW regression guard banning ad-hoc untrusted joins (IC-03)
```

**Structure Decision**: Single-project CLI. Work concentrates in `src/specify_cli/status/` (resolvers + write sinks), `src/specify_cli/core/` (the canonical seams), and `tests/architectural/` (the new guard). No new top-level packages.

## Complexity Tracking

No charter violations — none.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — resolve()-containment for the store.py slug resolver

- **Purpose**: Close the residual symlink-dir escape in `store.py._SlugResolver.resolve` — it uses `.exists()`/`read_text()` with segment-grammar only, so a valid-label slug naming a symlink dir under `kitty-specs/` escapes. Add `resolve()`-containment via `ensure_within_any`. (Q1→A)
- **Relevant requirements**: FR-002, FR-008, C-004
- **Affected surfaces**: `src/specify_cli/status/store.py` (`_SlugResolver.resolve`, ~line 184), `src/specify_cli/core/utils.py` (reuse `ensure_within_any`), `tests/status/`
- **Scope correction (review)**: `aggregate.py` has **no** `_SlugResolver` analog; its slug guard `_validate_mission_slug` (aggregate.py:344-359) already calls `assert_safe_path_segment` and **raises** `InvalidMissionSlug` (callers catch it). So FR-003 is NOT resolver-parity work — it is (a) documenting aggregate's existing raise-guard and (b) handing aggregate's composed-path reads (`_find_meta_path` glob, aggregate.py:430-477) to the IC-02 audit for a containment disposition.
- **Sequencing/depends-on**: none (decision locked)
- **Risks**:
  - Preserve fail-closed *read* semantics (return `None`, don't raise); symlink-escape test must assert REJECTION, proven by mutation.
  - **macOS symlinked-root hazard (blocker-class)**: `ensure_within_any` resolves BOTH candidate and roots with `resolve(strict=False)`. The call MUST pass the un-resolved logical root; tests MUST include a **symlinked-root positive case** (e.g. `tmp_path` under `/private/var` on macOS) proving a legitimate slug is ACCEPTED — otherwise the guard false-rejects on macOS/CI and regresses NFR-003. See research Decision 6.

### IC-05 — harden the meta.json slug source feeding the derived-view write sinks

- **Purpose**: Close the write-path traversal still LIVE after #2036 (code-verified in review). `views.py:_stale_check_slug` (→ `resolve_mission_identity`, mission_metadata.py:225) and the `lifecycle.py:340-341` empty-slug fallback read `meta.json mission_slug` **unvalidated** and join it into `derived_dir / <slug>` + `mkdir`. The reducer seam (#2036) only sanitizes the *event* slug — and downgrading a hostile event slug to `""` actively triggers this `meta.json` fallback. Route `resolve_mission_identity().mission_slug` through `safe_mission_slug(..., feature_dir.name)`.
- **Relevant requirements**: FR-009, FR-007 (correction), FR-008, C-004
- **Affected surfaces**: `src/specify_cli/mission_metadata.py` (~line 225, the single source), with verification at the two consumers `src/specify_cli/status/views.py` (~240/264) and `src/specify_cli/status/lifecycle.py` (~341/426); `tests/status/`
- **Sequencing/depends-on**: none; independent of IC-01 (different source). Prefer the single chokepoint at `mission_metadata.py` so both consumers are covered at once.
- **Risks**: `resolve_mission_identity` is broadly consumed — sanitizing its slug must keep display-only consumers working (downgrade to `feature_dir.name` is display-safe); add a negative test (hostile `meta.json` + empty event log → no write outside `derived/`).

### IC-02 — codebase-wide untrusted→FS sink audit

- **Purpose**: Systematically enumerate every untrusted-string→FS-path sink in `src/specify_cli` via a reproducible ruleset (recorded seed-set + sink predicate, FR-004); route confirmed-reachable sinks through the canonical seam; assign every sink one disposition (`routed-through-seam`/`unreachable`/`trusted-source`). (Q2→C)
- **Relevant requirements**: FR-001, FR-004
- **Affected surfaces**: `src/specify_cli/**` (audit); fixes localized to confirmed-reachable sinks; an audit-record artifact under the mission dir
- **Pre-identified audit candidates (review-found floor — not exhaustive)**: `events/decision_log.py:99` (`mission_slug`→write), `coordination/surface_resolver.py:433-434` and `missions/_read_path_resolver.py:438` (`<root>/KITTY_SPECS_DIR/<mission_slug>` composition), `dossier/drift_detector.py:211,233` (`mission_slug` read+write), `migration/mission_state.py:1053` (`mission_slug` join), `review/cycle.py:225` (validated-segment-only, no containment — document), `review/arbiter.py:387,483,520` and `post_merge/review_artifact_consistency.py:59` (`tasks_dir / wp_id` — the named-but-unaddressed `wp_id` sinks). The audit MUST disposition each of these plus anything the ruleset surfaces.
- **Sequencing/depends-on**: none to start; its inventory scopes IC-03's guard coverage. Note overlap with IC-01/IC-05 on `status/` files — see decomposition note below.
- **Risks**: must distinguish trusted (`feature_dir.name`, resolved-identity) from untrusted sources to avoid false positives; record a disposition for every sink so none is silently dropped (SC-003).

### IC-03 — regression guard against ad-hoc unvalidated joins

- **Purpose**: A `tests/architectural/` test that fails when a new untrusted-segment join bypasses the canonical seam on the audited surfaces, preventing class regression.
- **Relevant requirements**: FR-005
- **Affected surfaces**: `tests/architectural/` (new test), referencing the IC-02 audited-surface list
- **Sequencing/depends-on**: IC-02 (needs the audited-surface inventory)
- **Risks**: keep the guard precise (low false-positive) — anchor on the known untrusted sources/sinks, not every `Path /` join.

### IC-04 — loopback_http.py rationale + hotspot record

- **Purpose**: Document the loopback-only (127.0.0.1) rationale in-code, retain the binding regression tests, and record the two Sonar hotspots for UI review. No behavioural change; explicitly NOT forcing HTTPS.
- **Relevant requirements**: FR-006, C-001
- **Affected surfaces**: `src/specify_cli/core/loopback_http.py` (comments/docstring), `tests/core/test_loopback_http.py` (retain), PR #2036 body / Sonar UI note
- **Sequencing/depends-on**: none
- **Risks**: ensure no reviewer later "fixes" this by forcing HTTPS — the rationale must be explicit and the regression tests must lock loopback binding.

### IC-00 (baseline, landed in PR #2036 — recognized, no new work)

- merge.py bookkeeping capture-time validation; wrapper `0755→0700`; `store.py` segment guard; `safe_mission_slug` helper; reducer-seam chokepoint. **FR-007** — must not regress.
- **Coverage correction (review, code-verified)**: the reducer-seam chokepoint protects only the **event-log** slug path. `progress.py` is fully covered; `views.py`/`lifecycle.py` have a `meta.json`-slug fallback that bypasses the seam — that gap is NEW work under **IC-05**, not baseline.

### Decomposition / ownership note (review)

`status/` is touched by IC-01 (store.py), IC-05 (views.py/lifecycle.py via mission_metadata.py), and IC-02 (audit enumerates the same files). To avoid ownership overlap when slicing WPs, linearize the shared surface: (1) IC-02 audit-record first (read-only inventory); (2) a single `status/`+`core/`-owning WP lands IC-01 + IC-05 + the status-side IC-02 fixes; (3) IC-03 guard last (needs the inventory); IC-04 (loopback) is independent and can run in parallel.

## Post-Planning Brownfield Checks

*(recorded per standing practice; see Phase 0 research for detail)*

- **Foldable issues / split-brain**: the resolver duplication between `store.py` and `aggregate.py` is the known logical-duplication seam — IC-01 keeps them at parity rather than forking a third mechanism; the canonical-seam reuse (C-002) is the consolidation lever.
- **LOC / scope**: bounded to `status/` + `core/` + one architectural test; no codebase-wide rename (not a bulk edit).
- **Deprecations**: none due for removal in the touched surfaces.
- Outcome: no scope expansion beyond the locked decisions; audit (IC-02) is the controlled discovery step.

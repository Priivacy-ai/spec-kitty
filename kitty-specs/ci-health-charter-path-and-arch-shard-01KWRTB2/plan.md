# Implementation Plan: CI Health: Charter-Path Hotfix + Arch-Adversarial Shard

**Branch**: `tidy/ci-docs-charter-path-and-arch-adversarial-shard` | **Date**: 2026-07-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/ci-health-charter-path-and-arch-shard-01KWRTB2/spec.md`

**Branch contract**: current branch, planning/base branch, and merge target are
all the same branch — `tidy/ci-docs-charter-path-and-arch-adversarial-shard`
(confirmed via `spec-kitty agent mission setup-plan --json`,
`branch_matches_target: true`). No worktree is created for planning.

## Summary

Two independent CI-health fixes bundled by operator decision (#2397):

1. **Concern A (docs, trivial).** `docs/guides/contributing.md:394` still says
   `memory files (memory/charter.md)`; this is the sole surviving offender
   `test_current_docs_do_not_publish_memory_charter_path` scans for across the
   four guarded doc roots (`docs/context`, `docs/guides`, `docs/api`,
   `spec-driven.md`). Fix: replace the stale path reference with the canonical
   `.kittify/charter/charter.md`.
2. **Concern B (CI topology, moderate).** `arch-adversarial`
   (`.github/workflows/ci-quality.yml:1702`) is today a **single-shard**
   matrix (`shard: architectural`) covering `tests/adversarial` (21 tests),
   `tests/architectural` (737 tests — the dominant bulk), `tests/architecture`
   (9), `tests/lint` (35) — 802 tests total, measured at 14.4 min
   (`tests/release/ci_topology_timings_postshrink.json`), now the slowest pole
   in an otherwise de-serialized pipeline (~13.6 min next-lane sub-target).
   Fix: split it into a **3-shard matrix**, module-file-level partitioned
   (216 / 215 / 215 tests, balanced by test-count proxy, no file split across
   shards), routed by **dedicated pytest markers** (`arch_shard_1/2/3`) rather
   than raw `--ignore` path lists — mirroring the existing marker-driven
   selection style (`docs_scoped`, `windows_ci`) and satisfying the operator's
   explicit steer toward tag-based, functionally-coherent routing over
   alphabetic/path-list splitting.

Both concerns land on the same branch/PR by operator decision; they touch
disjoint files (one doc line vs. CI workflow + test infra) so there is no
implementation-order dependency between them.

## Technical Context

**Language/Version**: Python 3.11+ (`pyproject.toml` `requires-python = ">=3.11"`); CI runners pin `python-version: '3.12'` via `astral-sh/setup-uv@v8.1.0`.
**Primary Dependencies**: pytest + pytest-xdist (`-n auto --dist loadfile`), pytest's own marker `Expression` engine (already consumed generically by `tests/architectural/_gate_coverage.py`'s `Gate(paths, ignores, marker_expr)` model), GitHub Actions (`.github/workflows/ci-quality.yml`).
**Storage**: N/A — no persisted data; this is CI-workflow YAML + pytest configuration (`pytest.ini` marker registry) + a small committed shard-assignment table.
**Testing**: pytest, run via the existing `tests/architectural/` self-referential architectural-guard style (static YAML/marker parsing, no live CI invocation needed to verify structure). New/changed guards: `tests/docs/test_current_charter_paths.py` (Concern A, already exists — just needs to go green), `tests/architectural/test_shard_universe_bounded.py` (Concern B — currently scoped only to jobs whose name contains `"core-misc"`; needs generalizing or a sibling assertion so it also covers the newly-sharded `arch-adversarial`), `tests/release/test_coverage_topology_ownership.py` (Concern B — per-shard coverage artifact names), a new completeness guard for the `arch_shard_*` marker partition (every test under the 4 arch-pole roots carries exactly one `arch_shard_N` marker — no gaps, no double-assignment).
**Target Platform**: GitHub Actions `ubuntu-latest` runners (CI infra change); local Linux/macOS dev machines for reproduction (`pytest -m 'arch_shard_2 and ...'` must reproduce a shard's exact test set locally).
**Project Type**: single project (CLI monorepo) — this mission is a CI-topology/test-infra change, not an application feature; no `src/` product code changes.
**Performance Goals**: arch-adversarial's slowest shard must land under the ~13.6-min next-lane sub-target (down from the current single-shard 14.4 min); Concern A has no performance dimension.
**Constraints**: NFR-002 (every shard runs on 100% of source changes — no differential/path-filtered triggering); the job must stay group-less and de-serialized (`if: always()`, no dorny filter `if:`, no `needs:` edge — do not accidentally re-enter `JOB_GROUPS`/fast-lane serialization, per the existing block comment at `ci-quality.yml:1683-1696`); FR-004 shard routing must be deterministic and reproducible locally; FR-005 partition must be exact (union = full pre-split universe, intersection = ∅); FR-006 coverage ownership must re-partition cleanly (the existing `coverage-arch-adversarial-${{ matrix.shard }}.xml` / `arch-adversarial-${{ matrix.shard }}-reports` naming already generalizes over shard labels — confirm it still holds for 3 shards); the docs-only trim (`-m 'docs_scoped and not windows_ci'`, PR #2391) must still apply per-shard on a docs-only PR.
**Scale/Scope**: 802 tests across 4 directories (`tests/adversarial` 21, `tests/architectural` 737, `tests/architecture` 9, `tests/lint` 35), split into 3 shards of 216/215/215 (module-file-count proxy weight — real per-test durations aren't available pre-merge, same honesty caveat the mission's own `ci_topology_timings_postshrink.json` already documents for its own projections).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority / canonical sources (Governing Principles; Standing Order 6).** Concern A: fix the doc at its one canonical offending line, no new authority. Concern B: reuse the *existing* `fast-tests-core-misc` sharding pattern and the *existing* generic `Gate(paths, ignores, marker_expr)` model in `tests/architectural/_gate_coverage.py` rather than inventing a parallel shard-modeling mechanism. **PASS.**
- **Architectural gate discipline (Standing Order 5).** `tests/architectural/test_shard_universe_bounded.py`'s catch-all coverage today is scoped to jobs whose name contains `"core-misc"` (`_CATCH_ALL_SUBSTR`), so it does **not** currently gate `arch-adversarial` at all. Sharding arch-adversarial without extending this invariant (or adding a sibling one) would be a **gate-unmask that cannot self-validate** (per charter Standing Order 5 / `feedback_gate_unmask_cannot_self_validate`) — the split would ship with no non-vacuous guard proving the union/no-double-count property FR-005 requires. **Action required in Phase 1 design**: generalize or extend this guard to cover `arch-adversarial`, plus add a completeness guard for the new `arch_shard_*` marker partition itself (every collected test under the 4 pole roots carries exactly one shard marker).
- **Test remediation / red-first discipline (Standing Order 4).** Concern A already has a pre-existing red test (`test_current_docs_do_not_publish_memory_charter_path`) — the fix is verified by making that pre-existing guard pass, not a new test. Concern B's new invariants (shard-universe generalization, marker-completeness guard) must be authored RED-first against today's single-shard topology, per the same discipline used in the prior `ci-topology-shrink` mission (`test_arch_pole_deserialized.py`'s own docstring: "Authored FAILING against today's topology"). **PASS, with the red-first requirement carried into tasks.**
- **Terminology canon.** No `feature`/`ceremony` terms introduced; no mission-terminology surface touched. **PASS.**
- **Tiered rigour (DDD).** This is pure CI/test-infra glue, not core domain logic — the "more rigour on core, less on glue" principle still applies proportionally: the new marker-completeness guard is a cheap, structural (collection-time) assertion, not a heavyweight integration test. **PASS.**
- **No version prescription in scope.** No version numbers assigned in this plan. **PASS.**

No Charter Check violations requiring justification — Complexity Tracking table below is intentionally empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/ci-health-charter-path-and-arch-shard-01KWRTB2/
├── plan.md              # This file (/spec-kitty.plan command output)
├── research.md          # Phase 0 output (/spec-kitty.plan command)
├── data-model.md        # Phase 1 output (/spec-kitty.plan command) — shard-assignment table shape
├── quickstart.md        # Phase 1 output (/spec-kitty.plan command) — local shard reproduction
├── contracts/           # N/A for this mission — no API surface; noted in research.md
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command — NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

This mission touches CI/test infrastructure only — no `src/` product code.

```
docs/guides/contributing.md                          # Concern A: one-line fix

.github/workflows/ci-quality.yml                      # Concern B: arch-adversarial matrix (currently
                                                        # single shard at line ~1702) -> 3-shard matrix

pytest.ini                                             # Concern B: register arch_shard_1/2/3 markers
                                                        # (single source of truth per #2034 —
                                                        # test_marker_registry_single_source.py)

tests/_arch_shard_map.py (new)                         # Concern B: single-source module-stem -> shard
                                                        # assignment table + the collection-time hook
                                                        # that applies the arch_shard_N marker

tests/conftest.py                                      # Concern B: wire the shard-assignment hook via
                                                        # pytest_collection_modifyitems, scoped to items
                                                        # collected under the 4 pole roots only

tests/architectural/test_shard_universe_bounded.py     # Concern B: generalize _CATCH_ALL_SUBSTR (or add
                                                        # a sibling assertion) so arch-adversarial's
                                                        # shard union/no-double-count is gated, not vacuous

tests/architectural/test_arch_shard_marker_completeness.py (new)
                                                        # Concern B: every collected test under
                                                        # tests/{adversarial,architectural,architecture,lint}
                                                        # carries exactly one arch_shard_N marker

tests/architectural/test_ci_quality_path_filters.py    # Concern B: two assertions hard-pin the literal
                                                        # single shard name "architectural"
                                                        # (line ~239 `entry["shard"] == "architectural"`,
                                                        # line ~291 `"architectural" in arch_shards") —
                                                        # found by the post-plan brownfield squad
                                                        # (randy-reducer); FOLD-PRE into IC-03, re-pin the
                                                        # same behavioral invariants (parity ratchet
                                                        # in-scope of the always-on pole; extracted arch
                                                        # shard still exists) against
                                                        # {"arch_shard_1","arch_shard_2","arch_shard_3"}

tests/release/test_coverage_topology_ownership.py      # Concern B: confirm/extend for 3 shard labels
```

**Structure Decision**: Single project (CLI monorepo), no new source trees. Concern
A is a one-line doc fix verified by an existing test. Concern B follows the
established CI-topology mission pattern (`ci-topology-shrink-01KWQAVX`,
`ci-suite-map-bind-01KWNPMP`): workflow YAML changes plus structural
(`tests/architectural/`) and topology (`tests/release/`) guards that assert the
new shape by construction, never by convention.

## Complexity Tracking

*No Charter Check violations — table intentionally left empty.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Implementation Concern Map

### IC-01 — Docs charter-path hotfix

- **Purpose**: Restore green `fast-tests-docs` on every open PR by removing the last `memory/charter.md` reference from the guarded doc roots.
- **Relevant requirements**: FR-001, FR-002.
- **Affected surfaces**: `docs/guides/contributing.md` (line 394).
- **Sequencing/depends-on**: none — independent of IC-02/IC-03.
- **Risks**: Low. Verify via the guard itself (`pytest tests/docs/test_current_charter_paths.py`), not by inspecting the single known line, per the spec's exception clause.

### IC-02 — Arch-adversarial marker-based shard partition

- **Purpose**: Introduce the `arch_shard_1/2/3` marker taxonomy and the single-source module-stem → shard assignment table (216/215/215 tests, whole files never split across shards), wired via a collection-time hook scoped to the 4 pole roots.
- **Relevant requirements**: FR-003, FR-004.
- **Affected surfaces**: `pytest.ini` (marker registration), `tests/_arch_shard_map.py` (new), `tests/conftest.py` (hook wiring).
- **Sequencing/depends-on**: none — can proceed independently of IC-01; IC-03 depends on this.
- **Risks**: Marker registration must satisfy `test_marker_job_completeness.py`'s ROUTED-BY-MARKER classification (a CI job selecting `-m arch_shard_N` makes this automatic, re-derived live — no hand-edit of that test's ledger expected, but confirm at implementation time). The hook must not leak `arch_shard_N` marks onto tests outside the 4 pole roots (would corrupt unrelated shard-completeness assumptions elsewhere).

### IC-03 — Arch-adversarial workflow matrix + coverage/topology guards

- **Purpose**: Expand `.github/workflows/ci-quality.yml`'s `arch-adversarial` job from 1 to 3 matrix legs selecting by `arch_shard_N` marker (combined with the existing full-selection and docs-only-trim marker expressions), each emitting its own `coverage-arch-adversarial-<shard>.xml`; extend the structural guards so the partition is asserted by construction.
- **Relevant requirements**: FR-003, FR-004, FR-005, FR-006.
- **Affected surfaces**: `.github/workflows/ci-quality.yml` (arch-adversarial job block), `tests/architectural/test_shard_universe_bounded.py` (generalize catch-all scope or add sibling), `tests/architectural/test_arch_shard_marker_completeness.py` (new), `tests/architectural/test_ci_quality_path_filters.py` (re-pin the two shard-name assertions at ~line 239/291 — see Pre-tasks scan outcome below), `tests/release/test_coverage_topology_ownership.py` (confirm/extend).
- **Sequencing/depends-on**: IC-02 (needs the markers to exist before the workflow can select by them; the new/extended guards can be authored red-first before or alongside IC-02).
- **Risks**: Must preserve `if: always()`, no `needs:` edge, no dorny filter `if:` (de-serialized, group-less — regression here silently re-enters `JOB_GROUPS` per the existing block comment). Must preserve the docs-only trim per-shard. `test_shard_universe_bounded.py`'s `_CATCH_ALL_SUBSTR = "core-misc"` scoping is a real gap discovered during planning — generalizing it is required, not optional, or FR-005 ships gate-unmasked. `test_ci_quality_path_filters.py`'s two literal `"architectural"` shard-name pins will red the moment the matrix changes if not updated in the same change (found by the post-plan brownfield squad, verified against source — not planned before the squad ran).

## Pre-tasks Scan Outcome (post-plan brownfield check, 2026-07-05)

Per the charter's Quality & Tech-Debt Standing Orders (adversarial squad
cadence + campsite cleaning), a bounded, profile-loaded squad ran after this
plan and before `/spec-kitty.tasks`:

- **Foldable-issue search** (`planner-priti`, via `gh`) — **NIL, nothing foldable.**
  Confirmed #2397's body/comment match this plan's scope exactly (no
  referenced sibling/follow-up issue). Three adjacent-but-distinct open issues
  were found and explicitly left as **SEPARATE-TICKET** (different fix
  mechanisms, would grow scope): #2283 (functional-shard marker-gate
  divergence — different problem class), #2380 (charter DRG-reachability
  drift, not the retired path string), #2354 (contributing-guide docsite
  publishing umbrella, unrelated to the one stale-path line). No open issue
  tracks the `test_shard_universe_bounded.py` catch-all-scoping gap this plan
  already found on its own — it stays inside this mission.
- **Split-brain + LOC-reduction scan** (`randy-reducer`) — **one real FOLD-PRE
  finding, verified against source**: `tests/architectural/test_ci_quality_path_filters.py`
  hard-pins the literal single-shard name `"architectural"` in two assertions
  (`entry["shard"] == "architectural"` at ~line 239;
  `assert "architectural" in arch_shards` at ~line 291) — both will red the
  moment the matrix becomes `arch_shard_1/2/3`. Folded into IC-03 above (see
  Project Structure). No split-brain duplication found: the
  `_COMPOSITE_ROUTING` table in `_gate_coverage.py` routes a different concern
  (src-package LOC-growth → existing named shards) and does not overlap with
  the new `tests/_arch_shard_map.py`; no dead/abandoned prior sharding attempt
  exists (`grep -rn "arch_shard"` predates this plan with zero hits besides an
  unrelated `arch_shard_min` timing key); `test_coverage_topology_ownership.py`
  is already shard-label-agnostic (matches by job name, not shard value) as
  R4 already claimed; historical/archive docs retaining
  `.kittify/memory/charter.md` are correctly out of scope as labeled legacy
  snapshots, not a second live authority.
- **Deprecation check** (done directly, mechanical) — **NIL.**
  `docs/migrations/shim-registry.yaml` is empty (`shims: []`); no
  `deprecated`/removal-due markers exist in any of the touched surfaces
  (`contributing.md`, `ci-quality.yml`, `pytest.ini`).

**Net effect on scope**: one file added to IC-03's affected surfaces
(`test_ci_quality_path_filters.py`); no scope growth beyond the mission's
existing two concerns; no tickets filed (nothing rose to SEPARATE-TICKET
severity that isn't already tracked).

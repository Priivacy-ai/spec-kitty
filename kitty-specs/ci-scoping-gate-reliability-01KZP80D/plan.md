# Implementation Plan: CI Scoping Gate Reliability

**Branch**: `fix/ci-scoping-gate-reliability` | **Date**: 2026-08-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/ci-scoping-gate-reliability-01KZP80D/spec.md`

## Summary

Two blocking CI gates are rescoped to reflect the PR's own changes. **#3008**: a data-only PR
(`packs/**`, mission planning artifacts under `kitty-specs/**`, charter config under `.kittify/**`)
never triggers the quality workflow at all — its `pull_request.paths`/`push.paths` allowlists omit
those trees (Gate 0), and even bundled with a `src/**` change no dorny group selects the corpus suites
(Gate 1). We close both gates with a **narrow** trigger + a **blocking** corpus-test job, taking care
not to fire on `status.events.jsonl`/notes/trace churn. **#3147**: the blocking docs dead-link gate
scans the whole tree and fails PRs for pre-existing broken links they never touched — we scope the
blocking check to the PR's diff and keep a whole-tree scan as a non-blocking scheduled signal. The
corpus-suite inventory and the exact two-gate trace are in
[research/corpus-suite-inventory.md](./research/corpus-suite-inventory.md).

## Technical Context

**Language/Version**: GitHub Actions YAML + Python 3.11+ (arch-guard tests)
**Primary Dependencies**: GitHub Actions, `dorny/paths-filter@v4`, pytest (architectural guards)
**Storage**: N/A
**Testing**: `tests/architectural/test_ci_quality_path_filters.py` + `test_ci_collection_completeness.py` (co-evolve, must stay green with the new group claimed); a new/extended path-filter test proving the `corpus` group IS selected on corpus data and is NOT selected on `status.events.jsonl`-only diffs
**Target Platform**: GitHub Actions CI (Linux runners)
**Project Type**: single (CI workflow config + architectural guards)
**Performance Goals**: do not add a heavy job to every PR — the corpus job runs only when the `corpus` group is selected (narrow globs)
**Constraints**: corpus job is blocking (feeds `quality-gate`); narrow `kitty-specs` globs excluding lifecycle churn (C-001); no double-run of already-covered suites (NFR-004); whole-tree docs scan retained as non-blocking (C-002); reuse `dorny/paths-filter` + the `fast-tests-docs` job shape + `doctrine-charter-tests.yml` prior art (C-003)
**Scale/Scope**: ~2 workflow files (`.github/workflows/ci-quality.yml`, `docs-freshness.yml`) + a new corpus job + arch guards + `ci_topology_census.json`

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Canonical sources / no hand-rolled equivalents (C-003)**: PASS — reuses the existing dorny filter
  mechanism, the `fast-tests-docs` job shape, and the `doctrine-charter-tests.yml` path-filtered prior
  art rather than a parallel mechanism.
- **Arch gates co-evolve, never bypassed (NFR-003)**: PASS — the path-filter/collection-completeness
  invariants are updated to claim the new group; no `# noqa`/skip to pass.
- **No silent caps / false-green (charter Sonar/CI guidance)**: PASS — the fix's entire point is to
  remove a silent false-green (corpus suites skipped) and a false-red (docs whole-tree); the corpus
  job is blocking so the removed blind spot is genuinely enforced.
- **Campsite / scope discipline**: PASS — scoped to the two named gates; narrow globs bound blast radius.

No charter violations. No Complexity Tracking entries required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/ci-scoping-gate-reliability-01KZP80D/
├── plan.md
├── spec.md
├── research.md                       # Phase 0 decisions
├── research/corpus-suite-inventory.md  # the two-gate trace + corpus-reading suite map
├── quickstart.md                     # Phase 1: how to verify
└── tasks.md                          # Phase 2 (/spec-kitty.tasks)
```

### Source (repository root)

```
.github/workflows/
├── ci-quality.yml         # pull_request.paths + push.paths allowlists; dorny filter groups; new corpus job; quality-gate wiring
└── docs-freshness.yml     # diff-scope the blocking dead-link check; whole-tree scan -> scheduled/non-blocking

tests/architectural/
├── test_ci_quality_path_filters.py       # co-evolve: assert corpus group selection + status-churn non-selection
├── test_ci_collection_completeness.py    # co-evolve: new group claims its suites; universe still total
└── ci_topology_census.json               # map the corpus test dirs to the new target_group
```

**Structure Decision**: Single project; CI-config edits + architectural-guard co-evolution. No new runtime modules.

## Implementation Concern Map

> Concerns are not work packages. `/spec-kitty.tasks` maps these to WPs. Natural split: a #3008 WP
> (IC-01+IC-02+IC-04-corpus) and a #3147 WP (IC-03). Both touch BLOCKING gates on every PR — high care.
>
> **⚠️ Post-plan squad (architect-alphonso) remediation is AUTHORITATIVE — see
> [tracer-squad-findings.md](./tracer-squad-findings.md).** Load-bearing corrections folded below:
> B1 (discrete `on.paths` globs, no braces), M1 (`@pytest.mark.corpus` marker, not whole dirs),
> M2 (register like the `docs` group, NOT `ci_topology_census.json`), M3 (co-evolve
> `test_docs_freshness_invariant.py` + `test_rulers_blocking.py`; FR-005 = the existing `push:main`
> backstop), M5 (explicit fail-closed base-ref for #3147), N1 (docs-freshness is NOT required — red-X
> friction, not a merge block).

### IC-01 — Corpus trigger (close Gate 0)

- **Purpose**: Make a data-only PR start the quality workflow at all by adding narrow corpus paths to `pull_request.paths` AND `push.paths`.
- **Relevant requirements**: FR-001, FR-003; C-001.
- **Affected surfaces**: `.github/workflows/ci-quality.yml` (`:14-30`, `:44-66`).
- **Sequencing/depends-on**: none (but pairs with IC-02 — a trigger with no group/job is inert).
- **Risks**: over-broad globs → corpus job fires on nearly every PR (the `status.events.jsonl` churn trap). MUST use `packs/**` + `kitty-specs/**/{spec.md,plan.md,tasks/**,contracts/**,acceptance-matrix.json}` + `.kittify/{charter,glossaries,doctrine,skills}/**`, never bare `kitty-specs/**`.

### IC-02 — Corpus change-group + blocking job (close Gate 1)

- **Purpose**: Add a `corpus` dorny group + a blocking corpus-test job that runs the corpus-reading tests (selected by a `@pytest.mark.corpus` marker, `-m corpus` — NOT whole dirs, M1) and feeds `quality-gate`.
- **Relevant requirements**: FR-002; NFR-001, NFR-004.
- **Affected surfaces**: `ci-quality.yml` — register the group EXACTLY like the `docs` precedent (M2): `changes.outputs.corpus` row + a `corpus:` dorny filter + a `fast-tests-corpus` if-gate (modeled on `fast-tests-docs` `:1808-1833`) + `JOB_GROUPS["fast-tests-corpus"]=["corpus"]` (`:4296`) + a `quality-gate.needs` edge (`:4198-4258`, required by `test_suite_jobs_gate_blocking.py`, N2). Plus `@pytest.mark.corpus` on the reader tests + marker registration.
- **Sequencing/depends-on**: IC-01 (trigger must fire first).
- **Risks**: **M1 double-run** — do NOT run whole dirs (re-runs doctrine/missions/charter/core_misc + huge `tests/architectural` on push/mixed PRs); the `-m corpus` marker bounds it. **M2** — do NOT touch `ci_topology_census.json`/`src_backed_groups`/the unmatched loop (corpus paths are non-src; a census row reds `test_ci_topology_worklist`). `arch-adversarial` needs no edit (its `always()` fires once triggered).

### IC-03 — Docs dead-link diff-scoping (#3147)

- **Purpose**: Scope the blocking dead-link check to the PR's changed files; retain a whole-tree scan as a non-blocking scheduled/full-run signal.
- **Relevant requirements**: FR-004, FR-005; C-002.
- **Affected surfaces**: `.github/workflows/docs-freshness.yml` (`:78-82` the blocking `relative_link_fixer --check` + `related_validator --strict` invocations); BOTH scripts gain a diff-scope mode. **FR-005 is already satisfied by the existing unfiltered `push:main` backstop (`:48-49`, non-blocking) — RETAIN it (M3); a `schedule:` trigger is optional/additive, never a replacement.**
- **Sequencing/depends-on**: none (independent of #3008).
- **Risks**: **M5** — diff-scope needs an explicit, fail-closed base ref: derive changed files from `github.event.pull_request.base.sha` with `actions/checkout` `fetch-depth: 0`, and ERROR on an empty/unresolvable changed-set (never pass trivially — that's the false-green). Apply to BOTH `relative_link_fixer` and `related_validator`. The check must still BITE on a link the PR itself breaks. **N1** — docs-freshness is NOT a required check; this is red-X friction, not a merge block — do NOT wire it into `quality-gate.needs`.

### IC-04 — Arch-invariant co-evolution + regression guard

- **Purpose**: Keep the arch invariants honest with the new `corpus` group + #3147 change; add regression guards (corpus-selection + status-churn-non-selection; a corpus completeness invariant, M4).
- **Relevant requirements**: NFR-002, NFR-003; SC-002, SC-004.
- **Affected surfaces (corrected per squad)**: `tests/architectural/test_ci_quality_path_filters.py`, `test_ci_collection_completeness.py` (co-evolve for the new group); a NEW corpus completeness guard mirroring `docs-freshness.yml:6-9` (M4: assert every committed path a `@pytest.mark.corpus` test reads is matched by the corpus trigger globs). **#3147 co-evolution (M3):** `tests/docs/test_docs_freshness_invariant.py` (keeps the `push:main` backstop + PR-allowlist shape) and `tests/docs/test_rulers_blocking.py` (CLI RED-proof — pass it a base/changed-set, keep the seeded RED green). **Do NOT touch `ci_topology_census.json` (M2)** — corpus is non-src; a census row reds `test_ci_topology_worklist`.
- **Sequencing/depends-on**: follows IC-01/IC-02/IC-03.
- **Risks**: these gates run in CI's integration-core-misc job (not fast local) — run `tests/architectural/` + `tests/docs/` before pushing; `test_suite_jobs_gate_blocking.py` reds if `fast-tests-corpus` lacks a `quality-gate.needs` edge (N2).

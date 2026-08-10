---
work_package_id: WP01
title: Corpus data triggers and gates the blocking corpus suite (#3008)
dependencies: []
requirement_refs:
- C-001
- C-003
- FR-001
- FR-002
- FR-003
- NFR-001
- NFR-002
- NFR-003
- NFR-004
planning_base_branch: fix/ci-scoping-gate-reliability
merge_target_branch: fix/ci-scoping-gate-reliability
branch_strategy: Planning artifacts for this mission were generated on fix/ci-scoping-gate-reliability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/ci-scoping-gate-reliability unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
history:
- event: created
  at: '2026-08-10T16:54:20Z'
  actor: architect-alphonso
agent_profile: python-pedro
authoritative_surface: .github/workflows/
create_intent:
- tests/architectural/test_ci_corpus_trigger_completeness.py
execution_mode: code_change
owned_files:
- .github/workflows/ci-quality.yml
- pytest.ini
- tests/architectural/test_ci_quality_path_filters.py
- tests/architectural/test_ci_collection_completeness.py
- tests/architectural/test_ci_corpus_trigger_completeness.py
- tests/doctrine/**
- tests/missions/**
- tests/specify_cli/missions/**
- tests/glossary/**
- tests/contract/test_example_round_trip.py
- tests/charter/synthesizer/test_manifest.py
- tests/integration/test_mission_review_contract_gate.py
- tests/architectural/test_wp_owned_files_no_kitty_specs.py
- tests/architectural/test_no_tracked_test_feature_missions.py
- tests/architectural/test_events_tracker_public_imports.py
- tests/architectural/test_verdict_seam_census.py
role: implementer
tags: []
tracker_refs:
- '#3008'
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile governs your implementation style, boundaries, and quality standards for this work package.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Close **both** gates that let a corpus regression ship invisibly (#3008):

- **Gate 0 (decisive)**: a data-only PR never triggers `ci-quality.yml` at all because
  `pull_request.paths`/`push.paths` omit `packs/**`, corpus `kitty-specs` files, and `.kittify`
  corpus config. → add **narrow, discrete** corpus globs to BOTH allowlists.
- **Gate 1**: even bundled with a `src/**` change, no dorny group selects the corpus-reading suites.
  → add a `corpus` change-group + a **blocking** `fast-tests-corpus` job wired into `quality-gate`.

**Done when**:
- SC-001: a `packs/built-in/**`-only diff (simulated by the path-filter test) triggers the workflow
  and runs the corpus suites as a blocking gate.
- SC-002: a `kitty-specs/**/status.events.jsonl`-only diff does NOT select the `corpus` group.
- SC-004: `test_ci_quality_path_filters.py` + `test_ci_collection_completeness.py` are green with the
  new `corpus` group claimed — no suite left unclaimed, no `# noqa`/skip.
- The corpus suite runs the corpus-reading tests via the `-m corpus` marker (NOT whole directories).

## Context & Constraints

- **Authoritative squad remediation (READ BOTH FIRST)**:
  [tracer-squad-findings.md](../tracer-squad-findings.md) (B1, M1, M2, M4, N2) **and**
  [investigate-squad-findings.md](../investigate-squad-findings.md) — the pre-implement squad found a
  BLOCKER (B-WP01 `pytestmark` clobber) and three RISKs (marker-completeness false-green R-WP01-a,
  Gate-0 unguarded R-WP01-b, 4 unnamed co-evolution guards R-WP01-c) that are folded into the subtasks
  below. The investigate findings SUPERSEDE any conflicting wording here.
- **Prior art to mirror (C-003)**: the `docs` change-group in `.github/workflows/ci-quality.yml` and
  its `fast-tests-docs` job. The census header at `:426` calls the group wiring a "5-edit atomic"
  pattern — follow it exactly for `corpus`.
- **C-001**: never add bare `kitty-specs/**` or `status.events.jsonl` to any trigger allowlist. The
  `docs-freshness` allowlist arch-invariant also forbids `kitty-specs/**` there.

### Anchors in `ci-quality.yml` (verify line numbers — file is ~4385 lines)

- `on.pull_request.paths` ≈ `:14-38`; `on.push.paths` ≈ `:44-66`. Discrete globs only (B1).
- `changes` job `outputs:` block ≈ `:160-193` — one row per group (the `docs:` row is `:181`).
- `dorny/paths-filter@v4` `filters: |` ≈ `:200`; the `docs:` filter ≈ `:373-376`.
- `fast-tests-docs` job ≈ `:1808-1833` (gated `always() && (docs=='true' || push)`, marker
  `-m "not windows_ci"`).
- `quality-gate.needs` ≈ `:4198-4258` (add `fast-tests-corpus`); `JOB_GROUPS` dict ≈ `:4296-4335`
  (`"fast-tests-docs": ["docs"]` is `:4314`).
- **Do NOT touch** `src_backed_groups`, the `unmatched` catch-all loop (`:475-535`), or
  `tests/architectural/ci_topology_census.json` — corpus paths are non-src; a census row reds
  `test_ci_topology_worklist` (M2). **M2 completion (investigate squad):** the census stays green
  ONLY IF **every corpus dorny glob stays non-src** — an `src/**` glob in the `corpus:` filter would
  grow `mapped_src_dirs` and red `test_census_mapped_dirs_matches_live_derivation`. Also note: adding
  `corpus` to the `unmatched` loop reds `test_src_filter_coverage.py:155` (unmatched == src-backed),
  NOT the census — that is the guard that actually bites.
- **Atomicity (R-WP01-c):** the corpus wiring (on.paths globs + `changes.outputs.corpus` +
  `corpus:` dorny filter + `fast-tests-corpus` if-gate + `JOB_GROUPS` row + `quality-gate.needs` edge
  + `-m corpus`) is a SINGLE atomic set. A partial edit reds a guard the base plan didn't name —
  `test_workflow_coherence.py:266` (JOB_GROUPS == parsed if-gating), `test_src_filter_coverage.py:180`
  (every group gates a test job), `test_marker_job_completeness.py:221` (registered marker must be
  routed-by-marker — the teeth behind M1). Land it whole.

## Subtasks & Detailed Guidance

### Subtask T001 — Discrete corpus globs in both trigger allowlists (FR-001, FR-003, C-001, B1)

- **Purpose**: make a data-only PR start the workflow (Gate 0), and keep the `push` allowlist in sync
  so the post-merge run also fires.
- **Steps**: add these DISCRETE lines to BOTH `on.pull_request.paths` and `on.push.paths` (GitHub
  `on.paths` supports only `* ** ? + ! []` — **no `{a,b}` brace expansion**, so braces would match
  nothing and make the fix inert):
  ```yaml
  - 'packs/**'
  - 'kitty-specs/**/spec.md'
  - 'kitty-specs/**/plan.md'
  - 'kitty-specs/**/tasks/**'
  - 'kitty-specs/**/contracts/**'
  - 'kitty-specs/**/acceptance-matrix.json'
  - '.kittify/charter/**'
  - '.kittify/glossaries/**'
  - '.kittify/doctrine/**'
  - '.kittify/release/downstream-verified.json'
  ```
- **Notes**: `.kittify/doctrine/overlays/**` is already listed — the broader `.kittify/doctrine/**`
  supersets it; keep only one (prefer the broader). MINOR-3: do NOT add `.kittify/skills/**` (no such
  dir). `acceptance-matrix.json` has no committed reader today — keep it for future-proofing (it is a
  narrow leaf, not churn).
- **Files**: `.github/workflows/ci-quality.yml`.

### Subtask T002 — `corpus` change-group (FR-002, M2)

- **Purpose**: give the trigger a group so the job can be selected.
- **Steps**:
  1. Add a `corpus:` row to the `changes` job `outputs:` block using the **exact** run_all/unmatched
     shape every other group uses (copy the `docs:` line `:181`, rename to `corpus`).
  2. Add a `corpus:` dorny filter (mirror the discrete corpus globs from T001 — dorny DOES support
     braces, but keep discrete to stay identical to `on.paths` and to the completeness invariant).
- **Do NOT**: add `corpus` to `src_backed_groups`, the `unmatched` loop, or `ci_topology_census.json`
  (M2 — those are the src-child-dir map; a corpus row reds `test_ci_topology_worklist`).
- **Files**: `.github/workflows/ci-quality.yml`.

### Subtask T003 — `fast-tests-corpus` blocking job (FR-002, NFR-001, NFR-004, M1)

- **Purpose**: run the corpus-reading suites when corpus data changes, as a blocking job.
- **Steps**: add a job modeled on `fast-tests-docs`:
  - `needs: [changes]`, `if: >- always() && (needs.changes.outputs.corpus == 'true' || github.event_name == 'push')`.
  - Run **`-m corpus`** (M1 — NOT whole directories; whole dirs re-run doctrine/missions/charter/
    core_misc and the huge `tests/architectural` on push/mixed PRs). Pass the explicit directory list
    that CONTAINS the marked modules (see T005) so collection stays bounded, e.g.
    `uv run python -m pytest <reader-dirs> -m "corpus and not windows_ci" -q ...`.
  - **`-m` selection (CORRECTED by investigate squad — no override contest exists)**: there is NO
    default `-m` in the active pytest config. `pytest.ini` `addopts` is `--tb=short` only; the
    `-m "not slow and … and not architectural …"` list lives in `[tool.mutmut] pytest_add_cli_args`
    (`pyproject.toml:406,422-431`) and is passed ONLY when mutmut forks pytest (`:453-455`) — plain
    pytest/CI is unaffected. So `-m "corpus and not windows_ci"` is the **sole** marker filter; it
    cleanly collects the marked readers (including any under `tests/architectural/`) with no override.
    (Even so, a CLI `-m` fully OVERRIDES an addopts `-m` — verified — so the design is robust either way.)
  - **No masking exit 5**: if the `corpus` marker is registered but applied to zero modules,
    `-m corpus` collects nothing → pytest **exit 5** → job FAILS (a fail-safe RED, not a false-green).
    Do NOT mask it (`|| true`, `--suppress-no-test-exit-code`). Run `--collect-only -m corpus` in dev
    to confirm the marked set is non-empty and matches the enumerated inventory.
- **NFR-004 honesty**: the `-m corpus` marker bounds the run to the marked subset even when a whole dir
  (e.g. `tests/architectural`) is a collection root — unmarked neighbors are deselected. Residual
  overlap (a marked `tests/doctrine`/`tests/architectural` module also runs in its home job on a mixed
  PR or on `push`) is small and intentional; state this in the job header comment rather than claiming
  zero overlap.
- **Files**: `.github/workflows/ci-quality.yml`.

### Subtask T004 — Wire the gate (NFR-001, N2)

- **Purpose**: make the corpus job actually block merge.
- **Steps**:
  1. Add `"fast-tests-corpus": ["corpus"]` to the `JOB_GROUPS` dict (`:4296`).
  2. Add `- fast-tests-corpus` to `quality-gate.needs` (`:4198`). Without this edge,
     `tests/architectural/test_suite_jobs_gate_blocking.py` reds (pytest-jobs containment; see
     `contracts/quality-gate-needs-containment.md`).
- **Files**: `.github/workflows/ci-quality.yml`.

### Subtask T005 — Register + apply the `corpus` marker (FR-002, NFR-004)

- **Purpose**: define which tests the corpus job runs.
- **Steps**:
  1. Register the marker in **`pytest.ini`** (`markers =` at `:14`) — NOT `pyproject.toml` (its
     `[tool.pytest.ini_options]` block is intentionally empty; a markers list there is dead config
     that silently drifts — see the note at `pyproject.toml:207-213`).
  2. **⚠️ BLOCKER B-WP01 — APPEND, never replace `pytestmark`.** 6 of the 7 named readers ALREADY
     carry a load-bearing `pytestmark`; a literal `pytestmark = [pytest.mark.corpus]` OVERWRITES it,
     dropping `architectural`/`contract`/`unit`/`integration`/`fast`/`git_repo` → cascade of reds
     (shard bucketing in `conftest._apply_shard_markers`, `test_marker_job_completeness` which
     HARD-asserts `contract` is routed-by-marker, and `test_ci_collection_completeness` orphans).
     **Extend the existing list**; add a fresh `pytestmark` only where a module has none. Existing
     markers to preserve:
     | Reader | Existing → make it |
     |--------|--------------------|
     | `tests/architectural/test_wp_owned_files_no_kitty_specs.py:12` | `fast` → `[pytest.mark.fast, pytest.mark.corpus]` |
     | `tests/architectural/test_no_tracked_test_feature_missions.py:10` | `[architectural, git_repo]` → `+ pytest.mark.corpus` |
     | `tests/architectural/test_events_tracker_public_imports.py:26` | `[architectural]` → `+ pytest.mark.corpus` |
     | `tests/architectural/test_verdict_seam_census.py:165` | `architectural` → `[pytest.mark.architectural, pytest.mark.corpus]` |
     | `tests/contract/test_example_round_trip.py:73` | `[contract, fast]` → `+ pytest.mark.corpus` |
     | `tests/charter/synthesizer/test_manifest.py:44` | `[unit]` → `[pytest.mark.unit, pytest.mark.corpus]` |
     | `tests/integration/test_mission_review_contract_gate.py:38` | `[integration, git_repo]` → `+ pytest.mark.corpus` |
     For the `tests/doctrine/**` built-in-graph readers, confirm each module's existing `pytestmark`
     (grep) and append `pytest.mark.corpus` the same way. Enumerate readers from
     [research/corpus-suite-inventory.md](../research/corpus-suite-inventory.md) + a grep for the
     corpus-loading entry points (`load_built_in_graph`, `packs/built-in` fixtures). Mark only modules
     that actually read the corpus.
- **Files**: `pytest.ini` + the corpus-reader test modules (owned dirs above).

### Subtask T006 — Co-evolve the arch invariants (NFR-002, NFR-003, SC-002, SC-004)

- **Purpose**: keep the CI-topology guards honest with the new group.
- **Steps**:
  - `tests/architectural/test_ci_quality_path_filters.py`: claim the `corpus` group; add assertions
    that a `packs/built-in/**` (and a narrow `kitty-specs/<m>/spec.md`) diff SELECTS `corpus`, and a
    `kitty-specs/<m>/status.events.jsonl`-only diff does NOT (SC-002). NOTE this test parses only the
    dorny `filters` block (Gate 1) — it does NOT cover the `on.paths` trigger (Gate 0). Gate 0 is
    covered by T007.
  - `tests/architectural/test_ci_collection_completeness.py`: the new group claims its suites; the
    universe stays total (no suite unclaimed).
- **Verify the 4 co-evolution guards the base plan omitted (R-WP01-c)** — a partial 5-edit reds one of
  them, so run them all and confirm green:
  - `test_workflow_coherence.py` (`JOB_GROUPS == parsed if-gating`, FR-011).
  - `test_src_filter_coverage.py` (every named group gates a test job; `unmatched == src-backed`).
  - `test_marker_job_completeness.py` (registered `corpus` marker must be routed-by-marker — reds if
    the job runs whole dirs without `-m corpus`).
  - `test_ci_topology_worklist.py` + `test_suite_jobs_gate_blocking.py` (M2 / N2).
- **Notes**: these live in CI's integration-core-misc job (not fast-local). Run:
  `PWHEADLESS=1 python -m pytest tests/architectural/test_ci_quality_path_filters.py tests/architectural/test_ci_collection_completeness.py tests/architectural/test_workflow_coherence.py tests/architectural/test_src_filter_coverage.py tests/architectural/test_marker_job_completeness.py tests/architectural/test_ci_topology_worklist.py tests/architectural/test_suite_jobs_gate_blocking.py tests/architectural/test_ci_corpus_trigger_completeness.py -p no:cacheprovider -q`.

### Subtask T007 — Corpus completeness invariant, HONEST form (M4 reworked + R-WP01-a + R-WP01-b)

- **Purpose**: close two silent-no-op vectors — (1) Gate 0 shipping inert because nothing guards the
  `on.paths` trigger, and (2) a corpus reader that is never marked silently dropping out of the gate.
- **⚠️ M4-as-worded is NOT statically computable.** "Every path a `@corpus` test *reads*" cannot be
  enumerated statically — readers reach data through loaders/fixtures (`load_built_in_graph`,
  `packs/built-in` conftest fixtures) and dynamically-built paths. `docs-freshness` itself concedes its
  true input set is "unbounded" and leans on the `push:main` backstop. Implement the **decidable
  proxy** instead, in `tests/architectural/test_ci_corpus_trigger_completeness.py`:
  1. **Gate-0 presence (R-WP01-b, the decisive net)**: parse the workflow and assert every corpus glob
     is present in **BOTH** `on.pull_request.paths` AND `on.push.paths`. **YAML gotcha:**
     `yaml.safe_load` parses the top-level `on:` key as boolean `True` — access
     `data[True]["pull_request"]["paths"]` / `data[True]["push"]["paths"]` (a `data["on"]` access
     crashes or asserts nothing). Optionally also assert the `on.paths` corpus set == the `corpus:`
     dorny filter set (keeps the two allowlists in lockstep).
  2. **Reader-root coverage (glob-vs-glob, decidable)**: declare the set of corpus data ROOTS
     (`packs/`, the `kitty-specs/**` leaf globs, `.kittify/{charter,glossaries,doctrine}`,
     `.kittify/release/downstream-verified.json`) and assert each declared root is covered by a corpus
     trigger glob.
  3. **Marker-completeness (R-WP01-a, closes the residual false-green)**: bind readers → marked. Assert
     the set of `@pytest.mark.corpus`-marked modules equals a **curated list** (so a NEW reader forces a
     conscious registry update), OR assert the `-m corpus` collection count == the enumerated inventory
     count from `research/corpus-suite-inventory.md` (a **floor**, not just `>0`). T007-without-this
     guards trigger-coverage only, not marking-coverage — an unmarked reader would ship #3008 for its
     module.
- **Files**: `tests/architectural/test_ci_corpus_trigger_completeness.py` (new — see `create_intent`).

## Test Strategy

- Arch guards are the acceptance surface (T006, T007). All must be green with the group claimed and
  zero skip/noqa (NFR-003).
- Run the CI-topology suite before pushing:
  `PWHEADLESS=1 python -m pytest tests/architectural/test_ci_quality_path_filters.py tests/architectural/test_ci_collection_completeness.py tests/architectural/test_suite_jobs_gate_blocking.py tests/architectural/test_ci_topology_worklist.py tests/architectural/test_ci_corpus_trigger_completeness.py -p no:cacheprovider -q`.
- Sanity-collect the corpus selection: `python -m pytest <reader-dirs> -m "corpus and not windows_ci" --collect-only -q` and confirm it collects the marked readers (incl. the architectural ones) and nothing unexpected.

## Risks & Mitigations

- **Gate-0 ships inert (R-WP01-b, highest)**: forgetting T001 makes every arch test green with a
  workflow that never triggers on corpus PRs. T007's Gate-0 presence check is the ONLY net — write it.
- **`pytestmark` clobber (B-WP01, BLOCKER)**: APPEND to existing `pytestmark`, never replace (T005).
- **Marker-completeness false-green (R-WP01-a)**: T007 must bind readers ⊆ marked (curated list or
  count floor), not only marked → globs.
- **Partial 5-edit reds an unnamed guard (R-WP01-c)**: land on.paths + group + filter + job + JOB_GROUPS
  + needs + `-m corpus` as one atomic set; run `test_workflow_coherence`/`test_src_filter_coverage`/
  `test_marker_job_completeness` too.
- **Brace-glob inertness (B1)**: discrete globs only in `on.paths`.
- **Double-run (M1/NFR-004)**: `-m corpus` bounds it; do not run whole dirs.
- **Census red (M2)**: do not touch `ci_topology_census.json`/`src_backed_groups`/unmatched loop; keep
  every corpus glob non-src.
- **Missing gate edge (N2)**: add the `quality-gate.needs` edge or `test_suite_jobs_gate_blocking.py` reds.

## Review Guidance

- Confirm the globs are discrete (no `{}`), present in BOTH `pull_request.paths` and `push.paths`, and
  exclude `status.events.jsonl`/notes/trace.
- Confirm the 5-edit group pattern matches the `docs` precedent and the `quality-gate.needs` edge AND
  the `JOB_GROUPS` row both exist (needs edge = failure blocks; JOB_GROUPS row = improper-skip blocks).
- Confirm `ci_topology_census.json` is untouched and every corpus glob is non-src.
- Confirm every reader's `pytestmark` was EXTENDED (existing markers preserved), not overwritten.
- Confirm the corpus job is BLOCKING, runs `-m corpus` (not whole dirs), and exit 5 is NOT masked.
- Confirm T007 asserts Gate-0 presence in BOTH `on.paths` blocks AND marker-completeness (readers ⊆
  marked) — not a vacuous pass, and not the unimplementable "paths a test reads" form.
- Confirm the co-evolution run set (path_filters, collection_completeness, workflow_coherence,
  src_filter_coverage, marker_job_completeness, topology_worklist, suite_jobs_gate_blocking) is green.

## Activity Log

- 2026-08-10T16:54:20Z – system – lane=planned – Prompt created.

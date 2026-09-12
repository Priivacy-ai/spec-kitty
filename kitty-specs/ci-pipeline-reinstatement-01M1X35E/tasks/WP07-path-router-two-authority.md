---
work_package_id: WP07
title: Path router + two-authority + single gate-selection authority
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
requirement_refs:
- FR-004
- FR-005
- FR-008
- FR-016
- NFR-002
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
subtasks:
- T034
- T035
- T036
- T037
- T038
- T039
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: implementer-ivan
authoritative_surface: .github/workflows/ci-router.yml
create_intent:
- .github/workflows/ci-router.yml
- scripts/ci/gate_selection.py
- tests/architectural/test_gate_selection_authority.py
execution_mode: code_change
owned_files:
- .github/workflows/ci-router.yml
- scripts/ci/gate_selection.py
- tests/architectural/test_gate_selection_authority.py
- tests/architectural/test_ci_quality_path_filters.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load <profile>` (role:
implementer) before anything else. Then read `plan.md` (TOPOLOGY T1),
`contracts/router-two-authority.md` (**authoritative**), `research.md` D1, and the
charter §"ATDD-First" + SO#5 + SO#6 (reuse `dorny/paths-filter`, don't hand-roll).

**Cluster gate:** this WP claims only after ALL FOUNDATION WPs (WP01–WP06) are
approved/done — it consumes the WP05 scrub artefact for its filter groups.

## Objective

Build the **path-scoped change router** and the **single gate-selection authority**:

- **Two-authority model (contract):** exactly two hand-authored sources — the dorny
  filter block (`group → globs[]`) and the job `if:` gates (`if:
  needs.changes.outputs.<group>`). Everything else (catch-all OR-list, aggregator
  `needs:`, completeness oracle) is **derived + asserted against** the two.
- **Fail-closed:** a `src/**` change matched by **no** group forces `run-all` (loud
  unmatched alarm), never a silent skip; `docs`/`corpus` are non-src, excluded from
  the unmatched loop.
- **Shift-left ladder (FR-005):** cheapest static/lint/regen/terminology/arch-import
  gates run and fail first.
- **FR-008 / NFR-002 split:** the **fast** always-on gates (terminology, layer-rule)
  run unconditionally and de-serialized (adding **no** filter group); the **heavy**
  architectural battery is **code-scoped** (a docs-only PR pays for neither).
- **Gate-selection authority (FR-016/#2476):** ONE importable function that **parses**
  the two authorities (does not re-encode them) and answers "which shards/gates does
  this diff select" — built here, reused by WP18 (local pre-PR parity) and WP17
  (completeness oracle). Not a second parser.

## Subtask guidance

### T034 — Red-first: rewrite `test_ci_quality_path_filters.py` (SEPARATE first commit)

The existing `test_ci_quality_path_filters.py` pins that the husk has **no** filter
(research D1 guard). As your **first commit**, rewrite it to assert the reinstated
two-authority model + fail-closed unmatched→run-all against the on-disk router. Run
against base: it must red for the right reason (the router `ci-router.yml` does not yet
exist / still has no filters). This is the in-repo red-first for a CI-YAML WP.

### T035 — Tidy-first + author `ci-router.yml`

If you touch a shared shift-left surface, do a behavior-preserving tidy commit first
(SO#2). Then author `.github/workflows/ci-router.yml`: the dorny `changes` job
(`dorny/paths-filter`, SHA-pinned) computing `group → outputs` from the WP05 scrub
groups, plus the shift-left front (ruff/format/uv-lock/commit-msg/markdown/TID251/
glossary → `regen --check` → terminology + fast arch-import gates) ordered
cheapest-first with no `needs:` between the front-line lint jobs.

### T036 — Job `if:` gates + fast/heavy arch split

Wire the job `if:` gates (`if: needs.changes.outputs.<group>`). Realize the FR-008 /
NFR-002 split: the **fast** always-on gates (terminology, layer-rule/import) run
unconditionally, de-serialized, adding **no** filter group; the **heavy** architectural
battery is **code-scoped** so a docs-only PR runs neither. A docs-only PR must run 0
code shards (NFR-002).

Also in `ci-router.yml`: **declare `workflow_dispatch`; honor the `mode` input**
(PR=fail-fast/short-circuit, full=`if: always()`/run-all) in this router's own
fail-fast/`needs` behavior per FR-018/FR-019 — the mode-conditioned logic lives in this
owned workflow file, verified by WP11's cross-cutting `test_dual_mode_contract`.

### T037 — Single gate-selection authority

Author `scripts/ci/gate_selection.py`: one importable function that **parses** the two
authorities from the on-disk `ci-router.yml` (the dorny filter block + the job `if:`
gates) and returns "which shards/gates a given changed-path set selects". It PARSES —
it does not re-encode the routing as a second hand-maintained map (that would be the
very #2476 duplication we are closing). Keep complexity ≤15; give it a clean public
API for WP17/WP18.

### T038 — `test_gate_selection_authority.py`

Author `tests/architectural/test_gate_selection_authority.py`: assert the authority's
answers are consistent with the two hand-sources (feed sample diffs, assert selected
gates), and assert it is the **single** authority (WP17/WP18 import it; there is no
second parser). Include a non-vacuity floor.

### T039 — Fail-closed catch-all

Implement + assert: a `src/**` change matched by no group forces `run-all` with a loud
unmatched alarm (never a silent skip); `docs`/`corpus` are excluded from the unmatched
loop (data, not code). Assert this via both the router YAML and the gate-selection
authority.

## Branch Strategy

- Base/target: `feat/ci-pipeline-reinstatement`; worktree via `spec-kitty implement WP07`.
- Depends on all FOUNDATION WPs (cluster gate) — claim after they are approved/done.
- Commit order: **T034 red-first FIRST**, then T035 tidy, then T036–T039.

## Definition of Done

- T034 red on base (evidence captured), green on final.
- `ci-router.yml` implements the two-authority model, the shift-left ladder, the
  fast/heavy arch split, and fail-closed unmatched→run-all; dorny SHA-pinned.
- `scripts/ci/gate_selection.py` is the single importable authority that PARSES the two
  sources; `test_gate_selection_authority.py` asserts consistency + singularity + a
  non-vacuity floor.
- A docs-only path set selects 0 code shards (NFR-002) — asserted by
  `test_ci_quality_path_filters.py` (feed a docs-only diff, assert 0 code shards) — an
  objective assertion, not an eyeballed read of the YAML.
- `ci-router.yml` declares `workflow_dispatch` and honors the `mode` input
  (PR fail-fast vs full `if: always()`) in its own fail-fast/`needs` behavior
  (FR-018/FR-019) — this router's mode wiring is verified by WP11's
  `test_dual_mode_contract`.
- **Targeted test surface**: `pytest tests/architectural/test_ci_quality_path_filters.py tests/architectural/test_gate_selection_authority.py -q` (these two tests gate this DoD).

## Risks

- **Re-encode temptation**: the authority must PARSE, not duplicate. A second
  hand-maintained routing map re-opens #2476 — reviewer must confirm parsing.
- **Two-authority drift**: any derived surface hand-maintained instead of asserted
  drifts silently. Assert all derived surfaces against the two sources.
- **#3008 hazard**: `on.paths` (Gate-0) vs dorny `filters:` (Gate-1) drift silently
  no-ops routing — keep in lockstep or run on every PR with Gate-0 dropped
  (contract §Invariant 6).
- **New-file arch battery**: new `scripts/ci/gate_selection.py` symbol + new test dir
  trips dead-symbol `__all__`, shard-map/path-filter routing for the new test dir,
  clock-call-ban. Pre-check locally (memory `new-file arch gate battery`).
- **regen-assets**: this WP edits no `packs/` SOURCE, so `spec-kitty regen` should not
  fire; if a generated-fixture gate reds, trace the source, don't improvise.

## Reviewer guidance

- Confirm T034 red-on-base for the right reason.
- Confirm the gate-selection authority PARSES the YAML (open it — reject any
  second hand-map).
- Feed a docs-only and a `src/**`-unmatched diff to the authority; confirm 0-code-shard
  and run-all respectively.
- Confirm the fast/heavy arch split matches FR-008/NFR-002 (docs-only pays for neither
  the heavy battery nor a code shard).

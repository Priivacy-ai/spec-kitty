---
work_package_id: WP02
title: Dead-code census machine oracle (bidirectional guardrail)
dependencies: []
requirement_refs:
- C-006
- FR-013
- NFR-006
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: python-pedro
authoritative_surface: tests/architectural/_p1_census_oracle.py
create_intent:
- tests/architectural/_p1_census_oracle.py
- tests/architectural/test_p1_census_oracle.py
- tests/architectural/p1_census/census.json
execution_mode: code_change
owned_files:
- tests/architectural/_p1_census_oracle.py
- tests/architectural/test_p1_census_oracle.py
- tests/architectural/p1_census/census.json
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load <profile>` (role:
implementer) before anything else. Then read `plan.md` (FOUNDATION F2),
`contracts/p1-census-oracle.md` (**authoritative** — the bidirectional guardrail),
`data-model.md` E3, and the charter §"ATDD-First" + SO#5 (non-vacuous gates).

## Objective

P1 ("no dead-code tests in CI") is **paramount** and MUST be machine-enforced, not a
reviewer scrub (the post-spec squad's convergent finding). This WP builds the
**dead-code census as an in-repo machine oracle** that (a) authorizes each base-red
drop (consumed by WP03), (b) authorizes each shard/`--cov` exclusion (consumed by
WP05), and (c) excludes census-`dead` surfaces from the coverage denominator. The
oracle is the P1 authority every downstream scrub/exclusion depends on — build it
before the things that consume it (WP03/WP05/WP15 depend on this WP).

**Census subject (binding — the load-bearing distinction):** the census evaluates the
**retired src surface a test imports/exercises**, NOT the test file's own importer
count. A base-red test is droppable ONLY if the src surface it covers is census-`dead`
— *never* because "the test file has zero importers" (every test file has zero
importers; that predicate is always true and would authorize dropping any red). The
zero-importer-AND-not-dynamically-reached evidence is measured over the **src surface
under test**, not the test module.

**The loophole is two-sided; the guardrail is bidirectional:**
- *False-negative (rubber-stamp)*: a live regression mislabeled "dead-code test" and
  dropped. Defense: a drop requires **independent evidence** about the **src surface
  under test** (retirement-gate ref / ADR / that src surface is
  zero-importer-AND-not-dynamically-reached), never self-certification and never the
  test file's own importer count.
- *False-positive (mis-mark live as dead)*: a surface reachable only dynamically
  (entry points, plugin/registry dispatch, `getattr`/import-string, CLI wiring) with
  static importer-count 0, wrongly marked dead. Defense: a **"known-live is never
  dead"** guard refuses to mark these `dead`.

**Boundary (C-006):** census-`dead` is about *behavioral tests over dead code*. The
enforcement allowlists (`test_no_dead_symbols` / `test_no_dead_modules` /
`test_no_retired_subsystems`) that *quote* dead surfaces as banned strings are
**always-on** and OUT of scope of exclusion — never disable or exclude them.

## Subtask guidance

### T007 — Red-first: self-mutation negative (SEPARATE first commit)

As your **first commit**, author `tests/architectural/test_p1_census_oracle.py` with
a self-mutation negative that plants a dead-code shard / retired-import fixture and
asserts (i) the census flags it `dead` and (ii) the exclusion gate fires. Run against
base and **confirm red for the right reason** — the oracle `_p1_census_oracle.py`
does not yet exist, so import it lazily/in-test so the file still *collects*; assert
the observable behavior is missing, not merely that a symbol is absent. Capture the
red evidence.

### T008 — Census schema + data artefact

Create `tests/architectural/p1_census/census.json` with the E3 schema: per entry
`{surface: path|symbol, status: dead|live, evidence: <importer-count|ADR|gate-ref>,
authorizes: drop|denominator-exclude}`. Seed it with the surfaces the mission needs
(the retired subsystems sync/saas/delivery/emit/websockets, the `mission_v1`
dead-import test subjects WP03 will drop). Evidence must be concrete and
reviewer-checkable — no bare "dead" labels.

### T009 — Census oracle resolution logic

Author `tests/architectural/_p1_census_oracle.py`: an importable oracle that resolves
each surface's status from (a) the retirement arch gates
(`test_no_retired_subsystems`), (b) a static importer graph over `src/**` + `tests/**`,
and (c) the recorded `census.json` evidence. Expose the single public function(s)
WP03/WP05/WP15 will import (e.g. `is_dead(surface) -> (bool, evidence)` and
`census_dead_surfaces()`). Keep complexity ≤15 (extract helpers); this is importable
support, so give it a clear API and docstrings.

### T010 — False-negative guard (independent evidence required)

Add the guard + its test: a surface may be authorized `drop` **only** with
independent evidence about the **src surface under test** (retirement-gate ref / ADR /
that src surface is zero-importer-AND-not-dynamically-reached). A `census.json` entry
with `status: dead` but no valid evidence field must be **refused** (the oracle
raises / the test reds). Add a second **planted negative: a live-src test is REFUSED as
a drop** — a test whose src surface is live (importer>0 or dynamically reached) must not
be authorizable `drop` even if someone labels it `dead`. This is what makes WP03's
per-red drop non-fakeable and forbids dropping a red on the (always-true) test-file
importer count.

### T011 — False-positive "known-live is never dead" guard

Add the guard + a planted positive-side negative test: plant a surface that is
importer-0 statically but reachable dynamically (simulate an entry-point / registry /
import-string dispatch). Assert the census **refuses to mark it `dead`**. Enumerate
the dynamic-reach signals the oracle honors (entry points, plugin/registry dispatch,
`getattr`/import-string, CLI wiring) and document them in the oracle.

**Own intermediate red anchor (distinct from T007's false-negative red):** stage this
guard so it has its **own** red — with the resolution oracle already present (T009) but
the known-live guard **absent**, a known-live-but-importer-0 surface is mis-marked
`dead` and the test reds. Land the guard to turn it green. Do **not** co-land guard and
assertion as a tautology that was never red; the reviewer must see this false-positive
guard fail on its own before it passes, separately from the T007 false-negative anchor.

### T012 — Non-vacuity floor + denominator exclusion + boundary

- **Non-vacuity (SO#5 / DIR-043):** the oracle MUST fail if it evaluates an empty set
  — add a floor assertion + test.
- **Denominator exclusion:** assert a census-`dead` surface is excluded from the
  coverage denominator (the contract WP10/WP15 rely on).
- **Boundary:** add a test asserting the enforcement allowlists
  (`test_no_dead_symbols`/`test_no_dead_modules`/`test_no_retired_subsystems`) are
  NOT in the exclusion set — they stay always-on.

## Branch Strategy

- Base/target: `feat/ci-pipeline-reinstatement`; worktree via `spec-kitty implement WP02`.
- Commit order: **T007 red-first FIRST**, then T008–T012. Reviewer verifies
  red-on-base → green-on-final.

## Definition of Done

- T007 was red on base (evidence captured) and green on final.
- `_p1_census_oracle.py` exposes the importable API WP03/WP05/WP15 consume;
  `census.json` carries concrete per-surface evidence.
- Both guardrail directions have a **planted negative** that actually fails when the
  guard is removed (false-negative: unevidenced drop refused **and** a live-src test
  refused as a drop; false-positive: known-live-importer-0 refused as dead). The
  false-positive guard (T011) has its **own** intermediate red (oracle present, guard
  absent → known-live mis-marked `dead` reds), distinct from the T007 false-negative
  red — neither is a co-landing tautology.
- The census subject is the **retired src surface under test**, never the test file's
  own (always-zero) importer count — asserted, not just prose.
- Non-vacuity floor present; denominator-exclusion asserted; enforcement allowlists
  proven out of scope.
- **Targeted test surface**: `pytest tests/architectural/test_p1_census_oracle.py -q`
  plus `pytest tests/architectural/test_no_retired_subsystems.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_no_dead_modules.py -q`.

## Risks

- **Fakeable census (top squad-flagged risk)**: the anti-laziness pass will target this
  DoD. The independent-evidence guard (T010) must actually reject an unevidenced
  entry — prove it with the planted negative, not prose.
- **Dynamic-reach false-positives**: under-enumerating dynamic-reach signals wrongly
  drops live code. Cross-check against the `test_no_dead_*` allowlists' own
  dynamic-reach handling; reuse their logic where canonical (SO#6), don't fork it.
- **New-file arch battery** (memory `new-file arch gate battery`): a new src/test
  symbol + test file trips dead-symbol `__all__`, shard-map completeness,
  clock-call-ban, env-fragile absolute counts. Pre-check locally under
  `uv sync --all-extras`; annotate golden-count `len==N` asserts if any.

## Reviewer guidance

- Verify T007 red-on-base for the right reason (missing behavior, not import error).
- Independently confirm both planted negatives fail when their guard is deleted —
  this is the non-fakeability proof.
- Confirm the oracle's public API is what WP03/WP05/WP15 import (no divergent
  second census).
- Confirm enforcement allowlists are untouched and proven out-of-scope.

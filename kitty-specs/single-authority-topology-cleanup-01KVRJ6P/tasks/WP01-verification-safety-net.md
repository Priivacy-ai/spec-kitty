---
work_package_id: WP01
title: Verification safety net (differential cell + AST guard + RED repro)
dependencies: []
requirement_refs:
- FR-010
- FR-011
- NFR-002
- NFR-003
tracker_refs: []
planning_base_branch: feat/single-authority-topology-cleanup
merge_target_branch: feat/single-authority-topology-cleanup
branch_strategy: Planning artifacts for this mission were generated on feat/single-authority-topology-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-authority-topology-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1313978"
history:
- Created by /spec-kitty.tasks 2026-06-23
agent_profile: python-pedro
authoritative_surface: tests/
create_intent:
- tests/architectural/test_commit_target_kind_guard.py
execution_mode: code_change
owned_files:
- tests/missions/test_surface_resolution_equivalence.py
- tests/architectural/test_commit_target_kind_guard.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before anything else, load your profile: read
`src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt its
directives/tactics (or run `/ad-hoc-profile-load python-pedro`). State which
directives you applied before implementing.

## Objective

Land the **verification safety net** that GATES every deletion and collapse in
this mission. Nothing in lane B (the `CommitTargetKind` eradication, the
`FLATTENED` deletion, the `topology=None` husk-arm collapse) is safe to land
until these three things exist: a differential-equivalence cell proving
classify-on-read ≡ backfill-then-read, a non-fakeable AST guard against
reintroducing the eradicated type, and a live RED repro of the FR-004 bug that a
later WP will flip green.

This is a **behavior-neutral** mission with ONE correctness improvement (FR-004);
WP01 is what makes the improvement provable and the deletions reversible-safe.

## Context

- The SSOT seam (PR #2086) already shipped: `MissionTopology` is stored in
  `meta.json`; `read_topology(feature_dir)` (`src/specify_cli/migration/backfill_topology.py:68`)
  absorbs a missing field by deriving a concrete topology; the differential gate
  `tests/missions/test_surface_resolution_equivalence.py` (~37 KB) already
  parametrizes `flattened-stale-coord` / `coord-deleted` / `coord-empty` cells
  with a `_stored_topology` helper.
- `tests/architectural/` already has AST infrastructure: `audit.py`,
  `_ratchet_keys.py` (composite_key), `test_no_dead_modules.py` — reuse it
  (C-009 canonical sources), do NOT hand-roll a new AST walker.

## Subtasks

### T001 — Differential cell: classify-on-read ≡ backfill-then-read (GREEN)
Extend `test_surface_resolution_equivalence.py` with a new parametrized cell that,
for every `(topology × transient)` combination, asserts the resolved surface from
**classify-on-read** (an un-backfilled `meta.json`, topology derived on the fly)
is identical to **backfill-then-read** (the same mission after
`backfill_mission_topology`). Use the existing `_stored_topology` helper + the
existing matrix. The cell MUST be asserted **green** — do NOT park it behind an
`_XFAIL_*_OUT_OF_SCOPE` marker (those guard the orthogonal C-005 transient
probes). If the equivalence cannot yet be green on current code for the
flattened-un-backfilled case, that is exactly what T002 captures as the RED repro
— keep T001 to the cells that ARE equivalent today (backfilled paths) and let
T002 own the bug.

### T002 — NFR-002 live repro (xfail strict, RED-by-design)
Add a focused test: an **un-backfilled flattened mission** (meta.json has NO
`topology` key, a stale coordination husk on disk) resolves its planning surface.
On current `main` this resolves to the stale-coord husk (the #2062 bug, surviving
on the un-backfilled path). Assert it resolves to **PRIMARY**. Mark it
`@pytest.mark.xfail(strict=True, reason="FR-004 not yet landed — flips green in WP06")`
so the suite is green now and the strict-xfail FAILS loudly the moment WP06 makes
it pass (forcing WP06 to remove the marker). This is the live RED→GREEN evidence
for NFR-002 — a static edit cannot satisfy it.

### T003 — AST guard against CommitTargetKind / FLATTENED.value reintroduction
Create `tests/architectural/test_commit_target_kind_guard.py` reusing
`audit.py` + `_ratchet_keys.py`. It must FAIL CI if, in `src/`:
(a) any `CommitTargetKind` symbol reference reappears, OR
(b) anything serializes the former enum value `"flattened"` **as the enum** (NOT
the surviving `flattened` provenance meta-flag — distinguish by symbol/AST, never
by grepping the string, because `FLATTENED.value == "flattened"` collides with the
flag). Today `CommitTargetKind` still exists, so scope the guard to ASSERT the
post-eradication invariant and mark it `xfail(strict=True, reason="enum still
present until WP04/WP05 — flips green when eradicated")`, OR write it to count
references and assert the count only drops (a ratchet). Choose the ratchet form if
it lets the guard be green-and-tightening through WP03→WP05; otherwise xfail-strict
that WP04/WP05 flips. Document the choice in the test docstring.

### T004 — Planted-literal self-test (non-fakeability, NFR-003)
Add a self-test proving the T003 guard actually fails on a planted phantom: feed
the guard a synthetic source containing a `CommitTargetKind` reference AND a
synthetic source serializing the former enum value, and assert the guard reports
both. This proves the guard is not a no-op (the gate-unmask discipline: a guard
that can't fail on a planted offender is theater).

## Campsite (#1970 — REQUIRED)
While in these test files: remove any dead helpers, stale xfail markers whose
reason no longer holds, duplicated fixture setup (S1192), and fix any lint/type
debt on the lines you touch. Do NOT broaden into unrelated test files.

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP01-specific test-DoD
- **(a) Absolute per-topology surface cell (OWNED HERE).** Add a cell that pins, by an explicit value table, `SINGLE_BRANCH`/`LANES` → **PRIMARY** (`routes_through_coordination` False) and `COORD`/`LANES_WITH_COORD` → **coordination** (`routes_through_coordination` True). This is **not** cross-leg equality — it is the ONLY kill for the wrong-mapping mutant the differential gate (leg-vs-leg) cannot catch. T001's differential cell and this absolute cell are complementary: keep BOTH.
- **(b) T004 non-fakeability hardening.** The planted-literal self-test must ALSO plant an **aliased re-import** (`import ... as _K`) and a `getattr(context, "CommitTargetKind")` form, and a **negative control**: a legit `meta["flattened"] = False` must NOT trip the guard (the surviving meta-flag is not an enum reference).
- **(c) T003 ratchet keying.** If T003 uses the ratchet form, key it on a **symbol-set** (qualname presence), not an integer `== N` count.
- **(d) Drainer naming.** The NFR-002 xfail (T002) names **WP06** as its drainer (verbatim in the `reason=`).

## Definition of Done
- T001 cell green; T002 repro xfail-strict (RED-by-design, `reason=` names WP06);
  T003 guard present (ratchet or xfail-strict, documented); T004 self-test proves
  T003 non-fakeable (incl. aliased re-import + `getattr` forms + the
  `flattened=False` negative control).
- The absolute per-topology surface cell (a) pins SINGLE_BRANCH/LANES→PRIMARY and
  COORD/LANES_WITH_COORD→coordination by value table, distinct from the differential
  cell.
- `ruff check` + `mypy` clean on the two owned files.
- The owned tests run green (xfail-strict counts as green) in
  `PWHEADLESS=1 pytest tests/missions/test_surface_resolution_equivalence.py tests/architectural/test_commit_target_kind_guard.py -q`.

## Branch Strategy
Planning/base + merge target: `feat/single-authority-topology-cleanup`. Execution
worktree is allocated per the computed lane from `lanes.json` (Lane A). Land via
the implement-review loop; do not push to `origin/main`.

## Reviewer guidance
Verify the T002 repro is genuinely RED on current code (run it without the xfail
to confirm it fails). Verify T004 proves the guard fails on a phantom. Reject if
T001 is parked behind an out-of-scope xfail or if the guard greps the `"flattened"`
string instead of resolving the symbol.

## Activity Log

- 2026-06-23T07:07:42Z – claude:opus:python-pedro:implementer – shell_pid=1292683 – Assigned agent via action command
- 2026-06-23T07:23:36Z – user – shell_pid=1292683 – WP01 implement progression
- 2026-06-23T07:23:38Z – user – shell_pid=1292683 – WP01 implement progression
- 2026-06-23T07:24:29Z – user – shell_pid=1292683 – WP01 progression to claimed
- 2026-06-23T07:24:31Z – user – shell_pid=1292683 – WP01 progression to in_progress
- 2026-06-23T07:25:01Z – claude:opus:python-pedro:implementer – shell_pid=1292683 – Ready for review: differential cell GREEN, AST guard + planted self-test, NFR-002 repro RED-by-design (xfail strict, drains in WP06)
- 2026-06-23T07:26:27Z – claude:opus:reviewer-renata:reviewer – shell_pid=1313978 – Started review via action command
- 2026-06-23T07:35:25Z – user – shell_pid=1313978 – Review passed (reviewer-renata): T001 differential GREEN + absolute anchor (classify_on_read IS topology); DoD-(a) absolute per-topology table via production routes_through_coordination, both-sided controls; T002 strict-xfail RED-for-right-reason verified via --runxfail (resolve_handle_to_read_path returns -coord husk not PRIMARY, #2062 leak, not Import/TypeError), companion red-contract test PASSES, reason names WP06; T003 AST symbol-set ratchet reuses _ratchet_keys.composite_key (no file.py:NNN, no string-grep of flattened), live=39==baseline=39 real/two-sided; T004 all planted offenders (direct/alias/getattr/serialize) bite via production discover_references + flattened=False negative control empty; 10 guard tests under -m architectural; 45 passed+1 xfailed; ruff+mypy clean; no drive-by edits beyond 2 owned files. Reviewer committed issue-matrix md-separator repair (orthogonal gate). Pre-existing marker-convention failure untouched.

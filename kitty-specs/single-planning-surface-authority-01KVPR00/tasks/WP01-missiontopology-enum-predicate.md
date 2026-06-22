---
work_package_id: WP01
title: MissionTopology enum + routes_through_coordination predicate (seam foundation)
dependencies:
- WP00
requirement_refs:
- FR-001
- FR-005
tracker_refs:
- "2069"
planning_base_branch: feat/single-planning-surface-authority
merge_target_branch: feat/single-planning-surface-authority
branch_strategy: Planning artifacts for this mission were generated on feat/single-planning-surface-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-planning-surface-authority unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "404914"
history:
- Created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/context.py
create_intent:
- tests/missions/test_mission_topology_seam.py
execution_mode: code_change
owned_files:
- src/mission_runtime/context.py
- src/specify_cli/coordination/commit_router.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/orchestrator_api/commands.py
- src/mission_runtime/artifacts.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading or writing any code, **load the `python-pedro` agent profile** (the
governed implementer identity for this WP). Read the profile YAML under the doctrine
agent-profile surface and adopt its identity, governance scope, boundaries, and the
initialization declaration. Concretely:

- Apply Pedro's implementer boundaries: implement the WP contract precisely, do not
  expand scope, do not refactor outside the five `owned_files`, and never weaken a
  guard/test to make a check pass.
- Honor the canonical-sources discipline (CLAUDE.md): use the existing
  `mission_runtime` seam and the existing `CommitTargetKind`/`CommitTarget` value
  objects; do **not** invent a parallel topology type or hand-roll a new resolver.
- Honor NFR-004: every new/changed line passes `ruff` and `mypy` with zero
  issues/warnings; cyclomatic complexity ≤15; no new S1192 (no ≥3 duplicated
  non-trivial literal). No suppression (`# noqa`, `# type: ignore`) added to pass.

Do **not** start editing until the profile is loaded and you have read the GROUND
TRUTH files listed under Context.

## Objective

Lay the **seam foundation** for the MissionTopology SSOT mission (#2069). This WP does
two things and nothing more:

1. **Name the shape (FR-001).** Add a mission-level enum
   `MissionTopology {SINGLE_BRANCH, LANES, COORD, LANES_WITH_COORD}` in
   `src/mission_runtime/context.py`, naming the orthogonal **coordination × lanes** 2×2
   grid as ONE value. `FLATTENED` is **NOT** a member of this enum — it is a separate
   historical/metadata *provenance* flag, never a shape value (a mission that was coord
   and had its `coordination_branch` dropped is now `SINGLE_BRANCH`/`LANES` + a
   `flattened` provenance mark).

2. **Introduce the shape classifier (FR-001) — the SINGLE authority that computes a
   topology from signals.** Add `classify_topology(coordination_branch: str | None,
   has_lanes: bool) -> MissionTopology` (also in `context.py`). This is **DISTINCT** from
   the per-ref predicate below: `classify_topology` maps the two orthogonal mission-level
   signals to exactly one of the four enum cells. It is the one and only place a topology
   is derived from `(coordination_branch, has_lanes)`; WP02 (mint at create + backfill +
   compute-once-persist shim), WP03 (pure resolver), and WP04 all **consume** it instead of
   re-deriving the 2×2 logic. The exhaustive truth table:

   | `coordination_branch is not None` | `has_lanes` | → `MissionTopology` |
   |-----------------------------------|-------------|---------------------|
   | `False` | `False` | `SINGLE_BRANCH` |
   | `False` | `True`  | `LANES` |
   | `True`  | `False` | `COORD` |
   | `True`  | `True`  | `LANES_WITH_COORD` |

   `FLATTENED` is **never** an output of `classify_topology` — a flattened mission (its
   `coordination_branch` was dropped) classifies as `SINGLE_BRANCH`/`LANES` **plus** a
   separate `flattened` provenance flag (see FR-001 / spec Domain Language). Do not add a
   `flattened` parameter or output here.

3. **Introduce the routing predicate (FR-005) and adopt it at the 5 decision sites this
   WP owns.** Add a per-ref predicate `routes_through_coordination(target: CommitTarget)
   -> bool` (also in `context.py`) that replaces direct `.kind is COORDINATION` reads,
   and re-express **the five `.kind is COORDINATION` branch-decision sites this WP owns**
   through it. Note the two are **orthogonal**: `classify_topology` answers the
   *whole-mission shape* from `(coordination_branch, has_lanes)`; `routes_through_coordination`
   answers the *per-ref* routing question from a `CommitTarget`. Do NOT derive one from the
   other.

This is the **seam-first** WP: WP02 (store/backfill), WP03 (pure resolver), and WP04
**depend on both `MissionTopology` existing AND `classify_topology` being the sole
shape-computing authority**, so this enum + classifier must land first and be importable
from the `mission_runtime` public surface.

### Explicit scope guard (C-007 — DO NOT over-reach)

- The `CommitTargetKind` **TYPE is NOT deleted** in this WP. Its ~143 value-literal
  references (≈63 constructions + ≈24 imports + ≈56 test refs across 41 files) are
  behavior-neutral and are **carved to Mission B (#2070)**. This WP stops **reading**
  `.kind` for **decisions** only; the `CommitTarget.kind` constructor field stays
  vestigial. Do **not** eradicate, rename, or deprecate the type, its members, or its
  constructions (e.g. the `CommitTarget(ref=..., kind=CommitTargetKind.COORDINATION)`
  constructions at `artifacts.py:123`, `orchestrator_api/commands.py:1294`,
  `implement.py:1304`, `commit_router.py` etc. stay exactly as they are).
- FR-005 spans **9** decision sites across the codebase. **This WP owns only 5 of them.**
  The other four live in files owned by sibling WPs and MUST NOT be touched here:
  `cli/commands/agent/mission.py:776,858` (WP05), `cli/commands/agent/tasks.py:359`
  (WP06), and `missions/_substantive.py:379` (WP07). Note this in the Reviewer Guidance
  so the reviewer does not flag FR-005 as incomplete in this WP.

## Context

**Read these GROUND TRUTH files before writing anything** (verify the live line numbers —
they may have drifted from the references below):

- `kitty-specs/single-planning-surface-authority-01KVPR00/spec.md` — **FR-001 verbatim**
  (the enum + `FLATTENED`-is-not-a-member contract) and **FR-005 verbatim** (the predicate
  + the 9-site list + the C-007 type-survives carve).
- `kitty-specs/single-planning-surface-authority-01KVPR00/plan.md` — **IC-01** (lines
  ~110–117); the **C-005 linearization** (`context.py` is a shared anchor — land it first)
  and the **C-007 Mission-B carve**.
- `src/mission_runtime/context.py` — the file you anchor in. Verified live structure:
  - `CommitTargetKind(enum.Enum)` at **:51** with members `PRIMARY` / `COORDINATION` /
    `FLATTENED` (do NOT change this enum).
  - `CommitTarget` frozen dataclass at **:66** with fields `ref: str`,
    `kind: CommitTargetKind` (:80–:81). This is the per-ref value the predicate accepts.
  - `ExecutionContext` frozen dataclass at **:177** (the op-composite VO; do NOT touch its
    fields — IC-03/WP03 returns it). `ActionContext = ExecutionContext` alias at :267.
  - `__all__` at **:270–:281**. You will extend it with `MissionTopology` and
    `routes_through_coordination`.
- `src/mission_runtime/__init__.py` — the public re-export surface. `CommitTarget` /
  `CommitTargetKind` are imported at **:31–:32** and listed in `__all__` at **:55–:56**.
  You will add `MissionTopology` and `routes_through_coordination` to **both** the
  `from mission_runtime.context import (...)` block (:28–:38) **and** `__all__` (:51–:68)
  so WP02/WP03 (and downstream) can `from mission_runtime import MissionTopology`.

**Verified owned decision sites** (each currently reads `placement.kind is
CommitTargetKind.COORDINATION` — confirmed by grep on 2026-06-22):

| # | File | Line | Current expression |
|---|------|------|--------------------|
| 1 | `src/specify_cli/coordination/commit_router.py` | **:118** | `use_coord = placement.kind is CommitTargetKind.COORDINATION` |
| 2 | `src/specify_cli/coordination/commit_router.py` | **:193** | `if placement.kind is CommitTargetKind.COORDINATION and target_branch:` |
| 3 | `src/specify_cli/cli/commands/implement.py` | **:604** | `if placement_ref.kind is CommitTargetKind.COORDINATION:` |
| 4 | `src/specify_cli/orchestrator_api/commands.py` | **:1283** | `if placement is not None and placement.kind is CommitTargetKind.COORDINATION:` |
| 5 | `src/mission_runtime/artifacts.py` | **:50** | `and self.commit_target.kind is CommitTargetKind.COORDINATION` (inside the `is_coordination_owned` property, guarded by a `self.commit_target is not None` check at :49) |

**Import facts** (verified): each owned file already imports `CommitTargetKind` (and
`CommitTarget`) from the `mission_runtime` surface —
`commit_router.py:33`, `implement.py:34`, `orchestrator_api/commands.py:39`,
`artifacts.py:14` (imports from `mission_runtime.context` directly, since it is in-package).
After routing through the predicate, the **decision-site** imports of `CommitTargetKind`
may become unused **in that specific use** — but each of these files **also constructs**
`CommitTarget(..., kind=CommitTargetKind.X)` elsewhere (e.g. `commit_router` materialises
coord refs, `implement.py:1304`, `orchestrator_api:1294`, `artifacts.py:123`), so the
import almost certainly stays needed. **Verify with `ruff` after editing**: if a
`CommitTargetKind` import genuinely becomes unused in a file, remove only that import line
(campsite #1970, touched lines only). Do not remove an import that is still referenced.

**Predicate design (single authority, no duplication — C-005/C-003):**

- Signature: `routes_through_coordination(target: CommitTarget) -> bool`.
- Body: a single expression — `return target.kind is CommitTargetKind.COORDINATION`.
  This is the **per-ref** projection: it answers "does THIS ref route through the
  coordination worktree?" The enum (`MissionTopology`) names the *whole-mission* shape;
  the predicate is the *per-ref* routing question (FR-005). Keep them distinct — do NOT
  try to derive the per-ref answer from `MissionTopology` in this WP (the per-ref
  `CommitTarget` is what the decision sites hold; the mission-level enum is consumed by
  WP02/WP03 to MINT/RESOLVE topology, not by these branch sites).
- Place `routes_through_coordination` directly **after** the `CommitTarget` dataclass
  definition (so it can reference the type) and **after** `CommitTargetKind` — i.e. around
  `context.py:82`. Place the `MissionTopology` enum near the other enums (after
  `CommitTargetKind` at :64, before `CommitTarget`), so the topology vocabulary is grouped.
- The predicate is the ONE place `.kind is COORDINATION` is read for a decision going
  forward; every owned site calls it. Do **not** inline a second copy of the comparison.

**`classify_topology` design (single shape authority — C-005/C-003, FR-001):**

- Signature: `classify_topology(coordination_branch: str | None, has_lanes: bool) ->
  MissionTopology`.
- Body: a small, flat 2×2 mapping (no nested branching beyond the truth table; complexity
  trivially ≤15). It is the ONE place the `(coordination_branch, has_lanes) → topology`
  derivation lives — WP02/WP03/WP04 import and call it, never re-implement the grid.
- Place it directly **after** the `MissionTopology` enum definition (so it can return the
  type), i.e. grouped with the topology vocabulary near `context.py:64`.

```python
def classify_topology(
    coordination_branch: str | None,
    has_lanes: bool,
) -> MissionTopology:
    """Map the two orthogonal mission signals to one topology cell (FR-001).

    The SINGLE authority that derives a MissionTopology from
    (coordination_branch, has_lanes). WP02/WP03/WP04 consume this — they do
    not re-implement the 2x2 grid. FLATTENED is never returned: a flattened
    mission classifies as SINGLE_BRANCH/LANES + a separate `flattened`
    provenance flag.
    """
    has_coord = coordination_branch is not None
    if has_coord and has_lanes:
        return MissionTopology.LANES_WITH_COORD
    if has_coord:
        return MissionTopology.COORD
    if has_lanes:
        return MissionTopology.LANES
    return MissionTopology.SINGLE_BRANCH
```

**MissionTopology enum design (FR-001):**

```python
class MissionTopology(enum.Enum):
    """The four mission shapes of the orthogonal coordination × lanes grid.

    Names the 2×2 cross-product as ONE stored value (#2069). FLATTENED is NOT a
    member: it is a historical/metadata provenance flag, never a shape value — a
    mission that was COORD and had its coordination_branch dropped is now
    SINGLE_BRANCH/LANES + a `flattened` provenance mark (see spec Domain Language).
    """

    SINGLE_BRANCH = "single_branch"   # no coord, no lanes
    LANES = "lanes"                   # no coord, lanes
    COORD = "coord"                   # coord, no lanes
    LANES_WITH_COORD = "lanes_with_coord"  # coord, lanes
```

(Use the value strings exactly as above so WP02's `meta.json` minting and WP03's resolver
agree on the serialized form. Confirm with WP02/WP03 authors only if a different string
casing is later required — but ship these as the canonical serialized tokens.)

## Subtasks

### T005 — Add the `MissionTopology` enum to `context.py` (FR-001)
Add the `MissionTopology` 4-member enum (above) in `src/mission_runtime/context.py`,
grouped with the existing enums (after `CommitTargetKind` at :64). Docstring MUST state
that `FLATTENED` is **not** a member and is a separate provenance flag. Do not modify
`CommitTargetKind`, `CommitTarget`, or `ExecutionContext`.

### T006 — Add the `routes_through_coordination` predicate AND the `classify_topology` shape classifier to `context.py` (FR-005 + FR-001)
Add **two** functions to `src/mission_runtime/context.py`:

1. `routes_through_coordination(target: CommitTarget) -> bool` returning
   `target.kind is CommitTargetKind.COORDINATION`, placed after the `CommitTarget`
   dataclass. Docstring states it is the **single per-ref routing authority** replacing
   direct `.kind is COORDINATION` decision reads, and that the `CommitTargetKind` type
   itself survives (vestigial) until Mission B (#2070).
2. `classify_topology(coordination_branch: str | None, has_lanes: bool) ->
   MissionTopology` (body + docstring per the **`classify_topology` design** block in
   Context), placed directly after the `MissionTopology` enum. This is the **single
   shape-computing authority**: the ONE place `(coordination_branch, has_lanes)` is mapped
   to a topology cell per the 2×2 truth table. WP02/WP03/WP04 consume it; it never re-derives
   per-ref routing and it never returns `FLATTENED`. Keep it distinct from
   `routes_through_coordination` — the two answer orthogonal questions.

### T007 — Export all three new symbols from the `mission_runtime` public surface
Extend `src/mission_runtime/context.py` `__all__` (:270–:281) and
`src/mission_runtime/__init__.py` (both the `from mission_runtime.context import (...)`
block at :28–:38 **and** `__all__` at :51–:68) with `MissionTopology`,
`classify_topology`, and `routes_through_coordination`. Keep `__all__` alphabetically
sorted to match the existing convention. WP02/WP03/WP04 depend on
`from mission_runtime import MissionTopology, classify_topology` resolving.

### T008 — Route the 5 owned decision sites through the predicate (FR-005)
Re-express each of the five verified sites to call `routes_through_coordination(<target>)`
instead of reading `.kind is CommitTargetKind.COORDINATION`. Import the predicate from the
`mission_runtime` surface (or `mission_runtime.context` for the in-package `artifacts.py`):

- `commit_router.py:118` → `use_coord = routes_through_coordination(placement)`
- `commit_router.py:193` → `if routes_through_coordination(placement) and target_branch:`
- `implement.py:604` → `if routes_through_coordination(placement_ref):`
- `orchestrator_api/commands.py:1283` →
  `if placement is not None and routes_through_coordination(placement):`
- `artifacts.py:50` → inside `is_coordination_owned`, replace the `.kind is ...COORDINATION`
  term with `routes_through_coordination(self.commit_target)` (the `self.commit_target is
  not None` guard at :49 already narrows the type for mypy; keep it).

After editing, run `ruff check` on the five files: if a `CommitTargetKind` import is now
genuinely unused in a file, remove that single import line; otherwise leave imports intact
(every owned file also CONSTRUCTS `CommitTarget(..., kind=...)`, so the import is expected
to remain). **Do not touch the `CommitTarget(...)` constructions** (C-007).

### T009 — Add a focused, non-fakeable unit test for the seam
Add `tests/missions/test_mission_topology_seam.py` (new test file) that:
1. **Enum cells (FR-001):** asserts `MissionTopology` has exactly the four members
   `{SINGLE_BRANCH, LANES, COORD, LANES_WITH_COORD}` and that there is **no** `FLATTENED`
   member (`assert not hasattr(MissionTopology, "FLATTENED")`). Assert the four serialized
   `.value` strings (so WP02/WP03 are pinned to the agreed wire form).
2. **Predicate truth table (FR-005):** parametrized over the per-ref `CommitTargetKind`
   cells — `routes_through_coordination(CommitTarget("r", CommitTargetKind.COORDINATION))
   is True`; `... PRIMARY) is False`; `... FLATTENED) is False`. (This is the per-ref 2×2
   routing answer the decision sites depend on.)
3. **Classifier truth table (FR-001):** parametrized over the **full 2×2 grid** of
   `(coordination_branch, has_lanes)` — all four cells asserted:
   - `classify_topology(None, False) is MissionTopology.SINGLE_BRANCH`
   - `classify_topology(None, True)  is MissionTopology.LANES`
   - `classify_topology("<real coord branch ref>", False) is MissionTopology.COORD`
   - `classify_topology("<real coord branch ref>", True)  is MissionTopology.LANES_WITH_COORD`

   Use a production-shaped coordination branch ref for the `is not None` cells (e.g. a
   `kitty/mission-<slug>-<mid8>-coord`-style string), NOT a bare placeholder, so the test
   exercises the real "branch present" signal. This is the non-fakeable proof that
   `classify_topology` is the single authority mapping signals → the correct enum cell, and
   that `FLATTENED` is never produced.
4. **Public-surface import (T007):** asserts `from mission_runtime import MissionTopology,
   classify_topology, routes_through_coordination` resolves (so WP02/WP03/WP04 can import
   them).

Use production-shaped values (real-format refs/branch names, not `"r"` placeholders) where
the assertion meaningfully exercises them — at minimum a realistic branch ref string for
the `CommitTarget.ref`. The predicate test is the non-fakeable proof that the predicate
returns the right bool for each routing cell.

## Branch Strategy

Planning artifacts for this mission were generated on `feat/single-planning-surface-authority`.
During `/spec-kitty.implement`, this WP may branch from a dependency-specific base (it
depends on WP00, the test-only ratchet re-key), but completed changes MUST merge back into
`feat/single-planning-surface-authority` unless the human explicitly redirects the landing
branch. This is the **first seam WP** of the linearized chain
(WP00 → WP01 → WP02 → WP03 → …); land `context.py` cleanly before the dependents branch.

## Definition of Done

Each item is verifiable by a reviewer with a single command — no "looks done" claims.

1. **Enum exists and excludes FLATTENED.**
   `python -c "from mission_runtime import MissionTopology; print(sorted(m.name for m in
   MissionTopology))"` prints exactly
   `['COORD', 'LANES', 'LANES_WITH_COORD', 'SINGLE_BRANCH']`, and
   `python -c "from mission_runtime import MissionTopology; assert not
   hasattr(MissionTopology,'FLATTENED')"` exits 0.
2. **Predicate exists and is correct.** The new unit test
   `tests/missions/test_mission_topology_seam.py` passes, including the truth-table
   asserting `routes_through_coordination` returns `True` only for `COORDINATION` and
   `False` for `PRIMARY`/`FLATTENED`.
2a. **Classifier exists and is the single shape authority.** The same unit test pins the
   **full 2×2 truth table** for `classify_topology`: all four cells of
   `(coordination_branch, has_lanes)` map to `SINGLE_BRANCH` / `LANES` / `COORD` /
   `LANES_WITH_COORD` respectively, and `FLATTENED` is never returned. WP02/WP03/WP04
   consume `classify_topology` rather than re-deriving the grid.
3. **All three symbols are on the public surface.**
   `python -c "from mission_runtime import MissionTopology, classify_topology,
   routes_through_coordination"` exits 0; all three appear in `mission_runtime.__all__` and
   `mission_runtime.context.__all__`.
4. **All 5 owned sites no longer read `.kind` to decide.**
   `grep -rn "\.kind is CommitTargetKind.COORDINATION" src/specify_cli/coordination/commit_router.py
   src/specify_cli/cli/commands/implement.py src/specify_cli/orchestrator_api/commands.py
   src/mission_runtime/artifacts.py` returns **zero** matches. (The CONSTRUCTIONS
   `kind=CommitTargetKind.COORDINATION` may still appear and MUST be left intact — only the
   `.kind is ...COORDINATION` **decision reads** are gone.)
5. **The `CommitTargetKind` type is untouched (C-007).**
   `git diff` shows no change to the `CommitTargetKind` enum definition, its members, or any
   `CommitTarget(...)` construction; `grep -rn "class CommitTargetKind" src/` still resolves
   to `context.py`. The four sibling-owned decision sites (`mission.py:776,858`,
   `tasks.py:359`, `_substantive.py:379`) are NOT touched.
6. **Static analysis clean (NFR-004).** `ruff check .` and `mypy` on the five owned files
   report zero issues/warnings on changed lines; complexity ≤15; no new S1192; no
   suppression added.
7. **Suite green for the touched surface.**
   `PWHEADLESS=1 pytest tests/missions/test_mission_topology_seam.py -q` passes, and the
   existing coordination/commit-router and artifacts tests still pass
   (`PWHEADLESS=1 pytest tests/ -k "commit_router or artifacts or implement" -q`).
8. **Campsite discipline (#1970).** Only the lines required for the enum, predicate,
   exports, the 5 site edits, and any now-dead import are changed — no unrelated reflow.

## Risks

- **R1 — Over-reach into Mission B (TOP).** The temptation is to "finish" FR-005 by
  eradicating `CommitTargetKind` or routing all 9 sites. This WP owns **5** sites and must
  **leave the type and all constructions intact** (C-007). Routing a sibling-owned site
  (`mission.py`/`tasks.py`/`_substantive.py`) is an ownership violation that `finalize-tasks`
  will flag — do not touch them.
- **R2 — Predicate/enum conflation.** `MissionTopology` (whole-mission shape) and
  `routes_through_coordination` (per-ref routing) answer different questions. Do NOT derive
  the per-ref bool from the enum; the decision sites hold a `CommitTarget`, so the predicate
  keys on `target.kind`. Conflating them couples this WP to WP02/WP03's stored value
  prematurely.
- **R3 — Dead-import false positive.** After routing, a `CommitTargetKind` import may *look*
  unused but is still referenced by a `CommitTarget(...)` construction in the same file.
  Trust `ruff`, not eyeballing — remove an import only when `ruff` reports F401.
- **R4 — Wire-form drift.** WP02 mints `topology` into `meta.json` and WP03 resolves it
  using `MissionTopology(...)`. If the `.value` strings here differ from what those WPs
  expect, the round-trip breaks. T009 pins the four serialized values so any later drift is
  caught by a red test, not a silent mismatch.
- **R5 — Line drift vs the cited references.** The line numbers above were verified
  2026-06-22 but WP00 (the dependency) is test-only and should not move these `src/` lines;
  still, re-grep `\.kind is CommitTargetKind.COORDINATION` in each owned file before editing
  and cite the live line in your implementation notes.

## Reviewer Guidance

- **FR-005 is intentionally partial in this WP.** Confirm exactly **5** decision sites were
  routed (the table in Context). The remaining 4 (`agent/mission.py:776,858` → WP05,
  `agent/tasks.py:359` → WP06, `_substantive.py:379` → WP07) are owned by sibling WPs and
  MUST be absent from this diff. Do **not** reject for "missed sites" — FR-005 spans WPs.
- **Verify the type survives (C-007).** Reject if the diff deletes/renames `CommitTargetKind`
  or any of its members, or touches a `CommitTarget(..., kind=CommitTargetKind.X)`
  construction. The type is vestigial-by-design here; eradication is Mission B (#2070).
- **Verify the predicate is the single authority.** There should be exactly ONE
  `target.kind is CommitTargetKind.COORDINATION` comparison left in `src/` for routing — the
  one inside `routes_through_coordination`. Confirm the 5 sites all call the predicate and
  none re-inline the comparison.
- **Verify FLATTENED is not an enum member.** It is a provenance flag (per spec Domain
  Language); a `MissionTopology.FLATTENED` member is a spec violation (FR-001) — reject.
- **Verify `classify_topology` exists and is the single shape authority (FR-001).** Reject
  if it is missing. It must map `(coordination_branch, has_lanes)` to the four enum cells
  per the 2×2 truth table, must NOT return `FLATTENED`, and must NOT take a `flattened`
  parameter. Confirm it is distinct from `routes_through_coordination` (whole-mission shape
  vs per-ref routing) and that WP02/WP03/WP04 are expected to consume it rather than
  re-deriving the grid. Reject if the WP re-implements the 2×2 logic anywhere else.
- **Verify the public export.** `from mission_runtime import MissionTopology,
  classify_topology, routes_through_coordination` must resolve — WP02/WP03/WP04 are blocked
  otherwise.
- **Verify the test is non-fakeable.** The predicate truth-table test must assert the
  predicate's bool per routing cell (not just "it runs"); the **classifier truth-table test
  must assert all four `(coordination_branch, has_lanes)` cells** map to the correct enum
  member (and that `FLATTENED` never appears); the enum test must assert the absence of
  `FLATTENED` and the four `.value` strings.
- **Static analysis & campsite.** `ruff`/`mypy` clean on changed lines; complexity ≤15; no
  new S1192; only touched lines changed (#1970).

## Activity Log

- 2026-06-22T14:55:01Z – claude:opus:python-pedro:implementer – shell_pid=376465 – Assigned agent via action command
- 2026-06-22T15:08:34Z – claude:opus:python-pedro:implementer – shell_pid=376465 – WP01 IMPLEMENTATION COMPLETE + VERIFIED (commit cec75f2b6). MissionTopology enum (4 cells, no FLATTENED) + classify_topology (2x2 single authority) + routes_through_coordination predicate in src/mission_runtime/context.py; all three exported from mission_runtime. 5 owned decision sites routed (commit_router x2, implement, orchestrator_api, artifacts); CommitTargetKind import dropped only from commit_router (genuinely unused there). 4 sibling sites (mission.py/tasks.py/_substantive.py) untouched per WP05/06/07 ownership. tests/missions/test_mission_topology_seam.py: 15 passed. ruff exit 0, mypy exit 0, C901 clean. Related sweep 605 passed; 2 pre-existing gitignore-contract failures (test_intake, test_gitignore_contract) reproduce on clean lane base - unrelated to WP01. BLOCKED on move-task->for_review: lane-b is 55 commits behind / 12 ahead of feat/single-planning-surface-authority; the divergent history is the full mission planning-artifact + status chain (git cherry shows all 12 lane commits as not-in-base by patch-id, incl WP00 code commit 37e4e0a7e). Rebase hits add/add conflict on planning artifact kitty-specs/.../spec.md. This is flat-mission lane-loop topology friction, NOT a code defect; a full-history rebase would rewrite WP00's approved commit + shared planning chain (high-risk). Escalating rather than forcing a destructive rewrite. Operator decision needed: --force the move, or reconcile lane-b base with the advanced planning base at orchestration level.
- 2026-06-22T15:12:16Z – claude:opus:python-pedro:implementer – shell_pid=376465 – WP01 code complete+verified (commit cec75f2b6): enum+predicate+classify_topology, 5 sites routed, 15 tests green, ruff/mypy clean. --force: lane-b base is the stale mission-branch (pre-#2081); all 6 WP01 source files are IDENTICAL between lane base and feat/ (diff is self-contained, conflict-free) — base divergence is a merge-time reconciliation item, not a code conflict.
- 2026-06-22T15:12:28Z – claude:opus:reviewer-renata:reviewer – shell_pid=404914 – Started review via action command
- 2026-06-22T15:19:28Z – user – shell_pid=404914 – APPROVED cycle 1 (--force across KNOWN-BENIGN base divergence): MissionTopology enum (4 cells, no FLATTENED) + classify_topology 2x2 single authority + routes_through_coordination predicate; 5 owned sites routed, 4 sibling sites + CommitTargetKind type untouched (C-007). Seam test non-fakeability PROVEN by mutation (inverted mapping -> 2 red). ruff/mypy clean, 605 passed, 2 pre-existing failures (untouched intake/gitignore). lane-b base is stale pre-#2081 branch but all 6 WP01 source files identical to feat/ -> conflict-free; rebase avoided (high-risk), base reconciliation is merge-time.

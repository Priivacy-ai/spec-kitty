---
work_package_id: WP03
title: Extract the terminal assembler, then delegate the wrapper
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
- FR-021
- FR-024
- NFR-001
- NFR-002
- NFR-003
- NFR-009
planning_base_branch: fix/read-side-seam-primary-primitive-closure
merge_target_branch: fix/read-side-seam-primary-primitive-closure
branch_strategy: Planning artifacts for this mission were generated on fix/read-side-seam-primary-primitive-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/read-side-seam-primary-primitive-closure unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
- T021
phase: Phase 2 - Delegate
history:
- at: '2026-07-28T09:27:08Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/_read_path_resolver.py
create_intent:
- tests/specify_cli/missions/test_primary_read_delegation.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/missions/_read_path_resolver.py
- src/mission_runtime/resolution.py
- tests/architectural/test_single_mission_surface_resolver.py
- tests/specify_cli/missions/test_read_path_resolver_validation.py
- tests/specify_cli/missions/test_primary_read_delegation.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Extract the terminal assembler, then delegate the wrapper

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---


## Objective

Two strictly ordered halves in one WP, because the boundary between them is the mission's
most dangerous sequencing gate and putting it inside a single WP means it cannot be crossed by
accident.

**Half A (T015–T018) — extract.** Split the pure `KITTY_SPECS_DIR` assembly out of
`primary_feature_dir_for_mission` into a module-private leaf, and re-point the seam's own
PRIMARY leg plus the resolver-internal callers at that leaf. **Zero call-site changes.**

**Half B (T019–T021) — delegate.** Make the (now assembly-free) public wrapper resolve through
the kind-aware seam internally. Call sites remain untouched, so the **existing suite is the
harness**: every behavioural difference across all 34 sites surfaces at once, attributably, at
one file's cost.

## ⚠ Why Half A exists at all — read this before writing any code

The seam reaches the primitive **through its own PRIMARY leg**:

```text
read_dir → resolve_artifact_surface → resolve_planning_read_dir → primary_feature_dir_for_mission
```

So making `primary_feature_dir_for_mission` call `read_dir(...)` **without** first extracting
the assembler is an **infinite recursion**, not a refactor (Ledger M16). `RecursionError` after
delegation is the **highest-priority stop** in this WP: it means Half A did not fully cover
the PRIMARY leg. Do not work around it by adding a guard flag or a recursion depth check —
find the uncovered path.

`resolve_planning_read_dir`'s PRIMARY leg *is* the composition the 33 semi-compliant sites
hand-inline. They are not choosing a different answer; they are duplicating the resolver's body
and keeping the decision in the caller. That is why delegation is answer-preserving.

## Why WP01 must land first

Half A re-points the **4 `resolution.py` callers** off the primitive. That alone drops the
scanned count (46 → 42), below the recorded 44 floor. The extraction would red a gate WP01
retires. Confirm before starting: `test_resolution_authority_gates.py` no longer contains the
two use-count floors.

## Context & Constraints

- **C-005 Step 0 / Step 1** — the sequence is extract → delegate → remove. Removal is WP08's.
- **NFR-001** — behaviour-preserving except **one named delta**: the seam's bare-`<slug>`
  **backfill recovery**. Every routed read must resolve an identical directory for a
  materialized, non-backfilled mission.
- **NFR-002** — no new raises where leniency is the contract. A PRIMARY kind must not begin
  raising on a husk, an empty coord worktree, or a deleted coord branch. `read_dir()` raises
  only for a **COORD** kind on a coord-routing topology whose branch is deleted — so routing a
  PRIMARY kind cannot introduce a raise. If you observe one, that is a real regression.
- **NFR-003** — red-first per behavioural change, verified by reverting the product file.
- **NFR-009** — no cycle in the `read_dir` call graph.
- **All PRIMARY kinds resolve to the same anchor**, which is why Half B can delegate using a
  *single* PRIMARY kind and stay answer-equivalent for every caller. If you find you cannot
  honestly pick one value, that itself is evidence the decision belongs to the caller — stop
  and report it rather than inventing a parameter.

## Doctrine for this WP

- **`tactic:refactoring-change-function-declaration`** — **this WP is that tactic.** "Have the
  old function call the new one internally… migrate callers one by one… remove the old function
  when no callers remain", selected "when the function is public API or has many callers".
  `Run: spec-kitty charter context --include tactic:refactoring-change-function-declaration`
  **When doing T019**, follow its sequence literally; do not improvise a variant.
- **`DIRECTIVE_025` (boy-scout / campsite)** — the licence **and the bound** for Half A: clean
  the surface first, as a **distinct preceding step**, behaviour-preserving, scoped to surfaces
  this mission touches. `Run: spec-kitty charter context --include directive:DIRECTIVE_025`
  **When doing T015**, keep the extraction purely structural — resist "while I'm here"
  behavioural improvements. A behavioural change hidden in Half A destroys Half B's evidence.
- **`DIRECTIVE_034` (test-first)** — a red must manifest in an **assertion** about behaviour,
  not as a missing symbol at collection.
  `Run: spec-kitty charter context --include directive:DIRECTIVE_034`
  **When doing T017** — this is the exact hazard: the import-time content descriptor errors
  ~30 tests at collection if it is not re-authored **in the same commit** as T015.
- **`tactic:tdd-red-green-refactor`** / **`DIRECTIVE_041`** — for T020's pin: write the failing
  test first, verify it fails by reverting the product file.
  `Run: spec-kitty charter context --include directive:DIRECTIVE_041`
  **When doing T020**, the backfill-recovery delta must be **pinned by a test**, never absorbed
  silently — an absorbed delta is indistinguishable from a bug next quarter.
- **`tactic:architectural-gate-non-vacuity`** — for T021: a stub that is never reached makes its
  harness **vacuously green**.
  `Run: spec-kitty charter context --include tactic:architectural-gate-non-vacuity`
  **When doing T021**, "the fixture still passes" is not evidence — prove the stubs are still
  reached.

## Subtasks

### T015 — Extract the terminal `KITTY_SPECS_DIR` assembler into a module-private leaf (FR-021)

**Purpose**: give the resolver a terminal path constructor that does **not** go through the
public wrapper, so the wrapper can later delegate without recursing.

**Steps**:
1. Identify the pure assembly inside `primary_feature_dir_for_mission`: the
   `KITTY_SPECS_DIR`-rooted join. It is pure — repo root + handle → directory, no probing.
2. Extract it to a module-private leaf in `_read_path_resolver.py`. Keep it a **leaf**: no
   coordination probing, no topology awareness, no seam import. It is L3 assembly.
3. Re-point the **7 in-module callers** of the primitive at the leaf (census shows 7 sites in
   `_read_path_resolver.py`).
4. This leaf is **permanent** (C-004) and the sanctioned owner of that path assembly under a
   separate architectural gate — never delete it.
5. **Private by convention, not unreachable.** SC-001's end state is *"the private assembler has
   only in-module **and named-sanctioned** callers"* — cross-module sanctioned callers are
   anticipated. The **four FR-005 foundation sites** (`core/paths.py` ×2, `core/git_ops.py`,
   `coordination/surface_resolver.py`) import the **public wrapper** today and WP08 deletes it,
   so they must end up importing this leaf. WP07 T034 re-points them; keep the leaf importable
   for exactly those four, and do **not** add it to `__all__`.

**Files**: `src/specify_cli/missions/_read_path_resolver.py`.
**Validation**: no behaviour change; the leaf has no imports from `mission_runtime`.

### T016 — Re-point the seam's PRIMARY leg and the resolver-internal callers (FR-021, NFR-009)

**Purpose**: break the recursion path before it can exist.

**Steps**:
1. Re-point `resolve_planning_read_dir`'s **PRIMARY leg** at the new leaf.
2. Re-point the **4 internal callers** in `src/mission_runtime/resolution.py` at the leaf
   (census: 4 sites; the cycle legs are around `:426`, `:755`, `:801`, `:995`).
3. Verify **no path** from `read_dir` reaches the public wrapper. Trace it explicitly:
   `read_dir` → `resolve_artifact_surface` → `resolve_planning_read_dir` → *leaf*. Write the
   trace into the commit body — this is the evidence that Half B is safe.
4. Confirm no new cycle (NFR-009).

**Files**: `src/mission_runtime/resolution.py`, `src/specify_cli/missions/_read_path_resolver.py`.

### T017 — Re-author the import-time content descriptor onto the leaf (Ledger M4)

**Purpose**: `tests/architectural/test_single_mission_surface_resolver.py` pins, **at import
time**, that the primitive's body still holds that exact raw join under that exact qualname.
T015 moves the body → the descriptor no longer matches → **collection ERROR for ~30 tests**,
which reads as collateral damage and will be misattributed.

**Steps**:
1. Re-author the `ContentDescriptor` onto the **post-extraction leaf** — the new qualname, the
   same raw join. **In the same commit as T015/T016.**
2. Note that the descriptor's subject survives WP08: the *wrapper* is deleted, the *leaf*
   remains. So this is a one-time re-author, not a two-step. Do not build in a transitional
   fallback.

**Validation**: `uv run pytest tests/architectural/test_single_mission_surface_resolver.py -q`
**collects cleanly**. Zero collection errors is the bar (`DIRECTIVE_034`).

### T018 — Prove the extraction behaviour-neutral (SC-018)

**Purpose**: Half B's evidence is only meaningful if Half A changed nothing.

**Steps**:
1. **Zero call-site changes** outside the two resolver modules. `git diff --stat` must show
   only the owned files.
2. **Re-derive both canonicalizer counts** with the census recipe in
   [quickstart.md](../quickstart.md) §1 and record them. WP01 retired the gate that used to
   assert this, so SC-003's evidence is now yours to produce by census rather than by gate.
   State the before/after integers in the commit body.
3. A PRIMARY-kind read through the seam completes **without recursion**.
4. Run the mission's behaviour-preservation suites:
   `tests/merge/ tests/specify_cli/coordination/ tests/specify_cli/status/`.

**Validation**: commit Half A **separately** from Half B. A reviewer must be able to see the
extraction land green (modulo WP01/WP02's recorded expected reds) before the delegation.

### T019 — Delegate the public wrapper to the seam (FR-002)

**Purpose**: prove equivalence in production and surface the hidden delta at one file's cost.

**Steps**:
1. Change **only the public wrapper's body**. The leaf from T015 stays untouched.
2. Delegate to `placement_seam(...).read_dir(<a single PRIMARY kind>)` — legitimate because all
   PRIMARY kinds resolve to the same anchor.
3. **Do not touch a single call site.** That is what makes the existing suite a valid harness.

**Files**: `src/specify_cli/missions/_read_path_resolver.py` (wrapper body only).
**Validation**: `RecursionError` anywhere → stop, return to T016, find the uncovered leg.

### T020 — Attribute every divergence; pin backfill recovery red-first (FR-003, NFR-003)

**Purpose**: convert "we believe these are equivalent" into recorded evidence, and document
the one real delta rather than absorbing it.

**Every** divergence must be attributed to exactly one of four causes: **anchoring** /
**backfill recovery** / **husk** / **raising**. Expected outcomes, per the eight real-repo
fixtures in [quickstart.md](../quickstart.md) §4:

| Fixture | Expect |
|---|---|
| flat / `SINGLE_BRANCH`, no coord | equal |
| coord + materialized worktree | equal |
| coord + **husk** (worktree present, no `meta.json`) | equal; PRIMARY resolves the primary anchor, **does not raise** |
| coord branch **deleted** | equal, no raise for a PRIMARY kind (a COORD kind raises — correctly) |
| coord worktree **empty** (create window) | equal, no raise |
| mission absent entirely | equal |
| `repo_root` = a lane worktree | equal (both CWD-invariant) |
| **backfilled** (bare `<slug>` primary, composed `<slug>-<mid8>` coord) | **differs — the seam recovers the existing dir; the blind composition returned a path that does not exist** |

**Steps**:
1. Write `tests/specify_cli/missions/test_primary_read_delegation.py` pinning the
   backfill-recovery delta **red-first** — verify it fails by reverting the wrapper body
   (NFR-003).
2. Also pin the husk case explicitly: a PRIMARY-kind read on a husk mission resolves the
   primary anchor and does **not** raise.
3. There is a **latent shape** at `status/aggregate.py:543`'s `.name`-derived handle, whose
   value is the *composed* form on a backfilled mission. It is latent today behind a
   short-circuit. Record it here; WP07 discharges it.
4. Build fixtures under the **session scratchpad**, not a bare `/tmp` path, and remove any
   throwaway worktree afterwards.

**Validation**: every divergence has a named cause in writing; backfill recovery is the only
**accepted** behavioural delta and it is pinned.

### T021 — Hand-verify the Class-C patch fixture did not go vacuously green

**Purpose**: this is the mission's subtlest hazard and it is silent.

A module-wide fixture stubs **four** resolver names *because* the PRIMARY leg calls them
internally. T016 re-points that leg → **the stubs become unreached** → the convergence harness
may pass while testing nothing. "The fixture still passes" is therefore not evidence.

**Steps**:
1. The fixture is **`tests/specify_cli/cli/commands/test_coord_status_commit_2155.py::_install_distinguishable_topology`**
   (~:100). It stubs five resolver names on `_read_path_resolver` — including
   `primary_feature_dir_for_mission` and `_canonicalize_primary_read_handle` — and its own inline
   comment says *"PRIMARY-partition leg of `resolve_planning_read_dir` composes via this
   primitive"*. That is exactly the leg T016 re-points, so that stub becomes unreached. Its
   docstring already names the hazard: *"A stub returning the SAME dir for both under coord
   topology would make the convergence assertion vacuous (constant-stub rejection)."*
2. Prove the stubs are still **reached**: assert on the stub (call count / side effect), or
   deliberately break a stub and confirm the harness reds.
3. If they are genuinely unreached, the harness is now vacuous — **re-point it at the real
   seam** rather than deleting it or leaving it green (`DIRECTIVE_041`: a green test that would
   stay green if the code regressed provides no coverage).
4. A separate negative patch asserts that a specific kind **never** routes through the planning
   resolver — confirm the extraction does not trip it.

**Validation**: state in writing, for each of the four stubs, whether it is still reached and
what you did about it.

## Branch Strategy

- Planning/base branch: **`fix/read-side-seam-primary-primitive-closure`**
- Final merge target: **`fix/read-side-seam-primary-primitive-closure`**
- Claim and prepare the workspace with the canonical entry point:
  `spec-kitty agent action implement WP03 --agent <name>`
- Worktree allocated **per computed lane** from `lanes.json` by that command.
  Never hand-construct it; never `git stash` inside a lane worktree.

## Test Strategy

```bash
# Half A, then Half B — separate commits, separate runs
PWHEADLESS=1 SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 uv run pytest \
  tests/architectural/test_single_mission_surface_resolver.py \
  tests/specify_cli/missions/ -q
PWHEADLESS=1 SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 uv run pytest \
  tests/merge/ tests/specify_cli/coordination/ tests/specify_cli/status/ -q
```

Plus the six C-008 gates (tasks.md §5), `uv run ruff check <changed>`, and project-mode
`uv run python -m mypy --strict src/specify_cli src/charter src/doctrine`.

## Definition of Done

- Half A committed **separately** from Half B, in that order.
- The leaf is module-private, pure, and has no `mission_runtime` import (T015).
- The `read_dir` → leaf trace is written into the commit body; **no** path from `read_dir`
  reaches the public wrapper; no new cycle (T016, NFR-009).
- The content descriptor is re-authored onto the leaf in the **same commit**; that module
  collects cleanly (T017).
- Zero call-site changes; both canonicalizer counts re-derived and recorded with before/after
  (T018, SC-018, SC-003).
- The wrapper delegates; **no `RecursionError`** anywhere (T019).
- Every divergence attributed in a **named artifact** — append a `## WP03` section to
  `kitty-specs/read-side-seam-primary-primitive-closure-01KYKMMT/research/expected-reds.md`
  listing each divergence and its cause (anchoring / backfill recovery / husk / raising).
  "In writing" with no location is not reviewable. Backfill recovery pinned **red-first**,
  verified by reverting the product file; husk case pinned (T020).
- The four Class-C stubs each have a written reached / not-reached verdict and a resolution
  (T021).
- `ruff` and project-mode `mypy` clean.
- Finish: commit, `spec-kitty agent tasks mark-status T015 T016 T017 T018 T019 T020 T021 --status done`, then
  `spec-kitty agent tasks move-task WP03 --to for_review` and **wait** for the synchronous pre-review gate.

## Risks

- **`RecursionError` is the highest-priority stop.** It means Half A is incomplete. Never mask
  it with a guard flag or a depth counter.
- **A behavioural change smuggled into Half A destroys Half B's evidence.** Keep the extraction
  purely structural (`DIRECTIVE_025`'s bound).
- **Collection errors, not assertion failures**, are how T017's hazard presents — ~30 tests at
  once, twice over if you also rename.
- **The Class-C fixture can go silently green.** Passing is not evidence.
- If you cannot honestly pick one PRIMARY kind for the delegation, **stop and report** — that
  is evidence the decision belongs to the caller, which is a plan-level finding, not something
  to paper over with a parameter.

## Reviewer Guidance

1. Are Half A and Half B **separate commits**, with Half A demonstrably behaviour-neutral?
2. Is the `read_dir` → leaf trace written down, and does it actually hold when you follow it in
   the code?
3. Is the backfill-recovery pin **red-first**? Revert the wrapper body yourself and confirm the
   test fails.
4. For each of the four Class-C stubs: is there a written reached/not-reached verdict, with
   evidence rather than "the fixture passes"?
5. Are the re-derived canonicalizer counts in the commit body, given WP01 removed the gate that
   used to assert them?
6. Zero call-site changes outside the two resolver modules — check `git diff --stat`.

## Activity Log

> **CRITICAL**: entries MUST be chronological — **append** new entries at the END, never
> prepend or insert. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`, timestamp in
> UTC (`date -u "+%Y-%m-%dT%H:%M:%SZ"`). The acceptance system reads the LAST entry as the
> current state, so out-of-order entries fail acceptance even when the work is complete.

- 2026-07-28T09:27:08Z – system – Prompt created.

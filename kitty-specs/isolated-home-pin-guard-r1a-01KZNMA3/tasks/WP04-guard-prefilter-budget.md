---
work_package_id: WP04
title: 'The guard: eight transitions, the exemption mechanism, the pre-filter proof, and the budget'
dependencies:
- WP02
requirement_refs:
- FR-002
- FR-004
- FR-007
- FR-009
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- C-002
- C-003
- C-006
- C-007
- C-013
planning_base_branch: feat/isolated-home-pin-guard
merge_target_branch: feat/isolated-home-pin-guard
branch_strategy: Planning artifacts for this mission were generated on feat/isolated-home-pin-guard. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/isolated-home-pin-guard unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
- T021
history: []
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/_home_pin_synthetic.py
- tests/architectural/test_home_pin_synthetic_trees.py
- tests/architectural/test_spec_kitty_home_pin_guard.py
- tests/architectural/test_spec_kitty_home_pin_prefilter.py
- tests/architectural/test_spec_kitty_home_pin_budget.py
execution_mode: code_change
owned_files:
- tests/architectural/_home_pin_synthetic.py
- tests/architectural/test_home_pin_synthetic_trees.py
- tests/architectural/test_spec_kitty_home_pin_guard.py
- tests/architectural/test_spec_kitty_home_pin_prefilter.py
- tests/architectural/test_spec_kitty_home_pin_budget.py
role: implementer
tags: []
task_type: code-implementation
tracker_refs: []
---

# Work Package Prompt: WP04 (alias WP-b) – The guard: eight transitions, the exemption mechanism, the pre-filter proof, and the budget

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

> ## ⛔ PRECONDITION — CHECK IT, DO NOT ASSUME IT
>
> Before the first subtask: **`tests/architectural/test_home_pin_gate_verdict.py` is present and GREEN in
> this lane's worktree** (`worktree_allocator.py:462-472` degrades to a printed warning if the dependency
> branch is unresolvable, **so this is checked**).

## Objective

Ship the guard's mechanism — the synthetic-tree materialiser and its **collected** correctness home, the eight
SC-006 transitions red-first, SC-004, SC-013, the synthetic outermost-versus-innermost witness, the `E`
mechanism over materialised artefacts, the pre-filter differential at NFR-002's strength, and the `timing`-only
budget module. **This WP is green on its own branch without WP03 and without WP05.**

## Context

- **Plan concerns**: IC-04 (the guard, the exemption set, the eight transitions), IC-05 (the pre-filter's proof
  obligations), IC-08 (CI landing).
- **Why this WP is parallel with WP03.** The real-tree `discovered == census ∪ E` assertion is deliberately
  **not here** — it lives in WP05. That is what buys the parallelism, and it is what FR-009's root parameter
  exists to enable. Everything here runs over **materialised** trees and **materialised** exempt artefacts.
- **This is the largest WP (7 subtasks) and will attract scrutiny automatically because it is where the code
  is.** Plan §10 notes the corollary: WP05 will not, and that is where the one assertion proving the class is
  frozen lives. Do not move work there.
- **No precedent exists for an executable pre-filter proof in this repository.** Both shipping byte
  pre-filters (`_sole_door_scan.py:461-476`, `test_commit_target_kind_guard.py:186-188`) argue soundness in a
  comment and prove nothing. **R1a sets the precedent.**

---

### Subtask T015: `_home_pin_synthetic.py` plus its COLLECTED home — materialised trees, never checked in

**Purpose**: FR-009's root parameter is what makes this possible. Build the materialiser and prove it
**where the proof actually runs**.

**Steps**:

1. Create `tests/architectural/_home_pin_synthetic.py`: a materialiser writing trees into `tmp_path` **from
   source STRINGS**.
2. **Its correctness is proven, not assumed, IN A COLLECTED MODULE.** `pytest.ini` sets `testpaths = tests`
   with **no `python_files` override**, so **`_home_pin_synthetic.py` is NEVER COLLECTED** and assertions
   placed there **would never run**. They live in `test_home_pin_synthetic_trees.py`.
3. For **each named tree**, `discover(root=<materialised>)` returns a member key set **EQUAL** to the
   enumerated set the tree was built to contain, so a tree that **silently fails to write a file** reds here
   instead of greening a transition downstream.
4. A **counterpart assertion** proves `discover(Path("tests"))` finds **NO member under any test-owned fixture
   root**.
5. **NOTHING is checked in under `tests/`**:
   - a checked-in tree sits inside the classifier's never-narrowed walk, so its deliberate 41st members land
     in `discovered` and `discovered == census ∪ E` **can never green**;
   - a checked-in deliberate `SyntaxError` **reds `ruff check` with `invalid-syntax`**, which is **not a rule
     code** and **cannot be per-file-ignored**.
6. All materialised sources are parsed **only** through `_home_pin_scan.parse_module`.
7. **CAUTION — do not bind the env key to a module constant (`ENV = "SPEC_KITTY_HOME"`) here for
   convenience**: that is an **assignment-bound constant valued `"SPEC_KITTY_HOME"`** and it **reds SC-002b**,
   whose population must stay **0**.

**Files**: `tests/architectural/_home_pin_synthetic.py` (new, ~200 lines, never collected);
`tests/architectural/test_home_pin_synthetic_trees.py` (new, ~180 lines, collected, `architectural`-marked).

**Validation**: Every cheap repair for a checked-in tree is separately barred — directory exclusion by
C-003/NFR-001, a census row by C-007, a third `E` entry by fixed arity — so **the materialiser is the only
C-001-compatible demonstration path**.

**What this cannot see**: a shape nobody wrote a tree for.

---

### Subtask T016: The eight SC-006 transitions, red-first

**Purpose**: All eight, over materialised trees, **each demonstrated RED before the mechanism exists**.

**Steps** — one tree and one assertion per transition:

1. **Empty census reds.**
2. **The census-frozen tree greens**, attesting **FREEZING** and asserting **nothing about desert**.
3. **A 41st member anywhere reds.**
4. **A 41st under a name used nowhere else reds.**
5. **A removed row with the definition still present reds.**
6. **A 41st that also requests the owner AND RESTATES the pin reds** — with the witness declared
   `(monkeypatch, <a materialised fixture that YIELDS a home root>)` and **NO `tmp_path`**, **modelled on the
   live population-1 `runtime_home` shape, never on the `None`-returning canonical owner**, because a witness
   that gratuitously re-declares `tmp_path` **tests nothing FR-010 is for**.
7. **A 41st member ACCOMPANIED BY a new census row still reds** — additions are **structurally impossible**,
   not merely discouraged.
8. **Removing one of a COLLIDING PAIR reds** — two members in **DIFFERENT files** whose **BARE
   `composite_key` is byte-identical**.

**Files**: `tests/architectural/test_spec_kitty_home_pin_guard.py` (new, ~300 lines at this stage);
`tests/architectural/_home_pin_synthetic.py` (+ tree builders).

**Validation**: **Transition (8) is the single cheapest test that catches the 19-key collapse and the only one
that keeps it caught.** Without it the C-012 interpretation is **unpinned and can be reverted with the other
seven still green.**

**What this cannot see**: whether a member's presence is justified — R1a adjudicates nothing.

---

### Subtask T017: SC-004, SC-013, and the SYNTHETIC witness that takes C-004 off a single real row

**Purpose**: Three permanent guards, one of which removes a live single-point-of-failure in WP01's C-004
mechanisation.

**Steps**:

1. **SC-004 ships as a PERMANENT test** over a materialised tree in which a **census row is stale while every
   member is present**, and the guard **reds ON THE ROW**.
2. **The same subtask includes a tree where `discovered ⊂ census` and requires a red** — which is what proves
   the comparison is **SET EQUALITY and not containment**.
3. **SC-013** ships a tree containing a **deliberate `SyntaxError`** and asserts the guard **REDS**, with the
   error **propagating out of `parse_module` and caught nowhere on the guard's call path**, asserted **by AST
   as well as behaviourally**.
4. **AND THE PERMANENT GUARD SHIPS THE SYNTHETIC OUTERMOST-VERSUS-INNERMOST WITNESS required by C-012(5)**:
   a materialised member whose **keyed def and innermost def differ**, asserting that the `MemberKey` qualname
   is the **INNERMOST** and that `kind` is taken at the **KEYED** def.
5. **Why it is not optional.** Without it, **both of C-004's discriminators rest on one real-tree site —
   `:1165` — held in the class by an unused `monkeypatch` parameter that `ruff`'s relaxed `ARG` for
   `tests/**` will not defend**, so a routine cleanup **silently disarms the mechanisation**.

**Files**: `tests/architectural/test_spec_kitty_home_pin_guard.py` (+~180 lines);
`tests/architectural/_home_pin_synthetic.py` (+ tree builders).

**Validation**: `except SyntaxError: continue` **narrows the walk with nothing firing and buys budget
headroom**, which is NFR-001's defeat wearing an exception handler.

**What this cannot see**: whether the row was stale for a good reason; and a file unreadable for reasons other
than syntax.

---

### Subtask T018: The `E` mechanism — arity, hash placement, and the co-edit asymmetry, over materialised artefacts

**Purpose**: FR-004's exemption set and direction mechanism. **Three limbs over MATERIALISED artefacts, so
this WP is green without WP03 or WP05.**

**Steps**:

1. **(i) ARITY** — a test invokes **mypy AT TEST TIME**, as `[sys.executable, "-m", "mypy"]` and **NEVER a
   bare `mypy` from `PATH`**, on a temporary module that **IMPORTS THE REAL `Exempt` from `_home_pin_scan`**
   (never re-declaring it, **or the limb tests mypy rather than the type**) and assigns a **three-element
   tuple** to a `tuple[Exempt, Exempt]` annotation. Assert a **non-zero exit and a diagnostic naming the tuple
   type**. **POSITIVE CONTROL**: the same harness **exits zero** for a **two-element** tuple.
   **If mypy is unavailable the test FAILS — a skip is a fake green.**
   **STATED COST**: that choice **reds the always-on pole on any machine without mypy**, and under DIR-013
   such a red must be **reported, not absorbed**.
   **This limb is not insurance**: CI runs mypy only over `src/specify_cli src/charter src/doctrine`, with
   `continue-on-error`, so **`tests/` has no mypy gate** and SC-005's "a third entry is a type error" would
   otherwise be enforced by **nothing**. It proves the **MECHANISM**; **WP05 runs mypy over the REAL
   `_home_pin_exempt.py`**, which is what SC-005 needs.
2. **(ii) HASH PLACEMENT** — the guard **RECOMPUTES** the key-set hash from the census and compares. Over
   materialised artefacts:
   - an `owed_to` re-point **PASSES**;
   - a header edit **PASSES**;
   - a row removal **without** a tombstone **REDS**;
   - a row removal **WITH** a matching tombstone **PASSES**.
3. **(iii) `E`'s CO-EDIT RULE** — **any** delta to `E` or its hash **reds UNCONDITIONALLY**, with **no
   tombstone path**, because **`E` never legitimately changes in R1a or R1b**.

**Files**: `tests/architectural/test_spec_kitty_home_pin_guard.py` (+~200 lines).

**Validation**: A blanket **"touching both reds"** rule would pass (ii) **and forbid R1b's entire job**, so
(ii) requires the **legitimate-adjudication case to PASS** as well as the illegitimate one to red.

**What this cannot see**: the real `E` — **WP05 asserts that.**

---

### Subtask T019: `test_spec_kitty_home_pin_prefilter.py` — OD-002 form (a), with the differential, and without a contended wall clock

**Purpose**: FR-002's pre-filter proof, at NFR-002's strength.

**Steps**:

1. **ONE classifier called TWICE** — `discover(root, prefilter=True)` and `discover(root, prefilter=False)` —
   **never two implementations agreeing with each other**.
2. The **symmetric difference of their FULL outputs is empty**: **member sets AND every member's
   `home_partition`**, because **the pre-filter serves both variables** and extending its scope without
   extending its proof is what §0.6 condemns the repository's two existing pre-filters for.
3. **THE SAME TEST** asserts the two passes **PARSED DIFFERENT FILE SETS** — prefiltered **strictly smaller**,
   unfiltered **EQUAL to the full enumeration** — as a **set relation**, counts **reported** (**`C-002`** — no
   counted definition of done; the number is content, never a threshold, and it is stale the moment anyone
   adds a file), **`2737` never
   asserted**.
4. **THE 90 s FIGURE IS AN EXECUTION ENVELOPE HERE, NOT AN ASSERTION**: a wall-clock assertion inside the
   contended `arch-adversarial` pole is the anti-pattern `ci-quality.yml:2157-2180` documents (**#2032**). If a
   timed limb is wanted it **moves to the `timing` module**.
5. **WHERE ANY DURATION IS TAKEN ANYWHERE IN THIS MISSION IT IS `time.perf_counter()`**: `time.time()` is in
   `_BANNED_CALLS` (`tests/_support/wall_clock_assertions.py:10-20`) and `tests/conftest.py:245-250` raises a
   `pytest.UsageError` **AT COLLECTION**, taking the whole suite down.
6. Published cost figures use the **measured pair — 0.684 s prefiltered / 8.36 s unfiltered — or none at
   all**; the three inconsistent figures previously quoted for one quantity are dropped, and the argument
   survives either way.

**Files**: `tests/architectural/test_spec_kitty_home_pin_prefilter.py` (new, ~180 lines).

**Validation**: **Without the differential, `prefilter` can be a parameter the body ignores** and the symmetric
difference is empty **by construction** in about a second.

**What this cannot see**: key-indirection members. **NEITHER form can** — both passes run the same classifier,
so the symmetric difference is empty **by construction** if it cannot see them. SC-002b covers that (T020).

---

### Subtask T020: SC-002b's premise, bound to the registry entry that carries it

**Purpose**: Keep the pre-filter's unstated-then-stated premise from being quietly deleted.

**Steps**:

1. **FR-007's positive-control rule is discharged for this premise in WP01.** **THE CONTROL AND THE EMPTY-SET
   ASSERTION LIVE IN WP01/T004, NOT HERE** — they need only a materialised module, so there is **no dependency
   on this package**, and putting them here would have forced either a **WP01 DoD that a downstream WP
   completes** or an **edit to a WP01-owned file**.
2. **What this subtask owns is the BINDING**: the pre-filter module asserts that the id
   **`assignment_bound_env_key_constant` is PRESENT in `_home_pin_scan.INERT_LIMBS`**, so the premise on which
   the pre-filter's soundness rests **cannot be silently removed from the registry while the pre-filter still
   depends on it**.
3. It **PUBLISHES BOTH FIGURES** in its own failure message **and** in `record.md` — **0 assignment-bound
   against 229 literal `ast.Constant` occurrences in 98 files**. **The 229 is what makes the 0 meaningful**;
   the earlier form of this criterion asserted all such constants were empty and was **falsified by its own
   subject matter**.
4. **SC-002b is unconditional and is NOT substitutable by either OD-002 form.**

**Files**: `tests/architectural/test_spec_kitty_home_pin_prefilter.py` (+~50 lines); `record.md` (append both
figures).

**Validation**: An over-narrow matcher returns `set()`, greens forever, and **still greens the day someone
writes the indirection**; the control in T004 detects that, and **this binding is what stops the id being
dropped from the registry to make an equality green**.

**What this cannot see**: a constant **assembled at runtime** rather than written as a literal.

---

### Subtask T021: `test_spec_kitty_home_pin_budget.py` — budget (a), the enumerated set, and both parallel modes

**Purpose**: SC-007's budget and enumerated-set criterion, in the **only** module of this WP that is not
`architectural`.

**Steps**:

1. `pytestmark = pytest.mark.timing` **and NOTHING else**, so it runs in **`timing-nfr-serial`**
   (`-m timing -n0`, always-on, wired into `quality-gate.needs`, **merge-blocking**) and is **correctly
   excluded from the pole** by `and not timing`.
2. **Three warm runs, every one inside 6 s** (NFR-001), timed with **`time.perf_counter()`**.
3. **In the same module**, the set of files the guard **ENUMERATED** is asserted **EQUAL** to a
   `Path(root).rglob("*.py")` **computed INLINE IN THE TEST**, **never obtained from the module under test** —
   because the seam exposes exactly one enumerator and **the natural assertion is a self-comparison that a
   narrowed walk passes**. Count **REPORTED, never asserted** (**`C-002`**).
4. **NFR-003**: identical verdicts under `-n0` and `-n auto --dist loadfile`, **both demonstrated**.
5. **OD-003 is discharged** by reading the figure out of `timing-nfr-serial` on the draft PR and **recording it
   as a number**. The budget **may be RAISED with that evidence and the contention headroom STATED**, and
   **the walk may NEVER be narrowed**.

**Files**: `tests/architectural/test_spec_kitty_home_pin_budget.py` (new, ~120 lines, `timing`-only).

**Validation**: **The cheapest way to meet a wall-clock budget is to narrow the walk**; the inline `rglob` set
equality makes that impossible — which is **why the anti-drift rule bans `ast.parse`/`NodeVisitor` in the guard
modules but explicitly does NOT ban `rglob`**.

**What this cannot see**: the guard under contention. `timing-nfr-serial` measures it **uncontended** while
`arch-adversarial` runs it under `-n auto` on 4 vCPUs, so **the serial figure is a FLOOR, not the worst case**.

---

## Definition of Done

Per-subtask completion is a `spec-kitty agent tasks mark-status <Txxx> --status done` event.

1. **PRECONDITION, before the first subtask**: `tests/architectural/test_home_pin_gate_verdict.py` is present
   and **GREEN** in this lane's worktree (`worktree_allocator.py:462-472` degrades to a printed warning, so
   this is **checked**).
2. **All eight SC-006 transitions, SC-004, SC-013 and the synthetic outermost-versus-innermost witness land
   RED-FIRST over materialised trees**, and the **counterpart guard proves no member lives under any
   test-owned fixture root**.
3. **`discovered == census ∪ E` is proven to be SET EQUALITY, not containment**, by a tree in which
   `discovered ⊂ census` **reds**.
4. **SC-002 asserts empty symmetric difference over BOTH variables' outputs AND that the two passes parsed
   different file sets**, with **90 s as an execution envelope** rather than an in-pole wall-clock assertion.
5. **`E`'s fixed arity is enforced by a test-time `[sys.executable, '-m', 'mypy']` invocation importing the
   REAL `Exempt`**, with a **positive control**, **failing rather than skipping** when mypy is absent.
6. **IC-08 landing, mechanically**: **THREE** `architectural` modules (`test_home_pin_synthetic_trees.py`,
   `test_spec_kitty_home_pin_guard.py`, `test_spec_kitty_home_pin_prefilter.py`) and **ONE `timing`-only**
   module (`test_spec_kitty_home_pin_budget.py`); **`_home_pin_synthetic.py` is a helper and is never
   collected**. All four covered by `test_gate_coverage.py::test_no_new_orphan_surfaces`.
   **`tests/_arch_shard_map.py` is NOT edited.**
7. **Zero `ast.parse` calls and zero `ast.NodeVisitor` subclasses** in every module of this WP; materialised
   sources parsed **only** via `_home_pin_scan.parse_module`.
8. **No duration anywhere uses `time.time()`.** **NFR-004**: `ruff check` and `mypy --strict` clean, **never
   `ruff format`**. **C-013**: explicit-path `git add`, long commands bounded with `timeout`, nothing merged.
   **C-006**: no file under `src/` changes and **no existing test module changes**.

## Not Done If

- **Any synthetic tree is checked in under `tests/`.**
- **Transition (8) or the synthetic outermost-versus-innermost witness is missing.**
- The pre-filter proof **lacks the parsed-file-set differential**, or is **weakened to OD-002 form (b)**, or
  **asserts a wall clock inside the pole**.
- The budget is met by **narrowing the walk**, by a **directory or filename filter**, or by
  **`except SyntaxError: continue`**.
- The budget module carries **`architectural` instead of `timing`**; the mypy arity test **skips** when mypy is
  absent, **re-declares `Exempt` locally**, or **invokes bare `mypy`**.
- **T015's assertions live in `_home_pin_synthetic.py`**, where `testpaths = tests` never collects them.

## Risks

| Risk | Mitigation |
|---|---|
| **The golden-count ratchet has ZERO headroom.** `tests/architectural` sits at **25/25** convert-classified sites against a frozen ceiling of **25**, so **any** new `len(x) == N` assertion in this WP trips `test_golden_count_ban::test_convert_sites_do_not_exceed_frozen_baseline`. | Every assertion is a **SET comparison, never a count**. **The baseline may NOT be re-frozen** — the fix is always to convert the assertion, never to raise the bound. C-002 already forbids a counted definition of done; this is that rule at the point it bites. |
| `prefilter=` becomes a parameter the body ignores; the symmetric difference is then empty by construction. | The parsed-file-set differential (T019(3)) is the only limb that sees it. |
| The mypy arity test skips on a machine without mypy — a fake green. | It **fails**. Stated cost: it reds the always-on pole there, and under DIR-013 that red is **reported, not absorbed**. |
| A convenient `ENV = "SPEC_KITTY_HOME"` module constant in the materialiser. | Reds SC-002b, whose population must stay 0. Called out in T015(7). |
| Transition (8) dropped as "redundant". | It is the only transition that keeps the 19-key collapse caught; without it C-012 can be reverted with seven greens. |
| The budget red is repaired by narrowing the walk. | The inline `rglob` set equality (T021(3)) makes that impossible. Raise the budget **with the recorded runner figure** instead; never narrow. |
| Wall clock taken with `time.time()`. | `tests/conftest.py:245-250` raises `pytest.UsageError` **at collection**, taking the whole suite down. Use `time.perf_counter()`. |
| Pre-existing reds (C-009 vs DIR-013). | Classify per CLAUDE.md's baseline-red gotcha; record evidence in `record.md`; route to the **OPERATOR** as a TG-item. **C-013 forbids `gh issue create` here.** |

## Reviewer Guidance

- **Count the transitions. There are eight.** Check (8) — the colliding pair in **different files** with a
  byte-identical bare `composite_key` — and check T017's synthetic outermost-versus-innermost witness. Those
  two are what keep C-012 and C-004 pinned once `:1165` is cleaned up.
- Check T019 asserts the **parsed file sets differ**, not merely that the outputs agree.
- Check the mypy harness **imports the real `Exempt`** and uses `[sys.executable, "-m", "mypy"]`.
- Check T018(ii) has **all four** cases, including the two that must **PASS**. A blanket "touching both reds"
  rule forbids R1b's entire job.
- Check the budget module is **`timing`-only** and every other module is **`architectural`**.
- Confirm no synthetic tree is checked in and that `_home_pin_synthetic.py` holds **no assertions**.

## Implementation

```bash
spec-kitty agent action implement WP04 --agent <name>
```

## Activity Log

- 2026-08-11T22:08:30Z – claude – shell_pid=196556 – Fourth pass (commit ad61b3329): verdict seam guard shipped as tests/architectural/test_home_pin_verdict_seam.py, WP04-owned, architectural-marked, 14 tests. Predicate: a module does verdict work when it imports _home_pin_scan AND shows one of three signals — reads a census/baseline artefact path (contiguous path token, docstrings excluded); hand-rolls a digest; or compares operands naming 2+ of census/baseline/discovered/exempt. Such a module must import _home_pin_verdict. Scanner-import gate is load-bearing: raw signals fire in 40+ modules across src/ u tests/, gated the population is 4, offenders none. Bites: materialised copy reading the census and comparing reds on artefact-read+verdict-comparison; copy re-deriving the checksum with hashlib reds on hand-rolled-hash alone; ordinary consumer passes; adding the one-line import clears it. Mid-pass defect found and fixed: the first artefact regex spanned newlines so any docstring mentioning baseline above a .yaml below matched — it fired on this package's own prefilter module; now a contiguous path token with docstrings skipped, and that false positive ships as a negative control. Limits recorded in the docstring. Exemptions by name with reasons, asserted live; _home_pin_gate.py deliberately not exempted. as_key TypeError/ValueError branches now exercised. Mutation table identical for the third consecutive pass. 64 architectural passed / 4 timing deselected; repo gates 52 passed; ruff + mypy --strict clean on 7 files. NOTE FOR COORDINATOR: WP04 was already in for_review, not in_progress, so the requested move-task was an illegal for_review->for_review transition and was NOT forced. Also lanes.json write_scope still lists only the original 5 files — _home_pin_verdict.py and test_home_pin_verdict_seam.py are not in it.
- 2026-08-11T22:40:36Z – claude – shell_pid=275229 – Cycle-2 rejection addressed (commit 262edad32). Both required changes constructed before being made. (1) EXEMPT key set pinned by content against FROZEN_EXEMPT_KEYS; reproduced the reviewer's walk-through first (one filler row moved offenders from ['architectural/test_hand_rolled.py'] to [] with all three limbs accepting), and after the fix that row surfaces as an unauthorised addition. Set equality, never len(EXEMPT)==3; my earlier reason for declining was refuted by test_golden_count_ban.py:4-9's own exemplar. test_every_exemption_states_a_reason kept, threshold dropped to non-empty. (2) verdict_comparisons fired only on ast.Eq; constructed that '<=' and '.issubset()' were NOT SEEN while '==' was caught. Signal now covers <=, <, >=, >, issubset, issuperset, with both containment copies as positive controls 3 and 4. Real tree re-measured: same 4 modules, 0 offenders, 0 stale exemptions, no new false positives. (3) Fourth honest limit recorded: assembled artefact path is invisible, measured. (4) Figures corrected: gated population 4 not 3; raw denominator published as 103. Mutation table identical for the FOURTH consecutive pass. Verification: 67 architectural passed / 4 timing deselected; seam guard + timing 10 passed; verdict guard + golden-count 26 passed; ruff + mypy --strict clean on 7 files. COORDINATOR NOTE: WP04 is in for_review, so the requested move-task was again an illegal for_review->for_review and was NOT forced; the rejection appears not to have moved the lane back to in_progress.
- 2026-08-11T22:49:27Z – claude – shell_pid=275229 – Cycle-3 items done (commit ee4728edf). (1) EXEMPT key set pinned OUTSIDE the module in a generated file, tests/architectural/_home_pin_verdict_exempt_pin.yaml, digest via _home_pin_verdict.hash_of_key_set (no second generator; makes the guard a consumer of its own seam), regenerated by 'python -m tests.architectural.test_home_pin_verdict_seam --freeze-exempt-pin'. Constructed with the in-module pin deliberately SATISFIED first: step 0 offenders ['architectural/test_hand_rolled.py']; step 1 add EXEMPT row -> offenders [] with both pins False; step 2 also update FROZEN_EXEMPT_KEYS in the same file -> in-module pin TRUE, EXTERNAL pin STILL FALSE (expected d86430d68e73d94a..., actual 1808f692ca007ad4...). FROZEN_EXEMPT_KEYS kept as belt; the external file is the braces. Plus an instrument check that the digest moves when the key set does. RAISED DEVIATION: the instructed target (the baseline artefact the guard already reads) does not exist — spec_kitty_home_pin_baseline.yaml is not in this lane (WP05 generates it), render_baseline emits a fixed five-key document so a sixth would mean editing WP01-owned _home_pin_scan.py, and its exempt_set_sha256 is E's hash (two Exempt rows of the behaviour class), a DIFFERENT set from the guard's exempt MODULE list — overloading one field with two unrelated sets would be worse than the defect being fixed. Followed the repo's own precedent instead: _golden_count_baseline.json + --freeze-baseline beside test_golden_count_ban.py in this same directory. (2) All five operators and both method spellings now exercised via parameterised cases, each asserted to FIRE the signal rather than merely execute the branch, plus a drift test asserting configured operators and spelling cases stay in step by SET comparison. ==, <=, issubset already had end-to-end controls; <, >=, >, issuperset were untested branches in the code written to close an untested-branch finding. Mutation table IDENTICAL for the fifth consecutive pass. Verification: 93 passed / 4 deselected across all five WP04 modules plus golden-count ratchet and WP02's seam guard; verdict seam guard alone 28 passed; ruff clean and mypy --strict clean on 7 files; no len(...)==N. COORDINATOR NOTE: WP04 remains in for_review so move-task was again an illegal for_review->for_review and was NOT forced.
- 2026-08-12T00:55:08Z – claude – shell_pid=275229 – Terminology Canon fix (commit 71ab6b8ea). Two docstrings in test_home_pin_verdict_seam.py used the forbidden term whose canonical form is 'status commit', as ordinary English describing why the in-module exemption pin was weak. Reworded to say it plainly. Line 202 (module constant): '...tells a maintainer exactly which adjacent line to edit. The cost of forgiving yourself did not actually rise, which is the shape of the word count it replaced.' Line 769 (test docstring): '...so satisfying it is a two-adjacent-line edit in one file - raising no more real cost than the word count it replaced.' SWEEP FOUND A SECOND OCCURRENCE the reported failure did not: the guard greps case-sensitively via 'git grep --fixed-strings', so the capitalised use at line 202 was LATENT, not failing, and would have tripped the moment anyone lowercased the sentence. Both removed. Swept all EIGHT WP04-owned files (7 .py plus the generated _home_pin_verdict_exempt_pin.yaml, which is in scope since the guard scans tests/**/*.yaml) for both forbidden terms and for feature/features: zero hits remaining. The only surviving repo-wide matches are pre-existing and correctly excluded - docs/adr/ (immutable historical snapshots) and the guard's own file. VERIFICATION: pytest tests/architectural/test_no_legacy_terminology.py = 10 passed. Full run 103 passed / 4 deselected across all five WP04 modules plus the terminology guard, golden-count ratchet and WP02's seam guard. ruff clean, mypy --strict clean on 7 files. Mutation table UNCHANGED for the sixth consecutive run, as a docstring edit should leave it. Root cause noted for the record: this guard runs only in CI's integration-tests-core-misc job and not in fast-tests-*, which is why every local gate this package ran stayed green - the trap CLAUDE.md flags explicitly for prose changes.

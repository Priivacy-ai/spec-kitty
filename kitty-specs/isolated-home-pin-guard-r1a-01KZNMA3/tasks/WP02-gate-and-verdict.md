---
work_package_id: WP02
title: 'The gate: the seam teeth, the window measurement, and the verdict that halts the Mission'
dependencies:
- WP01
requirement_refs:
- FR-008
- FR-009
- NFR-004
- NFR-006
- C-003
- C-006
- C-011
- C-012
- C-013
planning_base_branch: feat/isolated-home-pin-guard
merge_target_branch: feat/isolated-home-pin-guard
branch_strategy: Planning artifacts for this mission were generated on feat/isolated-home-pin-guard. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/isolated-home-pin-guard unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
history: []
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/_home_pin_gate.py
- tests/architectural/test_home_pin_seam_no_second_copy.py
- tests/architectural/test_home_pin_gate_verdict.py
execution_mode: code_change
owned_files:
- tests/architectural/_home_pin_gate.py
- tests/architectural/test_home_pin_seam_no_second_copy.py
- tests/architectural/test_home_pin_gate_verdict.py
role: implementer
tags: []
task_type: code-implementation
tracker_refs: []
---

# Work Package Prompt: WP02 (alias WP-0b) – The gate: the seam teeth, the window measurement, and the verdict that halts the Mission

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

> ## 🛑 THIS WORK PACKAGE CAN HALT THE MISSION
>
> T009 publishes a machine-readable `verdict:`. **If it reads `halt`:**
>
> 1. **WP02 is NOT marked approved and NOT marked done.** It stays at `for_review`.
> 2. **WP03, WP04, WP05 and WP06 are moved to `blocked`**, one command each:
>    ```bash
>    spec-kitty agent tasks move-task WP03 --to blocked
>    spec-kitty agent tasks move-task WP04 --to blocked
>    spec-kitty agent tasks move-task WP05 --to blocked
>    spec-kitty agent tasks move-task WP06 --to blocked
>    ```
>    **Note the command.** `spec-kitty agent tasks mark-status` takes **T-ids** and accepts only
>    `done` / `pending` — it is the **wrong** command here. `blocked` is reachable only through `move-task`.
> 3. **Leaving WP02 unapproved is what actually holds the dependents.**
>    `dependency_readiness_for_wp` (`core/dependency_graph.py:50-77`) admits **only** `approved` / `done`
>    (`_SATISFYING_DEPENDENCY_LANES = {approved, done}`) and explicitly excludes `blocked` and `for_review`,
>    so `implement WP03` and `implement WP04` then **RAISE**.
> 4. **Operator sign-off is requested. The implementer may NOT proceed on their own authority.**
>
> **KNOWN RESIDUAL, stated here rather than discovered later: this enforcement is PROCEDURAL, not
> structural.** It depends on a human performing two lane transitions correctly at the exact moment they
> have just learned the Mission is halting — and `approved` is the habitual next action. The collected
> verdict test (T008) is defence-in-depth *behind* that, **not** the enforcement. This residual is recorded
> again in WP06/T030; do not let it go unwritten.

---

## Objective

Author `_home_pin_gate.py` (window measurement, rename detector, banding, ±1 stability, the unbounded
first-parent walk with a defined exit), the anti-drift seam teeth over a **discovered** consumer set, and the
**collected** verdict test with its 806-state oracle. Then run the measurement under the amended schedule and
publish `research/home_pin_gate/verdict.yaml`.

## Context

- **Plan concerns**: IC-02 (the forward-catch-rate gate and its verdict artefact), IC-08 (CI landing).
- **The gate is no longer R1a's own stopping mechanism, and the spec says so.** The measurement has
  **leaked**: an independent lens measured `r = 100%` at candidate windows roughly **300, 600 and 2000**
  first-parent commits back (`|R| = 9, 33, 34`). **On published evidence the verdict is already known to be
  `proceed`.** What is *protected* is the **stopping rule's independence from `r`**; what is *lost* is the
  analyst's blindness. Do not describe this WP as a discovery.
- **The stated window is already known VOID.** Measured post-tasks, `709a59534 -> 5d49d31ed` gives **37**
  members at the start SHA and **40** at the end with **0 departures**, so **`|R| = 3`** against a floor of
  **10**. **Lowering the floor is REFUSED by the operator.** T009 starts from the VOID result and walks.
- **The split from WP01 buys zero throughput and exists for halt hygiene.** WP-0b depends on WP-0a and
  everything depends on WP-0b; the critical path is unchanged. **Nobody may "optimise" the split back
  together.**
- **How the gate reaches every package, from the MEASURED lane graph.** `lane-a=[WP01]` depends on nothing;
  `lane-b=[WP02]` depends on `lane-a`; `lane-c=[WP03]` and `lane-d=[WP04]` **both depend on `lane-b`, not on
  `lane-a`**; `lane-e=[WP05]` depends on `lane-c` and `lane-d`. `_ordered_dependency_lanes` resolves **direct**
  dependencies only — there is no transitive closure — so lane-a's content reaches lane-c and lane-d
  **transitively, through lane-b's tip**, which already carries lane-a's because lane-b was allocated first.
  Two earlier statements are struck: that WP-0b's commits are "in every downstream lane's base" (**FALSE** —
  the lane base is the mission branch), and that "lane-b and lane-c both declare `depends_on_lanes=('lane-a',)`"
  (**FALSE** — that was the five-lane graph measured *before* the WP-0a/WP-0b split renumbered the lanes).
  The conclusion survives; the mechanism is **two hops, not one**. The tip-merge path
  **degrades to a printed warning** at `worktree_allocator.py:462-472` if a dependency branch is
  unresolvable — a longer chain with a soft failure at each hop, which is why WP03 and WP04 each
  carry an explicit precondition. The second, independent limb — **a package may not author the test that
  must block it** — is sound and unchanged.

---

### Subtask T006: `_home_pin_gate.py` — extraction at both SHAs, the rename detector, banding, ±1 stability, the unbounded walk

**Purpose**: The driver. `subprocess` and `git` live **HERE and nowhere else** — `_home_pin_scan.py` is
imported by collected tests under a 6-second budget and must stay clean of both.

**AUTHORED FIRST IN THIS PACKAGE**, because T007's guard asserts this module is in the discovered consumer set.

**Steps**:

1. Create `tests/architectural/_home_pin_gate.py`. It **imports `discover`** from `_home_pin_scan` and owns
   **no predicate**, so the no-second-copy property is preserved.
2. Extraction: for each SHA, extract `tests/` with **`git archive`** into a temporary directory and call
   `discover(root=<extracted>/tests)`. **FR-009's root parameter is therefore exercised by the gate before
   any consumer depends on it** — the two-SHA measurement is evidence the seam works rather than a claim that
   it will.
3. `band(|R_f|, |R|)` and `stability(|R_f|, |R|)` are **pure exported functions**, per `data-model.md`
   §Banding:
   - `|R| < 10` -> **VOID** (a precondition, **NOT a band**; evaluated **BEFORE** banding);
   - any admissible ±1 changing the **CONSEQUENCE class** -> **INADMISSIBLE**;
   - `r == 100%` -> `proceed`; `50% <= r < 100%` -> `proceed-degraded`; `r < 50%` -> **HALT**.
   - **Clamp**: `|R_f| − 1` skipped at `|R_f| = 0`; `|R_f| + 1` at `|R_f| = |R|`; `|R| − 1` at
     `|R| = |R_f|`; **and `|R| − 1` also skipped when it would fall below the floor, because VOID is not a
     band.**
4. **Every population it produces is an AST set difference.** `git log -S` and `git diff | grep` are text
   search over a population and are **barred (C-003)**.
5. **Rename detector**, proven on materialised departure/arrival sets:
   - a **unique mutual best match** on `(resolved_value, params_at_keyed_def, kind)` **in the same file**
     PAIRS;
   - a **two-way tie is REFUSED** and both sites retained;
   - a candidate whose `resolved_value` is `None` **never matches**.
6. **The walk implements the AMENDED §0.9 schedule**: backwards along `upstream/main`'s **FIRST-PARENT**
   history **ONE COMMIT AT A TIME** — `main` is rebase-merged, so there are no merge commits to step over —
   with **NO ATTEMPT CAP**, stopping at the first SHA where **BOTH** `|R| >= 10` **and** ±1 consequence-class
   stability hold, and with the **DEFINED EXIT**: reaching the **root of first-parent history** without both
   holding jointly stops the walk and **the OPERATOR decides**.
7. **The stopping rule reads `|R|` and stability ONLY, NEVER `r`.**
8. The emitted document's **top-level key set EQUALS** `data-model.md`'s enumerated `Verdict` field list.

**Files**: `tests/architectural/_home_pin_gate.py` (new, ~400 lines).

**Validation**: The stopping rule's independence from `r` is the **entire forking-path defence** and it
survives the cap's removal untouched; a rule that read `r` would let a walker stop at a convenient band.

**What this cannot see**: whether ±1 stability is satisfiable at any window. Reachability is evidenced for the
**floor** (first met ~300-600 commits back) and **NOT evidenced** for stability.

---

### Subtask T007: `test_home_pin_seam_no_second_copy.py` — the anti-drift teeth, over a DISCOVERED consumer set

**Purpose**: Convert the "imports, not re-implements" instruction from an intention into a red. **The seam is
not the import; it is the test that makes the import the only option.**

**Steps**:

1. Compute **by AST** the **SET** of modules under `tests/` importing from `_home_pin_scan`.
2. Assert that set is **NON-EMPTY** and **CONTAINS `_home_pin_gate.py`** — which exists because **T006
   precedes this subtask**. That ordering is made explicit here because the previous revision put this guard
   in a package where its own named consumer did not yet exist, and it was **red at its own completion**.
3. **The consumer set is DISCOVERED, never hard-coded**, so WP03/WP04/WP05's modules are covered **without
   editing this file**.
4. Assert every member contains **ZERO `ast.parse` calls** and **ZERO `ast.NodeVisitor` subclasses**;
   synthetic sources anywhere in the Mission are parsed **only** through `_home_pin_scan.parse_module`.
5. A second limb asserts **by AST** that `_home_pin_scan.py` imports **neither `subprocess` nor any git
   surface**.
6. **Both limbs ship a positive control** over a materialised module that **DOES** contain the banned
   construct.

**Files**: `tests/architectural/test_home_pin_seam_no_second_copy.py` (new, ~180 lines).

**Validation**: Prose is exactly what failed at `_sole_door_scan.py:13-27`; a hard-coded consumer list greens
the day a consumer is renamed, which is why the set is **discovered and asserted non-empty**.

**What this cannot see**: a second copy of the predicate written **without importing `_home_pin_scan` at all**.

---

### Subtask T008: `test_home_pin_gate_verdict.py` — the COLLECTED gate, the 806-state oracle, and the keys checked against this tree

**Purpose**: The gate that blocks every package. A **collected**, `architectural`-marked, **top-level** module —
not "WP-a's first task", which gates only whichever package happens to be sequenced first.

**Steps** — seven limbs, each independently falsifiable:

1. **(a)** **FAILS** when the verdict artefact is **absent**, demonstrated against an empty `tmp_path`.
2. **(b)** **FAILS** when it reads `halt`, demonstrated over a materialised artefact.
3. **(c)** Passes **only** for `proceed` / `proceed-degraded`.
4. **(d)** **Recomputes `band`** from the published `r`, `|R|`, `|R_f|` and asserts it **EQUALS** the published
   label — the SC-000(vi) limb, **without which `proceed` written above `r = 0.6` is undetectable**.
5. **(e)** Asserts internal consistency **AS SETS**: `R_f ⊆ R`; `r == |R_f| / |R|`; `|R| >= 10`; `end_sha`
   equal to §0.9's literal; **both operand sets non-empty** — **AND** requires the `start_sha_crosscheck`
   key to be **present** with its `symmetric_difference` field **present WHETHER EMPTY OR NOT**, and any
   non-empty difference to carry a **non-empty `explanation` sibling**, so the cross-check T009 publishes is
   verified by **something** rather than by nobody.
6. **(f)** Runs the **oracle**: the **FULL mapping** `(|R|, |R_f|) -> consequence class` over
   `|R| in [10,40]`, `|R_f| in [0,|R|]`, compared **as a MAPPING** against one built **inline** from §0.9's
   thresholds and clamp, reproducing §0.9's independently published **`380 go / 364 halt / 62 inadmissible`**.
7. **(g)** **THE RESIDUAL IS NARROWED, NOT ACCEPTED.** `MemberKey` is content-addressed, so for **every** key
   in `sites_at_end` whose `rel_path` still exists in the working tree, recompute
   `(relpath_posix, *composite_key_from_file(path, lineno))` — the C-012 3-tuple, composed that way **because
   the primitive returns a 2-tuple** — and assert it **equals the published key**, with a **PUBLISHED
   NON-ZERO FLOOR** on the number of keys checked so the limb **cannot degrade to zero silently**.
8. **No git, no subprocess** in this module. Measured cost: **0.19 s for 40 keys, 1.35 s for 191**.
9. `start_sha` is asserted equal to **whatever the widening schedule selected and published**, not to a
   literal, **because the window WILL move**.

**Files**: `tests/architectural/test_home_pin_gate_verdict.py` (new, ~260 lines).

**Validation**: A test asserting `"verdict" in artefact` passes for `halt`; **(b)** kills that, **(d)** kills a
mislabelled band, **(g)** kills a fabricated end-SHA operand set.

**What this cannot see**: the **START-SHA operands**, which name content that is not in this tree. Forgery cost
is now *"consistent numbers that are also real token lines at real line numbers in this repository"*, not
*"consistent numbers"*; the start half remains unprovable without git, and **that is stated in the record
rather than papered over**.

---

### Subtask T009: Run the measurement under the amended schedule, publish the verdict, and enforce a halt through the lane machine

**Purpose**: Take the measurement, publish every operand, and — if the answer is `halt` — stop the Mission
through the lane machine, not through prose.

**Steps**:

1. **Start from the VOID result and walk.** `709a59534 -> 5d49d31ed` gives `|R| = 3` against a floor of 10.
   Lowering the floor is refused.
2. Publish `research/home_pin_gate/verdict.yaml` — **the SOLE authority for attempted windows, with no
   rendered duplicate** — committed, carrying **all six SC-000 components**:
   - the **site sets at BOTH SHAs** as operands, so the difference is recomputable without re-running;
   - **every rename pair** with its matching keys;
   - **every refused-ambiguous candidate**;
   - **every unpaired departure and arrival**;
   - `R` / `|R|` / `|R_f|` / `r`; **both SHAs**;
   - **EVERY attempted window** with its `(start_sha, |R|, |R_f|, band)`, **BEGINNING WITH the VOID result at
     `709a59534` (`|R| = 3`)**;
   - the **exact invocation**;
   - the **±1 stability result over consequence classes with the clamp**;
   - the **`start_sha_crosscheck`**;
   - and a **machine-readable `verdict:`**.
   This is **FR-008's unconditional publication list**, not a degraded-band-only one.
3. **The cross-check runs the CHECKED-IN INDEPENDENT INSTRUMENT** `clf.py` from
   `research/spec_kitty_home_pin_evidence/` (C-011) against a `git archive` extraction at the selected start
   SHA — **never a re-implementation**. Publish the symmetric difference against `discover()` **whether empty
   or not**; any non-empty difference is **explained, never tuned away**.
4. **THE RECORD MUST NAME, IN SO MANY WORDS**, whether §0.3's `28 -> 30` figure is **RE-DERIVED** at the moved
   SHA or **EXPLICITLY SUPERSEDED** — **one of those two words, not "addressed"** — because §0.3's published
   growth is what determined this window's fate once already.
5. **THE MEASUREMENT HAS LEAKED and the record must say so**: `r = 100%` at candidate windows ~300, ~600 and
   ~2000 first-parent commits back (`|R| = 9, 33, 34`), so **on published evidence the verdict is already
   known to be `proceed`**. WP-0b **confirms a known answer rather than discovering one**; R1a must stop
   describing the gate as its own stopping mechanism, and what is protected is only the stopping rule's
   independence from `r`.
6. **ON `halt`**: follow the banner at the top of this prompt exactly — WP02 stays at `for_review`, WP03..WP06
   go to `blocked` via `move-task`, operator sign-off is requested, and the implementer may not proceed.
7. **NFR-006**: the gate run is **pinned to the external `pytest>=9.0.3,<9.1` venv**; the resolved interpreter
   path and the **verbatim invocation** are recorded in `verdict.yaml`'s `invocation` field. **NEVER a bare
   `uv run` or `uv sync`; no `.venv` inside this tree.**

**Files**: `research/home_pin_gate/verdict.yaml` (new, mission-directory artefact assigned to this WP).

**Validation**: The operands are published and **T008(g) recomputes the surviving ones from this tree**; the
stopping rule was **pre-committed before this measurement** and does not read `r`.

**What this cannot see**: how contributors will behave, and arrivals that never became sites.

---

## Definition of Done

Per-subtask completion is a `spec-kitty agent tasks mark-status <Txxx> --status done` event.

1. The verdict artefact exists, `band(published) == published.verdict` passes, and
   `test_home_pin_gate_verdict.py` is **COLLECTED** and **reds on `halt`**.
2. **How the gate reaches every package, stated correctly** — see Context above. The lane base is the mission
   branch, not WP-0b's commits; the tip-merge degrades to a printed warning at
   `worktree_allocator.py:462-472`, which is why WP03 and WP04 each carry an explicit precondition. The
   independent limb — a package may not author the test that must block it — is sound and unchanged.
3. **On `halt`**: WP-0b is never moved past `for_review`, WP03..WP06 are moved to `blocked` via `move-task`,
   and the record carries the operator escalation. `mark-status` takes T-ids and only `done`/`pending`;
   `blocked` is reachable only through `move-task`.
4. **NFR-006**: pinned external `pytest>=9.0.3,<9.1` venv; resolved interpreter path and verbatim invocation
   recorded in `verdict.yaml`'s `invocation`. Never a bare `uv run` or `uv sync`; no `.venv` inside this tree.
5. **IC-08 landing, mechanically**: both new test modules are **top-level**, `architectural`-marked, and
   covered by `test_gate_coverage.py::test_no_new_orphan_surfaces` against `_gate_coverage_baseline.json`.
   **`tests/_arch_shard_map.py` is NOT edited.**
6. **NFR-004**: `ruff check` and `mypy --strict` clean, **never `ruff format`**. **C-013**: nothing merged,
   no `gh issue create`, explicit-path `git add` only, every long command bounded with `timeout`, and a
   timeout is a **datum**, never silently retried. **C-006**: only this WP's three owned files and the verdict
   artefact are touched; no file under `src/` changes. Identical results under `-n0` and
   `-n auto --dist loadfile`.

## Not Done If

- The gate is implemented as an **instruction in a downstream WP's first task** rather than as a collected test.
- The walk stops at an **attempt cap**, or the **stopping rule reads `r`**, or a window is accepted **for the
  band it produces**.
- The verdict **omits either operand set**, omits the **VOID result at `709a59534`**, or omits the
  **`start_sha_crosscheck`**.
- The record fails to use the word **RE-DERIVED** or **SUPERSEDED** for §0.3's `28 -> 30` figure.
- On `halt`, **WP-0b is moved to `approved`**, or **any downstream WP is left out of `blocked`**.
- **`_home_pin_scan.py` is edited by this WP.**

## Risks

| Risk | Mitigation |
|---|---|
| **The golden-count ratchet has ZERO headroom.** `tests/architectural` sits at **25/25** convert-classified sites against a frozen ceiling of **25**, so **any** new `len(x) == N` assertion in this WP trips `test_golden_count_ban::test_convert_sites_do_not_exceed_frozen_baseline`. | Every assertion is a **SET comparison, never a count**. **The baseline may NOT be re-frozen** — the fix is always to convert the assertion, never to raise the bound. C-002 already forbids a counted definition of done; this is that rule at the point it bites. |
| The halt path is procedural: two lane transitions performed by a human at the moment they learn the Mission is halting, with `approved` as the habitual next action. | Stated prominently in the banner and re-recorded in WP06/T030. The collected verdict test is defence-in-depth **behind** this, not the enforcement. **There is no structural fix inside R1a.** |
| The walk is unbounded. | It is unbounded **but not unterminated**: the defined exit is the root of first-parent history, at which the **operator decides**. Reachability of `|R| >= 10` is evidenced (~300-600 commits back); **±1 stability at such a window is NOT evidenced**. |
| `r` has leaked, so no analyst can run this blind. | The stopping rule does not read `r` — a leaked value cannot steer a rule that does not read it. Record the loss honestly (T009(5), WP06/T030). |
| A timeout on a long `git archive` walk gets retried into a different answer. | **A timeout is a datum.** Record it; never silently retry. |
| Pre-existing reds (C-009 vs DIR-013). | Classify per CLAUDE.md's baseline-red gotcha; record command, failure summary and merge-base evidence in `record.md`; route to the **OPERATOR** as a TG-item. **C-013 forbids `gh issue create` here.** |

## Reviewer Guidance

- **Check (b) and (d) of T008 before anything else.** A verdict test that only asserts `"verdict" in artefact`
  passes for `halt`, and a band that is published rather than recomputed hides `proceed` written above
  `r = 0.6`.
- Check that the stopping rule's code path **never reads `r`**. That independence is the whole instrument.
- Check that **every attempted window** is in `verdict.yaml`, including the VOID one at `709a59534`.
- Check T007's consumer set is **discovered and asserted non-empty** — a hard-coded list greens on a rename.
- Check the words **RE-DERIVED** or **SUPERSEDED** appear literally for §0.3's `28 -> 30`.

## Implementation

```bash
spec-kitty agent action implement WP02 --agent <name>
```

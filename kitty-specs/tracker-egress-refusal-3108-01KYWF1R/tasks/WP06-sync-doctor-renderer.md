---
work_package_id: WP06
title: sync doctor reports the verdict the gate enforces (lands alone)
dependencies:
- WP05
requirement_refs:
- C-011
- C-012
- C-020
- FR-014
- NFR-005
planning_base_branch: bundle-c-tracker-refusal-3108
merge_target_branch: bundle-c-tracker-refusal-3108
branch_strategy: Planning artifacts for this mission were generated on bundle-c-tracker-refusal-3108. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into bundle-c-tracker-refusal-3108 unless the human explicitly redirects the landing branch.
created_at: '2026-08-01T00:20:00+00:00'
subtasks:
- T032
- T033
- T034
- T035
- T036
phase: Stage 6a - Reporting, before the guards
history:
- at: '2026-08-01T00:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/sync.py
create_intent:
- tests/cli/commands/test_sync_doctor_tracker_egress_3108.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/sync.py
- tests/cli/commands/test_sync_doctor_tracker_egress_3108.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '3108'
---

# Work Package Prompt: WP06 – `sync doctor` reports the verdict the gate enforces (lands alone)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and
behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## Objective

Give `spec-kitty sync doctor` a **new renderer** that reports the tracker-egress verdict — the same
verdict the gates enforce, from the same function, asked with the same destination literals — printed
**unconditionally in every checkout**, with **one row per `EgressDestination` member**: two rows,
always.

`doctor` reported healthy throughout the 2026-07-27 incident. A refusal an operator can only discover
by running the command that fails is a diagnostic gap. This WP closes it — and it closes it **without
reusing the consent-readability fault renderer**, which is measured to be wrong three ways for this
content.

## Owned files — a hard boundary

You may write **exactly two files**:

- `src/specify_cli/cli/commands/sync.py`
- `tests/cli/commands/test_sync_doctor_tracker_egress_3108.py` (**new**)

You may **not** edit any other file. In particular, these are **detection signals, not planned
edits** — read them, run them, never change them:

| File | Why it must not move |
|---|---|
| `tests/cli/commands/test_sync_doctor_consent_health_3030.py` | `:366` asserts `flat.count("REPAIR THE FILE'S SYNTAX") == 4` over the **whole rendered output**. That count staying at 4 is this WP's detection signal. |
| `tests/sync/test_consent_fault_vocabulary_3030.py` | `:261` pins `CONFIG_FAULT_KINDS` by **exact equality**. The set is **not extended**. |
| `src/specify_cli/tracker/egress_verdict.py` | WP03 owns it. Import from it; never edit it. |
| `src/specify_cli/tracker/saas_client.py` | WP05 owns it. |

**One live agent per file** is a standing rule of this Mission.

## What you may assume is already true (dependencies)

WP06 depends on **WP05**, and transitively on WP01–WP04. Therefore:

- `tracker_egress_verdict(root: Path | None, *, destination: EgressDestination)` exists in
  `src/specify_cli/tracker/egress_verdict.py`, **never raises** (NFR-003), and returns a value object
  carrying `refused`, `refusing_channels` (**all** of them, never just the first), `destination`
  (echoed back), the **Channel-1 state**, the **Channel-2 state** plus the **raw value**, the
  operator `message`, and ordered `remedies`.
- **The two vocabularies you branch on, spelled exactly as WP03 ships them. Do not paraphrase either
  — you look these up, you do not re-derive them.**
  - **Channel-2 state** (the field, and the first element of every `_JOIN` key):
    **`absent` / `refused` / `permitted` / `fault`**. Not `refuse`, not `grant`. `data-model.md:278`
    already spells them correctly; **`spec.md` FR-003 (line 616) still says `refuse`/`grant` and is
    the stale one** — the on-disk values win, because those are the two strings an operator writes
    and the two the fault message quotes. A mismatch here is a `KeyError` or, worse, a branch that
    is silently never taken.
  - **Channel-1 state**: `no record` / `recorded refusal` / `not consentable`, **plus a fourth,
    `undetermined`**, which WP03 sets — without calling its classifier — when `root is None`. Your
    renderer hits `undetermined` on **both** rows whenever `locate_project_root(Path.cwd())` returns
    `None`, so it needs its own row wording; it is **not** `not consentable`, whose remedy
    (`spec-kitty init`) is wrong advice for a checkout that does not exist.
  - **The join's outcome vocabulary** — `refuse` / `permit` / `defer` / `defer_reported_noop`.
    `defer` and `defer_reported_noop` enforce identically and **must render differently**: the
    second is Channel 2 `permitted` at `HOSTED_SERVICE`, and it is precisely the case checkout 6
    exists to expose.
- Both gates already call it: the three local gates with `LOCAL_SUBPROCESS`, `SaaSTrackerClient._request`
  with `HOSTED_SERVICE`.
- Channel 2's polarity is fixed by destination: at `LOCAL_SUBPROCESS` two-way (`refused` refuses,
  `permitted` grants independently of Channel 1); at `HOSTED_SERVICE` **narrowing only** (`refused`
  refuses, `permitted` is a **reported** no-op and Channel 1 stays a hard prerequisite).

**Note this concern is schedulable much earlier than its position suggests** — its only technical
dependency is on the verdict function (IC-04/WP03). It is placed after WP05 so that guard G4's
membership set is stable when WP07 lands.

## Requirements this WP satisfies

**FR-014 — `sync doctor` gets a *new* renderer, printing *one row per destination*, not a third scope
through `_render_consent_fault`.** Quoted from `spec.md`:

> "I want tracker egress reported by a block written for a **verdict**, printed unconditionally
> including the permitted case, placed beside the consent-readability section
> (`cli/commands/sync.py:1736-1817`) and rendered by its own function. **The block prints one row per
> `EgressDestination` member — two rows, always, in every checkout — and never consults the on-disk
> provider to decide what to show.** That is a correctness requirement, not a layout choice: the
> on-disk provider does not determine the destination (FR-004's measurement), so a
> provider-conditional rendering would confirm `permitted` as in force to an operator whose
> `list-tickets --provider jira` is refused. Two rows also make the renderer honest about the case
> FR-005 covers and a one-row block cannot express: Channel 2 `permitted` with Channel 1 absent is
> *permitted locally and refused hosted* in the same checkout at the same moment."

**C-020 — a typo fails closed, and says what to type instead.** The fault text must **name the
offending value verbatim and name both legal values**. "The same wording is what `sync doctor` renders
for that checkout, on **both** destination rows, so the diagnostic surface and the failing command
tell the operator the same thing."

**C-012 — blast radius, named before the work starts.** Items (2) and (3) are yours:
`test_sync_doctor_consent_health_3030.py:366` (an exact count over the whole rendered output) and
`tests/sync/test_consent_fault_vocabulary_3030.py:261` (`CONFIG_FAULT_KINDS` pinned by exact
equality; **not extended**).

**NFR-005** — `ruff check` and `mypy --strict` clean, no blanket suppressions, ≥90 % coverage on new
branches from focused tests executing the new helpers directly.

**Success criterion — SC-014**, quoted in full because it *is* the acceptance shape:

> "`sync doctor` renders seven distinguishable tracker-egress blocks — refused by
> `tracker.egress: refused`, refused by a tracker-key fault (naming the offending value and both
> legal values, C-020), refused by Channel 1 in each of its three states, `tracker.egress: permitted`,
> fully permitted — each block carrying **one row per destination**, for **14** rows in total; prints
> the block in all seven checkouts; and each row's rendered verdict equals the verdict enforced at
> that destination, field-for-field. At least one checkout renders **two different answers on its two
> rows** (Channel 2 `permitted` + Channel 1 absent → local permitted, hosted refused), which is the
> assertion a one-row block cannot satisfy. The new block contributes **0** to
> `flat.count(\"REPAIR THE FILE'S SYNTAX\")` and never prints
> `This is NOT a missing consent record`."

---

## Measured hazards — carried verbatim, not summarised

### H-A. `sync doctor` must NOT route through `_render_consent_fault`. Measured three ways.

From `spec.md` FR-014 and `tracer-squad-findings.md` §3.4:

- **A plain string** arriving at `_render_consent_fault` (`cli/commands/sync.py:1711-1733`) yields
  `kind="unknown"` and `detail="no detail recorded"` — **the refusal text is discarded**.
- **A fault-shaped carrier** announces a **correct, readable** file as `UNREADABLE` and tells the
  operator to **REPAIR** it.
- **`_CONSENT_FAULT_NOT_ABSENCE` (`sync.py:1691-1696`) prints *"This is NOT a missing consent
  record"* unconditionally** — **literally false** for the absence case, and **hard-coded outside the
  registry**, so registering a new fault kind **does not fix it**.

**Resolution: write a new renderer.** A verdict inside a *readability* section is a category error;
the readability section's own contract (`sync.py:1737-1743`) is *readability*, not verdict.

Also refused, and for stated reasons:

- **Not** the per-project Consent column (`_per_project_store_table`, `:1429-1473`): it is hard-coded
  binary (`consented` / `denied (<level>)` plus one `unknown (identity unresolved)` case), so a second
  *decision* has nowhere to go in it.
- **`CONFIG_FAULT_KINDS` is not extended** — pinned by exact equality at
  `tests/sync/test_consent_fault_vocabulary_3030.py:261`.

### H-B. WP06 must land alone. It is a necessity, and its detection signal is a count over shared output.

From `plan.md` Stage 6 and IC-07:

> "Its detection signal is `test_sync_doctor_consent_health_3030.py:366`'s
> `flat.count(\"REPAIR THE FILE'S SYNTAX\") == 4` — an exact count over the **whole rendered
> output**. A count over shared output cannot attribute a movement to one of two co-landing changes."

**That count staying at 4 is the signal that the new block did *not* route through the old helper.**
It is a **detection signal, not a planned edit**: from `plan.md` *Open Items* 4 —

> "The brief lists it as blast radius that 'will move'; `spec.md` FR-014, US7 sc5 and SC-014 require
> `flat.count(\"REPAIR THE FILE'S SYNTAX\")` to remain **exactly 4**. **Reading adopted: the spec.**
> The test is a detection signal, not a planned edit — **if it moves, the new block routed through
> the fault renderer**, which is the defect FR-014 exists to prevent."

If it moves, **the implementation is wrong**. Do not "repair" the pinned test.

### H-C. The doctor renders one row per destination, with two literal calls — not a loop.

From `plan.md` *Open Items* 11:

> "`spec.md` FR-014 requires one row per destination, and FR-003/G4 pin the call sites. These are
> reconciled by counting **two different things**: G4 asserts the set of **enclosing functions** is
> exactly five *and* the number of **call expressions** is exactly six. An implementer who reads
> 'five call sites' as 'five call expressions' will write a doctor renderer that **loops over
> `EgressDestination`**, which **G5 then rejects** because the loop variable is a `Name`, not a
> literal member. Both assertions are deliberate and both are exact; do not collapse them into one
> number."

So the renderer contains **two written-out calls**, each with a literal `EgressDestination` member:

```python
local = tracker_egress_verdict(root, destination=EgressDestination.LOCAL_SUBPROCESS)
hosted = tracker_egress_verdict(root, destination=EgressDestination.HOSTED_SERVICE)
```

**This duplication is deliberate and it is the thing the guard exists to check.** A `for destination
in EgressDestination:` loop makes the argument an `ast.Name` node and reds WP07's guard G5.

> **Known internal inconsistency in `plan.md`, resolved here.** `plan.md` line 515 (*Complexity
> Tracking*) says the renderer holds "the per-destination loop". That sentence contradicts *Open
> Items* 11, FR-015 G5 and FR-003's six-call-expression count, all of which are explicit and
> load-bearing. **Follow the two-literal-calls reading.** The complexity point that sentence was
> making still holds and is still satisfied: all new branching lives in the new renderer, and
> `doctor()` gains **one call, not branches**.

### H-D. Import form is load-bearing on guard G5.

`EgressDestination` is imported **under its own name**:

```python
from specify_cli.tracker.egress_verdict import EgressDestination, tracker_egress_verdict
```

An aliased import (`import … as ED`, or `from specify_cli.tracker import egress_verdict as ev`) makes
each `destination` argument an `Attribute` on the alias and G5 reports non-literal — a **false red**.
Loud rather than silent, but a lost afternoon for anyone who has not been told.

### H-E. The block never consults the on-disk provider.

The provider on disk does **not** determine the destination: `--provider` overrides it **in memory**
(`TrackerService._resolve_saas_backend_for_provider`, `service.py:84-98`) and never rewrites the file.
A provider-conditional rendering would tell an operator with a `beads` binding that `permitted` is in
force while `list-tickets --provider jira` is refused, and tell an operator with a `jira` binding
nothing at all about the local half. **Two rows are what the checkout actually has to say.**

### H-F. "Tracker egress is fine" and "I never looked" must not render identically.

That equivalence is the incident's false-green. Neither may one destination's answer be printed as if
it were both. This is why the block prints **unconditionally, including the permitted case**.

---

## Standing rules — binding on every measurement you take

- **Revalidate every line citation before you trust it (C-011).** Every `file.py:NNN` in this
  prompt was taken at the measurement base **`bb2020fea`** — recorded as `measurement_base_sha` in
  `wps.yaml`, so the drift diff is derivable rather than transcribed:
  `git diff --stat bb2020fea..<your base> -- <the paths you cite>`. Implementation runs on a **later**
  base. Re-derive every citation **by symbol name (`grep`), never by line number**, *before* any step
  that depends on it. **A line that moved is bookkeeping. A symbol that moved *semantically* — a
  changed signature, a relocated gate, a changed default, a new caller — is a re-plan trigger**, and
  the correct response is to stop and re-plan, not to patch the citation and continue. Four drifts
  were already found at `bb2020fea` itself, which is the evidence that this is necessary rather than
  ceremonial.
- **Never pipe a suite whose exit status you intend to trust.** `pytest … | tail` reports `tail`'s
  status and buffers until exit. **Quote the `N passed` line.** An **empty output file is no
  measurement**.
- **A killed run is neither a pass nor a fail.** Re-run it narrowed; do not explain it.
- **Measure in a `git worktree` pinned to a commit — and set `PYTHONPATH=$WT/src`.** The editable
  install hard-codes the **main checkout's** src path, so a worktree run otherwise imports the live
  tree and any "identical results" conclusion is a tautology.
- **Read the failure text, not the tally.**
- **Print the input count alongside any "all checks passed"** — a gate that ran on zero files passes
  vacuously.
- **Red first, and make the red the consequence.** Assert the bytes, not a boolean.
- **Include a positive control that must pass.**
- **Any assertion of absence must establish why the thing would otherwise have happened.**
- **Control your diagnostic** — run any probe against a case whose answer you already know before
  trusting it.
- **Mutations as pytest plugins via `PYTHONPATH`, never source edits**, and never source edits during
  a verification run.
- **Five recorded ways a mutation silently lies** — check each: (1) the architecture moved and the
  patched gate became a redundant second → all-green reads as "your pin is fine"; (2) the reds are
  `TypeError`s from a changed signature, not assertion failures; (3) the mutant hard-codes a value the
  tests **vary** → no-ops for exactly the tests most likely to catch the defect; (4) the branch is
  unreachable on the local interpreter and **live on CI's** (3.11/3.12 vs 3.14) → zero binds means
  *your environment differs*, not *the code is dead*; (5) **`from X import f` rebinds by value** →
  patching the defining module leaves the *deciding* module inert; patch every name a symbol is
  reachable by and report the per-site split.
- **Explicit-path staging.** `git add <paths>`, never `git add -A` — 13 files were lost to a stray
  `add -A` in this lineage.
- **`ruff format` is NOT clean on this repo** (`line-length = 164`); only `ruff check` is meaningful.
  New code must pass `ruff` and `mypy --strict` with no blanket suppressions.
- **One live agent per file.**
- **Known pre-existing failures — do not chase, do not fix in-PR, do not retry to green:**
  `tests/architectural/test_tid251_enforcement.py` (4 tests);
  `test_charter_package_exports::test_charter_package_cold_import_keeps_status_orchestration_out`;
  two `test_safe_commit_cmd::…_3033`;
  `test_charter_io::test_get_mission_id_returns_none_when_meta_json_malformed`;
  `test_doctor_ops::test_sweep_nfr_002_10k_files_under_5s` (wall-clock, fails under load).
  `ModuleNotFoundError: No module named 'typer'` in subprocess daemon tests is environmental.

---

## Subtasks, in execution order

### T032 — Pin the baseline and the detection signal, before writing anything

1. **Record the base SHA** and re-derive every citation in this prompt **by symbol name (`grep`),
   never by line number** (`_render_consent_fault`, `_render_consent_readability`,
   `_CONSENT_FAULT_NOT_ABSENCE`, `_per_project_store_table`, `doctor`). A citation whose line moved is
   a bookkeeping fix; a **symbol that moved semantically** is a **re-plan trigger**.

2. **Measure the detection signal on the pre-change tree**, unpiped, exit status trusted:

   ```
   pytest tests/cli/commands/test_sync_doctor_consent_health_3030.py -q
   ```

   **Quote the `N passed` line** (baseline at `bb2020fea` was `15 passed in 54.64s`; re-derive at your
   base). Then confirm by reading that the assertion at `:366` is
   `assert flat.count("REPAIR THE FILE'S SYNTAX") == 4`. **That 4 is your detection signal for the
   whole WP.**

3. **Confirm the wiring site.** In `src/specify_cli/cli/commands/sync.py`, `doctor()` calls
   `_render_per_project_store(console, issues)` then `_render_consent_readability(console, issues)`
   (at `bb2020fea`: `:5936` and `:5940`, inside `doctor()` at `:5737`, already carrying
   `# noqa: C901`). Your new call goes **immediately after** `_render_consent_readability`.

4. **Confirm the land-alone precondition.** Your change set will contain your two owned files and
   nothing else. If any other file needs touching, **stop and report** rather than folding it in —
   a count over shared output cannot attribute a movement to one of two co-landing changes.

**Exit for T032:** base SHA recorded; citations re-derived by symbol; `test_sync_doctor_consent_health_3030.py`'s
`N passed` line quoted; the `== 4` assertion confirmed by reading; the wiring site located by symbol;
interpreter version recorded.

---

### T033 — Red first: author the new suite against the un-rendered tree

Create `tests/cli/commands/test_sync_doctor_tracker_egress_3108.py`. Write the assertions **before**
the renderer exists and **observe them red**, so the red is the consequence — the block's **absence
from the rendered output** — rather than a boolean.

Build **seven checkouts**, each isolated (isolated `HOME` / `SPEC_KITTY_HOME`), and invoke
`sync doctor` through the CLI runner in each:

| # | Checkout | `LOCAL_SUBPROCESS` row | `HOSTED_SERVICE` row |
|---|---|---|---|
| 1 | `tracker.egress: refused` | refused, **Channel 2** | refused, **Channel 2** |
| 2 | tracker-key **fault** (a near-miss value, e.g. `refuse`) | refused, **Channel 2**, fault text | refused, **Channel 2**, fault text |
| 3 | Channel-1 **recorded refusal**, no tracker key | refused, **Channel 1**, state spelled out | refused, **Channel 1**, state spelled out |
| 4 | Channel-1 **absent (no record)**, no tracker key | refused, **Channel 1**, state spelled out | refused, **Channel 1**, state spelled out |
| 5 | Channel-1 **not consentable** (no `project.uuid`), no tracker key | refused, **Channel 1**, state spelled out | refused, **Channel 1**, state spelled out |
| 6 | `tracker.egress: permitted`, Channel 1 **absent** | **permitted, by Channel 2** | **refused, by Channel 1**, *plus* the recorded grant is a **no-op here** |
| 7 | fully permitted (Channel 1 granted, no tracker key) | permitted | permitted |

Assertions:

1. **14 rows.** Seven checkouts × two destination rows. Assert the row count explicitly and assert the
   block is printed in **all seven** — including the permitted cases. *"Tracker egress is fine" and
   "I never looked" must not render identically.*
2. **Row 6 is the discriminating case.** Checkout 6 renders **two different answers on its two rows**.
   This is the assertion a one-row block cannot satisfy. Do not let it be the only distinguishing
   assertion, but do assert it explicitly.
3. **Field-for-field equality with the enforced verdict** (US7 sc4, SC-014). For each checkout and
   each destination, call `tracker_egress_verdict(root, destination=<the same literal>)` directly and
   assert the rendered row's fields equal the enforced verdict's fields — `refused`,
   `refusing_channels`, `destination`, the Channel-1 state, the Channel-2 state and raw value. **The
   reported answer and the enforced answer are produced by the same function with the same
   destination literal**, and this test is what proves it.
4. **The fault row names its parts** (C-020): for checkout 2, the rendered text names the key, quotes
   the **offending raw value verbatim**, and names **both** legal values `refused` and `permitted`.
5. **The negative pins** (US7 sc5):
   - `"This is NOT a missing consent record"` does **not** appear anywhere in the new block, in any
     of the seven checkouts.
   - The new block contributes **0** to `flat.count("REPAIR THE FILE'S SYNTAX")` — assert that count
     is `0` across all seven of *your* checkouts.
   - The rendered block does not announce a readable file as `UNREADABLE` and does not tell the
     operator to `REPAIR` anything.
6. **Non-vacuity.** Print the number of checkouts rendered and the number of rows asserted alongside
   any "all rows matched" summary. A renderer that ran on zero checkouts passes vacuously.
7. **Control your diagnostic.** Before trusting the row-extraction helper, run it against a rendered
   output whose row content you already know (e.g. checkout 7) and confirm it reports what you expect.
8. **The `root=None` case — asserted, and deliberately OUTSIDE the seven.** Invoke `sync doctor`
   from a directory that is **not** inside any checkout, so `locate_project_root(Path.cwd())`
   returns `None`. Assert: the block **is still printed**; it carries **two** rows; both rows are
   **refused**; both carry the Channel-1 state **`undetermined`** (not `not consentable` — its
   `spec-kitty init` remedy is wrong advice here); and the block does **not** raise, does **not**
   disappear, and does **not** render identically to a permitted checkout.

   **Keep this case out of SC-014's counts.** SC-014 says *seven* checkouts and *fourteen* rows, and
   those two numbers are asserted exactly; this is an **eighth** case, counted and reported
   **separately**, so the 7/14 assertions stay literal. State that separation in the test file, or
   the next reader will "fix" one of the two numbers.

   **Why it must be asserted at all:** without it, the only place `root=None` at `LOCAL_SUBPROCESS`
   is exercised is WP03's unit pin, and this renderer is what makes that cell reachable in
   production. An unasserted reachable cell is how the block ends up raising in the one situation an
   operator runs `doctor` from the wrong directory.

**Run the suite and quote the red.** Every one of the seven checkouts must fail with **the block
absent from the output** — that is the consequence, not a proxy.

**Exit for T033:** the new file exists with all seven checkouts and 14 rows asserted; the run is red;
the red is quoted and is *block absent*, not an incidental error.

---

### T034 — The new renderer

Add a **new** function to `src/specify_cli/cli/commands/sync.py`, placed **beside**
`_render_consent_readability` (not inside it, not routed through `_render_consent_fault`):

```python
def _render_tracker_egress(console_out: Any, issues: list[str]) -> None:
    """Report the tracker-egress verdict the gates enforce (#3108 FR-014, SC-014).

    One row per EgressDestination member — two rows, always, in every checkout.
    ...
    """
```

**The signature takes no `root`, and the two mandated calls need one. Resolve it inside the body,
the way the sibling does.** `_render_consent_readability(console_out: Any, issues: list[str])` —
whose signature this one matches deliberately, because `doctor()` calls them the same way — resolves
its own root at `sync.py:1786`:

```python
repo_root = locate_project_root(Path.cwd())
```

Write **that line** into `_render_tracker_egress`. Do not widen the signature (it would break the
one-call, no-branches wiring in T035), do not thread a root down from `doctor()`, and do not invent
a different resolver — the diagnostic must answer about **the same checkout the readability block
just answered about**, or the two sections in one `doctor` run describe two different projects.

**`locate_project_root(Path.cwd())` returns `None` outside a checkout, and that is a specified case,
not an error path.** It is the reason WP03 pins `root=None` at **both** destinations rather than only
at `HOSTED_SERVICE`. Pass the `None` straight through to both calls — the verdict function never
raises (NFR-003) and answers it with `UNDETERMINED_PROJECT_REFUSAL`'s bytes and a Channel-1 state of
`undetermined`. **Do not guard the block behind `if repo_root is not None:`** — that would make "I am
not in a checkout" and "tracker egress is fine" render identically, which is H-F, the incident's own
false-green. It is asserted in T033 as a **separate case, deliberately outside SC-014's seven** (see
T033 item 8).

Requirements on its body:

1. **Two written-out calls with literal members** — never a loop, never a computed destination
   (H-C, and WP07's guard G5):

   ```python
   root = locate_project_root(Path.cwd())          # may be None; that is a rendered case
   local = tracker_egress_verdict(root, destination=EgressDestination.LOCAL_SUBPROCESS)
   hosted = tracker_egress_verdict(root, destination=EgressDestination.HOSTED_SERVICE)
   ```

2. **Import `EgressDestination` under its own name** (H-D).

3. **Never read the on-disk provider** to decide what to show (H-E). There is no
   `load_tracker_config` call in this renderer for the purpose of choosing rows.

4. **Print unconditionally**, in every checkout, including when both rows are permitted.

5. **Report, never re-derive.** Every field printed comes from the verdict object. Do not compose a
   second message; do not re-classify the Channel-1 state locally. The whole point of FR-003 is that
   the enforced answer and the reported answer cannot disagree.

6. **Row content**, per destination:
   - the destination name;
   - refused / permitted;
   - the **refusing channel(s)** — **all** of them, never just the first, so an operator who clears
     the tracker key is not surprised by a second refusal;
   - for a Channel-1 refusal, the Channel-1 state spelled out (**no record** / **a refusal is
     recorded** / **not consentable, no project identity resolved** / **undetermined — this
     directory is not inside a checkout**) — with wording **distinct per state**, all four of them;
   - for a Channel-2 fault, the offending raw value **verbatim** and **both** legal values (C-020);
   - for Channel 2 `permitted` at `HOSTED_SERVICE`, an explicit statement that **the recorded tracker
     grant is a no-op at this destination** and Channel 1 still decides.

7. **Never** emit `_CONSENT_FAULT_NOT_ABSENCE`'s text, and **never** emit the string
   `REPAIR THE FILE'S SYNTAX` or any substring that would contribute to that count.

8. **Do not extend `CONFIG_FAULT_KINDS`.** It is pinned by exact equality at
   `tests/sync/test_consent_fault_vocabulary_3030.py:261`.

9. **Do not add to `_per_project_store_table`.** It is hard-coded binary and has nowhere to put a
   second *decision*.

10. **Complexity ceiling 15** (`C901` / Sonar `S3776`). If the renderer approaches it, extract a small
    per-row helper — but keep the **two literal call expressions in the renderer itself**, because
    G4 counts enclosing *functions* (exactly five) and *call expressions* (exactly six), and moving a
    call into a helper adds a sixth enclosing function.

11. **Repeated non-trivial literals** appearing ≥3 times (the two legal values, the key path, the
    row labels) are hoisted to named module constants (Sonar `S1192`).

**Exit for T034:** the renderer exists; `grep` confirms no `for` over `EgressDestination` and no
aliased import; `ruff check` and `mypy --strict` clean on `sync.py`.

---

### T035 — Wire it into `doctor()`, adding one call and no branches

In `doctor()` (`sync.py`, at `bb2020fea` `:5737`, already `# noqa: C901`), add the call **immediately
after** `_render_consent_readability(console, issues)`:

```python
_render_consent_readability(console, issues)
# --- 3e. Is tracker egress refused, and by which channel? (#3108 FR-014, SC-014) ---
# Beside the readability block, not inside it: that section's contract is
# readability, not verdict. Two rows, always — one per EgressDestination —
# because the on-disk provider does not determine the destination.
_render_tracker_egress(console, issues)
```

- **One call, no branches.** `doctor()` gains a call; all new branching lives in the renderer. The
  `# noqa: C901` on `doctor()` is pre-existing and must **not** be used as licence to add branching
  there.
- Follow the existing house style for the section comment: the surrounding sections carry a `--- 3x.
  <question> ---` header explaining *why the block sits where it sits*.
- `issues` is appended to with the same strings the block prints, so `doctor`'s summary and the
  section cannot say different things about one verdict — that is the invariant
  `_render_consent_fault` was built around, and it is worth preserving even though you are not
  reusing that function.

**Exit for T035:** the wiring is in place; the new suite from T033 is now **green**; the red-to-green
transition is quoted.

---

### T036 — Exit: the counts, the detection signal, and the quality gates

1. **The new suite, alone, unpiped:**

   ```
   pytest tests/cli/commands/test_sync_doctor_tracker_egress_3108.py -q
   ```

   **Quote the `N passed` line.** Confirm the printed non-vacuity numbers: **7 checkouts, 14 rows**
   — **plus**, reported separately, the `root=None` case's **1 invocation, 2 rows**, which is
   deliberately excluded from the 7/14.

2. **The detection signal — the criterion this WP is judged by:**

   ```
   pytest tests/cli/commands/test_sync_doctor_consent_health_3030.py -q
   ```

   **Quote the `N passed` line and confirm it matches T032's baseline** (`15 passed` at `bb2020fea`).
   And confirm `flat.count("REPAIR THE FILE'S SYNTAX")` at `:366` **is still exactly 4**.

   > **If it moves, the implementation is wrong.** It is a detection signal, not a planned edit. Do
   > not edit that test. Do not weaken its assertion. Go back and find where the new block routed
   > through `_render_consent_fault` or emitted the pinned string.

3. **`CONFIG_FAULT_KINDS` untouched:**

   ```
   pytest tests/sync/test_consent_fault_vocabulary_3030.py -q
   ```

   Quote the `N passed` line. This file must be green and unedited.

4. **Wider blast radius, each with its prediction** (an **unpredicted** movement is a
   **stop-and-attribute event**):

   | Suite | Prediction |
   |---|---|
   | `tests/cli/commands/test_sync_doctor_consent_health_3030.py` | **unchanged** |
   | `tests/sync/test_consent_fault_vocabulary_3030.py` | **unchanged** |
   | `tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py` | **unchanged** |

5. **Quality gates (NFR-005, IC-11):**
   - `ruff check src/specify_cli/cli/commands/sync.py tests/cli/commands/test_sync_doctor_tracker_egress_3108.py`
     — clean. **No blanket `# noqa`**, no per-file ignore additions.
   - `mypy --strict` clean on the changed source, **no `# type: ignore` added to achieve it**.
   - Do **not** run `ruff format` and do not treat a formatting diff as evidence.
   - ≥90 % coverage on the new renderer's branches, from focused tests executing it directly rather
     than relying on the CLI-level suite alone.
   - Complexity of the new renderer ≤ 15; `doctor()` gains one call and zero branches.

6. **Confirm the land-alone necessity holds.** `git status` and `git diff --stat` must show your two
   owned files and **nothing else**. Stage with explicit paths:

   ```
   git add src/specify_cli/cli/commands/sync.py tests/cli/commands/test_sync_doctor_tracker_egress_3108.py
   ```

   **Never `git add -A`.**

7. **Do not chase the known pre-existing failures.** A *newly* encountered pre-existing failure is
   **filed as an issue before being treated as baseline**, confirmed by running the same test against
   the merge-base with `PYTHONPATH=<worktree>/src`.

---

## Exit criterion for WP06

From `plan.md` Stage 6a:

> "*Stage 6a (IC-07):* the new doctor suite green with **14** rows asserted across seven checkouts, at
> least one checkout rendering **different answers on its two rows**; and
> `test_sync_doctor_consent_health_3030.py` still `15 passed` with the count still `4`."

Plus: the specific pin observed **red-then-green** is the new suite's *block absent* red across all
seven checkouts; the change set is two files; `ruff check` and `mypy --strict` clean.

## What to report back

1. The base SHA and the outcome of the citation revalidation.
2. The **red** quoted — the block absent from all seven checkouts — and the green counterpart.
3. The new suite's `N passed` line, with the printed **7 checkouts / 14 rows** non-vacuity numbers.
4. `test_sync_doctor_consent_health_3030.py`'s `N passed` line before and after, and an explicit
   statement that `flat.count("REPAIR THE FILE'S SYNTAX")` is **still exactly 4**.
5. Confirmation that the renderer contains **two literal call expressions and no loop**, that it
   resolves its own root with `locate_project_root(Path.cwd())` inside the body (matching
   `sync.py:1786`) rather than widening its signature, and that `EgressDestination` is imported
   under its own name with the line
   `from specify_cli.tracker.egress_verdict import EgressDestination, tracker_egress_verdict`.
5b. The `root=None` case: block printed, two rows, both refused, both Channel-1 state
   `undetermined`, **counted separately from SC-014's 7/14**.
6. Confirmation that `git diff --stat` shows exactly your two owned files.
7. Any hazard you judged not to apply, and why.

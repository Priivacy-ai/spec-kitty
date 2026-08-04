---
work_package_id: WP07
title: Falsity guards G1-G6, exact and not blind to their own subject
dependencies:
- WP04
- WP05
- WP06
requirement_refs:
- C-002
- C-006
- C-009
- C-010
- C-011
- FR-015
planning_base_branch: bundle-c-tracker-refusal-3108
merge_target_branch: bundle-c-tracker-refusal-3108
branch_strategy: Planning artifacts for this mission were generated on bundle-c-tracker-refusal-3108. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into bundle-c-tracker-refusal-3108 unless the human explicitly redirects the landing branch.
created_at: '2026-08-01T00:20:00+00:00'
subtasks:
- T037
- T038
- T039
- T040
- T041
- T042
phase: Stage 6b - Falsity guards, last
history:
- at: '2026-08-01T00:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_tracker_egress_guards_3108.py
create_intent:
- tests/architectural/test_tracker_egress_guards_3108.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/architectural/test_tracker_egress_guards_3108.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '3108'
---

# Work Package Prompt: WP07 – Falsity guards G1–G6, exact and not blind to their own subject

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and
behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## Objective

Write **six** AST falsity guards over `src/` that make the properties a future change can silently
break **structural** rather than test-dependent. Each guard asserts **exact membership and an exact
count** — never `<=` — prints and asserts its own **non-zero input count**, and is **killed by
synthetic mutated source held in the test**, never by a source edit.

The bar is higher than "the guards pass". It is: **a guard that survives its own mutants while blind
to its subject is worse than no guard**, because it converts an unexamined property into an examined
one that is false. This WP exists because that exact failure was measured.

## Owned files — a hard boundary

You may write **exactly one file**:

- `tests/architectural/test_tracker_egress_guards_3108.py` (**new**)

You may **not** edit any source file, any other test file, `_baselines.yaml`, or any dossier file.
**No source is edited during a verification run** — that is a standing rule, and for a guard whose
subject *is* the source tree it is the rule that shapes the whole design (see H-D).

In particular:

| File | Why you must not touch it |
|---|---|
| `src/specify_cli/tracker/*.py`, `src/specify_cli/cli/commands/sync.py` | WP03–WP06 own them. They are your **subject**, read-only. |
| `tests/architectural/test_egress_consent_boundary.py` | **Untouched.** `local_service.py` holds **zero** HTTP sinks (measured: 0, against a control of 8 in `saas_client.py`, over 1198 scanned files) and therefore **cannot** be allowlisted — `test_every_listed_file_still_holds_a_sink` (`:792-805`) deletes entries that guard nothing. **No `_baselines.yaml` bump** (`egress_allowlist_files: 28`) is needed or permitted (C-010). The same applies to the new `egress_verdict.py`. |

**One live agent per file.**

## Why this WP lands last

From `plan.md` Stage 6 and IC-08:

> "**Why the guards last:** G4's exact membership (five enclosing functions, six call expressions) and
> G5's literal-member set are **only satisfiable once every call site exists**, and a guard written
> earlier would be edited by every later stage. **A guard whose own history is a chain of edits is a
> guard nobody can trust.** *Unprovable otherwise:* that the guard's counts are a property of the
> architecture rather than of the guard's most recent revision."

WP07 depends on **WP04** (three local gates), **WP05** (the hosted gate) and **WP06** (the doctor
renderer). All five enclosing call sites and all six call expressions must exist before you start. If
any is missing, **stop and report** — do not lower a count to make a guard pass.

## What you may assume is already true

- `src/specify_cli/tracker/egress_verdict.py` exists, defining `EgressDestination` (closed two-member
  enum: `LOCAL_SUBPROCESS`, `HOSTED_SERVICE`) and
  `tracker_egress_verdict(root: Path | None, *, destination: EgressDestination)`.
- `LocalTrackerService.sync_pull`, `.sync_push` and `.sync_run` each call it as their **first
  executable statement**, ahead of `self._load_runtime()`, each passing
  `destination=EgressDestination.LOCAL_SUBPROCESS` as a literal, **written out at each site — there
  is no `_require_egress` helper**.
- `SaaSTrackerClient._request` calls it passing `destination=EgressDestination.HOSTED_SERVICE`
  **unconditionally**.
- `sync doctor`'s new renderer calls it **twice**, once per destination, each with a literal member —
  **not a loop**.
- `factory.SUPPORTED_PROVIDERS == ("beads", "fp")` and `build_connector` has exactly **one** call site
  tree-wide, inside `LocalTrackerService._build_engine`.

## Requirements this WP satisfies

**FR-015 — six falsity guards, repo-wide, exact-membership, non-vacuous, and not blind to their own
subject.** Quoted in the subtasks below, guard by guard.

**C-002** — "any implementation that computes the destination from a configuration read is out of
contract, regardless of the answers it happens to give … **G5 pins this structurally**; US5 scenario 4
pins it behaviourally."

**C-006 — falsifying preconditions**, of which three are guarded: (1) `build_connector` stays
restricted to `("beads", "fp")` [G1]; (2) `_build_engine` stays the sole connector-construction site
and its callers stay exactly the three gated methods [G2, G3]. Precondition (3) — *the tracker path
stays operator-invoked* — is **prose only; no executable guard exists for it**, and a re-check is
required of any Mission adding an automatic caller. Do not invent a guard for it here.

**C-009 — Bundle B moves this Mission's call sites.** "`tracker_egress_verdict`, `EgressDestination`,
Channel 2's resolver, the module-local sentinel and all five call sites move with it. Recorded so the
move is a rename rather than a rediscovery — and so **G4's exact-membership assertion (5 enclosing
functions, 6 call expressions) and G5's literal-member assertion are understood as things Bundle B
must update, not things Bundle B may let fall to zero.**"

**C-010** — `local_service.py` cannot be egress-allowlisted and must not be added.

**Success criterion — SC-017**, quoted in full:

> "All **six** falsity guards (FR-015 G1–G6) assert exact membership and an exact count, print a
> non-zero input count, and each fails against **synthetic mutated source** passed to the guard's
> analyzer callable — never a source edit — with the killed-pin count reported. **G4 and G5 each kill
> three mutants**: (i) a call site whose `destination` is a name bound from a config read; (ii) a call
> site with the two literals swapped; and (iii) **a sixth call site written module-qualified**
> (`ev.tracker_egress_verdict(…, destination=ev.EgressDestination.…)`), which is the form measured to
> pass an `ast.Name`-only matcher. **G6 kills one**: a provider read reintroduced into
> `egress_verdict.py`. **A guard that kills only mutants (i) and (ii) has not been proven — it has
> been proven against the two mutants that share its blind spot.**"

> **One correction to SC-017's wording, carried here because the code decides it.** SC-017 describes
> G4's and G5's three mutants with one shared list, item (ii) of which is *"a call site with the two
> literals swapped"*. **That mutant kills G5 and cannot kill G4.** An in-place swap changes no
> enclosing function and no call-expression count, so G4 — which asserts exactly those two numbers —
> passes against it. G4's third mutant is therefore an **ADDED sixth call site with a swapped
> literal** (which moves both counts); G5's stays the **in-place** swap (which moves the per-site
> mapping). Both guards still kill **three each**, as SC-017 requires. The per-guard tables in T040
> and T041 are authoritative over the shared sentence.

---

## Measured hazards — carried verbatim, not summarised

### H-A. The guards must resolve both `ast.Name` and `ast.Attribute` func nodes.

Measured. From `spec.md` FR-015 and `plan.md` Stage 6:

> "A sixth, **ungated** call site written module-qualified —
>
> ```python
> from specify_cli.tracker import egress_verdict as ev
> ev.tracker_egress_verdict(root, destination=ev.EgressDestination.LOCAL_SUBPROCESS)
> ```
>
> — **passes both G4 and G5**, with G4's input count merely *rising* to 4, because a matcher
> inspecting only `ast.Name` func nodes never sees it. **Both previously specified G5 mutants keep
> the `ast.Name` form, so a guard with this hole kills 2/2 and reports itself healthy.** Every
> call-site guard therefore resolves **both `ast.Name` and `ast.Attribute` func nodes**, and G4 and
> G5 each carry a **third mutant in module-qualified form**. A guard that survives its own mutants
> while blind to its subject is worse than no guard: it converts an unexamined property into an
> examined one that is false."

**The module-qualified mutant *is* the detection** (R-20). If it fails to kill, your matcher is blind.

### H-B. Count both things. Never `<=`.

- **Exactly 5 enclosing functions**: `LocalTrackerService.sync_pull`, `.sync_push`, `.sync_run`,
  `SaaSTrackerClient._request`, and `sync doctor`'s renderer.
- **Exactly 6 call expressions**: the doctor renderer calls **twice**, once per destination row.

From `plan.md` *Open Items* 11: "An implementer who reads 'five call sites' as 'five call expressions'
will write a doctor renderer that loops over `EgressDestination`, which G5 then rejects because the
loop variable is a `Name`, not a literal member. **Both assertions are deliberate and both are exact;
do not collapse them into one number.**"

And from FR-015: "**never `<=`, which passes on a zero-call scan, which is exactly what happens after
Bundle B moves a file**". A `<=` assertion is not a weaker guard; it is a guard that reports healthy
after its subject has been deleted (R-07).

### H-C. The body needs its own guard — and its expected set is empty, which is why the input count is load-bearing.

From `spec.md` FR-015 G6 and `plan.md` Stage 6:

> "**G6 — the body, not just the call sites.** G5 guards *where the destination comes from*; the
> original defect lived **inside** the verdict. A future change reading *'if the on-disk provider is
> local, treat this as local regardless of the argument'* passes G5 at all six expressions, and only
> one behavioural test (SC-005a) would catch it. G6 asserts that
> `src/specify_cli/tracker/egress_verdict.py` contains **no** reference to `provider`,
> `LOCAL_PROVIDERS` or `SAAS_PROVIDERS`, and **no `.provider` attribute access on a
> `load_tracker_config` result** — exact membership, **expected set empty**, with the printed
> non-zero input count being **the number of AST nodes scanned** (an empty-set assertion over zero
> nodes is exactly the vacuity the rule exists to prevent). One mutant reintroduces a provider read."

Detection signal for the defect this guards (R-21): **G6 red; or SC-005a red with G5 green — the
signature of a body-side derivation.**

### H-D. Each guard is an analyzer callable, invoked twice. Nothing on disk is edited.

From `plan.md` Stage 6, stated once and applying to all six:

> "The plan forbids source edits during a verification run and requires mutations to be
> `PYTHONPATH`-injected plugins; neither instruction tells an implementer how to mutate a guard whose
> subject *is* the source tree. **The rule: each guard is written as an analyzer callable taking
> source text or a root path** and returning its findings, and its test invokes it **twice** — once
> against `src/` (the real run, reporting the real input count) and once against **synthetic mutated
> source held in the test string** (the mutant run, reporting the killed-pin count). **Nothing on disk
> is touched.** Without this stated, an implementer at this stage either breaks the no-source-edits
> rule or quietly ships the guards with no mutants at all."

### H-E. What G5's clauses are actually worth.

> "Its set-equality clause — *'the literal members passed are exactly the two'* — carries almost
> nothing alone, because the doctor renderer supplies both members by itself. **The per-site mapping
> is the load-bearing half**: `_request` always `HOSTED_SERVICE`, the three local sites always
> `LOCAL_SUBPROCESS`. **That is the clause whose mutant must kill.**"

### H-F. The destination is a parameter because deriving it reopens `#3030`.

This is the property G5 exists to preserve, and it is worth stating so you do not weaken the guard
under pressure. `saas_client._request` passes `HOSTED_SERVICE` and is structurally incapable of
anything else — it must **never** be derived. Measured:

```
PRECONDITION on-disk provider : 'beads'
SUBJECT backend class         : SaaSTrackerService
SUBJECT in-memory cfg.provider: 'jira'
SUBJECT on-disk cfg.provider  : 'beads'   <-- what a config-reading verdict() would have seen
CONTROL (disk=jira) backend   : SaaSTrackerService
NEGATIVE CONTROL              : TrackerServiceError raised for 'beads' (the probe discriminates)
```

`TrackerService._resolve_saas_backend_for_provider` (`service.py:84-98`) overrides the on-disk
provider **in memory** — which is exactly why deriving the destination would make
`tracker.egress: permitted` an **affirmative grant to spec-kitty's hosted service with Channel 1
absent**.

### H-G. No guard *decides* polarity for a new transport, and G4 only prompts.

From `data-model.md` §2: G5 **passes** when a new transport reuses `HOSTED_SERVICE` — the argument is
still an `Attribute`, the literal set is still the two members, and the per-site clause names only the
four existing sites. What fires is **G4**, and it fires only as a *prompt* whose obvious resolution is
to edit the guard. The actual requirement lives in the enum's docstring (FR-017). **Do not try to
build a guard that catches a repointed member** — record in your file's module docstring that neither
G4 nor G5 substitutes for that operator decision, so the next reader does not mistake a passing G5 for
an answered question.

### H-H. Import form is load-bearing, and a wrong import form produces a false red.

`EgressDestination` is imported under its own name at every call site. An aliased import makes each
`destination` argument an `Attribute` on the alias and **G5 reports non-literal — a false red**. Loud,
not silent, but write the failure message so the next person reads "aliased import?" in the first
line rather than losing an afternoon.

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

### T037 — The analyzer harness: callables, dual invocation, shared matcher, input counts

Create `tests/architectural/test_tracker_egress_guards_3108.py` with the scaffolding every guard
shares. **Write this first**, because getting it wrong makes all six guards blind in the same way.

1. **Every guard is an analyzer callable**, not an inline test body. Two shapes:
   - **root-path analyzers** (G1–G5): `def _analyze_x(root: Path) -> Findings` scanning `.py` files
     under `src/`, and a sibling entry point taking **source text** so the same analyzer can be run
     against a synthetic module held in the test string.
   - **source-text analyzers** (G6): `def _analyze_x(source: str) -> Findings`.

   Each returns a structured `Findings` object carrying, at minimum: the exact membership set it
   found, the counts it counted, and **the input count** (files scanned, or AST nodes visited).

2. **Every guard's test invokes its analyzer twice** — once against the real `src/` tree, once
   against **synthetic mutated source held in the test**. Report the two results separately: the
   **real input count** and the **killed-pin count**. **Nothing on disk is edited.**

3. **The shared call matcher resolves both `ast.Name` and `ast.Attribute` func nodes** (H-A). A call
   is a `tracker_egress_verdict` call if:
   - `node.func` is `ast.Name` with `id == "tracker_egress_verdict"`; **or**
   - `node.func` is `ast.Attribute` with `attr == "tracker_egress_verdict"` (whatever the value
     expression is — `ev.tracker_egress_verdict`, `egress_verdict.tracker_egress_verdict`, …).

   The same both-forms rule applies to `build_connector` (G2) and `_build_engine` (G3).

   **Control your diagnostic:** before trusting the matcher, run it against a synthetic module you
   have written to contain **exactly one `ast.Name` call and exactly one `ast.Attribute` call**, and
   assert it finds **2**. A matcher you have not falsified is not a matcher.

4. **Enclosing-function resolution.** Walk the module AST maintaining a stack of
   `FunctionDef`/`AsyncFunctionDef`/`ClassDef` nodes so a call can be attributed to a **qualified
   name** (`LocalTrackerService.sync_push`, `SaaSTrackerClient._request`, the doctor renderer's
   function name). G4's membership set is over these qualified names.

5. **Input counts are printed and asserted non-zero.** Every guard prints, next to any "all checks
   passed", the number of files scanned (or AST nodes visited) **and** the interpreter version
   (`sys.version`). Record the interpreter version because *"a zero count is a statement about the
   environment, not about the code"* (R-13, mutation-lie #4).

6. **Module docstring.** State: (a) that these are analyzer callables invoked twice and that no source
   is edited; (b) that the matcher resolves both `ast.Name` and `ast.Attribute` func nodes and why
   (the measured module-qualified blind spot); (c) that **neither G4 nor G5 decides polarity for a new
   transport** — that decision lives in `EgressDestination`'s own docstring (H-G); (d) that
   **Bundle B must update these counts, not let them fall to zero** (C-009); (e) that an **aliased
   import of `EgressDestination` produces a false red on G5** (H-H).

**Exit for T037:** the harness exists; the matcher's own falsification probe (one `Name` call + one
`Attribute` call → 2) passes; input-count printing works and is non-zero on `src/`.

---

### T038 — G1 and G2: the connector perimeter

**G1** — `set(factory.SUPPORTED_PROVIDERS) == {"beads", "fp"}`.

> "so `LocalTrackerService` cannot become a second, differently-gated route to a third party."

- Exact set equality. Read it from the source (AST or import), print the set found and the input count.
- C-006 note to carry in the test's docstring: *"Note what this precondition no longer carries."* The
  earlier revision called it the sharpest failure the Mission could have, because a widened
  `SUPPORTED_PROVIDERS` would have made a **config-derived** polarity mis-classify a hosted
  destination as local. With the destination supplied as a literal by each call site, **that failure
  mode is structurally impossible and G1 now guards only the gate-divergence half. The sharpest
  failure moved, and it is guarded by G5.**
- **Mutant:** a synthetic `factory` source with a third provider. Must kill.

**G2** — the set of `build_connector` call sites in `src/` is exactly
`{local_service.LocalTrackerService._build_engine}`, **count exactly 1**.

- Measured: exactly one call site tree-wide.
- Exact membership **and** exact count. **Never `<=`.**
- Matcher resolves both `ast.Name` and `ast.Attribute` func forms.
- **Mutants:** (i) a synthetic second `build_connector` call in another function; (ii) the same
  written module-qualified (`factory.build_connector(...)`). Both must kill.

**Exit for T038:** G1 and G2 green against `src/` with printed non-zero input counts; each killed by
its mutants with the killed-pin counts reported.

---

### T039 — G3: the gate is the first *executable* statement of exactly three methods

**G3** — the set of `_build_engine` callers in `local_service.py` is exactly
`{sync_pull, sync_push, sync_run}`, and in each **the gate call is the first executable statement of
the method body**.

From `plan.md` *Open Items* 7:

> "An AST check must **tolerate a docstring as the first *node*** while still requiring the gate to be
> the first ***executable*** statement. Minor, but a naive implementation will either reject a
> docstring or accept a statement before the gate."

Implementation rules:

1. Membership over `_build_engine` callers is **exact**; count exactly 3; never `<=`.
2. For each of the three methods, walk `body`; skip a leading `ast.Expr` whose value is an
   `ast.Constant` of type `str` (the docstring); **the next node must contain the
   `tracker_egress_verdict` call**. Nothing else is tolerated — no logging line, no local variable
   assignment, no `if TYPE_CHECKING` shim.
3. **No `_require_egress` helper may stand in for it.** FR-003: "a helper would let G3's 'first
   statement' property be satisfied by a call to the helper, **which stops pinning
   `tracker_egress_verdict` at all**". So G3 asserts the first executable statement contains a call
   matched by the **`tracker_egress_verdict` matcher**, not merely "some call".
4. This guard is the structural half of R-14 — *the gate is quietly moved back to `_build_engine` by a
   later reader, because it produces no egress and therefore looks harmless*. Carry C-018's sentence
   in the test docstring: moving it back reintroduces, on a refused command, **a machine-global
   credential-store read and a `TrackerSqliteStore` construction that `mkdir`s and creates a SQLite
   file with three tables** (`store.py:278-281`).

**Mutants (all synthetic source):** (i) a fourth caller of `_build_engine`; (ii) a method whose gate
call is preceded by a harmless-looking statement; (iii) a method whose first executable statement is a
call to a `_require_egress`-style helper rather than `tracker_egress_verdict`. All must kill. The
**positive control**: a method whose body is `docstring → gate → rest` must **pass**.

**Exit for T039:** G3 green with a printed non-zero input count; the docstring-tolerance positive
control passes; all three mutants kill.

---

### T040 — G4: five enclosing functions, six call expressions, both exact

**G4** — from FR-015:

> "the set of **enclosing functions** containing a `tracker_egress_verdict` call in `src/` is exactly
> the **five** named in FR-003 — `sync_pull`, `sync_push`, `sync_run`, `SaaSTrackerClient._request`,
> and `sync doctor`'s renderer — count exactly **5**; and the number of **call expressions** is
> exactly **6**, the extra one being the doctor's second destination row. **Both are exact.**"

> *"The rejected draft said 'exactly three' while its own FR-001 demanded three local sites, FR-016 a
> fourth and FR-014 a fifth; the number was arithmetically impossible and was repeated five times in
> the plan."* — do not repeat that class of error: **derive both numbers from the tree and assert both
> explicitly.**

Implementation rules:

1. **Two separate assertions**, never collapsed: `len(enclosing_functions) == 5` with exact
   membership, and `len(call_expressions) == 6`.
2. **Never `<=`.** A `<=` passes on a zero-call scan — which is what happens after a sibling Mission
   moves the file (R-07, C-009).
3. Membership is over **qualified** names so a same-named function elsewhere cannot satisfy it.
4. Print the input count (files scanned) and assert it non-zero.
5. Failure message: name the expected five, the found set, the symmetric difference, and the two
   counts. Add the line *"If Bundle B moved these call sites, update this membership set — do not let
   it fall to zero."*

**Three mutants, all synthetic source (SC-017):**

| # | Mutant | Must kill because |
|---|---|---|
| i | **an added** call site whose `destination` is a **name bound from a config read** | it is an extra enclosing function **and** an extra call expression: 6 → 7 and 5 → 6, and both of G4's exact counts move |
| ii | **an ADDED sixth call site whose two literals are swapped** relative to its enclosing function's correct polarity — e.g. a new local-side function passing `HOSTED_SERVICE` | 6 → 7 enclosing functions and 6 → 7 call expressions. **Note the correction, and do not undo it.** The obvious reading — *"swap the two literals at the existing sites"* — **cannot kill G4**: swapping literals in place leaves the enclosing-function set and both counts **exactly unchanged**, so G4 passes and the mutant reports the guard healthy. Per-site polarity is **G5's** clause, and G5 kills the in-place swap (its own mutant ii). G4's third kill must therefore be an **addition**, not a permutation. |
| iii | **a sixth call site written module-qualified** — `from specify_cli.tracker import egress_verdict as ev` … `ev.tracker_egress_verdict(root, destination=ev.EgressDestination.LOCAL_SUBPROCESS)` | **this is the one a naive `ast.Name`-only matcher passes, with the input count merely *rising*.** A guard that kills only (i) and (iii) *"has been proven against the two mutants that share its blind spot."* |

> **If you find yourself unable to make a mutant kill, the answer is never to lower the killed-pin
> count.** SC-017 says G4 and G5 kill **three each**, and the three above are three *different*
> defects, not three spellings of one. A mutant that cannot kill the guard it is assigned to is a
> **specification error in this prompt** — report it, do not absorb it by writing `2/3` and moving
> on. (Mutants ii and iii differ: ii is an added site with the *wrong polarity for its position*;
> iii is an added site in a *syntactic form the matcher may not see at all*. Both are additions,
> and both must be present.)

**Exit for T040:** G4 green against `src/` — exactly 5 enclosing functions and exactly 6 call
expressions, both printed — with a non-zero input count; **all three mutants kill**, killed-pin count
reported as 3/3.

---

### T041 — G5: every `destination` is a literal member, and the per-site mapping holds

**G5** — from FR-015:

> "every `tracker_egress_verdict` call expression in `src/` passes `destination=` as an **`Attribute`
> node on `EgressDestination`** — a literal member — and **no call site derives it from a config
> read**: the guard asserts that no call expression's `destination` argument is a `Name` or `Call`
> node, and that the set of literal members passed is exactly `{LOCAL_SUBPROCESS, HOSTED_SERVICE}`
> with **`_request`'s always `HOSTED_SERVICE` and the three local sites' always `LOCAL_SUBPROCESS`**.
> **This is what converts 'polarity follows the destination' from a remembered rule into a
> `mypy`-checkable, guardable property**, and it is the reason the destination is a required
> keyword-only parameter rather than a defaulted one."

Implementation rules, in the order of their worth (H-E):

1. **The load-bearing clause — the per-site mapping.** Assert, per qualified call site:
   - `SaaSTrackerClient._request` → **always `HOSTED_SERVICE`** (and only that);
   - `LocalTrackerService.sync_pull` / `.sync_push` / `.sync_run` → **always `LOCAL_SUBPROCESS`**;
   - the doctor renderer → **exactly one of each**, one call per destination.

   *"That is the clause whose mutant must kill."*
2. **The node-shape clause.** For all six call expressions, the `destination` keyword argument's value
   node is an `ast.Attribute` whose `attr` is a member name and whose value resolves to
   `EgressDestination`. **No `ast.Name`. No `ast.Call`.** A `Name` is what a loop variable or a
   config-derived local looks like; a `Call` is what a derivation looks like.
3. **The set-equality clause.** The set of literal members passed across all six is exactly
   `{LOCAL_SUBPROCESS, HOSTED_SERVICE}`. Keep it — but record in the test docstring that *"it carries
   almost nothing on its own, because the doctor renderer supplies both members by itself."*
4. **The matcher resolves both `ast.Name` and `ast.Attribute` func nodes** for the call itself
   (H-A) — that is orthogonal to clause 2, which is about the *argument*.
5. **`destination` is keyword-only**, so the argument is always found in `node.keywords`. A call with
   `destination` positional is a `mypy` error before it is a guard error; assert `node.keywords`
   carries it and fail loudly if it does not.
6. Print the input count; assert it non-zero; report the interpreter version.
7. Failure message begins with the false-red hint: *"If `EgressDestination` was imported under an
   alias, this is a false red — import it under its own name (FR-015 G5, `data-model.md` §2)."*

**Three mutants, all synthetic source (SC-017):**

| # | Mutant | Kills which clause |
|---|---|---|
| i | `destination` is a **name bound from a config read** (`dest = _dest_from_config(root)` … `destination=dest`) | clause 2 — `Name` node |
| ii | the **two literals swapped IN PLACE**: `_request` passing `LOCAL_SUBPROCESS`, a local gate passing `HOSTED_SERVICE`, with **no site added or removed** | clause 1 — **the per-site mapping**, and this is the clause that carries G5. **This mutant is the exact defect that would reopen `#3030`.** It is deliberately an in-place swap here, because G5's per-site clause is the only guard clause that can see it: it moves **no count**, which is exactly why **G4's** third mutant had to become an *added* site instead (see T040). Two guards, two different mutants, one shared literal-swap idea — do not copy one into the other. |
| iii | **a sixth call site written module-qualified** — `ev.tracker_egress_verdict(…, destination=ev.EgressDestination.LOCAL_SUBPROCESS)` | the matcher's blind spot. **This is the specific pin `plan.md` names as the one to observe red-then-green.** |

**Positive control:** the real `src/` tree must **pass** G5 in the same run. Without it, three killing
mutants prove only that the guard fails on something.

**Exit for T041:** G5 green against `src/` with a printed non-zero input count; all three mutants kill,
killed-pin count reported as 3/3; **the module-qualified mutant observed red-then-green** (red when
the matcher is `ast.Name`-only — you may demonstrate this by running your analyzer with the
`ast.Attribute` branch disabled *in a test-local copy of the matcher*, never by editing source).

---

### T042 — G6: the body, with an empty expected set and an AST-node input count

**G6** — from FR-015:

> "the verdict function must not re-derive the destination in its own body. G5 guards the call sites;
> the original defect lived in the *body*, and a future change reading *'if the on-disk provider is
> local, treat this as local regardless of the argument'* passes G5 at all six expressions. G6 asserts
> that `src/specify_cli/tracker/egress_verdict.py` contains **no** reference to `provider`,
> `LOCAL_PROVIDERS` or `SAAS_PROVIDERS`, and **no `.provider` attribute access on a
> `load_tracker_config` result** — exact membership, and the expected set is **empty**, with the
> **printed non-zero input count being the number of AST nodes scanned** (an empty-set assertion over
> zero nodes is precisely the vacuity the rule exists to prevent)."

Implementation rules:

1. A **source-text analyzer**: `def _analyze_verdict_body(source: str) -> Findings`.
2. Findings = every offending reference, each with its AST node type and line, so the failure message
   names *what* it found rather than asserting a bare `== set()`.
3. Offences: any `ast.Name` with `id` in `{"provider", "LOCAL_PROVIDERS", "SAAS_PROVIDERS"}`; any
   `ast.Attribute` with `attr == "provider"`; any `ast.Attribute` with `attr == "provider"` whose
   value traces to a `load_tracker_config(...)` result (the specific form named in the requirement —
   assert it explicitly as well as via the general `.provider` rule, so the requirement's own wording
   is pinned).
4. **Expected set is empty** — and therefore **the input count is the whole proof**. Print and assert
   `nodes_scanned > 0`, and print the file's byte length beside it. *An empty-set assertion over zero
   nodes is exactly the vacuity this rule exists to prevent.*
5. **One mutant:** synthetic `egress_verdict.py` source that reintroduces a provider read — e.g.

   ```python
   cfg = load_tracker_config(root)
   if cfg.provider in LOCAL_PROVIDERS:
       destination = EgressDestination.LOCAL_SUBPROCESS
   ```

   Must kill, and the failure must name `provider`, `LOCAL_PROVIDERS` and the `.provider` access.
6. **Positive control:** the real `egress_verdict.py` passes with a non-zero node count printed.
7. Test docstring carries R-21's detection signal: **"G6 red; or SC-005a red with G5 green — the
   signature of a body-side derivation."**

**Then close out the WP:**

8. **Run the guard suite, unpiped, exit status trusted:**

   ```
   pytest tests/architectural/test_tracker_egress_guards_3108.py -q
   ```

   **Quote the `N passed` line.** Report, per guard: the **real input count**, the **membership set**,
   the **exact counts**, and the **killed-pin count** — **G4 and G5 three each, G6 one**, G1/G2/G3
   their own.

9. **Run the wider architectural sweep** and apply the known-red roster (C-013) without chasing it:

   ```
   pytest tests/architectural/ -q
   ```

   Quote the summary line. The four `test_tid251_enforcement.py` failures and the rest of the roster
   are **not yours**. Confirm no *new* red is attributable to your file.

10. **Confirm `tests/architectural/test_egress_consent_boundary.py` is untouched and green**, and that
    **no `_baselines.yaml` bump** was made (`egress_allowlist_files: 28` unchanged). C-010:
    `local_service.py` and the new `egress_verdict.py` hold zero HTTP sinks and **cannot** be
    allowlisted — `test_every_listed_file_still_holds_a_sink` deletes entries that guard nothing.

11. **Quality gates:** `ruff check` clean on your file, no blanket `# noqa`; `mypy --strict` clean, no
    `# type: ignore` added. Do not run `ruff format`. Complexity of each analyzer ≤ 15 — extract
    per-guard helpers rather than one large visitor.

12. **Explicit-path staging:**

    ```
    git add tests/architectural/test_tracker_egress_guards_3108.py
    ```

    **Never `git add -A`.** `git diff --stat` must show exactly one file.

---

## Exit criterion for WP07

From `plan.md` Stage 6b:

> "*Stage 6b (IC-08):* all **six** guards green, each **printing** its non-zero input count, and each
> **killed** by its mutants with the killed-pin count reported — **G4 and G5 by three each**
> (config-derived name, swapped literals, module-qualified call site), **G6 by one** (a reintroduced
> provider read). **The specific pin observed red-then-green: G5 under the module-qualified mutant**,
> because that is the one a naive matcher passes."

Plus: `tests/architectural/test_tracker_egress_guards_3108.py` green with its `N passed` line quoted;
G4 asserting **exactly 5 enclosing functions and exactly 6 call expressions**, never `<=`; the change
set is one file.

## What to report back

1. Per guard: the **real input count**, the **membership set found**, the **exact counts**, and the
   **killed-pin count** (G4 3/3, G5 3/3, G6 1/1).
2. The **G5 module-qualified mutant** observed red-then-green, quoted — this is the specific pin.
3. G6's **AST-node count** printed beside its empty expected set, with the positive control.
4. The `N passed` line for your suite and for `tests/architectural/` (with the known-red roster
   identified and *not* chased).
5. Confirmation that `test_egress_consent_boundary.py` is untouched, green, and that
   `_baselines.yaml` was not bumped.
6. Confirmation that `git diff --stat` shows exactly one file.
7. Any hazard you judged not to apply, and why — in particular, note explicitly that C-006
   precondition (3), *the tracker path stays operator-invoked*, is **prose only with no executable
   guard**, and that you did not invent one.

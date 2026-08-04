---
work_package_id: WP04
title: The local gate, its bind preservation, and the CHANGELOG break entry
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- C-011
- C-012
- C-018
- C-021
- FR-001
- FR-011
- FR-012
- FR-013
- FR-017
- NFR-001
- NFR-002
- NFR-004
- NFR-005
planning_base_branch: bundle-c-tracker-refusal-3108
merge_target_branch: bundle-c-tracker-refusal-3108
branch_strategy: Planning artifacts for this mission were generated on bundle-c-tracker-refusal-3108. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into bundle-c-tracker-refusal-3108 unless the human explicitly redirects the landing branch.
created_at: '2026-08-01T00:20:00+00:00'
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
- T027
phase: Stage 4 - The local gate, the breaking change
history:
- at: '2026-08-01T00:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks-packages
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tracker/local_service.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/tracker/local_service.py
- src/specify_cli/cli/commands/tracker.py
- tests/sync/tracker/test_local_service.py
- CHANGELOG.md
role: implementer
tags: []
task_type: implement
tracker_refs:
- '3108'
---

# Work Package Prompt: WP04 – The local gate

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its
guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## Objective

Close **Gap B** — the `beads`/`fp` path is ungated entirely. `src/specify_cli/tracker/local_service.py`
holds **zero** consent references today; a committed `sync.enabled: false` does not stop it shipping
issue titles as argv of an operator-named executable. This WP installs the verdict as the **first
executable statement** of `sync_pull`, `sync_push` and `sync_run`, ahead of `_load_runtime`, carries
the committed decision through `LocalTrackerService.bind`, amends the three docstrings this Mission
falsifies, and writes the Breaking Changes entry **in the same commit as the break**.

**Done** = WP01's refusing acceptance pins for the **local** destination flip red → green; the
Stage-1 positive controls stay green; `TestSyncOperations` is green with a **one-line** fixture
repair; and `CHANGELOG.md` carries the Breaking Changes entry.

**This is the breaking change.** Deny-on-absence of both channels means **every existing `beads`/`fp`
binding stops working on upgrade** unless its project records a decision at one of the two channels.
That cost is a deliverable (FR-013), not a footnote.

---

## Boundaries — what this WP may touch

**Owned files — the only files you may edit:**

- `src/specify_cli/tracker/local_service.py`
- `src/specify_cli/cli/commands/tracker.py` (**docstrings only — no behavioural change**)
- `tests/sync/tracker/test_local_service.py`
- `CHANGELOG.md`

**Hard boundary.** You may not edit files another WP owns:

- **`tests/sync/tracker/test_tracker_egress_refusal_3108.py` is WP01's.** Its refusing pins are the
  tests you make green. **If one of them is wrong, you do not fix it here** — report it and let WP01's
  owner change it. You may run it as often as you like; you may not edit it.
- `src/specify_cli/tracker/config.py`, `service.py`, `saas_service.py` (WP02);
  `src/specify_cli/tracker/egress_verdict.py` (WP03);
  `src/specify_cli/tracker/saas_client.py` (WP05);
  `src/specify_cli/cli/commands/sync.py` (WP06);
  `tests/architectural/test_tracker_egress_guards_3108.py` (WP07);
  `docs/migrations/**` (WP08).
- `src/specify_cli/tracker/factory.py` is **unchanged** — pinned by guard G1
  (`set(SUPPORTED_PROVIDERS) == {"beads", "fp"}`).

**Dependencies — what you may assume is already true:**

- **WP01** — `tests/sync/tracker/test_tracker_egress_refusal_3108.py` exists, its consenting controls
  are green on the un-gated tree (push captures **exactly 3** argv with the sentinel verbatim; the
  unseeded variant captures **1**), and its refusing pins for the local destination are **red**. Its
  bind-counter wrapper is already written against the name you are about to bind.
- **WP02** — `TrackerProjectConfig` has an `egress` field in `_KNOWN_KEYS` carrying the raw value plus
  a derived fault; the module-local absence sentinel is **`EGRESS_ABSENT`** in `tracker/config.py`;
  a `bind` plants no null; preservation is green **on disk** at A3, B1, B2, C and D, and asserted at
  the **unit level** at A2 and A4; `TrackerService.bind`'s local branch (`service.py:163`) now hands
  `LocalTrackerService` the **loaded** config rather than an empty one.

  > **What WP02 could NOT deliver, and why it lands on you.** `LocalTrackerService.bind`
  > (`local_service.py:47-63`) **never reads `self._config`** — it builds a fresh
  > `TrackerProjectConfig` from its keyword arguments at `:57` and saves that. So WP02's A2 fix at
  > `service.py:163` hands a loaded config to a constructor whose `bind` drops it one frame later,
  > and **changes nothing on disk**. `plan.md`'s Red-First table records the honest position: the
  > FR-011 preservation reds were *"measured independently at three of them: **A1, A3, C**"* — A2 is
  > not among them, and WP02 is forbidden `local_service.py`.
  >
  > **Consequences for you, both of them:**
  > 1. **The end-to-end `TrackerService.bind` preservation pin is YOURS**, in T024, because site A1
  >    is what makes it real. WP02 asserts A2 only at the unit level, against the constructor
  >    argument.
  > 2. **The window, named at both ends (it is also stated in WP02).** The spec makes a cross-site
  >    guard the condition of splitting FR-011's sites across change sets — *"the split requires a
  >    guard asserting that every `TrackerProjectConfig(` construction whose value flows into
  >    `save_tracker_config` carries `egress`."* That guard is **not** written for the A1-vs-A2/A3
  >    split. It is accepted anyway because **WP02 and WP04 land on one branch**
  >    (`bundle-c-tracker-refusal-3108`) and are never released separately. **The window is: from
  >    WP02 landing until your T024 lands, `LocalTrackerService.bind` still erases a committed
  >    `egress`.** Nothing ships in it. **T024 closes it, and T026 depends on it being closed.**
- **WP03** — `tracker_egress_verdict(root: Path | None, *, destination: EgressDestination)` exists,
  never raises, and composes the 8-cell join. Its message is composed **once**, in that module.

If any of the three is not on the branch you are working from, **stop**. Do not stub it.

---

## Requirements this WP satisfies

### FR-001 — The gate runs at the head of the three sync entry points, before `_load_runtime`

> *"I want the tracker-egress verdict consulted as the **first statement** of
> `LocalTrackerService.sync_pull`, `sync_push` and `sync_run` — ahead of `self._load_runtime()` at
> `local_service.py:116/131/141` — so that a refusing project is told it refused rather than handed a
> `TrackerConfigError` traceback, and so that nothing is read or created on its behalf first."*

**Why not `_build_engine`** — the site a rejected draft chose: `_load_runtime` is called
*synchronously* before the coroutine that reaches `_build_engine`, and it calls `load_tracker_config`,
which **raises** `TrackerConfigError` on an unparseable file (`config.py:148-149`). It also reads the
machine-global credential store and constructs `TrackerSqliteStore`, which **`mkdir`s and creates a
SQLite file with three tables** (`store.py:278-281`), on behalf of a project that is about to be
refused.

**Rejected alternatives, recorded so you do not re-litigate them:** `_load_runtime` itself (also
called by `map_add`/`map_list`, which perform no egress); `TrackerService._resolve_backend`
(`service.py:65`, bypassed by `bind()` at `service.py:131-166`); `cli/commands/tracker.py::_service`
(`:327` — CLI only, invisible to any future library caller); `factory.build_connector`
(`factory.py:32` — does not have the repo root in scope).

> *"Because the local gate sits at three call sites rather than one, FR-015 guard G3 pins that set
> exactly — and pins the call as the first **executable** statement, so **no `_require_egress` helper
> may stand in for it**."*

### FR-011 (A1) — `LocalTrackerService.bind` must carry the decision forward

| # | Site | Class | Today | Required |
|---|---|---|---|---|
| A1 | `LocalTrackerService.bind` (`local_service.py:47-63`, construction at `:57`) | **erases today** | Builds a **fresh** config from its arguments and calls `save_tracker_config` — everything committed and not passed as a constructor argument is discarded, including any recorded `egress`. | Load the committed config first and carry `egress` (and `_extra`) forward. |

The other eight construction sites are WP02's or out of scope. **A recorded tracker-egress decision
outlives its binding.** *"Deleting a `refused` is a silent fail-open; deleting a `permitted` silently
withdraws a working local binding."* Pin in **both** directions, with the sibling `sync:` block
asserted still present as the control.

### FR-012 — The refusal is operator-visible, actionable, non-zero, and names the Channel-1 state

> *"I want the refusal raised as a `RuntimeError` subclass so `_run_or_exit` (`tracker.py:346-351`)
> prints it in red and exits 1 — never a silent no-op, never a zero exit with an empty result, because
> these are interactive commands and someone running `sync push` would otherwise believe their data
> shipped. On the local path the exception is a new `LocalTrackerServiceError` subclass […] **The two
> hierarchies are not unified — the verdict is.** Both messages are the `message` field of the same
> `tracker_egress_verdict` value."*

`LocalTrackerServiceError` is already a `RuntimeError` subclass (`local_service.py:27`), so
`_run_or_exit` needs **no** change.

### FR-013 (the CHANGELOG half) — The breaking change is a deliverable, not a note

> *"(2) a **Breaking Changes** entry in `CHANGELOG.md` stating that `beads`/`fp` bindings now require a
> recorded decision at one of the two channels and that absence of both denies."*

**No version number is assigned in scope.** The entry lands **in the same commit as the gate**, so the
break never lands undocumented (IC-09(a)). The upgrade note, its `index.md` link and the CI anchor
check are IC-09(b) — **WP08's**, not yours.

### FR-017 — Three docstrings this Mission makes false are amended

> *"`local_service.py:8` — *'No SaaS imports live here — only local connector infrastructure'* — must
> record the consent import; `_check_sync_readiness` (`tracker.py:296-312`) — *'Local providers reach
> the sync command without going through the SaaS surface at all: no auth token, no
> `SPEC_KITTY_SAAS_URL`, no reachability probe, no background daemon'* — becomes false the moment the
> local path consults the hosted-sync consent chain; and `_check_binding_readiness`
> (`tracker.py:315-324`), whose text is defined by mirroring the former and must not inherit a claim
> that is no longer true. […] **All five are pinned by the same docstring test**, so a later revert of
> any of them reds."*

WP03 authored deliverables 4 and 5 (the `egress_verdict.py` module docstring and the classifier's
docstring). **You own the single test that pins all five** — place it in
`tests/sync/tracker/test_local_service.py`, a file you own. Per SC-019 the two authored ones are
asserted to contain the literal strings `invocation/adapters.py:81`, `Q3`, `delete` and
`not migrate`.

### NFR-001, NFR-002, NFR-004, NFR-005

- **NFR-001** — zero captured argv for every refusing fixture, across all three entry points; on
  `push` and `run` also no captured element equal to or containing the sentinel title.
- **NFR-002** — zero HTTP, zero `subprocess.run`, and **zero local side effect**: the seeded pair's
  tracker SQLite file **byte-identical**, and the unseeded pair leaving **no file** at the resolved db
  path.
- **NFR-004** — three entry points, three refusing cases, three controls, each end to end.
- **NFR-005** — `ruff check` and `mypy --strict` clean, no blanket suppressions, ≥90 % coverage on new
  branches.

### Constraints

- **C-012 (1)** — `tests/sync/tracker/test_local_service.py:235,262,287`: `TestSyncOperations` binds a
  `beads` provider into a fixture repo with **no consent record at either channel** and then calls
  `svc.sync_pull/push/run`, so FR-001's gate makes all three **red**. *"They are repaired by
  committing `tracker: {egress: permitted}` into the fixture repo — one line, no machine-global state
  […] **not** by patching out the gate."*
- **C-018** — where the gate sits, and what a later reader must not do with it.
- **C-021** — the unparseable-config acceptance scenario is **cut** and must not be re-authored.

### Success criteria owned here

SC-001, SC-002, SC-003, SC-004, SC-006, SC-007, SC-011, SC-012, SC-018 (the CHANGELOG half), SC-019,
SC-020.

---

## Standing rules — binding on every measurement you make

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
  status and buffers until exit. **Quote the `N passed` line**; **an empty output file is no
  measurement.**
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
- **Mutations as pytest plugins via `PYTHONPATH`, never source edits**, and never source edits during
  a verification run.
- **Explicit-path staging.** `git add <paths>`, never `git add -A` — 13 files were lost to a stray
  `add -A` in this lineage.
- **`ruff format` is NOT clean on this repo** (`line-length = 164`); only `ruff check` is meaningful.
- **One live agent per file.**
- **Known pre-existing failures — do not chase, do not fix in-PR, do not retry to green:**
  `tests/architectural/test_tid251_enforcement.py` (4 tests);
  `test_charter_package_exports::test_charter_package_cold_import_keeps_status_orchestration_out`;
  two `test_safe_commit_cmd::…_3033`;
  `test_charter_io::test_get_mission_id_returns_none_when_meta_json_malformed`;
  `test_doctor_ops::test_sweep_nfr_002_10k_files_under_5s` (wall-clock, fails under load).
  `ModuleNotFoundError: No module named 'typer'` in subprocess daemon tests is environmental.

---

## Measured hazards that apply to this WP — facts, not advice

**Hazard A — the house test pattern patches out the gate.**
`tests/sync/tracker/test_local_service.py:235,262,287` do `patch.object(svc, "_build_engine", …)`
(docstring `:193-195`: *"We mock `_build_engine` to avoid needing the spec_kitty_tracker package"*).
**A plugin-injected gate on that seam measured bind count 0 with 519 tests green.** You own that file
and will be tempted to repair `TestSyncOperations` by patching the gate out. **Do not.** The repair is
**one committed config line** in the fixture repo. `_build_engine` may stay patched **only for that
class's own delegation assertions** (SC-020 explicitly permits this) — it may not stand in for the
gate.

**Hazard B — the gate sits ahead of `_load_runtime`.** As the **first executable statement** of
`sync_pull`/`sync_push`/`sync_run`. `self._repo_root` is in scope; **all three are plain `def`**, so
the gate is ordinary synchronous code raising **before any event loop exists**.

```
spec-kitty tracker sync push
  └ tracker_callback         is_saas_sync_enabled()  → armed (fixtures set it explicitly)
  └ _check_sync_readiness    _is_local_binding() → short-circuits (unchanged)
  └ _service() → TrackerService.sync_push → _resolve_backend() → LocalTrackerService.sync_push
      └ ▸ GATE  ← FIRST EXECUTABLE STATEMENT (written out here; no helper)
          verdict = tracker_egress_verdict(
              self._repo_root,
              destination=EgressDestination.LOCAL_SUBPROCESS,   ← LITERAL (G5)
          )
          if verdict.refused: raise <LocalTrackerServiceError subclass>(verdict.message)
      └ _load_runtime()          NOT REACHED  → no credential-store read, no SQLite file
      └ _build_engine()          NOT REACHED  → no connector
      └ the credential-named executable   NOT REACHED  → 0 argv, 0 subprocess.run
  └ _run_or_exit catches RuntimeError → red text on stderr, exit 1
```

**C-018 — what a later reader must not do with it.** *"Moving it back to `_build_engine` reintroduces,
on a refused command: a machine-global credential-store read, and a `TrackerSqliteStore` construction
that `mkdir`s and creates a SQLite file with three tables (`store.py:278-281`) — no egress, so every
NFR about bytes still holds, **which is exactly why the move would look harmless**."*

**Hazard C — `destination` is a required keyword-only parameter, never derived.**
`TrackerService._resolve_saas_backend_for_provider` (`service.py:84-98`) overrides the on-disk
provider **in memory**, so three commands drive the hosted transport from a repo whose committed
config says `beads`. **Deriving polarity from the file would make `tracker.egress: permitted` a grant
to spec-kitty's hosted service with Channel 1 absent.** Your three sites pass
`EgressDestination.LOCAL_SUBPROCESS` as a **literal**, unconditionally, with **no** provider read
anywhere near them.

**Hazard D — `from X import f` rebinds by value.** Measured at `bb2020fea`: after patching
`specify_cli.tracker.egress_consent.project_egress_refusal`,
`TSC.project_egress_refusal is TE.project_egress_refusal` → **`False`**. Tests patch the **deciding**
module's bound name and report the per-site split. **The local path's target is whatever name
`local_service.py` binds `tracker_egress_verdict` under, throughout** — that is the name WP01's bind
counter wraps, so **choose it deliberately and do not rename it later**. The split is not uniform:
`specify_cli.invocation.resolve_egress_consent` and
`specify_cli.invocation.propagator.resolve_egress_consent` do **not** observe a patch on
`invocation.adapters` (measured `False`), while the call-time import inside
`tracker/egress_consent.py:178` **does** (measured: flipped refuse → permit). Report per site.

**Hazard E — the arming gate satisfies every refusing assertion with nothing built.** Un-armed,
`cli/commands/tracker.py:354-366` aborts the whole group: exit 1, 0 subprocess, 0 HTTP. Every WP01
fixture sets `SPEC_KITTY_ENABLE_SAAS_SYNC=1` **and asserts refusal text**. When you evaluate whether
your gate works, check that the matched text is **not** `saas_sync_disabled_message()` — SC-013 pins
it, and it is the reason the whole acceptance suite is not already green today.

**Hazard F — the positive control needs a seeded store and the right ownership mode.** `doctrine_mode`
defaults to `external_authoritative`, under which `local_can_write("title")` is `False` and `push`
skips without calling `create_issue`; and an empty store never reaches `create_issue` at all.
Measured: empty store → **1 argv, no sentinel**; seeded store with
`doctrine: {mode: spec_kitty_authoritative}` → **3 argv** (`list`, `create`, `show`), sentinel present.
**If a control you inherit from WP01 captures 1 argv, the fixture is broken, not your gate.**

**Hazard G — C-021: the unparseable-config acceptance scenario is cut. Do not re-author it.**
`_is_local_binding()` (`cli/commands/tracker.py:280-293`) wraps its
`load_tracker_config(require_repo_root())` in `with suppress(Exception)` and returns `False` on any
failure, so for an unparseable file `_check_sync_readiness` takes the **SaaS** branch,
`LocalTrackerService` is never constructed, and your gate is **never reached through the CLI at all**.
The *fault-refuses* property is pinned at the **unit** level against `tracker_egress_verdict` (WP03,
NFR-003). *"Changing `_is_local_binding`'s exception handling to make the scenario reachable is
explicitly out of scope — it would alter readiness behaviour for every local command to buy one
acceptance test."*

---

## Subtasks & Detailed Guidance

### T021 — Confirm the preconditions before you write a line of gate

- **Purpose**: this WP's whole value is *"the gate is the cause of the change in behaviour rather than
  a coincidence of the harness"*. That claim is only available if the harness was working first.
- **Steps**:
  1. Run WP01's file **alone** on the current branch, unpiped: `pytest
     tests/sync/tracker/test_tracker_egress_refusal_3108.py`. Confirm and **quote**:
     - the consenting `push` control captures **exactly 3** argv with `ACME Holdings carve-out`
       verbatim in the `create`;
     - the unseeded consenting variant captures **exactly 1**;
     - the local refusing pins are **red**, and US1 sc1's red prints the confidential title inside a
       captured argv element.
  2. Confirm WP02 landed: `egress` is in `_KNOWN_KEYS`; `TrackerService.bind`'s local branch hands the
     **loaded** config; a `bind` plants no `egress: null`.
  3. Confirm WP03 landed: `tracker_egress_verdict` importable, `len(_JOIN) == 8`, the never-raises
     suite green.
  4. Record the **interpreter version** you are measuring on. CI runs 3.11/3.12; the local interpreter
     in this environment is 3.14. *"A zero bind count is a statement about the environment, not about
     the code."*
  5. Re-derive by symbol name the lines you are about to edit: `LocalTrackerService.sync_pull`,
     `.sync_push`, `.sync_run`, `._load_runtime`, `._build_engine`, `.bind`, `LocalTrackerServiceError`,
     `_check_sync_readiness`, `_check_binding_readiness`, `_run_or_exit`. **A symbol that moved
     semantically is a re-plan trigger.**
- **Files**: none (verification only).
- **Validation**: three quoted `N passed`/`N failed` lines plus the interpreter version.
- **Edge cases**: if WP01's consenting control captures 1 argv, **stop** — the fixture is wrong and no
  later result from that suite means anything. Report it to WP01's owner; do not edit their file.

### T022 — The gate, three sites, first executable statement, literal destination

- **Purpose**: FR-001, NFR-004, and the structural property guard G3 will pin.
- **Steps**:
  1. Import `tracker_egress_verdict` and `EgressDestination` into `local_service.py`, with **exactly
     this line**:

     ```python
     from specify_cli.tracker.egress_verdict import EgressDestination, tracker_egress_verdict
     ```

     **This is not a style preference; it is a cross-WP contract with two consumers.**
     - **G5 (WP07).** An aliased import (`import … as ED`, or `from specify_cli.tracker import
       egress_verdict as ev`) makes each `destination` argument an `Attribute` on the alias, and G5
       reports non-literal — a **false red**: loud rather than silent, but a lost afternoon for
       anyone who has not been told.
     - **WP01's bind counter.** `from X import f` **rebinds by value**, so the counter must wrap the
       name the *deciding* module holds. WP01 was told the target is
       **`specify_cli.tracker.local_service.tracker_egress_verdict`** and wrote its wrapper against
       that string **before you existed**. The line above is what makes that string real.
       **Bind it under this name and do not rename it later** — a rename makes WP01's counter read 0
       forever, and a zero bind counter is indistinguishable from a gate that is never entered.
       (WP05 and WP06 are handed the same import line for the same reasons.)
  2. In **each** of `sync_pull`, `sync_push` and `sync_run`, **write the gate out** as the **first
     executable statement** of the method body:

     ```python
     verdict = tracker_egress_verdict(
         self._repo_root,
         destination=EgressDestination.LOCAL_SUBPROCESS,
     )
     if verdict.refused:
         raise <LocalTrackerServiceError subclass>(verdict.message)
     ```

     A docstring is tolerated as the first AST *node*; nothing else is. **No `_require_egress`
     helper** — a helper would satisfy G3's "first statement" property with a call to the helper and
     **stop pinning `tracker_egress_verdict` at all**.
  3. All three are plain `def`, so this is ordinary synchronous code raising **before any event loop
     exists**. It runs **ahead of `self._load_runtime()`**.
  4. Leave `map_add`, `map_list` and `status` **ungated**, deliberately: they construct no connector
     and run no subprocess, and `status()` reaches `load_tracker_config` directly
     (`local_service.py:81`), bypassing `_load_runtime` entirely.
  5. Do **not** add a provider read, a `LOCAL_PROVIDERS`/`SAAS_PROVIDERS` reference, or any branch on
     the destination near these sites. The literal is unconditional.
- **Files**: `src/specify_cli/tracker/local_service.py`.
- **Validation**: WP01's local refusing pins flip **red → green**; the Stage-1 positive controls stay
  green. **The specific pin observed red-then-green is US1 sc1, whose red prints
  `ACME Holdings carve-out` inside a captured argv element.** Quote both states.
- **Edge cases**: *"An incomplete binding in a refusing project"* — `_load_runtime` would raise
  *"Tracker provider/workspace configuration is incomplete."* Because the gate runs first, such an
  operator sees the **refusal** instead. **Deliberate: the egress verdict outranks configuration
  completeness**, because telling an operator to finish a binding they are not permitted to use is
  worse advice than telling them why they are refused.

### T023 — The refusal exception, and the message that is never re-composed

- **Purpose**: FR-012.
- **Steps**:
  1. Add a new `LocalTrackerServiceError` **subclass** for the refusal. `LocalTrackerServiceError` is
     already a `RuntimeError` subclass (`local_service.py:27`), so `_run_or_exit`
     (`tracker.py:346-351`) prints it in red and exits 1 with **no change to that helper**. Do not
     change `_run_or_exit`.
  2. Raise it with **`verdict.message`** — the `message` field of the verdict value. **No path-local
     message strings anywhere.** The two refusal exception hierarchies (local and hosted) are **not**
     unified; the **verdict** is.
  3. Add the pin: the raised message **equals** `verdict.message` for the same verdict, so a later
     edit that re-composes text at the raise site reds. (`plan.md` Open Items 1 asks for exactly
     this.)
  4. Confirm through WP01's suite that the refusal exits **non-zero** and prints **text**, and that
     the matched text is **not** `saas_sync_disabled_message()` — the string beginning *"Hosted SaaS
     sync is not enabled on this machine. Set"*.
- **Files**: `src/specify_cli/tracker/local_service.py`;
  `tests/sync/tracker/test_local_service.py`.
- **Validation**: the message-identity pin green; WP01's SC-013 negative pin green.
- **Edge cases**: never a silent no-op and never a zero exit with an empty result — *"these are
  interactive commands and someone running `sync push` would otherwise believe their data shipped."*

### T024 — Site A1: `LocalTrackerService.bind` carries the decision forward

- **Purpose**: FR-011 (A1). **This site erases today, and its red exists on the base.**

  > **T024 MUST land before T026.** T026's whole claim — *"the repair is one committed config
  > line"* — is only true once `LocalTrackerService.bind` stops erasing, and **this subtask is what
  > makes it stop.** Run them in this order and say in the PR body that you did.
- **Steps**:
  1. Write the failing pin first, in `tests/sync/tracker/test_local_service.py`: commit
     `tracker: {egress: refused}` into a project, run `LocalTrackerService.bind(...)`, assert `egress`
     is still present with its value, **and assert the sibling `sync:` block is still present as the
     control**. The control proves the file was written and the rest survived, so a missing key is
     **erasure**, not a write failure. Observe the red and quote it.
  2. **Write the end-to-end `TrackerService.bind` preservation pin here too — it is yours, not
     WP02's.** Commit a decision, call **`TrackerService.bind(...)`** on a **local** provider, and
     assert the decision survived **on disk**, with the sibling `sync:` block as the control. WP02
     fixed `service.py:163` to hand `LocalTrackerService` the loaded config, but that change is
     **inert on disk** until step 3 below lands, because `bind` never reads `self._config`. So this
     pin is red before step 3 and green after it — **observe both and quote both**. WP02 could not
     have earned it: it is forbidden `local_service.py`, and a pin it could write would have been
     red before its fix and red after.
  3. Fix `bind` (`local_service.py:47-63`, construction at `:57`) to **load the committed config
     first** and carry `egress` (and `_extra`) forward instead of building a fresh
     `TrackerProjectConfig` from its arguments alone.
  4. Repeat the pin in **both** directions — a recorded `refused` **and** a recorded `permitted`.
     *"Erasing a `refused` is a silent fail-open; erasing a `permitted` silently withdraws a working
     local binding."*
- **Files**: `src/specify_cli/tracker/local_service.py`;
  `tests/sync/tracker/test_local_service.py`.
- **Validation**: both directions red then green, each with the `sync:` control asserted.
- **Edge cases**: A2 (`service.py:163`) is WP02's and should already hand you the loaded config. If it
  does not, **report it** — do not fix `service.py` here.

### T025 — The five docstrings, pinned by one test

- **Purpose**: FR-017, SC-019.
- **Steps**:
  1. **Amend `local_service.py:8`** — *"No SaaS imports live here — only local connector
     infrastructure"* — to record that the file now consults the egress verdict / hosted-sync consent
     chain.
  2. **Amend `_check_sync_readiness` (`tracker.py:296-312`)** — *"Local providers reach the sync
     command without going through the SaaS surface at all: no auth token, no `SPEC_KITTY_SAAS_URL`,
     no reachability probe, no background daemon"* — which becomes **false** the moment the local path
     consults the hosted-sync consent chain.
  3. **Amend `_check_binding_readiness` (`tracker.py:315-324`)**, whose text is defined by mirroring
     the former and **must not inherit a claim that is no longer true.**
     **`cli/commands/tracker.py` gets docstring edits only. No behavioural change.
     `_is_local_binding`'s short-circuit is unchanged.**
  4. Write **one** docstring test, in `tests/sync/tracker/test_local_service.py`, pinning **all five**
     FR-017 deliverables — the three you amended **and** WP03's two authored ones
     (`egress_verdict.py`'s module docstring and the Channel-1 classifier's docstring). Per SC-019,
     assert the two authored ones contain the literal strings `invocation/adapters.py:81`, `Q3`,
     `delete` and `not migrate`, *"so the retirement condition cannot be softened into a 'consider
     revisiting'."*
- **Files**: `src/specify_cli/tracker/local_service.py`,
  `src/specify_cli/cli/commands/tracker.py`, `tests/sync/tracker/test_local_service.py`.
- **Validation**: the single docstring test reds if **any** of the five is reverted — verify by
  temporarily mutating each in a scratch copy (a `PYTHONPATH`-injected plugin, **never** a source edit
  during a verification run).
- **Edge cases**: if WP03's two docstrings do not carry the required literals, **report it** — you own
  the test, not their module.

### T026 — Repair `TestSyncOperations` with exactly one committed line

- **Purpose**: C-012 (1), SC-020 — and the claim that *"the repair is one committed config line"*.
- **Steps**:
  1. Run `pytest tests/sync/tracker/test_local_service.py` and confirm `TestSyncOperations`
     (`:235,262,287`) is **red under the gate** — it binds a `beads` provider into a fixture repo with
     **no consent record at either channel** and then calls `svc.sync_pull/push/run`.
  2. Repair it by **committing `tracker: {egress: permitted}` into the fixture repo** — one line, no
     machine-global state.

     **This is possible only because YOUR OWN T024 landed first — site A1, in `local_service.py`.**
     The `repo` fixture creates only `.kittify/` with no `config.yaml`, and `_setup_bound_service`
     binds through **`LocalTrackerService.bind`**, which before T024 builds a fresh
     `TrackerProjectConfig` at `local_service.py:57` and saves it — **erasing the pre-seeded key**.
     **It is not WP02 that makes this work**: WP02 is forbidden `local_service.py` entirely, and its
     A2 fix at `service.py:163` hands `bind` a loaded config that `bind` then ignores. An earlier
     draft of this prompt credited WP02 here; that attribution was wrong, and acting on it would
     send you to the wrong WP when the repair fails.

     **So: if this repair does not hold, check T024, not WP02.**
  3. **Do not patch out the gate.** `_build_engine` may stay patched **only for that class's own
     delegation assertions** (SC-020 permits exactly this and nothing more).
  4. Assert the one-line claim: the fixture diff for this repair is a single added config line.
  5. Re-run the whole file and quote `N passed`.
- **Files**: `tests/sync/tracker/test_local_service.py`.
- **Validation**: `TestSyncOperations` green; the repair is one line; `_build_engine` is not patched
  as a substitute for the gate anywhere.
- **Edge cases**: if the repair requires writing the key **after** `bind()`, **site A1 has not
  landed** — that fixture shape hides the very erasure bug FR-011 exists to fix. Stop and go back to
  **T024**, which is the subtask that owns it.

### T027 — The CHANGELOG Breaking Changes entry, in the same commit as the break

- **Purpose**: FR-013 (2), SC-018's CHANGELOG half, IC-09(a).
- **Steps**:
  1. Add a **Breaking Changes** entry to `CHANGELOG.md` stating that **local tracker providers
     (`beads`/`fp`) now require a recorded decision at one of the two channels, and that absence of
     both denies.** Name both channels: the hosted-sync consent chain, and the new
     `tracker.egress` key in the project's own committed `.kittify/config.yaml`.
  2. Link the upgrade note. **WP08 authors the note itself** (`docs/migrations/`, its `index.md` link
     and the CI anchor check) — you write the CHANGELOG entry and its link only.
  3. **No version number is assigned in scope.**
  4. This entry **lands in the same commit as the gate**, so the break never lands undocumented.
  5. **Run the terminology guard before pushing prose**: `pytest
     tests/architectural/test_no_legacy_terminology.py` (≈0.1 s). It enforces the Terminology Canon —
     **Mission**, never "feature". Some repo-wide gates run only in CI's
     `integration-tests-core-misc` job, so a forbidden-term regression otherwise only fails at CI.
  6. Close the WP by running the quality gates and quoting them: `ruff check` clean, `mypy --strict`
     clean with no added `# type: ignore`, ≥90 % coverage on the new branches.
- **Files**: `CHANGELOG.md`.
- **Validation**: the entry is present under Breaking Changes and links the note's path; the
  terminology guard is green with its runtime quoted.
- **Edge cases**: do not create or edit anything under `docs/migrations/` — that is WP08's.

---

## Test Strategy

- **Owned test file**: `tests/sync/tracker/test_local_service.py` — the A1 preservation pins (both
  directions, with the `sync:` control), the five-docstring pin, the message-identity pin, and the
  repaired `TestSyncOperations`.
- **Inherited, run but never edited**: `tests/sync/tracker/test_tracker_egress_refusal_3108.py`
  (WP01). Its local refusing pins flipping red → green **is** this WP's acceptance evidence.
- **Run**:
  - `pytest tests/sync/tracker/test_tracker_egress_refusal_3108.py` — **alone**, unpiped, `N passed`
    quoted, every **local** cell asserting a **non-zero LOCAL bind counter**, with the interpreter
    version recorded beside it. The US5 cells stay **red** here: they need WP05's swap, and their
    counter is the hosted one.
  - **Then again inside** `pytest tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py`. *"A
    discrepancy between the two is cross-test pollution (the `#3115` class), not this Mission — and is
    a finding to report, not to chase to green."*
  - `pytest tests/sync/tracker/test_local_service.py`.
  - `pytest tests/architectural/test_no_legacy_terminology.py` before pushing the CHANGELOG.
- `ruff check` and `mypy --strict` clean on all owned files.

## Definition of Done

- The gate is the **first executable statement** of `sync_pull`, `sync_push` and `sync_run`, ahead of
  `_load_runtime`, **written out at each site with no helper**, each passing
  `EgressDestination.LOCAL_SUBPROCESS` as a **literal**.
- WP01's local refusing pins are **green**; the Stage-1 positive controls are **still green**;
  **US1 sc1 observed red-then-green**, with the red quoted and its red printing
  `ACME Holdings carve-out` in a captured argv element.
- **The LOCAL bind counter — the wrapper on
  `specify_cli.tracker.local_service.tracker_egress_verdict` — is non-zero in every acceptance test
  that drives `sync_pull` / `sync_push` / `sync_run` on a local binding**, with the interpreter
  version recorded beside it; one test asserts the counting wrapper changes no outcome.
  **You verify this counter; you do not own the file it is asserted in.** Scope it exactly:
  - the **US5** cells route through `SaaSTrackerService` → `SaaSTrackerClient._request` and **never
    call the local name at all** — their counter is the **hosted** one, and it is **WP05's** to make
    non-zero, not yours;
  - **US1 sc4** (the `sync now` drain) asserts **no** bind counter, by WP01's recorded exemption;
  - the **consenting controls** are not subject to the bind-counter rule (WP01's exit criterion says
    so, and a counter asserted on them would have made WP01's own controls red).
  A blanket *"every acceptance test"* reading of this line is wrong and unsatisfiable. **If WP01's
  file asserts the local counter in a US5 cell, that is a defect in WP01's file — report it, do not
  edit it, and do not "fix" it by adding a second local call site.**
- Site A1 preserves a committed `egress` in **both** directions, with the sibling `sync:` block
  asserted present as the control — red then green, both quoted. **The end-to-end
  `TrackerService.bind` pin (T024 step 2) is included, red then green, both quoted.**
- **T024 landed before T026**, stated in the PR body, because T024 is the sole guarantor of T026's
  one-committed-config-line claim.
- **`src/specify_cli/cli/commands/tracker.py` received docstring edits and nothing else — and the PR
  body QUOTES THE FULL DIFF OF THAT FILE** so the claim is checkable rather than asserted. This
  prompt makes the docstrings-only claim three times and pins it nowhere; the full diff is the pin.
  A behavioural change smuggled into that file would alter readiness behaviour for every local
  command, which is exactly what C-021 records as out of scope.
- The five FR-017 docstrings are pinned by **one** test, including the literal strings
  `invocation/adapters.py:81`, `Q3`, `delete`, `not migrate`.
- `TestSyncOperations` green with a **one-line** fixture repair, and `_build_engine` **not** patched as
  a substitute for the gate.
- `CHANGELOG.md` carries the Breaking Changes entry, **in the same commit as the gate**; the
  terminology guard is green.
- `ruff check` and `mypy --strict` clean; no blanket suppressions.
- No file outside the four owned files is modified. **WP01's acceptance file is not edited.**

## Risks & Mitigations

- **The gate is installed and never entered** (measured: bind count 0 with 519 tests green) → the H4
  bind counter asserted non-zero in every acceptance test, plus the SC-020 grep pin.
- **`TestSyncOperations` "repaired" by patching out the gate** → the repair is one committed config
  line; `_build_engine` may stay patched only for that class's delegation assertions.
- **The gate drifts back to `_build_engine`** → C-018 records what that reintroduces, and US3 sc4's
  unseeded pair is the pin that reds when it happens (`TrackerSqliteStore.__init__` `mkdir`s and
  creates the file, `store.py:278-281`).
- **The break lands undocumented** → the CHANGELOG entry is in the same commit, by rule.
- **Someone re-authors the cut unparseable-config scenario** → C-021 records why it is unreachable
  through the CLI and why fixing `_is_local_binding` is out of scope.

## Review Guidance

- Verify the gate is the first **executable** statement in all three methods (a docstring is tolerated
  as the first AST node; nothing else is), and that it is **written out**, not delegated to a helper.
- Verify `destination=EgressDestination.LOCAL_SUBPROCESS` is a **literal attribute access** at all
  three sites, with `EgressDestination` imported under its own name.
- Verify no provider read, `LOCAL_PROVIDERS`/`SAAS_PROVIDERS` reference, or destination branch was
  added.
- Verify the raise uses `verdict.message` and composes no text of its own.
- Verify the `TestSyncOperations` repair is genuinely one committed config line and does **not** write
  the key after `bind()`.
- Verify the **local** bind counter is asserted non-zero in every acceptance test **that drives a
  local sync entry point** — not in the US5 cells, not in US1 sc4, not in the consenting controls —
  and that the interpreter version is recorded beside every count.
- Verify the import line is verbatim
  `from specify_cli.tracker.egress_verdict import EgressDestination, tracker_egress_verdict`, so
  WP01's counter target and WP07's G5 both resolve.
- Verify T024 preceded T026 and that the `TestSyncOperations` repair is credited to T024, not WP02.
- Verify the PR body **quotes the full diff of `cli/commands/tracker.py`**.
- Verify `map_add`, `map_list` and `status` remain ungated.

## Activity Log

- 2026-08-01T00:20:00Z – system – Prompt created.

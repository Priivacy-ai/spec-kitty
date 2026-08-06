# WP02 evidence — route the 5 ledger rows / 6 call sites

**Work package**: WP02 — Route the refuse-raw rows onto `load_meta_fail_closed`
**Profile**: `python-pedro` (role `implementer`), resolved via `spec-kitty agent profile show python-pedro`
**Base SHA**: `f1681bf1bcc93b9631125766b6a0bafd4f30d332`
**Requirements**: `FR-001`, `NFR-001`, `NFR-002`, `C-001`, `C-003`, `C-008`, `SC-001`

> Out-of-map planning write. `kitty-specs/` paths cannot appear in `owned_files` by
> construction (`mission_parsing.py:153-157`, `:207-215`), so this committed evidence file
> is a declared out-of-map write. `mark-status` carries no evidence field — its payload is a
> bare `{T0xx: Status}` (`status/models.py:481`) — so this file, not the checkbox, is the record.

---

## 0. Workspace, and why it is the repository root

The runtime named a lane worktree at
`.worktrees/meta-fail-closed-3162-01KZ7FSQ-lane-b`. **It does not exist**: `.worktrees/` is
absent and `git worktree list` reports only the main tree. The WP prompt independently
mandates the repository root, so WP02 ran from
`/home/jeroennouws/dev/sk-missions/3162`.

The split-tree hazard is therefore **closed by construction**, proven by probe:

```
core.paths        : /home/jeroennouws/dev/sk-missions/3162/src/specify_cli/core/paths.py
gate SRC_ROOT     : /home/jeroennouws/dev/sk-missions/3162/src
ledger _SRC_ROOT  : /home/jeroennouws/dev/sk-missions/3162/src
```

The imported module, the gate's AST census root, and the ledger test's census root are the
same tree. `PYTHONPATH=/home/jeroennouws/dev/sk-missions/3162/src` was passed on **every**
`python -c` and `pytest` invocation regardless, and `.venv/bin` was prepended to `PATH`
(`command -v spec-kitty` → `.../3162/.venv/bin/spec-kitty`, not `~/.local/bin`).

Every test file additionally derives its AST census target from the **imported module's own
`__file__`** rather than from the test file's location — this closes the hazard *inside the
test*, which is strictly stronger than the `SRC_ROOT` pattern that created it.

---

## 1. THE SHARED-BRANCH FINDING — read this before checking any absolute count

`lanes.json` assigns WP02 to lane-b and WP05/WP07 to other lanes, expecting **separate
worktrees**. No worktree exists, so **every lane is committing to `feat/meta-fail-closed-3162`
in the same working tree, concurrently.** Observed directly:

- `src/specify_cli/git/ref_advance.py` appeared modified in my working tree at 03:21:58 —
  a file WP02 never touched. It is WP05's site.
- `git log <base>..HEAD` interleaves WP02, WP05 and WP07 commits.
- WP05 landed its allocated `+1` mid-WP: `e06dfdc6f fix(WP05): route ref_advance site A`.

**Consequence: the absolute routed census reads 130, not 129, and that is correct.** The
`129 / 129` pre/post pair the WP prompt asks for is not measurable on a shared branch once
WP05 lands. WP02's obligation — **0-net** — is therefore discharged as an *attributable
per-file delta* against WP02's base SHA:

| File | base `f1681bf1` | post-WP02 | delta |
|---|---|---|---|
| `runtime/next/_internal_runtime/planner.py` | 1 | 1 | 0 |
| `runtime/next/runtime_bridge_io.py` | 1 | 1 | 0 |
| `specify_cli/bulk_edit/gate.py` | 2 | 2 | 0 |
| `specify_cli/missions/_read_path_resolver.py` | 3 | 3 | 0 |
| `specify_cli/coordination/surface_resolver.py` | 2 | 2 | 0 |
| **WP02 subtotal** | **9** | **9** | **0** |

Whole-tree: base **129** → live **130**; the entire `+1` is
`specify_cli/git/ref_advance.py` `0 → 1`, which is WP05's sole allocation
(`contracts/headroom-allocation.md` §2: *"WP05 | YES — the sole allocator | +1 | prints pre
129, post 130"*). **130 is inside the two-sided band `[127, 130]`.**

All commits used explicit per-path `git add`; no other lane's work was ever staged.

---

## 2. T006 — baseline

| Item | Value |
|---|---|
| Base SHA | `f1681bf1bcc93b9631125766b6a0bafd4f30d332` |
| Routed census pre | **129** |
| Band | **`[127, 130]`**, two-sided — **126 is RED** |
| `pending-batch-a` grep hits | **13** (see correction §6.3 — 12 rows + 1 legend line) |
| Cone selected | **2006** |
| Cone result | `2005 passed, 1 skipped in 1210.36s (0:20:10)`, `exit=0` |
| `^ERROR tests/` lines | **0** |

The single skip is `tests/runtime/test_home_unit.py:61: windows_ci: requires sys.platform ==
'win32'` — a platform guard, not a masked red. Baseline was run with the five WP02 test files
**parked outside the tree** so it measures a clean base.

Band derivation, from the three verbatim assertions of `test_routed_load_meta_floor`
(`tests/architectural/test_inline_meta_read_gate.py`, `ROUTED_LOAD_META_FLOOR = 126` at
`:221`, `ROUTED_LOAD_META_FLOOR_MARGIN = 4` at `:220`):

```python
assert len(routed) >= ROUTED_LOAD_META_FLOOR, (...)
assert len(routed) > ROUTED_LOAD_META_FLOOR, (
    "ROUTED_LOAD_META_FLOOR must be a concrete census integer strictly below "
    "the live routed count, not '>= len(routed)' (anti-vacuous)."
)
assert len(routed) - ROUTED_LOAD_META_FLOOR <= ROUTED_LOAD_META_FLOOR_MARGIN, (...)
```

clause 1 → `len >= 126`; clause 2 is **strict** → `len >= 127`; clause 3 → `len <= 130`.
**Band `[127, 130]`; 126 is RED**, and the bound fails downward as well as upward — a fold of
rows 10/11 walks toward it.

Baseline quality gates — all four owned source files clean on `ruff check`,
`ruff check --select C901`, and `mypy --strict` (`exit=0` each, 12 invocations).

---

## 3. Per-subtask record

Each row: red commit (test alone), then green commit carrying **routing + its ledger-row
deletion together**. Atomic because `test_no_unaccounted_load_meta_call_sites` gates on exact
equality in both directions — routing without deleting fails `stale`, deleting without routing
fails `unaccounted`. Every ledger row was located by **content key**, never line number.

| Subtask | Census row(s) | Red SHA | Green SHA | Routed census |
|---|---|---|---|---|
| T007 | 4 — `planner._resolve_workflow_for_mission` | `5b93d25a7` | `7602fd6fa` | 129 |
| T008 | 5 — `runtime_bridge_io._workflow_runtime_template` | `e29601890` | `5ee77834a` | 129 |
| T009 | 6 — `gate._is_bulk_edit_mission` | `77e3adf25` | `aa87e26be` | 129 |
| T010 | 7 — `gate.ensure_occurrence_classification_ready` | `4147417c1` | `233fb6385` | 129 |
| T011 | 10 + 11 — `_read_path_resolver.read_primary_meta` | `a41eb7de7` | `271fefd62` | 130 (WP05's +1 landed; WP02 delta 0) |

`git show --stat` on all five greens shows the source file **and**
`tests/specify_cli/test_meta_fail_closed_full_census_contract.py` in the same commit.

### Quoted reds

**T007** — `2 failed, 3 passed in 58.62s`

```
E   ValueError: Malformed JSON in .../meta.json: Expecting value: line 1 column 16 (char 15)
E   AssertionError: _resolve_workflow_for_mission must hold EXACTLY ONE
    load_meta_fail_closed() call in its own body; found 0
E   assert 0 == 1
```

**T008** — `3 failed, 3 passed in 61.02s`

```
E   ValueError: Malformed JSON in .../.worktrees/wp02-row05-probe-01KVN754-coord/
    kitty-specs/wp02-row05-probe-01KVN754/meta.json: Expecting value: line 1 column 16 (char 15)
E   AssertionError: _workflow_runtime_template must hold EXACTLY ONE
    load_meta_fail_closed() call in its own body; found 0
```

**T009** — `2 failed, 4 passed in 80.43s`

```
E   ValueError: Malformed JSON in .../meta.json: Expecting value: line 1 column 16 (char 15)
E   AssertionError: _is_bulk_edit_mission must hold EXACTLY ONE
    load_meta_fail_closed() call in its own body; found 0
```

**T010** — `4 failed, 3 passed in 66.39s`

```
E   AssertionError: ensure_occurrence_classification_ready must hold EXACTLY ONE
    load_meta_fail_closed() call in its own body; found 0
E   AssertionError: gate.py still calls load_meta( somewhere; count=1
E   AssertionError: gate.py still imports load_meta; with both census rows 6 and 7
    routed the import is unused and ruff F401 flags it
```

**T011** — `7 failed, 6 passed in 68.79s`

```
E   AssertionError: read_primary_meta must enter load_meta_fail_closed exactly TWICE
    ... Got 0; full reader trace={'load_meta': 3}
E   AssertionError: read_primary_meta must hold EXACTLY TWO load_meta_fail_closed()
    calls in its own body ... Got 0
E   AssertionError: assert [] == ['primary_dir...anonical_dir']
```

### Greens

| Subtask | Result |
|---|---|
| T007 | `32 passed in 65.21s`, `exit=0` |
| T008 | `722 passed, 1 skipped in 1236.65s`, `exit=0`, 0 `^ERROR tests/` |
| T009 | `224 passed in 146.50s`, `exit=0`, 0 `^ERROR tests/` |
| T010 | `250 passed in 140.85s`, `exit=0`, 0 `^ERROR tests/` |
| T011 | `622 passed in 132.88s`, `exit=0`, 0 `^ERROR tests/` |

### The per-site anti-fold assertions (the binding budget control)

Five executable AST call-count assertions over each routed function's **own body**, matched on
the **exact callee name** (nested `def`/`lambda` bodies excluded, so a helper defined inside
cannot launder a call out of the count; `load_meta_fail_closed` never increments `load_meta`):

| Census row | Function | `load_meta_fail_closed(` | `load_meta(` |
|---|---|---|---|
| 4 | `_resolve_workflow_for_mission` | 1 | 0 |
| 5 | `_workflow_runtime_template` | 1 | 0 |
| 6 | `_is_bulk_edit_mission` | 1 | 0 |
| 7 | `ensure_occurrence_classification_ready` | 1 | 0 |
| 10+11 | `read_primary_meta` | **2** | 0 |

Plus two module-wide anti-fold pairs the per-function scope cannot express: `gate.py` holds
exactly **2** routed calls and **0** unrouted (catches a fold of its two reads into one shared
helper), and `read_primary_meta`'s two routed calls still take `primary_dir` and
`canonical_dir` as their first positional arguments respectively — so the count of 2 cannot be
met by duplicating a single read.

Why these and not the printed pre/post pair: a fold reads **128**, which satisfies **all
three** clauses of `test_routed_load_meta_floor` at floor 126 / margin 4, and reads 129 — also
green — once WP06 moves the floor to 127. The printed numbers are non-binding.

---

## 4. Import surgery

- **`planner.py`** — `load_meta` had exactly one use, so the `mission_metadata` import was
  **replaced**. `core.paths` at module level forms no new cycle (the module already imports
  `core.constants`); verified by importing the module in a fresh interpreter.
- **`runtime_bridge_io.py`** — same shape; `:380` was the module's only use.
- **`gate.py` — two rows, one import, split across two commits.** T009 **added**
  `load_meta_fail_closed` and **kept** `load_meta` (row 7 at `:80` was still live; removing it
  early is a `NameError`). T010 **removed** it once both rows were routed; `ruff check` F401 is
  the gate and passes. Post-T010 `grep -n 'load_meta\b' src/specify_cli/bulk_edit/gate.py`
  returns **nothing**.
- **`_read_path_resolver.py`** — the in-function `load_meta` import feeding rows 10/11 was
  deleted and `load_meta_fail_closed` added to the existing module-level `core.paths` import.
  The **second** in-function import at `:117` feeding `_declares_coordination_branch`
  (`on_malformed="none"`) is **untouched** — a `silent-by-contract` site whose ledger row must
  survive WP02. A test now pins that it still holds 1 `load_meta(` and 0
  `load_meta_fail_closed(`.

The load-bearing deferred `mission_metadata` import **inside** `load_meta_fail_closed` was not
touched.

---

## 5. THE C-001 REGRESSION FOUND AND FIXED

**A 1:1 swap is not behaviour-neutral at the callers.** `MissionMetaReadError`'s MRO is
`RuntimeError → Exception`; it is deliberately **not** a `ValueError`. Two pre-existing
*degrade* callers wrap `read_primary_meta` in `except (ValueError, OSError)` and therefore
**silently stopped absorbing corruption** once rows 10/11 were routed — they began raising
instead of degrading, which is exactly the arm change `C-001` forbids:

1. `_read_path_resolver.py:1257` — the never-raise primitive behind
   `candidate_feature_dir_for_mission` / `resolve_feature_dir_for_slug`. **Caught live** by
   `tests/missions/test_wp17_husk_arm_collapse.py::test_corrupt_meta_lenient_primitive_degrades_not_raises`.

   > **Citation correction (review cycle 2).** This line originally read `:1259`, which matches
   > neither state of the file. The pre-edit arm is `    except (ValueError, OSError):` at
   > **`:1257`** — verified identical at the green's parent `233fb6385` — and post-edit it sits at
   > **`:1269`**. The enclosing symbol is **`_stored_topology_best_effort`** (`:1223` at
   > `233fb6385`, `:1226` at the cycle-2 HEAD). Commit `271fefd62`'s message repeats the wrong
   > `:1259` *and* names `_read_path_resolver.stored_topology_for_mission`, **a symbol that does
   > not exist anywhere in `src/`** (`grep -rn stored_topology_for_mission src/` → no matches).
   > That commit message is immutable, so the correction is recorded here instead. The sibling
   > citation `surface_resolver.py:564` below is correct and is left unchanged.
2. `coordination/surface_resolver.py:564` — documented contract *"a malformed / unreadable
   primary meta degrades to `True`"*. **Same defect class, found by inspection after the
   first; no test in WP02's cone covered it.**

Both arms widened to `(MissionMetaReadError, ValueError, OSError)`, restoring each caller's
degrade contract byte-identically. Adding a class to an `except` tuple adds no routed call, so
the budget is unaffected.

`surface_resolver.py` is **out of this WP's `owned_files`** — a one-line change plus rationale,
recorded here because shipping a known arm change that no in-scope test would catch is a worse
outcome than a declared out-of-map edit.

Two other `except ValueError` arms were checked and are **unrelated** to meta reads:
`gate.py:71` catches `Path.relative_to`, `_read_path_resolver.py:141` catches an enum lookup.

### One friction test re-pinned, not deleted

`test_corrupt_meta_raises_typed_error_not_classified_primary` asserted
`pytest.raises(ValueError, match="Malformed JSON")` — it pinned the raw-`ValueError` escape
that `FR-001` exists to **remove**. Its setup and the over-collapse mutant it kills are
preserved verbatim; only the assertion moved to `MissionMetaReadError`, strengthened to also
pin `__cause__` preservation and non-`ValueError`-ness.

---

## 6. Corrections to the WP02 prompt and to `spec.md`

### 6.1 T008's prescribed fixture cannot reach census row 5

T008 step 1 prescribes a corrupt `kitty-specs/<slug>-<mid8>/meta.json` driven through
`get_or_start_run`. That fixture raises from **census row 10**, not row 5:
`_workflow_runtime_template` resolves the mission dir on its own first line via
`_resolve_runtime_feature_dir` → `read_primary_meta`, shadowing its own read. Measured on the
unrouted tree:

```
get_or_start_run             @ runtime_bridge_io.py:499
_workflow_runtime_template   @ runtime_bridge_io.py:376   <- the RESOLVE, not the read
_resolve_runtime_feature_dir @ runtime_bridge.py:1138
resolve_handle_to_read_path  @ _read_path_resolver.py:966
read_primary_meta            @ _read_path_resolver.py:846 <- census row 10 fires here
```

**Fix used**: a coord-topology fixture — valid primary meta declaring `coordination_branch`
plus a materialized `.worktrees/<slug>-<mid8>-coord/` whose own `meta.json` is corrupt. A
guard assertion pins the correction (traceback must contain `_workflow_runtime_template` and
must **not** contain `read_primary_meta`), so the test cannot regress into testing row 10.

### 6.2 Census row 11's corrupt-file arm is structurally unreachable — `SC-001` needs restating

`spec.md` settles `Q7` by asserting row 11's fixture "already exists" at
`tests/status/test_aggregate_coord_deleted_contract.py:70-92` and that writing corrupt JSON
instead of valid reaches `:862`. **It does not.** `:862`'s target is `_canonicalize_handle`'s
resolved `feature_dir`, and canonicalization indexes via `load_meta(entry,
on_malformed="none")` (`context/mission_resolver.py:176`), which **skips** any dir whose
`meta.json` is corrupt. A corrupt meta makes the handle unresolvable, `_canonicalize_handle`
returns `None`, and `:862` never executes — `read_primary_meta` returns `({}, False)` having
never read the corrupt file. The two readers' accept-sets are **identical** (both reject
exactly "not a JSON object"), so no content can be valid for the indexer and corrupt for the
re-read. Verified across all four handle forms: composed `<slug>-<mid8>`, bare `mid8`, full
ULID, bare human slug.

**`SC-001`'s "7/7 behavioural" is unachievable as specified and its denominator must be
restated** so a later work package does not inherit the false premise.

**Substitute used** (better than what it replaces): a `sys.setprofile` execution trace
asserting `read_primary_meta` **enters `load_meta_fail_closed` exactly twice** on a real file
through a public entry. It patches nothing, observes the real call stack, and is a seam proof
and an anti-fold control in one instrument — 0 entries before routing, 2 after, 1 under a fold.
A companion test pins *why* the corrupt arm is unreachable, so if the canonicalizer ever grows
a corruption-tolerant index the assertion goes red and row 11 becomes testable.

This is not a fail-open: on that path the corrupt file is never read, and `({}, False)` is the
honest "no primary meta resolved for this handle" answer.

### 6.3 `pending-batch-a` is 12 rows, not 13

`grep -c 'pending-batch-a'` returns **13**, but `:185` is the legend comment
(``#   ``pending-batch-a``    — a real routing target that is genuinely UNROUTED.``), so there
are **12 rows**. This matches `contracts/routing-manifest.md`'s 12-rows/13-call-sites split.
T012's `13 → 8` arithmetic still holds because it counts grep hits.

### 6.4 The `129 / 129` pre/post obligation is unmeasurable on a shared branch

See §1. Discharged as an attributable per-file delta instead.

---

## 7. T012 — closeout

### Ledger arithmetic

`pending-batch-a` grep hits **13 → 8**. `git diff <base> -- <ledger>` shows **exactly 5 deleted
lines and 0 added**, nothing else in the file:

```
-    ("src/runtime/next/_internal_runtime/planner.py", "_resolve_workflow_for_mission"): (1, "pending-batch-a"),
-    ("src/runtime/next/runtime_bridge_io.py", "_workflow_runtime_template"): (1, "pending-batch-a"),
-    ("src/specify_cli/bulk_edit/gate.py", "_is_bulk_edit_mission"): (1, "pending-batch-a"),
-    ("src/specify_cli/bulk_edit/gate.py", "ensure_occurrence_classification_ready"): (1, "pending-batch-a"),
-    ("src/specify_cli/missions/_read_path_resolver.py", "read_primary_meta"): (2, "pending-batch-a"),
```

WP03's rows (`context/resolver.py`, `decisions/service.py`, `_resolve_planning_branch.py`) and
WP04's rows (`resolution.py` ×3, `upgrade/feature_meta.py`) verified **byte-identical** to base,
as is the `_read_path_resolver.py` / `_declares_coordination_branch` `silent-by-contract` row.

### Untouched surfaces

- `git diff --stat -- tests/status/test_aggregate_coord_deleted_contract.py` → **empty**; the
  test is green **and byte-identical**.
- `git diff --stat -- src/mission_runtime/` → **empty**.

### Quality table — all four owned source files (plus the out-of-map fifth)

| File | `ruff check` pre → post | `C901` pre → post | `mypy --strict` pre → post |
|---|---|---|---|
| `runtime/next/_internal_runtime/planner.py` | clean → clean | clean → clean | clean → clean |
| `runtime/next/runtime_bridge_io.py` | clean → clean | clean → clean | clean → clean |
| `specify_cli/bulk_edit/gate.py` | clean → clean | clean → clean | clean → clean |
| `specify_cli/missions/_read_path_resolver.py` | clean → clean | clean → clean | clean → clean |
| `specify_cli/coordination/surface_resolver.py` (out-of-map) | — → clean | — → clean | — → clean |

**Out-of-map writes — the complete declared list** *(added post-review-cycle-2; the cycle-2
remediation's own out-of-map edits were made under an explicit reviewer mandate but were never
declared here the way `surface_resolver.py` was, which is the gap this closes)*:

| Path | Why it is out of map | Authority |
|---|---|---|
| `src/specify_cli/coordination/surface_resolver.py` | One line inside an `except` tuple. Restores a documented degrade contract that WP02's routing had silently broken; no routed-call delta. | Declared by WP02 cycle 1 — shipping a known arm change no in-scope test would catch was the worse outcome. |
| `src/specify_cli/cli/commands/agent/mission_setup_plan.py` | Stranded degrade arm on the routed caller chain, widened to `(MissionMetaReadError, ValueError, ActionContextError)`. | Mandated by review cycle 1's BLOCKER. |
| `src/specify_cli/cli/commands/agent/mission_record_analysis.py` | Same. | Same. |
| `src/specify_cli/cli/commands/agent/mission_finalize.py` | Same. | Same. |
| `src/specify_cli/cli/commands/agent/mission_check_prerequisites.py` | Same. | Same. |
| `scripts/sweep_degrade_arms_on_routed_chain_3162.py` | New chain-local sweep instrument; WP03/WP04 route into the same callers and need it. | Mandated by review cycle 1's BLOCKER ("add the sweep as a repeatable instrument"). |
| `tests/specify_cli/cli/commands/agent/test_wp02_cycle2_degrade_arms_on_routed_chain.py` | Red-first pin for the four widened arms; directory is outside WP02's original cone. | Same. |

No other WP owns any of these paths, so there is no ownership conflict; none was touched by a
sibling lane during the cycle.

`ruff check` only; `ruff format` was never run. All five new/edited test files also pass
`ruff check`.

### Commits

**10 WP02 commits**, each red preceding its green, none squashed. The branch also carries WP05
and WP07 commits interleaved (see §1) — those are other lanes', not WP02's.

---

## Review cycle 2 — BLOCKER remediation: four degrade arms on the routed call chain

### The defect and why cycle 1's sweep missed it

Cycle 1's arm sweep was **file-local**: after routing rows 10/11 it searched
`_read_path_resolver.py` for `except` clauses that would stop absorbing corruption, found two,
and fixed them. The sweep needed to be **chain-local** — the routed function's *transitive
callers*. Four arms sit on the chain

```
_find_feature_directory -> resolve_handle_to_read_path -> read_primary_meta
```

several call hops from the edit, in a different package. `MissionMetaReadError`'s MRO is
`MissionMetaReadError -> RuntimeError -> Exception -> BaseException -> object` (measured, no
`ValueError`, no `OSError`), so each `except (ValueError, ActionContextError)` silently stopped
absorbing corruption the moment the site was routed.

### The four arms, widened

All four widened to `(MissionMetaReadError, ValueError, ActionContextError)`, mirroring the two
already fixed in cycle 1. Line numbers re-derived immediately before and after the edit:

| File | pre-edit | post-edit | enclosing symbol |
|---|---|---|---|
| `cli/commands/agent/mission_setup_plan.py` | `:301` | `:311` | `_resolve_setup_plan_feature_dir` |
| `cli/commands/agent/mission_record_analysis.py` | `:259` | `:266` | `record_analysis` |
| `cli/commands/agent/mission_finalize.py` | `:291` | `:298` | `_resolve_mission_slug` |
| `cli/commands/agent/mission_check_prerequisites.py` | `:238` | `:245` | `check_prerequisites` |

Pre-edit text at all four, verbatim: `except (ValueError, ActionContextError) as detection_error:`.

Adding a class to an `except` tuple adds no `load_meta` call: the routed census stayed at
**130** (`scripts/verify_meta_routing_manifest_3162.py` → `VERDICT: PASS`, exit 0).

### What was proven, and what was not

The review brief predicted `setup-plan` and `record-analysis` were behaviourally reachable and
that `finalize-tasks` / `check-prerequisites` were **static hazards only, unreachable in
fixture**. Measurement refined this in both directions:

- **`setup-plan`, `record-analysis` — proven end-to-end, no patching.** A corrupt `meta.json`
  under the composed handle drives the command's public entry; pre-fix the payload is
  `{"error": "Cannot read .../meta.json: ... — fail-closed", ...}` with `error_code`,
  `mission_flag`, `available_missions` and `example_command` **absent**; post-fix the structured
  detection payload is restored. Both exit 1 either way — the regression is invisible to an
  exit-code assertion and lives entirely in the agent-facing JSON.
- **`finalize-tasks`, `check-prerequisites` — the typed error never reaches these two arms; the
  widenings are defensive static hardening.** *(Corrected post-review-cycle-2. This section
  previously claimed "the arm is reached", contradicting cycle 1's "static hazards only". Cycle 2
  instrumented the raise sites on the real corrupt-meta fixture across seven invocation shapes —
  five handle forms plus the `--mission`-less cwd variants — and could not reach either arm with
  `MissionMetaReadError`. On `check-prerequisites`, two raises occur under the guarded `try` but
  are absorbed inside `_stored_topology_best_effort` before reaching the arm, and the third is
  fatal at an unguarded site. When either arm does fire end-to-end it fires with
  `ActionContextError` (`error_code=FEATURE_CONTEXT_UNRESOLVED`), never `MissionMetaReadError`.
  Both widenings are still correct and worth keeping — the static pin blocks re-narrowing, and
  WP03/WP04 route more sites into these chains — but they are **behaviour-neutral today**. This
  was a correction that was itself wrong, the exact pattern the Q7 provenance note warns about.)*

  The second, unguarded read is real and stands. These two read the primary meta **again**, later,
  at a site guarded by no arm at all:
  - `check-prerequisites` → `mission_branch_context._resolve_feature_target_branch` →
    `core.paths.read_target_branch_from_meta`
  - `finalize-tasks` → `_validate_occurrence_map_ready` →
    `bulk_edit.gate.ensure_occurrence_classification_ready`, plus a direct `resolution.read_dir`

  These are **not stranded arms** (the sweep confirms none remain) — they are *absent* arms, a
  different defect class, **outside this bounded fix-list and deliberately not fixed here**.
  Because of them, an end-to-end payload assertion for these two would be testing the unfixed
  site rather than the fixed one, so they are pinned at the seam their arm actually guards.

Honest labelling of the five new tests: **2 behavioural fixture-driven** (`setup-plan`,
`record-analysis`), **2 arm-contract seam-injected** (`finalize-tasks`,
`check-prerequisites`), **1 static** (parametrized ×4, keyed by *symbol* not line number so
benign edits cannot make it false-red).

Red → green, input counts printed:
`tests/specify_cli/cli/commands/agent/test_wp02_cycle2_degrade_arms_on_routed_chain.py`
→ **8 collected: 8 failed / 0 passed** pre-fix, **8 passed** post-fix. Every red was verified to
fail *for the stated reason* (the first red run failed on `PROJECT_ROOT_NOT_FOUND` — a fixture
defect, not the arm — and was corrected before being counted).

`tests/specify_cli/cli/commands/agent/` is outside WP02's original declared cone, which is why
cycle 1 never ran it: **1552 → 1560 collected, 1550 → 1558 passed, 2 xfailed, exit 0**, zero
`^ERROR tests/`. The `+8` is exactly this file.

### The durable instrument

`scripts/sweep_degrade_arms_on_routed_chain_3162.py` — an import-resolved fixpoint over `src/`,
seeded with the routed function, that reports every `except` clause a routing would strand.

It is **not** plain reverse reachability. A frame that absorbs the exception shields every frame
above it, so a reachability sweep reports the whole blast radius: seeded naively it returned
**15** arms at base, drowning the answer. It instead propagates the typed error outward and stops
at the **first guarding frame on each path** — the frontier you must actually fix. Widen those,
re-run, and the next frontier surfaces.

**Known-answer validation.** The brief's recorded control was "exactly the two arms WP02 already
fixed" at base `f1681bf1`. **That control is wrong, and the instrument disproves it**: at base the
correct answer is **six** — the two file-local arms *plus* the four command-chain arms, which
exist unchanged at base and are exactly what this BLOCKER is about. A control of 2 would have
demanded the instrument be blind to the defect it exists to catch.

```
$ .venv/bin/python scripts/sweep_degrade_arms_on_routed_chain_3162.py --rev f1681bf1
  modules parsed  : 1199        functions indexed: 9831
  HAZARDS: 6
    surface_resolver.py:564            (try at :562)   _husk_is_authoritative_surface
    _read_path_resolver.py:1257        (try at :1252)  _stored_topology_best_effort
    mission_check_prerequisites.py:238 (try at :230)   check_prerequisites
    mission_finalize.py:291            (try at :289)   _resolve_mission_slug
    mission_record_analysis.py:259     (try at :253)   record_analysis
    mission_setup_plan.py:301          (try at :293)   _resolve_setup_plan_feature_dir
```

The two cycle-1 arms are reproduced at their recorded locations, and the four BLOCKER arms are
**rediscovered independently**, at the exact line numbers the reviewer cited, without the
instrument being told about them. The differential is the real control:

| tree | hazards |
|---|---|
| base `f1681bf1` | **6** |
| cycle-2 HEAD, before this fix | **4** (the two cycle-1 arms now absorbed) |
| cycle-2 HEAD, after this fix | **0 — `VERDICT: CLEAN`, exit 0** |

Getting the model wrong is detectable: the first implementation resolved calls without following
re-export shims (`mission.py` re-exports `_find_feature_directory`) and found only **3** of the 6.
The known answer caught it. A sweep whose control did not reproduce is not a sweep — hence
`--expect`, which fails the run when the control drifts.

**WP03 and WP04 route more sites into these same callers.** Run this **before** claiming a green,
seeded with whatever function the work package routes:

```
.venv/bin/python scripts/sweep_degrade_arms_on_routed_chain_3162.py --seed <routed_function>
```

Exit status is `1` on any hazard, so it drops straight into a gate.

### Why `SC-002`'s existing probe structurally cannot see this class

`SC-002` is a "**4 degrade sites × 3 shapes**" probe: its subject is the routed **site**, and it
varies content shape per site. A stranded arm is by construction **not at a site** — it is at a
*caller*, often in another package, that never appears in a site-scoped enumeration. The two axes
are orthogonal, so no number of shapes per site can reach a caller, and a green `SC-002` carries
**no information** about this defect class. That is why the chain-local sweep is a separate,
caller-scoped instrument rather than another shape added to `SC-002`.

### Quality gate (cycle 2)

`ruff check` clean on all six touched/added files (`ruff format` never run). `mypy --strict`
introduces **zero** new errors: the 10 `no-any-return` findings across
`mission_setup_plan.py` / `mission_finalize.py` / `mission_check_prerequisites.py` are
**pre-existing** — the identical 10, in the identical functions, are reproduced by running
`mypy --strict` on the unmodified `HEAD` copies of those files (line numbers shift only by the
comment lines this change adds). Per the charter's pre-existing-failure rule they are reported,
not fixed, being outside this change's locality.

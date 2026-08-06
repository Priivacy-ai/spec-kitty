---
work_package_id: WP02
title: Route the 5 refuse-raw ledger rows (6 call sites), each with its ledger row
dependencies:
- WP01
requirement_refs:
- FR-001
- NFR-001
- C-001
- C-008
planning_base_branch: feat/meta-fail-closed-3162
merge_target_branch: feat/meta-fail-closed-3162
branch_strategy: Planning artifacts for this mission were generated on feat/meta-fail-closed-3162. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/meta-fail-closed-3162 unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
- T012
history: []
agent_profile: python-pedro
authoritative_surface: src/
create_intent: []
execution_mode: code_change
owned_files:
- src/runtime/next/_internal_runtime/planner.py
- src/runtime/next/runtime_bridge_io.py
- src/specify_cli/bulk_edit/gate.py
- src/specify_cli/missions/_read_path_resolver.py
- tests/specify_cli/test_meta_fail_closed_full_census_contract.py
- tests/specify_cli/bulk_edit/**
- tests/next/**
- tests/runtime/**
- tests/missions/**
role: implementer
tags: []
tracker_refs: []
---

# WP02 — Route the 5 refuse-raw ledger rows (6 call sites)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Route the **refuse-raw** `meta.json` reads — the ones that today let a bare `ValueError` escape — onto
`load_meta_fail_closed`, so a corrupt `meta.json` raises the typed `MissionMetaReadError` instead. Scope is
**5 ledger rows / 6 call sites** (see the arithmetic below), and each routing edit lands in the **same
commit** as the deletion of its own `pending-batch-a` ledger row. No arm changes anywhere (`C-001`).

## Where this WP runs, how to start it, and where its evidence lands

**This WP runs from the repository root.** Do not reconstruct a worktree path yourself; every path below is
repo-relative from the tree you are in. Start with `spec-kitty implement WP02` — `spec-kitty agent action
implement WP02 --agent <name>` does **not** resolve a workspace, its `--help` reads *"Display work package
prompt with implementation instructions."*, and `CLAUDE.md` § Execution Workspace Strategy is explicit that
*"`spec-kitty implement WP##` is the only supported way to prepare a workspace."*

**`PYTHONPATH=<workspace>/src` on every `python -c` and every `pytest` that could run outside the repository
root.** The split-tree hazard produces a *silently wrong* answer rather than an error:
`.venv/lib/python3.11/site-packages/_editable_impl_spec_kitty_cli.pth` pins `specify_cli` / `runtime` imports to
the **main** tree's `src/`, while `SRC_ROOT` in the gate
(`tests/architectural/test_inline_meta_read_gate.py:61`) and `_SRC_ROOT` in the ledger test
(`tests/specify_cli/test_meta_fail_closed_full_census_contract.py:54`) derive from **the test file's own
location**. Outside the install tree the AST census reads the *edited* `src/` while behavioural assertions import
the *unedited* one — which is exactly this WP's shape: each subtask's **structural** proof (the call-count
assertion) goes green off the edited source while its **behavioural** twin (the `load_meta_fail_closed`
traceback frame) stays red off the unedited source, with no diagnosable cause. Nothing provisions `.venv` into a
git worktree (`.gitignore:31-32`), so `.venv/bin/python` only resolves at the root.

**Committed evidence destination.** `mark-status` exposes only `--status`, `--mission`, `--auto-commit`,
`--json`; its payload is `WPInnerStateDelta.subtasks: Mapping[str, Status]`
(`src/specify_cli/status/models.py:481`) — a bare `{T0xx: Status}`. **The record carries no evidence field, and
an earlier draft of this prompt claimed it "carries the evidence named in that subtask's Validation block". That
claim was false and is struck.** This WP's committed destination is
`kitty-specs/meta-fail-closed-3162-01KZ7FSQ/evidence/WP02-evidence.md`, a declared **out-of-map** planning write
with a one-line rationale (`kitty-specs/` paths cannot appear in `owned_files` by construction —
`mission_parsing.py:153-157`, `:207-215`). `$EV` under `/tmp` is a **scratch redirect target only**; every
number, quoted red, SHA and grep result it holds is copied into that committed file before the subtask is
marked.

## Context

**Scope arithmetic, stated explicitly, because the two counting conventions differ.**
**7 refuse-raw call sites − 1** (census row 8, `src/specify_cli/context/resolver.py`
`_read_meta_json`, which moves to WP03 because it is an `allow_missing=False` site) **= 6 call sites =
5 ledger rows**, because `read_primary_meta` carries census rows 10 and 11 under **one** ledger row with
count 2. **Never write "5" or "6" unqualified in any commit message, comment, test id or report — always
say which convention you mean** (`5 ledger rows` / `6 call sites`).

The 6 call sites, by symbol (`C-003` — cite `file:line` *and* symbol; line numbers shift under this
mission's own edits):

| Census row | Ledger row key | Site (as of now) | Symbol |
|---|---|---|---|
| 4 | `planner.py` / `_resolve_workflow_for_mission` | `src/runtime/next/_internal_runtime/planner.py:188` | `_resolve_workflow_for_mission` |
| 5 | `runtime_bridge_io.py` / `_workflow_runtime_template` | `src/runtime/next/runtime_bridge_io.py:380` | `_workflow_runtime_template` |
| 6 | `gate.py` / `_is_bulk_edit_mission` | `src/specify_cli/bulk_edit/gate.py:57` | `_is_bulk_edit_mission` |
| 7 | `gate.py` / `ensure_occurrence_classification_ready` | `src/specify_cli/bulk_edit/gate.py:80` | `ensure_occurrence_classification_ready` |
| 10 + 11 | `_read_path_resolver.py` / `read_primary_meta` (count **2**) | `:846` and `:862` | `read_primary_meta` |

**The seam.** `load_meta_fail_closed(feature_dir)` — `src/specify_cli/core/paths.py`, symbol
`load_meta_fail_closed`. One positional arg, no kwargs, hard-codes `allow_missing=True,
on_malformed="raise"`. It raises `MissionMetaReadError` (symbol `MissionMetaReadError` in the same module,
MRO `RuntimeError → Exception` — **not** a `ValueError`) with the underlying decode error as `__cause__`.
It keeps a **load-bearing deferred import** of `specify_cli.mission_metadata` *inside* the function body to
avoid re-forming the `core.paths ↔ mission_metadata` cycle. **Do not "tidy" that deferred import.**

**The coupling that defines every commit in this WP.**
`tests/specify_cli/test_meta_fail_closed_full_census_contract.py` holds the `pending-batch-a` routing
ledger (`_ACCOUNTED_SITES`) and gates on **exact equality in both directions** — its own maintenance banner
says *"If you ROUTE a site, DELETE its row"*. `test_no_unaccounted_load_meta_call_sites` asserts three
arms: `unaccounted` (a live site with no row), `grew` (more live calls than the row's count), and `stale`
(a row the live scan no longer finds). So **each routing edit and its own ledger-row deletion are ONE
commit.** Routing without deleting the row fails the `stale` arm; deleting without routing fails the
`unaccounted` arm. There is no ordering that passes; they must be atomic.

**Match ledger rows by content, never by line number.** This WP's rows are at `:201`, `:202`, `:203`,
`:204` and `:243` *as of now*, but that file is mutated by five commits in sequence across
WP02 → WP03 → WP04, so a line number is stale the moment the previous commit lands. Every subtask below
re-locates its row with `grep -n` on the row's literal `("<path>", "<symbol>")` key. WP03's rows
(`context/resolver.py`, `decisions/service.py`, `_resolve_planning_branch.py`) and WP04's rows
(`resolution.py` ×3, `upgrade/feature_meta.py`) are **not yours** — leave them byte-identical.

**What the tests must actually do.** `FR-001` requires **real corrupt files driven through public entry
points**. Patching `load_meta_fail_closed` proves nothing. `SC-001` closed a specific cheat this WP must
not reintroduce: wrapping the public entries in `except ValueError: raise MissionMetaReadError(...)`
satisfies "a typed error reaches the caller" with **zero routing** — right type, right message, real file,
real entry point, routed count unchanged, inline gate silent. So each subtask needs **both** proofs:

- **behavioural** — the raised error's traceback contains a frame whose function is `load_meta_fail_closed`
  in `core/paths.py`, and `exc.__cause__` is the underlying decode `ValueError` (preserved, not swallowed);
- **structural** — the call site literally reads `load_meta_fail_closed(`, the module contains **no** local
  `raise MissionMetaReadError`, and the ledger row is gone **in the same commit**.

### The budget is closed by assertion, not by narration — one call-count assertion per routed site

**Every routing subtask in this WP (`T007`–`T011`) must carry a per-site structural call-count assertion**,
in the shape T011 already uses for `read_primary_meta`: parse the module with `ast` and assert, inside the
**routed function's own body**, the **exact** number of `load_meta_fail_closed(` calls and **zero**
`load_meta(` calls. The expected counts are `1, 1, 1, 1, 2` for census rows 4, 5, 6, 7 and 10+11 respectively.
Note `load_meta(` must be matched as an exact callee name, not as a substring — `load_meta_fail_closed(`
contains it.

Why this replaces the pre/post print obligation as the *binding* control (the prints stay; they are not what
closes the budget): a lane-local fold reads **128**, and `128 >= 126`, `128 > 126`, `128 - 126 = 2 <= 4` —
**all three clauses of `test_routed_load_meta_floor` are green**; after WP06 re-derives the floor to 127 the
merged tree's folded **129** is green too. A fold survives both gates, caught only by a printed number a human
has to compare, and lanes B and C are concurrent and file-disjoint so no file-overlap check can see the
coupling. The ledger cannot catch it either: its `grew` arm fires on *more* live calls than a row's count, and a
fold produces *fewer*. Twelve executable assertions across WP02/WP03/WP04 are the instrument.

**The budget.** This WP is **0-net** on the routed count. There is exactly **one** net routed call of
headroom for the whole mission and **WP05** spends it. A 1:1 `load_meta` → `load_meta_fail_closed` swap is
count-neutral because both names are in `ROUTED_CALLEES` (`tests/architectural/test_inline_meta_read_gate.py`,
symbol `ROUTED_CALLEES`) — but **any helper wrapping or second reader call breaks it.** Print the routed
count **pre and post this WP's edits**; both must read **129**. The admissible band is **`[127, 130]`** and
**126 is RED**: `test_routed_load_meta_floor` asserts `len >= FLOOR`, `len > FLOOR` (anti-vacuous) and
`len - FLOOR <= MARGIN` against `ROUTED_LOAD_META_FLOOR = 126` / `ROUTED_LOAD_META_FLOOR_MARGIN = 4`. The
bound is **two-sided** — folding rows 10 and 11 into a single call reds the gate *downward*.

**Discipline.**

- `src/mission_runtime/` is **not** this WP's surface. All three `resolution.py` sites are degrade sites
  owned by WP04. Do not touch them.
- `tests/missions/**` is shared with WP03; that is legal only because WP02 → WP03 is a dependency chain.
  Stay inside your own subtask's files.
- **Test cone for this WP:** `tests/next`, `tests/runtime`, `tests/missions`,
  `tests/specify_cli/bulk_edit`, plus the ledger test. Run-only (never edited):
  `tests/status/test_aggregate_coord_deleted_contract.py`,
  `tests/architectural/test_inline_meta_read_gate.py::test_routed_load_meta_floor`.
  **Never** run `tests/sync` or `tests/cli` — sibling missions may hold those windows (`C-007`).
- **Never pipe a suite whose exit status you need.** Redirect to a file, echo `$?`, then `grep` the
  `N passed` line out of the file. Print the **selected** count too (`--collect-only -q`, redirected).
- `ruff check` only, **never** `ruff format`.
- Charter §ATDD-First: the failing test is its **own commit**, before the implementation commit. Coupling
  D2 binds routing↔ledger-deletion only, so per ledger row you land **two** commits: (1) red ATDD test,
  (2) routing + ledger-row deletion. `plan.md`'s IC-02 "one commit per ledger row … + its test" is
  ambiguous here; the charter wins (see Risks).
- Evidence scratch: `export EV=/tmp/wp02-3162-evidence && mkdir -p "$EV"`. `$EV` is a **redirect target, not
  the evidence**. Nothing under `$EV` is committed, so everything it holds that a reviewer must read is copied
  into `kitty-specs/meta-fail-closed-3162-01KZ7FSQ/evidence/WP02-evidence.md` — the committed destination — as
  each subtask closes. A number that exists only under `$EV` is a number the reviewer cannot see.

**Measurement commands** (use these verbatim; from the workspace root):

```bash
# Routed census (the budget). Expect 129 pre AND post this WP.
.venv/bin/python -c "from tests.architectural.test_inline_meta_read_gate import \
scan_routed_load_meta_calls, SRC_ROOT; print(len(scan_routed_load_meta_calls(SRC_ROOT)))"

# Live unrouted load_meta census, keyed (path, qualname) -> count.
.venv/bin/python -c "from tests.specify_cli.test_meta_fail_closed_full_census_contract import \
scan_load_meta_call_sites, _SRC_ROOT; \
print(sorted((k, n) for k, n in scan_load_meta_call_sites(_SRC_ROOT).items()))"
```

---

### Subtask T006: Baseline — routed count, ledger inventory, cone green, quality gates

**Purpose**
Establish the pre-edit numbers this WP is judged against, so every later delta is attributable. Nothing in
this subtask edits `src/`. `NFR-002`'s two-sided bound and the `[127, 130]` band are recorded here.

**Steps**

1. `export EV=/tmp/wp02-3162-evidence && mkdir -p "$EV"` and record `git rev-parse HEAD` to
   `$EV/base-sha.txt`. That SHA is this WP's `planning_base_branch` anchor for the red→green check.
2. Print the routed census with the command above; redirect to `$EV/routed-pre.txt`. **Assert it reads
   `129`.** If it does not, stop and report: the band is `[127, 130]`, `126` is RED, and a pre-edit value
   outside `129` means the tree drifted and WP01's manifest anchor no longer holds.
3. Quote the three assertions of `test_routed_load_meta_floor` (symbol, in
   `tests/architectural/test_inline_meta_read_gate.py`) verbatim into `$EV/band.txt`, together with
   `ROUTED_LOAD_META_FLOOR = 126` and `ROUTED_LOAD_META_FLOOR_MARGIN = 4`, and the derived band
   `[127, 130]` with the note **126 is RED**.
4. Inventory your five ledger rows **by content**, not line number:
   `grep -n 'pending-batch-a' tests/specify_cli/test_meta_fail_closed_full_census_contract.py > $EV/ledger-pre.txt`.
   Confirm all 13 `pending-batch-a` rows are present and that exactly these five are yours:
   `planner.py`/`_resolve_workflow_for_mission`, `runtime_bridge_io.py`/`_workflow_runtime_template`,
   `gate.py`/`_is_bulk_edit_mission`, `gate.py`/`ensure_occurrence_classification_ready`,
   `_read_path_resolver.py`/`read_primary_meta` (count `2`).
5. Print the selected count and run the cone green at baseline, redirected, exit status echoed:
   ```bash
   .venv/bin/python -m pytest tests/next tests/runtime tests/missions \
     tests/specify_cli/bulk_edit tests/specify_cli/test_meta_fail_closed_full_census_contract.py \
     tests/status/test_aggregate_coord_deleted_contract.py \
     --collect-only -q > $EV/cone-selected-pre.txt 2>&1; echo "exit=$?"
   .venv/bin/python -m pytest tests/next tests/runtime tests/missions \
     tests/specify_cli/bulk_edit tests/specify_cli/test_meta_fail_closed_full_census_contract.py \
     tests/status/test_aggregate_coord_deleted_contract.py \
     -q -ra > $EV/cone-pre.txt 2>&1; echo "exit=$?"
   grep -E '[0-9]+ (passed|failed)' $EV/cone-pre.txt
   grep -c '^ERROR tests/' $EV/cone-pre.txt
   ```
   `-ra`, never `-rf`. Count `^ERROR tests/`, not bare `^ERROR`. Any baseline red must be classified
   pre-existing (same selection on `$EV/base-sha.txt`) before you touch code — never green-washed.
6. Capture the quality-gate baseline on the four owned source files, per file:
   `ruff check --select C901 <file>` and `ruff check <file>` and
   `.venv/bin/python -m mypy --strict <file>`, all redirected to `$EV/quality-pre.txt`. These are
   criteria, not afterthoughts.

**Files**
Read-only over `src/`. Writes only under `$EV`.

**Validation**
`$EV/routed-pre.txt` reads `129`; `$EV/band.txt` states `[127, 130]` and "126 is RED";
`$EV/ledger-pre.txt` shows your five rows located by key; the cone's `N passed` line and selected count are
quoted with `exit=` shown; `$EV/quality-pre.txt` holds a per-file pre value for all four files.

---

### Subtask T007: Route census row 4 — `planner._resolve_workflow_for_mission`, with its ledger row

**Purpose**
`src/runtime/next/_internal_runtime/planner.py`, symbol `_resolve_workflow_for_mission` (`:188` as of now):
`load_meta(mission_dir)` with no `try`, so a corrupt `meta.json` throws a bare `ValueError` straight onto
the `spec-kitty next` path. Route it; keep the `if meta is None:` default-workflow arm exactly as it is
(`C-001` — no arm changes).

**Steps**

1. **Red-first commit.** Add `tests/next/test_wp02_row04_planner_fail_closed.py` with a test id naming
   census row 4. Write a real corrupt `meta.json` (`tmp_path/"meta.json"` containing `{"workflow_id":`) and
   drive it through the **public** entry `runtime.next.runtime_bridge_engine.resolve_workflow_for_mission`
   (symbol; it delegates to `_resolve_workflow_for_mission` by live attribute lookup). No patching of
   `load_meta_fail_closed`. Assert:
   - `pytest.raises(MissionMetaReadError)` (import the symbol from `specify_cli.core.paths`);
   - **behavioural** — `"load_meta_fail_closed" in [f.name for f in traceback.extract_tb(exc.__traceback__)]`
     and the same frame's `filename` ends with `core/paths.py`; and `isinstance(exc.__cause__, ValueError)`;
   - **structural, as a call-count assertion** — parse `planner.py` with `ast` and assert that
     `_resolve_workflow_for_mission`'s **own body** contains **exactly one** `load_meta_fail_closed(` call and
     **zero** `load_meta(` calls (exact callee name, not substring — `load_meta_fail_closed` contains
     `load_meta`). Plus: `"raise MissionMetaReadError"` appears **nowhere** in the module, and the module has
     no `except ValueError` around the read. The count assertion is what closes the budget for this row; a
     `"load_meta_fail_closed(" in source` substring check is green under a fold and does not;
   - **negative control** — a *valid* `meta.json` and an *absent* `meta.json` both still resolve
     `software-dev-default` cleanly (`NFR-001`'s absent-file arm).
   Commit the test alone. Run it, redirect, quote the failing assertion into `$EV/T007-red.txt`, and record
   the commit SHA.
2. **Green commit — routing + ledger row, atomic.** In `planner.py`:
   - replace the module-level `from specify_cli.mission_metadata import load_meta` (`:37`) with
     `from specify_cli.core.paths import load_meta_fail_closed`. `load_meta` has exactly **one** use in
     this module, so leaving the old import trips `ruff` F401 — confirm with
     `grep -n 'load_meta\b' src/runtime/next/_internal_runtime/planner.py`. The module already imports
     `specify_cli.core.constants` at module level, so a module-level `core.paths` import forms no new
     cycle; verify by importing the module in a fresh interpreter.
   - swap the call **1:1**: `meta = load_meta_fail_closed(mission_dir)`. One call in, one call out — no
     helper, no second read. Anything else breaks 0-net.
   - update the stale two-line comment above the call that names `load_meta` and its `allow_missing`/
     `on_malformed` contract; it now documents the wrong reader. Leaving it is canonical-authority drift.
3. In the **same commit**, delete this site's ledger row from
   `tests/specify_cli/test_meta_fail_closed_full_census_contract.py`. Locate it by content:
   `grep -n '"src/runtime/next/_internal_runtime/planner.py", "_resolve_workflow_for_mission"' <file>`.
   Delete that one line only.
4. Run the row's own test plus the ledger test, redirected; then print the routed census and confirm it
   still reads **129** (`$EV/T007-routed.txt`).
5. `ruff check` and `.venv/bin/python -m mypy --strict` on `planner.py`; append to `$EV/quality-post.txt`
   with the `C901` pre/post pair for this file.

**Files**
`src/runtime/next/_internal_runtime/planner.py`;
`tests/specify_cli/test_meta_fail_closed_full_census_contract.py` (one row deleted);
`tests/next/test_wp02_row04_planner_fail_closed.py` (new).

**Validation**
Red SHA with its quoted failure, then green SHA; `git show --stat <green>` shows the routing **and** the
row deletion in one commit; both arms of `test_no_unaccounted_load_meta_call_sites` green; routed census
`129`; `ruff check` and `mypy --strict` clean.

---

### Subtask T008: Route census row 5 — `runtime_bridge_io._workflow_runtime_template`, with its ledger row

**Purpose**
`src/runtime/next/runtime_bridge_io.py`, symbol `_workflow_runtime_template` (`:380` as of now):
`load_meta(mission_dir)`, bare default, no `try` — refuse-raw. Route it; keep the `if meta is None: return
None, None` arm and the `workflow_id is None` arm untouched.

**Steps**

1. **Red-first commit.** Add `tests/runtime/test_wp02_row05_bridge_io_fail_closed.py`, test id naming
   census row 5. Build a **real** repo-root / runtime-bridge fixture — `plan.md` flags that row 5's earlier
   "too expensive to fixture" claim rested on no attempted construction, so construct it: a `tmp_path`
   repo root with `kitty-specs/<slug>-<mid8>/meta.json` written corrupt, and drive the public entry
   `runtime.next.runtime_bridge_io.get_or_start_run` (symbol, `:469` as of now; `_start_ephemeral_query_run`
   at `:431` is the second caller and is an acceptable second probe). Neighbouring tests in
   `tests/runtime/test_bridge_io.py` show the fixture shape — reuse it, do not invent one.
2. Assert the same four things as T007 step 1: typed raise; behavioural traceback frame in
   `load_meta_fail_closed` plus `__cause__` preserved; **structural as a call-count assertion** — `ast`-parse
   `runtime_bridge_io.py` and assert `_workflow_runtime_template`'s **own body** holds **exactly one**
   `load_meta_fail_closed(` call and **zero** `load_meta(` calls (exact callee name), with no local
   `raise MissionMetaReadError` in the module; negative control on valid **and** absent `meta.json` returning
   `(None, None)` as before.
3. Commit the test alone, quote its red into `$EV/T008-red.txt`, record the SHA.
4. **Green commit — routing + ledger row, atomic.** Replace the module-level
   `from specify_cli.mission_metadata import load_meta` (`:102`) with
   `from specify_cli.core.paths import load_meta_fail_closed` — confirm with
   `grep -n 'load_meta\b' src/runtime/next/runtime_bridge_io.py` that `:380` is the module's only use.
   Swap the call **1:1** and update the stale `load_meta` contract comment above it.
5. In the **same commit**, delete the ledger row located by content:
   `grep -n '"src/runtime/next/runtime_bridge_io.py", "_workflow_runtime_template"' tests/specify_cli/test_meta_fail_closed_full_census_contract.py`.
6. Run the row's test + the ledger test + `tests/runtime` (redirected, exit echoed, `N passed` quoted).
   Print the routed census → must read **129**.
7. `ruff check` + `mypy --strict` on `runtime_bridge_io.py`; append the `C901` pre/post pair.

**Files**
`src/runtime/next/runtime_bridge_io.py`;
`tests/specify_cli/test_meta_fail_closed_full_census_contract.py` (one row deleted);
`tests/runtime/test_wp02_row05_bridge_io_fail_closed.py` (new).

**Validation**
Red SHA quoted, green SHA green; one commit carries routing + row deletion; ledger equality holds both
directions; routed census `129`; `ruff`/`mypy` clean.

---

### Subtask T009: Route census row 6 — `gate._is_bulk_edit_mission`, with its ledger row

**Purpose**
`src/specify_cli/bulk_edit/gate.py`, symbol `_is_bulk_edit_mission` (`:57` as of now):
`meta = load_meta(feature_dir)` then `return meta is not None and meta.get("change_mode") == "bulk_edit"`.
Refuse-raw — a corrupt `meta.json` throws `ValueError` out of the bulk-edit gate. Route it; the
`meta is not None` guard stays exactly as written.

**Steps**

1. **Red-first commit.** Add or extend `tests/specify_cli/bulk_edit/test_wp02_row06_gate_fail_closed.py`
   (test id naming census row 6). Drive a real corrupt `meta.json` through the public entry
   `specify_cli.bulk_edit.gate.check_review_diff_compliance` (symbol; it calls `_is_bulk_edit_mission` at
   `:242`) — **not** `ensure_occurrence_classification_ready`, which reads `meta` itself first at `:80` and
   is row 7's entry point. Choosing the wrong entry point silently tests the other row.
2. Assert typed raise + behavioural traceback frame + `__cause__` + **structural as a call-count assertion**:
   `ast`-parse `gate.py` and assert `_is_bulk_edit_mission`'s **own body** holds **exactly one**
   `load_meta_fail_closed(` call and **zero** `load_meta(` calls (exact callee name), with no local
   `raise MissionMetaReadError` in the module. Scope the assertion to **that function's body**, not the
   module: `ensure_occurrence_classification_ready` still holds a live `load_meta(` call at this commit, so a
   module-wide zero-`load_meta` assertion is red here and only becomes true at T010. Negative controls: a
   valid non-bulk-edit `meta.json` returns `False`, a valid
   `change_mode: bulk_edit` returns `True`, and an absent `meta.json` returns `False` unchanged.
3. Commit the test alone; quote the red into `$EV/T009-red.txt`; record the SHA.
4. **Green commit — routing + ledger row, atomic.** In `gate.py`, **add**
   `from specify_cli.core.paths import load_meta_fail_closed` at module level and **keep** the existing
   `from specify_cli.mission_metadata import load_meta` (`:17`) — `:80` is still unrouted at this point and
   removing the import here breaks it. The import removal belongs to T010. Swap `:57` **1:1** to
   `load_meta_fail_closed(feature_dir)`; leave `:80` alone.
5. In the **same commit**, delete the row located by content:
   `grep -n '"src/specify_cli/bulk_edit/gate.py", "_is_bulk_edit_mission"' tests/specify_cli/test_meta_fail_closed_full_census_contract.py`.
   The sibling `gate.py` / `ensure_occurrence_classification_ready` row **must survive this commit** — the
   `unaccounted` arm needs it while `:80` is still live. Verify both facts in the diff.
6. Run `tests/specify_cli/bulk_edit` + the ledger test, redirected. Print the routed census → **129**.
7. `ruff check` + `mypy --strict` on `gate.py` (`ruff` will not yet flag `load_meta` — it is still used).

**Files**
`src/specify_cli/bulk_edit/gate.py` (site `:57` and one import added);
`tests/specify_cli/test_meta_fail_closed_full_census_contract.py` (one row deleted, one row deliberately
retained); `tests/specify_cli/bulk_edit/test_wp02_row06_gate_fail_closed.py` (new).

**Validation**
Red then green SHAs; the diff shows exactly one row deleted and the sibling row intact; ledger equality
green in both directions **with** row 7 still ledgered; routed census `129`; `ruff`/`mypy` clean.

---

### Subtask T010: Route census row 7 — `gate.ensure_occurrence_classification_ready`, with its ledger row

**Purpose**
`src/specify_cli/bulk_edit/gate.py`, symbol `ensure_occurrence_classification_ready` (`:80` as of now):
its own `meta = load_meta(feature_dir)` read, separate from `_is_bulk_edit_mission`'s. Refuse-raw. Route
it; the `if meta is None: return GateResult(passed=True, change_mode=None)` arm stays.

**Steps**

1. **Red-first commit.** Add `tests/specify_cli/bulk_edit/test_wp02_row07_gate_entry_fail_closed.py`, test
   id naming census row 7. Drive a real corrupt `meta.json` through
   `specify_cli.bulk_edit.gate.ensure_occurrence_classification_ready` directly — it is public and is the
   entry `spec-kitty implement` uses (`cli/commands/implement.py:1216`), so it needs no wrapper.
2. Assert typed raise + behavioural traceback frame + `__cause__` + **structural as a call-count assertion**:
   `ast`-parse `gate.py` and assert `ensure_occurrence_classification_ready`'s **own body** holds **exactly
   one** `load_meta_fail_closed(` call and **zero** `load_meta(` calls (exact callee name); **and now** the
   whole module holds **zero** `load_meta(` calls and **exactly two** `load_meta_fail_closed(` calls (rows 6
   and 7), which is the assertion that catches a fold of the two `gate.py` reads into one shared helper; no
   local `raise MissionMetaReadError`. Negative controls: absent
   `meta.json` → `GateResult(passed=True, change_mode=None)`; a valid non-bulk-edit mission → passed;
   a valid bulk-edit mission with a good occurrence map → passed.
3. Commit the test alone; quote the red into `$EV/T010-red.txt`; record the SHA.
4. **Green commit — routing + ledger row, atomic.** Swap `:80` **1:1** to
   `load_meta_fail_closed(feature_dir)`. `gate.py` now has **zero** `load_meta` uses, so **remove** the
   module-level `from specify_cli.mission_metadata import load_meta` (`:17`) in this commit — `ruff check`
   F401 is the gate on that. Confirm with `grep -n 'load_meta\b' src/specify_cli/bulk_edit/gate.py` that
   the only remaining matches are `load_meta_fail_closed`.
5. In the **same commit**, delete the row located by content:
   `grep -n '"src/specify_cli/bulk_edit/gate.py", "ensure_occurrence_classification_ready"' tests/specify_cli/test_meta_fail_closed_full_census_contract.py`.
   After this commit **no** `gate.py` row remains in `_ACCOUNTED_SITES`.
6. Run `tests/specify_cli/bulk_edit` + the ledger test + `tests/next/test_occurrence_gate_next_loop.py`
   (the gate is reached from the `next` loop via `runtime_bridge.py:711`), redirected. Print the routed
   census → **129**.
7. `ruff check` + `mypy --strict` on `gate.py`; append the `C901` pre/post pair.

**Files**
`src/specify_cli/bulk_edit/gate.py` (site `:80`, import removed);
`tests/specify_cli/test_meta_fail_closed_full_census_contract.py` (one row deleted);
`tests/specify_cli/bulk_edit/test_wp02_row07_gate_entry_fail_closed.py` (new).

**Validation**
Red then green SHAs; `grep` proves `gate.py` has no `load_meta` import left and no `gate.py` ledger row
remains; ledger equality green both directions; routed census `129`; `ruff` F401 clean; `mypy --strict`
clean.

---

### Subtask T011: Route census rows 10 **and** 11 — `read_primary_meta`, one ledger row of count 2

**Purpose**
`src/specify_cli/missions/_read_path_resolver.py`, symbol `read_primary_meta`: **two** call sites —
`load_meta(primary_dir) or {}` (`:846`, row 10) and `load_meta(canonical_dir) or {}` (`:862`, row 11, the
canonicalize-on-miss re-read). They share **one** ledger row whose count is `2`. This is the subtask where
the two counting conventions bite, and the one place a fold would red the floor downward.

**Steps**

1. **Read the risk before editing.** Both calls must be swapped **individually**. Collapsing them into one
   read, or hoisting a local helper around them, takes this lane's routed census to **128** — and a second
   fold anywhere reaches **126, which is RED**. The `or {}` idiom is preserved verbatim at both sites:
   `load_meta_fail_closed` returns `None` on absence exactly as `load_meta` did, so `or {}` keeps its
   current meaning and no arm changes (`C-001`).
2. **Red-first commit.** Add `tests/missions/test_wp02_rows1011_read_primary_meta_fail_closed.py`, with
   **two** test ids, one naming census row 10 and one naming census row 11. Stay inside this file —
   `tests/missions/**` is shared with WP03.
   - Row 10: a composed handle `<slug>-<mid8>` whose primary `meta.json` is corrupt, driven through the
     public entry `specify_cli.missions._read_path_resolver.read_primary_meta` (symbol) — or through
     `resolve_handle_to_read_path` (`:966` calls it), which is the wider public seam.
   - Row 11: a **non-composed** handle (bare `mid8` or full ULID) so the topology-blind compose misses and
     the canonicalize-on-miss branch at `:862` executes with corrupt JSON. `plan.md` records that
     `tests/status/test_aggregate_coord_deleted_contract.py:70-92` already drives exactly this path with
     bare-`mid8`/full-ULID handles — copy that fixture shape; do **not** edit that file.
3. Assert, per row: typed raise + behavioural traceback frame in `load_meta_fail_closed` + `__cause__`
   preserved + structural. The structural assertion here is stronger than elsewhere: parse the module and
   assert `read_primary_meta`'s body contains **exactly two** `load_meta_fail_closed(` calls and **zero**
   `load_meta(` calls, so a fold is caught by the test and not only by the floor. Negative controls: valid
   primary meta returns `(meta, declares_coordination)` unchanged; absent primary meta returns `({}, False)`
   unchanged; an ambiguous handle still propagates `MissionSelectorAmbiguous`
   (symbol, `_read_path_resolver.py:44`, a plain `Exception` — **not** a `ValueError`, so nothing you add
   may catch it).
4. Commit the tests alone; quote both reds into `$EV/T011-red.txt`; record the SHA.
5. **Green commit — both routings + the one ledger row, atomic.** In `read_primary_meta`:
   - delete the in-function `from specify_cli.mission_metadata import load_meta` (`:843`) and add
     `load_meta_fail_closed` to the **existing** module-level
     `from specify_cli.core.paths import WorkspaceRootNotFound, resolve_canonical_root` (`:28`). `core.paths`
     is already a module-level dependency of this file, so no new cycle is formed.
   - **Do not touch** the *other* in-function `from specify_cli.mission_metadata import load_meta` at `:113`
     feeding `_declares_coordination_branch` (`:115`, `on_malformed="none"`). That is a
     `silent-by-contract` site and not this mission's.
   - swap both calls 1:1: `load_meta_fail_closed(primary_dir) or {}` and
     `load_meta_fail_closed(canonical_dir) or {}`. Keep the long explanatory comment block at `:848-860`
     (the #1848 divergence rationale) intact.
6. In the **same commit**, delete the single ledger row located by content:
   `grep -n '"src/specify_cli/missions/_read_path_resolver.py", "read_primary_meta"' tests/specify_cli/test_meta_fail_closed_full_census_contract.py`.
   The neighbouring `_read_path_resolver.py` / `_declares_coordination_branch` row is
   `silent-by-contract` and **must survive**.
7. Run, redirected: the new tests, the ledger test, `tests/missions`, and the run-only
   `tests/status/test_aggregate_coord_deleted_contract.py` — the last must be **green without being
   edited**. If it needs editing, rows 10/11's behaviour changed and this subtask stops.
   Print the routed census → must read **129**, and print the two-call structural check explicitly.
8. `ruff check` + `mypy --strict` on `_read_path_resolver.py`; append the `C901` pre/post pair.

**Files**
`src/specify_cli/missions/_read_path_resolver.py`;
`tests/specify_cli/test_meta_fail_closed_full_census_contract.py` (one row deleted);
`tests/missions/test_wp02_rows1011_read_primary_meta_fail_closed.py` (new).

**Validation**
Two reds quoted, one green commit carrying both routings + the row deletion; the structural test proves
**two** routed calls (no fold); `tests/status/test_aggregate_coord_deleted_contract.py` green and
byte-identical (`git diff --stat` prints nothing for it); routed census `129`; `ruff`/`mypy` clean.

---

### Subtask T012: Close the WP — 0-net proof, ledger equality, cone sweep, evidence

**Purpose**
Prove the WP is 0-net on the routed count, that all five of its ledger rows are gone and no others were
touched, and that the cone is green. This is where the pre/post pair required by the Headroom Allocation
table is completed.

**Steps**

1. Print the routed census post-edits into `$EV/routed-post.txt`. **It must read `129`, identical to
   `$EV/routed-pre.txt`.** Quote both files side by side and state the delta as `0`. If the delta is
   anything other than `0` — including **−1**, which trends toward the RED `126` — stop and report; the
   band is `[127, 130]` and this WP has no headroom (WP05 spends the mission's single net call).
2. Confirm the ledger arithmetic by content, not line number:
   `grep -c 'pending-batch-a' tests/specify_cli/test_meta_fail_closed_full_census_contract.py` must have
   dropped from **13** to **8**, and `git diff $(cat $EV/base-sha.txt) -- tests/specify_cli/test_meta_fail_closed_full_census_contract.py`
   must show exactly **five** deleted lines and **zero** other changes. Quote the five deleted rows from
   the diff. WP03's and WP04's rows must be untouched.
3. Run the whole cone, redirected, exit echoed, selected count printed:
   ```bash
   .venv/bin/python -m pytest tests/next tests/runtime tests/missions \
     tests/specify_cli/bulk_edit tests/specify_cli/test_meta_fail_closed_full_census_contract.py \
     tests/status/test_aggregate_coord_deleted_contract.py \
     --collect-only -q > $EV/cone-selected-post.txt 2>&1; echo "exit=$?"
   .venv/bin/python -m pytest tests/next tests/runtime tests/missions \
     tests/specify_cli/bulk_edit tests/specify_cli/test_meta_fail_closed_full_census_contract.py \
     tests/status/test_aggregate_coord_deleted_contract.py \
     -q -ra > $EV/cone-post.txt 2>&1; echo "exit=$?"
   grep -E '[0-9]+ (passed|failed)' $EV/cone-post.txt; grep -c '^ERROR tests/' $EV/cone-post.txt
   ```
   Do **not** add `tests/sync` or `tests/cli` (`C-007`).
4. Run the two-sided floor gate as a run-only check:
   `.venv/bin/python -m pytest tests/architectural/test_inline_meta_read_gate.py::test_routed_load_meta_floor -q -ra`
   redirected; quote the `1 passed` line. Do not edit that file — it is WP06's surface.
5. Confirm `git diff --stat` prints nothing for
   `tests/status/test_aggregate_coord_deleted_contract.py` and nothing under `src/mission_runtime/`.
6. Assemble the per-file quality table: `ruff check` clean and `mypy --strict` clean on all four owned
   source files, with the `C901` pre/post pair quoted per file from `$EV/quality-pre.txt` and
   `$EV/quality-post.txt`.
7. `git log --oneline $(cat $EV/base-sha.txt)..HEAD` — expect **10** commits (5 red ATDD + 5
   routing+ledger), with each red preceding its green. Confirm none was squashed away.

**Files**
No source edits. Writes only under `$EV`.

**Validation**
`129` pre and `129` post with the delta stated as `0`; five ledger rows deleted and nothing else in that
file; the cone's `N passed` and selected count quoted with `exit=`; `test_routed_load_meta_floor` green;
`ruff`/`mypy` clean per file; `git log` shows the 10 commits in red→green order.

---

## Definition of Done

`spec-kitty agent tasks mark-status <Txxx> --status done --mission meta-fail-closed-3162-01KZ7FSQ` marks a
subtask **done and nothing more**: the command exposes only `--status`, `--mission`, `--auto-commit` and
`--json`, and its payload is a bare `{T0xx: Status}` (`src/specify_cli/status/models.py:481`). **It carries no
evidence.** A checkbox is not evidence and neither is the `mark-status` record; the evidence is the committed
`kitty-specs/meta-fail-closed-3162-01KZ7FSQ/evidence/WP02-evidence.md`, which must contain, per subtask,
everything named in that subtask's Validation block.

- [ ] Every routed subtask (`T007`–`T011`) carries a **per-site call-count assertion** — the exact number of
      `load_meta_fail_closed(` calls (`1, 1, 1, 1, 2`) and **zero** `load_meta(` calls in the routed
      function's own body, matched on the exact callee name. Five assertions, not five prints.
- [ ] Every `python -c` / `pytest` run outside the repository root carries `PYTHONPATH=<workspace>/src`, and
      the evidence names which tree each count came from.

- `spec-kitty agent tasks mark-status T006 --status done` — routed census `129` pre; the `[127, 130]` band
  and "126 is RED" recorded from the three quoted assertions; five ledger rows inventoried by key; cone
  green at baseline with selected count; per-file `ruff`/`C901`/`mypy` baseline.
- `spec-kitty agent tasks mark-status T007 --status done` — census row 4 routed; red SHA + quoted failure,
  green SHA; routing and row deletion in **one** commit; routed census `129`.
- `spec-kitty agent tasks mark-status T008 --status done` — census row 5 routed; real repo-root fixture, no
  patching of `load_meta_fail_closed`; red/green SHAs; one atomic commit; routed census `129`.
- `spec-kitty agent tasks mark-status T009 --status done` — census row 6 routed via
  `check_review_diff_compliance`; the row 7 ledger row deliberately retained and shown intact; routed
  census `129`.
- `spec-kitty agent tasks mark-status T010 --status done` — census row 7 routed; `load_meta` import gone
  from `gate.py` (F401 clean); no `gate.py` row left in `_ACCOUNTED_SITES`; routed census `129`.
- `spec-kitty agent tasks mark-status T011 --status done` — census rows 10 **and** 11 routed as **two**
  calls (structural test proves two, not one); the single count-2 ledger row deleted;
  `tests/status/test_aggregate_coord_deleted_contract.py` green **and** byte-identical; routed census `129`.
- `spec-kitty agent tasks mark-status T012 --status done` — routed census `129` pre and `129` post, delta
  stated as `0`; `pending-batch-a` count 13 → 8 with exactly five deleted lines; cone green with selected
  count; `test_routed_load_meta_floor` green; `ruff`/`mypy` clean on all four files; `git log` showing 10
  commits in red→green order.

Mission-level gates this WP must not break: `FR-001` (7/7 raw-escape sites typed — this WP supplies **6 of
the 7 call sites**, row 8 is WP03's), `NFR-001` (no malformed read yields a value indistinguishable from a
valid one, asserted per site **including the absent-file arm**), `C-001` (no arm changed), `C-008`
(red-first where a red is possible — it is possible at all five ledger rows here, so no exception is
claimed).

## Risks

1. **Splitting a routing from its ledger-row deletion.** The exact-equality gate fails in one direction or
   the other whichever way you order them. Mitigation: stage both edits and commit once; verify with
   `git show --stat <sha>` that the source file **and** the ledger file are both in the commit.
2. **Matching a ledger row by line number.** Five commits mutate that file in sequence across
   WP02 → WP03 → WP04, so `:201`–`:204` and `:243` are stale as soon as an earlier commit lands. Mitigation:
   every subtask re-locates its row with `grep -n` on the literal `("<path>", "<symbol>")` key.
3. **Folding rows 10 and 11 into one read.** Takes the lane to routed `128`; a second fold anywhere reaches
   `126`, which is **RED**. The bound is two-sided, and this programme has already had three floor
   mismatches caused by exactly this kind of collapse. Mitigation: T011's structural test asserts **exactly
   two** `load_meta_fail_closed(` calls in `read_primary_meta`, so the fold is caught by a test rather than
   only by the census.
4. **Reintroducing `SC-001`'s cheat.** `except ValueError: raise MissionMetaReadError(...)` at a public
   entry satisfies "a typed error reaches the caller" with **zero routing**. Mitigation: every subtask
   asserts a `load_meta_fail_closed` frame in the traceback **and** that the module contains no local
   `raise MissionMetaReadError`.
5. **Breaking 0-net with a convenience helper.** A shared `_read_meta(dir)` wrapper looks tidy and either
   adds a routed call (helper + call site) or removes one (fold). It also risks authoring a second
   predicate answering "is this `meta.json` readable", which `NFR-002`'s kept clause forbids. Mitigation:
   1:1 swaps only; routed census printed after every subtask.
6. **Import surgery at `gate.py`.** Two sites share one `load_meta` import. Removing it in T009 breaks
   `:80`; forgetting it in T010 leaves an F401. Mitigation: T009 adds `load_meta_fail_closed` and keeps
   `load_meta`; T010 removes `load_meta`. `ruff check` is the gate.
7. **Re-forming the `core.paths ↔ mission_metadata` cycle.** `load_meta_fail_closed` holds a load-bearing
   *deferred* import of `mission_metadata`. Mitigation: check each new import site individually for
   module-level vs deferred (`_read_path_resolver.py` already imports `core.paths` at module level;
   `planner.py` already imports `core.constants`), import each edited module in a fresh interpreter, and do
   **not** tidy the deferred import inside `load_meta_fail_closed`.
8. **`MissionSelectorAmbiguous` is a plain `Exception`, not a `ValueError`.** It is raised inside
   `read_primary_meta`'s canonicalization path. `except Exception` anywhere near these sites would swallow
   it. Mitigation: this WP adds **no** `except` clause at all; T011 asserts the ambiguous-handle refusal
   still propagates.
9. **Straying out of surface.** `src/mission_runtime/resolution.py` (WP04) and `tests/missions/**` (shared
   with WP03) are the two temptations. Mitigation: T012 asserts an empty `git diff --stat` under
   `src/mission_runtime/`, and all WP02 tests in `tests/missions/` live in one clearly-named new file.
10. **ATDD-first vs. `plan.md`'s IC-02 commit slicing.** IC-02 says "one commit per ledger row … +
    its test"; the charter's §ATDD-First requires the failing test as its own earlier commit. Coupling D2
    binds only routing↔ledger-deletion, so both can be satisfied: test commit, then routing+ledger commit.
    Recorded here so the reviewer does not read the extra commit as a coupling violation.

## Reviewer Guidance

- **Check atomicity first, per ledger row.** For each of the five, run `git show --stat <green-sha>` and
  confirm the source file and `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` are in the
  **same** commit. A split is an automatic rejection — it means the tree was red in one direction at an
  intermediate commit.
- **Check the count, both directions.** `routed-pre.txt` and `routed-post.txt` must both read `129`. `130`
  means the implementer spent WP05's headroom. `128` means something folded — reject even though `128` is
  inside `[127, 130]`, because the mission's `+1` then lands on a wrong base and a second fold reaches the
  RED `126`.
- **Check the seam proof, not the exception type.** For each site, confirm the test asserts a
  `load_meta_fail_closed` frame in the traceback and `__cause__` preservation, and that the module has no
  local `raise MissionMetaReadError`. A test that only asserts
  `pytest.raises(MissionMetaReadError)` is the `SC-001` cheat and does not close `FR-001`.
- **Check for the fold explicitly at every routed row, not only T011.** Each of `T007`–`T011` must carry an
  executable call-count assertion over the routed function's own body: exactly `1, 1, 1, 1, 2`
  `load_meta_fail_closed(` calls and **zero** `load_meta(` calls, matched on the exact callee name. Read the
  assertions, not just their greens. A subtask whose structural proof is a substring check or a printed
  pre/post pair is a rejection: a fold reads **128**, which satisfies all three clauses of
  `test_routed_load_meta_floor` at `126/4`, and reads **129** — also green — once WP06 sets the floor to 127.
  The printed numbers stay, but they are not what closes the budget.
- **Check the untouched surfaces.** `git diff --stat` must print nothing for
  `tests/status/test_aggregate_coord_deleted_contract.py` and nothing under `src/mission_runtime/`. If the
  status test was edited, rows 10/11's behaviour changed and the WP must be rejected, not amended.
- **Check the arithmetic language.** Any report, commit message or comment that says "5 sites" or "6 rows"
  unqualified is a defect: the conventions differ and mixing them silently in one document is what this
  mission was rewritten to stop. The correct phrasing is **5 ledger rows / 6 call sites**.
- **Check the ledger deltas.** `pending-batch-a` count `13 → 8`, exactly five deleted lines, no other
  change to that file, and WP03's/WP04's rows byte-identical.
- **Check the quality gates as criteria.** `ruff check` clean (never `ruff format`), `mypy --strict` clean,
  and a `C901` pre/post pair quoted **per file** for all four owned source files.
- **Check red→green.** `git log --oneline <base>..HEAD` shows 10 commits, each red preceding its green, none
  squashed away, and each red's failure quoted from a redirected run (not a pipe).

---
work_package_id: WP03
title: Route the 3 allow_missing=False sites — routing + None arm + handler, one commit per site
dependencies:
- WP01
- WP02
requirement_refs:
- FR-003
- FR-004
- FR-013
- FR-014
- NFR-001
- C-001
- C-002
- C-008
planning_base_branch: feat/meta-fail-closed-3162
merge_target_branch: feat/meta-fail-closed-3162
branch_strategy: Planning artifacts for this mission were generated on feat/meta-fail-closed-3162. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/meta-fail-closed-3162 unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
- T019
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent:
- tests/specify_cli/context/test_wp03_row08_resolver_fail_closed.py
execution_mode: code_change
owned_files:
- src/specify_cli/context/resolver.py
- src/specify_cli/decisions/service.py
- src/specify_cli/missions/_resolve_planning_branch.py
- tests/specify_cli/test_meta_fail_closed_full_census_contract.py
- tests/specify_cli/context/test_wp03_row08_resolver_fail_closed.py
- tests/specify_cli/decisions/**
- tests/context/**
- tests/missions/**
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP03 – Route the 3 `allow_missing=False` sites

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Route census rows **8, 9 and 12** — the three `meta.json` reads that pass `allow_missing=False` — onto
`load_meta_fail_closed` (`src/specify_cli/core/paths.py:638`, symbol `load_meta_fail_closed`), **without
changing any site's arm** (`C-001`, D4=a).

`load_meta_fail_closed` returns `None` on absence; all three sites today receive `FileNotFoundError` instead.
So routing a site is **not** a drop-in swap: each routing arrives with an explicit `if result is None:` arm
carrying the **missing-file message**, the handler change (rows 9 and 12), the removal of the now-dead
`except FileNotFoundError`, and the deletion of that site's `pending-batch-a` ledger row — **all in one
commit**. Three sites, three commits.

## Where this WP runs, how to start it, and where its evidence lands

**This WP runs from the repository root.** Every path below is repo-relative from the tree you are in; do not
reconstruct a worktree path yourself.

**Start command:**

```bash
spec-kitty implement WP03
```

`spec-kitty agent action implement WP03 --agent <name>` does **not** resolve a workspace — its `--help` reads
*"Display work package prompt with implementation instructions."* `CLAUDE.md` § Execution Workspace Strategy
is explicit: *"`spec-kitty implement WP##` is the only supported way to prepare a workspace."*

**`PYTHONPATH=<workspace>/src` on every `python -c` and every `pytest` that could run outside the repository
root** — including the scratch working tree T017's mutation probes use. The split-tree hazard produces a
*silently wrong* answer, not an error:
`.venv/lib/python3.11/site-packages/_editable_impl_spec_kitty_cli.pth` pins `specify_cli` / `runtime` imports
to the **main** tree's `src/`, while `SRC_ROOT` in the gate
(`tests/architectural/test_inline_meta_read_gate.py:61`) and `_SRC_ROOT` in the ledger test
(`tests/specify_cli/test_meta_fail_closed_full_census_contract.py:54`) derive from **the test file's own
location**. Outside the install tree the AST census reads the *edited* `src/` while behavioural assertions
import the *unedited* one — the structural half of a proof goes green while its behavioural twin stays red,
with no diagnosable cause. That bites hardest at T017: an arm-deletion probe run in a scratch tree without
`PYTHONPATH` exercises the **committed** arm and reports the probe as green, i.e. the exact opposite of what
`SC-004` needs. Nothing provisions `.venv` into a git worktree (`.gitignore:31-32`), so `.venv/bin/python`
only resolves at the root.

**Committed evidence destination.** `spec-kitty agent tasks mark-status` exposes only `--status`,
`--mission`, `--auto-commit` and `--json`; its payload is `WPInnerStateDelta.subtasks: Mapping[str, Status]`
(`src/specify_cli/status/models.py:481`) — a bare `{T0xx: Status}`. **The record carries no evidence field.**
This WP's committed evidence destination is
`kitty-specs/meta-fail-closed-3162-01KZ7FSQ/evidence/WP03-evidence.md`, written as a declared **out-of-map**
planning write with a one-line rationale (`kitty-specs/` paths cannot appear in `owned_files` by construction
— `mission_parsing.py:153-157`, `:207-215`). Every `git show` quote, every grep with its input count, the
three quoted failing message assertions, the six `C901` numbers and the pre/post routed pair go **into that
file**. Redirect targets are scratch; nothing load-bearing is left in `/tmp`.

## Context

### Why this work package exists in this shape

`analysis-report.md` § **BLOCKER-2** rejected the previous slicing, which routed all three sites in one work
package and added their `None` arms in the next — shipping a **fail-open** in the committed interval, in a
guard whose own comment forbids it.

**Row 8 is the sharp one.** `src/specify_cli/context/resolver.py:68-78`, symbol `_read_meta_json`, carries
this comment directly above the call:

> `# FR-005 / post-#2091: this site hard-fails on a missing meta.json (MissingIdentityError) and propagates a malformed-JSON failure rather than silently tolerating it -- allow_missing=True or on_malformed="empty" would MASK that guard and silently re-introduce the removed legacy tolerance. allow_missing=False never returns None, so or {} only narrows the type for mypy (mirrors mission_metadata.load_meta_strict).`

Route the call at `:75` and `or {}` stops being a mypy no-op and becomes **live control flow**: absent
`meta.json` → `{}` → `mission_id = data.get("mission_id") or feature_dir.name` (`:80`) → **a fabricated
identity**, silently, with `MissingIdentityError` **never raised**. That is exactly the tolerance the comment
forbids, re-introduced by the mission whose purpose is fail-closed reads — and a direct `NFR-001` violation
("zero malformed reads yield a value indistinguishable from a valid one").

**Rows 9 and 12 are the same shape with milder symptoms.** Their pre-existing arms raise the **same
exception types** with the **wrong cause**:

- `src/specify_cli/decisions/service.py:134` (symbol `_resolve_mission_id`): the surviving path reports
  "has no mission_id field" instead of "meta.json not found for mission …".
- `src/specify_cli/missions/_resolve_planning_branch.py:116` (symbol `load_mission_target_branch`): the
  existing `if data is None:` arm at `:127-131` says "is not a JSON object" and is commented
  `# Unreachable`, **losing the `--target-branch <ref>` remediation** that the `FileNotFoundError` arm at
  `:117-121` carries.

### Couplings this work package must honour

From `plan.md` § **Atomicity couplings — all five**:

- **Coupling 2** — each routing + its ledger-row deletion are ONE commit. The ledger
  (`tests/specify_cli/test_meta_fail_closed_full_census_contract.py`, symbol `_ACCOUNTED_SITES`) is checked
  for **exact equality in both directions**: `test_no_unaccounted_load_meta_call_sites` and the staleness arm
  fail simultaneously, so a split commit is red whichever way it is ordered.
- **Coupling 3** — each `allow_missing=False` site's routing + its `None` arm are ONE commit. BLOCKER-2.
- **Coupling 4** — each refuse-typed site's routing + its `except` widening are ONE commit (`C-002`).
  `MissionMetaReadError` is a **`RuntimeError`**, not a `ValueError`, so the moment the call is routed the
  existing `except ValueError` **stops catching it** and the wrapper leaks where `DecisionError` /
  `PlanningBranchResolutionFailed` is contracted (`SC-003`).

Coupling 5 (routing and handler as two commits) is `FR-002`'s device for the **4 degrade sites** and belongs
to WP04. **It does not apply here.** Do not stage this work package's edits.

### Commit shape — this WP is three commits, and unlike WP02 there is no separate red commit

**Each site's guard test rides in the *same* commit as its site.** Unlike WP02 — which lands **ten** commits,
a red ATDD commit then a routing+ledger commit per ledger row — this work package has **no separate red
commit**, because **no base-red is possible**: the absent-file behaviour is already correct at baseline
(`test_resolver.py:256` is green today) and every intermediate red lives in the **working tree** and is never
committed. Coupling 3 forbids committing routing without its `None` arm, which is what a red-first commit
here would be.

Read this before you start, because an implementer arriving with WP02's habit lands **six** commits and is
rejected on a **count** rather than on a contract: this WP's Reviewer Guidance opens by rejecting any number
other than three. Three commits, one per site, each carrying routing + `None` arm + (rows 9, 12) handler
change + dead-`FileNotFoundError` removal + ledger-row deletion. The `C-008` exception for the missing base-red
is declared in the Risks section, not by inventing a red.

### The budget is closed by assertion, not by narration — one call-count assertion per routed site

**Each of `T014`, `T015` and `T016` must carry a per-site structural call-count assertion**, in the shape WP02
T011 uses for `read_primary_meta`: `ast`-parse the module and assert that the routed function's **own body**
contains **exactly one** `load_meta_fail_closed(` call and **zero** `load_meta(` calls — matched on the exact
callee name, not as a substring (`load_meta_fail_closed(` contains `load_meta(`). Three sites, three
assertions, expected count `1` at each.

Why an assertion and not the printed pre/post pair (the prints stay; they are not what closes the budget): a
fold that collapses two routed calls into one reads **128**, and `128 >= 126`, `128 > 126`,
`128 - 126 = 2 <= 4` — **all three clauses of `test_routed_load_meta_floor` are green**. After WP06 re-derives
the floor to 127 the merged tree's folded **129** is green too. So a fold survives both gates and is otherwise
caught only by a printed number a human has to compare. Lanes B and C are concurrent and file-disjoint, so no
file-overlap check can see the coupling. Twelve executable assertions across WP02/WP03/WP04 are the
instrument.

### `SC-004` closed a cheat — do not reintroduce it

A guard that asserts only the **exception type** is green at baseline, green after the change, **and still
green under arm-deletion** at rows 9 and 12, because the pre-existing arms raise the same types. Every guard
here therefore asserts the **message**: the missing-file text, and for `load_mission_target_branch` the
`--target-branch` remediation string. `SC-004` requires a **mutation probe per site**: delete the
`if result is None:` arm, quote the failing assertion (it must be the message assertion), restore.

### `FR-013` — the dead handlers, and the `except Exception` ban

`load_meta_fail_closed` hard-codes `allow_missing=True` (`src/specify_cli/core/paths.py:676`), so it **never**
raises `FileNotFoundError`. After routing, `except FileNotFoundError` at `resolver.py:76`, `service.py:135`
and `_resolve_planning_branch.py:117` is **unreachable and effect-free**. Remove each in the same commit as
its site. Both the charter's Code Review Checklist and `CLAUDE.md` reject effect-free handlers — remove it and
let the exception propagate, or add concrete recovery logic. The refusal each arm carried moves into the
`if result is None:` arm, so removal loses no behaviour (`SC-015`).

`C-002`'s never-`except Exception` rule applies to **all six** handlers in the mission, not only the two owned
here. Widen to `except (ValueError, MissionMetaReadError)` — or catch `MissionMetaReadError` by name in its own
clause — and nothing broader. `MissionSelectorAmbiguous` is confirmed **not** a `ValueError`
(`src/specify_cli/missions/_read_path_resolver.py:44`, plain `Exception`); a broad handler swallows it.

### Budget — 0-net, two-sided band

This work package is **0-net** on the routed count: 3 swaps, and both `load_meta` and `load_meta_fail_closed`
are in `ROUTED_CALLEES` (`tests/architectural/test_inline_meta_read_gate.py:105`). **WP05 is the mission's only
allocator** of the single net routed call.

- Live routed count: **129**. `ROUTED_LOAD_META_FLOOR = 126` (`:221`), `..._MARGIN = 4` (`:220`).
- `test_routed_load_meta_floor` (`:1084`) asserts **three** things — `len >= FLOOR`, `len > FLOOR`
  (explicitly anti-vacuous), `len - FLOOR <= MARGIN` — so the admissible band is **`[127, 130]`**.
- **The band is two-sided. `126` is RED.** A pass that folds two calls into one reds the floor **downward**,
  and a lane's own gate run cannot see the merged tree. Print the count **pre and post**; a delta of anything
  other than **0** stops the work package.

### Cone, ownership and discipline

- **Cone**: `tests/specify_cli/context`, `tests/specify_cli/decisions`, `tests/context`, `tests/missions`,
  plus the ledger test `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` and the run-only
  `tests/integration/test_coord_loop_workspace.py`. **Never `tests/sync` or `tests/cli`** — `C-007`'s window
  is held by a sibling mission and this work package never needs it.
- `tests/integration/test_coord_loop_workspace.py` is **not** in `owned_files` and must still be **run**. That
  omission from the previous cone is why the concern's own verification would not have caught the fail-open.
- `tests/missions/**` is shared with WP02 — legal **only** because `WP02 → WP03` is a declared dependency chain
  (`src/specify_cli/ownership/validation.py`; no-overlap is relaxed along a directed path). Do not touch WP02's
  files there; add new modules.
- **`tests/specify_cli/context/` is owned at FILE level, not as a glob.** This WP owns exactly
  `tests/specify_cli/context/test_wp03_row08_resolver_fail_closed.py`. The earlier
  `tests/specify_cli/context/**` glob claimed `tests/specify_cli/context/test_resolver.py`, which this WP itself
  declares **run-only** and must leave byte-identical — its `:256` message pin is row 8's only real assertion, and
  a WP cannot both own a file and promise not to touch it. Row 8's new malformed-file guard goes in the named
  module above, not into `test_resolver.py`.
- **Ledger rows: match by content, never by line number.** As of now the three rows read at `:215`
  (`context/resolver.py`, `_read_meta_json`), `:222` (`decisions/service.py`, `_resolve_mission_id`) and
  `:244` (`missions/_resolve_planning_branch.py`, `load_mission_target_branch`) — but **five commits mutate
  this file in sequence** across WP02/WP03/WP04, so every line number in it is stale the moment a neighbour
  lands. Grep the `(path, symbol)` tuple.
- **Cite `file:line` *and* symbol** in every piece of evidence (`C-003`). Lines shift; symbols do not.
- **Test evidence**: redirect each suite to a file, quote the `N passed` line verbatim, print the selected
  test count, `-ra` never `-rf`, and count `^ERROR tests/` — not bare `^ERROR `.
- **`ruff check` only** — never `ruff format`. Plus `mypy --strict`. No `# noqa`, `# type: ignore`, or
  per-file ignore added to reach green (`SC-017`).

### Measuring the routed count

Use **WP01's recorded command and its input file count** verbatim (`contracts/routing-manifest.md`). The
known-working form, if you need to confirm you are invoking the same scanner:

```bash
.venv/bin/python -c "
import sys, pathlib
sys.path.insert(0, 'tests/architectural')
import test_inline_meta_read_gate as m
print('routed:', len(m.scan_routed_load_meta_calls(pathlib.Path('src'))))
print('input files:', len(list(pathlib.Path('src').rglob('*.py'))))
"
```

`ROUTED_CALLEES` matches callee **names** over all of `src/`, not the call graph — it counts
`doc_analysis/doc_state.py`'s *locally defined* `_require_meta`. An unrelated commit anywhere that adds a call
named `load_meta*` moves the number, so record the command **and** the input file count with every print; the
gate's own header records three prior false reds from exactly this miscount.

### Subtask T013 — Pre-measure the routed count

**Purpose**: establish this work package's 0-net baseline before any edit, so the post-print in T019 is a
comparison and not an assertion.

**Steps**

1. Confirm WP01 and WP02 are landed and that `contracts/routing-manifest.md` and
   `contracts/headroom-allocation.md` exist. WP01 anchors the count, the band and the ledger convention; WP02
   is the dependency that makes the shared `tests/missions/**` glob legal.
2. Run WP01's recorded routed-count command in this worktree. Print the count **and** the input file count.
   Expected: **129** routed.
3. Quote the three assertions of `test_routed_load_meta_floor`
   (`tests/architectural/test_inline_meta_read_gate.py:1084`) verbatim from the source, and restate the derived
   band `[127, 130]` with **126 is RED** written out.
4. Record the three ledger rows by `(path, symbol)` tuple — not by line — with their current line numbers as
   an at-this-moment observation only.
5. Run the cone green **before** editing anything, redirected, and quote each `N passed` line. This is the
   baseline that distinguishes a failure this work package caused from a pre-existing one (charter
   § Pre-existing Failure Reporting Rule).

**Files**: none edited. Reads `contracts/routing-manifest.md`,
`tests/architectural/test_inline_meta_read_gate.py`, and the ledger test.

**Validation**: routed count printed as **129** with its command and input file count; the three floor
assertions quoted; the pre-edit cone run quoted with `N passed` per suite; `grep -c "except FileNotFoundError"`
over the three source files printed as **3** (this is `SC-015`'s red — it must be captured *before* T014).

### Subtask T014 — Census row 8: `context/resolver.py` `_read_meta_json` — ONE commit

**Purpose**: close the fail-open. This is the commit BLOCKER-2 exists to force.

**Steps**

1. Write the guard first. `tests/specify_cli/context/test_resolver.py:256` already pins
   `pytest.raises(MissingIdentityError, match="meta.json not found")` inside
   `test_missing_meta_json_raises` (**`:251`** — verified by opening the file; an earlier draft said `:250`)
   — it is **green at baseline** and stays green. Capture it green
   now; that is the `C-008` declaration for this site (a base-red is impossible — the absent-file behaviour
   is already correct). Add a malformed-file guard asserting `MissionMetaReadError` through the site's own
   public entry point (`resolve_context`), not by patching `load_meta_fail_closed`. **The guard rides in this
   subtask's single commit** — there is no separate red commit in this WP (see § Commit shape).
2. In **one** commit:
   - Replace the `load_meta(feature_dir, allow_missing=False, on_malformed="raise") or {}` call at
     `resolver.py:75` with `load_meta_fail_closed(feature_dir)`.
   - **Add `if result is None:` raising `MissingIdentityError` with the message
     `f"meta.json not found at {feature_dir / 'meta.json'}."`** — the exact text `test_resolver.py:256`
     matches on. This arm is the whole point of the commit.
   - **Delete** the now-dead `except FileNotFoundError` arm at `:76-78` (`FR-013`).
   - Reconcile the `or {}`: with the `None` arm present it is dead. Remove it — do not leave both, and never
     leave `or {}` as the absence path.
   - **Rewrite the guard comment at `:68-73`.** It currently asserts "`allow_missing=False` never returns
     `None`, so `or {}` only narrows the type for mypy", which is false after routing. The replacement states
     that the site is routed onto `load_meta_fail_closed`, that `None` means absent, and that the
     `if result is None:` arm is the `MissingIdentityError` guard. Leaving the old text makes the file document
     a contract it no longer has.
   - **Delete the ledger row** `("src/specify_cli/context/resolver.py", "_read_meta_json")` from
     `_ACCOUNTED_SITES` (coupling 2). Match by tuple.
3. Do not touch `mission_id = data.get("mission_id") or feature_dir.name` at `:80` — that legacy fallback is
   **field-absent** and in-contract (`C-001`); the defect is reaching it with a `{}` from an **absent file**.
4. **Add the call-count assertion** (see § The budget is closed by assertion): `ast`-parse
   `src/specify_cli/context/resolver.py` and assert `_read_meta_json`'s **own body** contains **exactly one**
   `load_meta_fail_closed(` call and **zero** `load_meta(` calls, matched on the exact callee name. It rides in
   this same commit. A substring check on the source text is green under a fold and does not close the budget.

**Files**: `src/specify_cli/context/resolver.py`, the ledger test, and the new
`tests/specify_cli/context/test_wp03_row08_resolver_fail_closed.py` (this WP's only owned file under
`tests/specify_cli/context/` — `test_resolver.py` is run-only and stays byte-identical).

**Validation**: `git show <sha> --stat` shows the source file **and** the ledger file in one commit;
`tests/specify_cli/context/` green, redirected, `N passed` quoted; `test_resolver.py`'s `:256` assertion text
unchanged; `grep -n "except FileNotFoundError" src/specify_cli/context/resolver.py` → 0 matches; the
call-count assertion exists and asserts **1** and **0**.

### Subtask T015 — Census row 9: `decisions/service.py` `_resolve_mission_id` — ONE commit

**Purpose**: keep `DecisionError` as the contracted refusal while the underlying exception type changes, and
give the absent-file case its own cause.

**Steps**

1. Write both guards first. (a) absent `meta.json` → `DecisionError` whose **message names the missing file**
   (`meta.json not found for mission …`) — asserted on the **message**, because `DecisionError` is what the
   field-absent path raises too. (b) malformed `meta.json` → `DecisionError` (still, not
   `MissionMetaReadError`), through the public entry point. Capture (a) green at baseline; (b) is red on the
   uncommitted intermediate tree and green at the commit.
2. In **one** commit:
   - Route `service.py:134` onto `load_meta_fail_closed(feature_dir)`.
   - **Add the `if result is None:` arm** raising `DecisionError(code=DecisionErrorCode.MISSION_NOT_FOUND,
     details={"mission_slug": mission_slug}, message=f"meta.json not found for mission {mission_slug!r}")` —
     carrying the **missing-file** cause. Without it the surviving path reports "has no mission_id field",
     which is the wrong cause and is **green under a type-only assertion**.
   - **Widen the handler at `:141`** from `except ValueError as exc:` to
     `except (ValueError, MissionMetaReadError) as exc:` (or a second named clause).
     `MissionMetaReadError` is a `RuntimeError`; unwidened, the wrapper leaks and `SC-003` fails while
     `SC-001` passes. **Never `except Exception`.**
   - Keep the handler's comment truthful: it currently explains that `load_meta(on_malformed="raise")` wraps
     JSON-syntax and read/decode failures into `ValueError`. After routing the seam wraps them into
     `MissionMetaReadError`. Update the text.
   - **Delete** the dead `except FileNotFoundError` arm at `:135-140`.
   - **Delete the ledger row** `("src/specify_cli/decisions/service.py", "_resolve_mission_id")`.
3. Import `MissionMetaReadError` and `load_meta_fail_closed` from `specify_cli.core.paths`; check whether this
   module imports `core.paths` at module level or deferred and match the existing shape. **Do not "tidy" any
   deferred import** — `core/paths.py`'s in-function `mission_metadata` import (`:670`) is load-bearing against
   a circular import.
4. **Add the call-count assertion** (see § The budget is closed by assertion): `ast`-parse
   `src/specify_cli/decisions/service.py` and assert `_resolve_mission_id`'s **own body** contains **exactly
   one** `load_meta_fail_closed(` call and **zero** `load_meta(` calls, matched on the exact callee name. Scope
   it to the function, and name the module in the assertion's own message: `_resolve_mission_id` is defined in
   four modules on this tree, two of them this mission's own sites with **opposite arms**. It rides in this
   same commit.

**Files**: `src/specify_cli/decisions/service.py`, the ledger test, new tests under
`tests/specify_cli/decisions/**`.

**Validation**: `git show <sha> -- src/specify_cli/decisions/service.py` shows the routing hunk, the `None`
arm and the handler widening **in one commit** (`SC-016`); the two guards green; `grep -n "except Exception"`
over the file → 0; `grep -n "except FileNotFoundError"` over the file → 0; the call-count assertion exists and
asserts **1** and **0**.

### Subtask T016 — Census row 12: `_resolve_planning_branch.py` `load_mission_target_branch` — ONE commit

**Purpose**: keep `PlanningBranchResolutionFailed` as the refusal **and** restore the `--target-branch`
remediation that the `FileNotFoundError` arm carries and the "Unreachable" `None` arm does not.

**Steps**

1. Write both guards first. (a) absent `meta.json` → `PlanningBranchResolutionFailed` whose message contains
   **both** `meta.json not found at <path>` **and** `Re-run with --target-branch <ref> to override.` The
   remediation half is the assertion that the pre-existing `:127-131` arm ("is not a JSON object") cannot
   satisfy — assert it explicitly. (b) malformed `meta.json` → `PlanningBranchResolutionFailed` with the
   "unreadable" message, still carrying the remediation.
2. In **one** commit:
   - Route `_resolve_planning_branch.py:116` onto `load_meta_fail_closed(feature_dir)`.
   - **Rewrite the existing `if data is None:` arm at `:127-131`.** It is currently dead-by-comment
     (`# Unreachable: allow_missing=False + on_malformed="raise" never returns None`) and its message is the
     wrong cause. After routing it is the **live absent-file arm**: it must carry
     `f"meta.json not found at {meta_path}. Re-run with --target-branch <ref> to override."` and the
     `# Unreachable` comment must go. This is the one site where the arm already exists — the edit re-purposes
     it rather than adding it, and T017's probe deletes it.
   - **Widen the handler at `:122`** to catch `MissionMetaReadError` by name alongside `ValueError`. Never
     `except Exception`.
   - **Delete** the dead `except FileNotFoundError` arm at `:117-121`, whose remediation text has moved into
     the `None` arm.
   - **Delete the ledger row**
     `("src/specify_cli/missions/_resolve_planning_branch.py", "load_mission_target_branch")`.
   - Amend the docstring: "tolerant of missing/corrupt files" still holds, but name `load_meta_fail_closed` as
     the seam and `None` as the absent signal.
3. Leave `resolve_planning_branch_from_meta(data)` untouched — the mapping path is unchanged (`C-001`).
4. **Add the call-count assertion** (see § The budget is closed by assertion): `ast`-parse
   `src/specify_cli/missions/_resolve_planning_branch.py` and assert `load_mission_target_branch`'s **own
   body** contains **exactly one** `load_meta_fail_closed(` call and **zero** `load_meta(` calls, matched on
   the exact callee name. It rides in this same commit.

**Files**: `src/specify_cli/missions/_resolve_planning_branch.py`, the ledger test, new tests under
`tests/missions/**` (WP02-shared — add your own module, do not edit WP02's).

**Validation**: `git show <sha>` shows routing + re-purposed `None` arm + handler change + dead-arm removal
+ ledger deletion in one commit; both guards green with the `--target-branch` substring asserted; the
call-count assertion exists and asserts **1** and **0**;
`grep -n "Unreachable" src/specify_cli/missions/_resolve_planning_branch.py` → 0 matches for this function.

### Subtask T017 — `SC-004` mutation probe, 3 of 3

**Purpose**: prove each `None` arm is **load-bearing**, not decorative. This is the subtask that makes
`SC-004` unfakeable.

**Steps**

1. For each of the three commits, in a scratch working tree: re-apply the commit with **only** the
   `if result is None:` arm removed. Change nothing else — the handler stays widened, the ledger row stays
   deleted, the dead `FileNotFoundError` arm stays gone.
2. Run the site's own guard and **quote the failing assertion**. The quoted failure must be the **message**
   assertion, not a type assertion:
   - Row 8: must fail at `tests/specify_cli/context/test_resolver.py:256` on `match="meta.json not found"`.
   - Row 9: must fail on the missing-file message, and must **not** be satisfiable by the "has no mission_id
     field" text.
   - Row 12: must fail on the `--target-branch` remediation substring.
3. Restore the arm; verify the tree is byte-identical to the committed state (`git status --porcelain` empty).
4. Demonstrate once that a **type-only** form of the same guard is green under arm-deletion at rows 9 and 12
   (assert only the exception type, show it passing with the arm removed). That demonstration is the reason
   `SC-004` reads "the assertion is on the MESSAGE"; without it the criterion's justification is unevidenced.

**Files**: none committed. Scratch tree only; the probe output is evidence, not an artifact.

**Validation**: three quoted failing assertions, each naming a message; one quoted type-only guard passing
under arm-deletion; `git status --porcelain` empty after each restore.

### Subtask T018 — `SC-003` negative controls and the two run-only pins

**Purpose**: prove the change did not turn a **valid** read into a failure, and run the pins that live
outside this work package's `owned_files`.

**Steps**

1. **Negative controls**: for rows 9 and 12, a **valid** `meta.json` returns cleanly through the public entry
   point — no exception, correct value (`SC-003`). A fail-closed pass that fails closed on valid input is not a
   pass. Add the equivalent for row 8.
2. Assert that each of the two handlers owned here catches `MissionMetaReadError` **by name** and that neither
   is `except Exception`. `SC-007`'s third assertion covers all six mission-wide; supply these two and do not
   weaken the other four.
3. **Run, never edit**: `tests/specify_cli/context/test_resolver.py` (the `:256` pin) and
   `tests/integration/test_coord_loop_workspace.py`. Prove non-edit with `git diff --stat
   <planning_base_branch> -- <path>` printing nothing, quoted.
4. **Read this before quoting the integration file as a pin.** `spec.md` `FR-004`, `plan.md` IC-03 and
   `analysis-report.md` BLOCKER-2 all cite `tests/integration/test_coord_loop_workspace.py:611,627` as a test
   that "pins row 8's arm" / "a meta-less husk must raise `MissingIdentityError`". **Verified: both lines are
   docstring prose** inside `TestResolveContextReadsFromPrimary` — `grep -n MissingIdentityError` over that
   file returns **exactly those two lines and no assertion**, and the test asserts `resolve_context`
   **succeeds** against the PRIMARY dir. It will **not** fail under row 8's arm-deletion. Run it — it is a
   real consumer of `_read_meta_json` — but **do not** cite it as a second failing assertion in T017, and
   record the correction. Row 8's message pin is `test_resolver.py:256`, alone.
5. Run the full declared cone for this work package: `tests/specify_cli/context`,
   `tests/specify_cli/decisions`, `tests/context`, `tests/missions`,
   `tests/specify_cli/test_meta_fail_closed_full_census_contract.py`,
   `tests/integration/test_coord_loop_workspace.py`. Redirect each, quote `N passed`, print the selected
   count, `-ra`, and count `^ERROR tests/`.

**Files**: new tests in `tests/specify_cli/context/test_wp03_row08_resolver_fail_closed.py` and under
`tests/specify_cli/decisions/**`, `tests/context/**`, `tests/missions/**`. **No edits** to the two run-only
files, and none to `tests/specify_cli/context/test_resolver.py`, which is not in `owned_files`.

**Validation**: negative controls green; `git diff --stat` empty for the integration file; every cone suite's
`N passed` quoted with its selected count; the docstring-vs-assertion correction recorded.

### Subtask T019 — Post evidence

**Purpose**: discharge `SC-011`, `SC-015`, `SC-016`, `SC-017` and the complexity register with measurements,
not narration.

**Steps**

1. **Routed count POST**, same command and input file count as T013. Print both numbers side by side:
   pre **129**, post **129**, **delta 0**. State the band `[127, 130]` and that **126 is RED**. A non-zero
   delta stops the work package — do not "explain" it.
2. **`SC-015`**: `grep -n "except FileNotFoundError"` over the three source files → **0 matches**, quoted with
   the input file count, against the **3** captured in T013. Print the justification alongside:
   `load_meta_fail_closed` hard-codes `allow_missing=True` (`src/specify_cli/core/paths.py:676`), so the arm is
   unreachable, and the refusal it carried now lives in the `if result is None:` arm — with T017's message
   probes as the proof that no behaviour was lost.
3. **`SC-016`**: `git show <sha> -- <file>` per site, quoted, showing routing hunk + `None` arm + `except`
   change in **one** commit. Plus `git log --oneline` showing **three** commits, none squashed, none staged.
4. **Ledger**: quote the three deleted rows from the diffs by `(path, symbol)` tuple, and show
   `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` green — exact equality holding in both
   directions after all three deletions.
5. **`SC-017`**: `ruff check` and `mypy --strict` over the changed files, zero issues, quoted with the file
   list and count. No `# noqa`, `# type: ignore` or per-file ignore added.
6. **Complexity register**: `ruff check --select C901` **pre and post, per file**, for `_read_meta_json`,
   `_resolve_mission_id` and `load_mission_target_branch`. `plan.md`'s register lists all three as
   `[UNVERIFIED — measure]`; **measuring them is this work package's deliverable**. Ceiling is 15.
7. Append to the mission tracer files (tooling-friction, approach, design-decisions) — charter Standing
   Order 3.

**Files**: no source edits. Evidence only.

**Validation**: pre/post routed both **129** with delta 0; `SC-015` grep at 0 with the red at 3;
three `git show` quotes; `git log --oneline` showing three commits; ruff/mypy clean; six `C901` numbers
(three files × pre/post) recorded.

---

## Definition of Done

Each subtask is closed by writing its evidence into
`kitty-specs/meta-fail-closed-3162-01KZ7FSQ/evidence/WP03-evidence.md` and then marked, one call per subtask,
T013 through T019:

```bash
spec-kitty agent tasks mark-status T013 --status done --mission meta-fail-closed-3162-01KZ7FSQ  # ... T019
```

`mark-status` records **status only** — it exposes `--status`, `--mission`, `--auto-commit`, `--json` and its
payload is a bare `{T0xx: Status}` (`src/specify_cli/status/models.py:481`). It is **not** an evidence channel.
A subtask is **not** done until the evidence named in its own **Validation** line is captured and quoted **in
that committed file**. The work package is done when all seven are marked **and**:

- **Three commits, one per site** — not six. `git log --oneline` proves it. No staging, no squash, no split,
  and **no separate red commit**: unlike WP02's ten commits, each guard here rides with its site because no
  base-red is possible (§ Commit shape).
- **Three call-count assertions**, one per routed site: **exactly one** `load_meta_fail_closed(` call and
  **zero** `load_meta(` calls in `_read_meta_json`, `_resolve_mission_id` (in `decisions/service.py`) and
  `load_mission_target_branch`, matched on the exact callee name.
- Every `python -c` / `pytest` run outside the repository root carries `PYTHONPATH=<workspace>/src` — including
  T017's scratch-tree probes, where omitting it exercises the committed arm and reports the probe green.
- Every commit contains its site's routing **and** its `None` arm **and** (rows 9, 12) its handler change
  **and** its dead-`FileNotFoundError` removal **and** its ledger-row deletion.
- Routed count **129 → 129**, delta **0**, printed with the command and input file count both times.
- `SC-004`: three message-asserting mutation probes, each quoting a failing **message** assertion.
- `SC-003`: valid-file negative controls green at all three sites; both owned handlers catch
  `MissionMetaReadError` by name; neither is `except Exception`.
- `SC-015`: the three greps at **0**, the red at **3** captured before the removals. `SC-016`: per-site
  `git show` quotes. `SC-017`: `ruff check` and `mypy --strict` clean, no suppressions added.
- `tests/integration/test_coord_loop_workspace.py` and `test_resolver.py`'s `:256` assertion
  **byte-identical**, `git diff --stat` quoted empty.
- The whole declared cone green, redirected, `N passed` quoted per suite, selected counts printed.

## Risks

1. **The fail-open ships if any commit is split.** Routing row 8 without its `None` arm is a fabricated mission
   identity, silently, in whatever tree that commit exists in. Check every commit **before** committing:
   routing hunk and `None` arm in the same `git diff` output, or do not commit.
2. **A type-only guard passes the whole work package and proves nothing.** Rows 9 and 12 raise the same
   exception types before, after, and under arm-deletion. T017 is the check.
3. **Ledger line numbers are stale by design.** Deleting by line number deletes a neighbour's row and reds the
   equality gate in the *other* direction. Match the `(path, symbol)` tuple.
4. **Downward floor red.** Folding two calls into one takes the lane to 128 and the merged tree toward 126,
   which is RED. This work package swaps three calls for three calls — nothing else.
5. **`except Exception` looks like the easy widening and is banned at all six handlers.**
   `MissionSelectorAmbiguous` (`missions/_read_path_resolver.py:44`) is a plain `Exception`; a broad catch
   swallows an ambiguous-handle refusal.
6. **`or {}` is easy to leave in place.** At row 8 it is the fail-open mechanism itself. Removing the
   `FileNotFoundError` arm while leaving `or {}` as the absence path reproduces BLOCKER-2 exactly.
7. **The stale comment is part of the defect.** `resolver.py:68-73` asserts a contract routing invalidates.
8. **`tests/missions/**` is shared with WP02.** Editing WP02's modules there is out of scope even though the
   glob permits the path.
9. **No base-red exists for `SC-004`** — the absent-file behaviour is already correct at baseline, a declared
   `C-008`/`C-011` exception (`spec.md`'s red-first register, `FR-004` row). Do not manufacture a red by
   committing a broken intermediate; rows 9 and 12's intermediate red lives in the **working tree** and is
   **never committed**.

## Reviewer Guidance

Reject on any of these without reading further:

- **Fewer or more than three commits**, or any commit missing one of: routing, `None` arm, handler change
  (rows 9/12), dead-handler removal, ledger-row deletion. Verify with `git show <sha> --stat` and the full
  patch, per commit. This is `FR-014`/`SC-016` and it is why the work package exists. **Six commits is the
  expected wrong answer** — it is WP02's shape (red commit then implementation commit, per row) carried across.
  Before rejecting on the count, check whether the implementer read § Commit shape: if they landed six because
  they manufactured a base-red, that is also a `C-008`/`C-011` violation (no base-red is possible here), so
  say which of the two you are rejecting on.
- **A routing subtask with no call-count assertion**, or one whose structural proof is a substring check on
  the source text. A fold reads **128** — green under all three clauses at `126/4`, and green at **129** once
  WP06 sets the floor to 127 — so only the assertion catches it.
- **A guard that asserts only an exception type** at any of the three sites. Row 12's must name the
  `--target-branch` remediation; row 9's must name the missing-file cause, not "has no mission_id field".
- **A mutation probe whose quoted failure is a type assertion**, or one described rather than quoted.
- **`except Exception`** anywhere in the diff; also check the four handlers this work package does **not**
  own are untouched.
- **A `# noqa`, `# type: ignore` or per-file ignore** added to reach `SC-017` green.
- **An edited `tests/integration/test_coord_loop_workspace.py`** or a changed `:256` assertion text in
  `test_resolver.py`. `git diff --stat` must be empty for both.
- **A routed count printed once**, without its command and input file count, or with a non-zero delta
  "explained".
- **A ledger row deleted by line number** (a neighbouring row disappears, or the equality gate reds in the
  staleness direction).

Then verify the substance:

- Read `resolver.py`'s replacement comment: does it describe the routed contract, or is it the old text about
  `or {}` narrowing for mypy?
- Confirm `or {}` is gone from row 8's absence path and that
  `mission_id = data.get("mission_id") or feature_dir.name` at `:80` is **unchanged** — the field-absent
  fallback is in-contract (`C-001`); only the absent-*file* path was the defect.
- Confirm row 12's `if data is None:` arm no longer says "not a JSON object" nor carries `# Unreachable`.
- Confirm the six `C901` numbers exist. `plan.md`'s complexity register has three `[UNVERIFIED — measure]` rows
  for this work package's functions; a missing number is a missing deliverable, not a formatting lapse.
- Confirm the implementer recorded the `test_coord_loop_workspace.py:611,627` correction (docstrings, not
  assertions) rather than quietly citing them as a pin they cannot be.

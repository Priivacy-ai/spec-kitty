---
work_package_id: WP08
title: Terminal integration verification, the sweep handshake, and the DRAFT PR
dependencies:
- WP02
- WP03
- WP04
- WP05
- WP06
- WP07
requirement_refs:
- NFR-002
- C-003
- C-007
- C-008
planning_base_branch: feat/meta-fail-closed-3162
merge_target_branch: feat/meta-fail-closed-3162
branch_strategy: Planning artifacts for this mission were generated on feat/meta-fail-closed-3162. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/meta-fail-closed-3162 unless the human explicitly redirects the landing branch.
subtasks:
- T047
- T048
- T049
- T050
- T051
- T052
history: []
agent_profile: debugger-debbie
authoritative_surface: scripts/
create_intent:
- scripts/verify_meta_fail_closed_integration_3162.py
execution_mode: planning_artifact
owned_files:
- scripts/verify_meta_fail_closed_integration_3162.py
role: investigator
tags: []
tracker_refs: []
---

# WP08 — Terminal integration verification, the sweep handshake, and the DRAFT PR

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `debugger-debbie`
- **Role**: `investigator`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work
package's `task_type` and `authoritative_surface`.

---

## Ownership note — read this; the earlier version asserted a constraint that does not exist

**What is true.** `owned_files` may **not** contain paths under `kitty-specs/`: `_is_mission_specs_owned_file`
(`src/specify_cli/cli/commands/agent/mission_parsing.py:153-157`) classifies any such entry as a mission-specs
path and `_invalid_mission_specs_owned_files` (`:207-215`) turns it into a hard `finalize-tasks` error
(`_validate_owned_files_not_in_mission_specs`, `mission_finalize.py:918-937`). So
`contracts/integration-verification.md` is written as a declared **out-of-map** planning write with a one-line
rationale, which the tasks-packages contract permits.

**What was false and is struck.** The earlier note said that prohibition *"forced"* this WP to own a script.
It does not, and it is not the reason the script exists. Two corrections:

1. `execution_mode: planning_artifact` is the load-bearing declaration: it routes this WP to the **repository
   root** (`src/specify_cli/workspace/context.py:752` — *"planning_artifact -> repository root"* — and the
   branch at `:761`), which is the only tree with a `.venv`. Nothing provisions `.venv` into a git worktree
   (`.gitignore:31-32`; no venv references across `workspace/`, `lanes/`, `git/`). Every `.venv/bin/python`
   and the `pip install -e .` in T048 would be unrunnable in a lane worktree — so a `code_change` declaration
   would have made this WP's central obligation impossible.
2. The `scripts/` entry exists because **an ownership manifest requires a non-empty `owned_files`**, not
   because `kitty-specs/` is barred. Measured: `build_wp_manifests` builds a manifest only when
   `fm.execution_mode and fm.owned_files` are **both** truthy
   (`src/specify_cli/ownership/validation.py:355-357`), and `compute_lanes` then raises
   `LaneComputationError: Executable WP 'WP08' has no ownership manifest` for any WP in the dependency graph
   without one (`src/specify_cli/lanes/compute.py:326-336`); `validate_authoritative_surface`
   (`ownership/validation.py:223-253`) additionally requires `authoritative_surface` to prefix an `owned_files`
   entry. `owned_files: []` is honoured at the **inference** layer (`mission_parsing.py:161-187`,
   `mission_finalize.py:796-801`) but **refused at the lane layer**. `[UNVERIFIED — upstream gap]`: a
   `planning_artifact` WP whose only deliverable lives under `kitty-specs/` has no fully clean declaration
   today; `_PLANNING_PREFIXES` is `("kitty-specs/", "docs/")` (`ownership/validation.py:75`), so the `scripts/`
   entry earns a **non-fatal** consistency warning. File it upstream rather than working around it silently.

**Therefore the script is a real deliverable, not a placeholder.**
`scripts/verify_meta_fail_closed_integration_3162.py` **must be created** by this WP (T049 owns it; see its
Files/Validation lines and the DoD). It is the re-runnable form of the integration counts: routed and inline
with their input file counts, the floor and margin read off the merged tree, the derived band, and the
`pending-batch-a` row delta. Because every number here is *perishable* — the reasons are tabulated below — a
committed script that a reviewer can re-run on the merged tree is worth more than a prose snapshot of it.
An earlier draft named the script **only** in frontmatter while the DoD said the artifact was *"the only file
this WP wrote"*, so this WP could be marked done with its entire declared write surface empty; that
contradiction is resolved by making the surface load-bearing.

Note `scripts/` is **not** in CI's lint scope (`ruff check src tests`) and is exempted only from `TID251`, so
run `ruff check` on the script explicitly and keep every function at complexity <= 15.

## Objective

Produce **one** artifact — `contracts/integration-verification.md` — carrying the measured evidence that
this mission's claims still hold **on the merged tree**, not on the tree each work package happened to see.
Then perform the `C-007` sweep-window check, and open the cross-fork **DRAFT** PR.

This WP writes no code and edits no test. Every number in the artifact is re-derived here with its command
and its input count quoted; nothing is summed from per-lane reports. `SC-011`'s routed count, `SC-006`'s two
deltas, `SC-008`'s marker green, `SC-002`'s 12 captured lines, the ledger's row-count delta, `SC-009`'s
filing register and `SC-017`'s clean lint are each **perishable in a different way** — the reasons are
tabulated below, and each one is why per-concern lanes cannot close this evidence themselves.

## Where this WP runs, how to start it, and where its evidence lands

**This WP runs from the repository root.** `execution_mode: planning_artifact` routes the workspace there
(`src/specify_cli/workspace/context.py:752`, `:761`), which is the only tree with a `.venv`
(`.gitignore:31-32`) and therefore the only tree in which `pip install -e .` and `.venv/bin/python` mean what
this prompt says they mean.

**Start command:**

```bash
spec-kitty implement WP08
```

`spec-kitty agent action implement WP08 --agent <name>` does **not** prepare a workspace — its `--help` reads
*"Display work package prompt with implementation instructions."* `CLAUDE.md` § Execution Workspace Strategy
is explicit: *"`spec-kitty implement WP##` is the only supported way to prepare a workspace."*

**`PYTHONPATH` on anything that could run outside the root.** Every `python -c` and every `pytest` invocation
below that might be executed from somewhere other than the repository root — in particular the pristine-baseline
`git worktree` comparisons in T048/T050 — must carry `PYTHONPATH=<workspace>/src`, naming the tree whose
`src/` is being measured. The hazard is a *silently wrong* answer, not an error:
`.venv/lib/python3.11/site-packages/_editable_impl_spec_kitty_cli.pth` pins `specify_cli` / `runtime` imports
to the **main** tree's `src/`, while `SRC_ROOT` in the gate
(`tests/architectural/test_inline_meta_read_gate.py:61`) and `_SRC_ROOT` in the ledger test
(`tests/specify_cli/test_meta_fail_closed_full_census_contract.py:54`) are derived from **the test file's own
location**. Outside the tree `.venv` was installed from, the AST census reads the *edited* `src/` while every
behavioural assertion imports the *unedited* one — a structural assertion goes green while its behavioural
twin stays red, with no diagnosable cause. Record which tree each number came from.

**Committed evidence destination.** `spec-kitty agent tasks mark-status` exposes only `--status`,
`--mission`, `--auto-commit` and `--json`; its payload is `WPInnerStateDelta.subtasks: Mapping[str, Status]`
(`src/specify_cli/status/models.py:481`) — a bare `{T0xx: Status}`. **The record carries no evidence field.**
This WP's committed destination is
`kitty-specs/meta-fail-closed-3162-01KZ7FSQ/contracts/integration-verification.md` (an out-of-map planning
write, which is what `planning_artifact` is for), with
`scripts/verify_meta_fail_closed_integration_3162.py` as the committed, re-runnable form of the counts inside
it. Every capture, pass line, sample, register row and quotation named below goes **into that file**. Scratch
redirect targets under `<scratch>/` are working files whose contents are quoted in; nothing load-bearing is
left in `/tmp`.

## Context

### Why every proof in this WP is a re-capture

| Proof | Why the lane's capture perished |
|---|---|
| `SC-011` / `NFR-002` — routed count + re-derived floor | WP05 spends the mission's **single** net routed call (`129 → 130`, the exact ceiling of the admissible band `[127, 130]`); WP06 re-derives `ROUTED_LOAD_META_FLOOR`. Only the merged tree has **both**. `ROUTED_CALLEES` matches callee **names** and the census is global over `src/`, so an unrelated concurrent landing also moves the number |
| `SC-006` — inline count | Two independent causes (predicate widening, source change) move one number. The lane that widened cannot separate them on the merged tree |
| `SC-008` / `SC-010` — `#2804`'s marker | **Not transitive.** The marker imports `_run_lane_based_merge` (`tests/regression/test_issue_2804_merge_resets_gate_artifacts.py:84`), and `src/specify_cli/merge/executor.py:116` imports `resolve_placement_only`, which reaches `_resolve_mission_id` and `_resolve_coordination_branch` — **two of WP04's four degrade sites**. It also shells out to `merge_driver.py` **as a subprocess** (`src/specify_cli/lanes/merge.py:84`, `command="spec-kitty merge-driver-meta %O %A %B"`, `pattern="kitty-specs/**/meta.json"` at `:85`), which WP05 may edit. A subprocess edit is invisible until `pip install -e .` |
| `SC-002` — 4 degrade sites × 3 shapes = 12 lines | WP04 captured it against its own lane's `src/`. On the merged tree WP05's edits are also present |
| `SC-009` — filing register | Only ≥2 of the ≥5 mandated filings were pinned upstream; the rest are filed across five lanes and only close here |
| Ledger `pending-batch-a` rows | Three lanes (WP02, WP03, WP04) delete rows from **one** file, gated on exact equality in both directions. Only the merged tree has all deletions |
| `SC-017` — `ruff check` / `mypy --strict` | The union of touched files exists only after the merge |

### Order of operations — the reinstall comes first

`pip install -e .` (or the tree's `uv`-equivalent), **then** measure. A capture taken before the reinstall
is a **stale-install false red or a stale-install false green — both worthless**, and the artifact must
**say in writing that the reinstall preceded the capture**, with the install command and its exit line
quoted. This is a named recurring class in this programme, not a hypothetical.

### The cone, corrected — 14 directories, not the 5 originally declared

`tests/specify_cli`, `tests/mission_runtime`, `tests/regression`, `tests/merge`, `tests/architectural`,
plus the nine the import-line grep proved were under-declared: `tests/integration`, `tests/missions`,
`tests/runtime`, `tests/next`, `tests/context`, `tests/status`, `tests/upgrade`, `tests/coordination`,
`tests/lanes`. All 14 verified present on this tree.

`tests/specify_cli/cli/commands/` is **inside** `tests/specify_cli` and is **not** the barred top-level
`tests/cli` — the census conflated them. Note the mission's `SC-008` byte-identical file lives there:
`tests/specify_cli/cli/commands/test_row_aware_merge_driver.py`.

### `C-007` — the handshake is a check *before* sweeping, not a sweep

`tests/sync` and `tests/cli` must never run concurrently, and a **sibling mission may hold either window**.
This mission's 14-directory cone contains **neither**, so nothing here needs the window; the handshake
exists so a broad sweep does not take it by accident.

**A single `pgrep` sample taken in a gap between runs is not evidence that a sweep finished.** That mistake
has already been made in this programme and sent an implementer hunting a completion that had not happened.
Sample more than once, spaced, and record the samples with timestamps.

### Measurement discipline — this WP is nothing but measurement, so it binds hardest

- **Never pipe a suite whose exit status you need.** Redirect (`> f 2>&1`), then quote the `N passed` /
  `N failed` line verbatim from the file.
- **Print the input count for every derivation** — N in, M out, and why each of the N−M was dropped. A bare
  output number is not a measurement.
- **`-ra`, never `-rf`.** Count `^ERROR tests/`, never `^ERROR `.
- **Control every probe against a known answer and show the control.** Documented traps on this tree: naive
  `grep -c 'except ValueError'` gives **9** where the answer is **6**; a naive grep for routed calls gives
  **296** where the answer is **129**.
- **Report distributions, not scalars, for anything that varies between runs.** If two runs of one selection
  differ, the truth is the distribution and the tail matters.
- **A killed or timed-out run is neither pass nor fail.** Say exactly that in the artifact — **and then make
  it terminate.** See § The sweep is priced below; a rule that forbids reading a timeout as green without
  saying how to avoid one is a rule that produces an unfinishable subtask.

### The sweep is priced — budgets, `timeout`, and the documented parallel form

The 14-directory cone is **expensive**, and it was previously unpriced. Two measurements taken on this tree:

- `pytest --collect-only -q` on **one file** took **50.22 s**.
- **One node** of `tests/architectural/test_inline_meta_read_gate.py` took **58.20 s**.

`tests/specify_cli`, `tests/integration` and `tests/architectural` are among the fourteen. A serial pass over
all of them at that cost per file does not terminate inside any plausible session.

**Therefore:**

1. **Every directory run carries an explicit `timeout`.** Wrap each invocation:
   `timeout <BUDGET> .venv/bin/python -m pytest <dir> ...`. Record the budget used and the elapsed time next
   to each directory's pass line. `timeout` exits `124` on expiry — that is the machine-readable form of
   "neither pass nor fail".
   **`<BUDGET>` is `[UNVERIFIED]`: 1800 s per directory is an operational ceiling, not a measurement.** The
   two figures above are the only measured anchors; no full-directory wall-clock was measured. Print the
   budget you used and the elapsed time so the next run can replace this with a measured number.
2. **Use the documented parallel form.** `CLAUDE.md` § Local parallel test run and
   [`docs/development/testing-parallel.md`](../../../docs/development/testing-parallel.md) document
   `PWHEADLESS=1 pytest <dir> -n auto --dist loadfile -p no:cacheprovider` as the supported form, and
   **`--dist loadfile` is mandatory — never bare `--dist load`**, because `loadfile` keeps every test in a
   file on one worker and preserves file-scoped fixture and collection semantics. Per-worker HOME isolation
   means a parallel run never touches the real `~/.spec-kitty`. This is **permitted here**, not a shortcut:
   it is the repository's own documented way to finish a broad selection.
3. **Real-port / daemon suites run serially, `-n0`.** OS-global resources (real ports, singleton daemons) are
   not protected by per-worker HOME isolation. The only suite the docs name is
   `tests/sync/test_orphan_sweep.py` (ports 9400–9449) — **which is outside this mission's cone**. Before
   parallelising, apply the documented criterion to each of the fourteen yourself and **name** any directory
   you run `-n0`, with the resource it binds. See the note in § Things in the upstream planning artifacts:
   the 12-vs-2 split this instruction inherited does not reproduce on this tree.
4. **Parallel does not license substitution.** `-n auto --dist loadfile` changes *how* the declared cone runs,
   never *what* runs: still 14 directories, still `-ra`, still redirected, still `collected N items` and
   `^ERROR tests/` per directory, still no full-suite substitution and no `tests/sync` / `tests/cli`.
5. **Collection equivalence, if you parallelise.** Per `docs/development/testing-parallel.md`, a parallel run
   must collect the same node ids as a serial one. Where you parallelise, quote `collected N items` and state
   that the count matches the serial `--collect-only` figure for the same directory — otherwise a worker
   split, not the mission, is what moved the number.
- **A cited line number is not evidence that the line asserts anything.** This programme carried docstring
  prose as a "pinning assertion" through four artifacts. Open the file before citing it.
- **Beware the stale global binary.** `/home/jeroennouws/.local/bin/spec-kitty` resolves to an unrelated
  checkout and is first on `PATH` today (verified). Prepend the tree's own `.venv/bin` and quote
  `command -v spec-kitty` before trusting any CLI result.
- Cite every authority by **`file:line` and symbol** (`C-003`): `load_meta_fail_closed` at
  `src/specify_cli/core/paths.py:638`, `MissionMetaReadError` at `:506`.

### Discipline

If verification reveals a defect, **do not fix it here.** Record it, name the WP that owns the fix, and file
it. `ruff check` only — **never** `ruff format`.

### Subtask T047 — The `C-007` sweep-window check, sampled more than once

**Goal:** prove, before any broad selection runs, that no sibling mission holds the `tests/sync` or
`tests/cli` window, and record what was checked rather than asserting a conclusion.

1. Fix `PATH` first and quote the result — the global binary is stale:
   `export PATH=/home/jeroennouws/dev/sk-missions/3162/.venv/bin:$PATH; command -v spec-kitty`.
   If it still resolves under `~/.local/bin`, stop and say so; every later CLI result is void.
2. Sample the daemon/sweep indicators **at least three times, spaced ≥30s apart**, each with a timestamp:
   `date -Is; pgrep -af 'run_sync[_]daemon'; pgrep -af 'pytest tests/(sync|cli)'`. Record **all** samples
   including the empty ones. One empty sample proves nothing about a run that is between selections.
3. Check the sibling missions' worktrees for an in-flight sweep (`~/dev/sk-missions/3167` is the named
   sibling in `plan.md` IC-08). Quote what you inspected — process list, lock file, or mission events — and
   state explicitly which of those you could **not** inspect.
4. Record the negative-need argument with its evidence: the declared cone is the 14 directories above, and
   `tests/sync` / `tests/cli` are **not** among them, so this mission never needs the window. Print the
   14-item list and the two barred names side by side so the reader can check the disjointness.
5. Record the `tests/specify_cli/cli/commands/` vs `tests/cli` distinction and that `SC-008`'s
   byte-identical file is under the former.

**Evidence in the artifact:** the `command -v spec-kitty` line; ≥3 timestamped samples verbatim; the sibling
check with its gaps named; the disjointness list. **Do not** write "no sweep running" as a bare claim.

`spec-kitty agent tasks mark-status T047 --status done`

### Subtask T048 — Reinstall FIRST, then re-capture `SC-008`, `SC-010` and `SC-002`

**Goal:** re-capture the behaviour proofs on the merged tree in an order that cannot produce a stale-install
verdict, and say in the artifact that the order was honoured.

1. **Reinstall before anything else**: `pip install -e .` (or the tree's `uv` equivalent). Quote the command
   and its final line. State in the artifact: *"the reinstall preceded the capture."* Reason, in the
   artifact, in one sentence: `src/specify_cli/lanes/merge.py:84` registers
   `spec-kitty merge-driver-meta %O %A %B` for `pattern="kitty-specs/**/meta.json"` (`:85`), so
   `merge_driver.py` runs as a **subprocess** and WP05's edit is invisible to the marker until reinstall.
2. Re-run the marker, redirected, `-ra`:
   `.venv/bin/python -m pytest tests/regression/test_issue_2804_merge_resets_gate_artifacts.py -ra > <scratch>/wp08_2804.txt 2>&1`.
   Quote the `N passed` / `N failed` line verbatim and `grep -c '^ERROR tests/'` (not `^ERROR `).
3. Name both re-pinned assertions individually, at `file:line`, and **open** the file before citing: `:482`
   (`overall_verdict`) and `:489` (`SCAFFOLD_TODO_MARKER not in json.dumps(post_matrix)`) inside
   `test_merge_resets_filled_gate_artifacts_to_placeholder` (`:420`). A one-assertion account is what made
   `SC-008` look reachable by widening the verdict alone.
4. Re-run `SC-010`'s companion (`test_widened_2804_assertion_rejects_wrong_verdict`) in the same selection
   and quote its result. Confirm its fixture is the **defect's own shape** (take-theirs / scaffold-clobber
   with the accepted evidence handle absent), not merely a disallowed `fail`.
5. `SC-008`'s two diff obligations, quoted with **empty output shown as empty**:
   `git diff --stat <measurement baseline> -- src/` and
   `git diff --stat upstream/main -- tests/specify_cli/cli/commands/test_row_aware_merge_driver.py`.
   Use the corrected path (see the finding at the end of this file).
6. Re-capture `SC-002` on the merged tree: **positive control first** — deliberately break one handler, quote
   the non-empty `diff`, restore — then `diff pre.txt post.txt` empty with **12** captured lines each side,
   `wc -l` non-zero on both, and the **input count printed** (4 sites × 3 shapes = 12). A malformed-only
   probe satisfies the criterion's shape while the absent-file arm regresses; fewer than 12 lines fails the
   criterion regardless of what its diff says.
7. If the marker is red, classify before reacting: pre-existing (it is red on pristine `upstream/main`
   `98198e980`, `1 failed in 96.97s`, `^ERROR tests/` = 0) versus caused by this mission's landings. Do not
   fix it here; name the owning WP.

`spec-kitty agent tasks mark-status T048 --status done`

### Subtask T049 — Re-derive the counts, the two deltas, and close the ledger

**Goal:** every number that moved during the mission, re-measured on the merged tree with its input count.

1. **Routed (`SC-011` / `NFR-002`).** Print the live routed count with the command and the number of files
   walked. Expected **130** — 0-net from WP02/WP03/WP04, **+1** from WP05 at `ref_advance.py:247`. Control
   the probe: the naive grep gives **296**; the AST census gives **129** at baseline. Quote both so the
   reader can see the probe is the right one.
2. **The floor — measure, never copy.** `plan.md`'s `## [UNVERIFIED] items` row 1 states plainly that
   **`127` and `[128, 131]` are derived from the ruling's stated rule, not measured**, and that copying them
   is forbidden. **Read the merged tree's `ROUTED_LOAD_META_FLOOR` and `ROUTED_LOAD_META_FLOOR_MARGIN` out
   of `tests/architectural/test_inline_meta_read_gate.py` and print the values found**, then print the band
   that follows from them.
3. **The bound is two-sided.** `test_routed_load_meta_floor` (`:1084`) asserts **three** things:
   `len >= FLOOR` (`:1092`), `len > FLOOR` (`:1097`, explicitly anti-vacuous — its own message says "not
   '>= len(routed)' (anti-vacuous)") and `len - FLOOR <= MARGIN` (`:1101`). The middle one is strict, so at
   floor 126 the admissible band is `[127, 130]` and **126 is RED**. State that a fold which *collapses* two
   calls into one reds the gate **downward** — three prior floor mismatches in this programme came from
   exactly that. Run the test and quote its `N passed` line.
4. **Inline (`SC-006`) — two numbers, never one.** Report the **widening delta** (sites the predicate change
   adds at a fixed tree) and the **code delta** (sites the source change adds at a fixed predicate)
   **separately**. One number cannot distinguish "the widening found a real site" from "a new unrouted read
   landed". Expected admissible outcome: live returns to **7**, with `INLINE_META_READ_FLOOR`,
   `FLOOR_MARGIN` and `inline_meta_read_baseline` all still **7**. Any raised inline floor requires the code
   delta printed as **0** *and* the raise argued in the PR body (T052).
5. **The ledger closes.** `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` gates on exact
   equality in **both** directions — `test_no_unaccounted_load_meta_call_sites`'s unaccounted arm and its
   stale-row arm pass and fail together. Report the `pending-batch-a` row count as a **delta, not a bare
   number**: baseline is **12 rows** (verified — `grep -c 'pending-batch-a'` returns **13**, of which one is
   the legend comment at `:185`; that exclusion is the control for the count), and after WP02/WP03/WP04 the
   routed sites' rows must all be gone. Print `12 → N` and enumerate any survivor with the reason it lived.
6. **Attribute deviations before fixing them.** Any count that is not the expected value is reconciled
   against WP01's recorded command and input file count **first**. The gate's own header records **three**
   prior false reds from this exact miscount.
7. If a count varies between runs, report the **distribution** over ≥3 runs, not a scalar.
8. **Create `scripts/verify_meta_fail_closed_integration_3162.py`** — this WP's one owned file, and a required
   deliverable, not a placeholder. It re-derives everything in steps 1–5 in one command so a reviewer can
   reproduce the integration verdict without reconstructing it from prose: routed and inline counts with their
   input file counts, `ROUTED_LOAD_META_FLOOR` and `ROUTED_LOAD_META_FLOOR_MARGIN` read off
   `tests/architectural/test_inline_meta_read_gate.py`, the band that follows from them, and the
   `pending-batch-a` row count with the `:185` legend line excluded. It takes the tree root as an argument and
   defaults to the repository root; it **prints the tree and the `PYTHONPATH` it measured**; it exits non-zero
   if any count is outside the band. `ruff check` clean, complexity <= 15 per function, no `# noqa`. Quote its
   output verbatim into the artifact beside each number, and cite it by path as the regeneration command.
   If WP01 shipped `scripts/verify_meta_routing_manifest_3162.py`, **reuse its shape** rather than authoring a
   second way to count — a second predicate answering one question is what `NFR-002`'s kept clause forbids.

**Files**: `scripts/verify_meta_fail_closed_integration_3162.py` (new); evidence into
`contracts/integration-verification.md`.

`spec-kitty agent tasks mark-status T049 --status done`

### Subtask T050 — The 14-directory cone, `-ra`, and `SC-017`

**Goal:** the merged tree is green over the mission's real cone, and the static gates are clean, both
measured per directory rather than in aggregate.

1. Run each of the 14 directories, **redirected** and **under an explicit `timeout`**, one file per
   directory. Serial form:
   ```bash
   timeout 1800 .venv/bin/python -m pytest <dir> -ra > <scratch>/wp08_cone_<dir>.txt 2>&1; echo "exit=$?"
   ```
   Documented parallel form, permitted for every directory you have **not** identified as binding a real port
   or a singleton daemon (§ The sweep is priced):
   ```bash
   PWHEADLESS=1 timeout 1800 .venv/bin/python -m pytest <dir> -ra \
     -n auto --dist loadfile -p no:cacheprovider > <scratch>/wp08_cone_<dir>.txt 2>&1; echo "exit=$?"
   ```
   **`--dist loadfile`, never bare `--dist load`.** Any directory you run `-n0` must be named with the
   resource it binds. Quote the `N passed` / `N failed` line **per directory**, verbatim from the file, with
   `exit=` and the elapsed time beside it. Never pipe a suite whose exit status you need. `exit=124` is a
   `timeout` expiry — record it as **neither pass nor fail** and re-run it in the parallel form (or with a
   larger, printed budget); do not raise the budget silently and do not let it read as green.
2. Print the **selected count per directory** (`collected N items`) alongside the pass line. A pass line
   without a collection count cannot distinguish green from empty.
3. `grep -c '^ERROR tests/'` per file — **not** `^ERROR `, which catches unrelated prose. Report each count,
   including the zeros.
4. Targeted cone runs per charter §Testing Requirements. **Do not substitute a full-suite run**; the
   full-suite gate is reserved for post-merge mission-level validation. Do not add `tests/sync` or
   `tests/cli` to the selection (`C-007`).
5. Classify every red before treating it as this mission's: reproduce on the pristine baseline in a separate
   `git worktree` with the **same selection**, and quote both runs. A red that reproduces there is
   pre-existing and is reported, not fixed here. Name the owning WP for any red that is this mission's.
6. A killed or timed-out directory run is **neither pass nor fail** — record it as killed/timed-out with the
   elapsed time, the budget, and `exit=124`, then **re-run it in the documented parallel form** (§ The sweep
   is priced) rather than re-running the same serial selection and hoping. Do not let it read as green, and do
   not drop the directory from the cone because it timed out.
7. **`SC-017`**: `ruff check` and `mypy --strict` over the mission's touched files. Print the **file list and
   its count** (the input count), then the results, and count only **new** errors — establish the baseline
   error set on the pristine tree with the same file list and show the difference. No `# noqa`,
   `# type: ignore` or per-file ignore may be added to reach zero. **`ruff check` only — never
   `ruff format`.**

`spec-kitty agent tasks mark-status T050 --status done`

### Subtask T051 — Complete the `SC-009` filing register

**Goal:** one row per mandated filing, each **verified**, with the register closing or explicitly stating
why a row is empty.

1. Build the register as a table: `#` / filing / mandated-by / issue number / verification line. Verify
   **every** row with `gh issue view <n> --json number,title` and quote the output. An issue number that was
   never viewed is not a filing.
2. At least **five** obligations exist across the mission and only ~2 were pinned upstream; `spec.md`
   `SC-009` enumerates eight. The ones that must close here include: the **`#2804` superseding issue**
   (`FR-010`, `Q9`); the **pending-poisons-the-aggregate product defect** with
   `src/specify_cli/acceptance/gates_core.py:525` cited as its evidence (`FR-011`, `C-006`); the
   **4-read-expression deferral** (`FR-007`, `NFR-004`); **`Q8`**'s lock-only comparison duplicated ×3 with
   `_VCS_LOCK_META_FIELDS` declared twice (`C-009` — filed **before** that code was edited, number cited in
   a comment at the surviving comparison); **`NFR-001`'s degrade residue** with `Q4` as candidate remedy;
   the **L1 pure-decode primitive** (`text|bytes → dict|None`, typed) (`C-004`); the **`_baselines.yaml`
   register deviation** if that is how it was resolved rather than by adding the entry; and the **`Q2`
   full-routing residue**.
3. Where a row is empty, say **why** in the row — "not filed", "resolved by adding the register entry
   instead, `git show` quoted", "superseded by #N" — never leave it blank and never mark it done by
   narration.
4. For the `_baselines.yaml` row, record which remedy was taken. The absence is verified upstream
   (`grep -c inline_meta tests/architectural/_baselines.yaml` → **0**); the charter Burn-down Policy §(a)
   choice is a governance call, so record the operator's answer or record that it is still open.
5. `Q4` and `Q11` remain **operator** questions. Record them as open with their owners; do **not** answer
   them here, and do not present a filing as an answer.
6. Cross-check the register against this WP's own findings: any defect surfaced in T048/T049/T050 that this
   WP declined to fix must appear as a register row with the owning WP named.

`spec-kitty agent tasks mark-status T051 --status done`

### Subtask T052 — History compaction, rebase, and the cross-fork DRAFT PR

**Goal:** one readable, linear, sliced branch and a **DRAFT** PR whose body carries the arguments no test
can carry.

1. Compact and rebase onto the current upstream base — **admin bunched, code by slice**, per charter
   §Code Quality (linear, rebased onto the current upstream base, logically sliced). **Not one squash.**
2. **Do not squash WP04's two commits.** The routing-then-handler ordering **is** the ATDD evidence that
   replaces the base-red `NFR-003` makes impossible. Quote `git log --oneline` showing both present, in
   order, inside the lane.
3. Open the PR **cross-fork to `Priivacy-ai:main`, as a DRAFT**. Quote the creation command and the returned
   URL, and confirm the draft flag in `gh pr view --json isDraft`.
4. The PR body must carry, or the corresponding charter row reverts to a violation:
   - `SC-006`'s **argued raise** — if any floor was raised, the argument for it, with the code delta printed
     as **0**;
   - the **widening delta and the code delta as two separate numbers**;
   - the **`C-011` documented exception** with its five reviewer verification steps (routing SHA + its red,
     handler SHA green on the same selection, `git log` ordering inside the WP, both commits unsquashed,
     `SC-002`'s empty diff over non-empty captures with the positive control first);
   - the routed count `129 → 130` against the **measured** floor and band, with **126 is RED** stated;
   - the ledger row delta `12 → N`;
   - any remaining Sonar UI-side work, stated explicitly.
5. **Never merge the PR from an agent. Never un-draft** without the operator's explicit go — the operator
   performs the mainline merge (charter: "The operator merges").
6. Link the `SC-009` register's issues from the PR body so the filings are reachable from the diff.

`spec-kitty agent tasks mark-status T052 --status done`

## Definition of Done

- [ ] `contracts/integration-verification.md` **and** `scripts/verify_meta_fail_closed_integration_3162.py`
      both exist, and are the **only two** files this WP wrote; no source, no test, no `spec.md` / `plan.md` /
      `wps.yaml` / other `tasks/*.md` touched.
- [ ] **The script exists and its output is quoted.** It is this WP's entire declared write surface
      (`owned_files`), `create_intent` suppresses the zero-match ownership error
      (`src/specify_cli/ownership/validation.py:411-433`), and no review or accept gate revisits existence — so
      an absent script is invisible to tooling and only a reviewer catches it. It must re-derive, on the merged
      tree: routed and inline counts with their input file counts, `ROUTED_LOAD_META_FLOOR` and its margin read
      off `tests/architectural/test_inline_meta_read_gate.py`, the derived band, and the `pending-batch-a` row
      delta with the `:185` legend excluded; print the tree and `PYTHONPATH` it measured; and exit non-zero on
      any count outside the band. `ruff check` clean; complexity <= 15 per function; no `# noqa`.
- [ ] The artifact **is** the evidence: every capture, sample and pass line quoted below lives in that
      committed file, not in a `mark-status` record (which carries only `{T0xx: Status}`,
      `src/specify_cli/status/models.py:481`) and not only in `/tmp`.
- [ ] Every command run outside the repository root carries `PYTHONPATH=<workspace>/src`, and the artifact
      names which tree each number came from.
- [ ] The artifact states **in writing** that `pip install -e .` preceded every capture, with the command
      and its final line quoted.
- [ ] `PATH` fix and `command -v spec-kitty` quoted, resolving inside the tree's `.venv/bin`.
- [ ] `C-007`: **≥3 timestamped** `pgrep` samples quoted (not one), the sibling check recorded with its gaps
      named, and the 14-vs-2 disjointness printed.
- [ ] `SC-008`: marker `N passed` line quoted verbatim from a redirected run; `^ERROR tests/` counted; both
      assertions named at `:482` and `:489` after **opening** the file; both `git diff --stat` obligations
      quoted with empty output shown as empty.
- [ ] `SC-010`: companion result quoted; fixture confirmed to be the defect's own shape.
- [ ] `SC-002`: **positive control quoted first and non-empty**; `diff pre.txt post.txt` empty; **12**
      captured lines per run; input count (4 × 3) printed; both `wc -l` non-zero.
- [ ] `SC-011` / `NFR-002`: routed count printed with command **and input count**; naive-grep control
      (**296** vs the census's **129**) shown; floor and margin **read off the merged tree and printed**,
      never copied from `plan.md`'s `127` / `[128,131]`; band derived from the printed values; **126 is
      RED** stated; the three assertions cited at `:1092`, `:1097`, `:1101`.
- [ ] `SC-006`: widening delta and code delta reported as **two separate numbers**.
- [ ] Ledger: `pending-batch-a` row count reported as a **delta** (`12 → N`, with the `:185` legend line
      excluded and that exclusion shown as the control); survivors enumerated with reasons.
- [ ] The **14-directory** cone: `N passed` line **per directory** from redirected runs, `collected N items`
      per directory, `^ERROR tests/` per directory; `-ra` used; no full-suite substitution; no `tests/sync`,
      no `tests/cli`.
- [ ] Every directory run carries an explicit `timeout` with the **budget and elapsed time printed**; any
      `exit=124` recorded as **neither pass nor fail** and re-run; where `-n auto --dist loadfile` was used,
      `--dist load` was **not**, and the `collected N items` count matches the serial `--collect-only` figure;
      any `-n0` directory named with the OS-global resource it binds.
- [ ] `SC-017`: file list **and count** printed; `ruff check` and `mypy --strict` results quoted; only
      **new** errors counted against a same-file-list baseline; no suppressions added; no `ruff format`.
- [ ] `SC-009`: register complete, every row verified by a quoted `gh issue view <n> --json number,title`;
      empty rows carry a stated reason.
- [ ] Any killed or timed-out run recorded as **neither pass nor fail**.
- [ ] Any varying count reported as a **distribution** over ≥3 runs.
- [ ] Every defect found is **reported with the owning WP named**, not fixed here.
- [ ] Every citation carries **`file:line` and symbol** (`C-003`).
- [ ] DRAFT cross-fork PR to `Priivacy-ai:main` open; history linear and sliced; WP04's two commits
      unsquashed; PR body carries the argued raise, the two deltas, and the `C-011` exception with its five
      verification steps; **not merged, still a draft**.

**Subtask marking** — run per subtask as it completes. This records **status only**; it is not the evidence
channel. The evidence is the committed `contracts/integration-verification.md`.

```bash
spec-kitty agent tasks mark-status <Txxx> --status done --mission meta-fail-closed-3162-01KZ7FSQ
```

## Risks

1. **The stale install.** Re-capturing `SC-008` before `pip install -e .` produces a verdict about code that
   is not on disk. Both directions are worthless — a false red sends someone hunting a phantom, a false
   green ships the regression. Reinstall first, and say so in the artifact.
2. **The stale global binary.** `/home/jeroennouws/.local/bin/spec-kitty` is first on `PATH` today and
   resolves to an unrelated checkout (verified). Any CLI measurement taken without the `PATH` fix is void.
3. **One `pgrep` sample.** A sample taken between two selections shows nothing and has already misled this
   programme. Three spaced samples, timestamped, or the handshake is unrecorded.
4. **Copying the floor.** `127` and `[128,131]` appear in `plan.md` and look authoritative. They are
   rule-derived, `plan.md` says so in its `[UNVERIFIED]` list, and copying them is forbidden. Measure.
5. **Reading the bound as one-sided.** **126 is RED.** A fold that collapses two routed calls into one reds
   the gate downward, and three prior mismatches in this programme came from exactly that. A criterion that
   only bounds from above is satisfied by a change that breaks the gate.
6. **Reporting `SC-006` as one number.** It hides both failure modes it exists to separate.
7. **A malformed-only `SC-002` probe.** Satisfies the criterion's shape while the absent-file arm regresses
   — the exact defect `NFR-003` was rewritten to catch.
8. **`^ERROR ` instead of `^ERROR tests/`, `-rf` instead of `-ra`, piping a suite whose exit status
   matters.** Each silently changes the number being reported.
9. **Citing a line without opening it.** Docstring prose was carried as a pinning assertion through four
   artifacts in this programme. Open the file.
10. **Fixing what you found.** This WP has no code surface. A defect found here is filed and attributed, and
    the owning WP fixes it; absorbing it here destroys both the attribution and the review boundary.
11. **Squashing the branch, or un-drafting it.** Squashing destroys `FR-002`'s only red; un-drafting or
    merging without the operator's explicit go violates the charter's "the operator merges".
12. **An unbudgeted sweep that never terminates.** Measured on this tree: `--collect-only -q` on one file
    took **50.22 s**; one gate node took **58.20 s**. Without a `timeout` and the documented
    `-n auto --dist loadfile` form, the 14-directory cone is not finishable and the honest "a timed-out run is
    neither pass nor fail" rule becomes a reason to report nothing. Budget it, parallelise it the documented
    way, print the elapsed time.
13. **`--dist load` instead of `--dist loadfile`.** Scatters a file's tests across workers and breaks
    file-scoped fixture and collection semantics — a red that is the runner's, not the mission's.
14. **Running in a lane worktree.** This WP is `planning_artifact` and runs at the repository root. Nothing
    provisions `.venv` into a worktree (`.gitignore:31-32`), and outside the install tree the gate's
    `SRC_ROOT` (`test_inline_meta_read_gate.py:61`) and the ledger test's `_SRC_ROOT` (`:54`) read the edited
    `src/` while imports resolve to the unedited one. Carry `PYTHONPATH=<workspace>/src` on any command that
    leaves the root.

## Reviewer Guidance

Check these in order; the first four are where this WP fails if it fails.

1. **Was the reinstall first, and is it stated?** Find the `pip install -e .` line and confirm it precedes
   the marker capture in the artifact's own narrative. If the order is not stated, treat every
   install-sensitive number as unmeasured.
2. **Are the floor and band measured or copied?** If the artifact prints `127` or `[128,131]` without a
   command that read them off the merged tree, reject — `plan.md`'s `[UNVERIFIED]` row 1 forbids exactly
   that. Then confirm the two-sidedness is stated with **126 is RED** and the three assertions cited at
   `:1092`, `:1097`, `:1101`.
3. **Two numbers for `SC-006`?** One number is a rejection, whatever its value.
4. **Input counts everywhere.** Every derived number must show N in, M out, and why the N−M dropped. Check
   the routed count, the inline count, the ledger delta, the `SC-017` file list and the `SC-002` probe
   individually — a bare output number is not a measurement.
5. **Controls shown, not claimed.** The naive-grep control (**296** vs **129**), the `pending-batch-a`
   legend-line exclusion, and `SC-002`'s positive control must each be **quoted**. A bare "verified" is not
   a control.
6. **Per-directory pass lines, read out of files.** 14 directories, 14 `N passed` lines, 14 collection
   counts, 14 `^ERROR tests/` counts. Aggregates hide empty selections. Confirm `tests/sync` and `tests/cli`
   are absent and that no full-suite run was substituted for the cone.
7. **`SC-009` rows are viewed, not numbered.** Every row needs a quoted `gh issue view`. An empty row needs
   a stated reason.
8. **The PR is a DRAFT, cross-fork, sliced, and argues its raise.** Confirm WP04's two commits survive
   unsquashed and that the body carries the `C-011` exception with its five steps. If the body omits them
   the exception is undocumented and the charter row reverts to a violation.
9. **Defects are attributed, not absorbed.** Every finding names the owning WP.
10. **The declared write surface is not empty.** `scripts/verify_meta_fail_closed_integration_3162.py` must
    exist, be `ruff check` clean, and have its output quoted in the artifact. It is this WP's only `owned_files`
    entry; `create_intent` suppresses the tooling's zero-match error and no later gate re-checks existence, so a
    WP marked done without it was marked done with an empty write surface. **Run it yourself** and compare its
    numbers against the artifact's.

### Things in the upstream planning artifacts to be aware of

- **`spec.md` `SC-008` and `plan.md`'s file-collision matrix cite the right path; `WP04`'s risk note does
  not.** The byte-identical file is `tests/specify_cli/cli/commands/test_row_aware_merge_driver.py`
  (verified: `find tests -name test_row_aware_merge_driver.py` returns exactly that one path). WP04's risk 8
  calls it `tests/merge/test_row_aware_merge_driver.py`, which does not exist. Use the verified path — a
  `git diff --stat` against a non-existent path prints nothing and would read as a **false green**.
- **`spec.md` `SC-009` mandates "≥5" filings and then enumerates 8.** The row count is the obligation, not
  the prose floor: close all eight or state per row why not.
- **The register's verification flags differ across artifacts** — `plan.md` IC-08 and `wps.yaml` T051 say
  `--json number,title,body`; this WP requires at minimum `number,title`. Quoting `body` as well is strictly
  better; do not treat the shorter form as non-compliant.
- **`analysis-report.md` predates the IC renumbering** and attributes some IC-05 surfaces to IC-04. Read
  `plan.md`'s numbering as authoritative.
- **`analysis-report.md`'s trailing Correction applies to every pin you inherit.**
  `tests/integration/test_coord_loop_workspace.py:611,627` are **docstring prose**, not assertions. Do not
  cite them as evidence of anything, and apply the same suspicion to every line number handed to you.
- **The "twelve of fourteen directories are parallel-safe" split does not reproduce.** The post-tasks squad's
  remediation directive asked for `-n auto --dist loadfile` to be permitted for *twelve* of the fourteen,
  implying two real-port/daemon exclusions. Measured on this tree, the only serial-only suite named anywhere in
  the documentation is `tests/sync/test_orphan_sweep.py` (ports 9400–9449,
  `docs/development/testing-parallel.md:82-93`), and it is **outside** this mission's cone — so the split is
  **14/0**, not 12/2, and the identity of the two implied exclusions is `[UNVERIFIED]`. Apply the documented
  criterion (binds an OS-global resource: real TCP port or singleton daemon) to each of the fourteen yourself,
  name any directory you exclude and the resource it binds, and record the count you found.

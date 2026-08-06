# WP08 — terminal integration verification

Mission `meta-fail-closed-3162-01KZ7FSQ`. Every number below was re-derived in this WP; nothing
is summed from a per-lane report. Commands are quoted with their exit status and elapsed time.

## §0 Scope — what this artifact covers, and what it does NOT

**This §0 was rewritten on the second pass (2026-08-06).** Its previous version said the
14-directory cone had not been run and that T047, T048 and T051 were not done. All four of those
statements are now **out of date** and are corrected below; the earlier version is superseded, not
merely amended, because a reader who trusted it would under-read the evidence that now exists.

**Every count in this artifact is `pre-rebase (base 96494e5ec)`.** The branch is 95 commits behind
`upstream/main` (tip `d0ed802cc`), and `upstream/main` is itself already red on this mission's own
gate (`test_routed_load_meta_floor`: routed 133, floor 128, band `[129, 132]`) with a routed site
set largely disjoint from ours. So the post-rebase routed count is **neither 130 nor 133** and the
floor will need re-deriving. That rebase and that re-derivation are the **orchestrator's**, not this
WP's, and are recorded in `residual-ledger.md` under BASE HYGIENE. Read every number below as
correct against the base that exists today and as requiring a re-take afterwards.

**Covered here:** T047 (§11), T048 (§12), T049 (§5, §13 — including the script at §5.6), T050
(§14, discharged from the full-suite measurement), T051 (§15), plus the original four ledger items
`F10` (§2), `F2` (§3), `F3` (§4), `F13` (§1), the architectural cone (§6), the static gates (§7),
and the WP03 review folds (§8).

| Subtask | Status | Where |
|---|---|---|
| T047 — `C-007` sweep-window check, ≥3 timestamped samples | **DONE** | §11 — 4 samples, spaced 35 s, all quoted including the empty ones |
| T048 — reinstall FIRST, then re-capture `SC-008` / `SC-010` / `SC-002` | **DONE** | §12 — reinstall at `19:47:55`, marker `2 passed`, `SC-002` 12 lines each side with the positive control first |
| T049 — re-derive the counts, the two deltas, close the ledger | **DONE** | §5 + §13; the script now **exists** (§5.6) |
| T050 — the 14-directory cone, `-ra`, `SC-017` | **DONE** | §14 — discharged from a 16-pass full-suite measurement of 21,475 nodes, attributed against `96494e5ec` |
| T051 — the `SC-009` filing register | **DONE** | §15 — all 8 rows, each verified by a quoted `gh issue view`; row 5's emptiness carries its reason |
| T052 — history compaction, rebase, cross-fork DRAFT PR | **NOT DONE — the orchestrator's step** | Deliberately left unmarked. The operator is landing the PR personally. This WP did not compact history, did not rebase, did not push and did not open a PR. |

**One subtask is genuinely not done and is not claimed:** T052. Nothing below should be read as PR
readiness.

**Convention: every issue reference in this file is backticked, including inside quotations and code
fences.** Cycle 1 rejected this artifact for a **bare** `#3113` at what was then `:473`, which minted
an unresolvable issue-matrix row and blocked the mission's approval gate (fixed in `8ed6a1258`). A bare
`#NNNN` anywhere in a mission artifact re-breaks that gate, so where a quoted commit message, `gh`
payload or source comment contained a bare reference, the backticks were added. **Only the backticks
were added** — no quoted text was otherwise altered.

## §1 Environment, and the `F13` cross-tree rule

```
$ export PATH=/home/jeroennouws/dev/sk-missions/3162/.venv/bin:$PATH; command -v spec-kitty
/home/jeroennouws/dev/sk-missions/3162/.venv/bin/spec-kitty
```

Resolves inside the tree's own `.venv/bin`, not the stale `~/.local/bin` binary.

**The reinstall preceded every capture in §5–§7.**

```
$ .venv/bin/python -m pip install -e . --no-deps
  Uninstalling spec-kitty-cli-3.2.6:
    Successfully uninstalled spec-kitty-cli-3.2.6
Successfully installed spec-kitty-cli-3.2.6
exit=0
```

**Baseline ref.** `96494e5ec` = `git merge-base HEAD main` = `git merge-base HEAD upstream/main`.
`98198e980` is `upstream/main`'s **tip**, not the fork point, and is used nowhere below.

**`F13`.** Every `pytest` run in this WP was executed **in the repository-root tree**
`/home/jeroennouws/dev/sk-missions/3162`, so form A cannot arise. `rootdir` was printed as the
control on every run:

```
rootdir: /home/jeroennouws/dev/sk-missions/3162
configfile: pytest.ini
```

The single scratch-tree measurement (§8's `contextlib.suppress` positive control) used
**standalone `python`** against a `git archive HEAD src` tree — the form F13 records as sound
for `PYTHONPATH` — and `git status --short src/` was verified empty afterwards.

**`C-007` negative-need argument (argument only — not a sampled measurement).** The selection
run in §6 is `tests/architectural`. `tests/sync` and `tests/cli` are not that directory and were
not run. `tests/specify_cli/cli/commands/` is inside `tests/specify_cli` and is **not** the
barred top-level `tests/cli`; `SC-008`'s byte-identical file
`tests/specify_cli/cli/commands/test_row_aware_merge_driver.py` lives under the former.

## §2 `F10` — six mission-introduced architectural gate reds, closed

The ledger recorded **four** remaining. Running the **whole** `tests/architectural` directory
instead of WP06's 57-node selection surfaced **two more** (§2.3, §2.4).

### 2.1 Red first, quoted verbatim

`4 failed, 1 passed in 358.84s`, `grep -c '^ERROR tests/'` = **0**.

```
test_ci_collection_completeness::test_every_test_node_is_collected_on_a_push_to_main
  AssertionError: 6 of 36260 collected test NODES (1 files) run in NO job on a push to 'main'
  Files with at least one such node:
      tests/runtime/test_wp02_row05_bridge_io_fail_closed.py

test_next_shard_marker_completeness::test_every_next_root_test_has_exactly_one_shard_marker
  AssertionError: 11 test(s) under group 'next' carry NO shard marker (assignment gap —
  add the missing unit to the 'next' row's shard map)

test_next_shard_marker_completeness::test_shard_union_equals_full_next_root_universe
  AssertionError: 11 test(s) under group 'next' are collected but selected by NO shard marker

test_gate_coverage::test_no_new_orphan_surfaces
  AssertionError: 1 test file(s) are selected by ZERO CI gates and are not in the recorded
  baseline — they will never run in CI:
      tests/runtime/test_wp02_row05_bridge_io_fail_closed.py
```

`test_meta_bypass_diagnosability.py` is **absent** from that list: the module-level `pytestmark`
fix applied before WP08 had already closed it. Red #4 names exactly one file.

### 2.2 One root cause for reds 1–4, and the trap in fixing it

`tests/_next_shard_map.py` registers the `next` group with `default_fallback=False`
(`tests/_shard_registry.py`), so an under-root file absent from `file_assignment` receives **no**
`next_shard_N` marker at all. The `arch` row opts into the hash-bucket fallback and would have
auto-covered it; `next`'s does not. The ledger's diagnosis (*"shard assignment, not markers —
`tests/conftest.py:242`"*) was **correct**.

Both of WP02's files were registered in shard **2** — lightest by file count, `24/22/25` →
`24/24/25`, this module's own documented pick rule.

**The trap.** `tests/next/test_wp02_row04_planner_fail_closed.py`'s only gate was
`unit-contract-residual`, whose selector **excludes every `next_shard_*` test by construction**:

```
-m "(unit or contract) and not (fast or integration or git_repo or slow or e2e or
architectural or distribution or windows_ci or quarantine or regression or timing or
docs_scoped or arch_shard_1 or arch_shard_2 or arch_shard_3 or next_shard_1 or
next_shard_2 or next_shard_3)"
```

Registering it in the shard split **alone** would have moved it from one gate to **zero** —
turning a GC-1 fix into a new orphan. Its module marker therefore goes `unit` → `[unit, fast]`,
which places it in `fast-tests-next` (`-m "fast and not windows_ci"`, shard-agnostic). `fast` is
honest, measured: slowest item **0.06 s**, no subprocess, no git, no network
(`docs/context/testing-taxonomy.md` §Fast — `fast` is the performance characterisation,
orthogonal to the `unit` category).

### 2.3 Red 5 — golden-count regrowth (a NEW finding, not in the ledger's list)

```
test_golden_count_ban::test_convert_sites_do_not_exceed_frozen_baseline
  tests/architectural: 26 un-annotated convert-classified golden-count site(s) exceeds the
    frozen baseline ceiling of 25.
  tests/mission_runtime: 4 un-annotated convert-classified golden-count site(s) exceeds the
    frozen baseline ceiling of 0.
```

Attribution, re-derived with the gate's own `scan_repo()`:

* `tests/architectural` 26 = **25 pre-existing + 1 mine** (WP08's own new F3 gate file).
* `tests/mission_runtime` 4 = **all four WP04's**, in `test_wp04_routed_call_counts.py` and
  `test_wp04_sc007_guard_and_handler_contract.py`. `tests/mission_runtime` is **absent** from
  `_golden_count_baseline.json`'s ceilings ⇒ implicit ceiling **0**, so the gate went red the
  moment WP04 landed. **Mission-introduced, not pre-existing at `96494e5ec`** — the directory
  could not have been absent from the ceilings had it carried convert sites when they were frozen.

Fixed as **2 conversions + 3 per-site escapes**, judged individually, with
`_golden_count_baseline.json` **untouched**:

| Site | Remedy | Why |
|---|---|---|
| `test_sweep_degrade_arms_instrument.py` `len(hazards) == 1` | **convert** | A set-equality over hazard identity `(file, function, sorted(caught), guarded_callee)`. A bare count passes when the sweep reports one hazard at the **wrong frame** — the failure mode that matters for an instrument whose job is naming the frontier frame. |
| `test_wp04_sc007_…py` `len(_C002_HANDLERS) == 6` | **convert** | A frozenset equality over the six `(module, symbol)` pairs. The count passes when one governed handler is **swapped** for another — exactly the edit `C-002` exists to catch. |
| `len(targets) == 1` ×2 (both AST helpers) | escape | Every element is an `ast.FunctionDef` whose `.name` **is** `symbol` by construction of the filter that built the list. The elements are indistinguishable, so `set(targets)` carries **less** information than the count. The contract is uniqueness of the definition. |
| `len(fail_closed) == 1` | escape | `fail_closed` is a list of **identical strings** (filtered `n == _FAIL_CLOSED_CALLEE`), so `set(fail_closed) == {…}` holds for one call **and for five** — strictly weaker. The count IS the contract: the mission's routed-budget assertion, load-bearing in both directions. |

Re-scanned after the edits, ceilings file unchanged:

```
tests/architectural   : live=25  ceiling=25
tests/mission_runtime : live=0   ceiling=ABSENT->0
violating dirs: []
```

### 2.4 Red 6 — the E3 manifest, refrozen with the direction measured

```
test_gate_coverage::test_gc2b_bites_on_producer_side_selection_shrink
  producer-side fault injection did not shrink the REAL selection ...
  Extra items in the left set:
    'tests/runtime/test_wp02_row05_bridge_io_fail_closed.py::test_census_row05_*'
```

That test asserts a **strict subset** of the committed E3 node-id manifest, so adding 6 tests to
`integration-tests-next`'s real selection reds it. Its companion
`test_model_fidelity_spotcheck_sharded_next_tier` **passed** (modeled == fresh real), so model
and reality agree — only the snapshot was stale.

`tests/architectural/baselines/integration-tests-next-nodeids.txt` was refrozen, captured with
`gc.collect_real_union_for_target` (the **same** function both sides of the GC-2b comparison
use, so the two sides cannot drift apart via a capture-method difference):

```
target        : integration-tests-next
committed     : 442 node-ids
fresh REAL    : 448 node-ids
DROPPED (in committed, not fresh): 0
ADDED   (in fresh, not committed): 6
   + tests/runtime/test_wp02_row05_bridge_io_fail_closed.py::test_census_row05_corrupt_meta_raises_typed_error_through_ephemeral_query_run
   + tests/runtime/test_wp02_row05_bridge_io_fail_closed.py::test_census_row05_corrupt_meta_raises_typed_error_through_get_or_start_run
   + tests/runtime/test_wp02_row05_bridge_io_fail_closed.py::test_census_row05_is_routed_exactly_once_and_is_not_folded
   + tests/runtime/test_wp02_row05_bridge_io_fail_closed.py::test_census_row05_module_carries_no_local_typed_raise
   + tests/runtime/test_wp02_row05_bridge_io_fail_closed.py::test_census_row05_negative_control_absent_meta_returns_none_pair
   + tests/runtime/test_wp02_row05_bridge_io_fail_closed.py::test_census_row05_negative_control_valid_meta_returns_none_pair

$ git diff --stat tests/architectural/baselines/integration-tests-next-nodeids.txt
 tests/architectural/baselines/integration-tests-next-nodeids.txt | 7 +++++++
 1 file changed, 7 insertions(+)
```

**0 deletions.** That is coverage *gained*, not a gap accepted — a refreeze that accepted a gap
shows `DROPPED > 0`. The file's own committed header mandates this exact path (*"Regenerate ONLY
with an explicit provenance comment (data-model E3) when a WP legitimately changes this job's
selection"*), and `_gate_coverage.py:1113-1124` records the same design intent. Had the diff
dropped anything, the gate would have been left red and ledgered instead.

**`_gate_coverage_baseline.json`, `_baselines.yaml` and `_golden_count_baseline.json` were not
touched anywhere in WP08.**

### 2.5 Closure evidence — the authoritative analyzer, never a workflow grep

`tests/architectural/_gate_coverage.py`. Universe **36268** nodes, **68** gates parsed, **57**
jobs active on a push to `main`. Elapsed 82 s.

```
SUMMARY: 17/17 files have ZERO zero-gate nodes in BOTH models;
         total zero-gate nodes across both models = 0
```

All 17 test files this mission added (16 from WP02–WP07 plus WP08's own gate) are selected by
**exactly one** gate, in both the all-jobs and the main-push-active model. The three that moved:

```
=== tests/next/test_wp02_row04_planner_fail_closed.py
  nodes: 5  markers(union): ['fast', 'next_shard_2', 'unit']
  [ALL-JOBS]  gates: 1; nodes with ZERO gates: 0
      ci-quality.yml:fast-tests-next:'fast and not windows_ci'  -> 5/5 nodes
  [MAIN-PUSH] gates: 1; nodes with ZERO gates: 0

=== tests/runtime/test_wp02_row05_bridge_io_fail_closed.py
  nodes: 6  markers(union): ['git_repo', 'integration', 'next_shard_2']
  [ALL-JOBS]  gates: 1; nodes with ZERO gates: 0
      ci-quality.yml:integration-tests-next:'next_shard_2 and not windows_ci and (git_repo or integration)'  -> 6/6 nodes
  [MAIN-PUSH] gates: 1; nodes with ZERO gates: 0

=== tests/architectural/test_sweep_degrade_arms_instrument.py
  nodes: 8  markers(union): ['arch_shard_1', 'architectural', 'git_repo']
  [ALL-JOBS]  gates: 1; nodes with ZERO gates: 0
      ci-quality.yml:arch-adversarial:'arch_shard_1 and not windows_ci and (git_repo or integration or architectural) and not timing'  -> 8/8 nodes
  [MAIN-PUSH] gates: 1; nodes with ZERO gates: 0
```

Universe consistency control: **36260** nodes before WP08's 8 new tests, **36268** after — a
delta of exactly `+8`.

## §3 `F2` — the CHANGELOG entry

`docs/changelog/CHANGELOG.md` (repo root is a symlink to it), under `## [Unreleased] - 3.2.6` /
`### 💥 Breaking Changes`. Content: the 13 routed read call sites enumerated by
`module:symbol`; the `ValueError` → `MissionMetaReadError` type change with
`load_meta_fail_closed` at `src/specify_cli/core/paths.py:638` and `MissionMetaReadError` at
`:506`; the **ten** widened handlers in three groups; and the floors.

**13 routed call sites, derived not asserted.** The branch deletes **12** `pending-batch-a` rows
from `_ACCOUNTED_SITES` in `tests/specify_cli/test_meta_fail_closed_full_census_contract.py`,
one of which (`missions/_read_path_resolver.read_primary_meta`) carries count **2** ⇒ 12 rows,
13 call sites. The two totals are never addable and the entry says which is which.

**Ten widened handlers, in three groups** — recording only the brief's "four widened stranded
arms" would have understated the surface by six:

| Group | Count | Where |
|---|---|---|
| file-local at the routed sites | 2 | `coordination/surface_resolver.py`, `missions/_read_path_resolver.py` — `except (ValueError, OSError)` → `except (MissionMetaReadError, ValueError, OSError)` (verified in the branch diff) |
| **stranded** arms on the caller chain | 4 | `cli/commands/agent/`: `mission_setup_plan.py`, `mission_record_analysis.py`, `mission_finalize.py`, `mission_check_prerequisites.py` — this is the brief's set |
| **degrade-site** handlers | 4 | `mission_runtime/resolution.py` ×3, `upgrade/feature_meta.py` |

**Correction to the brief on the floors.** It says *"the two floors moving
(`ROUTED_LOAD_META_FLOOR` 126→127)"*. Measured
`git show 96494e5ec:tests/architectural/test_inline_meta_read_gate.py` against HEAD:

| Constant | `96494e5ec` | HEAD | |
|---|---|---|---|
| `ROUTED_LOAD_META_FLOOR` | 126 | **127** | moved |
| `ROUTED_LOAD_META_FLOOR_MARGIN` | 4 | 4 | — |
| `INLINE_META_READ_FLOOR` | 7 | 7 | re-derived, **held** |
| `FLOOR_MARGIN` | 2 | 2 | — |

Both floors were re-derived; **one** moved. The entry says so rather than repeating "two".

## §4 `F3` — the sweep is now CI-exercised

`tests/architectural/test_sweep_degrade_arms_instrument.py`, 8 tests, in the always-on arch pole
(`arch-adversarial`, `arch_shard_1`, verified by the analyzer in §2.5).

**The gate deliberately does not rest on `--self-check`.** That flag shells out to
`git archive f1681bf1 src`; `actions/checkout` defaults to `fetch-depth: 1` and the arch pole
does not override it, so on a CI runner the control rev is usually absent — and after a squash
merge it may never exist on `main` again. Pinning the gate there would be a landmine of exactly
the class `DIR-041` forbids. So:

* `--self-check` runs when the rev **is** present (it is locally — **8 passed, 0 skipped**) and
  **skips with the reason named** when it is not;
* the calibration that always runs in CI is a **synthetic positive control** (one stranded arm on
  a 3-module chain must be reported as exactly that hazard — identity, not count), its
  **negative control** (the same chain, arm widened ⇒ CLEAN), a **live-tree CLEAN** assertion
  over the mission's four routed seeds, and an anti-vacuity assert on the live tree that the
  typed error escapes **more** frames than the seeds themselves (measured **65** raising frames
  from 4 seeds), so a call graph resolving no edges cannot report CLEAN vacuously;
* the recorded `--expect` control string is pinned at **6** locations, because an emptied
  `CONTROL_EXPECT` silently degrades the script's own comparison into "expect clean".

`--self-check`'s assertion is scoped to the **calibration**, not the live verdict: it replays the
control and *then* sweeps the working tree, so its exit status is `1` whenever the live tree has
a hazard. Asserting `status == 0` made a live-tree finding read as *"the known answer did not
reproduce"* — a failure for the wrong reason. Found by the injection control below, fixed before
committing.

**Load-bearing, proved by injection.** Narrowing one of WP02's four widened arms
(`mission_finalize.py:298`, `except (MissionMetaReadError, ValueError, ActionContextError)` →
`except (ValueError, ActionContextError)`) took the live test red and named the arm exactly:

```
  mission_finalize.py:298  (try at :290)
    except (ValueError, ActionContextError) as detection_error:
    in      : specify_cli.cli.commands.agent.mission_finalize._resolve_mission_slug
    catches : ['ActionContextError', 'ValueError']  (no RuntimeError -> strands MissionMetaReadError)
    chain   : _find_feature_directory -> resolve_handle_to_read_path -> read_primary_meta
```

Restored from a byte copy taken before the injection; `git status --short src/` empty afterwards.
No `reset --hard`, no `checkout` of a directory.

The four asserted seeds are **dotted qualnames** (a bare `--seed _resolve_mission_id` resolves to
`mission_runtime.resolution._resolve_mission_id`, a different function on a different chain).
The **F11** chain is deliberately **excluded and named as excluded**, with a test pinning that:
WP04 measured `safe_commit_cmd.py:306` leaking identically at `96494e5ec`, at pre-routing
`45b278823` and at HEAD, so sweeping it here would pin a known-open finding as this gate's
expected answer and turn its eventual fix into a false red.

## §5 Re-derived counts (T049)

All from `scripts/verify_meta_routing_manifest_3162.py`, `exit=0`, `VERDICT: PASS`.

```
TREE measured : /home/jeroennouws/dev/sk-missions/3162
SRC_ROOT      : /home/jeroennouws/dev/sk-missions/3162/src
PYTHONPATH    : <unset>
freeze-check  : off (band-only verdict)
== §4 LIVE COUNTS (gate's own AST scanners) ==
  INPUT .py files walked: 1199
  ROUTED live (AST walk): 130
  INLINE live (AST walk): 7
  const INLINE_META_READ_FLOOR = 7
  const FLOOR_MARGIN = 2
  const ROUTED_LOAD_META_FLOOR = 127
  const ROUTED_LOAD_META_FLOOR_MARGIN = 4
  DERIVED routed band: [128, 131] (two-sided; 127 is RED)
== BOUNDS ==
  routed 130 in [128, 131]: OK
  inline 7 <= 7 and gap <= 2: OK
```

### 5.1 Routed — 130, with its input count and its probe control

**1199** `.py` files walked in, **130** routed calls out. The naive-grep control, printed by the
same tool, shows which probe is the right one:

```
SNAPSHOT routed naive regex (grep -rn 'load_meta' src): got 307
  (DRIFTED from freeze-point 296; not graded — pass --freeze-check to grade)
SNAPSHOT routed AST authoritative: got 130 (DRIFTED from freeze-point 129)
```

The naive regex answers **307** where the answer is **130**. Both snapshots drift **by design**
as the mission progresses and are graded only under `--freeze-check`; the graded verdict is the
band line.

### 5.2 The floor was READ, not copied

`ROUTED_LOAD_META_FLOOR = 127` and `ROUTED_LOAD_META_FLOOR_MARGIN = 4` were read off
`tests/architectural/test_inline_meta_read_gate.py` **on this tree** by the tool above, and the
band `[128, 131]` is derived from the printed values. `plan.md`'s `127` / `[128,131]` are
rule-derived and its own `[UNVERIFIED]` list forbids copying them; they were not copied. That
they agree with the measurement is a coincidence worth stating, not the source.

### 5.3 The bound is two-sided; **127 is RED**

`test_routed_load_meta_floor` asserts **three** things. **Citation correction:** the WP08 prompt
cites the `def` at `:1084` and the asserts at `:1092` / `:1097` / `:1101`. Post-WP06 the real
lines are:

| Line | Assertion |
|---|---|
| `:1305` | `def test_routed_load_meta_floor()` |
| `:1313` | `assert len(routed) >= ROUTED_LOAD_META_FLOOR` |
| `:1318` | `assert len(routed) > ROUTED_LOAD_META_FLOOR` — **strict**, explicitly anti-vacuous |
| `:1322` | `assert len(routed) - ROUTED_LOAD_META_FLOOR <= ROUTED_LOAD_META_FLOOR_MARGIN` |

The middle one is strict, so at floor **127** the admissible band is `[128, 131]` and **127 is
RED**. A fold that *collapses* two routed calls into one therefore reds the gate **downward** —
the failure mode three prior floor mismatches in this programme came from.

### 5.4 Inline — the two deltas, separately, now MEASURED as a 2×2

**Correction, second pass.** The earlier version of this section reported the code delta as **0**
and argued it from `INLINE_META_READ_FLOOR` being unchanged at 7. That argument restates the floor;
it does not measure the delta. Measured properly, **both deltas are non-zero and they cancel** —
which is the exact reason `SC-006` mandates two numbers rather than one.

The measurement is a 2×2: the gate's inline scanner at each of two revisions, run over each of two
`src` trees, so the predicate can be varied with the tree held fixed and vice versa.
`scripts/verify_meta_fail_closed_integration_3162.py` prints it:

```
  CONTROL known answer: corrected(HEAD,HEAD)=7 vs live tree=7 -> PASS
                    tree=BASE  tree=HEAD
  predicate=BASE            7          7
  predicate=HEAD            8          7
  WIDENING delta (predicate BASE->HEAD, tree fixed at BASE): +1
  CODE     delta (tree BASE->HEAD, predicate fixed at HEAD): -1
```

* **widening delta = `+1`** (sites the predicate change adds at a fixed tree). WP06's one-call-hop
  widening exposes exactly one further real site, named rather than counted:
  `src/specify_cli/git/ref_advance.py::_meta_change_is_vcs_lock_only`. At `96494e5ec` that function
  read `worktree_text = meta_path.read_text(encoding="utf-8")` (`:244`) and parsed it one hop away
  via `worktree_meta = _parse_meta_object(worktree_text)` (`:247`) — invisible to the narrow
  predicate, a genuine inline meta read to the widened one.
* **code delta = `−1`** (sites the source change adds at a fixed predicate). The mission **routes
  that same site**: at HEAD `ref_advance.py:247` is
  `worktree_meta = load_meta_fail_closed(meta_path.parent)`. Verified by count, not by reading the
  diff: `grep -c 'load_meta_fail_closed('` on `ref_advance.py` is **0** at `96494e5ec` and **1** at
  HEAD.

So the same one-line edit is simultaneously the mission's **single net routed `+1`** (`129 → 130`)
and the inline census's **`−1`**. One number could not have distinguished "the widening found a real
site" from "a new unrouted read landed"; two numbers show it was the former, and that the mission
then closed it.

**No inline floor was raised**, so `SC-006`'s argued-raise obligation does not arise: live inline
**7**, `INLINE_META_READ_FLOOR` **7**, `FLOOR_MARGIN` **2**, gap **0**, unchanged between
`96494e5ec` and HEAD (§3's table). `test_allowlist_matches_floor` is an equality against
`INLINE_META_READ_FLOOR` and is green (§13).

**The control this measurement needed, and the trap it caught.** A naive 2×2 over `git archive`
copies reports **8** where the real tree reports **7**, in every cell.
`test_inline_meta_read_gate._rel` (`:424`) makes paths relative to `_REPO_ROOT`, derived from the
**gate file's own** `__file__` — *not* from the `src_root` argument it was passed — and
`EXCLUDED_REL_PATHS` (`:75`) is matched against that value. On a relocated tree the exclusion
therefore stops matching and `src/specify_cli/mission_metadata.py` (the canonical reader's own
internals) re-enters the census. This is the same `_rel()` cross-tree trap already folded into the
ledger via `#3241`, surfacing here in a second gate surface. The script restates the exclusion by
**path suffix**, which survives relocation, and prints the known-answer control above
(`corrected(HEAD,HEAD)` must equal the real tree's live figure) so the corrected probe is shown to
be right rather than asserted to be.

### 5.5 The ledger row delta — `12 → 0`

```
grep -c 'pending-batch-a' test_meta_fail_closed_full_census_contract.py: 1 (candidates in)
legend/prose hits dropped: 1 at line(s) [185]
ledger ROWS out: 0  (convention: ledger row)
CALL SITES out: 0  (convention: call site; expanded from row counts)
```

The `:185` legend-line exclusion is shown as the control: **1 candidate in, 1 legend hit
dropped, 0 rows out.** Baseline was **12** rows / **13** call sites (the branch diff of
`_ACCOUNTED_SITES` deletes exactly those 12 rows). **`12 → 0`, no survivors.**

### 5.6 `scripts/verify_meta_fail_closed_integration_3162.py` — CREATED (`c6b10791b`)

**Correction, second pass.** The earlier version of this section recorded the script as
*"deliberately NOT created"*, arguing that `scripts/verify_meta_routing_manifest_3162.py` already
was that script and that authoring a second one would violate the `NFR-002` clause T049 step 9 itself
cites. **Half of that argument was right and half of it was wrong.** Right: `NFR-002`'s kept clause
does forbid a second predicate answering one question, and a second *counter* must not be written.
Wrong: a script that **composes** the existing counter is not a second counter, and refusing to write
one left this WP's entire declared `owned_files` surface empty — which `create_intent` suppresses
(`src/specify_cli/ownership/validation.py:411-433`) and no review or accept gate re-checks, so the
absence was invisible to tooling and the deviation cost more than it saved.

The script now exists and **authors no second way to count**. Every count delegates to
WP01's verifier (`gate_constants`, `routed_band`, `ledger_pending_rows`, `pending_grep_lines`,
`legend_lines`, `python_files`, `check_bounds`, `import_gate`) and to the gate's own AST scanners
(`scan_routed_load_meta_calls`, `scan_inline_meta_reads`). It adds only what WP01's verifier does not
report: `SC-006`'s two deltas separated, and the `_rel()` relocation control (§5.4).

Its verbatim output, `exit=0`:

```
==============================================================================
verify_meta_fail_closed_integration_3162 — mission meta-fail-closed-3162-01KZ7FSQ
==============================================================================
TREE measured : /home/jeroennouws/dev/sk-missions/3162
SRC_ROOT      : /home/jeroennouws/dev/sk-missions/3162/src
PYTHONPATH    : <unset>
sys.executable: /home/jeroennouws/dev/sk-missions/3162/.venv/bin/python
baseline ref  : 96494e5ec (git merge-base HEAD main)
== LIVE COUNTS (the gate's own AST scanners; no second predicate) ==
  INPUT .py files walked        : 1199
  ROUTED live (AST walk)        : 130
  INLINE live, exclusion by suffix: 7
  INLINE live, gate's own _rel()  : 7
  const INLINE_META_READ_FLOOR = 7
  const FLOOR_MARGIN = 2
  const ROUTED_LOAD_META_FLOOR = 127
  const ROUTED_LOAD_META_FLOOR_MARGIN = 4
  DERIVED routed band           : [128, 131] (two-sided; 127 is RED)
== LEDGER `pending-batch-a` ROWS (baseline was 12 rows / 13 candidates) ==
  grep -c 'pending-batch-a' candidates in : 1
  legend/prose hits dropped              : 1 at line(s) [185]
  ledger ROWS out                        : 0
  DELTA                                  : 12 -> 0
== SC-006 — the TWO deltas, measured as a 2x2 (predicate x tree) ==
  control: shared helper tests/architectural/_ratchet_keys.py changed in-branch? no (byte-identical; sharing it is sound)
  CONTROL known answer: corrected(HEAD,HEAD)=7 vs live tree=7 -> PASS
                    tree=BASE  tree=HEAD
  predicate=BASE            7          7
  predicate=HEAD            8          7
  WIDENING delta (predicate BASE->HEAD, tree fixed at BASE): +1
  CODE     delta (tree BASE->HEAD, predicate fixed at HEAD): -1
  Reported as TWO numbers: one cannot distinguish 'the widening found a
  real site' from 'a new unrouted read landed'. They cancel here.
== BOUNDS ==
  routed 130 in [128, 131]: OK
  inline 7 <= 7 and gap <= 2: OK
==============================================================================
VERDICT: PASS
==============================================================================
```

Note the `INLINE live, gate's own _rel()` line reads **7** here because the measured tree **is** the
script's own repository root, so `_rel` resolves correctly. Point it at a relocated tree and that line
diverges from the suffix-corrected line, which is what makes the trap visible rather than silent.

Lint, quoted:

```
$ .venv/bin/ruff check scripts/verify_meta_fail_closed_integration_3162.py
All checks passed!
exit=0
$ .venv/bin/ruff check --select C901 --no-cache scripts/verify_meta_fail_closed_integration_3162.py
All checks passed!
exit=0
$ grep -c '# noqa\|# type: ignore' scripts/verify_meta_fail_closed_integration_3162.py
0
```

`ruff format` was never run. The two regeneration commands for §5 are:

```bash
.venv/bin/python scripts/verify_meta_routing_manifest_3162.py
.venv/bin/python scripts/verify_meta_fail_closed_integration_3162.py
```

## §6 The architectural cone — GREEN

Documented parallel form. `--dist loadfile`, never bare `--dist load`.

```bash
PWHEADLESS=1 timeout 7200 .venv/bin/python -m pytest tests/architectural -ra \
  -n 6 --dist loadfile -p no:cacheprovider > <scratch>/cone_arch2.txt 2>&1
```

| | |
|---|---|
| rootdir (control) | `/home/jeroennouws/dev/sk-missions/3162`, `configfile: pytest.ini` |
| selected | `6 workers [1703 items]` |
| result | `1699 passed, 2 skipped, 2 xfailed, 1 warning in 709.78s (0:11:49)` |
| `exit=` | **0** |
| elapsed / budget | **710 s** / 7200 s — no `exit=124`, no killed run |
| `grep -c '^ERROR tests/'` | **0** |
| `grep -c '^FAILED '` | **0** |

**Collection equivalence.** Serial `pytest tests/architectural --collect-only -q` reports
`1703 tests collected in 50.75s`, `exit=0`. The parallel run collected `[1703 items]` and
accounts for all of them: `1699 + 2 + 2 = 1703`. The worker split did not move the number.

**Workers = 6, not `-n auto`.** `nproc` = 16, and 16 concurrent workers each spawning further
`--collect-only` subprocesses is a memory risk on this host; 6 was used and is printed rather
than left implicit. This narrows nothing — `--dist loadfile` keeps every file on one worker
either way.

**No directory was run `-n0`.** Applying the documented criterion (binds an OS-global resource:
a real TCP port or a singleton daemon), `tests/architectural` binds neither; the only
serial-only suite named in `docs/development/testing-parallel.md:82-93` is
`tests/sync/test_orphan_sweep.py` (ports 9400–9449), which is outside this selection.

The 2 skips and 2 xfails are pre-existing and self-documenting, both unrelated to this mission:

```
SKIPPED [1] tests/architectural/test_compat_shims.py:96: got empty parameter set for (adapter_path)
SKIPPED [1] tests/architectural/test_compat_shims.py:104: got empty parameter set for (adapter_path)
XFAIL tests/architectural/test_egress_consent_boundary.py::...[injected-transport-positional-url-name]
XFAIL tests/architectural/test_egress_consent_boundary.py::...[injected-transport-positional-non-url-name]
      — `#3113`, FR-015 non-adoption decision, pinned red deliberately
```

**Remaining failures attributed against `96494e5ec`: none. The cone has zero failures and zero
errors.**

### 6.1 The five test files touched outside the cone

```
tests/next/test_wp02_row04_planner_fail_closed.py
tests/runtime/test_wp02_row05_bridge_io_fail_closed.py
tests/mission_runtime/test_wp04_routed_call_counts.py
tests/mission_runtime/test_wp04_sc007_guard_and_handler_contract.py
tests/specify_cli/context/test_wp03_row08_resolver_fail_closed.py
```

`28 passed in 55.41s`, `exit=0`, `grep -c '^ERROR tests/'` = **0**.

## §7 Static gates (`SC-017`)

**`ruff check`** over CI's exact lint scope (`ruff check src tests`):

```
$ .venv/bin/ruff check src tests
All checks passed!
exit=0
```

`ruff format` was **never** run. No `# noqa`, no `# type: ignore`, no per-file ignore was added.
The three `# golden-count: cardinality-is-contract` annotations in §2.3 are a *classification*
escape hatch the gate itself documents and requires a per-site rationale for, not a lint
suppression — each carries one.

**`mypy --strict` — no longer `[UNVERIFIED]`; MEASURED on both sides.** The earlier version of this
section argued the result from byte-identity of the input and flagged itself `[UNVERIFIED]`. Two
things about it were wrong, and both are corrected here.

**Correction 1 — "WP08 changed no file under `src/`" is stale.** It was true when written; it is not
true now. `24a5e62a5` touches `src/specify_cli/cli/commands/agent/mission_check_prerequisites.py`
(one token). It is the only `src/` file in WP08's commit range, verified per-commit:

```
68643e23a  (no src/ files)     02831c055  (no src/ files)
ec3cd37e8  (no src/ files)     8ed6a1258  (no src/ files)
928139858  (no src/ files)     24a5e62a5  src/specify_cli/cli/commands/agent/mission_check_prerequisites.py
9db18639c  (no src/ files)     be01cbbf3  (no src/ files)
6bfb6fbc3  (no src/ files)     c6b10791b  (no src/ files)
```

That edit exists **because** the full-suite measurement found the mission's one new `mypy` error:
WP02 widened the `except` tuple at `mission_check_prerequisites.py:245` to catch
`MissionMetaReadError` but left the callee's parameter annotation at `ValueError |
ActionContextError`. The callee only does `str(detection_error)`, so the fix is behaviour-neutral.

**The delta is `0 → 1 → 0`, measured on both sides under CI's own invocation** (`ci-quality.yml:849`,
`mypy --strict src/specify_cli src/charter src/doctrine`; note CI runs it as
*"[INFO] Run mypy report (advisory)"*):

```
$ cd /home/jeroennouws/dev/sk-missions/base-96494e5ec && mypy --strict src/specify_cli src/charter src/doctrine
Success: no issues found in 1130 source files
exit=0
$ cd /home/jeroennouws/dev/sk-missions/3162 && mypy --strict src/specify_cli src/charter src/doctrine
Success: no issues found in 1130 source files
exit=0
```

Baseline-worktree identity control: `git -C base-96494e5ec rev-parse HEAD` →
`96494e5ec4df2fa2f923a90eb7b7985aa0386b84`. Same invocation, same **1130** source files both sides,
so the delta is against a clean floor rather than a noisy one. No suppression was added to reach it.

**Correction 2 — the briefing's "known pre-existing findings" list does not reproduce under CI's
invocation, and the earlier version of this section repeated it as though it did.** Base measures
**zero** under package scope. The findings are real but **invocation-dependent**, which is worth
stating precisely because "confirmed pre-existing, do not fix" is the right call either way:

```
$ mypy --strict src/specify_cli/cli/commands/merge_driver.py          # single-file scope, HEAD
src/specify_cli/cli/commands/merge_driver.py:645: error: Returning Any from function declared to return "dict[str, Any]"  [no-any-return]
Found 1 error in 1 file (checked 1 source file)

$ mypy --strict src/specify_cli/cli/commands/merge_driver.py          # single-file scope, BASE 96494e5ec
src/specify_cli/cli/commands/merge_driver.py:630: error: Returning Any from function declared to return "dict[str, Any]"  [no-any-return]
Found 1 error in 1 file (checked 1 source file)
```

Both report the **same source line**, `return AcceptanceMatrix.from_dict(merged_document).to_dict()`,
at `:630` (base) and `:645` (HEAD) — line-shifted only, so it is **pre-existing, proved rather than
asserted**. Under package scope `mypy` resolves `to_dict()`'s real return type through the package;
under single-file scope `follow_imports = "skip"` (`pyproject.toml:299`) erases it to `Any`. Same for
F12's `no-any-return` family. **Not fixed and not suppressed here**, per the standing direction.

## §8 WP03 review folds

1. `tests/specify_cli/context/test_wp03_row08_resolver_fail_closed.py` cited
   `TestResolveContext.test_missing_meta_json_raises`. The **class** does exist (`test_resolver.py:125`);
   what does not exist is that method *inside* it. Re-derived: the
   method is at `tests/specify_cli/context/test_resolver.py:251`, inside
   **`TestResolveContextErrors`** (class at `:215`; verified by listing every `class` and `def`
   between `:215` and `:255` — no intervening class). Corrected, with the correction recorded so
   the wrong name does not read as a rename.
2. `safe_commit_cmd.py:14` → **`:306`**. Re-derived:
   `grep -n 'except (FileNotFoundError, ValueError)'` returns a single match at `306`, inside
   `_resolve_mission_aware_target`. `:14` is an import line.
3. `resolver.py:78` → **`:86`**. Re-derived: `:78` is inside the explanatory comment block;
   `data = load_meta_fail_closed(...)` is `:83`, `if data is None:` `:84`,
   `raise MissingIdentityError(msg)` **`:86`**.
4. The `contextlib.suppress` probe's on-chain calibration was the tautology
   `expected 0, got 0 -> PASS` — a line a probe that inspected **nothing** produces identically.
   WP03's reviewer supplied the missing anti-vacuity figure (**16** arms inspected on-chain) and
   a positive control (**16 → 17**, correctly FAILED). **Both were re-derived independently**,
   reusing the committed sweep's own `CallGraph` / `STRANDABLE` vocabulary:

```
on-chain funcs (transitive callers reaching a seed) : 18
suppress() arms inspected on-chain                  : 16
TOTAL suppress-with-STRANDABLE sites in src/         : 48   <- reproduces the recorded 48
ON-CHAIN naming a STRANDABLE exception               : 0
```

All 16 are interview/prompt guards (`charter/interview.py` ×3, `cli/commands/lifecycle.py` ×3,
`missions/plan/plan_interview.py` ×5, `missions/plan/specify_interview.py` ×5); **none** names a
`STRANDABLE` exception, which is *why* the strandable on-chain count is 0 rather than the probe
being blind. Positive control on a `git archive HEAD src` scratch tree (working tree never
touched; `git status --short src/` empty afterwards):

```
                                   HEAD   INJECTED
suppress() arms inspected on-chain   16 ->   17
TOTAL suppress-with-STRANDABLE       48 ->   49
ON-CHAIN naming a STRANDABLE          0 ->    1   <- verdict flips CLEAN -> HAZARD
    resolver.py:243  suppress('ValueError',)  in specify_cli.context.resolver.resolve_context
```

## §9 Commits

```
02831c055 fix(WP08): refreeze integration-tests-next's E3 node-id manifest — coverage GAINED, +6/-0
6bfb6fbc3 fix(WP08): close a FIFTH mission-introduced arch gate red — golden-count regrowth
9db18639c docs(WP08): fold WP03's review corrections — three citations and the missing anti-vacuity figure
928139858 docs(WP08): close ledger F2 — record the breaking exception-type change in the CHANGELOG
ec3cd37e8 test(WP08): close ledger F3 — put the chain-local degrade-arm sweep under a CI gate
68643e23a fix(WP08): close ledger F10 — put WP02's two new test files in a gate that runs them
```

## §10 One process incident, recorded

The session scratchpad was wiped mid-WP, destroying every raw redirect file taken before it (the
red-first capture among them). The numbers survived **only** because they had been quoted
verbatim into commit messages as each fix landed. Everything re-derivable was re-taken after the
wipe (§2.5's analyzer run, §5, §6, §8). The red-first text in §2.1 is quoted from
`68643e23a`'s commit message, captured at the time of the run, and its raw file no longer exists.
A first whole-cone run was also killed by an unrelated interruption; that measurement was
discarded as **neither pass nor fail** and the cone was re-run from scratch (§6), not reported
from the partial.

---

# Second pass (2026-08-06) — T047, T048, T049's re-verification, T050's discharge, T051

Everything from here down was measured on the second pass, after the review rewind that reset
T047–T052 to `planned`. **Baseline ref remains `96494e5ec`** (`git merge-base HEAD main`);
`98198e980` is not used anywhere. **Every count is `pre-rebase (base 96494e5ec)`** — see §0.

## §11 T047 — the `C-007` sweep-window check, sampled four times

### 11.1 `PATH` first, because the global binary is stale

```
$ export PATH=/home/jeroennouws/dev/sk-missions/3162/.venv/bin:$PATH; command -v spec-kitty
/home/jeroennouws/dev/sk-missions/3162/.venv/bin/spec-kitty
exit=0
$ which -a spec-kitty
/home/jeroennouws/dev/sk-missions/3162/.venv/bin/spec-kitty
/home/jeroennouws/.local/bin/spec-kitty
```

Resolves inside the tree's own `.venv/bin`. `which -a` shows the stale `~/.local/bin` install is
still on `PATH` but now **second**, which is the point of the fix — it is present and losing, not
absent.

### 11.2 Four timestamped samples, spaced 35 s, ALL quoted including the empty ones

The prompt requires ≥3 spaced ≥30 s apart. Four were taken, spanning **105 s**
(`19:47:45` → `19:49:30`). Verbatim:

```
=== SAMPLE 1 ===                          === SAMPLE 3 ===
2026-08-06T19:47:45+02:00                 2026-08-06T19:48:55+02:00
-- pgrep -af 'run_sync[_]daemon' --       -- pgrep -af 'run_sync[_]daemon' --
(no match, pgrep exit=1)                  (no match, pgrep exit=1)
-- pgrep -af 'pytest tests/(sync|cli)' -- -- pgrep -af 'pytest tests/(sync|cli)' --
(no match, pgrep exit=1)                  (no match, pgrep exit=1)
-- ss -ltn sport 9400-9449 --             -- ss -ltn sport 9400-9449 --
State Recv-Q Send-Q Local Address:Port    State Recv-Q Send-Q Local Address:Port
   (header only — no listener)               (header only — no listener)

=== SAMPLE 2 ===                          === SAMPLE 4 ===
2026-08-06T19:48:20+02:00                 2026-08-06T19:49:30+02:00
-- pgrep -af 'run_sync[_]daemon' --       -- pgrep -af 'run_sync[_]daemon' --
(no match, pgrep exit=1)                  (no match, pgrep exit=1)
-- pgrep -af 'pytest tests/(sync|cli)' -- -- pgrep -af 'pytest tests/(sync|cli)' --
(no match, pgrep exit=1)                  (no match, pgrep exit=1)
-- ss -ltn sport 9400-9449 --             -- ss -ltn sport 9400-9449 --
State Recv-Q Send-Q Local Address:Port    State Recv-Q Send-Q Local Address:Port
   (header only — no listener)               (header only — no listener)
```

The `ss` probe is an addition to the prompt's two `pgrep`s, and it is the one that would catch
`F17`'s recorded failure mode — a daemon **leaked onto port 9400 and surviving into the next pytest
pass**, which no `pgrep` for `pytest` can see because the leaked process is not a pytest. All four
samples show no listener in `9400–9449`.

**A self-match caveat, recorded because it nearly produced a false positive.** A bare
`pgrep -af 'pytest'` matches the *invoking shell's own command line* when the pattern appears in it,
and it did: `pgrep -af 'pytest'` returned pid `501311`, which was the `bash -c` wrapper running the
`pgrep` itself. The four samples above are not affected — `pytest tests/(sync|cli)` is an ERE whose
parentheses are a group, so the literal text `pytest tests/(sync|cli)` in the shell's own cmdline
does **not** match it. Anyone re-running this must check for that artifact before reading a hit as a
real sweep.

### 11.3 The sibling check, with its gaps named explicitly

`~/dev/sk-missions/3167` is the sibling named in `plan.md` IC-08. It is **present**, and was
inspected:

```
$ git -C ~/dev/sk-missions/3167 rev-parse --abbrev-ref HEAD
fix/tooling-defects-3212-3221-3227
$ git -C ~/dev/sk-missions/3167 log --oneline -1
d0ed802cc docs(landing): changelog entry for the `#3086` merged-coordination-mission fix
$ find ~/dev/sk-missions/3167 -maxdepth 2 -name '.pytest_cache' -printf '%TY-%Tm-%Td %TH:%TM\n'
2026-08-05 19:12
$ find ~/dev/sk-missions/3167/kitty-specs -name status.events.jsonl -printf '%TY-%Tm-%Td %TH:%TM  %p\n' | sort -r | head -2
2026-08-06 01:46  kitty-specs/review-verdict-write-integrity-01KZ1CGF/status.events.jsonl
2026-08-06 01:46  kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/status.events.jsonl
```

Its most recent `pytest` activity is **~24 h stale** (`.pytest_cache` at `2026-08-05 19:12`) and its
most recent mission event ~18 h stale, against a sample time of `2026-08-06 19:47`. There is no lock
file modified in the last 2 h. Also inspected: the full `pgrep -af python` process list — 20
processes, **none** from any `sk-missions` tree. The live ones are a `work-coordinator` broker and
dashboards, `mempalace` MCP servers, WebSocket probes belonging to a `spec-kitty-saas` session (ports
8733–8736), and a Django test run in `wt-ws-bounded-715`. None binds `9400–9449`.

**What I could NOT inspect, named rather than glossed:**

1. **There is no advisory lock for the sweep window at all.** The `C-007` handshake is *only* process
   inspection — no lock file, no mission-event field, and no CLI command reserves or reports the
   `tests/sync` / `tests/cli` window. So "no sweep running" can never be more than a sample; a
   sibling that starts one microsecond after sample 4 is undetectable by construction. This is the
   structural reason the prompt demands spaced samples instead of one, and it is a gap in the
   *mechanism*, not in this measurement.
2. **A queued-but-not-started sweep is invisible.** Nothing enumerates pending work, so a sibling
   agent about to run `tests/sync` looks identical to one that never will.
3. **Processes of other users** were not enumerated; only this UID's. Nothing suggests another user
   on this host, but it was not proved.

### 11.4 The negative-need argument, printed side by side so disjointness is checkable

The 14 cone directories, all verified present on this tree, against the 2 barred names:

```
CONE (14, this mission's selection)          BARRED (2, C-007)
PRESENT  tests/specify_cli                   PRESENT(but BARRED)  tests/sync
PRESENT  tests/mission_runtime               PRESENT(but BARRED)  tests/cli
PRESENT  tests/regression
PRESENT  tests/merge
PRESENT  tests/architectural
PRESENT  tests/integration
PRESENT  tests/missions
PRESENT  tests/runtime
PRESENT  tests/next
PRESENT  tests/context
PRESENT  tests/status
PRESENT  tests/upgrade
PRESENT  tests/coordination
PRESENT  tests/lanes
```

The two lists are **disjoint**: neither `tests/sync` nor `tests/cli` is among the fourteen, so this
mission never needs the window. Both barred directories exist, so their absence from the cone is a
selection decision rather than an accident of the tree.

### 11.5 The `tests/specify_cli/cli/commands/` vs `tests/cli` distinction

`tests/specify_cli/cli/commands/` is **inside** `tests/specify_cli` and is **not** the barred
top-level `tests/cli`; the census conflated them. `SC-008`'s byte-identical file lives under the
former, verified as the only such path on the tree:

```
$ find tests -name test_row_aware_merge_driver.py
tests/specify_cli/cli/commands/test_row_aware_merge_driver.py
```

This matters beyond pedantry: `WP04`'s risk 8 calls it `tests/merge/test_row_aware_merge_driver.py`,
which does not exist — and a `git diff --stat` against a non-existent path prints nothing and would
read as a **false green**. See §12.4, where the control for that is shown.

## §12 T048 — reinstall FIRST, then re-capture `SC-008`, `SC-010` and `SC-002`

### 12.1 The reinstall preceded every capture in this section

**The reinstall preceded the capture.** Quoted with its timestamp, so the ordering is checkable
against the capture timestamps rather than merely asserted:

```
$ .venv/bin/python -m pip install -e . --no-deps
Installing collected packages: spec-kitty-cli
  Attempting uninstall: spec-kitty-cli
    Found existing installation: spec-kitty-cli 3.2.6
    Uninstalling spec-kitty-cli-3.2.6:
      Successfully uninstalled spec-kitty-cli-3.2.6
Successfully installed spec-kitty-cli-3.2.6
exit=0
$ date -Is
2026-08-06T19:47:55+02:00
```

Every capture in §12 and §13 was taken **after** `19:47:55`.

**Why the order is load-bearing, in one sentence:** `src/specify_cli/lanes/merge.py:84` registers
`spec-kitty merge-driver-meta %O %A %B` for `pattern="kitty-specs/**/meta.json"` (`:85`), so
`merge_driver.py` runs as a **subprocess** and WP05's edit to it is invisible to the marker until the
package is reinstalled — making a pre-reinstall capture a stale-install false red or false green,
both worthless.

**Recorded for completeness:** ledger `F20` argues the reinstall is unnecessary *by construction*,
because `_editable_impl_spec_kitty_cli.pth` contains a plain path entry and therefore reads live
files. That argument is sound for **imports**, and it is exactly why no pre-reinstall/post-reinstall
disagreement appeared here. It does **not** cover the console-script entry points that a subprocess
invocation resolves, which is the surface the reinstall protects. The reinstall was performed and is
reported as performed; no capture disagreed across it.

### 12.2 The marker — `SC-008`, redirected, `-ra`

```bash
timeout 1800 .venv/bin/python -m pytest \
  tests/regression/test_issue_2804_merge_resets_gate_artifacts.py -ra \
  > <scratch>/wp08_2804.txt 2>&1; echo "exit=$?"
```

| | |
|---|---|
| rootdir (control) | `/home/jeroennouws/dev/sk-missions/3162`, `configfile: pytest.ini` |
| selected | `collected 2 items` |
| result, verbatim | `========================= 2 passed in 75.60s (0:01:15) =========================` |
| `exit=` | **0** |
| elapsed / budget | **77 s** / 1800 s — no `exit=124`, no killed run |
| `grep -c '^ERROR tests/'` | **0** |
| `grep -c '^FAILED '` | **0** |
| `-ra` short summary | empty (nothing to report) |

`^ERROR tests/` was counted, **not** `^ERROR `.

### 12.3 Both re-pinned assertions, named individually — after OPENING the file

**Citation correction, and it is a substantive one.** The prompt cites the test at `:420` with its
two assertions at `:482` (`overall_verdict`) and `:489`
(`SCAFFOLD_TODO_MARKER not in json.dumps(post_matrix)`). Opening the file shows **all three line
numbers are stale and the second assertion is no longer that assertion at all.** WP07 (`FR-009`)
refactored both clauses into ONE shared predicate:

| What | Real location | Assertion |
|---|---|---|
| the marker test | `:575` `def test_merge_resets_filled_gate_artifacts_to_placeholder` | calls the shared predicate at `:660` |
| the shared predicate | `:321` `def _assert_2804_acceptance_contract(post_matrix)` | — |
| **assertion 1** | **`:344`** | `assert verdict in ADMISSIBLE_MERGED_VERDICTS` — the `overall_verdict` clause |
| **assertion 2** | **`:351`** | `assert ACCEPTED_EVIDENCE_HANDLE in json.dumps(post_matrix)` — **evidence survival** |
| fixture self-control | `:342` | `_assert_evidence_handle_fixture_self_control()` |

Assertion 2 is **re-pinned, not deleted**, and the file says why at `:648-657`, quoted verbatim:

> *"Assertion 2 was `SCAFFOLD_TODO_MARKER not in json.dumps(post_matrix)`. It is RE-PINNED, NOT
> DELETED: under the row-union it is unsatisfiable BY DESIGN -- the union admits the scaffold row,
> whose `description` and `notes` ARE the marker (see PLACEHOLDER_ACCEPTANCE_MATRIX above). Measured
> through the reconciler, control first: CONTROL filled fixture contains marker? False / merged
> criterion_ids: ['AC-001', 'FR-001', 'FR-003'] / overall_verdict: pending / POST contains
> SCAFFOLD_TODO_MARKER? True. Its CONTENT is the real `#2804` contract, so it moves to evidence
> survival rather than being dropped."*

So a reviewer checking this WP against the prompt's `:482`/`:489` would find neither line and could
conclude the assertions had been dropped. They have not been; they are at `:344` and `:351` in a
shared predicate, and the one-assertion account the prompt warns against is structurally impossible
now because **both** clauses live in the single predicate that the falsifiability companion also
calls.

### 12.4 `SC-010`'s companion, in the same selection, on the defect's own fixture

`test_widened_2804_assertion_rejects_wrong_verdict` (`:736`) is the second of the two tests in the
`2 passed` above — same selection, same run.

**Its fixture is the defect's own shape**, confirmed by opening it rather than by trusting the name:

* the case under test is `_take_theirs_acceptance_document()` (`:692`) — *"the take-theirs /
  scaffold-clobber document … exactly the shape the pre-fix merge produced -- the mission branch's
  placeholder winning outright"*, built through the real `AcceptanceMatrix` so `overall_verdict` is
  **computed** (`pending`), not hand-asserted, *"and the accepted evidence handle is **absent**"*;
* the absence is asserted as a **precondition** at `:780`:
  `assert ACCEPTED_EVIDENCE_HANDLE not in json.dumps(take_theirs)`, with the message *"that absence
  IS the defect"*;
* the failure is pinned to the **right clause** at `:791`:
  `assert "assertion 2, evidence survival" in message`, and at `:800`
  `assert "assertion 1" not in message` — because `pending` is the defect's own signature and
  **must** be admitted by assertion 1;
* it carries a **positive twin** at `:767-772` (the row-union merged document passes the same shared
  predicate), so the negative is not vacuous;
* the `"fail"` case at `:810` is labelled in the source itself as a *"SECONDARY, EXPLICITLY
  INSUFFICIENT WITNESS"* which *"on its own proves NOTHING about `#2804`"*.

That is the correction `SC-010` exists for: not merely a disallowed value, but the defect's own
fixture, failing via the clause that carries falsifiability.

### 12.5 `SC-008`'s two diff obligations, with empty output shown as empty

```
$ git diff --stat 96494e5ec -- src/
 src/mission_runtime/resolution.py                  | 70 +++++++++++-----
 src/runtime/next/_internal_runtime/planner.py      | 12 +--
 src/runtime/next/runtime_bridge_io.py              | 12 +--
 src/specify_cli/bulk_edit/gate.py                  |  6 +-
 .../commands/agent/mission_check_prerequisites.py  | 11 ++-
 src/specify_cli/cli/commands/agent/mission_finalize.py         |  9 +-
 src/specify_cli/cli/commands/agent/mission_record_analysis.py  |  9 +-
 src/specify_cli/cli/commands/agent/mission_setup_plan.py       | 14 +++-
 src/specify_cli/cli/commands/implement.py          | 12 +++
 src/specify_cli/cli/commands/implement_cores.py    | 70 ++++++++++++++--
 src/specify_cli/cli/commands/merge_driver.py       | 19 ++++-
 src/specify_cli/context/resolver.py                | 24 ++++--
 src/specify_cli/coordination/surface_resolver.py   | 12 ++-
 src/specify_cli/core/paths.py                      | 28 +++++--
 src/specify_cli/decisions/service.py               | 34 +++++---
 src/specify_cli/git/ref_advance.py                 | 96 +++++++++++++++++++---
 src/specify_cli/missions/_read_path_resolver.py    | 24 ++++--
 src/specify_cli/missions/_resolve_planning_branch.py           | 35 +++++---
 src/specify_cli/upgrade/feature_meta.py            | 26 ++++--
 19 files changed, 412 insertions(+), 111 deletions(-)
exit=0
```

**Non-empty: 19 files, +412/−111.** Measured against the baseline ref `96494e5ec`, not against
`upstream/main`'s tip.

```
$ git diff --stat upstream/main -- tests/specify_cli/cli/commands/test_row_aware_merge_driver.py
<<< OUTPUT IS EMPTY — byte-identical to upstream/main >>>
exit=0

$ git diff --stat 96494e5ec -- tests/specify_cli/cli/commands/test_row_aware_merge_driver.py
<<< OUTPUT IS EMPTY — byte-identical to 96494e5ec >>>
```

Byte-identical against **both** refs. The second diff is an addition to the prompt's obligation: it
pins the file against the ref this WP actually attributes with, since `upstream/main` (`d0ed802cc`)
is 95 commits ahead and an emptiness there is a weaker statement.

**The control that makes an empty diff mean something.** A `git diff --stat` against a
**non-existent** path prints nothing and is indistinguishable from byte-identity — which is exactly
how `WP04`'s wrong path (`tests/merge/…`) would have read as a false green. So the path was proved to
exist:

```
$ ls -la tests/specify_cli/cli/commands/test_row_aware_merge_driver.py
-rw-r--r--. 1 jeroennouws jeroennouws 28442 Aug  5 00:54 tests/specify_cli/cli/commands/test_row_aware_merge_driver.py
$ git rev-parse --short upstream/main
d0ed802cc
```

28442 bytes, and the ref resolves. Both diffs are empty **because the contents match**, not because
the arguments were meaningless.

### 12.6 `SC-002` re-captured — positive control first, 12 lines per side

The probe is WP04's shape, rebuilt: **4 degrade sites × 3 shapes (malformed / absent / valid) = 12
cases**, standalone `python` (not `pytest`), which is the form ledger `F13` records as sound for
`PYTHONPATH`. Per `F13`'s strengthened rule, the control is the **imported module's own `__file__`**,
printed on every capture — not `rootdir`, which proves only where the config came from.

**POSITIVE CONTROL, QUOTED FIRST AND NON-EMPTY.** One handler deliberately broken in an **isolated
`git archive HEAD src` copy**, so the working tree was never dirtied. Pre-edit and post-edit lines
quoted:

```
$ sed -n '1134p' <isolated>/src/mission_runtime/resolution.py      # PRE-EDIT
    except MissionMetaReadError:
$ sed -n '1134p' <isolated>/src/mission_runtime/resolution.py      # POST-EDIT (injected)
    except TypeError:

$ diff <(grep '|' sc002_pre.txt) <(grep '|' sc002_poscontrol.txt)
7c7
< _resolve_mission_id|malformed|'legacy-wp08-sc002-degrade-probe-01KWP08S'
---
> _resolve_mission_id|malformed|!!RAISED MissionMetaReadError: Cannot read <tmp>/meta.json: Malformed JSON in <tmp>/meta.json: Expecting value: line 1 column 18 (char 17) — fail-closed (meta.json exists but is corrupt or unreadable)
diff exit=1
```

**Non-empty, `diff exit=1`** — the probe is sensitive to exactly the defect class `SC-002` exists to
catch. Restored from a byte copy taken **before** the injection, and the real tree verified untouched:

```
$ sed -n '1134p' <isolated>/src/mission_runtime/resolution.py      # RESTORED
    except MissionMetaReadError:
$ git status --short src/
<<< EMPTY >>>
```

No `reset --hard`, no `checkout` of a directory, no `clean`, no `stash`.

**The captures, with the tree each number came from printed by the probe itself:**

```
sc002_pre.txt  : RESOLVED mission_runtime.resolution = <scratch>/head_src/src/mission_runtime/resolution.py
                 RESOLVED specify_cli.upgrade.feature_meta = <scratch>/head_src/src/specify_cli/upgrade/feature_meta.py
sc002_post.txt : RESOLVED mission_runtime.resolution = /home/jeroennouws/dev/sk-missions/3162/src/mission_runtime/resolution.py
                 RESOLVED specify_cli.upgrade.feature_meta = /home/jeroennouws/dev/sk-missions/3162/src/specify_cli/upgrade/feature_meta.py
```

**The input count is printed, not inferred**, and both sides are non-zero:

```
$ grep 'INPUT cases' sc002_pre.txt sc002_post.txt
INPUT cases: 12   (4 sites x 3 shapes)      # both files
$ wc -l sc002_pre.txt sc002_post.txt
  17 sc002_pre.txt
  17 sc002_post.txt
  34 total
$ for f in pre post; do grep -c '|' sc002_$f.txt; done
12
12
```

**The diff is empty:**

```
$ diff <(grep '|' sc002_pre.txt) <(grep '|' sc002_post.txt); echo exit=$?
exit=0
```

The 12 captured lines, identical on both sides:

```
_mid8_from_primary_meta|malformed|''
_mid8_from_primary_meta|absent|''
_mid8_from_primary_meta|valid|'01KWP08S'
_resolve_coordination_branch|malformed|None
_resolve_coordination_branch|absent|None
_resolve_coordination_branch|valid|'kitty/coord-sc002-probe'
_resolve_mission_id|malformed|'legacy-wp08-sc002-degrade-probe-01KWP08S'
_resolve_mission_id|absent|'legacy-wp08-sc002-degrade-probe-01KWP08S'
_resolve_mission_id|valid|'01KWP08SC002PROBE7X9QZTBVKMN'
load_feature_meta|malformed|None
load_feature_meta|absent|None
load_feature_meta|valid|{...parsed mapping...}
```

The **absent** arm is captured explicitly at all four sites — a malformed-only probe would satisfy
the criterion's shape while that arm regressed untouched, which is the defect `NFR-003` was rewritten
to catch. These 12 lines reproduce WP04's recorded 12 exactly, modulo the probe's own slug and
mission-id constants (WP04 used `…01KWP04S…`, this re-capture uses `…01KWP08S…`), which appear in the
`valid` and `legacy-` outputs by construction.

### 12.7 The marker was not red, so no classification was needed

T048 step 7 asks for a pre-existing-vs-mission-caused classification **if** the marker is red. It is
green (`2 passed`, `exit=0`), so no classification arises and none is invented. The stronger related
finding is in §14.4: this mission turns a **pre-existing red green**.

## §13 T049 — the counts, re-verified on the second pass

T049 was measured on the first pass (§5). This section re-verifies it rather than restating it: every
number was re-derived after the reinstall, and the two changes from §5 are the code delta (§5.4) and
the script (§5.6), both corrections rather than confirmations.

### 13.1 The verifier, re-run, `exit=0`

```
TREE measured : /home/jeroennouws/dev/sk-missions/3162
SRC_ROOT      : /home/jeroennouws/dev/sk-missions/3162/src
PYTHONPATH    : <unset>
sys.executable: /home/jeroennouws/dev/sk-missions/3162/.venv/bin/python
== §4 LIVE COUNTS (gate's own AST scanners) ==
  INPUT .py files walked: 1199
  ROUTED live (AST walk): 130
  INLINE live (AST walk): 7
  const INLINE_META_READ_FLOOR = 7
  const FLOOR_MARGIN = 2
  const ROUTED_LOAD_META_FLOOR = 127
  const ROUTED_LOAD_META_FLOOR_MARGIN = 4
  DERIVED routed band: [128, 131] (two-sided; 127 is RED)
== BOUNDS ==
  routed 130 in [128, 131]: OK
  inline 7 <= 7 and gap <= 2: OK
VERDICT: PASS
```

**Routed 130 with its input count 1199.** The naive-grep control, printed by the same tool so the
reader can see which probe is the right one:

```
SNAPSHOT routed naive regex (grep -rn 'load_meta' src): got 307
  (DRIFTED from freeze-point 296; not graded — pass --freeze-check to grade)
SNAPSHOT routed AST authoritative: got 130 (DRIFTED from freeze-point 129)
```

The naive regex answers **307** where the answer is **130**. The DoD's `296` / `129` pair is the
**freeze-point** form of the same control; both are printed above, and both drift by design as the
mission progresses. The graded verdict is the band line, not the snapshots.

### 13.2 The floor was READ off this tree, never copied

```
$ grep -n '^ROUTED_LOAD_META_FLOOR\|^ROUTED_LOAD_META_FLOOR_MARGIN\|^INLINE_META_READ_FLOOR\|^FLOOR_MARGIN' \
    tests/architectural/test_inline_meta_read_gate.py
170:INLINE_META_READ_FLOOR = 7
184:FLOOR_MARGIN = 2
293:ROUTED_LOAD_META_FLOOR_MARGIN = 4
294:ROUTED_LOAD_META_FLOOR = 127
```

`plan.md`'s `## [UNVERIFIED] items` row 1 states that `127` and `[128, 131]` are **derived from the
ruling's stated rule, not measured**, and forbids copying them. They were not copied — they were read
off `:293-294` on the merged tree, and the band is derived from the printed values. That the read
values agree with `plan.md`'s rule-derived ones is a coincidence worth stating, not the source.

### 13.3 The bound is two-sided; **127 is RED**

Re-derived by **opening** the file. The prompt's `:1084` / `:1092` / `:1097` / `:1101` are stale by
~220 lines post-WP06:

| Line | Assertion |
|---|---|
| `:1305` | `def test_routed_load_meta_floor()` |
| `:1313` | `assert len(routed) >= ROUTED_LOAD_META_FLOOR` |
| `:1318` | `assert len(routed) > ROUTED_LOAD_META_FLOOR` — **strict**, explicitly anti-vacuous |
| `:1322` | `assert len(routed) - ROUTED_LOAD_META_FLOOR <= ROUTED_LOAD_META_FLOOR_MARGIN` |

The middle assertion's own message, quoted verbatim from `:1319-1320`:

> *"ROUTED_LOAD_META_FLOOR must be a concrete census integer strictly below the live routed count, not
> '>= len(routed)' (anti-vacuous)."*

Because that inequality is **strict**, at floor **127** the admissible band is `[128, 131]` and
**127 is RED**. The bound therefore binds **downward as well as upward**: a fold that *collapses* two
routed calls into one reds this gate **from below**, which is the failure mode three prior floor
mismatches in this programme came from. A criterion that only bounded from above would be satisfied by
a change that breaks the gate.

### 13.4 The gates run green

```bash
timeout 1800 .venv/bin/python -m pytest \
  tests/architectural/test_inline_meta_read_gate.py::test_routed_load_meta_floor \
  tests/architectural/test_inline_meta_read_gate.py::test_allowlist_matches_floor \
  tests/specify_cli/test_meta_fail_closed_full_census_contract.py -ra > <scratch>/t049_gates.txt 2>&1
```

| | |
|---|---|
| rootdir (control) | `/home/jeroennouws/dev/sk-missions/3162`, `configfile: pytest.ini` |
| selected | `collected 29 items` |
| result, verbatim | `======================== 29 passed in 77.95s (0:01:17) =========================` |
| `exit=` | **0** |
| elapsed / budget | **79 s** / 1800 s |
| `grep -c '^ERROR tests/'` | **0** |
| `grep -c '^FAILED '` | **0** |

### 13.5 The ledger row delta — `12 → 0`, derived three independent ways

```
$ sed -n '185p' tests/specify_cli/test_meta_fail_closed_full_census_contract.py
#   ``pending-batch-a``    — a real routing target that is genuinely UNROUTED.

$ grep -c 'pending-batch-a' <file>                      # LIVE
1
$ grep -n 'pending-batch-a' <file>                      # LIVE, the sole hit IS the legend
185:#   ``pending-batch-a``    — a real routing target that is genuinely UNROUTED.

$ git show 96494e5ec:<file> | grep -c 'pending-batch-a'  # BASELINE
13
$ git show 96494e5ec:<file> | sed -n '185p'              # the legend line, byte-identical at base
#   ``pending-batch-a``    — a real routing target that is genuinely UNROUTED.

$ git diff 96494e5ec..HEAD -- <file> | grep -c '^-.*pending-batch-a'   # rows DELETED
12
$ git diff 96494e5ec..HEAD -- <file> | grep -c '^+.*pending-batch-a'   # rows ADDED
0
```

**`12 → 0`, no survivors.** The three derivations agree:

1. **baseline**: 13 candidates − 1 legend line at `:185` = **12 rows**;
2. **live**: 1 candidate, which *is* the legend line = **0 rows**;
3. **the branch diff** of `_ACCOUNTED_SITES` deletes exactly **12** rows and adds **0**.

The `:185` exclusion is shown as the control, and the legend line is **byte-identical at baseline and
HEAD** — which is what makes excluding it at both ends a valid comparison rather than a convenient
subtraction. There are no survivors to enumerate.

### 13.6 The counts do not vary, shown over 3 runs rather than asserted

T049 step 7 requires a distribution for anything that varies. Three consecutive runs:

```
run1:  files 1199   ROUTED 130   INLINE 7   ledger rows 0   VERDICT: PASS
run2:  files 1199   ROUTED 130   INLINE 7   ledger rows 0   VERDICT: PASS
run3:  files 1199   ROUTED 130   INLINE 7   ledger rows 0   VERDICT: PASS
```

Zero variance across all four numbers, so a scalar is honest here — and that is reported as a measured
distribution of three identical samples, not as a single run generalised.

### 13.7 No count deviated, so no reconciliation against WP01 was needed

T049 step 6 requires any count that is not the expected value to be reconciled against WP01's recorded
command and input file count first. Every count matched its expected value (routed 130, inline 7,
floors 127/4 and 7/2, ledger `12 → 0`), so no deviation arose. The input file count **1199** is printed
by the same tool WP01 used, on the same tree, which is the reconciliation the step asks for.

## §14 T050 — the cone and `SC-017`, discharged from the full-suite measurement

**This section supersedes the previous §0's claim that only `tests/architectural` was run.** T050 was
discharged by a completed full-suite measurement rather than by 14 separate directory runs, and it is
reported as such. §6's `tests/architectural` run stands as the per-directory evidence for that
directory; the numbers below are the whole-cone superset.

### 14.1 What was measured

**21,475 nodes selected across 16 sequential passes: 21,422 passed, 14 failed, 37 skipped, 2 xfailed.**
Every pass was **collection-equivalent** against its own serial `--collect-only` count, so no worker
split moved any number. Passes were run sequentially, never concurrently.

`tests/sync` and `tests/cli` were run in their own separate sequential passes, and
`tests/sync/test_orphan_sweep.py` alone at `-n0` — the only suite the documentation names as binding an
OS-global resource (ports 9400–9449, `docs/development/testing-parallel.md:82-93`).

### 14.2 The 14 failures, attributed against `96494e5ec`

Attribution is against `96494e5ec` = `git merge-base HEAD main`. `98198e980` is `upstream/main`'s tip,
is **not** an ancestor of HEAD (`git merge-base --is-ancestor 98198e980 HEAD` → no), and is used
nowhere.

| Class | Count | Attribution |
|---|---|---|
| **pre-existing** | **13** | Red at base **and** at head, byte-identical causes. Reported, not fixed. |
| **measurement artifacts** | **6** | Not real reds — see 14.3. All pass when re-run serially. |
| **mission-introduced** | **1** | The dogfood corpus guard. **FIXED** — see 14.3. |

The classes overlap in the arithmetic because the 6 artifacts and the 13 pre-existing are counted
across passes; the load-bearing statement is the one below.

**Net: zero mission-introduced failures remain.**

### 14.3 The one mission-introduced failure, and the six artifacts

**Mission-introduced (1), now FIXED.** The dogfood corpus guard went red because this mission is a
**natively-born, event-sourced** mission that never receives the `status_phase` stamp — the stamp is
written only by the legacy-seeding path. Closed by stamping `status_phase: "1"` in `meta.json`
(`be01cbbf3`), which records something true: the mission *is* event-sourced, phase ≥ 1. Gate re-run:
**6 passed, exit 0**. The underlying two-authorities disagreement is ledgered as `R5` with the
operator's decision, and an attempted fix that a control killed is recorded there too so it is not
retried.

**Measurement artifacts (6), all topology and none the branch's:**

* **3 latency reds** — `test_completion_latency_within_budget` ×3, wall-clock budgets sampled under
  6-way contention. All three pass serially. Ledgered as `F18`: the file carries
  `pytestmark = [pytest.mark.integration]` and **not** the `timing` marker `pytest.ini` defines for
  exactly this purpose.
* **2 `test_issue_1071` reds plus leak-guard errors** — two `tests/sync` workers binding **port 9413**
  concurrently. Ledgered as `F17`, with three composing causes measured: overlapping declared port
  bands (`[9401,9425)` vs `[9400,9425)`), an incomplete serial-only exclusion list (four files bind
  real ports through the harness, only `test_orphan_sweep.py` is named), and a **TOCTOU** in
  `find_free_port_in_range`. **`--dist loadfile` is NOT the defect and must not be "fixed"** — the
  contended resource is OS-global and shared *across* files, which file-affinity cannot address.

### 14.4 Better than no-regression: the mission turns a pre-existing red GREEN

`tests/regression/test_issue_2804_merge_resets_gate_artifacts.py::test_merge_resets_filled_gate_artifacts_to_placeholder`
**fails at base and passes at head.** So WP07 works as claimed, and the branch's effect on the suite is
strictly positive rather than merely neutral. §12.2's `2 passed` is the head half of that pair.

### 14.5 `SC-017` — the static gates

**`ruff check`**, CI's exact lint scope, re-run on this pass:

```
$ .venv/bin/ruff check src tests
All checks passed!
exit=0
```

Plus the one file this WP added, which is **outside** CI's scope (`scripts/` is not in `ruff check src
tests`) and so was linted explicitly — see §5.6: clean, `C901` clean, zero `# noqa`, zero
`# type: ignore`.

**`ruff format` was never run.** No suppression of any kind was added to reach zero.

**`mypy --strict` delta `0 → 1 → 0`**, measured on both sides — full evidence and both corrections in
§7. Summary: base `96494e5ec` and HEAD both report `Success: no issues found in 1130 source files`,
exit 0, same invocation, same file count; the one new error (WP02's widened `except` tuple outgrowing
its callee's annotation) was fixed in `24a5e62a5`.

### 14.6 What this discharge does NOT claim

* It does **not** claim 14 individually-quoted per-directory `N passed` lines with 14 collection counts
  and 14 `^ERROR tests/` counts, in the form T050 step 1 describes. The measurement was 16 sequential
  passes over the full suite with per-pass collection equivalence, which is a **superset** of the cone
  in coverage but is **not** the same presentation. `[UNVERIFIED]` as a per-directory table.
* The per-directory form **is** present for `tests/architectural` (§6: `1703` collected, `1699 passed,
  2 skipped, 2 xfailed`, `exit=0`, `^ERROR tests/` = 0) and for the five touched files outside the cone
  (§6.1: `28 passed`, `exit=0`).
* The 14 failures are reported as **class totals with named causes**, not as 14 individually quoted
  tracebacks.
* No run in this measurement was killed or timed out. A first whole-cone run on the earlier pass **was**
  killed and was discarded as **neither pass nor fail** (§10), not reported from the partial.

## §15 T051 — the `SC-009` filing register, complete

`spec.md`'s `SC-009` mandates *"≥5 filings"* and then enumerates **eight**. The row count is the
obligation, so all eight are below.

**The blocker that was recorded against this subtask is not a blocker.** WP08 previously recorded T051
as blocked because it *"needs `gh issue view` rows; filing is forbidden"*. **Reading is not filing.**
The operator direction bars `gh issue create`; `gh issue view` is a read and is permitted. Every row
below is verified by a real `gh issue view` against the live tracker.

Auth control, per the documented workaround for org-repo scopes:

```
$ unset GITHUB_TOKEN; gh auth status
github.com
  ✓ Logged in to github.com account MOES-Media (keyring)
  - Active account: true
  - Token: gho_************************************
  - Token scopes: 'admin:org', 'gist', 'project', 'repo', 'workflow', 'write:packages'
```

`unset GITHUB_TOKEN` preceded every `gh` call.

### 15.1 The register

| # | Filing | Mandated by | Issue | Verification |
|---|---|---|---|---|
| 1 | Superseding issue for `#2804`: what is pinned now, why the shape changed, and that `b04da00e1` deleted `tests/merge/test_gate_artifact_merge_drivers_2804.py` | `FR-010`, `Q9` | `#3232` | **viewed**, OPEN |
| 2 | The pending-poisons-the-aggregate product defect, `src/specify_cli/acceptance/gates_core.py:525` as evidence | `FR-011`, `C-006` | `#3231` | **viewed**, OPEN |
| 3 | Deferral of the 4 scanner-invisible bypass read expressions (no allowlist entry is possible) | `FR-007`, `NFR-004` | `#3239` | **viewed**, OPEN |
| 4 | `Q8`: lock-only comparison duplicated, `_VCS_LOCK_META_FIELDS` declared twice — filed **before** that code was edited, number cited in a comment at the surviving comparison | `C-009` | `#3228` | **viewed**, OPEN, `createdAt 2026-08-06T01:11:16Z`; in-code citation **verified** |
| 5 | `NFR-001`'s residue: the 4 degrade sites remain knowingly indistinguishable under `D4=a`, with `Q4` as candidate remedy | `NFR-001`, `Q4` | **none — NOT FILED** | See 15.3. Recorded in `residual-ledger.md` instead, by operator direction. No number exists, so none is quoted rather than one being invented. |
| 6 | The **L1 pure-decode primitive** (`text\|bytes → dict\|None`, typed) — the missing seam tier | `C-004` | `#3229` | **viewed**, OPEN, `createdAt 2026-08-06T01:11:41Z` |
| 7 | `inline_meta` absent from `tests/architectural/_baselines.yaml`, so the allowlist sits **off** the charter Burn-down register | charter Burn-down Policy §(a) | `#3240` | **viewed**, OPEN — and still an **open operator call**, see 15.4 |
| 8 | Full routing of the 4 non-routed bypass sites (the `Q2` residue after R-1) | `Q2`, `C-004` | `#3230` | **viewed**, OPEN, `createdAt 2026-08-06T01:12:07Z` |

### 15.2 The quoted `gh issue view` output for every numbered row

```
$ unset GITHUB_TOKEN; gh issue view 3232 --json number,title,state
{"number":3232,"state":"OPEN","title":"Supersedes `#2804`: the re-pinned regression marker (row-union authority model) and the unit gate deleted in `b04da00e1`"}

$ unset GITHUB_TOKEN; gh issue view 3231 --json number,title,state
{"number":3231,"state":"OPEN","title":"Acceptance gate: one admitted scaffold row makes `overall_verdict` `pending` and blocks acceptance (pending-poisons-the-aggregate)"}

$ unset GITHUB_TOKEN; gh issue view 3239 --json number,title,state
{"number":3239,"state":"OPEN","title":"meta-fail-closed WP06 / SC-009 row 3: four scanner-invisible meta.json bypass reads deferred — no allow-list entry is possible at any baseline (FR-007 / NFR-004)"}

$ unset GITHUB_TOKEN; gh issue view 3228 --json number,title,state,createdAt
{"createdAt":"2026-08-06T01:11:16Z","number":3228,"state":"OPEN","title":"Q8: the meta.json VCS-lock-only comparison is duplicated — 2 declarations, 2 non-equivalent comparators"}

$ unset GITHUB_TOKEN; gh issue view 3229 --json number,title,state,createdAt
{"createdAt":"2026-08-06T01:11:41Z","number":3229,"state":"OPEN","title":"L1 seam tier: add a pure-decode meta.json primitive (text|bytes -> dict|None) so the two blob-fed bypass parsers can route"}

$ unset GITHUB_TOKEN; gh issue view 3240 --json number,title,state
{"number":3240,"state":"OPEN","title":"meta-fail-closed WP06 / SC-009 row 7: inline_meta_read allow-list is absent from tests/architectural/_baselines.yaml — register it or record the deviation (OPEN operator call)"}

$ unset GITHUB_TOKEN; gh issue view 3230 --json number,title,state,createdAt
{"createdAt":"2026-08-06T01:12:07Z","number":3230,"state":"OPEN","title":"Q2 residue: route the 4 remaining meta.json bypass reads (deferred on routed budget + missing L1 tier, NOT on structure)"}
```

Rows 3 and 7 are self-identifying: their titles literally say *"SC-009 row 3"* and *"SC-009 row 7"*.

**Row 4's extra obligation, verified in code.** `C-009` requires the number cited *in a comment at the
surviving comparison*, filed before that code was edited:

```
$ grep -rn '3228' src/specify_cli/git/ref_advance.py
232:# Q8 (`#3228`): this comparison is duplicated -- ``_VCS_LOCK_META_FIELDS`` is
```

And row 4's recorded measured correction (**×2, not ×3**) checks out — 2 declarations and 2
comparators, no third:

```
$ grep -n '_VCS_LOCK_META_FIELDS' src/specify_cli/git/ref_advance.py src/specify_cli/cli/commands/implement_cores.py
src/specify_cli/git/ref_advance.py:42:_VCS_LOCK_META_FIELDS: frozenset[str] = frozenset({"vcs", "vcs_locked_at"})
src/specify_cli/cli/commands/implement_cores.py:50:_VCS_LOCK_META_FIELDS: frozenset[str] = frozenset({"vcs", "vcs_locked_at"})
$ grep -n 'def _is_vcs_lock_only_meta_change\|def _is_vcs_lock_only_meta_diff' src/specify_cli/git/ref_advance.py src/specify_cli/cli/commands/implement_cores.py
src/specify_cli/git/ref_advance.py:239:def _is_vcs_lock_only_meta_change(
src/specify_cli/cli/commands/implement_cores.py:241:def _is_vcs_lock_only_meta_diff(
```

`createdAt` for `#3228` is `2026-08-06T01:11:16Z`, which is **before** WP05's first code commit —
the "filed before that code was edited" clause, verified by timestamp rather than by narration.

### 15.3 Row 5 is empty, and this is WHY — not a blank

Row 5 has **no issue number and is not filed.** The reason, stated in the row rather than left to be
inferred: **operator direction for this mission forbids `gh issue create`, consciously overriding
charter `DIR-013`.** The residue is instead recorded in `residual-ledger.md` under *"`SC-009` register
row for `NFR-001` (filed here, not as a tracker issue)"*, with its evidence: the four degrade sites
remain knowingly indistinguishable under `D4=(a)` because `""`, `None`, `legacy-<slug>` and `None` are
each values a **valid** `meta.json` also yields — demonstrated by the `SC-002` probe, whose 12 lines in
§12.6 show `_mid8_from_primary_meta` returning `''` for malformed **and** absent input.

This row is **not** marked done by narration and **no** number was invented for it. It is an
open, recorded residue with a named candidate remedy (`Q4`).

### 15.4 `Q4` and `Q11` remain OPERATOR questions — recorded, not answered

Neither is answered here, and no filing is presented as an answer to either.

| Question | Status | Owner |
|---|---|---|
| **`Q4`** — should the 4 degrade sites **log** when they degrade? | **OPEN** | *"the work package that owns the degrade sites' routing"* (`spec.md:535`). Adding logging is a behaviour change `D4` did not authorise. It is row 5's candidate remedy, not its answer. |
| **`Q11`** — does `merge_driver.py:167 _load_json_object` belong to the bypass class for full routing? | **OPEN — and it is a QUESTION, not a deliverable** (`spec.md:538`) | Operator. Previously mis-listed as a *requirement*; it is not one. |

Row 7 (`#3240`) is likewise an **open operator call**, not a closed filing: the charter Burn-down
Policy §(a) choice between *registering* `inline_meta` in `_baselines.yaml` and *recording the
deviation* is a governance decision. The absence itself is verified upstream
(`grep -c inline_meta tests/architectural/_baselines.yaml` → **0**). The issue records the question;
the operator's answer is still outstanding. **No ratchet baseline was regenerated** — neither
`_baselines.yaml`, nor `_gate_coverage_baseline.json`, nor `_golden_count_baseline.json`.

### 15.5 Cross-check — this WP's own declined findings, per T051 step 6

Every defect this WP surfaced and declined to fix, with its owner:

| Finding | Surfaced in | Declined because | Where it lives |
|---|---|---|---|
| The `_rel()` relocation trap in the inline gate — `EXCLUDED_REL_PATHS` silently stops matching on a relocated tree, over-counting inline sites by 1 | T049 (§5.4) | It is a `tests/architectural` tooling defect, not `meta.json` read routing. **Worked around, not fixed**: the new script restates the exclusion by suffix and prints the control. | Already folded into the ledger via `#3241`; this is a second instance of the same trap, in a second gate surface |
| `F17` — `tests/sync` real-port collision (band overlap, incomplete exclusion list, TOCTOU) | T050 (§14.3) | `tests/sync` infrastructure; the mission changed no `src/specify_cli/sync/` file | `residual-ledger.md` `F17` |
| `F18` — three wall-clock latency assertions marked `integration` rather than `timing` | T050 (§14.3) | Testing-taxonomy/CI-topology question; the file is untouched by this mission | `residual-ledger.md` `F18` |
| `F19` — `locate_project_root()` escapes a detached worktree, relocating `rootdir` and `__file__` while the data corpus does not | earlier pass | A `core.paths` ownership decision | `residual-ledger.md` `F19` |
| `F20` — the venv `.pth` pins HEAD's `src`; `.venv/bin` absent from `PATH` | earlier pass | Environment topology | `residual-ledger.md` `F20` |
| `F14` — `gc._baseline_header` hardcodes one mission's provenance for every E3 target | earlier pass | A `tests/architectural` tooling mission | `residual-ledger.md` `F14` |
| `F16` — the `implement` action gate cannot be satisfied for WP08 (`analysis-report.md` has no frontmatter) | earlier pass | Adding frontmatter to a planning artifact purely to satisfy a guard would be editing evidence to pass a gate | `residual-ledger.md` `F16` |
| `R1`–`R4` — the `for_review`/`approved` guard's surface model, the no-implementation-commits refusal, `pre_review_gate`'s `no_coverage`, and shared-worktree data loss | across the mission | spec-kitty product/tooling defects outside this mission's subject | `residual-ledger.md` `R1`–`R4` |
| `R5` — two cut-over authorities disagree about a natively-born mission, and one gates CI | T050 (§14.3) | Fixed *for this mission* by the operator-decided stamp; the authority reconciliation is a read-authority mission | `residual-ledger.md` `R5` |
| **Upstream base-hygiene red** — `test_routed_load_meta_floor` is **already red on `upstream/main`** (routed 133, floor 128, band `[129, 132]`), with a routed site set largely disjoint from ours | reported by the orchestrator during this pass | **Not this mission's**, and not this WP's to fix. The rebase and the floor re-derivation are the orchestrator's. | `residual-ledger.md`, BASE HYGIENE |

**Nothing above was absorbed into this WP**, which has no code surface beyond its one owned script.
The two corrections this WP *did* make to its own artifact — the `SC-006` code delta (§5.4) and the
`mypy` claim (§7) — are corrections to this WP's own prior evidence, not fixes to another WP's surface.

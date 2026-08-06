# Implementation Plan: meta.json fail-closed routing, and #2804's re-pin

**Branch**: `feat/meta-fail-closed-3162` | **Date**: 2026-08-05 | **Spec**: `./spec.md`
**Input**: `./spec.md` (remediated after the post-specify pass and again after the post-plan adversarial
squad — see `./analysis-report.md`, which is the binding directive for this revision)

## Summary

Route 13 `meta.json` reads onto `load_meta_fail_closed` preserving each site's arm, make the bypass reads
diagnosable, route the single gate-reachable bypass site, widen the architectural gate by the one shape it
can reach, re-derive both floors, and re-pin #2804's **two** assertions to what the current merge design
actually guarantees. No behaviour change at the 4 degrade sites; a typed error where 7 raw `ValueError`s
escape today.

The post-plan squad rejected the previous slicing outright: it cut **by arm** (routing in one concern, the
`None` arms and handlers in the next), which shipped a **fail-open** at `context/resolver.py` and a
`C-002` violation at `decisions/service.py` / `_resolve_planning_branch.py` in the committed interval.
This revision slices **by site**: a site's routing, its `None` arm, its handler change and its ledger-row
deletion are **one indivisible edit**, owned by whichever concern routes it.

### Measured — holds on both `96494e5ec` and branch `HEAD`

`HEAD` is `1e5bc865b`; `git diff --name-only 96494e5ec HEAD | grep -v '^kitty-'` → **0** files, and every
load-bearing file is byte-identical to current `upstream/main` `98198e980`. Branch-head measurements *are*
baseline measurements; no number below moves with the label.

| Quantity | Value | Note |
|---|---|---|
| Sites to route | **13** | arms: **4 degrade / 2 refuse-typed / 7 refuse-raw**; ledger sum 13, live 13, ledger == live |
| `except ValueError` handlers to change | **6** | not 4 — the 2 refuse-typed sites also catch it and would leak the wrapper. Naive `grep -c` gives **9** (a comment at `resolution.py:491` plus two unrelated handlers) |
| Bypass sites (no `load_meta` at all) | **5 read expressions / 6 invocation sites** | **Convention declared per count.** The 5 are read expressions: `ref_advance.py:203` (git show), `:244` (`read_text`), `implement_cores.py:335` (`show_blob`), `:427` (`read_bytes`), `merge_driver.py:171` (`read_text`). Under the **call-site** convention this mission uses elsewhere (it is why census rows 10/11 count `read_primary_meta` as 2 and yield 13, not 12), `merge_driver._load_json_object` is invoked from `:243` **and** `:244`, so the total is **6**. Both defensible; mixing them silently in one document is not. And 5/6 is the current count, **not the closure** |
| Gate widening reach | **1 site** | `ref_advance.py:247`; **0** false positives over `src/`. Breakdown: **19 candidates → 17 rejected at clause 2 → 1 rejected at clause 3 → 1 accepted**. The inherited "31 candidates / 30 at clause 3" reproduces under **no** definition (8 variants swept) |
| What holds false positives at zero | **clause 2**, not clause 3 | Clause 3 (the meta-path clause) rejects exactly **one** candidate. The load-bearing guard is clause 2 — the call-site argument must resolve to a `read_text`/`open`/`read_bytes` call. A later widening of clause 2 unlocks ~17 candidates with **no** measured clause-3 protection. The previous plan's attribution was inverted and licensed widening the very clause that guards the count |
| `read_bytes` added to `_extract_read_base` | **0 new sites** | free evasion-vector closure; control fixture expected 1→2 and got 1→2 |
| Live routed count | **129** | `ROUTED_LOAD_META_FLOOR = 126`, `ROUTED_LOAD_META_FLOOR_MARGIN = 4`. `test_routed_load_meta_floor` asserts **three** things — `len >= FLOOR`, `len > FLOOR` (explicitly anti-vacuous), `len - FLOOR <= MARGIN` — so the admissible band is **`[127, 130]`**, not `[126,130]`. **126 is RED.** Headroom is **one** net routed call |
| Live inline count | **7** | `= INLINE_META_READ_FLOOR` (`:127`); `FLOOR_MARGIN = 2` (`:134`); allowlist **7** entries; `inline_meta_read_baseline` **7**; shrink-only |
| #2804's marker | **red on pristine `upstream/main` `98198e980`** | `git worktree add`, `1 failed in 96.97s`, `^ERROR tests/` = 0, `E assert 'pending' == 'pass'`. A genuine same-selection pre-existing red — and it carries a **second** red assertion (`SCAFFOLD_TODO_MARKER not in json.dumps(post_matrix)`), false after the merge by a *different* mechanism |

**The band is two-sided.** This programme has already had three floor mismatches caused by folds that
*collapsed* call sites. A routing pass that replaces two calls with one reds
`test_routed_load_meta_floor` **downward**. Census rows 10 and 11 are two calls inside one function
(`read_primary_meta`) — the concrete temptation.

## Technical Context

**Language/Version**: Python 3.11. **Primary Dependencies**: none added.
**Storage**: N/A (filesystem `meta.json` only).
**Testing**: `.venv/bin/python -m pytest`. Redirect, quote the `N passed` line, print input counts, `-ra`
never `-rf`, count `^ERROR tests/` not `^ERROR `. `ruff check` and `mypy --strict` are criteria, not
afterthoughts (`DIR-030`) — no criterion previously required either.
**Target Platform**: Linux / macOS / Windows CLI.
**Project Type**: single (CLI + library).
**Performance Goals**: `tests/architectural/test_inline_meta_read_gate.py` must stay inside its fast-tier
budget (`test_gate_runs_under_fast_tier_budget`, `:1229`) after the widening.

**Constraints**:
- `tests/sync` and `tests/cli` never sweep concurrently (`C-007`). **A sibling mission at
  `~/dev/sk-missions/3167` may hold the `tests/sync` window — the handshake is owned by IC-08 and must be
  performed before any broad sweep.** Neither directory is in this mission's cone, so the mission never
  needs the window; the handshake exists so a *broad* sweep does not take it by accident.
- **Declared test cone (14 top-level directories).** The previous 5-directory cone was under-declared by
  **9**, not conservatively declared: an import-line grep (control: `INLINE_META_READ_FLOOR` returns only
  the 2 architectural files, confirming no over-match) found 26 test files outside it that import a changed
  module.

  `tests/specify_cli`, `tests/mission_runtime`, `tests/regression`, `tests/merge`, `tests/architectural`,
  **`tests/integration`**, **`tests/missions`**, **`tests/runtime`**, **`tests/next`**, **`tests/context`**,
  **`tests/status`**, **`tests/upgrade`**, **`tests/coordination`**, **`tests/lanes`**.

  None of the 9 additions is `tests/sync` or `tests/cli`, so none collides with mission 3167's window.
  The one that matters most is `tests/status/test_aggregate_coord_deleted_contract.py:81-92`, which pins
  census rows 10/11. (An earlier draft also named `test_coord_loop_workspace.py:611,627` as pinning row
  8's arm — those two lines are **docstring prose**, not assertions; withdrawn.)
  **`tests/specify_cli/cli/commands/` is *inside* `tests/specify_cli` and is NOT the barred top-level
  `tests/cli`** — the census conflated the two, which is why `test_implement_cores.py` and
  `test_row_aware_merge_driver.py` were treated as unreachable.
- Every routing commit deletes its own `pending-batch-a` ledger row in the **same** commit
  (`tests/specify_cli/test_meta_fail_closed_full_census_contract.py:193`, exact-equality in both
  directions: `test_no_unaccounted_load_meta_call_sites` `:292`, the staleness arm `:322-331`).
- The routed budget is **one** net call for the whole mission, allocated in the Headroom Allocation table
  below. Every other concern is **0-net**.

**Scale/Scope**: 12 source files, 1 architectural gate, 1 regression marker, 1 census ledger,
≥5 tracker filings.

### Headroom Allocation — the routed budget has exactly one allocator

There is **one** net routed call for the whole mission (`129` live, band `[127,130]`). Three concerns touch
routed call counts and the previous plan had no allocator, so each would have assumed the call was free.

| Concern | May spend the net call? | Net routed delta | Pre/post print obligation |
|---|---|---|---|
| IC-01 | n/a — no code | 0 | Records `129` as the manifest anchor and the band `[127,130]` |
| IC-02 | **No — 0-net** | **0** (6 swaps; `load_meta` and `load_meta_fail_closed` are both in `ROUTED_CALLEES`) | Print live routed **pre and post its own edit**; both must read **129** |
| IC-03 | **No — 0-net** | **0** (3 swaps) | Print pre and post; both **129** |
| IC-04 | **No — 0-net** | **0** (4 swaps) | Print pre and post; both **129** |
| IC-05 | **Yes — the one call, at `ref_advance.py:247`** (R-1) | **+1** | Print pre **129**, post **130**; both inside `[127,130]` with the floor still 126 |
| IC-06 | **No — 0-net**; re-derives `ROUTED_LOAD_META_FLOOR` | **0** | Print live routed pre and post the floor move; assert the three clauses of `test_routed_load_meta_floor` hold at the new floor |
| IC-07 | **No — 0-net** | **0** (test + tracker only) | Print pre and post; both unchanged |

**The 0-net constraint is what makes parallel lanes safe.** Each lane measures the count in its own
worktree; if only IC-05 is non-zero, every lane is individually green and the merged tree reads 130. A
concern that quietly folds two calls into one breaks this **downward** — and 126 is RED.

Acceptance criteria are per-concern, not mission-end: **every concern above prints the routed count before
and after its own edit.** `SC-011`'s previous form ("print 129 pre and 129 post") was satisfiable by
changing nothing, because the census counts callee **names** and cannot see whether routing happened.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Requirement | Status |
|---|---|
| Single canonical authority | **Partial — one seam decision open.** 13 reads converge on one seam and `NFR-002`'s kept clause (no new predicate answering "is this `meta.json` readable") is criterion-backed by a pre/post enumeration of predicate symbols. But `C-004` deferred the **bypass seam** question *to* `NFR-002`, which never adjudicated it and carried no predicate-counting criterion — so 4–5 sites would each author a local answer. IC-05 must record the three-tier seam family and file the missing L1 primitive; until that lands the row is Partial, not Pass |
| ATDD-first / red-first (`C-011`) | **Documented exception — not a Pass.** See Complexity Tracking row 1. The charter (§ATDD-First Discipline) requires the ATDD test RED on the WP's `planning_base_branch`. IC-04's red is on an **intermediate commit**, and `NFR-003` requires degrade behaviour identical pre- and post-change, so a base-red is **impossible by construction**. `FR-008` and `FR-006`'s `read_bytes` half are marked **"no red possible — synthetic pin required"** (`read_bytes` adds **0** sites, measured). The reviewer verification that replaces the base-red check is spelled out in Complexity Tracking |
| Architectural gate discipline | **Deviation — not grantable as Pass.** Three reasons: (i) the only baseline-held green state was the one the plan forbade (widen + route, which the plan's `Q2` "diagnosable-only" excluded — BLOCKER-1); (ii) `SC-005`'s unreachability control was a **vacuous negative** with no positive twin, which `architectural-gate-non-vacuity` forbids; (iii) **`inline_meta` is absent from `tests/architectural/_baselines.yaml`** — verified, `grep -c inline_meta` → **0** — so the allowlist this mission governs sits **off** the charter's Burn-down Policy §(a) register. Deferring `FR-007` with a control **is** charter-compliant in principle (the alternative is the forbidden re-freeze), but as specified it was a gate-discipline breach wearing a vacuous control as cover. Remedied by IC-06: add the positive twin, and **register `inline_meta` in `_baselines.yaml` or file the register deviation** |
| Pre-existing failure reporting (§Pre-existing Failure Reporting Rule) | **Pass** — `FR-009` is an inverted red: #2804's marker is red on **pristine `upstream/main` `98198e980`**, reproduced in a clean `git worktree`, same selection, `^ERROR tests/` = 0. That is a genuine pre-existing classification, not "belongs to a known class tracked elsewhere" |
| Complexity ceiling 15 | **Owned** — backed by the `## Complexity Tracking` register below, which names the functions that gain branches and the per-file `ruff check --select C901` pre/post obligation. It previously said "Check per file" and owned nothing |
| Campsite cleaning (Standing Order 2) | **Scoped** — `Q8` (the lock-only comparison duplicated ×3, `_VCS_LOCK_META_FIELDS` declared twice at `ref_advance.py:42` and `implement_cores.py:50`) is domain-matched debt on IC-05's exact surface. `C-009` had **zero** enforcement anywhere. **Filed, not absorbed** (`DIR-024` locality of change); the filing is IC-05's deliverable |
| Git & workflow discipline (Standing Order 7) | **Owned by IC-08** — commit slicing, the DRAFT cross-fork PR, and `SC-006`'s "the raise argued in the PR body". Previously unowned |

## Project Structure

### Documentation (this mission)

```
kitty-specs/meta-fail-closed-3162-01KZ7FSQ/
├── spec.md                        # Mission specification (remediated twice)
├── plan.md                        # This file
├── analysis-report.md             # Post-plan adversarial squad directive (binding)
├── research.md                    # Phase 0 synthesis
├── research/
│   ├── 3162-census.md             # The 13 sites, arms, bypass class, gate blindness
│   ├── evidence-log.csv
│   └── source-register.csv
├── data-model.md
├── contracts/
│   ├── routing-manifest.md        # NEW — IC-01: the 13 sites x arm x handler x ledger row
│   └── headroom-allocation.md     # NEW — IC-01: the routed-budget allocator
├── decisions/                     # DM-01KZ96X4NH..., DM-01KZ96X4W6..., DM-01KZ96X52V...
├── checklists/
└── tasks/                         # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

Concrete paths, one owner each. This is the map `/spec-kitty.tasks` turns into `owned_files` globs; prose
"Surfaces" lines gave the lane computation nothing to consume, which is why this section's absence was
load-bearing.

```
src/
├── mission_runtime/
│   └── resolution.py                      IC-04  rows 1,2,3 (:509,:852,:1107) + handlers :514,:853,:1108
├── runtime/next/
│   ├── _internal_runtime/planner.py       IC-02  row 4 (:188)
│   └── runtime_bridge_io.py               IC-02  row 5 (:380)
└── specify_cli/
    ├── core/paths.py                      IC-04  docstring :648-651 (R-2, same commit as the routing)
    ├── bulk_edit/gate.py                  IC-02  rows 6,7 (:57,:80)
    ├── missions/
    │   ├── _read_path_resolver.py          IC-02  rows 10,11 (:846,:862)
    │   └── _resolve_planning_branch.py     IC-03  row 12 (:116) + handler :122
    ├── context/resolver.py                IC-03  row 8 (:75) + FileNotFoundError arm :68-78
    ├── decisions/service.py               IC-03  row 9 (:134) + handler :141
    ├── upgrade/feature_meta.py            IC-04  row 13 (:42) + handler :43
    ├── git/ref_advance.py                 IC-05  _parse_meta_object :181-189, :203, :242, :244, :247
    └── cli/commands/
        ├── implement_cores.py             IC-05  _parse_meta_mapping :259, :335, :421-427
        └── merge_driver.py                IC-05  _load_json_object :167, read :171, calls :243,:244

tests/
├── specify_cli/
│   ├── test_meta_fail_closed_full_census_contract.py   IC-02 + IC-03 + IC-04 (ledger rows; see collision matrix)
│   ├── context/test_resolver.py                       IC-03  (:256 pins row 8's MissingIdentityError)
│   ├── decisions/                                     IC-03
│   ├── bulk_edit/                                     IC-02
│   └── cli/commands/
│       ├── test_implement_cores.py                    IC-05  (run before editing implement_cores.py)
│       └── test_row_aware_merge_driver.py             IC-07  READ-ONLY — must stay byte-identical (SC-008)
├── mission_runtime/                                   IC-04
├── upgrade/                                           IC-04
├── next/ , runtime/                                   IC-02
├── missions/                                          IC-02 + IC-03
├── context/                                           IC-03
├── status/test_aggregate_coord_deleted_contract.py    IC-02  RUN-ONLY (:70-92 supplies row 11's fixture shape; :81-92 pins rows 10/11)
├── integration/test_coord_loop_workspace.py           IC-03  RUN-ONLY (:611,:627 are PROSE, not pins)
├── coordination/ , lanes/                             IC-08  (cone coverage only)
├── regression/
│   ├── test_issue_2804_merge_resets_gate_artifacts.py IC-07  (both assertions; fixture rows :172-185)
│   └── test_issue_2795_claim_blocker.py               IC-05  RUN-ONLY
├── merge/                                             IC-07  (the deleted unit gate test_gate_artifact_merge_drivers_2804.py, removed in b04da00e1, is cited not restored)
└── architectural/
    ├── test_inline_meta_read_gate.py                  IC-06  :127,:134,:220,:221 + tests :1061,:1084,:1109,:1116,:1125,:1166
    ├── inline_meta_read_allowlist.yaml                IC-06  DECLARED UNCHANGED (7 entries, baseline 7)
    ├── _baselines.yaml                                IC-06  register inline_meta, or file the deviation
    ├── <fixtures>/unreachability_control.py           IC-06  NEW — negative; scanned by explicit argument, NOT under src/
    ├── <fixtures>/unreachability_control_twin.py      IC-06  NEW — positive twin (same module, read inlined, path named meta_path -> sites: 1)
    └── tool_artifact_enrolment/registry/_is_self_write_only_diff.md   IC-05  FILE-LEVEL glob, not the directory
```

**Structure Decision**: single-project CLI layout, unchanged. Three ownership rules fall out of the map
and bind `/spec-kitty.tasks`:

1. **`tests/architectural/` must be globbed at file level, never as a directory.**
   `tool_artifact_enrolment/registry/_is_self_write_only_diff.md` is an IC-05 surface living inside IC-06's
   directory. A directory glob unions the bypass concern with the gate concern for no reason.
2. **`mission_runtime/` belongs to IC-04 alone.** The previous plan named it under the refuse concern,
   where it owns **nothing** — all three `resolution.py` sites are degrade. As an `owned_files` glob that
   forced a needless lane union with the mission's sharpest-risk concern. Struck.
3. **The routing ledger is a shared surface with an explicit rule, not an unowned one.**
   `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` was in **no** concern's surfaces. It
   is now owned jointly by IC-02, IC-03 and IC-04, which is what forces them into a single lane (see the
   collision matrix). The unreachability control must **not** live under `src/` —
   `scan_inline_meta_reads` walks `SRC_ROOT`, so a fully-inlined read there raises the live census and reds
   the floor it exists to prove.

## Complexity Tracking

*Charter Check has three non-grantable rows; each is justified here rather than granted by narration.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| **ATDD-first base-red waived for IC-04** (4 degrade sites) | `NFR-003` requires the degrade fallback be **identical** pre- and post-change across malformed, absent and valid input. A test that is red on `planning_base_branch` would be asserting behaviour the mission is forbidden from changing. The only real red is the `MissionMetaReadError` escape created by the routing commit itself. **Reviewer verification that replaces the base-red check:** (a) the routing commit's SHA quoted with the escaped `MissionMetaReadError` as its red evidence; (b) the handler commit's SHA green on the same selection; (c) `git log --oneline` proving routing precedes handler **inside the work package**; (d) both commits present in the lane's final history, not squashed away; (e) the `SC-002` `diff pre.txt post.txt` empty with both captures at non-zero `wc -l`, positive control first | A base-red test is impossible by construction, not merely expensive. Writing one anyway would mean pinning a behaviour change `D4=(a)` forbids. Declaring the requirement "already green at baseline, regression guard only" was the previous framing and it let a routing that preserved one arm and broke another pass |
| **ATDD-first base-red impossible for `FR-008` and `FR-006`'s `read_bytes` half** | `read_bytes` adds **0** new sites (measured, control fixture 1→2). There is no site whose detection flips, so no red exists. Pinned by a **synthetic** fixture instead: a scratch module whose read is `read_bytes`-fed, red before the `_extract_read_base` change and green after | Allowlisting or skipping leaves the evasion vector open with no evidence it was ever closed. A live-tree red cannot be manufactured without adding an unrouted read to `src/`, which reds the floor |
| **Architectural allowlist governed off the `_baselines.yaml` register** | `inline_meta` is absent from `tests/architectural/_baselines.yaml` (verified `grep -c` → 0), so the charter's Burn-down Policy §(a) — growth above baseline FAILS CI, shrinkage WARNS — does not currently reach this allowlist. `inline_meta_read_baseline` lives inside `inline_meta_read_allowlist.yaml` instead, enforced by `test_allowlist_shrink_only` (`:1125`) and `test_allowlist_matches_floor` (`:1116`) | Leaving it unregistered and unremarked is the actual violation. IC-06 must either add the register entry or file the deviation with the two enforcing tests cited as the compensating control — silence is not an option, and this mission is the one that touches the allowlist |

### Complexity ceiling register (`<= 15`, ruff `C901` / Sonar `S3776`)

Functions that gain branches in this mission. Each owning concern runs `ruff check --select C901` on its
own files **pre and post** and quotes both, per file. Values are not asserted here — measuring them is the
deliverable, and inventing them would be worse than leaving them open.

| Function | File:line | Owner | What it gains | Pre / post |
|---|---|---|---|---|
| `_read_meta_json` | `context/resolver.py:68-80` | IC-03 | an `if result is None:` arm; loses a dead `except FileNotFoundError` | `[UNVERIFIED — measure]` |
| `_resolve_mission_id` | `decisions/service.py:134` | IC-03 | an `if result is None:` arm; handler widened | `[UNVERIFIED — measure]` |
| `load_mission_target_branch` | `_resolve_planning_branch.py:116-131` | IC-03 | an `if result is None:` arm carrying the missing-file message | `[UNVERIFIED — measure]` |
| `_mid8_from_primary_meta` | `resolution.py:509` | IC-04 | handler extended to a tuple | `[UNVERIFIED — measure]` |
| `_meta_change_is_vcs_lock_only` | `ref_advance.py:231-251` | IC-05 | routed read + a corruption-diagnostic arm | `[UNVERIFIED — measure]` |
| `_committed_meta_object` | `ref_advance.py:192-207` | IC-05 | a corrupt-at-HEAD arm distinct from absent-at-HEAD (`returncode != 0`) | `[UNVERIFIED — measure]` |
| `_is_self_write_only_diff` | `implement_cores.py:388-446` | IC-05 | a corruption-diagnostic arm | `[UNVERIFIED — measure]` |
| `scan_inline_meta_reads` / `_extract_read_base` | `test_inline_meta_read_gate.py:589` / `:507` | IC-06 | the one-hop intra-module parse-helper anchor, plus `read_bytes` | `[UNVERIFIED — measure]`; also must hold `test_gate_runs_under_fast_tier_budget` (`:1229`) |

## Implementation Concern Map

*Include this section when the mission has multiple distinct architectural areas that inform how tasks are
decomposed.*

> **Note**: Implementation concerns are NOT work packages and are NOT executable units.
> `/spec-kitty.tasks` translates these into executable WPs — one concern may become
> multiple WPs; multiple small concerns may merge into one WP. Do not label concerns
> with WP-style IDs or sequencing language.

**Slicing rule, binding on every concern below.** A site's **routing + its `None` arm + its handler change
+ its ledger-row deletion is one indivisible edit**, owned by whichever concern routes it. This is what
`C-002` already mandated; the previous cut by *arm* violated it twice.

**Counting convention inside this map.** "Site" means **call site** (13 of them). "Ledger row" means a row
in `_ACCOUNTED_SITES` (12 of them, one with count 2). Where the two differ the text says which. This is the
same convention the bypass count now declares, applied consistently.

### IC-01 — Freeze the routing manifest, both floors, and the budget allocation

- **Purpose**: pin the 13 sites with their arm, handler and ledger row; the 6 handlers at `file:line`; the
  5-read/6-invocation bypass set with its convention; **both** live counts; and the per-concern routed
  allocation — before anything moves.
- **Relevant requirements**: `FR-002`, `NFR-002` (kept clause only), `SC-011`
- **Affected surfaces**:
  - `kitty-specs/meta-fail-closed-3162-01KZ7FSQ/contracts/routing-manifest.md` (new)
  - `kitty-specs/meta-fail-closed-3162-01KZ7FSQ/contracts/headroom-allocation.md` (new)
- **Sequencing/depends-on**: none. Every other concern depends on it.
- **Risks**:
  - The manifest must record the **predicate-symbol enumeration** that `NFR-002`'s surviving clause needs
    ("no new predicate answering *is this `meta.json` readable*"). Without a pre-list there is nothing to
    compare post against, and the clause closes by narration. **Enumerate the symbols, not the count.**
  - `ROUTED_CALLEES` matches callee **names**, not the call graph — it counts
    `doc_analysis/doc_state.py`'s *locally defined* `_require_meta`. The census is global over `src/`, so
    an unrelated commit anywhere that adds a call named `load_meta*` moves the number. The manifest must
    record the measurement **command and its input file count**, so a mid-mission drift is attributable
    rather than mistaken for this mission's doing. The gate's own header records **three** prior false reds
    from exactly this miscount.
  - The manifest is the only place the `[127,130]` band and the "126 is RED" two-sidedness are stated
    machine-readably. If it records a ceiling only, the downward failure mode returns.
- **Commit slices**: one commit. No source or test files.
- **Acceptance evidence**: `129` and `7` printed with their commands and input counts; the band derived
  from the three assertions of `test_routed_load_meta_floor` (`:1084`) quoted verbatim, not paraphrased.

### IC-02 — Route the 5 plain refuse-raw ledger rows (6 call sites)

- **Purpose**: the raw-escape sites that need no `None` arm raise `MissionMetaReadError` instead of a bare
  `ValueError`, each with its ledger row deleted in the same commit.
- **Scope, stated in both conventions**: **5 ledger rows / 6 call sites** across 4 files — census rows
  **4, 5, 6, 7, 10, 11**. `read_primary_meta` holds rows 10 and 11 under one ledger row with count 2. The
  7th refuse-raw site (row 8, `context/resolver.py`) is **not** here: it passes `allow_missing=False` and
  belongs to IC-03 with its `None` arm.
- **Relevant requirements**: `FR-001`, `NFR-001`, `SC-001`
- **Affected surfaces**:
  - `src/runtime/next/_internal_runtime/planner.py:188` (`_resolve_workflow_for_mission`)
  - `src/runtime/next/runtime_bridge_io.py:380` (`_workflow_runtime_template`)
  - `src/specify_cli/bulk_edit/gate.py:57` (`_is_bulk_edit_mission`), `:80`
    (`ensure_occurrence_classification_ready`)
  - `src/specify_cli/missions/_read_path_resolver.py:846` and `:862` (`read_primary_meta`, both reads)
  - `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` — delete rows at `:201`, `:202`,
    `:203`, `:204`, `:243`
  - new tests under `tests/next/`, `tests/runtime/`, `tests/specify_cli/bulk_edit/`, `tests/missions/`
  - **run-only, not edited**: `tests/status/test_aggregate_coord_deleted_contract.py:70-92`
- **Sequencing/depends-on**: IC-01
- **Risks**:
  - **Downward floor red.** Rows 10 and 11 are two calls in one function. Folding them into one routed call
    takes live routed to 128 in this lane and, combined with the mission's `+1`, still lands inside the
    band — but the *pattern* is exactly what produced three prior floor mismatches, and a second fold
    anywhere reaches 126, which is **RED**. Print the routed count pre and post; a delta of anything other
    than **0** stops the concern.
  - Tests must exercise **real corrupt files through the site's own public entry point**. Patching
    `load_meta_fail_closed` proves nothing: `SC-001` was satisfiable by leaving every read unrouted and
    wrapping the 7 public entries in `except ValueError: raise MissionMetaReadError(...)` — real corrupt
    file, real entry point, correct type, routed count unchanged, inline gate silent. Assert the read goes
    **through the seam** (the ledger row's disappearance from `scan_load_meta_call_sites` is that
    assertion, which is why the deletion is in the same commit).
  - **Row 11 is reachable — `Q7`'s "fixtures that do not exist" was unsupported.**
    `tests/status/test_aggregate_coord_deleted_contract.py:70-92` already drives `read_primary_meta`'s
    canonicalize-on-miss path with bare-`mid8`/full-ULID handles; writing corrupt JSON instead of valid
    reaches `:862`. `SC-001`'s denominator is **7/7**. Row 5 (`runtime_bridge_io.py:380`) needs a real
    repo-root/runtime-bridge fixture; its cost claim rested on no attempted construction either.
  - `runtime_bridge_io.py:102`, `planner.py:37` and `gate.py:17` import `mission_metadata` at module level.
    `core.paths` keeps a **load-bearing deferred import** of `mission_metadata` inside
    `load_meta_fail_closed` (`core/paths.py:665-670`) to avoid re-forming the cycle. Check each new import
    site individually for module-level vs deferred; do **not** "tidy" the deferred import.
- **Commit slices**: one commit per ledger row (5 commits), each = routing + ledger-row deletion + its
  test. Coupling D2.
- **Acceptance evidence**: routed count printed pre and post, **both 129**; `ruff check` and
  `mypy --strict` clean on the 4 files; the 5 deleted rows quoted from the diff;
  `tests/status/test_aggregate_coord_deleted_contract.py` green **without being edited** — if it needs
  editing, that is a behaviour change and the concern stops.

### IC-03 — Route the 3 `allow_missing=False` sites, one commit each, arm included

- **Purpose**: close the fail-open. `load_meta_fail_closed` returns `None` on absence where these three
  currently receive `FileNotFoundError`, so routing without the arm silently drops a guard.
- **Scope**: census rows **8, 9, 12**. Rows 9 and 12 are also the mission's **2 refuse-typed** sites, so
  their `except ValueError` handlers (`decisions/service.py:141`,
  `missions/_resolve_planning_branch.py:122`) are owned **here**, with their routing — not in a separate
  handler concern. That containment is the whole point: the previous cut routed these two in one concern
  and widened their handlers in the next, so the committed interval leaked
  `MissionMetaReadError` instead of `DecisionError` / `PlanningBranchResolutionFailed` — a direct `C-002`
  violation. Since refuse-typed ⊂ `allow_missing=False`, one concern removes both defects.
- **Relevant requirements**: `FR-003`, `FR-004`, `SC-003`, `SC-004`, and `C-002`
- **Affected surfaces**:
  - `src/specify_cli/context/resolver.py:75` (row 8) — the `or {}` at `:75`, the guard comment `:68-73`,
    the `except FileNotFoundError` arm `:91-93`, and `mission_id = feature_dir.name` at `:80`
  - `src/specify_cli/decisions/service.py:134` (row 9) + handler `:141`
  - `src/specify_cli/missions/_resolve_planning_branch.py:116` (row 12) + handler `:122` + the existing
    `None` arm `:127-131`
  - `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` — delete rows at `:215`, `:222`,
    `:244`
  - `tests/specify_cli/context/test_resolver.py` (`:256` already pins
    `MissingIdentityError, match="meta.json not found"`), `tests/specify_cli/decisions/`,
    `tests/missions/`, `tests/context/`
  - **run-only, not edited**: `tests/integration/test_coord_loop_workspace.py` (its `:611,:627` are
    docstring prose, not assertions — run it, never cite it as a pin)
- **Sequencing/depends-on**: IC-01
- **Risks**:
  - **The fail-open, verbatim.** At `context/resolver.py`, routing without the arm turns `or {}` from a
    mypy no-op into load-bearing control flow: absent `meta.json` → `{}` → `mission_id = feature_dir.name`
    (`:80`) → **a fabricated identity, silently**, and `MissingIdentityError` never raised. The comment at
    `:68-73` was written to forbid exactly that ("`allow_missing=True` … would MASK that guard and silently
    re-introduce the removed legacy tolerance"). **Routing and the `if result is None:` arm are one commit
    or the tree ships the regression the mission exists to prevent.** Coupling D3.
  - Rows 9 and 12 are the same shape with milder symptoms — the pre-existing arms raise the **same
    exception types with the wrong cause**: `decisions/service.py` says "has no mission_id field" instead
    of "meta.json not found"; `_resolve_planning_branch.py:127-131` says "not a JSON object" and is
    commented "Unreachable", losing the `--target-branch` remediation the `FileNotFoundError` arm carries.
    **`SC-004` must assert the message, not the type** — type-only guards are green at baseline, green
    after, and green under arm-deletion.
  - **One existing test pins row 8, and it was always inside the cone** — so the concern's own
    verification *would* have caught the fail-open. It is
    `tests/specify_cli/context/test_resolver.py:256` — **the sole pin**. The fail-open is still real and
    the per-site re-slice is still the fix; what is withdrawn is the claim that the cone hid it. (`test_coord_loop_workspace.py:611,627`
    is docstring prose, not assertions; it is run-only and is not a mutation-probe victim. Note this also
    means the cone under-declaration did **not** hide the fail-open — the real pin was always in-cone.)
  - **`except Exception` is banned at all 6 handlers**, not just these two. `MissionSelectorAmbiguous` is
    confirmed **not** a `ValueError` (`missions/_read_path_resolver.py:44`, plain `Exception`); a broad
    handler would swallow it.
  - **Dead handlers.** `except FileNotFoundError` becomes unreachable at all three rows —
    `load_meta_fail_closed` hard-codes `allow_missing=True`. Removing them is in scope: no requirement
    covered it, and both the charter review checklist and `CLAUDE.md` reject effect-free handlers.
- **Commit slices**: **one commit per site** (3 commits). Each = routing + the `if result is None:` arm
  carrying the missing-file message + the handler change (rows 9, 12) + the dead-handler removal + the
  ledger-row deletion + its test. Couplings D2, D3, D4 all land inside a single commit here.
- **Acceptance evidence**: routed count pre/post, both **129**; for each site the mutation probe of
  `SC-004` (delete the `None` arm, quote the failing assertion **naming the missing-file message**,
  restore); `SC-003`'s negative control that a **valid** file returns cleanly; the two run-only tests green
  and byte-identical.

### IC-04 — Route the 4 degrade sites and change their 4 handlers, routing first

- **Purpose**: preserve every fallback while the exception type changes underneath, with the intermediate
  escape as the red.
- **Scope**: census rows **1, 2, 3, 13**, and the 4 degrade handlers `resolution.py:514`, `:853`, `:1108`,
  `upgrade/feature_meta.py:43`. Plus `core/paths.py:648-651` per **R-2**.
- **Relevant requirements**: `FR-002`, `NFR-003`, `SC-002`, `SC-007`, and `C-002`
- **Affected surfaces**:
  - `src/mission_runtime/resolution.py` — row 1 `:509` (`_mid8_from_primary_meta`, degrade → `""`) with
    handler `:514`; row 2 `:852` (`_resolve_coordination_branch`, degrade → `None`) with handler `:853`;
    row 3 `:1107` (`_resolve_mission_id`, degrade → `legacy-<slug>`) with handler `:1108`
  - `src/specify_cli/upgrade/feature_meta.py:42` (`load_feature_meta`, degrade → `None`) with handler `:43`
  - `src/specify_cli/core/paths.py:648-651` — **R-2**: amend the docstring in the **same commit as the
    routing**. It currently names callers that "must stay deliberately silent about corruption … they are
    not routed here", which is precisely what these 4 sites do; leaving it makes the canonical authority
    document a client contract its own client set contradicts
  - `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` — delete rows at `:198`, `:199`,
    `:200`, `:249`
  - `tests/mission_runtime/`, `tests/upgrade/`, and the `SC-002` probe harness + a baseline worktree at
    `96494e5ec` (previously unowned)
- **Sequencing/depends-on**: IC-01
- **Risks — the sharpest in the mission.**
  - `MissionMetaReadError` is a **`RuntimeError`** (`core/paths.py:506`), so routing without the handler
    turns 4 silent fallbacks into 4 crashes, three of them on `spec-kitty` resolution paths.
  - **`resolution.py:514` is EXTENDED, not narrowed.** Its `try` also wraps
    `_canonicalize_primary_read_handle` and `_compose_primary_feature_dir`, whose traversal guard raises a
    real `ValueError`. `US2` scenario 3 as first written ("narrowed to `MissionMetaReadError`" ∧
    "traversal-guard behaviour unchanged") is satisfiable only by
    `except (MissionMetaReadError, ValueError)` — i.e. **not a narrowing**. Write the tuple.
    `SC-007` needs **two** assertions: a test that **trips the guard**, and a test that an ambiguous handle
    still propagates `MissionSelectorAmbiguous` (plain `Exception`, `_read_path_resolver.py:44`, raised
    *inside* the same `try`). `SC-007` was otherwise satisfiable by narrowing `:509` strictly and asserting
    `pytest.raises(ValueError)` on the guard — red at baseline, green after, criterion reported met, while
    the degrade-to-`""` behaviour `US2` scenario 3 protects is silently deleted.
  - **A degrade site's fallback may be derived from the malformed file.** Row 3 falls through to the
    `legacy-<slug>` sentinel; row 1 returns `""`. State per site whether the fallback is *derived* or
    *constant*, because a derived fallback can produce a plausible-but-wrong value.
  - **`SC-002` was satisfiable by feeding the probe malformed input only.** `NFR-003` demands **three**
    input shapes; `SC-002` named none, so the absent-file arm could regress untouched — the exact defect
    `NFR-003` was rewritten to catch. The harness must enumerate **4 sites × 3 shapes = 12 captured
    lines**, with the positive control first (break one handler, show the `diff` non-empty, quote it).
    A same-run double-print, or an empty diff over two empty captures, is not evidence.
  - **This concern's routing commit is on the `#2804` marker's live code path.** `merge/executor.py:116`
    imports `resolve_placement_only`, which reaches `_assemble_core_fragments` → `_resolve_mission_id`
    (row 3) and `_resolve_coordination_branch` (row 2). IC-07's evidence does not survive this concern
    landing; re-capture is IC-08's.
- **Commit slices — deliberately TWO commits, and this is the one exception in the mission**:
  1. **routing only** for all 4 sites + the `core/paths.py:648-651` docstring + the 4 ledger-row deletions.
     Quote the escaping `MissionMetaReadError` as the red.
  2. **handlers only** — the 4 `except` clauses changed to include `MissionMetaReadError`.

  See coupling D5 below: `C-002`'s "same edit" reads as "same **work package**" here, and only here.
- **Acceptance evidence**: routed count pre/post, both **129**; the routing commit's SHA with its red
  quoted; the handler commit's SHA green; `git log --oneline` showing the order; the 12-line `SC-002`
  capture pair with `diff` empty and both files at non-zero `wc -l`; the positive control quoted first.

### IC-05 — Make the bypass reads diagnosable, route the one gate-reachable site, and file `Q8`

- **Purpose**: a corrupt `meta.json` at a bypass site says so instead of hiding behind a generic
  dirty-worktree message; and the one site the widened gate can see is **routed**, which is what gives
  IC-06 a charter-compliant green landing state.
- **Scope**: the **5 read expressions / 6 invocation sites**. `ref_advance.py:247` is **routed** (R-1);
  the other four are **diagnosable-only** (`Q2`).
- **Relevant requirements**: `FR-005`, `C-004`, `C-009`, `NFR-002` (the seam-family record), and R-1
- **Affected surfaces**:
  - `src/specify_cli/git/ref_advance.py` — `_parse_meta_object:181-189`; `_committed_meta_object:192-207`
    with the `git show` read at `:203`; `_meta_change_is_vcs_lock_only:231-251` with
    `meta_path = worktree / path` at `:242`, `read_text` at `:244` and the parse at **`:247`**; the
    consumer at `:315`; `_is_vcs_lock_only_meta_change:210`; `_VCS_LOCK_META_FIELDS:42`
  - `src/specify_cli/cli/commands/implement_cores.py` — `_parse_meta_mapping:259`;
    `_committed_meta_mapping:330-338` with `show_blob` at `:335`; `_is_self_write_only_diff:388-446` with
    `source = (repo_root / Path(repo_rel)).resolve()` and `read_bytes` at `:421-427`;
    `_is_vcs_lock_only_meta_diff:241`; `_VCS_LOCK_META_FIELDS:50`
  - `src/specify_cli/cli/commands/merge_driver.py` — `_load_json_object:167`, its read at `:171`, its
    **two** invocations at `:243` and `:244`
  - `tests/architectural/tool_artifact_enrolment/registry/_is_self_write_only_diff.md` — **file-level
    surface**, not a `tests/architectural/` directory glob
  - **run-only, not edited**: `tests/specify_cli/cli/commands/test_implement_cores.py`,
    `tests/regression/test_issue_2795_claim_blocker.py`
- **Sequencing/depends-on**: IC-01. **IC-06 depends on this concern**, not the reverse.
- **Risks**:
  - **`:247` is the routed site and the routing is exact, not approximate.**
    `load_meta_fail_closed(meta_path.parent)` is correct there because the call at `ref_advance.py:315` is
    gated on `Path(path).name == _META_FILENAME`, so `meta_path.parent / "meta.json" == meta_path` by
    construction, same encoding. Verify the gate before relying on the identity; if it were absent the
    substitution would silently read a different file.
  - **This concern spends the mission's entire routed headroom** (129 → 130). Any further routed call
    anywhere reds `test_routed_load_meta_floor` upward at 131 against floor 126 + margin 4. Print pre and
    post; **+1 exactly**.
  - **`C-004`'s factual basis was wrong on two counts and the corrected version changes the work.**
    (i) **2 of the 5 hold real filesystem paths** — `ref_advance.py:242` and
    `implement_cores.py:421-427` (the latter under a `name == _META_JSON_FILENAME` gate). Both parents *are*
    feature dirs; the seam fits verbatim. The obstacle was the **routed budget**, not structure. Do not
    repeat "structurally cannot use the seam". (ii) **`_parse_meta_text` cannot serve the blob sites** — it
    takes a `Path` and performs the read itself (`mission_metadata.py:331-349`), so it cannot accept
    `git show` stdout (`str`) or `show_blob` output (`bytes`).
  - **Record the seam family, three tiers, and file the missing primitive** — this is the Charter Check
    "Partial" row's remedy: **L1** pure decode (`text|bytes → dict|None`, typed) — the **missing
    primitive, must be filed**; **L2** path-level (`_parse_meta_text`, exists, needs a public fail-closed
    entry for the temp-blob case, `merge_driver.py:167`); **L3** dir-level (`load_meta_fail_closed`,
    exists, reachable by 2 of the 5). Diagnosable-only remains the right *scope* call for the other four —
    resting on the budget, not on a false structural claim.
  - `_committed_meta_object` conflates absent-at-HEAD with corrupt-at-HEAD via `{}`, but its
    `returncode != 0` check **already separates them internally**, so a fail-closed variant is writable
    without losing the newly-added case. This note is correct as written; keep it.
  - `merge_driver.py:167` runs **as a subprocess** — `lanes/merge.py:84` registers
    `spec-kitty merge-driver-meta` for `kitty-specs/**/meta.json`. An edit there is invisible until
    `pip install -e .`. **Reinstall before capturing any evidence that crosses it**, and expect
    stale-install false reds otherwise.
  - **`Q8` is filed, not absorbed.** The lock-only comparison exists in **three** copies and
    `_VCS_LOCK_META_FIELDS` is declared twice (`ref_advance.py:42`, `implement_cores.py:50`), with two
    independent comparison functions (`ref_advance.py:210`, `implement_cores.py:241`). `C-009` had **zero**
    enforcement anywhere, and this concern edits exactly that code — the strongest pull toward absorbing
    it. File it (`DIR-024`), cite both declarations and both comparators, quote `gh issue view <n>`.
  - `FR-005` previously had **no success criterion**, so this concern was closable with zero evidence. One
    exists now: each bypass site against a **corrupt** fixture, asserting the message names `meta.json`
    **and the path**, controlled on the valid file.
- **Commit slices**:
  1. `ref_advance.py:247` routed (+1 routed call) with its test — the site R-1 assigns the headroom to.
  2. `ref_advance.py` remaining diagnosability (`_committed_meta_object`, `_parse_meta_object`).
  3. `implement_cores.py` diagnosability + the `_is_self_write_only_diff.md` registry note.
  4. `merge_driver.py` diagnosability (reinstall before evidence).
  5. Filings: `Q8`, and the L1 pure-decode primitive.
  No ledger rows are touched — `grep -c 'load_meta(' src/specify_cli/git/ref_advance.py` → 0, and
  `scan_load_meta_call_sites` matches the exact name `load_meta` only (`_TARGET`), so routing onto
  `load_meta_fail_closed` neither deletes nor adds a row here.
- **Acceptance evidence**: routed pre **129** / post **130**, floor still 126, all three clauses of
  `test_routed_load_meta_floor` quoted; 5 corrupt-fixture messages quoted with their valid-file controls;
  the two run-only tests green and unedited; `gh issue view <n>` for `Q8` and for the L1 primitive.

### IC-06 — Widen the gate, re-derive both floors, and give the control a positive twin

- **Purpose**: the floor test sees a delegated-parse read; the invisible shapes are deferred with a
  **non-vacuous** control rather than an allowlist entry that would be stale on arrival.
- **Relevant requirements**: `FR-006`, `FR-007`, `FR-008`, `NFR-004`, `SC-005`, `SC-006`, and R-1
- **Affected surfaces**:
  - `tests/architectural/test_inline_meta_read_gate.py` — the anchor move in `scan_inline_meta_reads`
    (`:589`) and `_extract_read_base` (`:507`, add `read_bytes`); `INLINE_META_READ_FLOOR` (`:127`);
    `FLOOR_MARGIN` (`:134`); `ROUTED_LOAD_META_FLOOR` (`:221`) and its margin (`:220`)
  - `tests/architectural/inline_meta_read_allowlist.yaml` — **declared unchanged**: 7 entries,
    `inline_meta_read_baseline` 7
  - `tests/architectural/_baselines.yaml` — register `inline_meta`, or file the register deviation
  - two new fixtures under `tests/architectural/` (**not** under `src/`), scanned by explicit argument:
    the unreachability control (`sites: 0`) and its **positive twin** (same scratch module, read inlined,
    path named `meta_path` → `sites: 1`)
- **Sequencing/depends-on**: **IC-05** (needs `ref_advance.py:247` routed). IC-01 transitively.
- **Risks**:
  - **The previous plan had no green landing state and named the wrong coupling.** Under diagnosable-only
    the widened scanner still flags `:247` — the widening exists to see `json.loads(param)` inside a
    private same-module helper fed by `meta_path.read_text()`, and diagnosability changes neither the
    `json.loads` in `_parse_meta_object` (`:181-189`) nor the call at `:247`. Live inline goes 7 → 8
    against a shrink-only ceiling of 7. The escape table, with controls first:

    | State | Result |
    |---|---|
    | widen, diagnosable-only | RED `test_inline_meta_read_floor` (`count <= 7`) + RED `..._green_against_seeded_allowlist` |
    | widen, `FLOOR → 8`, allowlist 7 | RED **`test_allowlist_matches_floor`** (`len(allowlist) == INLINE_META_READ_FLOOR`, an **equality**, `:1116`) |
    | widen, `FLOOR → 8`, allowlist 8, baseline 7 | RED `test_allowlist_shrink_only` (`:1125`) |
    | widen, `FLOOR → 8`, allowlist 8, baseline 8 | all green — **the re-freeze the charter forbids** |
    | **widen, site ROUTED (live back to 7)** | **all green** |

    `test_allowlist_matches_floor` is the assertion that forecloses the middle escape, and **no mission
    artifact mentioned it** (`grep -rn "matches_floor"` over the mission dir returned nothing).
  - **The allowlist closure is unconditional, not "impossible without bumping the baseline".**
    `test_allowlist_entries_are_still_live` (`:1166`) requires every entry to match a live **detected**
    site, so an entry for a scanner-invisible shape is stale on arrival and red at **any** baseline. An
    implementer reading the previous framing literally would have bumped the baseline, still been red, and
    then been tempted to weaken the staleness guard.
  - **`SC-005`'s control was vacuous.** A negative that prints `sites: 0` also prints `sites: 0` for a
    broken scanner. `architectural-gate-non-vacuity` forbids a negative with no positive twin. Both
    fixtures land in the same commit.
  - **Attribute the zero-false-positive count to clause 2, not clause 3.** Clause 3 rejects **one** of 19
    candidates; clause 2 rejects **17**. Stating clause 3 as the guard licenses a future widening of
    clause 2 that unlocks ~17 candidates with no measured protection. `C-005`'s "measure before adopting"
    survives on the number and failed on the reasoning.
  - `SC-006`'s previous "or made diagnosable → live returns to 7" branch is **false** and struck.
    Report the **widening delta** and the **code delta** separately: the ratchet cannot itself tell "the
    widening found a real site" from "a new unrouted read landed", and one number hides both.
  - **`SC-008`'s "passes on current `main`" was unrunnable as phrased** — the widened marker lives on the
    branch. The equivalent here: run the widened scanner against baseline `src/` at `96494e5ec` **and**
    branch head, both counts printed.
  - The widened scanner must stay inside `test_gate_runs_under_fast_tier_budget` (`:1229`).
- **Commit slices**: **one commit** for the widening + `INLINE_META_READ_FLOOR` + `FLOOR_MARGIN` +
  `inline_meta_read_baseline` + `ROUTED_LOAD_META_FLOOR` + both control fixtures. Coupling D1 — the three
  inline assertions are mutually locking and any one moving alone reds another. A second commit carries the
  `_baselines.yaml` registration (or the filed deviation) and `FR-007`'s deferral issue.
- **Acceptance evidence**: inline live printed pre and post the widening, **7 → 7** after `:247` is routed,
  floor 7, allowlist 7, baseline 7; the widening delta and code delta printed **separately**; the twin
  fixtures printing `sites: 0` and `sites: 1` in the same run; routed live printed pre and post the floor
  move with all three clauses of `test_routed_load_meta_floor` re-asserted at the new floor;
  `gh issue view <n>` for the deferral and the `_baselines.yaml` deviation.

### IC-07 — Re-pin #2804's two assertions and close the tracker honestly

- **Purpose**: one answer to one question, and the product defect owned rather than made to disappear.
- **Relevant requirements**: `FR-009`, `FR-010`, `FR-011`, `SC-008`, `SC-009`, `SC-010`, `C-006`
- **Affected surfaces**:
  - `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py` — **both** assertions under the one
    `# --- CONTRACT (RED on base) ---` banner, and the fixture rows at `:172-185`
  - **read-only, must stay byte-identical**:
    `tests/specify_cli/cli/commands/test_row_aware_merge_driver.py:427-448`
  - tracker: the superseding issue for #2804, and the pending-poisons-the-aggregate product defect with
    `src/specify_cli/acceptance/gates_core.py:525` cited
  - `tests/merge/` — cite (do not restore) `test_gate_artifact_merge_drivers_2804.py`, deleted in
    `b04da00e1` (−249 lines); it was the unit gate that held this invariant and no requirement owned it
- **Sequencing/depends-on**: none — **may start at any time.** But it is **not independent**, and its
  evidence must be **re-captured at final integration** by IC-08.
- **Risks**:
  - **The marker carries TWO red assertions, not one.** `overall_verdict == "pass"` **and**
    `SCAFFOLD_TODO_MARKER not in json.dumps(post_matrix)`. The second is false after the merge by a
    *different* mechanism: the row-union admits the scaffold row, whose `description` and `notes` **are**
    the marker (fixture rows `:172-185`). Measured through the reconciler, control first:
    `CONTROL filled fixture contains marker? False`; merged `criterion_ids: ['AC-001','FR-001','FR-003']`;
    `overall_verdict: pending`; `POST contains SCAFFOLD_TODO_MARKER? True`. **Widening only the verdict
    assertion cannot make `SC-008` pass.**
  - The second assertion's content **is** the real #2804 contract and is unsatisfiable by design under the
    row-union authority model — not merely stale. **Re-pin it, do not delete it**: to
    evidence-survival, `"<accepted-evidence-handle>" in json.dumps(post_matrix)`, negatively controlled
    against a take-theirs fixture. Measured: accepted evidence survives `True`; take-theirs control
    (placeholder alone) `False`.
  - **`SC-010` passed while the defect it exists to catch was fully present.**
    `overall_verdict ∈ {pass, pending, fail, pass_pending_consolidation}`
    (`acceptance/matrix.py:247-272`); the sibling test pins `pending`, so a widened predicate must admit
    it — and then "fails on some disallowed verdict" is satisfied by `verdict in {"pass","pending"}` plus a
    fixture with one `pass_fail: "fail"` row. **But the #2804 defect's own signature is `pending`.** The
    companion test must fail against **the defect's own fixture**, not against any disallowed value.
    `Q10` is settled **no — keep the marker**; `"fail"` is the concrete disallowed value, reachable from a
    one-criterion fixture (`matrix.py:259`). `IC-07` is therefore sizable, not a footnote.
  - **The product defect is not fixed here** (`C-006`) and must be filed with `gates_core.py:525` cited.
    Widening the pin without filing it makes a red go away without addressing what it pointed at.
  - Filing obligations: **≥5 are mandated across the mission and only 2 were pinned.** `SC-009` is a
    filing **register**, one row per obligation, each verified by `gh issue view <n>`.
  - **Two couplings make this concern's evidence perishable** — see IC-08. (i) IC-04's three
    `resolution.py` degrade sites sit on the path the marker exercises: the marker imports
    `_run_lane_based_merge`; `merge/executor.py:116` imports `resolve_placement_only`; AST-resolved that
    reaches `_assemble_core_fragments` → `_resolve_mission_id` (row 3) and `_resolve_coordination_branch`
    (row 2). (ii) IC-05 edits `merge_driver.py:167`, which runs **as a subprocess** inside the marker
    (`lanes/merge.py:84`), so the edit is invisible until `pip install -e .` — the documented
    stale-install false-red class. **`SC-008` captured in an IC-07-only lane is not evidence it still
    passes once IC-04 and IC-05 land.**
- **Commit slices**: (1) the verdict assertion widened, matched to the issue-matrix sibling's already-widened
  form; (2) the second assertion re-pinned to evidence-survival with its take-theirs negative control;
  (3) the companion `test_widened_2804_assertion_rejects_wrong_verdict` against the defect's own fixture;
  (4) the tracker filings.
- **Acceptance evidence**: both assertions quoted before and after; the reconciler measurement pair with
  its control; `git diff --stat upstream/main -- tests/specify_cli/cli/commands/test_row_aware_merge_driver.py`
  printing **nothing**, quoted; the companion test red against the defect fixture and green against the
  filled one; the filing register with `gh issue view <n> --json number,title,body` per row.

### IC-08 — Terminal integration verification, the sweep handshake, and the PR

- **Purpose**: re-capture the evidence that per-concern lanes cannot hold, and land the mission as one
  readable PR.
- **Relevant requirements**: `SC-006`, `SC-008`, `SC-010`, `SC-011`, `C-007`, `NFR-002`, charter Standing
  Orders 6, 7 and 9
- **Affected surfaces**: no owned source or test files — verification, coordination and the PR only.
  Read/run surface is the full 14-directory cone declared in Technical Context.
- **Sequencing/depends-on**: IC-02, IC-03, IC-04, IC-05, IC-06, IC-07 — all of them.
- **Risks**:
  - **IC-07's `SC-008` / `SC-010` evidence is stale by the time it merges.** Re-capture on the integrated
    tree, **after `pip install -e .`**, because `merge_driver.py` runs as a subprocess. A capture taken
    before the reinstall is a stale-install false red or a stale-install false green — both worthless.
  - **The routed and inline counts must be re-derived on the integrated tree**, not summed from per-lane
    numbers. `ROUTED_CALLEES` is global over `src/` and matches callee names, so an unrelated concurrent
    landing moves it. Expected: routed **130** (0-net from IC-02/03/04, +1 from IC-05) against the
    re-derived floor; inline **7**. Any deviation is attributed against IC-01's recorded command and input
    count before anything is "fixed".
  - **The `tests/sync` sweep-window handshake with mission 3167 (`C-007`) is this concern's, and it must
    happen before any broad sweep.** The mission's own cone contains neither `tests/sync` nor `tests/cli`,
    so the handshake is a guard against a broad sweep taking the window by accident. `pgrep -af
    'run_sync[_]daemon'` empty before each invocation.
  - **`SC-006`'s "the raise argued in the PR body"** is a PR-body deliverable, not a test. So is the
    separate reporting of widening delta vs code delta, and the `C-011` documented exception with its
    reviewer verification steps. If the PR body omits them the exception is undocumented and the row
    reverts to a violation.
  - Charter §Code Quality: linear history, logically sliced, independently reviewed **while still a
    draft**, DRAFT PR first, **the operator merges**. Do not squash IC-04's two commits — the ordering is
    the ATDD evidence.
  - `pytest` cone runs are targeted per charter §Testing Requirements; the full-suite gate is reserved for
    post-merge mission-level validation. Do not substitute a full run for the cone.
- **Commit slices**: no code. History compaction, rebase onto the current upstream base, DRAFT PR.
- **Acceptance evidence**: routed and inline counts on the integrated tree with commands and input counts;
  `SC-008`/`SC-010` re-captured post-`pip install -e .`; the 14-directory cone run with `N passed` quoted
  per directory and `^ERROR tests/` counted (not `^ERROR `); the filing register complete; the PR body
  carrying the argued raise, the two deltas, and the `C-011` exception.

## Atomicity couplings — all five

The previous plan flagged one and named the wrong tests for it.

1. **The widening + the floor/allowlist triple are ONE commit** (IC-06). The mutually locking assertions
   are `test_inline_meta_read_floor` (`:1061`), **`test_allowlist_matches_floor`** (`:1116`, an
   **equality**: `len(allowlist) == INLINE_META_READ_FLOOR`) and
   `test_inline_meta_read_gate_green_against_seeded_allowlist` (`:1109`). Any one moving alone reds
   another. The previously cited pair — `test_allowlist_shrink_only` +
   `test_allowlist_entries_are_still_live` — is not the bidirectional coupling; the equality is.
2. **Each routing + its ledger-row deletion are ONE commit** (IC-02, IC-03, IC-04). The exact-equality gate
   makes the "unaccounted" arm (`:292`) and the "stale row" arm (`:322-331`) pass and fail simultaneously,
   so a split commit is red in one direction or the other whichever way it is ordered.
3. **Each `allow_missing=False` site's routing + its `None` arm are ONE commit** (IC-03) — else fail-open
   at row 8, or the wrong cause at rows 9 and 12. This is the blocker the previous slicing shipped.
4. **Each refuse-typed site's routing + its `except` widening are ONE commit** (IC-03, rows 9 and 12) —
   `C-002`. `MissionMetaReadError` is a `RuntimeError`, so routing alone makes `SC-001` pass and `SC-003`
   fail: the wrapper leaks where `DecisionError` / `PlanningBranchResolutionFailed` is contracted.
5. **Deliberately NOT atomic — and this needs saying out loud.** The 4 degrade sites' **routing** and
   **handler** change are **two commits inside ONE work package** (IC-04). That is `FR-002`'s red-first
   device: the escaping `MissionMetaReadError` between the two commits *is* the red, and it is the only red
   available (`NFR-003` forbids a behaviour change, so no base-red can exist).

   **This is the single case where `C-002`'s "same edit" must be read as "same work package".** As written,
   `C-002` ("all six handlers must change in the same edit as their routing") and `FR-002` ("land the
   routing first and quote the resulting escape as the red, then change the handler") **contradict each
   other**, and an implementer would have picked one silently — most likely `C-002`, destroying the only
   red the requirement has. The resolution is: **commit granularity for rows 9 and 12 (coupling 4),
   work-package granularity for rows 1, 2, 3 and 13 (this coupling).** Nowhere else.

## Dependency graph

```
IC-01  (manifest / floors / budget allocation)
  │
  ├──> IC-02  (5 refuse-raw ledger rows = 6 call sites)
  │      └──> IC-03  (3 allow_missing=False sites, 1 commit each)
  │             └──> IC-04  (4 degrade sites + 4 handlers + R-2 docstring)
  │                          ^ lane B: SEQUENTIAL, forced union on the routing ledger
  │
  ├──> IC-05  (bypass diagnosability + ref_advance.py:247 routed, +1)
  │      └──> IC-06  (gate widening + BOTH floors re-derived)
  │                          ^ lane C: sequential, disjoint from lane B
  │
  └──> IC-07  (#2804 both assertions + tracker)  — lane D; startable as soon as IC-01
                                                    lands, evidence perishable

IC-02, IC-03, IC-04, IC-05, IC-06, IC-07  ──> IC-08  (terminal integration verify + PR)
```

**IC-02, IC-03 and IC-04 are a chain, not parallel siblings.** An earlier drawing of this graph put all three
on sibling edges from IC-01, which contradicted this plan's own lane table (`B | IC-02 → IC-03 → IC-04`) and the
file-collision matrix row for `tests/specify_cli/test_meta_fail_closed_full_census_contract.py`, whose three-way
write is exactly what forces the chain: the ledger is checked for exact equality in **both** directions, so
parallel siblings would each be green in isolation and collide at merge. `wps.yaml` declares the chain
(`WP03.dependencies: [WP01, WP02]`, `WP04.dependencies: [WP01, WP03]`), and the `owned_files` overlap on that
one file is legal **only** along that directed path (`src/specify_cli/ownership/validation.py:160-205`).

`IC-01 → IC-07` is also a real edge: IC-07 quotes IC-01's recorded routed-count measurement command verbatim.
It costs nothing to schedule — IC-01 is lane A with no source or test files and must land first regardless — and
it unions no lane, since IC-07's single file is disjoint from every other lane's.

Three edges the previous plan did not have, and one it had backwards:

- **IC-06 depends on IC-05**, because the only charter-compliant green state for the widened gate requires
  `ref_advance.py:247` to be **routed** (R-1). The previous plan had the gate concern depending on the
  bypass concern for the wrong reason (scope) and would have landed a widening with no green state.
- **IC-07 → IC-08 is a real edge**, not a courtesy. IC-07 is *startable* as soon as IC-01 lands and
  *verifiable* only at integration.
- **IC-01 → IC-07** — IC-07 consumes IC-01's measurement command verbatim; zero scheduling cost, no lane union.
- **IC-04 → IC-08** carries the marker's code-path coupling; **IC-05 → IC-08** carries the subprocess /
  stale-install coupling.

## File-collision matrix

Every file with more than one candidate owner, and the lane consequence. Files with a single owner are
omitted; the full map is in `## Project Structure`.

| File | IC-02 | IC-03 | IC-04 | IC-05 | IC-06 | IC-07 | Consequence |
|---|---|---|---|---|---|---|---|
| `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` | **W** rows `:201-204`, `:243` | **W** rows `:215`, `:222`, `:244` | **W** rows `:198-200`, `:249` | — | — | — | **Lane union.** Three concerns write one file, so the no-overlap guard puts IC-02+IC-03+IC-04 in **one lane**, sequential inside it. This is also correct on the merits: the ledger is checked for exact equality in **both** directions, so separate lanes would each be green in isolation and collide at merge |
| `tests/architectural/` (directory) | — | — | — | **W** `tool_artifact_enrolment/registry/_is_self_write_only_diff.md` only | **W** gate file, allowlist, `_baselines.yaml`, 2 fixtures | — | **No collision — provided IC-05's glob is file-level.** A directory glob unions the bypass concern with the gate concern for nothing. IC-05 and IC-06 are already dependency-sequential, so no lane is bought either way; the file-level glob is what keeps `tasks` from widening IC-05's ownership |
| `src/specify_cli/cli/commands/merge_driver.py` | — | — | — | **W** | — | **R** (subprocess, at runtime) | **No write collision.** IC-07 never edits it; it *executes* it via the installed console script. The coupling is evidence-freshness, discharged by IC-08's `pip install -e .` + re-capture |
| `src/mission_runtime/resolution.py` | — | — | **W** | — | — | **R** (via `merge/executor.py:116` → `resolve_placement_only`) | **No write collision.** Same evidence-freshness coupling, same discharge |
| `tests/status/test_aggregate_coord_deleted_contract.py` | **R** (run-only) | — | — | — | — | — | Run, never edit. If it needs editing, rows 10/11's behaviour changed and IC-02 stops |
| `tests/integration/test_coord_loop_workspace.py` | — | **R** (run-only) | — | — | — | — | Run, never edit. `:611`, `:627` are **prose**, not pins |
| `tests/specify_cli/cli/commands/test_row_aware_merge_driver.py` | — | — | — | — | — | **R** (must stay byte-identical) | `SC-008` asserts `git diff --stat upstream/main` prints nothing for it |

**Lane assignment justified by the matrix**

| Lane | Concerns | Why it may run in parallel |
|---|---|---|
| A | IC-01 | No source/test files. Must land first; nothing collides with it |
| B | IC-02 → IC-03 → IC-04 | Forced union on the ledger file. Source files are pairwise disjoint. **0-net routed**, so lane-local counts read 129/129 |
| C | IC-05 → IC-06 | Dependency-sequential. Files disjoint from lane B. **+1 routed**, the mission's whole headroom |
| D | IC-07 | Files disjoint from every other lane. Evidence re-captured in lane E |
| E | IC-08 | Terminal; no owned files |

Lanes B and C are safe in parallel **only because of the 0-net constraint**: each measures the routed count
in its own worktree, only C is non-zero, so each is individually green and the merged tree reads 130. If
lane B ever went non-zero — including **downward**, by folding rows 10/11's two calls into one — the merged
count would be wrong in a way neither lane's own gate run could see.

## `[UNVERIFIED]` items

Listed rather than guessed, per the standing rule that a number not measured on this tree is not a number.

1. **`ROUTED_LOAD_META_FLOOR`'s post-move value and the resulting band.** R-1 mandates re-derivation "to
   restore the established 3-below-live gap". At live **130** the gap rule gives **127**, and applying the
   band rule (`[FLOOR+1, FLOOR+MARGIN]`, which is how `[127,130]` follows from floor 126 / margin 4) gives
   **`[128,131]`**. Both values are **derived from the ruling's stated rule, not measured**. IC-06 must
   print the live count and derive the floor from it, never copy these.
2. **Every complexity-ceiling figure** in the Complexity Tracking register. No `ruff check --select C901`
   run was performed this pass; each cell is a measurement obligation on its owning concern.
3. **The exact line numbers of the new `None` arms, handler tuples and diagnostic arms.** Cited targets are
   the *current* lines; edits shift them. Cite by **symbol** (`C-003`), not by line alone, in the WPs.
4. **`ref_advance.py:203` vs the census's `:206`, and `:242` vs `:243`.** The analysis report cites `:203`
   (the `git show` read) and `:242` (`meta_path = worktree / path`); `research/3162-census.md` cites `:206`
   (the parse) and `:244` (`read_text`). These are adjacent lines in the same expressions, not a conflict,
   but the pair was never reconciled in one document. IC-01's manifest must pin one line per read
   expression and one per parse, in both conventions.
5. **`Q4`** (should the 4 degrade sites log when they degrade) remains an **operator** question, not a
   deliverable. It is `NFR-001`'s recorded residue, given an owner (IC-04's filing register) and an SC —
   but the *decision* is not made here. `Q11` likewise stays an operator question and is **struck from any
   concern's requirements list**: a concern cannot own an unanswered question as a deliverable. IC-05 owns
   the *scope call's consequence* (`merge_driver.py:167` is enrolled as the L2 case), not the question.
6. **Whether `inline_meta` should be added to `tests/architectural/_baselines.yaml` or the deviation
   filed.** The absence is verified (`grep -c` → 0); which remedy the charter's Burn-down Policy wants is
   a governance call IC-06 must put to the operator, with the two enforcing tests offered as the
   compensating control.

## Directive items I did not apply as written, and why

1. **"The 5 plain refuse-raw sites" is 5 ledger rows / 6 call sites, and I said so.** Applied, with the
   arithmetic made explicit rather than silently reconciled: 7 refuse-raw call sites − row 8
   (`allow_missing=False`, moved to IC-03) = **6 call sites**, which map to **5** `_ACCOUNTED_SITES` rows
   because `read_primary_meta` carries rows 10 and 11 under one row with count 2. Leaving "5" unqualified
   would have reproduced, inside the remediation, the exact convention-mixing the directive told me to
   declare per count.
2. **I did not create a separate refuse-typed concern**, and the suggested decomposition did not ask for
   one — but the reason needs recording because two of the six handlers live there.
   Refuse-typed (rows 9, 12) is a **subset** of `allow_missing=False` (rows 8, 9, 12), so folding them into
   IC-03 puts each site's routing, `None` arm and handler in one commit and satisfies couplings 3 and 4
   simultaneously. A separate refuse-typed concern would have re-created the `C-002` split the directive
   diagnosed, one layer down. All 6 handlers are owned: 4 degrade → IC-04, 2 refuse-typed → IC-03. Row 8's
   handler is `except FileNotFoundError`, not one of the 6 `except ValueError` handlers, and its removal is
   IC-03's.
3. **R-1's "re-derive both floors in the same change" is honoured at work-package, not commit,
   granularity**, and I flagged the ambiguity rather than resolving it silently. IC-05 routes
   `ref_advance.py:247`; IC-06 widens and re-derives both floors. Each step is independently green:
   routing alone takes routed 129 → 130 (inside `[127,130]`) and leaves inline at 7 because the *unwidened*
   scanner never saw `:247`; the widening then finds 0 new sites and both floors re-derive against a stable
   live count. Putting them in one commit would also work but would mix a `src/` behaviour change into the
   gate commit, which makes the widening-delta / code-delta separation `SC-006` demands harder to evidence,
   not easier. **If the operator intends literal same-commit, IC-05's first slice and IC-06's first slice
   merge — the concern boundary survives either way.**
4. **I did not assign the ledger file to a single owner**, which "Assign the file explicitly" could be read
   as asking. Three concerns route sites, and coupling 2 requires each routing commit to delete its own
   row, so a single owner would either serialise all routing behind one concern or violate coupling 2.
   Instead the file is explicitly listed in all three concerns' surfaces **with the specific row line
   numbers each deletes**, and the collision matrix states the consequence (one lane). That is explicit
   ownership at row granularity, and it is what the exact-equality gate actually requires.
5. **`Q11` is not listed as any concern's requirement**, per the analysis report's own ruling that "an IC
   cannot own an unanswered question as a deliverable". The previous plan had it in IC-04's Requirements
   list. IC-05 owns the consequence, not the question. Recorded under `[UNVERIFIED]` item 5 so it is not
   mistaken for dropped.
6. **Nothing in the directive was refused.** The four items above are scope clarifications with their
   reasoning recorded, not declined instructions.

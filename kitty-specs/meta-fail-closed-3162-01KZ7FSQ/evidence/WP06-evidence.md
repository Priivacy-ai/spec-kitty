# WP06 evidence — widen the gate, re-derive both floors, give the control a positive twin

**Out-of-map planning write, by declaration.** `kitty-specs/` paths cannot appear in `owned_files` by
construction (`mission_parsing.py:153-157`, `:207-215`), and `mark-status` carries no evidence field
(`WPInnerStateDelta.subtasks: Mapping[str, Status]`, `src/specify_cli/status/models.py:481`). This file is
WP06's committed evidence destination per its own prompt.

**Every coordinate below is stated as pre-edit or post-edit and was re-derived on the tree named.**

---

## Commits

| # | SHA | Contents |
|---|---|---|
| 1 | `172ec9aad` | **Coupling 1, atomically**: scanner widening (`read_bytes` + the one-hop anchor), `INLINE_META_READ_FLOOR`, `FLOOR_MARGIN`, `ROUTED_LOAD_META_FLOOR` + margin, both control fixtures, the `:103` header amendment, all new tests |
| 2 | `2b9b8ee13` | Converted the anchor-hop pin's `len(sites) == 1` so `tests/architectural` stays at its frozen golden-count ceiling of 25 |
| 3 | `085d47540` | Replaced the clause-attribution figures with measured ones (the prompt's figure was wrong — see Prompt defects) |

Parent of commit 1: `402c90c3c`. `git merge-base --is-ancestor 172ec9aad HEAD` → true.

**Files touched by WP06, union over all three commits** (nothing else, no sibling lane's files absorbed):

```
tests/architectural/_fixtures/unreachability_control.py
tests/architectural/_fixtures/unreachability_control_twin.py
tests/architectural/test_inline_meta_read_gate.py
```

`git show --name-only` over the three commits filtered to `^src/` → **NONE**. WP06 edits no file under
`src/`, so its routed delta is structurally 0.

---

## T034 — gate condition and PRE measurements

### The gate condition is MET: `ref_advance` is ROUTED, not merely diagnosable

The prompt cites the target as `ref_advance.py:247` inside `_meta_change_is_vcs_lock_only` (`:231`).
**Both coordinates moved under WP05's remediation and are re-derived here.** Post-edit, current tree:

```
$ grep -n "def _meta_change_is_vcs_lock_only\|worktree_meta = load_meta_fail_closed\|meta_path = worktree / path" src/specify_cli/git/ref_advance.py
260:def _meta_change_is_vcs_lock_only(
297:    meta_path = worktree / path
299:        worktree_meta = load_meta_fail_closed(meta_path.parent)
```

`src/specify_cli/git/ref_advance.py:299`, verbatim:

```python
        worktree_meta = load_meta_fail_closed(meta_path.parent)
```

`_parse_meta_object(worktree_text)` is **gone** from `_meta_change_is_vcs_lock_only`. The helper
`_parse_meta_object` still exists (`ref_advance.py:181`) and is still called once, at `ref_advance.py:220`
inside `_committed_meta_object` — with `result.stdout`, a `git show` subprocess stream, which the widened
scanner rejects at clause 2. That is routing, not diagnosability. **The escape table's only green row
holds; nothing was widened against an unrouted site.**

The chain-local exception hazard was checked and does not arise for WP06: WP06 changes no `except` arm and
no `src/` file, so it cannot change which exception escapes any call site. (WP02's committed chain-local
sweep instrument, `scripts/sweep_degrade_arms_on_routed_chain_3162.py`, was present in the working tree
mid-task and was destroyed by the incident below; WP06 had no need of it and did not substitute a
file-local grep for it.)

### PRE counts, WP01's recorded command verbatim

```
$ PYTHONPATH=<tree>/src .venv/bin/python scripts/verify_meta_routing_manifest_3162.py
  INPUT .py files walked: 1199
  ROUTED live (AST walk): 130
  INLINE live (AST walk): 7
  const INLINE_META_READ_FLOOR = 7
  const FLOOR_MARGIN = 2
  const ROUTED_LOAD_META_FLOOR = 126
  const ROUTED_LOAD_META_FLOOR_MARGIN = 4
  DERIVED routed band: [127, 130] (two-sided; 126 is RED)
  routed 130 in [127, 130]: OK
  inline 7 <= 7 and gap <= 2: OK
VERDICT: PASS      (exit 0)
```

**Band derivation from the three assertions of `test_routed_load_meta_floor`** (pre-edit `:1084-1105`),
with floor 126 and margin 4: clause 1 `len >= FLOOR`; clause 2 `len > FLOOR` **strict**; clause 3
`len - FLOOR <= MARGIN`. Admissible live values are therefore `[127, 130]` — **126 is RED**, because
clause 2 is strict and `126 > 126` is false while clauses 1 and 3 both pass. **The bound is two-sided:**
a *fold* collapsing two routed calls into one reds this gate from below, not only a drain from above.

### Constants recorded PRE

| Constant | Value | Coordinate (pre-edit) |
|---|---|---|
| `INLINE_META_READ_FLOOR` | 7 | `:127` |
| `FLOOR_MARGIN` | 2 | `:134` |
| `ROUTED_LOAD_META_FLOOR_MARGIN` | 4 | `:220` |
| `ROUTED_LOAD_META_FLOOR` | 126 | `:221` |
| `inline_meta_read_baseline` | 7 | `inline_meta_read_allowlist.yaml:19` |
| allowlist entries | 7 | via `load_allowlist` |

```
$ grep -c "inline_meta" tests/architectural/_baselines.yaml
0
```

`ruff check --select C901` PRE on the gate file → `All checks passed!` (ceiling 15).

The **7 live allowlist keys** `(file, qualname, token)` were captured to a file as T037's token-stability
baseline.

---

## T035 — the two control fixtures

Both under `tests/architectural/_fixtures/`, **neither under `src/`**, both stating that prohibition in
their own module docstring so a future editor cannot "tidy" them into `src/`.

Printed **in the same run** (`-s`), by `test_unreachability_control_is_zero_and_its_twin_is_one`:

```
tests/architectural/_fixtures/unreachability_control.py -> sites: 0
tests/architectural/_fixtures/unreachability_control_twin.py -> sites: 1
```

Scanned by **explicit argument** over `FIXTURES_DIR` and filtered to each fixture's own `rel_path`
(`_fixture_site_count`), so `_fixtures/bad_adapter.py` and `_fixtures/org_packs/**` cannot contribute.

The control carries **two** shapes: `_inlined_git_show_read` (research control `C3` verbatim, parse
inlined) and `_delegated_git_show_read` (the **post-widening repeat** — the one-hop anchor does reach that
delegated call site and then rejects it at clause 2). So the `0` is a measured statement about the widened
predicate, not just the old one.

`ruff check` clean on both fixtures. `mypy --strict` clean on both. Neither collected by pytest — the
gate-file run collects 53 items, all from `test_inline_meta_read_gate.py`; the leading-underscore
directory keeps `_fixtures/` out of collection.

`test_control_fixtures_are_not_under_src` additionally asserts no `unreachability_control` path appears in
the live `src/` census.

---

## T036 — the `read_bytes` synthetic pin

`_extract_read_base` (post-edit) now matches through a named constant:

```python
_READ_METHOD_NAMES: frozenset[str] = frozenset({"read_text", "read_bytes", "open"})
```

**Unit pin**: `test_read_source_base_direct_read_bytes`, beside the existing `..._direct_read_text` and
`..._direct_open_call`. **Observed RED before the change**: `E assert None is not None`.

**Scan-level pin**: `test_read_bytes_scan_level_pin_moves_one_to_two`, a `tmp_path` pair generated at
runtime. Printed in the run output, not only asserted:

```
read_bytes pin: read_text-fed module only -> sites: 1
read_bytes pin: + read_bytes-fed module -> sites: 2
```

**Observed RED before the change** at `1 -> 1` (`AssertionError: expected the measured 1 -> 2, got 1 -> 1`).

**No third fixture committed.** `git show --name-only` over the three WP06 commits lists exactly two files
under `_fixtures/`.

The "no red possible" exception is stated **in the test's own docstring** (charter `C-011` paired with this
spec's `C-008`), including why manufacturing a live red would be a `C-008` violation dressed as compliance.

---

## T037 — ONE commit for coupling 1

```
$ git show --stat 172ec9aad
 tests/architectural/_fixtures/unreachability_control.py      |  69 +++
 tests/architectural/_fixtures/unreachability_control_twin.py |  45 ++
 tests/architectural/test_inline_meta_read_gate.py            | 507 ++++++++++++-
 3 files changed, 600 insertions(+), 21 deletions(-)
```

That one commit carries the scanner change, `INLINE_META_READ_FLOOR`, `FLOOR_MARGIN`,
`ROUTED_LOAD_META_FLOOR`, its margin, and both fixtures.

### The real coupling, said out loud

**Earlier planning named the wrong pair here.** The older framing was
`test_allowlist_shrink_only` + `test_allowlist_entries_are_still_live`. The actual bidirectional lock is
the **equality** at `test_allowlist_matches_floor`:

```python
    assert len(load_allowlist(ALLOWLIST_PATH)) == INLINE_META_READ_FLOOR
```

An equality, not a bound — so the allowlist cannot grow *or* shrink without the floor moving in the same
commit, and the floor cannot move without the allowlist. That is what forces atomicity; the shrink-only
pair alone would not.

### The `:103` header amendment

Pre-edit, the comment ended *"it does no call-graph resolution, so a full transitive walk would be a
larger structural change than this landing fold warrants."* That became false. Post-edit it separates the
two scanners: the ROUTED census still does **no** call-graph resolution (which is why delegating wrappers
must be enrolled in `ROUTED_CALLEES` by hand), while the INLINE scanner now carries **one** bounded
intra-module hop, `_MAX_PARSE_HELPER_HOPS == 1`, that does not recurse and does not cross a module
boundary. A full transitive walk is stated as remaining out of scope.

### The widening, bounded in code

The hop fires only when direct clause-2 resolution has already failed, and only when **every** bound
holds: `fn` is a **module-level** `def` (`isinstance(parents.get(id(fn)), ast.Module)`), **private**
(`_`-prefixed), **single-parameter** (no `*args`/`**kwargs`/pos-only/kw-only, exactly one positional), the
argument is a bare `Name` naming that parameter, and the parameter is **never rebound** in the body. The
reported site is the **call site**, never the helper's `json.loads` line.

Eight bound tests pin what it must not reach: public helper; multi-parameter helper; call site passing a
non-read; call site whose read is not a meta.json path; class-level `staticmethod`; nested `def`;
parameter rebound before the parse; and a cross-module import. **These eight are green before the widening
too** — an unwidened scanner reports 0 for every shape in that family — so they are stated as *bounds*, not
as red-first evidence, both here and in their own docstring.

**The widening's red-first evidence** is
`test_anchor_hop_flags_private_same_module_parse_helper_call_site`: **observed RED** returning `[]` where
1 site is required (`AssertionError: expected the C2b shape to be reached, got []`), which independently
reproduces research control `C2b`'s measured 0.

### Allowlist declared unchanged, and verified

```
$ git diff --stat 402c90c3c HEAD -- tests/architectural/inline_meta_read_allowlist.yaml
(empty)
```

7 entries, `inline_meta_read_baseline: 7`. **No entry written for any scanner-invisible shape.**
`test_allowlist_entries_are_still_live` is **unedited** and green.

**`FR-007`'s closure is unconditional, and this is the reason.** That test compares each entry against
`_live_inline_meta_read_keys` — sites the scanner **detects**. An entry for a shape the scanner cannot see
matches no live key, so `staleness_twin_guard` returns it as stale and the test reds **on arrival, at any
baseline**. Raising `inline_meta_read_baseline` opens nothing; it only invites weakening the staleness
guard, which is the one move this WP must not make.

### Token stability

The 7 live keys re-derived post-widening and diffed against the T034 capture: **`diff` empty, byte-identical**
(37 lines each). Expected, and it is a *constraint* rather than a nicety: the anchor only moves for
unbound-parameter arguments and none of the 7 has one, and the hop is entered only after direct resolution
fails, so the pass is strictly additive. Had any token drifted, `matches_floor` and
`entries_are_still_live` would have red the widening. Keys were taken from the tool's own report, never
hand-typed.

### The five named tests, green on this commit

Selected 6, **6 passed** (`test_inline_meta_read_floor`, `test_routed_load_meta_floor`,
`test_inline_meta_read_gate_green_against_seeded_allowlist`, `test_allowlist_matches_floor`,
`test_allowlist_shrink_only`, `test_allowlist_entries_are_still_live`), exit 0.

---

## T038 — `ROUTED_LOAD_META_FLOOR` re-derived from the measurement

Measured, with the arithmetic printed:

```
INPUT .py files walked under <tree>/src: 1199
MEASURED live routed call sites: 130
MEASURED live inline reads     : 7

--- ROUTED floor derivation (growth ratchet, established 3-below-live gap) ---
  gap rule           : floor = live - 3
  arithmetic         : 130 - 3 = 127
  resulting floor    : ROUTED_LOAD_META_FLOOR = 127
  margin (unchanged) : ROUTED_LOAD_META_FLOOR_MARGIN = 4
  resulting band     : [FLOOR+1, FLOOR+MARGIN] = [128, 131]

--- three clauses at the NEW floor, operands shown ---
  clause 1  len(routed) >= FLOOR         : 130 >= 127 -> True
  clause 2  len(routed) >  FLOOR (STRICT): 130 > 127 -> True   <-- anti-vacuous; two-sided
  clause 3  len - FLOOR <= MARGIN        : 130 - 127 = 3 <= 4 -> True

--- the same three clauses at the OLD floor 126 ---
  clause 1: 130 >= 126 -> True | clause 2: 130 > 126 -> True | clause 3: 130-126 = 4 <= 4 -> True

--- INLINE floor derivation (CEILING ratchet: floor = live) ---
  floor  = live = 7  -> INLINE_META_READ_FLOOR confirmed 7
  gap    = FLOOR - live = 7 - 7 = 0
  margin : FLOOR_MARGIN = 2; admissibility 0 <= 2 -> True
```

The measured value is **127**. It **coincides with the unverified planning figure**; it was derived here
from the printed live count and the gap rule, and no planning artifact is its source.

**Why the move was necessary even though the gate was green.** At live 130 with floor 126 and margin 4 all
three clauses pass untouched — the gap had merely drifted out to exactly the margin, one routed call from a
false red. Nothing else in this WP forces the move, which is why "not 126" has to be asserted separately.

### Provenance (the criterion that cannot invert)

```
$ git show 172ec9aad -- tests/architectural/test_inline_meta_read_gate.py | grep '^[-+]ROUTED_LOAD_META_FLOOR'
-ROUTED_LOAD_META_FLOOR = 126
+ROUTED_LOAD_META_FLOOR = 127
```

**Both** the removed old value and the added new value print. **The committed value is explicitly NOT 126.**
Committed line, verbatim, post-edit coordinate:

```
tests/architectural/test_inline_meta_read_gate.py:294:ROUTED_LOAD_META_FLOOR = 127
```

Per the prompt, **no anti-copy grep for `127` / `[128,131]` was run over the gate file as a criterion** —
the 3-below-live rule *produces* 127, so that form is satisfied by skipping the work and unsatisfiable by
doing it. It belongs only to WP01, scoped to `contracts/`.

### Routed pre/post for WP06's own edits

**PRE 130 / POST 130, delta 0.** Structural, not coincidental: no WP06 commit touches any file under
`src/`. Post-change verifier reads the new floor and re-derives the band:

```
  ROUTED live (AST walk): 130
  const ROUTED_LOAD_META_FLOOR = 127
  DERIVED routed band: [128, 131] (two-sided; 127 is RED)
  routed 130 in [128, 131]: OK
  inline 7 <= 7 and gap <= 2: OK
VERDICT: PASS      (exit 0)
```

`SC-013` / `NFR-002`'s kept clause is argued, not re-enumerated: the predicate population under `src/` is
untouched by construction — WP06 edits nothing there — so no new local predicate can have been authored.

---

## T039 — two trees, two labelled deltas, re-measured budget

### The measurement trap this WP hit, and how it was corrected

A first pass imported the widened predicate from the main tree and pointed it at each worktree's `src/`.
It reported **inline 8 at branch head**, which looked exactly like "the widening found an unrouted read".
It was an artifact. `_rel()` derives `_REPO_ROOT` from **the gate file's own location** and falls back to
`path.as_posix()` when `Path.relative_to` raises, so on a foreign tree every `rel` is absolute,
`rel in EXCLUDED_REL_PATHS` silently stops matching, and `src/specify_cli/mission_metadata.py:348
(_parse_meta_text)` — the canonical reader's own implementation — is counted as a violation.

**Every number below was therefore re-taken with the predicate resident in the tree being measured**, so
`_REPO_ROOT` and the exclusion list resolve in-tree. Each run prints the predicate module's own
`__file__`, whether `_MAX_PARSE_HELPER_HOPS` is present, and the resolved `SRC_ROOT`, as a control against
measuring the wrong pair. The underlying fragility is filed as part of **#3241**.

The unwidened predicate is byte-identical at `96494e5ec` and at `402c90c3c` (`diff -q` → identical), so
the code delta is a clean fixed-predicate comparison.

### The matrix — 1 199 input `*.py` files in every cell

| tree | predicate | INLINE | ROUTED |
|---|---|---|---|
| `96494e5ec` (measurement baseline) | UNWIDENED | 7 | 129 |
| `96494e5ec` | **WIDENED** | **8** | 129 |
| branch head (`172ec9aad`) | UNWIDENED | 7 | 130 |
| branch head | **WIDENED** | **7** | 130 |

### Two deltas, separately labelled

- **Widening delta** (predicate change at a **fixed** tree): **+1 at `96494e5ec`** (7 → 8) and **0 at
  branch head** (7 → 7).
- **Code delta** (unwidened predicate, baseline vs head — the source change alone): **0** (7 → 7).

One number would hide both. The pair says something a single number cannot: the widening reaches a real
site, and the routing has already emptied it. Enumerated, the 8th site at the baseline is
`src/specify_cli/git/ref_advance.py:247 (_meta_change_is_vcs_lock_only)` — the exact site WP05 routed.

**The inline floor is NOT raised**, so the "code delta printed as 0 plus the raise argued in the PR body"
obligation does not apply; recorded here explicitly rather than left silent.

Live inline returns to **7** because WP05 routed the site. `SC-006`'s *"or made diagnosable → live returns
to 7"* branch is **struck as false**, and measured: with `_parse_meta_object` merely diagnosable the
widened scanner still flags the call site, which is the +1 at `96494e5ec`.

### Fast-tier budget, re-measured with seconds

`test_gate_runs_under_fast_tier_budget` own duration, from `--durations`:

```
9.66s call  tests/architectural/test_inline_meta_read_gate.py::test_gate_runs_under_fast_tier_budget
```

**9.66 s against the 30 s ceiling** — 32% utilised, ~20 s margin. **Not thin.** Per-scan split across the
resident-in-tree runs: inline scan 5.70–7.90 s, routed scan 1.63–2.25 s, both together 7.32–10.11 s. The
extra module-wide pass costs essentially nothing (head: unwidened 9.86 s vs widened 9.91 s, within
run-to-run noise) because the hop is entered only when clause 2 has already failed. **The ceiling was not
raised.**

### The cone

```
$ .venv/bin/python -m pytest tests/architectural -ra -p no:randomly
collected 1695 items
= 8 failed, 1683 passed, 2 skipped, 2 xfailed, 1 warning in 1800.64s (0:30:00) =
$ grep -c '^ERROR tests/'  ->  0
```

Selected **1695**. `-ra` used. No `tests/sync`, no `tests/cli` in any selection, at any point in this WP.
Output redirected to a file, never piped for an exit status. No run was killed.

`tests/architectural/test_inline_meta_read_gate.py` itself: all dots. Final dedicated run, selected 53,
**53 passed**, `^ERROR tests/` 0, exit 0.

### Attribution of all 8 cone failures — none is WP06's

**No WP06-owned file appears anywhere in the failure output** (grepped for `unreachability_control`,
`test_inline_meta_read_gate`, `_fixtures` across the whole FAILURES section: no match).

| Failure | Named files | Attribution |
|---|---|---|
| `test_gate_coverage::test_no_new_orphan_surfaces` | WP02's `tests/runtime/test_wp02_row05_bridge_io_fail_closed.py`, WP05's `tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py` | **Not WP06** — measured red at parent `402c90c3c` too, identical two files. Filed **#3241** |
| `test_golden_count_ban::test_convert_sites_do_not_exceed_frozen_baseline` | `tests/architectural: 26 > ceiling 25` | **WP06's own** — green at parent, red at `172ec9aad`. **Repaired in commit `2b9b8ee13`**, see T040/A3 |
| `test_next_shard_marker_completeness` ×2 | 11 tests in WP02's `tests/next/test_wp02_row04_planner_fail_closed.py` and `tests/runtime/test_wp02_row05_bridge_io_fail_closed.py` carry no shard marker | **WP02's** |
| `test_ci_collection_completeness`, `test_pytest_marker_convention`, `test_pytest_marker_correctness` (`git_repo` marker), `test_same_tier_uniqueness` | same WP02/WP05 files | **WP02's / WP05's** — same marker/shard root cause |

WP06 added no test file outside `tests/architectural/`, so none of the marker/shard/orphan failures can be
its. Nothing was retried to green and nothing was green-washed.

### Quality gates on changed files

`ruff check` → `All checks passed!`; `ruff check --select C901` → `All checks passed!` (ceiling 15, PRE and
POST both clean — the hop was extracted into `_sole_parameter_name`, `_unbound_helper_parameter`,
`_same_module_call_sites`, `_reads_meta_path`, `_site_at`, `_iter_json_parse_calls` precisely so
`_scan_file_for_inline_meta_reads` stayed under it); `mypy --strict` over all three changed files →
`Success: no issues found in 3 source files`. **`ruff format` was never run.**
`merge_driver.py:645`'s `no-any-return` was not touched.

---

## T040 — the governance surface

### Part A — the two CI ratchet baselines, checked by RUNNING the gates

**A1. Directories this mission adds a test file to.** Re-derived two ways, not from memory.

From the eight WPs' own `owned_files`/`create_intent` (**input: 8 WP prompt files**) — 16 directories:
`tests/specify_cli` (WP02/03/04, the ledger), `tests/specify_cli/bulk_edit` (WP02), `tests/next` (WP02),
`tests/runtime` (WP02), `tests/missions` (WP02, WP03), `tests/specify_cli/context` (WP03),
`tests/specify_cli/decisions` (WP03), `tests/context` (WP03), `tests/mission_runtime` (WP04),
`tests/upgrade` (WP04), `tests/specify_cli/git` (WP05), `tests/specify_cli/cli/commands` (WP05),
`tests/architectural/tool_artifact_enrolment/registry` (WP05, a `.md`), `tests/architectural` (WP06),
`tests/architectural/_fixtures` (WP06), `tests/regression` (WP07).

On the **merged-so-far** tree (`git diff --diff-filter=A 98198e980..HEAD -- tests/`): **13 files added**
across **10 directories** — `tests/architectural/_fixtures` (WP06 ×2), `tests/missions` (×2), `tests/next`,
`tests/runtime`, `tests/specify_cli/bulk_edit` (×2), `tests/specify_cli/cli/commands`,
`tests/specify_cli/cli/commands/agent`, `tests/specify_cli/context`, `tests/specify_cli/decisions`,
`tests/specify_cli/git`. `tests/context`, `tests/mission_runtime`, `tests/upgrade` and `tests/regression`
have **no added file yet** — WP04 has not started, and WP03/WP07 placed or edited elsewhere.

**A2. Orphan check — RUN, and RED. The inference was correct, and it is not WP06's.**

`_gate_coverage_baseline.json._comment`, verbatim: *"Gate-coverage ratchet baseline (Issue #2034 / #1933).
Frozen set of test FILES that contain >=1 test selected by zero CI gates — the visible #1931 worklist. **The
ratchet (`test_gate_coverage.py`) fails on any NEW orphan file not listed here.** Regenerate with:
`uv run python -m tests.architectural._gate_coverage --update-baseline`"*, with `"orphan_files": []`.

```
$ .venv/bin/python -m pytest tests/architectural/test_gate_coverage.py tests/architectural/test_golden_count_ban.py -p no:randomly -ra
collected 46 items
FAILED tests/architectural/test_gate_coverage.py::test_no_new_orphan_surfaces
E   AssertionError: 2 test file(s) are selected by ZERO CI gates and are not in the recorded baseline — they will never run in CI:
E       tests/runtime/test_wp02_row05_bridge_io_fail_closed.py
E       tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py
=================== 1 failed, 45 passed in 501.82s (0:08:21) ===================
```

Attributed by measurement, same selection at WP06's parent `402c90c3c`: **1 failed, 36 passed**, the
**identical two files**. So the red **pre-dates WP06**. The two orphans belong to **WP02** (row 5) and
**WP05** (diagnosability) — and the WP05 case is sharp: **WP05 is APPROVED on the strength of a test file
CI will never execute.**

**Not repaired here, by design (A5).** The gate's own prescribed fix is a marker on the *test file*, which
is another WP's surface. Regenerating the baseline would make the gate green by *recording* that two test
files never run, and the baseline's own text permits regeneration only *"If the coverage gap is intentional
and tracked"* — it is neither. Named the owning WPs and **filed #3241**, which also carries the likely
mechanism (an unmarked real-`git` test lands in no shard, because CI's fast shard selects with
`-m "... not (git_repo or integration)"`).

**A3. Golden-count check — RUN, RED, and this one WAS WP06's. Repaired in-surface.**

`_golden_count_baseline.json.$schema-note`, verbatim: *"Per-directory ceiling on non-escaped
`convert`-classified golden-count sites (FR-014/#2076). Regenerate via
`python -m tests.architectural.test_golden_count_ban --freeze-baseline` after a batch conversion lands;
never hand-edit except to record a documented decrease. **A directory absent here has an implicit ceiling
of 0 — any convert-classified site appearing there fails the guard immediately.**"*

Verified on this tree: the `ceilings` map **omits** `tests/regression`, `tests/missions`, `tests/context`,
`tests/mission_runtime`, `tests/upgrade` and `tests/merge` — all six as named. Checked against **every**
A1 directory: of the 10 with actually-added files, only `tests/missions` is among the omitted (implicit
ceiling 0, 2 files added by WP02/WP03). It did **not** trip: the violation reported was a different one.

The single violation was **`tests/architectural: 26 ... exceeds the frozen baseline ceiling of 25`** —
the directory WP06 edits. Attributed before fixing: **green at parent `402c90c3c` (9 passed), red at
`172ec9aad`.** Enumerating the 26 sites, three sit in the gate file, of which only one is new:

| Site | Verdict |
|---|---|
| `test_inline_meta_read_gate.py:1262 test_scan_routed_load_meta_calls_counts_call_sites  len(routed) == 2` | pre-existing, line-shifted only |
| `test_inline_meta_read_gate.py:1412 test_routed_count_floor_blocks_mass_allowlist  len(sites) == 2` | pre-existing, line-shifted only |
| `test_inline_meta_read_gate.py:1542 test_anchor_hop_flags_private_same_module_parse_helper_call_site  len(sites) == 1` | **WP06's, new** |

Repaired by **converting** the site (commit `2b9b8ee13`), which is the first remedy the file's own text
offers — not by re-freezing the baseline and not by annotating it `# golden-count: cardinality-is-contract`:

```python
    assert [s.key.enclosing_qualname for s in sites] == ["caller"], (
        f"expected the C2b shape to be reached at the CALL SITE exactly once, got {sites}"
    )
```

The qualname-list comparison pins both that exactly one site is reported **and** that it is reported at
the call site rather than the helper — strictly more than the cardinality did — and carries no line number,
so benign edits to the scratch module cannot move it (cf. `test_ratchet_positional_anchor_ban.py`).
Re-measured: `tests/architectural` back to **25**, **0** sites attributable to WP06; `test_golden_count_ban.py`
**9 passed**.

**A4. Which baselines WP06 changed: NEITHER. Recorded, not assumed.**

```
$ git diff --stat 402c90c3c HEAD -- tests/architectural/_gate_coverage_baseline.json
(empty)
$ git diff --stat 402c90c3c HEAD -- tests/architectural/_golden_count_baseline.json
(empty)
```

Both **byte-identical**. No regeneration command was run against either. "Nothing needed changing" is a
finding here, arrived at by running both gates: one was green after an in-surface code fix, the other is
red for a cause outside this WP's surface and is filed.

### Part B — `_baselines.yaml` and the filings

**The operator question is PUT, not answered.** `grep -c "inline_meta" tests/architectural/_baselines.yaml`
→ **0 before** (T034) and **0 after**; `git diff --stat` on that file → **empty**. WP06 did not touch it and
did not pick a remedy. **Filed as #3240**, stating both remedies (register with a `# justification:` comment
per the file's own per-PR edit policy, vs record the deviation), and offering the compensating control
explicitly: `test_allowlist_matches_floor` (the **equality**) and `test_allowlist_shrink_only` already
enforce shrink-only behaviour — the equality being strictly stronger than a `<= baseline` ratchet — plus
`test_allowlist_entries_are_still_live`, which evicts stale entries, a property a count baseline does not
provide at all. `test_ratchet_baselines.py` was not run as a gate on a change, because no change was made.

**`SC-009` register rows recorded** (numbers verified with `gh issue view <n> --json number,title,state,createdAt`):

| Row | Filing | Issue | Created (UTC) |
|---|---|---|---|
| **3** | `FR-007`/`NFR-004` deferral — 4 scanner-invisible bypass reads, **no allowlist entry possible at any baseline** | **#3239** | `2026-08-06T10:41:00Z` |
| **7** | `inline_meta` absent from `_baselines.yaml` — **open operator call** | **#3240** | `2026-08-06T10:41:19Z` |
| (A5) | Two files selected by zero CI gates (WP02, WP05) + the cross-tree `_rel()` over-count | **#3241** | `2026-08-06T10:41:46Z` |

All three `OPEN`. Sibling precedent: rows 4/6/8 = #3228/#3229/#3230 (WP05); rows 1/2 = #3231/#3232 (WP07).

**`NFR-004`'s denominator, as integers: 1 reached and routed / 4 deferred with a control / 0 allowlisted.**

The routing ledger `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` is **byte-identical**
across every WP06 commit (`git diff --stat 402c90c3c HEAD` → empty). No routing-ledger row touched.

---

## Incident — uncommitted work destroyed mid-task by a sibling lane

A sibling lane (WP03) ran `git reset --hard 664095fbd` in this shared tree, discarding WP06's uncommitted
edits to `tests/architectural/test_inline_meta_read_gate.py` (the file reverted to its 1235-line HEAD state
with `ROUTED_LOAD_META_FLOOR = 126`). The two `_fixtures/` modules survived, being untracked.

Every edit was reconstructed from this session's own authored content, then verified rather than assumed:
`ruff`, `ruff --select C901`, `mypy --strict` all clean, and the full gate file re-run to **53 passed**
before committing. **All counts in this document were re-taken after the reset** — the tree had also moved
to `402c90c3c`, folding in WP03's three routed swaps, and the re-measurement confirms those were 0-net
(routed still 130). Nothing here describes the destroyed tree. Work has been committed per-path
(`git add <path>`, never `-A`) at each coherent step since.

---

## Prompt defects and unachievable instructions

1. **`spec-kitty agent action implement WP06 --agent claude --mission …` refuses.** Exact error:
   `Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.` /
   `Reason: invalid_analysis_report_frontmatter: File has no frontmatter: …/analysis-report.md`. Worked from
   the repository root, which WP06's own prompt directs.

2. **The clause-attribution figure in the prompt is wrong, and it was propagated into a committed code
   comment before being caught.** The prompt states *"19 candidates → 17 rejected at clause 2 → 1 rejected
   at clause 3 → 1 accepted"* and requires the "clause 3 rejects exactly one" claim be stated. Measured on
   `96494e5ec`, it reproduces under **neither** available population definition:
   - anchor-hop candidates: **9 → 6 at clause 2 / 2 at clause 3 / 1 accepted** (the 1 being
     `ref_advance.py:247`, the expected control answer, so the population is the right one)
   - whole `json.loads` population: **150 → 92 / 51 / 7**

   So **clause 3 rejects 2, not 1**, and the prompt's replacement figure is of the same unreliable class as
   the "31 candidates, 30 rejected at clause 3" figure it was introduced to refute. Corrected in commit
   `085d47540`; the comment now names both populations with their arithmetic. **The load-bearing conclusion
   survives unchanged**: clause 2 dominates under both populations (6 of 8 rejections; 92 of 143), 0 false
   positives, so clause 2 is the clause to leave alone.

3. **"the twin's `sites: 1` is red before the widening and green after, which is `NFR-004`'s only
   achievable red" is false.** The twin as specified (read *inlined*, path named `meta_path`) is a plain
   clause-2+3 hit that the **unwidened** scanner already reports as 1 — research control `C2a` measured
   exactly that. Observed: the fixture test passed in the pre-widening run. The twin's real job is
   non-vacuity of the control, which it does. The widening's red-first evidence is instead the anchor-hop
   pin, observed RED at `[]`. Stated in the test's own docstring too, not only here.

4. **All `file:line` citations in the prompt's Context and T034/T037 sections for `ref_advance.py` are
   stale** (`:231`, `:242`, `:244`, `:247`; the helper at `:180-189`). Post-WP05-remediation the symbols
   are at `:260`, `:297`, `:299`, `:181`. Re-derived above. The gate file's own cited coordinates
   (`:61`, `:103`, `:127`, `:134`, `:220`, `:221`, `:507`, `:519`, `:549`, `:589`, `:604`, `:1061`,
   `:1084`, `:1109`, `:1116`, `:1125`, `:1136`, `:1166`, `:1229`) were all **correct pre-edit**.

5. **The verifier's default verdict is band-only**, as the dispatch note said and the prompt did not.
   `scripts/verify_meta_routing_manifest_3162.py` exits **0** on this tree and prints its four freeze-point
   snapshots as `DRIFTED … not graded — pass --freeze-check to grade`. The band line was used as the
   signal, and `--freeze-check` was deliberately not passed.

6. **`_MAX_ASSIGNMENT_HOPS` is at `:471` pre-edit as cited, but the prompt's claim that `FLOOR_MARGIN`
   would need re-deriving to a new value is not what the measurement supports.** The gap is 0 and any
   non-negative margin is admissible, so the measurement constrains the margin from below only; 2 is kept
   and the reasoning is recorded in the constant's own comment rather than silently preserved.

## Not measured / limitations

- **`--freeze-check` verdict**: not run. Deliberate — the freeze-point snapshots grade a tree the mission
  has moved past, and grading them would report progress as failure.
- **Whether the other 6 cone failures are pre-existing on the merge base `98198e980` or were introduced by
  WP02/WP05**: not measured. They are attributed as *not WP06's* on the strength of the files they name
  (all WP02/WP05, none WP06) plus the fact that WP06 adds no test file outside `tests/architectural/`.
  Distinguishing "pre-existing" from "sibling-introduced" among those 6 is the owning lanes' work, and the
  two I own responsibility for (`test_gate_coverage`, `test_golden_count_ban`) were both attributed by
  measurement at WP06's parent. `[UNVERIFIED]` as to which of those two sub-categories they fall in.
- **WP02's chain-local sweep instrument** was present in the tree mid-task and destroyed by the reset
  before WP06 needed it. WP06 has no exception-escape surface (no `except` arm, no `src/` edit), so nothing
  was substituted for it; this is a statement of non-applicability, not of coverage.

# WP03 — AST patch-seam census, shared resolver, control fixture

**Produced by**: WP03, agent `claude` / profile `python-pedro`
**Lane worktree**: `.worktrees/sync-sleep-count-3136-01KZ9B5A-lane-c`
**Lane branch**: `kitty/mission-sync-sleep-count-3136-01KZ9B5A-lane-c`

## Toolchain (captured before the first WP03 command)

```
$ date -u "+%Y-%m-%dT%H:%M:%SZ"
2026-08-07T01:20:19Z

$ command -v python pytest ruff mypy      # after prepending the repo-root .venv/bin
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/python
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/pytest
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/ruff
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/mypy

$ python -V      -> Python 3.12.13
$ pytest --version -> pytest 9.0.3
$ ruff --version   -> ruff 0.15.12
$ mypy --version   -> mypy 1.20.2 (compiled: yes)
```

Identical to WP01's pinned set (`notes/environment-3136.md` T001). **No `uv` subcommand of any
kind was executed by WP03** — not even `uv --version`. The lane worktree has no `.venv` of its
own; the repo-root venv is used by absolute path.

## R5 — the editable install resolves to the REPO ROOT, so every census run pins PYTHONPATH

```
$ python -c "import specify_cli; print(specify_cli.__file__)"                # UNPINNED
/home/jeroennouws/dev/sk-missions/3136/src/specify_cli/__init__.py           # <- repo root

$ PYTHONPATH=$PWD/src python -c "import specify_cli; print(specify_cli.__file__)"   # PINNED
/home/jeroennouws/dev/sk-missions/.../lane-c/src/specify_cli/__init__.py     # <- lane tree
```

This is load-bearing for WP03 specifically: the census classifies by **importing** the module
prefix a `patch()` target names, so an unpinned run would resolve `specify_cli.*` against the
repo-root tree — which is where **WP02 is concurrently editing `saas_client.py`**. Every census
invocation in this file is `PYTHONPATH=<lane>/src`.

---

## Refs and attribution

```
$ git rev-parse HEAD                      28bb40ac802596d8f3f62be343ccad2ddc014281 (pre-WP03-commit)
$ git merge-base HEAD main                1aed89411b50203c8dbd9b284d70cc8fefbf32fa
$ git merge-base --is-ancestor 98198e980 HEAD ; echo $?     0
```

**The ref used for mission-diff purposes is `98198e980`** (the mission's *diff base*). It is an
ancestor of HEAD, so diffs keyed on it stay valid. `1aed89411…` is the genuine merge base with
`main`; WP01 already recorded that "`98198e980` is the merge base" is a prompt defect, and this WP
re-derived both independently rather than inheriting them.

**Lane provenance.** `lane-c` was seeded from `98198e980` plus a planning-artifacts commit, so it did
**not** contain the recorded planning commit `4bdcb48f1`. `spec-kitty implement WP03` refused with an
actionable merge instruction; the merge was performed and all 10 conflicts — every one a planning
artifact under `kitty-specs/` — resolved to **ours**, because the lane snapshot is strictly newer
(its WP03 prompt is byte-identical to `feat/sync-sleep-count-3136` HEAD, while `4bdcb48f1`'s is
49+/28- behind). Net tree effect: append-only `kitty-ops` op logs. `src/`, `tests/` and `scripts/`
are identical across lane-c, `4bdcb48f1` and the mission head, so every number below is measurable
in this lane.

**`tests/sync` and `tests/cli` were NEVER run by WP03.** The census is a static `ast.parse()` reader.
The C-001 window was not acquired and was not needed.

---

## T014 — the shared resolver, exported from `check_patch_targets.py`

`resolve_patch_target(target, *, first_party_roots) -> PatchTargetVerdict`, with the verdict
vocabulary as a `StrEnum` (`PatchTargetOutcome`). **There is exactly one resolver**; the census
imports it and never re-implements the import walk.

All five outcomes exercised:

```
specify_cli.tracker.saas_client.SaaSTrackerClient    -> own_module     resolved=specify_cli.tracker.saas_client
specify_cli.tracker.saas_client.time.sleep           -> reach_through  resolved=time
subprocess.run                                       -> foreign        resolved=subprocess
specify_cli.sync.runtime.SyncRuntime.start           -> not_a_module   resolved=None
totally.bogus.module.attr                            -> unresolvable   resolved=None
nodot                                                -> unresolvable   resolved=None
```

**CLI invariance.** Baseline before any WP03 edit:

```
$ ./.venv/bin/python scripts/check_patch_targets.py
All 5052 patch() targets valid.        exit=0
```

Final, after the fixture landed:

```
$ ./.venv/bin/python scripts/check_patch_targets.py
All 5063 patch() targets valid.        exit=0
```

**Arithmetic: `5052 + 11 = 5063`.** The 11 are the fixture's literal `patch("…")` targets — 3 + 2 + 3
in the three case modules plus 3 in the decoy module (1 live decorator, 1 quoted in the docstring,
1 in a comment). Every one resolves, so the `[ENFORCED]` job stays at exit 0.

`validate()` was **not** re-expressed via the helper. The prompt permits that "**only if** its return
values are unchanged for every input", and they would not be: the verdict carries no
attribute-existence check (which `validate()` performs) and `resolve_patch_target` deliberately
ignores the `_SKIP_MODULE_PREFIXES` short-circuit so the census can classify `subprocess.run` as
`foreign` rather than skip it. The condition is unmet, so the rewrite was declined and the CLI path
left byte-for-byte equivalent in effect. Pure addition.

`ruff check` clean; `mypy --strict` → `Success: no issues found in 1 source file`.

---

## T015 — the classifier, and the declared first-party boundary

```json
"first_party_roots": ["charter","doctrine","glossary","kernel","mission_runtime",
                      "runtime","spec_kitty_events","spec_kitty_tracker","specify_cli","tests"],
"buckets": {"own_module": 357, "reach_through": 286, "foreign": 6,
            "not_a_module": 15, "unresolvable": 0},
"literal_predicate_flagged": 649
```

Total sites **664**. The literal FR-005 predicate would flag **649 / 664 = 97.7 %** — printed in
every report so the over-breadth cannot quietly disappear. The root set is derived from `src/`
subdirectories unioned with a declared extras frozenset, overridable via `--first-party-roots`, and
echoed into the payload.

**These reproduce the prompt's independent probe exactly (357 / 286 / 6 / 15 / 0).** `plan.md:838`'s
`356 / 286 / 7` is **wrong on two of three numbers** and would have been red on arrival.

### The one real bug this WP found in its own instrument — twice

Both were caught by Arm D/F going red, *not* by inspection, which is the whole argument for the
control test:

1. **`patch()` calls inside a function body were invisible.** The first walker only saw decorators,
   `with` items and module-level calls, so `return patch("…")` in a fixture helper
   (`tests/sync/test_sync_action_gate.py:184`) was dropped. That single miss moved three reported
   figures: 663→**664**, own_module 356→**357**, literal predicate 648→**649**. *The buggy version
   reproduced `plan.md`'s `356`.*
2. **Class-level `@patch` decorators were dropped** when class traversal was added
   (`TestSyncFeatureDossier`, 5 decorators): own_module 357→352. Restored to **357**.

---

## T016 — the read-side matcher

`./.venv/bin/python scripts/patch_seam_census.py tests/sync --contract` → **exactly four lines, in
true file order**:

```
test_saas_client.py::TestPolling::test_exponential_backoff_intervals  n=3  delays=[0.9, 2.0, 4.4]
test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after  n=1  delays=[3.0]
test_saas_client.py::TestRetryBehaviors::test_429_defaults_to_5s_when_missing  n=1  delays=[5.0]
test_saas_client_origin.py::TestSearchIssues::test_429_retries_then_raises  n=1  delays=[2.0]
```

Matches `spec.md:578-583` on all four nodes, both `n` values and all four delay sequences. Ordering
is by (file, first assertion line) — sorting by node name would put `:957` before `:937`.

- **One level of alias resolution is load-bearing and implemented transitively.** The canonical shape
  at `test_saas_client.py:783-786` needs two hops (`delays` → `sleep_calls` → `mock_sleep`); without
  it both `:784` and `:786` are missed entirely.
- **`side_effect=` sink tracking** confirmed: the patch is at `test_final_sync_diagnostics.py:303`
  and the assertion at `:309`. `plan.md`/`spec.md` both cite `:309` as the patch site; **`:309` is
  the assertion**. Recorded, keyed on the assertion line.
- **`n=` comes from the assertion's own cardinality expression.** The `in` form reports **`n=0`** —
  verified in the fixture at `seam_negative_cases.py:41` and pinned by Arm C. Deriving `n` from the
  printed delay list would report `n=1` honestly while asserting no cardinality at all.

`--contract` is scoped to the declared `--seam-module` (default
`specify_cli.tracker.saas_client`), echoed into `--json` as `seam_module`. The
`specify_cli.sync.batch` sleep seam at `test_final_sync_diagnostics.py:309` is a genuine
corruptible assertion but is **out-of-class** for SC-001's slice, so it appears in
`all_sleep_attr_assertions` (**6** over `tests/sync/`) and **not** in `corruptible_assertions`.
*(Amended 2026-08-07: this paragraph previously named `corruptible_assertions` as the list carrying
it, and quoted `6` as that list's size. `corruptible_assertions` is seam-scoped and is `5` pre-fix
and `0` post-fix; `6` has always been the unscoped `all_sleep_attr_assertions` figure.)*

**Contract lines are sourced from `sleep_assertions`, not `corruptible`.** Re-measured on the
composed tree the four lines above are **byte-identical** in both tree states. Sourcing them from
the verdict-filtered set — as the first shipped version did — would have emptied `--contract`
entirely the moment the retargets landed, because the four nodes are then all `own_module`. SC-002
pins the delay contract, which the retargets do not touch.

---

## T017 — three front doors, one analysis pass

All three modes run; renderers are dict-dispatched over one in-memory `CensusResult`. Exit **0** in
every mode — this is a reporter, not the gate.

`--siblings` is keyed on where a sibling seam is **read or driven**, not on the decorator line, and
is scoped to **`seam_patch_nodes`** — nodes that *patch* the seam (14 pre-fix / 15 post-fix) — rather
than `sleep_nodes`, nodes that *assert on* it (4 in both states).

**AMENDED 2026-08-07 (WP03 review). The block that stood here quoted evidence the committed census
could not produce.** It named `test_saas_client.py:804 … disposition=corruptible` in
`test_timeout_after_5_minutes`, and reported the vocabulary as `correct-by-alias 1 /
corruptible 10 / undisposed 2`. Re-running the *shipped* artifact over `tests/sync`,
`tests/sync/tracker` and `tests` produced **4 lines in all three scopes**, `:804` **absent**, and
`corruptible 2 / undisposed 2 / correct-by-alias 0`. Cause: `test_timeout_after_5_minutes`
(`:789-807` pre-fix) patches the seam but carries **no sleep assertion**, so the late re-scoping of
`sleep_nodes` onto assertion-carrying nodes dropped the whole function — and the evidence quoted
above it was never re-measured. **Absent is worse than `undisposed`:** a patched-but-unread sibling
is precisely what `undisposed` is a name for, and the narrower scope deleted the category's own
subject matter.

Re-derived from the committed artifact. Every scope now emits **24 lines**, identically for
`tests/sync`, `tests/sync/tracker` and `tests`:

```
# pre-fix (lane-c)
tests/sync/tracker/test_saas_client.py:787  TestPolling::test_exponential_backoff_intervals
    target=specify_cli.tracker.saas_client.secrets.randbelow  verdict=reach_through
    read=call_count  disposition=corruptible
tests/sync/tracker/test_saas_client.py:804  TestPolling::test_timeout_after_5_minutes
    target=specify_cli.tracker.saas_client.time.monotonic  verdict=reach_through
    read=side_effect_assignment  disposition=corruptible

# post-fix (composed lane-c+lane-b tree; the same two DoD slots, retargeted)
tests/sync/tracker/test_saas_client.py:800  TestPolling::test_exponential_backoff_intervals
    target=specify_cli.tracker.saas_client._randbelow  verdict=own_module
    read=call_count  disposition=correct-by-alias
tests/sync/tracker/test_saas_client.py:817  TestPolling::test_timeout_after_5_minutes
    target=specify_cli.tracker.saas_client._monotonic  verdict=own_module
    read=side_effect_assignment  disposition=correct-by-alias
```

Both DoD slots carry a **derived** disposition in both tree states, and `test_timeout_after_5_minutes`
is now visible — which is the whole point of scoping on `seam_patch_nodes`.

**The vocabulary is non-vacuous across the pre/post pair, and only across the pair.** Measured, all
three scopes, both trees:

| tree state | `corruptible` | `correct-by-alias` | `undisposed` | total |
|---|---|---|---|---|
| pre-fix (lane-c) | **10** | 0 | 14 | 24 |
| post-fix (composed) | 0 | **10** | 14 | 24 |

Stated honestly: on any **single** tree state one of the three outcomes is `0`, because the ten
`_monotonic`/`_randbelow` siblings move as a block from `reach_through` to `own_module` when the
retargets land — which is exactly the state change FR-012 exists to make. The fourteen `httpx.Client`
siblings are `undisposed` in both states and are the standing evidence that the category is real.
The earlier "all three reachable in one tree" claim was not measurable and is withdrawn.

---

## T018 — the committed control fixture

`tests/architectural/_fixtures/patch_seam_control/` — **no `__init__.py`**, four non-`test_` modules
(so pytest never collects them):

| Filename | Role |
|---|---|
| `seam_decorator_cases.py` | 3 decorator positives incl. the `:783-786` two-hop alias shape |
| `seam_contextmanager_cases.py` | the 2 forms R1 could not see: context-manager + `side_effect=` sink |
| `seam_negative_cases.py` | own-module patch, monotonic-only node, and the `in` form (`n=0`) |
| `seam_decoy_cases.py` | the 3 decoys — docstring, comment, bare string literal — plus 1 live seam |

Hand-derived ground truth (written while writing the fixture, **not** transcribed from `spec.md`):
**9** AST patch sites; buckets own_module 1 / reach_through 8 / foreign 0 / not_a_module 0 /
unresolvable 0; **7** sleep-seam sites; **7** sleep nodes; **8** corruptible assertions; **1**
monotonic-only node.

**The grep gap, which is the point of the fixture:** naive `grep 'patch('` over the directory counts
**16**; the AST census counts **9**.

`ruff check` clean. `check_patch_targets.py` exit **0**.

---

## T019 — the control test, seven arms

`tests/architectural/test_patch_seam_census_control.py`, `pytestmark = [pytest.mark.architectural]`,
consuming the census **only by subprocess over its CLI** — no `sys.path` insertion, no `# noqa: E402`.

**Red first, and red for the right reason.** Before the census existed, 8 collected / **8 failed**,
every one on:

```
census exited 2 ... can't open file '.../scripts/patch_seam_census.py': [Errno 2] No such file or directory
```

Green after: **`8 passed`**, 8 collected.

- **Arm A** — patch sites, corruptible assertions and sleep nodes vs hand-derived truth.
- **Arm B** — the 3 decoys contribute nothing; grep(16) > census(9).
- **Arm C** — the `in` form reports `n=0`.
- **Arm D** — buckets over `tests/sync/` pinned as a frozenset **including `unresolvable: 0`**, so a
  thinner environment cannot shrink the flagged set for free.
- **Arm E** — self-mutation: `--only-forms decorator` must lose exactly
  `{(seam_contextmanager_cases.py, 32, 4), (seam_contextmanager_cases.py, 41, 2)}`. Driven by an
  **injected CLI parameter**, never by editing the shipped file.
- **Arm F** — AST ⊇ regex after removing prose spans, exception set **derived** from each file's own
  string-literal and comment spans.
- **Arm G** *(added 2026-08-07, WP03 review)* — an `own_module` sleep seam is counted in
  `sleep_assertions` and is **not** corruptible.

**`len(x) == N` appears nowhere**; every arm asserts frozenset equality. The
`tests/architectural` golden-count bucket is at 25/25 with zero headroom —
`test_golden_count_ban.py` re-run after Arm G: **9 passed**.

### AMENDED 2026-08-07 (WP03 review) — Arms D and F were red on arrival at consolidation

Both arms pinned figures measured on the lane they were written in. Neither survives WP02:

| arm | pinned in lane-c | actual post-fix |
|---|---|---|
| D | `own_module 357 / reach_through 286` | **384 / 264** |
| F | `{test_sync_doctor.py:33, test_saas_client.py:559, :659, :669}` | `{test_sync_doctor.py:33, test_saas_client.py:562, :668, :678, test_sleep_attribution_guard_3136.py:5}` |

Keying Arm F on `(file, line)` rather than the target string did **not** immunise the pin — WP02
edits the very docstrings those lines sit in, so every line moves and a fifth file appears.
`residual-ledger.md:448-449` had already predicted exactly this. *A hand-transcribed line pin is not
a contract; it is a snapshot.*

- **Arm D now discriminates on tree state.** `_tree_state()` reads `saas_client.py`'s own AST for a
  module-scope binding of `_sleep` — not by import (this file imports nothing from `specify_cli`)
  and not by grep (`_sleep` appears in that module's prose in both states). It selects between two
  **measured** tables, and asserts the two tables differ, so a discriminator that mapped both states
  onto one figure cannot pass.
- **Arm F's exception set is now derived**, not transcribed: every regex-only hit must fall inside a
  string-literal or comment span computed from the file's own `ast` constants and `tokenize`
  comments. It also asserts the regex-only set is **non-empty**, so the arm cannot pass by the
  cross-check silently ceasing to compute. A genuine divergence — a live `patch()` the AST walker
  missed — is by definition *not* inside prose, so the arm still fails on the thing it exists to
  catch. Verified against both tree states: all 4 pre-fix hits and all 5 post-fix hits are explained.

**Both states verified end to end.** `tests/architectural/test_patch_seam_census_control.py` →
**9 passed** on lane-c, and **9 passed** on the composed lane-c + lane-b tree.

### Arm F — the restated cross-check, measured

`plan.md:846-847`'s plain-superset wording is **false on the base tree**. Measured: AST **664**,
regex **667**, with **4 regex-only** and **1 AST-only**. The identity closes:
`664 − 1 (AST-only) + 4 (regex-only) = 667`.

| Direction | Site | Why |
|---|---|---|
| regex-only | `tests/sync/test_sync_doctor.py:33` | inside a docstring |
| regex-only | `tests/sync/tracker/test_saas_client.py:559`, `:659`, `:669` | inside a docstring |
| AST-only | `tests/sync/test_dossier_trigger.py:54` | a comment sits between `patch(` and the target |

All four regex-only hits are docstrings, which NFR-007 **requires** the AST to exclude.

~~The pin is keyed on `(file, line)` and never on the target, because **WP02 T009 rewrites `:559`'s
target string**; a target-keyed pin is green in both lanes alone and breaks only at
consolidation.~~ **SUPERSEDED 2026-08-07 (WP03 review).** Moving from a target-keyed pin to a
line-keyed pin traded one snapshot for another: WP02's edits move all three `test_saas_client.py`
lines and add a fifth file. The arm no longer transcribes a set at all — see the amendment under
T019. Post-fix, measured on the composed tree, the derived rule explains all five regex-only hits:
`test_sync_doctor.py:33`, `test_saas_client.py:562`, `:668`, `:678`, and
`test_sleep_attribution_guard_3136.py:5` (WP02's guard module docstring, the RL-014 prose).

---

## T020 — census on both trees, and the two ratification flags

Both runs used the same interpreter, printed per run:

```
$ ./.venv/bin/python -V     ->  Python 3.12.13      (lane-c working tree, pre-fix mission head)
$ ./.venv/bin/python -V     ->  Python 3.12.13      (98198e980, detached worktree)
```

### `files_scanned`, per scope, labelled

| Scope | Count | Command |
|---|---:|---|
| `tests/sync/` recursive — **the scanned set** | **141** | `find tests/sync -name '*.py' \| wc -l` |
| `tests/sync/tracker/*.py` — sub-denominator only | **22** | `ls tests/sync/tracker/*.py \| wc -l` |

### ⚑ RATIFICATION 1 — SC-001's `files_scanned: 22`

**`[NEEDS RATIFICATION]`, not silently picked.** SC-001 mandates a `tests/sync/` scan (**141** files)
while pinning **22**, the number a *narrowed* `tests/sync/tracker/` scan produces — and a narrowed
scope is BLOCKER-2's exact failure. The census reports **both, labelled**. The operator ratifies.

### ⚑ RATIFICATION 2 — `sleep_patch_sites: 14`

`14` counts occurrences of the literal `specify_cli.tracker.saas_client.time.sleep`; after FR-012's
retargets **0** match, so a correct implementation would report `0` and fail. Implemented as
**`sleep_seam_patch_sites`**, matching `…saas_client.time.sleep` **or** `…saas_client._sleep`.
Measured pre-fix (lane-c): **14**.

**AMENDED 2026-08-07 (WP03 review). Post-fix it is 16, not 14 — and the difference is not drift.**
"14 in either tree state" was asserted by construction and never measured against a post-fix tree.
Measured on the composed lane-c + lane-b tree (`git diff --name-status lane-c lane-b -- tests/sync
src` is exactly WP02's four files, so that tree is a faithful prediction of consolidation):

```
                                            pre-fix   post-fix
test_saas_client.py        _sleep / time.sleep   13         13
test_saas_client_origin.py:229                    1          1
                                              ------     ------
the invariant WP02 preserves                     14         14
test_sleep_attribution_guard_3136.py:158  _sleep   —         +1
test_sleep_attribution_guard_3136.py:157  time.sleep (live, pre-fix form — RL-014)
                                                  —         +1
                                              ------     ------
census sleep_seam_patch_sites                    14         16
`seam_patch_nodes`                               14         15
```

**The 14 is invariant exactly as designed; the +2 is WP02's guard.** Both extra sites live in
`_dual_recorder_window`, which patches the alias *and* the pre-fix stdlib target in the same `with`
block on purpose — that dual recorder **is** SC-004 arm (b)'s instrument. `seam_patch_nodes` rises by
only 1 because both sites sit in that one node.

**Scoping decision handed to WP05, not just a number.** `sleep_seam_patch_sites` counts *the
mission's own guard* alongside the production test surface it grades. WP05 must choose, and say
which it chose:

- **`16` — unscoped.** Honest about what is on the tree. Rises again if any later WP adds another
  guard, so it grades the mission's own output, not the codebase's.
- **`14` — guard-excluded.** The invariant the criterion was written to express. Requires excluding
  `test_sleep_attribution_guard_3136.py` **by construction** (e.g. a declared `--exclude` scope
  echoed into `--json` the way `first_party_roots` and `seam_module` already are) and **never** by a
  hardcoded filename list inside the census — a hardcoded exclusion is the exact vacuity this
  instrument exists to prevent.

This is the same trap RL-014 already set for arm 4c: *size the count against the instrument you
actually ship, and name the scope before naming the number.*

**The composition was NOT re-adjudicated and `spec.md` was NOT edited.** `spec.md:504` already
carries the corrected composition — 14 live = 13 in `test_saas_client.py` + 1 at
`test_saas_client_origin.py:229`, docstrings excluded — and explicitly retires the earlier
"13 live + 1 docstring" reading. Verified against that composition:

```
full dotted target string, bare grep      15   (13 live + :559 and :715, both prose)
live decorator form, line-anchored        13   test_saas_client.py
live decorator form, line-anchored         1   test_saas_client_origin.py:229
census sleep_seam_patch_sites             14   AST, docstrings excluded (pre-fix)
```

Both prose lines sit inside **one** docstring spanning **`513-762`** (AST-verified).

**AMENDED 2026-08-07 (WP03 review). The claim that a stale restatement survives at `spec.md:566-567`
is itself false, and is withdrawn.** Re-read verbatim, `spec.md:566-567` carries the **corrected**
composition — *"which is **14** pre-fix (13 in `test_saas_client.py` + 1 in `…_origin.py:229`, per
`:504`) and **14** post-fix"* — landed by `91255f6da` ("repair 25 drifted citations and close the
last spec contradiction"). There is nothing stale there. Left standing, this note would have sent a
later WP to "fix" a non-defect in a spec that is already right.

### The non-tracker `tests/sync/` instances — measured **10**, not 9

`spec.md:557` and `:967` say **9**. **The AST census finds 10**, corroborated by independent grep
(2 + 8):

| `file:line` | Target | Disposition | Reason |
|---|---|---|---|
| `tests/sync/test_final_sync_diagnostics.py:260` | `specify_cli.sync.batch.time.sleep` | `out-of-class` | `sync.batch` seam, not `saas_client`; outside C-004's permitted change set |
| `tests/sync/test_final_sync_diagnostics.py:303` | `specify_cli.sync.batch.time.sleep` | `out-of-class` | same seam; `side_effect=` sink feeding the assertion at `:309` |
| `tests/sync/test_reconnection.py:119` | `specify_cli.sync.client.asyncio.sleep` | `out-of-class` | `sync.client` async seam, different module and different sleep primitive |
| `…:137`, `…:151`, `…:169`, `…:187`, `…:206`, `…:241`, `…:269` | `specify_cli.sync.client.asyncio.sleep` | `out-of-class` | as above (7 further sites) |

**Total 10.** All ten are context-manager form, which is exactly why R1's decorator-only census saw
none of them. The likely origin of `9` is counting only `:303` (the `side_effect` sink discussed in
the analysis) and missing `:260`, the plain context-manager patch in the same file. **Recorded, not
fixed** — T020 step 6 forbids editing `spec.md`.

### Both trees, same interpreter — the pre-fix baseline

The base tree was materialised as a throwaway detached worktree and removed afterwards
(`git worktree remove /tmp/wp03-base-98198e9` → exit 0). **The R5 pin was verified per run**, not
assumed: `PYTHONPATH=/tmp/wp03-base-98198e9/src` resolved `specify_cli.__file__` to
`/tmp/wp03-base-98198e9/src/specify_cli/__init__.py`, so the base arm genuinely measured the base
tree rather than the editable install's repo-root checkout.

| | `98198e980` (diff base) | lane-c pre-fix head |
|---|---|---|
| `./.venv/bin/python -V` | **Python 3.12.13** | **Python 3.12.13** |
| `files_scanned` (`tests/sync/`) | 141 | 141 |
| `own_module` | 357 | 357 |
| `reach_through` | 286 | 286 |
| `foreign` | 6 | 6 |
| `not_a_module` | 15 | 15 |
| `unresolvable` | **0** | **0** |
| total sites | 664 | 664 |
| `literal_predicate_flagged` | 649 | 649 |
| `sleep_seam_patch_sites` | 14 | 14 |

**Identical, and that is the expected result, not a null finding:** WP01 changed no code, and
`src/`, `tests/` and `scripts/` are byte-identical between `98198e980` and this lane. A delta here
would have meant contamination.

### SC-001's denominators — both tree states, both measured

```
                              pre-fix   post-fix     SC-001 requires
nodes_with_sleep_assertions:      4         4        4, must not move
sleep_assertions:                 5         5        5, must not move
corruptible_assertions:           5         0        5 -> 0
sleep_seam_patch_sites:          14        16        (see RATIFICATION 2)
```

Pre-fix nodes (identical post-fix, line numbers shifted by WP02's prose edits):

```
    TestPolling::test_exponential_backoff_intervals
    TestRetryBehaviors::test_429_respects_retry_after
    TestRetryBehaviors::test_429_defaults_to_5s_when_missing
    TestSearchIssues::test_429_retries_then_raises
```

The four nodes are exactly SC-002's four. **These denominators are scoped to the `saas_client`
slice**, which is what `spec.md:556-557` says they are; the wider unscoped view is reported
alongside as `all_sleep_attr_nodes` (24 pre / 26 post) and `all_sleep_attr_assertions` (6, both).

**AMENDED 2026-08-07 (WP03 review). Two scoping bugs, found in two different ways.**

1. Found in-WP, pre-fix: `nodes_with_sleep_assertions` initially reported **14** because it was
   derived from nodes that *patch* the seam rather than nodes that *carry a sleep assertion*. 14
   nodes patch it; only 4 read it.
2. Found at review, post-fix only: `sleep_assertions` and `corruptible_assertions` were **rendered
   from the same expression**, so they could never differ — and `corruptible` consulted only node
   membership, never the resolver verdict. On the pre-fix tree both faults are invisible, because
   every seam site there happens to be `reach_through` and 5 == 5 is the right answer by accident.
   On the post-fix tree the pair reported **5 / 5** where SC-001 requires **5 / 0**, and
   `nodes_with_sleep_assertions` would have collapsed to **0** had `corruptible` alone been fixed.

   `sleep_assertions` is now verdict-**agnostic** (every assertion reading a declared-seam sleep
   patch) and `corruptible_assertions` is the verdict-**filtered** subset (`reach_through` or
   `foreign` only, resolved through the site each assertion's own mock binds, keyed
   `(file, node_id, binds)`). That is the census's own `_disposition()` vocabulary, which has always
   called an `own_module` patch `correct-by-alias`; before the fix the module contradicted itself.
   `nodes_with_sleep_assertions` and `--contract` are both re-sourced from `sleep_assertions`, so
   neither empties when the fix lands.

   Pinned by control-test **Arm G**, which builds an `own_module` `_sleep` seam and a
   `reach_through` `time.sleep` seam side by side and requires the first to appear in
   `sleep_assertions` and **not** in `corruptible_assertions`. Against the shipped code it failed
   with `observed unexpected : [(16, 2)]` — one line of fixture, both blockers.

---

## Prompt and artifact defects found (recorded, not fixed)

1. **`spec.md:557` and `:967` say 9 non-tracker `tests/sync/` instances; there are 10.** AST census
   and an independent grep both give 2 (`test_final_sync_diagnostics.py:260`, `:303`) + 8
   (`test_reconnection.py`) = **10**. Most likely `:260` was missed because the analysis discussed
   `:303`'s `side_effect` sink. Out of this WP's change set.
2. **The WP03 prompt says `test_saas_client.py` has "15 `time.sleep` occurrences by bare `grep -c`".**
   A bare `grep -c 'time\.sleep'` gives **28**. **15** is the count for the *full dotted target*
   `specify_cli.tracker.saas_client.time.sleep`. The substance (15 = 13 live + 2 prose) is correct;
   only the stated command is. Verified: 13 live decorators + 1 in `…_origin.py:229` = **14**, and
   both prose lines sit in one docstring spanning **513-762**.
3. **The prompt locates the AST-only cross-check site at
   `tests/sync/tracker/test_dossier_trigger.py:54`.** The file is at
   `tests/sync/test_dossier_trigger.py:54` — not under `tracker/`.
4. **`plan.md:838`'s `356 / 286 / 7`** is wrong on two of three numbers (`357 / 286 / 6`), as the
   prompt warned. Recorded because the *first, buggy* version of this census reproduced `356` — a
   wrong number is reachable by a wrong instrument, which is the argument for Arm D.
5. **The prompt's T020 step 4 warns the spec may need its composition "corrected".** Checked first:
   `spec.md:504` **already** carries the corrected composition and explicitly retires the old
   reading. Nothing to fix. ~~The stale restatement at `spec.md:566-567` is recorded, not touched.~~
   **WITHDRAWN 2026-08-07 (WP03 review): there is no stale restatement at `spec.md:566-567`.** That
   line carries the *corrected* composition, landed by `91255f6da`. The claim was itself the drifted
   citation. See **RL-021**.

## Ledger — out-of-scope findings (no issues filed, per operator instruction)

**PROMOTED 2026-08-07 (WP03 review).** These four lived only in this note, so `residual-ledger.md`
carried none of them — and WP07 files from the ledger, not from WP notes. They are now
**RL-017**, **RL-018**, **RL-019** and **RL-020** respectively, in the order below, with the full
evidence in the ledger. The two findings surfaced by the review remediation itself are **RL-021**
(the false `spec.md:566-567` citation) and **RL-022** (`sleep_seam_patch_sites` = 16 and the scoping
decision WP05 must make). The bullets below are retained as the finding record; the ledger is
authoritative.

- **RL-017 — lane worktrees carry the destructive `uv run`.** `AGENTS.md:589` (reached as `CLAUDE.md`, a
  symlink) instructs ``PWHEADLESS=1 uv run pytest tests/ui/ -q`` in **lane-b and lane-c** (`grep -c`
  → 1 each); the repository-root tree has **0** because the fix landed after these lanes were seeded
  from `98198e980`. Not fixed in-lane: it would collide with the landed fix at consolidation. **WP03
  executed no `uv` subcommand of any kind.**
- **RL-018 — a comment ending in the bare word `patch` creates a phantom target for the
  `[ENFORCED]` lint.** `check_patch_targets.py`'s regex bridges newlines with `\s*`, so a trailing comment
  `# context-manager patch` immediately above a line beginning `("seam_contextmanager_cases.py"`
  was extracted as the target `seam_contextmanager_cases.py` and **reddened the enforced job**
  (`::error::Broken patch() targets (1 of 5064 checked)`). Caught and fixed inside this WP; recorded
  because it is a live trap for any file that *writes about* patch targets. It is the exact mirror of
  the `test_dossier_trigger.py:54` AST-only case, and independent evidence for NFR-007's AST mandate.
- **RL-019 — charter DIR-013 vs the operator's bar on filing issues.** DIR-013 requires opening a GitHub
  issue for pre-existing failures. This WP encountered **none**, so the rule has no trigger here; the
  standing conflict is already recorded as RL-005 and is not re-litigated.
- **RL-020 — `spec-kitty implement WP03` could not allocate the lane unaided.** It failed with
  `cannot auto-merge the recorded planning commit … into lane 'lane-c'`, requiring a manual merge
  first. The error was actionable and the supported path was followed; recorded because the lane
  branches were seeded from a commit that predates the recorded planning commit, which will recur for
  every remaining lane in this mission.
- **Consolidation note.** This WP adds a file under `kitty-specs/`. `environment-3136.md`'s
  self-measuring `git diff --stat 98198e980 HEAD -- kitty-specs/` figures are measured on the mission
  branch and will move when lane-c lands. WP01's note already binds whoever appends to re-run them;
  flagged here so it is not discovered at merge.

## What was NOT verified

- ~~**`[UNVERIFIED]`** — the post-fix (WP02-applied) census values.~~ **CLOSED 2026-08-07 (WP03
  review). Every post-fix figure in this note is now MEASURED, not asserted.** The instrument had
  been validated only against the tree it was born into; three of the four review blockers were that
  single fault. The post-fix tree is the composed lane-c + lane-b checkout (throwaway detached
  worktree, merged clean, WP02's four files exactly, removed afterwards). Post-fix, measured:
  `nodes_with_sleep_assertions` **4**, `sleep_assertions` **5**, `corruptible_assertions` **0**
  (SC-001 satisfied), the four `--contract` lines byte-identical, `sleep_seam_patch_sites` **16**
  (14 invariant + 2 guard — see RATIFICATION 2), buckets 384 / 264 / 6 / 15 / 0. WP05 still owns the
  criterion; it no longer inherits an unmeasured prediction.
- **`[UNVERIFIED]`** — behaviour of the census on trees other than this one. `_mock_importer` executes
  module-level code on import; over `tests/sync/` every **imported** prefix is `specify_cli.*` or
  stdlib (measured: `specify_cli` 657, `subprocess` 4, `asyncio` 2, `spec_kitty_events` 1 — no target
  imports a `tests.*` module), so nothing under `tests/sync/` is imported. Re-check before widening
  the scan.
  *(Amended 2026-08-07: this said "every **resolved** prefix", which is false — the resolved-module
  roots include `httpx` 130, `requests` 81 and `websockets` 1, because `_mock_importer` imports the
  longest importable prefix and then walks the remainder by `getattr`. The safety bound is about what
  gets **imported**, not what the walk lands on, so the bound itself holds; only the word was wrong,
  and a reader checking the claim against the payload would have found it false and distrusted the
  bound.)*

---

## The golden-count ratchet — measured directly, not assumed

Risk 8 says the `tests/architectural` bucket is at **25/25 with zero headroom** and that one new
`len(x) == N` reds `test_golden_count_ban.py`. Two things had to be checked, because
`scan_repo()` **rglobs all of `tests/`** — fixture directories included:

```
=== sites introduced by WP03 ===
  tests/architectural/_fixtures/patch_seam_control/seam_decorator_cases.py:47
      expr='sleep_calls'  n=3  classification=keep  escaped=False

=== non-escaped 'convert' count for tests/architectural ===
  live:              25
  baseline ceiling:  25
```

- **The control test contributes 0 sites.** Its only textual `len(...) == 3` is inside a *comment*
  on the ground-truth table (`:79`); the guard matches `ast.Compare` nodes, so a comment is inert.
  Every arm asserts frozenset equality.
- **The fixture contributes 1 site, classified `keep`, not `convert`** — so it does not count against
  the ceiling. The `assert len(sleep_calls) == 3` at `seam_decorator_cases.py:47` is load-bearing:
  it reproduces the canonical alias shape from `test_saas_client.py:783-786` that the read-side
  matcher must handle. **No escape marker was added**, because none was needed — adding
  `# golden-count: cardinality-is-contract` here would have been a workaround for a problem that
  does not exist.

**WP03 adds zero convert-classified sites. The bucket is unmoved at 25/25.**

---

## Adjacent guard suites — re-run, green

```
$ ./.venv/bin/python -m pytest \
    tests/architectural/test_pytest_marker_convention.py \
    tests/architectural/test_golden_count_ban.py \
    tests/architectural/test_gate_coverage.py \
    -q -ra -p no:cacheprovider > guards.txt 2>&1

48 passed in 722.83s (0:12:02)
GUARDS_EXIT=0
```

Probe discipline applied to the zero, so it cannot be a missing-file artefact:

```
test -s guards.txt         -> NON-EMPTY: 3 lines
grep -c 'passed'           -> 1        # twin >= 1: it really is a pytest run
grep -c '^ERROR tests/'    -> 0        # a real zero, anchored form
```

Output was **redirected, never piped** — a pipe would have replaced pytest's exit status with the
tail command's. The 12-minute wall clock is contention, not pathology: two sibling agents were
running full `tests/architectural` suites concurrently on the same machine (confirmed via `ps`),
and the process was verified alive and accumulating CPU rather than hung before it was waited on.

**Final control test, against the committed state:** `8 passed in 94.90s`, `CTRL3_EXIT=0`,
8 collected.

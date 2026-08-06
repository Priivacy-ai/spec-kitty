# Phase 0 research — `Priivacy-ai/spec-kitty#3162`: the 13 unrouted `meta.json` sites

**Baseline:** `upstream/main` `96494e5ec`; measured on branch `feat/meta-fail-closed-3162`
at HEAD `6fbc1e23f`. Interpreter pinned to `.venv/bin/python`.
**Scope:** the `Priivacy-ai/spec-kitty#3162` half only. `Priivacy-ai/spec-kitty#3138`
is a separate agent's bisect and is untouched here.
**Binding operator decision D4 = (a):** route all 13 through `load_meta_fail_closed`
**preserving each site's existing refuse-vs-degrade arm**. Option (c) (route only the
sites that leak a raw `ValueError`) is the named budget fallback. Option (b) (uniform
refusal) is out of scope — it would change behaviour at the sites that deliberately degrade.

---

## 1. The census — all 13 sites

The ledger in `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` carries
**12 rows** tagged `pending-batch-a` (lines 198–204, 215, 222, 243, 244, 249); one row
(`read_primary_meta`) has count `2`, so the row set expands to **13 call sites**. The
`grep -c 'pending-batch-a'` figure of 13 counts 12 ledger rows plus the one docstring
mention at `:185` — the two 13s agree by coincidence, not by construction. Deriving the
13 from the row *counts* is the reliable path.

All 13 sit on the canonical reader's **raise** contract (`on_malformed="raise"` —
explicit at 7 sites, the signature default at 6). None is on `"none"`/`"empty"`, so a
malformed `meta.json` genuinely produces a `ValueError` at every one of them.

| # | Site | Function | Read shape | Arm taken **today** |
|---|------|----------|-----------|---------------------|
| 1 | `src/mission_runtime/resolution.py:509` | `_mid8_from_primary_meta` | `load_meta(primary_dir, allow_missing=True, on_malformed="raise")` inside `try` | **DEGRADE** — `except ValueError: return ""` (identity unproven) |
| 2 | `src/mission_runtime/resolution.py:852` | `_resolve_coordination_branch` | same, one-line explicit form | **DEGRADE** — `except ValueError: return None` ("coordination topology undeclared") |
| 3 | `src/mission_runtime/resolution.py:1107` | `_resolve_mission_id` | same, one-line explicit form | **DEGRADE** — `except ValueError: meta = None` → falls through to the `legacy-<slug>` sentinel |
| 4 | `src/runtime/next/_internal_runtime/planner.py:188` | `_resolve_workflow_for_mission` | `load_meta(mission_dir)` (bare default), no `try` | **REFUSE-raw** — raw `ValueError` escapes onto the `spec-kitty next` path |
| 5 | `src/runtime/next/runtime_bridge_io.py:380` | `_workflow_runtime_template` | `load_meta(mission_dir)` (bare default), no `try` | **REFUSE-raw** |
| 6 | `src/specify_cli/bulk_edit/gate.py:57` | `_is_bulk_edit_mission` | `load_meta(feature_dir)` (bare default), no `try` | **REFUSE-raw** |
| 7 | `src/specify_cli/bulk_edit/gate.py:80` | `ensure_occurrence_classification_ready` | `load_meta(feature_dir)` (bare default), no `try` | **REFUSE-raw** |
| 8 | `src/specify_cli/context/resolver.py:75` | `_read_meta_json` | `load_meta(..., allow_missing=False, on_malformed="raise") or {}` inside `try` catching **only** `FileNotFoundError` | **REFUSE-raw** — the `FileNotFoundError` arm is typed (`MissingIdentityError`); the `ValueError` arm is not handled at all |
| 9 | `src/specify_cli/decisions/service.py:134` | `_resolve_mission_id` | `load_meta(..., allow_missing=False, on_malformed="raise") or {}` inside `try` | **REFUSE-typed** — `except ValueError: raise DecisionError(MISSION_NOT_FOUND)` |
| 10 | `src/specify_cli/missions/_read_path_resolver.py:846` | `read_primary_meta` (first read) | `load_meta(primary_dir) or {}` (bare default), no `try` | **REFUSE-raw** |
| 11 | `src/specify_cli/missions/_read_path_resolver.py:862` | `read_primary_meta` (canonicalized re-read) | `load_meta(canonical_dir) or {}` (bare default), no `try` | **REFUSE-raw** |
| 12 | `src/specify_cli/missions/_resolve_planning_branch.py:116` | `load_mission_target_branch` | `load_meta(..., allow_missing=False, on_malformed="raise")` inside `try` | **REFUSE-typed** — `except ValueError: raise PlanningBranchResolutionFailed` |
| 13 | `src/specify_cli/upgrade/feature_meta.py:42` | `load_feature_meta` | `load_meta(feature_dir)` (bare default) inside `try` | **DEGRADE** — `except ValueError: return None` ("meta needs repair") |

Line numbers confirmed on this head: `grep -n 'on_malformed' src/mission_runtime/resolution.py`
returns exactly `512`, `852`, `1107` — `:512` is the `on_malformed=` keyword line of the
multi-line call whose `ast.Call` node begins at `:509`, which is why
`Priivacy-ai/spec-kitty#3162`'s body cites `:509` and the operator brief cites `:512`.
**Both are the same single call site.** The census above uses the call-node line (`:509`)
so it stays consistent with the AST-derived numbers for every other row.

---

## 2. The verified split — the programme's 6/7 figure is **partly wrong**

The prior analysis put the split at **6 divergent-wrapper (degrade) vs 7 route-unwrapped
(raw)**. Re-derived from source rather than cited:

- **7 route-unwrapped is CORRECT.** Exactly 7 sites let a raw `ValueError` reach the user.
- **"6 divergent-wrapper → degrade" is WRONG as a behavioural claim.** 6 is the right
  count of sites carrying an `except ValueError`, but only **4 of those 6 degrade**. The
  other **2 refuse** — they catch the `ValueError` and re-raise a typed domain error
  (`DecisionError(MISSION_NOT_FOUND)`, `PlanningBranchResolutionFailed`). Collapsing
  "has an `except ValueError`" into "degrades" is the error.

**The split that D4 actually needs** — because D4 says *preserve each site's
refuse-vs-degrade arm* — is:

| Arm today | Count | Sites |
|---|---|---|
| **DEGRADE** (malformed absorbed to a sentinel; nothing surfaces) | **4** | `resolution.py:509`, `:852`, `:1107`, `upgrade/feature_meta.py:42` |
| **REFUSE-typed** (malformed → domain error) | **2** | `decisions/service.py:134`, `_resolve_planning_branch.py:116` |
| **REFUSE-raw** (malformed → raw `ValueError` to the user) | **7** | `planner.py:188`, `runtime_bridge_io.py:380`, `gate.py:57`, `gate.py:80`, `context/resolver.py:75`, `_read_path_resolver.py:846`, `:862` |
| | **13** | |

So D4's routing target is **4 degrade arms to preserve** and **9 refuse arms** (of which
7 must gain a typed error and 2 already have one). The budget fallback (c) — "route only
the 7 that leak raw" — is exactly the REFUSE-raw row above, unchanged by this correction.

### Commands behind the split

**Command 1 — mechanical AST derivation.** For each censused `(file, function)` row,
locate the `load_meta` call node, find every same-function `ast.Try` whose *body*
contains it, keep the handlers that catch `ValueError` (or a tuple containing it, or a
bare `except`), and classify each handler body as REFUSE (contains `ast.Raise`) or
DEGRADE (does not). No such handler ⇒ REFUSE-raw.

```
.venv/bin/python <scratch>/derive_arms.py
```

Output (verbatim tallies):

```
INPUT rows (ledger pending-batch-a): 12  expected call sites: 13
DERIVED call sites: 13
DEGRADE: 4
REFUSE-raw: 7
REFUSE-typed: 2
TOTAL: 13
```

The script is retained at
`/tmp/claude-1000/-home-jeroennouws-dev-sk-missions/ca298d9c-391a-43ff-ab54-419c109c6f77/scratchpad/derive_arms.py`
and should be re-run (or lifted into the work package as a test) rather than trusted from
this document. It emits a `COUNT MISMATCH` line if a file's live `load_meta` call count
diverges from the ledger row — it did not fire, so the ledger row counts are still true
on this head.

**Command 2 — the control on that classifier**, run *before* trusting it on the 13. Three
sites whose arm is known by reading: `core.paths.load_meta_fail_closed` (must be
REFUSE-typed), `mission_metadata.load_meta_or_empty` (no `try` at all, must be
REFUSE-raw — the classifier deliberately does not read `on_malformed`, so this pins that
limitation), `_resolve_planning_branch.load_mission_target_branch` (must be REFUSE-typed).

```
.venv/bin/python <scratch>/control_arms.py
→ CONTROL INPUT cases: 3  PASSED: 3
```

The `load_meta_or_empty` control matters: it proves the classifier is blind to the
`on_malformed` kwarg. That blindness is harmless here **only because** all 13 sites were
independently confirmed to be on the `"raise"` contract (audited per-site; 7 explicit,
6 by signature default).

**Command 3 — behavioural confirmation.** Independent of the AST: a temp mission dir with
`{ this is not json` as `meta.json`, each reachable function called directly.
Positive control first (`load_meta_fail_closed` on the same dir must raise
`MissionMetaReadError` — it did); negative control second (all 7 probes against a
*valid* `meta.json` must return cleanly — 7/7 did); only then the real case.

```
.venv/bin/python <scratch>/probe_behaviour.py
```

| Probe | Corrupt-meta result |
|---|---|
| `planner._resolve_workflow_for_mission` | RAW `ValueError` |
| `gate._is_bulk_edit_mission` | RAW `ValueError` |
| `gate.ensure_occurrence_classification_ready` | RAW `ValueError` |
| `context.resolver._read_meta_json` | RAW `ValueError` |
| `_read_path_resolver.read_primary_meta` | RAW `ValueError` |
| `_resolve_planning_branch.load_mission_target_branch` | typed `PlanningBranchResolutionFailed` |
| `upgrade.feature_meta.load_feature_meta` | `None` (degrade) |

`C1 PASS`, `C2 input probes: 7 clean: 7 unexpected-raise: 0`, then
`probes run: 7  raw ValueError escapes: 5`. Those 5 raw escapes cover 6 of the 7
REFUSE-raw census rows (`read_primary_meta` is one function holding rows 10 and 11).
Two REFUSE-raw rows were **not** behaviourally reached and rest on the AST derivation
alone: `runtime_bridge_io.py:380` (needs a real repo-root/runtime-bridge fixture) and
`_read_path_resolver.py:862` (the canonicalized re-read only fires on the
non-composed-handle miss path, which the fixture's composed handle never takes).

A detail the spec should carry: at `context/resolver.py:75` the raw `ValueError` escapes
**before** the already-routed `read_target_branch_from_meta` call three lines below it
can produce the typed `MissionMetaReadError`. The function is half-routed today, and the
unrouted half wins.

---

## 3. The bypass sites — and there are **4**, not 2

`Priivacy-ai/spec-kitty#3162` names two sites in `src/specify_cli/git/ref_advance.py`
that reach `meta.json` without `load_meta` at all. Verified:

```
grep -c 'load_meta(' src/specify_cli/git/ref_advance.py   → 0
```

Both go through the module-private parser `_parse_meta_object` (`:181–189`), a
`json.loads` + `isinstance(dict)` check that returns `None` on failure:

- **`_committed_meta_object` (`:192–207`)** — `_run_git(worktree, ["show", f"HEAD:{path}"])`,
  then `_parse_meta_object(result.stdout)` at `:206`; `None` → `{}`.
- **`_meta_change_is_vcs_lock_only` (`:231–251`)** — `meta_path = worktree / path`,
  `meta_path.read_text(encoding="utf-8")` at `:244`, `_parse_meta_object(worktree_text)`
  at `:247`; `None` → `return False`.

Consumed from `_dirty_entries` (`:254–320`) at `:315`: a tracked `meta.json` whose only
diff against HEAD is the claim-time VCS lock (`vcs`, `vcs_locked_at`) is tolerated as a
regenerable stamp; anything else blocks the ref advance
(`Priivacy-ai/spec-kitty#2795`).

### Two more of the same shape, in a second file

Searching for the *shape* rather than the file found the class is larger:

```
grep -rn 'def _parse_meta[a-z_]*(' src/
  src/specify_cli/mission_metadata.py:331   _parse_meta_text     ← the canonical reader's OWN internal
  src/specify_cli/cli/commands/implement_cores.py:259  _parse_meta_mapping
  src/specify_cli/git/ref_advance.py:181    _parse_meta_object

grep -c 'load_meta(' src/specify_cli/cli/commands/implement_cores.py   → 0
```

`implement_cores.py`'s `_parse_meta_mapping` (`:259`, `json.loads(raw.decode("utf-8"))`,
`None` on `UnicodeDecodeError`/`JSONDecodeError`/non-dict) is fed by two reads:

- **`_committed_meta_mapping` (`:330–338`)** — `git.show_blob(...)` at `:335` →
  `_parse_meta_mapping(blob)` at `:338`.
- **`_is_self_write_only_diff` (`:388–446`)** — `_parse_meta_mapping(source.read_bytes())`
  at `:427`; `None` → `return False`.

Structurally identical to `ref_advance.py`'s pair (git-blob or direct file read, parse
delegated to a private helper) and driving the same `vcs`/`vcs_locked_at` lock-only
comparison via a *third* independent copy of it (`_is_vcs_lock_only_meta_diff` at `:241`,
against `ref_advance.py:210`'s `_is_vcs_lock_only_meta_change` — `_VCS_LOCK_META_FIELDS`
is declared twice, `ref_advance.py:42` and `implement_cores.py:50`). The spec must decide
whether `Priivacy-ai/spec-kitty#3162`'s bypass scope is the 2 named sites or the full
4-site class; treating it as 2 leaves an identical hole in the file next door.

### What each bypass site does with a malformed read — measured

Real git repo, valid `meta.json` committed, working copy varied. Controls first, because
"it blocks" only means something once "it tolerates" is shown to fire at all.

```
.venv/bin/python <scratch>/probe_ref_advance.py
```

| Case | `_committed_meta_object` | `_meta_change_is_vcs_lock_only` |
|---|---|---|
| **C1 control** valid HEAD + lock-only working copy | dict | `True` → **TOLERATED** (advance proceeds) |
| **C2 control** valid HEAD + real meta edit | dict | `False` → **BLOCKS** |
| **R1** valid HEAD + CORRUPT working copy | dict | `False` → **BLOCKS** |
| **R2** CORRUPT HEAD blob + lock-only working copy | `{}` | `False` → **BLOCKS** |
| **R3** CORRUPT HEAD + CORRUPT working copy | `{}` | `False` → **BLOCKS** |

Both controls behaved as predicted, so the three real results are trustworthy. Corruption
at either end degrades to **blocks the advance** — safe in effect (no data loss, no
false-open) but **silent about the cause**: the operator gets the generic dirty-worktree
diagnostic naming `meta.json`, never "meta.json is corrupt". That is the fail-closed gap:
not unsafety, but an undiagnosable refusal.

One conflation to resolve, and it is resolvable: `_committed_meta_object` returns `{}` for
both "absent at HEAD (newly added `meta.json`)" and "present at HEAD but corrupt". The
function already distinguishes them internally — `if result.returncode != 0: return {}`
is the absent case, and the `_parse_meta_object(...) is None` path is specifically
"present but unparseable". A fail-closed variant can therefore be written **without**
losing the legitimate newly-added case.

---

## 4. The gate that cannot see them — demonstrated, not inferred

### The shape `tests/architectural/test_inline_meta_read_gate.py` matches

`scan_inline_meta_reads(SRC_ROOT)` (`:589`) anchors on an `ast.Call` node and requires
**all three** of:

1. the callee resolves to `json.loads` or `json.load` (`_is_json_loads_call` / `_is_json_load_call`,
   `:417`/`:433` — alias- and `from json import loads`-aware);
2. its **first positional argument** resolves, via `_read_source_base` (`:519`) and up to
   `_MAX_ASSIGNMENT_HOPS` *intra-function* reassignment hops, to a read call —
   `X.read_text(...)`, `X.open(...)`, or `open(X, ...)` (`_extract_read_base`, `:507`);
3. that `X` is a meta path per `is_meta_path_expr` (`:549`) — either a name in
   `META_PATH_VAR_NAMES` (`meta_path`/`meta_file`/`meta_json`/`target_meta_path`) or a
   literal `<dir> / "meta.json"` join.

Everything is anchored on the `json.loads` call node, and every hop is *same-function*
(`_enclosing_function` supplies `fn`; `_follow_assignment_chain` searches only within it).
There is no call-graph resolution — the gate's own comment at `:96–104` says so
explicitly about the *routed* scan, and the inline scan is the same way.

### Why `ref_advance.py` does not match

Driving the gate's own scanner (imported, not re-implemented):

```
.venv/bin/python <scratch>/probe_gate_blindness.py
```

**C0 — the file is in scope.** `files walked: 1199`;
`src/specify_cli/git/ref_advance.py in walk: True`;
`in EXCLUDED_REL_PATHS: False`; and `grep -c 'ref_advance' tests/architectural/inline_meta_read_allowlist.yaml → 0`.
So the miss is not an exclusion, not an allowlist entry, and not a walk gap. It is structural.

**C1 — positive control, the scanner is live.** It returns exactly the 7 known sites
(`INLINE_META_READ_FLOOR = 7`): 5 upgrade migrations plus the 2 `src/charter/` sites.
A scanner that returned nothing would make the ref_advance zero meaningless.

**REAL — `sites reported in src/specify_cli/git/ref_advance.py: 0`.**

**C2 — the cause isolated to one variable.** Two scratch modules differing *only* in
whether the parse is inlined:

- **C2a**, `worktree_meta = json.loads(meta_path.read_text(encoding="utf-8"))` after
  `meta_path = worktree / path` → **1 site flagged**,
  `token='worktree_meta = json . loads ( meta_path . read_text ( encoding = ) )'`.
  The scanner *does* match `ref_advance.py`'s path expression and read call. Note the
  variable is literally named `meta_path`, satisfying clause 3 by the name heuristic even
  though `worktree / path` is not a `/ "meta.json"` literal join.
- **C2b**, the identical read with the parse delegated to a `_parse_meta_object(text)`
  helper — `ref_advance.py`'s real shape → **0 sites flagged**.

The single edit that flips the gate from 1 to 0 is the cross-function split. That is the
blindness, shown rather than asserted: the parse sees only a parameter (`text`), which
`_follow_assignment_chain` cannot bind to a read inside `_parse_meta_object`; and the
read function contains no `json.loads` call for the walk to anchor on.

**C3 — the `git show` site is a different problem.** A scratch module with the
`git show` read *fully inlined* (`json.loads(result.stdout)` alongside a
`meta_path = worktree / path`) → **0 sites flagged**. `json.loads`' argument traces to
subprocess stdout, which is not `read_text`/`open`/`open()`. No amount of widening the
*path-expression* clause reaches it.

**The floor tests are green today, with all four bypass sites invisible.** Narrowed run,
no `tests/sync` or `tests/cli` involvement, `pgrep -af 'run_sync[_]daemon'` empty before
each invocation:

```
.venv/bin/python -m pytest tests/architectural/test_inline_meta_read_gate.py -p no:randomly -q -ra
  → exit=0 ; "40 passed in 91.70s" ; grep -c '^ERROR tests/' → 0

.venv/bin/python -m pytest \
  tests/architectural/test_inline_meta_read_gate.py::test_routed_load_meta_floor \
  tests/architectural/test_inline_meta_read_gate.py::test_inline_meta_read_floor \
  tests/architectural/test_inline_meta_read_gate.py::test_inline_meta_read_gate_green_against_seeded_allowlist \
  -p no:randomly -v -ra
  → exit=0 ; all three PASSED ; "3 passed in 72.99s" ; grep -c '^ERROR tests/' → 0
```

Neither run was killed. Output was redirected to a file and the `N passed` line quoted
from it, not piped.

The companion `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` cannot see
these sites either, and says so by construction: `scan_load_meta_call_sites` (`:128`)
matches `ast.Call` nodes whose callee is a `load_meta` binding. A read that never names
`load_meta` produces no row. Two gates, two different reasons for the same blind spot.

### Answering the work package's question: widen, or allowlist?

Both, split by site — the two bypass shapes have different answers:

- **The `read_text`-fed sites** (`ref_advance.py:245→247`, `implement_cores.py:427`) are
  reachable by widening. The gate needs **one** new capability: follow a private,
  same-module, single-parameter parse helper — i.e. when a `json.loads` arg is an
  unbound parameter of function `F`, treat calls to `F` within the same module as the
  read anchor and apply clauses 2–3 there. That is a bounded, one-hop, intra-module
  call-graph step, not general call-graph resolution. C2a/C2b bound the work precisely:
  the path clause already matches; only the anchor needs to move.
- **The `git show` / `show_blob` sites** (`ref_advance.py:206`, `implement_cores.py:338`)
  are **not** reachable by widening the existing clauses at all — C3 proves the read
  source is outside the matched set even with the parse inlined. Covering them means a
  genuinely new detector (a `git show <ref>:<path ending in meta.json>` / `show_blob`
  argument-shape clause), which is its own design decision. If the work package will not
  build that detector, these two **must** be allowlisted with a dated rationale and a
  tracked issue, exactly as the 5 migration and 2 `src/charter/` entries are today.

Either way the allowlist's own contract applies: an entry needs `file`, `qualname`,
tool-derived `token`, `rationale`, and `issue` (the loader raises `AllowlistEntryError`
without them), and `inline_meta_read_baseline` / `INLINE_META_READ_FLOOR` must move with
the census. Widening the scanner **raises** the live count, so
`test_inline_meta_read_floor`'s ceiling and `FLOOR_MARGIN = 2` will both need re-pinning
in the same change — the gate is a *shrink-only* ceiling, so a widening that discovers 4
new sites turns it red until the floor is re-derived. That is a first-class task, not a
footnote.

---

## 5. The canonical target

**`load_meta_fail_closed`** — `src/specify_cli/core/paths.py:638`

```python
def load_meta_fail_closed(feature_dir: Path) -> dict[str, Any] | None
```

Verified at runtime: `inspect.signature` → `(feature_dir: 'Path') -> 'dict[str, Any] | None'`;
`'load_meta_fail_closed' in specify_cli.core.paths.__all__` → `True` (`:923` region).

The contract a caller must satisfy:

- **One positional argument**, the mission *directory* (not the `meta.json` path). The
  function appends `meta.json` itself.
- **No keyword arguments.** It hard-codes `allow_missing=True, on_malformed="raise"`
  internally. A caller that today passes `allow_missing=False` (rows 8, 9, 12) is
  therefore **not** a drop-in swap: `load_meta_fail_closed` returns `None` for an absent
  file where those sites currently get `FileNotFoundError`. Each of the three has a
  distinct typed missing-file arm (`MissingIdentityError`, `DecisionError(MISSION_NOT_FOUND)`,
  `PlanningBranchResolutionFailed`) that must be re-expressed as an explicit
  `if result is None:` branch. This is the single largest correctness trap in the routing.
- **Returns** `None` when `meta.json` is absent (the field-absent case; callers apply
  their documented default), or the parsed `dict` when present and valid.
- **Raises** `MissionMetaReadError` when `meta.json` exists but is corrupt, non-object, or
  unreadable. Never for a missing file.
- Its docstring names the deliberate non-clients: callers that must stay silent about
  corruption keep using `load_meta_or_empty` or `on_malformed="none"`. None of the 13 is
  in that class (all 13 are on the `"raise"` contract), so all 13 are legitimate targets.

**`MissionMetaReadError`** — `src/specify_cli/core/paths.py:506`

```python
class MissionMetaReadError(RuntimeError):
    def __init__(self, meta_path: Path, cause: Exception) -> None
```

MRO verified: `MissionMetaReadError → RuntimeError → Exception → BaseException → object`.
Carries `.meta_path` and `.cause`; message is
`f"Cannot read {meta_path}: {cause} — fail-closed (meta.json exists but is corrupt or unreadable)"`.
In `__all__`. **It is not a `ValueError`** — so any site whose existing `except ValueError`
is meant to keep degrading will stop catching it the moment the call is routed. Every one
of the 4 DEGRADE arms must have its handler changed to `except MissionMetaReadError` (or
a tuple) in the same edit, or D4's "preserve the arm" is silently violated and three
`spec-kitty` resolution paths start crashing where they used to fall back.

**Import feasibility — no new package boundary is crossed.** 89 references to
`load_meta_fail_closed` already exist in `src/`. Precedent exists in every package that
holds one of the 13:

- `src/mission_runtime/` — 20 `core.paths` references; `lifecycle_phase.py:139` already
  does a deferred `from specify_cli.core.paths import MissionMetaReadError, load_meta_fail_closed`.
- `src/runtime/` — `next/prompt_builder.py:33` imports `core.paths` at module level;
  `next/runtime_bridge.py:250` imports `MissionMetaReadError` deferred.
- `src/specify_cli/` — same package; `context/resolver.py:27` and
  `missions/_read_path_resolver.py:28` already import `core.paths` at module level.

`core.paths` keeps a **load-bearing deferred import** of `mission_metadata` inside
`load_meta_fail_closed` to avoid re-forming the `core.paths ↔ mission_metadata` cycle
(documented at `:665–670`). Routing must not "tidy" that up, and new callers in the two
files that currently import `mission_metadata` at module level
(`planner.py:37`, `runtime_bridge_io.py:102`, `gate.py:17`, `decisions/service.py:38`,
`_resolve_planning_branch.py:42`, `upgrade/feature_meta.py:18`) should be checked
individually for whether a module-level `core.paths` import is safe there or must be
deferred.

**Routing is observable as progress**, in both directions: a routed site disappears from
`scan_load_meta_call_sites` (its `pending-batch-a` ledger row must be deleted, or
`test_meta_fail_closed_full_census_contract.py` flags the stale row — it warns
explicitly at `:329`), and appears in `scan_routed_load_meta_calls`, which counts
`ROUTED_CALLEES = {load_meta, load_meta_strict, load_meta_or_empty, load_meta_fail_closed,
_load_meta_fail_closed, _require_meta}`. Since both names are in that set, routing
`load_meta` → `load_meta_fail_closed` is **routed-count neutral**, so
`ROUTED_LOAD_META_FLOOR = 126` should not move. That is worth stating in the spec: this
programme has already had **three** recorded floor/census mismatches from exactly this
class of miscount (the `:96–104` comment records two of them, and
`Priivacy-ai/spec-kitty#3175`'s landing pass a third).

---

## 6. Open questions and risks for the spec

**Q1 — Is the bypass scope 2 sites or 4?** `Priivacy-ai/spec-kitty#3162` names only
`ref_advance.py`'s pair. `implement_cores.py:338` and `:427` are the identical shape,
also `load_meta`-free, also gate-invisible, also driving the same `vcs`/`vcs_locked_at`
lock-only decision. Scoping to 2 leaves a matching hole one file away. **Spec decision,
not implementer's** — it changes the work-package budget.

**Q2 — Should the bypass sites be routed at all, or only made diagnosable?** All four
already fail *safe* (they block, never false-open). What they lack is a diagnosis. Options:
(i) route to `load_meta_fail_closed` and let `MissionMetaReadError` propagate — changes
`spec-kitty implement`'s claim-time behaviour from "worktree dirty" to a hard typed error;
(ii) keep the block but attach a corruption-specific message; (iii) allowlist and defer.
D4 covers the 13 and is silent on these four.

**Q3 — Widen the gate, or allowlist?** §4 answers the mechanics; the *choice* is the
spec's. Widening for the `read_text`-fed pair is bounded and cheap; a `git show` detector
is a new design. Note that widening turns `test_inline_meta_read_floor` red until the
ceiling and `FLOOR_MARGIN` are re-derived — sequence that deliberately.

**Q4 — What is the operator-visible contract at the 4 DEGRADE sites?** D4 says preserve
the arm, so a corrupt `meta.json` will keep resolving to `""` / `None` / `legacy-<slug>` /
"needs repair" with no diagnostic. That is a deliberate choice to preserve behaviour, and
it means `Priivacy-ai/spec-kitty#3155`'s "never a raw crash" claim becomes true while
"corruption is always visible" stays false at 4 sites. If the spec wants those 4 to at
least *log*, that must be written down — an implementer preserving the arm literally will
not add it.

**Q5 — `resolution.py:509`'s handler is broader than the reader.** Its `except ValueError`
also swallows the path-traversal guard `ValueError` from `assert_safe_path_segment` inside
`_compose_primary_feature_dir` (the code comments this at `:493–498`). Narrowing the
handler to `except MissionMetaReadError` while routing would **change** behaviour: an
unsafe path segment would start propagating instead of degrading to `""`. The spec must
say whether that is a wanted fix or a regression to avoid; it cannot be decided silently
at the keyboard.

**Q6 — The three `allow_missing=False` sites need explicit missing-file branches.** Rows
8, 9, 12. See §5. Highest-risk mechanical trap in the change; each needs its own red test
proving the *missing-file* arm still produces its typed error after routing.

**Q7 — Is `_read_path_resolver.py:862` (row 11) reachable by any test?** It is the
canonicalized re-read on the non-composed-handle miss path; the behavioural probe could not
reach it with a composed handle. The work package needs a fixture with a bare-`mid8` /
full-ULID / numeric-prefix handle, or row 11 will be routed without a red test. Same for
`runtime_bridge_io.py:380`, which needs a real repo-root fixture.

**Q8 — Three parallel copies of the lock-only comparison.** `_VCS_LOCK_META_FIELDS` is
declared in both `ref_advance.py:42` and `implement_cores.py:50`, with two independent
comparison functions (`ref_advance.py:210`, `implement_cores.py:241`) and two independent
private parsers. Out of scope for `Priivacy-ai/spec-kitty#3162`, but a routing pass that
touches both files will be tempted into it. Name it as out of scope (DIR-024, locality of
change) or as its own follow-up issue.

## Could not establish

- **Behavioural confirmation for 2 of the 13**: `runtime_bridge_io.py:380` and
  `_read_path_resolver.py:862` rest on the AST derivation plus a source read, not on an
  observed raw `ValueError`. Both need fixtures the work package should build anyway
  (see Q7).
- **Whether any existing test pins the current degrade behaviour of the bypass sites.**
  `tests/specify_cli/cli/commands/test_implement_cores.py` and
  `tests/regression/test_issue_2795_claim_blocker.py` reference the helpers and the
  lock-only fields, but I did not run them (they are outside this Phase-0 scope and
  `test_implement_cores.py` sits under `tests/specify_cli/cli/`, adjacent to the
  `tests/cli` sweep this mission is barred from). The work package must run them before
  changing `implement_cores.py` or `ref_advance.py`.
- **`INLINE_META_READ_FLOOR` after widening.** Not derivable until the widening shape is
  chosen; the C2a/C2b/C3 results bound it (the two `read_text`-fed sites would appear; the
  two `git show`-fed ones would not).

**Minor hygiene note (not a gate failure):** `inline_meta_read_allowlist.yaml`'s entry for
`src/charter/mission_type_profiles.py::_read_meta_mission_type` records `line: 441`; the
live site is at `:650`. The allowlist header states `line:` is a non-authoritative
locator and no comparison, set-membership, or count logic reads it — the authoritative
`(file, qualname, token)` key still matches, which is why all 40 tests pass. Worth
refreshing opportunistically if the work package touches the file (DIR-025), not worth a
task.

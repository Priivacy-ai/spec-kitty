# Headroom allocation — mission `meta-fail-closed-3162-01KZ7FSQ`

**Status**: frozen by `WP01`. Binding on `WP02`–`WP08`.
**Requirements**: `NFR-002`, `SC-011`, `SC-013`, `C-003`.
**Companion**: `contracts/routing-manifest.md` — every citation, count and convention below is
defined there and is not restated loosely here.

> **Conventions and citation rules carry over verbatim from the routing manifest.** Every count states
> its convention **inline**; every symbol is **module-qualified** (`C-003`); a read-expression count
> and a call-site count are **never addable**; every number carries the command that produced it and
> that command's input count. **Regeneration command** for the routed and inline numbers:
>
> ```bash
> PYTHONPATH=<tree>/src .venv/bin/python scripts/verify_meta_routing_manifest_3162.py [TREE_ROOT]
> ```

---

## §1 — The invariant, in one sentence

**There is exactly one net routed call for the whole mission** — live routed **129 call sites** inside
the two-sided admissible band **`[127, 130]`** (derived in `contracts/routing-manifest.md` §4.4 from
the three verbatim assertions of `test_routed_load_meta_floor`,
`tests/architectural/test_inline_meta_read_gate.py:1084`) — **and `WP05` spends it**, routing
`specify_cli.git.ref_advance._meta_change_is_vcs_lock_only`'s parse at `ref_advance.py:247`
`[shifts — cite the symbol]` per operator ruling **R-1**. **Every other work package is 0-net.**

---

## §2 — The allocation table

Convention: every "routed" figure below is a **routed call-site count**, measured by the gate's own
AST scanner `scan_routed_load_meta_calls` (`test_inline_meta_read_gate.py:657`) over an input
population of **1 199** `*.py` files under `<tree>/src`.

| WP | May spend? | Net routed delta | Pre/post print obligation | Notes |
|---|---|---|---|---|
| `WP01` | **n/a — no code** | 0 | Records **129** and the band `[127, 130]` as the anchor, with the command and its input file count | This document + `contracts/routing-manifest.md` + `scripts/verify_meta_routing_manifest_3162.py` |
| `WP02` | **no** | **0-net** | prints **129 / 129** | 6 swaps (census rows 4, 5, 6, 7, 10, 11). `load_meta` **and** `load_meta_fail_closed` are **both** in `ROUTED_CALLEES` (`test_inline_meta_read_gate.py:105`), so a 1:1 swap is count-neutral |
| `WP03` | **no** | **0-net** | prints **129 / 129** | 3 swaps (rows 8, 9, 12) |
| `WP04` | **no** | **0-net** | prints **129 / 129** | 4 swaps (rows 1, 2, 3, 13 — the four degrade sites) |
| `WP05` | **YES — the sole allocator** | **+1** | prints pre **129**, post **130**; both inside `[127, 130]`, floor still 126 | Routes `specify_cli.git.ref_advance._meta_change_is_vcs_lock_only`'s parse at `ref_advance.py:247` per **R-1** |
| `WP06` | **no** | **0-net** | prints the count **and the floor** pre and post the floor move, and **re-asserts all three clauses** of `test_routed_load_meta_floor` at the new floor | Re-derives `ROUTED_LOAD_META_FLOOR` from the **measured** live count — see §6 |
| `WP07` | **no** | **0-net** | prints **130 / 130** | test + tracker only |
| `WP08` | **no** | **0-net** | prints the count on the **integrated** tree, pre and post its own edit | **Re-derives on the integrated tree; never sums lane numbers** |

**Exactly one row says "may spend". Every other row reads 0-net.**

---

## §3 — The print obligation is **per work package**, not mission-end

Each work package prints the routed count **before and after its own edit**, **from its own
worktree**, using this manifest's recorded command and its input file count. **A delta of anything
other than that work package's allocated value STOPS that work package.**

**Why per-work-package and not mission-end.** `SC-011`'s previous form — "print 129 pre and 129
post" — was **satisfiable by changing nothing**. The census counts callee **names** over the whole of
`src/` and **cannot see whether routing happened**: swapping `load_meta` for
`load_meta_fail_closed` leaves the total unchanged because both names are in `ROUTED_CALLEES`, and so
does swapping nothing at all. A mission-end check therefore reads identical whether the routing
landed or was skipped. Only a per-work-package pre/post pair, taken in the tree that work package
actually edited, distinguishes "0-net because the swap was count-neutral" from "0-net because no swap
occurred" — the latter being caught by that work package's own behavioural assertions, which the
count can never substitute for.

---

## §4 — The lane consequence: 0-net is what makes lanes B and C parallel-safe

Lane B is `WP02 → WP03 → WP04`; lane C is `WP05 → WP06`. **They are parallel-safe *only* because of
the 0-net constraint.** Each lane measures the routed count in **its own worktree**. If only `WP05` is
non-zero, then every lane is individually green against the band `[127, 130]`, and the merged tree
reads **130** — still inside the band, still above the floor. That is the whole basis of the
parallelism; it is load-bearing, not bookkeeping.

**A lane that quietly folds two calls into one breaks this DOWNWARD, and neither lane's own gate run
can see it.** The concrete risk is named in `contracts/routing-manifest.md` §4.5: **census rows 10 and
11 are two `load_meta` calls inside one function**,
`specify_cli.missions._read_path_resolver.read_primary_meta` (`:846` first read, `:862`
canonicalized re-read) — both owned by `WP02`, in lane B. Folding them during routing looks like
tidying and takes routed from 129 to 128; a second such fold anywhere takes it to **126, which is
RED** (clause 2, `len(routed) > ROUTED_LOAD_META_FLOOR`, is strict). Lane B would still read inside
the band on its own, and the breach would surface only at integration — which is exactly the
misattribution this mission's anchor exists to prevent. This programme has already had **three floor
mismatches caused by folds that collapsed call sites**.

**Rule: rows 10 and 11 must remain two distinct call sites after routing.**

---

## §5 — The `NFR-002` / `SC-013` predicate-symbol pre-list

`NFR-002`'s **kept** clause is: *no second predicate answering "is this `meta.json` readable"*. A
count cannot serve that criterion — `SC-013` compares **lists** — so what follows is an enumeration
of **module-qualified symbols**, not a number.

### 5.1 Derivation command and input count

Probe: **AST walk** (`ast.FunctionDef` / `ast.AsyncFunctionDef` definitions whose name is in the
input name set), never a regex. Input name set = the six `ROUTED_CALLEES` names
(`test_inline_meta_read_gate.py:105`) **plus** the three private bypass parsers and the L2 seam
primitive from `contracts/routing-manifest.md` §3.5 —
`{load_meta, load_meta_strict, load_meta_or_empty, load_meta_fail_closed, _load_meta_fail_closed,
_require_meta, _parse_meta_text, _parse_meta_object, _parse_meta_mapping, _load_json_object}`.

```
TREE: /home/jeroennouws/dev/sk-missions/3162/src
INPUT: name set = 10 names; population = 1199 .py files
OUT:   predicate definitions = 12
  specify_cli/cli/commands/implement_cores.py:259  _parse_meta_mapping
  specify_cli/cli/commands/merge_driver.py:167  _load_json_object
  specify_cli/core/paths.py:638  load_meta_fail_closed
  specify_cli/doc_analysis/doc_state.py:68  _require_meta
  specify_cli/git/ref_advance.py:181  _parse_meta_object
  specify_cli/mission_metadata.py:280  load_meta
  specify_cli/mission_metadata.py:331  _parse_meta_text
  specify_cli/mission_metadata.py:362  load_meta_strict
  specify_cli/mission_metadata.py:385  load_meta_or_empty
  specify_cli/mission_metadata.py:474  _load_meta_fail_closed
  specify_cli/mission_metadata.py:500  _require_meta
  specify_cli/task_utils/support.py:599  load_meta
```

**10 names in, 1 199 files walked, 12 definitions out.** No definition was dropped: every match is a
real predicate.

### 5.2 The pre-list, as module-qualified symbols

| # | Symbol (module-qualified, `C-003`) | `file:line` `[shifts — cite the symbol]` | Role |
|---|---|---|---|
| P01 | `specify_cli.core.paths.load_meta_fail_closed` | `core/paths.py:638` | **L3** — the ONE public fail-closed reader |
| P02 | `specify_cli.mission_metadata.load_meta` | `mission_metadata.py:280` | the canonical parser (DEF A) |
| P03 | `specify_cli.mission_metadata.load_meta_strict` | `mission_metadata.py:362` | silent-by-contract wrapper |
| P04 | `specify_cli.mission_metadata.load_meta_or_empty` | `mission_metadata.py:385` | silent-by-contract wrapper |
| P05 | `specify_cli.mission_metadata._parse_meta_text` | `mission_metadata.py:331` | **L2** — path-level; takes a `Path` and reads itself |
| P06 | `specify_cli.mission_metadata._load_meta_fail_closed` | `mission_metadata.py:474` | module-private delegating helper (in `ROUTED_CALLEES`) |
| P07 | `specify_cli.mission_metadata._require_meta` | `mission_metadata.py:500` | module-private delegating helper (in `ROUTED_CALLEES`) |
| P08 | `specify_cli.task_utils.support.load_meta` | `task_utils/support.py:599` | DEF B — the path-signature adapter, delegates to P02 |
| P09 | `specify_cli.doc_analysis.doc_state._require_meta` | `doc_analysis/doc_state.py:68` | **locally defined**, same name as P07; the symbol that produced the census miscount |
| P10 | `specify_cli.git.ref_advance._parse_meta_object` | `ref_advance.py:181` | bypass parser (B1, B2) |
| P11 | `specify_cli.cli.commands.implement_cores._parse_meta_mapping` | `implement_cores.py:259` | bypass parser (B3, B4) |
| P12 | `specify_cli.cli.commands.merge_driver._load_json_object` | `merge_driver.py:167` | bypass parser (B5) |

> **`specify_cli.mission_metadata`, not `specify_cli.missions.mission_metadata`.** There is no
> `src/specify_cli/missions/mission_metadata.py` on this tree. The planning artifacts misqualify
> P02–P07; the module-qualified names above are the measured ones.

> **P07 and P09 share the bare name `_require_meta` and are different functions in different
> packages.** P09 is the *locally defined* one the name-matching census counts, and it is exactly why
> `contracts/routing-manifest.md` §4.6 records that `ROUTED_CALLEES` matches names rather than the
> call graph. Another reason no citation in this mission may be a bare symbol.

### 5.3 The `SC-013` comparison rule

The post-change list must be:

1. **no longer than the pre-list** — at most 12 definitions, and
2. **contain no new local predicate** — no symbol at a `file:line` that is not one of P01–P12 above.

A 1:1 `load_meta` → `load_meta_fail_closed` swap is **predicate-neutral**: both names are already in
`ROUTED_CALLEES` and both definitions (P02, P01) are already on the pre-list, so the list is unchanged
in length and in membership. **The 13 routings therefore cannot violate `NFR-002` by themselves.** The
risk `SC-013` actually guards is a **bypass site authoring a *local* answer** to "is this `meta.json`
readable" instead of routing — which is why the four non-routed bypass sites (B1, B3, B4, and B5) are
**diagnosable-only** in this mission and the **L1** pure-decode primitive is **filed, not built**
(`SC-009`, `contracts/routing-manifest.md` §3.9).

### 5.4 The mutation probe `WP06` / `WP08` will run — executed here to prove the criterion bites

The probe: plant a second local predicate at one bypass site, re-derive the list, confirm the
criterion goes **red**, revert. Run against a **scratch copy** of a single bypass file so `src/`
is untouched; quoted verbatim:

```
--- baseline (unmutated single file) ---
TREE: .../scratchpad/mutbase/src
INPUT: name set = 10 names; population = 1 .py files
OUT:   predicate definitions = 1
  specify_cli/git/ref_advance.py:181  _parse_meta_object
--- mutated ---
TREE: .../scratchpad/mutprobe/src
INPUT: name set = 10 names; population = 1 .py files
OUT:   predicate definitions = 2
  specify_cli/git/ref_advance.py:181  _parse_meta_object
  specify_cli/git/ref_advance.py:435  _require_meta
--- revert: scratch copy discarded; git status on src/ ---
(empty above = src/ untouched)
```

The planted predicate was:

```python
def _require_meta(text: str) -> dict | None:
    """PLANTED second local predicate answering "is this meta.json readable"."""
    import json
    try:
        return json.loads(text)
    except ValueError:
        return None
```

**1 in → 2 out**: the new local predicate appears at a `file:line` that is **not** on the pre-list, so
rule 2 of §5.3 is violated and `SC-013` goes red. **Reverted** (the scratch copy was discarded;
`git status --porcelain src/` is empty). The criterion is demonstrably sensitive to the exact failure
mode it exists to catch — it is not a criterion that closes by narration.

---

## §6 — `NFR-002`: what is struck, and what stands

> **STRUCK under operator ruling `R-1`.** `NFR-002`'s clause *"the routed budget is ONE call **and the
> floor is immovable**"* — the **immovability** half is **STRUCK**. **No downstream work package may
> restate it as live.**

> **STANDS.** The **budget of one net routed call** for the whole mission stands, and `WP05` is its
> sole allocator (§1, §2).

**Why the immovability fell.** Raising a *growth* floor toward the live count is the ratchet
**tightening** — the precedented operation on this gate, not a re-freeze. The precedent, recorded as a
**rule** and never as a value: on 2026-08-04 `ROUTED_LOAD_META_FLOOR` was raised **117 → 126** "to
restore the established 3-below-live gap (mechanic 2) against the corrected 129"
(`tests/architectural/test_inline_meta_read_gate.py:215-217`). A floor that may never move would have
made that correction impossible and would have left a **false-red** standing on CI — which is exactly
what happened while the floor sat at 117 against a live count of 110.

> **PROHIBITION, restated here so it binds this document too.** **No re-derived
> `ROUTED_LOAD_META_FLOOR` value and no re-derived band appears in this document or in
> `contracts/routing-manifest.md`.** `WP06` **must print the measured live routed count and derive the
> new floor from it**; copying a candidate floor or band out of `plan.md`, `analysis-report.md`, or any
> other planning artifact is **forbidden**. The hole is deliberate: filling it here would pre-empt a
> measurement `WP06` owes. Every appearance of the integer `127` in either contract is the **low bound
> of the derived band `[127, 130]`**, never a floor value.

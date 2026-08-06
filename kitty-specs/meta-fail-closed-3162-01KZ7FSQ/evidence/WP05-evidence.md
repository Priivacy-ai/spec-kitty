# WP05 evidence — make the bypass reads diagnosable, route site A

**Out-of-map planning write, with rationale**: `mark-status` carries no evidence field (its payload is
a bare `{T0xx: Status}`, `src/specify_cli/status/models.py:481`), and `kitty-specs/` paths cannot appear
in `owned_files` by construction (`mission_parsing.py:153-157`, `:207-215`). This file is WP05's
committed evidence destination, as the WP prompt directs.

**Tree**: `/home/jeroennouws/dev/sk-missions/3162` (repository root). `.worktrees/` does not exist.
Probe proving the imported module resolves to this tree:

```
specify_cli.__file__ = /home/jeroennouws/dev/sk-missions/3162/src/specify_cli/__init__.py
ref_advance.__file__ = /home/jeroennouws/dev/sk-missions/3162/src/specify_cli/git/ref_advance.py
core.paths.__file__  = /home/jeroennouws/dev/sk-missions/3162/src/specify_cli/core/paths.py
```

**Base SHA at T027**: `77e3adf25f3c1c052337dc46761b4fc01b9b33d6`, branch `feat/meta-fail-closed-3162`.

---

## Commits

| # | SHA | Subtask | Contents |
|---|---|---|---|
| 1 | `e06dfdc6f4603df3f6f9ab5cf0e72ac8e871ed09` | T028 + T029 | Site A routed onto `load_meta_fail_closed`; `Q8` comment; `SC-009` register rows 4/6/8; ATDD tests |
| 2 | `241ced5a1bd433a207393ef589b648f879ebfa2d` | T030 | Site B corrupt-at-HEAD diagnosable |
| 3 | `c660d28f3a611e94f587f3844003495493ea81b7` | T031 | Sites C and D diagnosable; registry row; bypass test file |
| 4 | `8ad575ceba45825c801ba2eb847fb5a026fff3dc` | T032 | Site E diagnosable (after `pip install -e .`) |
| 5 | `eb98551fe` | T033 | Committed evidence + mission tracer entries |
| 6 | *(this commit)* | review cycle 1 remediation | Sites C/D wired to an operator-visible surface; registry-row and evidence corrections; 6 MINORs |

Files touched across commits **1–4** — only these **7**:
`kitty-specs/.../spec.md`, `src/specify_cli/git/ref_advance.py`,
`src/specify_cli/cli/commands/implement_cores.py`, `src/specify_cli/cli/commands/merge_driver.py`,
`tests/specify_cli/git/test_ref_advance_meta_diagnosability.py`,
`tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py`,
`tests/architectural/tool_artifact_enrolment/registry/_is_self_write_only_diff.md`.

Commit **5** adds four of this WP's own planning artifacts — this evidence file and
`traces/{approach,design-decisions,tooling-friction}.md` — bringing the commits **1–5** union to
**11**, measured as the union of the five commits' own `git show --name-only`, not as a range diff
(a range would sweep in sibling lanes' commits on this shared branch). *Correction, post-review
cycle 2: this paragraph previously said "commits 1–5 — **only** these" over the 7-file list. The
list was right for 1–4; an earlier edit widened the range without widening the list. No
out-of-scope source file is involved — the four omissions are WP05's own evidence and traces.*

Commit 6 (review cycle 1 remediation) touches those same files minus `spec.md`, `ref_advance.py` and
`merge_driver.py`, plus this evidence file and **one out-of-map file**:
`src/specify_cli/cli/commands/implement.py` — declared, with its rationale, in the T031 section below.

---

## Why the one routing is forced — said out loud, as the WP requires

WP06 widens `scan_inline_meta_reads` to see `json.loads(param)` inside a **private same-module parse
helper fed by a `read_text()` call** — exactly `ref_advance:_parse_meta_object` fed from
`_meta_change_is_vcs_lock_only`. A **diagnosable-only** edit leaves that shape in place, so the widened
scanner still flags it: live inline goes **7 → 8** against a **shrink-only ceiling of 7**. Both escapes
are closed: bumping `INLINE_META_READ_FLOOR` to 8 reds `test_allowlist_matches_floor` (`:1116`), an
**equality** (`len(allowlist) == INLINE_META_READ_FLOOR`), and satisfying that needs an allow-list entry
— the re-freeze the charter forbids; weakening `test_allowlist_entries_are_still_live` (`:1166`) is
forbidden by `FR-007`. **Routing is the unique green landing state for WP06.** An implementer who "just
improves the message" here leaves WP06 unlandable.

---

## Line-number re-derivation — which line each subtask edited

Every bypass site has **three distinct lines** (path bind, read, parse). Re-derived on this tree.
`ref_advance.py` shifted **+7** after the `Q8` comment was inserted; both sets are given.

| Site | `module:symbol` | path bind | read | parse call | `json.loads` |
|---|---|---|---|---|---|
| A | `git.ref_advance:_meta_change_is_vcs_lock_only` (`:231`→`:238`) | `:242`→`:249` | `:244`→`:251` `read_text` | **`:247`→`:254`** | `:184` (in `_parse_meta_object`) |
| B | `git.ref_advance:_committed_meta_object` (`:192`) | — | `:203` `git show` | `:206` | `:184` (same helper) |
| C | `cli.commands.implement_cores:_is_self_write_only_diff` (`:388`) | `:423` | `:427` `read_bytes` | `:427` | `:263` (in `_parse_meta_mapping`) |
| D | `cli.commands.implement_cores:_committed_meta_mapping` (`:330`) | — | `:335` `show_blob` | `:338` | `:263` (same helper) |
| E | `cli.commands.merge_driver:_load_json_object` (`:167`) | — | `:171` `read_text` | `:174` | `:174` |

**`:247` is not a `json.loads` line** — it is `worktree_meta = _parse_meta_object(worktree_text)`, the
delegating call; the `json.loads` is at `:184`.

**Lines actually edited, per subtask:**

- **T029** edited `ref_advance.py:250-256` (post-comment numbering) — the `try` / `read_text` /
  `except OSError` / parse-call / `None`-arm block. **`:249` (`meta_path = worktree / path`) was KEPT**,
  because it supplies `meta_path.parent`.
- **T030** edited `ref_advance.py:_committed_meta_object`'s parse branch (the
  `_parse_meta_object(...) is None` arm at `:206-207`). The `returncode != 0` absent arm (`:204`) is
  unchanged.
- **T031** edited `implement_cores.py:428-429` (site C's `working is None` arm) and `:338` (site D's
  parse). The path bind (`:423`), the gate (`:426`) and the read (`:427`) are unchanged;
  `_parse_meta_mapping` (`:259`, `json.loads` `:263`) was **not touched at all**.
- **T032** edited `merge_driver.py:174` (the `json.loads`) **only**. `:169-170` (`missing → {}`) and
  `:172-173` (`blank → {}`) are byte-identical.

**Citation discipline (`C-003`, tightened):** every citation above is `module:symbol` **and** line.
`_resolve_mission_id` alone is defined in four modules — `charter/_io.py:358`,
`mission_runtime/resolution.py:1058`, `specify_cli/post_merge/retrospective_terminus.py:143`,
`specify_cli/decisions/service.py:112` — two of them this mission's own census sites with **opposite
arms** (row 3 degrade, row 9 refuse-typed).

---

## T027 — pre-measurement and the routing identity

**Routed PRE = `129`.** WP01's manifest anchor holds.

```
$ PYTHONPATH=<tree>/src .venv/bin/python -c "from tests.architectural.test_inline_meta_read_gate import \
  scan_routed_load_meta_calls, SRC_ROOT; print(len(scan_routed_load_meta_calls(SRC_ROOT)))"
129
```

### The band, from the three assertions quoted verbatim from source

`ROUTED_LOAD_META_FLOOR_MARGIN = 4` (`test_inline_meta_read_gate.py:220`),
`ROUTED_LOAD_META_FLOOR = 126` (`:221`). `test_routed_load_meta_floor` (`:1084`):

```python
    routed = scan_routed_load_meta_calls(SRC_ROOT)
    assert len(routed) >= ROUTED_LOAD_META_FLOOR, (
        f"routed load_meta*() census dropped to {len(routed)}; expected "
        f">= {ROUTED_LOAD_META_FLOOR}. A drop means call sites stopped routing "
        "through the canonical reader family."
    )
    assert len(routed) > ROUTED_LOAD_META_FLOOR, (
        "ROUTED_LOAD_META_FLOOR must be a concrete census integer strictly below "
        "the live routed count, not '>= len(routed)' (anti-vacuous)."
    )
    assert len(routed) - ROUTED_LOAD_META_FLOOR <= ROUTED_LOAD_META_FLOOR_MARGIN, (
        f"ROUTED_LOAD_META_FLOOR ({ROUTED_LOAD_META_FLOOR}) is more than "
        f"ROUTED_LOAD_META_FLOOR_MARGIN ({ROUTED_LOAD_META_FLOOR_MARGIN}) below the "
        f"live routed count ({len(routed)}); tighten the floor."
    )
```

Clause 2 is **strict and explicitly anti-vacuous**, so it dominates clause 1: low bound `FLOOR+1 = 127`.
Clause 3 gives high bound `FLOOR+MARGIN = 130`. **Band `[127, 130]`, two-sided. 126 is RED** — clause 2
reads `126 > 126`, false. A fold that *collapses* calls reds the gate downward just as an extra routing
reds it upward.

### The gate — verified, not assumed

`ref_advance.py:315` (pre-comment numbering; `:322` post):

```python
        if Path(path).name == _META_FILENAME and _meta_change_is_vcs_lock_only(
```

with `_META_FILENAME: str = "meta.json"` at `:45`. **Identity: `meta_path.parent / "meta.json" ==
meta_path`** by construction — the substitution reads the same file, not a different one.

### The encoding — verified, not assumed

Replaced read: `worktree_text = meta_path.read_text(encoding="utf-8")` (`:244`).
`mission_metadata.load_meta`'s default (`:285`): `encoding: str = _UTF8`, with `_UTF8: str = "utf-8"`
at `:31`. **Not** BOM-tolerant `utf-8-sig`, so routing does not change BOM behaviour.

### Sole consumer

```
$ grep -rn '_meta_change_is_vcs_lock_only' src/ tests/
src/specify_cli/git/ref_advance.py:231:def _meta_change_is_vcs_lock_only(
src/specify_cli/git/ref_advance.py:315:        if Path(path).name == _META_FILENAME and _meta_change_is_vcs_lock_only(
```

**2 hits in → 1 definition + 1 call site out.** One consumer, as claimed.

### `C901` PRE (ceiling 15)

```
=== C901 PRE: src/specify_cli/git/ref_advance.py ===            All checks passed!   exit=0
=== C901 PRE: src/specify_cli/cli/commands/implement_cores.py === All checks passed! exit=0
=== C901 PRE: src/specify_cli/cli/commands/merge_driver.py ===   All checks passed!  exit=0
```

---

## T028 — filings, and they precede the code

| `SC-009` row | Filing | Issue | Created (UTC) |
|---|---|---|---|
| 4 | `Q8` — duplicated lock-only comparison | **#3228** | `2026-08-06T01:11:16Z` |
| 6 | **L1** pure-decode primitive (filed, not built) | **#3229** | `2026-08-06T01:11:41Z` |
| 8 | `Q2` residue — full routing of the 4 non-routed sites | **#3230** | `2026-08-06T01:12:07Z` |

`gh issue view <n> --json number,title,body` was run and quoted for all three (see transcript).

**Precedence proved** — filings vs `git log --format=%cI`:

| Event | Time (UTC) |
|---|---|
| #3228 filed | `2026-08-06T01:11:16Z` |
| #3229 filed | `2026-08-06T01:11:41Z` |
| #3230 filed | `2026-08-06T01:12:07Z` |
| Commit 1 `e06dfdc6f` | `2026-08-06T01:21:25Z` (`03:21:25+02:00`) |
| Commit 2 `241ced5a1` | `2026-08-06T01:26:14Z` |
| Commit 3 `c660d28f3` | `2026-08-06T01:35:18Z` |
| Commit 4 `8ad575ceb` | `2026-08-06T01:37:22Z` |

**All three filings precede all four code commits.**

`Q8`'s number is cited in a code comment immediately above
`git.ref_advance:_is_vcs_lock_only_meta_change` — the surviving comparator this WP's routed site keeps
feeding. The comparators were **not** unified (`C-009`, `DIR-024`).

### Measured correction to `Q8`'s premise

The WP and `C-009` say the lock-only comparison exists in **three** copies. Measured: **two**.

> **Correction (review cycle 1 MINOR).** This paragraph first reported the grep as **6 lines**. It
> returns **7**. The seventh is WP05's own `Q8` comment at `ref_advance.py:232` — the WP added it and
> then quoted a count taken before it existed. Re-measured on the committed tree:
> `grep -rn '_VCS_LOCK_META_FIELDS' src/ | wc -l` → **7**. The decomposition that carries the
> conclusion (2 declarations, 2 comparators) is unchanged; only the total was stale.

`grep -rn '_VCS_LOCK_META_FIELDS' src/` → **7 lines** = **2 declarations** (`ref_advance.py:42`,
`implement_cores.py:50`) + 2 docstring references (`implement_cores.py:246`, `ref_advance.py:246`)
+ 2 uses (`implement_cores.py:256`, `ref_advance.py:257`) + **1 `Q8` comment**
(`ref_advance.py:232`, added by this WP), with **2 comparators**
(`git.ref_advance:_is_vcs_lock_only_meta_change:210`,
`cli.commands.implement_cores:_is_vcs_lock_only_meta_diff:241`). The third candidate,
`specify_cli.acceptance:ACCEPTANCE_PROVENANCE_FIELDS` (`acceptance/__init__.py:76`), is a **7-field
acceptance-provenance overlay** — a different concept, not a copy. Recorded in the issue and in the
register cell. The two comparators are also **not equivalent**: `ref_advance`'s uses `.get()` (absent
and `None`-valued are indistinguishable) while `implement_cores`' uses a `_MISSING_META_VALUE` sentinel
(`:52`) and so distinguishes them.

---

## T029 — Commit 1, the routing, and the headroom

**RED first**, on the base behaviour (`5 failed, 2 passed` of 7; the 2 passing are negative controls,
correctly green on both sides):

```
FAILED tests/specify_cli/git/test_ref_advance_meta_diagnosability.py::test_corrupt_worktree_meta_blocks_advance_and_is_diagnosed
FAILED tests/specify_cli/git/test_ref_advance_meta_diagnosability.py::test_non_utf8_worktree_meta_is_diagnosed_instead_of_escaping
FAILED tests/specify_cli/git/test_ref_advance_meta_diagnosability.py::test_corrupt_blob_at_head_is_diagnosed
FAILED tests/specify_cli/git/test_ref_advance_meta_diagnosability.py::test_valid_blob_at_head_emits_no_diagnosis
FAILED tests/specify_cli/git/test_ref_advance_meta_diagnosability.py::test_absent_at_head_is_not_reported_as_corrupt
==================== 5 failed, 2 passed in 79.37s (0:01:19) ====================
```

**The red also proves the assertions are non-vacuous.** The baseline message already contains
`meta.json` *and* the path, because the porcelain line is ` M kitty-specs/…/meta.json`:

```
E   assert 'could not be decoded' in "Refusing to advance branch 'kitty/mission-3162-meta-diagnosability' …
E       Dirty entries:
E          M kitty-specs/3162-meta-diagnosability/meta.json
```

So an assertion of the form `"meta.json" in text and path in text` **passes on the unrouted baseline
and proves nothing**. Every `SC-012` assertion therefore also requires the diagnosis phrase
`could not be decoded`, which no baseline arm emits.

**GREEN at the commit**: `4 passed in 69.95s`, 4 selected.

### The routed pair

```
routed PRE  = 129
routed POST = 130
FLOOR            = 126   (unchanged -- WP06 re-derives it, FR-008)
MARGIN           = 4
clause 1  n >= F        : 130 >= 126 -> True
clause 2  n >  F        : 130 >  126 -> True   (strict, anti-vacuous)
clause 3  n - F <= M    : 4 <= 4 -> True
band             = [127, 130]  -> 130 in band: True
inline live      = 7 (floor 7) -- untouched by WP05
```

**Attribution, measured rather than asserted** (the tree is shared — see the concurrency note below):
`git/ref_advance.py` held **0** routed sites at HEAD and holds **exactly 1** after the edit
(`('src/specify_cli/git/ref_advance.py', 277)`). The `+1` is WP05's and nothing else's.

### No ledger movement

```
$ grep -c 'load_meta(' src/specify_cli/git/ref_advance.py
0
$ git diff --stat feat/meta-fail-closed-3162 -- tests/specify_cli/test_meta_fail_closed_full_census_contract.py
(empty)
```

`scan_load_meta_call_sites` matches the exact name `load_meta` (`_TARGET`), and `load_meta_fail_closed(`
does not match it, so routing neither adds nor deletes a ledger row.

### `MissionMetaReadError` caught by name

```
MissionMetaReadError MRO: ['MissionMetaReadError', 'RuntimeError', 'Exception', 'BaseException', 'object']
issubclass(MissionMetaReadError, ValueError) = False
issubclass(MissionMetaReadError, OSError)    = False
```

It is a `RuntimeError` (`core/paths.py:506`), so neither the pre-existing `except OSError` nor any
`except ValueError` would have caught it. The catch is **mandatory**; without it the routing converts
"corrupt meta is genuine dirt" into an uncaught crash in the dirty-worktree scan. It is caught **by
name**, never `except Exception`.

### The deliberate behaviour delta — an IMPROVEMENT, not a regression

`except OSError` (`:245`) does **not** catch `UnicodeDecodeError`, which is a `ValueError` subclass, so
a non-UTF-8 `meta.json` escaped `_meta_change_is_vcs_lock_only` **uncaught**. Reproduced live in the red
run, not assumed:

```
E   UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 10: invalid start byte
```

After routing, `_parse_meta_text` lists `UnicodeDecodeError` explicitly
(`mission_metadata.py:349`, `#3163`), so that input is blocked-and-diagnosed. Asserted by
`test_non_utf8_worktree_meta_is_diagnosed_instead_of_escaping`. **`NFR-003` binds the four degrade
sites, not this one.**

---

## T030 — Commit 2, site B

**Design choice, stated as the WP requires.** T030 offered two options (message in the caller, or an
optional subject argument on `_parse_meta_object`). **A third, narrower option was taken: the
diagnosability lives in the caller and `_parse_meta_object` is not touched at all** — neither converted
to raise nor given a parameter. Reason: it is imported by the **run-only**
`tests/regression/test_issue_2795_claim_blocker.py` (`:55`), whose
`test_parse_meta_object_handles_malformed_and_non_object` (`:291-294`) pins it to return `None` for
`"{not json"` and `"[1, 2, 3]"`. That file is not in `owned_files`, so leaving its signature untouched
is strictly safer than adding a parameter to it.

The absent-vs-corrupt arms stay distinct: `returncode != 0` → absent-at-HEAD → `{}` **silent**;
`_parse_meta_object(...) is None` → corrupt-at-HEAD → `{}` **plus a message**. Neither function's return
type or value set changed.

Verification:

- `tests/regression/test_issue_2795_claim_blocker.py`: **`9 passed in 72.14s`**
- `test_parse_meta_object_handles_malformed_and_non_object`: **`1 passed in 69.98s`**
- `git diff --stat feat/meta-fail-closed-3162 -- tests/regression/` → **empty**
- `tests/specify_cli/git/test_ref_advance_meta_diagnosability.py`: **`7 passed in 70.48s`**, 7 selected

---

## T031 — Commit 3, sites C and D, and the registry row

- `_parse_meta_mapping`'s `dict | None` return contract is **unchanged** (both callers depend on it).
- Site C keeps returning `False`; site D keeps returning `None` for absent.
- The module is deliberately free of console/typer side effects, so the diagnosis is **collected**
  into a `diagnostics` sink rather than printed, and an executor emits it.

> **Correction (review cycle 1 BLOCKER).** As first written, this bullet was true but incomplete in
> the way that mattered: it said the diagnosis is "collected rather than printed" and stopped there.
> It did not disclose that **no production caller collected it**. `diagnostics` was an optional
> parameter defaulting to `None`; the sole production caller of `_is_self_write_only_diff`
> (`implement_cores.py:619-620`) passed nothing, and `_committed_meta_mapping`'s only production call
> is nested inside that same function, so it inherited the same `None`. The two tests that covered
> sites C and D allocated the list themselves, so they passed on a tree where the operator saw
> nothing new. `SC-012`'s bar is *operator-visible*, not "collected somewhere" — at sites C and D the
> generic dirty-worktree refusal remained the only thing an operator saw, and the criterion was not
> met. The remediation below closes that gap; the reachability of every row is now stated explicitly
> in the `SC-012` table.

- **Reachability, wired (remediation).** `resolve_planning_artifact_staging` takes the sink and
  threads it into its `_self_write` predicate; the git executor
  `implement._ensure_planning_artifacts_committed_git` allocates the list, passes it in, and prints
  each (deduped) note through `console` before the generic "Planning artifacts not committed"
  listing. This is the same "core collects, executor emits" split the module already uses for
  `structural`, and the same shape as site A/B's `ref_advance.py:382-389`.
  - **Out-of-map edit, declared:** `src/specify_cli/cli/commands/implement.py` is **not** in WP05's
    `owned_files`. The executor half cannot live anywhere else — `implement_cores.py` imports no
    `console`/`typer` and moving one in would be an architectural change, not a diagnosability fix.
    The edit is confined to `_ensure_planning_artifacts_committed_git`: one sink allocation, one
    keyword argument, one two-line print loop, plus comments. No other behaviour in that file
    changes.
- Registry row updated **in place, prose only**: `symbol:` (`_is_self_write_only_diff`), `literals:`
  (`_WP_SELF_WRITE_FILENAME_RE`), `status:` and `retirement-wp:` are all unchanged.
  `tests/architectural/` was touched at **file level only** — never globbed (a
  `tests/architectural/**` glob would union this lane with WP06's).

Verification:

- sites C+D selection: **`6 passed, 5 deselected in 123.27s`** (6 selected)
- `tests/architectural/test_exemption_registry_ratchet.py`: **`12 passed in 77.72s`**
- `tests/specify_cli/cli/commands/test_implement_cores.py` (run-only, not edited): **`64 passed in
  76.01s`**; `git diff --stat feat/meta-fail-closed-3162 --` on it prints nothing.

---

## T032 — Commit 4, site E, reinstall first

**`pip install -e .` ran BEFORE any merge-driver evidence** (exit `0`):

```
Successfully installed spec-kitty-cli-3.2.6
console_script: spec-kitty -> specify_cli:main
$ .venv/bin/spec-kitty merge-driver-meta --help
 Usage: spec-kitty merge-driver-meta [OPTIONS] BASE OURS THEIRS
 Field-merge conflicting ``meta.json`` blobs; write result to ``ours``.
```

The driver is registered as a **subprocess** (`lanes/merge.py`, all three quoted from source):

```
82:        config_key="spec-kitty-meta",
84:        command="spec-kitty merge-driver-meta %O %A %B",
85:        pattern="kitty-specs/**/meta.json",
```

The handler that keeps the exit code unchanged (`merge_driver:merge_driver_meta`). Coordinates are
**post-edit** — re-derived on the committed tree, since this WP's own `+15` lines in
`merge_driver.py` moved the handler down:

```
261:    except (json.JSONDecodeError, EventLogMergeError) as exc:
262:        typer.echo(str(exc), err=True)
263:        raise typer.Exit(1) from exc
```

> **Correction (review cycle 1 MINOR).** This block was quoted at `:246-248`, a pre-edit coordinate
> (an even earlier draft said `:245-247`). The quoted **text** was verbatim correct in every version;
> only the line numbers were stale. `:261-263` is the committed-tree location.

It catches **both**, so raising `EventLogMergeError` instead of letting `json.JSONDecodeError` escape
leaves exit-code behaviour identical.

**`_parse_json_document` (`:322`) untouched** — the row-matrix reader, a structural lookalike whose
subject is not `meta.json`:

```
$ git diff -- src/specify_cli/cli/commands/merge_driver.py | grep -E '^[+-]' | grep -i 'parse_json_document\|RowMatrixMergeError'
(empty)
```

Verification (all post-reinstall):

- `tests/merge/test_merge_driver_wrappers_2709.py`: **`10 passed in 123.90s`**, 10 selected, including
  `test_load_json_object_missing_returns_empty` (`:96`), `test_load_json_object_blank_returns_empty`
  (`:100`), `test_load_json_object_reads_object` (`:106`),
  `test_load_json_object_rejects_non_object` (`:112`), and
  `test_meta_wrapper_translates_bad_json_to_exit1` (`:141`).
- `tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py`: **`11 passed in 77.66s`**, 11
  selected.

---

## T033 — `SC-012`, `SC-013`, the seam family and the gates

### `SC-012` — the table

**Convention, declared: 5 read expressions / 6 invocation sites.** They differ because site E is one
read expression invoked at two call sites (`merge_driver.py:243` `ours`, `:244` `theirs`). A
read-expression count and a call-site count are **never addable**. Input count for the derivation:
`grep -n '_load_json_object' src/specify_cli/cli/commands/merge_driver.py` → 3 hits in → 1 dropped as
the `def` line at `:167` → **2 invocation sites out**.

Every message below was captured by running the corrupt fixture, and is asserted on **text**, not on
exception type. Each row carries its valid-file negative control.

**Reachability is a separate column, and it is the one `SC-012` grades.** A message that exists is
not the same as a message an operator sees. Each row therefore names the operator-visible surface it
reaches and the test that drives that surface through a **production entry point**.

> **Correction (review cycle 1 BLOCKER).** The first version of this table had no reachability
> column. Rows C and D sat beside A, B and E as if they satisfied the same criterion; they did not.
> Their messages were appended to a `diagnostics` sink that **no production caller supplied**, so at
> sites C and D nothing an operator sees changed and `SC-012` was unmet for 2 of the 5 read
> expressions. The message text quoted for C and D was authentic then and is unchanged now — the
> defect was reachability, not authenticity. Both rows are now wired to an operator-visible surface
> and the column below records how.

| # | Site — `module:symbol` | Outcome | Corrupt-fixture message (quoted verbatim) | Valid-file control | Operator-visible via |
|---|---|---|---|---|---|
| A | `git.ref_advance:_meta_change_is_vcs_lock_only` | **ROUTED** | `kitty-specs/demo/meta.json: meta.json could not be decoded (Cannot read /tmp/…/kitty-specs/demo/meta.json: Malformed JSON in /tmp/…/kitty-specs/demo/meta.json: Expecting property name enclosed in double quotes: line 1 column 2 (char 1) — fail-closed (meta.json exists but is corrupt or unreadable)); treated as genuine local state` — returns `False` | notes `[]` | `_dirty_entries` allocates `notes` (`ref_advance.py:382`) and folds `notes[0]` into the refusal line (`:389`). Driven end-to-end by `test_corrupt_worktree_meta_blocks_advance_and_is_diagnosed` through `advance_branch_ref`. **Reachable.** |
| B | `git.ref_advance:_committed_meta_object` | diagnosable | `HEAD:kitty-specs/demo/meta.json: meta.json could not be decoded at HEAD (committed blob is not a JSON object); treating every working-copy key as changed` — returns `{}` | returns `{'slug': 'x'}`, notes `[]`; **absent-at-HEAD** returns `{}`, notes `[]` — distinct from corrupt | Same sink: `_meta_change_is_vcs_lock_only` passes its own `diagnostics` down at `ref_advance.py:314-316`, so B's note lands in the same `notes` list `:389` folds into the refusal. **Reachable.** |
| C | `cli.commands.implement_cores:_is_self_write_only_diff` | diagnosable | `/tmp/…/kitty-specs/demo/meta.json: meta.json could not be decoded; not treated as a self-write-only diff` — returns `False` | notes `[]` | `resolve_planning_artifact_staging(..., diagnostics=…)` → `implement._ensure_planning_artifacts_committed_git` allocates the sink and `console.print`s each note before the generic listing. Driven through that executor by `TestSitesCandDReachTheOperator::test_site_c_corrupt_working_meta_is_operator_visible`. **Reachable (was NOT — see correction above).** |
| D | `cli.commands.implement_cores:_committed_meta_mapping` | diagnosable | `HEAD:kitty-specs/demo/meta.json: meta.json could not be decoded at HEAD (committed blob is not a JSON object)` — returns `None` | returns the mapping, notes `[]` | Same executor and same sink (inherited through `_is_self_write_only_diff`, `implement_cores.py:467-469`). Driven by `TestSitesCandDReachTheOperator::test_site_d_corrupt_committed_meta_is_operator_visible`. **Reachable (was NOT — see correction above).** |
| E (inv. 1 `ours`, inv. 2 `theirs`) | `cli.commands.merge_driver:_load_json_object` | diagnosable | `/tmp/…/meta.json: meta.json could not be decoded (Expecting property name enclosed in double quotes: line 1 column 2 (char 1))` | valid → `{'slug': 'x', 'vcs': 'git'}`; **missing → `{}`**; **blank → `{}`** (pinned tolerances intact) | `merge_driver_meta` catches `EventLogMergeError` and echoes it to **stderr** before `Exit(1)` (`merge_driver.py:261-263`). **Reachable.** |

Every message names **`meta.json`** and **the path**. **5 read expressions / 6 invocation sites, all
covered**; both of site E's invocations are asserted (parametrized over which side is corrupt).

### `SC-013` — predicate-symbol list, post

Same AST walk and same 10-name set as WP01 §5.1:

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

**12 out, identical to WP01's pre-list P01–P12** in membership *and* `file:line`. Rule 1 (no longer
than the pre-list): 12 ≤ 12 ✓. Rule 2 (no new local predicate): no symbol at a `file:line` outside
P01–P12 ✓. The diagnosability edits added **no** new predicate — they route or annotate, they do not
author a local answer to "is this `meta.json` readable".

### `SC-013` mutation probe — run and reverted

Run against a **scratch copy** of one bypass file so `src/` is never touched.

```
--- STEP 1: baseline (unmutated single file) ---
INPUT: name set = 10 names; population = 1 .py files
OUT:   predicate definitions = 1
  specify_cli/git/ref_advance.py:181  _parse_meta_object
--- STEP 2: mutated ---
INPUT: name set = 10 names; population = 1 .py files
OUT:   predicate definitions = 2
  specify_cli/git/ref_advance.py:181  _parse_meta_object
  specify_cli/git/ref_advance.py:507  _require_meta
--- STEP 3: REVERT (scratch copy discarded) ---
ls: cannot access '…/scratchpad/mut': No such file or directory
```

Planted predicate: a second local `_require_meta(text) -> dict | None`. **1 in → 2 out**: it appears at
a `file:line` **not** on the pre-list, violating rule 2, so `SC-013` goes **RED**. Reverted; the probe
left `src/` untouched (the only `src/` modifications at that moment were T031/T032's own pending
commits, since committed).

### The seam family, and the denominator as integers

| Tier | Symbol | Status in this mission |
|---|---|---|
| **L1** | — | **MISSING — filed, not built** (#3229, T028) |
| **L2** | `specify_cli.mission_metadata:_parse_meta_text` (`mission_metadata.py:331`) | exists; `Path`-only, so it **cannot** serve sites B/D (blobs already in memory) |
| **L3** | `specify_cli.core.paths:load_meta_fail_closed` (`core/paths.py:638`) | exists; **reached by site A here**, available to site C on budget |

**Denominator: 1 routed / 4 diagnosable-only / 0 allowlisted.**

### The two struck claims, named as struck

1. **`C-004`'s "structurally cannot use the seam" is REFUTED and STRUCK.** Sites **A** and **C** hold
   real filesystem paths whose parents are feature dirs — `meta_path = worktree / path` under the
   `Path(path).name == _META_FILENAME` gate, and `source = (repo_root / Path(repo_rel)).resolve()`
   (`implement_cores.py:423`) under the `name == _META_JSON_FILENAME` gate (`:426`). The obstacle at
   site C is the **routed budget**, not structure. This evidence does not repeat the struck claim, and
   the `Q2` issue and the registry row both record the correct reason.
2. **`NFR-002`'s immovable-floor clause is STRUCK** under operator ruling `R-1`. The **budget of one
   net routed call stands** and WP05 is its sole allocator; the **immovability does not**. WP05 did not
   move `ROUTED_LOAD_META_FLOOR` — it still reads **126** — because WP06 owns that re-derivation
   (`FR-008`), and copying a floor or band from any planning artifact is forbidden.

### The cone

```
$ pytest tests/specify_cli/git \
         tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py \
         tests/merge \
         tests/lanes/test_issue_2993_lane_planning_ancestry.py \
         tests/specify_cli/cli/commands/test_implement_cores.py \
         tests/regression/test_issue_2795_claim_blocker.py -ra
collected 744 items
================= 744 passed, 2 warnings in 137.89s (0:02:17) ==================
exit=0
$ grep -c '^ERROR tests/' → 0
```

**744 passed / 744 selected / exit=0.** `-ra`, never `-rf`. **No `tests/sync`, no `tests/cli`** were
run at any point (`C-007` — sibling missions hold those windows). Note the byte-identical file lives
under `tests/specify_cli/cli/commands/`, which is **not** the barred top-level `tests/cli`.

### Quality gates

`ruff check` — **clean** on all three source files and both test files. **`ruff format` was never run.**

`mypy --strict`:

- `src/specify_cli/git/ref_advance.py` — `Success: no issues found`
- `src/specify_cli/cli/commands/implement_cores.py` — `Success: no issues found`
- `src/specify_cli/cli/commands/merge_driver.py` — **one PRE-EXISTING error, not introduced by WP05**:
  `merge_driver.py:645: error: Returning Any from function declared to return "dict[str, Any]"
  [no-any-return]`. Attributed by measurement: the identical error is present on the committed HEAD
  version at line **630**, and WP05's edit adds a net **+15** lines above it (630 + 15 = 645). The
  expression is `AcceptanceMatrix.from_dict(merged_document).to_dict()` — untouched by this WP and
  outside its surface. Not "fixed" here: doing so would be scope creep into unrelated code.

`C901` (ceiling **15**), PRE and POST, per file:

| File | PRE | POST |
|---|---|---|
| `src/specify_cli/git/ref_advance.py` | All checks passed | All checks passed |
| `src/specify_cli/cli/commands/implement_cores.py` | All checks passed | All checks passed |
| `src/specify_cli/cli/commands/merge_driver.py` | All checks passed | All checks passed |

Named explicitly, all below the ceiling both before and after:
`git.ref_advance:_meta_change_is_vcs_lock_only`, `git.ref_advance:_committed_meta_object`,
`cli.commands.implement_cores:_is_self_write_only_diff`.

---

## `SC-008` — byte-identity, proved per-commit

> **Correction (review cycle 1 MINOR).** The original proof ran
> `git diff --stat feat/meta-fail-closed-3162 -- <path>` from a checkout **of that same branch**. That
> is a working-tree-vs-tip diff, and WP05's changes are *on* the tip — so it returns empty whether or
> not WP05 touched the file. It could not have gone red, and it is dropped here rather than kept
> alongside the real proof. The `ls` guard it was paired with did rule out the nonexistent-path false
> green, but not this one. **The obligation-bearing command is per-commit**, and it is the only one
> this section now relies on. The substance was never in doubt; the quoted method did not prove it.

The obligation is that WP05 did not modify three specific paths. A commit either contains a path or it
does not, so the question is decided by asking each of WP05's commits directly:

```
$ git show --name-only --format="" <sha> -- <path>
```

over WP05's five SHAs (`e06dfdc6f`, `241ced5a1`, `c660d28f3`, `8ad575ceb`, `eb98551fe`) — empty output
means that commit does not touch that path. Input count: **5 SHAs × 3 paths = 15 invocations**.

| Obligated path | Commits touching it |
|---|---|
| `tests/specify_cli/cli/commands/test_row_aware_merge_driver.py` | **0 of 5** |
| `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` | **0 of 5** |
| `kitty-specs/meta-fail-closed-3162-01KZ7FSQ/contracts/` | **0 of 5** |

**Controlled against a known answer — the probe is not vacuous.** The same loop over a path WP05 *did*
change returns a hit, so "0 of 5" is a measurement and not an artefact of a probe that can only print
nothing:

```
$ for s in e06dfdc6f 241ced5a1 c660d28f3 8ad575ceb eb98551fe; do \
    git show --name-only --format="" $s -- src/specify_cli/cli/commands/implement_cores.py; done
src/specify_cli/cli/commands/implement_cores.py       <- c660d28f3, 1 of 5
```

The three obligated paths all exist (so "0 of 5" is not the nonexistent-path false green either):

```
$ ls tests/specify_cli/cli/commands/test_row_aware_merge_driver.py
tests/specify_cli/cli/commands/test_row_aware_merge_driver.py
ls exit=0
$ ls tests/specify_cli/test_meta_fail_closed_full_census_contract.py
tests/specify_cli/test_meta_fail_closed_full_census_contract.py
ls exit=0
$ ls kitty-specs/meta-fail-closed-3162-01KZ7FSQ/contracts/
headroom-allocation.md
routing-manifest.md
ls exit=0
```

Note that the `ls` guard alone would not have sufficed: for a nonexistent path such as
`tests/merge/test_row_aware_merge_driver.py`, `ls` exits **2** while the old `git diff --stat` still
printed nothing — which is precisely why the per-commit form, not the diff, carries this criterion.

---

## Concurrency hazard encountered — flagged, not papered over

**This WP did not run in an isolated worktree, and a sibling agent was committing to the same branch
and the same working tree throughout.** Observed during WP05: `src/specify_cli/bulk_edit/gate.py`,
`src/specify_cli/missions/_read_path_resolver.py`,
`tests/specify_cli/test_meta_fail_closed_full_census_contract.py`,
`tests/regression/test_issue_2804_merge_resets_gate_artifacts.py` and several planning files were
modified and committed by WP02/WP07 while WP05 was in flight, and `HEAD` moved from
`5ee77834a` → `77e3adf25` between two consecutive commands at the start.

Consequences and how each was handled:

- **Every commit was path-scoped.** `git add <explicit paths>` only; never `git add -A`, never
  `git commit -a`. WP05 commits 1–4 contain exactly the seven files listed at the top; commit 5 adds
  this evidence file and the three `traces/` files, for a measured union of **11** across commits 1–5.
  Nothing else, and no sibling lane's file, appears in any of them.
- **The routed pre/post pair was taken across a moving tree.** Both `129` and `130` were measured with
  sibling dirt present, so the `+1` delta is still attributable; and it was independently confirmed at
  file granularity (`ref_advance.py`: 0 routed sites at HEAD → exactly 1 after the edit).
- **The census-ledger byte-identity obligation was briefly unsatisfiable through no fault of WP05**:
  early in the WP, `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` was dirty with
  WP02's row deletion. It later landed on the branch, so the diff against the branch tip is now empty.
  WP05's own commits touch **zero** lines of that file — verified per-SHA.

---

## Deviations, corrections and unverifiable items

1. **`spec-kitty implement WP05` could not prepare a workspace.** The WP's "Where this WP runs" section
   says to start with it. Run as directed it fails the dependency gate:
   `dependencies_not_satisfied: WP05 depends on WP01; all dependencies must be approved or done before
   implementation can start` — **WP01 is in `for_review`, not `approved`/`done`**. The command also
   requires `--mission <slug>`, which the WP does not mention. Work proceeded from the repository root
   (which is what the WP prescribes anyway: "This WP runs from the repository root"), with the
   module-`__file__` probe above proving the tree.
2. **`Q8`'s "×3" is wrong; measured ×2.** See T028 above. Recorded in the issue and the register.
3. **`_is_self_write_only_diff` is at `implement_cores.py:388`** — confirmed by grep re-derivation. An
   intermediate `sed` window suggested `:386`; the grep is authoritative and matches the WP.
4. **`merge_driver.py`'s non-object message is at `:176`** (the `raise`), with `:175` the
   `if not isinstance(...)`. The WP's `:175-176` is the two-line span — consistent.
5. **The `mypy --strict` pre-existing error** in `merge_driver.py` is reported rather than hidden or
   "fixed"; see the Quality gates section for its attribution.
6. **Nothing in this WP is `[UNVERIFIED]`.** Every number reported was measured on this tree with the
   command shown. The one number WP05 deliberately did **not** derive is the new
   `ROUTED_LOAD_META_FLOOR` — that is WP06's obligation (`FR-008`), and copying a candidate value is
   forbidden by both contracts.

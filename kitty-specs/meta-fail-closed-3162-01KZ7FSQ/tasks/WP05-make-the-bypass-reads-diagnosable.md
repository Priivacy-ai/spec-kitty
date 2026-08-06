---
work_package_id: WP05
title: Make the bypass reads diagnosable, route ref_advance.py:247, and file Q8 + the L1 primitive
dependencies:
- WP01
requirement_refs:
- FR-005
- NFR-002
- C-003
- C-004
- C-009
planning_base_branch: feat/meta-fail-closed-3162
merge_target_branch: feat/meta-fail-closed-3162
branch_strategy: Planning artifacts for this mission were generated on feat/meta-fail-closed-3162. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/meta-fail-closed-3162 unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
- T031
- T032
- T033
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent:
- tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py
execution_mode: code_change
owned_files:
- src/specify_cli/git/ref_advance.py
- src/specify_cli/cli/commands/implement_cores.py
- src/specify_cli/cli/commands/merge_driver.py
- tests/specify_cli/git/**
- tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py
- tests/architectural/tool_artifact_enrolment/registry/_is_self_write_only_diff.md
role: implementer
tags: []
tracker_refs: []
---

# WP05 — Make the bypass reads diagnosable, route `ref_advance.py:247`, and file `Q8` + the L1 primitive

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile named in the frontmatter, and behave according to
its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and pick the best match for this WP's
`task_type` and `authoritative_surface`.

---

## Objective

Five read expressions parse `meta.json` without reaching the canonical seam at all. **Four become
diagnosable only**; **one is routed** — `specify_cli.git.ref_advance:_meta_change_is_vcs_lock_only`, the site
the census calls `ref_advance.py:247`, onto `load_meta_fail_closed(meta_path.parent)` (operator ruling
**R-1**). Then file `Q8` and the **L1 pure-decode primitive** instead of absorbing either (`C-009`).

## Where this WP runs, how to start it, and where its evidence lands

**This WP runs from the repository root.** Every path below is repo-relative from the tree you are in, and
`pip install -e .` (T032) only means what this prompt says it means in the tree `.venv` was installed from.
Start with `spec-kitty implement WP05` — `spec-kitty agent action implement WP05 --agent <name>` does **not**
resolve a workspace, its `--help` reads *"Display work package prompt with implementation instructions."*, and
`CLAUDE.md` § Execution Workspace Strategy is explicit that *"`spec-kitty implement WP##` is the only supported
way to prepare a workspace."*

**`PYTHONPATH=<workspace>/src` on every `python -c` and every `pytest` that could run outside the repository
root.** The split-tree hazard produces a *silently wrong* answer rather than an error:
`.venv/lib/python3.11/site-packages/_editable_impl_spec_kitty_cli.pth` pins `specify_cli` / `runtime` imports to
the **main** tree's `src/`, while `SRC_ROOT` in the gate
(`tests/architectural/test_inline_meta_read_gate.py:61`) and `_SRC_ROOT` in the ledger test
(`tests/specify_cli/test_meta_fail_closed_full_census_contract.py:54`) derive from **the test file's own
location**. Outside the install tree the AST census reads the *edited* `src/` while behavioural assertions
import the *unedited* one — a structural assertion goes green while its behavioural twin stays red, with no
diagnosable cause. Two concrete consequences here: the `129 → 130` routed pair is the mission's **entire**
headroom and a count taken through the wrong tree is unattributable; and the merge-driver subprocess resolves
through the installed console script, not through `PYTHONPATH`, so **reinstall** rather than reaching for an
import path (T032). Nothing provisions `.venv` into a git worktree (`.gitignore:31-32`).

**Committed evidence destination.** `mark-status` exposes only `--status`, `--mission`, `--auto-commit`,
`--json`; its payload is `WPInnerStateDelta.subtasks: Mapping[str, Status]`
(`src/specify_cli/status/models.py:481`) — a bare `{T0xx: Status}`, **no evidence field**. This WP's committed
destination is `kitty-specs/meta-fail-closed-3162-01KZ7FSQ/evidence/WP05-evidence.md`, a declared **out-of-map**
planning write with a one-line rationale (`kitty-specs/` paths cannot appear in `owned_files` by construction —
`mission_parsing.py:153-157`, `:207-215`). The `SC-012` table, the `SC-013` pre/post diff and its reverted
mutation probe, the routed `129`/`130` pair, the three `gh issue view` outputs, the four SHAs and the `C901`
pairs all go **into that file**. `$EV` is a scratch redirect target quoted into it; nothing load-bearing is left
in `/tmp`.

## Context

### Why the one routing is forced, not a style preference

WP06 widens `scan_inline_meta_reads` specifically to see `json.loads(param)` inside a **private same-module
parse helper fed by a `read_text()` call** — exactly the shape of `ref_advance:_parse_meta_object` fed from
`_meta_change_is_vcs_lock_only`. A **diagnosable-only** edit leaves that shape in place, so the widened
scanner still flags it: live inline goes **7 → 8** against a **shrink-only ceiling of 7**. Every escape is
closed:

- Bumping `INLINE_META_READ_FLOOR` to 8 reds `test_allowlist_matches_floor` (`:1116`), an **equality** —
  `len(allowlist) == INLINE_META_READ_FLOOR`. Satisfying it means an allowlist entry, i.e. raising
  `inline_meta_read_baseline` from 7 — the **re-freeze the charter forbids** (Burn-down Policy §(a)).
- Weakening `test_allowlist_entries_are_still_live` (`:1166`) is forbidden by `FR-007`.

**Routing is therefore the unique green landing state for WP06.** An implementer who "just improves the
message" here leaves WP06 unlandable. Say this out loud in your evidence.

### The seam fits verbatim at that site — verified, not assumed

The only consumer is `ref_advance.py:315`, gated on `Path(path).name == _META_FILENAME` (`:45`,
`"meta.json"`), so `meta_path.parent / "meta.json" == meta_path` by construction. Encoding matches too: the
site reads `read_text(encoding="utf-8")` (`:244`) and `mission_metadata.load_meta`'s default is
`encoding=_UTF8` (`:285`, `_UTF8 = "utf-8"` at `:31`) — **not** BOM-tolerant `utf-8-sig`. Re-verify both
before relying on the identity; without the gate the substitution reads a different file.

### Line-number hazard — re-derive before editing, and say which line you edited

Every bypass site has **three distinct lines** — path binding, read, parse — and the artifacts cite
different ones: `plan.md` the reads (`:203`, `:335`), the census the parses (`:206`, `:338`). Re-derive all
three and state which one each subtask edits. Derived on the tree at authoring time:

| Site | module:symbol | path bind | read | parse call | `json.loads` |
|---|---|---|---|---|---|
| A | `git.ref_advance:_meta_change_is_vcs_lock_only` | `:242` | `:244` `read_text` | **`:247`** | `:184` (in `_parse_meta_object`) |
| B | `git.ref_advance:_committed_meta_object` | — | `:203` `git show` | `:206` | `:184` (same helper) |
| C | `cli.commands.implement_cores:_is_self_write_only_diff` | `:423` | `:427` `read_bytes` | `:427` | `:263` (in `_parse_meta_mapping`) |
| D | `cli.commands.implement_cores:_committed_meta_mapping` | — | `:335` `show_blob` | `:338` | `:263` (same helper) |
| E | `cli.commands.merge_driver:_load_json_object` | — | `:171` `read_text` | `:174` | `:174` |

**`:247` is not a `json.loads` line.** It is `worktree_meta = _parse_meta_object(worktree_text)`, the
delegating call; the `json.loads` is at `:184`. `plan.md` calls `:247` "the parse", true only in the
delegating sense. Site E is invoked **twice** (`:243`, `:244`) — the whole difference between "5 read
expressions" and "6 invocation sites". Declare which convention each of your counts uses.

### `C-003` is insufficient as written — use `module:symbol`

`C-003` says cite by symbol, never by line alone. Not enough here: `_resolve_mission_id` is defined in
**four** modules under exactly that name (`charter/_io.py:358`, `mission_runtime/resolution.py:1058`,
`specify_cli/post_merge/retrospective_terminus.py:143`, `specify_cli/decisions/service.py:112`) — eight
with the `_resolve_mission_id_*` prefix family — and two are this mission's own census sites with
**opposite arms** (row 3 degrade, row 9 refuse-typed). Cite `module:symbol` **and** line throughout.

### The four diagnosable-only sites, and why they are not routed

A corrupt `meta.json` must say so, naming **`meta.json`** *and* the path, instead of a generic
dirty-worktree message or a bare `json.JSONDecodeError`. Two of them **cannot** use the seam at all:
`_parse_meta_text` (`src/specify_cli/mission_metadata.py:331` — the module is `specify_cli`, not
`specify_cli.core`, which `plan.md`/`spec.md` leave ambiguous) takes a `Path` and performs the read itself,
so it accepts neither `git show` stdout (`str`, site B) nor `show_blob` output (`bytes`, site D).

The remaining obstacle at sites **C** and **E** is the **routed budget**, not structure. `C-004`'s original
"structurally cannot use the seam" claim is **refuted and struck** — site C holds
`(repo_root / Path(repo_rel)).resolve()` under a `name == _META_JSON_FILENAME` gate (`:426`) and its parent
*is* a feature dir. **Do not repeat the struck claim.** Separately, `_committed_meta_object` (site B)
conflates absent-at-HEAD with corrupt-at-HEAD via `{}`, but its `returncode != 0` check (`:204`) **already
separates the two internally**, so a fail-closed variant is writable without losing the case.

### Budget — this WP spends the mission's only headroom

Routing site A takes routed **129 → 130**, exactly the top of the admissible band **`[127, 130]`**; every
other WP is **0-net**. The bound is **two-sided**: `test_routed_load_meta_floor` (`:1084`) asserts
`len >= FLOOR`, `len > FLOOR` (explicitly anti-vacuous) and `len - FLOOR <= MARGIN` against
`ROUTED_LOAD_META_FLOOR = 126` / `MARGIN = 4`, so **126 is RED** — a fold that *collapses* calls reds the
gate downward too. Print the count pre and post **this WP's own edits**:

```bash
.venv/bin/python -c "from tests.architectural.test_inline_meta_read_gate import \
scan_routed_load_meta_calls, SRC_ROOT; print(len(scan_routed_load_meta_calls(SRC_ROOT)))"
```

No ledger row moves: `grep -c 'load_meta(' src/specify_cli/git/ref_advance.py` → **0**, and
`scan_load_meta_call_sites` matches the exact name `load_meta` (`_TARGET`), so routing onto
`load_meta_fail_closed` neither adds nor deletes a row.

### `merge_driver.py` runs as a subprocess

`src/specify_cli/lanes/merge.py` registers the driver in a `_MergeDriverSpec` block: `config_key="spec-kitty-meta"`
at **`:82`**, `command="spec-kitty merge-driver-meta %O %A %B"` at **`:84`**, `pattern="kitty-specs/**/meta.json"`
at **`:85`** (all three verified by opening the file — cite the line that carries the fact you are asserting).
WP07's `#2804` marker asserts on the driver's result, so an edit to site E is **invisible until
`pip install -e .`** (the documented stale-install false-red class). Reinstall **before** claiming any
merge-driver result. Its current tolerance — `missing → {}` at **`:169-170`** (`if not path.exists():` /
`return {}`) and `blank → {}` at `:172-173` — is pinned by four tests in
`tests/merge/test_merge_driver_wrappers_2709.py` (`:96`, `:100`, `:106`, `:112`), plus
`test_meta_wrapper_translates_bad_json_to_exit1` (`:141`) for the exit code.

### Discipline

- `tests/architectural/` here is **file-level, not a glob**: this WP owns only the enrolment-registry row
  `tool_artifact_enrolment/registry/_is_self_write_only_diff.md`, keyed on `symbol:`/`literals:` and parsed
  by `test_exemption_registry_ratchet.py`. A `tests/architectural/**` glob unions this lane with WP06's.
- Do **not** glob `tests/specify_cli/cli/commands/**` — `test_row_aware_merge_driver.py` lives there and
  `SC-008` requires it **byte-identical**. Your only new file there is `test_meta_bypass_diagnosability.py`.
- This WP owns **no** routing-ledger rows (the ledger covers `load_meta` sites, not bypass parsers). Leave
  `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` byte-identical.
- **Cone**: `tests/specify_cli/git`, the new bypass test file, `tests/merge` (site E),
  `tests/lanes/test_issue_2993_lane_planning_ancestry.py`. Run-only, never edited:
  `tests/specify_cli/cli/commands/test_implement_cores.py`,
  `tests/regression/test_issue_2795_claim_blocker.py`. **Never** `tests/sync` or `tests/cli` — sibling
  missions may hold those windows (`C-007`).
- Redirect every suite to a file; quote `N passed` **and** the selected count; `-ra`, never `-rf`.
  `ruff check` only — **never `ruff format`**. Ceiling **15**: `ruff check --select C901` per touched file,
  **pre and post** (all three pass clean today).

---

### Subtask T027 — Pre-measurement and verify the routing identity

**Purpose**: anchor the budget at **129** before any edit, and prove the `load_meta_fail_closed(
meta_path.parent)` substitution is exact rather than approximate.

**Steps**

1. Record `git rev-parse HEAD` as this WP's `planning_base_branch` anchor → `$EV/base-sha.txt`.
2. Print the routed count with the command in Context → `$EV/routed-pre.txt`. **It must read `129`.** If it
   does not, stop and report: WP01's manifest anchor no longer holds.
3. Quote all three assertions of `test_routed_load_meta_floor` **verbatim from the source**, plus
   `ROUTED_LOAD_META_FLOOR = 126` (`:221`) and `ROUTED_LOAD_META_FLOOR_MARGIN = 4` (`:220`), into
   `$EV/band.txt`, with the derived band and the note **126 is RED**.
4. **Verify the gate.** Quote `ref_advance.py:315` showing `Path(path).name == _META_FILENAME`, and
   `_META_FILENAME` at `:45`. Then state the identity: `meta_path.parent / "meta.json" == meta_path`.
5. **Verify the encoding.** Quote `read_text(encoding="utf-8")` at `:244` and
   `mission_metadata.load_meta`'s `encoding: str = _UTF8` default (`:285`, `_UTF8` at `:31`). If the
   default were `utf-8-sig` the routing would change BOM behaviour; it is not.
6. Confirm the sole consumer: `grep -rn '_meta_change_is_vcs_lock_only' src/ tests/` → one call site
   (`:315`) plus the definition. Quote it with the input count.
7. `ruff check --select C901` **PRE** on all three owned source files → `$EV/c901-pre.txt`.

**Files**: scratch evidence only; no repository changes made in this subtask.

**Validation**: `$EV/routed-pre.txt` reads `129`; `$EV/band.txt` carries the three verbatim assertions and
"126 is RED"; the gate, the encoding and the single-consumer grep are quoted with input counts; `C901` PRE
recorded per file.

---

### Subtask T028 — File `Q8`, the L1 primitive and the `Q2` residue **before** touching the code

**Purpose**: `C-009` ("file, do not absorb") had **zero** enforcement anywhere, and this is the work
package with the strongest pull to absorb — it edits the duplicated code directly. File first
(`DIR-024`, locality of change).

**Steps**

1. File **`Q8`**: the lock-only comparison exists in **three** copies and `_VCS_LOCK_META_FIELDS` is
   declared **twice** — `git.ref_advance:42` and `cli.commands.implement_cores:50` — with two independent
   comparators, `git.ref_advance:_is_vcs_lock_only_meta_change:210` and
   `cli.commands.implement_cores:_is_vcs_lock_only_meta_diff:241`. Cite both declarations and both
   comparators in the issue body. **Do not unify them in this WP.**
2. File the **L1 pure-decode primitive**: `text|bytes → dict|None`, typed — the missing seam tier without
   which sites **B** and **D** cannot route. Record the three tiers in the body: **L1** missing;
   **L2** `mission_metadata:_parse_meta_text:331` (exists, `Path`-only, needs a public fail-closed entry
   for the temp-blob case at `merge_driver:_load_json_object:167`); **L3**
   `core.paths:load_meta_fail_closed:638` (exists, reachable by 2 of the 5).
3. File the **`Q2` residue**: full routing of the four non-routed bypass sites, deferred on the **routed
   budget**, not on `C-004`'s struck structural claim.
4. Verify each with `gh issue view <n> --json number,title,body` and quote the output (`unset GITHUB_TOKEN`
   first if `gh` fails on scopes). Record all three numbers in `SC-009`'s register (rows **4**, **6**, **8**).
5. Cite `Q8`'s issue number in a **code comment at the surviving comparison** —
   `git.ref_advance:_is_vcs_lock_only_meta_change` (`:210`), the copy this WP's routed site keeps feeding.

**Files**: the tracker; a one-line comment in `src/specify_cli/git/ref_advance.py`; the register rows.

**Validation**: three `gh issue view` outputs quoted with their numbers; register rows 4, 6, 8 filled; the
`Q8` number present as a comment at `:210`; the filings' timestamps **precede** T029–T032's commit SHAs
(`git log --format=%cI` compared against the issue creation times, quoted).

---

### Subtask T029 — **Commit 1**: route site A, and spend the headroom

**Purpose**: replace the read+parse pair in `git.ref_advance:_meta_change_is_vcs_lock_only` with
`load_meta_fail_closed(meta_path.parent)`, which is what gives WP06 its only green landing state.

**Steps**

1. Write the ATDD test first, under `tests/specify_cli/git/`, RED on T027's base SHA: a corrupt
   `meta.json` inside a real worktree fixture must (a) still block the advance and (b) produce a message
   naming **`meta.json`** and the path. Quote the red.
2. Edit **`:243-249`**. Keep the `:242` path binding (`meta_path = worktree / path`) — it supplies
   `meta_path.parent`. Replace the `try`/`read_text`/`except OSError`/parse-call/`None`-arm block with the
   seam call plus **two** arms: `None` (absent) → `return False`, unchanged; `MissionMetaReadError` → emit
   the diagnosable message, then `return False`. **The catch is mandatory** — `MissionMetaReadError` is a
   `RuntimeError` (`core.paths:506`), so routing without it converts "treated as genuine dirt" into an
   uncaught crash in the dirty-worktree scan.
3. **Record the one deliberate behaviour delta and assert it.** Today `except OSError` at `:245` does
   **not** catch `UnicodeDecodeError`, which is a `ValueError` subclass — so a non-UTF-8 `meta.json`
   currently escapes this function uncaught. `_parse_meta_text` lists `UnicodeDecodeError` explicitly
   (`mission_metadata.py:349`, `#3163`), so after routing that input is blocked-and-diagnosed instead of
   crashing. Add a test for the non-UTF-8 byte case and state the delta as an **improvement**, not a
   regression — `NFR-003` binds the four degrade sites, not this one.
4. Print routed **POST** → `$EV/routed-post.txt`: **130**, floor still **126**, band `[127, 130]`. Quote
   the three clauses again against the new count. Do not touch `ROUTED_LOAD_META_FLOOR` — WP06 re-derives
   it (`FR-008`).
5. Confirm no ledger movement: `grep -c 'load_meta(' src/specify_cli/git/ref_advance.py` → **0**, and
   `git diff --stat -- tests/specify_cli/test_meta_fail_closed_full_census_contract.py` → empty. Quote both.
6. Commit; **quote the SHA** and the green test run with `N passed`.

**Files**: `src/specify_cli/git/ref_advance.py`; new test under `tests/specify_cli/git/`.

**Validation**: red quoted on the base SHA, green quoted at the commit; `MissionMetaReadError` caught by
name (not `except Exception`); routed PRE **129** / POST **130** both quoted; ledger diff empty; the
`UnicodeDecodeError` delta asserted and labelled.

---

### Subtask T030 — **Commit 2**: `ref_advance.py`'s remaining diagnosability (site B)

**Purpose**: make corrupt-at-HEAD distinguishable from absent-at-HEAD at
`git.ref_advance:_committed_meta_object`, without breaking a run-only pinned contract.

**Steps**

1. **Read `tests/regression/test_issue_2795_claim_blocker.py` first — it constrains the design.** It
   imports `_parse_meta_object` (`:55`), and `test_parse_meta_object_handles_malformed_and_non_object`
   (`:291-294`) asserts it returns `None` for `"{not json"` and `"[1, 2, 3]"`. That file is **run-only and
   not in `owned_files`**, so `_parse_meta_object` cannot be converted to raise.
2. So put the diagnosability in the **caller**, or give `_parse_meta_object` an **optional** subject argument
   (path or `HEAD:<path>` handle) used only to build the message, with the return contract still
   `dict | None`. State which you chose and why.
3. `_committed_meta_object` (`:192`): keep `returncode != 0` → absent-at-HEAD → `{}` (unchanged), and give
   the `_parse_meta_object(...) is None` branch at `:206-207` its own **corrupt-at-HEAD** message naming
   `meta.json` and `HEAD:<path>`. The two cases are already separated internally; do not collapse them.
4. Do **not** change either function's return type or its `{}`/`None` value set — site A's routing (T029)
   is the only behavioural change in this WP.
5. Add the `SC-012` pair for site B in `tests/specify_cli/git/`: corrupt blob at HEAD → message asserted on
   **text**; valid blob → normal result and **no** such message.
6. Run `tests/regression/test_issue_2795_claim_blocker.py` green and prove it **unedited**:
   `git diff --stat -- tests/regression/` → empty, quoted.
7. Commit; quote the SHA and `N passed`.

**Files**: `src/specify_cli/git/ref_advance.py`; tests under `tests/specify_cli/git/`.

**Validation**: `_parse_meta_object` still returns `None` on both pinned inputs (quote the run); absent-vs-
corrupt arms distinct and both quoted; `tests/regression/` diff empty; site B's corrupt/valid pair quoted.

---

### Subtask T031 — **Commit 3**: `implement_cores.py` (sites C and D) + the registry row

**Purpose**: diagnosability at the two `implement_cores` bypass reads, and an honest registry note at the
exemption row this WP touches.

**Steps**

1. `_parse_meta_mapping` (`:259`, `json.loads` at `:263`) swallows `UnicodeDecodeError` and
   `json.JSONDecodeError` into `None` with no subject. It takes `raw: bytes` and has no path, so — as at
   T030 — the message comes from the callers or from an added optional subject argument. Keep the
   `dict | None` return: `_is_self_write_only_diff:428-429` and `_committed_meta_mapping:336-338` depend on it.
2. Site **C**, `_is_self_write_only_diff` (`:388`): the parse at `:427` sits under the
   `name == _META_JSON_FILENAME` gate (`:426`) with `source` bound at `:423`. On `working is None`
   (`:428-429`) emit the corrupt message naming `meta.json` and `source`, then keep returning `False`.
   **Do not route this site** — the budget is spent (T029). Note in the commit message that its parent
   *is* a feature dir and the obstacle is budget, not structure.
3. Site **D**, `_committed_meta_mapping` (`:330`, `show_blob` at `:335`, parse at `:338`): keep
   `blob is None` → `None` (absent) and give the unparseable-blob path its own message naming `meta.json`
   and the ref-qualified path.
4. Update `tests/architectural/tool_artifact_enrolment/registry/_is_self_write_only_diff.md` — **the row
   file only**. Keep `symbol:` (`_is_self_write_only_diff`) and `literals:` (`_WP_SELF_WRITE_FILENAME_RE`)
   intact, since `test_exemption_registry_ratchet.py` parses them; add prose recording that this mission
   made the meta arm diagnosable and did **not** retire the mechanism, with full routing deferred to T028's
   `Q2` issue. **Do not** change `status:` or `retirement-wp:`.
5. Add sites C and D to `tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py` with their
   valid-file negative controls. Do not touch `test_row_aware_merge_driver.py` (`SC-008`).
6. Run `tests/specify_cli/cli/commands/test_implement_cores.py` green and prove it **unedited**
   (`git diff --stat` → empty, quoted). Commit; quote the SHA, `N passed` and the selected count.

**Files**: `src/specify_cli/cli/commands/implement_cores.py`;
`tests/architectural/tool_artifact_enrolment/registry/_is_self_write_only_diff.md`;
`tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py`.

**Validation**: `_parse_meta_mapping` return contract unchanged; both messages assert on text; registry row
keeps `symbol:`/`literals:` and the ratchet test is green; `test_implement_cores.py` green and unedited;
`test_row_aware_merge_driver.py` byte-identical.

---

### Subtask T032 — **Commit 4**: `merge_driver.py` (site E), reinstall before any evidence

**Purpose**: make the merge-driver's corrupt-meta message name `meta.json` and the path, without breaking
its pinned tolerance — and without reporting a stale-install false red.

**Steps**

1. `pip install -e .` **first**; quote the command and the resolved `spec-kitty merge-driver-meta` entry
   point. Evidence captured before this is invalid — `lanes/merge.py:84` registers the driver as a
   subprocess for `kitty-specs/**/meta.json`.
2. `_load_json_object` (`:167`): keep `missing → {}` (**`:169-170`** — `if not path.exists():` then
   `return {}`; `:168` is the docstring) and `blank → {}` (`:172-173`) exactly — pinned by
   `tests/merge/test_merge_driver_wrappers_2709.py:96` and `:100`. Wrap the `json.loads` at `:174` so a syntax
   error becomes a message naming `meta.json` and `path`, in the same style as the existing non-object message at
   `:175-176` (`f"{path}: meta.json is not a JSON object"`).
3. Prefer raising `EventLogMergeError` over letting the raw `json.JSONDecodeError` escape: the handler in
   `merge_driver:merge_driver_meta` at **`:246-248`** (`except (json.JSONDecodeError, EventLogMergeError) as exc:`
   `:246`, `typer.echo(str(exc), err=True)` `:247`, `raise typer.Exit(1) from exc` `:248` — verified by opening the
   file; an earlier draft said `:245-247`) already catches **both** and echoes `str(exc)` to stderr before
   `Exit(1)`, so exit-code behaviour is unchanged and `test_meta_wrapper_translates_bad_json_to_exit1` (`:141`)
   stays green. Verify, do not assume.
4. **Do not touch `_parse_json_document` (`:322`, `if not path.exists()` `:324`, read `:326`, `json.loads`
   `:330`).** It is a structural
   lookalike whose subject is the row matrix, not `meta.json`; it is **not** a bypass site and editing it
   would inflate the count and cross into WP07's territory.
5. Site E is one read expression invoked **twice** (`:243`, `:244` — the two `_load_json_object(...)` arguments
   to `reconcile_meta_payloads`). Cover **both** invocations in
   `test_meta_bypass_diagnosability.py` (corrupt `ours`, corrupt `theirs`) with valid-file controls, and
   declare the convention next to the count.
6. Run `tests/merge/test_merge_driver_wrappers_2709.py` green — all four tolerance tests plus `:141` —
   redirected, `N passed` and selected count quoted.
7. Commit; quote the SHA.

**Files**: `src/specify_cli/cli/commands/merge_driver.py`;
`tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py`.

**Validation**: reinstall quoted **before** any merge-driver result; `missing`/`blank` → `{}` still pinned
green; exit-1 translation still green; `_parse_json_document` untouched (`git diff` quoted); both
invocations covered.

---

### Subtask T033 — Seam family, `SC-012`/`SC-013` closure, quality gates

**Purpose**: close the criteria and record the adjudication `NFR-002`/`C-004` moved **into this mission**,
so the Charter Check's "Single canonical authority — Partial" row can be resolved.

**Steps**

1. **`SC-012`**: table the **5 read expressions / 6 invocation sites** (convention declared, input count
   printed) with, per row, the corrupt-fixture message quoted (naming `meta.json` **and** the path, asserted
   on **text**, not exception type) and the valid-file control beside it. A type-only row does not count.
2. **`SC-013`**: print the predicate-symbol list **post** and diff it against WP01's pre-list
   (`contracts/headroom-allocation.md`). Post must be **no longer** and contain **no new local predicate**.
   Then run the **mutation probe**: add a second local predicate at one bypass site, show `SC-013` goes
   red, **revert**, and quote all three steps.
3. Record the seam family: **L1** filed not built (T028); **L2** `_parse_meta_text`
   (`mission_metadata.py:331`) — `Path`-only, cannot serve sites B/D; **L3** `load_meta_fail_closed`
   (`core.paths:638`) — reached by site A here, available to site C on budget. Denominator as integers:
   **1 routed / 4 diagnosable-only / 0 allowlisted**.
4. State the two struck claims explicitly so they cannot be re-inherited: `C-004`'s "structurally cannot use
   the seam" (refuted — sites A and C hold real feature-dir paths) and `NFR-002`'s immovable floor (R-1).
5. Run the full cone redirected: `tests/specify_cli/git`, the new bypass test, `tests/merge`,
   `tests/lanes/test_issue_2993_lane_planning_ancestry.py`, plus the two run-only files. Quote `N passed`,
   the selected count and `exit=`. **No `tests/sync`, no `tests/cli`.**
6. `ruff check` + `mypy --strict` over the three changed source files → zero issues, quoted (`SC-017`).
   `ruff check --select C901` **POST** against T027's PRE, per file, ceiling **15** — name
   `_meta_change_is_vcs_lock_only`, `_committed_meta_object` and `_is_self_write_only_diff` explicitly.
7. Append to the three mission tracer files per charter Standing Order 3.

**Files**: evidence in the WP's status/report surface; tracer files. No source changes.

**Validation**: `SC-012` table complete at 5/6 with declared convention, message text and controls;
`SC-013` post-list no longer than pre plus the reverted mutation probe; denominator printed as integers;
cone `N passed` + selected count + `exit=`; `C901` PRE/POST per file; `ruff`/`mypy` clean.

---

## Definition of Done

- [ ] `git.ref_advance:_meta_change_is_vcs_lock_only` calls `load_meta_fail_closed(meta_path.parent)`, the
      `None` arm returns `False`, and `MissionMetaReadError` is **caught by name** (never `except
      Exception`). The identity is **verified**: `:315` gate and `utf-8` default both quoted.
- [ ] Routed count printed **pre 129 / post 130**, floor still **126**, band `[127, 130]` restated with
      **126 is RED**. Not 131 (upward red), not 126 (downward red).
- [ ] Four diagnosable-only sites each produce a message naming **`meta.json`** and the path, asserted on
      **text**, each with a valid-file negative control (`SC-012`, 5 expressions / 6 invocations,
      convention declared, input count printed).
- [ ] `_parse_meta_object` still returns `None` for `"{not json"` and `"[1, 2, 3]"`; `tests/regression/`
      diff **empty**.
- [ ] `merge_driver`'s `missing → {}` and `blank → {}` still green; `pip install -e .` quoted **before**
      any merge-driver evidence; `_parse_json_document` untouched.
- [ ] **`SC-008` byte-identity, proved by path and base ref — not asserted.** Three obligations, each quoted
      with its command *and* its (empty) output:
      - `git diff --stat <planning_base_branch> -- tests/specify_cli/cli/commands/test_row_aware_merge_driver.py`
        prints **nothing**, **and** `ls tests/specify_cli/cli/commands/test_row_aware_merge_driver.py` **succeeds**.
        The `ls` is not ceremony: `git diff --stat` against a path that does **not exist** also prints nothing, so
        the empty diff alone is indistinguishable from a false green. **The real path is
        `tests/specify_cli/cli/commands/test_row_aware_merge_driver.py`** (`find tests -name
        test_row_aware_merge_driver.py` returns exactly that one path); **`tests/merge/test_row_aware_merge_driver.py`
        does not exist** and must never be the path in a quoted command — WP04, WP07 and WP08 all flag the same
        nonexistent variant. Note it lives under `tests/specify_cli`, which is **not** the barred top-level
        `tests/cli`.
      - `git diff --stat <planning_base_branch> -- tests/specify_cli/test_meta_fail_closed_full_census_contract.py`
        prints **nothing** (this WP owns no routing-ledger row), **and** `ls` on that path succeeds.
      - `git diff --stat <planning_base_branch> -- kitty-specs/meta-fail-closed-3162-01KZ7FSQ/contracts/`
        prints **nothing** (WP01's routing manifest is not this WP's surface), **and** `ls` on that directory
        succeeds.
      Use the WP's actual `planning_base_branch` (`feat/meta-fail-closed-3162`) as the base ref in each command
      and quote the ref you used — a bare `git diff --stat` compares against the working tree and proves nothing
      about the base.
- [ ] Registry row updated in place with `symbol:`/`literals:` intact and the ratchet test green;
      `tests/architectural/` touched at **file level** only.
- [ ] `Q8`, the **L1 primitive** and the `Q2` residue filed with `gh issue view` quoted; `SC-009` rows 4, 6
      and 8 recorded; `Q8`'s number cited in a comment at `_is_vcs_lock_only_meta_change` (`:210`); filings
      **precede** the code commits.
- [ ] `SC-013` post-list no longer than WP01's pre-list, mutation probe run and reverted.
- [ ] The struck claims are named as struck (`C-004`'s structural claim; `NFR-002`'s immovable floor).
- [ ] `ruff check` + `mypy --strict` clean (`SC-017`); `C901` pre/post per file, ceiling 15; **no `ruff
      format`**.
- [ ] Cone was `tests/specify_cli/git`, the new bypass test, `tests/merge`, the lane-ancestry test and the
      two run-only files — **no `tests/sync`, no `tests/cli`**. Every citation is `module:symbol` **and**
      line (`C-003`, tightened — see Context).

**Subtask marking** — run per subtask as it completes. This records **status only**: `mark-status` exposes
`--status`, `--mission`, `--auto-commit`, `--json` and its payload is a bare `{T0xx: Status}`
(`src/specify_cli/status/models.py:481`). It is **not** an evidence channel — everything above lives in the
committed `kitty-specs/meta-fail-closed-3162-01KZ7FSQ/evidence/WP05-evidence.md`.

```bash
spec-kitty agent tasks mark-status <Txxx> --status done --mission meta-fail-closed-3162-01KZ7FSQ
```

## Risks

1. **"Just improve the message" at site A.** The most likely failure. It leaves `json.loads` inside
   `_parse_meta_object` reachable from a `read_text`-fed delegating call, so WP06's widened scanner still
   flags it, live inline goes 7 → 8, and the only escapes are a re-freeze the charter forbids or a weakening
   `FR-007` forbids. **WP06 becomes unlandable.**
2. **Routing site A without catching `MissionMetaReadError`.** It is a `RuntimeError`; uncaught it turns
   "corrupt meta is genuine dirt" into a crash inside the dirty-worktree scan.
3. **Converting `_parse_meta_object` to raise.** Breaks
   `tests/regression/test_issue_2795_claim_blocker.py:291-294`, a run-only file this WP may not edit.
4. **Spending more than one routed call.** A second routing anywhere lands **131** (upward red); a fold that
   collapses calls lands **126** (downward red). The bound is two-sided.
5. **Stale-install false red at site E.** Reinstall first, or you debug a subprocess running the old code.
6. **Absorbing `Q8`.** The duplicated comparators are under your hands in T029–T031. File, do not unify
   (`C-009`, `DIR-024`), and timestamp the filing **before** the code commits.
7. **Editing `_parse_json_document`** (`merge_driver:322`) because it looks identical. It is the row-matrix
   reader, not a `meta.json` bypass site; touching it inflates the count and crosses into WP07's lane.
8. **Globbing `tests/architectural/**` or `tests/specify_cli/cli/commands/**`.** The first unions this lane
   with WP06; the second puts `SC-008`'s byte-identical file inside your ownership.
9. **Citing by line alone.** Five commits move lines in these three files, and `_resolve_mission_id` alone
   is defined in four modules — two of them this mission's own sites with opposite arms.

## Reviewer Guidance

Check these in order; the first four are where this WP fails if it fails.

1. **Site A is routed, not merely re-messaged.** Read
   `git.ref_advance:_meta_change_is_vcs_lock_only`: it must call `load_meta_fail_closed(meta_path.parent)`,
   catch `MissionMetaReadError` **by name**, and keep the `None` arm returning `False`. A diagnosable-only
   edit here is a rejection, not a style note — it leaves WP06 with no green state.
2. **The identity was verified.** Both the `:315` gate quote and the `utf-8` default quote must be present.
3. **Budget: pre 129, post 130.** Not 131, not 126. `ROUTED_LOAD_META_FLOOR` must still read **126** —
   WP06 re-derives it, not this WP.
4. **`SC-012` is 5/6 rows of quoted message text with valid-file controls**, convention declared and input
   count printed. Type-only assertions and messages that omit either `meta.json` or the path do not count.
5. **`_parse_meta_object`'s `None` contract survives** and `tests/regression/` is unedited. Run
   `test_parse_meta_object_handles_malformed_and_non_object` yourself.
6. **The reinstall precedes the merge-driver evidence** in the transcript order, and the four `2709`
   tolerance tests plus the exit-1 test are green.
7. **Filings precede code.** Compare issue creation times against `git log --format=%cI`. `Q8`'s number
   must appear as a comment at `_is_vcs_lock_only_meta_change` (`:210`).
8. **The struck claims are named as struck.** If the evidence repeats "structurally cannot use the seam",
   reject — `C-004`'s factual basis was corrected; sites A and C hold real feature-dir paths.

### Things in the upstream planning artifacts to be aware of

- **`plan.md` and `research/3162-census.md` cite different lines for the same sites** — `plan.md` the reads
  (`:203`, `:335`), the census the parse calls (`:206`, `:338`); neither says which. `plan.md` also calls
  `:247` "the parse (`json.loads`)": `:247` is the delegating call, the `json.loads` is at `:184`. The
  census's `ref_advance.py:245→247` is off by one — the `read_text` is at `:244`. Re-derive.
- **`plan.md`/`spec.md` cite `mission_metadata.py:331-349` without a package.** The module is
  `src/specify_cli/mission_metadata.py`, **not** `src/specify_cli/core/mission_metadata.py` (nonexistent).
  Same for "path built at `:421-427`": the binding is one line, `:423`; gate `:426`; read `:427`.
- **A behaviour delta at site A that no artifact records**: `except OSError` (`:245`) does not catch
  `UnicodeDecodeError` (a `ValueError` subclass), so a non-UTF-8 `meta.json` escapes
  `_meta_change_is_vcs_lock_only` uncaught **today**. Routing fixes it (`_parse_meta_text` lists it
  explicitly, `#3163`). Recorded in T029 as an improvement; `NFR-003` does not bind this site.
- **`analysis-report.md` predates the IC renumbering** and attributes some of this concern's surfaces
  (the registry row, the `Q8` row) to `IC-04`. `plan.md`'s numbering is authoritative: this is `IC-05`.

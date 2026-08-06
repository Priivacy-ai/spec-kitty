---
work_package_id: WP06
title: Widen the gate, re-derive both floors, and give the control a positive twin
dependencies:
- WP05
requirement_refs:
- FR-006
- FR-007
- FR-008
- NFR-002
- NFR-004
- C-005
- C-008
planning_base_branch: feat/meta-fail-closed-3162
merge_target_branch: feat/meta-fail-closed-3162
branch_strategy: Planning artifacts for this mission were generated on feat/meta-fail-closed-3162. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/meta-fail-closed-3162 unless the human explicitly redirects the landing branch.
subtasks:
- T034
- T035
- T036
- T037
- T038
- T039
- T040
history: []
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/_fixtures/unreachability_control.py
- tests/architectural/_fixtures/unreachability_control_twin.py
execution_mode: code_change
owned_files:
- tests/architectural/test_inline_meta_read_gate.py
- tests/architectural/inline_meta_read_allowlist.yaml
- tests/architectural/_baselines.yaml
- tests/architectural/_gate_coverage_baseline.json
- tests/architectural/_golden_count_baseline.json
- tests/architectural/_fixtures/unreachability_control.py
- tests/architectural/_fixtures/unreachability_control_twin.py
role: implementer
tags: []
tracker_refs: []
---

# WP06 — Widen the gate, re-derive both floors, and give the control a positive twin

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work
package's `task_type` and `authoritative_surface`.

---

## Objective

Widen the inline-meta-read scanner by the **one shape it can reach** — a `json.loads` whose argument resolves,
**one hop**, into a private same-module single-parameter parse helper fed by a `read_text`/`open`/`read_bytes`
— and **re-derive both floors in the same change**. Give `SC-005`'s unreachability control a **positive twin**
so its `sites: 0` means something. Write **no** allowlist entry; leave `inline_meta_read_baseline` at **7**.
Then, as the mission's terminal owner of `tests/architectural/`, **own the two CI ratchet baselines five WPs
move** (T040 — see § The ratchet baselines).

## Where this WP runs, how to start it, and where its evidence lands

**This WP runs from the repository root.** Start with `spec-kitty implement WP06` — `spec-kitty agent action
implement WP06 --agent <name>` does **not** resolve a workspace, its `--help` reads *"Display work package
prompt with implementation instructions."*, and `CLAUDE.md` § Execution Workspace Strategy is explicit that
*"`spec-kitty implement WP##` is the only supported way to prepare a workspace."*

**`PYTHONPATH=<workspace>/src` on every `python -c` and every `pytest` that could run outside the repository
root** — T039 already requires it for the `96494e5ec` worktree, and it is **load-bearing for this WP more than
any other**. `SRC_ROOT` (`tests/architectural/test_inline_meta_read_gate.py:61`,
`SRC_ROOT = _REPO_ROOT / "src"`) is derived from **the gate file's own location**, while
`.venv/lib/python3.11/site-packages/_editable_impl_spec_kitty_cli.pth` pins `specify_cli` / `runtime` imports to
the **main** tree's `src/`. So a scanner run in a worktree walks that worktree's `src/` while anything it
imports comes from the main tree — the exact split that makes "the widening found a real site" and "a different
tree was measured" indistinguishable. The same applies to `_SRC_ROOT` in the ledger test
(`tests/specify_cli/test_meta_fail_closed_full_census_contract.py:54`). Every count in this WP must name the
tree it walked **and** the `PYTHONPATH` it ran under. Nothing provisions `.venv` into a git worktree
(`.gitignore:31-32`).

**Committed evidence destination.** `mark-status` exposes only `--status`, `--mission`, `--auto-commit`,
`--json`; its payload is `WPInnerStateDelta.subtasks: Mapping[str, Status]`
(`src/specify_cli/status/models.py:481`) — a bare `{T0xx: Status}`, **no evidence field**. This WP's committed
destination is `kitty-specs/meta-fail-closed-3162-01KZ7FSQ/evidence/WP06-evidence.md`, a declared **out-of-map**
planning write with a one-line rationale (`kitty-specs/` paths cannot appear in `owned_files` by construction —
`mission_parsing.py:153-157`, `:207-215`). The two `sites:` numbers, the floor derivation arithmetic, the
provenance `git show` output, the two labelled deltas, the elapsed seconds, the orphan/golden-count results and
the `gh issue view` outputs all go **into that file**; nothing load-bearing is left in `/tmp`.

## Context

The gate lives at `tests/architectural/test_inline_meta_read_gate.py`; the predicate is `scan_inline_meta_reads`
(`:589`) → `_scan_file_for_inline_meta_reads` (`:604`) → `_read_source_base` (`:519`) → `_extract_read_base`
(`:507`) → `is_meta_path_expr` (`:549`), with `SRC_ROOT` `:61` and `_MAX_ASSIGNMENT_HOPS` `:471`.

### Gate condition — WP05 must have **ROUTED** `ref_advance.py:247`, not merely made it diagnosable

`dependencies: ["WP05"]` is necessary but not sufficient — **verify the routing before you widen anything.**
The target is the call `_parse_meta_object(worktree_text)` at `src/specify_cli/git/ref_advance.py:247` inside
`_meta_change_is_vcs_lock_only` (`:231`), fed by `meta_path.read_text(...)` (`:244`) and
`meta_path = worktree / path` (`:242`); the helper is `_parse_meta_object` (`:180-189`). Diagnosability changes
neither the `json.loads` at `:183` nor the call at `:247`, so on a merely-diagnosable site the widened scanner
still flags it: live inline goes **7 → 8** against a **shrink-only ceiling of 7**, and **there is no green
configuration**. Every escape closed:

| State | Result |
|---|---|
| widen, site not routed | RED `test_inline_meta_read_floor` (`count <= 7`, `:1061`) + RED `test_inline_meta_read_gate_green_against_seeded_allowlist` (`:1109`) |
| widen, `FLOOR → 8`, allowlist 7 | RED `test_allowlist_matches_floor` (`:1116`) — an **equality** |
| widen, `FLOOR → 8`, allowlist 8, baseline 7 | RED `test_allowlist_shrink_only` (`:1125`) |
| widen, `FLOOR → 8`, allowlist 8, baseline 8 | green, but this is the **re-freeze the charter forbids** |
| **widen, site ROUTED (live back to 7)** | **green** |

**If T034 finds `:247` unrouted, stop and escalate.** Do not widen, do not raise a floor, do not add an
allowlist entry — no state of this work package is both landed and charter-compliant.

### Atomicity — coupling 1: the scanner, the floor and the allowlist are mutually locking

`plan.md`'s coupling 1. Three assertions lock jointly: `test_inline_meta_read_floor` (`:1061`,
`count <= FLOOR`), `test_allowlist_matches_floor` (`:1116`,
`len(load_allowlist(ALLOWLIST_PATH)) == INLINE_META_READ_FLOOR` — an **equality**) and
`test_inline_meta_read_gate_green_against_seeded_allowlist` (`:1109`, `violations == []`). **Any one moving
alone reds another, so the widening, the floors and the allowlist state land in ONE commit** (T037). Say this
out loud in your evidence: **earlier planning named the wrong pair here** — `test_allowlist_shrink_only` +
`test_allowlist_entries_are_still_live` — and the real bidirectional coupling is the **equality** at `:1116`,
which no mission artifact mentioned before the post-plan pass.

### `FR-007` — the allowlist route is **unconditionally** closed

`test_allowlist_entries_are_still_live` (`:1166`) compares each entry against `_live_inline_meta_read_keys` —
every entry must match a live **detected** site, so an entry for a scanner-invisible shape is **stale on arrival
and red at any baseline**. Bumping `inline_meta_read_baseline` opens nothing; it only invites the follow-on move
of weakening the staleness guard, and **that is the one thing this work package must not do.** The baseline stays
**7**; the allowlist keeps exactly its **7** entries.

### `FR-006` — state the predicate, and get the guard right

The scanner accepts a call **iff**: **(1)** it is `json.loads`/`json.load`, import-binding resolved, with ≥1
arg; **(2)** `_read_source_base(args[0], fn)` resolves the argument — through same-function assignment /
`with`-binding hops — to a `read_text`/`open` call (**`read_bytes` added here**); **(3)**
`is_meta_path_expr(base, fn)` holds (a canonical meta-path name, a `<dir> / "meta.json"` join, or a `Name`
resolved through ≤ `_MAX_ASSIGNMENT_HOPS` reassignments to such a join). The widening adds the **one-hop
private same-module single-parameter parse helper** at **clause 2's** boundary.

Measured: **19 candidates → 17 rejected at clause 2 → 1 rejected at clause 3 → 1 accepted**
(`ref_advance.py:247`), **0** false positives over `src/`. The earlier "31 candidates, 30 rejected at clause
3" reproduces under **no** definition (eight variants swept) and is **refuted**. **Clause 2 is the
load-bearing guard** holding false positives at zero; **clause 3 rejects exactly one candidate**. The earlier
attribution to clause 3 was inverted and it licensed the wrong future move — widening clause 2 later would
unlock ~17 candidates with **no** measured clause-3 protection. `C-005` survives on the number and failed on
the reasoning. The `read_bytes` addition to `_extract_read_base` (`:507`) yields **0** new sites over `src/`,
so it is marked **"no red possible — synthetic pin required"**: a `tmp_path` fixture pair generated at
runtime, measured **1 → 2**, with **no third fixture file committed for it** (T036).

### `SC-005` / `NFR-004` — the control needs a positive twin, and must not live under `src/`

A bare `sites: 0` is a **vacuous negative** — a broken scanner also prints 0, which is what
`architectural-gate-non-vacuity` forbids. Two fixtures under `tests/architectural/_fixtures/` (the leading
underscore keeps pytest from collecting them), scanned by **explicit argument**: the unreachability control
(`sites: 0`) and its twin with the read **inlined** and the path named `meta_path` (`sites: 1`). **Neither
may go under `src/`** — `scan_inline_meta_reads` walks `SRC_ROOT`, so a fully-inlined read placed there
would raise the live census and **red the very floor the control exists to prove**. `NFR-004`'s denominator,
as integers: **1 reached and routed / 4 deferred with a control / 0 allowlisted**.

### `FR-008` / `NFR-002` — re-derive both floors, and **print** the value

**Inline**: the re-derivation **confirms 7** — WP05's routing returns live inline to 7, so
`INLINE_META_READ_FLOOR` (`:127`) stays 7 and `FLOOR_MARGIN` (`:134`, currently **2**) is re-derived against
the same live count. **Routed**: the floor **moves** — WP05's routing takes live routed **129 → 130**, exactly
the **ceiling** of the admissible band **`[127, 130]`**, so `ROUTED_LOAD_META_FLOOR` (`:221`) is re-derived to
restore the established 3-below-live gap (precedent: `117 → 126` on 2026-08-04, for exactly this reason).

**Do NOT copy a value from planning.** `plan.md`'s `[UNVERIFIED]` item 1 offers **`127`** and **`[128,131]`**,
both derived from the ruling's stated rule rather than measured on this tree. This change must **print** the
measured live count and derive the floor from it. **The band is two-sided**:
`test_routed_load_meta_floor` (`:1084`) asserts **three** things — `len >= FLOOR`, `len > FLOOR` (strict,
explicitly anti-vacuous in its own docstring) and `len - FLOOR <= MARGIN` (margin **4**, `:220`). The strict
middle assertion is why **126 is RED** and why the bound binds downward as well as upward.

#### The floor criterion is **provenance**, and the committed value is **not 126**

An earlier draft of this prompt demanded *"an anti-copy grep quoted proving `127` and `[128,131]` were **not**
pasted"* over the gate file. **That criterion inverts and is struck.** The derivation rule it tells you to apply
— 3-below-live, at live **130** — *produces* **127**. So doing the work correctly makes the bullet unsatisfiable,
and skipping the work makes it pass. It was written against a copied *number* when what was missing was that
number's *provenance*.

Two criteria replace it:

1. **Provenance — the diff must show both values.** Quote:
   ```bash
   git show <sha> -- tests/architectural/test_inline_meta_read_gate.py | grep '^[-+]ROUTED_LOAD_META_FLOOR'
   ```
   It must print **both** the removed old line and the added new line — e.g. a `-ROUTED_LOAD_META_FLOOR = 126`
   and a `+ROUTED_LOAD_META_FLOOR = <measured>`. Quote the output verbatim. This cannot invert: it is satisfied
   only by a constant that actually moved, whatever value it moved to, and it is unsatisfiable by pasting
   anything.
2. **The committed value is not 126.** Assert it explicitly and quote the committed line.

**Why criterion 2 has to be stated separately.** At the post-WP05 live count of **130** with
`ROUTED_LOAD_META_FLOOR = 126` and `MARGIN = 4`, all three clauses pass untouched: `130 >= 126`, `130 > 126`,
`130 - 126 = 4 <= 4`. **The gate is green with the floor left at 126.** Nothing else in this WP forces the move
— not the widening, not the allowlist, not the fixtures — so without an explicit "not 126" criterion the honest
way to satisfy `FR-008`'s routed half and the lazy way of skipping it are indistinguishable from the outside.

Keep an anti-copy grep **only where it is scoped to `contracts/`**, which is where WP01's Definition of Done
already has it correctly: WP01 must not pre-empt the measurement by writing `127` or `[128,131]` into its
manifest. Over this WP's own gate file, the grep is the inverting one — do not run it as a criterion here.

**`SC-006` — report two deltas, separately.** The **widening delta** (predicate change at a fixed tree) and the
**code delta** (source change at a fixed predicate) are two numbers: the ratchet cannot itself tell "the
widening found a real site" from "a new unrouted read landed", so **one number hides both**. `SC-006`'s "or
made diagnosable → live returns to 7" branch is **struck as false**.

### The ratchet baselines — this WP owns them, because otherwise nobody does

Two CI ratchet baselines live in this WP's `authoritative_surface` and **five WPs create new test files that can
move them**. Before the post-tasks pass, `grep` for either file across the whole mission directory returned
**nothing** and no `owned_files` entry matched either one, so the owning WP was **nobody** — WP08's sweep would
surface the red and its own Risk 10 would hand the repair back to "the owning WP". They are now in this WP's
`owned_files`, which unions no lane: this surface is already `tests/architectural/`, this WP already owns
`_baselines.yaml`, it is sequential with WP05, and it is file-disjoint from lane B.

Quote each file's **own warning text** in T040 and check it, rather than assuming:

- `tests/architectural/_gate_coverage_baseline.json` — *"Gate-coverage ratchet baseline (Issue #2034 / #1933).
  Frozen set of test FILES that contain >=1 test selected by zero CI gates — the visible #1931 worklist.
  **The ratchet (`test_gate_coverage.py`) fails on any NEW orphan file not listed here.** Regenerate with:
  `uv run python -m tests.architectural._gate_coverage --update-baseline`"*, with `"orphan_files": []`.
- `tests/architectural/_golden_count_baseline.json` — *"Per-directory ceiling on non-escaped
  `convert`-classified golden-count sites (FR-014/#2076). Regenerate via
  `python -m tests.architectural.test_golden_count_ban --freeze-baseline` after a batch conversion lands; never
  hand-edit except to record a documented decrease. **A directory absent here has an implicit ceiling of 0 — any
  convert-classified site appearing there fails the guard immediately.**"* Its `ceilings` map **omits**
  `tests/regression`, `tests/missions`, `tests/context`, `tests/mission_runtime`, `tests/upgrade` and
  `tests/merge` (verified on this tree) — and this mission adds test files under `tests/missions`,
  `tests/context`, `tests/mission_runtime` and `tests/upgrade`.

**The red is inferred, not observed.** No gate was run when the ownership gap was found. If gate selection is
directory-globbed such that a new file in an already-selected directory is never an orphan, the gate-coverage
half is a non-issue — but that is a question you **answer by running the gates**, which is why T040 requires the
runs and forbids assuming either outcome. The **ownership** gap is real either way: a baseline nobody owns is a
baseline nobody repairs.

### `_baselines.yaml` — an open operator question, not a silent pick

`grep -c "inline_meta" tests/architectural/_baselines.yaml` returns **0** today, so this allowlist sits
**off** the charter's Burn-down-Policy §(a) register even though that policy says *every* mutable
architectural allowlist is governed by a baseline there. Either **register it** or **file the deviation** —
and **which of the two the policy wants is an open operator question** (`plan.md` `[UNVERIFIED]` item 6),
so **this work package must not silently pick**. Put it to the operator with `test_allowlist_matches_floor`
and `test_allowlist_shrink_only` offered as the compensating control.

### Three things this change makes true that nobody has priced

1. **`test_gate_runs_under_fast_tier_budget`** (`:1229`) imposes a **30 s** ceiling over *both* scans. The
   widening adds a module-wide pass; **re-measure and print the elapsed time**, do not assume headroom.
2. **Allowlist keys are `(file, qualname, token)`** (`InlineMetaReadKey`, token from `code_tokens_by_line`,
   never hand-typed), so the widening must **ADD a pass** rather than re-derive tokens for the existing 7.
   Measured stable — the anchor only moves for **unbound-parameter** arguments, none of the 7 has one — but
   state it as a **constraint**: `matches_floor` + `entries_are_still_live` turn token drift into a red widening.
3. **The gate's own header becomes false.** `test_inline_meta_read_gate.py:103` says the gate "does no
   call-graph resolution, so a full transitive walk would be a larger structural change than this landing fold
   warrants." This commit adds a one-hop intra-module resolution. **Amend the comment there** — the one hop,
   its bound, and that a full transitive walk stays out of scope.

### Budget and discipline

**0-net** on the routed count for this WP's own edits — WP05 spends the mission's single call, and this WP edits
no file under `src/`, so the delta is structurally 0; **print routed pre/post anyway** (`SC-011`). This WP owns
**no routing-ledger rows**: leave `tests/specify_cli/test_meta_fail_closed_full_census_contract.py`
**byte-identical**. `owned_files` here are **file-level, deliberately** — WP05 owns the enrolment registry row in
the same directory (`.../tool_artifact_enrolment/registry/_is_self_write_only_diff.md`), and a `**` glob would
union the two lanes for nothing. **Cone**: `tests/architectural`; **never** `tests/sync` or `tests/cli`
(`C-007`). Redirect suite output to a file and quote **`N passed`**; print the **selected count**; use **`-ra`**,
not `-rf`; count `^ERROR tests/`, not `^ERROR `. **`ruff check` only — never `ruff format`.** Complexity ceiling
**15** (`C901`). Cite every site by **`file:line` and symbol** (`C-003`).

### Subtask T034 — Gate condition and PRE measurements

**Purpose**: prove the one precondition that makes a green landing possible, and establish the two live
counts every later subtask compares against.

**Steps**

1. **Gate condition first.** Confirm WP05 **routed** `ref_advance.py:247`: quote the current source of
   `_meta_change_is_vcs_lock_only` (`:231`) showing `load_meta_fail_closed(...)` in place of
   `_parse_meta_object(worktree_text)`. A diagnostic added around an unchanged `_parse_meta_object` call is
   **not** routing. **If it is unrouted, STOP here and escalate** — cite the escape table as the reason.
2. Print the live **inline** count PRE with its command and **input file count**; expect **7**. Use **WP01's
   recorded measurement command verbatim** (`contracts/headroom-allocation.md`) — a second way to count is a
   second predicate answering one question (`NFR-002`).
3. Print the live **routed** count PRE with its input file count. Expect **130** (WP05 spent the mission's
   one call, `129 → 130`) — the **ceiling** of the current band `[127, 130]`, which is why
   `ROUTED_LOAD_META_FLOOR` must move in T038. Print the band derivation from the **three** assertions of
   `test_routed_load_meta_floor` (`:1084-1105`) with `ROUTED_LOAD_META_FLOOR = 126` (`:221`) and its margin
   **4** (`:220`): admissible `[127, 130]`, **126 is RED**, the bound **two-sided**.
4. Record the current constants — `INLINE_META_READ_FLOOR = 7` (`:127`), `FLOOR_MARGIN = 2` (`:134`),
   `inline_meta_read_baseline: 7`, **7** allowlist entries — plus
   `grep -c "inline_meta" tests/architectural/_baselines.yaml` → expect **0** (T040's input), the **7 live
   allowlist keys** (`file`, `qualname`, `token`) as T037's token-stability baseline, and
   `ruff check --select C901` PRE for the gate file (ceiling **15**).

**Files**: read-only. No repository changes in this subtask.  
**Validation**: routing at `:247` quoted from source; inline PRE **7** and routed PRE **130** both printed
with input counts; band printed with **126 is RED**; five constants recorded; `grep -c` → 0 quoted; 7 keys
captured; `C901` PRE quoted.

### Subtask T035 — The two control fixtures: `sites: 0` and its positive twin `sites: 1`

**Purpose**: close `SC-005`/`NFR-004` with a negative that is **falsifiable**, because a bare `sites: 0`
is indistinguishable from a broken scanner.

**Steps**

1. Write `tests/architectural/_fixtures/unreachability_control.py` — a scratch module reproducing one of the
   **4 deferred** scanner-invisible bypass read expressions with the read **fully inlined** (the
   post-widening repeat of research control `C3`). Expected: **`sites: 0`**.
2. Write `tests/architectural/_fixtures/unreachability_control_twin.py` — the **same** module with the read
   inlined **and the path named `meta_path`**, so clause 3 holds. Expected: **`sites: 1`**.
3. **Neither goes under `src/`.** `scan_inline_meta_reads` walks `SRC_ROOT`; a fully-inlined read committed there
   raises the live census and reds `test_inline_meta_read_floor` — the floor the control exists to prove. State
   this in each fixture's module docstring so a future editor cannot "tidy" them into `src/`.
4. Add the assertions to `test_inline_meta_read_gate.py`, scanning **by explicit argument**, in the shape
   `test_new_inline_meta_read_is_flagged` (`:1136`) already uses. **Trap**: a bare
   `len(scan_inline_meta_reads(_FIXTURES_DIR))` folds in the pre-existing `_fixtures/bad_adapter.py` and
   `_fixtures/org_packs/**`, making both numbers meaningless — either copy the fixture into a `tmp_path` scratch
   root and scan that, or filter by the fixture's own `rel_path`. **Print `sites: N` per fixture.**
5. Both fixtures are committed repository files, so they must be **`ruff check` clean** — an unused `json` import
   reds this WP's own quality gate. Confirm the leading-underscore directory keeps pytest from collecting them
   (`--collect-only` over `tests/architectural`, quoted), and that no other architectural gate scans `tests/`
   for this shape. Both land in the **same commit as the widening** (T037) — the twin's `sites: 1` is red before
   the widening and green after, which is `NFR-004`'s only achievable red.

**Files**: both `_fixtures/unreachability_control*.py`; `tests/architectural/test_inline_meta_read_gate.py`.  
**Validation**: both fixtures under `tests/architectural/_fixtures/`, **neither under `src/`**; one run prints
`sites: 0` **and** `sites: 1`; scan by explicit argument, scoped so `bad_adapter.py`/`org_packs` cannot
contribute; `ruff check` clean on both; `--collect-only` shows neither collected.

### Subtask T036 — The `read_bytes` synthetic pin: no red possible, so pin it 1 → 2

**Purpose**: `FR-006`'s `read_bytes` half adds **0** sites over `src/`, so no live census moves and no floor
can go red. It is a documented **"no red possible — synthetic pin required"** exception (charter `C-011`
red-first discipline; `C-008`).

**Steps**

1. Add `read_bytes` to `_extract_read_base` (`:507`) alongside `read_text`/`open` in the `ast.Attribute` arm;
   keep the `open(X, ...)` `ast.Name` arm unchanged. Add `test_read_source_base_direct_read_bytes` beside the
   existing `test_read_source_base_direct_read_text` (`:789`) and `..._direct_open_call` (`:800`) — a
   unit-level pin on the resolver itself.
2. Add the **scan-level synthetic pin**: a **`tmp_path` fixture pair generated at runtime**, one module whose
   read is `read_text`-fed and one whose read is `read_bytes`-fed, scanned by explicit argument. Measured
   control: **before = 1, after = 2**. Assert the **2**, put the measured `1 → 2` in the test docstring, and
   **print** the pair's counts in the run output, not only inside an assertion.
3. **Do not commit a third fixture file** for this — the pin lives inside `test_inline_meta_read_gate.py`
   beside T035's two committed fixtures, generated at runtime.
4. State in the docstring **why** there is no live red: a live-tree red cannot be manufactured without adding
   an unrouted read to `src/`, which reds `test_inline_meta_read_floor` — so manufacturing one would be a
   `C-008` violation dressed as compliance.

**Files**: `tests/architectural/test_inline_meta_read_gate.py`.  
**Validation**: `read_bytes` in `_extract_read_base`, quoted; `test_read_source_base_direct_read_bytes` exists
and passes; synthetic pair prints `1 → 2`; **no third file** under `_fixtures/` (`git status --short` quoted);
the "no red possible" exception stated in the docstring, not in a commit message only.

### Subtask T037 — ONE COMMIT: the widening + both floors + the allowlist state + both fixtures

**Purpose**: land coupling 1 atomically. The three mutually locking assertions must be green **in the same
commit** as the predicate change.

**Steps**

1. **The anchor move** in `_scan_file_for_inline_meta_reads` / `_read_source_base`: when `args[0]` resolves
   to an **unbound parameter** of a **private (`_`-prefixed), same-module, single-parameter** function, take
   **one hop** to that function's call sites in the same module and resolve the passed argument through
   clause 2. Bound the hop explicitly and reject anything else. The reported site is the **call site**
   (`ref_advance.py:247`, `_meta_change_is_vcs_lock_only`), not the helper's `json.loads` line.
2. **Amend the header comment at `:103`**, which currently says the gate "does no call-graph resolution".
   That becomes false here. State the one hop, its bound, and that a full transitive walk stays out of scope.
3. **Same commit** — the constants: `INLINE_META_READ_FLOOR` (`:127`) re-derived and **confirmed 7**;
   `FLOOR_MARGIN` (`:134`) re-derived against the same live count; `ROUTED_LOAD_META_FLOOR` (`:221`) and
   `ROUTED_LOAD_META_FLOOR_MARGIN` (`:220`) per T038's **measured** value. Also in it: both T035 fixtures and
   their assertions, plus T036's `read_bytes` change and pins.
4. **Same commit** — `inline_meta_read_allowlist.yaml` **declared unchanged**: **7** entries,
   `inline_meta_read_baseline: 7`. **No entry is written for any scanner-invisible shape** (`FR-007`) —
   `test_allowlist_entries_are_still_live` (`:1166`) would make it stale on arrival at **any** baseline.
5. **Token stability check.** Re-derive the 7 live keys and diff against T034's capture — **identical**, because
   the anchor only moves for unbound-parameter arguments and none of the 7 has one. If any token drifted,
   `matches_floor` and `entries_are_still_live` red the widening; **freshen from the tool's own report, never
   by hand**, and say so in the evidence. Then run the three locking assertions plus `test_allowlist_shrink_only`
   (`:1125`) and `test_allowlist_entries_are_still_live` (`:1166`) green **on this commit**; quote the SHA.
6. In the evidence: state that **earlier planning named the wrong coupling** here
   (`test_allowlist_shrink_only` + `test_allowlist_entries_are_still_live`) and the real bidirectional lock is
   the **equality** at `:1116`; and attribute the **0** false positives to **clause 2** (17 of 19 rejections),
   **not** clause 3 (exactly 1).

**Files**: `tests/architectural/test_inline_meta_read_gate.py`; `inline_meta_read_allowlist.yaml` (declared
unchanged — verify with `git diff`); both `_fixtures/` modules.  
**Validation**: **one** SHA carrying scanner + both floors + fixtures, `git show --stat <sha>` quoted; `:103`
amended and quoted; allowlist `git diff` **empty** and baseline still 7; 7 keys byte-identical to T034's
capture; five named tests green with `N passed` and the selected count; clause-2 attribution stated.

### Subtask T038 — Re-derive `ROUTED_LOAD_META_FLOOR` from the measurement, and print it

**Purpose**: `FR-008`'s routed half. Live routed is **130**, the ceiling of `[127, 130]`, so the floor must
move or the gate is stale the moment WP05 lands.

**Steps**

1. Print the **measured** live routed count and derive the floor **from it** — restore the established
   3-below-live gap. Show the arithmetic in the run output: live, gap rule, resulting floor, resulting band
   from `[FLOOR+1, FLOOR+MARGIN]`.
2. **Do NOT copy `plan.md`'s `[UNVERIFIED]` item 1** (**`127`**, **`[128,131]`** — derived from the ruling's
   rule, not measured here). If your measurement agrees, say **"measured, and it coincides with the unverified
   figure"** — never cite the plan as the source.
3. Re-assert **all three** clauses of `test_routed_load_meta_floor` (`:1084`) at the new floor: `>= FLOOR`,
   the **strict** `> FLOOR` (anti-vacuous), and `- FLOOR <= MARGIN`. Print each clause's evaluated operands,
   and restate that the strict middle assertion is what makes the bound **two-sided** — a *fold* that
   collapses two calls into one reds the gate from below.
4. Print routed **pre and post** this WP's own edits — **both 130**, delta **0**. This WP edits no `src/`
   file, so a non-zero delta means something outside this WP's scope moved and must be investigated, not
   absorbed. Same fact answers `SC-013` / `NFR-002`'s kept clause: the predicate population is untouched, so
   no new local predicate can have been authored — argue it, do not re-enumerate.
5. **Provenance, not an anti-copy grep.** Quote
   `git show <sha> -- tests/architectural/test_inline_meta_read_gate.py | grep '^[-+]ROUTED_LOAD_META_FLOOR'`
   and show that it prints **both** the removed old value and the added new value. Then assert explicitly that
   **the committed value is not 126** and quote the committed line. Do **not** run an anti-copy grep for `127`
   / `[128,131]` over the gate file as a criterion — at live 130 with `FLOOR=126, MARGIN=4` all three clauses
   pass untouched, so nothing else forces the floor to move, and the 3-below-live rule you are told to apply
   *produces* 127: the anti-copy form is satisfied by skipping the work and unsatisfiable by doing it. The
   anti-copy grep belongs only to WP01, scoped to `contracts/`.

**Files**: the gate file's floor block, landed in T037's commit. **Validation**: measured live routed printed; floor derived **from** it with the arithmetic shown; three
clauses printed with operands; routed pre/post both **130**, delta **0**; the **provenance** `git show | grep
'^[-+]ROUTED_LOAD_META_FLOOR'` output quoted showing **both** values, and the committed value asserted **not
126**; `SC-013` neutrality argued from "no `src/` edit".

### Subtask T039 — `SC-006`: two trees, two deltas, and the re-measured budget

**Purpose**: separate "the widening found a real site" from "a new unrouted read landed", and re-price the
fast-tier cost of the extra pass.

**Steps**

1. Run the **widened** scanner **twice**: against `src/` at the measurement baseline `96494e5ec` (via
   `git worktree add`, `PYTHONPATH=<worktree>/src`) **and** at branch head, printing **both** counts with
   input file counts. This is the runnable equivalent of `SC-008`'s unrunnable "passes on current `main`".
2. Report **two numbers, separately and labelled** — **widening delta** (unwidened vs widened predicate at a
   **fixed** tree) and **code delta** (unwidened predicate at baseline vs at head, the source change alone).
   One number hides both. Any raised inline floor would require the **code delta printed as 0** and the raise
   argued in the PR body — here the floor is **not** raised, so say so.
3. Confirm live inline returns to **7** because WP05 routed `:247`. Restate that `SC-006`'s "or made diagnosable
   → live returns to 7" branch is **struck as false**, measured (`ref_advance.py DIAGNOSABLE → widened: FLAGGED
   :247`).
4. **Re-measure `test_gate_runs_under_fast_tier_budget`** (`:1229`) — the **30 s** ceiling now covers a
   module-wide pass that did not exist before. **Print the elapsed seconds** for both scans, not just "passed".
   If the margin is thin, say how thin; do not raise the ceiling.
5. Run the whole cone: `pytest tests/architectural -ra`, output redirected. Quote **`N passed`** and the
   **selected count**; count `^ERROR tests/` (not `^ERROR `) and quote the number. **No `tests/sync`, no
   `tests/cli`** in any selection. Then `ruff check` and `mypy --strict` over the changed files → zero issues,
   quoted (`SC-017`), plus `C901` PRE/POST for the gate file, ceiling **15** — the anchor hop must not push
   `_read_source_base` or `_scan_file_for_inline_meta_reads` past it; extract a helper if it would.

**Files**: none (scratch worktree outside the repo tree). **Validation**: both tree counts printed with input counts; **two** labelled deltas; live inline **7**;
elapsed seconds for both scans printed against the 30 s ceiling; cone `N passed` + selected count +
`^ERROR tests/` count; `ruff`/`mypy` clean; `C901` PRE/POST quoted.

### Subtask T040 — SECOND COMMIT: the governance surface, the two ratchet baselines, and the question put to the operator

**Purpose**: close `SC-009` rows **3** and **7** without silently deciding a governance question this WP
does not own, and discharge this WP's ownership of the two CI ratchet baselines (§ The ratchet baselines).

**Steps — part A: the two ratchet baselines (run the gates; do not assume either outcome)**

A1. **Enumerate every directory this mission adds a test file to**, from the eight WPs' `owned_files` and
    subtask Files lines — not from memory. Print the list with its input count. At authoring time that set is
    `tests/next`, `tests/runtime`, `tests/missions`, `tests/context`, `tests/mission_runtime`, `tests/upgrade`,
    `tests/specify_cli/bulk_edit`, `tests/specify_cli/context`, `tests/specify_cli/decisions`,
    `tests/specify_cli/git`, `tests/specify_cli/cli/commands`, `tests/architectural/_fixtures` — **re-derive it
    on the merged-so-far tree** and say which WP contributes each.
A2. **Orphan check.** `tests/architectural/_gate_coverage_baseline.json` says in its own `_comment`:
    *"**The ratchet (`test_gate_coverage.py`) fails on any NEW orphan file not listed here.** Regenerate with:
    `uv run python -m tests.architectural._gate_coverage --update-baseline`"*, and it currently carries
    `"orphan_files": []`. **Run `pytest tests/architectural/test_gate_coverage.py -ra`, redirected**, and quote
    the `N passed`/`N failed` line and any named orphan. If it is red: regenerate with the documented command
    (never hand-edit), quote the resulting `git diff` on the baseline, and re-run green. If it is green, say so
    and say **why** — e.g. gate selection is directory-globbed, so a new file in an already-selected directory is
    never an orphan. **Either answer is acceptable evidence; assuming either is not.** The red for this half was
    *inferred* when the ownership gap was found, never observed.
A3. **Golden-count check.** `tests/architectural/_golden_count_baseline.json` says in its own `$schema-note`:
    *"Per-directory ceiling on non-escaped `convert`-classified golden-count sites (FR-014/#2076). Regenerate via
    `python -m tests.architectural.test_golden_count_ban --freeze-baseline` after a batch conversion lands; never
    hand-edit except to record a documented decrease. **A directory absent here has an implicit ceiling of 0 —
    any convert-classified site appearing there fails the guard immediately.**"* Verified: its `ceilings` map
    **omits** `tests/regression`, `tests/missions`, `tests/context`, `tests/mission_runtime`, `tests/upgrade` and
    `tests/merge` — four of which this mission adds files to. **Run
    `pytest tests/architectural/test_golden_count_ban.py -ra`, redirected**, quote the pass line, and check the
    result against **every** directory from A1. If red: regenerate with the documented `--freeze-baseline`
    command, quote the `git diff`, and re-run green — a *decrease* must be documented per the file's own policy.
    If green, state the reason (e.g. none of this mission's new tests are `convert`-classified).
A4. **Say which of the two baselines you actually changed and which you did not**, with `git diff --stat` on both
    files quoted — an empty diff shown as empty. Both are in this WP's `owned_files` precisely so that "nothing
    needed changing" is a **recorded** finding rather than an unexamined one.
A5. If either gate is red for a reason this WP cannot repair inside its own surface, **name the owning WP and
    file it** rather than editing another WP's test file. Record the row in `SC-009`.

**Steps — part B: `_baselines.yaml` and the deferral filings**

1. `tests/architectural/_baselines.yaml`: **either** register `inline_meta` **or** file the register deviation
   — and **put the choice to the operator**, because `plan.md` `[UNVERIFIED]` item 6 records which remedy the
   charter's Burn-down Policy §(a) wants as an **open governance call**. Silence is not an option, and neither
   is picking quietly. Offer the compensating control explicitly in the filing:
   `test_allowlist_matches_floor` (`:1116`, the equality) and `test_allowlist_shrink_only` (`:1125`) already
   enforce shrink-only behaviour, which is what §(a)'s baseline would buy.
2. Quote `grep -c "inline_meta" tests/architectural/_baselines.yaml` **before** (0, from T034) and **after**
   your chosen action, so the change of state is visible either way. If registering: add the entry **with a
   `# justification:` comment on the changed line** per the file's own per-PR edit policy, and run
   `tests/architectural/test_ratchet_baselines.py` green. If deviating: do **not** touch the file, and record
   the issue number.
3. File `FR-007`'s **deferral issue** for the **4** scanner-invisible bypass read expressions, stating that
   **no allowlist entry is possible** (stale on arrival at any baseline) and citing the committed control +
   twin as the evidence. Verify with `gh issue view <n> --json number,title,body` and quote it.
4. Record `SC-009` register rows **3** (`FR-007`/`NFR-004` deferral) and **7** (`inline_meta` absent from
   `_baselines.yaml`) with their issue numbers, and restate `NFR-004`'s denominator as integers:
   **1 reached and routed / 4 deferred with a control / 0 allowlisted**.
5. Commit this **second** commit separately from T037's. Quote both SHAs and confirm
   `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` is **byte-identical** across both
   (`git diff --stat <base> -- <that file>` → nothing). Append to the three mission tracer files
   (tooling-friction, approach, design-decisions) per charter Standing Order 3.

**Files**: `tests/architectural/_baselines.yaml` (only if registering); `_gate_coverage_baseline.json` and/or
`_golden_count_baseline.json` (only if a gate is red and the documented regeneration command changes them); no
other repository changes.  
**Validation**: the A1 directory list printed with its input count and per-WP attribution;
`test_gate_coverage.py` and `test_golden_count_ban.py` each **run and quoted** (pass line from a redirected run),
with any regeneration done by the documented command and its `git diff` quoted; `git diff --stat` quoted for
**both** baseline files, empty shown as empty; the "red was inferred, not observed" caveat resolved either way in
writing; operator question **stated**, not silently resolved; `grep -c` quoted before **and** after;
`test_ratchet_baselines.py` green if registered; `gh issue view` quoted for the deferral (and for the
deviation, if filed); `SC-009` rows 3 and 7 recorded with numbers; two SHAs quoted; ledger file byte-identical;
tracer files appended.

## Definition of Done

- [ ] **Gate condition proven**: `ref_advance.py:247` is **routed** (source quoted), not merely diagnosable.
- [ ] The widening is **one hop, private, same-module, single-parameter**, bounded in code and quoted; the
      header comment at `:103` no longer claims "no call-graph resolution"; `read_bytes` in
      `_extract_read_base` (`:507`) with the unit pin **and** the runtime `tmp_path` pair printing **1 → 2**,
      and **no third committed fixture** (`git status --short` quoted).
- [ ] **ONE commit** carries the scanner change, `INLINE_META_READ_FLOOR`, `FLOOR_MARGIN`,
      `ROUTED_LOAD_META_FLOOR`, its margin, and both control fixtures — coupling 1. `git show --stat` quoted.
- [ ] Inline live **7 → 7**; floor **7**; allowlist **7** entries; baseline **7**; allowlist `git diff` **empty**;
      the **7** keys byte-identical pre/post (token-stability diff quoted). **No allowlist entry** for any
      scanner-invisible shape; `test_allowlist_entries_are_still_live` green **and unedited**, with the
      **unconditional** closure stated in the evidence.
- [ ] `ROUTED_LOAD_META_FLOOR` **re-derived from the measured live count** with the arithmetic printed; all three
      clauses of `test_routed_load_meta_floor` printed with operands at the new floor. **Provenance quoted**:
      `git show <sha> -- tests/architectural/test_inline_meta_read_gate.py | grep '^[-+]ROUTED_LOAD_META_FLOOR'`
      prints **both** the old and the new value. **And the committed value is explicitly asserted not to be
      126** — at live 130 with `FLOOR=126, MARGIN=4` all three clauses pass untouched, so nothing else in this WP
      forces the move. The inverting anti-copy grep over the gate file is **struck**; the anti-copy grep survives
      only in WP01, scoped to `contracts/`.
- [ ] Both control fixtures print **`sites: 0`** and **`sites: 1`** in the **same** run, scanned by explicit
      argument, scoped so `_fixtures/bad_adapter.py` and `org_packs/**` cannot contribute; **neither fixture
      under `src/`**; both `ruff check` clean and neither collected by pytest.
- [ ] `SC-006`: both tree counts printed; **widening delta** and **code delta** as **two labelled numbers**.
      `test_gate_runs_under_fast_tier_budget` **re-measured**, elapsed seconds printed against the 30 s ceiling.
      Routed count printed pre and post, **both 130**, delta **0**; band restated with **126 is RED** and the
      bound described as **two-sided**.
- [ ] Clause-2 attribution stated (17 of 19 rejections); clause 3 rejects **exactly one**; the refuted
      "31/30-at-clause-3" figure named as refuted; `NFR-004`'s denominator stated as **1 / 4 / 0**.
- [ ] `_baselines.yaml`: registered **or** deviation filed, **and the choice put to the operator** as an open
      question; `grep -c` quoted before and after; `SC-009` rows **3** and **7** recorded with `gh issue view`.
- [ ] **The two CI ratchet baselines are discharged, by running the gates rather than assuming them.**
      `test_gate_coverage.py` and `test_golden_count_ban.py` each run and quoted; the check covers **every**
      directory this mission adds a test file to, enumerated with its input count; each baseline's own warning
      text quoted (`_gate_coverage_baseline.json`: *"fails on any NEW orphan file not listed here"*;
      `_golden_count_baseline.json`: *"A directory absent here has an implicit ceiling of 0 — any
      convert-classified site appearing there fails the guard immediately"*, with `tests/regression`,
      `tests/missions`, `tests/context`, `tests/mission_runtime`, `tests/upgrade`, `tests/merge` named as absent);
      any regeneration done with the file's own documented command, never by hand; `git diff --stat` quoted for
      both files with empty shown as empty. **"No change needed" is a recorded finding, not a skipped step.**
- [ ] Cone was `tests/architectural` only — **no `tests/sync`, no `tests/cli`**; `N passed`, selected count and
      `^ERROR tests/` count quoted; `-ra` used. `ruff check` + `mypy --strict` clean (`SC-017`); `C901`
      PRE/POST for the gate file, ceiling **15**.
- [ ] `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` **byte-identical**; no routing-ledger
      row touched. Every citation carries **`file:line` and symbol** (`C-003`).

**Subtask marking** — run per subtask as it completes. This records **status only**: `mark-status` exposes
`--status`, `--mission`, `--auto-commit`, `--json` and its payload is a bare `{T0xx: Status}`
(`src/specify_cli/status/models.py:481`). It is **not** an evidence channel — everything above lives in the
committed `kitty-specs/meta-fail-closed-3162-01KZ7FSQ/evidence/WP06-evidence.md`.

```bash
spec-kitty agent tasks mark-status <Txxx> --status done --mission meta-fail-closed-3162-01KZ7FSQ
```

## Risks

1. **Widening against an unrouted `:247`.** There is **no green configuration** — every escape in the table is
   closed, and the only "green" one (baseline → 8) is the **re-freeze the charter forbids**. T034 catches this.
2. **Bumping `inline_meta_read_baseline`.** It opens nothing, it stays red, and it leads directly to the
   forbidden move: weakening the staleness guard.
3. **Splitting coupling 1.** The scanner, the floors and the allowlist state lock through the **equality** at
   `:1116`; any one landing alone reds another. One commit.
4. **Believing clause 3 is the guard.** Clause 2 rejects **17** of 19; clause 3 rejects **one**. The inversion
   matters more than the arithmetic: a future widening of clause 2 would unlock ~17 candidates with **no
   measured clause-3 protection**. Put the corrected attribution in the code comment, not only in the report.
5. **A fixture under `src/`** — a fully-inlined read committed there raises the live census and reds
   `test_inline_meta_read_floor`, destroying the floor the control exists to prove.
6. **A vacuous control**, or one scanned too widely. `sites: 0` alone is what `architectural-gate-non-vacuity`
   forbids, so the twin must appear in the **same** run output; and `_fixtures/` already holds `bad_adapter.py` +
   `org_packs/**`, so a bare directory scan makes both `sites:` numbers meaningless.
7. **Copying `127` / `[128,131]` from the plan.** They are `[UNVERIFIED]` by the plan's own label; a pasted floor
   is a stale floor the moment live moves. **Token drift on the existing 7** is the mirror risk: measured stable,
   but `matches_floor` + `entries_are_still_live` turn any drift into a red widening, so never hand-type a token.
8. **Unpriced fast-tier cost** (the extra module-wide pass shares a **30 s** ceiling with the routed scan —
   measure it, do not raise the ceiling), and **silently picking the `_baselines.yaml` remedy** (an operator
   call; deciding it quietly in a test-directory commit is the failure mode this note exists to prevent).

## Reviewer Guidance

Check these in order; the first four are where this WP fails if it fails.

1. **Is `ref_advance.py:247` routed?** Read the source, not the WP's claim. If `_parse_meta_object(worktree_text)`
   is still there, the widening had no green landing state and every green run downstream is suspect — it means a
   floor or a baseline was moved.
2. **Is coupling 1 one commit?** `git show --stat`: scanner change, `INLINE_META_READ_FLOOR`, `FLOOR_MARGIN`,
   `ROUTED_LOAD_META_FLOOR` and **both** fixtures together. Then confirm the evidence says out loud that the
   real lock is the **equality** at `:1116` and that earlier planning named the wrong pair. Silence on that is
   a rejection, not a style note.
3. **Was the routed floor measured, and did it actually move?** Two checks, both mandatory. (a) Demand the
   printed live count and the derivation arithmetic. (b) Run the provenance grep yourself:
   `git show <sha> -- tests/architectural/test_inline_meta_read_gate.py | grep '^[-+]ROUTED_LOAD_META_FLOOR'`
   must show **both** an old and a new value, and **the committed value must not be 126**. A committed 126 is a
   rejection even though the gate is green: at live 130 with margin 4 all three clauses pass untouched, so a green
   gate is not evidence the floor was re-derived. Do **not** reject on an anti-copy grep for `127` over the gate
   file — the derivation rule produces 127, so that check inverts; it applies only to WP01's `contracts/`.
4. **Do both fixtures print in the same run — `sites: 0` and `sites: 1`?** And is the scan scoped so
   `bad_adapter.py` / `org_packs` cannot contribute? A `sites: 0` without its twin is the vacuous negative.
5. **Allowlist untouched.** `git diff` on `inline_meta_read_allowlist.yaml` must be **empty**: 7 entries,
   baseline 7, no new entry — and `test_allowlist_entries_are_still_live` must be unedited.
6. **Two deltas, not one**, separately labelled — one number is not `SC-006`. And `:103`'s header comment must
   be amended; it claimed no call-graph resolution, which this commit made false.
7. **Budget re-measured, with seconds printed.** "Passed" is not a measurement of a 30 s ceiling that just
   gained a pass.
8. **The operator question is open.** The `_baselines.yaml` remedy must be **put** to the operator with the two
   enforcing tests offered as compensating control. A quietly-registered baseline, or a quietly-skipped one, both
   fail this check.
9. **Scope hygiene.** Cone is `tests/architectural` only; the routing ledger is byte-identical; routed pre/post
   both **130**; no file under `src/` was touched.
10. **The ratchet baselines were checked by running the gates.** Find the quoted `test_gate_coverage.py` and
    `test_golden_count_ban.py` runs and the enumerated directory list. A claim that neither baseline needed
    changing is acceptable **only** with both runs quoted — the red was inferred, never observed, so an
    unexamined "green" and an unrun gate look identical in a summary. Also confirm any regeneration used the
    file's documented command rather than a hand edit.

### Three things in the upstream planning artifacts to be aware of

- **The wrong atomicity pair survives in the narrative.** `plan.md`'s IC-06 "Commit slices" bullet and coupling 1
  both name the equality at `:1116`; the *older* framing (`test_allowlist_shrink_only` +
  `test_allowlist_entries_are_still_live`) survives in the analysis report's account of what the previous plan got
  wrong. Read coupling 1 as authoritative and record the correction.
- **`plan.md` cites `FLOOR_MARGIN` at `:134` without its value.** It is **2** on this tree, and the constant's own
  comment says the gap is **0** at `FLOOR == live == 7`. Re-derive it against the measured count in T037 rather
  than assuming that comment survives the widening.
- **`C-011` is a *charter* constraint ID (ATDD-First Discipline), not one of this spec's own.** This spec's
  constraint table runs `C-001` … `C-009` — no local `C-010` or `C-011` — and the Standing rules table qualifies
  foreign `FR-008`/`FR-004`/`FR-007`/`C-002`/`NFR-003` but **not** `C-011`, so the nine "documented `C-011`
  exception" citations read as pointers to a missing local constraint. When you invoke the no-red-possible
  exception (T036, T038), cite it as **charter `C-011`** paired with this spec's own `C-008`.

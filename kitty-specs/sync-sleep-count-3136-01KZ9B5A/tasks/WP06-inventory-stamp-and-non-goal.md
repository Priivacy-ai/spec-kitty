---
work_package_id: WP06
title: The inventory verdict stamp (body-only) and the recorded CPU-contention non-goal
dependencies:
- WP01
requirement_refs:
- FR-008
- FR-009
- C-005
- C-007
planning_base_branch: feat/sync-sleep-count-3136
merge_target_branch: feat/sync-sleep-count-3136
branch_strategy: Planning artifacts for this mission were generated on feat/sync-sleep-count-3136. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/sync-sleep-count-3136 unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
history: []
agent_profile: curator-carla
authoritative_surface: docs/development/process-global-inventory-3115.md
create_intent: []
execution_mode: code_change
owned_files:
- docs/development/process-global-inventory-3115.md
- kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/non-goals-3136.md
role: curator
tags: []
tracker_refs: []
---

# Work Package Prompt: WP06 – The inventory verdict stamp (body-only) and the recorded CPU-contention non-goal

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the profile — `agent_profile: curator-carla`, `role: curator`,
`agent: claude`. Do not start with the file edit.

```
/ad-hoc-profile-load curator-carla
```

**Fallback if the skill does not resolve the profile**: `spec-kitty profiles list`, then
`spec-kitty profiles show curator-carla`. If the CLI is also unavailable, read the profile source at
`packs/built-in/agent_profiles/curator-carla.agent.yaml` (verified present) and adopt it verbatim.
Do not proceed as a generic agent: this WP's entire product is two records a successor will trust
without re-deriving, which is a curation judgement, not an implementation one.

Start command:

```bash
spec-kitty implement WP06
```

---

## Objective

Land two records, both of which are about work that will **not** be done. That is precisely why each
has to be precise enough that a successor does not redo it.

1. **Stamp the `#3115` inventory's verdict column as falsified**, scoped to that column only, in
   `docs/development/process-global-inventory-3115.md` — **body only, no frontmatter field touched**.
2. **Record the CPU-contention reproduction as a deliberate non-goal with all three of its reasons**,
   plus the post-spec squad's sharper framing of the defect, in
   `kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/non-goals-3136.md` (the `<guard-rationale>`).

Requirements: `FR-008`, `FR-009`, `C-005`, `C-007`. Delivery criterion: `SC-010` (four commands).
`SC-011` is a spec self-check, not a criterion — do not treat it as an acceptance arm.

---

## Context

### Why the verdict column is falsified, not merely unverified

`docs/development/process-global-inventory-3115.md` carries **53** `E`-numbered rows, ids `E1`–`E53`,
contiguous (verified by extracting and sorting them). Measured pre-edit state:

```bash
grep -cE '^\| E[0-9]+ \|' docs/development/process-global-inventory-3115.md   # → 53
grep -c '3136' docs/development/process-global-inventory-3115.md              # → 0
grep -c 'unverified' docs/development/process-global-inventory-3115.md        # → 0
```

Every row's last field is the **Dependence** verdict — `depends` / `does not depend` /
`undetermined`. The page's own `## Legend — the four mandatory values` (`:213`) calls it item **4**,
and `## Method` item 4 (`:227-231`) defines it as *"whether `test_429_respects_retry_after`'s outcome
depends on the entry"*. So the verdicts are verdicts **about one node**.

At the time they were derived, that node had never exhibited the failure. **It now does.** `spec.md`
`:49` records `TestRetryBehaviors::test_429_respects_retry_after` as a victim on PR #3209's
`fast-tests-sync` (head SHA `5e98c2bb7`, pinned — the branch moved twice during this mission), and
`spec.md:50` records three census nodes failing simultaneously in job `92278529393` on pristine
`main` at `98198e980`. The column is therefore **falsified**, not merely unverified — a stamp reading
only "unverified" understates it (`plan.md` IC-07 risk (a)).

### The inventory is live input to a running guard, not documentation

`tests/sync/_leak_guard.py` traces its watch list to the inventory by row-id: `_WatchedGlobal` carries
an `inventory_id` field (`:47`) that the guard reads at runtime — `entry.inventory_id == label`
(`:458`), `_UNEVALUATABLE_WATCHED_ENTRIES[entry.inventory_id]` (`:576`), the fingerprint map keyed by
it (`:680`), the drift report (`:724`).

Structurally: `_WATCHED_SINGLETONS` (`:58-61`) → `E26`, `E27`; `_WATCHED_FIXTURE_DATA` (`:84-99`) →
`E28`–`E41`; `_WATCHED_ENV_KEYS` (`:108`) → the composite label `"E51/E52"` (one watch, two rows);
`_UNWATCHED_ENTRIES` (`:114-140`) → `E15, E16` / `E17, E18, E19` / `E20, E21, E22` / `E42-E50`, each
with a stated reason, reported every session; `E53` in the CWD drift message (`:735`).
`_WATCHED_CARRY_FORWARD` (`:71-80`) carries the id `carry-forward:LEVEL_RESOLVERS` and is deliberately
**not** an inventory row (its own comment says so) — do not "fix" it into one.

**29 distinct row-ids in the guard, all of them currently resolvable** — verified:
```bash
ids=$(grep -ohE '\bE([1-9]|[1-4][0-9]|5[0-3])\b' tests/sync/_leak_guard.py | sort -u -V)
echo "$ids" | wc -l    # → 29
for id in $ids; do
  n=$(grep -cE "^\| $id \|" docs/development/process-global-inventory-3115.md)
  [ "$n" -eq 1 ] || echo "UNRESOLVED $id -> $n"
done                   # → no output
```

The stamp must not disturb a row-id or the `| E<n> | … |` row shape those resolutions depend on.
This check is a pure grep over two files — it does **not** run `tests/sync`, which `C-001` forbids.

### The two verdict-column traps

1. **The Dependence column is the *last* field, not a fixed pipe index.** Nine tables carry `E`-rows:
   six are five-column (`| # | Module : symbol | Reset seam | Caller | Dependence |`, e.g. `:234`),
   three are three-column (`| # | Module : symbol | Dependence |`, `:356`, `:379`, `:410`). A
   mechanical edit keyed on "column 5" corrupts the three-column tables.
2. **The verdicts are not uniform.** 52 rows read `does not depend`; exactly **one** reads `depends` —
   `E22` (`tests/sync/tracker/conftest.py::_patch_saas_token_bridges`, autouse, `:55-174`), and its
   own text warns that *"WP06 inherits only limb 1 if this row is read carelessly; both limbs are
   load-bearing"* (that is `#3115`'s WP06, not this one — name the collision in the stamp so nobody
   conflates them).

### Re-derive only the load-bearing rows — and derive that set, do not assume it

The operator ruling is: stamp the column, and re-derive **only** what this mission's fix actually
depends on. If that set is empty, say so and cite **0** row numbers rather than implying coverage.
`SC-010` sub-3 requires zero row-id tokens in `plan.md` and in the `<guard-rationale>`; sub-4 is its
**positive twin** — the identical pattern against the inventory itself must return **53**, because a
grep that matches nothing satisfies a "0 hits" negative silently.

**Do not open T034 having already concluded "empty".** Two rows are live candidates and must be
adjudicated on the tree, not by assumption:

- **`E15`** (`:296`) states that `src/specify_cli/tracker/saas_client.py`'s *"entire module-level
  assignment surface is **exactly two names**"* (`_SESSION_EXPIRED_MESSAGE` `:36`,
  `_UNAUTHENTICATED_CATEGORY` `:39`). WP02's alias seam adds **three** module-level assignments
  (`_sleep`, `_monotonic`, `_randbelow`) to that exact module, so the row's stated measurement goes
  stale the moment WP02 lands. Whether that makes it *depended on by the fix* is T034's question.
- **`E22`** — the only `depends` row; it `monkeypatch.setattr`s attributes on the `saas_client` module
  object (`tests/sync/tracker/conftest.py:106-108`, `:172`), the same surface the alias seam extends,
  and it governs whether the census nodes' `client` fixture can construct at all.

Both branches are legitimate outcomes. What is not legitimate is picking one without the commands.

### The cross-lane hazard: body-only is a constraint, not a coincidence

WP04 regenerates `docs/development/3-2-page-inventory.yaml` from **every** docs page's frontmatter.
The inventory page has an entry there (`…3-2-page-inventory.yaml:1793-1797`: `tag: current`,
`divio_type: reference`, both derived from this page's frontmatter `type: reference`).

**WP06 must be body-only. Touch no frontmatter field** — not `updated`, not `doc_status`, not
`related`. The page's frontmatter is `:1-10`; every edit belongs at `:11` or later. **Escalation
path**: if a stamp turns out to need a frontmatter field, WP06 **gains a dependency on WP04** and
loses its parallelism with lanes A and B — stop, record the reason, and escalate. Do not silently
edit frontmatter and do not silently regenerate the lockfile.

### `C-010` — the terminology guard, and a second docs-scoped guard

Touching docs prose triggers guards that run only in CI's `integration-tests-core-misc` job, so a
regression passes every local doctrine run and surfaces late.
- `tests/architectural/test_no_legacy_terminology.py` — `C-010`'s named guard. **⚠ Budget ~75–90 s,
  NOT "~0.1 s".** Measured on this tree: `10 passed in 75.19s`. `CLAUDE.md`'s
  *"Pre-push: run the terminology guard"* paragraph is the source of the `≈0.1 s` figure and it is
  wrong by ~690×; `WP04:185` already carries this correction (`⚠ CORRECTION 4`) and WP06 inherits it
  here. **Do not edit `CLAUDE.md`** — it is not owned by this WP; record the divergence and move on.
  An implementer who expects 0.1 s watches a healthy gate for 70 s and starts debugging it. Scan roots are
  `("src", "tests", "docs")` (`:71`); `kitty-specs/` is excluded (`:78`), so the inventory page **is**
  in scope and this WP prompt is not. Its `_FORBIDDEN_TERMS` (`:30-33`) are built from fragments and
  are **two** legacy terms — a compliance-event noun and a hyphenated status-mutation phrase. Read
  `:30-33` before writing prose; do not guess them from this description.
- `tests/architectural/test_glossary_canonical_terms.py` — not named by `C-010`, but it scans
  `:(glob)docs/**/*.md` (`:47`) for non-canonical casing of multi-word glossary surfaces and carries
  the same `docs_scoped` marker (`:44`). The inventory page is in its scope too. Run it as well.

Use the canonical vocabulary — `Mission`, not `feature`. Note honestly that the `Mission`/`feature`
distinction is **glossary policy** (and `CLAUDE.md` overstates it as enforced by the legacy denylist);
the two-term denylist does not enforce it, and the casing guard is what adjudicates `docs/` surfaces.

### ENVIRONMENT — read this before running anything

**NEVER run a bare `uv run`.** It re-solves against the tracked `.python-version` (`3.11.15`,
verified), **destroys `.venv`**, and drops `pytest` / `ruff` / `mypy`. This has happened **three
times in this mission**. Recorded proof: `uv sync --dry-run --python 3.12` → `Would uninstall 70
packages`.

**`~/.local/bin/*` resolve to an unrelated checkout.** Measured: `command -v pytest` →
`/home/…/.local/bin/pytest` (shebang `/usr/bin/python`, not this `.venv`); `command -v ruff` →
`/home/…/.local/bin/ruff`. The correct binaries are `./.venv/bin/python` (3.12.13),
`./.venv/bin/pytest` (9.0.3), `./.venv/bin/ruff` (0.15.12). Prepend `./.venv/bin` to `PATH`, and
**quote** `command -v` output when recording it — an unquoted path is not evidence of what ran.

```bash
./.venv/bin/python -m pytest ...   ./.venv/bin/ruff check .   # correct forms
uv run --python 3.12 --extra test --extra lint <cmd>   # only ever with both flags
uv sync --python 3.12 --extra test --extra lint        # recovery if .venv is destroyed
```

### Discipline for this WP

- **Do NOT run `tests/sync` or `tests/cli`** (`C-001`). Every check here is a grep, a docs-scoped
  architectural test, or `ruff check` — and **`ruff check` only, never `ruff format`** (`C-002` greps
  the WP notes for that string).
- **Every claim carries the command that produced it, and prints its input count** (the 53 rows, the
  29 guard ids). A verdict with no input count is not evidence.
- **A cited `file:line` is not evidence that the line says what the citation claims — open every one.**
  This mission has already had docstring prose become a load-bearing constraint twice, and a fixture
  claimed to reach a site it structurally cannot.
- Expect a **non-fatal** warning: `code_change WP does not own any files under src/ or tests/`. It is
  deliberate. `planning_artifact` would sweep this WP into `lane-planning` and destroy its parallelism
  with lanes A and B. Record the warning; do not "fix" the `execution_mode`.

---

### Subtask T033 — Measure the inventory and its consumers before touching anything

**Purpose**: establish the input counts every later claim rests on, and capture the pre-edit state so
the stamp's effect is a diff, not an assertion.

**Steps**

1. Count the rows and prove the id set is `E1`–`E53` contiguous:
   ```bash
   grep -cE '^\| E[0-9]+ \|' docs/development/process-global-inventory-3115.md
   grep -oE '^\| E[0-9]+ \|' docs/development/process-global-inventory-3115.md \
     | grep -oE 'E[0-9]+' | sort -V | tr '\n' ' '
   ```
2. Record the pre-edit negatives (`grep -c '3136' …` and `grep -c 'unverified' …`, both **0** today)
   and the verdict distribution (52 `does not depend`, 1 `depends` — `E22`), each with its command.
3. Enumerate the nine `E`-row tables and their column counts, so the stamp's placement is chosen
   against the real structure and not against the five-column shape alone.
4. Run the guard-id resolution loop from `## Context`; record `29` and the empty failure output.
5. Open — actually open — `tests/sync/_leak_guard.py:44-140`, the `Legend` at `:213-231`, and the
   `Method` §4 definition. Confirm each says what this prompt claims. Report any divergence rather
   than proceeding on the prompt's word.

**Files**: reads only — `docs/development/process-global-inventory-3115.md`,
`tests/sync/_leak_guard.py`.

**Validation**: `53`, `29`, `0`, `0` recorded verbatim with their commands; the id list printed and
visibly contiguous.

---

### Subtask T034 — Derive the load-bearing row set (and decide the SC-010 branch)

**Purpose**: answer "which inventory rows does *this mission's fix* actually depend on?" with a
falsifiable derivation, because `SC-010` sub-3 inverts depending on the answer.

**Steps**

1. Enumerate what the fix touches, from `plan.md`'s `## Project Structure`: the alias seam in
   `src/specify_cli/tracker/saas_client.py`, the 24 patch-target retargets in
   `tests/sync/tracker/test_saas_client.py` and `…/test_saas_client_origin.py`, and the new guard
   module. Print the list.
2. For each of the 53 rows, ask the single question that matters: **does the correctness of this
   mission's fix rest on that row's verdict being true?** Not "is the row about a file the fix
   touches" — dependence, not adjacency.
3. Adjudicate the two named candidates explicitly, with evidence, in writing:
   - **`E15`** — the fix adds three module-level assignments to the module whose row asserts the
     surface is "exactly two names". Does the *fix's correctness* depend on that assertion, or does
     the fix merely make the row's measurement stale? Record which, and why.
   - **`E22`** — the only `depends` row, monkeypatching the `saas_client` module object that the
     alias seam extends. Read both limbs (`tests/sync/tracker/conftest.py:106-108` and `:155-172`)
     before ruling.
4. **Branch A — the set is empty.** State it with the reasoning and cite **0** row numbers; `SC-010`
   sub-3's negative then applies as written. **Branch B — non-empty.** `SC-010` sub-3 inverts: the
   **inventory doc** names each row, each carrying a re-derivation verdict against the four census
   nodes (`TestPolling::test_exponential_backoff_intervals`,
   `TestRetryBehaviors::test_429_respects_retry_after`,
   `TestRetryBehaviors::test_429_defaults_to_5s_when_missing`,
   `TestSearchIssues::test_429_retries_then_raises`), while the `<guard-rationale>` still carries zero
   row-id tokens. If that combination proves impossible, escalate rather than weakening either half.
5. Whichever branch: the derivation goes in the notes with its commands. "We depend on none of it" is
   only falsifiable if the reader can see how it was checked.

**Files**: reads — the inventory, `plan.md`, `spec.md`, `tests/sync/tracker/conftest.py`,
`src/specify_cli/tracker/saas_client.py`. Writes — none yet.

**Validation**: the branch is named, the two candidates are individually adjudicated with `file:line`
evidence that was opened, and the cited row count (0 or N) is stated as a number.

---

### Subtask T035 — Write the verdict-column stamp (body-only)

**Purpose**: make the falsification impossible to inherit silently, without disturbing what the leak
guard resolves against.

**Steps**

1. Place the stamp in the **body**, at or after `:11`. The natural anchors are the `## Legend` item 4
   and the `## Method` §4 definition — both are where a reader learns what the column means. A single
   clearly-headed stamp block plus a one-line pointer under each affected table heading is enough;
   nine near-identical blocks are not.
2. The stamp must say, in plain terms:
   - The column was derived against `test_429_respects_retry_after` **at a time when that node had
     never exhibited the failure**.
   - That node **now does** exhibit it — a victim on PR #3209's `fast-tests-sync`, head `5e98c2bb7`;
     and three census nodes failed simultaneously on pristine `main` at `98198e980` (job
     `92278529393`). Therefore the column is **falsified**, not merely unverified.
   - The stamp is scoped to the **Dependence column only**. The `#`, `Module : symbol`, `Reset seam`
     and `Caller` fields are untouched and remain load-bearing — `tests/sync/_leak_guard.py` resolves
     29 row-ids against this page.
   - The re-derived set from T034 (named rows, or an explicit **zero** with its reasoning).
   - It cites `#3136` (this satisfies `SC-010` sub-1) and the `#3115`-WP06 / this-WP06 name collision
     flagged in `E22`'s own text, so the two are not conflated.
3. **Touch no frontmatter.** Do not bump `updated`. Do not regenerate
   `docs/development/3-2-page-inventory.yaml` — that is WP04's file. Do not alter any
   `| E<n> | … |` row-id, row order, table header, or column count; if a per-row marker seems
   necessary, prefer a column-level statement, because a per-row edit is a structural change to a
   surface a running guard consumes.
4. Re-run the guard-id resolution loop **after** the edit: still `29`, no `UNRESOLVED` lines.

**Files**: `docs/development/process-global-inventory-3115.md` (**owned**, body only).

**Validation**: `grep -c '3136' …` ≥ 1; `grep -cE '^\| E[0-9]+ \|' …` still `53`;
`git diff -U0 -- …inventory-3115.md` shows no hunk at `:1-10`; the resolution loop → `29`, no output.
Read the diff; do not summarize it.

---

### Subtask T036 — Record the non-goal, then run the full validation battery

**Purpose**: record the CPU-contention decision **with its reasoning**, so the next reader inherits a
decision instead of re-deriving it at the cost of another agent-day; then prove the whole WP.

**Steps**

1. Create `kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/non-goals-3136.md` — the `<guard-rationale>`
   in `SC-010` sub-3. The `notes/` directory does not exist yet and must be created.
2. Record **all three** `C-005` reasons, each as its own reason, not merged into a summary:
   (a) **the producer is already named** and independently reproduced by two parties — CPython's
   `subprocess.Popen._wait(timeout)` POSIX busy-wait, `delay = min(delay * 2, remaining, .05)`;
   (b) **a contention repro cannot name a producer**, only make an existing one likelier to be caught;
   (c) **a local pass is the default outcome for a narrow-window race**, so a negative result is
   **uninformative by construction** — the predecessor's own probe missed because the thread had not
   entered its wait loop when the sub-millisecond test body ran.
3. Record the post-spec squad's sharper framing: the failure is **topology-and-timing dependent, not
   composition-dependent**. Pristine `main` reddens on this class in **11 of 18** consecutive
   `fast-tests-sync` jobs (61%), including at this mission's own baseline `98198e980`
   (`analysis-report.md:37-45`); and it is **nondeterministic at a fixed commit** — three of six
   same-SHA run pairs disagree, with `bb2020fea9` producing different victim sets with different
   magnitudes on identical commits (`analysis-report.md:50-53`).
4. Carry zero inventory row-id tokens into this file (Branch A), or exactly the set T034 licensed
   (Branch B, in the inventory doc, not here).
5. Run the battery (`D=docs/development/process-global-inventory-3115.md`,
   `K=kitty-specs/sync-sleep-count-3136-01KZ9B5A`):
   ```bash
   N="$K/notes/non-goals-3136.md"
   grep -c '3136' "$D"; grep -cE '^\| E[0-9]+ \|' "$D"        # SC-010 sub-1, sub-4 (→ 53)
   grep -cE '\bE[0-9]+\b' "$K/plan.md"                        # SC-010 sub-3 — two single-value
   grep -cE '\bE[0-9]+\b' "$N"                                # commands, never one over two files
   # SAME-FILE positive twin for the <guard-rationale> negative above.
   # sub-4's `53` fires against a DIFFERENT file ($D), so it cannot tell an
   # empty/absent $N from a compliant one: `grep -c` on an absent file prints
   # no count and exits 2, which reads as satisfied.
   test -s "$N" && echo "NON-EMPTY: $(wc -l < "$N") lines" || echo "MISSING OR EMPTY — FAIL"
   grep -c 'uninformative by construction' "$N"               # twin: must be >= 1 (reason (c))
   grep -c '11 of 18' "$N"                                    # twin: must be >= 1
   ./.venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q      # C-010, ~75-90 s
   ./.venv/bin/python -m pytest tests/architectural/test_glossary_canonical_terms.py -q
   ./.venv/bin/ruff check .                                   # C-002 / SC-012
   ```
6. **Expect `grep -cE '\bE[0-9]+\b' plan.md` to return `1`, not `0`** — see Risks. Report the measured
   value, name the false positive, and report the disambiguated value alongside it. Do **not** edit
   `plan.md` (not owned by this WP) and do not report `0` from a pattern you quietly changed without
   saying so.

**Files**: `kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/non-goals-3136.md` (new — see Risks on
its ownership).

**Validation**: three reasons individually present; `11/18` present with its source; the same-file
positive twins (`test -s` + line count, `uninformative by construction` ≥ 1, `11 of 18` ≥ 1) recorded
**beside** the zero-row-id negative; both architectural tests `EXIT=0` (the terminology guard takes
**~75–90 s**, not 0.1 s — do not kill it); `ruff check` → `All checks passed!`; every grep recorded
with its command.

---

## Definition of Done

- [ ] `docs/development/process-global-inventory-3115.md` carries a body-only verdict-column stamp
      naming the PR #3209 (`5e98c2bb7`) falsification of `test_429_respects_retry_after`, scoped
      explicitly to the Dependence column. `git diff` shows **no hunk in `:1-10`** (frontmatter).
- [ ] `grep -c '3136' …inventory-3115.md` ≥ `1` (`SC-010` sub-1); `grep -cE '^\| E[0-9]+ \|' …` = `53`
      (`SC-010` sub-4, the positive twin), unchanged by the edit.
- [ ] The guard-id resolution loop prints `29` and no `UNRESOLVED` line, **after** the edit.
- [ ] The load-bearing row set is derived, not assumed; `E15` and `E22` each individually adjudicated;
      the branch (empty → cite **0**; non-empty → the criterion inverts) is named and honoured.
- [ ] `notes/non-goals-3136.md` records all three `C-005` reasons plus the topology-and-timing framing
      with `11 of 18`.
- [ ] `SC-010` sub-3 reported as **two single-value commands**; the `plan.md` result reported as
      measured, with its false positive named.
- [ ] The `<guard-rationale>` zero-row-id negative carries a **same-file positive twin**:
      `test -s notes/non-goals-3136.md` true with its line count, plus
      `grep -c 'uninformative by construction'` ≥ 1 and `grep -c '11 of 18'` ≥ 1 **against that same
      file**. `SC-010` sub-4's `53` fires against the inventory page and cannot distinguish an
      absent `non-goals-3136.md` from a compliant one — on an absent file `grep -c` prints no count
      and exits `2`.
- [ ] Both docs-scoped guards run via `./.venv/bin/python -m pytest … -q` → `EXIT=0`, transcripts
      recorded (`C-010`, feeds `SC-016`); `./.venv/bin/ruff check .` → `All checks passed!`; no
      `ruff format` run and that string absent from the notes (`C-002`); no `tests/sync` or
      `tests/cli` run (`C-001`).
- [ ] The non-fatal `code_change WP does not own any files under src/ or tests/` warning is recorded
      as expected, not treated as a defect.
- [ ] Subtasks marked complete with evidence:
      ```bash
      spec-kitty agent tasks mark-status T033 T034 T035 T036 --status done \
        --mission sync-sleep-count-3136-01KZ9B5A
      ```
      Record the command's output envelope in the notes — the `mark-status` transcript is the
      evidence, not the claim that it was run.

---

## Risks

1. **`SC-010` sub-3's negative is red on `plan.md` today, through a false positive this WP cannot
   fix.** Measured: `grep -cE '\bE[0-9]+\b' plan.md` → **1**, at `plan.md:354`, which reads
   `# noqa: E402` — a lint code, not an inventory row-id. `plan.md` IC-07 risk (b) asserts *"this plan
   contains none, deliberately"*; that assertion is false as committed. **Mitigation**: report the
   literal value (`1`) **and** a row-id-shaped value using a bounded pattern that cannot collide with
   `E402`/`E501`, since the row-ids are exactly `E1`–`E53`:
   `grep -cE '\bE([1-9]|[1-4][0-9]|5[0-3])\b' plan.md` → **0** (measured). Report both, name the
   collision, and escalate the criterion's wording. Do not edit `plan.md`; it is not owned here.
2. **`notes/non-goals-3136.md` is required by `plan.md`'s IC-07 and by `SC-010` sub-3, but is absent
   from this WP's `owned_files`.** `plan.md`'s `## Project Structure` assigns it to IC-07 and to no
   other concern, so no other WP will create it. **Mitigation**: create it and record the ownership
   gap in the notes and the review handoff, so the reviewer adjudicates it rather than discovering it.
   If the reviewer rules the manifest must be fixed first, stop — do not widen `owned_files`
   unilaterally.
3. **A frontmatter touch would race WP04's generated lockfile across lane boundaries** —
   `docs-freshness` reds every PR on `INVENTORY-LOCKFILE-DRIFT`. **Mitigation**: body-only, verified
   by reading the diff. **Escalation**: a stamp needing a frontmatter field converts WP06 into a
   WP04-dependent package; stop and say so.
4. **A mechanical column edit corrupts the three-column tables, and disturbing a row-id breaks a
   running guard rather than a document.** The Dependence field is the *last* column — pipe index 5 in
   six tables, index 3 in three others — and 29 row-ids resolve from `tests/sync/_leak_guard.py`.
   **Mitigation**: no per-row mechanical rewrite; a column-level statement, then re-assert `53` rows
   and re-run the resolution loop (a grep, so `C-001` is not violated).
5. **Concluding "the depended-on set is empty" without deriving it.** `E15` and `E22` are live
   candidates. **Mitigation**: T034 requires each to be adjudicated individually, in writing, with
   opened `file:line` evidence.
6. **`C-010`'s guard only reds in CI's `integration-tests-core-misc` job**, so a terminology
   regression in fresh prose survives every local doctrine run — and a bare `uv run` would remove the
   very tools that run it. **Mitigation**: both docs-scoped guards are in the DoD;
   `./.venv/bin/<tool>` everywhere, with the recovery command in `## Context`.

---

## Reviewer Guidance

- **Open the diff, not the summary.** Confirm every hunk falls at `:11` or later in
  `docs/development/process-global-inventory-3115.md`. A frontmatter hunk is an automatic rejection —
  it converts this WP into a WP04-dependent package and the lane graph no longer holds.
- **Re-run the positive twin and the resolution loop yourself.** `grep -cE '^\| E[0-9]+ \|' …` must
  return **53** post-edit, and the loop must print `29` with no `UNRESOLVED`. A stamp that quietly
  reflowed a table shows up here and nowhere else.
- **Check that the stamp says *falsified*, not *unverified*.** "Unverified" understates a column whose
  reference node is now a confirmed victim. The PR #3209 head SHA `5e98c2bb7` must appear — a branch
  name is not reproducible; that branch moved twice during this mission.
- **Check the re-derived set is derived.** If the WP reports "empty", look for the adjudication of
  `E15` and `E22` specifically. An empty set asserted without those two named is not a derivation, and
  a "0 hits" grep with no positive twin is not evidence.
- **Check the three `C-005` reasons are three, and that `11 of 18` is present and attributed.** A
  single sentence covering "we can't reproduce it locally" collapses the reasons into the least useful
  one; the decisive reason is the third, that a negative result is uninformative **by construction**.
  Without the `11 of 18` framing the next reader re-derives "pristine `main` is green" — the claim the
  post-spec squad falsified.
- **Verify `SC-010` sub-3 was reported as two commands.** `grep -cE … file1 file2` prints one count
  per file and has no single value to compare; a single-number report from that form is a defect, not
  a pass. Expect the `plan.md` value to be `1` with the `E402` false positive named — a bare `0` here
  means the pattern was changed without saying so.
- **Verify no `tests/sync` / `tests/cli` run appears in any transcript** (`C-001`) and that no
  `ruff format` was run (`C-002`). Do **not** treat the `code_change WP does not own any files under
  src/ or tests/` warning as a finding — it is the deliberate cost of keeping this WP out of
  `lane-planning`.

---
work_package_id: WP04
title: The ADR that adjudicates the idiom, its era index row, and the generated page-inventory lockfile
dependencies:
- WP02
requirement_refs:
- FR-010
- FR-011
- C-010
planning_base_branch: feat/sync-sleep-count-3136
merge_target_branch: feat/sync-sleep-count-3136
branch_strategy: Planning artifacts for this mission were generated on feat/sync-sleep-count-3136. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/sync-sleep-count-3136 unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
history: []
agent_profile: curator-carla
authoritative_surface: docs/adr/3.x/
create_intent:
- docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md
execution_mode: code_change
owned_files:
- docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md
- docs/adr/3.x/README.md
- docs/development/3-2-page-inventory.yaml
role: curator
tags: []
tracker_refs: []
---

# Work Package Prompt: WP04 – The ADR that adjudicates the idiom, its era index row, and the generated page-inventory lockfile

## ⚡ Do This First: Load Agent Profile

Before reading any other section of this prompt, load your agent profile:

```
/ad-hoc-profile-load curator-carla
```

- **Profile**: `curator-carla` — **Role**: `curator` — **Agent**: `claude`
- This loads governance context, tool preferences, and behavioural directives. Do not skip it.
- **Fallback if the skill does not resolve**: read the profile directly from
  `packs/built-in/agent_profiles/curator-carla.agent.yaml` (verified present), or list the
  available profiles with `ls packs/built-in/agent_profiles/` and take `curator-carla.agent.yaml`.
  The rendered reference copy is `docs/reference/agent_profiles/curator-carla.md`.

---

## Objective

Land one ADR under `docs/adr/3.x/` that records the module-local `_sleep` / `_monotonic` /
`_randbelow` aliases (WP02's seam in `src/specify_cli/tracker/saas_client.py`) as a **deliberate,
canonical testability seam** — and, in the same document, **adjudicate the idiom rather than the
instance**, so this class of code ends the mission with one seam style and a stated precedence rule
instead of two styles and none. Then regenerate — never hand-edit — the two generated indexes the ADR
forces: the era `README.md` row and `docs/development/3-2-page-inventory.yaml`.

Start with: `spec-kitty implement WP04`.

---

## Context

### Why this ADR exists at all

Without a record, the alias rots exactly as its predecessor did. `_poll_jitter_multiplier`
(`src/specify_cli/tracker/saas_client.py:104-106`) is a seam with **zero callers** — verified this
session: `grep -rn '_poll_jitter_multiplier' src/ tests/` returns exactly one hit, its own definition
at `:104`. It returns `0.8 + (secrets.randbelow(4001) / 10000.0)` (max `1.2`) while the live inline
jitter at `:515-516` is `secrets.randbelow(4000)` / `0.8 + (jitter_basis_points / 10000)` (max
`1.1999`). A dead seam that has drifted from the live code. The whole difference between WP02's alias
and that corpse is this ADR plus WP05's gate arm asserting the alias's own call-site routing
(FR-010 conditions i and ii).

### The one thing this WP must get right — adjudicate the IDIOM (FR-011)

`src/specify_cli/sync/batch.py` **already exposes a competing seam**, and every line below was opened
and confirmed this session:

| Fact | Verified at |
|---|---|
| `def run_final_sync_with_retries(` with `*, sleep: Callable[[float], None] \| None = None` | `batch.py:628-631` |
| `sleeper = time.sleep if sleep is None else sleep` | `batch.py:641` |
| `sleeper` threaded through the retry helpers (`_sleep_before_final_sync_retry`, `_handle_final_sync_exception`, `_handle_final_sync_result`) | `batch.py:667-700` |
| **Three tests already use it**, `sleep=sleeps.append` | `tests/sync/test_final_sync_diagnostics.py:180`, `:207`, `:239` |
| The single caller that does **not** thread it | `src/specify_cli/sync/background.py:467` — `run_final_sync_with_retries(self._perform_sync)`, inside `_guarded_final_sync` |

So `batch.py`'s reach-through row exists **solely** because one caller declines an injection point that
is already there. An ADR that blesses an alias for `saas_client.py` while saying nothing about this
leaves the class with **two seam styles and no precedence rule** — a second authority, which is what
the charter's *Single canonical authority* governing principle forbids
(`.kittify/charter/charter.md:24-29`), introduced by the very document meant to establish canonicity.

**The ADR must therefore state the rule, not describe the instance:**

> Where a module already exposes a call-site injection point, **thread it**. Introduce a module-local
> stdlib alias **only** where the stdlib call has no threadable caller.

with **both worked examples**: `saas_client.py` **earns** an alias (its `time.sleep` / `time.monotonic`
/ `secrets.randbelow` calls are internal to `_request_with_retry` and `_poll_operation`, with no
injectable caller); `batch.py` **does not** — its row is closable by threading one keyword argument at
`background.py:467`.

And it must **relate itself explicitly** to
`docs/adr/3.x/2026-06-26-1-single-authority-seam-and-call-site-gate.md` (verified present, 13 398
bytes), which already decided seam + AST call-site gate + curated allowlist **against** a full
injectable DI port. This mission is a *second application* of that precedent, not a new decision — the
ADR must say so rather than re-deciding it.

### The generated lockfile — the blocker this WP owns

`scripts/docs/freshen_adr_inventory.py`'s own module docstring (`:1-31`) calls
`docs/development/3-2-page-inventory.yaml` *"a **generated lockfile**, regenerated from every page's
frontmatter"* (verified; 111 557 bytes). It writes **two** index updates in one command: that lockfile
row, and a `| YYYY-MM-DD | [Title](filename.md) |` row in the era `README.md`.

And the job that checks it is unconditional:

| Fact | Verified at |
|---|---|
| `docs-freshness.yml` runs on **every** `pull_request`, **no path filter** | `.github/workflows/docs-freshness.yml:3-6` |
| It runs `check_docs_freshness.py --ci` | same file, the *"Docs freshness (R3 lockfile drift default-on…)"* step |
| `INVENTORY-LOCKFILE-DRIFT` is **error** severity — *"the aggregate exit code keys off `any(f.severity == "error")`"* | `scripts/docs/check_docs_freshness.py:743-752` |
| The job installs Python **3.11** | `docs-freshness.yml` — `run: uv python install 3.11` |
| The `pr:deferred` / `pr:skip-ci` label escape exists but is **not** a path filter | `docs-freshness.yml:11` — the `if: ${{ !contains(…'pr:deferred') && !contains(…'pr:skip-ci') }}` line, re-measured by opening the file (`:10` is `runs-on: blacksmith-4vcpu-ubuntu-2404`). Must not be used to dodge this |

A new ADR without its regenerated row **reds a blocking job on this mission's PR**. Regenerate; never
hand-edit (a hand-edit drifts on the next run, because the file is generated *from* frontmatter).

**Baseline measured this session**: the tree is currently clean —
`freshen_adr_inventory --check: clean (missing_rows=0 inventory_stale=False)` — so any drift after this
WP is this WP's own.

### The frontmatter contract — with three corrections to the planning documents

The lockfile is generated *from frontmatter*, so frontmatter is the real input. Every claim below was
checked by opening the checker, not by trusting the plan.

**Required, and enforced:**

| Field | Enforced by | Evidence |
|---|---|---|
| `title` | inventory + README row generation — a missing value is a hard `FreshenError` | `freshen_adr_inventory.py:_read_adr_meta` — `if not title or not date: raise FreshenError(...)` |
| `date` | same, plus the README row format `\| YYYY-MM-DD \| [Title](file.md) \|` | `freshen_adr_inventory.py:AdrMeta.row()` |
| `status` | MADR convention — `Proposed \| Accepted \| Deprecated \| Superseded` | `docs/architecture/adr-template.md`; 100 % of `docs/adr/3.x/2026-*.md` frontmatter uses exactly `title` / `status` / `date` |

**⚠ CORRECTION 1 — the ADR does NOT need a `description`.** The planning brief says
`description_length_check.py --strict` requires a 50–180-char `description`. It does not apply here:
`scripts/docs/description_length_check.py:59-65` defines
`_EXCLUDE_PREFIXES: Final[tuple[str, ...]] = ("docs/adr/",)`, with the comment *"ADR decision bodies …
carry only bare `status` frontmatter — by design they have no `description`."* The walk at
`validate_descriptions` skips any page whose repo-relative path starts with that prefix. **Both** of
this WP's owned `.md` files (`docs/adr/3.x/2026-08-06-1-…md` and `docs/adr/3.x/README.md`) are under it.
Adding a `description` is not required; do not invent one to satisfy a gate that does not run.

**⚠ CORRECTION 2 — do NOT add `doc_status` / `updated`.** `packs/built-in/styleguides/common-docs.styleguide.yaml`
sets `frontmatter_required_fields: [doc_status, updated]` but lists `"adr/**"` under
`frontmatter_in_scope_exclusions`, with the comment: *"DIRECTIVE_042 MADR exemption … ADR bodies carry
MADR `status`/`date`, NOT `doc_status`/`updated` … **Backfilling doc_status/updated onto an ADR would
VIOLATE the directive** — the correct fix is this exclusion, not a backfill."* Copy the sibling
convention exactly.

**⚠ CORRECTION 3 — `PYTHONPATH=.` is mandatory, and the era README's own instruction omits it.**
`docs/adr/3.x/README.md`'s `## Naming` section says to run
`python scripts/docs/freshen_adr_inventory.py docs/adr/3.x/<your-adr>.md`. Run verbatim, that **fails**:

```
ModuleNotFoundError: No module named 'scripts'      # exit 1, verified this session
```

because the script does `from scripts.docs._inventory import parse_frontmatter` (`:41`). With
`PYTHONPATH=.` it exits 0. `docs-freshness.yml` sets `PYTHONPATH: .` on every docs step for exactly
this reason. The canonical command is in T023.

**Still enforced and still applicable**: `related_validator.py --strict` (resolves every `related:`
frontmatter edge — sibling ADRs carry **no** `related:` key, verified across the whole `2026-*` cohort,
so relate to the 2026-06-26 ADR with a **body link**, not a frontmatter edge) and
`relative_link_fixer.py --check` (`EXCLUDE_PREFIXES: tuple[str, ...] = ()` at `:98` — the full `docs/`
tree, ADRs included, so every relative body link in the new ADR must resolve).

### C-010 — the terminology guard, and what it actually covers

Touching prose triggers C-010. Run it. But be precise about what it catches:

- The `_FORBIDDEN_TERMS` arm (canonical `status commit`, not `cere`+`mony`; not `status`+`-writing`)
  **excludes `docs/adr/`** — `tests/architectural/test_no_legacy_terminology.py:44-52` lists
  `"docs/adr/"` in `_EXCLUDED_PATH_FRAGMENTS`, and `test_docs_adr_exemption_is_narrow` pins that the
  exemption is narrow. The ADR body is out of scope for this arm.
- The **lane-consolidation arm is not exempt**: `_LANE_CONSOLIDATION_SCAN_ROOTS = ("src", "docs")` with
  a file-level grandfathered baseline and no `docs/adr/` carve-out. So `lane merge`, `merge the lanes`,
  `merging lanes`, `lane-merge` in the new ADR **would** fail it. Canonical term is
  `consolidate` / `consolidation`.
- The canon also binds **Mission**, never `Feature`, in active prose
  (`.kittify/charter/charter.md:433-439`).
- **⚠ CORRECTION 4 — it is not ~0.1 s.** Measured on this tree: `10 passed in 75.19s`. Budget ~75–90 s.
  It only fails in CI's `integration-tests-core-misc` job otherwise, so a regression passes every local
  doctrine run and surfaces late — which is why it is run here, before push, not at acceptance.

### Cross-lane hazard — WP06 must stay body-only

WP04 regenerates the lockfile from **every** page's frontmatter under `docs/`. WP06 also touches
`docs/` (it stamps a verdict column into `docs/development/process-global-inventory-3115.md`). The two
lanes are non-conflicting **only** because WP06 is **body-only** and touches no frontmatter. If WP06
ever needs a frontmatter field, it **gains a dependency on WP04 and loses its parallelism**. State this
in the WP notes so the two do not silently collide on a generated file, and if WP06 has already landed
a frontmatter edit, regenerate *after* it and say so.

### ⚠ ENVIRONMENT — read before running anything

**NEVER run a bare `uv run`.** The tracked `.python-version` is `3.11.15` while `.venv` is Python
`3.12.13` (both verified). A bare `uv run` re-solves against `.python-version`, **destroys `.venv`**,
and drops `pytest` / `ruff` / `mypy`. This has happened **three times in this mission**. Proof, measured
this session:

```
uv sync --dry-run --python 3.12   →   Would uninstall 70 packages
```

- **Use** `./.venv/bin/<tool>` directly, or `uv run --python 3.12 --extra test --extra lint …`.
- **Recover** with `uv sync --python 3.12 --extra test --extra lint`.
- `~/.local/bin/*` resolve to an **unrelated checkout** (verified: `command -v ruff` →
  `/home/jeroennouws/.local/bin/ruff`). Prepend `./.venv/bin` to `PATH` and **quote** `command -v` output
  when recording it.
- **`docs-freshness.yml` runs on Python 3.11 in CI while this WP authors on 3.12.** Record it. Do not
  assume a 3.12-only environment, and do not "fix" a 3.11-only result by forcing 3.12.

### This WP's notes file — named

Every "recorded in the WP notes" in this prompt means exactly one path:

```
kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/adr-and-lockfile-3136.md
```

It is a **declared out-of-map planning write** (`wps.yaml`'s WP04 block) — `owned_files` may not
carry any path under `kitty-specs/`, so it is named there instead. **Create it before the first
command runs** and write the `command -v` / `--version` block into it first, so it is non-empty by
construction.

---

### Subtask T021 — Author the ADR from the canonical template, with the correct frontmatter

**Purpose.** Create `docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md` so the alias seam is a
recorded contract rather than an incidental shape, using the repo's own template and the frontmatter the
generators actually read.

**Steps.**
1. Read `docs/architecture/adr-template.md` (verified present) and follow its section order:
   *Context and Problem Statement · Decision Drivers · Considered Options · Decision Outcome
   (Chosen option, Consequences ±/neutral, Confirmation) · Pros and Cons of the Options ·
   More Information*.
2. Frontmatter — exactly three keys, matching every sibling in the era:
   ```yaml
   ---
   title: 'ADR: <the decision, stated as a rule>'
   status: Accepted
   date: '2026-08-06'
   ---
   ```
   No `description`, no `doc_status`, no `updated`, no `related:` (see Corrections 1–3). The generator
   strips a leading `ADR: ` prefix from the title for the README row (`_clean_title`), so the prefix is
   the sibling convention and is safe.
3. **Record options and rationale, not a fait accompli.** The template mandates *Considered Options* and
   *Pros and Cons of the Options*. Give at least these alternatives and why each lost:
   - **Test-side hardening only** (tighten assertions, thread-filtered recorders) — leaves the
     production reach-through intact; the defect class stays open and re-enters on the next test.
   - **A full injectable DI port for clock/sleep/randomness** — already decided **against** by
     `docs/adr/3.x/2026-06-26-1-single-authority-seam-and-call-site-gate.md`; re-deciding it here would
     be a second authority.
   - **Wrapper functions** (`def _sleep(x): time.sleep(x)`) instead of assignment aliases — refused: the
     alias must be bound **at import** by assignment, and WP05's arm 4b refuses an `ast.FunctionDef`
     form statically.
   - **Do nothing / leave the seam undocumented** — this is `_poll_jitter_multiplier`'s history; name it.
4. State the **Confirmation** section as an executable predicate, not prose: name WP05's gate file
   `tests/architectural/test_shared_module_object_patches.py` and its arms **4a** (zero calls in
   `saas_client.py` whose callee *resolves* to `time.sleep` / `time.monotonic` / `secrets.randbelow`)
   and **4b** (the three module-scope names are `ast.Assign` to those attributes). See the Risks note on
   node-ids.
5. Every relative body link must resolve (`relative_link_fixer --check` covers the full `docs/` tree).
   Same-directory ADR links are bare basenames, e.g.
   `[the 2026-06-26 seam ADR](2026-06-26-1-single-authority-seam-and-call-site-gate.md)`.

**Files.** `docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md` (create).

**Validation.**
```bash
cd /home/jeroennouws/dev/sk-missions/3136
PYTHONPATH=. ./.venv/bin/python scripts/docs/related_validator.py --strict --repo-root . ; echo "EXIT=$?"
PYTHONPATH=. ./.venv/bin/python scripts/docs/relative_link_fixer.py --check --repo-root . ; echo "EXIT=$?"
```
Both must exit `0`. Quote the summary line of each in the WP notes.

---

### Subtask T022 — State FR-011 as a RULE with two worked examples

**Purpose.** Settle the precedence between the two seam idioms now present in this cone, so the mission
does not institutionalise a second idiom with no rule for choosing.

**Steps.**
1. Write the rule verbatim as a rule, in the Decision Outcome:
   *where a module already exposes a call-site injection point, **thread it**; introduce a module-local
   alias **only** where the stdlib call has no threadable caller.*
2. **Worked example A — `saas_client.py` earns an alias.** Its stdlib calls sit inside
   `_request_with_retry` / `_poll_operation` with no injectable caller; the alias is the only seam a
   test can bind that structurally cannot observe another thread's `time.sleep`.
3. **Worked example B — `batch.py` does not.** Cite `batch.py:628-631`, `:641`, the threading through
   `:667-700`, the three existing consumers (`tests/sync/test_final_sync_diagnostics.py:180`, `:207`,
   `:239`, all `sleep=sleeps.append`), and the one non-threading caller, `background.py:467`. State the
   consequence plainly: that row is closable by threading one keyword argument, **not** by a new alias.
   (This also corrects the "requires alias seams in four more product modules" framing WP07 inherits.)
4. **Relate to the precedent.** Link
   `docs/adr/3.x/2026-06-26-1-single-authority-seam-and-call-site-gate.md` and state that this ADR is a
   **second application** of its seam + AST-call-site-gate + curated-allowlist decision, not a new one.
5. **Say the three `_`-prefixed names are load-bearing, in the words a dead-symbol sweep would grep.**
   Name `_sleep`, `_monotonic`, `_randbelow` literally, say they are referenced by `patch()` target
   strings in `tests/sync/tracker/`, and say that deleting them as "unused private helpers" would
   silently reopen the defect class. This is the sentence that stops the `_poll_jitter_multiplier`
   ending.
6. **Terminology.** Canonical `Mission` (never `Feature`); canonical `consolidate`/`consolidation`
   (never `lane merge` / `merge the lanes` / `merging lanes` / `lane-merge`); canonical `status commit`.

**Files.** `docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md` (edit).

**Validation.**
```bash
cd /home/jeroennouws/dev/sk-missions/3136
ADR=docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md
grep -c 'batch.py' "$ADR"                                   # >= 1 — the counter-example is present
grep -c '2026-06-26-1-single-authority-seam' "$ADR"         # >= 1 — the precedent is related
grep -cE '_sleep|_monotonic|_randbelow' "$ADR"              # >= 3 — the names are greppable
```
Each count must be non-zero; record the three numbers. A reviewer reads these as the falsifiable test
that the ADR adjudicated the idiom rather than the instance.

---

### Subtask T023 — Regenerate BOTH indexes with the single canonical command

**Purpose.** Close BLOCKER-5: an ADR without its regenerated lockfile row reds a blocking job on every
PR. One command owns both updates; nothing here is hand-edited.

**Steps.**
1. Run the canonical command — note `PYTHONPATH=.` (Correction 3) and the explicit venv interpreter:
   ```bash
   cd /home/jeroennouws/dev/sk-missions/3136
   PYTHONPATH=. ./.venv/bin/python scripts/docs/freshen_adr_inventory.py \
       docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md
   echo "EXIT=$?"
   ```
2. **Never hand-edit `docs/development/3-2-page-inventory.yaml`** and never hand-write the README row.
   Both are regenerated from frontmatter; a hand-edit drifts on the next run. If the row looks wrong,
   the *frontmatter* is wrong — fix that and re-run.
3. Confirm idempotence and cleanliness with the `--check` mode (it must report
   `missing_rows=0 inventory_stale=False`):
   ```bash
   PYTHONPATH=. ./.venv/bin/python scripts/docs/freshen_adr_inventory.py --check \
       docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md ; echo "EXIT=$?"
   ```
4. Report `git diff --stat` for **both** generated files. Expect a one-row addition to the era README's
   index table (date-ascending, so after the `2026-08-04` row) and a six-line block in the lockfile
   (`path` / `tag` / `divio_type` / `owning_workstream` / `current_target` / `notes`), sorted so it lands
   after `2026-08-04-1-egress-consent-boundary.md` and before `docs/adr/3.x/README.md`.
5. If `git diff --stat` shows lockfile churn **beyond** the new row, stop: another lane has changed
   frontmatter under `docs/` (see the WP06 hazard). Do not absorb unrelated churn silently — record it.

**Files.** `docs/adr/3.x/README.md` (index row only), `docs/development/3-2-page-inventory.yaml`
(regenerated).

**Validation.**
```bash
git diff --stat docs/development/3-2-page-inventory.yaml docs/adr/3.x/README.md
git diff docs/adr/3.x/README.md          # exactly one added table row
```

---

### Subtask T024 — Run the docs checks the way the job runs them

**Purpose.** Prove the blocking job will be green, on the interpreter the job actually uses.

**Steps.**
1. Run the freshness gate as CI does, redirecting so the exit status is capturable:
   ```bash
   cd /home/jeroennouws/dev/sk-missions/3136
   SPEC_KITTY_ENABLE_SAAS_SYNC=1 SPEC_KITTY_NO_UPGRADE_CHECK=1 PYTHONPATH=. \
     ./.venv/bin/python scripts/docs/check_docs_freshness.py --ci \
     --report /tmp/freshness-wp04.json --link-check none > /tmp/wp04-freshness.txt 2>&1
   echo "EXIT=$?"; tail -5 /tmp/wp04-freshness.txt
   ```
   Assert **no** `INVENTORY-LOCKFILE-DRIFT` finding:
   `grep -c 'INVENTORY-LOCKFILE-DRIFT' /tmp/wp04-freshness.txt` → `0`.
2. Run the two strict rulers (`related_validator`, `relative_link_fixer`) if not already recorded in
   T021, and quote their summary lines.
3. Run the C-010 terminology guard, redirected, and quote the summary line (budget ~75–90 s):
   ```bash
   ./.venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q \
     > /tmp/wp04-terminology.txt 2>&1 ; echo "EXIT=$?" ; tail -3 /tmp/wp04-terminology.txt
   ```
   Baseline measured before this WP: `10 passed in 75.19s`, `EXIT=0`.
4. **Record the interpreter split explicitly** in the WP notes: these commands ran on
   `./.venv/bin/python` → **Python 3.12.13**, while `docs-freshness.yml` installs **3.11**. A 3.12-local
   pass **does not transfer**; state that, and do **not** "fix" a 3.11-only result by forcing 3.12.
5. `ruff check` only if any Python file were touched — **none is**, so this WP runs no formatter.
   **Never run `ruff format`.**

**Files.** None owned; produces evidence for the Definition of Done.

**Validation.** All four commands exit `0`, with the summary line of each quoted in the WP notes.

---

## Definition of Done

All of the following, each with the quoted command output recorded in the WP notes:

1. `docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md` exists, follows
   `docs/architecture/adr-template.md`'s section order, and carries **exactly** `title` / `status` /
   `date` frontmatter — no `description`, no `doc_status`, no `updated`.
2. The ADR states the FR-011 **rule** verbatim, with **both** worked examples (`saas_client.py` earns an
   alias; `batch.py` does not, and `background.py:467` is why), and relates itself to
   `docs/adr/3.x/2026-06-26-1-single-authority-seam-and-call-site-gate.md`.
3. The ADR records **Considered Options** and their rationale — at minimum test-side hardening, full DI,
   and wrapper functions — not a fait accompli.
4. The ADR names `_sleep`, `_monotonic`, `_randbelow` as load-bearing in dead-symbol-sweep language, and
   names WP05's gate file plus arms 4a/4b in its Confirmation section.
5. `freshen_adr_inventory.py --check` on the new ADR reports
   `clean (missing_rows=0 inventory_stale=False)`, `EXIT=0`.
6. `git diff --stat` shows the era README index row **and** the lockfile row, and **no** unexplained
   lockfile churn.
7. `check_docs_freshness.py --ci` → `EXIT=0` and `grep -c 'INVENTORY-LOCKFILE-DRIFT'` → `0`.
8. `related_validator.py --strict` → `EXIT=0`; `relative_link_fixer.py --check` → `EXIT=0`.
9. **C-010**: `./.venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q` →
   `EXIT=0`, summary line quoted.
10. The WP notes record the 3.11-vs-3.12 interpreter split and the WP06 body-only dependency.
11. Mark the subtasks complete with evidence:
    ```bash
    spec-kitty agent tasks mark-status T021 T022 T023 T024 --status done \
      --mission sync-sleep-count-3136-01KZ9B5A
    ```
    Each subtask's evidence is the quoted command output above; do not mark a subtask done on a command
    whose exit status was not captured.

---

## Risks

1. **The ADR is prose, and prose has become a load-bearing constraint three times in this programme.**
   *Mitigation*: every claim in the ADR is stated as a predicate a reader can execute, with the gate file
   and arms named. Do not write a sentence the gate cannot confirm.
2. **The gate node-id may not exist yet.** WP04 depends on **WP02 only** — WP05, which creates
   `tests/architectural/test_shared_module_object_patches.py`, is a sibling and may not have landed.
   `plan.md` names arms **4a–4d** but pins no pytest function names. *Mitigation*: cite the gate by
   **file path + arm label** (stable, `plan.md:521`). If the file has landed, open it and upgrade the
   citation to the real node-id; if it has not, say so in one clause rather than inventing a node-id
   that will not resolve. **Never cite a node-id you have not run.**
3. **The lockfile is regenerated from every page's frontmatter**, so a concurrent frontmatter edit
   anywhere under `docs/` drifts it. *Mitigation*: WP06 is body-only by constraint; verify `git diff`
   scope before committing and stop on unexplained churn.
4. **Hand-editing the lockfile or the README row** produces a diff that looks right and drifts on the
   next run. *Mitigation*: only the named command writes those two files.
5. **Interpreter destruction.** A reflexive bare `uv run` wipes `.venv` (70 packages) mid-WP.
   *Mitigation*: the environment section above; recover with
   `uv sync --python 3.12 --extra test --extra lint`.
6. **C-010 passes locally on the wrong arm.** The `_FORBIDDEN_TERMS` arm exempts `docs/adr/`, so a
   reviewer could wrongly conclude the ADR is unguarded prose. *Mitigation*: the lane-consolidation arm
   **does** cover `docs/` with no ADR carve-out, and the lockfile row lands under `docs/` in scope for
   both — run the whole file, not one arm.
7. **Scope creep into a design document.** The template says ADRs are 1–2 pages, one decision per ADR,
   focused on *why*. *Mitigation*: this ADR decides one thing (the idiom precedence rule and the alias's
   canonical status). Implementation detail belongs to WP02 and WP05.

---

## Reviewer Guidance

Reject if any of these is true:

- **The ADR describes the instance instead of deciding the idiom.** The rule must appear as a rule, with
  `batch.py` as a named counter-example. An ADR that only says "`saas_client.py` gets three aliases" is
  the failure this WP exists to prevent — it leaves two seam styles with no precedence, a second
  authority under the charter's *Single canonical authority* principle.
- **`docs/adr/3.x/2026-06-26-1-single-authority-seam-and-call-site-gate.md` is not related.** Without it
  the ADR re-decides settled ground.
- **The Considered Options section is missing, empty, or lists only the chosen option.** An ADR records
  options and rationale; a fait accompli is not an ADR.
- **The lockfile or README row was hand-edited.** Check that the diff is exactly what the generator
  produces: re-run `freshen_adr_inventory.py --check` and require
  `clean (missing_rows=0 inventory_stale=False)`.
- **Frontmatter carries `description`, `doc_status`, or `updated`.** These are wrong for an ADR — the
  first is excluded from its gate, the latter two would violate DIRECTIVE_042's MADR exemption.
- **Any exit status is claimed without a captured command.** Every DoD row needs a quoted summary line.
- **A cited `file:line` was not opened.** A citation is not evidence of what the line says. Spot-check
  at least `batch.py:641` and `background.py:467` yourself.

Verify positively:

- `grep -n "_sleep\|_monotonic\|_randbelow" docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md`
  returns the three names in dead-symbol-sweep language.
- The era README diff is exactly **one** added table row, date-ascending.
- The lockfile diff is exactly **one** added six-key block at the correct sort position.
- `tests/architectural/test_no_legacy_terminology.py` was run to completion (~75 s), not skipped as
  "cheap".

**Do NOT run `tests/sync` or `tests/cli`** while reviewing this WP — they are out of scope and slow, and
this WP touches no code they cover.

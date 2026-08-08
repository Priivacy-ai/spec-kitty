# WP04 notes — ADR, era index row, and the generated page-inventory lockfile

Declared out-of-map planning write (`wps.yaml` WP04 block): `owned_files` may not carry a
path under `kitty-specs/`, so this notes file is named in the prompt instead.

All commands below were run in the **lane worktree**, not the repository-root checkout:

```
/home/jeroennouws/dev/sk-missions/3136/.worktrees/sync-sleep-count-3136-01KZ9B5A-lane-d
```

See "Prompt defects" §D-2 — the prompt's validation blocks say `cd /home/jeroennouws/dev/sk-missions/3136`
(the root checkout), which contradicts the lane-worktree rule. Paths below are otherwise verbatim.

---

## Environment

Recorded before the first mutating command. The venv lives at the **repository root**; the lane
worktree has none, so every invocation uses the absolute root interpreter.

```
$ export PATH="/home/jeroennouws/dev/sk-missions/3136/.venv/bin:$PATH"
$ command -v python  ->  "/home/jeroennouws/dev/sk-missions/3136/.venv/bin/python"
$ command -v pytest  ->  "/home/jeroennouws/dev/sk-missions/3136/.venv/bin/pytest"
$ command -v ruff    ->  "/home/jeroennouws/dev/sk-missions/3136/.venv/bin/ruff"
$ command -v mypy    ->  "/home/jeroennouws/dev/sk-missions/3136/.venv/bin/mypy"

$ .venv/bin/python --version   ->  Python 3.12.13
$ .venv/bin/python -m pytest --version -> pytest 9.0.3
$ .venv/bin/ruff --version     ->  ruff 0.15.12
$ .venv/bin/mypy --version     ->  mypy 1.20.2 (compiled: yes)
$ cat .python-version          ->  3.11.15
```

`~/.local/bin/*` resolves to an unrelated checkout, which is why the quoted `command -v` output
above is the check that matters, not a bare tool name.

**No bare `uv run` / `uv sync` was executed at any point in this WP.** The editable install
(`_editable_impl_spec_kitty_cli.pth`) was present at the start and is present at the end.

### Interpreter split — 3.12 local vs 3.11 in CI (DoD 10)

Every command in this WP ran on `./.venv/bin/python` → **Python 3.12.13**.
`.github/workflows/docs-freshness.yml` installs **Python 3.11** (`uv python install 3.11`) and the
tracked `.python-version` is **3.11.15**.

**A green result here does not transfer to CI by itself.** The docs scripts in scope are pure
`pathlib` / `re` / YAML frontmatter parsing with no version-gated syntax, so divergence is
unlikely — but "unlikely" is not "proven", and this WP does not prove it. Do **not** "fix" a
3.11-only failure by forcing 3.12; fix the script.

---

## Prompt defects found

### D-1 (material) — `_poll_jitter_multiplier` no longer exists; the prompt describes the pre-WP02 tree

The prompt's Context says:

> `_poll_jitter_multiplier` (`src/specify_cli/tracker/saas_client.py:104-106`) is a seam with
> **zero callers** — verified this session: `grep -rn '_poll_jitter_multiplier' src/ tests/`
> returns exactly one hit, its own definition at `:104`.

Measured on the lane tree (post-WP02):

```
$ grep -rn '_poll_jitter_multiplier' src/ tests/
   -> (no output, 0 hits)
$ git grep -n '_poll_jitter_multiplier' 98198e980 -- src/ tests/
   -> 98198e980:src/specify_cli/tracker/saas_client.py:104:def _poll_jitter_multiplier() -> float:
$ git log --oneline -S'_poll_jitter_multiplier' -- src/specify_cli/tracker/saas_client.py
   -> e652ff9fa fix(tracker): add module-local _sleep/_monotonic/_randbelow seam (#3136)
```

**WP02 deleted it** in the same commit that introduced the alias seam — which is exactly FR-010's
third condition ("`_poll_jitter_multiplier` deleted or promoted in the same change"). The prompt
was written before WP02 landed, so its present tense is a prediction that the tree has overtaken.

**Disposition: folded, not filed.** The ADR is in this WP's scope, so it states the precedent in the
**past tense** — the dead seam *existed*, drifted, and was removed by this mission. Writing it in the
present tense would have put a false, greppable claim into the authority path. The drift figures are
confirmed on the base rather than taken from the prompt:

```
$ git show 98198e980:src/specify_cli/tracker/saas_client.py | sed -n '104,106p'
def _poll_jitter_multiplier() -> float:
    """Return a cryptographically strong jitter multiplier in [0.8, 1.2]."""
    return 0.8 + (secrets.randbelow(4001) / 10000.0)

$ git show 98198e980:src/specify_cli/tracker/saas_client.py | sed -n '515,516p'
            jitter_basis_points = secrets.randbelow(4000)
            jitter_factor = 0.8 + (jitter_basis_points / 10000)
```

`randbelow(4001)` → max `1.2`; the live inline `randbelow(4000)` → max `1.1999`. The drift was real.

### D-2 (procedural) — validation blocks target the root checkout

Every validation block in the prompt opens with `cd /home/jeroennouws/dev/sk-missions/3136`, the
repository-root checkout. The operator's standing rule is that WP work happens in the allocated lane
worktree. **Disposition: substituted** the lane worktree path; commands otherwise verbatim. Recorded
rather than silently corrected because the root checkout is where a copy-paste would have landed.

### D-3 (advisory) — dispatched profile is `python-pedro`, prompt frontmatter says `curator-carla`

`agent_profile: curator-carla` in the WP frontmatter; the operator dispatched `python-pedro` and
instructed that profile be applied. **Disposition: operator instruction followed**, divergence
recorded. No behavioural conflict arose — this WP touches no Python, so the implementer profile's
test/typecheck gate is vacuous here and the curator's authority-path discipline is what bound.

---

## Workspace allocation — two merge conflicts resolved before work began

`spec-kitty implement WP04` failed twice on workspace allocation. Both were resolved manually in the
lane worktree, as the error message instructs.

**(1) Planning commit `4bdcb48f1` → lane-d.** Add/add conflicts on `spec.md`, `plan.md`, and all seven
WP prompts, plus `status.events.jsonl`.

- Markdown artifacts: resolved to the **lane side** (`a96dd28fc`). It is strictly newer and carries
  the 2026-08-07 corrections (the SC-005 reroute-vs-retarget correction, the `:559` + `:715`
  two-docstring count) plus normalized frontmatter. Verified the WP04 **bodies are identical**
  across both sides — only frontmatter formatting differed.
- `status.events.jsonl`: append-only, so union in timestamp order. The planning side held 2 genesis
  events (`MissionCreated`, `SpecifyStarted` @ `2026-08-05T16:12`) absent from the lane side; the
  lane side held 43 lane transitions from `2026-08-06T01:44`. Result: **45 rows**, all valid JSON,
  all `event_id`s unique.
- Commit: `133850fb9`.

**(2) Dependency lane-b (WP02) → lane-d.** Only `status.events.jsonl` conflicted. Compared by
`event_id` set: **all 18** events on the lane-b side were already present on the lane-d side
(theirs-only count: **0**), so the union is exactly the lane-d content. Resolved to the lane-d bytes
with no reformatting. Commit: `88e74b117`.

---

## Dependency verified by construction, not by prose (WP02)

The ADR adjudicates the **form** of the seam, so the form was read off the tree via AST rather than
trusted from the prompt:

```
$ python -c "<ast walk over src/specify_cli/tracker/saas_client.py module body>"
_sleep: Assign line=58 value=time.sleep
_monotonic: Assign line=59 value=time.monotonic
_randbelow: Assign line=60 value=secrets.randbelow
```

No `FunctionDef` named `_sleep` / `_monotonic` / `_randbelow` exists at module scope. This is the
property the ADR's Decision Outcome turns on: **assignment binds at import**, so the stdlib module
attribute and the module-local alias are two distinct patch targets. A wrapper (`def _sleep(x):
time.sleep(x)`) would forward to the stdlib at call time and collapse them into one recorder.

Call sites confirmed routed through the aliases (`saas_client.py:537`, `:540`):

```
537:            jitter_basis_points = _randbelow(4000)
540:            _sleep(jittered_delay)
```

### FR-011 counter-example — every cited line opened

| Claim | Line opened | Verdict |
|---|---|---|
| `run_final_sync_with_retries` takes `*, sleep: Callable[[float], None] \| None = None` | `batch.py:628-631` | confirmed |
| `sleeper = time.sleep if sleep is None else sleep` | `batch.py:641` | confirmed, verbatim |
| `sleeper` threaded through the retry helpers | `batch.py:648, 655, 669, 674, 681, 684, 693, 700` | confirmed |
| Three tests already inject via `sleep=sleeps.append` | `tests/sync/test_final_sync_diagnostics.py:180, 207, 239` | confirmed |
| The one caller that declines the injection point | `background.py:467` — `run_final_sync_with_retries(self._perform_sync)` inside `_guarded_final_sync` | confirmed |

### WP05's gate file has NOT landed (prompt Risk 2 realised)

```
$ ls tests/architectural/test_shared_module_object_patches.py
   -> No such file or directory
```

WP04 depends on WP02 only; WP05 is a sibling. Per Risk 2 the ADR therefore cites the gate by
**file path + arm label (4a / 4b)** and says in one clause that the file is not yet present.
**No pytest node-id is cited anywhere in the ADR** — none has been run, and inventing one would
produce an unresolvable citation in the authority path.

---

## Frontmatter contract — the three corrections re-verified, not transcribed

| Correction | Re-measured on this tree | Verdict |
|---|---|---|
| C-1: no `description` needed | `scripts/docs/description_length_check.py:65` → `_EXCLUDE_PREFIXES: Final[tuple[str, ...]] = ("docs/adr/",)` | confirmed |
| C-2: no `doc_status` / `updated` | `packs/built-in/styleguides/common-docs.styleguide.yaml:150-154` lists the DIRECTIVE_042 MADR exemption; `**/README.md` also excluded | confirmed |
| C-3: `PYTHONPATH=.` mandatory | `freshen_adr_inventory.py` imports `from scripts.docs._inventory import …` | confirmed; all runs below set it |

Sibling convention copied exactly (`docs/adr/3.x/2026-08-04-1-egress-consent-boundary.md`): exactly
three frontmatter keys (`title` / `status` / `date`), an `ADR: ` title prefix that `_clean_title`
(`freshen_adr_inventory.py:146-152`) strips for the README row, and **no H1** — the body opens at
`## Context and Problem Statement`.

---

## D-4 (material) — the prompt names TWO generated indexes; there are THREE

This is the defect that actually cost this WP a red, and it is the one a future ADR author will hit
again.

The prompt's "The generated lockfile — the blocker this WP owns" section says
`freshen_adr_inventory.py` *"writes **two** index updates in one command"* — the era `README.md` row
and `docs/development/3-2-page-inventory.yaml` — and DoD 7 requires
`check_docs_freshness.py --ci` → `EXIT=0`.

**Those two are not sufficient.** After both were regenerated and `--check` reported clean, the
blocking gate was still red:

```
$ SPEC_KITTY_ENABLE_SAAS_SYNC=1 SPEC_KITTY_NO_UPGRADE_CHECK=1 PYTHONPATH=. \
    .venv/bin/python scripts/docs/check_docs_freshness.py --ci --report … --link-check none
EXIT=1
ERROR DOCS-INDEX-DRIFT docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md: present in docs/ tree, absent from committed index
check_docs_freshness: exit=1 findings=1 errors=1 warnings=0
```

There is a **third** generated index — `docs/development/3-2-docs-retrieval-index.yaml`, the Common
Docs retrieval index (WP01 / C-001, a deliberately separate artifact from the page inventory). Its
drift rule `DOCS-INDEX-DRIFT` is **`error` severity and default-on**, exactly like
`INVENTORY-LOCKFILE-DRIFT` (`check_docs_freshness.py:816-831`), so it reds the same blocking job.
`freshen_adr_inventory.py` does **not** write it; `scripts/docs/docs_index.py --write` does.

**Disposition: folded, with a declared out-of-map edit.** `docs/development/3-2-docs-retrieval-index.yaml`
is **not** in WP04's `owned_files`.

> **Out-of-map rationale (one line):** a new ADR cannot land without regenerating the docs retrieval
> index, because its drift rule is error-severity and default-on on the same unconditional
> `docs-freshness` job that BLOCKER-5 is about — regenerating it is the completion of T023's own
> purpose, not new scope.

The edit is generator-written, never hand-edited, and its diff is exactly one added page block for
this ADR and nothing else (verified below).

**Sub-finding — the tool's own remediation hint recommends the banned command.** The
`suggested_action` embedded in `_docs_index_finding` reads:

```
regenerate the docs index with PYTHONPATH=. uv run python scripts/docs/docs_index.py --write, then commit it
```

A bare `uv run` re-solves the environment and destroys `.venv` — it has cost this Mission four venv
rebuilds. **I did not follow the hint**; I ran `PYTHONPATH=. .venv/bin/python scripts/docs/docs_index.py --write`.
The hint string is a live footgun aimed at exactly the agent most likely to obey it verbatim (one who
has just been handed a blocking error). Recommend a follow-on ledger entry; it is outside this WP's
`owned_files` (`scripts/docs/check_docs_freshness.py`) and outside its stated scope, so it is **filed,
not folded**. See `residual-ledger.md` RL-050.

---

## Command evidence

Every command ran in the lane worktree on `./.venv/bin/python` (Python 3.12.13). Exit statuses are
captured, not inferred.

### T021 — the ADR, and the two strict rulers

```
$ PYTHONPATH=. .venv/bin/python scripts/docs/related_validator.py --strict --repo-root .
related_validator: checked 947 edge(s); 0 dangling.
EXIT=0

$ PYTHONPATH=. .venv/bin/python scripts/docs/relative_link_fixer.py --check --repo-root .
[relative_link_fixer] CHECK: 0 dead bare-relative body links
EXIT=0
```

Frontmatter is exactly three keys, and the forbidden ones are absent:

```
$ sed -n '1,5p' docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md
---
title: 'ADR: Thread the Injection Point You Already Have — a Module-Local Stdlib Alias Only Where No Caller Can Be Threaded'
status: Accepted
date: '2026-08-06'
---

$ <grep the frontmatter block for ^(description|doc_status|updated|related):>  -> 0
```

Section order follows `docs/architecture/adr-template.md`: Context and Problem Statement · Decision
Drivers · Considered Options · Decision Outcome (rule, wrapper rationale, load-bearing note,
Consequences +/−/neutral, Confirmation) · Pros and Cons of the Options · More Information. No H1, per
the sibling convention.

### T022 — the idiom is adjudicated, measured on the ADR as committed

Reproduce with (`ADR=docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md`):

```
$ grep -c 'batch.py' "$ADR"                            -> 9    (required >= 1)
$ grep -c '2026-06-26-1-single-authority-seam' "$ADR"  -> 3    (required >= 1)
$ grep -cE '_sleep|_monotonic|_randbelow' "$ADR"       -> 12   (required >= 3)
$ grep -c 'background.py:467' "$ADR"                   -> 3
```

Terminology arms, measured on the ADR body:

```
$ grep -inE 'lane merge|merge the lanes|merging lanes|lane-merge' "$ADR" | wc -l  -> 0
$ grep -icE '\bfeature' "$ADR"                                                    -> 0
$ grep -ic 'ceremony' "$ADR"                                                      -> 0
$ grep -oE '\bMission\b' "$ADR" | wc -l                                           -> 3
```

### T023 — both prompt-named indexes regenerated by the single canonical command

```
$ PYTHONPATH=. .venv/bin/python scripts/docs/freshen_adr_inventory.py \
      docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md
README-ROW-ADDED 2026-08-06-1-module-local-stdlib-alias-seam.md
freshen_adr_inventory: rows_added=1 inventory=regenerated
EXIT=0

$ PYTHONPATH=. .venv/bin/python scripts/docs/freshen_adr_inventory.py --check \
      docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md
freshen_adr_inventory --check: clean (missing_rows=0 inventory_stale=False)
EXIT=0
```

Diff scope — no churn beyond the new rows:

```
$ git diff --stat docs/development/3-2-page-inventory.yaml docs/adr/3.x/README.md
 docs/adr/3.x/README.md                   | 1 +
 docs/development/3-2-page-inventory.yaml | 6 ++++++
 2 files changed, 7 insertions(+)
```

The README diff is exactly one added row, date-ascending after `2026-08-04`, with the `ADR: ` prefix
stripped by `_clean_title` as expected. The lockfile diff is exactly one added six-key block, sorted
after `2026-08-04-1-egress-consent-boundary.md` and before `docs/adr/3.x/README.md`. Nothing in either
file was hand-edited.

Third index (see D-4), generator-written:

```
$ PYTHONPATH=. .venv/bin/python scripts/docs/docs_index.py --write
docs_index: exit=0 generated=697 committed=697 drift=False (added=0 removed=0 changed=0)
EXIT=0

$ git diff --stat docs/development/3-2-docs-retrieval-index.yaml
 docs/development/3-2-docs-retrieval-index.yaml | 22 ++++++++++++++++++++++
 1 file changed, 22 insertions(+)
```

One added page block, this ADR only.

### T024 — the blocking job, red then green

**Red (before the third index was regenerated):**

```
EXIT=1
ERROR DOCS-INDEX-DRIFT docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md: present in docs/ tree, absent from committed index
check_docs_freshness: exit=1 findings=1 errors=1 warnings=0
```

**Green (after):**

```
$ SPEC_KITTY_ENABLE_SAAS_SYNC=1 SPEC_KITTY_NO_UPGRADE_CHECK=1 PYTHONPATH=. \
    .venv/bin/python scripts/docs/check_docs_freshness.py --ci \
    --report <scratch>/freshness-wp04.json --link-check none
EXIT=0
check_docs_freshness: exit=0 findings=0 errors=0 warnings=0

$ grep -c 'INVENTORY-LOCKFILE-DRIFT' <out>  -> 0
$ grep -c 'DOCS-INDEX-DRIFT'         <out>  -> 0
```

**C-010 terminology guard** — run to completion, not skipped as cheap:

```
$ .venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q -p no:cacheprovider
Baseline, before any WP04 edit:  10 passed in 81.26s   EXIT=0
After the ADR + all three indexes: 10 passed in 62.47s   EXIT=0
```

(The prompt budgeted ~75–90 s and cited 75.19 s; both of my runs land in that neighbourhood. The
spread between my own two runs is machine noise, not signal.)

**No Python file was touched by this WP**, so no `ruff` / `mypy` run applies. `ruff format` was never
run.

### Dependency guard re-run (source of the Confirmation block's numbers)

The ADR's Confirmation section quotes measurements I generated, not figures transcribed from the
prompt:

```
$ PYTHONPATH=src .venv/bin/python -m pytest \
    tests/sync/tracker/test_sleep_attribution_guard_3136.py -q -n0 -p no:cacheprovider -s
[#3136 guard] row=1 census_site=test_saas_client.py:784 stdlib_mock.call_count=150 alias_mock.call_count=3
[#3136 guard] row=2 census_site=test_saas_client.py:786 stdlib_mock.call_count=150 alias_mock.call_count=3
[#3136 guard] row=3 census_site=test_saas_client.py:937 stdlib_mock.call_count=150 alias_mock.call_count=1
[#3136 guard] row=4 census_site=test_saas_client.py:957 stdlib_mock.call_count=150 alias_mock.call_count=1
[#3136 guard] row=5 census_site=test_saas_client_origin.py:261 stdlib_mock.call_count=150 alias_mock.call_count=1
5 passed in 62.50s
EXIT=0
```

Run alone at `-n0`; `tests/sync` and `tests/cli` were never run concurrently.

---

## Cross-lane hazard — WP06 must stay body-only (DoD 10)

WP04 regenerates **all three** indexes from **every** page's frontmatter under `docs/`. WP06 also
touches `docs/` (it stamps a verdict column into
`docs/development/process-global-inventory-3115.md`).

The two lanes are non-conflicting **only** because WP06 is **body-only** and touches no frontmatter.
If WP06 ever needs a frontmatter field — including a `title` change, which now feeds the retrieval
index's `title` and `anchors` as well as the page inventory — it **gains a dependency on WP04 and
loses its parallelism**, and the regeneration must be re-run *after* it.

At the time of this WP, WP06 had **not** landed a frontmatter edit: the diff scopes recorded above
show only this ADR's own rows in all three generated files, with no foreign churn to absorb.

**The hazard is now wider than the prompt states**, because the retrieval index keys on headings and
the first paragraph too — so a WP06 body edit that changed a **heading** in a page it owns would also
drift `3-2-docs-retrieval-index.yaml`, not only a frontmatter edit. Body-only is necessary but, for
that file, "body-only below the heading level" is the actual safe condition.

---

## Review cycle 1 — remediation (2026-08-07)

### BLOCKER 1 — the ADR's wrapper justification was false; re-measured, not transcribed

The rejected ADR claimed at two sites that a wrapper form would make "the two recorders collapse into
one". **That is false**, and the document contradicted itself: its own Confirmation section already
said correctly that "a wrapper with every decorator retargeted is runtime-immune and would pass the
guard".

The claim originated in the dispatch brief. Per the standing rule — *if your prompt contains a claim
you cannot reproduce, measure it* — it was re-measured here rather than corrected by transcribing the
reviewer's numbers. A temporary probe was placed in `tests/sync/tracker/` so this directory's autouse
`conftest.py` shim applied (a standalone script fails: the guard's `client` fixture passes the legacy
`credential_store=` kwarg, which the real constructor no longer accepts). It reused the shipped
guard's `_run_polluted` / `_invoke_backoff_poll` so the topology is the real one, and **was deleted
immediately after the run** — `git status` clean, nothing committed.

Four cells, `{assign, wrapper}` × `{both targets patched, stdlib attribute only}`:

```
[wp04] saas_client   : <lane-d>/src/specify_cli/tracker/saas_client.py
[wp04] shipped _sleep : builtin_function_or_method (<built-in function sleep>)
[wp04] _PROBE_CALLS   : 150

[wp04] form     topology       stdlib_mock  alias_mock
[wp04] assign   BOTH-patched           150           3
[wp04] assign   STDLIB-only            150           -
[wp04] wrapper  BOTH-patched           150           3
[wp04] wrapper  STDLIB-only            153           -

[wp04] BOTH-patched identical across forms : True ((150, 3) vs (150, 3))
[wp04] assign  STDLIB-only : 150  (probe only == 150? True)
[wp04] wrapper STDLIB-only : 153  (excess over probe = 3)
1 passed in 115.25s
EXIT=0
```

**Independently reproduces the reviewer's figures.** The wrapper does **not** collapse the recorders:
patching `saas_client._sleep` replaces the wrapper object outright, so its body never runs and the
two forms are indistinguishable in the guard's own window. The real difference is the **reciprocal**
direction: with only the stdlib attribute patched, the wrapper still leaks this module's own 3 sleeps
into the process-global recorder (`153` = 150 probe + 3 own), so `saas_client` stays both a
contributor to and observable by every stdlib sleep recorder in the worker. The assignment reads
exactly `150` — the reach-through is severed in both directions. That is the property arm 4b
protects, and it is now what the ADR states at both sites.

`:166` ("a wrapper … would pass the guard") was correct and is unchanged.

**Published history carries the false clause.** Commit `a5ee0baea`'s message repeats "collapse them
into one". It is not rewritten — the correction lives in the ADR body and in this note. A reader of
`git log` alone would be misled; a reader of the authority path would not.

### BLOCKER 2 — RL-ids renumbered into WP04's reserved block

`RL-017` → **`RL-050`**, `RL-018` → **`RL-051`**, `RL-020` → **`RL-052`**, order preserved. Internal
cross-references updated (`RL-017` → `RL-050` inside the third-index entry; the notes' "See
`residual-ledger.md` RL-016" was itself dangling and now points at `RL-050`).

Read against the composed tree before renumbering: the allocator lives on
**`feat/sync-sleep-count-3136`** (`97e490c33`, header corrected by `7c96cf085`) — **not** on coord,
whose branch and worktree are still at `RL-016`. Coord's `RL-017`…`RL-022` are six unrelated
findings; they keep their IDs.

`feat/` was deliberately **not** merged into lane-d. The two branches have diverged substantially
(lane-d carries WP02's seam and guard, which `feat/` does not yet have; `feat/` carries WP01/WP03/WP06
evidence, which lane-d does not). Pulling that in on the eve of review would mix three other work
packages into this lane for no benefit — the reserved block makes the renumber collision-free
*without* their entries being present, which is the point of reserving it.

### Also fixed this pass

- **[MEDIUM]** Two quoted summary lines read `check_docs_freshness: exit=0 findings=1 errors=1` where
  the tool prints **`exit=1`**. Reproduced independently before correcting, non-destructively — by
  pointing `--docs-index` at the pre-commit blob from `a5ee0baea^` with the tree untouched:

  ```
  $ git show a5ee0baea^:docs/development/3-2-docs-retrieval-index.yaml > <scratch>/pre-index.yaml
  $ … check_docs_freshness.py --ci --docs-index <scratch>/pre-index.yaml --link-check none
  ERROR DOCS-INDEX-DRIFT docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md: present in docs/ tree, absent from committed index
  check_docs_freshness: exit=1 findings=1 errors=1 warnings=0
  ```

  `exit=0` beside `errors=1` was internally impossible, since the aggregate keys off
  `any(f.severity == "error")`. Both occurrences corrected.
- **[LOW]** The Confirmation transcript is now marked as elided (`… ` per row for the stripped
  `[#3136 guard] ` prefix and `probe_thread=` field), and the `150` is attributed to its pinned
  constant `_PROBE_CALLS` at `test_sleep_attribution_guard_3136.py:83` rather than presented as a
  sample.
- **[OPTIONAL, taken]** "Threadable caller" was defined only ostensively. It now carries a two-clause
  test (a parameter a test can supply, reachable without a change that spreads) so the rule decides
  new cases rather than only the two worked examples.

### Not taken on trust this cycle

Re-measured myself: the four-cell wrapper/assign matrix; the `exit=1` summary line; the location of
the allocator commits and the coord-vs-feat ledger state. Accepted from the reviewer without
re-derivation: that `a5ee0baea`'s commit message carries the same false clause (verified by reading
the message, which is self-evident) and the reviewer's own `-n0` re-run of the guard.

---

## Review cycle 2 — remediation (2026-08-07)

### The blocker: the "threadable caller" test contradicted worked example A

Cycle 1's fix for blocker 1 introduced a two-clause test that, applied literally, said
`saas_client.py` should **not** have an alias — the opposite of worked example A three paragraphs
later. Same shape as blocker 1 (a general claim the document's own example refutes), in the one
section whose purpose is to decide new cases.

Both clauses verified as holding, so the contradiction was real and not a misreading:

```
$ grep -rn '_poll_operation(\|_request_with_retry(' tests/ | grep -v 'def ' | wc -l
22          (20 in test_saas_client.py, 2 in test_sleep_attribution_guard_3136.py)

$ grep -rn '_poll_operation(\|_request_with_retry(' src/ | grep -v saas_client.py | wc -l
0           (all 17 production callers are inside saas_client.py itself)
```

**Route 2 taken**, per the coordinator's architecture call: condition the rule on severance rather
than on whether a caller could thread a parameter. Route 1 (delete the section) would have returned
the ADR to an ostensive-only definition, and deciding new cases is the document's whole value.

### The restatement

The verbatim FR-011 rule is unchanged. What replaced the two-clause test:

> **Can every test that asserts on these calls opt in — is there an injection point on the path that
> test actually drives?**
>
> **Yes** — thread it, and fix any asserting test that has not. The default path keeps a residual
> exposure; accept and record it.
> **No — no injection point exists anywhere on that path** — then the default path itself must be
> severed, and only the import-bound alias does that.

The mechanical justification is already proved elsewhere in the document: threading buys a seam only
on calls that opt in, because `sleeper = time.sleep if sleep is None else sleep` (`batch.py:641`)
resolves the stdlib attribute at call time on the `None` branch. Threading and aliasing therefore do
not buy the same thing, which is why "could a caller thread it?" was never the deciding question.

### The both-examples check — run BEFORE committing, which is what cycle 1 omitted

```
Example A: saas_client.py
  path driven by asserting tests : test -> client._poll_operation / _request_with_retry -> _sleep
  injection point on that path?  : NO  (no method on the path accepts a sleep function)
  tests passing one              : 0
  => sever the default path      => ALIAS          vs stated verdict "earns an alias"   MATCH

Example B: batch.py
  path driven by asserting tests : test -> service.stop() -> _guarded_final_sync
                                   -> run_final_sync_with_retries -> sleeper
  injection point on that path?  : YES (`sleep=` at batch.py:628-631)
  tests already opting in        : 3  (:180, :207, :239)
  tests not opting in            : 2  (:260, :303)
  => thread it, fix stragglers   => NO ALIAS       vs stated verdict "does not earn one" MATCH
```

**The check earned its keep — it caught a false claim in my own first draft.** That draft asserted
`batch.py`'s sleeps are "asserted only by tests that opt in — all three pass `sleep=sleeps.append`".
That is false. Measured:

```
$ grep -rn 'sync\.batch\.time\.sleep' tests/
tests/e2e/test_mission_create_clean_output.py:157:        patch("specify_cli.sync.batch.time.sleep"),
tests/sync/test_final_sync_diagnostics.py:260:        patch("specify_cli.sync.batch.time.sleep"),
tests/sync/test_final_sync_diagnostics.py:303:        patch("specify_cli.sync.batch.time.sleep", side_effect=sleeps.append),
```

`:303` feeds `:309`'s `assert sleeps == [FINAL_SYNC_RETRY_BACKOFF_SECONDS, …]` — a **genuine
corruptible assertion** on `batch.py`'s default path, exactly this ADR's defect. (WP03's census
recorded the same node as corruptible-but-out-of-class for SC-001's slice; this is that finding
reached independently.)

Had the ADR shipped the naive severance question, that assertion would have made `batch.py` earn an
alias and broken example B — the same contradiction in a new place. The resolution is the one the
evidence actually supports: **both non-opting tests reach the retry loop through `service.stop()` →
`_guarded_final_sync` → `run_final_sync_with_retries(self._perform_sync)` at `background.py:467`,
which forwards no sleeper.** They patch the shared module object because the one link on their path
declines the injection point, not because none exists. That is a **threading** defect, and threading
that single keyword argument lets them opt in like the other three. Example B stands, and is now
stronger and honest about the corruptible assertion rather than silent on it.

The ADR now states this, and states the accepted residual: threading `background.py:467` does not
eliminate `batch.py`'s default-path exposure, because the `sleep is None` branch remains — accepted
and recorded, since the seam exists and the remedy is to use it.

### Verification

Every cited line opened, not inferred: `:309`, `:303` and `:260` read verbatim; both tests confirmed
to drive `service.stop()` (`:265`, `:305`); `_guarded_final_sync` at `background.py:465`. The single
`sleep=` grep hit under `tests/sync/tracker/` is docstring prose at `test_saas_client.py:670`, not a
live injection — so example A's "0 tests pass one" is exact.

Gates after this pass — the generated indexes are **untouched**, as the cycle-2 review required:

```
heading set vs HEAD            : IDENTICAL (22)      first paragraph: IDENTICAL
docs_index --strict            : drift=False (697/697)   EXIT=0
freshen_adr_inventory --check  : clean (missing_rows=0 inventory_stale=False)  EXIT=0
check_docs_freshness --ci      : exit=0 findings=0 errors=0 warnings=0  EXIT=0
related_validator --strict     : 947 edge(s); 0 dangling      EXIT=0
relative_link_fixer --check    : 0 dead bare-relative body links   EXIT=0
C-010 terminology              : 10 passed in 56.16s   EXIT=0
git status docs/               : only the ADR modified
```

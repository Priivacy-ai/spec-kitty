# Research — meta.json fail-closed routing, and `#2804`'s returning red

**Mission:** `meta-fail-closed-3162-01KZ7FSQ`
**Baseline:** `upstream/main` **`96494e5ec`** (2026-08-04T21:51), measured 2026-08-05
**Interpreter:** `/home/jeroennouws/dev/sk-missions/3162/.venv/bin/python` (3.11.15), pytest 9.0.3,
`pytest_timeout` + `xdist` importable.

Two independent investigations, one per issue. `Priivacy-ai/spec-kitty#3162`'s census is its own artifact
at `research/3162-census.md` (516 lines, with its controls). `Priivacy-ai/spec-kitty#3138`'s bisect is
below, because it changed the mission's shape.

---

## Part 1 — `#3138`: the commit is `b04da00e13`, and the finding is a design conflict

**Verdict: structural design conflict. Not a regression, not an incomplete fix, not a revert.**

### The bisect

Each commit's own test revision against its own source, `PYTHONPATH=<worktree>/src` verified to override
the editable `.pth`, no `uv run` inside a worktree.

| Commit | Date | Marker result |
|---|---|---|
| `623f6178f1` — the `#2804` fix | 2026-07-24 | **`1 passed in 91.31s`** ← diagnostic control, answer known in advance |
| `10e970ed2` — `b04da00e13^` | 2026-07-29 | **`1 passed in 87.59s`** |
| **`b04da00e13`** — `#3076` row-aware driver | 2026-07-30 05:01Z | **`1 failed in 90.81s`** |
| `e561227069` | 2026-07-30 19:15Z | `1 failed` — same assertion; **carries, does not cause** |
| `96494e5ec` (head) | 2026-08-05 | `1 failed in 84.26s` — same assertion |

`e561227069` is **exonerated**, and `src/specify_cli/acceptance/matrix.py` is not implicated either.

**The date gap is a sampling artifact, not an onset.** `#3138` reports the red first appearing 2026-07-31
while both suspects are 2026-07-30. Resolved: CI run **`30515463326`** at **2026-07-30T05:04:34Z** already
shows `regression tests (blocking)` and `integration-tests-core-misc (misc)` — the exact two jobs `#3138`
names — failing at `b04da00e13` with the byte-identical assertion message. **`b04da00e13` landed red on
main.** The inventory that produced "2026-07-31" had sampled two runs at `bb2020fea9`.

### The assertion's own stated mechanism is false

`tests/regression/test_issue_2804_merge_resets_gate_artifacts.py:482` fails with
`assert 'pending' == 'pass'`, and its message blames `-X theirs` clobbering. Traced
`reconcile_acceptance_matrix_documents({}, FILLED, PLACEHOLDER)` against the test's exact fixtures:

- merged `criterion_id`s: `['AC-001', 'FR-001', 'FR-003']`
- `pass_fail`: `AC-001 pending`, `FR-001 pass`, `FR-003 pass`
- `FR-001`'s evidence (`d5b8324f9`) **survives**
- `overall_verdict`: `pending`

**Nothing was clobbered and `-X theirs` never won.** The proof: the raw placeholder has **no**
`overall_verdict` key, so a genuine take-theirs would have produced `None`, not `'pending'`. The
`#1732`/C-002 `-X theirs` note at `merge_driver.py:4-13,:75` is scoped to `meta.json` planning keys and is
not the mechanism here.

**The real mechanism:** `b04da00e13` replaced `623f6178f1`'s whole-file, **evidence-scored side-selection**
(`_acceptance_matrix_fill_score` / `_write_more_filled_side` — the filled document wins *entirely*, scaffold
rows discarded) with a **row-union reconciler** under FR-008. The union admits the mission branch's scaffold
row `AC-001` (`pending`), and `AcceptanceMatrix.overall_verdict` (`src/specify_cli/acceptance/matrix.py:249`)
is a **computed property** where `any(v == "pending")` dominates. **One surviving scaffold row poisons the
aggregate.**

### Why this is a design conflict rather than a bug

The two authority models are **mutually exclusive on this fixture**. `#2804`'s pin requires
`overall_verdict == 'pass'`, reachable only by discarding `AC-001` — precisely what FR-008 forbids
("never silently discard").

**Two tests in this repository pin contradictory answers for the same input, and the same commit shipped
both.** `tests/specify_cli/cli/commands/test_row_aware_merge_driver.py:427-448`,
`test_merge_driver_acceptance_matrix_writes_result_to_ours`, builds the identical shape — empty base, ours
`FR-001 pass`, theirs `AC-001 pending` — and asserts:

```python
assert merged["overall_verdict"] == "pending"  # AC-001 is still pending
```

Run on head: **`1 passed in 50.99s`**.

And `kitty-specs/write-side-seam-matrix-tracer-01KYP3MH/contracts/merge-driver-algorithm.md:40` closes the
escape hatch **by design**: *"the driver … never re-authors a computed verdict (acceptance
`overall_verdict` stays a property, not a merged field)."* No rule in the new design can satisfy `#2804`'s
assertion; the contract forbids the only mechanism that would.

Corroborating, and it matters for how the record is written: `b04da00e13` also **deleted**
`tests/merge/test_gate_artifact_merge_drivers_2804.py` (−249 lines), the unit gate `623f6178f1` added to
hold this invariant, and rewrote the marker (+106) claiming its assertions were *"verified against this
exact fixture"* — empirically false, since it failed in that same commit. The author **did** widen the
sibling `issue-matrix` assertion for exactly this reason ("deliberately narrower than byte-identical …
satisfied whether the merge cleanly resolves or surfaces a structured conflict marker") but did **not**
widen the acceptance-matrix one — because a computed aggregate has no conflict-marker representation.

### The product consequence is real

`src/specify_cli/acceptance/gates_core.py:525` turns `verdict == "pending"` into a **blocking activity
issue**. A merged mission whose acceptance genuinely passed now reports `pending` on the integration
branch. This is not a test-shape curiosity.

### OPERATOR DECISION — taken 2026-08-05

**Widen `#2804`'s acceptance-matrix assertion, exactly as its own issue-matrix sibling was already widened,
and reopen or supersede `#2804` to record that its pin changed shape.**

Rejected: a `SCAFFOLD_TODO_MARKER`-keyed suppression rule in the reconciler. It would fix the product
consequence *and* let `#2804`'s pin pass unchanged, but the driver has **zero** scaffold awareness today
(grep confirms none), so it amends the FR-008 authority model and is materially bigger than this mission
scoped.

**Consequence: the pending-poisons-the-aggregate product defect is NOT fixed here and must be filed** —
with `gates_core.py:525` as evidence and the suppression rule as its candidate fix. Widening the pin
without filing that would make a red go away without addressing what the red pointed at, which is the
failure this programme exists to close.

---

## Part 2 — `#3162`: see `research/3162-census.md`

Summarised; the artifact carries the tables and controls.

**Three inherited numbers were wrong and are corrected there:**

| Claim | Was | Measured |
|---|---|---|
| The arm split | 6 divergent-wrapper / 7 route-unwrapped | **4 DEGRADE / 2 REFUSE-typed / 7 REFUSE-raw.** Six sites carry `except ValueError` but only four degrade; the other two re-raise a typed domain error. Under D4 ("preserve each site's arm") the operative figure is **4 arms to preserve, 9 refusals**. Fallback (c) is unaffected — it is exactly the 7. |
| Bypass sites | 2 (`ref_advance.py`) | **4.** `implement_cores.py:259 _parse_meta_mapping` is a second private parser, fed by `git.show_blob` (`:338`) and `source.read_bytes()` (`:427`) — same shape, same lock-only decision, and `grep -c 'load_meta('` on that file is **0** too. |
| `resolution.py` sites | `:512` a site | `:509` and `:512` are **the same call** — `:512` is the `on_malformed=` keyword line of a multi-line call whose AST node begins at `:509`. `grep -c` returns 13 only because it also counts a docstring at `:185`. |

**The gate blindness is demonstrated, not inferred** — controls `C0`–`C3`. The gate anchors on
`json.loads`/`json.load` and resolves the first argument through ≤N *same-function* hops. Two scratch
modules differing **only** in whether the parse is inlined: inlined → **1 flagged**; delegated to a private
helper → **0 flagged**. **The cross-function split alone flips the gate**; the path clause already matches.
A fully-inlined `git show` read → still **0 flagged**, so no path-clause widening reaches it. Floor tests
are green today with all four sites invisible (`40 passed in 91.70s`, exit 0, `grep -c '^ERROR tests/'` → 0).

**Answer to the work package's question: both, split by site.** The two `read_text`-fed sites are reachable
by one bounded widening (follow a private same-module single-parameter parse helper); the two
`git show`/`show_blob` sites need a genuinely new detector or a dated allowlist entry. Either way widening
**raises** the live count against a shrink-only ceiling, so `INLINE_META_READ_FLOOR` and `FLOOR_MARGIN = 2`
must be re-derived **in the same change**.

**Two traps in the canonical target that will bite an implementer.** `load_meta_fail_closed(feature_dir)`
lives at `core/paths.py:638`, takes **one positional arg and no kwargs**, and `MissionMetaReadError` (`:506`)
is a `RuntimeError` — **not** a `ValueError`. So (a) all **4** DEGRADE handlers must become
`except MissionMetaReadError` **in the same edit**, or three resolution paths start crashing where they used
to fall back; and (b) the three `allow_missing=False` sites (rows 8, 9, 12) are **not** drop-in swaps — they
currently receive `FileNotFoundError` where the wrapper returns `None`, so each needs an explicit
`if result is None:` branch. Routing is **routed-count neutral** — both names are in `ROUTED_CALLEES`, so
`ROUTED_LOAD_META_FLOOR = 126` should not move.

---

## Open questions for the spec

| ID | Question |
|---|---|
| Q1 | Bypass scope: 2 sites or 4? The census found 4; the issue names 2. |
| Q2 | Route the bypass sites, or only make them **diagnosable**? Corruption today degrades to "blocks the advance" with a generic dirty-worktree message and never says "meta.json is corrupt". |
| Q3 | Widen the gate vs allowlist with a dated rationale — and the sequencing of the floor re-derivation, since widening raises a shrink-only ceiling. |
| Q4 | The 4 DEGRADE sites stay silent under D4. Should they log? |
| Q5 | `resolution.py:509`'s handler also swallows the **traversal-guard** `ValueError`, so narrowing it changes behaviour. Wanted fix, or regression to avoid? |
| Q6 | The three `allow_missing=False` sites each need a red test on the missing-file arm. |
| Q7 | Row 11 and `runtime_bridge_io.py:380` need fixtures nothing currently provides. |
| Q8 | Three duplicated copies of the lock-only comparison — name out of scope, or spin off? |
| **Q9** | **`#2804`'s disposition:** reopen it, or supersede it with a new issue? The pin changed shape; the record must say so. |
| **Q10** | Does the widened assertion still pin anything worth pinning, or does widening make the marker vacuous? If vacuous, deleting it honestly beats keeping a green that means nothing. |

## Standing rules carried into every work package

- Never pipe a suite whose exit status you intend to trust — redirect, quote the `N passed` line.
- Print the input count alongside any "all checks passed"; a gate on zero files passes vacuously.
- `-ra`, **not** `-rf`; count **`^ERROR tests/`**, not `^ERROR ` — the plain form over-counts, because a
  captured log record at level ERROR begins with it.
- Control every probe against a case whose answer you already know before trusting it on the real one.
- A killed run is neither a pass nor a fail — re-run narrowed and say you did.
- **Do not run `tests/sync` or `tests/cli` sweeps while the sibling mission at `~/dev/sk-missions/3167`
  holds that window.** Sibling daemon sessions reap each other — 16 recorded false reds.
- `pkill -f` and `pgrep -f` both match their own caller's command line; the `[b]racket` class is required in
  **both** forms, and reaps belong in a script file.
- Explicit-path staging: `git add <paths>`, never `git add -A`.
- `ruff check` only — this repo is **not** `ruff format`-clean at `line-length = 164`.
- Cite issues as `owner/repo#NNNN`; a bare foreign `#NNNN` mints a mandatory issue-matrix row this mission
  cannot resolve. This mission's **own** issues must be bare so they *do* mint one.
- File follow-up issues for anything out of scope rather than absorbing it.

# Tracer: Tooling Friction — org-tier-expected-artifacts-unreachable-01M0RMBG

Mission for issue #3703. Seeded by the orchestrator at scaffold time per charter Standing
Order #3 and the sk-design reflexive-failure clause. Append as the mission proceeds.

Mark every entry **verified first-hand** or **reported by a subagent**.

---

## F1 — `agent mission create` emitted the SK-72 event-capture warnings (verified first-hand)

Scaffold command succeeded (exit 0, `"result": "success"`, topology `single_branch`), but
stderr carried the SK-72 / SK-65 family warnings:

```
Warning: event journal capture failed: project sync store is locked
Warning: Event routing failed: project sync store is locked
Warning: Event did not durably queue; dropping from publication
Warning: Explicit-context event capture failed: machine layout cutover did not publish
         within the bounded wait
```

Non-fatal here — the command completed. Ledger **SK-72** (open, verified first-hand) is the
root cause: every event-emitting command inline-drives a store cutover that can block
forever on SQLite `BEGIN IMMEDIATE`. The probe is O(projects x 8) and this host carries 172
project dirs.

**Mitigation adopted for this mission:** every event-emitting spec-kitty invocation
(`plan`, `finalize-tasks`, `safe-commit`, `record-analysis`, status transitions) runs with
`SPEC_KITTY_SYNC_MINIMAL_IMPORT=1` and a generous timeout. No new ledger entry — SK-72
already carries this, including the mitigation.

## F2 — scaffold auto-commit message: NOT a defect (verified first-hand, corrects a stale reading)

`agent mission create` auto-committed `f0db78a6f "Add meta for feature
org-tier-expected-artifacts-unreachable-01M0RMBG"`.

The `sk` hub's SKILL.md still describes this message as "commitlint-invalid,
Terminology-Canon-violating" (its SK-64 reference). **The ledger retracted that**, having
actually run both gates:

- `commitlint.config.cjs` carries an explicit `ignores` entry matching
  `/^(Add|Update) (meta|spec|tasks|plan) for (feature|mission) /` — this message passes.
- `tests/architectural/test_no_legacy_terminology.py` scans `_SCAN_ROOTS = ("src","tests","docs")`
  file content and never reads `git log` — commit subjects are out of its scope.

So this commit is left exactly as-is. Not amended.

**The live risk that IS real and inherited by this mission:** the ignore alternation covers
`meta|spec|tasks|plan` but NOT `record-analysis`'s commit, which reads `Add analysis report
for mission <slug>` and genuinely fails commitlint (`type-empty`, `subject-empty`). Two
independent missions measured it as the only failing commit in their PR range. **The analyze
phase of this mission will emit that commit, so PR-prep must reword it in-range** (the
SK-64-sanctioned choice) rather than loosening the shared lint config.

Upstream doc drift worth noting: `~/.hermes/skills/sk/SKILL.md` should be corrected to match
the ledger's retraction.

## F3 — lanes.json `predicted_surfaces` is keyword-match noise, not a real surface claim

`lanes.json`'s `lanes[0].predicted_surfaces` lists `api`, `app-shell`, `artifact-rendering`,
`tests`, `tracker-integration` for this mission — a pure `src/charter/` + five test-file
path-join bugfix that touches none of those subsystems. `infer_surfaces()`
(`src/specify_cli/lanes/compute.py:162-176`) derives `predicted_surfaces` via case-insensitive
substring matching against the WP prompt's prose, not `owned_files` — e.g. it matched
"tracker" inside the WP01 frontmatter's own `tracker_refs: []` key name, and similar
incidental matches produced the other four labels.

This is inert for this single-WP mission (no lane-overlap comparison ever runs against a
single lane), so no functional change was made to `lanes.json` — it is a generated,
computed file (SK-72 bans hand-editing spec-kitty state) and confirmed adversarial review
(TASKS-SEQ-001) found no fix belongs inside this mission's own artifacts; the root cause is
pre-existing `infer_surfaces()` keyword-matching behavior in the tooling itself. Recording it
here so a future reader of this mission's `lanes.json` does not mistake `predicted_surfaces`
for a claim about which subsystems WP01 actually touches.

## F4 — analyze phase (2026-08-24): commitlint trap CONFIRMED first-hand; SK-06/#3133 NOT reproduced

**Commitlint trap (F2's prediction, now observed).** `spec-kitty agent mission
record-analysis` auto-commits its own write with the subject `Add analysis report for mission
org-tier-expected-artifacts-unreachable-01M0RMBG`. That subject matches neither
`commitlint.config.cjs`'s `ignores` regex (`^(Add|Update) (meta|spec|tasks|plan) for
(feature|mission) `— "analysis report" is not in the `meta|spec|tasks|plan` alternation) nor
any `type-enum` prefix, so it fails `type-empty`/`subject-empty` exactly as F2 predicted. It
fired **four times** in this phase — once per analyze round, because every re-run after a fix
commit re-invokes `record-analysis`:
- `e051ba2b0` (round 1, one finding: I1)
- `a5ec593ed` (round 2, after I1 fix, one finding: I2)
- `195b3b385` (round 3, after I2 fix, one finding: I3)
- `6c3a00d7a` (round 4, after I3 fix, findings-free, verdict `ready`)

Only the **last** of these (`6c3a00d7a`) is the one that matters for the final artifact state;
the earlier three are superseded intermediate states still reachable in history. **PR-prep
must reword all four commits in-range** (or fold them) — not just one — since commitlint runs
per-commit across the PR range, not just on the tip. Confirming the SK-64-sanctioned choice:
do not loosen the shared lint config.

**record-analysis requires a clean worktree — new operational finding, not previously
documented in this mission's tracer.** `record-analysis` fails loudly with
`error_code: DIRTY_WORKTREE` if any tracked file is modified/uncommitted when it's invoked
(confirmed first-hand: a verify-round subagent hit this after a fixer subagent's edits were
still uncommitted). Remediation is exactly what the error names: commit the fix first, then
re-run analyze. This is sane fail-closed behavior, not a defect — recording it here because it
changes this mission's fix-loop shape: every analyze round in this phase was FIX (fresh
subagent) → COMMIT (orchestrator, `safe-commit`) → RE-ANALYZE (fresh subagent), not
FIX-then-immediately-re-analyze-in-the-same-subagent as a naive reading of the design-pipeline
doc's 4b template might suggest.

**Side effect, every round:** each `record-analysis` invocation also regenerates
`.kittify/dossiers/<slug>/snapshot-latest.json` (new `snapshot_id`, updated `parity_hash_*`)
but does NOT always fold that file into its own auto-commit — three of the four rounds left it
modified-but-uncommitted, requiring the orchestrator to fold it into the next `safe-commit`
alongside the actual fix. Not blocking, just an extra file to remember when committing.

**SK-06 / issue #3133 ("record-analysis silently writes verdict: unknown for an explicitly
ready report") — investigated, NOT reproduced on this checkout.** Read
`src/specify_cli/analysis_report.py` directly: `verdict: unknown` is reachable ONLY when the
report body carries no `analysis-findings/v1` carrier at all (`parse_structured_findings`
returns `None` for a missing/foreign leading frontmatter block —
`write_analysis_report`'s `structured is None` branch, `analysis_report.py:433-437`). Given a
present, schema-valid carrier, the verdict is `compute_verdict_from_findings()` — a pure
function of `findings[].severity`, deterministic, never `unknown`. Across all four analyze
rounds this phase ran (one with a real medium finding, one with a real medium finding, one
with a real low finding, one clean), the persisted verdict matched the carrier's computed
verdict exactly every time — `ready` in all four cases (none of this mission's findings ever
reached high/critical). **Conclusion: the carrier-based recorder in this checkout already
implements the fix #3133 asks for** (a documented, structured verdict/count block, per its
"Expected" section) — issue #3133 is open upstream but its reproduction (`spec-kitty-saas`
mission on 3.2.6, an OLDER/different codepath) does not describe this checkout's current
`analysis_report.py`. Not closing #3133 ourselves (out of this mission's scope and no access
to re-verify the original repro's exact version), but recording here that a phase-agent on a
current `main` checkout should NOT expect to hit it as long as the analyzing agent emits the
carrier per `packs/built-in/missions/mission-steps/software-dev/analyze/prompt.md` — omitting
the carrier, not a tooling defect, is the only way `unknown` occurs on this checkout.

## F5 — `ruff` absent from this checkout's hand-built `.venv` (verified first-hand)

`Makefile`'s `lint` target runs `uv run ruff check src/`, but the dispatch instructions for
this WP explicitly ban a bare `uv run` ("destroys the hand-built `.venv`"). Checked directly:
`.venv/bin/ruff` does not exist and `.venv/bin/python -m ruff` raises `No module named ruff`,
even though `ruff>=0.4.0` is declared in `pyproject.toml`'s `[project.optional-dependencies]
lint` group — this checkout's `.venv` was evidently built without the `lint` extra installed.
Sibling checkouts on this host (e.g. `../3384/.venv/bin/ruff`) do carry it, confirming this is
a per-checkout gap, not a repo-wide one.

**Workaround adopted (does not touch this checkout's `.venv`):** `uvx ruff check ...` — `uvx`
spins up an isolated, ephemeral tool environment distinct from `uv run`'s project-environment
sync, so it does not resync or mutate `.venv`. Confirmed: `uvx ruff@0.4.10` failed to parse
`ruff.toml`'s `UP045` selector (too old a pinned version for this repo's current lint config);
plain `uvx ruff` (latest) succeeded cleanly against both the TID251 gate
(`uvx ruff check src tests --select TID251` → "All checks passed!") and the full lint target
scoped to the touched production file (`uvx ruff check src/charter/org_expected_artifacts.py`
→ "All checks passed!"). Ruff is advisory-only per this WP's dispatch instructions, so this
gap was not otherwise blocking, but a future WP that treats ruff as load-bearing on this
checkout should either fix the `.venv`'s `lint` extra (outside this WP's six-file scope) or
use the same `uvx ruff` substitution.

## F6 — `agent tasks mark-status` succeeds but does not auto-commit under the SK-72 cutover stall (verified first-hand)

`SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 spec-kitty agent tasks mark-status T001 T002 T003 T004 T005
T006 --status done --mission org-tier-expected-artifacts-unreachable-01M0RMBG` printed the
same SK-72-family warnings as F1 plus a full `LayoutCutoverIncompleteError` traceback from
`sync/layout_generation.py:694` (`_await_publish_or_loud`), reached via
`sync/dossier_pipeline.py:_prepare_bodies` → `sync/body_upload.py:_enqueue_artifact` →
`sync/body_queue.py:enqueue`. Despite the traceback, the command still printed "✓ Marked 6
subtasks as done: T001, T002, T003, T004, T005, T006" and exited — the event-sourced status
write itself succeeded (`status.events.jsonl` gained a real entry, `status.json` and this
mission's dossier `snapshot-latest.json` were regenerated). What did **not** happen: this
invocation's `--auto-commit` default did not land a commit — the three files were left
modified-but-uncommitted in the worktree afterward (mirrors F4's "record-analysis... does NOT
always fold that file into its own auto-commit" pattern, now observed on `mark-status` too).
**Mitigation applied:** ran `spec-kitty safe-commit` explicitly against the three touched
state files (`snapshot-latest.json`, `status.events.jsonl`, `status.json`) with a
`chore(mission): ...` message rather than leaving the tree dirty or hand-editing state.
Confirms `SPEC_KITTY_SYNC_MINIMAL_IMPORT=1` is necessary-but-not-sufficient mitigation for
SK-72 on this command family — the command completes and the state write is durable, but the
auto-commit half of the operation can silently no-op under the same cutover stall, requiring
an explicit follow-up `safe-commit` every time.

## F7 — SK-69 reproduced in its *absent-refs* variant; only the lane-diff-gated transitions need `--force` (verified first-hand)

Recording the WP01 lane transitions after reviewer approval, `agent status emit` refused:

```
Error: WP01 cannot move to for_review: no implementation commit on lane lane-a
(kitty/mission-org-tier-expected-artifacts-unreachable-01M0RMBG-lane-a) beyond
fix/org-tier-expected-artifacts-3703. Commit the work in the lane worktree first,
or pass --force if there is genuinely nothing to commit.
```

**This mission is the ORIGINAL SK-69 shape, not #3705's variant.** Both refs are simply
absent here:

```
git rev-parse kitty/mission-org-tier-expected-artifacts-unreachable-01M0RMBG        -> fatal: Needed a single revision
git rev-parse kitty/mission-org-tier-expected-artifacts-unreachable-01M0RMBG-lane-a -> fatal: Needed a single revision
```

`meta.json` records `topology: single_branch` and `target_branch:
fix/org-tier-expected-artifacts-3703`, where all seven WP01 commits
(`d817c7d02..df979f6d8`) live — the topology's normal path. So the guard compares two refs
the mission never had.

**Disposition**: followed SK-69's recorded disposition rather than re-litigating it — the
CLI's own documented `--force --reason`, with a reason stating this mission's actual facts
(absent refs, not same-SHA refs). This goes through the CLI, validates against the state
machine, and lands an auditable reason in `status.events.jsonl`. It is not a hand-edit. The
guard's *intent* — do not advance a WP that did no work — was demonstrably satisfied: the
work is committed and an independent reviewer confirmed RED-first **empirically**, by
reverting `src/charter/org_expected_artifacts.py:88` and observing 19 failures across all
six files.

**Corroborates and narrows SK-69**: exactly as #3705 measured, `--force` was needed ONLY for
`in_progress→for_review` and `for_review→in_review`. The final
`--to approved --review-result-json '{...}'` succeeded **cleanly, no force**. Two independent
missions, two different ref topologies (absent here, same-SHA there), same narrow fix surface:
only the lane-diff check is broken.

**Side effect worth knowing**: each `status emit` auto-commits a
`chore(spec-kitty): status transition WP01` commit. Two landed here (`e984d0c06`,
`2dcca651a`). They are bookkeeping only — `git diff df979f6d8..HEAD -- src/ tests/` is empty,
so the reviewer's verdict still applies to byte-identical implementation content.

## F8 — commitlint exposure in the PR range is SEVEN commits, not four (verified first-hand against the config)

F2 predicted the `record-analysis` commit would fail commitlint. Correct, but incomplete. Read
`commitlint.config.cjs` directly and enumerated the whole PR range (`3442ca1af..HEAD`, 45
commits). Two distinct failure classes:

**Class 1 — spec-kitty tooling defect (4 commits), the SK-64 gap:**
`e051ba2b0`, `a5ec593ed`, `195b3b385`, `6c3a00d7a` — all `Add analysis report for mission <slug>`,
emitted by `record-analysis`. The `ignores` regex is
`/^(Add|Update) (meta|spec|tasks|plan) for (feature|mission) /` — "analysis report" is not in the
alternation, so these are linted and fail `type-empty` + `subject-empty`. Confirms SK-64's
retracted-and-replaced framing for a third and fourth time.

Note the *other* tool auto-commits DO pass, exactly as SK-64 says: `f0db78a6f` (`Add meta for
feature ...`), `53d61dfb5` (`Add tasks for feature ...`) and `9eae1fa2e` (`Add plan for mission
...`) all match the ignore regex.

**Class 2 — OUR OWN naming error (3 commits), not a tooling defect:**
`c76ce3473`, `48e6f185d`, `c575d081a` — `reviews(spec):`, `reviews(plan):`, `reviews(tasks):`.
The `type-enum` is `build, chore, ci, docs, feat, fix, lint, perf, plan, refactor, revert, spec,
style, test`. **`reviews` is not in it.** `spec:` IS allowed (so the five `spec:` fix-round
commits pass).

This one is ours to own, not spec-kitty's: the review-protocol fixes the *artifact filenames*
(`<phase>.<group>.findings.yaml`) but says nothing about the commit *type*. The phase agents
chose `reviews(...)` freely and picked a type the repo does not allow. **Doctrine improvement
worth carrying upstream**: the review-protocol should name a conforming commit type for the
trail commit — `docs(reviews):` or `chore(reviews):` would pass.

**Disposition**: all seven are `sk-land`'s to fold — rewording in-range is a history rewrite
requiring force-with-lease, which that runbook owns. **The shared lint config is NOT to be
loosened** (SK-64's stated preference, and a landing pass must not weaken a repo-wide gate).

## F9 — `cutover-guard` reds the PR; the remedy works but DENIES having worked (SK-50, 4th first-hand corroboration)

CI `cutover-guard` failed on the first full run of PR #3708:

```
cutover-guard report
  Missions touched by diff : 1
  Un-cut-over              : 1

Un-cut-over mission(s) block this diff:
  org-tier-expected-artifacts-unreachable-01M0RMBG: status_phase not flipped
  despite event-log runtime evidence
    remedy: spec-kitty migrate backfill-runtime-state --mission org-tier-...-01M0RMBG
```

Root cause is the SK-50/SK-51 family: `agent mission create` does not stamp `status_phase` at
scaffold time, so a mission created by the current version is un-cut-over by default and the
guard fires on the happy path. `meta.json` carried **no** `status_phase` key at all before the
remedy.

**SK-50 reproduced exactly — the summary lied.** Ran the guard's own prescribed remedy from the
mission's primary checkout (SK-49's worktree hazard did not apply — this mission's branch lives
in the checkout itself, not a linked worktree):

```
backfill-runtime-state summary
  Total missions scanned : 1
  Flipped                     : 0
  Skipped (already migrated)  : 1
  Seed events                 : 0
  Failed                      : 0
```

...while `git diff` showed it had just added `"status_phase": "1"` to `meta.json`. **The write
was real and the report denied it.** Following SK-50's operational rule — *ignore the summary,
check `git diff` on the mission's `meta.json`* — is what caught this. Trusting the summary would
have led to hunting a nonexistent second defect.

Not a hand-edit: the value was written by the sanctioned CLI, then committed as a landing fold.

**This is the fourth independent first-hand corroboration of SK-50** (prior: PR #3524 /
`up-org-template-fsm-01M06F9K`, PR #3681 / `mission-scaffold-tasks-lanes-defects-01M0NERD`, and
the entry's original observation). The defect is stable, reproducible, and on the default happy
path of every new mission — `Flipped: 0 / Skipped (already migrated): 1` is what a SUCCESSFUL
flip looks like.

**Fix direction (unchanged from SK-50/SK-51)**: have `agent mission create` stamp the current
`status_phase` at scaffold time, since a mission created by the current version is by definition
already cut over; and separately, make the summary count the write it actually performed.

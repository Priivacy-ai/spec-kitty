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

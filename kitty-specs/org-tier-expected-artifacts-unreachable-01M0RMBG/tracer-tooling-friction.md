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

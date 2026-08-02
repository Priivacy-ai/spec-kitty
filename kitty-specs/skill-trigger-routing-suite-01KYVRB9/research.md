# Research: Skill Trigger-Routing Conformance Suite

**Mission**: `skill-trigger-routing-suite-01KYVRB9` | **Date**: 2026-07-31

All citations below are re-verified directly against a local checkout of
`garrison-hq/muster` at tag `v1.2.1` (commit `16f0d34c3126fab5df2ee0b6e1e304a4d9bcb8e3`,
read-only inspection — that checkout is a different agent's active
workspace and is never written to by this mission). Every finding here
either confirms a spec.md citation or narrows/corrects it; none required
opening `spec.md` for a rewrite, per this skill's guardrail, but four of
them (§2, §3, §6, §7) materially change how the plan must specify
verification, and are called out again in `plan.md`'s "Findings Requiring
Spec Attention."

---

## §1 — The behavioral case pipeline, traced end to end

`doSkillsRun` (`src/cli/index.ts:1532`) reads and schema-validates the
manifest, then for each `type: behavioral` case either records a graceful
skip (`{passed:true, skipped:true}`, no endpoint configured) or calls
`runBehavioralSkillCaseSafe` → `runBehavioralSkillCase` (`:1414`), which:

1. Parses the referenced `SKILL.md` for `name`/`description` frontmatter.
2. Loads the query-set file at `querySetPath` (`shouldTrigger[]`,
   `nearMiss[]` — the YAML's own `threshold` field is read but **discarded**;
   the case's own `c.threshold` wins, `:1455`).
3. Builds exactly **one** `ToolDefinition` from that name/description (or,
   for `isControl: true` cases, overrides the description with
   `RIGGED_IMPOSSIBLE_DESCRIPTION` and the name with the literal string
   `"rigged-impossible-control"`, `:1430-1444`).
4. Calls `runTriggerConformance` (`trigger.ts:397`), which hard-gates on
   `MIN_QUERIES_PER_AXIS = 8` (`:66`, gate at `:403-422`), then for each
   query runs `runSingleQuery` (`:269`) `runsPerQuery` times, each
   individual model call wrapped in its own `try/catch` (`:280-291`) —
   a thrown error increments that query's own `runsErrored` and is
   **never retried, never skipped, never propagated**.
5. `gradeAxis` (`:230`) aggregates `sum(runsTriggered)/sum(runsTotal)` across
   all queries in the axis; `should-trigger` passes iff `triggerRate >=
   threshold`, `near-miss` passes iff `triggerRate < threshold`.
6. The CLI (`:1470-1481`) reports `{id, type:"behavioral", passed, skipped:
   false, shouldTriggerAxis, nearMissAxis, isControl: verdict.isControl}`.

## §2 — Finding: `runsErrored` is not a case-level field (materially affects FR-004/FR-005 verification design)

Spec.md's User Story 3 / FR-004 language ("the case report shows `passed:
false`, `runsErrored: 0`") reads as if `runsErrored` were a field directly
on the JSON case object. It is not. `SkillsCaseResult` (`src/cli/index.ts:1268-1290`)
carries only `errored?: boolean` (a **case-level** structural-failure flag —
set only when the whole case throws before any query executes, e.g. a
missing `skillDir`; never set by a network failure, because
`runSingleQuery`'s per-call `try/catch` swallows that first). The actual
per-run error counts live two levels down, inside
`shouldTriggerAxis.queryBreakdown[].runsErrored` and
`nearMissAxis.queryBreakdown[].runsErrored` (`AxisVerdict`/`QueryRunResult`,
`trigger.ts:230-259`, `:294-299`).

**Consequence for the plan**: any script or workflow step that asserts on
`runsErrored` must compute it as
`sum(shouldTriggerAxis.queryBreakdown[].runsErrored) + sum(nearMissAxis.queryBreakdown[].runsErrored)`
for the target case — never read a nonexistent top-level field. This is
codified in `data-model.md`'s Evidence Artifact section and
`contracts/verification-scripts-cli-contract.md`'s `check-control-
discrimination.mjs` contract. Traced numerically: a fully dead endpoint
makes every `runSingleQuery` call throw, so `runsTriggered = 0` and
`runsErrored = runsPerQuery` for every query in both axes — the derived sum
is `2 * (8 shouldTrigger + 8 nearMiss) * runsPerQuery` at minimum-fixture
size, always `> 0`, and `triggerRate = 0` for both axes regardless of
whether the endpoint is dead or the model is simply well-behaved. This is
exactly why the derived `runsErrored` sum — not `passed`, not
`triggerRate` — is the only field distinguishing "the control discriminated
because the model is good" from "the control discriminated because nothing
ran" (garrison-hq/muster#76, confirmed at the source level here).

## §3 — Finding: the manifest schema has no distractor-tool hook — muster#82 is structural at v1.2.1, not something this mission's YAML can fix

`runBehavioralSkillCase` always constructs exactly one `ToolDefinition`
(`src/cli/index.ts:1458-1463`, a fixed-length-1 array literal) from the
target skill's own frontmatter. `SkillsManifestBehavioralCase`
(`:1254-1263`) has exactly these fields: `id, type, skillDir, profile,
querySetPath, runsPerQuery, threshold, isControl` — **no field exists to
declare additional tools**. `trigger.ts`'s own `TriggerCase.tools:
ToolDefinition[]` type technically accepts an array, and `targetTool =
triggerCase.tools[0]` (`:424`) only grades against index 0, but the CLI's
manifest-driven code path — the only path this mission's `skills run`
invocation exercises — never populates `tools[1..]`. Adding distractor
tools would require either a muster source change (out of scope: this
mission adds no code to `src/core/` or `src/adapters/`, C-001 diff-scope,
Scope Guard) or a fork of the CLI's manifest parser (also out of scope).

**Consequence for the plan**: distractor tools are **not achievable within
this mission at the pinned `1.2.1`**. This is recorded as a known,
structural limitation in `conformance/skills/README.md` (a `[LIMITATION]`
tag, alongside the D-1 `[CONVENTION]` tag) rather than attempted via a
manifest workaround that the schema does not support. The should-trigger
axis for every case in this suite can therefore only detect actively
repellent descriptions, exactly as the underlying hazard note warned — the
suite reports this limitation, it does not paper over it. A future muster
PR adding a `distractorTools` (or similar) field to
`SkillsManifestBehavioralCase` would be the correct fix, tracked the same
way D-1 tracks the twin-phrasing rubric addendum: as a dependency note, not
this mission's own diff.

## §4 — `isControl` mechanics confirmed

The manifest case's own `isControl: boolean` field (schema-required, not
optional — `:1262`) is what the CLI reads to decide whether to substitute
`RIGGED_IMPOSSIBLE_DESCRIPTION`/`"rigged-impossible-control"` as the tool
name/description (`:1430-1444`); `trigger.ts` then independently re-derives
its own `isControl` verdict by checking `tools[0].function.name ===
"rigged-impossible-control"` (`:420`, `:467`) — a deliberate double-check
(the CLI's comment at `:1433-1441` explains this is intentional: reporting
`c.isControl` directly instead would mask `trigger.ts`'s own blind spot).
**Plan implication**: authoring the manifest only requires setting
`isControl: true` on exactly one case; the tool-name substitution is
automatic and must not be hand-duplicated in the query-set YAML or
elsewhere.

## §5 — Exit-code divergence, confirmed at the source (not just the doc)

`doSkillsRun`'s only path to exit `2` is the manifest read/parse
`try/catch` at `:1544-1556` (`ExecutionError` thrown before any case runs).
Every per-case execution error — including a fully dead
`MUSTER_ENDPOINT` — is caught inside `runSingleQuery` (per network call,
§1 above) or `runBehavioralSkillCaseSafe` (per case, structural-only) and
folded into `passed`/`errored`/`runsErrored`, never re-thrown. The CLI
returns `ok ? 0 : 1` (`:1584`). `site/src/content/docs/reference/cli.md`
states one uniform rule ("`2` execution error (unreadable file, bad
manifest, **endpoint down**)") that `behave`/`a2a` honor for a genuinely
unreachable endpoint but `skills`/`sop` do not — `skills` folds
endpoint-down into per-run/per-case failures at exit `1`, confirmed above;
this mission does not attempt to reconcile that (muster#78 is an open
product question upstream, out of this mission's scope guard). FR-004's
falsification condition (dead endpoint → `passed:false` **and** derived
`runsErrored > 0`, never exit `2`) is the correct, code-verified
expectation for `skills run` specifically.

## §6 — Finding: C-001's file-glob is narrower than FR-002/FR-005's own committed deliverables

C-001's prose lists the allowed diff surface as
`conformance/scripts/check-trigger-*.mjs` (a glob matching only filenames
starting `check-trigger-`). FR-002 commits to authoring
`check-twin-phrasing.mjs` and FR-005 commits to authoring
`check-evidence-artifact-shape.mjs` — **neither filename matches that
glob**. C-001's own stated verification command
(`git diff --stat main -- src/doctrine/skills/` empty) does not actually
exercise the glob, so this inconsistency would not be caught mechanically
today, but it would misfire if anyone later encodes C-001's prose glob as
a literal CI check. The plan resolves this by stating the intended
allowed-script set explicitly and exhaustively (four filenames, §7 below)
rather than by a glob a future reader could reasonably over- or
under-match. This is flagged here, not silently patched into spec.md's own
constraints table (this skill's guardrail: spec issues route back to
`spk-mission-specify`, not a silent plan-time edit).

## §7 — Plan-level addition: a fourth verification script, `check-control-discrimination.mjs`

Spec.md's FR-004 verification command is prose ("run the manifest... and
assert... from the JSON report"), not a checked-in, rejection-case-testable
script — a departure from every other FR in this spec, all of which name a
concrete `.mjs`. Per this programme's own hazard history ("ten broken
verification commands, every one caught by constructing the rejection case
and running it, none by reading"), an assertion this load-bearing (it is
the entire discrimination-control proof, User Story 3 / SC-002) should not
be left as an ad hoc one-off `node -e` invocation re-typed by whoever runs
it. The plan adds `conformance/scripts/check-control-discrimination.mjs
<report.json> --mode healthy|dead-endpoint` to lane-b's write scope
(§Work-Package Outline in `plan.md`), computing the §2 derived `runsErrored`
sum and asserting the mode-appropriate expectation
(`healthy`: `passed===false && runsErrored===0`; `dead-endpoint`:
`passed===false && runsErrored>0`). Full contract in
`contracts/verification-scripts-cli-contract.md`.

## §8 — File-naming convention for the 3 skills that are both a duplicate-pair member and a run-family member

`spk-run-next`, `spk-run-review-wp`, `spk-run-implement-review` are each
simultaneously the "new" side of one of the five duplicate pairs (WP01) and
one of the three run-family cluster members (WP02). Because the
near-miss purpose differs per axis-under-test (WP01's near-miss set borrows
from the *legacy twin's* should-trigger phrasing; WP02's near-miss set
borrows from the *other two run-family siblings'* should-trigger phrasing),
these three skills need **two distinct query-set files each**, not one
file serving both purposes — mixing both near-miss sources into one
8-minimum array would make a resulting near-miss trigger ambiguous between
"confused with the legacy twin" and "confused with a run-family sibling."
Spec.md's own arithmetic ("10 duplicate-pair files... 13 query-set files
minimum") already implies this (10 + 3, not 10 total), but never states the
naming convention that keeps WP01 and WP02 from writing the same filename
for these 3 skills. This plan fixes the convention as:

- WP01 (duplicate-pair purpose): `<skill-id>-duplicate-pair-queries.yaml`
- WP02 (run-family purpose): `<skill-id>-run-family-queries.yaml`

applied to all 13 files for naming uniformity (not only the 3 that would
otherwise collide), and two distinct manifest case `id`s per shared skill
(e.g. `spk-run-next` and `spk-run-next-run-family`), both referencing the
same `skillDir` but a different `querySetPath`. See `data-model.md`
§Duplicate Pair / Run-Family Cluster and `plan.md`'s Work-Package Outline.

## §9 — D-1 rubric addendum: confirmed muster-side target, no local vendored copy

`docs/rubric/skills-trigger-taxonomy.md` lives in `garrison-hq/muster`
(confirmed present at `v1.2.1`, no "twin" language, matching spec.md's own
finding). This mission's fork (`spec-kitty`) has no vendored copy of that
file to patch — D-1's muster-side PR is tracked as a dependency note only;
this mission's own diff never touches it. `conformance/skills/README.md`
carries the `[CONVENTION]`-tagged inline text meanwhile (FR-006/D-1), and
now also the `[LIMITATION]`-tagged distractor-tools note from §3.

# Data Model: Skill Trigger-Routing Conformance Suite

**Mission**: `skill-trigger-routing-suite-01KYVRB9` | **Date**: 2026-07-31

Every shape below is either a file this mission authors (Trigger Query Set,
Behavioral Manifest Case, Evidence Artifact) or a muster-owned shape this
mission only consumes (Trigger Verdict and its nested Axis/Query shapes) —
the consumed shapes are copied verbatim from `garrison-hq/muster@v1.2.1`
source, not re-derived, per `research.md` §1.

## Trigger Query Set (authored, one YAML file per `(skill, purpose)` pair)

`conformance/skills/trigger-queries/<skill-id>-<purpose>-queries.yaml`,
`purpose ∈ {duplicate-pair, run-family}` (research.md §8):

```yaml
id: string                    # matches the skill id under test
source: "docs/rubric/skills-trigger-taxonomy.md"   # normative source, fixed
threshold: 0.5                 # present for shape-parity with muster's own
                                # fixture convention; the manifest case's own
                                # `threshold` field wins at run time
                                # (research.md §1 point 2) — kept here so a
                                # human reading the file alone still sees an
                                # intended value, not so the CLI reads it
shouldTrigger:                 # >= 8 entries (MIN_QUERIES_PER_AXIS, trigger.ts:66)
  - "..."
nearMiss:                      # >= 8 entries; for a duplicate-pair-purpose
                                # file, at least one entry is byte-identical
                                # to a phrase in the twin's should-trigger
                                # set; for a run-family-purpose file, at
                                # least one entry from EACH of the other two
                                # siblings' should-trigger sets (FR-002)
  - "..."
```

- **Duplicate pairs** (5): `ad-hoc-profile-load` ↔ `spk-doctrine-profile-load`;
  `spec-kitty-runtime-next` ↔ `spk-run-next`; `spec-kitty-runtime-review` ↔
  `spk-run-review-wp`; `spec-kitty-implement-review` ↔
  `spk-run-implement-review`; `spec-kitty-git-workflow` ↔
  `spk-admin-git-workflow` — 10 `-duplicate-pair-queries.yaml` files.
- **Run-family cluster** (3): `spk-run-next`, `spk-run-review-wp`,
  `spk-run-implement-review` — 3 additional `-run-family-queries.yaml`
  files, authored only for these three (the other 7 duplicate-pair skills
  have no run-family purpose file). 13 files total.

## Behavioral Manifest Case (authored, one entry per query-set purpose)

`conformance/skills/behavioral-manifest.yaml`, one case per query-set file
above (13 non-control cases) plus exactly one control case (14 total):

```yaml
defaults:
  model: gpt-4o-mini            # D-2, explicit pin
  runsPerQuery: 3
  threshold: 0.5

cases:
  - id: string                  # e.g. "spk-run-next" or
                                 #      "spk-run-next-run-family" for the
                                 #      second, run-family-purpose case over
                                 #      the same skillDir (research.md §8)
    type: behavioral
    skillDir: "../../src/doctrine/skills/<skill-id>"
    profile: base
    querySetPath: "trigger-queries/<skill-id>-<purpose>-queries.yaml"
    runsPerQuery: 3              # case-level; overrides the query-set's own
                                  # `threshold` field, NOT `runsPerQuery`
                                  # (the query set has no runsPerQuery field
                                  # at all — only `threshold` is shadowed)
    threshold: 0.5
    isControl: false
  # ...13 of the above...
  - id: rigged-impossible-control
    type: behavioral
    skillDir: "../../src/doctrine/skills/ad-hoc-profile-load"  # placeholder
                                  # dir — irrelevant to grading once isControl
                                  # substitutes name+description (research.md §4);
                                  # any real, readable skillDir satisfies
                                  # parseSkill() without being graded on its
                                  # own frontmatter
    profile: base
    querySetPath: "trigger-queries/rigged-impossible-control-queries.yaml"
    runsPerQuery: 3
    threshold: 0.5
    isControl: true               # sole `true` in the manifest (FR-004)
```

`rigged-impossible-control-queries.yaml` follows the `examples/` pattern
(D-3): `shouldTrigger` = 8 plausible, unrelated queries; `nearMiss` = 8
topically-adjacent variants of those same queries — deliberately never the
literal string `ZZZCONTROL` (muster#73), since the control's own
description substitution (`RIGGED_IMPOSSIBLE_DESCRIPTION`) already contains
that token and a literal near-miss match on it would self-match by text
overlap rather than by a model reasoning about tool fit.

## Trigger Verdict (consumed, muster `trigger.ts`/`src/cli/index.ts` @ v1.2.1)

```ts
// QueryRunResult — trigger.ts:294-299 (one per query in an axis)
interface QueryRunResult {
  query: string;
  runsTotal: number;      // = runsPerQuery
  runsTriggered: number;
  runsErrored: number;    // per-query error count; NOT summed anywhere upstream
}

// AxisVerdict — trigger.ts gradeAxis() return shape, :230-259
interface AxisVerdict {
  axis: "should-trigger" | "near-miss";
  triggerRate: number;    // sum(runsTriggered)/sum(runsTotal) across queries
  threshold: number;
  passed: boolean;        // should-trigger: rate>=threshold; near-miss: rate<threshold
  queryBreakdown: QueryRunResult[];
}

// SkillsCaseResult (JSON report entry) — src/cli/index.ts:1268-1290
interface SkillsCaseResult {
  id: string;
  type: "static" | "behavioral";
  passed: boolean;
  skipped?: boolean;             // true only when no endpoint configured
  shouldTriggerAxis?: AxisVerdict;
  nearMissAxis?: AxisVerdict;
  isControl?: boolean;
  errored?: boolean;             // case-level STRUCTURAL failure only
                                  // (bad skillDir/querySetPath) — NEVER set
                                  // by a network/endpoint failure; do not
                                  // confuse with the derived runsErrored
                                  // sum below (research.md §2)
}
```

**Derived field this mission's tooling computes (does not exist in
muster's own JSON)**:

```
runsErrored(case) =
  sum(case.shouldTriggerAxis.queryBreakdown[].runsErrored) +
  sum(case.nearMissAxis.queryBreakdown[].runsErrored)
```

This is the only field that distinguishes a healthy-and-discriminating
control (`runsErrored(case) === 0`) from a dead-endpoint run producing a
shape-identical `passed: false` (`runsErrored(case) > 0`, in fact equal to
`runsPerQuery * (shouldTrigger.length + nearMiss.length)` when the endpoint
is fully unreachable — every call fails, research.md §2).

## Evidence Artifact (authored shape, committed by the cadence workflow)

`conformance/skills/trigger-evidence/<run-timestamp>.json`
(`<run-timestamp>` = the workflow run's own ISO-8601 timestamp with `:`
replaced by `-` for filesystem safety):

```json
{
  "timestamp": "2026-07-31T14:02:00Z",
  "model": "gpt-4o-mini",
  "endpointHost": "api.openai.com",
  "cases": [
    {
      "id": "spk-run-next",
      "isControl": false,
      "passed": true,
      "shouldTrigger": { "triggerRate": 0.92, "threshold": 0.5, "passed": true },
      "nearMiss":      { "triggerRate": 0.08, "threshold": 0.5, "passed": true },
      "runsErrored": 0
    },
    {
      "id": "rigged-impossible-control",
      "isControl": true,
      "passed": false,
      "shouldTrigger": { "triggerRate": 0.0, "threshold": 0.5, "passed": false },
      "nearMiss":      { "triggerRate": 0.0, "threshold": 0.5, "passed": true },
      "runsErrored": 0
    }
  ]
}
```

Field obligations (FR-005, NFR-002, NFR-003):

- `endpointHost` is a **bare host** (`new URL(MUSTER_ENDPOINT).host`) —
  never the full URL, never a query string, never a credential. NFR-002's
  grep guard additionally scans this file for `sk-`/`api[_-]?key=`-shaped
  substrings.
- `runsErrored` is present per case (the derived sum above), as its own
  field distinct from `triggerRate` — NFR-003's requirement that a
  `runsErrored>0, triggerRate:0` case is visually distinguishable from a
  `runsErrored:0, triggerRate:0` case is satisfied by this field's mere
  presence and non-omission (a script that computed the sum but then
  dropped it before serializing would violate NFR-003 even though it
  "used" the right data internally).
- `model` records **whichever model actually produced the run** (the
  manifest's pinned default, or `MUSTER_MODEL` if it was set to override
  for iteration) — never silently defaulted to the manifest's static text
  if the run used something else (spec.md FR-003).
- The schema is formalized in `contracts/evidence-artifact.schema.json`.

## Duplicate Pair / Run-Family Cluster (declared relationship, consumed by `check-twin-phrasing.mjs`)

Not a file of its own — a small in-repo declaration (e.g. a constant array
in `check-twin-phrasing.mjs`, or a tiny `conformance/skills/clusters.yaml`
if the script benefits from separating data from logic; deferred to tasks
phase which one) of:

```yaml
duplicatePairs:
  - [ad-hoc-profile-load, spk-doctrine-profile-load]
  - [spec-kitty-runtime-next, spk-run-next]
  - [spec-kitty-runtime-review, spk-run-review-wp]
  - [spec-kitty-implement-review, spk-run-implement-review]
  - [spec-kitty-git-workflow, spk-admin-git-workflow]
runFamily:
  - [spk-run-next, spk-run-review-wp, spk-run-implement-review]
```

`check-twin-phrasing.mjs` walks this declaration, and for each pair/triple
loads the relevant `*-duplicate-pair-queries.yaml` /
`*-run-family-queries.yaml` files by the naming convention in
research.md §8, asserting the cross-reference condition (FR-002) — never
by walking the manifest's case list itself, so the check remains meaningful
even if a manifest case is temporarily commented out during authoring.

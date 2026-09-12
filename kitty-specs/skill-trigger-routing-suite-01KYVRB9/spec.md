# Mission Specification: Skill Trigger-Routing Conformance Suite

**Mission Branch**: `main` (single-branch topology — this repo's `branch-context`
resolver returned `current_is_primary: false`, `recommended_strategy: stay`;
mission artifacts commit directly to `main`, no dedicated feature branch)
**Created**: 2026-07-31
**Status**: Draft
**Input**: MOES-Media/spec-kitty issue https://github.com/MOES-Media/spec-kitty/issues/25
("[M6] skill-trigger-routing-suite — trigger-routing conformance for
confusable legacy/spk skill clusters"), programme: muster ⇄ Spec Kitty
agent-conformance programme, wave 2 (authoring).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prove or disprove routing for the highest-confusion pairs (Priority: P1)

A programme maintainer suspects that five legacy/spk duplicate skill pairs —
`ad-hoc-profile-load`↔`spk-doctrine-profile-load`,
`spec-kitty-runtime-next`↔`spk-run-next`,
`spec-kitty-runtime-review`↔`spk-run-review-wp`,
`spec-kitty-implement-review`↔`spk-run-implement-review`,
`spec-kitty-git-workflow`↔`spk-admin-git-workflow` — are indistinguishable to
Claude Code's own skill-routing machinery, because their names and
descriptions overlap. They want machine-checked evidence, not opinion: a
should-trigger query set and a near-miss query set per skill, run against a
real model, with the near-miss set for each skill deliberately including its
twin's should-trigger phrasing (the sharpest available discrimination test).

**Why this priority**: this is the entire reason the mission exists — without
this, "these skills might be confusable" stays a hunch.

**Independent Test**: run
`npx --offline @garrison-hq/muster@1.2.1 skills run conformance/skills/behavioral-manifest.yaml --json`
against a configured `MUSTER_ENDPOINT` and inspect the per-case
`shouldTriggerAxis.triggerRate` / `nearMissAxis.triggerRate` for any one
duplicate-pair case. This is testable and demonstrates value in isolation of
the run-family cluster (User Story 2).

**Acceptance Scenarios**:

1. **Given** a behavioral manifest case for `spec-kitty-runtime-next` whose
   near-miss set contains phrasing drawn from `spk-run-next`'s should-trigger
   set, **When** `skills run` executes it against the pinned model, **Then**
   the JSON report's `nearMissAxis.triggerRate` for that case is the
   discrimination signal — a high rate is a genuine, reportable routing
   defect (or evidence the duplicate pair should not both exist), not a
   grader bug.
2. **Given** a query set with only 6 should-trigger queries authored by
   mistake, **When** `skills run` executes that case, **Then** the case
   report shows `passed: false` with both axes zeroed
   (`triggerRate: 0`, `queryBreakdown: []`) — the hard gate at
   `trigger.ts:403-422` (muster commit `16f0d34c3126fab5df2ee0b6e1e304a4d9bcb8e3`,
   tag `v1.2.1`), never a partial grade.

---

### User Story 2 - Detect within-family confusion in the run-family cluster (Priority: P2)

The same maintainer wants to know whether `spk-run-next`, `spk-run-review-wp`,
and `spk-run-implement-review` — three skills in the same naming family with
adjacent responsibilities — are distinguishable from each other, not just
from their legacy twins.

**Why this priority**: this is real routing risk (three similarly-named
skills competing for the same class of request) but is secondary to the
duplicate-pair evidence in User Story 1, which the programme is explicitly
blocked on upstream decisions for.

**Independent Test**: run the same `skills run` invocation and inspect the
three run-family cases' near-miss axes for cross-contamination (e.g.
`spk-run-next`'s near-miss set contains `spk-run-review-wp` should-trigger
phrasing and vice versa).

**Acceptance Scenarios**:

1. **Given** the three run-family query sets, **When** `skills run` executes
   all three cases, **Then** each case's near-miss set is confirmed (by a
   loader script, not by eyeballing YAML) to contain at least one phrase
   drawn from each of the other two skills' should-trigger sets.

---

### User Story 3 - The grader must prove it can fail (Priority: P1)

Before trusting any trigger rate, the maintainer needs to see the grader
actually fail on a case engineered to be impossible to pass — otherwise a
model that always calls the tool (or a dead endpoint that always reports
"triggered") would look identical to a healthy, discriminating suite.

**Why this priority**: this is the discrimination-control requirement the
whole programme's charter binds every grader to; without it the other two
user stories produce numbers nobody can trust.

**Independent Test**: run `skills run` and confirm the `isControl: true` case
is present in the JSON report with `passed: false`, `runsErrored: 0` (a
control that fails because every run genuinely executed and was graded, not
because the endpoint died), for both the offline static path and one real
`MUSTER_ENDPOINT` invocation.

**Acceptance Scenarios**:

1. **Given** the manifest's rigged-impossible control case, **When**
   `skills run` executes it against a live, healthy endpoint, **Then** the
   case report shows `passed: false` and `runsErrored: 0`.
2. **Given** the same control case, **When** `MUSTER_ENDPOINT` points at an
   unreachable host, **Then** the case report shows `passed: false` **and**
   `runsErrored > 0` — this is the rejection case that distinguishes a
   discriminating control from a dead endpoint producing a shape-identical
   verdict (garrison-hq/muster#76).

---

### Edge Cases

- What happens when a query set's `shouldTrigger` or `nearMiss` array has
  fewer than 8 entries? → Hard gate fires: `passed: false`, both axes zeroed,
  regardless of what a live model would have done (`trigger.ts:403-422`).
- What happens when `MUSTER_ENDPOINT` is unset entirely? → `skills run`
  records every `type: behavioral` case as `{passed: true, skipped: true}`
  (muster `src/cli/index.ts` `resolveSkillsBehavioralEndpoint` /
  `doSkillsRun`, unchanged in this mission) — a green report under these
  conditions verifies nothing about routing and must never be the evidence
  committed for FR-005.
- What happens when the endpoint is reachable but every run errors (e.g.
  wrong model name)? → Each case's `runsErrored` is nonzero; an errored run
  is counted as a non-trigger, never skipped, never silently a 0
  (muster's own upstream errored-run-counting behavior, unrelated to and
  outside this mission's own FR/NFR/C numbering below) — the evidence
  artifact (FR-005) must surface
  `runsErrored` per case so a 0% trigger rate caused by breakage is never
  misread as a 0% trigger rate caused by good discrimination.
- What happens to the process exit code when the required control case fails
  as designed? → `skills run` returns `ok ? 0 : 1` (muster `src/cli/index.ts`,
  `doSkillsRun`, exit 2 reserved for manifest read/parse errors or an
  uncaught exception) — a healthy run **including its required control**
  legitimately exits 1, because the control is a failed case by design
  (garrison-hq/muster#77). No acceptance command in this spec asserts on the
  bare exit code; each inspects the JSON report's per-case fields instead.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Duplicate-pair and run-family query sets, ≥8 per axis | User Story 1, 2 | High | Open |
| FR-002 | Near-miss sets contain the twin's should-trigger phrasing | User Story 1, 2 | High | Open |
| FR-003 | Behavioral manifest pinned to model, runsPerQuery, threshold | User Story 1 | High | Open |
| FR-004 | One rigged-impossible control per manifest, observed failing | User Story 3 | High | Open |
| FR-005 | Cadence workflow with committed per-run evidence artifact | User Story 1, 2, 3 | High | Open |
| FR-006 | Discovered routing defects filed as SK issues, indexed in README | User Story 1, 2 | Medium | Open |

**FR-001** — Query sets live under `conformance/skills/trigger-queries/`, one
YAML file per skill under test, shaped like
`fixtures/skills/trigger-queries/weather-skill-queries.yaml` in
`garrison-hq/muster` (`id`, `source`, `threshold`, `shouldTrigger[]`,
`nearMiss[]`) — confirmed present at muster `16f0d34c3126fab5df2ee0b6e1e304a4d9bcb8e3`
(tag `v1.2.1`) with 10 entries per axis. Covers, at minimum, the ten skills in
the five duplicate pairs plus the three run-family skills (13 query-set files
minimum).
- **Verification command**: `node conformance/scripts/check-trigger-queryset-shape.mjs conformance/skills/trigger-queries/*.yaml`
  (new script, this mission's own lane-b deliverable) exits 0 when every file
  has ≥8 `shouldTrigger` entries and ≥8 `nearMiss` entries and all five
  required fields.
- **Falsification condition**: a fixture with 7 `shouldTrigger` entries must
  make the script exit 1 (not 0) — the rejection case to actually construct
  and run before FR-001 is marked done, per this programme's nine-vacuous-check
  history.
- **Normative citation**: hard gate at `trigger.ts:403-422`
  (`querySet.shouldTrigger.length < MIN_QUERIES_PER_AXIS || querySet.nearMiss.length < MIN_QUERIES_PER_AXIS`,
  constant `MIN_QUERIES_PER_AXIS = 8` at `trigger.ts:66`), muster commit
  `16f0d34c3126fab5df2ee0b6e1e304a4d9bcb8e3` (tag `v1.2.1`). **Not**
  `trigger.ts:360-379` as issue #25 states — that range is the
  endpoint/model config block, unrelated to the axis-count gate.

**FR-002** — For each of the five duplicate pairs and each ordered pair
within the run-family cluster, the near-miss set of skill A contains at
least one phrase drawn from skill B's should-trigger set (and vice versa).
This convention does not yet exist in muster's shipped rubric
(`docs/rubric/skills-trigger-taxonomy.md` at `v1.2.1` has no "twin" language —
confirmed by direct search) — see Decision D-1 below for how this mission
resolves that gap.
- **Verification command**:
  `node conformance/scripts/check-twin-phrasing.mjs conformance/skills/trigger-queries/`
  (new script) exits 0 when, for every declared pair, at least one near-miss
  string in A's file is byte-identical to a should-trigger string in B's file
  (and symmetrically).
- **Falsification condition**: a pair where A's near-miss set is populated
  but shares zero strings with B's should-trigger set must exit 1.
- **Normative citation**: issue #25 §2 ("each skill's near-miss set contains
  its twin's should-trigger phrasing — the sharpest available discrimination
  between overlapping surfaces").

**FR-003** — One `conformance/skills/behavioral-manifest.yaml`
(does not yet exist — confirmed by direct listing of `conformance/skills/`,
which today holds only the pre-existing `manifest.yaml` static suite and
`control/`) with:
- `runsPerQuery: 3`, `threshold: 0.5` (issue #25 §5, FR-003, carried forward
  unchanged — both values match muster's shipped default expectations in
  `docs/rubric/skills-trigger-taxonomy.md`).
- `model: gpt-4o-mini` pinned explicitly in the manifest's default config
  block (issue #25 omits a model pin entirely; `gpt-4o-mini` is the same
  default muster's own `resolveSkillsBehavioralEndpoint` falls back to when
  `MUSTER_MODEL` is unset, so pinning it in the manifest keeps the committed
  evidence artifact reproducible even if that muster default ever changes).
  `MUSTER_MODEL` may override at run time for iteration against a local
  model; the committed evidence artifact (FR-005) always records whichever
  model actually produced it.
- Tools built from each SKILL.md's `name` + `description` frontmatter (the
  actual routing surface Claude Code matches on) — one tool per case, per
  muster's existing `TriggerCase.tools: ToolDefinition[]` shape
  (`trigger.ts:122` et al., same SHA).
- Credentials via `MUSTER_API_KEY`-style environment variable only — never a
  literal key in the manifest or workflow file, never a repo-local `.env`
  (NI-001 scans the whole tree including gitignored files).
- **Failure policy**: if `MUSTER_ENDPOINT`/`MUSTER_API_KEY` are unset, the
  cadence workflow step is expected to produce muster's own graceful-skip
  shape (`{passed: true, skipped: true}` per case) — the workflow must
  additionally assert `skipped !== true` on at least one non-control case
  before treating a green run as evidence (see FR-005), otherwise a run with
  no credentials configured would silently pass as if it had tested routing.
- **Verification command**:
  `MUSTER_ENDPOINT=<test-endpoint> npx --offline @garrison-hq/muster@1.2.1 skills run conformance/skills/behavioral-manifest.yaml --json | node -e "const r=JSON.parse(require('fs').readFileSync(0)); process.exit(r.results.some(c=>c.type==='behavioral' && c.skipped) ? 1 : 0)"`
  exits 0 only when no behavioral case was skipped. (Corrected during WP04:
  muster's real `skills run --json` top-level shape is
  `{ok, total, passed, failed, skipped, results}` — there is no top-level
  `cases` key. The original `r.cases.some(...)` throws at runtime and,
  because a thrown Node script also exits non-zero, coincidentally still
  satisfies "exits 1" for the unset-endpoint case — but for the wrong
  reason, and would not distinguish a real skip from a script crash.)
- **Falsification condition**: running the same command with `MUSTER_ENDPOINT`
  unset must make this check exit 1 (every case skipped) — construct and run
  this rejection case, not just describe it.
- **Normative citation**: k-of-n aggregation rationale, `trigger.ts:26-31`
  (module doc comment), same SHA — confirmed unchanged, this citation from
  issue #25 is correct as stated.

**FR-004** — Exactly one `isControl: true` case per manifest (rigged-impossible
description pattern, following muster's own
`fixtures/skills/trigger-queries/rigged-impossible-queries.yaml` shape,
same SHA) — but **not** copied verbatim: muster's own `fixtures/` copy of
this fixture has a known defect (near-miss axis self-matches the literal
`ZZZCONTROL` placeholder token against a description that also contains
`ZZZCONTROL`, garrison-hq/muster#73) that over-determines its
`passed: false` and proves nothing about the grader. This mission's control
must follow the pattern muster's own `examples/` copy uses instead (rewritten
specifically to avoid this self-match, per the same issue).
- **Verification command**: run the manifest against a live, reachable
  endpoint and assert (from the JSON report) `isControl === true`,
  `passed === false`, **and** `runsErrored === 0` for that case — `runsErrored
  === 0` is what distinguishes real discrimination from a dead endpoint
  producing a shape-identical `passed: false` (garrison-hq/muster#76).
- **Falsification condition**: point `MUSTER_ENDPOINT` at an unreachable host
  and re-run — the control case must then show `passed: false` **with**
  `runsErrored > 0`, and the cadence workflow's inversion step (see FR-005)
  must distinguish this from the healthy case, not treat both as equivalent
  "control failed as expected" outcomes.
- **Normative citation**: issue #25 §8 ("Discrimination control... why it
  must fail: trigger grading is statistical; without a rigged case a
  permanently-triggering model+prompt combination would look like a healthy
  suite") plus garrison-hq/muster#73 and garrison-hq/muster#76 for the two
  ways a naive control implementation is satisfiable without discriminating
  anything.

**FR-005** — A `workflow_dispatch`-triggered GitHub Actions workflow (schedule
wiring deferred to M8, garrison-hq/muster-action#2 per issue #25's scope
guard) that runs `skills run` against the pinned manifest and commits a
per-run evidence artifact to the repo (not left only in workflow logs or PR
prose) at `conformance/skills/trigger-evidence/<run-timestamp>.json`
containing, at minimum: per-axis trigger rates per case, `runsErrored` per
case, the model actually used, the endpoint **host** (never the key or full
URL with credentials), and an ISO-8601 timestamp.
- **Verification command**: `node conformance/scripts/check-evidence-artifact-shape.mjs conformance/skills/trigger-evidence/<file>.json`
  (new script) exits 0 when every required field is present and the endpoint
  field contains no `@` (crude but effective credential-leak guard: a bare
  host has no `user:pass@` or query-string token) and no substring matching
  a `MUSTER_API_KEY`-shaped value.
- **Falsification condition**: an evidence file recording only prose
  ("suite passed") with no per-axis rates, or one where the endpoint field
  is a full URL with an embedded API key query parameter, must make the
  script exit 1. This is the exact failure mode a sibling mission hit
  (a control recorded at "0/24" in prose that re-measured at "4/24" because
  its evidence lived in prose, never in a structured artifact) — construct
  a prose-only evidence file and confirm the check rejects it before
  marking FR-005 done.
- Never runs on `pull_request` (C-002).

**FR-006** — Any duplicate-pair or run-family case whose near-miss axis
trigger rate exceeds its threshold (a genuine routing defect, or evidence the
duplicate pair itself is the defect) is filed as a spec-kitty GitHub issue
against `MOES-Media/spec-kitty`, with the failing query-set file attached or
linked, and indexed by URL in this suite's README. No SKILL.md is edited to
"fix" the finding in this mission (scope guard, issue #25 §4) — muster
reports, it does not rewrite.
- **Verification command**: manual for this mission (filing issues is a
  post-execution action gated on M5's release being consumed by a real run);
  the README's index format is validated by
  `command grep -c 'github.com/MOES-Media/spec-kitty/issues/' conformance/skills/README.md`
  returning a nonzero count once at least one finding exists.
- **Falsification condition**: a README with a "Findings" section header but
  zero linked issue URLs underneath it must not be accepted as satisfying
  FR-006.

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Offline static path unaffected | Adding `conformance/skills/behavioral-manifest.yaml` and `trigger-queries/**` must not change any byte of the existing offline `skills run conformance/skills/manifest.yaml` static-path output (diff of `--json` output before/after this mission's changes, on the static manifest only, is empty) | Reliability | High | Open |
| NFR-002 | Credentials never in committed files | `command grep -rE '(sk-|api[_-]?key\s*[:=]\s*["\047][A-Za-z0-9]{16,})' conformance/skills/behavioral-manifest.yaml .github/workflows/skill-trigger-routing.yml` exits 1 (no match) at every commit in this mission | Security | High | Open |
| NFR-003 | Errored runs never silently zero | Every evidence artifact (FR-005) records `runsErrored` per case as a field distinct from `triggerRate`; a case with `runsErrored > 0` and `triggerRate: 0` must be visually distinguishable in the artifact from a case with `runsErrored: 0` and `triggerRate: 0` | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Diff scope | Diff touches only `conformance/skills/trigger-queries/**`, `conformance/skills/behavioral-manifest.yaml`, `conformance/skills/trigger-evidence/**`, `conformance/scripts/check-trigger-*.mjs`, one workflow file, and `conformance/skills/README.md` — no `SKILL.md` under `src/doctrine/skills/` is edited (verify: `git diff --stat main -- src/doctrine/skills/` is empty at merge) | Technical | High | Open |
| C-002 | No `pull_request` trigger, secrets by env only | The workflow file's `on:` block contains no `pull_request` key (verify with a YAML parse, not a text grep of the `on:` block alone — this programme has previously shipped a check that read `on:` but never the job body; here the risk is the reverse, a workflow with `pull_request` present is the rejection case to construct and confirm the parser catches) | Technical | High | Open |
| C-003 | muster version pin | `@garrison-hq/muster` is pinned to exactly `1.2.1` (not a range, not a SHA) everywhere it is invoked in this mission's workflow and README — `command grep -c '@garrison-hq/muster@1\.2\.1' .github/workflows/skill-trigger-routing.yml conformance/skills/README.md` returns the expected count; `command grep -c '@garrison-hq/muster@\^' <same files>` must return 0 | Technical | High | Open |

### Charter Directives Binding This Mission (hand-enumerated — not in `charter.yaml`)

`charter.yaml`'s `directives:` array contains only `DIR-001` through
`DIR-013`, **all** `severity: warn` (confirmed via both direct `grep` and
`spec-kitty charter context --action specify --json`'s `all_directives`
list — 13 entries, no `C-0xx` IDs). The binding `C-0xx` directives exist only
as prose in `.kittify/charter/charter.md` and are **not** discoverable by
walking `charter.yaml` alone. They are enumerated here by hand, per this
programme's repeated finding that a charter table built by walking
`charter.yaml` reproduces this same omission:

- **C-003** (`charter.md:~469`) — Mission B dual-read: legacy + new homes
  listed together where relevant. Not directly applicable to this mission
  (no dual-homed identifier is being introduced), noted for completeness.
- **C-004** (`charter.md:481`) — Burn-down Policy (HiC §5a.2). Not directly
  applicable — this mission adds new query sets, it does not burn down an
  existing deprecation list.
- **C-007** (`charter.md:494`) — `__all__` Declaration Convention, scoped to
  `src/charter/` and `src/kernel/`. Not applicable — this mission's deliverables
  live under `conformance/` and `.github/workflows/`.
- **C-011** (`charter.md:504`) — **ATDD-First Discipline, binds this mission.**
  Every WP's coding cannot start until a failing-first ATDD test exists
  pinning the user-observable behavior, committed as its own commit (often
  the lane's first commit) before any implementation commit. The reviewer
  verifies RED on the WP's `planning_base_branch` and GREEN on its final
  commit. For this mission, the ATDD tests are the verification commands
  under each FR above (e.g. FR-001's query-shape checker, FR-004's
  live-endpoint-vs-dead-endpoint control assertion) — each must be committed
  failing against an empty/placeholder fixture before the real query sets or
  manifest are authored. C-011 outranks all DIR-0xx (warn-only) when the two
  would conflict.

### Key Entities

- **Trigger Query Set**: one YAML file per skill under test — `id`, `source`
  (rubric doc path), `threshold`, `shouldTrigger[]` (≥8 phrases expected to
  invoke the skill), `nearMiss[]` (≥8 phrases expected not to, including the
  twin's should-trigger phrasing for duplicate/cluster pairs).
- **Behavioral Manifest Case**: one entry in `behavioral-manifest.yaml` —
  references a query set, a skill's `name`+`description` (built into a tool
  definition), `runsPerQuery`, `threshold`, and an `isControl` flag for
  exactly one entry.
- **Trigger Verdict**: muster's own output shape per case — `id`, `passed`,
  `shouldTriggerAxis`/`nearMissAxis` (each with `triggerRate`, `threshold`,
  `passed`, `queryBreakdown`), `isControl`. This mission does not change this
  shape; it only produces inputs to it and persists a summarized evidence
  artifact derived from it.
- **Evidence Artifact**: one committed JSON file per cadence run — per-case
  axis rates, `runsErrored`, model, endpoint host, timestamp.
- **Duplicate Pair / Run-Family Cluster**: a declared relationship between
  two or three skill directories under `src/doctrine/skills/`, used by the
  twin-phrasing check (FR-002) to know which should-trigger set to borrow
  near-miss phrases from.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every one of the 5 duplicate pairs and the 3-member run-family
  cluster (13 skills total) has a committed, shape-valid query set with ≥8
  entries per axis, verifiable by a single script run in under 5 seconds.
- **SC-002**: A cadence run against a real model produces a committed
  evidence artifact whose discrimination-control case shows `runsErrored: 0`
  and `passed: false` — proof the grader can fail for the right reason, not
  just fail.
- **SC-003**: For at least one duplicate pair, the committed evidence
  artifact's near-miss trigger rate is high enough to constitute a
  reportable finding (or low enough to constitute reportable evidence the
  pair is well-discriminated) — either outcome is success; a manifest that
  produces no signal either way (all zeros because credentials were never
  configured) is not.
- **SC-004**: Zero `SKILL.md` files under `src/doctrine/skills/` are modified
  by this mission's diff.

## Scope Guard

Explicitly out of scope for this mission (issue #25 §4, carried forward
unchanged):

- Editing any `SKILL.md` to fix a discovered routing defect. Findings are
  filed as spec-kitty GitHub issues only (FR-006); the suite reports, it
  does not remediate.
- Covering all 53 skills in the existing static manifest. Clusters first
  (the 5 duplicate pairs + 3-member run-family cluster = 13 skills);
  breadth is a future mission, driven by evidence from this one.
- PR gating on this workflow's results (cost — deferred, no owning mission
  yet named in issue #25).
- Action/schedule plumbing to turn `workflow_dispatch` into a real cron
  cadence — that is M8 (garrison-hq/muster-action#2).
- This mission is spec-agnostic-core-compliant by construction: it adds no
  code to `src/core/` or `src/adapters/` in either repo; it only authors
  YAML fixtures, a workflow file, and small Node verification scripts that
  consume muster's published CLI (`@garrison-hq/muster@1.2.1`) as an
  external dependency. NI-002 (core never imports adapters) is therefore
  not at risk from this mission's own diff.

## Lanes (non-overlapping `write_scope`)

- **lane-a** — `write_scope: ["conformance/skills/trigger-queries/**"]`
  - WP01: the five duplicate-pair query sets (10 files) + twin-phrasing
    cross-references between each pair.
  - WP02: the three run-family query sets + twin-phrasing cross-references
    across all three (each borrows near-miss phrasing from the other two).
- **lane-b** — `write_scope: ["conformance/skills/behavioral-manifest.yaml", "conformance/scripts/check-trigger-queryset-shape.mjs", "conformance/scripts/check-twin-phrasing.mjs", "conformance/scripts/check-evidence-artifact-shape.mjs", ".github/workflows/skill-trigger-routing.yml", "conformance/skills/README.md"]`
  - WP03: manifest, verification scripts, workflow, and README, including the
    rigged-impossible control case and its two verification runs
    (live-healthy and dead-endpoint).

No collisions: lane-a never writes to the manifest, scripts, workflow, or
README; lane-b never writes query-set YAML. lane-b's WP03 depends on lane-a's
WP01/WP02 output existing (the manifest references query-set file paths by
name) — this dependency must be declared explicitly in `wps.yaml` at the
tasks phase, covering every file the manifest transitively references, per
this programme's repeated finding that under-declared `dependencies` have
caused wrong-worktree resolution via `resolve_workspace_for_wp()`.

## Normative Citations

| Claim | Citation | Pin |
|---|---|---|
| 8-minimum-per-axis hard gate | `src/adapters/skills/trigger.ts:403-422`, constant at `:66` | `garrison-hq/muster@16f0d34c3126fab5df2ee0b6e1e304a4d9bcb8e3` (tag `v1.2.1`) |
| k-of-n aggregation rationale | `src/adapters/skills/trigger.ts:26-31` | same SHA |
| Query-set fixture shape | `fixtures/skills/trigger-queries/weather-skill-queries.yaml` | same SHA |
| Trigger-testing methodology, 8-10/axis upstream guidance, `[MUSTER-OWN]` divergences | `docs/rubric/skills-trigger-taxonomy.md` (resolves OQ-1: real upstream is `agentskills.io/skill-creation/optimizing-descriptions`, not the originally-cited fabricated fragment) | same SHA |
| Rigged-impossible near-miss self-match defect | `github.com/garrison-hq/muster/issues/73` | issue, open |
| `expectations.violations` parsed-not-compared | `github.com/garrison-hq/muster/issues/74` | issue, open |
| Live control satisfiable by dead endpoint | `github.com/garrison-hq/muster/issues/76` | issue, open |
| `isControl` exit-code semantics inverted across adapters | `github.com/garrison-hq/muster/issues/77` | issue, open |
| Single-tool bias caps should-trigger discriminative power | `github.com/garrison-hq/muster/issues/82` | issue, open |
| Exit-code contract (`ok ? 0 : 1`, exit 2 reserved for manifest errors) | `src/cli/index.ts` `doSkillsRun` (~line 1584 for the 0/1 return; error path ~line 1496 catch) | same SHA |
| Charter ATDD-first binding | `.kittify/charter/charter.md:504` (this repo, `spec-kitty-conformance-m6` clone at `c36b727cf`) | commit `c36b727cf` |

## Live-Model Plan

- **Model**: `gpt-4o-mini`, pinned explicitly in `behavioral-manifest.yaml`'s
  default config (matches muster's own unset-`MUSTER_MODEL` fallback, so the
  pin is redundant-but-explicit rather than silently inherited).
- **`runsPerQuery`**: `3` (issue #25 FR-003, unchanged).
- **Threshold**: `0.5` (issue #25 FR-003, unchanged) — a query passes its
  axis if `runsTriggered / runsTotal >= 0.5`, aggregated across all queries
  in the axis (muster's axis-level pooling, `[MUSTER-OWN]` per the rubric).
- **Credentials**: `MUSTER_API_KEY` (or whatever env var
  `effectiveApiKeyEnv("MUSTER_API_KEY")` resolves to at the pinned SHA) —
  environment variable only, injected as a GitHub Actions secret at workflow
  run time, never written to any file in this repo, no `.env` created.
- **Endpoint**: `MUSTER_ENDPOINT`, also environment-injected; the committed
  evidence artifact records only the endpoint's **host**, never the full URL
  or key.
- **Failure policy**: if the endpoint is unreachable, cases show
  `runsErrored > 0` and are counted as non-triggers, never skipped
  (muster's own upstream behavior, unchanged, unrelated to and outside this
  mission's own FR/NFR/C numbering below); if credentials are entirely unset,
  muster's CLI degrades every behavioral case to `{passed: true, skipped:
  true}` — this mission's workflow must assert at least one non-control case
  is `skipped !== true` before treating a run's exit code as meaningful
  (this is the FR-003 verification command above). A run where the control
  case reports `runsErrored > 0` must be treated as an infrastructure failure
  of the run, not as a valid "control fails as expected" data point, and
  must not be committed as evidence for SC-002.

## Dependencies

- **Hard blocker for execution** (not authoring): M5, garrison-hq/muster#59.
  **Status update**: this is resolved — `@garrison-hq/muster@1.2.1` is
  published on the npm registry (confirmed via `npm view`) and its git tag
  `v1.2.1` (`16f0d34c3126fab5df2ee0b6e1e304a4d9bcb8e3`) contains M5's
  `docs/rubric/skills-trigger-taxonomy.md` and the `runTriggerConformance`
  hard gate. FR-001/FR-002 (query-set authoring) can proceed immediately;
  FR-003/FR-004/FR-005 (live execution) can now also proceed — this removes
  the execution blocker issue #25 described as still-pending.
- M1, MOES-Media/spec-kitty#22 (directory + CI skeleton) — **resolved during
  this spec's authoring**: M1's work is done and merged (commit `08930a32b`,
  squash-merge of mission `sk-skills-static-conformance-01KYG7GE`, which
  authored the 53-case static manifest and the FR-005 discrimination-control
  fixture — exactly what M1/issue #22 describes), even though
  MOES-Media/spec-kitty#22 itself remains **open, unclosed** on GitHub — a
  tracker bookkeeping gap (this fork's spec-kitty bookkeeping is known to
  under-report merged missions as still-open/planned), not a real blocker.
  `conformance/` is confirmed scaffolded and this dependency is satisfied.
- Unblocks: M8 (garrison-hq/muster-action#2), M9 (garrison-hq/muster#60).

## Decisions

- **D-1 — Where does the twin-phrasing convention (FR-002) live?**
  Recommended and adopted: land it as a small addendum to muster's
  `docs/rubric/skills-trigger-taxonomy.md` (a separate, small PR to
  `garrison-hq/muster`, out of this mission's own diff scope but tracked as
  a dependency note), per issue #25 §9's own stated default. Rationale: the
  convention is methodology, not suite-specific policy — a future mission
  authoring query sets for a different confusable cluster should inherit it
  without re-deriving it from this suite's README. Until that muster PR
  lands, this suite's own README documents the convention inline, tagged
  `[CONVENTION]`, per the issue's fallback option.
- **D-2 — Model pin.** `gpt-4o-mini`, per the Live-Model Plan above — issue
  #25 left this unpinned; no reasonable default existed inside the issue
  text, but muster's own CLI default made the choice unambiguous once
  checked.
- **D-3 — Rigged-impossible control source.** Follow muster's `examples/`
  copy of the rigged-impossible fixture, not `fixtures/` — the latter has a
  live, open, self-match defect (garrison-hq/muster#73) that this mission
  must not inherit.

## Open Questions

- **OQ-A (was issue #25's OQ-1)** — Resolved during this spec's authoring,
  not left open: `docs/rubric/skills-trigger-taxonomy.md` already exists at
  `v1.2.1` and its own text states it resolves the original OQ-1. No action
  needed in this mission beyond citing the resolved doc.
- **OQ-B (was issue #25's OQ-5)** — Expected-fail support in muster
  manifests. Recommended option: (a), the CI-inversion pattern (this
  mission's own FR-004 control-assertion step uses it directly, and M8's
  FR-004 is the same pattern). Revisit only if inversion steps proliferate
  past ~3 workflows across the programme.
- **OQ-C (was M1 merge-status uncertainty)** — Resolved during this spec's
  authoring, not left open: see Dependencies section above (decision
  `01KYVRGR9MVG1BXY2SAPTS262T`). M1 is done and merged; only its tracking
  issue is stale.

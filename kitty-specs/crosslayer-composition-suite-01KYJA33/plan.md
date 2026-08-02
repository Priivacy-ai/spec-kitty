# Implementation Plan: Crosslayer Composition Suite (M7)

**Branch**: `kitty/mission-crosslayer-composition-suite` | **Date**: 2026-07-27 | **Spec**: [kitty-specs/crosslayer-composition-suite-01KYJA33/spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/crosslayer-composition-suite-01KYJA33/spec.md`

**Note**: This plan does not decompose into tasks or materialize work-package
files. `tasks/` remains untouched (`.gitkeep` + `README.md` only). Everything
below labeled "proposed WP" or "lane" is guidance for a later
`/spec-kitty.tasks` phase, not a committed task file.

## Summary

M7 composes a real deployed spec-kitty stack — a projected persona +
`AGENTS.md` policy extract (SOP) + one skill — and runs muster's `crosslayer`
adapter over it: `contradiction-lint.ts` gated on every PR (FR-004/FR-006/
C-001/C-002), `rule-survival.ts` on cadence against a live model (FR-005,
partially blocked on M3). A deterministic, never-graded profile→`Soul.md`
projector (FR-001/FR-002/FR-003) supplies the persona layer. Two work
packages can proceed immediately in parallel (projector; manifests+SOP-extract
+CI); a third is scoped now but cannot start until M3 (PR #30) merges.

## Technical Context

**Language/Version**: Python 3.11+ (`profile2soul.py`, per charter DIR-002);
Bash (drift-check scripts); YAML (composition manifests, GitHub Actions
workflow); no new TypeScript — `contradiction-lint.ts`/`composition.ts`/
`rule-survival.ts` are consumed as the pinned `@garrison-hq/muster@1.1.0`
npm package, never modified by this mission.
**Primary Dependencies**: `garrison-hq/muster-action` (pinned commit SHA,
same pattern `conformance.yml` already uses), Python stdlib only for the
projector (no new runtime dependency — determinism is easier to guarantee
without one; if YAML parsing of `*.agent.yaml` needs a library, reuse
whatever this fork already vendors for agent-profile parsing rather than
adding a new one).
**Storage**: N/A — files only (committed `Soul.md`, `sop-extract.md`,
manifests).
**Testing**: pytest for `profile2soul.py` unit behavior (determinism,
mapping, fabricated-defaults, falsification per FR-001) per charter
DIR-005/DIR-006; **plus** the operator's real-CLI verification requirement —
no WP is acceptance-complete on unit tests alone. Every FR/C row's
Verification cell in spec.md is a real command with a real exit code that
must be observed, not mocked.
**Target Platform**: GitHub Actions `ubuntu-latest` (CI, `crosslayer.yml`)
and any contributor's Linux/macOS dev machine (local verification).
**Project Type**: Single repo, tooling/CI addition — no new service.
**Performance Goals**: N/A. The one measured property is determinism
(byte-identical projector output across runs), not throughput.
**Constraints**: Static path (FR-001–FR-004, FR-006, C-001, C-002) must be
offline/zero-network and never require a secret (mirrors `contradiction-lint.ts`
own purity guarantee). Cadence path (FR-005) requires
`MUSTER_ENDPOINT`/`MUSTER_API_KEY` (or `OPENAI_API_KEY`) from GitHub Actions
repository secrets only — never a manifest value, argv, or log line. Every
`npx --offline` command requires the cache-warm prerequisite (`npm install
--no-save @garrison-hq/muster@1.1.0` once per environment, or CI's
`muster-action` equivalent).
**Scale/Scope**: 2 profiles (`architect-alphonso`, `reviewer-renata`) × 1
skill = 2 static FR-004 cases; 1 discrimination control (flip + neutralize);
up to 3 rule-survival cases (045, 029, 1 engineered erosion control) once
FR-005 unblocks — all inside the Scope Guard's 2×2 ceiling, not at it.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against `.kittify/charter/charter.yaml`'s directive set:

| Directive | Applicability | Status |
|---|---|---|
| DIR-001 (cross-platform) | Bash drift scripts must run under the shell CI actually uses (`ubuntu-latest`); no Windows-only assumptions. | Pass (bash + Python 3.11+, both cross-platform) |
| DIR-002 (Python 3.11+) | `profile2soul.py` | Pass |
| DIR-005 (tests for new functionality) | `profile2soul.py` needs pytest coverage (determinism, mapping, fabricated-defaults) in addition to the spec's own CLI-level verification commands. | Gate for WP-A: must ship both |
| DIR-006 (type annotations, mypy --strict) | `profile2soul.py` | Gate for WP-A |
| DIR-007 (docstrings for public APIs) | `profile2soul.py`'s public functions | Gate for WP-A |
| DIR-008 (no secrets in code) | FR-005's `MUSTER_ENDPOINT`/`MUSTER_API_KEY` — env-var only, never in manifest/argv/log (spec already states this; carried into WP-B's `crosslayer.yml` and WP-C's case files as a hard constraint) | Gate for WP-B, WP-C |
| DIR-009 (CHANGELOG for breaking changes) | N/A — no public API surface changes; conformance tooling is internal | N/A |
| DIR-010/DIR-011 (ASCII-safe identifiers) | N/A — this mission introduces no slug/identifier generation from user input | N/A |
| DIR-012 (assign tracker issue to HiC before implementing) | Applies to whoever starts implementation from this mission's seed ticket, `MOES-Media/spec-kitty#26` — flagged for the tasks/implement phase, not actionable at plan time | Carried forward, not a plan-phase gate |
| DIR-013 (pre-existing test failures → file an issue first) | Not evaluated in this pass (no test suite was run); carried forward as an implement-phase responsibility | Carried forward |

No violations requiring Complexity Tracking justification — nothing here
adds a project, a repository-pattern layer, or any structure the charter
would flag.

## Project Structure

### Documentation (this mission)

```
kitty-specs/crosslayer-composition-suite-01KYJA33/
├── spec.md              # Input (two review rounds complete)
├── plan.md              # This file
├── .gates/post-spec.json
└── tasks/                # untouched — .gitkeep + README.md only, per "stop after plan"
```

### Source Code (repository root)

```
conformance/
├── DECISIONS.md                        # shared, read cited (D1) — NOT edited by this mission
├── README.md                           # shared — NOT edited by this mission (collision avoidance, see Dependencies)
├── skills/manifest.yaml                # shared, unrelated to this mission — NOT edited
├── scripts/
│   ├── check-manifest-completeness.mjs # shared, M3 also touches — NOT edited by this mission
│   ├── check-persona-drift.sh          # NEW — lane-a (hazard-3 addition, see below)
│   └── check-sop-extract-drift.sh      # NEW — lane-b (FR-007)
├── tools/
│   ├── profile2soul.py                 # NEW — lane-a (FR-001)
│   └── PROJECTION.md                   # NEW — lane-a (FR-002)
└── crosslayer/                         # NEW directory
    ├── README.md                       # NEW — lane-b (this mission's own doc; never conformance/README.md)
    ├── personas/
    │   ├── architect-alphonso.Soul.md  # NEW, committed — lane-a (FR-003)
    │   └── reviewer-renata.Soul.md     # NEW, committed — lane-a (FR-003)
    ├── sop-extract.md                  # NEW — lane-b (FR-007 / OQ-6)
    ├── manifest.yaml                   # NEW — lane-b (FR-004)
    ├── control.yaml                    # NEW — lane-b (FR-006 flip+neutralize)
    ├── fixtures/
    │   └── invalid-persona-missing-key.Soul.md   # NEW — lane-b (C-001)
    └── cases/
        ├── architect-run-skill.yaml    # NEW — lane-b (FR-004 case 1)
        ├── reviewer-run-skill.yaml     # NEW — lane-b (FR-004 case 2)
        ├── rule-survival-045.yaml      # NEW, BLOCKED on M3 — lane-c (FR-005)
        ├── rule-survival-029.yaml      # NEW, BLOCKED on M3 — lane-c (FR-005)
        └── erosion-control-045.yaml    # NEW, BLOCKED on M3 — lane-c (FR-005)

.github/workflows/
└── crosslayer.yml                      # NEW — lane-b (FR-004 CI wiring + FR-005 cadence scaffold)
```

**Structure Decision**: No new top-level project. This is a tooling/CI
addition inside the existing repo, entirely under `conformance/**` (minus
the shared `README.md`), plus one new workflow file — matching C-002's
allow-list exactly.

## Complexity Tracking

*N/A — Charter Check found no violations requiring justification.*

## Implementation Concern Map

> Implementation concerns are not work packages. `/spec-kitty.tasks`
> translates these into executable WPs. Proposed WP/lane names below are
> guidance, matching this fork's own established `lane-a`/`lane-b`/`lane-c`
> convention (see M3's `WP01`/`WP02`/`WP03` precedent) — not committed task
> IDs.

### IC-00 — Reference-computation pre-step: considered and dissolved (post-plan architectural review)

- **Original concern**: FR-001's "frozen defaults table" does not exist
  anywhere yet — not in spec.md, not in D1/`DECISIONS.md`, not in the seed
  ticket `MOES-Media/spec-kitty#26` — it is a deliverable this mission
  authors, not a pre-existing
  citation. The spec's Dependencies section (prior form) read this as
  requiring lane-b's task file to carry lane-a's *literal* projected
  `Soul.md` bytes as inline fixture content (isolated worktrees, content
  must be duplicated, not referenced), and this IC originally proposed a
  tasks-authoring pre-step to freeze the defaults table and hand-compute
  both personas' exact bytes on the mission's coordination branch, before
  either lane's worktree is allocated, so that byte-identical content
  could be pinned into both lane-a's and lane-b's task files.
- **Why it dissolves — checked against muster's actual source, not just
  spec inference** (`composition.ts:281-333`, `contradiction-lint.ts`,
  pinned `624edd6d`): `resolvePersonaLayer` returns only
  `personaDoc.body.trim()` into `layerTexts` — the map
  `contradiction-lint.ts`'s `extractClauses`/`analyseLayerPair` actually
  scans for contradictions. RFC-1 front-matter (`voice`, `interaction`,
  `locale`, the fabricated object `composition`/`profile_overrides`/
  `extensions` blocks, the `profiles` list, the `values`/`safety` blocks)
  never reaches the lint; it is only
  ever consulted, structurally (presence/shape, not specific values), by
  RFC-1 strict-mode resolution. C-003 independently forbids grading any
  fabricated field as evidence. **FR-004's graded surface is therefore
  body text and composed behavior only**, and that body text is
  deterministically derivable by *either* lane directly from the same
  shared, read-only `*.agent.yaml` source per FR-001's mapping — lane-b
  never needs lane-a's output, byte-exact or otherwise.
- **What lane-b actually needs**: (a) `fixturePath` values in its case
  files that agree with lane-a's committed filenames — already fixed by
  this plan's own Project Structure section
  (`conformance/crosslayer/personas/architect-alphonso.Soul.md`,
  `.../reviewer-renata.Soul.md`), requiring no advance computation; and
  (b) a self-authored, RFC-1-valid sandbox persona (never committed to
  lane-a's path) to exercise its own manifest/CI wiring locally — its
  exact bytes are irrelevant, since they are never graded (C-003) and
  never seen by the lint (above). The real content is verified for real,
  automatically, once both lanes are merged: IC-04's static CI job runs on
  every PR against whatever is actually committed at that path, and the
  spec's own mission-level Real-CLI verification requirement re-runs the
  shipped manifest against the shipped personas before acceptance. No
  lane, at any point, needs to hand-compute or pre-guess the other lane's
  byte output.
- **Serialization considered and rejected**: forcing lane-a to merge
  before lane-b's task file is authored (trading away their parallelism)
  would only be justified if lane-b's own implementation-time acceptance
  depended on lane-a's real byte-exact content. It does not (above), so
  serialization buys nothing here and is not adopted — lane-a and lane-b
  remain independently parallel, per the Dependency Graph below.
- **What changed as a result**: spec.md's "Lane isolation" bullet
  (Dependencies & Assumptions) is corrected in place (post-plan review) to
  require path agreement only, not byte duplication. IC-02's
  Sequencing/depends-on note below is updated to match. This entry is
  retained (not deleted) as the auditable record of the concern and its
  resolution, matching this mission's own established convention for
  documenting post-spec/post-plan corrections rather than silently
  overwriting them.

### IC-01 — Profile→Soul.md projector, mapping doc, committed personas (proposed lane-a)

- **Purpose**: Deterministic, byte-stable `*.agent.yaml → Soul.md`
  projection; documents its own field mapping, fabricated-defaults table,
  and fidelity-loss table; commits the two personas this mission needs with
  a drift-checkable regenerate-and-diff pattern.
- **Relevant requirements**: FR-001, FR-002, FR-003.
- **Affected surfaces**: `conformance/tools/profile2soul.py`,
  `conformance/tools/PROJECTION.md`,
  `conformance/crosslayer/personas/architect-alphonso.Soul.md`,
  `conformance/crosslayer/personas/reviewer-renata.Soul.md`,
  `conformance/scripts/check-persona-drift.sh` (new — see risk note below).
- **Sequencing/depends-on**: none. Reads only
  `src/doctrine/agent_profiles/built-in/*.agent.yaml`, a shared read-only
  input owned by neither lane. Runs in parallel with lane-b (IC-02–04).
- **Acceptance evidence** (from spec.md, commands as written there):
  - FR-001: two-run byte-diff, expect exit `0`; falsification (inject
    `time.time_ns()` or unordered dict iteration into a local copy), expect
    exit `1`.
  - FR-002: `grep -A20 "^## Fidelity Loss" conformance/tools/PROJECTION.md`
    pipeline, expect exit `0`; falsification (a Fidelity Loss section that
    wrongly includes `initialization-declaration`), expect exit `1`.
  - FR-003: regenerate + `git diff --exit-code
    conformance/crosslayer/personas/`, expect exit `0` on a clean tree;
    falsification (hand-edit one committed persona byte), expect exit `1`.
- **Risks / hazard-3 note**: FR-003's own Verification cell is only an
  inline two-command sequence, with no dedicated committed script — unlike
  FR-007, which gets `check-sop-extract-drift.sh`. If that CI wiring is
  authored inline inside lane-b's `crosslayer.yml` instead, lane-b (who
  owns that file) becomes the sole party who can fix a broken persona-drift
  CI step, even though the artifact being checked (the persona files, the
  projector) is entirely lane-a's. That is exactly the "enforcer outside
  the write scope of the lane that can fix the enforced thing" shape
  hazard 3 warns about. **Restructuring**: give FR-003 the same pattern
  FR-007 already has — a committed `conformance/scripts/check-persona-drift.sh`
  authored and owned by lane-a, doing the regenerate+diff for both
  personas. Lane-b's `crosslayer.yml` then only contains a one-line call
  site (`bash conformance/scripts/check-persona-drift.sh`), which is thin
  enough that a bug there is very unlikely to be the actual source of a
  persona-drift false pass/fail — and if it ever is, lane-a can still fix
  the substantive logic on its own side without needing lane-b's file at
  all. This is not a new FR — it packages FR-003's existing verification
  command as a script instead of leaving it inline, for lane-ownership
  reasons only.

### IC-02 — Composition manifests + discrimination control + C-001 fixture (proposed lane-b, part 1)

- **Purpose**: The 2 real FR-004 static cases (architect+sop+skill,
  reviewer+sop+skill); FR-006's rigged discrimination control, proven both
  flip and neutralize directions with the spec's pinned fixture text
  (verbatim, spec.md's `#### FR-006 pinned fixture text` section — do not
  re-derive, transcribe exactly); C-001's RFC-1-invalid fixture (a persona
  missing a required key, expected to produce exit `2`, never a
  `findingTypes` result).
- **Relevant requirements**: FR-004, FR-006, C-001.
- **Affected surfaces**: `conformance/crosslayer/manifest.yaml`,
  `conformance/crosslayer/cases/architect-run-skill.yaml`,
  `conformance/crosslayer/cases/reviewer-run-skill.yaml`,
  `conformance/crosslayer/control.yaml`,
  `conformance/crosslayer/fixtures/invalid-persona-missing-key.Soul.md`.
- **Sequencing/depends-on**: none. IC-00 (above) is dissolved: lane-b
  authors its own self-contained, RFC-1-valid sandbox persona fixture(s)
  for FR-004's two real cases (never committed to
  `conformance/crosslayer/personas/`, lane-a's exclusive write scope) and
  does not need lane-a's real projector output, byte-exact or otherwise —
  only the `fixturePath` values need to agree with lane-a's committed
  filenames (already fixed by Project Structure above). The real
  body-text content is verified for real post-merge by IC-04's CI job and
  the mission's Real-CLI verification requirement. `control.yaml` and the
  C-001 fixture were already self-contained synthetic text per the spec's
  own pinned fixture and are unaffected by this change.
- **Acceptance evidence**:
  - FR-004: `npx --offline @garrison-hq/muster@1.1.0 crosslayer run
    conformance/crosslayer/manifest.yaml --static-only --json`, expect exit
    `0`, `failed: 0`; falsification (swap in FR-006's rigged case), expect
    exit `1`, `failed > 0`.
  - FR-006: two-command pair (flip: muster exit `1` AND `jq -e
    '.findings|length>0'` exit `0`; neutralize: muster exit `0` AND `jq -e
    '.findings|length==0'` exit `0`) — the exact pinned text substitution
    only, never blanking/truncating (explicitly disallowed by the spec).
  - C-001: exit exactly `2`, stderr contains `muster: crosslayer manifest
    run failed:`, never a `--json` summary.
- **Risk**: do not write anything under `conformance/crosslayer/personas/`
  — that is lane-a's exclusive write scope even though it is nested inside
  lane-b's broader `conformance/crosslayer/` tree.
- **Coupling-surface note (M-3 post-tasks-review correction)**: the
  `fixturePath` agreement with lane-a described above is one of **five**
  path-only couplings across this mission's task files, not the only one —
  spec.md's Dependencies & Assumptions section now names all five explicitly
  (WP01↔WP02, WP02↔WP03, WP04↔WP01, WP04↔WP02, WP04↔WP03). This plan
  previously implied singularity by only ever discussing this one pair;
  treat spec.md's list as authoritative going forward.

### IC-03 — SOP policy extract + its own drift gate (proposed lane-b, part 2)

- **Purpose**: A bounded `AGENTS.md` (35,933 bytes, verified) operating-
  policy extract (OQ-6, option (b), committed as final per the post-spec
  clarification), with a drift script mirroring FR-003's pattern exactly
  (the symmetry citation-correction #5 already draws).
- **Relevant requirements**: FR-007.
- **Affected surfaces**: `conformance/crosslayer/sop-extract.md`,
  `conformance/scripts/check-sop-extract-drift.sh`.
- **Sequencing/depends-on**: none. Reads `AGENTS.md`, a shared read-only
  repo-root file, not owned by either lane.
- **Acceptance evidence**: `bash conformance/scripts/check-sop-extract-drift.sh`,
  expect exit `0` on a clean tree; falsification (hand-edit one committed
  line of `sop-extract.md`, not `AGENTS.md`), expect exit `1`.
- **Note**: the OQ-6 spike (does extract byte-length correlate with
  baseline degradation) informs future tuning only — it does not gate
  FR-004 or FR-007, per the spec's own explicit decision. Do not block this
  IC on the spike's outcome.

### IC-04 — `crosslayer.yml` CI workflow: static PR gate + cadence scaffold (proposed lane-b, part 3)

- **Purpose**: New workflow, isolated from `conformance.yml` by design.
  Static job: every PR, `garrison-hq/muster-action@<pinned-sha>` invocation
  of FR-004's manifest, path-filtered to both `conformance/**` and
  `src/doctrine/agent_profiles/built-in/**` (M1 post-spec decision — a
  profile-only PR must see and be able to fix the persona-drift check its
  own diff affects). Cadence job: `schedule:` + `workflow_dispatch:`
  triggers, `MUSTER_ENDPOINT`/`MUSTER_API_KEY` sourced from GitHub Actions
  repository secrets only, running FR-005's cases — **but see risk note**:
  built now with zero real cases until IC-05/lane-c lands.
  Also wires the one-line call sites for `check-persona-drift.sh`
  (lane-a's script) and `check-sop-extract-drift.sh` (lane-b's own script).
- **Relevant requirements**: FR-004 (CI wiring), FR-005 (infra only — not
  case content), FR-003's CI enforcement (via the call site, not the logic).
- **Affected surfaces**: `.github/workflows/crosslayer.yml`.
- **Sequencing/depends-on**: static job — none. Cadence job's *case
  content* depends on IC-05 (lane-c); the workflow scaffold itself does
  not.
- **Risk — do not let an empty cadence job read as evidence FR-005 works**:
  until lane-c lands, the cadence job has zero rule-survival cases to run.
  If it globs a `cases/rule-survival-*.yaml`/`erosion-control-*.yaml`
  pattern that currently matches nothing, `muster crosslayer run` may exit
  `0` trivially (no cases = no failures). This must be documented inline in
  the workflow (a comment) and called out at mission-review time so a
  "green cadence job" before lane-c lands is never mistaken for FR-005
  being satisfied.
- **Second risk — never touch the shared files**: `.github/workflows/conformance.yml`
  and `conformance/README.md` are both out of scope (see Dependencies/
  collision-surface findings below). `conformance/scripts/check-manifest-completeness.mjs`
  (also touched by M3's PR #30) is never edited by this mission either —
  lane-a/lane-b only *add* new files (`check-persona-drift.sh`,
  `check-sop-extract-drift.sh`) into the same `conformance/scripts/`
  directory; different filenames, no line-level overlap, confirmed not a
  collision.

### IC-05 — FR-005 rule-survival case authoring (proposed lane-c, blocked on M3)

- **Purpose**: The two real rule-survival cases (045 no-direct-push, 029
  signing) citing M3's manifest `ruleId`s, plus the engineered
  `erosion-control-045` adversarial case (persona text arguing for direct
  pushes, expected to erode composed pass rate below `passThreshold`).
- **Relevant requirements**: FR-005 (case content only — infra is IC-04).
- **Affected surfaces**: `conformance/crosslayer/cases/rule-survival-045.yaml`,
  `conformance/crosslayer/cases/rule-survival-029.yaml`,
  `conformance/crosslayer/cases/erosion-control-045.yaml`, and — since the
  manifest format is `$ref`-included case files, not directory-glob
  auto-discovery (Key Entities: `CompositionManifestCase[]`) — new `$ref:`
  lines added into `conformance/crosslayer/manifest.yaml`, a file IC-02
  (lane-b) produced.
- **Sequencing/depends-on**: **hard external block on M3
  (`MOES-Media/spec-kitty#30`) merging to this fork's `main`** — the
  `ruleId`s these cases cite by reference do not exist until that PR lands.
  Also depends on IC-02/IC-04 (lane-b) having already **merged** to the
  mission's coordination/target branch — unlike lane-a/lane-b's mutual
  parallelism, lane-c must NOT be created as an upfront parallel worktree;
  its lane should be forked only after lane-b's merge, specifically so it
  can read (not duplicate) lane-b's already-merged `manifest.yaml` when
  adding `$ref` lines. Creating lane-c's worktree early, before lane-b
  merges, would reproduce the exact lane-isolation bite hazard 2 warns
  about, for no benefit (M3 blocks it anyway).
- **Enforcement, not just procedure (post-plan review finding)**: the
  ordering above is not automatically enforced by prose alone — it is
  enforced by machinery that only engages if lane-c's WP frontmatter
  actually declares the dependency. Concretely: lane-c's WP(s) **must**
  declare `depends_on` on lane-b's WP id(s) in frontmatter. That feeds
  `dependency_graph` → `compute_lanes`'s `depends_on_lanes`, which makes
  `worktree_allocator._merge_dependency_lane_tips`
  (`lanes/worktree_allocator.py:300`) auto-merge lane-b's branch tip into
  lane-c's worktree (failing closed on conflict), and makes
  `merge/ordering.get_merge_order` (`:69`) topologically sort lane-c after
  lane-b instead of falling back to bare numerical WP order — a fallback
  it takes silently (`logger.warning` only, `:104-110`) if no WP declares
  a dependency. Without the frontmatter declaration, none of this engages.
  Separately, `policy/merge_gates._evaluate_dependency_gate` (`:229`) can
  refuse a merge when a dependency isn't done/approved, but only when
  `MergeGateConfig.mode == "block"`; **this repo's `.kittify/config.yaml`
  does not set it, so it defaults to `"warn"`** (`policy/config.py:74`) —
  confirmed by inspection, no override present. In `warn` mode an
  out-of-order merge is not hard-blocked by this gate. Task authoring and
  accept-time review must independently verify lane-c was actually
  sequenced after lane-b's merge; do not rely on the gate alone.
- **Acceptance evidence**: `MUSTER_ENDPOINT=<live> MUSTER_API_KEY=<key> npx
  @garrison-hq/muster@1.1.0 crosslayer run conformance/crosslayer/manifest.yaml
  --json` — expect exit `0` when every real case's `verdict` is `survived`
  or `baseline-failure`; expect exit `1` if any case's `verdict` is
  `eroded` — **including a standalone run of `erosion-control-045`
  alone**, expected `verdict: "eroded"`, exit `1`.
- **Standing-requirement gap, stated plainly**: as of the post-spec gate
  (round 2), the `erosion-control-045` case's expected `eroded` verdict has
  been *designed* but never *observed* against a live endpoint — the gate
  receipt says so explicitly ("Not independently re-verified in this
  remediation pass"). Per this mission's own standing requirement ("every
  grader needs a rigged-impossible discrimination control that will be
  observed failing, not merely written"), **FR-005 cannot be marked
  acceptance-complete until this case is actually run against a live
  OpenAI/NIM endpoint and the `eroded` verdict is observed**, not assumed.
  This is lane-c's own acceptance gate, not a new requirement I am adding.
- **Open sequencing decision for the operator**: does this mission's own
  accept/merge wait for lane-c, or does the mission close with FR-001–004/
  006/007 done and FR-005 explicitly tracked as a fast-follow within the
  same mission once M3 lands? The spec states FR-005's status as "Proposed
  (blocked on M3)" — in scope, not deferred to a new mission — but does not
  itself say whether mission acceptance waits. I am flagging this as a
  decision point, not deciding it here: it is an architectural/product
  sequencing call, not a work-decomposition one.

## Cross-Lane / Review-Time Checks (not owned by any single lane's task file)

- **C-003** (fabricated-field grading-leakage audit): self-declared in the
  spec as cross-lane, review-time. Runs the `grep`-based candidate-surfacing
  command over **both** lanes' committed output at implement-review time;
  explicitly not a fully machine-checkable gate (inverted exit polarity —
  exit `1` = clean — deliberately, per LOW-1's remediation; do not wire it
  into a hard CI `&&`/`||` step).
- **C-002** (diff-scope allow-list): the spec does not explicitly assign
  this a lane the way it does C-001 (which LOW-2 assigned to lane-b) or
  C-003 (self-declared). Its own Verification command operates over
  `git diff --name-only main...HEAD` — the **whole mission's combined
  diff**, not any single lane's tree. I am classifying it the same way as
  C-003: a cross-lane, pre-merge/mission-review check, run once over the
  fully assembled diff (all lanes + `kitty-specs/**` + `crosslayer.yml`)
  before the mission's accept/merge gate, not a task any single lane's
  worktree executes during implementation. This closes a lane-assignment
  gap the spec left implicit for C-002 specifically (it assigned C-001
  explicitly but not this one).
  **Post-plan review correction — C-002 also runs per-lane**: C-002 and
  C-003 are not the same shape. C-003 genuinely needs cross-lane
  visibility (it audits both lanes' committed output together). C-002
  does not — `git diff --name-only <base>...<lane-branch>` is computable
  for a single lane in isolation, before that lane even merges. Deferring
  it entirely to the assembled-diff run discards a free fail-fast check:
  a lane that accidentally touches `conformance/README.md` or
  `.github/workflows/conformance.yml` would otherwise only be caught
  after both lanes have already merged, instead of at once. **C-002
  therefore runs twice**: (1) per-lane, against that lane's own diff,
  before each lane's merge into the mission branch — lane-a's and
  lane-b's own responsibility, each on its own branch; and (2) once more
  over the fully assembled diff, as already described above, as the
  cross-lane pre-merge/mission-review backstop. Both runs use the same
  command shape, scoped to `<base>...<lane-branch>` for (1) and
  `main...HEAD` for (2). **Record both C-002 and C-003 as
  acceptance-matrix criteria at accept time** — the acceptance matrix is
  the one artifact this codebase's `_evaluate_evidence_gate` can actually
  see and act on; left as free-floating prose with "no lane owns it," a
  cross-lane check degrades into "nobody does" it. Whoever runs the
  accept gate must add explicit acceptance-matrix rows for C-002 and
  C-003, not just leave them documented here.

## Dependency Graph

```
IC-01 (lane-a)                    IC-02+IC-03+IC-04 (lane-b)
projector, personas,               manifests, control, C-001
persona-drift script               fixture, sop-extract, CI workflow
                                    (static job + cadence scaffold,
                                     zero cases initially)

     ── runs in PARALLEL, no shared pre-step ──
     (IC-00 dissolved, above — lane-b authors its own sandbox persona
     fixture; path agreement is already fixed by Project Structure
     above, needing no advance computation)

                       │
                       ▼ (both merge to mission coordination branch)
        C-002 + C-003 (cross-lane, pre-merge review gate)
                   │
                   ▼
        ═══ external dependency ═══
        M3 (MOES-Media/spec-kitty#30) merges to fork main
        ═══════════════════════════
                   │
                   ▼
        IC-05 (lane-c, forked AFTER lane-b merges)
        FR-005 real case content + erosion-control-045,
        $ref-added into lane-b's manifest.yaml
                   │
                   ▼
        Live-endpoint run, `eroded` verdict OBSERVED
        (FR-005 acceptance-complete only after this)
```

**Parallel**: lane-a (IC-01) and lane-b (IC-02/03/04) — genuinely
independent from the start now that IC-00 is dissolved: lane-b needs no
advance-computed content from lane-a, only `fixturePath` agreement
(already fixed by Project Structure above), so there is no shared
pre-step gating either lane's start.

**Serial**: lane-c (IC-05) after lane-b merges AND after M3 merges
(whichever lands later — in practice M3, since it is blocked on CI
infrastructure the operator is separately fixing). Cross-lane C-002/C-003
after both lane-a and lane-b merge, before the mission's own accept/merge.

## Collision-Surface Check (beyond `conformance.yml` / `conformance/README.md`)

Re-verified via `gh pr view 30 --repo MOES-Media/spec-kitty --json files`
during this plan pass:

- `.github/workflows/conformance.yml` — already handled (M7 uses its own
  `crosslayer.yml`).
- `conformance/README.md` — already handled (M7 uses
  `conformance/crosslayer/README.md`).
- `conformance/scripts/check-manifest-completeness.mjs` — **checked, not a
  collision**: M3's PR #30 modifies this existing file, but M7 never edits
  it; M7 only *adds* two new files (`check-persona-drift.sh`,
  `check-sop-extract-drift.sh`) into the same `conformance/scripts/`
  directory. Same directory, disjoint filenames — no line-level overlap,
  so this is not a merge-time collision under hazard 1's file-diff
  granularity.
- `conformance/doctrine/**`, `conformance/doctrine/README.md` — M3-only
  paths; M7 never reads or writes here.
- `kitty-specs/doctrine-rule-manifests-01KYH7AM/**`,
  `kitty-specs/sk-skills-static-conformance-01KYG7GE/**` — M3's own mission
  bookkeeping directories (the latter is M1's, oddly also touched by PR
  #30); M7's own mission directory is
  `kitty-specs/crosslayer-composition-suite-01KYJA33/**`, a disjoint tree.
  No collision.
- No collision found beyond the two the spec already names.

## Spec-Level Findings from This Planning Pass

1. **Apparent circularity in the lane-a/lane-b duplication requirement —
   dissolved, not resolved by a hand-computation pre-step** (documented
   fully as IC-00 above). The spec's Dependencies section (prior form)
   required lane-b's task file to embed lane-a's literal projector output,
   and the "frozen defaults table" that output would have depended on is
   not specified anywhere in spec.md, D1, or the seed ticket
   `MOES-Media/spec-kitty#26`. Checked directly
   against muster's source (`composition.ts:281-333`): the persona layer
   contributes only its RFC-1 body text to `layerTexts`, which is the only
   thing `contradiction-lint.ts` scans; front-matter fields (the fabricated
   defaults table's own output) never reach the lint, and C-003
   independently forbids grading them. So the byte-exact duplication the
   original Dependencies bullet asked for was an over-reading of what
   FR-004 actually needs: `fixturePath` agreement (free, already fixed by
   Project Structure) plus a self-authored, RFC-1-valid sandbox persona
   for lane-b's own local testing. Real content is verified for real,
   automatically, post-merge (IC-04's CI job; the mission's Real-CLI
   verification requirement) — no hand-computed reference bytes are
   needed at any point, and lane-a/lane-b's parallelism is undisturbed.
   spec.md's "Lane isolation" bullet is corrected in place to match; IC-00
   is retained above as a dissolved/superseded entry so the reasoning
   stays auditable rather than silently removed.
2. **C-002's lane assignment was left implicit** (only C-001 and C-003 got
   explicit lane notes in the post-spec remediation). Closed above by
   treating it the same as C-003: cross-lane, pre-merge review gate.
3. **FR-003 has no dedicated committed drift-check script**, unlike its own
   sibling FR-007 — only an inline verification command. Addressed via a
   hazard-3-driven restructuring (IC-01 gets `check-persona-drift.sh`), not
   a new functional requirement — same underlying check, packaged for
   correct lane ownership.
4. **FR-005's manifest wiring mechanism is `$ref`-based, not glob-based**
   (per Key Entities' `CompositionManifestCase[]` description) — meaning
   lane-c cannot add rule-survival cases without also editing lane-b's
   `manifest.yaml`. This is why lane-c must be sequenced strictly after
   lane-b's merge rather than created as an upfront parallel worktree like
   lane-a.
5. **Nothing found to be self-contradictory in the spec's substance.** The
   tension in finding 1 is a sequencing/authoring-time gap, not a logical
   contradiction — the spec's requirements are internally consistent; they
   just do not, on their own, fully specify *when* the reference content
   must be produced relative to task authoring.
6. **Open decision, not resolved here**: whether this mission's own
   accept/merge waits for lane-c (FR-005) or ships with it explicitly
   tracked as a same-mission fast-follow once M3 lands. Flagged for the
   operator/architect, not decided by this plan (decomposition and
   sequencing is my mandate; whether to gate mission completion on a
   blocked FR is a product/architecture call).
7. **Spec's "byte-identical for every cited file" citation was imprecise
   (post-plan review finding)**: re-verified directly against muster's
   own repository (`git diff --stat` between the two pinned commits, per
   cited file). Five of the six cited files
   (`src/crosslayer/composition.ts`,
   `src/adapters/openclaw-sop/manifest.ts`,
   `src/adapters/rfc1/schema.json`, `src/crosslayer/rule-survival.ts`,
   `src/crosslayer/contradiction-lint.ts`) are byte-identical between
   `v1.1.0` (`6bdb070d`) and the pinned commit (`624edd6d`). The sixth,
   `src/cli/index.ts`, is not — an unrelated `memory-utilization` adapter
   was added to it between the two pins (372 changed lines). The specific
   cited logic (the `ExecutionError`→exit-`2` mapping,
   `emitCrossLayerSummary`'s exit-code contract) was diffed directly at
   both pins and is byte-identical modulo line-offset shift from the
   unrelated addition, so C-001/FR-004's substance is unaffected — only
   the blanket whole-file claim was wrong. Corrected in spec.md's
   Dependencies & Assumptions section directly, not left as an
   uncorrected citation.

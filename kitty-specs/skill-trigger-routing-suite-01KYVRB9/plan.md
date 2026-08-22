# Implementation Plan: Skill Trigger-Routing Conformance Suite

**Branch**: `kitty/mission-skill-trigger-routing-suite-01KYVRB9` | **Date**: 2026-07-31 | **Spec**: `kitty-specs/skill-trigger-routing-suite-01KYVRB9/spec.md`
**Input**: Feature specification from `kitty-specs/skill-trigger-routing-suite-01KYVRB9/spec.md`

**Branch contract** (confirmed via `spec-kitty agent mission setup-plan --json`,
2026-07-31): current branch, target branch, base branch, planning-base
branch, and merge-target branch are all the same single branch,
`kitty/mission-skill-trigger-routing-suite-01KYVRB9` (`branch_matches_target:
true`). Single-branch topology, no dedicated integration branch — every
artifact in this plan commits directly to that branch.

## Summary

Author a live-model behavioral conformance suite proving (or disproving)
that five legacy/spk duplicate skill pairs and a three-member run-family
cluster route correctly under Claude Code's own skill-trigger machinery:
13 query-set YAML files (10 duplicate-pair-purpose + 3 run-family-purpose,
covering the same 3 skills twice under two distinct near-miss purposes —
research.md §8), one behavioral manifest pinning `gpt-4o-mini`/`runsPerQuery:
3`/`threshold: 0.5` plus a rigged-impossible discrimination control, four
verification scripts (one more than spec.md names explicitly — research.md
§7), a `workflow_dispatch`-only cadence workflow that commits a per-run
evidence artifact, and a README carrying the D-1 `[CONVENTION]` twin-
phrasing note and a `[LIMITATION]` note on the structural single-tool-per-
case ceiling this mission cannot lift (research.md §3). Zero edits to any
`SKILL.md`; zero changes to muster or muster-action source; `@garrison-hq/
muster@1.2.1` consumed only as an external, exact-pinned `npx` CLI.

## Technical Context

**Language/Version**: N/A for spec-kitty runtime (no `.py` touched). This
mission's own artifacts are YAML (query sets, manifest), Markdown (README),
JSON (evidence artifacts, JSON Schema contract), and four dependency-free
Node ≥22 scripts — Node is already required by `npx @garrison-hq/muster`,
so no second toolchain is introduced.
**Primary Dependencies**: `@garrison-hq/muster@1.2.1` (external, published
npm CLI, exact pin verified against `npm view` and the local read-only
checkout's `v1.2.1` tag = commit `16f0d34c3126fab5df2ee0b6e1e304a4d9bcb8e3`).
Neither added to any spec-kitty dependency manifest.
**Storage**: Filesystem only — committed YAML/JSON artifacts under
`conformance/skills/`.
**Testing**: real-CLI verification, not a new pytest suite (this mission's
surface is entirely outside `src/`, matching the sibling
`sk-skills-static-conformance-01KYG7GE` precedent) — every check is run for
real, in both its pass and rejection directions, per `quickstart.md`.
**Target Platform**: GitHub Actions `ubuntu-latest` (cadence workflow, real
`MUSTER_ENDPOINT`/`MUSTER_API_KEY` secrets) and any POSIX developer machine
with Node ≥22 (local, static checks only — live-model checks need real
credentials).
**Project Type**: single conformance-data tree, extending the existing
`conformance/skills/` directory M1 scaffolded; no new top-level source
directory.
**Performance Goals**: not fixed here — NFR-001's byte-identical-diff
requirement is the only performance-adjacent gate, and it is measured (a
diff of `--json` output on the static manifest before/after this mission),
not asserted with a ceiling.
**Constraints**: C-001 (diff scope — corrected in this plan, see Findings
below), C-002 (no `pull_request` trigger, parsed not grepped), C-003
(muster pinned exactly `1.2.1`).
**Scale/Scope**: 13 query-set files, 14 manifest cases (13 + 1 control), 4
verification scripts, 1 workflow file, 1 README, 1 JSON-Schema contract,
1..N committed evidence artifacts (grows over time, one per cadence run).

## Charter Check

*Gate source: `.kittify/charter/charter.md`. DIR-001..013 are all
`severity: warn` per `charter.yaml`; the binding `C-0xx` directives exist
only as charter.md prose (spec.md's own hand-enumerated table, carried
forward here).*

| Charter gate | Status | Note |
|---|---|---|
| DIR-005 — Tests added for new functionality | PASS (alternate form) | No pytest file added (nothing here is spec-kitty Python code). Substituted by the mandatory real-CLI verification procedure (`quickstart.md`), run in both pass and rejection directions for every one of the four new scripts. |
| DIR-006 — mypy --strict | N/A | No `.py` file touched. |
| DIR-007 — Docstrings for public APIs | N/A (alt.) | No Python public API added. Each `.mjs` script carries an explanatory header comment (house convention for `conformance/`, per M1 precedent). |
| DIR-008 — No security issues | PASS, actively verified | NFR-002's grep runs at every commit (`quickstart.md` §6); the evidence-artifact schema (`contracts/evidence-artifact.schema.json`) structurally forbids `@` in `endpointHost`; credentials only ever enter via `MUSTER_API_KEY`/`MUSTER_ENDPOINT` env vars, never a file. |
| DIR-009 — Breaking changes in CHANGELOG.md | N/A | Purely additive; NFR-001 explicitly requires the *existing* static suite's output to be byte-identical, i.e. non-breaking by construction. |
| DIR-010/011 — identifier/slug sanitization | N/A | No identifier-normalization code touched. |
| DIR-012 — Tracker issue assigned to HiC before implementation | ACTION REQUIRED at implement time | Seed issue `MOES-Media/spec-kitty#25` must be assigned to the Human-in-Charge before WP01 implementation starts, mirroring M1's DIR-012 handling. |
| DIR-013 — Pre-existing failures reported before baselining | N/A unless encountered | This mission's acceptance surface never runs spec-kitty's own pytest suite; still applies if an implementing agent incidentally observes a pre-existing failure elsewhere in this checkout. |
| **C-011 — ATDD-first (binding)** | PASS, sequenced explicitly | See Verification Strategy below: every WP's first commit is a failing check against a placeholder/empty fixture, committed before the real fixture; the reviewer verifies RED on `planning_base_branch` (this same branch, single-branch topology) and GREEN on the WP's final commit. Commit SHAs are recorded live in the mission work log during implementation (not fixed in this plan, which precedes any implementation commit). |
| C-003 (charter, dual-read) | N/A | No dual-homed identifier introduced. |
| C-004 (charter, burn-down) | N/A | No deprecation-list burn-down; this mission adds new query sets. |
| C-007 (charter, `__all__`) | N/A | Scoped to `src/charter/`/`src/kernel/`; this mission's deliverables live under `conformance/`. |
| Single canonical authority | PASS | `conformance/skills/README.md` is the one home for this suite's local-invocation docs and the `[CONVENTION]`/`[LIMITATION]` notes; the evidence-artifact schema lives in exactly one contract file. |
| Architectural alignment | PASS | `conformance/` stays outside `src/`; muster consumed only as an external, pinned, published CLI — no source coupling in either direction. |
| Glossary & terminology | PASS | No new domain terminology; "trigger case," "should-trigger axis," "near-miss axis," "control" are all muster's own existing vocabulary. |

No charter gate violations requiring justification (Complexity Tracking
below is empty for the same reason).

## Project Structure

### Documentation (this mission)

```
kitty-specs/skill-trigger-routing-suite-01KYVRB9/
├── spec.md                                          # done
├── plan.md                                          # this file
├── research.md                                      # Phase 0 output
├── data-model.md                                    # Phase 1 output
├── quickstart.md                                    # Phase 1 output — verification procedure
├── contracts/
│   ├── evidence-artifact.schema.json                # Phase 1 output — FR-005 schema
│   └── verification-scripts-cli-contract.md         # Phase 1 output — FR-001/002/004/005 script interfaces
├── decisions/DM-01KYVRGR9MVG1BXY2SAPTS262T.md        # done (M1 merge-status decision)
└── tasks/                                            # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
conformance/skills/
├── manifest.yaml                              # UNCHANGED (NFR-001) — M1's existing static suite
├── behavioral-manifest.yaml                    # NEW — FR-003: 13 non-control + 1 control case
├── control/name-mismatch/SKILL.md              # UNCHANGED — M1's own static control fixture
├── trigger-queries/                            # NEW — FR-001/002
│   ├── ad-hoc-profile-load-duplicate-pair-queries.yaml
│   ├── spk-doctrine-profile-load-duplicate-pair-queries.yaml
│   ├── spec-kitty-runtime-next-duplicate-pair-queries.yaml
│   ├── spk-run-next-duplicate-pair-queries.yaml
│   ├── spk-run-next-run-family-queries.yaml
│   ├── spec-kitty-runtime-review-duplicate-pair-queries.yaml
│   ├── spk-run-review-wp-duplicate-pair-queries.yaml
│   ├── spk-run-review-wp-run-family-queries.yaml
│   ├── spec-kitty-implement-review-duplicate-pair-queries.yaml
│   ├── spk-run-implement-review-duplicate-pair-queries.yaml
│   ├── spk-run-implement-review-run-family-queries.yaml
│   ├── spec-kitty-git-workflow-duplicate-pair-queries.yaml
│   ├── spk-admin-git-workflow-duplicate-pair-queries.yaml
│   └── rigged-impossible-control-queries.yaml
├── trigger-evidence/                           # NEW — FR-005, grows one file per cadence run
│   └── <run-timestamp>.json
└── README.md                                   # NEW section: cadence suite (FR-006), [CONVENTION] + [LIMITATION] tags

conformance/scripts/
├── check-trigger-queryset-shape.mjs            # NEW — FR-001
├── check-twin-phrasing.mjs                     # NEW — FR-002
├── check-control-discrimination.mjs            # NEW — FR-004 (plan-level addition, research.md §7)
└── check-evidence-artifact-shape.mjs           # NEW — FR-005

.github/workflows/
└── skill-trigger-routing.yml                   # NEW — FR-005 cadence workflow, workflow_dispatch only (C-002)
```

**Structure Decision**: extends the existing `conformance/skills/` tree
M1 scaffolded; no new top-level directory. `conformance/skills/manifest.yaml`
and its static cases are never touched (NFR-001) — this mission's manifest
is a sibling file, `behavioral-manifest.yaml`, never a modification of the
existing one.

## Component & Data Flow

```
trigger-queries/*.yaml (13 files, 2 purposes)
        │  (querySetPath, one file per manifest case)
        ▼
behavioral-manifest.yaml (14 cases: 13 real + 1 isControl:true)
        │  npx --offline @garrison-hq/muster@1.2.1 skills run <manifest> --json
        ▼
doSkillsRun → runBehavioralSkillCase(Safe) → runTriggerConformance
        │  per query: runSingleQuery × runsPerQuery, each call try/catched
        │  individually (a dead endpoint increments that call's runsErrored,
        │  never aborts the case — research.md §1/§5)
        ▼
gradeAxis (should-trigger, near-miss) → TriggerVerdict
        │  CLI maps to SkillsCaseResult JSON (no case-level runsErrored field —
        │  research.md §2)
        ▼
raw --json report
        │  check-control-discrimination.mjs computes the derived runsErrored
        │  sum and asserts the mode-appropriate control expectation
        │  (quickstart.md §4 — the FR-004 both-condition sequencing)
        ▼
evidence-summarization step (tasks-phase implementation detail; shape fixed
by data-model.md) → conformance/skills/trigger-evidence/<timestamp>.json
        │  check-evidence-artifact-shape.mjs (schema + credential-leak guard)
        ▼
committed evidence artifact (FR-005) ── read by humans/FR-006 issue-filing,
                                          never regenerated retroactively
```

Cadence workflow (`skill-trigger-routing.yml`, `workflow_dispatch` only,
C-002) is the only caller of this whole pipeline in CI; the local
`quickstart.md` commands exercise the same pipeline by hand during
implementation.

## Verification Strategy (first-class; see `quickstart.md` for the executable form)

Per FR, per this plan's binding rule that a check is not proven until run
against its rejection case:

| FR | Verification approach | Command | Expected exit | Falsification condition (must be constructed and run) |
|---|---|---|---|---|
| FR-001 | Shape-gate all 13 query-set files | `node conformance/scripts/check-trigger-queryset-shape.mjs conformance/skills/trigger-queries/*.yaml` | `0` | A 7-entry `shouldTrigger` fixture → exit `1`, naming the file (`quickstart.md` §1) |
| FR-002 | Cross-reference every declared pair/triple | `node conformance/scripts/check-twin-phrasing.mjs conformance/skills/trigger-queries/` | `0` | A file with zero shared strings with its twin's should-trigger set → exit `1`, naming the pair (`quickstart.md` §2) |
| FR-003 | No behavioral case silently skipped when credentials are configured | `... skills run ... --json \| node -e "...c.skipped..."` (spec.md's own one-liner) | `0` when configured, `1` when `MUSTER_ENDPOINT` unset | Unset endpoint → exit `1` (every case skipped) — this is the required rejection proof, run *before* trusting any configured-endpoint green (`quickstart.md` §3) |
| FR-004 | Control observed failing in both conditions, `runsErrored` (derived) distinguishing them | `check-control-discrimination.mjs <report> --mode healthy\|dead-endpoint` | `0` in matching mode | Cross-wired mode/data pairs (`--mode healthy` against dead-endpoint data, and the inverse) → exit `1`; omitted `--mode` → exit `2` (`quickstart.md` §4, four rejection runs total) |
| FR-005 | Evidence artifact schema + credential-leak guard | `node conformance/scripts/check-evidence-artifact-shape.mjs <file>.json` | `0` | Prose-only file → exit `1` naming missing fields; full-URL-with-`api_key` file → exit `1` naming the leak (`quickstart.md` §5, two rejection proofs) |
| FR-006 | README findings index has ≥1 real issue URL once findings exist | `command grep -c 'github.com/MOES-Media/spec-kitty/issues/' conformance/skills/README.md` | nonzero once findings exist | A "Findings" header with zero linked URLs underneath must not satisfy this (spec.md's own falsification condition — manual review, not mechanical, since filing is post-execution) |
| NFR-001 | Static-path byte-identical diff | `diff <(before) <(after)` of `skills run conformance/skills/manifest.yaml --json`, this mission's changes only | empty diff | Any single-byte drift in the static path's own output → non-empty diff (run once before any edit, once after all edits) |
| NFR-002 | No credentials committed | `command grep -rE '(sk-\|api[_-]?key...)' behavioral-manifest.yaml skill-trigger-routing.yml` | `1` (no match) | A planted fake key → exit `0` (match found), confirming the grep actually fires (`quickstart.md` §6) — then discard, never commit |
| NFR-003 | `runsErrored` (derived) present and distinct from `triggerRate` | schema field presence check, `contracts/evidence-artifact.schema.json` | required field, always present incl. `0` | A summarizer that drops the field when it's `0` would violate this even while "using" the right data — checked by the schema's `required` list, not just its `type` |
| C-001 | Diff scope (corrected list, research.md §6) | manual review of the PR diff against the four named scripts + this plan's exact file list | — | (see Findings below — this constraint's own prose glob is narrower than FR-002/FR-005's committed deliverables; this plan's file list is the corrected authority) |
| C-002 | No `pull_request` trigger, YAML-parsed | `quickstart.md` §7 Python/PyYAML parse of the `on:` block | assertion passes | A scratch copy with `pull_request:` added under `on:` → assertion fires |
| C-003 | muster pinned exactly `1.2.1` | `command grep -c '@garrison-hq/muster@1\.2\.1' skill-trigger-routing.yml README.md` vs. `command grep -c '@garrison-hq/muster@\^'` | expected count / `0` | A `^1.2.1` range anywhere in either file → the second grep returns nonzero |

### FR-004's both-condition sequencing (explicit, since it is this mission's central proof)

1. Run the manifest against the real, healthy endpoint. Capture
   `/tmp/report-healthy.json`. Assert `--mode healthy` → exit `0`.
2. Point `MUSTER_ENDPOINT` at an unreachable host. Run again. Capture
   `/tmp/report-dead.json`. Assert `--mode dead-endpoint` against this file
   → exit `0`.
3. Cross-wire both ways (`--mode healthy` against `report-dead.json`;
   `--mode dead-endpoint` against `report-healthy.json`) → both must exit
   `1`. This is the actual proof that the discriminator is `runsErrored`
   (derived) and not `passed` alone — `passed:false` is true in *both*
   captured reports, by construction (research.md §2's numeric trace), so
   any check that only looked at `passed` would pass both cross-wired runs
   incorrectly.
4. Restore `MUSTER_ENDPOINT` to the healthy value before continuing any
   other work.

Full commands: `quickstart.md` §4.

## Distractor tools — not needed here because they are not achievable here

The hazard note asks whether FR-001/FR-002 need distractor tools in
`TriggerCase.tools` to avoid muster#82's single-tool bias (should-trigger
scores being dominated by "was there anything else to call," not
description quality). Traced against the actual pinned CLI
(`research.md` §3): `runBehavioralSkillCase` hardcodes a length-1
`ToolDefinition[]` from the target skill's own frontmatter, and
`SkillsManifestBehavioralCase` has no field to declare additional tools.
**This mission cannot add distractor tools without a muster source change**,
which is out of scope (C-001, Scope Guard: no code added to
`src/core/`/`src/adapters/` in either repo). The plan's answer is: do not
attempt a manifest-level workaround the schema does not support; instead,
`conformance/skills/README.md` carries an explicit `[LIMITATION]` note
(alongside D-1's `[CONVENTION]` note) stating that this suite's
should-trigger axis, as pinned, can only detect actively repellent
descriptions — not fine-grained quality differences among plausible
candidates — and that lifting this requires a muster-side manifest-schema
change (tracked the same way D-1 tracks the rubric-addendum PR: a
dependency note, not this mission's own diff).

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks`
> translates these into executable WPs.

### IC-01 — Duplicate-pair query sets (10 files)

- **Purpose**: Author the 10 `*-duplicate-pair-queries.yaml` files, each
  ≥8/axis, each pair's near-miss set containing at least one phrase
  byte-identical to its twin's should-trigger set (FR-002's duplicate-pair
  half).
- **Relevant requirements**: FR-001, FR-002 (duplicate-pair direction).
- **Affected surfaces**: `conformance/skills/trigger-queries/*-duplicate-pair-queries.yaml` (new, 10 files).
- **Sequencing/depends-on**: none.
- **Risks**: authoring 10 files by hand risks an asymmetric cross-reference
  (A borrows from B but not vice versa) — mitigated by `check-twin-phrasing.mjs`
  checking both directions explicitly (contracts file), run before this
  concern is considered done.

### IC-02 — Run-family query sets (3 additional files)

- **Purpose**: Author the 3 `*-run-family-queries.yaml` files for
  `spk-run-next`, `spk-run-review-wp`, `spk-run-implement-review` — same
  `skillDir` as their IC-01 counterpart, different `querySetPath`, near-miss
  drawn from the *other two* siblings' should-trigger sets (FR-002's
  run-family half, research.md §8's naming convention).
- **Relevant requirements**: FR-001, FR-002 (run-family direction).
- **Affected surfaces**: `conformance/skills/trigger-queries/*-run-family-queries.yaml` (new, 3 files).
- **Sequencing/depends-on**: none functionally, but should be authored
  after IC-01 settles each skill's `-duplicate-pair-` should-trigger phrases
  (the run-family near-miss sets borrow should-trigger phrases from
  siblings' *duplicate-pair* files, not a separate should-trigger list).
- **Risks**: the 3-way symmetric cross-reference (each of 3 siblings
  borrows from the other 2) is easy to under-populate to 2-way by mistake —
  `check-twin-phrasing.mjs`'s triple-mode check (contracts file) is the
  guard, not manual review.

### IC-03 — Rigged-impossible control query set

- **Purpose**: Author `rigged-impossible-control-queries.yaml` following the
  `examples/` pattern (D-3), never the `fixtures/` pattern (muster#73's
  `ZZZCONTROL` self-match defect) — 8 plausible/unrelated `shouldTrigger`
  queries, 8 topically-adjacent `nearMiss` variants of those same queries.
- **Relevant requirements**: FR-004.
- **Affected surfaces**: `conformance/skills/trigger-queries/rigged-impossible-control-queries.yaml` (new).
- **Sequencing/depends-on**: none.
- **Risks**: accidentally reusing the literal string the control's
  description-substitution introduces (`ZZZCONTROL-IMPOSSIBLE`) anywhere in
  `nearMiss` would reintroduce muster#73's self-match defect in this
  mission's own fixture — reviewed by direct text search for that
  substring before commit, in addition to the discrimination proof in IC-06.

### IC-04 — Behavioral manifest

- **Purpose**: Author `behavioral-manifest.yaml`: 13 real cases (one per
  IC-01/IC-02 file) + 1 control case (`isControl: true`, referencing IC-03's
  file), `model: gpt-4o-mini`/`runsPerQuery: 3`/`threshold: 0.5` pinned in a
  default config block, each case's own `threshold`/`runsPerQuery`
  overriding its query set's file-level `threshold` field per the CLI's
  actual precedence (research.md §1).
- **Relevant requirements**: FR-003.
- **Affected surfaces**: `conformance/skills/behavioral-manifest.yaml` (new).
- **Sequencing/depends-on**: IC-01, IC-02, IC-03 (references their file
  paths by name — this is the one genuine cross-lane dependency, declared
  explicitly per this programme's `resolve_workspace_for_wp()` history).
- **Risks**: none material beyond the dependency above; case-`id` collisions
  are avoided by the `<skill-id>` / `<skill-id>-run-family` naming
  convention (data-model.md).

### IC-05 — Four verification scripts

- **Purpose**: Author `check-trigger-queryset-shape.mjs`,
  `check-twin-phrasing.mjs`, `check-control-discrimination.mjs`,
  `check-evidence-artifact-shape.mjs` per
  `contracts/verification-scripts-cli-contract.md`.
- **Relevant requirements**: FR-001, FR-002, FR-004, FR-005.
- **Affected surfaces**: `conformance/scripts/*.mjs` (new, 4 files).
- **Sequencing/depends-on**: none to *start* (each script's contract is
  fully specified independent of IC-01–IC-04's content), but each script's
  GREEN proof needs its corresponding fixture: `check-trigger-queryset-shape.mjs`
  needs IC-01/IC-02's real files to prove GREEN (RED is proven against a
  placeholder first, per C-011).
- **Risks**: `check-control-discrimination.mjs`'s derived-sum computation
  (research.md §2) is the single highest-value correctness risk in this
  mission — a bug here silently launders a dead-endpoint run as a valid
  discrimination proof. Mitigated by the four-rejection-case sequence in
  `quickstart.md` §4 being mandatory, not optional, before FR-004 is marked
  done.

### IC-06 — Cadence workflow

- **Purpose**: Author `.github/workflows/skill-trigger-routing.yml`:
  `workflow_dispatch` only (C-002); steps in the order given in
  `contracts/verification-scripts-cli-contract.md`'s CI-wiring section;
  muster pinned exactly `1.2.1` (C-003); secrets via `MUSTER_ENDPOINT`/
  `MUSTER_API_KEY` repository secrets only.
- **Relevant requirements**: FR-005, C-002, C-003.
- **Affected surfaces**: `.github/workflows/skill-trigger-routing.yml` (new).
- **Sequencing/depends-on**: IC-04 (manifest path must exist), IC-05
  (script paths/exit-code contracts — needs the contract file only, not the
  scripts' source, so this can be authored in parallel with IC-05 in
  practice, same pattern as M1's IC-06/IC-03 relationship).
- **Risks**: schedule/cron wiring is explicitly out of scope (M8,
  garrison-hq/muster-action#2) — this workflow must not accidentally gain a
  `schedule:` trigger through copy-paste from a different workflow file in
  this repo.

### IC-07 — README (cadence section, `[CONVENTION]` + `[LIMITATION]` tags)

- **Purpose**: Extend `conformance/skills/README.md` (M1's existing file)
  with: local invocation for the behavioral suite, the pinned version, the
  D-1 `[CONVENTION]`-tagged twin-phrasing methodology note (until the
  muster-side rubric-addendum PR lands), the new `[LIMITATION]`-tagged
  single-tool-bias note (research.md §3), and the FR-006 findings index
  (empty until a real routing defect is filed, per spec.md's own
  falsification condition).
- **Relevant requirements**: FR-006, D-1.
- **Affected surfaces**: `conformance/skills/README.md` (extended, not
  replaced — M1's static-suite section stays intact).
- **Sequencing/depends-on**: IC-01 through IC-06 (documents facts those
  establish) and the Verification Strategy's FR-004 both-condition run (the
  README's own discrimination-proof section cannot be written accurately
  until that sequence has actually been executed once).
- **Risks**: none material.

## Work-Package Outline (preview for `/spec-kitty.tasks` — not tasks.md)

Spec.md's own two-lane split (lane-a query sets, lane-b manifest/scripts/
workflow/README) is preserved; this plan refines lane-b's `write_scope` to
the four actual script filenames (research.md §6 — the corrected,
exhaustive list, not the `check-trigger-*.mjs` glob) and states IC-04's
cross-lane dependency on lane-a's file paths explicitly, per this
programme's repeated `resolve_workspace_for_wp()` under-declared-dependency
finding:

```json
{
  "lanes": [
    { "lane_id": "lane-a", "wp_ids": ["WP01", "WP02"],
      "write_scope": [
        "conformance/skills/trigger-queries/**"
      ],
      "depends_on_lanes": [], "parallel_group": 0 },
    { "lane_id": "lane-b", "wp_ids": ["WP03"],
      "write_scope": [
        "conformance/skills/behavioral-manifest.yaml",
        "conformance/scripts/check-trigger-queryset-shape.mjs",
        "conformance/scripts/check-twin-phrasing.mjs",
        "conformance/scripts/check-control-discrimination.mjs",
        "conformance/scripts/check-evidence-artifact-shape.mjs",
        "conformance/skills/trigger-evidence/**",
        ".github/workflows/skill-trigger-routing.yml",
        "conformance/skills/README.md"
      ],
      "depends_on_lanes": ["lane-a"], "parallel_group": 1 }
  ]
}
```

- **WP01** (lane-a): IC-01 — the 10 duplicate-pair files. Before starting,
  confirm `MOES-Media/spec-kitty#25` is assigned to the Human-in-Charge
  (DIR-012).
- **WP02** (lane-a): IC-02 + IC-03 — the 3 run-family files + the control
  query set. Sequenced after WP01 within lane-a (borrows WP01's
  duplicate-pair should-trigger phrases); both are lane-a so no
  cross-lane dependency is needed for this internal order.
- **WP03** (lane-b): IC-04 + IC-05 + IC-06 + IC-07 — manifest, all four
  scripts, workflow, README. **Depends on lane-a** (`depends_on_lanes:
  ["lane-a"]`) because IC-04's manifest references WP01/WP02's file paths
  by name — unlike M1's WP03, which needed only a contract file from its
  sibling lane, this mission's lane-b needs lane-a's actual output paths to
  exist, so lane-b cannot start truly in parallel with lane-a (a
  correction from spec.md's Lanes section, which states the dependency in
  prose but does not mark `parallel_group` accordingly — flagged in
  Findings below).

**Build order**: WP01 → WP02 (lane-a, sequential) → WP03 (lane-b, after
lane-a's files exist). This is a single critical path, not the two-stream
parallelism spec.md's Lanes section implies by listing lane-a/lane-b as
non-colliding — non-collision (no shared file) is true and preserved, but
*sequencing* (lane-b needs lane-a's paths to exist before its own manifest
is authored) is not the same property as *parallelism*, and this plan
corrects that distinction explicitly.

## Complexity Tracking

*No entries — no charter gate violations require justification.*

No new runtime dependency anywhere: `@garrison-hq/muster` is consumed via
`npx`, never added to a spec-kitty dependency manifest. All four new
scripts use Node stdlib only.

## Findings Requiring Spec Attention

*Per this skill's guardrail, these are flagged, not silently patched into
spec.md's FR/NFR/C text. If any is judged to change a functional
requirement rather than clarify its verification, route back to
`spk-mission-specify` before tasks/implementation.*

1. **`runsErrored` is not a case-level JSON field.** FR-004/FR-005's own
   acceptance-scenario language reads as if it were. This plan defines it
   as a derived sum over both axes' `queryBreakdown[]` (research.md §2,
   `data-model.md`) and adds a script (`check-control-discrimination.mjs`)
   that computes it — this is a verification-design clarification, not a
   change to what FR-004 requires observationally.
2. **Distractor tools are structurally unavailable at muster `1.2.1`.**
   `SkillsManifestBehavioralCase` has no field for them; the CLI hardcodes
   one tool per case. This plan documents the limitation in the suite
   README rather than attempting an unsupported manifest workaround — spec.md
   never actually claimed distractor tools were in scope, so this is a
   clarification of an unstated gap, not a contradiction of stated text.
3. **C-001's `check-trigger-*.mjs` glob does not match two of the three
   scripts FR-002/FR-005 already name** (`check-twin-phrasing.mjs`,
   `check-evidence-artifact-shape.mjs`). This plan's Work-Package Outline
   carries the corrected, exhaustive four-script list (research.md §6). No
   functional requirement changes; the constraint's own prose is imprecise
   relative to the mission's own committed deliverables.
4. **Lane-b is sequentially dependent on lane-a, not merely
   non-colliding.** Spec.md's Lanes section states the dependency in prose
   ("lane-b's WP03 depends on lane-a's WP01/WP02 output existing") but its
   `write_scope` framing reads as a parallel two-lane split. This plan's
   `parallel_group` values (`0` for lane-a, `1` for lane-b) make the
   sequencing binding rather than advisory, for `/spec-kitty.tasks` to
   consume directly.
5. **FR-004's verification command as written in spec.md is prose, not a
   checked-in script**, the only FR in the document without one. This plan
   adds `check-control-discrimination.mjs` (research.md §7) to close that
   gap consistently with every other FR's pattern.
6. **13-file arithmetic is correct but the naming convention that avoids a
   same-filename collision between the two lanes' outputs for the 3 shared
   run-family skills is never stated in spec.md.** This plan fixes it
   (research.md §8, `<skill-id>-<purpose>-queries.yaml`).

None of the six items above changes an FR's stated *user-observable*
behavior; all six are verification-design or file-layout clarifications
this plan is responsible for supplying. If a future reviewer judges
otherwise for any item, that item should be routed back through
`spk-mission-specify` before `/spec-kitty.tasks` runs.

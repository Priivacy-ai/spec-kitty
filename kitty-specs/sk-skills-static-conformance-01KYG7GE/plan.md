# Implementation Plan: Skills Static Conformance Suite

**Branch**: `kitty/mission-sk-skills-static-conformance` | **Date**: 2026-07-27 | **Spec**: `kitty-specs/sk-skills-static-conformance-01KYG7GE/spec.md`
**Input**: Feature specification from `kitty-specs/sk-skills-static-conformance-01KYG7GE/spec.md`

**Branch contract** (confirmed via `spec-kitty agent mission setup-plan --json`):
current branch, target branch, base branch, planning-base branch, and
merge-target branch are all the **same single branch**,
`kitty/mission-sk-skills-static-conformance` (`branch_matches_target: true`).
There is no separate integration branch for this mission — every artifact in
this plan commits directly to that branch, and that is also where the
completed mission diff lands before any eventual PR to
`MOES-Media/spec-kitty` (the fork), never to upstream `Priivacy-ai/spec-kitty`
(spec Scope Guard, OQ-2).

## Summary

Bootstrap a `conformance/` tree in the spec-kitty fork that runs the
external `@garrison-hq/muster@1.1.0` CLI, via `garrison-hq/muster-action@v1`,
against all 53 built-in `src/doctrine/skills/*/SKILL.md` files: a static
manifest (53 conformant cases + 1 rigged control), a PR-gating GitHub
Actions workflow, a manifest-completeness check that keeps the manifest's
case count honest against the actual skill tree (FR-007, added post-spec-gate
by operator decision), the programme's D1–D5 decision record with citations
re-derived against the exact pinned muster version, and a README documenting
local invocation and muster's known gaps. Zero changes to spec-kitty runtime
code (`src/doctrine/**` and everything else outside `conformance/**` and
`.github/workflows/**`); zero changes to muster or muster-action source. This
is data + one small script consuming two external, already-shipped tools —
never a dependency spec-kitty's own runtime carries, and never a change that
makes muster couple back to spec-kitty (the operator's standing architectural
principle for this whole programme).

## Technical Context

**Language/Version**: N/A for spec-kitty runtime (no `.py` file is added or
changed). The `conformance/` tree itself is YAML (manifest), Markdown
(README, DECISIONS.md), and one dependency-free Node ≥22 script
(`check-manifest-completeness.mjs`) — Node is already a hard requirement for
this workflow via `npx @garrison-hq/muster`, so no second language toolchain
is introduced (research.md §6).
**Primary Dependencies**: `@garrison-hq/muster@1.1.0` (external, published
npm CLI, pinned exact version per C-003 — verified via `npm view
@garrison-hq/muster version` on 2026-07-27); `garrison-hq/muster-action@v1`
(external GitHub Action, consumed exactly as shipped). Neither is added to
`pyproject.toml` or any spec-kitty dependency manifest — both are pulled at
CI/local-invocation time via `npx`/the Action, never installed into
spec-kitty's own environment.
**Storage**: N/A.
**Testing**: this mission's acceptance surface is **real-CLI verification**,
not a new pytest suite (per operator directive — binding constraint 7): the
actual built muster CLI is run against the actual 53-skill manifest and its
documented exit code is asserted; the FR-005 control case is proven to flip
the exit code both ways; the FR-007 completeness script is run both against
the true tree (pass) and an induced mismatch (fail, naming the specific
skill). See "Verification Strategy" below and `quickstart.md`, which is the
executable form of this testing strategy. No spec-kitty pytest file is added
because none of this mission's surface is spec-kitty Python code (C-001
boundary) — DIR-005 ("tests added for new functionality") is satisfied by
this real-invocation procedure being a first-class, mandatory implementation
step recorded in the work log, not skipped as "just infrastructure."
**Target Platform**: GitHub Actions `ubuntu-latest` (CI, per the fork's
existing workflow convention — `actions/checkout@v6` etc.) and any POSIX
developer machine with Node ≥22 (local).
**Project Type**: single conformance-data tree; no new spec-kitty package,
module, or top-level source directory (`conformance/` sits beside
`src/doctrine/`, `docs/`, `.github/`, not inside `src/`).
**Performance Goals**: NFR-001 is measured, not asserted, at plan time — no
numeric ceiling is fixed here. The real GitHub Actions run_id and wall-clock
minutes are recorded in `conformance/README.md` after the first real green
run, following this project's existing measured-not-asserted CI-budget
pattern (`docs/plans/testing/ci-job-timings.md`, `docs/development/
testing-flakiness.md` — research.md §7).
**Constraints**: C-001 (diff touches only `conformance/**` and
`.github/workflows/**`); C-002 (no secrets, must pass on fork PRs — the
static path is fully offline by construction); C-003 (muster version pinned
exact, `1.1.0`, never a range); NFR-002 (deterministic given the pin, zero
network calls in the run path once cache-warmed).
**Scale/Scope**: 53 `StaticCase` entries + 1 `ControlCase` = 54 manifest
cases; one completeness-check script; one CI workflow file; two Markdown
docs (`README.md`, `DECISIONS.md` carrying 5 decisions).

## Charter Check

*Gate source: `.kittify/charter/charter.md`. Most Python-runtime gates are
N/A by construction (C-001: zero `.py` files touched) — marked explicitly
below rather than silently skipped, per this project's own "single canonical
authority" and evidence-over-assumption policy.*

| Charter gate | Status | Note |
|---|---|---|
| DIR-005 — Tests added for new functionality | PASS (alternate form) | No pytest file is added (nothing here is spec-kitty Python code). Substituted by the mandatory real-CLI verification procedure (Verification Strategy below, `quickstart.md`) — every check this mission adds is exercised for real, both pass and fail directions, with results recorded in the mission work log. |
| DIR-006 — Type annotations / mypy --strict | N/A | No `.py` file is added or changed. |
| DIR-007 — Docstrings for public APIs | N/A | No Python public API is added. The one Node script carries an explanatory header comment in lieu (house convention for the `conformance/` tree, not a charter-mandated Python docstring). |
| DIR-008 — No security issues (credentials, secrets handling) | PASS | Zero secrets anywhere in `conformance/**` or `.github/workflows/conformance.yml` — the entire suite is static and offline by design (C-002). |
| DIR-009 — Breaking changes documented in CHANGELOG.md | N/A | Purely additive; no existing behavior changes. |
| DIR-010/DIR-011 — ASCII slug sanitization + regression coverage | N/A | No identifier-normalization or slug-sanitization code is touched or added. |
| DIR-012 — Tracker-backed issue assigned to HiC before implementation starts | ACTION REQUIRED at implement time | This mission's seed is GitHub issue `MOES-Media/spec-kitty#22`. Whichever agent begins WP01/WP02/WP03 implementation **must assign issue #22 to the Human-in-Charge** before or as part of starting, per DIR-012 — flagged here so it is not missed at the tasks/implement handoff. |
| DIR-013 — Pre-existing test failures reported as an issue before treating them as baseline | N/A unless encountered | This mission does not run spec-kitty's own pytest suite as part of its acceptance surface; if an implementing agent incidentally observes a pre-existing failure while working in this checkout, DIR-013 still applies and must be filed. |
| Single canonical authority | PASS | `conformance/` is the one and only home for this suite; `DECISIONS.md` is the one and only home for the programme's D1–D5 record (FR-004) — no duplicate decision text lives elsewhere in this mission. |
| Architectural alignment (shared-package boundary respected) | PASS | `conformance/` is deliberately outside `src/`, matching the operator's standing principle that muster must not become tightly coupled to spec-kitty and vice versa — this mission is SK-side conformance *data* consuming muster as an external published CLI, never a source dependency in either direction. |
| ATDD-first | PASS (adapted) | The spec's Acceptance Scenarios (including the two FR-007 scenarios added this plan phase) are the outside-in acceptance surface; `quickstart.md` operationalizes them as the exact commands to run, both pass and fail directions, before any case or script is considered done. |
| Glossary & terminology adherence | PASS | No new domain terminology is introduced; "static case," "control case," "manifest," "profile" are all muster's own existing vocabulary, used as-is. |
| Model discipline / delegate to preserve context / dispatch a governed profile | N/A at plan phase | Governs how the *tasks/implement* phase dispatches agents, not this plan's content — noted for the tasks-phase handoff, not a plan-time gate. |

No charter gate violations requiring justification. No new runtime
dependency is added to spec-kitty itself (the two external tools are
consumed via CLI/Action, never as package dependencies).

## Project Structure

### Documentation (this mission)

```
kitty-specs/sk-skills-static-conformance-01KYG7GE/
├── spec.md                                    # done (amended this phase: FR-007 added)
├── plan.md                                    # this file
├── research.md                                # Phase 0 output
├── data-model.md                              # Phase 1 output
├── quickstart.md                              # Phase 1 output — also the verification procedure
├── contracts/
│   ├── skills-manifest-case.schema.json       # Phase 1 output — descriptive manifest shape
│   └── completeness-check-cli-contract.md     # Phase 1 output — FR-007 script/CI interface
└── tasks.md                                   # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
conformance/
├── README.md                        # FR-006: local invocation, pinned version, known gaps, CI timing
├── DECISIONS.md                     # FR-004: D1–D5, citations re-derived against muster v1.1.0
├── scripts/
│   └── check-manifest-completeness.mjs   # FR-007: dependency-free Node script
└── skills/
    ├── manifest.yaml                # FR-001/002/007: 53 StaticCase + 1 ControlCase
    └── control/
        └── name-mismatch/
            └── SKILL.md              # FR-005: rigged fixture, name != dirname

.github/workflows/
└── conformance.yml                   # FR-003: garrison-hq/muster-action@v1 gate
                                       # FR-007: + one completeness-check step
```

**Structure Decision**: single conformance-data tree, no new top-level
source directory beyond `conformance/` itself (which sits alongside
`src/`, `docs/`, `.github/` at the repo root, never inside `src/`). No
existing file under `src/doctrine/skills/` is modified — the 53
`StaticCase` entries reference those directories read-only via `skillDir`.

## Verification Strategy (first-class, per operator directive)

This mission cannot be called done on unit-test or agent-assertion alone.
Before any WP is marked complete, the implementing agent must run, for
real, and record the real result of:

1. **The real muster CLI against the real 53+1 manifest** (`quickstart.md`
   §1) — cache-warm, then offline `skills run`, asserting exit `0`.
2. **The FR-005 control case's discrimination proof, both directions**
   (`quickstart.md` §2) — un-flipped exit `0`; manually flipped exit
   non-zero; restored.
3. **The FR-007 completeness check, both directions** (`quickstart.md`
   §3) — true tree exits `0`; an induced mismatch exits non-zero **and**
   names the specific skill responsible; restored tree exits `0` again.
4. **A real GitHub Actions run of `conformance.yml`** (`quickstart.md` §4)
   — both steps green, wall-clock minutes and `run_id` recorded in
   `conformance/README.md` (NFR-001), and — if a fork-PR run is feasible to
   observe — confirmation that no secret is required (C-002, AC-3).

Steps 1–3 are cheap and MUST be run locally by the implementing agent
before requesting review; step 4 requires a real PR and is the closing
verification before the mission is proposed for merge.

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks`
> translates these into executable WPs.

### IC-01 — Static skills manifest

- **Purpose**: Author `conformance/skills/manifest.yaml`'s 53 `StaticCase`
  entries, one per built-in skill, each `{profile: base, expectations: {ok:
  true, violations: []}}` with a manifest-relative `skillDir`.
- **Relevant requirements**: FR-001, FR-002.
- **Affected surfaces**: `conformance/skills/manifest.yaml` (new).
- **Sequencing/depends-on**: none.
- **Risks**: none material — feasibility is pre-verified (spec Dependencies
  & Assumptions: all 53 skills already pass muster's three hard gates).

### IC-02 — Discrimination control fixture + case

- **Purpose**: Author the FR-005 rigged-broken fixture
  (`conformance/skills/control/name-mismatch/SKILL.md`, frontmatter `name`
  ≠ directory basename) and its manifest entry
  (`expectations: {ok: false, violations: []}`).
- **Relevant requirements**: FR-005.
- **Affected surfaces**: `conformance/skills/control/**`,
  `conformance/skills/manifest.yaml` (same file as IC-01 — same lane).
- **Sequencing/depends-on**: IC-01 (same manifest file; author together to
  avoid two separate edits to one file).
- **Risks**: control-case regression (spec edge case) — mitigated by the
  fail-safe already built into muster's own `passed = ok === expectations.ok`
  rule (data-model.md, ControlCase section); no extra guard needed here.

### IC-03 — Manifest completeness check script (FR-007)

- **Purpose**: Author `conformance/scripts/check-manifest-completeness.mjs`
  per `contracts/completeness-check-cli-contract.md` — dependency-free
  Node script comparing the manifest's static-case count/name-set against
  `src/doctrine/skills/*`, offset by the +1 control case (named constant,
  not a magic number).
- **Relevant requirements**: FR-007.
- **Affected surfaces**: `conformance/scripts/**` (new — added to lane-a's
  write scope; see Work-Package Outline below for the lane-collision
  resolution).
- **Sequencing/depends-on**: IC-01 (needs the manifest's final authoring
  convention — case/skillDir line shape — settled first).
- **Risks**: line-based parsing depends on a documented manifest-authoring
  convention rather than a real YAML parser (research.md §6) — mitigated by
  writing that convention down in the `"$comment"` clause of
  `contracts/skills-manifest-case.schema.json` (the schema's structural
  fields alone say nothing about line order, key order, or indentation) and
  exercising the script against the real manifest both ways (Verification
  Strategy step 3) before merge.

### IC-04 — Decision record (D1–D5, citations re-derived)

- **Purpose**: Author `conformance/DECISIONS.md`, carrying the programme's
  D1–D5 decisions verbatim in substance from issue #22 §11, with every
  `src/cli/index.ts` citation re-derived against muster's exact `v1.1.0` tag
  using the verified mapping in research.md §2 (binding constraint 4).
- **Relevant requirements**: FR-004.
- **Affected surfaces**: `conformance/DECISIONS.md` (new).
- **Sequencing/depends-on**: none functionally, but should not be committed
  before the citation re-derivation in research.md §2 is double-checked
  against the actual `v1.1.0` tag one more time at implementation time (tags
  are immutable, so this is a confirmation, not new research).
- **Risks**: none material — the re-derivation work is already done and
  verified in research.md §2; residual risk is transcription error when
  copying the table into prose, mitigated by copying the exact line numbers
  rather than re-typing from memory.

### IC-05 — README (local invocation + known gaps + pinned version)

- **Purpose**: Author `conformance/README.md`: the exact local invocation
  command, the two-step cache-warm-then-offline procedure, the pinned
  muster version (`1.1.0`), the two documented latent muster gaps (bare-cast
  manifest parsing; `expectations.violations` never compared), and — filled
  in only after Verification Strategy step 4 — the real CI run_id and
  wall-clock minutes.
- **Relevant requirements**: FR-006, NFR-001.
- **Affected surfaces**: `conformance/README.md` (new).
- **Sequencing/depends-on**: IC-01 through IC-04 (documents facts those
  concerns establish — the pinned version, the manifest's shape, the
  completeness check's existence, the decision record's location) and the
  Verification Strategy's step 4 (the CI timing entry cannot be written
  until a real workflow run exists).
- **Risks**: none material.

### IC-06 — CI workflow (FR-003) + completeness-check wiring (FR-007)

- **Purpose**: Author `.github/workflows/conformance.yml`: trigger on PR
  and push-to-main; run `garrison-hq/muster-action@v1` with `command:
  'skills run'`, `args: 'conformance/skills/manifest.yaml'`, `version:
  '1.1.0'`; then one additional step invoking
  `conformance/scripts/check-manifest-completeness.mjs` (FR-007's CI half).
- **Relevant requirements**: FR-003, FR-007, C-002, C-003.
- **Affected surfaces**: `.github/workflows/conformance.yml` (new — the
  sole file in lane-b's write scope).
- **Sequencing/depends-on**: IC-01 (manifest path must exist), IC-03 (script
  path/exit-code contract must be stable — satisfied by
  `contracts/completeness-check-cli-contract.md` alone; IC-06 does not need
  IC-03's source, only its contract).
- **Risks**: `garrison-hq/muster-action@v1`'s actual shipped `action.yml`
  input names are inferred from a design briefing, not verified against the
  live repository (research.md §5) — **the implementing agent must verify
  the real input schema before finalizing this file** and adjust field
  names if the shipped Action differs from `command`/`args`/`version`, and
  confirm the runner has a working `node` on `PATH` after the muster-action
  step completes, without relying on a `setup-node` step this plan does not
  add.

## Work-Package Outline (preview for `/spec-kitty.tasks` — not tasks.md)

The seed issue's two-lane decomposition is preserved, with lane-a's
`write_scope` widened by exactly one entry to resolve the FR-007
lane-collision the coordinator flagged (research.md §6):

```json
{
  "lanes": [
    { "lane_id": "lane-a", "wp_ids": ["WP01", "WP02"],
      "write_scope": [
        "conformance/skills/**",
        "conformance/DECISIONS.md",
        "conformance/README.md",
        "conformance/scripts/**"
      ],
      "depends_on_lanes": [], "parallel_group": 0 },
    { "lane_id": "lane-b", "wp_ids": ["WP03"],
      "write_scope": [".github/workflows/conformance.yml"],
      "depends_on_lanes": [], "parallel_group": 0 }
  ]
}
```

- **WP01** (lane-a): IC-01 + IC-02 + IC-03 — manifest, control fixture, and
  the FR-007 completeness script. IC-01+IC-02 share `manifest.yaml` and are
  grouped to avoid a same-file edit race; IC-03 is grouped with them because
  it depends on IC-01's manifest-authoring convention being settled first
  (plan.md IC-03 Sequencing), not because it shares a file.
  Before starting IC-01, the implementing agent must confirm
  `MOES-Media/spec-kitty#22` is assigned to the Human-in-Charge (DIR-012).
  `/spec-kitty.tasks` MUST render WP01's task list with IC-01 authored and
  committed before IC-03 begins; IC-02 may be authored alongside IC-01 or
  after.
- **WP02** (lane-a): IC-04 + IC-05 — decision record and README. Naturally
  sequenced after WP01 (documents WP01's outputs) though both are lane-a, so
  no cross-lane dependency is needed — a single lane can order its own WPs.
  Intra-WP02 order: IC-04 (DECISIONS.md) must be committed before IC-05
  (README.md) is authored — the README documents facts IC-04 establishes.
  Hold-open condition: WP02's prose may be authored early, but final
  review/approval must wait for Verification Strategy step 4 (a real
  `conformance.yml` run) to supply the CI `run_id` and wall-clock minutes
  before the README's timing entry is considered complete.
- **WP03** (lane-b): IC-06 — the workflow file, including the FR-007 wiring
  step. Depends only on `contracts/completeness-check-cli-contract.md` (this
  plan's artifact, already committed) for the script's interface — **not**
  on WP01's source file — so lane-b can start immediately in parallel with
  lane-a, exactly as the issue's original two-lane, zero-collision
  concurrency claim intended. No file appears in both lanes'
  `write_scope`.

**Build order**: WP01 → WP02 (same lane, sequential). WP03 is
lane-independent and parallel-safe from the start. Both lanes converge only
at the mission's final merge, by which point WP03's workflow step and
WP01's script must agree on the contract file above — no other coordination
is required.

## Complexity Tracking

*No entries — no charter gate violations require justification.*

No new runtime dependency is added anywhere: `@garrison-hq/muster` and
`garrison-hq/muster-action` are consumed as an external CLI (via `npx`) and
an external GitHub Action respectively, never added to `pyproject.toml`,
`package.json`, or any spec-kitty dependency manifest. The one Node script
this mission adds uses zero npm packages (Node stdlib only), so it does not
introduce a `package.json`/dependency-lock surface either.

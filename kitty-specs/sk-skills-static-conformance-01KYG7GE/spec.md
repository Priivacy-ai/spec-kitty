# Feature Specification: Skills Static Conformance Suite

**Mission**: `sk-skills-static-conformance-01KYG7GE` (mission_id `01KYG7GEG5F8HDJRGHGVFAX85B`)
**Created**: 2026-07-26
**Status**: Draft
**Mission Type**: software-dev
**Milestone**: muster ⇄ spec-kitty agent-conformance programme — wave 1, mission M1 (day-one static signal)
**Input**: Bootstrap `conformance/` in the spec-kitty fork: a muster skills-layer static manifest covering all 53 built-in `SKILL.md` files (agentskills.io frontmatter + layout rules), a PR-gating CI job via `muster-action@v1` exactly as shipped, and the programme decision record. Zero muster changes; proves the muster⇄spec-kitty seam end to end and yields a real conformance signal on day one.
**Seeds**: GitHub issue `MOES-Media/spec-kitty#22` (this mission's source description, including the full FR/C requirement table, work-package/lane decomposition, acceptance criteria, discrimination control, normative citations, risks, and the programme's D1–D5 design-decision record); the muster ⇄ spec-kitty agent-conformance programme plan.

---

## Overview

Spec-kitty ships 53 built-in agent skills under `src/doctrine/skills/*/SKILL.md`,
each following the open Agent Skills format published at agentskills.io. The
`muster` conformance harness (`@garrison-hq/muster`, an external npm CLI) already
ships a skills adapter that statically checks a `SKILL.md` skill's YAML
frontmatter and directory layout against that specification — but nothing in
the spec-kitty fork today invokes it. This mission is the first (wave 1) of a
larger, multi-repo muster ⇄ spec-kitty agent-conformance programme, and its job
is narrow and deliberately safe: prove the integration seam works end to end,
using only muster's existing, already-shipped static capability, with **zero
changes to muster itself**.

Concretely, this mission adds a `conformance/` tree to the spec-kitty fork
containing: a skills manifest enumerating one static conformance case per
built-in skill plus one deliberately-broken control case (to prove the suite
can actually fail, not just always pass), the programme's D1–D5 design-decision
record, a README documenting local invocation and known muster limitations,
and a GitHub Actions workflow that runs the suite via `muster-action@v1` on
every PR and push to `main`. It has been pre-verified that all 53 existing
skills already pass muster's three hard static gates (directory name matches
frontmatter `name`; `name` matches `^[a-z0-9-]+$` and is ≤64 chars;
`description` is ≤1024 chars), so a fully green suite is the expected day-one
outcome — this mission is infrastructure and a proof of the seam, not a
skill-fixing exercise.

Everything this mission does **not** do is deliberate and recorded: behavioral
skill-triggering conformance (muster's CLI unconditionally skips `type:
behavioral` cases today — see the "Relevant corrections" note under Dependencies
& Assumptions), profile or directive conformance, any change to muster or
`muster-action`, and any pull request to the upstream `Priivacy-ai/spec-kitty`
repository. Those are the concern of later programme missions (M2, M3, M5, M6,
M7, M8, M9), several of which this mission unblocks by establishing the
`conformance/` directory layout and CI skeleton they will land inside.

## User Scenarios & Testing

### Primary User Stories

1. **Spec-kitty contributor (PR gate)**: As a contributor opening a pull
   request against the spec-kitty fork, I want every built-in skill under
   `src/doctrine/skills/` to be automatically checked against the Agent Skills
   specification's static rules, so that a skill regression (a broken
   frontmatter field, a directory/name mismatch, an oversized description) is
   caught by CI before merge instead of discovered later.
2. **Programme operator (seam proof)**: As the operator driving the muster ⇄
   spec-kitty agent-conformance programme, I want a real, green, day-one
   conformance signal that proves the muster⇄spec-kitty integration seam works
   end to end — manifest authoring, path resolution, offline CLI invocation,
   and CI wiring via the shipped GitHub Action — before any later mission adds
   behavioral, profile, or directive conformance on top of it.
3. **Later-mission author (M3/M6/M7)**: As the author of a subsequent
   spec-kitty-side conformance mission, I want the `conformance/` directory
   layout, the CI workflow skeleton, and the programme's decision record
   already in place, so my mission lands inside an established structure
   without re-deriving path-resolution conventions or CI wiring from scratch.

### Acceptance Scenarios

#### Static manifest coverage (FR-001, FR-002)

1. **Given** the 53 built-in skills under `src/doctrine/skills/*/SKILL.md`,
   **When** `conformance/skills/manifest.yaml` is authored, **Then** it
   contains exactly one `type: static` case per built-in skill, each with
   `profile: base`, `expectations: {ok: true, violations: []}`, and a
   `skillDir` expressed relative to the manifest's own directory (no `../..`
   path segments), consistent with muster's manifest-relative path resolution.

   Clarification: "`../..`-free" means the path must not escape the
   repository checkout (no segment resolving above the repo root), not that
   the literal substring `../..` is forbidden. `skillDir` values necessarily
   read `../../src/doctrine/skills/<name>`, satisfying manifest-relative
   resolution without escaping the checkout.
2. **Given** that manifest, **When** the muster CLI's package is first
   cache-warmed — either `npm install --no-save @garrison-hq/muster@<pinned>`
   with network access enabled, or by pinning `@garrison-hq/muster` as a
   `devDependency` restored via `npm ci` — and then `npx @garrison-hq/muster
   skills run conformance/skills/manifest.yaml` is run with network access
   disabled, **Then** the process exits `0` and every case is reported
   conformant. This two-step cache-warm-then-offline-run procedure is
   documented in `conformance/README.md`.

#### CI gating (FR-003)

3. **Given** a pull request or a push to `main` on the spec-kitty fork,
   **When** the `.github/workflows/conformance.yml` workflow runs,
   **Then** it invokes `garrison-hq/muster-action@v1` with `command: skills
   run` against the manifest and the job succeeds only if the suite exits `0`.

#### CI timing measurement (NFR-001)

4. **Given** a real run of the `conformance.yml` workflow on GitHub Actions,
   **When** the workflow completes, **Then** its actual wall-clock minutes for
   that run's `run_id` are recorded in `conformance/README.md`, per this
   project's measured-not-asserted CI-budget policy.

#### Decision record (FR-004)

5. **Given** the programme's D1–D5 design decisions (persona adapter vs.
   projector; the behavioral-endpoint seam; rule-extraction authoring; mission
   placement across repos; the rubric surface), **When**
   `conformance/DECISIONS.md` is written, **Then** it records all five
   decisions verbatim, each with its cited file:line evidence, as the
   programme's decision record of authority for this mission.

#### Discrimination control (FR-005)

6. **Given** a deliberately broken skill fixture under
   `conformance/skills/control/` (its frontmatter `name` does not match its
   directory name), **When** the manifest declares that case with
   `expectations: {ok: false, ...}` and the suite runs, **Then** the case
   passes — because the harness's actual result (`ok: false`) matches the
   declared expectation, proving the suite can register a failure rather than
   trivially reporting success on everything.
7. **Given** that same control case, **When** its declared expectation is
   manually flipped to `ok: true` (a documented manual check, not part of CI),
   **Then** the suite run exits non-zero, because the harness's actual result
   no longer matches the (now wrong) expectation — this is the manual proof of
   discrimination described in AC-2.

#### Manifest completeness (FR-007)

8. **Given** the true, unmodified `src/doctrine/skills/*` tree (53 directories)
   and a `conformance/skills/manifest.yaml` that correctly enumerates all 53
   skill cases plus the one FR-005 control case (54 `type: static` cases
   total), **When** the FR-007 completeness check runs in CI, **Then** it
   exits `0` because the manifest's static-case count equals the skill
   directory count plus one.
9. **Given** a deliberately induced mismatch — either a skill directory added
   or removed from `src/doctrine/skills/*` without a matching manifest edit,
   or the check pointed at a manifest with a case deliberately deleted —
   **When** the completeness check runs, **Then** it exits non-zero and its
   failure message names the specific missing or extra skill(s) by directory
   name, not just a bare count mismatch. This is the manual/CI-observed proof
   that the check discriminates rather than trivially passing (mirrors the
   FR-005 control's proof obligation).

#### Documentation of local invocation and known gaps (FR-006)

10. **Given** a developer who wants to run the suite locally before opening a
   PR, **When** they read `conformance/README.md`, **Then** they find the
   exact local invocation command, the two-step cache-warm-then-offline-run
   procedure (warm via `npm install --no-save @garrison-hq/muster@<pinned>`
   with network enabled, or a pinned `devDependency` restored via `npm ci`,
   before running the network-disabled `skills run` invocation), the pinned
   muster version in use, and a plain statement of the two known muster
   limitations that affect this suite (the manifest is parsed without schema
   validation; `expectations.violations` is never compared, only
   `expectations.ok`).

#### Scope boundary (C-001, C-002, C-003)

11. **Given** the completed mission diff, **When** it is reviewed, **Then** it
   touches only paths under `conformance/**` and `.github/workflows/**` — no
   spec-kitty runtime source is changed.
12. **Given** a pull request opened from a fork of spec-kitty (no repository
    secrets available to the workflow), **When** the conformance workflow runs,
    **Then** it completes successfully without requesting or requiring any
    secret, because the static path is fully offline.
13. **Given** the workflow's `muster` version input, **When** it is inspected,
    **Then** it is an exact version string (e.g. `1.1.0`), never a floating
    range (`^`, `~`, `latest`), so the same commit always resolves the same
    muster build.

### Edge Cases

- **Upstream skill-tree move**: if spec-kitty later moves
  `src/doctrine/skills/` to a different path, every `skillDir` in the manifest
  breaks at once and the suite exits loudly (non-zero / exit `2`) rather than
  silently passing or silently skipping cases — this is an accepted, low-cost
  risk (trivial path fix), not a defect to design around now.
- **A future skill violates a static gate**: this is the suite working as
  intended (a true positive), not a mission risk; no special handling is
  required.
- **Manifest/skill-set drift**: if a new built-in skill is added upstream (or
  an existing one removed/renamed) without a corresponding manifest edit, the
  manifest would silently under- or over-count the built-in skill set — muster
  itself still does not validate that the manifest's case count matches the
  skill directory's actual contents (this remains one of the two documented
  latent muster gaps: the manifest is parsed with a bare cast, no schema
  validation, and this mission does not fix muster). This mission does,
  however, close the drift vector on the spec-kitty side: **FR-007** adds a
  completeness check (manifest `type: static` case count vs.
  `src/doctrine/skills/*` directory count, offset by the +1 FR-005 control
  case) that names the specific missing/extra skill(s) on mismatch. It is
  buildable entirely within `conformance/**` plus one wiring line in
  `.github/workflows/conformance.yml`, and is NOT forbidden by the scope
  guard, which excludes only muster/muster-action source changes. (This was
  originally deferred as candidate FR-007 for a follow-up mission; the
  operator reversed that deferral after the spec gate — see FR-007's
  provenance note in the Requirements table above.)
- **`expectations.violations` is ignored**: muster's CLI only compares
  `expectations.ok`, never `expectations.violations`, so a case's declared
  `violations: []` list is documentation only and is not itself verified by
  the harness. This is the second documented latent gap and is recorded, not
  fixed, per FR-006 and the scope guard.
- **Control-case regression**: if the control fixture under
  `conformance/skills/control/` is accidentally "fixed" (its name/directory
  mismatch resolved) without updating its manifest expectation, the case
  would newly report `ok: true` against a declared `ok: false` expectation and
  the suite would fail loudly — this is a beneficial fail-safe, not a risk.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `conformance/skills/manifest.yaml` enumerates one `type: static` case per built-in skill (53 cases), `profile: base`, `expectations: {ok: true, violations: []}`, `skillDir` relative to the manifest (`../..`-free; resolution per `src/cli/index.ts:1316`). | Proposed |
| FR-002 | `npx @garrison-hq/muster skills run conformance/skills/manifest.yaml` exits 0, fully offline. | Proposed |
| FR-003 | A workflow `.github/workflows/conformance.yml` runs FR-002 via `garrison-hq/muster-action@v1` (`command: skills run`) on every PR and push to main. | Proposed |
| FR-004 | `conformance/DECISIONS.md` records D1–D5 verbatim from the programme plan, with the file:line evidence, as the programme decision record. | Proposed |
| FR-005 | One rigged-broken control case ships under `conformance/skills/control/` (e.g. frontmatter name ≠ dirname) with `expectations: {ok: false, ...}` — the static discrimination analogue, proving the suite can fail (case passes because expectation matches actual, per `passed = ok === expectations.ok`, `src/cli/index.ts:1279`). | Proposed |
| FR-006 | `conformance/README.md` documents local invocation, the known muster gaps that affect this suite (manifest unvalidated; `expectations.violations` ignored), and the pinned muster version. | Proposed |
| FR-007 | **[Added post-spec-gate by explicit operator decision, reversing this document's original deferral; not sourced from seed issue `MOES-Media/spec-kitty#22` §5, whose FR table enumerates only FR-001–FR-006 — same as this spec's NFR-001/NFR-002, which the issue also does not contain.]** A CI step verifies manifest completeness: the count of `type: static` cases in `conformance/skills/manifest.yaml` equals the count of skill directories matching `src/doctrine/skills/*/SKILL.md`, plus one for the FR-005 rigged control case under `conformance/skills/control/`. A mismatch fails the job with a message naming the missing or extra skills. | Proposed |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | The conformance CI job gives fast feedback on pull requests. | No a-priori numeric ceiling asserted at spec time. At implement time, record the workflow's actual wall-clock minutes from a real GitHub Actions run_id in `conformance/README.md`, per this project's measured-not-asserted CI-budget policy (`docs/plans/testing/ci-job-timings.md`; `docs/development/testing-flakiness.md`). Any hard-failing gate on wall-clock must derive from that measured baseline. | Proposed |
| NFR-002 | The static suite's result is deterministic given a pinned muster version. | Repeated runs of `npx @garrison-hq/muster@<pinned> skills run conformance/skills/manifest.yaml` against the same commit produce identical `ok`/exit-code results, with zero network calls in the run path. | Proposed |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | No SK runtime code changes: the diff touches only `conformance/**` and `.github/workflows/**`. | Proposed |
| C-002 | The workflow needs no secrets and must pass on fork PRs (static path is offline — BRIEF constraint 2). | Proposed |
| C-003 | The muster version in CI is pinned (exact `version:` input, not a floating range) so the suite is byte-reproducible. | Proposed |

### Key Entities

- **Skills manifest** (`conformance/skills/manifest.yaml`): declares one
  `type: static` case per built-in skill plus the one control case; each case
  carries `profile`, `skillDir`, and `expectations`.
- **Static case**: a manifest entry pointing at one skill directory, expected
  to be conformant (`ok: true, violations: []`).
- **Control case**: a manifest entry pointing at a deliberately broken fixture
  under `conformance/skills/control/`, expected to be non-conformant (`ok:
  false`); the mechanism by which the suite proves it can discriminate rather
  than trivially pass.
- **Decision record** (`conformance/DECISIONS.md`): the programme's D1–D5
  design decisions, verbatim with file:line evidence, as the durable record of
  why the programme is shaped the way it is.
- **Conformance workflow** (`.github/workflows/conformance.yml`): the
  GitHub Actions job that gates PRs and pushes to `main` on the static suite's
  exit code via `garrison-hq/muster-action@v1`.
- **README** (`conformance/README.md`): local-invocation instructions, the two
  documented latent muster gaps affecting this suite, and the pinned muster
  version.
- **Completeness check** (FR-007): a CI-native check, independent of the
  muster CLI itself, that asserts `conformance/skills/manifest.yaml`'s
  `type: static` case count equals `src/doctrine/skills/*` directory count + 1
  (the FR-005 control case) and names the specific skill(s) responsible when
  the two diverge. Lives entirely under `conformance/**`; wired into
  `.github/workflows/conformance.yml` as one additional step.

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | A person or CI system can run one local command and get a pass/fail conformance signal for all 53 built-in skills against the Agent Skills specification's static rules, with no network access required. |
| SC-002 | Every pull request and every push to `main` automatically receives this conformance signal with no operator action and no repository secrets required. |
| SC-003 | The suite provably discriminates: a deliberately broken skill fixture is reported non-conformant, and manually flipping its declared expectation to "conformant" reliably flips the suite's exit code to failure. |
| SC-004 | The programme's five foundational design decisions (D1–D5) are durably recorded in a reviewable, versioned document rather than living only in issue or conversation history. |
| SC-005 | The exact conformance-tool version used in CI is pinned and documented, so the suite's result is reproducible on the same commit regardless of when or where it is run. |
| SC-006 | The manifest's case count is checked against the actual `src/doctrine/skills/*` tree on every CI run; a manifest/skill-set mismatch is caught and named by directory, never silently ignored (FR-007). |

## Dependencies & Assumptions

- **Depends on**: none. This is a wave-1 mission with no upstream mission
  dependency and can start immediately.
- **Unblocks**: M3 (`MOES-Media/spec-kitty#23`), M6 (`MOES-Media/spec-kitty#25`),
  M7 (`MOES-Media/spec-kitty#26`) — every later spec-kitty-side conformance
  mission lands inside the `conformance/` directory layout and CI skeleton this
  mission creates.
- **External dependencies**: the published `@garrison-hq/muster` npm package
  (pinned exact version) and the `garrison-hq/muster-action@v1` GitHub Action,
  used exactly as shipped, with no muster or muster-action source changes.
- **Assumption (pre-verified)**: all 53 existing built-in skills already pass
  muster's three hard static gates (directory name matches frontmatter `name`;
  `name` matches `^[a-z0-9-]+$` and is ≤64 characters; `description` is ≤1024
  characters) — confirmed by direct scan of the checkout. The two skills using
  `argument-hint` in frontmatter pass because the frontmatter schema declares
  `additionalProperties: true` (`src/adapters/skills/schema.ts:18-33`). A fully
  green day-one suite is therefore the expected, not merely hoped-for, outcome.
- **Assumption**: `skillDir` and other manifest-relative paths resolve
  relative to the manifest file's own directory, per muster's path-resolution
  behavior at `src/cli/index.ts:1316`.
- **Relevant corrections carried from the programme's verification pass**
  (context for FR-006 and the scope guard, not requirements to act on): muster's
  `doSkillsRun` unconditionally records every `type: behavioral` case as
  `{passed: true, skipped: true}` and never constructs a model client
  (`src/cli/index.ts:1330-1334`) — behavioral skill-triggering cases cannot run
  through the CLI until a later muster-side mission (M5) ships; and the skills
  manifest is parsed with a bare type cast (no schema validation) and
  `expectations.violations` is never compared, only `expectations.ok`
  (`src/cli/index.ts:1279,1319`) — both are documented as known limitations in
  `conformance/README.md`, not fixed in this mission.
- **Citation drift**: All muster-repo file:line citations in this spec and the
  seed issue were computed against muster HEAD (`v1.1.0-1-g8953ee8`), one
  commit past the `v1.1.0` tag actually publishable/pinnable under C-003. WP02
  must re-derive every `src/cli/index.ts` citation (FR-004's D1–D5 evidence,
  and the correction-#4 note) against the exact version pinned in the CI
  workflow before committing `DECISIONS.md`.
- **Out of scope** (see Scope Guard below): behavioral/trigger conformance
  cases; profile or directive checks; any change to muster or
  `muster-action` source; any pull request to the upstream
  `Priivacy-ai/spec-kitty` repository; fixing the two latent muster gaps noted
  above.

## Scope Guard

Carried verbatim in substance from the mission source (issue
`MOES-Media/spec-kitty#22`, section 4) — not in this mission:

- Behavioral/trigger cases (muster's CLI skips `type: behavioral` cases
  unconditionally today).
- Profile or directive checks.
- Any muster or `muster-action` change.
- Any upstream (`Priivacy-ai/spec-kitty`) pull request — this mission lands
  fork-side only (`MOES-Media/spec-kitty`); per the programme's open-question
  resolution (OQ-2), an upstream PR is deferred until a later mission (M4)
  demonstrates a real finding worth upstreaming.
- Fixing the two latent muster gaps recorded above (manifest schema
  non-validation; `expectations.violations` non-comparison) — recorded in
  `conformance/README.md`, not fixed here.

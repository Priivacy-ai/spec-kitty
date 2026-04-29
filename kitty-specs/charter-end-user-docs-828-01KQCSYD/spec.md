# Charter End-User Docs Parity (#828)

Mission type: documentation
Issue: https://github.com/Priivacy-ai/spec-kitty/issues/828
Target repository: Priivacy-ai/spec-kitty
Target branch: main

## Objective

Bring Spec Kitty end-user documentation to parity with the shipped Charter-era product. The result must be a documentation PR that an operator can use to understand and run current Charter workflows without reading source code.

This mission must follow the documentation mission discipline:

1. discover
2. audit
3. design
4. generate
5. validate
6. publish
7. accept

## Context

The Charter epic shipped product surface that is not yet coherently documented:

- DRG-backed governance context.
- Unified charter bundle validation.
- Charter synthesis and resynthesis into project-local doctrine.
- Profile/action invocation trails.
- Glossary runtime integration.
- Mission composition for built-in and custom missions.
- Retrospective learning loop, summary, and synthesizer apply/dry-run flows.

The current docs still lean on the older 2.x interview/generate/sync mental model and omit or under-document the current operator path.

## Audiences

- New operator using Spec Kitty on a project for the first time.
- Existing operator upgrading from older 2.x or early 3.x Charter docs.
- Agent or host integrator who needs governed profile/action invocation semantics.
- Project maintainer reviewing generated doctrine, glossary updates, and retrospective synthesis.
- Documentation contributor maintaining Divio-shaped docs.

## User Outcomes

- A new user can initialize governance, validate the charter bundle, synthesize doctrine, inspect status/lint/provenance, run one governed mission action, and understand the artifacts produced.
- An operator can tell which files are authoritative human policy versus generated doctrine consumed by runtime context.
- An integrator can explain the `(profile, action, governance-context)` primitive and the profile invocation lifecycle.
- A mission operator can run software-dev, research, documentation, and custom missions under `spec-kitty next` and interpret blocked decisions.
- A maintainer can use retrospective summary and synthesizer dry-run/apply flows safely.
- A user can troubleshoot stale bundles, missing doctrine, compact-context limitations, retrospective gate failures, and synthesizer rejection.

## Functional Requirements

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-001 | A gap analysis (`gap-analysis.md`) **must** be produced with a Divio coverage matrix covering all areas listed in the Audit scope. Each cell must be classified as `present-current`, `present-stale`, `missing`, or `intentionally-deferred`. Stale/missing cells must cite both the stale doc path and the source-of-truth code/spec path. | P0 | Draft |
| FR-002 | A documentation information architecture plan (`plan.md`) **must** be produced before any content is written, resolving the required design decisions listed in the Design scope. | P0 | Draft |
| FR-003 | A Charter current-state overview doc **must** be produced or updated to accurately describe the current synthesis/DRG model and to distinguish human-policy files from generated-doctrine files. | P0 | Draft |
| FR-004 | `docs/how-to/setup-governance.md` **must** teach the current recommended governance setup flow — including bundle validation and doctrine synthesis — and **must not** describe only the older interview/generate/sync flow. | P0 | Draft |
| FR-005 | Docs covering Charter synthesis, resynthesis (including dry-run, apply, status, lint, provenance, idempotency, staging, and recovery) **must** be produced or updated. | P0 | Draft |
| FR-006 | Docs covering DRG-backed governance context, action identities, bootstrap versus compact context, and known limitations (including compact-context behavior from #787 if still open) **must** be produced. | P0 | Draft |
| FR-007 | Docs covering governed profile invocation — `ask`, `advise`, `do`, `profile-invocation complete`, evidence/artifact correlation, and lifecycle trails — **must** be produced so that an operator can follow the invocation lifecycle without reading source code. | P0 | Draft |
| FR-008 | Docs covering mission composition under Charter (`spec-kitty next --agent <agent>`, composed step contracts, prompt resolution, blocked decisions, and Charter context loading) **must** be produced. | P0 | Draft |
| FR-009 | Documentation mission type docs **must** use the current phases: `discover`, `audit`, `design`, `generate`, `validate`, `publish`, `accept`. Docs **must not** describe phases from an earlier model. | P0 | Draft |
| FR-010 | Retrospective learning loop docs **must** be produced, covering HiC/autonomous behavior, skip semantics, facilitator failures, summary, synthesizer dry-run/apply, proposal kinds, conflicts, staleness, provenance, and exit codes. These docs **must** be reachable from navigation and split into appropriate Divio shapes. | P0 | Draft |
| FR-011 | Glossary docs **must** explain the runtime, DRG, project-local, and retrospective-proposal relationships so that a maintainer can understand what is authoritative human policy versus generated state. | P1 | Draft |
| FR-012 | A CLI reference **must** be produced or updated covering the Charter-era command surfaces listed in issue #828, verified against current `--help` output or source code. | P0 | Draft |
| FR-013 | Migration docs **must** be produced covering the upgrade path from older 2.x/early-3.x Charter projects. | P1 | Draft |
| FR-014 | Troubleshooting docs **must** be produced covering the following failure modes: stale bundle, missing doctrine, compact-context limitations, retrospective gate failures, and synthesizer rejection. | P1 | Draft |
| FR-015 | A release handoff artifact **must** be produced listing pages added/updated, command snippets validated, docs tests run, known limitations accepted, and any follow-up docs issues. | P0 | Draft |
| FR-016 | All added or changed pages **must** appear in the relevant table-of-contents entries and pass the docs integrity checks available in the repo. | P0 | Draft |
| FR-017 | A new user **must** be able to follow one tutorial from governance setup through Charter synthesis, one governed mission action, retrospective summary, and next-step learning, without reading source code. | P0 | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | Docs link/integrity checks and `tests/docs/` tests **must** pass with zero failures after all changes are applied. | 0 test failures | Draft |
| NFR-002 | All interactive command snippets included in the docs **must** be parseable and, where safe to execute, runnable against a temporary project without polluting the source repository. | 100% of interactive snippets either execute successfully or are explicitly marked as requiring external services | Draft |
| NFR-003 | Documentation **must not** claim that custom mission retrospective execution is deferred when the current shipped product supports it. | No false deferral claims present in any changed page | Draft |
| NFR-004 | Documentation mission phases documented in the generated content **must** match the phases declared in `mission-runtime.yaml`. | Exact phase-name match | Draft |
| NFR-005 | The Charter setup guide **must** be executable in a fresh temporary repository or **must** explicitly mark any command that requires an external service. | No undocumented external-service dependencies in the setup guide | Draft |

## Constraints

| ID | Constraint | Rationale | Status |
|---|---|---|---|
| C-001 | This mission **must not** produce another implementation spec for Charter behavior; it is strictly a documentation mission. | Scope is end-user docs parity, not product design. | Active |
| C-002 | This mission **must not** include #469 Phase 7 or additional #827 E2E canaries. | That work is tracked separately and must not be mixed into this docs PR. | Active |
| C-003 | Any validation command that touches hosted auth, tracker, or sync behavior on this machine **must** be run with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. | Machine rule required for this environment. | Active |
| C-004 | CLI reference entries **must** match the current shipped command surface. Screenshots **must not** be used as the primary source of truth for CLI behavior. | References must stay verifiable and non-stale. | Active |
| C-005 | Known product defects **must not** be hidden with vague prose. They must be documented clearly and linked to their open issues. | Users deserve accurate information about current limitations. | Active |

## Success Criteria

1. A new user can follow one end-to-end tutorial (setup → Charter synthesis → one governed mission action → retrospective summary → next-step learning) without reading source code.
2. `docs/how-to/setup-governance.md` teaches the current recommended flow and passes a fresh-repo execution check.
3. Documentation mission phases in all changed docs match `mission-runtime.yaml` exactly.
4. CLI reference entries for all covered Charter-era commands are verified against current `--help` output or source code with no discrepancies.
5. All changed and added pages pass the repo docs link/integrity checks and `tests/docs/` suite with zero failures.
6. The release handoff artifact is complete and the PR body references the artifact.

## Scope

### Discover

Produce a documentation spec or discovery note that names audiences, user outcomes, source-of-truth inputs, and explicit non-goals. Use issue #828 as the binding brief.

### Audit

Produce `gap-analysis.md` with a Divio coverage matrix. Minimum areas:

- Charter overview and mental model.
- Governance setup and bootstrap.
- Charter synthesis, resynthesis, status, and lint.
- Unified charter bundle and canonical paths.
- DRG-backed action context.
- Profile invocation and invocation trails.
- `spec-kitty next` with composition and built-in missions.
- Research mission under Charter.
- Documentation mission under Charter.
- Custom missions and retrospective marker/lifecycle.
- Glossary as doctrine and runtime surface.
- Retrospective learning loop and synthesizer.
- Cross-mission retrospective summary.
- Event, sync, and SaaS implications at operator level.
- Migration from older Charter docs.
- Troubleshooting and failure modes.
- CLI reference accuracy.

Each matrix cell must be classified as `present-current`, `present-stale`, `missing`, or `intentionally-deferred`. Stale/missing cells must cite both the stale docs path and the source-of-truth code/spec path.

### Design

Produce `plan.md` with the Divio information architecture and TOC strategy before writing content.

Required design decisions:

- Keep or replace the current `docs/2x/` section name for the shipped 3.x product language.
- Split Charter docs across tutorial, how-to, reference, and explanation pages.
- Integrate `docs/retrospective-learning-loop.md` into navigation.
- Keep CLI reference synchronized with the current command surface.
- Link Charter docs to mission docs, glossary docs, invocation trail docs, and host-surface parity docs without duplicating core explanations.
- Present known limitations, especially compact-context behavior from #787 if still open.

### Generate

Update or add end-user docs covering:

- Charter current-state overview and authoritative file model.
- Current governance setup flow.
- Synthesis and resynthesis, including dry-run, apply, status, lint, provenance, idempotency, staging, and recovery.
- DRG-backed governance context, action identities, bootstrap versus compact context, and known limitations.
- Governed profile invocation: `ask`, `advise`, `do`, `profile-invocation complete`, evidence/artifact correlation, and lifecycle trails.
- Mission composition under Charter: `spec-kitty next --agent <agent>`, composed step contracts, prompt resolution, blocked decisions, and Charter context loading.
- Documentation mission type with current phases: `discover`, `audit`, `design`, `generate`, `validate`, `publish`, `accept`.
- Glossary relationship to doctrine, runtime context, generated project state, and retrospective proposals.
- Retrospective learning loop: HiC/autonomous behavior, skip semantics, facilitator failures, summary, synthesizer dry-run/apply, proposal kinds, conflicts, staleness, provenance, and exit codes.
- CLI reference for Charter-era commands listed in #828.
- Migration docs for older 2.x/early-3.x Charter projects.
- Troubleshooting docs for the failure modes listed in #828.

### Validate

Validation must be evidence-based. Required checks:

- Run docs link/integrity checks available in the repo.
- Run docs tests under `tests/docs/`.
- Verify changed pages are reachable from TOCs.
- Verify no changed page contains stale `TODO: register in docs nav` text.
- Verify command snippets parse and, where safe, run in a temp project.
- Verify CLI reference flags match current `--help` for covered commands.
- Verify docs do not claim custom mission retrospective execution is deferred if current product supports it.
- Verify documentation mission phases match `mission-runtime.yaml`.
- Verify the Charter setup guide is executable in a fresh temp repo or explicitly marks commands that require external services.
- Verify no source-repo pollution from dogfood or documentation smoke commands.

### Publish

Produce a release handoff artifact listing:

- Pages added or updated.
- Command snippets validated.
- Docs tests run.
- Known limitations accepted.
- Follow-up docs issues, if any.

Update TOCs and any docs release notes/changelog if maintained.

## Acceptance Criteria

- A new user can follow one tutorial from setup through Charter synthesis, one governed mission action, retrospective summary, and next-step learning without reading source code.
- The Charter overview accurately describes the current synthesis/DRG model.
- `docs/how-to/setup-governance.md` teaches the current recommended flow, not only interview/generate/sync.
- Documentation mission docs use the current phases: `discover`, `audit`, `design`, `generate`, `validate`, `publish`, `accept`.
- Retrospective learning docs are reachable from navigation and split into appropriate Divio shapes.
- CLI reference covers the Charter-era command surfaces in #828 and is checked against current CLI help or code.
- Profile invocation and invocation trails are documented for operators.
- Glossary docs explain runtime, DRG, project-local, and retrospective relationships.
- Migration/troubleshooting docs cover stale bundle, missing doctrine, compact context, retrospective gate, and synthesizer failure modes.
- All changed pages are included in TOCs and pass docs validation.
- The PR includes validation evidence and any command-snippet smoke checks.

## Non-Goals

- Do not create another implementation spec for Charter behavior.
- Do not hide known product defects with vague prose; document limitations clearly and link issues.
- Do not update only architecture/development docs while leaving user-facing docs stale.
- Do not hand-wave CLI references; they must match the shipped command surface.
- Do not use screenshots as the primary source of truth for CLI behavior.
- Do not do #469 Phase 7 or additional #827 E2E canaries in this mission.

## Machine Rule

If any validation command touches hosted auth, tracker, or sync behavior on this computer, run it with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.

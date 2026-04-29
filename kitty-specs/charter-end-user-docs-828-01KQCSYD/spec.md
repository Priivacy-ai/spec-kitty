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

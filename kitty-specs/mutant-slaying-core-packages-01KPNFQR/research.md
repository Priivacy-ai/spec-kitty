# Research Notes: Mutant Slaying in Core Packages

**Mission**: `mutant-slaying-core-packages-01KPNFQR`
**Date**: 2026-04-20

This mission has no open technical unknowns — every methodology, tool, and pattern is codified in the shipped doctrine artefacts referenced from `spec.md` (Doctrine References section). The two small decisions below were worked through during plan authoring and are recorded here for audit.

## R-001: Residual list artefact format

**Decision**: Residuals are recorded as (a) inline `# pragma: no mutate` annotations on the source lines for accepted-equivalent mutants, each with a one-line rationale comment, **and** (b) a per-WP bullet under `docs/development/mutation-testing-findings.md` under a subheading for that phase. Two surfaces, complementary: inline annotations drive mutmut itself; the findings doc is the auditable trail.

**Rationale**:
- `# pragma: no mutate` is what mutmut reads; without it the survivor keeps reappearing in results.
- A per-WP bullet in the findings doc lets a reviewer audit the "why" without reading source comments.
- Two surfaces accept the redundancy cost in exchange for not losing lineage when a source line changes.

**Alternatives considered**:
- **Per-WP YAML sidecar** (`kitty-specs/<mission>/residuals/<sub-module>.yaml`) — rejected. Format proliferation. `tests/doctrine/` and the schema validators already carry non-trivial YAML surface; adding mission-specific residual YAMLs invites parse-script churn for little gain.
- **Inline annotation only** (no findings doc entry) — rejected. Loses the audit trail when the source line is later edited; the annotation may move or disappear while the decision lineage stays important.
- **Findings doc only** (no inline annotation) — rejected. mutmut keeps re-reporting the survivor on every run, noise that drowns the actionable items.

## R-002: Baseline re-sample trigger

**Decision**: Manual `mutmut run` (full or scoped) at each phase boundary, with the snapshot date recorded in `docs/development/mutation-testing-findings.md`. NFR-007 caps staleness at 7 days for Phase 2/3 planning gates. No automation.

**Rationale**:
- Mission is local-only per C-001 and ADR 2026-04-20-1. Automating a mutmut run would contradict that constraint.
- A full run currently takes 1–2 hours; scoped reruns take 5–15 minutes. Both are acceptable as manual developer actions at phase boundaries, not at every WP boundary.
- The `.meta` cache in `mutants/` is durable across runs, so a phase boundary re-sample is additive (re-tests pending mutants and any whose sources changed), not destructive.

**Alternatives considered**:
- **Cron job** — rejected. Violates C-001. Also impractical: a local cron would produce stale results if the developer isn't at their machine; a shared cron would require shared infrastructure.
- **Pre-commit hook re-sampling the touched sub-module** — rejected as too expensive per-commit (5–15 min adds up). Could be revisited in a future ticket as an opt-in `pre-push` hook.
- **CI job on a nightly schedule** — rejected as out of scope per ADR 2026-04-20-1. Would require merging the mutation-testing gate into CI, which the ADR explicitly defers.

## Non-decisions (intentional)

- **Target mutation score values** — already set by NFR-001/NFR-002 in the spec. No research needed.
- **Which sub-modules to include** — already enumerated by FR-001 through FR-012. No research needed.
- **Mutation operator library** — already enumerated in `PYTHON_MUTATION_TOOLS.md`. No research needed.
- **Test-annotation conventions** — already observed from existing test files and recorded in `spec.md` (Test Annotation Conventions subsection). No research needed.
- **Sandbox-incompatibility handling** — already governed by the `non_sandbox` / `flaky` marker taxonomy from ADR 2026-04-20-1. No research needed.

All `[NEEDS CLARIFICATION]` markers from plan authoring resolved. Phase 1 may proceed.

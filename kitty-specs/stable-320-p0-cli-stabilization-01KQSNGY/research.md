# Research: 3.2.0 Stable P0 CLI Stabilization

## Decision: Diagnose #967 before changing status semantics

**Rationale**: The reported hang could come from bootstrap fixtures, event emission, background sync hooks, event-loop lifecycle, file locking, or teardown. A timeout alone would make CI bounded but would not make the CLI more trustworthy.

**Alternatives considered**:

- Add only a global test timeout. Rejected because it does not repair the underlying nondeterminism.
- Rewrite status storage or event emission. Rejected as too broad for a stable-release blocker unless the investigation proves a small runtime fix is necessary.

## Decision: Use fail-closed latest-review-cycle semantics for #904

**Rationale**: The product decision requires Spec Kitty to treat the latest review-cycle artifact as authoritative unless a non-rejected terminal verdict or explicit durable override supersedes it. This is the safest stable-release posture because it prevents a mission from appearing complete while review evidence says it failed.

**Alternatives considered**:

- Emit warnings while allowing transitions. Rejected by the spec.
- Check all historical review artifacts equally. Rejected because old rejected cycles can be legitimately superseded by later approvals.

## Decision: Persist overrides as structured evidence

**Rationale**: Operators need an intentional escape hatch, but later reviewers must be able to distinguish a valid arbiter decision from accidental state drift. Structured metadata or a linked override artifact gives durable auditability.

**Alternatives considered**:

- Accept a command-line flag without persistence. Rejected because it leaves no proof trail.
- Edit the rejected artifact manually. Rejected because it obscures the original review result.

## Decision: Treat package ownership as mandatory for checklist cleanup

**Rationale**: The charter explicitly warns against broad `spec-kitty.*` name matching in mutating flows. Retired checklist cleanup must only remove known package-managed files, or preserve unknown files and warn.

**Alternatives considered**:

- Delete every `spec-kitty.checklist*` file by name. Rejected as unsafe for user customizations.
- Keep checklist in active registries for compatibility. Rejected because #968 requires it to remain retired.

## Decision: Validate generated skill frontmatter through fresh generation

**Rationale**: Snapshot tests can prove templates look correct, but #964 is about generated host-visible files. The regression test must inspect fresh generated `SKILL.md` output, including Codex/global skill paths.

**Alternatives considered**:

- Patch only `.agents/skills/spec-kitty.advise/SKILL.md`. Rejected because generated output would regress on the next install.
- Rely on manual smoke testing. Rejected because stable release needs repeatable evidence.

## Decision: Keep default validation local and offline

**Rationale**: The mission is CLI stabilization and does not need hosted auth, tracker, SaaS sync, or network access. Local deterministic tests reduce release risk and avoid coupling P0 CLI fixes to hosted infrastructure.

**Alternatives considered**:

- Exercise SaaS sync during default validation. Rejected as out of scope. If any hosted path is intentionally touched on this computer, it must run with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.

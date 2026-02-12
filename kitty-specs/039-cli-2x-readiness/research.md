# Research: CLI 2.x Readiness Sprint

**Feature**: 039-cli-2x-readiness
**Date**: 2026-02-12

## R1: Sync Infrastructure Location and State

**Decision**: Target the existing 2.x branch (not main). Sync infrastructure (13 modules in `src/specify_cli/sync/`) already exists on 2.x.

**Rationale**: 2.x is 588 commits diverged from main with ~370 files changed. The sync stack was deliberately removed from main at v0.13.27. Reintroducing it to main adds avoidable risk. 2.x is versioned as 2.0.0a3 and already contains the authenticated SaaS workflow.

**Alternatives considered**:
- Merge sync back into main: Rejected — high merge conflict risk (306 vs 588 commit divergence), main intentionally sync-free
- Build from scratch on main: Rejected — duplicates existing work on 2.x
- Cherry-pick individual modules: Rejected — cross-module dependencies make selective cherry-pick fragile

## R2: Batch Ingest Failure Root Cause

**Decision**: The "Synced: 0 Errors: 105" failure is a CLI-side error surfacing problem combined with likely server-side contract mismatch. Fix both the CLI error handling and document the server requirements.

**Rationale**:
- `batch.py:135` only reads the `error` field from 400 responses, discarding the `details` field
- Server returns per-event `results[]` on success (200), but CLI doesn't parse individual event statuses
- Token works for auth endpoints, so this isn't a pure auth failure
- Server-side may have payload validation issues (team/project authorization, schema version)

**Alternatives considered**:
- Fix only server side: Rejected — CLI needs better diagnostics regardless
- Add verbose logging only: Rejected — users need actionable summaries, not log dumps

## R3: Credential Path Strategy

**Decision**: Keep `~/.spec-kitty/credentials` separate from `~/.kittify/` for this sprint.

**Rationale**: Credentials (JWT tokens, user identity) are auth-specific concerns. Runtime (templates, missions, agent configs) is a different concern. Merging them risks credential exposure during template operations. The separation also allows different permission models (credentials are chmod 600, templates are world-readable).

**Alternatives considered**:
- Move credentials to `~/.kittify/credentials`: Deferred — would require updating all auth.py paths and testing migration
- Consolidate under `~/.kittify/auth/credentials`: Deferred — cleaner but adds scope

## R4: Lane Mapping Edge Cases

**Decision**: Map BLOCKED→doing and CANCELED→done for 4-lane sync. Document the lossy nature of the collapse.

**Rationale**: The 4-lane model is the SaaS contract. BLOCKED items are "in progress but stuck" — mapping to `doing` is reasonable because the SaaS doesn't need to distinguish stuck from active. CANCELED items are "terminal" — mapping to `done` is reasonable because both are terminal states from a workflow perspective.

**Alternatives considered**:
- Add BLOCKED and CANCELED to sync payload: Rejected — breaks SaaS contract, requires SaaS changes
- Map BLOCKED→planned: Rejected — blocked items have been started, reverting to planned is misleading
- Map CANCELED→planned: Rejected — canceled items should not appear as actionable

## R5: Test Environment ModuleNotFoundError: typer

**Decision**: Investigate on 2.x as part of WP01. The `typer` import failure is likely a test venv configuration issue, not a code problem.

**Rationale**: On main, the NameError was fixed but `ModuleNotFoundError: typer` appeared in a test-created venv. On 2.x, the NameError blocks before reaching this point. After fixing the NameError on 2.x, if typer is missing in the test environment, the fix is ensuring `typer` is in test dependencies (already in `pyproject.toml` but may not be installed in isolated test venvs).

**Alternatives considered**:
- Make typer optional: Rejected — typer is the CLI framework, it's required
- Skip tests that need typer: Rejected — these are core integration tests

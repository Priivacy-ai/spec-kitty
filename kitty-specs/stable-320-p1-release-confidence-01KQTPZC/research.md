# Research: Stable 3.2.0 P1 Release Confidence

## Decision: Keep weighted progress but label it as weighted/ready progress

**Rationale**: The current status implementation computes weighted progress through `compute_weighted_progress(...)`, where `approved` contributes `0.8` and `done` contributes `1.0`. That weighted metric is useful for readiness, but `spec-kitty agent tasks status` currently prints a done-only numerator beside that weighted percentage. This creates #966's contradictory signal.

**Alternatives considered**:

- Make the weighted percentage done-only. Rejected because the existing weighted progress model is intentionally used by status surfaces and decision logic.
- Keep the current output. Rejected because it makes approved-only boards look like `0/N` done while also mostly complete.
- Add separate done and weighted labels. Chosen because it preserves useful readiness signal while making semantics explicit.

## Decision: Add explicit JSON semantics if JSON output is touched

**Rationale**: `spec-kitty agent tasks status --json` currently exposes `progress_percentage` based on weighted progress. If implementation changes that output, automation needs explicit semantics. The preferred approach is additive: keep parseability, preserve backward-compatible fields when practical, and add fields such as done count, total count, done percentage, weighted percentage, or progress label.

**Alternatives considered**:

- Rename the existing field without compatibility. Rejected because machine consumers may already parse it.
- Leave JSON untouched and only fix human output. Acceptable only if the implementation can prove JSON is already internally consistent or not affected by #966.

## Decision: Verify #848 before adding code

**Rationale**: Existing release surfaces already include lock and package drift checks:

- `.github/workflows/ci-quality.yml` runs `uv lock --check`.
- `.github/workflows/check-spec-kitty-events-alignment.yml` runs `scripts/release/check_shared_package_drift.py`.
- `.github/workflows/release-readiness.yml` runs the same shared package drift check and exact installability checks.
- `scripts/release/check_shared_package_drift.py` compares CLI constraints, `uv.lock`, and SaaS pins when SaaS metadata is available.

The remaining #848 question is narrower: whether review/release evidence can still run against an installed `spec-kitty-events` version that differs from `uv.lock`. The mission should inspect and test that installed-environment path before changing code.

**Alternatives considered**:

- Immediately add a new gate. Rejected until evidence proves the current gates do not already cover the risk.
- Loosen `pyproject.toml` constraints. Rejected by the spec because it does not detect environment drift.

## Decision: Scope smoke runs as evidence-producing workflows

**Rationale**: The smoke requirement is release confidence, not a request to redesign smoke infrastructure. The plan should write exact command sequences in the evidence artifacts, run one local-only lifecycle path, and run one SaaS-enabled lifecycle path with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` on hosted/sync commands.

**Alternatives considered**:

- Make smoke fully automated before implementation. Deferred because current CLI surfaces and auth state must be selected during WP execution.
- Skip SaaS smoke if local passes. Rejected because this computer's testing rule and the mission spec require SaaS-enabled coverage where hosted/sync paths are touched.

## Decision: Defer #971 unless explicitly included as its own WP

**Rationale**: #971 is a strict mypy release-gate problem surfaced from PR #972 evidence. The starter brief explicitly says not to silently absorb it into this mission. The plan records #971 as deferred by default and only includes strict mypy cleanup if a later review explicitly widens the mission with a separate WP and evidence.

**Alternatives considered**:

- Include #971 automatically. Rejected because it would widen this P1 release-confidence tranche.
- Omit #971. Rejected because the spec requires an explicit included/deferred decision.

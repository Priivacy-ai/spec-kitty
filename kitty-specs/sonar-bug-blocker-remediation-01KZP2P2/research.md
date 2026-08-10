# Phase 0 Research: Sonar BUG and BLOCKER Remediation

The authoritative per-issue inventory (rule, file:line, message) is
[research/sonar-inventory.txt](./research/sonar-inventory.txt), pulled from the SonarCloud public API
(`https://sonarcloud.io/api/issues/search?componentKeys=Priivacy-ai_spec-kitty&issueStatuses=OPEN,CONFIRMED`).
This document records the *approach* decisions, not per-issue fixes (those land in implementation).

## Decision: fix at the root, never suppress

- **Decision**: Every issue is resolved by a real code/test change. A `# noqa` / `# type: ignore` /
  `NOSONAR` is never used to clear an issue. A genuine false positive is resolved by a written
  rationale (PR body / inline comment explaining why the code is correct), not a suppression.
- **Rationale**: Charter Sonar Expectations — "Prefer real fixes over suppression." Suppressions move
  the failure rather than closing it.
- **Alternatives considered**: bulk-suppress the test-quality rules — rejected: it green-washes the
  quality gate and the tautological tests would still prove nothing.

## Decision: mechanical vs investigate seam (the two-WP split)

- **Decision**: Split the work into a **mechanical** stream (S5863 tautological asserts, S5779 swallowed
  asserts, S8998 empty parametrize) and an **investigate** stream (S2083 path-injection, S3516
  always-same-return, S2583 always-true).
- **Rationale**: The mechanical stream is largely local, low-risk test-integrity repair with a clear
  correct shape. The investigate stream needs per-case judgment (real bug vs intentional-but-smelly vs
  trusted-local false positive) and touches src control flow / security — a different risk profile and
  review depth. Operator pre-approved this split.
- **Alternatives considered**: one flat pass — rejected: mixes low-risk mechanical edits with
  security/logic judgment, muddying review.

## Decision: S2083 (path-injection) — determine trusted-local vs external-input per site

- **Decision**: For each of the 3 sites, trace the tainted path component to its source. If it derives
  from **external/user input** reachable at runtime, validate/contain it (reject traversal, anchor under
  an allowed root) and add a test exercising the rejection. If it derives from **trusted repo/mission
  internal data**, keep the semantics and record a rationale (C-001) — do not add sanitization theatre.
- **Rationale**: Charter loopback/local-only special case — forcing sanitization on trusted-local paths
  is noise; real external vectors must be contained.
- **Method**: read the call chain feeding `bookkeeping_projection.py:212,346` and `skills/verifier.py:402`;
  classify the source; decide contain-vs-rationale per site.

## Decision: S3516 / S2583 (degenerate control flow) — classify real-bug vs intentional

- **Decision**: For each site, determine whether the degeneracy is a real defect (a branch that should
  vary but cannot — fix the logic, prove with a behavioral test) or an intentional constant (a
  protocol-conforming stub / defensive guard — remove the smell: drop the vacuous `return`, tighten the
  signature/return type, or make the invariant explicit) — never suppress.
- **Rationale**: Sonar cannot tell intent; a blind "add a branch" could invent wrong behavior. The
  charter requires the real fix, and every new branch needs a test (C-002).

## Decision: red-first for recoverable assertions (S5863)

- **Decision**: For each tautological assertion whose intended comparison is recoverable from context,
  write the corrected assertion so it *fails* against the current (buggy) behavior first (red-first
  evidence), then make it pass. Where intent is unrecoverable, remove the assertion with a one-line
  rationale rather than guess a wrong comparison.
- **Rationale**: NFR-003; a tautology "passing" tells us nothing — the corrected form must be shown to
  bite.

## Out of scope (recorded)

- HIGH-severity maintainability (S3776 complexity, S1192 dup-literals) — separate per-module missions
  (doctrine/charter/sync), per operator sequencing. C-003 bounds this mission to the 41 BUG+BLOCKER.

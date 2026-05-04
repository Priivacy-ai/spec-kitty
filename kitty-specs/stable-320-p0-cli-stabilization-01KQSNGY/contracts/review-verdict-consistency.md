# Contract: Review Verdict Consistency

## Scope

This contract covers #904 review-cycle/WP state consistency during WP transitions, mission status, mission review, and merge preflight.

## Required Behavior

- Before a WP moves to `approved` or `done`, Spec Kitty must inspect the latest applicable `review-cycle-N.md` artifact for that WP.
- If the latest applicable artifact has `verdict: rejected`, the transition must fail before mutating state unless an explicit override is supplied.
- The failure diagnostic must name:
  - the WP id,
  - the latest rejected review-cycle artifact,
  - the required repair or override action.
- Mission status, mission review, and merge preflight must not silently pass when a done or approved WP is contradicted by a latest rejected review-cycle artifact.
- Explicit overrides must be persisted as structured state in review-cycle metadata or a linked override artifact.

## Acceptance Checks

- A rejected latest review artifact blocks WP completion and leaves WP state unchanged.
- A later approved review artifact supersedes an earlier rejected artifact.
- An explicit override records durable evidence and permits the intended transition.
- Mission status, mission review, and merge preflight fail or report a blocking diagnostic on done/approved plus latest rejected contradiction.
- JSON-producing commands touched by this behavior keep parseable JSON on stdout.

## Non-Goals

- Warning-only policy.
- Manual deletion of rejected artifacts as the normal repair path.
- Reimplementation of PR #959 or PR #969 work without current repro evidence.

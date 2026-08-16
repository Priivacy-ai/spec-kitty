---
affected_files:
- tests/conftest.py
- tests/test_test_venv_bootstrap.py
- tests/_support/wall_clock_assertions.py
- tests/_support/test_wall_clock_assertions.py
cycle_number: 2
mission_slug: assertive-test-suite-sanitation-01KZME3P
reviewed_at: '2026-08-10T11:48:33Z'
reviewer_agent: reviewer-renata
wp_id: WP02
---

# WP02 Review Cycle 2 — Changes Requested

## Blocking finding 1 — Cache findings remain self-signed

The cache stores result rows and their SHA-256 in the same mutable document.
Erasing violations and recomputing the result authenticator changes a real
finding count from 1 to 0 while validating as a cache hit. Add that regression
and make omitted/substituted findings independently unverifiable.

## Blocking finding 2 — Invalid final symlink plus stale lease cannot recover

The expected-temp check resolves the final symlink before checking the recorded
temp sibling. An invalid final symlink outside the cache changes the expected
parent and rejects a legitimate stale sibling. Validate the lexical/cache-parent
relation without resolving the final symlink, preserve no-follow deletion, and
add the combined stale-lease/symlink regression.

## Verified closures

- Regular-file/simple-symlink finals rebuild and preserve targets.
- Eight concurrent cache readers/builders publish one equal artifact.
- Immutable-base #3283 probe reproduces timeout and partial-final visibility.
- Replay patches apply to 28ae75e and five files match HEAD byte-for-byte.
- Three clean starts are accurately labeled: one completion and two controlled
  SIGINT stops after body-start proof.
- Focused tests: 125 passed, 2 skipped; integration: 1 passed; Ruff passed.

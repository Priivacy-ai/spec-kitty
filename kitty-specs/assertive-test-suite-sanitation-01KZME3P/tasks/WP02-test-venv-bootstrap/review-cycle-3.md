---
affected_files:
- tests/_support/wall_clock_assertions.py
- tests/_support/test_wall_clock_assertions.py
cycle_number: 3
mission_slug: assertive-test-suite-sanitation-01KZME3P
reviewed_at: '2026-08-10T12:30:00Z'
reviewer_agent: reviewer-renata
wp_id: WP02
---

# WP02 Review Cycle 3 — Changes Requested

## Blocking finding — cache authority remains forgeable and malformed authority does not rescan

`tests/_support/wall_clock_assertions.py:114-120` stores the result and its HMAC
authority key inside the same caller-writable cache root. A process able to perform
cycle 2's schema-valid result rewrite can read `authority.key`, erase the finding,
and recompute both `result_sha256` and `authority_hmac_sha256`. Independent
reproduction changed a real finding count from 1 to 0 and the next cached call
returned zero without rescanning:

```text
coherent_forgery 1 0 BYPASS
```

The new key lifecycle also does not satisfy the corrupt-cache fallback. Creating
`authority.key` as a directory makes `_load_or_create_wall_clock_scan_authority_key`
raise `IsADirectoryError` instead of treating the cache as invalid and rescanning.
An existing 32-byte key with mode `0644` is accepted and remains world-readable,
so the HMAC's claimed authority boundary is not enforced.

This leaves T050's fail-closed oracle bypassable and does not make omitted or
substituted findings independently unverifiable. The arbiter should require an
authority source outside the mutable result-cache trust domain, validate/no-follow
its type and permissions where supported, and treat missing/malformed/rotated
authority as cache invalidation followed by a rescan. Add regression coverage for
coherent result+HMAC forgery, absent/malformed/rotated keys, permission repair, and
simultaneous first initialization.

## Verified closures and gates

- Lexical stale-lease recovery past an invalid final symlink passed and preserved
  the external target.
- Bootstrap + scanner focused tests: `126 passed, 2 skipped`.
- Spawned integration concurrency test passed.
- Ruff passed on all four changed Python files.
- Strict mypy reported only seven pre-existing errors identified before WP02.
- Both replay patches applied unchanged to immutable base `28ae75e`; all five
  replayed files were byte-identical to the lane; recorded SHA-256 values matched.

## WP anti-pattern checklist

1. Dead code: **PASS** — new helpers are called by live test-harness paths.
2. Synthetic-fixture test: **FAIL** — the new corruption test omits the same-root
   readable key, so it cannot catch the coherent forgery accepted by production.
3. Silent empty return: **PASS** — cache misses rescan; no new silent empty return.
4. FR coverage: **FAIL** — T050/NFR-004 fail-closed cache integrity remains open.
5. Frozen surface: **PASS** — changes remain inside WP02 ownership.
6. Locked decision: **FAIL** — cached forbidden assertions can still be erased.
7. Shared-file ownership: **PASS** — no uncoordinated overlap found.
8. Production fragility: **FAIL** — malformed authority state can abort collection.

Cycle 3 is final. No cycle 4; root arbiter decides approve/block and moves forward.

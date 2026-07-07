# Contract: Landing hygiene

The observable contracts this mission upholds (verified by the tests + reviews cited in `acceptance-matrix.json`).

## C1 — Review-prompt retention is bounded + safe (#2439, FR-001/002)
- `write_review_prompt_with_metadata()` prunes its WP dir to a default cap (newest-preserving) AFTER writing the current invocation.
- **Invariants**: the current-invocation file is NEVER pruned (excluded by name — proven by the future-mtime mutation test); the prune is **fail-safe** (swallows all errors, never raises — a review never fails on housekeeping); scoped strictly to `spec-kitty-review-prompts/<repo-id>/…`; the `<repo-id>`/path scheme (#959) + metadata are unchanged.

## C2 — The coverage allowlist can't silently rot (#2443, FR-003/004)
- The `diff-coverage` `--include` allowlist references only real files. The phantom `core/mission_detection.py` (never existed) is repointed to its real defining home `src/specify_cli/lanes/branch_naming.py` (cov-backed by fast/integration-tests-lanes), in **both** authorities (`ci-quality.yml` + `tests/release/test_diff_coverage_policy.py`) in lockstep — no split-brain.
- **Guard**: a glob-aware existence test (reusing the canonical `_diff_cover_critical_paths` parser) asserts every entry resolves — globs → `Path.glob` ≥1 match, literals → `.exists()`; reds specifically on a phantom entry.

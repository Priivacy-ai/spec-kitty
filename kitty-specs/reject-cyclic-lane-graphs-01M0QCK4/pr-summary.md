# PR Summary: Reject Cyclic Execution-Lane Graphs

## Summary

- Reject post-collapse execution-lane cycles inside authoritative `compute_lanes`.
- Emit deterministic human and JSON diagnostics with the closed cycle path and sorted WP membership.
- Preserve an absent or existing valid `lanes.json` on rejection, including validate-only mode.
- Add deterministic, recursion-safety, schema, persistence, compatibility, and governed performance proofs.

## Compatibility

Valid acyclic missions retain their existing manifest and finalization behavior.
Only previously accepted cyclic post-collapse graphs now fail. No file-format
migration or new runtime dependency is introduced.

## Validation

- 194 focused lane/finalization tests passed, 1 skipped
- 297 contract tests passed, 5 skipped
- 1,679 architectural tests passed, 5 skipped, 2 expected xfails
- Ruff and strict mypy passed
- Three-process hash-seed diagnostics are byte-stable
- 100-lane/500-edge benchmark p95 is below 100 ms
- Cross-repo lifecycle hard gate passes with companion E2E PR #586

## Review artifacts

- [Specification](./spec.md)
- [Plan](./plan.md)
- [Mission review](./mission-review.md)
- [Adversarial review](./adversarial-review.md)

Closes Priivacy-ai/spec-kitty#3431.

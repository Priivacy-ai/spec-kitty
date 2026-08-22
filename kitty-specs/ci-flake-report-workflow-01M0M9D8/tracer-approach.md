# Tracer: Approach

Seeded at planning; append during implement.

- Mission partitions into Capability A (flake-report tool + weekly workflow, WP01-03) and Capability B (draft/ready CI mode + red-first, WP04-06). A is shippable alone; B lands in the same consolidated PR.
- A is built pure-core-first (WP01) then IO/CLI/fixture (WP02) then workflow (WP03) — ATDD on the pure core.
- B extends existing `ci-quality.yml` machinery (unify, not duplicate); guard tests are the merge-gate contract.

## Implement log
- (append: what actually happened per WP)

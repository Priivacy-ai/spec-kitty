# Release Readiness: 064 Complete Mission Identity Cutover

**Date**: 2026-04-06
**Verdict**: **NO-GO** (blocked on external consumer update)

## External Consumer Status

| Consumer | Issue | Status | Blocker? |
|----------|-------|--------|----------|
| spec-kitty-orchestrator | Priivacy-ai/spec-kitty-orchestrator#6 | OPEN | **YES** |

The orchestrator API hard cutover (FR-004, FR-021, FR-022) renames 3 commands, 2 error codes, and the `--feature` → `--mission` CLI parameter. `spec-kitty-orchestrator` is the known external consumer and must be updated before production rollout.

## Success Criteria Assessment

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Agent can drive full mission lifecycle without feature-era fields | PASS (all code WPs approved) |
| 2 | Two worktrees emit distinct build_id values | PASS (WP06: build_id on envelopes + tracker bind) |
| 3 | Legacy project upgrade preserves identity | PASS (WP05: queue migration preserves data) |
| 4 | Compatibility gate rejects non-conformant payloads | PASS (WP01: gate + nested payload validation) |
| 5 | grep feature_slug on live paths returns zero | PASS (WP08: 222-file audit, zero live results) |
| 6 | Shape conformance tests pass | PASS (WP07: 53 tests across 4 surfaces) |
| 7 | No live orchestrator API accepts feature-era commands | PASS (WP04: old names fail as unknown) |
| 8 | Not shippable until orchestrator consumer updated | **BLOCKED** (Priivacy-ai/spec-kitty-orchestrator#6 OPEN) |

## Implementation Summary

- **274 files changed**, +5,880 / -4,201 lines across 16 commits on lane-a
- 9 WPs completed: compatibility gate, 3 module renames, orchestrator API hard cutover, body sync migration, tracker bind + event envelope, conformance tests, full audit + cleanup, release coordination
- spec-kitty-events upgraded from 2.9.0 → 3.0.0 (with uv override for spec-kitty-runtime packaging bug, tracked in Priivacy-ai/spec-kitty-runtime#10)

## Known Issues

1. **spec-kitty-runtime packaging bug** (Priivacy-ai/spec-kitty-runtime#10): runtime 0.4.2 metadata pins events==2.9.0 but code requires 3.0.0. Workaround via `[tool.uv] override-dependencies`.
2. **Pre-existing test failures** in `tests/next/` due to the runtime/events version mismatch. These are not regressions from this feature.
3. **body_upload_queue migration**: The `table body_upload_queue has no column named feature_slug` error will be resolved when the queue migration runs during next `spec-kitty upgrade`.

## Release Sequence (when unblocked)

1. Update and release `spec-kitty-orchestrator` first (Priivacy-ai/spec-kitty-orchestrator#6)
2. Validate orchestrator against renamed contract
3. Merge feature 064 lane to main
4. Release spec-kitty

## Filed Issues

| Repo | Issue | Purpose |
|------|-------|---------|
| spec-kitty | #418 | tasks/README.md hardcodes 2.x branch |
| spec-kitty | #430 | Fix-mode prompts for rejection cycles |
| spec-kitty | #432 | Persist review feedback as sub-artifacts |
| spec-kitty | #433 | Link #430 and #432 |
| spec-kitty-orchestrator | #6 | Breaking API rename mapping tables |
| spec-kitty-runtime | #10 | Packaging bug: events version mismatch |

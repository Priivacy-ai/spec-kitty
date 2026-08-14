---
work_package_id: WP02
title: Shared anchor propagation and finalize integration
lane: lane-b
dependencies: [WP01]
requirement_refs: [FR-001, FR-002, FR-003, FR-005, NFR-001]
---

Implement the read-only mission operation context, thread its mission anchor
through placement/status/workspace resolution, and route `finalize-tasks` through
that context. Preserve the repository root for Git/topology operations while
using the anchor for mission artifacts. Refuse ambiguous surfaces before writes.

Acceptance: a mission present only in a caller-owned worktree can run
`finalize-tasks --validate-only --mission <slug>` from that checkout without
reading or mutating the primary checkout.

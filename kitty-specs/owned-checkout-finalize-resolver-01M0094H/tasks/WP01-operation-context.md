---
work_package_id: WP01
title: Red-first operation-context and topology tests
lane: lane-a
dependencies: []
requirement_refs: [FR-001, FR-003, FR-004, NFR-002, NFR-003]
---

Create real linked-worktree fixtures and lock the operation-context contract:
caller-owned missions select the current checkout, managed lanes remain primary
anchored, foreign repositories are ignored, and conflicting identities fail
closed with a stable structured projection.

Acceptance: the new tests are red on the current upstream baseline and green
after the resolver is implemented.

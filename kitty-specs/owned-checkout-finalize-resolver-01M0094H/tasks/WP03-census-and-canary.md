---
work_package_id: WP03
title: Architectural census, compatibility tests, and canary validation
lane: lane-c
dependencies: [WP02]
requirement_refs: [FR-003, FR-004, NFR-001, NFR-003]
---

Add a non-vacuous census guard for covered lifecycle consumers, run the focused
primary/managed compatibility suite, build a pinned local canary executable,
and smoke the real TI4 mission from its task worktree. Record failures as
follow-up work instead of weakening the gate.

Acceptance: all scoped tests pass, the canary resolves the TI4 mission without
the old `FEATURE_CONTEXT_UNRESOLVED` split-brain, and primary remains unchanged.

---
work_package_id: WP01
title: Canonical Dossier Snapshot-Hash Definition
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
tracker_refs:
- '#2180'
planning_base_branch: feat/dossier-parity-reconciler
merge_target_branch: feat/dossier-parity-reconciler
branch_strategy: Planning artifacts for this mission were generated on feat/dossier-parity-reconciler. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dossier-parity-reconciler unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Canonical hash foundation
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "2818835"
history:
- at: '2026-07-20T06:13:30Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/dossier/hasher.py
create_intent:
- tests/dossier/test_canonical_hash.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/dossier/hasher.py
- src/specify_cli/dossier/indexer.py
- tests/dossier/test_canonical_hash.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 — Canonical Dossier Snapshot-Hash Definition

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile via `/ad-hoc-profile-load` (profile: `python-pedro`, role: `implementer`). Adopt its identity, governance scope, and boundaries for this WP.

## Objective

Define the ONE canonical dossier snapshot hash, computed identically wherever it runs. Structure: sort entries by artifact path, join `path\tcontent_hash` lines with newlines, `sha256`, and prefix the digest with `sha256:` — the server's shape (it carries path + stable ordering, which the CLI's prior concat-of-hashes form loses). Input: the normalized `WPMetadata` static projection, not raw file bytes, so runtime-mutable churn does not change the hash. This is the foundation every other WP and the companion server PR conforms to (C-001, C-004).

## Context

- Today the CLI hash (`compute_parity_hash_from_dossier`, `dossier/snapshot.py`) is concat-of-content-hashes → bare hex; the server (`spec-kitty-saas apps/dossier/materialize.py::_compute_snapshot_hash`) is `path\tcontent_hash` lines → `sha256:` prefix. This WP owns the CLI-side canonical definition in `dossier/hasher.py` + `dossier/indexer.py`; the server aligns to it in a companion PR (C-003).
- Per-artifact `content_hash` today comes from raw UTF-8 file bytes (`dossier/indexer.py` / `hasher.py`). Retire that for WP artifacts in favour of the normalized `WPMetadata` static projection (the #2686 direction) so runtime-mutable fields do not churn the hash (FR-002, AS-4).

## Subtasks

### T001 — Campsite-clean WP01 surfaces
Read `dossier/hasher.py` and `dossier/indexer.py`; note the current hash inputs and any dead/duplicated hashing paths. Leave the surfaces tidy before feature edits (no behavior change in this subtask).

### T002 — Red tests for the canonical hash (FR-001, FR-003, NFR-001)
In `tests/dossier/test_canonical_hash.py` add failing tests that pin: (a) the exact structure — sorted `path\tcontent_hash` lines, `sha256`, `sha256:` prefix — against a fixed golden value; (b) order-independence (shuffled input → same hash); (c) determinism across repeated runs. These are the executable contract for FR-001/FR-003.

### T003 — Implement the canonical hash (FR-001, FR-003, C-001)
In `dossier/hasher.py`, implement the canonical function as the single owning definition. No second formula anywhere (C-001). Bare-hex/concat form is retired here (its call-sites migrate in WP02).

### T004 — Route the hash input to the normalized projection (FR-002, C-004)
In `dossier/indexer.py`, compute per-WP `content_hash` from the normalized `WPMetadata` static projection rather than raw `WP##.md` bytes. Keep non-WP artifacts on their existing content hash. Document the projection shape so #2684/#2686 conform to it rather than redefining it.

### T005 — Prove determinism + stability (NFR-001) [P]
Add tests proving 100% identical hash across ≥100 repeated runs and that changing a runtime-mutable WP field (not canonical content) does NOT change the hash (AS-4 churn immunity). Run the focused type/style/coverage gates on the changed surfaces.

## Branch Strategy

Planning branch: `feat/dossier-parity-reconciler`. Final merge target: `feat/dossier-parity-reconciler`. Execution worktrees are allocated per computed lane from `lanes.json` during `/spec-kitty.implement`.

## Definition of Done

- Canonical hash implemented as the single definition; golden-value + order-independence + determinism tests green.
- WP-artifact hash input is the normalized static projection; churn-immunity test green (AS-4).
- No second hash formula remains in the CLI dossier surface.
- ruff + mypy clean on changed files; ≥90% changed-code coverage.

## Risks / Reviewer Guidance

- The projection shape is load-bearing for cross-repo parity — reviewer confirms it is documented and that the server companion PR can compute byte-identically.
- Verify order-independence is real (test with shuffled inputs), not incidental.

## Activity Log

- 2026-07-20T06:23:51Z – claude:sonnet:python-pedro:implementer – shell_pid=2760042 – Assigned agent via action command
- 2026-07-20T06:47:28Z – claude:sonnet:python-pedro:implementer – shell_pid=2760042 – Canonical hash + WP static projection; 42 tests green; lint clean; wired via dossier/__init__
- 2026-07-20T06:48:07Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=2818835 – Started review via action command
- 2026-07-20T06:48:26Z – user – shell_pid=2818835 – Canonical hash implemented; 23 canonical + 19 hasher (42) dossier-hash tests green, full dossier suites 366 green, gate-coverage GC-2b + orphan-surface green; ruff+mypy 0 on changed files; old concat/bare-hex Hasher form removed and callers verified (indexer routes WP content_hash through normalized WPMetadata static projection)
- 2026-07-20T06:53:50Z – user – shell_pid=2818835 – Review passed: canonical compute_dossier_snapshot_hash is byte-identical to server apps/dossier/materialize.py::_compute_snapshot_hash (sorted path-TAB-content_hash lines -> sha256 -> sha256: prefix). Independently reproduced golden dfa28d..c610 and empty-sentinel e3b0c4..b855; suite adds a 25-iter randomized server-shape cross-check and None-handling. WP content_hash routed through the normalized WPMetadata static projection (14 authored fields) not raw bytes; churn-immunity proven over 7 runtime fields with complementary content-change counter-tests (AS-4). Old Hasher concat/bare-hex form removed from hasher.py (C-001 on WP01 surface); snapshot.py::compute_parity_hash_from_dossier call-site migration is explicitly WP02 per T003 and out of WP01 owned_files. Determinism: 100-run + 20-shuffle order-independence with a real not-incidental guard (NFR-001). ruff+mypy clean on changed files; 42 tests green. compute_dossier_snapshot_hash exported via dossier/__init__ as the foundation contract for WP02/WP03.

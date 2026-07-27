---
work_package_id: WP02
title: CLI Snapshot-Hash Emit + Validation Migration
dependencies:
- WP01
requirement_refs:
- FR-008
tracker_refs:
- '#2180'
planning_base_branch: feat/dossier-parity-reconciler
merge_target_branch: feat/dossier-parity-reconciler
branch_strategy: Planning artifacts for this mission were generated on feat/dossier-parity-reconciler. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dossier-parity-reconciler unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
phase: Phase 2 - Emit-side migration
assignee: ''
agent: "claude:sonnet:reviewer:reviewer"
shell_pid: "2902046"
history:
- at: '2026-07-20T06:13:30Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/dossier/snapshot.py
create_intent:
- tests/dossier/test_snapshot_emit.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/dossier/snapshot.py
- src/specify_cli/sync/emitter.py
- tests/dossier/test_snapshot_emit.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 — CLI Snapshot-Hash Emit + Validation Migration

## ⚡ Do This First: Load Agent Profile

Load your assigned profile via `/ad-hoc-profile-load` (profile: `python-pedro`, role: `implementer`) before anything else.

## Objective

Migrate the CLI snapshot emit path and its validation from the retired concat/bare-hex form onto WP01's canonical hash, **without changing the `snapshot_hash` field name** in the emitted event (FR-008). The value format moves to the canonical `sha256:`-prefixed form; validation must accept it.

## Context

- `dossier/snapshot.py::compute_parity_hash_from_dossier` currently emits the concat/bare-hex value; the emitted event field is `snapshot_hash` (do not rename it).
- `sync/emitter.py` validates the emitted value with `_is_sha256_hex` (bare 64-hex). It must accept the canonical `sha256:`-prefixed form.
- Depends on WP01 (the canonical function must exist to call).

## Subtasks

### T006 — Red tests for the emit migration (FR-008)
In `tests/dossier/test_snapshot_emit.py` add failing tests: the emitted snapshot event carries the canonical `sha256:`-prefixed value under the unchanged `snapshot_hash` field, and `_is_sha256_hex` (or its successor) accepts that form while still rejecting genuinely malformed values.

### T007 — Migrate the producer (FR-008)
Point `compute_parity_hash_from_dossier` (and any sibling snapshot producer) at WP01's canonical function. Remove the concat/bare-hex computation.

### T008 — Update emit + validation (FR-008)
Update `sync/emitter.py` so the emit writes the canonical value and the validation accepts the `sha256:` prefix. Keep the field name `snapshot_hash`.

### T009 — Prove backward-compat call-sites unbroken [P]
Prove the envelope shape and field name are unchanged for existing consumers (only the value format changed). Run focused type/style/coverage gates.

## Branch Strategy

Planning branch: `feat/dossier-parity-reconciler`; final merge target: same. Worktrees are per-lane from `lanes.json` at implement time.

## Definition of Done

- Emit produces the canonical `sha256:` value under the unchanged `snapshot_hash` field; validation accepts it; malformed values still rejected.
- No concat/bare-hex producer remains.
- ruff + mypy clean; ≥90% changed-code coverage.

## Risks / Reviewer Guidance

- The field-name-stable / value-format-changed distinction is the crux — reviewer confirms no consumer keys off the old bare-hex format.
- Pairs with WP05 (re-baseline): existing recorded values become non-comparable until re-baselined; that cutover is WP05's job, not this WP's.

## Activity Log

- 2026-07-20T06:55:49Z – claude:sonnet:python-pedro:implementer – shell_pid=2837818 – Assigned agent via action command
- 2026-07-20T07:16:59Z – claude:sonnet:python-pedro:implementer – shell_pid=2837818 – WP02 canonical snapshot-hash emit+validation migration. Producer compute_parity_hash_from_dossier now delegates to WP01 compute_dossier_snapshot_hash (sha256:-prefixed); concat/bare-hex removed. emitter.py: new _is_canonical_snapshot_hash guards snapshot_hash + drift expected/actual_hash (accepts sha256: form + transitional bare-hex, rejects malformed); snapshot_hash field name unchanged. Tests: tests/dossier/test_snapshot_emit.py 18 pass (RED-first); full dossier+sync suite 2357 pass, 17 skip. Only pre-existing failure tests/sync/test_strict_json_stdout.py (env: sync Connection refused, verified identical on mission base). Lint: ruff check exit 0 on all changed .py; ruff format --check + mypy(strict) clean on snapshot.py (base-clean); my added lines in emitter.py/models.py introduce zero new format drift (emitter.py/models.py carry PRE-EXISTING ruff-format drift under line-length=164, present on mission base — not touched). Integration-verify: old concat/bare-hex gone; producer calls canonical; _is_sha256_hex now only guards proof per-file sha; no consumer keys off old bare-hex parity format. Out-of-map (justified): relaxed MissionDossierSnapshot.parity_hash_sha256 validator to accept sha256: prefix (value must round-trip model->emit); updated 3 pre-existing format assertions pinning retired bare-hex length.
- 2026-07-20T07:19:06Z – claude:sonnet:reviewer:reviewer – shell_pid=2902046 – Started review via action command
- 2026-07-20T07:21:54Z – user – shell_pid=2902046 – Review passed: producer delegates to WP01 canonical compute_dossier_snapshot_hash (concat/bare-hex removed); emitter validates snapshot_hash/drift hashes via new _is_canonical_snapshot_hash (sha256:-prefix + transitional bare-hex, rejects malformed); snapshot_hash field name/envelope unchanged; _is_sha256_hex correctly retained for proof per-file sha; RED-first test_snapshot_emit.py exercises real paths; 66 affected tests pass; out-of-map models.py validator relaxation + 3 assertion updates justified; pre-existing sync-env red + ruff-format drift not penalized (cat-2/3).

# Tasks: Sync Deactivated By Default

**Mission**: sync-deactivate-by-default-01M16M1P | **Branch**: `spike/3799-sync-deactivation-3798-accept-hermetic`
**Authoritative design**: [plan.md](./plan.md) — the **"Post-plan squad corrections (BINDING)"** section is authoritative over any sketch. Contracts in [contracts/](./contracts/). Change mode: **standard** (reclassified from bulk_edit — the skipif rollout is additive, not a rename; the occurrence-map gate is rename-only. Integrity guarded by the WP06 file-count census).

All WPs: `execution_mode: code_change`, test-first (DIR-034), ruff+mypy clean, complexity ≤15.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Add `sync_active()` to `core/saas_sync_config.py` + 8-row truth-table unit tests | WP01 | |
| T002 | #2801 clean-cut: pre-review gate reads only `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE`; rewrite its tests | WP01 | |
| T003 | Freeze `--collect-only` non-skipped node-id baseline for tests/sync + tests/specify_cli/sync | WP01 | |
| T004 | Freeze FR-013 census: frozen sorted SET of sync-coupled test file paths | WP01 | |
| T005 | Gate `register_default_handlers` at call-time on `sync_active()` | WP02 | |
| T006 | Route daemon spawn (daemon.py:1131/1154) + events emit/publish (events.py:109/182) through `sync_active()` | WP02 | |
| T007 | Gate emitter at `_emit` (return envelope, skip capture/route/queue) so all emit_* paths no-op + local-capture warning silenced | WP02 | |
| T008 | Deactivation guard tests (spies: seam-not-reached on default path) + doctor advisory (FR-018 code) | WP02 | |
| T009 | #3470: short-circuit `dossier_pipeline.py:471` on `not sync_active()` before enqueue | WP03 | |
| T010 | Anti-swallow test: under opt-in, real `_require_project_destination` violation surfaces via `DossierSyncResult.errors` | WP03 | |
| T011 | De-mask conftest: invert `conftest.py:223` setdefault + `:427` autouse to default-off | WP04 | |
| T012 | Add `sync_enabled` / `sync_disabled` fixtures; migrate ~60 non-sync flag-consumers onto `sync_enabled` | WP04 | |
| T013 | CI collection-time opt-in via env var on `fast-tests-sync` step (ci-quality.yml:1135) + push-guarded opt-in arm | WP04 | |
| T014 | Skipif rollout across tests/sync + tests/specify_cli/sync (additive marker) | WP05 | |
| T015 | Skipif for scattered clusters: delivery, dossier, stress, status fanout, integration/offline_queue_overflow, cli/commands/test_sync_* | WP05 | |
| T016 | Fold #2809's two named tests into the gating | WP05 | |
| T017 | File-count census test: recompute live skipif set, assert `== FROZEN_SET` (deletion + un-skip both red) | WP06 | |
| T018 | Rewrite the two arch guards that FIGHT default-off (gate_selection_invariance flag-at-collection; writer_census) | WP07 | |
| T019 | Update env-census frozen set (+ PRE_REVIEW_GATE_DISABLE literal); add inactive-path arm to PR#3570 goldens | WP07 | |
| T020 | NFR-004 collection-parity test: opt-in `--collect-only` == WP01 baseline | WP07 | |
| T021 | Docs: environment-variables, cli-commands, orphan-cleanup, spk-run-implement-review:44-45, sync-env-census.md, egress ADR | WP08 | |
| T022 | CHANGELOG breaking-change note (sync now opt-in) + verify doctor advisory copy | WP08 | |

## Work Packages

### WP01 — Foundation: sync_active() seam + #2801 clean-cut + freeze baselines *(unblocker)*
**Goal**: introduce the single arming predicate, decouple the pre-review gate, and freeze the collection/census baselines BEFORE any skipif exists. **Priority**: P1. **Deps**: none.
**Independent test**: `sync_active()` truth table (8 rows) passes; pre-review gate tests pass on the new env; baseline fixtures exist and are non-empty.
Subtasks: T001, T002, T003, T004. **Prompt**: [tasks/WP01-sync-active-seam-foundation.md](./tasks/WP01-sync-active-seam-foundation.md)

### WP02 — Gate the runtime surface (registration/daemon/emission/local-capture)
**Goal**: route every arming site through `sync_active()`; emitter gated at `_emit`. **Priority**: P1. **Deps**: WP01.
**Independent test**: default-path spies prove daemon-spawn + enqueue seams not reached across create/mark-status/move-task/issue-verdict/accept/implement/merge/doctor/next; no store-lock warning.
Subtasks: T005, T006, T007, T008. **Prompt**: [tasks/WP02-gate-runtime-surface.md](./tasks/WP02-gate-runtime-surface.md)

### WP03 — #3470 body-capture short-circuit + anti-swallow
**Goal**: silence the body-outbox traceback on the default path without swallowing real errors when active. **Priority**: P1. **Deps**: WP02.
**Independent test**: LEGACY-layout bare install → no traceback; opt-in + real violation → surfaces via `DossierSyncResult.errors`.
Subtasks: T009, T010. **Prompt**: [tasks/WP03-3470-body-capture.md](./tasks/WP03-3470-body-capture.md)

### WP04 — Conftest de-mask + fixtures + CI opt-in
**Goal**: make default-off the suite default so skipif actually fires; keep opt-in exercisable. **Priority**: P1. **Deps**: WP01.
**Independent test**: one sync module skips on default; `sync_enabled` fixture restores it; CI opt-in job runs it green.
Subtasks: T011, T012, T013. **Prompt**: [tasks/WP04-conftest-demask-ci.md](./tasks/WP04-conftest-demask-ci.md)

### WP05 — Skipif rollout (mechanical additive)
**Goal**: gate all sync-coupled test modules on the opt-in. **Priority**: P1. **Deps**: WP02, WP04. **Mechanical additive rollout** (census-guarded, WP06).
**Independent test**: default run over the clusters = skipped, 0 failed; #2809's two tests no longer red.
Subtasks: T014, T015, T016. **Prompt**: [tasks/WP05-skipif-bulk-rollout.md](./tasks/WP05-skipif-bulk-rollout.md)

### WP06 — File-count census guard
**Goal**: lock the gated file set so deletion AND un-skipping both red. **Priority**: P2. **Deps**: WP01, WP05.
**Independent test**: census passes at HEAD; removing a skipif or deleting a file reds it.
Subtasks: T017. **Prompt**: [tasks/WP06-file-count-census.md](./tasks/WP06-file-count-census.md)

### WP07 — Arch guards + goldens + NFR-004 parity
**Goal**: update the guards that must assert the new default-off contract; two currently FIGHT it. **Priority**: P2. **Deps**: WP01, WP02.
**Independent test**: rewritten guards green under default-off; collection-parity test green under opt-in.
Subtasks: T018, T019, T020. **Prompt**: [tasks/WP07-arch-guards-goldens.md](./tasks/WP07-arch-guards-goldens.md)

### WP08 — Docs + CHANGELOG + doctor advisory copy
**Goal**: living-documentation for the opt-in default + breaking-change discoverability. **Priority**: P2. **Deps**: WP03, WP07.
**Independent test**: terminology guard green; docs describe opt-in; CHANGELOG has the breaking-change note.
Subtasks: T021, T022. **Prompt**: [tasks/WP08-docs-changelog.md](./tasks/WP08-docs-changelog.md)

## Dependency graph
```
WP01 ─┬─ WP02 ── WP03 ──┐
      │     └── WP07 ────┼── WP08
      └─ WP04 ── WP05 ── WP06
                  (WP07 also deps WP01+WP02; WP06 deps WP01+WP05)
```
MVP = WP01+WP02+WP03 (the behavioral core). Test/guard/doc WPs harden it.

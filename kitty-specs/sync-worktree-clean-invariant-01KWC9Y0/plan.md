# Implementation Plan: Worktree-Clean Sync Invariant

**Branch**: `fix/sync-worktree-clean-invariant` | **Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/sync-worktree-clean-invariant-01KWC9Y0/spec.md`
**Source issue**: [#2263](https://github.com/Priivacy-ai/spec-kitty/issues/2263)

## Summary

Read-like and background commands (status-event emission; `sync status/pull/push/run`; `tracker status`/`map list`; the dashboard daemon tick) currently write `.kittify/config.yaml` as a side effect — through identity completion on the emit path (`ensure_identity`) and tracker `binding_ref` upgrades on read paths (`_maybe_upgrade_binding_ref → save_tracker_config`). Because `config.yaml` is not in the clean-tree allowlist, those writes dirty the worktree and make `record-analysis` (and peers) refuse with `DIRTY_WORKTREE`.

**Technical approach:** migrate the 8 read-context `ensure_identity` call sites to the existing side-effect-free `resolve_identity` (`identity/project.py:336`); make the missing-`build_id` case deterministic so read-path resolution is stable without persisting (**Decision C** — see research.md); convert the tracker `binding_ref` upgrade to a report-only `pending_binding_upgrade` on read paths; and enforce the result with one parametrized "no-dirty-tree" contract test across the whole command surface. Identity/binding persistence remains only at write-authorized boundaries (`init`, explicit bind/apply). No SaaS server changes; no allowlist expansion.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), rich (console), ruamel.yaml (config I/O), git (subprocess), pytest
**Storage**: `.kittify/config.yaml` (YAML; canonical store for project identity + tracker binding) — unchanged in location and schema
**Testing**: pytest with a parametrized no-dirty-tree contract test; `mypy --strict`; `ruff`; ≥90% coverage on new/changed lines; daemon/real-port variants run serially (`-n0`) per the repo parallel-test rules
**Target Platform**: cross-platform CLI (Linux, macOS, Windows)
**Project Type**: single (CLI library — `src/specify_cli/`)
**Performance Goals**: ≤ 50 ms added wall-clock per read command (NFR-002; expected ≤ 0 since a write is removed). **Verified by construction**, not by a wall-clock test: WP04's "no added write" assertion is the NFR-002 proxy (removing the write is the only latency change; a timing test would be flaky and violate NFR-004).
**Constraints**: do NOT allowlist `config.yaml`/`kitty-specs/**` (C-001); no auto `doctor --fix` (C-002); `config.yaml` stays the canonical store, only the persistence *boundary* moves (C-003); no on-the-wire/server changes (C-004); backward-compatible for complete-identity checkouts (C-005)
**Scale/Scope**: ~8 read-path call-site swaps + a deterministic `build_id` helper + tracker report-only change + 1 parametrized contract test; ≈ 6–10 files touched

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Charter item | Status | Note |
|--------------|--------|------|
| DIRECTIVE_001 — Architectural Integrity | ✅ PASS | Fix hardens an existing seam (read-only vs write-authorized identity; read vs persist tracker binding). No new boundary crossings. |
| DIRECTIVE_003 — Decision Documentation | ✅ PASS | The identity-stability choice is recorded as decision `DM-01KWCAQMZM…` and elaborated in research.md (with rejected A/B). |
| DIRECTIVE_010 — Specification Fidelity | ✅ PASS | Plan maps 1:1 to spec FR-001…FR-008 / NFR-001…004 / C-001…005. |
| DIRECTIVE_024 — Locality of Change | ✅ PASS | Comprehensive scope, but each change is local (one-line call-site swaps, one helper, one report-only branch, one test). |
| Project policy — mypy --strict / ruff / ≥90% new-code coverage / integration tests for CLI | ✅ PASS (target) | Encoded in Technical Context + acceptance. |
| Sonar — complexity ≤15, no new suppressions, repeated literals→constants | ✅ PASS (target) | Deterministic-`build_id` helper and report-only branch are small, single-purpose functions. |

**No charter violations → Complexity Tracking is empty.**

## Project Structure

### Documentation (this mission)

```
kitty-specs/sync-worktree-clean-invariant-01KWC9Y0/
├── plan.md              # This file
├── research.md          # Phase 0 — determinism finding, SaaS research, Decision C
├── data-model.md        # Phase 1 — identity/binding state model + build_id derivation
├── quickstart.md        # Phase 1 — how to verify the invariant locally
├── contracts/           # Phase 1 — behavioral contracts (identity, invariant, tracker)
└── tasks.md             # Phase 2 — created later by /spec-kitty.tasks
```

### Source Code (repository root)

```
src/specify_cli/
├── identity/
│   └── project.py            # resolve_identity (use), ensure_identity (keep at write boundaries),
│                             #   with_defaults / new deterministic build_id derivation
├── sync/
│   ├── emitter.py            # :100,:115 ensure_identity -> resolve_identity
│   ├── routing.py            # :47 ensure_identity -> resolve_identity
│   ├── events.py             # :180 ensure_identity -> resolve_identity
│   ├── __init__.py           # :253 ensure_identity -> resolve_identity
│   └── dossier_pipeline.py   # :233 ensure_identity -> resolve_identity
├── tracker/
│   ├── saas_service.py       # _maybe_upgrade_binding_ref -> report-only pending_binding_upgrade
│   ├── origin.py             # :452 ensure_identity -> resolve_identity (read context)
│   └── config.py             # save_tracker_config stays; called only on explicit bind/apply
└── cli/commands/
    ├── tracker.py            # :680 keep ensure_identity (tracker bind write boundary)
    ├── init.py               # :99,:863 ensure_identity — KEEP (write-authorized boundary)
    └── agent/mission_record_analysis.py  # clean-tree guard — unchanged; regression-tested

tests/specify_cli/sync/
└── test_worktree_clean_invariant.py   # NEW parametrized no-dirty-tree contract test
```

**Structure Decision**: Single-project CLI layout (existing). No new top-level directories. One new test module; all production changes are localized edits inside `identity/`, `sync/`, `tracker/`, and `cli/commands/`.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Side-effect-free identity on read/emit paths (with stable `build_id`)

- **Purpose**: Make read/emit identity resolution non-persisting while keeping identity stable across invocations (the core of the bug + NFR-001).
- **Relevant requirements**: FR-002, FR-003, NFR-001, NFR-002, C-003, C-005; scenarios AS-1, AS-2, AS-5, AS-6.
- **Affected surfaces**: `identity/project.py` (deterministic `build_id` derivation when missing; keep `ensure_identity` for write boundaries), `sync/emitter.py:100,115`, `sync/routing.py:47`, `sync/events.py:180`, `sync/__init__.py:253`, `sync/dossier_pipeline.py:233`, `tracker/origin.py:452`, `cli/commands/tracker.py:680`.
- **Sequencing/depends-on**: none (foundational).
- **Risks**: must NOT change `project_uuid` generation (Decision C); must keep `ensure_identity` at `init.py:99,863`; verify each migrated call site is genuinely read-context (not a hidden write boundary).

### IC-02 — Tracker `binding_ref` report-only on read paths

- **Purpose**: Stop read-like tracker ops from persisting `binding_ref` to `config.yaml`; surface available upgrades instead.
- **Relevant requirements**: FR-004, C-003; scenario AS-3.
- **Affected surfaces**: `tracker/saas_service.py` (`_maybe_upgrade_binding_ref` and its callers `status`/`sync_pull`/`sync_push`/`sync_run`/`map_list`), `tracker/config.py` (`save_tracker_config` invoked only on explicit bind/apply).
- **Sequencing/depends-on**: none (parallel with IC-01).
- **Risks**: ensure an explicit `tracker bind`/apply path still persists (no functional regression for intentional upgrades); choose where `pending_binding_upgrade` surfaces (result field + optional one-line notice).

### IC-03 — Worktree-clean invariant enforcement test

- **Purpose**: Encode INV-1 as a parametrized contract test that fails if any covered command dirties a clean checkout — including new commands added later.
- **Relevant requirements**: FR-005, FR-006, FR-008, NFR-004; scenarios AS-1, AS-6, AS-7.
- **Affected surfaces**: `tests/specify_cli/sync/test_worktree_clean_invariant.py` (new), modeled on `tests/specify_cli/cli/commands/test_accept_clean_tree.py`, `tests/mission_runtime/test_self_bookkeeping_allowlist.py`, `tests/specify_cli/cli/commands/test_accept_readiness_no_write.py`.
- **Sequencing/depends-on**: exercises IC-01 and IC-02 (authored alongside; can be written test-first).
- **Risks**: daemon/real-port variants must run serially; per-worker HOME isolation must be respected; the test must assert byte-identical `git status --porcelain` AND config.yaml mtime/content.

### IC-04 — `record-analysis` guard regression preservation

- **Purpose**: Prove the clean-tree gate still catches *genuine* dirt after the fix (no weakening / no allowlist creep).
- **Relevant requirements**: FR-007, C-001; scenario AS-4.
- **Affected surfaces**: `cli/commands/agent/mission_record_analysis.py` (no change), regression assertion in the new test module.
- **Sequencing/depends-on**: none.
- **Risks**: must assert a real source edit still yields `DIRTY_WORKTREE`; must assert the allowlist did NOT grow to include `config.yaml`.

## Phase 0 — Research

Complete. See [research.md](./research.md). The single open question (identity-completion determinism, NFR-001) is resolved: `with_defaults` mints random `uuid4` for `project_uuid`/`build_id`, so the realistic legacy-incomplete case drifts `build_id`; **Decision C** derives a missing `build_id` deterministically. SaaS-side research confirms a deterministic `build_id` is constraint-safe and drift cannot strand missions/WPs.

## Phase 1 — Design & Contracts

Complete. See [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md).

## Complexity Tracking

*No charter violations — none.*

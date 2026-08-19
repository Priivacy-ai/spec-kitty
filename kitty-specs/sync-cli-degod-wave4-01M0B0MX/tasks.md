# Tasks: Sync CLI Degod — Wave 4

**Mission**: `sync-cli-degod-wave4-01M0B0MX` | **Branch**: `refactor/wave4-sync-degod`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Contract**: [contracts/sync-cli-characterization-contract.md](./contracts/sync-cli-characterization-contract.md)
**Squad guards**: [research/squad-findings-post-plan.md](./research/squad-findings-post-plan.md) — read the plan's "WP-translation guards" §.

## Lane shape (critical)

Per the post-plan squad: **every degod WP edits the single `cli/commands/sync.py`** (removes a body, adds a call-through), so those WPs **cannot run in parallel lanes** — they are a **dependency chain** (same lane, overlap-exempt). Only `walker.py` (WP01) and the golden-harness test files (WP02) are independent lanes.

- **lane-a**: WP01 (walker — independent).
- **lane-b**: WP02 (golden harness — independent, prerequisite).
- **lane-c (serial chain)**: WP03 → WP04 → WP05 → WP06 → WP07 → WP08 → WP09 → WP10 → WP11 → WP12 (all share `sync.py`).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Complete walker.py named-constant set (directive/tactic/action/profile URNs) | WP01 | [P] |
| T002 | Replace raw URN literals + fix the 2 re-inlined constants; S1192 → 0 | WP01 | |
| T003 | Confirm `test_walker.py` frozenset-equality green | WP01 | |
| T004 | Golden harness scaffolding (CliRunner, `SPEC_KITTY_ENABLE_SAAS_SYNC=1` fixture, HOME isolation) | WP02 | [P] |
| T005 | Freeze the "safe" subcommands' flags/exit-codes/`--json` (routes/share/opt-*/now/gc/archive/mode/migrate/project-store/import-history/server + `status --check --json` + `diagnose --json`) | WP02 | |
| T006 | Enumerate + document the ~60 monkeypatched-callee set (the seam co-gate baseline) | WP02 | |
| T007 | Husk re-export block + late-bound `sync_module.<name>` convention + AST early-bind guard | WP03 | |
| T008 | `SyncPorts` skeleton + `default_ports()` (reuse Render/GitOps/Clock/FsReader) | WP03 | |
| T009 | sync.py Tier-1: extract S3358 nested ternaries (shared `_depth_color` for L184≡L6043) | WP03 | |
| T010 | sync.py Tier-1: reference re-inlined S1192 literals; correct S7632 suppression *format* (never delete a guarded except) | WP03 | |
| T011 | Extract `sync_render.py` (Console emit + `--json` envelopes) behind the Render port | WP04 | |
| T012 | Extract `sync_runtime.py` (runtime-open/lifecycle + config I/O adapters) | WP05 | |
| T013 | Extract `sync_purge_core.py` (census differentials + verdict — pure) + `sync_purge_exec.py` (readers/executors); retire `purge` cc26 | WP06 | |
| T014 | Extract `sync_store_report_core.py` — split the 3 shared render+`issues` helpers into compute (pure) + render | WP07 | |
| T015 | Extract `sync_authority.py` — three surfaces (read/write/admission) delegating to preflight/sharing_client/target_authority; author `test_sync_two_authority.py` (allowlist discriminator) | WP07 | |
| T016 | Extract `sync_dispatch_core.py` (batching + exit-code map — pure) + `sync_dispatch_exec.py`; retire `_enforce_sync_now_exit` cc22 | WP08 | |
| T017 | Freeze `status` full human-render golden (the cc-90 path) | WP09 | |
| T018 | Extract `sync_status_core.py` (gather-I/O → `build_status_rows`/`evaluate_boundary_coherence` → render shell); retire `status` C901 | WP09 | |
| T019 | Freeze `doctor` golden (non-json table + issues + healthy/unhealthy + exit-4 recovery) | WP10 | |
| T020 | Extract `sync_doctor_core.py` (gather-I/O → `build_doctor_report` → render shell); retire `doctor` C901 | WP10 | |
| T021 | Freeze `sync_workspace` golden (monkeypatch-golden stubbing `get_vcs`/`_detect_workspace_context`) | WP11 | |
| T022 | Degod `sync_workspace` into a thin shell; retire its C901 (daemon read/guard relocates intact) | WP11 | |
| T023 | Husk finalize: re-pin arch-gate baselines vs `upstream/main` (dead-symbol/module, ratchet, golden-count, CLI-count, writer-census 1:1 key swaps) | WP12 | |
| T024 | `docs/plans/code-quality/sync-env-census.md` + an executable FR-007 env-set-unchanged guard | WP12 | |
| T025 | File the deferred follow-on issue(s) (adapter-consolidation WS4/WS6-gated + env retirement-candidates) under #1797 / #1619 | WP12 | |

## Work Packages

### WP01 — Walker campsite (independent, lands first)
- **Goal**: Complete `calibration/walker.py`'s named-constant set; clear its 14 `S1192` smells with byte-identical behavior. **Independent of the degod.**
- **Priority**: P2 (campsite). **Execution mode**: code_change. **Dependencies**: none.
- **Independent test**: `tests/calibration/test_walker.py` passes (frozenset-equality); `ruff` reports 0 `S1192` on the file.
- **Subtasks**: T001, T002, T003. **Prompt**: [tasks/WP01-walker-constant-completion.md](./tasks/WP01-walker-constant-completion.md) · ~160 lines.
- **Requirements**: FR-005, NFR-003.

### WP02 — Golden-CLI characterization harness (independent, prerequisite for the chain)
- **Goal**: Freeze the observable contract of the "safe" `spec-kitty sync` subcommands before any extraction; enumerate the monkeypatched-callee seam set. (The GAP commands — `status` full-render, `doctor`, `sync_workspace` — are frozen in their own extraction WPs.)
- **Priority**: P1. **Execution mode**: code_change. **Dependencies**: none.
- **Independent test**: `tests/characterization/test_sync_*.py` green on pre-decomposition `sync.py`; must NOT mutate DIR-041 ratchets.
- **Subtasks**: T004, T005, T006. **Prompt**: [tasks/WP02-golden-characterization-harness.md](./tasks/WP02-golden-characterization-harness.md) · ~240 lines.
- **Requirements**: FR-001, NFR-001, C-003.

### WP03 — Husk scaffold + sync.py Tier-1 (chain head)
- **Goal**: Establish the husk re-export block + late-bind convention + `SyncPorts` skeleton, and land the Tier-1 mechanical fixes. **First WP that edits `sync.py`.**
- **Priority**: P1. **Execution mode**: code_change. **Dependencies**: WP02.
- **Independent test**: golden + the ~60 patch-tests green; `sync.py` `S3358`/`S1192`/`S7632` cleared; the AST early-bind guard passes.
- **Subtasks**: T007, T008, T009, T010. **Prompt**: [tasks/WP03-husk-scaffold-and-tier1.md](./tasks/WP03-husk-scaffold-and-tier1.md) · ~260 lines.
- **Requirements**: FR-006, C-005, NFR-003.

### WP04 — Render adapter
- **Goal**: Extract `sync_render.py` (all Console emit + `--json` envelopes) behind the Render port; `sync.py` calls through.
- **Priority**: P1. **Execution mode**: code_change. **Dependencies**: WP03.
- **Independent test**: golden + patch-tests green.
- **Subtasks**: T011. **Prompt**: [tasks/WP04-render-adapter.md](./tasks/WP04-render-adapter.md) · ~180 lines.
- **Requirements**: FR-002, C-001, C-002.

### WP05 — Runtime + config adapters
- **Goal**: Extract `sync_runtime.py` (runtime-open/lifecycle + config I/O).
- **Priority**: P1. **Execution mode**: code_change. **Dependencies**: WP04.
- **Subtasks**: T012. **Prompt**: [tasks/WP05-runtime-config-adapters.md](./tasks/WP05-runtime-config-adapters.md) · ~180 lines.
- **Requirements**: FR-002, C-001, C-002.

### WP06 — Purge core + exec (self-contained)
- **Goal**: Extract `sync_purge_core.py` (pure differentials/verdict) + `sync_purge_exec.py`; retire `purge` cc26. Best-isolated subsystem.
- **Priority**: P1. **Execution mode**: code_change. **Dependencies**: WP05.
- **Subtasks**: T013. **Prompt**: [tasks/WP06-purge-core-and-exec.md](./tasks/WP06-purge-core-and-exec.md) · ~200 lines.
- **Requirements**: FR-002, NFR-002.

### WP07 — Store-report core + authority adapters (before the monsters)
- **Goal**: Extract `sync_store_report_core.py` (split the 3 shared render+`issues` helpers into pure compute + render) and `sync_authority.py` (three surfaces, delegating); author the FR-004 two-authority arch-test.
- **Priority**: P1. **Execution mode**: code_change. **Dependencies**: WP06.
- **Independent test**: `test_sync_two_authority.py` green; golden + patch-tests green.
- **Subtasks**: T014, T015. **Prompt**: [tasks/WP07-store-report-and-authority.md](./tasks/WP07-store-report-and-authority.md) · ~260 lines.
- **Requirements**: FR-002, FR-004, C-002, C-007.

### WP08 — Dispatch core + exec
- **Goal**: Extract `sync_dispatch_core.py` (pure batching + exit-code map) + `sync_dispatch_exec.py`; retire `_enforce_sync_now_exit` cc22.
- **Priority**: P1. **Execution mode**: code_change. **Dependencies**: WP07.
- **Subtasks**: T016. **Prompt**: [tasks/WP08-dispatch-core-and-exec.md](./tasks/WP08-dispatch-core-and-exec.md) · ~200 lines.
- **Requirements**: FR-002, NFR-002.

### WP09 — `status` degod (retire C901)
- **Goal**: Freeze the `status` full-human-render golden FIRST, then restructure `status` (cc 90) into gather-I/O → `sync_status_core` → render shell; retire its `# noqa: C901`.
- **Priority**: P1. **Execution mode**: code_change. **Dependencies**: WP08.
- **Independent test**: the new full-render golden green pre/post; `status` ≤ 15, no `# noqa: C901`.
- **Subtasks**: T017, T018. **Prompt**: [tasks/WP09-status-degod.md](./tasks/WP09-status-degod.md) · ~280 lines.
- **Requirements**: FR-001, FR-003, NFR-002, SC-001.

### WP10 — `doctor` degod (retire C901)
- **Goal**: Freeze the `doctor` golden FIRST, then restructure `doctor` (cc 73) into gather-I/O → `sync_doctor_core` → render shell; retire its `# noqa: C901`.
- **Priority**: P1. **Execution mode**: code_change. **Dependencies**: WP09.
- **Subtasks**: T019, T020. **Prompt**: [tasks/WP10-doctor-degod.md](./tasks/WP10-doctor-degod.md) · ~260 lines.
- **Requirements**: FR-001, FR-003, NFR-002, SC-001.

### WP11 — `sync_workspace` degod (retire C901)
- **Goal**: Freeze the `sync_workspace` monkeypatch-golden (stub `get_vcs`/`_detect_workspace_context`) FIRST, then degod `sync_workspace` into a thin shell; retire its `# noqa: C901`. Daemon read/guard code relocates intact (C-004).
- **Priority**: P1. **Execution mode**: code_change. **Dependencies**: WP10.
- **Subtasks**: T021, T022. **Prompt**: [tasks/WP11-sync-workspace-degod.md](./tasks/WP11-sync-workspace-degod.md) · ~240 lines.
- **Requirements**: FR-001, FR-003, NFR-002, SC-001, C-004.

### WP12 — Husk finalize + governance closeout
- **Goal**: Re-pin the arch-gate baselines vs `upstream/main` (with per-writer census 1:1 key swaps); produce `docs/plans/code-quality/sync-env-census.md` + an executable FR-007 env-set-unchanged guard; file the deferred follow-on issue(s).
- **Priority**: P2. **Execution mode**: code_change. **Dependencies**: WP11.
- **Independent test**: full arch-gate suite green; env-set-unchanged guard green; follow-on issue link recorded.
- **Subtasks**: T023, T024, T025. **Prompt**: [tasks/WP12-husk-finalize-and-closeout.md](./tasks/WP12-husk-finalize-and-closeout.md) · ~220 lines.
- **Requirements**: FR-007, FR-008, NFR-004, C-005.

## MVP

The MVP arc is **WP02 (golden) → WP03 (husk+Tier-1)** — the safety net + seam that make every later extraction safe. WP09/WP10/WP11 (the three C901 retirements) are the mission's headline payoff.

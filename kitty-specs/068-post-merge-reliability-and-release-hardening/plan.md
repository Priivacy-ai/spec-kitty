# Implementation Plan: Post-Merge Reliability And Release Hardening

**Mission**: 068-post-merge-reliability-and-release-hardening
**Branch**: `main` (planning, base, and merge target — all `main`)
**Date**: 2026-04-07
**Spec**: [spec.md](spec.md)
**Plan input**: [spec.md](spec.md) FR-001..FR-022 + FR-023, NFR-001..NFR-006, C-001..C-006
**Validated against**: Fresh clone `/tmp/spec-kitty-20260407-090957` at commit `7307389a1f529dae9e90279ea972609bb0b420aa`

---

## Summary

Final workflow-stabilization mission for spec-kitty core. Five work packages drive the open backlog to zero:

| WP | Scope | Owns FRs | Issues |
|---|---|---|---|
| **WP01** | Post-merge stale-assertion analyzer (new `src/specify_cli/post_merge/` package + new `agent tests` CLI group) | FR-001..FR-004, FR-022 | #454 |
| **WP02** | `--strategy` wiring + squash default + status-events `safe_commit` fix (all in `_run_lane_based_merge`) | FR-005..FR-009, FR-019, FR-020 | #456, #416 (fix) |
| **WP03** | Diff-coverage policy validation + close-or-tighten | FR-010..FR-012 | #455 |
| **WP04** | Release-prep CLI populating the existing `agent/release.py` stub | FR-013..FR-023 | #457 |
| **WP05** | `scan_recovery_state` + `implement --base main` fix (FR-021), verification report, mission-close ledger | FR-016..FR-018, FR-021 | #415, #416 (verification) |

The technical approach is locked by the spec; this plan captures the architectural decisions made during planning interrogation, the file/module layout, the contracts between WPs, and the cross-WP sequencing constraints.

---

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty requirement)
**Primary Dependencies**:
- `typer` — CLI framework (existing)
- `rich` — console output (existing)
- `ruamel.yaml` — YAML parsing for `.kittify/config.yaml` (existing)
- Stdlib `ast` — Python AST parsing for WP01 stale-assertion analysis (no new dependency)
- Stdlib `subprocess` — git invocation (existing pattern in `specify_cli.git.commit_helpers`)
- `safe_commit` from `specify_cli.git` (existing helper, re-exported from `commit_helpers.py:38`)
- `specify_cli.lanes.recovery.scan_recovery_state` (existing, extended by FR-021)
- `specify_cli.status.emit.emit_status_transition` (existing, called by `_mark_wp_merged_done`)

**Storage**: Filesystem only (no database). Mission state lives in:
- `kitty-specs/<mission>/status.events.jsonl` — append-only event log (canonical lane state)
- `kitty-specs/<mission>/status.json` — derived snapshot
- `.kittify/config.yaml` — project configuration (`merge.strategy` key added by WP02)
- `.kittify/runtime/merge/<mission_id>/state.json` — ephemeral runtime state (out of scope for the FR-019 fix)

**Testing**: pytest. All new tests SHALL be added to the existing pytest suite and SHALL run without network access (NFR-005).

**Target Platform**: Cross-platform CLI (macOS, Linux). FSEvents-specific timing concerns are explicitly out of scope per the Assumptions section.

**Project Type**: Single Python package (`src/specify_cli/`). No web frontend, no mobile target.

**Performance Goals**:
- WP01 stale-assertion analyzer: ≤ 30 seconds wall-clock on spec-kitty core (~9000+ tests) — NFR-001
- WP04 release-prep command: ≤ 5 seconds wall-clock on a mission with up to 16 WPs — NFR-004
- WP02 mission→target merge: 100% success against `require_linear_history = true` on the integration test matrix — NFR-003

**Constraints**:
- `mypy --strict` clean (NFR-006, charter)
- ruff clean (charter)
- Critical-path diff coverage threshold pinned at commit `7307389a` (NFR-006, with WP03 carve-out)
- WP01 analyzer ≤ 5 false-positive findings per 100 LOC of merged change on a curated benchmark (NFR-002)
- No GitHub API calls (C-002)
- No re-implementation of existing recovery/merge subsystems (C-003)

**Scale/Scope**: Five work packages. ~8 new functional surfaces (analyzer module, agent tests CLI group, strategy wiring, safe_commit fix, scan_recovery_state extension, --base support, release-prep command, validation report). Two pre-identified residual gaps to fix; one verification report to author; one mission close ledger to maintain.

---

## Charter Check

**GATE STATUS**: ✅ PASS (pre-Phase-0)

Charter file: `.kittify/charter/charter.md` (loaded via `spec-kitty charter context --action plan --json`)

| Charter requirement | Compliance | Notes |
|---|---|---|
| **typer** as CLI framework | ✅ | All new commands use typer (WP01 `agent tests`, WP04 `agent release prep`) |
| **rich** for console output | ✅ | Stale-assertion report and release-prep payload both use rich for human output |
| **ruamel.yaml** for YAML parsing | ✅ | `.kittify/config.yaml` `merge.strategy` key parsed via existing ruamel.yaml infrastructure |
| **pytest** with **90%+ test coverage for new code** | ✅ | NFR-006 enforces critical-path coverage threshold; FR-020 and the FR-021 regression test land alongside production code |
| **mypy --strict** must pass | ✅ | NFR-006 |
| **Integration tests for CLI commands** | ✅ | FR-020 (lane merge end-to-end), FR-022 fallback test, FR-021 recovery integration test, FR-023 release-prep CLI test |
| **DIRECTIVE_010 Specification Fidelity** | ✅ | Plan derives from spec FRs verbatim; no deviations introduced |
| **DIRECTIVE_003 Decision Documentation** | ✅ | Architectural decisions captured in `research.md`; cross-WP sequencing captured here and in spec FR-019 |

**Charter Check post-Phase-1 re-evaluation**: see end of this document.

---

## Project Structure

### Documentation (this feature)

```
kitty-specs/068-post-merge-reliability-and-release-hardening/
├── spec.md                       # Mission spec (already authored)
├── plan.md                       # This file
├── research.md                   # Phase 0: architectural decisions and current-main analysis
├── data-model.md                 # Phase 1: dataclasses, event shapes, payload schemas
├── quickstart.md                 # Phase 1: maintainer-facing how-to for the new commands and bug fixes
├── contracts/                    # Phase 1: CLI command + library function signatures
│   ├── stale_assertions.md       # WP01 contract
│   ├── merge_strategy.md         # WP02 contract (CLI flag, config schema, library functions)
│   ├── diff_coverage_policy.md   # WP03 contract (validation report shape)
│   ├── release_prep.md           # WP04 contract (CLI command + JSON payload)
│   └── recovery_extension.md     # WP05 contract (scan_recovery_state + --base main)
├── meta.json                     # Mission identity (already authored)
├── checklists/
│   └── requirements.md           # Spec quality checklist
├── tasks/                        # Phase 2: WP files (NOT created by /spec-kitty.plan)
└── mission-close-ledger.md       # Created by WP05 at mission close (per C-005)
```

### Source Code (repository root)

```
src/specify_cli/
├── post_merge/                            # NEW package (WP01)
│   ├── __init__.py                        # Re-exports run_check, StaleAssertionFinding, StaleAssertionReport
│   └── stale_assertions.py                # AST-based source identifier extraction + AST-based test scan
├── cli/commands/
│   ├── merge.py                           # MODIFIED (WP02): wire --strategy, default to squash, safe_commit fix
│   ├── implement.py                       # MODIFIED (WP05 FR-021): accept --base main flag
│   └── agent/
│       ├── __init__.py                    # MODIFIED: register new `tests` subapp
│       ├── release.py                     # POPULATED (WP04): replace stub with real `prep` command
│       └── tests.py                       # NEW (WP01): `stale-check` subcommand
├── lanes/
│   ├── merge.py                           # MODIFIED (WP02): honor strategy parameter from upper layer
│   └── recovery.py                        # MODIFIED (WP05 FR-021): scan_recovery_state consults status events
├── git/
│   └── commit_helpers.py                  # USED AS-IS (safe_commit imported by WP02)
├── status/
│   ├── emit.py                            # USED AS-IS (emit_status_transition called by mark-done loop)
│   ├── store.py                           # USED AS-IS (append_event)
│   └── reducer.py                         # USED AS-IS (materialize for WP05 verification)
└── release/                               # NEW package (WP04, locked — package split committed at plan time)
    ├── __init__.py
    ├── changelog.py                       # Build draft changelog from mission/WP artifacts
    ├── version.py                         # Version bump per channel
    └── payload.py                         # Build structured release-prep payload

.kittify/
├── config.yaml                            # MODIFIED (WP02): merge.strategy schema added
└── charter/charter.md                     # USED AS-IS

.github/workflows/
└── ci-quality.yml                         # POSSIBLY MODIFIED (WP03, only if validation finds residual gap)

tests/
├── post_merge/
│   └── test_stale_assertions.py           # NEW (WP01): FR-002, FR-022, NFR-001, NFR-002 coverage
├── cli/commands/
│   ├── test_merge_strategy.py             # NEW (WP02 FR-005..FR-009): strategy wiring + push-error parser
│   ├── test_merge_status_commit.py        # NEW (WP02 FR-019, FR-020): events committed to git
│   └── test_implement_base_flag.py        # NEW (WP05 FR-021): --base main flag
├── lanes/
│   └── test_recovery_post_merge.py        # NEW (WP05 FR-021): scan_recovery_state with merged-deleted branches
├── cli/commands/agent/
│   ├── test_release_prep.py               # NEW (WP04 FR-013..FR-023): release-prep CLI + JSON payload
│   └── test_tests_stale_check.py          # NEW (WP01 FR-004): CLI subcommand wires through to library
└── (existing tests untouched unless WP03 changes ci-quality policy)
```

**Structure Decision**: This is a **single Python project** that extends an existing CLI tool. No web/mobile/multi-project structure. New code lands in:
- `src/specify_cli/post_merge/` — new package for WP01
- `src/specify_cli/cli/commands/agent/tests.py` — new CLI subgroup for WP01
- `src/specify_cli/release/` — new package for WP04 (package split is locked at plan time; not inlined)
- Existing files modified: `cli/commands/merge.py` (WP02), `cli/commands/implement.py` (WP05), `cli/commands/agent/release.py` (WP04), `cli/commands/agent/__init__.py` (WP01 + WP04 registrations), `lanes/merge.py` (WP02), `lanes/recovery.py` (WP05)

---

## Cross-WP Sequencing & Dependencies

The lane-planning step that runs after `/spec-kitty.tasks` will use this dependency graph to compute parallelism. Critical sequencing constraints:

```
WP01 ────────────────────────► (independent, parallel-safe)
                               new files only: post_merge/, agent/tests.py
                               touches agent/__init__.py for registration

WP02 ────────────────────────► (sequential within itself)
   FR-005/006/007/008 ─► FR-009 ─► FR-019 ─► FR-020
                                    │
                                    └── all edits land in _run_lane_based_merge
                                        in cli/commands/merge.py and lanes/merge.py

WP03 ────────────────────────► (verification-first, low-risk)
   FR-010 (validation report) ─► FR-011 OR FR-012
                                    │
                                    └── only touches .github/workflows/ if FR-012 fires

WP04 ────────────────────────► (independent, parallel-safe)
   touches cli/commands/agent/release.py + agent/__init__.py registration
   reads kitty-specs/ artifacts read-only

WP05 ────────────────────────► (independent of WP02 now that FR-019/020 moved)
   FR-021 ─► FR-016 (verification report) ─► FR-018 (mission close ledger)
   touches lanes/recovery.py + cli/commands/implement.py
```

### Lane-conflict matrix (file-level)

| File | Touched by |
|---|---|
| `src/specify_cli/cli/commands/merge.py` | WP02 only |
| `src/specify_cli/lanes/merge.py` | WP02 only |
| `src/specify_cli/lanes/recovery.py` | WP05 only |
| `src/specify_cli/cli/commands/implement.py` | WP05 only |
| `src/specify_cli/cli/commands/agent/__init__.py` | WP01 + WP04 (both add registrations) — **shared edit** |
| `src/specify_cli/cli/commands/agent/release.py` | WP04 only |
| `src/specify_cli/cli/commands/agent/tests.py` | WP01 only (new file) |
| `src/specify_cli/post_merge/` | WP01 only (new package) |
| `src/specify_cli/release/` | WP04 only (new package) |
| `.kittify/config.yaml` | WP02 only |
| `.github/workflows/ci-quality.yml` | WP03 only (and only if FR-012 fires) |

**Only shared edit**: `agent/__init__.py` (WP01 + WP04 both add subapp registrations). Each WP appends a single `app.add_typer(...)` line at the bottom of the file, registering different subapp names (`tests` for WP01, `release` for WP04). This is a textbook trivially-mergeable concatenation conflict — git resolves it without human help. **The lane planner MAY place WP01 and WP04 in separate lanes.** If both lanes register their subapp under different names (which they do), the merge has zero overlap.

**Recommended lane allocation** (to be confirmed at `/spec-kitty.tasks`):
- **Lane A**: WP02 (merge command — large, sequential, longest chain)
- **Lane B**: WP01 (stale-assertion analyzer — new package, isolated)
- **Lane C**: WP04 (release-prep — populates existing stub, isolated)
- **Lane D**: WP05 (recovery + implement)
- **Lane E**: WP03 (verification-first, low-risk, can run last)

This gives **5 parallel lanes maximum**, with the longest sequential chain inside Lane A (WP02's seven FRs — FR-005..FR-009 + FR-019/FR-020 — all touching the same file). The agent/__init__.py concatenation between lanes B and C is auto-resolvable.

If conflict-aversion is preferred over parallelism (e.g., to avoid even auto-resolvable merges), Lanes B and C can collapse into a single Lane B' that runs WP01 then WP04 sequentially. The default recommendation is full parallelism.

---

## Phase 0 Output Pointer

Phase 0 research is delivered as `kitty-specs/068-post-merge-reliability-and-release-hardening/research.md`.

Phase 0 deliverables:

1. **Decision log** for the three planning answers (library choice, command surface, library-import wiring)
2. **Current-main analysis** for the existing modules WP01/WP04 will integrate with (`stale_check.py`, `agent/release.py`, `commit_helpers.py`)
3. **Failure-mode reproduction** for the FR-019 bug (recovered from session evidence and FROM the spec's Mission 067 Failure-Mode Evidence (A) section)
4. **Failure-mode reproduction** for the FR-021 bug (scan_recovery_state + --base main, from Mission 067 Failure-Mode Evidence (B))
5. **Library-import wiring rationale** — why the merge runner imports `run_check` directly rather than spawning a subprocess

No `[NEEDS CLARIFICATION]` markers remain after Phase 0.

---

## Phase 1 Output Pointers

Phase 1 design artifacts:

1. **`data-model.md`** — dataclasses for `StaleAssertionFinding`, `StaleAssertionReport`, `ReleasePrepPayload`, `MergeStrategy`, `MergeConfig`, `RecoveryVerificationEntry`, `MissionCloseLedgerRow`. Plus the canonical shape of the new `done` event the safe_commit fix persists.
2. **`contracts/stale_assertions.md`** — WP01 library + CLI signatures
3. **`contracts/merge_strategy.md`** — WP02 CLI flag, config schema, library function signatures, push-error parser token list
4. **`contracts/diff_coverage_policy.md`** — WP03 validation report shape
5. **`contracts/release_prep.md`** — WP04 CLI command, JSON payload, integration with existing version-bump infrastructure
6. **`contracts/recovery_extension.md`** — WP05 `scan_recovery_state` extension surface, `--base main` flag, mission-close ledger schema
7. **`quickstart.md`** — maintainer-facing walkthrough: run a synthetic merge that exercises FR-019, run release-prep, run the stale-assertion analyzer, exercise the FR-021 post-merge unblocking path

Agent context file update happens at the end of Phase 1 via the existing agent script.

---

## Complexity Tracking

No charter violations. The spec was reviewed three times and all "complexity" the plan inherits is justified by either a tracked GitHub issue or a reproduced 067 failure mode. No items required.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none)    | n/a        | n/a                                  |

---

## Post-Phase-1 Charter Re-evaluation

**GATE STATUS**: ✅ PASS

After Phase 1 artifacts (`data-model.md`, `contracts/*`, `quickstart.md`) landed, the charter check was re-run against the design surface:

| Charter requirement | Phase 1 verification | Status |
|---|---|---|
| **typer** as CLI framework | All new CLI surfaces (`agent tests stale-check`, `agent release prep`, `--strategy`, `--base`) use typer parameters in their contract files | ✅ |
| **rich** for console output | `StaleAssertionReport` and `ReleasePrepPayload` both render via rich Console; merge runner reuses existing rich infrastructure | ✅ |
| **ruamel.yaml** for YAML parsing | `MergeConfig` reads `.kittify/config.yaml`'s `merge.strategy` key via the existing ruamel.yaml accessor in `specify_cli.config` | ✅ |
| **pytest** with **90%+ test coverage for new code** | Each contract file lists a test surface table mapping FRs to tests; FR-020 has the explicit regression test pattern; FR-021 has Scenario 7 coverage; FR-022 has its own fallback test | ✅ |
| **mypy --strict** must pass | All new dataclasses in `data-model.md` are fully typed with `Literal[...]`, `Path`, `list[...]`, `tuple[...]`, `Enum` — no `Any` leakage | ✅ |
| **Integration tests for CLI commands** | `test_strategy_flag_flows_through`, `test_done_events_committed_to_git`, `test_implement_base_flag_creates_workspace_from_ref`, `test_prep_command_emits_json_with_flag`, `test_cli_subcommand_invokes_library` — all integration-level | ✅ |
| **DIRECTIVE_010 Specification Fidelity** | Every contract file references the specific FR(s) it implements; no contract introduces behavior not in the spec | ✅ |
| **DIRECTIVE_003 Decision Documentation** | `research.md` captures all three planning decisions with rationale and rejected alternatives; cross-WP sequencing captured in `plan.md` and `spec.md` FR-019 | ✅ |

**No new charter violations introduced by Phase 1 artifacts.** Spec ↔ plan ↔ design alignment is verified.

### NFR coverage map

| NFR | Threshold | Phase 1 verification location |
|---|---|---|
| NFR-001 | ≤ 30s wall clock | `contracts/stale_assertions.md` test `test_runs_within_30s_on_spec_kitty_core` |
| NFR-002 | ≤ 5 FP / 100 LOC | `contracts/stale_assertions.md` test `test_fp_ceiling_under_5_per_100_loc` + FR-022 fallback |
| NFR-003 | 100% success on protected linear-history matrix | `contracts/merge_strategy.md` test `test_protected_linear_history_succeeds_default` |
| NFR-004 | ≤ 5s for 16-WP missions | `contracts/release_prep.md` test `test_runs_within_5s_for_16_wps` |
| NFR-005 | 0 network calls in new tests | `contracts/release_prep.md` test `test_payload_no_github_api_calls`; charter requirement |
| NFR-006 | mypy strict + critical-path coverage at commit `7307389a` | `data-model.md` types fully annotated; WP03 carve-out documented in `contracts/diff_coverage_policy.md` |

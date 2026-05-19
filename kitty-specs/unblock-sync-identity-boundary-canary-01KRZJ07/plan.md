# Implementation Plan: Unblock Sync Identity-Boundary Canary

**Branch**: `main` (planning base) → merges into `main` | **Date**: 2026-05-19 | **Spec**: [spec.md](spec.md)
**Mission ID**: `01KRZJ079AYV48V0Y41EACAC79` (mid8 `01KRZJ07`)
**Mission slug**: `unblock-sync-identity-boundary-canary-01KRZJ07`

## Summary

Fix three CLI bugs surfaced by the 2026-05-19 deployed-dev sync identity-boundary canary against `spec-kitty-cli==3.2.0rc13`, restoring the canary to a working release gate for scenarios 1, 2, and 4.

**Technical approach**:
- **#1122** — Register a `mission_lifecycle_row` shape in `src/specify_cli/audit/shape_registry.py`; teach the `FORBIDDEN_KEYS` detector in `src/specify_cli/audit/detectors.py` to consult the registry and skip the rule on rows that match the lifecycle shape (`aggregate_type == "Mission"` + presence of `event_type`). The status-transition row family remains gated. No change to lifecycle event writers; `status.events.jsonl` continues to hold both row families.
- **#1123** — Refactor `_render_boundary_table` in `src/specify_cli/cli/commands/sync.py` (≈line 1856) so file-path boundary fields render via plain `Console.print(f"{label}: {path}")` outside the Rich `Table`. The Table continues to render non-path identity rows. The text rendering becomes byte-identical to the `--json` `active_queue.path` value for every path field.
- **#1124** — Implement a new `spec-kitty doctor restart-daemon` subcommand as a composition of the existing daemon-stop and daemon-start plumbing (read `DaemonOwnerRecord`, invoke stop, invoke launch path used by `sync now`). Refresh all four `_REMEDIATION_HINTS` occurrences in `src/specify_cli/sync/preflight.py` (lines 99, 103, 107, 119, plus the related comment at 218) in one pass to keep wording consistent.
- **Acceptance** — A final WP runs the canary locally against the rc bump that bundles these fixes and captures evidence under `kitty-specs/<mission>/canary-evidence/`. Scenarios 1, 2, and 4 must be green; scenario 3 is allowed to remain red because `#43` lives in the sibling repo.

## Technical Context

**Language/Version**: Python 3.11+ (existing `spec-kitty` codebase requirement)
**Primary Dependencies**: typer (CLI), rich (console output), ruamel.yaml (YAML), psutil (daemon-process management), pytest (testing), mypy --strict (type checking)
**Storage**: filesystem only — per-mission `status.events.jsonl`, `.kittify/queue.db` (SQLite via `OfflineQueue`), `DaemonOwnerRecord` on disk under the home-state root
**Testing**: pytest, integration tests for CLI commands (typer.testing.CliRunner), targeted regression tests per fix; 90%+ coverage on new code (charter)
**Target Platform**: macOS + Linux dev machines; Python 3.11+
**Project Type**: single Python project (existing layout, `src/specify_cli/...`)
**Performance Goals**: audit wall-clock ≤ 2× rc13 baseline on a 100-mission tree (NFR-001); `doctor restart-daemon` ≤ 10 s end-to-end (NFR-002)
**Constraints**: must remain additive — no migration of existing `status.events.jsonl` files; no rename of `_failure_lines_from_set` tokens or `ForegroundIdentity`/`DaemonOwnerRecord` fields (C-004); no file split for `status.events.jsonl` (C-003)
**Scale/Scope**: 3 bug fixes + 1 cross-repo acceptance run; 4 work packages total

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter source: `/Users/robert/spec-kitty-dev/1122-1123-1124-43/spec-kitty/.kittify/charter/charter.md`

| Gate | Result | Notes |
|------|--------|-------|
| Stack policy (typer, rich, ruamel.yaml, pytest, mypy --strict) | PASS | All fixes use the existing stack; no new dependencies introduced. |
| 90%+ test coverage on new code | PASS-by-design | FR-009 requires per-fix regression tests; canary verification WP provides end-to-end evidence. |
| Integration tests for CLI commands | PASS-by-design | `doctor restart-daemon`, `sync status --check`, and `doctor mission-state --audit` all covered by CLI-level tests via `CliRunner`. |
| `mypy --strict` | PASS-by-design | New code paths follow existing typing conventions of touched modules. |
| Directive 003 — Decision Documentation | PASS | 5 specify decisions + 4 plan decisions captured in `kitty-specs/<mission>/decisions/index.json`. |
| Directive 010 — Specification Fidelity | PASS | Plan directly mirrors FR/NFR/C from spec.md without redesign; deviations would have to be re-anchored via spec revisions. |
| Locality of change | PASS | Each fix is localized to 1–2 modules; no abstraction added beyond extending `shape_registry`. |

No charter violations; **Complexity Tracking is empty**.

## Project Structure

### Documentation (this feature)

```
kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/
├── spec.md
├── plan.md                            # this file
├── research.md                        # Phase 0 output
├── data-model.md                      # Phase 1 output (minimal — no new entities)
├── quickstart.md                      # Phase 1 output
├── contracts/                         # Phase 1 output (CLI command + JSON contracts)
│   ├── doctor-restart-daemon.md
│   ├── sync-status-check-rendering.md
│   └── audit-row-family.md
├── checklists/
│   └── requirements.md
├── decisions/
│   └── index.json
└── canary-evidence/                   # populated by the final WP (cross-repo canary run)
    └── README.md
```

### Source Code (repository root)

```
src/specify_cli/
├── audit/
│   ├── detectors.py                   # MODIFY: row-family-scoped FORBIDDEN_KEY rule
│   ├── shape_registry.py              # MODIFY: register `mission_lifecycle_row` shape
│   └── models.py                      # READ-ONLY (TEAMSPACE_BLOCKER_CODES reference)
├── cli/
│   └── commands/
│       ├── doctor.py                  # MODIFY: register `restart-daemon` typer command
│       └── sync.py                    # MODIFY: split path rows out of Rich Table
├── sync/
│   ├── preflight.py                   # MODIFY: refresh 4 _REMEDIATION_HINTS entries
│   └── (daemon-stop / daemon-start primitives)  # CONSUMED by restart-daemon
└── (no new modules introduced)

tests/specify_cli/
├── audit/
│   └── test_detectors_row_family.py   # NEW: regression for #1122
├── cli/
│   └── commands/
│       ├── test_doctor_restart_daemon.py   # NEW: regression for #1124 (subcommand)
│       └── test_sync_status_check_paths.py # NEW: regression for #1123
└── sync/
    └── test_preflight_remediation_hints.py # NEW: regression for #1124 (hints)
```

**Structure Decision**: Single Python project, existing `src/specify_cli/` layout. No new packages. Tests land under `tests/specify_cli/<package>/...` matching the source layout convention already in the repo.

## Complexity Tracking

*Fill ONLY if Charter Check has violations that must be justified*

No violations. Table omitted intentionally.

## Phase Plan

### Phase 0 — Research

See [research.md](research.md). Six research questions resolved:
1. Lifecycle row identification signal (concluded: `aggregate_type == "Mission"` + `event_type` presence).
2. Rich Table overflow behavior under non-TTY captures (concluded: 80-col default + ellipsis is structural; only refactor avoids it).
3. `DaemonOwnerRecord` shape and lifecycle (concluded: existing record carries enough metadata to drive restart).
4. Existing daemon stop + launch primitives reusable by `restart-daemon` (concluded: yes; located in `sync/` package).
5. Canary harness execution shape from the sibling repo (concluded: `pytest tests/identity_boundary/` with seeded fixtures).
6. Scope of `_REMEDIATION_HINTS` rewrite and the comment at line 218 (concluded: all five touch-points updated together).

### Phase 1 — Design & Contracts

See [data-model.md](data-model.md) and [contracts/](contracts/). No new persisted entities; the design surface is:
- The `mission_lifecycle_row` shape contract in the shape registry.
- The `sync status --check` rendering contract (path fields render verbatim outside the Rich Table; JSON contract unchanged).
- The `spec-kitty doctor restart-daemon` CLI contract (positional/flag shape, exit codes, error cases).

### Phase 2 — Tasks (deferred to `/spec-kitty.tasks`)

WP shape (informational only — actually generated by `/spec-kitty.tasks`):
- WP01 — `#1122` audit row-family classifier via `shape_registry`.
- WP02 — `#1123` path rendering outside the Rich Table.
- WP03 — `#1124` `doctor restart-daemon` subcommand + 4-hint refresh.
- WP04 — Canary local verification (cross-repo): clone/checkout `spec-kitty-end-to-end-testing`, run canary against the rc bump, capture artifacts to `kitty-specs/<mission>/canary-evidence/`. Scenarios 1, 2, 4 must be green; scenario 3 may remain red per C-002.

## Branch Strategy

- **Current branch at plan start**: `main`
- **Planning/base branch for this mission**: `main`
- **Final merge target**: `main`
- **`branch_matches_target`**: `true`
- All WP worktrees will be created later by `spec-kitty implement WP##` once `/spec-kitty.tasks` finalizes the work-package set.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Lifecycle-row classifier accidentally accepts a malformed status-transition row that carries `event_type`. | Test matrix in WP01 covers a synthetic row with `aggregate_type="Mission"` AND `from_lane`/`to_lane` and confirms it still fails (the lifecycle exception must require absence of status-transition discriminators). |
| `restart-daemon` invoked when no daemon is registered. | WP03 contract requires an explicit, actionable error message and non-zero exit code; tested via `CliRunner`. |
| `sync status --check` rendering refactor breaks the visible boundary identity Table for wide TTYs. | WP02 keeps the Table for non-path identity rows and snapshot-tests both the wide-TTY and piped-capture renderings. |
| Canary scenario 4 still fails for some unrelated reason after fixes land. | WP04 captures full artifacts and the mission's "done" criterion explicitly enumerates scenarios 1, 2, 4 — a fourth red signals a regression, not an out-of-scope #43-style harness gap. |
| Cross-repo coupling in WP04 surprises future implementers. | The WP explicitly documents the sibling-repo checkout location and the expected canary invocation; canary evidence committed in this repo makes the proof self-contained. |

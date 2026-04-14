# Implementation Plan: Windows Compatibility Hardening Pass

**Branch**: `main` (planning) → merge target `main` | **Date**: 2026-04-14
**Spec**: [/Users/robert/spec-kitty-dev/windows/spec-kitty/kitty-specs/windows-compatibility-hardening-01KP5R6K/spec.md](./spec.md)
**Mission ID**: `01KP5R6KRZDXV1BKM3Q1FZMY77` (`mid8`: `01KP5R6K`)
**Input**: Feature specification from `/Users/robert/spec-kitty-dev/windows/spec-kitty/kitty-specs/windows-compatibility-hardening-01KP5R6K/spec.md`

---

## Summary

Deliver an intentional, coherent, tested Windows story across Spec Kitty's historically fragile surfaces: (1) drop Credential Manager from the Windows auth path (closes #603), (2) unify Windows runtime state under a single `%LOCALAPPDATA%\spec-kitty\` root with a destination-wins migration, (3) harden the git pre-commit hook generator to pin the absolute interpreter at install time, (4) correct all user-facing path messaging on Windows, (5) revalidate worktree + symlink fallback end-to-end, (6) add a blocking `windows-latest` CI job that runs a curated Windows-critical suite selected by `pytest.mark.windows_ci`, and (7) run a second-pass repo-wide audit and commit its findings as an architecture report.

Scope boundaries are fixed by the spec's Non-Goals and the discovery answers: no full-matrix Windows CI, no opt-in Credential Manager, no long-term dual-root Windows state, no non-Windows platform behavior changes, no doc-only mitigations.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty requirement)
**Primary Dependencies**: `typer`, `rich`, `ruamel.yaml`, `platformdirs`, `httpx`, existing internal modules (`specify_cli.auth.secure_storage`, `specify_cli.tracker`, `specify_cli.sync.daemon`, `specify_cli.policy`, `kernel.paths`, `specify_cli.core.worktree`, `specify_cli.mission`). `keyring` becomes a conditional non-Windows-only dependency.
**Storage**: Filesystem only. Canonical Windows root: `%LOCALAPPDATA%\spec-kitty\` resolved via `platformdirs.user_data_dir("spec-kitty", appauthor=False)`. Non-Windows platforms retain their current storage conventions.
**Testing**: `pytest` with a new `windows_ci` marker; native `windows-latest` GitHub Actions runner for the curated suite; `mypy --strict`; integration-level tests for CLI surfaces.
**Target Platform**: Windows 10+ (x64) **natively, with no WSL requirement**, macOS 13+, Linux (GitHub-hosted + common distros). WSL-hosted installs are treated as Linux and use the Linux code paths unchanged; none of this mission's Windows-specific code runs inside WSL. A Windows user can install Spec Kitty via `pipx` against Python for Windows (or the Microsoft Store Python) and the full CLI — auth, tracker, sync, daemon, worktrees, hooks, migrations — must work end-to-end without WSL.
**Project Type**: Single Python package with CLI (`spec-kitty` / `specify_cli`) — structure decision below.
**Performance Goals**: Windows CLI cold-start regression ≤ 150 ms vs. pre-mission baseline (NFR-001); curated Windows CI job p95 wall-clock ≤ 15 min (NFR-002); migration of ≤100-file / ≤50-MB state tree ≤ 5 s (NFR-003).
**Constraints**: No Credential Manager / `keyring` import on Windows code path (C-001); single `%LOCALAPPDATA%\spec-kitty\` root on Windows (C-002); no POSIX-shell / PATH-python assumptions in hook generator (C-003); blocking Windows CI on PRs (C-004); WSL unchanged (C-005); one-direction migration (C-006); every behavioral fix has a native Windows test (C-007).
**Scale/Scope**: Affects ~5 packages (`auth/secure_storage`, `tracker`, `sync`, `kernel/paths`, `policy/hook_installer`), ~12 call-sites for path rendering (`migrate_cmd`, `agent/status`, and audit-surfaced additions), one new migration module, one new helper module for runtime paths, one new CI job + marker, one new architecture report, ~15–25 new tests.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter source: `/Users/robert/spec-kitty-dev/windows/spec-kitty/.kittify/charter/charter.md` (bootstrap load; no `governance.yaml`). Applicable policy from charter context:

| Gate | Requirement | Status |
|---|---|---|
| CG-01 | Toolchain conformance: `typer`, `rich`, `ruamel.yaml`, `pytest`, `mypy` strict. | PASS — this mission stays in-toolchain. |
| CG-02 | ≥90% test coverage for new code. | PASS (design-level) — each new module (`windows_paths.py` helper, `migration.py`, hook generator changes) ships with targeted tests; coverage enforced via existing pytest-cov configuration. |
| CG-03 | `mypy --strict` must pass (no type errors). | PASS (design-level) — all new modules authored with strict types; no `Any` introduction. |
| CG-04 | Integration tests for CLI commands. | PASS — new integration tests cover `spec-kitty migrate` (Windows paths), `spec-kitty agent status` (Windows messaging), hook install flow, auth init on Windows. |
| CG-05 | DIRECTIVE_010 Specification Fidelity: implemented behavior faithful to spec. | PASS — plan directly tracks spec FR/NFR/C ids; every design element points to a requirement. |
| CG-06 | DIRECTIVE_003 Decision Documentation: material decisions captured. | PASS — discovery answers + ADR under `architecture/adrs/` for the auth-split decision and the Windows storage unification decision. |
| CG-07 | `requirements-validation-workflow`: spec checklist already ran and passed in `/spec-kitty.specify`. | PASS — see `checklists/requirements.md`. |
| CG-08 | `adr-drafting-workflow`: major architectural decisions get an ADR. | PASS — ADRs planned (see Phase 1). |

No charter violations. No complexity tracking rows required.

## Project Structure

### Documentation (this feature)

```
/Users/robert/spec-kitty-dev/windows/spec-kitty/kitty-specs/windows-compatibility-hardening-01KP5R6K/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── cli-migrate.md
│   ├── cli-agent-status.md
│   ├── auth-secure-storage.md
│   ├── hook-installer.md
│   └── windows-ci-job.md
├── checklists/
│   └── requirements.md  # Already exists (/spec-kitty.specify output)
├── meta.json
├── spec.md
├── status.events.jsonl
└── tasks/               # Populated by /spec-kitty.tasks (NOT created here)
```

### Source Code (repository root)

```
/Users/robert/spec-kitty-dev/windows/spec-kitty/
├── src/
│   ├── kernel/
│   │   └── paths.py                             # MODIFIED — unified Windows root helper; no behavior change on POSIX
│   └── specify_cli/
│       ├── auth/
│       │   └── secure_storage/
│       │       ├── abstract.py                  # MODIFIED — from_environment() hard platform split
│       │       ├── keychain.py                  # UNMODIFIED on POSIX; NEVER imported on Windows
│       │       └── file_fallback.py             # MODIFIED — _DEFAULT_DIR resolved via platformdirs; honors unified Windows root
│       ├── cli/
│       │   └── commands/
│       │       ├── migrate_cmd.py               # MODIFIED — path messaging via render_runtime_path; triggers windows_migrate on Windows
│       │       └── agent/
│       │           └── status.py                # MODIFIED — path messaging via render_runtime_path
│       ├── core/
│       │   └── worktree.py                      # UNMODIFIED logic; NEW tests under windows_ci marker
│       ├── mission.py                           # UNMODIFIED logic; NEW tests for Windows active-mission handle fallback
│       ├── paths/                               # NEW package (or add windows_paths.py under specify_cli/)
│       │   ├── __init__.py
│       │   ├── windows_paths.py                 # NEW — Windows root resolution + render_runtime_path helper
│       │   └── windows_migrate.py               # NEW — one-time destination-wins migration with timestamped quarantine
│       ├── policy/
│       │   └── hook_installer.py                # MODIFIED — #!/bin/sh + absolute sys.executable pinning; cross-platform tested
│       ├── sync/
│       │   └── daemon.py                        # MODIFIED — state/PID location via unified Windows root
│       └── tracker/
│           └── credentials.py                   # MODIFIED — credentials path via unified Windows root
├── tests/
│   ├── auth/
│   │   └── secure_storage/
│   │       ├── test_from_environment_platform_split.py  # NEW
│   │       └── test_file_fallback_windows_root.py       # NEW (windows_ci)
│   ├── paths/
│   │   ├── test_windows_paths.py                # NEW (unit)
│   │   ├── test_windows_migrate.py              # NEW (unit; windows_ci)
│   │   └── test_render_runtime_path.py          # NEW (unit)
│   ├── policy/
│   │   └── test_hook_installer_execution.py     # NEW (windows_ci) — actually executes the installed hook
│   ├── sync/
│   │   ├── test_daemon_windows_paths.py         # NEW (windows_ci)
│   │   └── test_issue_586_windows_import.py     # UPGRADED — runs under windows_ci, no longer simulated
│   ├── tracker/
│   │   └── test_credentials_windows_paths.py    # NEW (windows_ci)
│   ├── core/
│   │   └── test_worktree_symlink_fallback.py    # NEW (windows_ci)
│   ├── cli/
│   │   ├── test_migrate_cmd_messaging.py        # NEW
│   │   └── test_agent_status_messaging.py       # NEW
│   ├── regressions/                             # NEW directory
│   │   ├── test_issue_101_utf8_startup.py       # NEW (windows_ci)
│   │   ├── test_issue_105_hook_python_lookup.py # NEW (windows_ci)
│   │   └── test_issue_71_dashboard_empty.py     # NEW (windows_ci if reachable on runner)
│   └── kernel/
│       └── test_paths_unified_windows_root.py   # NEW (windows_ci)
├── .github/
│   └── workflows/
│       └── ci-windows.yml                       # NEW — windows-latest blocking job, runs pytest -m windows_ci
├── pyproject.toml                               # MODIFIED — keyring marker (sys_platform != "win32"); register windows_ci marker
├── architecture/
│   ├── 2026-04-14-windows-compatibility-hardening.md  # NEW — audit report (DIRECTIVE_003)
│   └── adrs/
│       ├── 2026-04-14-1-windows-auth-platform-split.md  # NEW ADR
│       └── 2026-04-14-2-windows-runtime-state-unification.md  # NEW ADR
├── docs/
│   └── explanation/
│       └── windows-state.md                     # NEW — explains canonical Windows layout + migration
└── CLAUDE.md                                    # MODIFIED — Windows state-layout section
```

**Structure Decision**: Single-project Python layout, consistent with the existing `src/` + `tests/` tree. The Windows-specific helpers live in a new `src/specify_cli/paths/` subpackage (rather than being scattered across consumers) so that path rendering, Windows root resolution, and migration share one import surface. The new CI job is a separate workflow file so it can be required/optional-ified independently of the existing Linux workflows.

## Execution Lanes

Lanes drive both `/spec-kitty.tasks` work-package assignment and `implement` lane-based worktrees. Each lane is internally sequential; cross-lane dependencies are listed.

| Lane | Scope | Depends on | Spec IDs |
|---|---|---|---|
| **A. Storage foundation** | New `src/specify_cli/paths/` package: `windows_paths.py` (unified root helper + `render_runtime_path`), `windows_migrate.py` (destination-wins + timestamped quarantine, idempotent). Unit tests. | — | FR-005, FR-006, FR-007, FR-008, FR-012, NFR-003, C-002, C-006 |
| **B. Auth hard split** | `abstract.py` platform dispatch; `file_fallback.py` uses unified Windows root via lane A; `pyproject.toml` conditional `keyring` marker; integration tests. | A | FR-001, FR-002, FR-019, C-001 |
| **C. Path messaging sweep** | `render_runtime_path` rollout: `migrate_cmd.py`, `agent/status.py`, `docs/`, `CLAUDE.md`, audit-surfaced additions; tests assert no `~/.kittify` / `~/.spec-kitty` in Windows output. | A | FR-012, FR-013, FR-019, SC-002 |
| **D. Tracker/sync/daemon re-rooting** | `tracker/credentials.py`, `sync/daemon.py`, `kernel/paths.py` consume unified Windows root; tests under `windows_ci`. | A | FR-003, FR-004, FR-005, NFR-004 |
| **E. Hook installer hardening** | `policy/hook_installer.py` pins absolute `sys.executable`; executable hook tests (including path-with-spaces fixture); regression test for #105. | — | FR-009, FR-010, FR-011, C-003 |
| **F. Native Windows CI + marker** | Register `windows_ci` pytest marker in `pyproject.toml`; new `.github/workflows/ci-windows.yml` blocking job on `windows-latest` with `pipx install` topology; runs `pytest -m windows_ci`. Verifies CI *fails* against pre-fix state for at least one pre-existing regression (SC-003). | — | FR-015, FR-016, NFR-002, NFR-006, C-004 |
| **G. Encoding + worktree + mission revalidation** | Regression tests for #101 (UTF-8 startup), #71 (dashboard empty), #586 (fcntl import — upgrade from simulated to native); worktree symlink-vs-copy + active-mission handle tests on Windows. | F | FR-014, FR-016, FR-017, SC-004 |
| **H. Audit report + ADRs + follow-ups** | Run second-pass repo-wide audit (grep + targeted reads per FR-018); commit `architecture/2026-04-14-windows-compatibility-hardening.md`; commit two ADRs; file GitHub follow-up issues for any residuals. Close-out messaging for #603 and #260 posture. | A, B, C, D, E, F, G | FR-018, FR-019, SC-005, SC-006, SC-007 |

Lanes A, E, F can start in parallel. B, C, D depend on A. G depends on F. H is the finalizer.

## Complexity Tracking

No charter violations. No rows required.

---

*Phase 0 (research) and Phase 1 (design & contracts) artifacts are produced alongside this plan and live in the same `kitty-specs/windows-compatibility-hardening-01KP5R6K/` directory: `research.md`, `data-model.md`, `contracts/*.md`, `quickstart.md`.*

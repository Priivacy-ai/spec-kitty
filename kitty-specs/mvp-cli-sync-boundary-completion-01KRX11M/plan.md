# Implementation Plan: MVP CLI Sync Boundary Completion

**Mission**: `mvp-cli-sync-boundary-completion-01KRX11M`
**Mission ID**: `01KRX11MCY70M5NFBBHT4DQHJ2`
**Branch**: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS` (PR #1107)
**Date**: 2026-05-18
**Spec**: [spec.md](./spec.md)

## Summary

Finish PR #1107 by closing its self-documented "post-merge follow-up": the daemon-owner coherence check is reachable from `sync status --check` but is not wired into per-action preflights for SaaS-producing CLI commands. The technical approach is additive: introduce a reusable `SyncBoundaryPreflight` in `src/specify_cli/sync/` that composes existing helpers (`check_daemon_owner_match()`, `is_orphan()`, `list_orphan_records()`, `detect_legacy_rows_for_scope()`); call it from every SaaS-producing CLI entry point (`sync now`, `agent mission setup-plan`, mission lifecycle commands that emit SaaS events / body uploads); harden `sync status --check` so its non-zero conditions and printed fields exactly match the preflight's refusal set; and tighten row-level legacy→scoped queue migration so `body_upload_queue` rows are migrated regardless of whether the scoped DB already contains rows. No new external dependencies, no SQLite schema changes, no SaaS changes.

## Technical Context

**Language/Version**: Python 3.11+ (existing `spec-kitty` codebase)
**Primary Dependencies**: typer (CLI framework), rich (console output), ruamel.yaml (frontmatter), httpx (SaaS HTTP), pytest + pytest-cov, mypy --strict
**Storage**: SQLite via `OfflineQueue` (existing scoped queue DB + legacy `~/.spec-kitty/queue.db`); JSON owner record on disk via `src/specify_cli/sync/owner.py`
**Testing**: pytest with ≥ 90% line coverage for changed CLI surfaces (`tests/sync/`, `tests/runtime/`); existing fixtures for `OfflineQueue`, daemon owner records, and `SPEC_KITTY_ENABLE_SAAS_SYNC=1` gating
**Target Platform**: Linux, macOS, and Windows 10+ developer machines per project charter; CLI commands invoked from the spec-kitty checkout. Path handling uses `pathlib.Path` throughout; test fixtures isolate the operator's home directory by patching `pathlib.Path.home()` so the same fixtures run on Windows (`USERPROFILE`) and POSIX (`HOME`).
**Project Type**: single (CLI tool)
**Performance Goals**: `SyncBoundaryPreflight` adds ≤ 100 ms to each sync-producing command on a coherent host (no SaaS round-trip in the gate; reads owner record + queries scoped/legacy queue counts via existing helpers)
**Constraints**: `SPEC_KITTY_ENABLE_SAAS_SYNC=1` mandatory for hosted-auth and sync CLI commands (POSIX `export …=1`, Windows `cmd.exe` `set …=1`, PowerShell `$env:… = 1`); no force-push or history rewrite; no production/dev SaaS DB row mutation; no marking stuck events skipped; force-required review-rejection rollback contract from `spec-kitty-events#32` is settled and must not be re-debated; all new code and tests must work on Linux/macOS/Windows 10+ (C-008)
**Scale/Scope**: PR-completion mission covering 4 already-open sub-issues (#1090 row-level migration, #1088 daemon owner record, #1087 sync status/doctor truthfulness, #1089 setup-plan refuse-loudly); estimated ≤ 8 WPs; changes confined to `src/specify_cli/sync/`, `src/specify_cli/cli/commands/sync.py`, `src/specify_cli/cli/commands/doctor.py`, `src/specify_cli/cli/commands/agent/mission.py`, and corresponding test files

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Loaded via `spec-kitty charter context --action plan --json` (mode: bootstrap, first_load).

**Policy summary applied**:
- **typer / rich / ruamel.yaml / pytest / mypy** as the canonical CLI/test stack — satisfied (no new framework introduced).
- **pytest with ≥ 90 % test coverage for new code** — covered by NFR-001; explicit per-WP test plans added in Phase 1 contracts.
- **`mypy --strict` must pass (no type errors)** — covered by NFR-002; verification command `uv run mypy --strict src/specify_cli/sync/` listed under Definition of Done.
- **Integration tests for CLI commands** — `tests/sync/test_sync_status_boundary_check.py`, `tests/runtime/test_setup_plan_sync_evidence.py`, and new preflight integration tests cover the SaaS-producing entry points.

**Action doctrine applied (`plan`)**:
- **DIRECTIVE_003 (Decision Documentation)** — Captured in `research.md` (preflight composition, output format, refuse vs warn).
- **DIRECTIVE_010 (Specification Fidelity)** — Plan tracks each FR/NFR/C from `spec.md` to a concrete code surface and test; deviations would be flagged in `research.md` and reviewed before acceptance.
- **adr-drafting-workflow** — Not creating a standalone ADR; `architecture/` already contains the broader sync-boundary ADRs; this mission's design notes live in `plan.md` and `research.md`.
- **premortem-risk-identification** — Risk register in `research.md` enumerates failure modes (preflight false positive on stale owner record after legitimate version bump, migration retry duplication, body-upload row stranding).
- **requirements-validation-workflow** — Each FR has a corresponding acceptance scenario in `spec.md` and a verification command in `quickstart.md`.

**Gates**: All charter gates pass. No violations to justify.

## Project Structure

### Documentation (this mission)

```
kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/
├── plan.md              # This file
├── spec.md              # Approved specification (already committed)
├── research.md          # Phase 0 — design decisions and risk register
├── data-model.md        # Phase 1 — entities (DaemonOwnerRecord, scoped vs legacy queue, preflight)
├── quickstart.md        # Phase 1 — operator runbook for verification + evidence
├── contracts/           # Phase 1 — internal contracts for preflight + status output
│   ├── sync-boundary-preflight.md
│   └── sync-status-output.md
├── tasks.md             # Phase 2 — generated by /spec-kitty.tasks
├── tasks/                # Phase 2 — per-WP files generated by /spec-kitty.tasks
└── checklists/
    └── requirements.md  # Spec quality checklist (already green)
```

### Source Code (repository root)

```
spec-kitty/
├── src/specify_cli/
│   ├── sync/
│   │   ├── owner.py            # CHANGED — preflight composition + structured mismatch result
│   │   ├── queue.py            # CHANGED — row-level migration covers body_upload_queue with non-empty scoped DB
│   │   ├── daemon.py           # UNCHANGED — owner-record write + health endpoint already in place
│   │   └── preflight.py        # NEW — SyncBoundaryPreflight composition + render helpers
│   └── cli/commands/
│       ├── sync.py             # CHANGED — _require_daemon_owner_coherence becomes a thin call into preflight; sync status --check expanded
│       ├── doctor.py           # CHANGED — doctor orphan-daemons surfaces preflight categories consistently
│       └── agent/mission.py    # CHANGED — setup_plan + WPCreated emission paths call preflight before any enqueue
└── tests/
    ├── sync/
    │   ├── test_queue_row_level_migration.py        # EXTENDED — body_upload_queue + non-empty scoped DB cases
    │   ├── test_daemon_owner_record.py              # EXTENDED — preflight cross-checks; orphan w/o os.kill
    │   ├── test_sync_status_boundary_check.py       # EXTENDED — every documented split-brain shape
    │   └── test_sync_boundary_preflight.py          # NEW — unit + integration tests for SyncBoundaryPreflight
    └── runtime/
        └── test_setup_plan_sync_evidence.py         # EXTENDED — preflight integration + body upload routing
```

**Structure Decision**: Single-project layout already in place; this mission adds one new module (`src/specify_cli/sync/preflight.py`) and one new test file (`tests/sync/test_sync_boundary_preflight.py`). All other changes are surgical edits to existing files.

## Phase 0: Outline & Research

Output: [research.md](./research.md)

Topics resolved (no `[NEEDS CLARIFICATION]` markers remain in `spec.md`):

1. **Preflight composition** — Single helper `SyncBoundaryPreflight` vs distributed call sites. Decision: single helper that returns a structured `PreflightResult` with `ok: bool`, `mismatches: list[Mismatch]`, `orphan_records: list[DaemonOwnerRecord]`, `legacy_rows_for_scope: int`. Rationale: matches FR-001/FR-002 reuse demand; matches existing `MergeState`/`PreflightResult` pattern in `src/specify_cli/merge/` (precedent in this repo).
2. **Refusal output format** — Operator-actionable, ≤ 25 lines, names canonical field per Domain Language. Decision: Rich-rendered table with two columns (`Field`, `Foreground vs Daemon` or `Detected`) followed by a one-line remediation hint per category. No JSON in default output; `--json` flag forwards structured result for scripting.
3. **`sync status --check` field parity** — Decision: `_build_boundary_check_failures()` becomes the single source for both `--check` exit code and preflight refusal, called from both the preflight helper and the status command. Eliminates drift risk.
4. **Row-level migration for body uploads** — Decision: extend `_migrate_legacy_queue_to_scope()` to iterate both `sync_events`-class rows and `body_upload_queue` rows, using primary-key idempotence (`INSERT OR IGNORE` keyed by event_id / upload_id). Migration is safe to re-run.
5. **Setup-plan refusal placement** — Decision: hook is `setup_plan()` line 926 (hosted SaaS sync auth preflight). The new boundary preflight runs *after* the existing auth preflight, before any enqueue or body upload path.
6. **No SaaS dependency change** — Decision: events package version is treated as fixed for this mission. If Phase 1 (events) releases a patch, dependency bump is out of scope here and handled by Phase 3.

Risk register (premortem):

- **R1**: Preflight false-positive on a legitimate version bump between foreground and a daemon that has not been restarted. Mitigation: refusal output explicitly names `sync now --restart-daemon` (or `doctor restart-daemon`) in the remediation hint. Documented in `quickstart.md`.
- **R2**: Body-upload row migration duplication when re-running. Mitigation: use `INSERT OR IGNORE` on the primary key; covered by a dedicated test case in `test_queue_row_level_migration.py`.
- **R3**: Test suite flake due to filesystem-shared `~/.spec-kitty/queue.db`. Mitigation: all preflight tests use `tmp_path`-scoped homes via existing `monkeypatch.setenv("HOME", …)` patterns; do not touch real legacy queue.
- **R4**: Orphan owner-record cleanup expectations differ between `sync doctor` and `doctor orphan-daemons`. Mitigation: both surfaces consume the same `list_orphan_records()` result; tests assert identical detection in both code paths.

## Phase 1: Design & Contracts

Outputs:
- [data-model.md](./data-model.md) — entities, invariants, transitions
- [contracts/sync-boundary-preflight.md](./contracts/sync-boundary-preflight.md) — internal API contract for `SyncBoundaryPreflight`
- [contracts/sync-status-output.md](./contracts/sync-status-output.md) — `sync status --check` output format and exit-code contract
- [quickstart.md](./quickstart.md) — operator runbook for verification + sub-issue evidence capture

Highlights (full details in linked artifacts):

- **`SyncBoundaryPreflight`** (new, in `src/specify_cli/sync/preflight.py`):
  ```python
  @dataclass(frozen=True)
  class PreflightResult:
      ok: bool
      mismatches: list[OwnerMismatch]
      orphan_records: list[DaemonOwnerRecord]
      legacy_rows_for_scope: int
      auth_present: bool

      def render(self, console: Console) -> None: ...
      def to_dict(self) -> dict[str, Any]: ...

  def run_preflight(
      *,
      repo_root: Path,
      foreground: ForegroundIdentity,
      require_auth: bool = True,
  ) -> PreflightResult: ...
  ```
- **Refusal exit code**: `2` (matches existing `_require_daemon_owner_coherence` exit code in `src/specify_cli/cli/commands/sync.py:342`).
- **`sync status --check` non-zero condition set** = preflight refusal condition set ∪ {`legacy_rows_for_scope > 0`}. Both routes return the same exit code mapping.
- **Wiring points (sequential, FR→file→line)**:
  - FR-002 `sync now` → `src/specify_cli/cli/commands/sync.py:1196` — replace inline gate with `run_preflight(...)`.
  - FR-002 `agent mission setup-plan` → `src/specify_cli/cli/commands/agent/mission.py:881` (entry) and `:2354` (WPCreated SaaS emission area) — preflight runs after existing hosted-auth preflight and before first enqueue.
  - FR-005 `sync status` printed fields → `src/specify_cli/cli/commands/sync.py:1329` and identity-boundary section at `:1503` — extended to include legacy queue counts, body-upload counts, orphan count.
  - FR-006 / FR-007 row-level migration → `src/specify_cli/sync/queue.py:706` (`_migrate_legacy_queue_to_scope`) — iterate both row classes; idempotent via `INSERT OR IGNORE`.
  - FR-008 setup-plan refusal — `src/specify_cli/cli/commands/agent/mission.py:926` (existing) and `:942` — blocking diagnostic remains; preflight call adds owner-coherence check.

Re-checked Charter Check post-design: no new violations. No `[NEEDS CLARIFICATION]` markers in plan or contracts. Decision verifier (`spec-kitty agent decision verify --mission …`) will be re-run by `/spec-kitty.analyze`.

## Complexity Tracking

No Charter Check violations to justify. No table entries needed.

---

## Branch contract (restated)

- Current branch at plan start: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS`
- Planning / base branch for this mission: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS`
- Final merge target: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS` (PR #1107)
- `branch_matches_target`: true

The mission's commits stack onto PR #1107 directly; no new long-lived branch.

---

## Phase outputs

- Phase 0 (research): `research.md`
- Phase 1 (design + contracts + quickstart): `data-model.md`, `contracts/sync-boundary-preflight.md`, `contracts/sync-status-output.md`, `quickstart.md`

Next step: `/spec-kitty.tasks` (user-invoked).

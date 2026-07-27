---
work_package_id: WP05
title: auth doctor visibility, reset reporting & --force
dependencies:
- WP01
- WP03
requirement_refs:
- FR-004
- FR-005
- FR-009
- NFR-005
tracker_refs: []
planning_base_branch: fix/sync-daemon-orphan-cleanup
merge_target_branch: fix/sync-daemon-orphan-cleanup
branch_strategy: Planning artifacts for this mission were generated on fix/sync-daemon-orphan-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/sync-daemon-orphan-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
phase: Phase 3 - Operator surface
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "5567"
history:
- at: '2026-06-30T11:18:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/auth/test_auth_doctor_classification.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/auth.py
- src/specify_cli/cli/commands/_auth_doctor.py
- tests/auth/test_auth_doctor_classification.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – auth doctor visibility, reset reporting & --force

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile named in the frontmatter **before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is set, run `spec-kitty agent profile list` and pick the best match for `task_type: implement` on `authoritative_surface: src/specify_cli/cli/commands/`.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks (```python`, ```bash`).

---

## Objective

Surface the WP01/WP03 classification through `spec-kitty auth doctor`: a **read-only** classified scan (`--json` schema_version → 2), an exact `reset_result` (`swept`/`skipped`/`failed`) from `--reset`, and a new **`--force`** flag that gates `operator_required` kills behind explicit consent (D-02). Without `--reset` the command stays strictly read-only.

## Context & Constraints

Read before editing:
- [contracts/auth-doctor-json.md](../contracts/auth-doctor-json.md) — the **normative** `--json` and `--reset --json` shapes; [spec.md](../spec.md) FR-004, FR-005, FR-009; [research.md](../research.md) D-02.
- WP03 gives you the classified `enumerate_orphans` records + the force-aware sweep returning `ResetResult`. WP01 gives the record `to_dict()`.

Current code:
- `auth.py:100-140` — the `doctor` Typer command (flags `--json`, `--reset`, `--unstick-lock`, `--stuck-threshold`, `--server`) → `doctor_impl()`.
- `_auth_doctor.py:610-746` — human (rich) output (7 sections incl. "Orphans" table); `:748-803` — JSON shape (`schema_version` 1, `orphans[]` = `{port,pid,package_version,protocol_version}`); `:839-857` — current `--reset` reporting (counts only).

**Negative scope**: do NOT edit `sync/*` (WP01–WP04 own it). `auth doctor` must remain **read-only** without `--reset` (read-only invariant). Keep the existing 6 non-orphan sections intact.

## Branch Strategy

- **Strategy**: lane-per-WP (from `lanes.json`)
- **Planning base branch**: `fix/sync-daemon-orphan-cleanup`
- **Merge target branch**: `fix/sync-daemon-orphan-cleanup`

> Depends on WP01 + WP03 — branch from the dependency-aware base.

## Subtasks & Detailed Guidance

### Subtask T021 – `--force` flag

- **Purpose**: Explicit consent for ambiguous kills (D-02).
- **Files**: `src/specify_cli/cli/commands/auth.py`.
- **Steps**:
  1. Add `force: bool = typer.Option(False, "--force", help="With --reset, also clean operator_required daemons.")`.
  2. Thread it to the reset path → `sweep_orphans(..., include_operator_required=force)` (WP03's parameter).
- **Notes**: `--force` only matters with `--reset`; if passed alone, it is a no-op (document in help).

### Subtask T022 – Render classification (human + JSON v2) (FR-004)

- **Purpose**: Visibility, not just counts.
- **Files**: `src/specify_cli/cli/commands/_auth_doctor.py`.
- **Steps**:
  1. Bump `schema_version` 1 → 2. Replace each `orphans[]` entry with the full record `to_dict()` (superset of the old keys — additive, back-compat per the contract).
  2. Human "Orphans" table gains `class` and `reason` columns.
- **Notes**: `never_touch` listeners are excluded from `orphans[]` (operator-relevant only).

### Subtask T023 – `reset_result` reporting + remediation hint (FR-005, FR-009)

- **Purpose**: Exact swept/skipped/failed.
- **Files**: `src/specify_cli/cli/commands/_auth_doctor.py`.
- **Steps**:
  1. On `--reset --json`, add a top-level `reset_result` object with `swept[]`/`skipped[]`/`failed[]` exactly per `contracts/auth-doctor-json.md`.
  2. Human `--reset` prints compact lines mirroring the arrays; when `operator_required` daemons were skipped (no `--force`), print a one-step hint: `… run with --force to clean N operator_required daemon(s)` (FR-009).
- **Notes**: Drive entirely off WP03's `ResetResult` — do not recompute classification here.

### Subtask T024 – Read-only invariant + force/confirm gate (D-02)

- **Purpose**: Safety.
- **Files**: `src/specify_cli/cli/commands/auth.py`, `_auth_doctor.py`.
- **Steps**:
  1. Without `--reset`: zero mutation (scan + report only).
  2. With `--reset` (no `--force`): clean `safe_auto`, list `operator_required` in `skipped`. In an interactive TTY you may prompt `y/N` to escalate; in `--json`/non-interactive, escalation requires `--force` (never an implicit prompt).
- **Notes**: Keep the existing F-002 finding/remediation command wiring.

### Subtask T025 – Tests

- **Purpose**: Cover schema v2, reset_result, force gating, read-only.
- **Files**: `tests/auth/test_auth_doctor_classification.py` (new).
- **Steps**: Patch `enumerate_orphans`/`sweep_orphans` (WP03) with fakes; assert: `--json` emits `schema_version==2` and per-record `cleanup_class`; `--reset --json` emits `reset_result` with the three arrays; default `--reset` skips `operator_required` and prints the `--force` hint; `--force` includes them; plain `auth doctor` performs no sweep. Follow the offline pattern in `tests/auth/test_auth_doctor_offline.py`.
- **Notes**: No real daemons here — that is WP06. Keep these fast.

## Test Strategy

- `PWHEADLESS=1 .venv/bin/pytest tests/auth/test_auth_doctor_classification.py tests/auth/test_auth_doctor_offline.py -q`.
- `.venv/bin/ruff check src/specify_cli/cli/commands/auth.py src/specify_cli/cli/commands/_auth_doctor.py tests/auth/test_auth_doctor_classification.py` + `.venv/bin/mypy --strict src/specify_cli/cli/commands/auth.py src/specify_cli/cli/commands/_auth_doctor.py` — zero issues.

## Risks & Mitigations

- **Schema break**: the v2 bump must stay additive on `orphans[]`; document it in the contract and keep pre-existing keys.
- **Accidental mutation**: assert the no-`--reset` read-only path in tests.
- **`--force` in non-interactive**: never prompt in `--json`; require the explicit flag.

## Review Guidance

- Verify `auth doctor` (no `--reset`) mutates nothing.
- Verify `--json` is schema_version 2 with full records (FR-004) and `--reset --json` has exact `reset_result` arrays (FR-005).
- Verify `operator_required` requires `--force`/confirm and the one-step hint prints (FR-009, D-02).

## Activity Log

- 2026-06-30T11:18:31Z – system – Prompt created.
- 2026-06-30T12:30:51Z – claude:sonnet:python-pedro:implementer – shell_pid=59920 – Assigned agent via action command
- 2026-06-30T12:40:14Z – claude:sonnet:python-pedro:implementer – shell_pid=59920 – auth doctor schema_version=2 records + reset_result(swept/skipped/failed) + --force gate + read-only invariant; mypy+ruff clean on all 3 files; 12 tests pass
- 2026-06-30T12:41:09Z – claude:opus:reviewer-renata:reviewer – shell_pid=41358 – Started review via action command
- 2026-06-30T12:50:04Z – user – shell_pid=41358 – Moved to planned
- 2026-06-30T12:51:25Z – claude:sonnet:python-pedro:implementer – shell_pid=86455 – Started implementation via action command
- 2026-06-30T13:00:10Z – claude:sonnet:python-pedro:implementer – shell_pid=86455 – Cycle 1: repointed report/repair test mocks to enumerate_identity_records/reset_orphans; updated schema_version assertion 1→2; removed stale type:ignore[misc]; full tests/auth/ green (411 passed); ruff+mypy --strict clean on both files. No production code changed.
- 2026-06-30T13:00:58Z – claude:opus:reviewer-renata:reviewer – shell_pid=94108 – Started review via action command
- 2026-06-30T13:05:41Z – user – shell_pid=94108 – Moved to planned
- 2026-06-30T13:07:29Z – claude:sonnet:python-pedro:implementer – shell_pid=3588 – Started implementation via action command
- 2026-06-30T13:10:03Z – claude:sonnet:python-pedro:implementer – shell_pid=3588 – Cycle 2: restored the load-bearing # type: ignore[misc] on the frozen-immutability test WITH inline rationale; full-set mypy --strict (6 files) Success; tests/auth/ 411 passed; ruff clean
- 2026-06-30T13:10:15Z – claude:opus:reviewer-renata:reviewer – shell_pid=5567 – Started review via action command
- 2026-06-30T13:12:47Z – user – shell_pid=5567 – Cycle 2 re-review passed: load-bearing frozen-test suppression restored with inline rationale (charter-compliant); full-set mypy --strict Success (6 files); tests/auth/ 411 passed; ruff clean. WP05 complete.

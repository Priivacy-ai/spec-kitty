---
work_package_id: WP01
title: Sync boundary preflight module
dependencies: []
requirement_refs:
- FR-001
- FR-003
- NFR-001
- NFR-002
- NFR-003
- NFR-004
planning_base_branch: kitty/pr/mvp-sync-boundary-cli-01KRVCQS
merge_target_branch: kitty/pr/mvp-sync-boundary-cli-01KRVCQS
branch_strategy: Planning artifacts for this mission were generated on kitty/pr/mvp-sync-boundary-cli-01KRVCQS. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/pr/mvp-sync-boundary-cli-01KRVCQS unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mvp-cli-sync-boundary-completion-01KRX11M
base_commit: e739fb3e9165020f5c096c3967345d2ee6efc4a9
created_at: '2026-05-18T08:21:10.197619+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "codex:gpt-5:reviewer-rita:reviewer"
shell_pid: "35858"
history:
- at: '2026-05-18T08:00:00Z'
  actor: planner
  note: Initial generation
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/sync/preflight.py
execution_mode: code_change
mission_id: 01KRX11MCY70M5NFBBHT4DQHJ2
mission_slug: mvp-cli-sync-boundary-completion-01KRX11M
owned_files:
- src/specify_cli/sync/preflight.py
- tests/sync/test_sync_boundary_preflight.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, run the `ad-hoc-profile-load` skill to adopt the assigned profile (`implementer-ivan`, role: `implementer`). The profile sets the identity, governance scope, and boundaries for the work in this WP.

## Objective

Create a reusable `SyncBoundaryPreflight` helper in `src/specify_cli/sync/preflight.py` that gates SaaS-producing CLI commands. The helper composes existing daemon-owner and queue-detection helpers and returns a structured `PreflightResult` that downstream WPs (WP03, WP04) call into. This WP is foundational — get the API shape right, or downstream WPs churn.

Authoritative contract: [`contracts/sync-boundary-preflight.md`](../contracts/sync-boundary-preflight.md).

## Context

- The PR this mission completes (#1107) already lands `check_daemon_owner_match()`, `is_orphan()`, `list_orphan_records()`, `_legacy_queue_db_path()`, `_migrate_legacy_queue_to_scope()`, and `detect_legacy_rows_for_scope()`.
- The known gap from the PR's own body: the daemon-owner coherence check is reachable from `sync status --check` but is **not** called as a preflight by any sync-producing command. This WP supplies the reusable check. WP03 and WP04 wire it into the entry points.
- The repo has a precedent for this composition shape: `src/specify_cli/merge/preflight.py` defines `PreflightResult` consumed by `merge`. Mirror its dataclass layout for reviewer familiarity.

## Branch strategy

- Planning/base branch: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS` (PR #1107).
- Final merge target: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS`.
- Execution worktree: allocated per computed lane from `lanes.json` by `finalize-tasks`; do not create one manually.

## Subtasks

### T001 — Create `preflight.py` with dataclasses

**Purpose**: Land the public types that the rest of this WP and WP03/WP04 consume.

**Steps**:

1. Create file `src/specify_cli/sync/preflight.py`.
2. Define `MismatchField` as a `typing.Literal[...]` with exactly these six string values, in this order: `"daemon_package_version"`, `"daemon_executable_path"`, `"daemon_source_path"`, `"daemon_server_url"`, `"daemon_team_or_user"`, `"daemon_queue_db_path"`. These names match the Domain Language in `spec.md` and the assertions in tests; do not rename them.
3. Define `@dataclass(frozen=True) class ForegroundIdentity` with fields per `data-model.md`: `package_version: str`, `executable_path: Path`, `source_path: Path`, `server_url: str | None`, `team_or_user: str | None`, `queue_db_path: Path`, `pid: int`.
4. Define `@dataclass(frozen=True) class OwnerMismatch` with fields: `field: MismatchField`, `foreground_value: str`, `daemon_value: str`, `remediation_hint: str`.
5. Define `@dataclass(frozen=True) class PreflightResult` with fields: `ok: bool`, `mismatches: tuple[OwnerMismatch, ...]`, `orphan_records: tuple[DaemonOwnerRecord, ...]`, `legacy_event_rows: int`, `legacy_body_upload_rows: int`, `auth_present: bool`, `auth_required: bool`. Add `legacy_rows_for_scope` as a `@property`.

**Files**:
- `src/specify_cli/sync/preflight.py` (new, ~80 lines after T001)

**Validation**:
- `from specify_cli.sync.preflight import ForegroundIdentity, OwnerMismatch, PreflightResult, MismatchField` succeeds.
- `mypy --strict src/specify_cli/sync/preflight.py` passes.

### T002 — Implement `collect_foreground_identity(repo_root)`

**Purpose**: Produce a `ForegroundIdentity` for the current foreground process so the preflight has one side of the comparison.

**Steps**:

1. Determine `package_version` from `spec_kitty.__version__` (or the canonical version constant the existing CLI uses; grep for `__version__` in `src/specify_cli/` if uncertain).
2. Set `executable_path = Path(sys.executable).resolve()`.
3. Set `source_path` to the resolved parent of `specify_cli.__file__` (or its installed location). Always absolute.
4. Read hosted-auth config via the existing helper(s) used by `_build_boundary_check_failures()` — do not re-implement auth config reading. If unauthenticated, `server_url` and `team_or_user` are both `None`.
5. Set `queue_db_path = default_queue_db_path(...)` from `src/specify_cli/sync/queue.py`.
6. Set `pid = os.getpid()`.
7. Return a `ForegroundIdentity` instance.

**Files**:
- `src/specify_cli/sync/preflight.py` (extended; +~40 lines)

**Validation**:
- Calling `collect_foreground_identity(repo_root)` in tests returns concrete values when env is configured and `None`s only for `server_url`/`team_or_user` when unauthenticated.

### T003 — Implement `run_preflight(...)`

**Purpose**: Compose existing helpers into the structured `PreflightResult`.

**Steps**:

1. Signature: `def run_preflight(*, repo_root: Path, foreground: ForegroundIdentity | None = None, require_auth: bool = True) -> PreflightResult:`.
2. If `foreground is None`, call `collect_foreground_identity(repo_root)`.
3. Read the daemon owner record via `owner_record_path()` from `src/specify_cli/sync/owner.py`. If absent, the daemon-side comparison is skipped (no mismatches from it).
4. If a record exists, call `is_orphan(record)`. Orphan records do not generate field-level mismatches; they go into `orphan_records` (alongside the result from `list_orphan_records()` to surface every orphan currently present).
5. If a record exists and is *not* orphan, build per-field `OwnerMismatch` entries comparing foreground vs record on each of the six canonical fields. Use `<unset>` as the rendered value when one side is `None` and the other has a concrete value. Skip the comparison when both sides are `None` (no mismatch).
6. Collect `orphan_records = tuple(list_orphan_records(...))`.
7. Compute `legacy_event_rows` and `legacy_body_upload_rows` from the extended `detect_legacy_rows_for_scope(...)` (delivered in WP02; until that lands, use existing single-count return and set body-upload to 0 — coordinate with WP02 via the shared API).
8. Compute `auth_present = foreground.server_url is not None and foreground.team_or_user is not None`.
9. Compute `ok` per `data-model.md` invariant: `ok == (no mismatches and no orphans and legacy_rows_for_scope == 0 and (auth_present or not auth_required))`.
10. Return the result.

**Remediation hints** for each field (one-liners; keep concise):
- `daemon_package_version`: "Run `spec-kitty doctor restart-daemon` to restart the daemon at the foreground version."
- `daemon_executable_path` / `daemon_source_path`: "Run `spec-kitty doctor restart-daemon` to restart the daemon at the foreground source."
- `daemon_server_url`: "Reauthenticate (`spec-kitty auth login`) or restart the daemon against the matching server."
- `daemon_team_or_user`: "Switch to the foreground team/user (`spec-kitty auth switch ...`) or restart the daemon."
- `daemon_queue_db_path`: "Run `spec-kitty doctor restart-daemon`; the scoped queue path changed."

**Files**:
- `src/specify_cli/sync/preflight.py` (extended; +~80 lines)

**Validation**:
- `run_preflight(...)` is read-only; tests assert no SaaS round-trip is made and no filesystem writes occur.

### T004 — Implement `PreflightResult.render` and `.to_dict`

**Purpose**: Make the result human-actionable and machine-consumable.

**Steps**:

1. `render(self, console: Console) -> None`:
   - If `ok` is `True`, return (no-op).
   - Print the header line: `Sync boundary refused: <N> mismatched field(s); <M> orphan daemon record(s); <K> legacy rows in scope.`.
   - When mismatches non-empty, print a Rich table with columns `Field`, `Foreground`, `Daemon`. Rows in canonical field order.
   - Print a `Remediation:` block listing one bullet per mismatch's `remediation_hint` (de-duplicated), plus a bullet for orphan cleanup when `orphan_records` non-empty (`"Run `spec-kitty doctor orphan-daemons` to clean up <M> orphan daemon record(s)."`), plus a bullet for legacy-row flush when `legacy_rows_for_scope > 0` (`"Run `spec-kitty sync now` to flush <K> legacy rows for the current scope after the boundary is coherent."`).
   - When `auth_required` is `True` and `auth_present` is `False`, include a refusal bullet: `"Hosted SaaS sync is enabled but no authenticated identity is available. Run `spec-kitty auth login` first."`.
   - Total output ≤ 25 visible lines for ≤ 6 mismatches and ≤ 3 orphans (NFR-004).
2. `to_dict(self) -> dict[str, Any]`:
   - Emit all dataclass fields as plain Python types (paths stringified, `None`s preserved as JSON `null`, tuples → lists).
   - Include the computed `legacy_rows_for_scope` and `ok` keys at the top level.

**Files**:
- `src/specify_cli/sync/preflight.py` (extended; +~70 lines)

**Validation**:
- Test asserts a 6-mismatch + 3-orphan case renders in ≤ 25 visible lines.
- `to_dict` is JSON-serializable via `json.dumps(result.to_dict())`.

### T005 — Add `tests/sync/test_sync_boundary_preflight.py`

**Purpose**: Lock the contract behavior so WP03 and WP04 build on a stable foundation.

**Steps**:

1. Create `tests/sync/test_sync_boundary_preflight.py`.
2. Add the following test cases. Isolate the operator's home directory in a cross-platform way: prefer `monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)` (works identically on POSIX `HOME` and Windows `USERPROFILE`). If any helper still reads `os.environ["HOME"]` or `os.environ["USERPROFILE"]` directly, also `monkeypatch.setenv("HOME", str(tmp_path))` and `monkeypatch.setenv("USERPROFILE", str(tmp_path))`. Reuse fixtures from existing `tests/sync/test_daemon_owner_record.py` and `tests/sync/conftest.py` where helpful (per C-008 cross-platform constraint):
   - `test_run_preflight_ok_on_coherent_host`: no owner record, scoped queue empty, foreground auth present → `ok=True`.
   - `test_run_preflight_refuses_on_daemon_package_version_mismatch`: write owner record with different version → `ok=False` with one mismatch on `daemon_package_version`.
   - Same shape for the other five canonical fields (separate test functions; parametrize if cleaner).
   - `test_run_preflight_refuses_on_orphan_record`: owner-record fixture with a pid known dead — do NOT call `os.kill`; use the same pattern as `tests/sync/test_daemon_owner_record.py:336`.
   - `test_run_preflight_refuses_on_legacy_rows_for_scope`: stage legacy queue rows for the current scope → `ok=False` with `legacy_event_rows > 0` (or `legacy_body_upload_rows > 0` for the body-upload variant).
   - `test_run_preflight_refuses_when_auth_required_and_absent`: unauthenticated foreground with `require_auth=True` → `ok=False` with `auth_present=False`.
   - `test_preflight_result_render_within_25_lines`: build a 6-mismatch + 3-orphan result and assert `render` output is ≤ 25 lines.
   - `test_preflight_result_to_dict_is_json_serializable`: assert `json.dumps(result.to_dict())` round-trips and contains all documented top-level keys.
   - `test_run_preflight_performance_budget`: time `run_preflight(...)` on a coherent host fixture; assert ≤ 100 ms (NFR-003). Use `pytest.mark.performance` if your repo has such a marker; otherwise inline `time.perf_counter` and `assert`.

**Files**:
- `tests/sync/test_sync_boundary_preflight.py` (new, ~250 lines)

**Validation**:
- `uv run pytest tests/sync/test_sync_boundary_preflight.py -q` exits 0.
- Coverage on `src/specify_cli/sync/preflight.py` is ≥ 90 % (NFR-001).

## Definition of Done

- [ ] All five subtasks complete.
- [ ] `uv run pytest tests/sync/test_sync_boundary_preflight.py -q` exits 0.
- [ ] `uv run mypy --strict src/specify_cli/sync/` exits 0 with no new errors.
- [ ] `uv run pytest --cov=src/specify_cli/sync/preflight tests/sync/test_sync_boundary_preflight.py` shows ≥ 90 % coverage on the new module.
- [ ] No `[NEEDS CLARIFICATION]` markers added to the mission directory.
- [ ] Owned-files boundary respected: no edits outside `src/specify_cli/sync/preflight.py` or `tests/sync/test_sync_boundary_preflight.py`.

## Risks

- **R6 (from research.md)**: Canonical field names diverge from spec.md / tests. Mitigation: copy field names verbatim from `spec.md` Domain Language table; tests assert on the literal strings.
- **API drift before WP02 lands**: `run_preflight` consumes the extended `detect_legacy_rows_for_scope` from WP02. If WP02 has not landed yet, gate the body-upload subtotal behind a feature check and add a TODO that WP02 lights up — but the contract field MUST exist now so WP02 only flips a value, not adds a field.

## Reviewer guidance

- Verify the six canonical field names in `MismatchField` match `spec.md` Domain Language verbatim.
- Verify `render()` output line count for a 6-mismatch + 3-orphan case (NFR-004).
- Verify the result is hashable / frozen (immutability matters for snapshot tests in downstream WPs).
- Verify no SaaS HTTP calls in `run_preflight` (look for `httpx`/`requests` imports — should be absent).

## Implementation command

```bash
spec-kitty agent action implement WP01 --agent <name> --mission mvp-cli-sync-boundary-completion-01KRX11M
```

## Activity Log

- 2026-05-18T08:21:11Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=14919 – Assigned agent via action command
- 2026-05-18T08:30:46Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=14919 – Preflight module + tests landed; ready for review
- 2026-05-18T08:31:44Z – codex:gpt-5:reviewer-rita:reviewer – shell_pid=17495 – Started review via action command
- 2026-05-18T08:36:58Z – codex:gpt-5:reviewer-rita:reviewer – shell_pid=17495 – Moved to planned
- 2026-05-18T08:38:00Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=20827 – Started implementation via action command
- 2026-05-18T08:45:21Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=20827 – Cycle 2: fixed read-only contract violation (replaced compute_foreground_identity + default_queue_db_path calls with pure scope-resolution helpers + new _resolve_queue_db_path_readonly); added regression test test_run_preflight_is_read_only_on_default_path; documented working validation command (uv run --with pytest python -m pytest ...) — 23/23 pass, mypy strict green
- 2026-05-18T08:45:49Z – codex:gpt-5:reviewer-rita:reviewer – shell_pid=27050 – Started review via action command
- 2026-05-18T08:52:18Z – codex:gpt-5:reviewer-rita:reviewer – shell_pid=27050 – Moved to planned
- 2026-05-18T08:52:25Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=32222 – Started implementation via action command
- 2026-05-18T08:58:53Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=32222 – Cycle 3: preflight is now strictly local-only — no SaaS round-trip; regression test in place
- 2026-05-18T08:59:18Z – codex:gpt-5:reviewer-rita:reviewer – shell_pid=35858 – Started review via action command
- 2026-05-18T09:06:08Z – codex:gpt-5:reviewer-rita:reviewer – shell_pid=35858 – Cycle 3 review passed (codex reviewer verdict approve, recorded verbally — sandbox blocked artifact write). Preflight is strictly read-only and never calls SaaS endpoints. Regression test trip-wires rehydrate_membership_if_needed and resolve_private_team_id_for_ingress. 24/24 tests pass, mypy --strict clean, 92% coverage on preflight.py.

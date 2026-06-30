---
work_package_id: WP01
title: Sync daemon classification engine
dependencies: []
requirement_refs:
- C-004
- FR-001
- FR-002
- FR-003
- FR-008
- NFR-005
tracker_refs: []
planning_base_branch: fix/sync-daemon-orphan-cleanup
merge_target_branch: fix/sync-daemon-orphan-cleanup
branch_strategy: Planning artifacts for this mission were generated on fix/sync-daemon-orphan-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/sync-daemon-orphan-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Classification foundation
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "78305"
history:
- at: '2026-06-30T11:18:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/classification.py
create_intent:
- src/specify_cli/sync/classification.py
- tests/sync/test_daemon_classification_unit.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/sync/classification.py
- tests/sync/test_daemon_classification_unit.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Sync daemon classification engine

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile named in the frontmatter **before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is set, run `spec-kitty agent profile list` and pick the best match for `task_type: implement` on `authoritative_surface: src/specify_cli/sync/classification.py`.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks (```python`, ```bash`).

---

## Objective

Create a **new, pure** module `src/specify_cli/sync/classification.py` that turns one probed sync-port listener into a `DaemonIdentityRecord` carrying a `cleanup_class` (`safe_auto` / `operator_required` / `never_touch`). This is the single decision authority both cleanup surfaces (WP02 startup reaper, WP03 `auth doctor` port-scan) will consume.

Two hard rules define this WP:
1. **The daemon-root scope marker is the primary kill authority — not `owner.json`** (FR-003). `owner_present` is recorded for reporting only and must never change the verdict.
2. **Version/executable mismatch is stale-version *evidence*, never a skip gate** (FR-008). Once scope, responsiveness, spawn-shape, and not-singleton hold, a differing `package_version`/`executable_summary` yields `safe_auto`.

The classifier is **pure and dependency-light**: it decides over already-extracted primitive facts. It must NOT signal processes, read files, or open sockets, and it must NOT import the kill paths from `owner.py`/`orphan_sweep.py`. Probing/extraction happens in the callers (WP02/WP03); this module only decides.

## Context & Constraints

Read before editing:
- [data-model.md](../data-model.md) — the **DaemonIdentityRecord** field table, the **CleanupClass**/**SkipReason** enums, and the normative **classification decision table (rows 1–9)**. The decision table is the spec for `classify_candidate`.
- [contracts/cleanup-classification.md](../contracts/cleanup-classification.md) — the function contract. **Refinement (authoritative here)**: instead of receiving a raw `cmdline`, `classify_candidate` receives a `CandidateProbe` of **pre-extracted** primitives (`singleton_scope_id`, `spawn_shape_ok`, `executable_summary`, health fields, listener pid). The cmdline parsing that produces those primitives is done by the callers using the existing pure helpers in `owner.py` (`_cmdline_daemon_root_marker` `sync/owner.py:613-624`, `_cmdline_has_daemon_spawn_signature` `:627-641`, `_process_executable_scopes` `:573-610`). Keeping extraction in the callers makes this module import-free of `owner.py`.
- [plan.md](../plan.md) IC-01; [research.md](../research.md) DD-01, D-01 (wedged → `operator_required`).

Domain anchors (read, do not edit here): sync port range `DAEMON_PORT_START=9400` / `DAEMON_PORT_MAX_ATTEMPTS=50` (`sync/daemon.py:198-199`) → `[9400,9450)`; scope marker prefix `DAEMON_SCOPE_ARG_PREFIX="--spec-kitty-daemon-root="` (`daemon.py:815`); resolved scope `_daemon_scope_root()` (`daemon.py:818-830`); `DAEMON_PROTOCOL_VERSION=1` (`daemon.py:204`); health payload shape (`daemon.py:487-520`).

**Negative scope**: no process signalling, no socket/file I/O, no edits to `owner.py`/`orphan_sweep.py`/`daemon.py` (other WPs own those). Defensive read of `daemon_family` from health: treat a missing `daemon_family` key as `"sync"` when the port is in range and the spawn signature is present (WP04 adds the field; this module must not hard-depend on it).

## Branch Strategy

- **Strategy**: lane-per-WP (resolved from `lanes.json` at finalize)
- **Planning base branch**: `fix/sync-daemon-orphan-cleanup`
- **Merge target branch**: `fix/sync-daemon-orphan-cleanup`

> Populated by finalize-tasks. WP01 has no dependencies — it is a root lane.

## Subtasks & Detailed Guidance

### Subtask T001 – Record + enums

- **Purpose**: Define the data shapes that are the vocabulary for the whole mission.
- **Files**: `src/specify_cli/sync/classification.py` (new).
- **Steps**:
  1. `class CleanupClass(str, Enum)`: `SAFE_AUTO="safe_auto"`, `OPERATOR_REQUIRED="operator_required"`, `NEVER_TOUCH="never_touch"`.
  2. `class SkipReason(str, Enum)`: `is_recorded_singleton`, `pre_marker`, `cross_root`, `missing_pid`, `pid_port_mismatch`, `unresponsive`, `not_spec_kitty`, `out_of_range`, `dashboard_family`, `third_party`.
  3. `class IdentitySource(str, Enum)`: `health_self_report`, `cmdline_marker`, `owner_record`, `none`.
  4. `@dataclass(frozen=True) class DaemonIdentityRecord` with every field in the data-model table (`daemon_family`, `pid`, `port`, `protocol_version`, `package_version`, `singleton_scope_id`, `daemon_root`, `queue_db_path`, `auth_scope`, `server_url`, `owner_present`, `identity_source`, `executable_summary`, `spawn_shape_ok`, `self_report_matches_listener`, `is_recorded_singleton`, `cleanup_class`, `skip_reason`).
- **Notes**: All ASCII enum values (DIR-010). Provide a `to_dict()` for the JSON surface WP05 renders (snake_case keys exactly matching `contracts/auth-doctor-json.md`).

### Subtask T002 – Pure input adapters

- **Purpose**: Define the inputs the classifier decides over, so callers populate them.
- **Files**: `src/specify_cli/sync/classification.py`.
- **Steps**:
  1. `@dataclass(frozen=True) class HealthProbe`: `responded: bool`, `status: str|None`, `protocol_version: int|None`, `package_version: str|None`, `daemon_family: str|None`, `owner_pid: int|None`, `owner_port: int|None`, plus the redacted owner reporting fields (`queue_db_path`, `auth_scope`, `server_url`). `responded=False` models a wedged listener.
  2. `@dataclass(frozen=True) class SingletonRef`: `pid: int|None`, `port: int|None` (from the daemon state file).
  3. `@dataclass(frozen=True) class CandidateProbe`: `port:int`, `listener_pid:int|None`, `health:HealthProbe|None`, `singleton_scope_id:str|None`, `spawn_shape_ok:bool`, `executable_summary:str|None`, `owner_present:bool`.
  4. `@dataclass(frozen=True) class ForegroundScope`: `scope_id:str`, `executable_scope:str`, `singleton:SingletonRef`.
- **Notes**: These are plain value objects — no logic. Document that the caller derives `singleton_scope_id`/`spawn_shape_ok`/`executable_summary` from cmdline via `owner.py` helpers.

### Subtask T003 – `classify_candidate` rows 1–6

- **Purpose**: Implement the first six rows of the decision table.
- **Files**: `src/specify_cli/sync/classification.py`.
- **Steps**: Implement `classify_candidate(probe: CandidateProbe, foreground: ForegroundScope) -> DaemonIdentityRecord` evaluating top-to-bottom, first match wins:
  1. `port ∉ [9400,9450)` → `never_touch` / `out_of_range`.
  2. not identifiable as SK sync (no `spawn_shape_ok` **and** no SK self-report) → `never_touch` / `not_spec_kitty` (or `third_party` if a foreign health response was seen).
  3. `is_recorded_singleton` (probe.listener_pid/port == foreground.singleton) → excluded from cleanup, `skip_reason=is_recorded_singleton` (record it; callers never act on it).
  4. `listener_pid is None` → `operator_required` / `missing_pid`.
  5. `singleton_scope_id is None` → `operator_required` / `pre_marker`.
  6. `singleton_scope_id != foreground.scope_id` → `operator_required` / `cross_root`.
- **Notes**: Keep cyclomatic complexity ≤15 — use a small ordered list of `(predicate, class, reason)` rules or early returns; do not nest deeply (Sonar S3776).

### Subtask T004 – `classify_candidate` rows 7–9 (D-01, FR-008)

- **Purpose**: The safety-critical tail.
- **Files**: `src/specify_cli/sync/classification.py`.
- **Steps**:
  7. **D-01**: no live health self-report (`probe.health is None or not probe.health.responded`) → `operator_required` / `unresponsive`. A wedged listener is never `safe_auto`.
  8. health pid/port ≠ listener (`health.owner_pid != listener_pid or health.owner_port != port`) → `operator_required` / `pid_port_mismatch`.
  9. else → `safe_auto` (scope proven, responsive, spawn-shape ok, not singleton). **FR-008**: do NOT add a version/executable equality check — a differing `package_version`/`executable_summary` is allowed and yields `safe_auto`. Set `identity_source=health_self_report`.
- **Notes**: `skip_reason is None` ⇔ `cleanup_class == safe_auto`. `owner_present` must not appear in any predicate (FR-003).

### Subtask T005 – Unit tests for every row

- **Purpose**: Prove the decision table at the lowest level (Sonar new-code coverage).
- **Files**: `tests/sync/test_daemon_classification_unit.py` (new).
- **Steps**: One focused test per decision row (1–9) plus: (a) FR-008 — same scope, responsive, **older** `package_version` → `safe_auto`; (b) D-01 — in-scope but `health=None` → `operator_required/unresponsive`; (c) FR-003 — `owner_present=True` with no scope marker still → `operator_required/pre_marker` (owner record does not rescue it). Use realistic values (ports 9400/9401/9449, a real-looking resolved scope path). Mark `@pytest.mark.unit`.
- **Notes**: No subprocesses, no sockets — pure inputs.

## Test Strategy

- `PWHEADLESS=1 .venv/bin/pytest tests/sync/test_daemon_classification_unit.py -q` (fast, pure).
- `.venv/bin/ruff check src/specify_cli/sync/classification.py tests/sync/test_daemon_classification_unit.py` — zero issues.
- `.venv/bin/mypy --strict src/specify_cli/sync/classification.py` — zero issues. The venv is already warm; prefer the direct binaries.

## Risks & Mitigations

- **Scope creep into probing**: keep this module pure. If you find yourself importing `psutil` or sockets here, stop — that belongs in WP02/WP03 callers.
- **Complexity ceiling**: the 9-row table can balloon a single function past complexity 15. Express it as an ordered rule list or split rows 1–6 / 7–9 into helpers, each tested.
- **Contract drift**: the `to_dict()` keys are consumed verbatim by WP05's JSON. Match `contracts/auth-doctor-json.md` exactly.

## Review Guidance

- Verify `owner_present` appears in **no** predicate (FR-003).
- Verify there is **no** version/executable equality gate before `safe_auto` (FR-008) — confirm the "older version, same scope → safe_auto" test exists and passes.
- Verify wedged (`health=None`) → `operator_required/unresponsive` (D-01).
- Verify the module imports nothing from `owner.py`/`orphan_sweep.py`/`daemon.py` kill paths (pure).
- Verify `skip_reason is None ⇔ cleanup_class == safe_auto`.

## Activity Log

- 2026-06-30T11:18:31Z – system – Prompt created.
- 2026-06-30T11:49:14Z – claude:sonnet:python-pedro:implementer – shell_pid=7219 – Assigned agent via action command
- 2026-06-30T11:57:09Z – claude:sonnet:python-pedro:implementer – shell_pid=7219 – Classification engine implemented; unit tests cover all 9 rows + FR-008/D-01/FR-003; ruff+mypy clean
- 2026-06-30T11:58:02Z – claude:opus:reviewer-renata:reviewer – shell_pid=78305 – Started review via action command
- 2026-06-30T12:03:05Z – user – shell_pid=78305 – Review passed: pure classifier, decision table rows 1-9 correct, FR-003/FR-008/D-01 proven by tests, ruff+mypy clean, no out-of-scope edits. Issue-matrix verdicts filled per spec.md (#2261/#1071 in-mission, #1868 deferred-with-followup C-007)

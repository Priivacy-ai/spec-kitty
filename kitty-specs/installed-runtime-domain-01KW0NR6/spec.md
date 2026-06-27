# Mission Specification: Centralize installed CLI runtime + remediation planning

**Mission Branch**: `feat/installed-runtime-domain`
**Mission ID**: `01KW0NR6E9XCH0QAREQWQ5ZDPB`
**Created**: 2026-06-26
**Status**: Draft
**Source**: GitHub issue #1358

## Context

Spec-kitty has no single domain model for the installed CLI runtime. Receipt-parsing
logic is copy-pasted across three modules and remediation-command construction is
scattered across five independent sites. This mission introduces a unified
`InstalledCliRuntime` domain type, a `RemediationCommand` type whose structured
`argv` plus `render()` satisfies both subprocess and copy-paste consumers, a
`UvReceiptReader` adapter collapsing the three parsers, and a `plan_remediation()`
pure function routing all five construction sites. It also adds durable
upgrade-attempt event recording for retry/backoff analysis (B2 scope).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Single runtime-detection call (Priority: P1)

A developer extending or debugging spec-kitty today must call `detect_install_method()`
(which discards receipt/tool-dir/bin-dir context it already probed), then independently
re-parse the uv receipt in each of `review`, `upgrade_ux`, and `install_method.py` to
recover the fields the first call threw away. After this mission, a single call to
`detect_runtime()` returns the complete installed-CLI snapshot — method, executable,
receipt path, tool dir, bin dir, python override, injected requirements, derived
provenance, platform, and safe-for-auto-upgrade flag — with nothing discarded.

**Why this priority**: This is the foundational type that all other work in this
mission builds on. Subsystems cannot consolidate remediation logic until there is a
single authoritative runtime record to draw from.

**Independent Test**: Fully testable by calling `detect_runtime()` in a simulated uv-tool
environment and asserting all fields (receipt_path, tool_dir, bin_dir, python,
requirements, safe_for_auto_upgrade) are populated from a single probe without
any module reading the receipt a second time.

**Acceptance Scenarios**:

1. **Given** spec-kitty is installed via uv-tool with a non-default tool dir and a pinned
   Python override in the receipt, **When** `detect_runtime()` is called, **Then** the
   returned record carries `tool_dir` (custom), `is_default_tool_dir=False`,
   `python` (the overridden interpreter), and `requirements` (the receipt's requirement
   list) — all populated from the same receipt read.
2. **Given** spec-kitty is installed via pipx, **When** `detect_runtime()` is called,
   **Then** `install_method` is PIPX, `receipt_path` is None, `is_default_tool_dir` is
   None, and `safe_for_auto_upgrade` is True.
3. **Given** a malformed or missing receipt file, **When** `detect_runtime()` is called,
   **Then** it returns a valid record with `receipt_path=None` and `requirements=()`
   rather than raising.

---

### User Story 2 — Consistent remediation across all upgrade surfaces (Priority: P1)

A spec-kitty user who runs `spec-kitty review` and sees an upgrade hint, then runs
`spec-kitty upgrade`, should see the same upgrade command in both places for their
install method. Today, review reconstructs the command by shlex-quoting argv built
from the receipt; upgrade_ux builds argv from a method-keyed dict; upgrade_hint uses
a static table; and version_checker/schema_version contain hardcoded pipx strings.
After this mission, all five surfaces call `plan_remediation()` and `RemediationCommand.render()`
so the output is structurally identical regardless of which surface the user encounters.

**Why this priority**: Divergence between surfaces confuses users about the right
upgrade command for their environment. The `review` surface carries the richest receipt
logic but that logic is not available to `upgrade_ux` or the static hint table.

**Independent Test**: Testable by asserting that `plan_remediation(runtime, UPGRADE, None).render("posix")`
produces the same string as the equivalent call site in each of the five legacy sites,
for each install method, with no surface re-implementing receipt-reading or env-prefix logic.

**Acceptance Scenarios**:

1. **Given** a uv-tool install with a custom tool dir and python-version override,
   **When** `plan_remediation()` is called with intent UPGRADE, **Then** the returned
   `RemediationCommand.render("posix")` includes the `UV_TOOL_DIR` env prefix and
   the `--python` flag reconstructed from the receipt — matching what the legacy
   `review` surface produced — and `RemediationCommand.argv` carries the same args
   as a usable subprocess tuple.
2. **Given** a pipx install, **When** `plan_remediation()` is called with intent UPGRADE,
   **Then** `render()` returns `"pipx upgrade spec-kitty-cli"` (CHK028-validated) and
   `argv` is `("pipx", "upgrade", "spec-kitty-cli")`.
3. **Given** any install method, **When** `UpgradeHint` is constructed via the post-migration
   `build_upgrade_hint()`, **Then** `UpgradeHint.command` equals `RemediationCommand.render(platform)`
   for the same install method — the `Plan.upgrade_hint` JSON contract is identical
   to its pre-migration value.
4. **Given** a Windows platform and a uv-tool install, **When** `RemediationCommand.render("windows")`
   is called, **Then** the output uses PowerShell-safe quoting (matching the pre-migration
   behavior from `review/__init__.py`'s PowerShell branch).

---

### User Story 3 — Durable upgrade-attempt history for retry/backoff analysis (Priority: P2)

A spec-kitty operator or developer investigating why the auto-upgrade loop re-ran after
a previous success wants to consult an upgrade-attempt history without digging through
logs. After this mission, each upgrade attempt (initiated by `_default_upgrade_runner`)
appends a structured record carrying timestamp, install method, intent, outcome, and
exit code to a dedicated history store. The store supports idempotency queries ("was
this exact upgrade already completed successfully?") and retry-eligibility checks ("how
many consecutive failures in the last N minutes?").

**Why this priority**: Without attempt history, the `NagCache` only records preference
state (snooze, always_upgrade, never_ask) and the current remote version. There is no
way to distinguish a first failure from a repeated transient error, or to detect that
an identical upgrade already succeeded earlier in the same session.

**Independent Test**: Testable by injecting a fake upgrade runner, triggering two
successive upgrade calls with the same install method and target version (first call
succeeds, second call is a no-op idempotency hit), and asserting the history store
contains exactly one success record and one idempotency record — plus a
`UvToolInstallationVerified` event with `confidence=HIGH` after the first call.

**Acceptance Scenarios**:

1. **Given** a uv-tool install and a successful auto-upgrade, **When** the upgrade
   runner completes with exit code 0, **Then** a `UvToolInstallationVerified` event
   is emitted carrying the receipt path, `entrypoint_match=True`, and `confidence=HIGH`,
   AND an attempt record (outcome=success, exit_code=0) is appended to the history store.
2. **Given** two consecutive upgrade attempts with identical install_method and
   target_version, **When** the history store is queried, **Then** `is_idempotent(attempt)`
   returns True for the second attempt if the first was a success.
3. **Given** three consecutive failed attempts in a 5-minute window, **When** the
   history store is queried for retry eligibility, **Then** the store reports
   `consecutive_failures=3` and the caller can apply a backoff policy without
   re-reading the NagCache.
4. **Given** a non-uv-tool install (e.g. pipx), **When** a successful upgrade completes,
   **Then** an attempt record is appended to the history store but no
   `UvToolInstallationVerified` event is emitted (the event is uv-tool specific).

---

### User Story 4 — Step-by-step migration with no regressions (Priority: P2)

A developer landing the migration in review wants to merge each step independently —
types only, then adapter, then planner, then each deletion — with the full test suite
green at every merge point. No big-bang rewrite. After this mission, the 7-step
strangler plan (see FR-016 through FR-022) defines discrete, independently shippable
units where each step builds on the last and existing call sites are never broken
mid-migration.

**Why this priority**: The duplication spans files with high test coverage and active
call sites. A single-step rewrite carries substantial regression risk and makes reviews
harder. The strangler plan ensures reviewers see exactly the scope of each deletion.

**Independent Test**: Testable by creating a branch per step, running the full test
suite (including the architectural terminology guard), and verifying each branch is
independently green before the next step begins.

**Acceptance Scenarios**:

1. **Given** step 1 is merged (types introduced, no behavior change), **When** the
   existing test suite runs, **Then** all tests pass including tests for
   `review/__init__.py`, `upgrade_ux.py`, and `upgrade_hint.py` call paths.
2. **Given** step 2 is merged (receipt adapter and `detect_runtime()` live, shim in
   place), **When** any of the 7 existing `detect_install_method()` call sites runs,
   **Then** it returns the same `InstallMethod` value as before.
3. **Given** step 4 is merged (review migration), **When** `review` is called on a
   uv-tool install, **Then** the reinstall command emitted matches the pre-migration
   output byte-for-byte.

---

### Edge Cases

- What happens when the uv receipt exists but lists no requirements matching `spec-kitty-cli`? `UvReceiptReader` returns `requirements=()` and `receipt_path=<path>` (receipt found but no spec-kitty entry).
- What happens when `UV_TOOL_DIR` is set to a non-default path but the receipt is missing? `detect_runtime()` records `tool_dir` from the env var and `receipt_path=None` — no attempt to read a non-existent receipt.
- What happens when `RemediationCommand.render()` generates a string that fails CHK028 validation (e.g., a path containing shell metacharacters)? Construction raises `ValueError` at render time with a CHK028 violation message; the caller falls back to a `MANUAL_GUIDANCE` command with a safe note.
- What happens when the history store file is corrupted or unreadable? Reads return an empty history (fail-open for queries); writes are best-effort with silent swallow (fail-safe for appends), matching the NagCache pattern.
- What happens when `plan_remediation()` is called with `intent=REINSTALL_WITH_TEST` for a non-uv-tool install? It returns a `RemediationCommand` with `intent=REINSTALL_WITH_TEST`, `argv=None`, and `note` describing the appropriate manual steps for that install method.
- What happens on Windows when the history store path uses a separator incompatible with the POSIX path construction? All history store paths are constructed via `pathlib.Path`, not string concatenation.

---

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | `InstalledCliRuntime` domain type | As a developer, I want a single frozen dataclass representing the full installed-CLI snapshot (install_method, executable, receipt_path, tool_dir, bin_dir, is_default_tool_dir, is_default_bin_dir, python, requirements, package_source, platform, safe_for_auto_upgrade) so no caller reconstructs these fields independently. | High | Open |
| FR-002 | `detect_runtime()` public function | As a developer, I want `detect_runtime()` to return an `InstalledCliRuntime` by enriching the existing detection chain, so all receipt/dir/python fields are populated in one call. | High | Open |
| FR-003 | `detect_install_method()` backward-compatible shim | As a developer, I want `detect_install_method()` to remain callable and return `runtime.install_method` so all 7 existing call sites stay green without changes until step 7. | High | Open |
| FR-004 | `RemediationCommand` domain type | As a developer, I want a frozen dataclass `RemediationCommand` with intent (UPGRADE / REINSTALL_WITH_TEST / MANUAL_GUIDANCE), argv (tuple or None), env (Mapping), and note (str or None) so subprocess and display consumers share one type. | High | Open |
| FR-005 | `RemediationCommand.render(platform)` | As a developer, I want `render(platform)` to emit an env-prefixed, CHK028-validated, platform-appropriate quoted string (shlex on POSIX, PowerShell-safe on Windows) so the copy-paste string and the subprocess argv are derived from the same source. | High | Open |
| FR-006 | `UpgradeHint` thin façade | As a developer, I want `UpgradeHint.command` to delegate to `RemediationCommand.render()` so the `Plan.upgrade_hint` JSON contract and all `UpgradeHint` consumers receive the same rendered string as before migration. | High | Open |
| FR-007 | `UvReceiptReader` adapter | As a developer, I want a single `UvReceiptReader` in `compat/_adapters/uv_receipt.py` that reads and parses `uv-receipt.toml`, returning all fields needed by `InstalledCliRuntime` (receipt_path, tool_dir, bin_dir, python, requirements), so the three independent receipt-reading implementations are eliminated. | High | Open |
| FR-008 | Receipt adapter is sole receipt-reading path | As a developer, I want the three legacy local `_active_uv_tool_receipt` / `_active_uv_tool_dir` / `_same_path` / `_uv_tool_python_args` implementations deleted after migration, so no duplicate receipt logic remains. | High | Open |
| FR-009 | `plan_remediation()` pure function | As a developer, I want `plan_remediation(runtime, intent, target_version) -> RemediationCommand` as a pure function (no I/O, deterministic) so all five construction sites route through one place. | High | Open |
| FR-010 | All five remediation sites routed through planner | As a user, I want `review/__init__.py`, `upgrade_ux.py`, `upgrade_hint.py`, `version_checker.py`, and `schema_version.py` to all call `plan_remediation()` so the output is structurally identical for the same install method and intent. | High | Open |
| FR-011 | `build_upgrade_hint()` reimplemented on planner | As a developer, I want `build_upgrade_hint(install_method, *, package, target_version)` to be reimplemented on top of `plan_remediation()` while preserving its public signature and `UpgradeHint` output type. | High | Open |
| FR-012 | `UvToolInstallationVerified` event | As an operator, I want a `UvToolInstallationVerified` event emitted after each uv-tool upgrade attempt, carrying receipt_path, entrypoint_match, package_binding, and confidence (LOW / MEDIUM / HIGH), so post-upgrade verification is auditable. | Medium | Open |
| FR-013 | Upgrade-attempt history store | As an operator, I want a dedicated history store (separate from NagCache) that records each upgrade attempt with timestamp, install_method, intent, outcome, exit_code, and attempt_id, so idempotency and retry-eligibility queries are possible without parsing logs. | Medium | Open |
| FR-014 | Upgrade runner emits event and history record | As an operator, I want `_default_upgrade_runner` (in `upgrade_ux.py`) to emit a `UvToolInstallationVerified` event (for uv-tool installs) and append an `UpgradeAttemptRecord` to the history store on every completion (success or failure). | Medium | Open |
| FR-015 | History store query interface | As an operator, I want the history store to expose queries for idempotency (was this exact upgrade already completed?), consecutive-failure count, and timestamp of last success, without reading the NagCache. | Medium | Open |
| FR-016 | Migration step 1 — introduce types | As a developer, I want `InstalledCliRuntime`, `RemediationCommand`, and `UvToolInstallationVerified` introduced with no behavior change so the new types can be reviewed in isolation. | High | Open |
| FR-017 | Migration step 2 — receipt adapter and `detect_runtime()` | As a developer, I want `UvReceiptReader` and `detect_runtime()` introduced and the `detect_install_method()` shim in place so all 7 existing call sites remain green. | High | Open |
| FR-018 | Migration step 3 — route planner, preserve hint contract | As a developer, I want `plan_remediation()` introduced and `build_upgrade_hint()` reimplemented on it while `UpgradeHint`, `_HINT_TABLE`, CHK028, and `Plan.upgrade_hint` JSON contract remain unchanged. | High | Open |
| FR-019 | Migration step 4 — migrate `review/__init__.py` | As a developer, I want the ~120 LOC of duplicate helpers (`_active_uv_tool_receipt`, `_active_uv_tool_dir`, `_same_path`, `_uv_tool_python_args`, `_uv_tool_reinstall_command`, `_uv_tool_env_prefix`, `_uv_tool_env_values`, `_same_path`, `_powershell_quote`) in `review/__init__.py` replaced by calls to `UvReceiptReader` and `plan_remediation()`. | High | Open |
| FR-020 | Migration step 5 — migrate `upgrade_ux.py` | As a developer, I want the duplicate helpers in `upgrade_ux.py` deleted and `_default_upgrade_runner` updated to consume `RemediationCommand.argv` and `.env` directly, with event emission and history record appended. | High | Open |
| FR-021 | Migration step 6 — fold hardcoded strings (optional) | As a developer, I want the hardcoded `"pipx upgrade spec-kitty-cli"` strings in `version_checker.py` (line 218) and `schema_version.py` (line 182) routed through `plan_remediation()` so no install-method strings are hardcoded outside the planner. | Low | Open |
| FR-022 | Migration step 7 — retire `detect_install_method()` shim | As a developer, I want the `detect_install_method()` shim retired and all remaining call sites updated to `detect_runtime().install_method` so the legacy bare-enum API is removed. | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | `detect_runtime()` never-raise contract | `detect_runtime()` must never raise; every probe wrapped in `try/except … # noqa: BLE001` with silent fall-through to defaults, identical to the existing CHK032 guarantee on `detect_install_method()`. | Reliability | High | Open |
| NFR-002 | CHK028 validation on render | `RemediationCommand.render()` must raise `ValueError` at render time if the composed string does not match `^[A-Za-z0-9 .\-+_/=:]{1,128}$` (CHK028), preventing shell metacharacters from reaching display surfaces. | Security | High | Open |
| NFR-003 | `UvReceiptReader` fail-soft | `UvReceiptReader` must return `None` (or empty fields) rather than raising on any filesystem error, TOML parse error, or schema mismatch. | Reliability | High | Open |
| NFR-004 | `plan_remediation()` is pure | `plan_remediation()` must be a pure function — no I/O, no side effects, deterministic output for the same inputs — so it is fully unit-testable without filesystem or subprocess stubs. | Testability | High | Open |
| NFR-005 | History store idempotency | Two history records with identical `attempt_id` must be deduplicated on read; the store must not grow unboundedly from retried attempts. | Reliability | Medium | Open |
| NFR-006 | History store concurrent-write safety | The history store must tolerate concurrent invocations without corruption; atomic-replace or append-only write semantics required. | Reliability | Medium | Open |
| NFR-007 | No PII in events or history records | `UvToolInstallationVerified` events and `UpgradeAttemptRecord` entries must contain no user paths, project slugs, hostnames, or machine IDs — extending CHK007/CHK048/CHK050. | Security | High | Open |
| NFR-008 | Each migration step independently test-gated | Each of FR-016 through FR-022 must pass the full test suite (including `tests/architectural/test_no_legacy_terminology.py`) before the next step begins; no step introduces a regression. | Quality | High | Open |
| NFR-009 | History store separate from NagCache | The history store must use a separate file from `upgrade-nag.json`; NagCache schema must not be extended for attempt history. | Architecture | High | Open |
| NFR-010 | Zero ruff/mypy issues in new code | All new modules must pass `ruff check` and `mypy` with zero issues and zero warnings; no blanket `# noqa` or `# type: ignore` suppressions permitted (per project code-style policy). | Quality | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | `detect_install_method()` shim preserved through step 6 | `detect_install_method()` must remain callable and return the correct `InstallMethod` enum from step 1 through step 6 (FR-016 through FR-021); it is removed only in step 7 (FR-022). No breaking API change before step 7. | Compatibility | High | Open |
| C-002 | `UpgradeHint` / `_HINT_TABLE` / CHK028 / `Plan.upgrade_hint` contract unchanged | The `UpgradeHint` type, `_HINT_TABLE` dict, CHK028 validation regex, and the `Plan.upgrade_hint` rendered-JSON contract must be functionally identical throughout all migration steps; no consumer of `build_upgrade_hint()` or `Plan.upgrade_hint` sees a behavior change. | Compatibility | High | Open |
| C-003 | No structural `Protocol` interfaces without a second implementation | Structural `Protocol` classes must not be introduced unless a second concrete implementation exists at time of introduction, consistent with the existing `compat/provider.py` convention (`LatestVersionProvider` has `PyPIProvider`, `NoNetworkProvider`, `FakeLatestVersionProvider`). | Architecture | High | Open |
| C-004 | New modules use frozen dataclasses + `from __future__ import annotations` + deferred imports | All new modules must follow the conventions established in the `compat/` layer: frozen dataclasses, `from __future__ import annotations` at the top, deferred imports inside functions where needed to avoid circular-import issues. | Architecture | High | Open |
| C-005 | PowerShell rendering branch preserved | `RemediationCommand.render("windows")` must emit PowerShell-safe quoting for all commands that currently use `_powershell_quote()` in `review/__init__.py`; the Windows rendering path must not regress. | Compatibility | High | Open |
| C-006 | `safe_for_auto_upgrade` encodes the existing 5-method whitelist | `InstalledCliRuntime.safe_for_auto_upgrade` must encode the same membership as `_SAFE_AUTO_UPGRADE_METHODS` in `install_method.py` (PIPX, UV_TOOL, BREW, PIP_USER, PIP_SYSTEM); no change to whitelist membership. | Compatibility | High | Open |
| C-007 | Receipt adapter targets the pre-staged directory | The `UvReceiptReader` adapter must be placed in `compat/_adapters/uv_receipt.py`; the pre-staged `compat/_adapters/__init__.py` is the designated home and must not be relocated. | Architecture | Medium | Open |
| C-008 | History store schema design is a gated deliverable | The exact history store schema (fields, file format, retention policy) must be finalized and reviewed before FR-013 implementation begins; the schema design and blast-radius assessment are required inputs to the step-2 work package. See open question in Assumptions. | Risk | High | Open |

### Key Entities *(domain data)*

- **`InstalledCliRuntime`**: Immutable snapshot of a spec-kitty-cli installation. Carries: install_method (reuses `InstallMethod` enum), executable path, receipt_path, tool_dir, bin_dir, is_default_tool_dir, is_default_bin_dir, python override, requirements (tuple of `UvRequirement`), package_source (derived: pypi-specifier | git | url | directory | editable | path), platform (posix | windows), and safe_for_auto_upgrade flag.
- **`UvRequirement`**: A single requirement entry from a uv receipt. Fields mirror the uv receipt TOML schema: name, specifier, directory, editable, path, git, url (all optional except name).
- **`RemediationCommand`**: A fully specified remediation action. Fields: intent (UPGRADE | REINSTALL_WITH_TEST | MANUAL_GUIDANCE), argv (tuple of str or None), env (Mapping[str, str]), note (str or None). The `render(platform)` method emits a CHK028-validated, env-prefixed, platform-quoted string for display consumers.
- **`UvReceiptReader`**: An adapter that reads and parses a `uv-receipt.toml` file given a tool-env directory, returning all `InstalledCliRuntime` fields derivable from the receipt. The single authoritative uv-receipt parser; replaces the three independent implementations.
- **`UvToolInstallationVerified`**: An event (frozen dataclass) emitted after a uv-tool upgrade attempt. Carries: receipt_path (Path or None), entrypoint_match (bool), package_binding (str), confidence (LOW | MEDIUM | HIGH).
- **`UpgradeAttemptRecord`**: A single history entry. Fields: attempt_id (str), timestamp (ISO datetime), install_method (InstallMethod), intent (str), outcome (success | failure | aborted), exit_code (int or None).
- **`UpgradeHint`**: Existing frozen dataclass (unchanged). After migration it becomes a thin façade: `command` delegates to `RemediationCommand.render()`. The `_HINT_TABLE` and CHK028 validation are preserved.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A single call to `detect_runtime()` returns all runtime context needed by any of the five legacy remediation sites; zero modules read the uv receipt more than once per invocation after migration.
- **SC-002**: The three independent receipt-parsing helper sets (`_active_uv_tool_receipt`, `_active_uv_tool_dir`, `_same_path`, `_uv_tool_python_args` and their variants) are fully deleted after migration steps 4 and 5; a codebase search for these function names returns zero results outside the new `UvReceiptReader` implementation.
- **SC-003**: For every install method and intent combination, `plan_remediation().render()` produces byte-for-byte identical output to what the corresponding legacy site produced before migration (verified by snapshot tests committed in step 3).
- **SC-004**: The upgrade-attempt history store supports idempotency and retry-eligibility queries with O(n) scan on at most the last 100 records; no external database is required.
- **SC-005**: All existing tests remain green after each individual migration step (FR-016 through FR-022); no step introduces a red-test window exceeding a single commit.
- **SC-006**: `UpgradeHint` consumers (`Plan.upgrade_hint` JSON, `upgrade` command display, `review` command display) continue to receive the same rendered command string before and after migration for every install method in `_HINT_TABLE`.

---

## Assumptions

1. The history store can be implemented as an append-only JSONL file (or SQLite sibling table — see mission 047 `OfflineQueue` precedent) under the same `~/.spec-kitty/` XDG directory as `upgrade-nag.json`, with no schema migration of existing NagCache data.
2. The `UvReceiptReader` output fields are stable for the versions of uv currently in the integration test matrix; no uv-receipt schema migration is in scope.
3. FR-021 (routing the hardcoded strings in `version_checker.py` and `schema_version.py` through `plan_remediation()`) is independently shippable and may be deferred to a follow-up mission if it increases step 6 scope materially.
4. The `detect_runtime()` detection chain for non-uv-tool install methods (pipx, brew, pip-user, pip-system, source, unknown) returns `InstalledCliRuntime` with `receipt_path=None` and `requirements=()`; no additional probing is required for those methods beyond what `detect_install_method()` already performs.
5. `RemediationCommand.render()` is responsible for CHK028 validation of the final string; individual argv components do not need to be pre-validated before assembly.

[NEEDS CLARIFICATION: History store persistence substrate — SQLite sibling table (consistent with OfflineQueue precedent from mission 047) vs. JSONL append-only file. Determination affects schema design, retention policy, concurrent-write strategy, and whether a migration is needed for existing installations. Must be resolved before FR-013 implementation begins.] <!-- decision_id: 01KW0NR6_HISTORY_STORE_SUBSTRATE -->

---

## Out of Scope

- Unrelated install-method detection changes beyond enriching `detect_runtime()` with fields already inspected by the current detection chain.
- Rewriting or changing the `Plan` planner decision logic (`compat/planner.py`) other than the `upgrade_hint` field.
- Changing the `NagCache` schema or its `upgrade-nag.json` file format.
- Introducing new install methods (e.g., snap, conda) — `InstallMethod` enum membership is unchanged.
- Changing the public `build_upgrade_hint()` signature or the `UpgradeHint` type's public fields.
- Migrating `version_checker.py` and `schema_version.py` hardcoded strings (FR-021) if the scope proves excessive — this is explicitly optional.

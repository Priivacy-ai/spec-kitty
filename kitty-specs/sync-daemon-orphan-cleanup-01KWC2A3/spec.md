# Mission Specification: Safe Sync Daemon Orphan Cleanup

| Field | Value |
|-------|-------|
| **Mission ID** | `01KWC2A3W1WQSNPR79D1N9MTF1` |
| **Mission slug** | `sync-daemon-orphan-cleanup-01KWC2A3` |
| **Mission type** | software-dev |
| **Target branch** | `fix/sync-daemon-orphan-cleanup` |
| **Source** | GitHub issue [#2261](https://github.com/Priivacy-ai/spec-kitty/issues/2261) (bug · reliability · P1 · usability) |
| **Status** | Draft — pending plan |
| **Created** | 2026-06-30 |

## Purpose

**TL;DR**: Prevent stale Spec Kitty sync daemons from piling up across upgrades by safely auto-retiring provably-orphaned ones and clearly reporting the rest.

Over time, normal CLI use and upgrades leave old sync-daemon processes resident on reserved ports, wasting resources and making auth/sync behavior hard to reason about. On 2026-06-30 one machine reported **18 orphan sync daemons** on ports `9401–9418` spanning package versions `3.2.2`, `3.2.3`, and `3.2.4`. Users should not have to discover this failure mode only after ports and background processes accumulate. This mission makes the sync daemon clean up after itself **safely**: only provably-orphaned daemons are auto-removed or self-retire, genuinely ambiguous ones are surfaced to the operator with a one-step fix instead of being killed silently, and cleanup is strictly walled off from the dashboard daemon's lifecycle and ports.

This is a narrow implementation slice for sync-daemon orphan prevention and cleanup — **not** a general daemon lifecycle refactor.

## User Scenarios & Testing

**Primary actor**: A Spec Kitty operator running the CLI. A secondary actor is the sync daemon itself, which acts on its own behalf at startup and while idle.

### Primary flow (happy path)

A developer who has upgraded Spec Kitty several times runs a CLI command that needs sync. Without thinking about daemons, they expect the system to *not* accumulate background processes. The system inspects the reserved sync port range, recognizes the prior-version daemons it can positively prove are its own stale orphans, retires them, and continues with a single healthy daemon — spawning no additional process.

### Acceptance scenarios

- **AS-1 — No redundant spawn** *(FR-006, FR-007, FR-008)*
  **Given** stale same-scope sync daemons from a prior version are listening in `[9400, 9450)` and are safely cleanable,
  **When** the operator runs a new CLI command that needs sync,
  **Then** the system cleans the stale daemons and does **not** spawn an additional daemon.

- **AS-2 — Ambiguous surfaced, never silently killed** *(FR-002, FR-006, FR-009)*
  **Given** a sync-like daemon that is pre-marker, cross-root, or missing daemon-local identity,
  **When** the scan runs,
  **Then** it is classified `operator_required`, reported with one-step remediation, and **not** killed by startup.

- **AS-3 — Visibility** *(FR-001, FR-004)*
  **Given** any mix of in-range candidates,
  **When** the operator runs `spec-kitty auth doctor --json` (or the human form),
  **Then** each candidate's identity record and `cleanup_class` (with `skip_reason` where relevant) appears in the output.

- **AS-4 — Exact reset reporting** *(FR-005)*
  **Given** a mix of `safe_auto` and `operator_required` daemons plus at least one process that cannot be killed,
  **When** the operator runs `spec-kitty auth doctor --reset --json`,
  **Then** `swept[]`, `skipped[]`, and `failed[]` each enumerate the exact PIDs/ports/reasons matching the real outcomes.

- **AS-5 — Self-retirement** *(FR-010, FR-011)*
  **Given** a sync daemon that is no longer the recorded singleton for its positively-proven scope and has no active sync work in flight,
  **When** the idle/no-work retirement threshold elapses,
  **Then** the daemon retires itself.

- **AS-6 — Cross-family safety** *(NFR-001, NFR-002, NFR-003, C-002)*
  **Given** a dashboard-shaped listener in `[9237, 9337)` and a third-party listener,
  **When** any sync cleanup path runs,
  **Then** both survive; symmetrically, a sync-shaped listener in `[9400, 9450)` survives every dashboard cleanup path.

- **AS-7 — Dashboard intent unchanged** *(C-003)*
  **Given** the operator runs `spec-kitty dashboard`,
  **When** the dashboard daemon starts,
  **Then** it uses `DaemonIntent.LOCAL_ONLY` and does not force hosted sync.

### Edge cases

- A daemon self-reports a PID/port that does **not** match the actual listener → not `safe_auto` (treated as `operator_required` or `never_touch`).
- The current recorded singleton is in range and healthy → never auto-killed (it is the live daemon).
- Package/executable version mismatch but singleton scope positively proven → **eligible** for cleanup, not skipped (FR-008).
- A Spec Kitty-looking process out of the sync range → `never_touch`.
- A third-party application squatting on a port inside `[9400, 9450)` → `never_touch`, never killed.
- During `--reset`, a process refuses to die (permission/race) → recorded in `failed[]`, never silently dropped.
- Daemon-root marker absent (pre-marker upgrade) → `operator_required`.
- Different `$HOME` / runtime root (cross-root) → `operator_required`, not `safe_auto`.

## Domain Language

| Canonical term | Meaning | Avoid / not the same as |
|----------------|---------|-------------------------|
| **Sync daemon** | Background auth/sync worker, user/runtime scoped; may outlive a single project command. Reserved ports `[9400, 9450)`. | Dashboard daemon |
| **Dashboard daemon** | Local per-project UI server with its own start/stop lifecycle and `.kittify/.dashboard` metadata. Reserved ports `[9237, 9337)`. | Sync daemon |
| **`daemon_family`** | Explicit family tag (`sync` vs dashboard) that gates which cleanup may touch a listener. | — |
| **Singleton scope** | The positively-provable identity scope that determines whether two daemons are "the same" recorded singleton. | `owner.json` health payload |
| **`cleanup_class`** | Classification of a scanned candidate: `safe_auto`, `operator_required`, or `never_touch`. | — |
| **Self-retirement** | A daemon voluntarily exiting when it is no longer the recorded singleton for its scope and has no work in flight. | Operator `--reset` |

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The sync-daemon scan produces, for each inspected listener, a structured **identity record** containing at minimum: `daemon_family`, `pid`, `port`, `protocol_version`, `package_version`, `singleton_scope_id`, `daemon_root`, `queue_db_path`, `auth_scope`, `server_url`, `owner_present`, `identity_source`, an executable/source identity summary, production-spawn-shape status, `cleanup_class`, and a `skip_reason` when cleanup is not automatic. | Approved |
| FR-002 | Each scanned candidate is assigned exactly one `cleanup_class`. **`safe_auto`**: sync daemon, port ∈ `[9400, 9450)`, self-reported PID/port match the actual listener, singleton scope positively proven, and not the current recorded singleton. **`operator_required`**: appears to be Spec Kitty sync but is pre-marker, cross-root, missing PID, missing daemon-local identity, or otherwise ambiguous. **`never_touch`**: third-party listener, dashboard daemon, cross-family listener, out-of-range process, or any process not identifiable as Spec Kitty sync. | Approved |
| FR-003 | Auto-kill decisions rely on a **daemon-local identity contract**, not on the shared `owner.json` health payload. `owner_present` may be reported but is not sufficient kill authority. | Approved |
| FR-004 | `spec-kitty auth doctor` and `spec-kitty auth doctor --json` expose the full scan classification (identity records, `cleanup_class`, and `skip_reason`). Count-only output is insufficient. | Approved |
| FR-005 | `spec-kitty auth doctor --reset` and `--reset --json` report exact cleanup results as three arrays: `swept[]` (PID, port, package/protocol, cleanup path, reason), `skipped[]` (PID/port when available + skip reason), and `failed[]` (PID/port when available + failure reason). Human output presents the same information compactly. | Approved |
| FR-006 | Sync startup may auto-clean **only** `safe_auto` sync daemons, and never kills `operator_required` or `never_touch` candidates. | Approved |
| FR-007 | When the new CLI starts and same-scope stale sync daemons exist that are `safe_auto`, startup cleans them and does **not** create an additional daemon. | Approved |
| FR-008 | A package/executable version mismatch is treated as **stale-version evidence** (eligible for cleanup) when singleton scope is positively proven; mismatch alone never causes cleanup to be skipped. | Approved |
| FR-009 | `spec-kitty auth doctor --reset` remains the explicit operator path that cleans `operator_required` sync daemons; ambiguous daemons are surfaced with one-step remediation guidance and never killed silently. | Approved |
| FR-010 | A newly started sync daemon **self-retires** when it is no longer the recorded singleton for its own positively-proven scope **and** no active sync work is in flight. | Approved |
| FR-011 | The idle / no-auth / no-work retirement delay is governed by a **named constant** that tests can patch to a low value to exercise the path deterministically. | Approved |
| FR-012 | The older same-`$HOME` singleton leak tracked in issue #1071 is **live-reconfirmed** against this implementation and then closed or explicitly re-scoped before the mission is considered done. | Approved |

## Non-Functional Requirements

| ID | Requirement | Measurable threshold | Status |
|----|-------------|----------------------|--------|
| NFR-001 | Sync cleanup stays bounded to the sync port range. | Every sync cleanup operation stays strictly within `[9400, 9450)` — **0** out-of-range signals. | Approved |
| NFR-002 | Dashboard cleanup stays bounded to the dashboard port range. | Every dashboard cleanup operation stays strictly within `[9237, 9337)` — **0** sync-port signals. | Approved |
| NFR-003 | Cross-family listeners are never wrongly killed. | Across all cleanup entrypoints: dashboard listeners survive **100%** of sync cleanups, sync listeners survive **100%** of dashboard cleanups, third-party listeners killed **0** times. | Approved |
| NFR-004 | Regression coverage uses live subprocesses, not mocks-only. | Tests use real loopback listeners and real subprocess PIDs covering: versions `3.2.2`/`3.2.3`/`3.2.4`, same-scope stale, pre-marker, different runtime-root/`$HOME`, third-party, dashboard, sync, and first/last/just-outside boundary ports for **both** ranges. | Approved |
| NFR-005 | New code passes quality gates. | Focused tests, `ruff`, and `mypy --strict` pass with **zero** issues and zero warnings on new code. | Approved |
| NFR-006 | Real-port tests do not flake on collisions. | Tests that bind real ports run serially or in isolated ranges — **0** port-collision flakes. | Approved |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Sync and dashboard daemon lifecycles remain **separate** (distinct ownership and safety envelopes). Shared helper code is permitted only when the daemon family is explicit. | Approved |
| C-002 | Sync cleanup never scans or kills dashboard ports; dashboard cleanup never scans or kills sync ports. | Approved |
| C-003 | `spec-kitty dashboard` startup continues to use `DaemonIntent.LOCAL_ONLY` and never forces hosted sync. | Approved |
| C-004 | No process is killed merely because it listens on a reserved port — identity must be positively established first. | Approved |
| C-005 | The daemon identity-contract change is captured in an ADR / decision note (per DIRECTIVE_003), and the operator remediation path (`auth doctor` → `auth doctor --reset`) is documented. | Approved |
| C-006 | On this development machine, hosted auth/sync test commands continue to use `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. | Approved |
| C-007 | Non-goals: do **not** replace the dashboard lifecycle with the sync lifecycle; do **not** change hosted auth or SaaS protocol semantics; do **not** attempt to resolve every daemon-identity seam from issue #1868. | Approved |

## Key Entities

- **Daemon Identity Record** — the per-candidate structure enumerated in FR-001; the authority for whether a daemon is provably "ours" and provably stale.
- **Cleanup Classification** — the `cleanup_class` verdict (`safe_auto` / `operator_required` / `never_touch`) plus `skip_reason`; the decision boundary between automatic and operator-driven cleanup.
- **Reset Result** — the `swept[]` / `skipped[]` / `failed[]` arrays returned by `auth doctor --reset`, each entry traceable to a real process outcome.

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | After upgrading and running the CLI while prior-version sync daemons are present, the system spawns **0** additional sync daemons when same-scope stale daemons are safely cleanable, and those stale daemons are gone afterward. |
| SC-002 | **100%** of ambiguous (`operator_required`) daemons are reported rather than silently killed, each accompanied by a one-step remediation command. |
| SC-003 | `auth doctor --json` shows identity and classification for **100%** of in-range candidates, and `auth doctor --reset --json` returns swept/skipped/failed entries that match the actual process outcomes. |
| SC-004 | Across the boundary regression matrix, dashboard and third-party listeners survive **100%** of sync cleanups and sync and third-party listeners survive **100%** of dashboard cleanups (0 wrongful kills). |
| SC-005 | An operator can go from "many orphans" to "clean" using exactly two documented commands: `spec-kitty auth doctor`, then `spec-kitty auth doctor --reset`. |
| SC-006 | Issue #1071 is live-reconfirmed and then closed or explicitly re-scoped. |

## Scope

**In scope**
- Safe orphan prevention and cleanup for the **sync daemon**, including scan, classification, `auth doctor` visibility, `--reset` reporting, startup auto-clean, and daemon self-retirement.
- The **dashboard daemon** appears only in **boundary and regression tests** (to prove cross-family isolation).
- Live-reconfirmation and closure/re-scoping of issue #1071.
- A decision record (ADR/note) for the daemon identity contract and operator remediation docs.

**Out of scope / non-goals**
- Replacing the dashboard lifecycle with the sync lifecycle.
- Killing arbitrary processes because they listen on a reserved port.
- Changing hosted auth or SaaS protocol semantics.
- Solving every daemon-identity seam from issue #1868 (broader workstream).

## Assumptions

- Sync daemon reserved ports are `[9400, 9450)`; dashboard daemon reserved ports are `[9237, 9337)`. These ranges are stable inputs to classification.
- Existing behavior already reuses a recorded healthy daemon, stops the recorded daemon on version/protocol mismatch, and runs a conservative reaper that intentionally skips daemons whose root marker, production spawn shape, or executable identity cannot be proven — this mission extends that model rather than replacing it.
- `auth doctor --reset` already provides a broader operator cleanup path via port scan and `/api/health` fingerprinting that this mission makes explicit and fully reported.
- Standard error handling applies: failures during cleanup are reported (in `failed[]`), not swallowed.

## Dependencies

- **Issue #1071** — older same-`$HOME` singleton leak. In scope for this mission (FR-012, SC-006): live-reconfirm, then close or explicitly re-scope.
- **Issue #1868** — broader daemon identity authority workstream. **Out of scope** here; this mission is a narrow slice (C-007).

## Definition of Done

All FR / NFR / C requirements satisfied and traceable to acceptance scenarios; success criteria SC-001…SC-006 demonstrated; the live-subprocess and dashboard-boundary regression matrices pass; `ruff` and `mypy --strict` clean on new code; the daemon identity-contract decision record and operator remediation docs are in place; and issue #1071 is reconfirmed and closed or re-scoped.

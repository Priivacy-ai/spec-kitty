# Phase 0 Research: MVP CLI Sync Boundary Completion

**Mission**: `mvp-cli-sync-boundary-completion-01KRX11M`
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

## R1 — Preflight composition: single helper vs distributed inline checks

**Decision**: Introduce a single helper `SyncBoundaryPreflight` (file `src/specify_cli/sync/preflight.py`) that composes existing helpers and returns a structured `PreflightResult`. Sync-producing CLI entry points call this one helper.

**Rationale**:
- FR-001 / FR-002 explicitly require *reusable* gating across multiple commands. A single helper is the only shape that prevents drift between `sync now`, `setup-plan`, and any future SaaS-producing path.
- The repo already has a precedent for this pattern: `src/specify_cli/merge/preflight.py` defines a `PreflightResult` dataclass consumed by the merge command. Mirroring that shape lowers reviewer load and reuses test conventions.
- FR-003 requires named mismatched fields; that is cleaner to produce in one composer than to assemble in each call site.

**Alternatives considered**:
- *Inline checks per command*: rejected — guarantees drift; each new sync-producing command needs to remember to call the same set of helpers, and FR-005 / FR-004 parity becomes harder to maintain.
- *Decorator-based gate*: rejected — typer command callbacks already have multiple decorators; another one increases cognitive load and complicates testing.

## R2 — Refusal output format

**Decision**: Default refusal output is a Rich-rendered, two-section block:
1. Header line: `Sync boundary refused: <N> mismatched field(s); <M> orphan daemon record(s); <K> legacy rows in scope`.
2. Table of mismatches with columns `Field`, `Foreground`, `Daemon`. Field names use Domain Language canonical terms (`daemon_package_version`, `daemon_executable_path`, `daemon_source_path`, `daemon_server_url`, `daemon_team_or_user`, `daemon_queue_db_path`).
3. One-line remediation hint per category (e.g., "Run `spec-kitty doctor restart-daemon` to restart the daemon at the foreground source.").

A `--json` flag (where supported) emits the structured `PreflightResult.to_dict()` for scripting; default output is human-readable. Total visible refusal length ≤ 25 lines (NFR-004).

**Rationale**: NFR-004 says actionable in one terminal screen; Rich tables fit comfortably below 25 lines for ≤ 6 fields + ≤ 3 orphans. Canonical field names match the domain language in `spec.md` and the assertions in tests.

**Alternatives considered**:
- *JSON only*: rejected — operators run these commands interactively; raw JSON requires extra parsing.
- *Free-form prose*: rejected — assertions in tests must scan for canonical field names; free-form prose is harder to assert on.

## R3 — `sync status --check` field parity with preflight

**Decision**: `_build_boundary_check_failures()` (existing, `src/specify_cli/cli/commands/sync.py:1286`) becomes the single source of truth for the failure set. The preflight helper imports and calls it, then adds the `auth_present` axis. The status command continues to consume it directly. Both paths therefore exit non-zero on the same conditions and print the same mismatch list.

**Rationale**: FR-004 and the preflight's refusal set must match. Sharing one builder eliminates that risk by construction.

**Alternatives considered**:
- *Duplicate logic*: rejected — guarantees the two surfaces drift; the bug the PR is trying to close.
- *Move builder into `owner.py`*: deferred — the builder reads queue counts and foreground identity, which are not natural fits for `owner.py`. Keeping it under `cli/commands/sync.py` and importing into `sync/preflight.py` is acceptable; if cyclic-import pressure emerges, move to `sync/coherence.py`.

## R4 — Row-level migration for `body_upload_queue`

**Decision**: Extend `_migrate_legacy_queue_to_scope()` (existing, `src/specify_cli/sync/queue.py:706`) so the inner loop walks both `sync_events`-class rows and `body_upload_queue` rows. Each `INSERT INTO scoped …` uses `INSERT OR IGNORE` keyed on the row's primary key (event_id for events, upload_id for body uploads) so retries are idempotent.

`detect_legacy_rows_for_scope()` (existing, `:744`) is extended to count both row classes and return a structured count instead of a bare integer if needed for `sync status --check` field expansion.

**Rationale**: FR-006 / FR-007 require body uploads to be migrated regardless of scoped-DB occupancy, and re-run safety is required by Scenario 3 in `spec.md`. `INSERT OR IGNORE` is the SQLite-native idempotence primitive; no schema change required.

**Alternatives considered**:
- *Truncate-and-rebuild*: rejected — non-empty scoped DB cannot be truncated; loses unrelated rows.
- *Separate migration entry point per row class*: rejected — doubles surface area and creates two code paths that can drift; one loop with two row classes is simpler.

## R5 — Setup-plan refusal placement

**Decision**: Add the boundary preflight at `src/specify_cli/cli/commands/agent/mission.py:926` *after* the existing hosted-auth preflight (so the auth-absent refusal at `:942` keeps firing first when no auth is present), and *before* any enqueue or body-upload path (covers the WPCreated emission area at `:2354`).

When auth is absent, the existing refusal is the operator's first signal; when auth is present, the new preflight runs and either passes or refuses with the structured mismatch list.

**Rationale**: FR-008 requires the auth-absent refusal to remain loud; FR-002 / FR-009 require the preflight to gate every SaaS-producing path. Layering the gates in this order keeps the existing test surface stable while adding the new gate exactly once.

## R6 — Events package dependency

**Decision**: Treat the `spec-kitty-events` package version pin in `pyproject.toml` / `uv.lock` as fixed for the duration of this mission. If Phase 1 (events doctrine reconciliation, `spec-kitty-events#32`) releases a patch, the dependency bump is *out of scope here* and handled by Phase 3 (SaaS) or by a follow-up CLI dependency bump.

**Rationale**: The MVP boundary the spec is closing is a CLI-internal gating issue, not an events-package contract issue. The force-required rollback contract from `spec-kitty-events#32` is already settled at the contract level; the CLI emits forced backward transitions and refuses to emit unforced ones today.

## R7 — Test fixtures and isolation

**Decision**: All new tests use `tmp_path`-scoped homes via existing `monkeypatch.setenv("HOME", …)` patterns; preflight tests do not touch the operator's real `~/.spec-kitty/queue.db`. Daemon owner-record tests use written-on-disk fixtures (no real `os.kill`), consistent with existing assertion at `tests/sync/test_daemon_owner_record.py:336`.

**Rationale**: Test suite flake on shared filesystem state is a known prior pain point; the existing tests already use this pattern. Reuse it to keep CI green.

## R8 — Backwards compatibility

**Decision**: All changes are additive on the CLI surface. `_require_daemon_owner_coherence()` remains callable from its current call site but becomes a thin wrapper around the preflight helper. The `sync status --check` exit codes do not regress (zero stays zero, non-zero stays non-zero); the set of detected non-zero conditions grows, which is correct per FR-004.

**Rationale**: The PR is a completion, not a rewrite. Keeping existing helpers as thin wrappers preserves any third-party invocation patterns and minimizes diff risk.

## Risk register

| ID | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Preflight false-positive on legitimate version skew between foreground and a running daemon | Medium | Medium (operator friction) | Refusal output names `doctor restart-daemon` remediation hint; documented in `quickstart.md` |
| R2 | Body-upload migration duplicates rows on retry | Low | High (sync amplification) | `INSERT OR IGNORE` keyed on primary key; dedicated test in `test_queue_row_level_migration.py` |
| R3 | Test flake from shared filesystem state | Low | Medium (CI noise) | All tests use `tmp_path` homes; do not touch real `~/.spec-kitty/queue.db` |
| R4 | Drift between `sync doctor` and `doctor orphan-daemons` detection | Medium | Low (operator confusion) | Both paths consume `list_orphan_records()` only; test asserts identical detection |
| R5 | Preflight call adds latency that surprises operators | Low | Low | NFR-003 caps at ≤ 100 ms; preflight only reads owner record and counts queue rows; no SaaS calls |
| R6 | New canonical field names diverge from what tests assert | Low | Medium (review churn) | Domain Language table in `spec.md` is the canonical source; field names lifted verbatim into preflight and tests |

## Open questions

None. No `[NEEDS CLARIFICATION]` markers remain.

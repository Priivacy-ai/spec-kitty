# Phase 0 Research: Unblock Sync Identity-Boundary Canary

**Mission**: `unblock-sync-identity-boundary-canary-01KRZJ07`
**Date**: 2026-05-19

This document resolves all design unknowns called out in the spec and the plan's Technical Context. Each entry uses the **Decision / Rationale / Alternatives** format.

---

## R1 — Lifecycle row identification signal

**Question**: How does the audit reliably tell a mission-lifecycle row apart from a status-transition row inside `status.events.jsonl`?

**Decision**: Match on `aggregate_type == "Mission"` AND presence of `event_type`. Both predicates must be true; either alone is insufficient.

**Rationale**:
- `src/specify_cli/status/lifecycle_events.py` is the canonical writer of mission-lifecycle rows; every row it emits carries `aggregate_type="Mission"` and an `event_type` discriminator (`MissionCreated`, `SpecifyStarted`, etc. — line refs in issue #1122).
- Status-transition rows produced by `status/store.py` and friends carry `from_lane` / `to_lane` and do **not** set `aggregate_type` or `event_type`. They use the StatusEvent shape declared in `src/specify_cli/status/models.py`.
- Requiring **both** predicates protects against future drift where a malformed status-transition row accidentally carries one of these fields — that row should still be flagged.

**Alternatives considered**:
- Match only on `event_type` presence. Rejected: a buggy status-transition writer could carry `event_type` and would be silently allowed.
- Match only on `aggregate_type == "Mission"`. Rejected: weaker; loses the principle "the FORBIDDEN_KEY rule is about the discriminator, not the owner."
- Match by inspecting the `event_id` ULID's time component or other proxies. Rejected: opaque, non-DDD.

---

## R2 — Rich Table behavior under non-TTY capture

**Question**: Is the ellipsis truncation in `sync status --check` a config issue (`overflow="fold"` on a column) or a structural issue (Rich Table is fundamentally width-bound)?

**Decision**: Structural. The cleanest long-term fix is to move file-path rows out of the Rich `Table` and render them via plain `Console.print` (already chosen via `print_paths_outside_table` decision).

**Rationale**:
- The `boundary_table` (`src/specify_cli/cli/commands/sync.py:1856-1863`) uses `Console()` whose width defaults to 80 columns when stdout is not a TTY. Even with `overflow="fold"`, Rich would *wrap* the path across multiple display lines — fold ≠ unwrap, fold just breaks at column width. Machine consumers that grep `Path` then read the rest of the line still trip over the wrap.
- The only rendering shape that preserves the canonical path verbatim on a single line, in every terminal width and in non-TTY captures, is `Console.print(f"{label}: {path}")` without a Table.
- The `--json` form already exposes paths as discrete string values; rendering them through `print` matches that contract.

**Alternatives considered**:
- `overflow="fold"` (Issue's option 1). One-liner cheap, but keeps the design quirk and the next path field added to the boundary view re-introduces the bug.
- Set `Console(width=10_000)` explicitly. Rejected: cosmetic, breaks visual layout for narrow TTYs.
- Render the entire boundary surface as plain text. Rejected: regresses operator UX for the non-path identity rows that benefit from tabular layout.

---

## R3 — `DaemonOwnerRecord` shape and lifecycle

**Question**: Does the existing `DaemonOwnerRecord` carry enough state for a stop-then-respawn cycle without re-deriving environment from scratch?

**Decision**: Yes. The record already persists `package_version`, `executable_path`, `source_path`, `server_url`, `queue_db_path`, and process metadata (pid, ports) — exactly the fields needed to drive a stop signal followed by a foreground-bound respawn.

**Rationale**:
- The record is the source of truth for `sync status --check` boundary comparison (`src/specify_cli/sync/preflight.py`).
- The same record is consumed by daemon-stop primitives that resolve the live process via `executable_path` and pid; `restart-daemon` can reuse this resolution.
- After stop, `sync now` (or its underlying launcher) reads the same record to spawn the new daemon at the recorded `executable_path` / `source_path` — i.e., **the foreground version/source by definition** (because the foreground is what writes the record at launch).

**Alternatives considered**:
- Mint a new `RestartIntent` record. Rejected: redundant; would duplicate state already owned by `DaemonOwnerRecord`.
- Read foreground from environment at restart time. Rejected: drifts from "restart at the registered owner's foreground" semantics; opens a class of mismatch bugs.

---

## R4 — Existing daemon stop + launch primitives

**Question**: Are existing daemon-stop and daemon-start primitives reusable by `restart-daemon`, or does the subcommand need its own lifecycle code?

**Decision**: Reusable. `restart-daemon` is a thin composition: `stop_registered_daemon()` → `launch_daemon_for_foreground()`, each already implemented in `src/specify_cli/sync/` (called by `sync stop` and `sync now`).

**Rationale**:
- The issue body explicitly suggests "Could wrap existing `sync stop` + `sync now` plumbing" — this matches `compose_stop_plus_start` from the plan decisions.
- Reuse minimizes new code surface and inherits existing test coverage of the lifecycle primitives.
- Composition keeps `restart-daemon` semantically honest: it is a guided helper, not a new lifecycle.

**Alternatives considered**:
- Hand-rolled signal-and-respawn. Rejected: duplicates existing logic, multiplies test surface.
- Spawn a subprocess that calls `spec-kitty sync stop && spec-kitty sync now`. Rejected: brittle (depends on PATH), harder to test, slower (two process spawns).

---

## R5 — Canary harness execution shape

**Question**: How is the canary invoked locally so WP04 can prove scenarios 1, 2, 4 turn green against the rc bump?

**Decision**: Clone or check out `Priivacy-ai/spec-kitty-end-to-end-testing` as a sibling directory; install the rc bump of `spec-kitty-cli` into the canary's virtualenv; run `pytest tests/identity_boundary/` with the documented seeded fixtures.

**Rationale**:
- The repo URL is known (`Priivacy-ai/spec-kitty-end-to-end-testing`), and scenarios 1–4 of issue `#42` are the gating tests.
- The canary uses pytest with fixture-driven `DaemonOwnerRecord` injection; running it requires a venv with the new spec-kitty-cli rc plus the canary's test deps.
- Captured artifacts go to `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/{run-1,latest}.json` to mirror the canary's own artifact convention.

**Alternatives considered**:
- Wait for the next scheduled CI canary in the sibling repo. Rejected: defers acceptance and decouples it from this mission's PR review.
- Stub out scenarios in-tree. Rejected: doesn't honor C-001 (no code change in sibling repo) and provides weaker proof.

---

## R6 — Scope of `_REMEDIATION_HINTS` rewrite

**Question**: Beyond the four lines explicitly called out in #1124 (99, 103, 107, 119), what else must be updated?

**Decision**: The four `_REMEDIATION_HINTS` strings plus the related comment at line 218 are all updated in one pass. No other occurrences exist in `src/specify_cli/sync/preflight.py`.

**Rationale**:
- A code grep of `"doctor restart-daemon"` in `src/specify_cli/sync/preflight.py` returns exactly those five sites; updating all five in a single change keeps wording consistent and prevents future readers seeing a stale comment after a hint update.
- The hints can now legitimately reference `spec-kitty doctor restart-daemon` (FR-007, FR-008) because the subcommand exists; the hint copy is refreshed to mention it as the primary remedy with the operator-friendly description from the WP03 spec.

**Alternatives considered**:
- Update only the four strings, leave the comment for later. Rejected: contradicts "all four occurrences should be updated together for consistency" in #1124.
- Inline-rewrite the dictionary to a function. Rejected: out-of-scope refactor; not needed by FR-008.

---

## Resolved unknowns from spec.md

| Spec marker | Resolution |
|-------------|------------|
| (none) | spec.md was committed substantive with all interview decisions resolved; no clarification markers were ever written. |

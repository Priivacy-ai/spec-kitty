---
work_package_id: WP02
title: Wire runtime surfaces onto Target Authority
dependencies:
- WP01
requirement_refs:
- FR-016
tracker_refs: []
planning_base_branch: mission/event-sync-retention-delivery
merge_target_branch: mission/event-sync-retention-delivery
branch_strategy: Planning artifacts for this mission were generated on mission/event-sync-retention-delivery. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/event-sync-retention-delivery unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 1 - Target Authority
assignee: ''
agent: "claude:opus:python-pedro:implementer"
shell_pid: "31738"
history:
- at: '2026-06-29T06:21:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/runtime.py
create_intent:
- tests/sync/test_target_authority_wiring.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/sync/config.py
- src/specify_cli/sync/runtime.py
- src/specify_cli/sync/preflight.py
- src/specify_cli/sync/owner.py
- src/specify_cli/sync/tracker_client_glue.py
- src/specify_cli/auth/config.py
- src/specify_cli/saas/readiness.py
- tests/sync/test_target_authority_wiring.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Wire runtime surfaces onto Target Authority

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this WP's `task_type` and `authoritative_surface`.

---

## Objectives & Success Criteria

Make every runtime hosted/sync surface consume the `ResolvedSyncTarget` from WP01 so that
**one resolved target** drives config reads, auth, readiness, preflight, owner records,
tracker glue, runtime sync, WebSocket, and the derived queue scope. This is the **rewiring
half of plan concern IC-00**: after WP01 produced the authority, this WP removes every
independent, surface-local target/scope derivation and routes them through the single
resolver. It honors **contract §1 (Target Authority)** exactly.

This WP is complete when:

- `sync/config.py` and `sync/runtime.py` obtain `resolved_server_url` from the
  `ResolvedSyncTarget`, not from ad-hoc config/env reads (T007).
- `auth/config.py` and `saas/readiness.py` evaluate auth/readiness against the **same**
  resolved target (T008).
- `sync/preflight.py` and `sync/owner.py` derive queue scope from the resolver — scope is
  **derived, never independently selected** (T009; contract §1 rule, C-002).
- `sync/tracker_client_glue.py` issues network calls to the **same** `resolved_server_url`
  as sync (T010).
- WebSocket, tracker, queue scope, and status all key off the one resolved target; every
  duplicate/independent target derivation is removed (T011; contract §1).
- `tests/sync/test_target_authority_wiring.py` proves env/config disagreement cannot split
  the live target from the derived queue scope (**SC-008**) and that a stale
  `active_queue_scope` is ignored as authority.

**Requirements satisfied**: FR-016 (canonical sync target authority — every surface uses the
one resolved target). Supporting: **SC-008** (env/config split-brain never derives scope for
one target while calling another), **C-002** (queue scope derived from identity, not an input
selector), **C-007** (target authority shared before journal migration/drain ships).

## Context & Constraints

- **Dependencies**: **WP01** — it hands you `ResolvedSyncTarget` and the resolver entry point
  in `src/specify_cli/sync/target_authority.py`. Import and consume that; do not re-derive
  the target, scope, or override mode anywhere in these files. WP01 already guarantees the
  split-brain guard fires before network use — your job is to make sure no surface reaches a
  network call or scope selection *without going through the resolver first*.
- **What this WP unblocks**: WP04/WP05 delivery-target identity, WP10 migration, and WP11/WP12
  status/CLI all assume a single coherent runtime target. After this WP, readiness, tracker,
  WebSocket, and queue scope can no longer disagree.
- **Links**:
  - `kitty-specs/event-sync-retention-delivery-01KVYWRG/spec.md` — FR-016, C-002, C-007,
    SC-008; "Env/config target split-brain" edge case.
  - `kitty-specs/event-sync-retention-delivery-01KVYWRG/plan.md` — IC-00 (affected surfaces
    list, which is exactly this WP's `owned_files` minus `queue.py`/`cli/commands/sync.py`).
  - `kitty-specs/event-sync-retention-delivery-01KVYWRG/contracts/event-sync-delivery-contract.md`
    — §1 Target Authority (rules + required tests).

- **IMPORTANT ownership note (out-of-map boundaries — do NOT touch)**:
  - **Do NOT edit `src/specify_cli/sync/queue.py`** — it is owned by **WP10**. `queue.py`
    still exposes `build_queue_scope`, `scope_db_path`, `read_queue_scope_from_session`,
    `read_queue_scope_from_credentials`. You may **read** and **call** these as a library, but
    the queue's *scope-consumption rewrite* (consuming the resolver's `derived_queue_scope`
    instead of computing its own) lands in WP10. Coordinate; do not pre-empt it. If a surface
    you own currently asks `queue.py` to compute scope, change *your* call site to pass the
    resolver's derived scope/path; do not change `queue.py` itself.
  - **Do NOT edit `src/specify_cli/cli/commands/sync.py`** — owned by **WP12**. CLI wiring
    (`sync now`/`server`/`status`) onto the resolver happens there.
  - These are disjoint-ownership rules from `finalize-tasks`; editing either file is a
    boundary violation that will fail review.

- **Architectural constraints**:
  - Contract §1: queue scope, ledger target identity, auth/readiness, WebSocket, tracker, and
    batch posts must use the **same** `resolved_server_url`. After this WP there is exactly
    one place that decides the target (WP01's resolver) and every surface reads it.
  - Contract §1: `active_queue_scope` is never an input selector — when wiring `preflight.py`
    /`owner.py`, the scope comes from `ResolvedSyncTarget.derived_queue_scope`; any cached
    scope is only a `stale_non_authoritative` diagnostic, never used to pick the queue.
  - C-002: identity = URL + scope; do not introduce a new identity key.
  - **Terminology Canon**: no `feature*` aliases in any flag/field/symbol you add or rename.
  - **Sonar/complexity**: keep each rewired function ≤15; where a surface mixed
    read+resolve+act, inject the resolved target as a parameter and drop the local resolution
    branch (this usually *lowers* complexity). Hoist any repeated literal (env var name,
    default URL) to a constant — prefer importing the constant WP01 already defined.

## Branch Strategy
- **Strategy**: Planning artifacts were generated on mission/event-sync-retention-delivery; completed changes must merge back into mission/event-sync-retention-delivery.
- **Planning base branch**: mission/event-sync-retention-delivery
- **Merge target branch**: mission/event-sync-retention-delivery
> Populated by `spec-kitty agent mission tasks`. Do not change manually.

## 🔴 ATDD-First (binding — charter C-011)

**You cannot start implementation until a failing-first ATDD test exists.** Per the charter's *ATDD-First Discipline* (binding, C-011), this WP follows red→green→refactor:

1. **RED first** — before any implementation commit, write at least one acceptance test that pins the user-observable behaviour this WP delivers (see the Subtasks/Acceptance below) and commit it **as the lane's first, separate commit while it FAILS**.
2. **GREEN** — implement until that test (and the rest) pass.
3. **Refactor** with the tests green.

The reviewer verifies **red→green**: the ATDD test was RED on `mission/event-sync-retention-delivery` and GREEN on this WP's final commit. A WP without a failing-first ATDD commit is **rejected at review** even if the code works.

## Subtasks & Detailed Guidance

### Subtask T007 – Rewire `sync/config.py` + `sync/runtime.py`
- **Purpose**: Route the resolved URL through the two most central sync surfaces so they stop
  reading config/env independently (FR-016).
- **Steps**:
  1. In `src/specify_cli/sync/config.py`: keep `SyncConfig.get_server_url()` /
     `set_server_url()` as the **config-file accessor** (the resolver reads through it). Add a
     thin path so callers that need the *runtime* target obtain a `ResolvedSyncTarget` rather
     than the raw `get_server_url()` — e.g. expose/keep a single resolver-backed entry point
     and route internal config consumers through it. Do not duplicate env reading here; the
     resolver owns env precedence.
  2. In `src/specify_cli/sync/runtime.py`: where sync routing/base-URL is resolved
     (see the `Could not resolve sync routing config` path and the WebSocket comment around
     "Server URL comes from `SPEC_KITTY_SAAS_URL` via WebSocketClient internals"), replace the
     ad-hoc URL source with `ResolvedSyncTarget.resolved_server_url`. The WebSocket and any
     emitter base URL must come from the same resolved target (T011).
  3. Resolve the target **once** per runtime entry and pass the object down, rather than
     re-resolving in nested calls (keeps complexity low and prevents drift).
- **Files**: `src/specify_cli/sync/config.py`, `src/specify_cli/sync/runtime.py`.
- **Parallel?**: No — both are the resolver's primary consumers and share the entry point.
- **Validation**:
  - [ ] `runtime.py` obtains its base/WebSocket URL from `ResolvedSyncTarget`, not a local
        env/config read.
  - [ ] `config.py` no longer performs independent env-override resolution; env precedence is
        the resolver's job.
  - [ ] A single resolution per runtime entry (no nested re-resolve).
- **Edge cases**: env unset (config-only) still resolves; `set_server_url()` write path
  unchanged so `sync server <url>` still updates `config.toml`.

### Subtask T008 – Rewire `auth/config.py` + `saas/readiness.py`
- **Purpose**: Make auth and readiness evaluate against the same resolved target, so readiness
  can never green-light a different URL than sync uses (FR-016, SC-008).
- **Steps**:
  1. In `src/specify_cli/auth/config.py`: `get_saas_base_url()` (reads `SPEC_KITTY_SAAS_URL`)
     remains the **env accessor** the resolver consumes for `env_server_url`. Do not let other
     surfaces call it directly to pick a live target — they should read
     `ResolvedSyncTarget.resolved_server_url`. If keeping the function, keep it as a
     low-level accessor; redirect higher-level "what target are we hitting?" callers to the
     resolver.
  2. In `src/specify_cli/saas/readiness.py`: `_probe_host_config()` currently encodes the
     precedence (env first, then `SyncConfig.get_server_url()`). Replace that bespoke
     precedence with `ResolvedSyncTarget.resolved_server_url` so readiness probes the resolved
     URL. `_probe_reachability(server_url, ...)` must receive the resolved URL; the
     `{server_url}` message templates then reference the single resolved target.
  3. `evaluate_readiness(...)` should accept or obtain the `ResolvedSyncTarget` and probe its
     `resolved_server_url`; the readiness result then describes the same target sync uses.
- **Files**: `src/specify_cli/auth/config.py`, `src/specify_cli/saas/readiness.py`.
- **Parallel?**: No — readiness depends on the auth accessor staying coherent.
- **Validation**:
  - [ ] `_probe_reachability` is called with the resolver's `resolved_server_url`.
  - [ ] readiness messages reference the resolved target, not a separately-read URL.
  - [ ] `get_saas_base_url()` is no longer the live-target source for high-level callers.
- **Edge cases**: env-override (`process_override`) ⇒ readiness probes the env URL; ambiguous
  split-brain ⇒ resolver already failed/warned (WP01) before readiness probes anything.

### Subtask T009 – Rewire `sync/preflight.py` + `sync/owner.py` (scope derived)
- **Purpose**: Ensure queue scope used by preflight and owner records is **derived from the
  resolver**, not selected independently — the structural fix for SC-008 (contract §1 rule,
  C-002).
- **Steps**:
  1. In `src/specify_cli/sync/preflight.py`: wherever preflight selects/validates a queue
     scope or db path, source it from `ResolvedSyncTarget.derived_queue_scope` /
     `queue_db_path`. Remove any local call that independently re-derives scope from a URL it
     read itself.
  2. In `src/specify_cli/sync/owner.py`: owner/daemon-owner records that persist a scope must
     record the resolver's `derived_queue_scope`. If owner currently calls
     `build_queue_scope(...)` with its own URL/identity, pass the resolver's derived scope
     instead (do **not** edit `queue.py`).
  3. Treat any cached/persisted scope (`active_queue_scope`) as a diagnostic only: if it is
     `stale_non_authoritative`, use the derived scope and surface the staleness — never pick
     the cached one (contract §1).
- **Files**: `src/specify_cli/sync/preflight.py`, `src/specify_cli/sync/owner.py`.
- **Parallel?**: No — both consume the resolver's derived scope; coordinate the seam with
  WP10 (which rewrites `queue.py`'s scope-consumption).
- **Validation**:
  - [ ] preflight uses `ResolvedSyncTarget.derived_queue_scope`/`queue_db_path`.
  - [ ] owner records the resolver's derived scope.
  - [ ] No independent scope selection from a self-read URL remains in either file.
  - [ ] Stale cached scope is reported, not used.
- **Edge cases**: unauthenticated scope (pre-auth) still resolves; switching targets changes
  the derived scope so preflight/owner follow without manual cache invalidation.

### Subtask T010 – Rewire `sync/tracker_client_glue.py` to the resolved URL
- **Purpose**: Make tracker network calls hit the **same** `resolved_server_url` as sync, so
  the tracker can never bind to a different target than the journal/ledger (contract §1).
- **Steps**:
  1. In `src/specify_cli/sync/tracker_client_glue.py`: where the tracker client is
     constructed/pointed at a base URL, source that URL from
     `ResolvedSyncTarget.resolved_server_url` rather than reading config/env locally.
  2. Pass the resolved target (or its URL) in from the runtime entry resolved in T007, rather
     than re-resolving inside the glue.
  3. Keep tracker consumption via the public `spec_kitty_tracker.*` surface per the Shared
     Package Boundary — only the *base URL* is what this WP redirects.
- **Files**: `src/specify_cli/sync/tracker_client_glue.py`.
- **Parallel?**: Could overlap T008/T009 once the resolver entry point exists, but in practice
  ordered after T007 (it reuses the runtime-resolved target).
- **Validation**:
  - [ ] tracker base URL == `ResolvedSyncTarget.resolved_server_url`.
  - [ ] no independent env/config URL read remains in the glue.
- **Edge cases**: env override ⇒ tracker follows the env URL (same as sync); offline/no-target
  path unchanged.

### Subtask T011 – One resolved target across WebSocket / tracker / scope / status
- **Purpose**: Close the loop required by contract §1: WebSocket, tracker, queue scope, and
  status all key off the **one** resolved target; remove any remaining independent target
  derivation (FR-016, SC-008).
- **Steps**:
  1. Audit the owned surfaces for any remaining direct reads of `SPEC_KITTY_SAAS_URL` or
     `SyncConfig.get_server_url()` that pick a *live* target (grep these files for the env var
     name and `get_server_url`). Each such site must be replaced with a read of the resolved
     target — except the two designated accessors (`get_saas_base_url`, `get_server_url`)
     which the resolver itself consumes.
  2. Ensure the WebSocket base URL (referenced in `runtime.py`) and the tracker base URL
     (T010) both come from the resolved target; confirm the status diagnostics source
     (`ResolvedSyncTarget.to_diagnostics_dict()` from WP01) is the single feed for the
     `target_authority` JSON section (assembled in WP11) — do not invent a parallel status
     target read here.
  3. Document, in a short module-level comment near the resolver import, that this surface
     consumes the canonical target and must not re-derive it (anchors future reviewers).
- **Files**: all sync/auth/saas files in `owned_files` (no new files).
- **Parallel?**: No — this is the convergence/audit step after T007–T010.
- **Validation**:
  - [ ] No owned surface independently derives a live target (only the two accessors remain,
        consumed by the resolver).
  - [ ] WebSocket, tracker, queue scope, and status diagnostics all trace back to one
        `ResolvedSyncTarget`.
- **Edge cases**: a surface that legitimately needs the raw config value (e.g. `sync server`
  display in WP12) is out of this WP's scope; do not touch CLI here.

### Subtask T012 – Wiring tests
- **Purpose**: Prove the wiring at the integration level: env/config disagreement cannot split
  the live target from the derived queue scope (SC-008), and a stale `active_queue_scope` is
  ignored as authority (NFR-001 — assert observable state, not call order).
- **Steps**:
  1. Create `tests/sync/test_target_authority_wiring.py`.
  2. **No split-brain across surfaces (SC-008)**: set `SPEC_KITTY_SAAS_URL` to a URL different
     from `config.toml`. Drive readiness/runtime/preflight/owner/tracker wiring and assert
     that the URL each surface targets **and** the derived queue scope all reflect the same
     resolved target — it is impossible to derive scope for one target while a surface posts
     to another. (If WP01 fails-closed on the ambiguous case, assert the failure/warning
     surfaces before any probe.)
  3. **Stale scope ignored**: seed a cached/persisted `active_queue_scope` that differs from
     the freshly derived scope; assert preflight/owner use the derived scope and surface the
     `stale_non_authoritative` diagnostic rather than honoring the cache.
  4. **Single-target coherence**: assert tracker base URL, WebSocket/runtime base URL, and the
     readiness-probed URL are equal to `ResolvedSyncTarget.resolved_server_url`.
  5. Use monkeypatch for env, tmp `config.toml`, and a seeded cached scope; stub network at
     the boundary (no real ports — this is not a daemon test, runs in the parallel suite).
- **Files**: `tests/sync/test_target_authority_wiring.py`.
- **Parallel?**: No — exercises the full wiring after T007–T011.
- **Validation**:
  - [ ] Env/config disagreement cannot split target vs queue scope (SC-008) — test passes.
  - [ ] Stale `active_queue_scope` is reported and ignored as authority — test passes.
  - [ ] All wired surfaces target the same `resolved_server_url` — test passes.
  - [ ] Assertions are on observable state/URLs, not call order (NFR-001).
- **Edge cases**: env equals config (no override); unauthenticated scope; corrupt cached scope
  treated as `absent`.

## Test Strategy

- **Mandatory tests** live in `tests/sync/test_target_authority_wiring.py` (the only test file
  in `owned_files`). They assert the contract §1 wiring invariants as observable state across
  the rewired surfaces — not internal call order (NFR-001).
- **Commands** (in-process; no real ports/daemon — runs in the parallel suite):
  ```bash
  PWHEADLESS=1 .venv/bin/pytest tests/sync/test_target_authority_wiring.py -q
  ```
  Parallel local run: `PWHEADLESS=1 .venv/bin/pytest tests/sync/test_target_authority_wiring.py -n auto --dist loadfile -q`.
  When touching readiness/owner near daemon paths, sanity-run the broader sync slice; any
  real-port/daemon case (e.g. orphan-sweep) must run serially with `-n0` in its own pass.
- **Regression sweep**: rerun the existing sync/auth/saas tests that exercise these modules
  (e.g. readiness, preflight, owner) to confirm the rewire preserves behavior:
  ```bash
  PWHEADLESS=1 .venv/bin/pytest tests/sync -q -k "readiness or preflight or owner or tracker or config"
  ```
- **Fixtures/stubs**: monkeypatch `SPEC_KITTY_SAAS_URL`; temp `config.toml`; seed a cached
  scope; stub the HTTP/WebSocket boundary so no live connection opens.
- **Lint/type gates** (clean, no suppressions):
  ```bash
  .venv/bin/ruff check src/specify_cli/sync/config.py src/specify_cli/sync/runtime.py \
    src/specify_cli/sync/preflight.py src/specify_cli/sync/owner.py \
    src/specify_cli/sync/tracker_client_glue.py src/specify_cli/auth/config.py \
    src/specify_cli/saas/readiness.py tests/sync/test_target_authority_wiring.py
  .venv/bin/mypy src/specify_cli/sync/runtime.py src/specify_cli/saas/readiness.py
  ```

## Risks & Mitigations

- **Wide surface (plan IC-00 risk)**: edits span `sync/`, `auth/`, and `saas/`; a missed call
  site re-introduces split-brain. *Mitigation*: T011 is an explicit audit step — grep every
  owned file for `SPEC_KITTY_SAAS_URL` and `get_server_url`, and the wiring test asserts all
  surfaces agree.
- **Boundary violation on `queue.py` / `cli/commands/sync.py`**: tempting to "just fix" scope
  consumption in `queue.py`. *Mitigation*: change only *your* call sites to pass the resolver's
  derived scope; the `queue.py` rewrite is WP10's and the CLI wiring is WP12's. Touching either
  file fails review.
- **Behavior drift in readiness/preflight**: replacing bespoke precedence could change which
  URL is probed. *Mitigation*: WP01's resolver matches `_probe_host_config()`'s existing
  precedence; rerun the readiness/preflight regression slice.
- **Double-resolution drift**: re-resolving the target in nested calls could diverge.
  *Mitigation*: resolve once per runtime entry (T007) and pass the object down.
- **Complexity ceiling (≤15)**: injecting the resolved target generally lowers complexity by
  deleting local resolution branches; keep helpers small and add a focused test per branch.

## Review Guidance

For `/spec-kitty.review`, verify:

- `sync/config.py` and `sync/runtime.py` source the live URL from `ResolvedSyncTarget`, not
  ad-hoc env/config reads; WebSocket base URL comes from the resolved target (T007, T011).
- `auth/config.py`'s `get_saas_base_url()` and `SyncConfig.get_server_url()` remain *only* the
  low-level accessors the resolver consumes; high-level callers read the resolved target.
- `saas/readiness.py` probes `ResolvedSyncTarget.resolved_server_url` (T008).
- `sync/preflight.py` and `sync/owner.py` derive queue scope from the resolver and treat any
  cached scope as a `stale_non_authoritative` diagnostic only (T009; contract §1, C-002).
- `sync/tracker_client_glue.py` targets the same `resolved_server_url` (T010).
- **No edits to `src/specify_cli/sync/queue.py` or `src/specify_cli/cli/commands/sync.py`** —
  ownership boundaries respected (WP10 / WP12).
- `tests/sync/test_target_authority_wiring.py` proves: env/config disagreement cannot split
  target vs queue scope (SC-008); stale `active_queue_scope` ignored; all surfaces share one
  resolved URL.
- `ruff`/`mypy` clean with no new suppressions; functions ≤15 complexity; no `feature*`
  aliases introduced (Terminology Canon).

## Activity Log
> Entries chronological, appended at END. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`
- 2026-06-29T06:21:37Z – system – Prompt created.
- 2026-06-29T07:49:09Z – claude:opus:python-pedro:implementer – shell_pid=31738 – Assigned agent via action command
- 2026-06-29T08:21:13Z – user – shell_pid=31738 – WP02 implementation: ResolvedSyncTarget wiring
- 2026-06-29T08:21:16Z – user – shell_pid=31738 – WP02 implementation: ResolvedSyncTarget wiring

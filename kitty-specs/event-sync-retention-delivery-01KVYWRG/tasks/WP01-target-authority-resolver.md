---
work_package_id: WP01
title: Target Authority resolver
dependencies: []
requirement_refs:
- FR-016
tracker_refs: []
planning_base_branch: mission/event-sync-retention-delivery
merge_target_branch: mission/event-sync-retention-delivery
branch_strategy: Planning artifacts for this mission were generated on mission/event-sync-retention-delivery. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/event-sync-retention-delivery unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Target Authority
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "30246"
history:
- at: '2026-06-29T06:21:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/target_authority.py
create_intent:
- src/specify_cli/sync/target_authority.py
- tests/sync/test_target_authority.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/sync/target_authority.py
- tests/sync/test_target_authority.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Target Authority resolver

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this WP's `task_type` and `authoritative_surface`.

---

## Objectives & Success Criteria

Build the single canonical runtime sync-target resolver — `ResolvedSyncTarget` and its
builder in `src/specify_cli/sync/target_authority.py`. This is the **core of plan concern
IC-00** (#2146) and the prerequisite every later WP depends on: journal target identity,
delivery-ledger target identity, and migration backfill all key off the one target this
resolver produces. It honors **contract §1 (Target Authority)** exactly.

This WP is complete when:

- A pure, side-effect-free `ResolvedSyncTarget` carries all eight contract §1 fields
  (`configured_server_url`, `env_server_url`, `override_mode`, `resolved_server_url`,
  `user_id`, `team_slug`, `derived_queue_scope`, `queue_db_path`,
  `active_queue_scope_status`).
- A resolver reads `~/.spec-kitty/config.toml` `[sync].server_url` and the
  `SPEC_KITTY_SAAS_URL` environment variable, computes `override_mode`, and produces a
  single `resolved_server_url` used by every hosted/sync surface (wiring happens in WP02).
- `derived_queue_scope` and `queue_db_path` are **derived** from the resolved URL +
  identity — never accepted as an input selector (contract §1 rule, **C-002**).
- `active_queue_scope_status` is computed as a diagnostic (`absent` / `matches` /
  `stale_non_authoritative`) and is **never** used as authority.
- The split-brain guard (contract §1) ensures env/config disagreement either applies one
  explicit whole-process override everywhere or fails/warns **before any network call** —
  satisfying **SC-008**.
- `tests/sync/test_target_authority.py` proves the contract §1 "Required tests" at the
  resolver level plus SC-008.

**Requirements satisfied**: FR-016 (canonical sync target authority). Supporting:
**C-002** (identity = URL + scope; queue scope derived), **C-007** (target authority before
journal migration), **SC-008** (env/config split-brain never derives scope for one target
while calling another).

## Context & Constraints

- **Dependencies**: none. This is the first WP in the mission; nothing precedes it.
- **What this WP hands downstream**: WP02 rewires `sync/config.py`, `sync/runtime.py`,
  `auth/config.py`, `saas/readiness.py`, `sync/preflight.py`, `sync/owner.py`, and
  `sync/tracker_client_glue.py` onto the `ResolvedSyncTarget` this WP produces. WP04/WP05
  derive delivery-target identity from `resolved_server_url` + `user_id`/`team_slug`. WP10
  migration backfill uses the same identity. Keep the public surface small and stable:
  a `ResolvedSyncTarget` dataclass and a resolver entry point (e.g. `resolve_sync_target(...)`).
- **Links**:
  - `kitty-specs/event-sync-retention-delivery-01KVYWRG/spec.md` — FR-016, FR-019, C-002,
    C-007, SC-008, SC-010; "Env/config target split-brain" edge case.
  - `kitty-specs/event-sync-retention-delivery-01KVYWRG/plan.md` — IC-00 (purpose, affected
    surfaces, sequencing, risks).
  - `kitty-specs/event-sync-retention-delivery-01KVYWRG/contracts/event-sync-delivery-contract.md`
    — §1 Target Authority (field table, rules, required tests).
- **Existing surfaces to read, NOT to edit here** (WP02 owns the rewiring; WP10 owns
  `queue.py`):
  - `src/specify_cli/sync/config.py` — `SyncConfig.get_server_url()` reads
    `[sync].server_url` from `config.toml` (default `https://spec-kitty-dev.fly.dev`);
    `set_server_url()` writes it. Reuse this read path; do not reimplement TOML parsing.
  - `src/specify_cli/auth/config.py` — `get_saas_base_url()` reads `SPEC_KITTY_SAAS_URL`
    (`_ENV_VAR = "SPEC_KITTY_SAAS_URL"`). Reuse it for `env_server_url`.
  - `src/specify_cli/sync/queue.py` — `build_queue_scope(server_url, username, team_slug)`,
    `scope_db_path(scope)` (→ `queues/queue-<digest>.db`), and
    `read_queue_scope_from_session()` / `read_queue_scope_from_credentials()`. The digest is
    a one-way hash of `server|user|team`. **Read these to mirror the derivation logic; do
    NOT import-and-mutate or edit `queue.py`** (owned by WP10).
  - `src/specify_cli/saas/readiness.py` — `_probe_host_config()` documents the precedence
    (env `SPEC_KITTY_SAAS_URL` first, then `SyncConfig.get_server_url()`). Your
    `override_mode` logic must match this precedence so readiness and the resolver agree.
- **Architectural constraints**:
  - Contract §1: `active_queue_scope` is **never** an input selector — only absent,
    recomputed cache, or stale diagnostic state.
  - Contract §1: queue scope, ledger target identity, auth/readiness, WebSocket, tracker,
    and batch posts must use the **same** resolved URL. This WP produces it; WP02 wires it.
  - C-002: target identity is canonical-URL + user/team scope; deployment metadata is never
    an identity key (out of scope for this WP — see WP04).
  - **Terminology Canon**: no `feature*` aliases in any new field, flag, or symbol. Use
    `target`/`scope`/`resolved`/`override` vocabulary.
  - **Sonar/complexity**: keep `resolve_sync_target` ≤15 by extracting read/derive/diagnose
    phases into small helpers (see Subtask steps). Hoist any literal used ≥3× (e.g. the
    override-mode tokens, env var name) to module constants.
- **No out-of-map edits.** Everything in this WP lives in the two `owned_files`.

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

## 🔒 Identifier Safety (binding — charter)

This WP generates storage-facing identifiers (`derived_queue_scope`, `queue_db_path`) from user/branch/URL/team input. Per the charter's *Identifier Safety Rules* they MUST be **ASCII-only and deterministic**: sanitize with an explicit ASCII allowlist (`[A-Za-z0-9_]`) or opt regexes into `re.ASCII` — never rely on default Unicode `\w`/`\W`. **Required regression coverage**: at least one accented-Latin input plus an assertion that the produced identifier `.isascii()` is `True`.

## Subtasks & Detailed Guidance

### Subtask T001 [P] – Define `ResolvedSyncTarget`
- **Purpose**: Establish the immutable value object that carries the complete contract §1
  field set. Every later WP reads from this object, so its shape is the contract surface.
- **Steps**:
  1. In `src/specify_cli/sync/target_authority.py`, define a frozen `@dataclass(frozen=True)`
     `ResolvedSyncTarget` with the eight contract §1 fields:
     - `configured_server_url: str | None` — `[sync].server_url` from `config.toml` (None if
       table/key absent).
     - `env_server_url: str | None` — `SPEC_KITTY_SAAS_URL` (None if unset/blank).
     - `override_mode: OverrideMode` — `none` | `setup_only` | `process_override`.
     - `resolved_server_url: str` — the single URL hosted calls, WebSocket, tracker, sync use.
     - `user_id: str | None` and `team_slug: str | None` — authenticated identity when known.
     - `derived_queue_scope: str` — deterministic isolation key (see T003).
     - `queue_db_path: Path` — scoped queue path derived from `derived_queue_scope` (T003).
     - `active_queue_scope_status: QueueScopeStatus` — `absent` | `matches` |
       `stale_non_authoritative` (T004).
  2. Model `override_mode` and `active_queue_scope_status` as `StrEnum` (Python 3.11+) with
     the exact token strings from the contract so JSON serialization (WP11/FR-019) is literal.
  3. Add a `to_diagnostics_dict()` (or similar) returning a JSON-safe `dict` for the
     `target_authority` section consumed later by WP11 (contract §6). Keys = field names.
  4. Document in the docstring that the object is purely descriptive: it never opens a
     network connection, never mutates config, never selects a queue.
- **Files**: `src/specify_cli/sync/target_authority.py`.
- **Parallel?**: Yes `[P]` — pure type definition with no dependency on other subtasks.
- **Validation**:
  - [ ] All eight contract §1 fields present with the listed types.
  - [ ] `override_mode` values are exactly `none`/`setup_only`/`process_override`.
  - [ ] `active_queue_scope_status` values are exactly `absent`/`matches`/`stale_non_authoritative`.
  - [ ] Dataclass is frozen/immutable; no setter mutates after construction.
- **Edge cases**: `configured_server_url` and `env_server_url` may both be None (no config,
  no env) — `resolved_server_url` must still resolve to the documented default; record how.

### Subtask T002 – Resolve config + env; compute `override_mode`
- **Purpose**: Read both target sources and decide which one wins, recording the decision as
  `override_mode` so downstream surfaces and status can explain the resolution (FR-016).
- **Steps**:
  1. Read `configured_server_url` via `SyncConfig().get_server_url()` semantics (the
     `[sync].server_url` key; treat the hard-coded default as "configured" only if no key is
     present — preserve the distinction by reading the raw key, not just the defaulted value).
  2. Read `env_server_url` via `auth.config.get_saas_base_url()` semantics
     (`SPEC_KITTY_SAAS_URL`); normalize blank/whitespace to None.
  3. Compute `override_mode`:
     - `none` — env unset, or env equals config (no real disagreement).
     - `process_override` — env set and differs from config, applied for the whole process
       (env wins everywhere; this is the contract's "explicit whole-process override").
     - `setup_only` — env present but scoped to a setup/diagnostic context that must NOT
       silently retarget live hosted calls (mark it; T005 decides fail/warn). Distinguish
       this from `process_override` so the split-brain guard can treat them differently.
  4. Set `resolved_server_url` from the winning source (env under `process_override`,
     else config, else default). Normalize trailing slashes consistently so the derived
     scope and URL comparisons are stable.
  5. Extract a `_read_target_sources()` helper and a `_classify_override(...)` helper to keep
     the top-level resolver ≤15 complexity (Sonar S3776 / ruff C901).
- **Files**: `src/specify_cli/sync/target_authority.py`.
- **Parallel?**: No — depends on T001's types.
- **Validation**:
  - [ ] Env==config ⇒ `override_mode == none`, `resolved_server_url` == that URL.
  - [ ] Env≠config whole-process ⇒ `process_override`, `resolved_server_url` == env URL.
  - [ ] Neither set ⇒ documented default URL, `override_mode == none`.
  - [ ] URL normalization is identical for config-read and env-read paths.
- **Edge cases**: env set to the *same* URL as config must not be reported as an override
  (no false split-brain); blank `SPEC_KITTY_SAAS_URL` is treated as unset.

### Subtask T003 – Derive `derived_queue_scope` + `queue_db_path`
- **Purpose**: Make the queue scope a deterministic function of resolved URL + identity, so
  it can never point at a different server than `resolved_server_url` (contract §1 rule;
  C-002). This is the structural fix for the split-brain class of bugs.
- **Steps**:
  1. Compute `derived_queue_scope` deterministically from `(resolved_server_url, user_id,
     team_slug)`. Mirror the existing `build_queue_scope(server_url, username, team_slug)`
     logic in `sync/queue.py` (read it for the exact composition; do not edit it). The scope
     must be a one-way digest-style key — identical inputs ⇒ identical scope.
  2. Derive `queue_db_path` from the scope, mirroring `scope_db_path(scope)` →
     `<scoped_queue_dir>/queue-<digest>.db`. The path is a **function of the scope**, not an
     independent value.
  3. Add an explicit assertion/invariant in the docstring: *the scope is derived from the
     resolved target, never supplied by a caller.* The resolver exposes no parameter that
     injects a scope or db path.
  4. When identity (`user_id`/`team_slug`) is unknown (pre-auth), derive a stable
     unauthenticated scope rather than failing — capture-first/local durability (WP03) must
     still work before auth.
- **Files**: `src/specify_cli/sync/target_authority.py`.
- **Parallel?**: No — depends on T002's `resolved_server_url`.
- **Validation**:
  - [ ] Same `(url, user, team)` ⇒ byte-identical `derived_queue_scope`.
  - [ ] Different resolved URL ⇒ different scope and different `queue_db_path`.
  - [ ] `queue_db_path` is purely a function of `derived_queue_scope`.
  - [ ] No public parameter accepts an externally supplied scope or db path.
- **Edge cases**: unauthenticated (no user/team) still yields a usable scope; changing only
  identity (same URL) changes the scope as expected.

### Subtask T004 – Compute `active_queue_scope_status`
- **Purpose**: Surface, as a pure diagnostic, whether any cached/persisted scope agrees with
  the freshly recomputed scope — and guarantee the cached value is never treated as
  authority (contract §1 rule).
- **Steps**:
  1. Read any persisted/cached scope using the read-only `read_queue_scope_from_session()` /
     `read_queue_scope_from_credentials()` semantics in `sync/queue.py` (read, do not edit).
     If no cached scope exists ⇒ `absent`.
  2. Compare the cached scope to the freshly `derived_queue_scope` from T003:
     - equal ⇒ `matches`.
     - different ⇒ `stale_non_authoritative` (the cache is stale; the **derived** value wins).
  3. Store only the *recomputed* `derived_queue_scope` on `ResolvedSyncTarget`; the stale
     cached value is reported in diagnostics but never used to pick a queue or db path.
  4. Keep this in a `_diagnose_scope_status(...)` helper returning the enum, so the resolver
     stays flat.
- **Files**: `src/specify_cli/sync/target_authority.py`.
- **Parallel?**: No — depends on T003's derived scope.
- **Validation**:
  - [ ] No cached scope ⇒ `absent`.
  - [ ] Cached == derived ⇒ `matches`.
  - [ ] Cached != derived ⇒ `stale_non_authoritative`, and `derived_queue_scope`/`queue_db_path`
        still reflect the derived (not cached) value.
- **Edge cases**: a corrupt/unreadable cache entry is treated as `absent` (never raises into
  authority); reading the cache must not mutate it.

### Subtask T005 – Split-brain guard (env vs config)
- **Purpose**: Enforce contract §1's hard rule and SC-008: when `SPEC_KITTY_SAAS_URL`
  disagrees with `config.toml`, either one explicit whole-process override applies
  everywhere, or the resolver fails/warns **before any network call** — never silently
  deriving scope for one target while hosted calls go to another.
- **Steps**:
  1. Implement the guard as a pure decision over `(configured_server_url, env_server_url,
     override_mode)`. It runs during resolution, before any caller could open a connection.
  2. If `override_mode == process_override`: the override is explicit and whole-process —
     allow it; both `resolved_server_url` and `derived_queue_scope` consistently reflect the
     env URL. (No split possible because scope is derived from the resolved URL.)
  3. If env disagrees with config but is NOT a clean whole-process override (the
     `setup_only` / ambiguous case): fail-closed by raising a clear, typed error
     (e.g. `SyncTargetSplitBrainError`) OR return a target carrying a structured warning that
     callers must surface before network use. Pick fail-closed by default; document the
     warning path if a setup/diagnostic caller legitimately needs the looser behavior.
  4. The guard must be evaluable with **zero network access** — it only inspects strings and
     the override classification. Add a docstring note: "raised/decided before any
     auth/readiness/WebSocket/tracker/sync call."
  5. Error/warning message names both URLs and the resolution rule so an operator can fix it
     (`config.toml` vs `SPEC_KITTY_SAAS_URL`). Hoist the message template to a constant.
- **Files**: `src/specify_cli/sync/target_authority.py`.
- **Parallel?**: No — depends on T002's `override_mode`.
- **Validation**:
  - [ ] Clean whole-process override ⇒ resolves; scope + URL both reflect env.
  - [ ] Ambiguous env/config disagreement ⇒ fails/warns with both URLs in the message.
  - [ ] Guard reaches its decision without any network call (provable: no socket/HTTP import
        on the decision path).
- **Edge cases**: env equals config (not a disagreement) ⇒ guard is a no-op; missing config
  with env set is an explicit override, not a split-brain.

### Subtask T006 – Resolver unit tests
- **Purpose**: Prove contract §1's "Required tests" and SC-008 at the resolver level, as
  observable state on the returned `ResolvedSyncTarget` (NFR-001 — assert state, not call
  order).
- **Steps**:
  1. Create `tests/sync/test_target_authority.py`.
  2. **All fields populated**: under env==config (and under a clean override), assert every
     one of the eight fields is set with expected values (contract §1 field table).
  3. **No split-brain (SC-008)**: with `SPEC_KITTY_SAAS_URL` set to a different URL than
     `config.toml`, assert the resolver either (a) under `process_override` produces a target
     whose `derived_queue_scope` and `resolved_server_url` both reflect the env URL — i.e. it
     is impossible to derive scope for one target while resolving another — or (b) raises the
     split-brain error / carries the warning before any network call.
  4. **Stale scope ignored**: seed a cached/persisted scope that differs from the freshly
     derived one; assert `active_queue_scope_status == stale_non_authoritative` AND
     `derived_queue_scope`/`queue_db_path` reflect the recomputed value, proving the stale
     cache is reported but never authoritative (contract §1 + SC-008).
  5. Add `absent`/`matches` status cases and the "neither config nor env" default case.
  6. Use monkeypatch/tmp fixtures for `config.toml`, `SPEC_KITTY_SAAS_URL`, and the cached
     scope; assert against the returned dataclass and `to_diagnostics_dict()` — no network.
- **Files**: `tests/sync/test_target_authority.py`.
- **Parallel?**: No — exercises all prior subtasks.
- **Validation**:
  - [ ] Test for all-fields-populated passes.
  - [ ] Test that env/config disagreement cannot split target vs derived scope passes (SC-008).
  - [ ] Test that a stale `active_queue_scope` is reported and ignored as authority passes.
  - [ ] Tests assert on returned state / diagnostics dict, not internal call order (NFR-001).
- **Edge cases**: blank env var; corrupt cached scope ⇒ `absent`; unauthenticated identity.

## Test Strategy

- **Mandatory tests** live in `tests/sync/test_target_authority.py` (the only test file in
  `owned_files`). They cover contract §1's three "Required tests" at the resolver level —
  the third (`sync status --check --json` exposes target-authority fields) is wired and fully
  asserted in WP11/WP12; here, assert that `to_diagnostics_dict()` returns those fields so
  the downstream JSON section has a source.
- **Commands** (the resolver is pure/in-process — no real ports, runs in the parallel suite):
  ```bash
  PWHEADLESS=1 .venv/bin/pytest tests/sync/test_target_authority.py -q
  ```
  For a parallel local run: `PWHEADLESS=1 .venv/bin/pytest tests/sync/test_target_authority.py -n auto --dist loadfile -q`.
- **Fixtures/stubs**: monkeypatch `SPEC_KITTY_SAAS_URL`; write a temp `config.toml` with
  `[sync].server_url`; seed a cached scope via a tmp credentials/session fixture. No network,
  no daemon, no real port — so no `-n0` serial pass is required for this WP.
- **Lint/type gates** (must be clean, no suppressions):
  ```bash
  .venv/bin/ruff check src/specify_cli/sync/target_authority.py tests/sync/test_target_authority.py
  .venv/bin/mypy src/specify_cli/sync/target_authority.py
  ```

## Risks & Mitigations

- **Ambiguous env/config precedence (plan IC-00 risk)**: leaving the precedence vague would
  let the ledger record delivery for one target while network calls hit another. *Mitigation*:
  `override_mode` makes the decision explicit and the split-brain guard (T005) fails/warns
  pre-network; tests T006 lock SC-008.
- **`active_queue_scope` treated as authority**: the classic regression. *Mitigation*: the
  resolver derives scope from the resolved URL only (T003) and reads the cache solely to set
  a diagnostic status (T004); a test asserts the stale cache is ignored.
- **Drifting from existing scope/URL logic in `queue.py`/`config.py`**: reimplementing the
  digest differently from `build_queue_scope`/`scope_db_path` would silently move queues.
  *Mitigation*: mirror those functions' composition exactly (read them; don't edit them) so
  WP02/WP10 line up.
- **Complexity ceiling (Sonar S3776 / ruff C901 ≤15)**: a single fat `resolve_sync_target`
  would exceed 15. *Mitigation*: extract read/classify/derive/diagnose/guard helpers; add a
  focused test per helper branch.

## Review Guidance

For `/spec-kitty.review`, verify:

- `ResolvedSyncTarget` carries all eight contract §1 fields with the exact enum tokens.
- The resolver reads `[sync].server_url` and `SPEC_KITTY_SAAS_URL` and computes
  `override_mode` (T002) with correct env-over-config precedence matching
  `saas/readiness.py::_probe_host_config()`.
- `derived_queue_scope`/`queue_db_path` are derived from the resolved URL + identity, with
  **no** public parameter that injects a scope (contract §1 rule; C-002).
- `active_queue_scope_status` is a pure diagnostic and the stale cache is never used to pick
  a queue (contract §1 "Required tests").
- The split-brain guard decides before any network call and either applies a whole-process
  override consistently or fails/warns (SC-008).
- `tests/sync/test_target_authority.py` covers: all fields populated; env/config disagreement
  cannot split target vs scope; stale scope reported and ignored.
- `ruff` and `mypy` are clean with no new suppressions; functions ≤15 complexity.
- No `feature*` aliases introduced (Terminology Canon).

## Activity Log
> Entries chronological, appended at END. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`
- 2026-06-29T06:21:37Z – system – Prompt created.
- 2026-06-29T07:20:08Z – claude:opus:python-pedro:implementer – shell_pid=27690 – Assigned agent via action command
- 2026-06-29T07:35:44Z – claude:opus:python-pedro:implementer – shell_pid=27690 – WP01 claimed: ResolvedSyncTarget resolver + ATDD; ruff/mypy/pytest green
- 2026-06-29T07:35:46Z – claude:opus:python-pedro:implementer – shell_pid=27690 – WP01 in_progress: ResolvedSyncTarget resolver + ATDD; ruff/mypy/pytest green
- 2026-06-29T07:37:39Z – claude:opus:python-pedro:implementer – shell_pid=27690 – Ready: ResolvedSyncTarget resolver + ATDD; ruff/mypy/pytest green
- 2026-06-29T07:39:22Z – claude:opus:reviewer-renata:reviewer – shell_pid=30246 – Started review via action command
- 2026-06-29T07:46:35Z – user – shell_pid=30246 – Review passed: contract §1 honored — all 9 ResolvedSyncTarget fields, StrEnum tokens none/setup_only/process_override + absent/matches/stale_non_authoritative, scope DERIVED via real build_queue_scope/scope_db_path with no injectable param (C-002), split-brain guard fails-closed pre-network (SC-008). ATDD red->green confirmed (test commit precedes impl). Identifier Safety: ASCII allowlist + accented-Latin .isascii() regression. mypy --strict + ruff clean, 24 tests pass, 100% new-code coverage, no out-of-scope code edits.

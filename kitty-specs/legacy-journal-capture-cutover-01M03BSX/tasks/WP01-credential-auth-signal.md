---
work_package_id: WP01
title: Restore credential parsing as an auth signal
dependencies: []
requirement_refs:
- FR-004
- FR-009
planning_base_branch: fix/legacy-journal-capture-cutover
merge_target_branch: fix/legacy-journal-capture-cutover
branch_strategy: Planning artifacts for this mission were generated on fix/legacy-journal-capture-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/legacy-journal-capture-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
history:
- at: '2026-08-15T00:00:00Z'
  actor: claude
  note: WP authored by tasks phase
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/sync/
create_intent:
- tests/sync/test_credential_scope_signal.py
execution_mode: code_change
owned_files:
- src/specify_cli/sync/queue.py
- src/specify_cli/sync/preflight.py
- src/specify_cli/sync/target_authority.py
- src/specify_cli/cli/commands/agent/mission_setup_plan.py
- tests/sync/test_credential_scope_signal.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before reading any code or editing any file, run:**

```
/ad-hoc-profile-load implementer-ivan
```

This loads your identity, ownership boundaries, and the governance context that binds
this work package (charter principles, red-first C-011, the "use canonical sources"
rule, and the terminology canon). Do not skip it: the profile tells you which files you
may mutate (`owned_files` above), which surfaces are off-limits (everything else), and
the ATDD-first discipline this WP is built around. Only after the profile is loaded and
you have confirmed your boundaries should you proceed to the Objective.

---

## Objective

Fix the **#3293 credential regression** (research.md Decision 1; spec US2 / FR-004) so a
genuinely-authenticated host is no longer refused at the setup-plan auth gate — **without
reverting #3293's ProjectSyncStore-owned queue selection** (FR-009 / C-003).

The regression narrowed `read_queue_scope_from_credentials` (`src/specify_cli/sync/queue.py:175-180`)
to a JSON-only read of an explicit `queue_scope` field. The supported credential format
the existing reproductions write no longer yields a scope, so the FR-011 auth gate in
`mission_setup_plan.py:1043-1075` treats an authenticated host as unauthenticated and
exits 2.

The fix is an **auth signal only**. Restoring parsing must let the gate answer the boolean
question "is this host authenticated?" — it must NOT re-introduce a credential→`scope_db_path`
derivation at `preflight.py` / `target_authority.py`. Deriving a live physical store path
from credentials is exactly the C-003/FR-009 revert this WP must avoid (research.md Decision
10, "Auth-signal (MAJOR-4)"; data-model.md "Credentials → auth signal (not a path)").

This WP is IC-01 in the plan (plan.md:147-153). It is the independent un-redder: it has no
dependencies and does not touch the layout/cutover surface.

---

## Context

**The two-bug split.** #3425 is really two defects on one root surface (research.md Decision
1). This WP owns the *credential* half — the one that reddens the blocking CI suite on `main`
today (spec US2 "Why this priority"). The layout silent-capture half is a separate WP.

**The revert-risk seam.** The restored parse value flows through several consumers that feed
`scope_db_path(...)`, which resolves a live legacy queue DB path:

- `preflight.py:480-484` — `read_queue_scope_from_credentials()` result is split on `"|"`
  (`credentials_scope.split("|")`, expecting the canonical `server|user|team` form).
- `preflight.py:516-519` — `_read_queue_scope_local_only()` result is passed to
  `scope_db_path(scope)` to choose the physical queue DB the preflight reports on
  (`_read_queue_scope_local_only` itself, at `preflight.py:397-416`, falls back to
  `read_queue_scope_from_credentials`).
- `target_authority.py:391-404` — `_read_cached_scope()` reads
  `read_queue_scope_from_credentials()`, but only as a **diagnostic** (`_diagnose_scope_status`
  at 407-418 explicitly reports, never selects — see the docstring "never used to pick a queue
  or DB path").
- `target_authority.py:465-466` — the authoritative `queue_db_path` is derived from
  `_derive_queue_scope(...)` → `scope_db_path(...)`, and does **not** read credentials.

So the trap is real for `preflight.py:516` (which would change which physical store a live
write lands in) and cosmetic for `target_authority.py` (diagnostic-only). The gate itself
(`mission_setup_plan.py:1059`) needs only a **boolean** "authenticated?", not a path.

**The gate.** `_enforce_saas_sync_auth_refusal` (`mission_setup_plan.py:1043-1075`) is
short-circuited by `SPEC_KITTY_ENABLE_SAAS_SYNC != "1"`, then computes
`read_queue_scope_from_session() or read_queue_scope_from_credentials()` and exits 2 with
`SAAS_SYNC_UNAUTHENTICATED` when that is falsy. Restoring parsing makes that truthy for an
authenticated host — which is all the gate needs.

---

## Subtasks

### T001 — Red-first: authenticated coherent host passes preflight (exit 0)

**Purpose.** Pin the FR-004 / SC-002 contract with a failing test *before* any production
change (C-011). The test proves that, with credentials written in the supported format on a
coherent authenticated host, `setup-plan`'s auth gate passes (exit 0) rather than refusing
with exit 2.

**Concrete steps.**
1. Create `tests/sync/test_credential_scope_signal.py` (declared in `create_intent`).
2. Add a fixture that isolates BOTH home roots to a temp dir: set `HOME` **and**
   `SPEC_KITTY_HOME` (and `XDG_*`/`APPDATA` as the sibling tests do) via `monkeypatch.setenv`
   pointing at `tmp_path`. This dev box's real `~/.spec-kitty` is a live legacy root
   (plan.md:131-133) — pinning only `HOME` is insufficient because scope/credential paths key
   off `SPEC_KITTY_HOME`.
3. Write credentials in the supported format the reproductions use (the `server|user|team`
   piped scope form the pre-#3293 parser accepted — see `preflight.py:479` "Canonical scope is
   `server|user|team`").
4. Set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` so the gate at `mission_setup_plan.py:1052` does not
   short-circuit.
5. Drive `_enforce_saas_sync_auth_refusal(json_output=True)` (or the real setup-plan entry
   point) and assert it does **not** raise `typer.Exit(code=2)` — i.e. the authenticated host
   is accepted.

**Files touched.** `tests/sync/test_credential_scope_signal.py` (new).

**Validation checklist.**
- [ ] Test FAILS before T002 (currently `read_queue_scope_from_credentials` returns `None` for
      the piped form → gate exits 2).
- [ ] Test pins BOTH `HOME` and `SPEC_KITTY_HOME` to a temp root.
- [ ] No ambient auth is consulted (no network, no real credentials file).

**Edge cases.** Ensure `SPEC_KITTY_ENABLE_SAAS_SYNC` is restored/unset by the fixture so the
gate short-circuit state does not leak to other tests.

### T002 — Restore `read_queue_scope_from_credentials` parsing to yield an auth signal

**Purpose.** Make `read_queue_scope_from_credentials` (`queue.py:175-180`) recognise the
supported credential format again so it returns a truthy scope string for an authenticated
host — turning T001 green — while remaining a pure, side-effect-free read.

**Concrete steps.**
1. In `queue.py:175-180`, extend the parse so that, in addition to the current JSON
   `queue_scope` field, the supported on-disk credential form (the `server|user|team` piped
   scope the pre-#3293 code produced, and that `preflight.py:482` still splits on `"|"`) is
   recognised and returned as a scope string.
2. Keep the function pure: no migration side effect, no SaaS round-trip, no path resolution.
   It returns `str | None` exactly as today (the signature and `__all__` export at
   `queue.py:527` stay unchanged).
3. Do NOT change `scope_db_path` (`queue.py:148-149`) or `build_queue_scope`
   (`queue.py:143-145`). This WP only restores the *read*, never the path derivation.

**Files touched.** `src/specify_cli/sync/queue.py`.

**Validation checklist.**
- [ ] T001 now passes.
- [ ] `read_queue_scope_from_credentials` still returns `None` for genuinely-absent/garbage
      credentials (no false positives).
- [ ] Function performs no I/O beyond the existing credentials-file read; no migration call.
- [ ] `ruff` + `mypy` clean on `queue.py`.

**Edge cases.** Corrupt/partial credentials must yield `None`, not raise (preserve the
`_read_json`-style defensive posture at `queue.py:167-172`). A JSON `queue_scope` explicit
value must still win where present (do not regress the current behavior).

### T003 — Gate consumes the boolean auth signal

**Purpose.** Confirm the FR-011 gate at `mission_setup_plan.py:1043-1075` treats the restored
scope purely as a boolean "authenticated?" — it already does (`if _scope: return` at line
1060), so this subtask is a *verification-and-lock* step, not a rewrite.

**Concrete steps.**
1. Read `_enforce_saas_sync_auth_refusal` (`mission_setup_plan.py:1043-1075`). Confirm line
   1059 (`_scope = read_queue_scope_from_session() or read_queue_scope_from_credentials()`)
   and line 1060 (`if _scope: return`) consume the value only as a truthiness signal — the
   scope string is never passed to `scope_db_path` or any store selector here.
2. If (and only if) any code on this gate path passes the credential-derived scope into a
   physical path, refactor it so the gate keeps a boolean signal. Expected outcome: **no code
   change needed** in `mission_setup_plan.py` beyond a clarifying comment that the value is an
   auth signal, not a path.
3. Add a focused assertion in `tests/sync/test_credential_scope_signal.py` that the gate accepts
   the host **without** materializing or touching any queue DB file (assert no
   `queue-*.db`/`queue.db` is created under the isolated `SPEC_KITTY_HOME` by the gate call).

**Files touched.** `src/specify_cli/cli/commands/agent/mission_setup_plan.py` (comment only,
if anything), `tests/sync/test_credential_scope_signal.py`.

**Validation checklist.**
- [ ] Gate path never calls `scope_db_path` with the credential-derived value.
- [ ] Test asserts no physical queue DB is created by the gate.
- [ ] If `mission_setup_plan.py` is edited, it is comment-only; no behavioral change to the
      gate ordering (it still runs before project-root resolution — line 1044-1050).

**Edge cases.** The daemon-owner-mismatch scenario (spec US2 acceptance #2): the boundary
preflight refusal must remain the one surfaced; the auth signal must not mask it by
short-circuiting a legitimate later refusal.

### T004 — Red-first: physical-store invariance (INV-6)

**Purpose.** Guarantee that restoring credential parsing does NOT change which physical store
a live write lands in (data-model.md INV-6; plan.md:124-126). This is the test that catches an
accidental C-003/FR-009 revert. Write it red-first against the pre-T002 behavior *or* as a
before/after invariant.

**Concrete steps.**
1. In `tests/sync/test_credential_scope_signal.py`, under the same BOTH-home-pinned isolation,
   capture the physical store selection the sync surface resolves for a live write.
2. Assert via `preflight.py` / `target_authority.py`, not via a private helper: e.g. call the
   read-only path resolver `_resolve_queue_db_path_readonly()` (`preflight.py:488-519`) — which
   routes through `_read_queue_scope_local_only()` → `scope_db_path` — and assert the resolved
   DB path is the **same** whether or not the restored credential parse is active. Equivalently,
   assert `resolve_sync_target(...)` (`target_authority.py:426-478`) yields the same
   `queue_db_path` (derived from `_derive_queue_scope`, `target_authority.py:465-466`, which
   does not read credentials) regardless of the credential parse.
3. The invariant to pin: the ProjectSyncStore-owned selection is authoritative; the credential
   read is an auth signal that must be *inert* for physical-store selection.

**Files touched.** `tests/sync/test_credential_scope_signal.py`.

**Validation checklist.**
- [ ] Test asserts the resolved physical DB path is unchanged by the credential-parse restore.
- [ ] Assertion goes through `preflight.py` / `target_authority.py` public-ish surfaces, not a
      re-implementation of path logic in the test.
- [ ] BOTH `HOME` and `SPEC_KITTY_HOME` pinned; deterministic, no ambient auth.

**Edge cases.** If restoring parsing at `queue.py` *would* have changed `preflight.py:516`'s
`scope_db_path(scope)` result (because the piped scope now flows there), the fix must ensure
the ProjectSyncStore selection still wins — the test must FAIL loudly if credential parsing
starts steering the physical store. That failure signal is the whole point of this subtask.

### T005 — Green the B/C reproductions; keep the JSON path

**Purpose.** Turn the two credential-regression reproductions (research.md Decision 1 "Tests B
& C") green, and confirm the existing JSON `queue_scope` behavior is preserved (no regression
of #3293's explicit-scope handling).

**Concrete steps.**
1. Identify the B/C reproductions that fail because `read_queue_scope_from_credentials` no
   longer derives a scope from the TOML/piped credentials (research.md Decision 1 names
   `sync/queue.py:175` and the gate at `mission_setup_plan.py:1043-1075`). Run them and confirm
   they now pass after T002.
2. Add/keep an assertion in `tests/sync/test_credential_scope_signal.py` that a JSON credentials
   file with an explicit `queue_scope` still returns that scope (guards against T002
   accidentally dropping the current path).
3. Do NOT modify the B/C reproduction files themselves if they already assert the correct
   contract — only the credential *parser* and the new signal test are in scope here. (Rewriting
   the mis-built #3425 reproductions is a different WP / IC-06.)

**Files touched.** `tests/sync/test_credential_scope_signal.py` (assertions); no production
change beyond T002.

**Validation checklist.**
- [ ] B/C reproductions pass on-branch.
- [ ] JSON explicit-`queue_scope` path still works (regression assertion green).
- [ ] No B/C reproduction file is edited unless it asserts a retired contract (out of scope
      here — flag it for IC-06 instead of editing).

**Edge cases.** If a B/C reproduction is red for a *layout* reason rather than the credential
reason, it belongs to the other WP — do not "fix" it here; note it and move on.

---

## Branch Strategy

- **Planning / base branch:** `fix/legacy-journal-capture-cutover`.
- **Merge target:** `fix/legacy-journal-capture-cutover` (same branch — this is a fix mission,
  not a `main` PR from the WP).
- **Execution:** `branch_strategy: lane`. The execution worktree is allocated per the computed
  lane from `lanes.json` — do NOT hand-construct a worktree path.
- **The only supported command to prepare the workspace:**

  ```
  spec-kitty agent action implement WP01 --agent <name>
  ```

  Consume the resolved workspace path the resolver returns; never reconstruct it.

---

## Test Strategy

- **Red-first (C-011).** T001 and T004 are authored to FAIL before the corresponding production
  change and pass after. Do not write the production fix first.
- **Auth-test isolation is mandatory.** Every auth/credential test pins BOTH `SPEC_KITTY_HOME`
  and `HOME` (plus `XDG_*`/`APPDATA` per the sibling tests) to an isolated temp root. This dev
  box's real `~/.spec-kitty` is a live legacy root (plan.md:131-133) — pinning only `HOME` is a
  known footgun. Scope/credential resolution keys off `SPEC_KITTY_HOME`.
- **Deterministic, no ambient auth.** Tests must not read the real credentials file, contact
  SaaS, or depend on the machine's login state. All roots are temp roots.
- **Fast, targeted runs only.** Do not run the full suite (it hangs the session and takes ~1h);
  CI is the release authority. Run:

  ```
  PWHEADLESS=1 .venv/bin/python -m pytest tests/sync/test_credential_scope_signal.py -q
  ```

  Prepend `.venv/bin` to `PATH` (shadow-venv footgun) — a bare `spec-kitty`/`python` runs the
  wrong interpreter.

---

## Definition of Done

- [ ] T001 red-first test passes: authenticated coherent host passes the gate (exit 0),
      `SPEC_KITTY_HOME` + `HOME` isolated.
- [ ] The B/C credential-regression reproductions pass on-branch (FR-004 / SC-002).
- [ ] T004 physical-store invariance test is green — restoring parsing does NOT change which
      physical store a live write lands in (INV-6 / FR-009 / C-003).
- [ ] JSON explicit-`queue_scope` path still works (no #3293 regression).
- [ ] `ruff check` and `mypy` clean on all owned production files (`queue.py`, `preflight.py`,
      `target_authority.py`, `mission_setup_plan.py`) — zero issues, zero suppressions added.
- [ ] **No #3293 revert:** `scope_db_path` and `build_queue_scope` are unchanged; the
      ProjectSyncStore-owned selection is preserved.
- [ ] Only `owned_files` are modified; no other file touched. No commit made by the implementer.

---

## Risks & Reviewer Guidance

- **The C-003 / FR-009 revert trap (primary risk).** Restoring `read_queue_scope_from_credentials`
  makes a real scope flow into consumers that call `scope_db_path` — notably
  `preflight.py:516` (`scope_db_path(scope)` via `_read_queue_scope_local_only`). If that changes
  which physical DB a live write lands in, it is a partial revert of #3293's ProjectSyncStore
  selection, which is forbidden (FR-009 / C-003; plan.md:124-126; data-model.md INV-6).
- **Reviewer must confirm:**
  1. `scope_db_path` (`queue.py:148-149`) and `build_queue_scope` (`queue.py:143-145`) are
     byte-for-byte unchanged.
  2. The credential-derived scope is consumed **only** as a boolean auth signal at the gate
     (`mission_setup_plan.py:1059-1060`) — never passed into a store selector on the live-write
     path.
  3. `target_authority.py:465-466` still derives `queue_db_path` from `_derive_queue_scope`
     (not from credentials) — the credential read at `_read_cached_scope` (401-404) remains
     diagnostic-only (`_diagnose_scope_status`, 407-418).
  4. The T004 invariance test genuinely asserts through `preflight.py` / `target_authority.py`
     and would fail if credential parsing started steering the physical store.
- **Isolation drift risk.** A test that pins only `HOME` can silently pass by reading this box's
  live legacy root. Reviewer should confirm every test in the new file pins `SPEC_KITTY_HOME`
  as well.
